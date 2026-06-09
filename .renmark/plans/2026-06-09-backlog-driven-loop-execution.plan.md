# Plan: backlog-driven-loop-execution (MVP)

**Feature goal:** Add a `/renmark:backlog` interactive intake + approval-buffer layer
(PRD REQ-13) that lists candidate work items, opens a per-item detail view, and on
"Approve and build" launches bounded Loop Mode (hardcoded max 5 iterations, no
user-facing budget/iteration/ID flags) on a managed feature branch — committing
passing iterations, gating on human merge approval, and guaranteeing every managed
branch ends merged+deleted, abandoned+deleted, or explicitly kept (no orphans).
Also lands a **design-only** scheduled-QA read-only seam (PRD REQ-14, not executed).

**Reuses, never replaces:** `renmark/loop.py` (LoopState, DEFAULT_MAX_ITERATIONS=5,
build_decision, stop_reason, read/write_loop), the `/renmark:loop` driving procedure,
`/renmark:orchestrate` / `/renmark:verify` / `/renmark:finish`, and the
lifecycle/state runtime. Backlog item state persists under `.renmark/state/backlog/`
via `state.state_dir(repo)`. **No new dependencies — Python ≥3.10 stdlib only.**

**Cross-cutting constraints (every task honors):** context hygiene — orchestrator/
skill reads only summaries, paths, metadata, status, verification evidence, never
code/diffs/full bodies; human gates preserved for merge / release / PRD edits /
destructive changes / budget escalation; only one code-writing loop per working
tree; `backlog.py` mirrors `loop.py`'s never-raise persistence (corrupt/missing JSON
degrades, never throws into chat). Dev gates: `pytest -q` · `ruff check` · `mypy .`.

---

### Task 1: backlog state model + persistence + branch-disposition logic
- **mode:** A
- **target:** renmark/backlog.py
- **complexity:** hard
- **executor:** opus
- **parallel_group:** 1
- **est_tokens:** 1500
- **est_cost_usd:** 0.17
- **verifier:** python3 -c "import renmark.backlog"
- **serves:** REQ-13
- **spec:**
  New deterministic, **never-raise** module mirroring the style of `renmark/loop.py`
  (read it first for the dataclass + `_coerce_*` + read/write/never-raise pattern, and
  reuse `from .state import state_dir`). Public surface (keep JSON-trivial: str/int/bool
  only so json round-trips with no custom serializer):

  - `STATUSES: tuple[str, ...]` — exactly: `"needs review"`, `"needs approval"`,
    `"approved"`, `"in progress"`, `"blocked"`, `"completed"`, `"rejected"`.
  - `RISKS`/`SOURCES` — light open string fields (not enums); just document expected
    values (risk: low/medium/high; source: e.g. user / qa / research / bug / idea).
  - `DISPOSITIONS: tuple[str, ...]` — branch end-states: `"merged-deleted"`,
    `"abandoned-deleted"`, `"kept"` (the no-orphan-branch invariant — every managed
    branch MUST end in exactly one).
  - `@dataclass BacklogItem` fields: `id: str` (BL-NNNN), `title: str`,
    `status: str = "needs review"`, `source: str = ""`, `risk: str = ""`,
    `summary: str = ""`, `evidence_path: str = ""`, `recommended_action: str = ""`,
    `served_requirements: str = ""` (e.g. "REQ-7" or ""), `pending_decision: str = ""`,
    `branch: str = ""`, `loop_id: str = ""`, `disposition: str = ""`,
    `created_at: str = ""`, `updated_at: str = ""`. Add `to_json()` like LoopState.
  - `backlog_dir(repo) -> Path` → `state_dir(repo) / "backlog"`.
  - `next_id(repo) -> str` — scan existing `BL-*.json`, return next zero-padded
    `BL-NNNN` (start `BL-0001`); never raise on a malformed filename (skip it).
  - `read_item(repo, item_id) -> BacklogItem | None` and
    `write_item(repo, item) -> Path | None` — never-raise; corrupt JSON → `None`,
    coerce unknown status → `"needs review"` (mirror `_coerce_status`).
  - `list_items(repo) -> list[BacklogItem]` — newest-first by `created_at` then id;
    never raise (skip unreadable files).
  - `managed_branch_name(item_id, slug) -> str` → `feature/backlog-<item_id-lowercased>-<safe-slug>`
    (sanitize slug like `loop.loop_id` does).
  - `completion_report(*, goal_reached: bool, iteration: int, max_iterations: int) -> str`
    — returns EXACTLY `f"Goal reached in {iteration}/{max_iterations} iterations."` when
    `goal_reached`, else `f"Stopped after {iteration}/{max_iterations} iterations. Goal not fully verified."`.
  - `status_for_outcome(*, goal_reached: bool) -> str` → `"completed"` if reached else
    `"blocked"`.
  - `is_terminal_disposition(value: str) -> bool` → `value in DISPOSITIONS`.

  Pure logic only — NO git calls, NO loop driving, NO network. Branch creation/merge/
  delete is performed by the SKILL (Task 3) via existing git/`/renmark:finish`; this
  module only NAMES branches and RECORDS dispositions. Full type hints (mypy clean),
  ruff clean.

### Task 2: tests for the backlog model
- **mode:** A
- **target:** tests/test_backlog.py
- **complexity:** medium
- **executor:** codex
- **parallel_group:** 2
- **est_tokens:** 1300
- **est_cost_usd:** 0.07
- **verifier:** python3 -m pytest tests/test_backlog.py -q
- **serves:** REQ-13
- **spec:**
  pytest tests for `renmark/backlog.py` (Task 1 — same public surface listed there).
  Use `tmp_path` as `repo`. Cover:
  - `next_id` returns `BL-0001` on empty backlog, increments past existing items, and
    skips malformed filenames without raising.
  - `write_item` → `read_item` round-trips all fields; reading a missing id → `None`;
    reading a corrupt/non-JSON file → `None` (never raises); an unknown `status` on disk
    coerces to `"needs review"`.
  - `list_items` is newest-first and skips unreadable files without raising.
  - `completion_report` wording is EXACT for both branches: `"Goal reached in 3/5
    iterations."` and `"Stopped after 5/5 iterations. Goal not fully verified."`.
  - `status_for_outcome` maps reached→`"completed"`, not-reached→`"blocked"`.
  - `managed_branch_name` is deterministic, lowercased, path-safe.
  - `DISPOSITIONS` contains exactly the three no-orphan end-states and
    `is_terminal_disposition` accepts them / rejects `""`.
  Match the existing repo test style (see `tests/` for conventions). No network, no git.

### Task 3: /renmark:backlog interactive skill
- **mode:** A
- **target:** plugin/skills/backlog/SKILL.md
- **complexity:** hard
- **executor:** opus
- **parallel_group:** 2
- **est_tokens:** 2200
- **est_cost_usd:** 0.18
- **verifier:** grep -q '^name: backlog' plugin/skills/backlog/SKILL.md && grep -q 'next-steps.md' plugin/skills/backlog/SKILL.md
- **serves:** REQ-13
- **spec:**
  New SKILL.md (study `plugin/skills/loop/SKILL.md` and `plugin/skills/feature/SKILL.md`
  for house style, the next-steps citation block, and governance framing). YAML
  frontmatter: `name: backlog` (MUST match dir), plus a `description:` covering: typed
  as `/renmark:backlog`; interactive intake + approval buffer; lists items then opens a
  detail view; "Approve and build" launches bounded Loop Mode internally.

  Body must specify:
  - **Step 0 — Context check:** `lifecycle.skill_preamble(repo, 'backlog')`; surface a
    one-line hint if non-None. Also check for an in-flight loop / in-progress item and
    offer to resume instead of starting fresh.
  - **List view:** read `backlog.list_items(repo)`, render a selectable list via
    `AskUserQuestion` showing title · status · source · risk · pending decision. Reading
    items is bounded metadata only (context hygiene).
  - **Detail view** (per selected item): show summary, source, evidence path, recommended
    action, risk, current status, served requirements (if known). Offer actions via
    `AskUserQuestion`: **Approve and build**, **Research more**, **Split into smaller
    items**, **Reject**, **Back**.
  - **Approve and build** (the load-bearing wiring): set item `status="approved"`→`"in
    progress"` (persist via `backlog.write_item`); derive goal from the item
    (title + summary + recommended_action); create a managed branch via
    `backlog.managed_branch_name(item.id, slug)` (`git checkout -b`); run **bounded Loop
    Mode** following the `/renmark:loop` driving procedure with **`max_iterations=5`
    hardcoded** and the default budget — NO user-facing `--budget`/`--max-iterations`/
    backlog-ID flags (vibe-coder flow). Commit each passing iteration to the branch (the
    loop already does this). On terminal status, print the bounded completion report from
    `backlog.completion_report(...)` ("Goal reached in N/5…" / "Stopped after 5/5…").
  - **Branch lifecycle / NO ORPHAN BRANCHES:**
    - Final verify PASS → **STOP for human merge approval** (REQ-12 gate; never
      auto-merge). On merge approval: merge into `main`, **re-run `/renmark:verify` on
      `main`**, delete the feature branch, set item `status="completed"` and
      `disposition="merged-deleted"`.
    - Final verify FAIL or loop reached 5/5 without success → **do NOT merge**; set item
      `status="blocked"` (needs review) and OFFER keep-or-delete via `AskUserQuestion`
      → set `disposition` to `"kept"` or `"abandoned-deleted"` (delete the branch on
      abandon). Every managed branch MUST end in exactly one `DISPOSITION` — record it on
      the item before returning.
  - **Research more / Split / Reject / Back:** Research more → route to research/brainstorm
    and leave status `"needs review"`; Split → guidance to create child items (status
    `"needs approval"`) — MVP may stub the mechanics but must persist intent; Reject → set
    `status="rejected"`; Back → return to list view.
  - **Human gates & hygiene (call out explicitly):** merge/release/PRD-edit/destructive/
    budget-escalation all require human approval; only one code-writing loop per working
    tree (refuse to start a second concurrent build); orchestrator/skill reads only
    summaries/paths/metadata/status/verification evidence — never code or diffs.
  - **Scheduled QA seam:** one-line pointer to `plugin/skills/backlog/SCHEDULED-QA.md`
    (Task 5) noting the read-only proposer lane is design-only (REQ-14), not executed here.
  - **Next step:** cite `${CLAUDE_PLUGIN_ROOT}/skills/_shared/next-steps.md` exactly like
    `loop/SKILL.md` does (required by the lint contract — do NOT paste the rules), and end
    with `*Mirror any rule changes in AGENTS.md in the same commit.*`.

### Task 4: register backlog in lifecycle domain + aux class
- **mode:** B
- **target:** renmark/lifecycle.py
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 2
- **est_tokens:** 450
- **est_cost_usd:** 0.03
- **verifier:** python3 -c "from renmark import lifecycle as l; assert l.DOMAIN_BY_SKILL['backlog']=='build'; assert 'backlog' in l.AUX_SKILLS; assert 'backlog' in l.AUX_LOCAL_ACTIONS"
- **serves:** REQ-13
- **spec:**
  Register the new `backlog` skill in the existing module-level registries (do not touch
  `PIPELINE_SKILLS` — backlog does not advance a Tier-0 lifecycle stage, so it is an aux
  skill):
  - Add `"backlog": "build"` to `DOMAIN_BY_SKILL` (shares the build domain with
    loop/orchestrate so "Approve and build" is NOT flagged as a cross-domain `/clear`
    transition).
  - Add `"backlog"` to `AUX_SKILLS`.
  - Add a `"backlog"` entry to `AUX_LOCAL_ACTIONS` with up to 2 follow-ups, e.g.
    `["/renmark:backlog (refresh the list)", "/renmark:finish"]`.
  Pure edits — keep formatting consistent with surrounding entries. mypy + ruff clean. No
  behavior change beyond registration; existing tests (test_next_steps iterates these
  frozensets) must stay green.

### Task 5: scheduled-QA read-only lane — design-only seam doc (REQ-14)
- **mode:** A
- **target:** plugin/skills/backlog/SCHEDULED-QA.md
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 2
- **est_tokens:** 900
- **est_cost_usd:** 0.03
- **verifier:** test -f plugin/skills/backlog/SCHEDULED-QA.md && grep -qi 'read-only' plugin/skills/backlog/SCHEDULED-QA.md && grep -q 'REQ-14' plugin/skills/backlog/SCHEDULED-QA.md
- **serves:** REQ-14
- **spec:**
  A DESIGN-ONLY (not implemented) reference doc co-located with the backlog skill,
  describing the future scheduled QA / Deep-QA lane per PRD REQ-14. NOT a SKILL.md (no
  frontmatter needed; lint only governs SKILL.md). Must state plainly:
  - **Purpose:** the read-only proposer lane — the third of renmark's four lanes
    (foreground feature / backlog intake / scheduled QA / execution). It feeds the backlog
    intake lane; it is the approval buffer's upstream.
  - **MAY:** inspect the project, run checks, research issues, write QA reports, and
    **propose** backlog items (status `"needs review"`).
  - **MUST NOT:** edit product code, commit, merge, release, edit `PRD.md`, escalate
    budget, or auto-execute backlog items. Autonomous scheduled *execution* is explicitly
    out of scope (still Deferred in the PRD).
  - **Clean seam:** how a future scheduler would call `backlog.write_item` to enqueue a
    proposed item (status `"needs review"`, `source="qa"`, an `evidence_path` to its
    report) WITHOUT touching code — so the MVP leaves the integration point obvious.
  - **Parallelism:** scheduled QA is read-only and may run in parallel; only one
    code-writing loop may run per working tree.
  Keep it concise (design doc, not a spec). Reference REQ-14 explicitly.

### Task 6: /renmark:backlog command shim
- **mode:** A
- **target:** plugin/commands/backlog.md
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 3
- **est_tokens:** 200
- **est_cost_usd:** 0.00
- **verifier:** test -f plugin/commands/backlog.md && grep -q 'skills/backlog/SKILL.md' plugin/commands/backlog.md
- **serves:** REQ-13
- **spec:**
  Command shim mirroring `plugin/commands/loop.md` EXACTLY in structure. YAML
  frontmatter with a `description:` (interactive backlog intake + approval buffer; lists
  items, opens a detail view, "Approve and build" launches bounded Loop Mode internally)
  and an `argument-hint:` (e.g. `'[item-id]'`, optional). Body: `Read
  ${CLAUDE_PLUGIN_ROOT}/skills/backlog/SKILL.md and follow its instructions exactly. The
  user provided this input: $ARGUMENTS` + the "If $ARGUMENTS is empty, begin the backlog
  skill's flow." line. This file + the SKILL.md satisfy the lint command↔skill pairing.

### Task 7: add /renmark:backlog to CLAUDE.md tooling table
- **mode:** B
- **target:** CLAUDE.md
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 3
- **est_tokens:** 200
- **est_cost_usd:** 0.00
- **verifier:** grep -q 'renmark:backlog' CLAUDE.md
- **serves:** REQ-13
- **spec:**
  In the "## Tooling — renmark workflow" table (around line 360), add one row for
  `/renmark:backlog` with a one-sentence description: "Interactive backlog intake +
  approval buffer; 'Approve and build' launches bounded Loop Mode on a managed branch."
  Place it adjacent to the loop/feature rows. Do NOT alter other rows. (AGENTS.md mirror
  is Task 8.)

### Task 8: mirror /renmark:backlog into AGENTS.md tooling table
- **mode:** B
- **target:** AGENTS.md
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 3
- **est_tokens:** 200
- **est_cost_usd:** 0.00
- **verifier:** grep -q 'renmark:backlog' AGENTS.md
- **serves:** REQ-13
- **spec:**
  Mirror Task 7 verbatim into the "## Tooling — renmark workflow" table in AGENTS.md
  (around line 63) — same `/renmark:backlog` row, same wording, same placement. The two
  files are intentionally kept in sync.

---

## Cost preview

| # | Task | Executor | Group | est_tokens | est_cost |
|---|---|---|---|---|---|
| 1 | renmark/backlog.py | opus | 1 | 1500 | $0.17 |
| 2 | tests/test_backlog.py | codex | 2 | 1300 | $0.07 |
| 3 | plugin/skills/backlog/SKILL.md | opus | 2 | 2200 | $0.18 |
| 4 | renmark/lifecycle.py | sonnet | 2 | 450 | $0.03 |
| 5 | plugin/skills/backlog/SCHEDULED-QA.md | sonnet | 2 | 900 | $0.03 |
| 6 | plugin/commands/backlog.md | haiku | 3 | 200 | $0.00 |
| 7 | CLAUDE.md | haiku | 3 | 200 | $0.00 |
| 8 | AGENTS.md | haiku | 3 | 200 | $0.00 |

**Total (incl. ~10k Agent overhead per haiku/sonnet/opus task): ~$0.48**

Executors: haiku×3, codex×1, sonnet×2, opus×2. Waves: 3 (group 1 → group 2 → group 3).

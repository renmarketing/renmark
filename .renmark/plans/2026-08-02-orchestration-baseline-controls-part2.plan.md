# Orchestration baseline controls — Part 2: routing enforcement + artifact lifecycle contract

Continues Part 1 (`.renmark/plans/2026-08-02-orchestration-baseline-controls-part1.plan.md`).
Implements audit §9 item 5 and the goal's dispatch/routing + artifact-contract scope, per
`.renmark/audits/orchestration-baseline-audit-2026-08-02.md` (Owner-accepted
ORCHESTRATION-BASELINE-2026-08). Extends REQ-30 machinery: `plan_lint.py` already runs a real,
BLOCKing check on every plan via `/renmark:check-plan` (the one universal pre-dispatch gate for
BOTH the Claude-native and headless paths) — this reuses that existing enforcement point rather
than the dry-run-only surfaces the audit found (`subagent_gate.py`, `cost.requires_escalation`).
The new check is WARN-only, so it never changes the outcome of an already-passing plan — it adds
a real, always-run audit trail instead of a silent no-op.

### Task 1: plan_lint Check 11 — escalation-unjustified (WARN)
- **mode:** B
- **target:** renmark/plan_lint.py
- **complexity:** hard
- **executor:** opus
- **role:** code-implementer
- **parallel_group:** 1
- **est_tokens:** 1800
- **est_cost_usd:** 0.177
- **verifier:** python3 -m py_compile renmark/plan_lint.py
- **serves:** REQ-30
- **spec:**
  Read `_check_fable_declared` (~line 292) and `_check_fable_mechanical` (~line 313) first — this
  new check follows the exact same shape (a `_check_*(tasks) -> list[tuple[str, str]]` function
  returning `(severity, message)` tuples, registered wherever those two are collected into the
  overall check-plan result — find that registration point and add this function there too).

  Add `_check_escalation_justified(tasks: list[Task]) -> list[tuple[str, str]]` (Check 11):
  - For each task where `t.executor in ("opus", "fable")`:
    - Derive a rough `kind` signal from the task's `role` and `spec` text (do not overfit — simple,
      conservative heuristics only): `kind="adversarial-review"` if `role == "reviewer"`;
      `kind="architecture"` if `t.complexity == "hard"` and the spec mentions any of
      `"state machine"`, `"architecture"`, `"cross-file"`, `"cross-module"`, `"migration"`
      (case-insensitive substring); else `kind=None`.
    - Call `from . import cost as _cost; justified = _cost.requires_escalation(complexity=t.complexity, kind=kind)`.
    - If NOT `justified`: append `("WARN", f"Task {t.index}: executor `{t.executor}` has no
      escalation justification recorded (complexity={t.complexity!r}, no architecture/adversarial/
      design-fork signal detected). See .renmark/memory/routing.md and
      plugin/skills/.shared/model-routing.md — confirm this escalation is intentional or reassign
      to `sonnet`/`codex`.")`.
  - **WARN only, never BLOCK.** This must not change the classification (PASS/WARN/BLOCK) of any
    plan that currently passes — it only adds visibility. Do not make this a BLOCK check under any
    circumstance; that would violate "must not change Renmark's pipeline outcomes."
  - Register the new check function in the same collection/aggregation logic the existing 10 checks
    use (read how `_check_fable_declared`'s result flows into the overall return value and mirror
    it exactly — do not build a second aggregation path).
  - Update this file's check count/docstring/comment if it names "10 checks" anywhere (e.g. a
    module docstring or a `CHECK_COUNT` constant) to reflect 11.

### Task 2: append_routing escalation_reason param
- **mode:** B
- **target:** renmark/memory.py
- **complexity:** simple
- **executor:** codex
- **role:** code-implementer
- **parallel_group:** 2
- **est_tokens:** 400
- **est_cost_usd:** 0.02
- **verifier:** python3 -m py_compile renmark/memory.py
- **serves:** REQ-30
- **spec:**
  `append_routing` (~line 260) currently takes `signature, executor, outcome, run_id=None,
  date=None, role=None`. Add one more trailing keyword param: `escalation_reason: str | None = None`.
  When it is not None/blank, append it to the constructed `line` (after the `role=` segment, same
  `if X and X.strip():` guard pattern already used for `role`): `line += f", escalation={escalation_reason.strip()}"`.
  Do not change any other behavior — existing callers that omit this param produce byte-identical
  output to today.

### Task 3: wire escalation reason into headless routing log
- **mode:** B
- **target:** renmark/cli/_engine.py
- **complexity:** medium
- **executor:** sonnet
- **role:** code-implementer
- **parallel_group:** 3
- **est_tokens:** 700
- **est_cost_usd:** 0.0261
- **verifier:** python3 -m py_compile renmark/cli/_engine.py
- **serves:** REQ-30
- **spec:**
  `_memory_log_outcome` (~line 249) already calls `_mem.append_routing(repo, signature=...,
  executor=task.executor, outcome=outcome, run_id=run_id)`, wrapped in `try/except Exception: pass`
  (keep that — this stays best-effort, matching the existing ledger-emission convention; do not make
  it fail-loud). Add: if `task.executor in ("opus", "fable")`, recompute the same
  justification check Task 1 added to `plan_lint.py` (import and reuse
  `renmark.plan_lint._check_escalation_justified` on a single-task list, or factor the per-task
  justification logic into a small shared helper both call — prefer factoring a tiny shared helper,
  e.g. `renmark.plan_lint.escalation_reason_for(task) -> str | None`, returning the WARN message
  text (or `None` if justified), and have BOTH `_check_escalation_justified` and this call site use
  it, so the logic lives in exactly one place). Pass the result as `escalation_reason=` to
  `append_routing`. For non-opus/fable executors, do not pass `escalation_reason` at all (keep the
  call exactly as it is today for those).

### Task 4: subagent-budget risk-trigger checklist
- **mode:** B
- **target:** plugin/skills/.shared/subagent-budget.md
- **complexity:** simple
- **executor:** haiku
- **role:** docs-editor
- **parallel_group:** 4
- **est_tokens:** 250
- **est_cost_usd:** 0.0101
- **verifier:** grep -q "security" plugin/skills/.shared/subagent-budget.md
- **serves:** REQ-30
- **spec:**
  Add a new short section, `## Independent reviewer — risk triggers`, listing exactly these seven
  triggers as a checklist (one per line, terse — this file is a reference doc, keep it that dense):
  security-sensitive change, data-loss risk, public/external contract change (API, schema, CLI
  flags), migration (data or schema), broad cross-module change, failed verification on the first
  pass, unresolved ambiguity in the task spec. State in one sentence: an independent
  `reviewer`-role dispatch is warranted when a task matches ANY of these; routine single-file
  changes with a clean first-pass verifier do not need one by default. Do not restate the existing
  subagent-profiles registry content — this is additive, a trigger list, not a role description.

### Task 5: model-routing.md real-enforcement citation
- **mode:** B
- **target:** plugin/skills/.shared/model-routing.md
- **complexity:** simple
- **executor:** haiku
- **role:** docs-editor
- **parallel_group:** 5
- **est_tokens:** 200
- **est_cost_usd:** 0.0092
- **verifier:** grep -q "plan_lint" plugin/skills/.shared/model-routing.md
- **serves:** REQ-30
- **spec:**
  Add one sentence near the "Hard escalation gate" section: check-plan's Check 11
  (`renmark/plan_lint.py`) now flags an `opus`/`fable` route lacking a `requires_escalation`-
  satisfying justification as a WARN on every plan validation (not just the `--dry-run` preview
  surface) — the routing table is enforced at the real pre-dispatch gate, not only documented. Keep
  it to one or two sentences; do not restate Check 11's logic here.

### Task 6: artifact lifecycle contract (new shared fragment)
- **mode:** A
- **target:** plugin/skills/.shared/artifact-lifecycle.md
- **complexity:** medium
- **executor:** sonnet
- **role:** docs-editor
- **parallel_group:** 6
- **est_tokens:** 900
- **est_cost_usd:** 0.03
- **verifier:** test -f plugin/skills/.shared/artifact-lifecycle.md
- **serves:** REQ-30
- **spec:**
  New reference doc, same style/precedent as `plugin/skills/.shared/context-taxonomy.md`. Content:

  - **Why:** extends CLAUDE.md's existing "Artifacts carry provenance and freshness metadata" block
    (which already requires `artifact_type`/`schema_version`/`created_at`/`source_sha`/
    `related_plan`/`generator`/`stale_after`/`dependency_refs`) with lifecycle rules that block
    does not yet cover: ownership, status, invalidation, replacement, and retention/archive.
  - **Lifecycle fields (additive to the existing provenance block, not a replacement):**
    `owner` (who/what generates and is responsible for this artifact — a skill name or `Owner` for
    human-authored files), `status` (`active | superseded | retired`), `dependencies` (paths this
    artifact was derived from — already partly covered by `dependency_refs`, cite it, don't
    duplicate), `invalidated_by` (what condition makes this artifact stale beyond `stale_after`'s
    timestamp — e.g. "source file changed", "superseding artifact published"), `replacement`
    (path to the artifact that supersedes this one, when `status: superseded`), `retention`
    (`durable | ephemeral` — durable artifacts live under `.renmark/memory/`, `.renmark/specs/`,
    `.renmark/plans/`; ephemeral ones under `.renmark/logs/`, `.renmark/state/`, per CLAUDE.md's
    existing canonical-homes list — cite that list, don't restate it).
  - **Retirement policy:** retiring a duplicated/stale artifact TYPE (not a bulk directory reorg)
    means: (1) stop the code/skill path that generates new instances of it, (2) leave existing
    instances on disk unless they are trivial one-off reruns explicitly named in an audit, (3) any
    reader that used to load that artifact type falls back to reading its replacement/canonical
    source — a backward-compatible read, never a hard break. Cite the ORCHESTRATION-BASELINE-2026-08
    audit (`.renmark/audits/orchestration-baseline-audit-2026-08-02.md`) as the worked example: it
    named `.renmark/memory/analytics.md` (stale, not auto-regenerated) and
    `.renmark/roadmap/agency-optimization-roadmap.md` (duplicate of the committed
    `.renmark/memory/roadmap.md`) as the first two targeted retirements under this policy.
  - Keep this file a reference doc — pointer-style, not a restatement of CLAUDE.md's existing
    provenance block.

### Task 7: CLAUDE.md pointer to artifact-lifecycle contract
- **mode:** B
- **target:** CLAUDE.md
- **complexity:** simple
- **executor:** haiku
- **role:** docs-editor
- **parallel_group:** 7
- **est_tokens:** 200
- **est_cost_usd:** 0.0092
- **verifier:** grep -q "artifact-lifecycle.md" CLAUDE.md
- **serves:** REQ-30
- **spec:**
  Find the existing "Artifacts carry provenance and freshness metadata" block in this file. Add one
  sentence at its end pointing to the new `plugin/skills/.shared/artifact-lifecycle.md` for the
  owner/status/dependencies/invalidation/replacement/retention rules — do not restate those rules
  inline, this file must stay thin per the project's own convention ("Keep CLAUDE.md/AGENTS.md thin
  and refer to canonical contracts").

### Task 8: AGENTS.md mirror
- **mode:** B
- **target:** AGENTS.md
- **complexity:** simple
- **executor:** haiku
- **role:** docs-editor
- **parallel_group:** 8
- **est_tokens:** 200
- **est_cost_usd:** 0.0092
- **verifier:** grep -q "artifact-lifecycle.md" AGENTS.md
- **serves:** REQ-30
- **spec:**
  Mirror Task 7's exact sentence into AGENTS.md's equivalent "Artifacts carry provenance and
  freshness metadata" block — this repo's own convention requires every CLAUDE.md rule change to be
  mirrored in AGENTS.md in the same commit. Keep the wording identical to Task 7's addition (adjust
  only for any pre-existing phrasing differences already present between the two files' equivalent
  blocks).

### Task 9: retire agency-optimization-roadmap.md duplicate
- **mode:** B
- **target:** .renmark/roadmap/agency-optimization-roadmap.md
- **complexity:** simple
- **executor:** haiku
- **role:** docs-editor
- **parallel_group:** 9
- **est_tokens:** 250
- **est_cost_usd:** 0.0101
- **verifier:** grep -q "memory/roadmap.md" .renmark/roadmap/agency-optimization-roadmap.md
- **serves:** REQ-30
- **spec:**
  This file duplicates the committed canonical `.renmark/memory/roadmap.md` (named as a retirement
  target in the ORCHESTRATION-BASELINE-2026-08 audit, §5). Per the retirement policy in Task 6's
  new `artifact-lifecycle.md`: do NOT delete the file (backward-compatible read — anything that
  already links to this path must not 404). Replace its body with a short frontmatter-style note:
  `status: retired`, `replacement: .renmark/memory/roadmap.md`, `retired_at: 2026-08-02`, one
  sentence explaining why (duplicate of the canonical roadmap memory file, retired per the
  ORCHESTRATION-BASELINE-2026-08 audit), and a pointer link to the replacement. Preserve the
  original filename and location — this is a targeted single-file retirement, not a directory
  reorg.

### Task 10: escalation-check tests
- **mode:** A
- **target:** tests/test_plan_lint_escalation.py
- **complexity:** medium
- **executor:** codex
- **role:** test-writer
- **parallel_group:** 10
- **est_tokens:** 900
- **est_cost_usd:** 0.03
- **verifier:** pytest tests/test_plan_lint_escalation.py -q
- **serves:** REQ-30
- **spec:**
  Test `renmark.plan_lint`'s new Check 11 (`_check_escalation_justified` / `escalation_reason_for`):
  1. An `opus` task with `complexity="simple"` and no architecture/adversarial signal → WARN fires,
     message mentions `model-routing.md`.
  2. An `opus` task with `complexity="hard"` and spec text containing "state machine" → no WARN
     (justified).
  3. A `reviewer`-role `opus` task → no WARN (adversarial-review justification).
  4. A `sonnet`/`codex`/`haiku` task, any complexity → never triggers this check at all (only
     opus/fable are in scope).
  5. **Regression guard:** run the full check-plan aggregation (whatever function collects all 11
     checks) against a small fixture plan that currently passes with 0 issues under the first 10
     checks plus one unjustified-opus task — assert the overall verdict is `WARN`, never `BLOCK`,
     and that the plan is NOT rejected (i.e. `/renmark:check-plan`'s existing PASS/WARN/BLOCK
     threshold behavior for this plan is unchanged from before Check 11 existed, modulo the one new
     WARN line). This is the direct proof that adding this check does not change any existing
     plan's dispatch outcome.
  6. Also test `renmark.memory.append_routing`'s new `escalation_reason` param: with it, the
     appended line contains `escalation=`; without it (existing call signature), the line is
     byte-identical to today's output — read the existing `tests/test_memory.py` (or equivalent)
     fixture for `append_routing` and extend it rather than duplicating its setup.

## Cost preview

| Executor | Count | Tokens (incl. agent overhead) | $/kT | Cost |
|---|---:|---:|---:|---:|
| opus | 1 | 1800 + 10000 = 11800 | $0.015 | $0.177 |
| sonnet | 2 | (700+900) + 2×10000 = 21600 | $0.003 | $0.0648 |
| haiku | 6 | (250+200+200+200+250) + 6×10000 = 61100 | $0.0001 | $0.00611 |
| codex | 2 | 400+900 = 1300 | ~$0.01–$0.05 | ~$0.06 est |

**Total: 10 tasks, 10 parallel groups (fully independent files — safe to run as one wave),
~95,800 tokens, ~$0.31**

## Follow-ups outside this plan (not orchestrated tasks)

1. **PRD.md REQ-30/REQ-31 amendment** — per the project's "one writer" rule
   (`plugin/skills/.shared/prd-alignment.md`), only `/renmark:prd` writes `PRD.md`. After Part 1 +
   Part 2 land, route a proposed REQ-30/REQ-31 amendment (citing the new enforcement mechanisms:
   plan_lint Check 11, `milestone_context_checkpoint`, the usage-instrumentation contract) through
   `/renmark:prd` update mode — human-gated, not a plan task.
2. **`.renmark/memory/analytics.md` regeneration** — deterministic, no LLM needed; regenerate via
   the existing `/renmark:analytics` command/tooling directly, not a build task.
3. **`/renmark:hygiene --apply`** — run (dry-run first) against the 32+ untracked
   `.renmark/{reviews,audits,reports,roadmap}/` files named in the audit's §5, using the existing
   hygiene skill — not reimplemented here.

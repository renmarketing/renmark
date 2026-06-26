---
artifact_type: plan
schema_version: 1
created_at: 2026-06-26T00:00:00Z
source_sha: e06da63
related_plan: null
generator: plan
stale_after: null
dependency_refs:
  - .renmark/specs/2026-06-26-p10-headless-contract.spec.md
---

# Plan — P10 headless / spawned-session contract

Implements the owner-locked headless contract (spec
`.renmark/specs/2026-06-26-p10-headless-contract.spec.md`, ADR-034): layered
detection in `config.py` (mirrors the P11 `is_proactive` pattern), a shared
doctrine file honored by the three centralized menu files, a dangerous-gate halt
path in `lifecycle.py` that records a human-review decision, and a `--set-headless`
CLI flag. No SKILL.md frontmatter is touched — behavior is inherited via the
shared menu files (protects the v0.20.0 trigger-only descriptions).

**Do-not-change guards honored:** detection precedence + dangerous-gate list are
owner-specified (no relaxing); P3 `skill_preamble` record-before-check ordering is
load-bearing (Task 7 must preserve it); detection never reads `CLAUDE_JOB_DIR`/`CLAUDECODE`.

---

### Task 1: headless detection helpers in config.py
- **mode:** B
- **target:** renmark/config.py
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 1
- **est_tokens:** 650
- **est_cost_usd:** 0.03
- **verifier:** `RENMARK_HEADLESS=1 python3 -c "from renmark import config; assert config.is_headless('.') is True; assert config.headless_source('.')=='env'" && RENMARK_HEADLESS=0 python3 -c "from renmark import config; assert config.is_headless('.') is False"`
- **serves:** P10
- **spec:**
  Add three public functions mirroring the existing `is_proactive`/`set_proactive`
  pattern (same module conventions: stdlib `json` only, never raise, read-modify-write
  on `.renmark/config.json`):
  - `is_headless(repo) -> bool` with precedence: env `RENMARK_HEADLESS=1` → True;
    `RENMARK_HEADLESS=0` → False (explicit OFF overrides config); else
    `.renmark/config.json` key `"headless"` (bool); else default **False**.
    Parse env case-insensitively for `1/true/yes/on` → True and `0/false/no/off` → False;
    any other env value falls through to config.
  - `set_headless(repo, value) -> None` — persist the `"headless"` key.
  - `headless_source(repo) -> str` — return `"env"`, `"config"`, or `"default"`
    describing which layer decided, for the preamble note.
  Do NOT read `CLAUDE_JOB_DIR` or `CLAUDECODE` — they are explicitly not headless signals.
  The tool-availability fallback (layer 4) is skill-side, NOT implemented here.

### Task 2: tests for headless detection
- **mode:** B
- **target:** tests/test_config.py
- **complexity:** medium
- **executor:** codex
- **parallel_group:** 2
- **est_tokens:** 800
- **est_cost_usd:** 0.02
- **verifier:** `python3 -m pytest -q tests/test_config.py`
- **serves:** P10
- **spec:**
  Add tests alongside the existing proactive tests, pinning all detection layers:
  `RENMARK_HEADLESS=1` → True; `RENMARK_HEADLESS=0` → False **even when config.json
  has `"headless": true`** (explicit OFF overrides config); config flag honored when
  env unset; default False when neither present; `headless_source` returns
  `env`/`config`/`default` correctly. Use `monkeypatch.setenv/delenv` and a tmp repo
  with `.renmark/config.json`, matching the style of the existing config tests.

### Task 3: headless-contract.md shared doctrine
- **mode:** A
- **target:** plugin/skills/_shared/headless-contract.md
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 1
- **est_tokens:** 900
- **est_cost_usd:** 0.03
- **verifier:** `test -f plugin/skills/_shared/headless-contract.md && grep -q "needs_input" plugin/skills/_shared/headless-contract.md && grep -q "RENMARK_HEADLESS" plugin/skills/_shared/headless-contract.md`
- **serves:** P10
- **spec:**
  Create the single-source doctrine file. Sections, lifted verbatim from the spec's
  "The contract" section:
  (1) **Detection precedence** — env `RENMARK_HEADLESS=1`>`=0`>`.renmark/config.json`>
  tool-availability fallback adapter (AskUserQuestion absent from the tool list →
  headless; reliable for spawned subagents, Claude Code issue #34592 closed
  "not planned"); never `CLAUDE_JOB_DIR`/`CLAUDECODE`. **Uncertainty rule:** if layers
  can't decide, treat dangerous gates as headless-safe (halt + emit). Note that
  Python (`config.is_headless`) owns env+config; the skill combines it with the
  tool-availability adapter.
  (2) **Safe vs dangerous gate table** — safe: routine next-steps, quality-gate menu,
  scope-contract Q&A, clear-default unclear-intent → auto-pick `(Recommended)`.
  Dangerous: `merge`, `release`, destructive ops, PRD approval, cost/token approval
  over budget → halt, write decision artifact, set `human_review_required=true`,
  return `needs_input` (never `failed`).
  (3) **Return schema** — the JSON object (`status` ∈ success|needs_input|failed,
  `mode`, `gate`, `decision`, `human_review_required`, `artifacts`, `reason`) + one
  classifier prose line using the repo's job words `result:`/`needs input:`/`failed:`.
  Include the 3 worked examples from the spec.
  (4) **Decision-artifact format** — `.renmark/decisions/<gate>-approval.json` with
  gate, timestamp, what needs approval, originating skill/stage.
  Keep it a contract doc (no code). This is the file the menu files reference.

### Task 4: handoff-menu.md honors the contract
- **mode:** B
- **target:** plugin/skills/_shared/handoff-menu.md
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 2
- **est_tokens:** 600
- **est_cost_usd:** 0.03
- **verifier:** `grep -q "headless-contract" plugin/skills/_shared/handoff-menu.md`
- **serves:** P10
- **spec:**
  Add a short "Headless mode" subsection that references
  `${CLAUDE_PLUGIN_ROOT}/skills/_shared/headless-contract.md` as the source of truth
  and states: when headless, do NOT render the `AskUserQuestion` picker — on a **safe**
  gate auto-pick the `(Recommended)` option and continue; on a **dangerous** gate
  (REQ-12: merge/release/destructive/PRD/over-budget) halt, write the decision
  artifact, set `human_review_required=true`, and emit the JSON+prose `needs_input`
  return. This reinforces the existing REQ-12 never-default-forward rule
  (lines ~154-169) — do not contradict it; reference it. Keep the addition tight
  (one subsection); do not rewrite the existing rules 6-9.

### Task 5: next-steps.md honors the contract
- **mode:** B
- **target:** plugin/skills/_shared/next-steps.md
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 2
- **est_tokens:** 500
- **est_cost_usd:** 0.03
- **verifier:** `grep -q "headless-contract" plugin/skills/_shared/next-steps.md`
- **serves:** P10
- **spec:**
  Add a short note referencing `headless-contract.md`: when headless, the
  state-derived next-step set is NOT presented via `AskUserQuestion`; instead the
  `(Recommended)` next command is auto-selected (safe routing) and the skill emits
  the JSON+prose return. Dangerous next-steps (e.g. a recommended merge/release)
  defer to the dangerous-gate halt rule rather than auto-running. One paragraph;
  do not restructure the existing class-1/2/3 routing.

### Task 6: scope-contract.md honors the contract
- **mode:** B
- **target:** plugin/skills/_shared/scope-contract.md
- **complexity:** simple
- **executor:** sonnet
- **parallel_group:** 2
- **est_tokens:** 400
- **est_cost_usd:** 0.03
- **verifier:** `grep -q "headless" plugin/skills/_shared/scope-contract.md`
- **serves:** P10
- **spec:**
  Add a one-paragraph note: the Q1–Q3 scope questions are a **safe** gate — in
  headless mode they are not asked interactively; the recommended/default option
  for each is auto-picked and recorded, per
  `${CLAUDE_PLUGIN_ROOT}/skills/_shared/headless-contract.md`. Do not change the
  question text or inference rules.

### Task 7: lifecycle.py — headless preamble note + dangerous-gate halt path
- **mode:** B
- **target:** renmark/lifecycle.py
- **complexity:** hard
- **executor:** opus
- **parallel_group:** 1
- **est_tokens:** 1300
- **est_cost_usd:** 0.17
- **verifier:** `python3 -m pytest -q tests/test_lifecycle.py && python3 -c "from renmark import lifecycle; assert hasattr(lifecycle,'halt_for_human_review')"`
- **serves:** P10
- **spec:**
  Two additions; **preserve the load-bearing P3 record-before-check ordering in
  `skill_preamble` — do not reorder existing logic.**
  (1) In `skill_preamble`, after the existing tiered logic, when
  `config.is_headless(repo)` is True, append a one-line hint:
  `"headless mode active (source: <env|config|default>)"` using
  `config.headless_source`. Additive only.
  (2) Add `halt_for_human_review(repo, gate, *, originating_skill, what)` that:
  writes `.renmark/decisions/<gate>-approval.json` (format per headless-contract.md —
  use the existing `summary.write_artifact` or a stdlib json dump, no new deps),
  sets `human_review_required=true` / `human_review_for=<gate>` in `lifecycle.json`
  via the existing write_lifecycle gate fields, and returns the structured dict
  `{status:"needs_input", mode:"headless", gate, decision:"halted_for_human_review",
  human_review_required:true, artifacts:[<decision-path>]}` for the skill to emit.
  Must not raise on a missing `.renmark/decisions/` dir — create it.
  Existing `tests/test_lifecycle.py` must stay green (verifier runs it).

### Task 8: tests for lifecycle headless behavior
- **mode:** B
- **target:** tests/test_lifecycle.py
- **complexity:** medium
- **executor:** codex
- **parallel_group:** 2
- **est_tokens:** 800
- **est_cost_usd:** 0.02
- **verifier:** `python3 -m pytest -q tests/test_lifecycle.py`
- **serves:** P10
- **spec:**
  Add tests: (a) with `RENMARK_HEADLESS=1`, `skill_preamble` output contains
  "headless mode active"; with headless off it does not. (b) `halt_for_human_review`
  writes `.renmark/decisions/<gate>-approval.json`, sets `human_review_required` true
  and `human_review_for` to the gate in `lifecycle.json`, and returns a dict with
  `status=="needs_input"` and `decision=="halted_for_human_review"`. Use a tmp repo;
  match existing lifecycle test style. Do not weaken existing assertions.

### Task 9: --set-headless CLI flag
- **mode:** B
- **target:** renmark/cli/_engine.py
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 2
- **est_tokens:** 450
- **est_cost_usd:** 0.03
- **verifier:** `python3 -m py_compile renmark/cli/_engine.py && grep -q "set-headless" renmark/cli/_engine.py`
- **serves:** P10
- **spec:**
  Mirror the existing `--set-proactive` wiring (argparse entry ~line 1084 and the
  handler ~line 1133): add `--set-headless true|false` that calls
  `config.set_headless(repo, value)`, validates the value the same way
  (`ap.error("--set-headless expects 'true' or 'false'")` on bad input), prints a
  confirmation, and add `--set-headless` to the "no-op / action" help string
  alongside `--set-proactive` (~line 1157). Do not alter `--set-proactive` behavior.

---

## Cost preview

Total spend = (output_tokens + 10k agent overhead for haiku/sonnet/opus) × $/kT;
codex runs as a subprocess (no overhead).

| Task | Executor | Tokens (+overhead) | Cost |
|---|---|---|---|
| 1 config.py helpers | sonnet | 650 + 10k | $0.032 |
| 2 test_config.py | codex | 800 | $0.02 |
| 3 headless-contract.md | sonnet | 900 + 10k | $0.033 |
| 4 handoff-menu.md | sonnet | 600 + 10k | $0.032 |
| 5 next-steps.md | sonnet | 500 + 10k | $0.032 |
| 6 scope-contract.md | sonnet | 400 + 10k | $0.031 |
| 7 lifecycle.py | opus | 1300 + 10k | $0.170 |
| 8 test_lifecycle.py | codex | 800 | $0.02 |
| 9 _engine.py CLI flag | sonnet | 450 + 10k | $0.031 |

**Total: ~$0.40** — 9 tasks, 2 parallel groups (wave 1: tasks 1,3,7 · wave 2: tasks 2,4,5,6,8,9).
Executors: codex×2, sonnet×6, opus×1.

# Plan — proportional-pipeline (C+A): cost ∝ feature size/risk

**Spec:** `.renmark/specs/2026-06-08-proportional-pipeline.spec.md`
**Branch:** `feature/proportional-pipeline`

New deterministic `renmark/sizing.py` classifier (the core, gates everything) →
tests + feature-router lite lane + proportional codereview, which all depend on
the classifier API. verify + plan-validation ALWAYS run regardless of tier.
Task 1 is correctness-critical (the heuristic) → opus; the rest → sonnet.

---

### Task 1: sizing classifier (deterministic, zero-LLM)
- **mode:** A
- **target:** renmark/sizing.py
- **complexity:** hard
- **executor:** opus
- **parallel_group:** 1
- **est_tokens:** 2200
- **est_cost_usd:** 0.18
- **verifier:** python3 -c "from renmark.sizing import classify_plan, classify_diff, Tier; print('ok')" && ruff check renmark/sizing.py && mypy renmark/sizing.py
- **serves:** REQ-2
- **spec:**
  Create `renmark/sizing.py` — a PURE, stdlib-only, zero-LLM classifier that maps a
  feature/diff to a tier. Read `renmark/parser.py` first (reuse `Task` fields:
  `complexity`, `mode`, `target`, `est_tokens`; the task list shape) — do NOT
  reimplement plan parsing. API:
  - `Tier` = a small enum/Literal: `"lite" | "standard" | "full"`.
  - `classify_plan(tasks: list[Task]) -> str` (returns a Tier value).
  - `classify_diff(repo, base_ref) -> str` — uses `git diff --stat <base>..HEAD`
    (or working tree) for line/file counts; stdlib `subprocess`/existing git helper.
  Signals + rules (expose thresholds as documented module constants, tunable):
  - any task `complexity == "hard"` → NEVER `lite` (≥ standard).
  - target/diff FILE TYPES: docs/config (`.md`, `.txt`, `.json`, `.toml`,
    `.gitignore`, template files) vs CODE (`.py`, etc.). A core-module edit
    (`renmark/*.py` — parser/lifecycle/dispatch/init/sizing) forces ≥ standard.
  - task count + diff line count thresholds → lite (≤3 tasks, no hard, doc/config-
    dominant OR very small code diff) / standard (moderate) / full (hard present,
    many tasks, core code, or large diff).
  - **Never raises:** on any uncertainty / unreadable signal / git failure, return
    `"standard"` (the safe middle — never accidentally `lite`).
  Add a module docstring explaining the tiers + that callers (feature router,
  codereview) share this single source of truth. Match existing code style + types.

### Task 2: sizing unit tests (tier boundaries)
- **mode:** A
- **target:** tests/test_sizing.py
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 2
- **est_tokens:** 1600
- **est_cost_usd:** 0.03
- **verifier:** python3 -m pytest tests/test_sizing.py -q
- **serves:** REQ-2
- **spec:**
  Hermetic pytest for `renmark.sizing` (sonnet per ADR-007 — new test file).
  Depends on Task 1. Read renmark/sizing.py + renmark/parser.py (build `Task`
  objects via the parser or directly) + an existing test for fixture style. Cover:
  - all-doc/config small task set (≤3, no hard) → `lite`.
  - any `hard` task → NOT `lite` (≥ standard) even if small.
  - core-module edit (e.g. target `renmark/parser.py`) → ≥ standard even if 1 task.
  - many tasks / large diff → `full`.
  - `classify_diff`: a tiny doc diff → lite-ish; a large/code diff → full (use a
    tmp git repo or monkeypatch the git-stat call — keep hermetic).
  - **degrade-to-standard:** an unreadable/empty/garbage input or git failure
    returns `"standard"`, never raises, never `"lite"`.
  Assert against the module's documented thresholds (read them; don't hardcode
  magic numbers the impl might tune — reference the constants where possible).

### Task 3: feature router — size-tier lite lane
- **mode:** B
- **target:** plugin/skills/feature/SKILL.md
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 2
- **est_tokens:** 1500
- **est_cost_usd:** 0.03
- **verifier:** grep -qi "lite lane\|--lite" plugin/skills/feature/SKILL.md && grep -qi "sizing\|classify_plan\|tier" plugin/skills/feature/SKILL.md
- **serves:** REQ-2
- **spec:**
  Read plugin/skills/feature/SKILL.md + the spec first. Add a SIZE-TIER step: after
  `plan` validates, call `renmark.sizing.classify_plan(tasks)` → tier; surface the
  tier + which stages will run + est-token band in the cost preview. Routing:
  - **lite:** skip the heavy path — orchestrate → **verify (ALWAYS)** → proportional
    codereview (cheap `/review` default + escalate; defer detail to the codereview
    skill, Task 4) → **land on `main`** (no PR / no codex / no release), per the
    single-branch-rule. Mechanism: the lane decision happens AFTER plan-validated;
    lite work lands on main (classify-before-branch, or branch then fast-forward
    main on lite finish — state the behavior, leave exact mechanics to execution).
  - **standard/full:** the existing branch → orchestrate → verify → full codex
    codereview → finish (PR/merge/release) flow, unchanged.
  - **Overrides:** `/renmark:feature <name> --full` forces full pipeline; `--lite`
    forces lite. Explicit always beats the heuristic.
  - **ALWAYS run regardless of tier:** plan validation + goal-backward verify (REQ-7).
  Keep the router's router-not-engineer contract + the single dispatch gate intact.
  Mirror any rule-affecting note to AGENTS.md/CLAUDE.md per the sync convention.

### Task 4: proportional codereview
- **mode:** B
- **target:** plugin/skills/codereview/SKILL.md
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 2
- **est_tokens:** 1500
- **est_cost_usd:** 0.03
- **verifier:** grep -qi "classify_diff\|proportional\|tier" plugin/skills/codereview/SKILL.md && grep -qi -- "--skip\|--full\|/review" plugin/skills/codereview/SKILL.md
- **serves:** REQ-2
- **spec:**
  Read plugin/skills/codereview/SKILL.md + the spec first. Make the review depth
  PROPORTIONAL to the diff via `renmark.sizing.classify_diff`:
  - **lite/doc diff → run the built-in cheap `/review` (the `code-review` skill,
    in-context, ~10–25k) by DEFAULT**, then OFFER a one-keystroke escalate to the
    full codex pass. NEVER silently skip — always state which review ran + offer escalate.
  - **standard/full diff → full codex review** (current behavior, `codex exec
    --sandbox read-only`).
  - **Flags:** add `--full` (force codex) and `--skip` (explicit skip) to the
    existing arg parser (alongside `--focus`). State the diff tier + chosen review
    before running.
  Keep the existing focus-mode prompts, the read-only sandbox, and the
  opus-reads-only-the-summary context-hygiene contract intact. Mirror any
  rule-affecting note to AGENTS.md/CLAUDE.md.

---

## Cost preview

| Task | Executor | Total tokens (incl. ~10k overhead) | Cost |
|---|---|---|---|
| 1 sizing.py classifier | opus | 12,200 | $0.183 |
| 2 sizing tests | sonnet | 11,600 | $0.0348 |
| 3 feature lite lane | sonnet | 11,500 | $0.0345 |
| 4 proportional codereview | sonnet | 11,500 | $0.0345 |

**Tasks: 4 (2 parallel groups). Executors: opus×1, sonnet×3.**
**Total tokens: ~47k. Total cost: ~$0.29**

*(Meta: once shipped, a feature this size would itself classify `standard`/`full` — it touches core `renmark/*.py` — so it would still get the full codex review. The lite lane is for the tiny features it's designed to cheapen.)*

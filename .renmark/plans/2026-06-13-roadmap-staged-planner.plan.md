---
artifact_type: plan
schema_version: 1
created_at: 2026-06-13
source_sha: b5b252e
generator: opus
related_spec: .renmark/specs/2026-06-13-roadmap-staged-planner.spec.md
dependency_refs:
  - .renmark/specs/2026-06-13-roadmap-staged-planner.spec.md
  - .renmark/research/2026-06-13-roadmap-staged-planner-reuse.research.md
status: plan-drafted
---

# Plan — roadmap-staged-planner

Decomposes `.renmark/specs/2026-06-13-roadmap-staged-planner.spec.md` into a
PRD-anchored staged program planner: a new program data model
(`program.json` + committed `program.md` checklist), a stage-to-stage driver
that wraps the existing `loop` per stage with structured-field stop conditions,
forward + `--setup` reconciliation modes on `/renmark:roadmap`, and entry-point
wiring for `start`/`feature`/`resume`. Reuse verdict (in-session, fresh):
`partial` — reuses loop/backlog/orchestrate/verify/approve/roadmap; genuinely new
= the stage/task model, the driver, `program.md`, entry-point divergence, the
per-stage digest. Routing follows `.renmark/memory/routing.md`: new
correctness-critical `renmark/*.py` state modules → opus; `tests/**` → codex;
SKILL.md contract edits → sonnet/haiku.

Waves: (1) data model → (2) driver + roadmap modes → (3) tests → (4) skill docs.

---

### Task 1: program data model
- **mode:** A
- **target:** renmark/program.py
- **complexity:** hard
- **executor:** opus
- **parallel_group:** 1
- **est_tokens:** 2600
- **est_cost_usd:** 0.19
- **verifier:** bash -c 'set -o pipefail; python3 -m py_compile renmark/program.py && python3 -c "from renmark import program; program.read_program" 2>&1 | tail -n 5'
- **serves:** REQ-9
- **spec:**
  Create `renmark/program.py` — the staged-program data model + persistence, the
  single source of truth for "where are we." This is correctness-critical state
  code (mirror the style/discipline of `renmark/loop.py` and `renmark/lifecycle.py`).
  Define:
  - A `TaskNode` and `StageNode` dataclass tree: stage has `id`, `title`,
    `serves` (REQ-n or "new"), `status` (`pending|in_progress|done|partial|needed|blocked`),
    `pipeline_phases` (e.g. ["brainstorm","plan"]), ordered `tasks`; each task has
    `id`, `title`, `status`, `retry_count` (int, monotonic), `pipeline_phases`
    (e.g. ["dispatch","qa"]), `summary` (≤5-line "what it did", optional).
    Program root has `feature`, `mode` (`feature-planner|staged|whole-product|setup`),
    `created_at`, `source_sha`, ordered `stages`, `stage_completion_sha` (map
    stage-id → sha snapshot taken when that stage starts), `current_stage_id`.
  - Canonical paths: runtime state at `.renmark/state/program.json` (gitignored);
    committed human checklist at `.renmark/roadmap/program.md`. Provide module
    constants for both.
  - `read_program(repo) -> Program | None` and `write_program(repo, program)` —
    write_program MUST persist `program.json` atomically (tmp+rename) AND
    re-render `program.md` from the same state every write (program.md is a
    rendered view, never hand-edited as truth).
  - `render_markdown(program) -> str` — deterministic checklist: stages as `##`
    headings with a status glyph, tasks as `- [x]/[ ]` checkboxes; a task's
    one-line summary shown inline when present. Carry artifact-provenance
    frontmatter (`artifact_type: program`, `schema_version: 1`, `created_at`,
    `source_sha`). NO LLM — pure string render.
  - `position(program) -> str` — the ONLY orchestrator-visible accessor: a single
    bounded line like `"Stage 2/5 · task 3/4 done · current: <stage title>"`.
  - Deterministic mutators: `mark_task(program, stage_id, task_id, status, summary=None)`,
    `mark_stage(...)`, `bump_retry(...)`, `snapshot_stage_sha(program, stage_id, sha)`.
    Each mutator returns the updated program; callers persist via `write_program`.
  - `stage_digest(program, stage_id) -> str` — bounded ≤5-line rollup of that
    stage's task summaries for the per-stage digest.
  Follow project conventions in `.renmark/memory/conventions.md`. Keep all I/O
  inside the repo (CLAUDE.md "writes stay in project"). No network, no LLM calls.

### Task 2: program driver (stage state machine)
- **mode:** A
- **target:** renmark/program_driver.py
- **complexity:** hard
- **executor:** opus
- **parallel_group:** 2
- **est_tokens:** 2400
- **est_cost_usd:** 0.18
- **verifier:** bash -c 'set -o pipefail; python3 -m py_compile renmark/program_driver.py && python3 -c "from renmark import program_driver" 2>&1 | tail -n 5'
- **serves:** REQ-10
- **spec:**
  Create `renmark/program_driver.py` — the deterministic stage-sequencing state
  machine that sits ABOVE the single-item `loop` (analogous to how `loop.py`
  holds budget/decide logic while the SKILL dispatches). It owns transitions,
  stop-condition evaluation, and resumable persistence; it does NOT itself call
  LLMs or read generated code. Import the model from `renmark.program`.
  Implement:
  - `next_stage(program) -> StageNode | None` — the next `pending`/`needed` stage
    in order (skips `done`; resumes `in_progress`).
  - `StopReason` enum + `evaluate_stop(stage_result) -> StopReason | None` —
    decides whether to surface-and-stop, reading ONLY structured fields (never
    LLM-interpreted "looks done"): `verify_failed` (verify
    `completion_state != complete` OR `validation_status != validated`),
    `plan_block` (check-plan BLOCK), `codereview_critical`, `retry_exhausted`
    (`retry_count >= 3` — circuit-break, treat as BLOCKER not transient),
    `prd_drift` (ALIGN verdict == drift). Budget/max-iter/usage-limit map to a
    distinct `paused` disposition (resumable, NO approval needed) — NOT a stop.
    REQ-12 gates (merge/release/destructive) map to `awaiting_approval`.
  - `advance_on_success(program, stage_id, repo)` — mark stage done, snapshot
    next stage's `stage_completion_sha` (current git sha) before it runs, persist
    via `program.write_program` BEFORE returning (Temporal write-state-before-return).
  - `drift_warning(program, stage_id, current_sha) -> str | None` — warn when the
    snapshot sha differs from current (plan-time drift guard).
  - A bounded `driver_status(program) -> str` (≤5 lines) the orchestrator reads to
    decide the next dispatch. No work happens here that needs generated-code
    context — the SKILL layer dispatches orchestrate/verify per stage and feeds
    back only structured results.
  Match `renmark/loop.py` conventions for status enums + persistence discipline.

### Task 3: roadmap forward + --setup modes + render
- **mode:** B
- **target:** renmark/roadmap.py
- **complexity:** hard
- **executor:** opus
- **parallel_group:** 2
- **est_tokens:** 1900
- **est_cost_usd:** 0.18
- **verifier:** bash -c 'set -o pipefail; python3 -m py_compile renmark/roadmap.py && python3 -c "from renmark import roadmap; roadmap.render_program_table" 2>&1 | tail -n 5'
- **serves:** REQ-9
- **spec:**
  Edit `renmark/roadmap.py` (keep the existing retrospective table + `--gaps`
  paths intact — do NOT remove or regress them; see CHANGELOG "Do not change").
  Add, importing from `renmark.program`:
  - `render_program_table(repo) -> str` — zero-LLM renderer of an in-flight
    program's position from `program.json`/`program.md`: stages → tasks with
    status (`done|partial|needed|pending`), the bounded `position()` line, and a
    "where work is needed" section listing `needed`/`partial` stages. Returns a
    clear "no in-flight program" string when none exists.
  - `reconcile_setup(repo, built_signal) -> Program` — the deterministic half of
    `--setup` brownfield reconciliation: given a freshly-derived program and a
    `built_signal` dict (the LLM-derived "what is built" map passed in by the
    SKILL's bounded subagent — this function does NOT itself read code or the PRD),
    set each stage/task status to `done|partial|needed` by matching `serves: REQ-n`
    and built-component evidence. Pure mapping logic over inputs; persists via
    `program.write_program`.
  - A `program_map_is_stale(repo) -> bool` helper that checks
    `.renmark/memory/project-map.md` freshness (mirror `renmark/blueprint.py`'s
    map-freshness guard) so the SKILL can halt `--setup` to `/renmark:init`.
  Do NOT pull the PRD body or source code into this module — it operates on
  structured inputs handed in by the SKILL's bounded subagents (REQ-5/G11).

### Task 4: tests — program data model
- **mode:** A
- **target:** tests/test_program.py
- **complexity:** medium
- **executor:** codex
- **parallel_group:** 3
- **est_tokens:** 1000
- **est_cost_usd:** 0.02
- **verifier:** bash -c 'set -o pipefail; python3 -m pytest tests/test_program.py -q 2>&1 | tail -n 5'
- **serves:** new
- **spec:**
  Pytest for `renmark/program.py`. Cover: round-trip `write_program`/`read_program`
  (program.json atomic write + program.md re-rendered every write); `position()`
  returns the bounded one-line form; `render_markdown` produces ticked checkboxes
  matching status and inlines task summaries; mutators (`mark_task`, `mark_stage`,
  `bump_retry` monotonic, `snapshot_stage_sha`) update state correctly;
  `stage_digest` is ≤5 lines; `read_program` returns None when no program file
  exists. Use a tmp_path repo fixture; assert program.json lands under
  `.renmark/state/` and program.md under `.renmark/roadmap/`.

### Task 5: tests — program driver
- **mode:** A
- **target:** tests/test_program_driver.py
- **complexity:** medium
- **executor:** codex
- **parallel_group:** 3
- **est_tokens:** 1100
- **est_cost_usd:** 0.02
- **verifier:** bash -c 'set -o pipefail; python3 -m pytest tests/test_program_driver.py -q 2>&1 | tail -n 5'
- **serves:** new
- **spec:**
  Pytest for `renmark/program_driver.py`. Cover: `next_stage` ordering (skips
  done, resumes in_progress, returns None when all done); `evaluate_stop` maps
  each structured signal to the right `StopReason` — verify_failed when
  completion_state!=complete OR validation_status!=validated, plan_block,
  codereview_critical, retry_exhausted at retry_count>=3, prd_drift; budget/usage
  → `paused` (not a stop); REQ-12 → `awaiting_approval`; `advance_on_success`
  marks done + snapshots next sha + persists before returning;
  `drift_warning` fires on sha mismatch and is silent on match. Build Program
  fixtures via `renmark.program` constructors.

### Task 6: tests — roadmap staged modes
- **mode:** A
- **target:** tests/test_roadmap_staged.py
- **complexity:** medium
- **executor:** codex
- **parallel_group:** 3
- **est_tokens:** 1000
- **est_cost_usd:** 0.02
- **verifier:** bash -c 'set -o pipefail; python3 -m pytest tests/test_roadmap_staged.py -q 2>&1 | tail -n 5'
- **serves:** new
- **spec:**
  Pytest for the new `renmark/roadmap.py` functions ONLY (do not touch existing
  roadmap tests). Cover: `render_program_table` renders stages/tasks with statuses
  + a "where work is needed" section, and returns the no-program string when
  absent; `reconcile_setup` maps a built_signal dict onto stage/task statuses
  (`done|partial|needed`) by `serves: REQ-n` matching and persists;
  `program_map_is_stale` returns True when project-map.md is missing/old and False
  when fresh. Assert the existing retrospective table path is untouched (import it,
  call it on a fixture, expect no exception).

### Task 7: roadmap SKILL — forward plan, --setup, render
- **mode:** B
- **target:** plugin/skills/roadmap/SKILL.md
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 4
- **est_tokens:** 1900
- **est_cost_usd:** 0.04
- **verifier:** grep -q 'whole-product' plugin/skills/roadmap/SKILL.md && grep -q -- '--setup' plugin/skills/roadmap/SKILL.md && grep -q 'program.json' plugin/skills/roadmap/SKILL.md
- **serves:** REQ-9
- **spec:**
  Edit `plugin/skills/roadmap/SKILL.md` to document the new forward modes WITHOUT
  removing the existing retrospective-table / `--gaps` behavior. Add:
  (1) **forward plan mode** (PRD present): a bounded subagent reads PRD.md in its
  own context and derives an ordered stage→task sequence (orchestrator NEVER sees
  the PRD body — cite REQ-5/G11); the deterministic emission uses
  `renmark.program.write_program`. One human approval gate (REQ-18) before any
  execution. (2) **`--setup` brownfield reconciliation**: derive the program from
  the PRD, THEN a bounded subagent produces a "what is built" signal from
  `.renmark/memory/project-map.md` + git history + existing `--gaps` ALIGN logic;
  pass that to `renmark.roadmap.reconcile_setup`; halt to `/renmark:init` when
  `program_map_is_stale`; then print the position via `render_program_table`,
  highlighting where work is needed. (3) **render**: `/renmark:roadmap` with an
  in-flight program shows `render_program_table` output. Keep the orchestrator
  output bounded (≤5 lines position, G3). Mirror citation style of neighboring
  SKILLs; do not paste shared-contract bodies — reference by path. Cap added
  length so the file stays well under the modularity budget.

### Task 8: resume SKILL — surface in-flight program
- **mode:** B
- **target:** plugin/skills/resume/SKILL.md
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 4
- **est_tokens:** 700
- **est_cost_usd:** 0.00
- **verifier:** grep -q 'program' plugin/skills/resume/SKILL.md && grep -q 'read_program' plugin/skills/resume/SKILL.md
- **serves:** REQ-10
- **spec:**
  Add a new step to `plugin/skills/resume/SKILL.md` (mirror the existing
  "Surface any in-flight loop" step 1.75 style) that surfaces an in-flight staged
  program: call `renmark.program.read_program`; if a program exists and is not
  fully done, print a bounded block — the `position()` line, current stage, and
  `Resume: /renmark:roadmap` (or `/renmark:approve` if awaiting an approval gate).
  Zero LLM calls, pure file IO, ≤5 lines output. Do not alter the existing
  lifecycle/loop/pause surfacing steps.

### Task 9: start SKILL — feature-planner entry
- **mode:** B
- **target:** plugin/skills/start/SKILL.md
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 4
- **est_tokens:** 1000
- **est_cost_usd:** 0.03
- **verifier:** grep -q 'feature-planner' plugin/skills/start/SKILL.md && grep -q 'program' plugin/skills/start/SKILL.md
- **serves:** REQ-9
- **spec:**
  Edit `plugin/skills/start/SKILL.md` to add the **feature-planner** entry mode:
  when the user wants to plan a whole program from scratch (greenfield), start can
  route into the staged planner — brainstorm the program, then emit a
  `renmark.program` via the roadmap forward planner — instead of (or after) the
  existing single-feature routing. Keep it additive: the existing adaptive
  one-question routing stays the default; the feature-planner path is an offered
  branch. Reference the roadmap SKILL's forward mode rather than duplicating it.
  Keep within the existing structure and length budget.

### Task 10: feature SKILL — staged mode handoff
- **mode:** B
- **target:** plugin/skills/feature/SKILL.md
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 4
- **est_tokens:** 1200
- **est_cost_usd:** 0.03
- **verifier:** grep -q 'staged' plugin/skills/feature/SKILL.md && grep -q 'program' plugin/skills/feature/SKILL.md
- **serves:** REQ-10
- **spec:**
  Edit `plugin/skills/feature/SKILL.md` to add the **staged** mode: when a feature
  is large enough to warrant multiple stages, feature can decompose it into a
  `renmark.program` of stages and drive them via the program driver (reusing the
  existing per-stage plan→orchestrate→verify pipeline), instead of a single
  pass. Preserve the existing single-feature full-pipeline flow as the default;
  staged is an offered branch for multi-stage features. Honor the single dispatch
  gate (feature owns it — do not introduce a second gate) and REQ-12 hard gates.
  Reference the program driver + roadmap forward mode by path; do not duplicate
  their contracts.

---

## Cost preview

| Task | Target | Executor | est_tokens (+overhead) | est_cost |
|---|---|---|---|---|
| 1 | renmark/program.py | opus | 2600 (+10k) | $0.19 |
| 2 | renmark/program_driver.py | opus | 2400 (+10k) | $0.18 |
| 3 | renmark/roadmap.py | opus | 1900 (+10k) | $0.18 |
| 4 | tests/test_program.py | codex | 1000 | $0.02 |
| 5 | tests/test_program_driver.py | codex | 1100 | $0.02 |
| 6 | tests/test_roadmap_staged.py | codex | 1000 | $0.02 |
| 7 | plugin/skills/roadmap/SKILL.md | sonnet | 1900 (+10k) | $0.04 |
| 8 | plugin/skills/resume/SKILL.md | haiku | 700 (+10k) | $0.00 |
| 9 | plugin/skills/start/SKILL.md | sonnet | 1000 (+10k) | $0.03 |
| 10 | plugin/skills/feature/SKILL.md | sonnet | 1200 (+10k) | $0.03 |

**Total (incl. ~10k Agent overhead/task): ~$0.71**
Executors: haiku×1, codex×3, sonnet×3, opus×3. Waves: 4. Tasks: 10.

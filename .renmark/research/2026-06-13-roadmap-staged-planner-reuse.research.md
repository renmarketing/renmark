---
artifact_type: research
schema_version: 1
created_at: 2026-06-14T01:50:35+00:00
source_sha: null
related_plan: null
generator: brainstorm-reuse-check
stale_after: null
dependency_refs: []
completion_state: complete
confidence: medium
validation_status: unvalidated
retry_count: 0
parser_success: true
schema_compliance: true
---

## Perspectives

### Perspective 1: What the feature wants (requirements analysis)
The staged program planner needs:
1. A STAGE+TASK data model — stages containing tasks, each annotated with pipeline phases
2. A single-approval entry point that produces the staged plan before execution begins
3. An autonomous stage-to-stage driver: loop each stage through existing pipeline, proceed on success, stop on failure
4. A living progress artifact (.renmark/state/program.md) ticked as each stage/task completes
5. Per-task completion summaries surfaced to the user during execution
6. Entry-point divergence: from /renmark:start → "feature planner" mode; from /renmark:feature → "staged" breakdown
7. Budget/max-iter/usage-limit surface-and-pause (resumable)
8. REQ-12 hard-gates (merge/release/destructive)

### Perspective 2: What already exists (reuse inventory)

**loop.py + /renmark:loop (SHIPPED — loop-mode MVP, 2026-06-09)**
- Provides: single upfront approval gate → autonomous orchestrate→verify→decide loop → commit-per-iteration → terminal status (done/budget-hit/max-iter/awaiting-approval/stalled).
- Budget + max-iter + usage-limit preflights (REQ-9/15/16) — all implemented.
- Resumable via loop.json + /renmark:resume (REQ-10).
- Context-hygienic: reads only verify metadata + spend ledger + bounded summaries (REQ-5/11).
- REQ-12 gating: never merges/releases/escalates budget without approval.
- PER-TASK PROGRESS: emits ONE bounded line per iteration already ("iter 2/5 · verify FAIL · spent 80k/300k...").
- WHAT IT DOES NOT DO: iterate over multiple stages; it operates on a single goal/plan; no stage-level data model; no program.md; no per-stage digest.

**/renmark:backlog (SHIPPED — backlog-driven-loop-execution, 2026-06-09)**
- Provides: single human approval gate → bounded Loop Mode on a managed branch (hardcoded max 5 iter) → branch lifecycle (no orphan branches) → human merge gate.
- Approve-once-then-build pattern: the user approves an item and the loop executes to terminal state.
- WHAT IT DOES NOT DO: multi-stage decomposition; stage-to-stage progression; staged roadmap model; program.md progress artifact.

**/renmark:roadmap (SHIPPED — with --gaps in next-step-engine, 2026-06-08)**
- Provides: per-task status table (task | llm | status | tokens | $ | commit) from usage.jsonl + git log; --gaps gap discovery (PRD-vs-shipped, T0/T1/T2).
- ALREADY renders a position/status table.
- WHAT IT DOES NOT DO: STAGE-level rows (only task rows); no stage grouping; no "current position in program" marker; table is read-only synthesis, not a live checklist.

**/renmark:feature (SHIPPED — proportional-pipeline, 2026-06-08)**
- Provides: branch isolation + plan→check-plan→orchestrate→verify→finish for ONE feature. Lite/standard/full lane classification.
- Dispatches the /renmark:orchestrate stage per-wave, then /renmark:verify.
- WHAT IT DOES NOT DO: multi-stage programs; does not drive multiple independent stages autonomously; no stage-level brainstorm/plan attached to a stage node.

**/renmark:orchestrate (SHIPPED)**
- Provides: wave-based task dispatch with G11 isolation, per-wave summaries to .renmark/state/wave-summaries/, commit per passing task.
- Wave summaries (.renmark/state/wave-summaries/wave-N.json) already carry SubagentOutput with summary_lines ≤ 5 — this IS the per-task completion summary source.
- WHAT IT DOES NOT DO: stage grouping above the wave level; no program-level state.

**/renmark:verify + /renmark:approve (SHIPPED)**
- REQ-12 gate: approve is the sole grant surface for human_review_required.
- Verify does goal-backward smoke + .verification.md metadata.

**lifecycle.py / lifecycle.json (SHIPPED)**
- Canonical stage order: init → brainstorm-complete → plan-drafted → plan-validated → created → verified → reviewed → documented → ready-to-release → released.
- WHAT IT DOES NOT DO: STAGE-within-a-PROGRAM model; lifecycle is per-feature, not per-stage.

### Perspective 3: What is genuinely new

**A) The staged program data model.**
No existing artifact represents a PROGRAM (an ordered list of STAGEs, each a list of TASKs, each annotated with pipeline phases). loop.json, lifecycle.json, and pipeline.json all operate at the single-feature/single-plan level. A program.json (or program.md) that encodes the multi-stage structure, tracks per-stage status (pending/running/done/blocked), and links to each stage's plan artifact — this does not exist.

**B) The stage-to-stage autonomous driver.**
The staged program needs a coordinator that, after each stage completes (loop terminal status = done), begins the NEXT stage — running /renmark:brainstorm (for that stage's scope), /renmark:plan, /renmark:orchestrate, /renmark:verify — without human prompting between stages (only stopping on issue). This multi-stage orchestration loop is NOT loop.py (which drives a single goal) and NOT backlog (which drives a single item). It is a new coordinator layer above them.

**C) The program.md living checklist.**
An on-disk artifact under .renmark/state/program.md that is updated (ticked) after each stage/task completion, and renderable by /renmark:roadmap to show the current position. Currently roadmap reads usage.jsonl + git log; a program.md would be a NEW source of truth for stage-level progress.

**D) Entry-point divergence logic.**
from /renmark:start → "feature planner" output (a breakdown of the current feature into stages with pipeline phases annotated). from /renmark:feature → "staged" execution breakdown. This branching is not in any current skill: start routes users into brainstorm or loop but has no staged decomposition; feature is a single-pipeline router. The entry-point dispatch is new wiring.

**E) Stage-level brainstorm+plan attachment.**
The request asks that each STAGE gets its own brainstorm and plan phase. Currently /renmark:brainstorm and /renmark:plan are feature-level (one per feature). Attaching them to each stage node (within the same overall feature/program run) is new composition — the skills exist, but wiring them to run per-stage inside a program loop is new orchestration.

**F) Per-stage digest surfacing.**
Beyond the per-task summary (which wave-summaries already produce), the user wants a per-stage digest — a human-readable rollup when a stage completes. This does not exist; loop.py produces a terminal status + bounded verdict at the end of the whole run, not a staged rollup.

### Perspective 4: Assumptions and edge cases

ASSUMPTION: "single-approval" means one human approval for the whole program roadmap before autonomous execution starts — not one per stage. If false, the autonomy value collapses and this becomes /renmark:backlog run N times.

ASSUMPTION: the stage-level brainstorm is lightweight (not a full /renmark:brainstorm interview) — the program roadmap itself IS the scope for each stage; brainstorm is for stage-level decomposition/detail, not goal discovery.

EDGE CASE: how does the staged driver handle a stage that ends with awaiting-approval (budget hit or usage-limit) without a failed verify? The loop stops but the stage is not "done". The driver must distinguish stage-done vs stage-paused vs stage-blocked.

EDGE CASE: single-writer / single-loop-per-working-tree (backlog.SKILL.md and loop.SKILL.md both enforce "one code-writing loop per working tree"). A staged program runs stages SEQUENTIALLY — this constraint is respected as long as only one stage loop is active at a time. The driver must serialize, not parallelize stages.

EDGE CASE: entry-point divergence (start vs feature) — "feature planner" mode should not write to the feature branch in planning mode; it should produce the staged breakdown as an artifact only, for the user to review before execution is approved.

EDGE CASE: roadmap position rendering — /renmark:roadmap currently synthesizes from usage.jsonl + git log (task-level, flat). To render a stage-grouped view, roadmap needs either (a) to read program.md as a new data source or (b) to receive stage annotations in usage.jsonl. Option (a) is cleaner and avoids polluting the flat log.

### Perspective 5: Deferred vs blocking

The reuse question asks what is a thin wrapper vs a real build. The honest answer: this is a REAL BUILD, not a thin wrapper. The STAGE+TASK data model, the multi-stage driver, and the program.md checklist are each load-bearing additions that require:
- A new Python module (e.g. renmark/program.py) with ProgramState, StageState, program.json/.md serialization.
- A new skill (or heavily extended /renmark:roadmap --staged) driving the stage-to-stage loop.
- Changes to /renmark:roadmap to read program.md as a data source.
- Changes to /renmark:start and /renmark:feature for entry-point divergence.

What IS thin-wrapper territory: the stop conditions (reuse loop.py stop_reason + REQ-12 gates), budget/max-iter preflights (reuse loop.parse_budget + loop.should_continue_budget), per-task summaries (reuse wave-summaries), and REQ-12 gating (reuse /renmark:approve). These are approximately 40% of the total surface area.

---

## Findings

### Reusable (shipped, name the skill + function served here)

| Skill / Module | What it covers for this feature |
|---|---|
| **loop.py + /renmark:loop** | Autonomous orchestrate→verify→decide engine for each stage; budget/max-iter/usage-limit preflights; REQ-9/10/11/12/15/16 compliance; per-iteration progress line |
| **/renmark:backlog** | Single-approval-before-build pattern; branch lifecycle; REQ-12 merge gate; "one loop per working tree" serialization guard |
| **/renmark:roadmap** | Per-task status table (extend to stage-grouped view); --gaps gap discovery; memory/roadmap.md snapshot target |
| **/renmark:orchestrate** | Wave-based task dispatch, wave-summaries (SubagentOutput.summary_lines) as per-task summary source |
| **/renmark:verify + /renmark:approve** | Goal-backward smoke + .verification.md; REQ-12 gate at every stage |
| **lifecycle.py** | Stage transitions, next_steps, human gate bits |
| **/renmark:feature** | Single-feature pipeline (stages reuse this per-stage; feature is the per-stage execution unit in the program) |
| **/renmark:brainstorm + /renmark:plan** | Stage-level brainstorm (scope per stage) + plan (task decomposition per stage) — skills exist, need new wiring |

### Genuinely New (not covered by any shipped skill)

| What | Why it is new |
|---|---|
| **STAGE+TASK data model + program.json/program.md** | No shipped artifact/module represents a multi-stage program; loop.json/lifecycle.json/pipeline.json all operate at single-feature granularity |
| **Stage-to-stage autonomous driver** | A coordinator that sequences stages (brainstorm→plan→loop→verify per stage) without per-stage human prompting — above loop.py (single goal) and backlog (single item) |
| **program.md living checklist** | New on-disk progress artifact ticked per stage/task; roadmap needs a new data-source read to render it |
| **Entry-point divergence (start vs feature)** | start → "feature planner" output; feature → "staged" breakdown; neither entry point currently produces a staged decomposition |
| **Per-stage digest** | Stage-completion rollup for the user; loop.py emits terminal verdict for the whole run, not per-stage summaries |
| **Stage-level brainstorm/plan wiring** | Skills exist but are feature-level; running them per-stage inside a program loop is new orchestration |

---

## Recommendations

1. **This is a real build — scope it as a new renmark/program.py module + a new /renmark:program skill** (or /renmark:roadmap --staged with a new execution mode). A thin extension to roadmap would not contain the data model.
2. **Leverage loop.py directly** — each stage runs as a bounded loop (one loop.json per stage, sequential). The stage driver calls loop.py stop logic, budget preflights, and usage-pause checks rather than reimplementing them.
3. **Reuse backlog's approval pattern** — the single-approval-then-execute flow is already the backlog contract; adopt it (approve the staged plan once → drive stages serially).
4. **program.md as a new roadmap data source** — have /renmark:roadmap read program.md when present and render a stage-grouped table alongside the flat task table. This keeps roadmap as the display surface.
5. **Entry-point divergence is a routing change in /renmark:start and /renmark:feature** — add a "--staged" flag or detect multi-feature scope in the plan; route to the new program skill.
6. **Serialize stages** — enforce the single-loop-per-working-tree constraint; the driver runs one stage at a time and writes stage status to program.json before moving to the next.

---

## Missing context

- The PRD has no explicit coverage of "roadmap-as-staged-program" vs the already-deferred "roadmap-batch execution (B)" — the brief says PRD alignment is aligned, but the overlap with the deferred B item should be revisited in brainstorm (they are related, not identical, but the driver is adjacent).
- Unclear whether "stage-level brainstorm" is a full /renmark:brainstorm interview or a lightweight scope-derivation from the program plan — this affects the implementation complexity significantly.

## Summary

- reuse: partial — loop.py + backlog + orchestrate + roadmap cover ~40% of the surface (execution engine, approval pattern, per-task summaries, status table)
- new: STAGE+TASK data model (program.json/md), stage-to-stage driver, program.md checklist, entry-point divergence (start vs feature), per-stage digest
- verdict: real build — renmark/program.py new module + new skill needed; thin wrapper is not sufficient
- key leverage: loop.py stop logic / budget preflights reuse per-stage; wave-summaries are the per-task summary source; backlog approval pattern for single-approval-gate
- blocker: deferred 'roadmap-batch (B)' item in features.md is adjacent — brainstorm must reconcile before spec is locked

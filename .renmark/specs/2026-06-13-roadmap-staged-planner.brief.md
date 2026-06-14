---
artifact_type: feature-brief
schema_version: 1
created_at: 2026-06-13
source_sha: 98c2d09
generator: feature-router
related_plan: null
status: pre-brainstorm
---

# Feature brief — roadmap-staged-planner

> Pre-brainstorm intent capture (written by `/renmark:feature` before a `/clear`).
> The brainstorm that follows should treat this as the starting point and produce
> the real spec at `.renmark/specs/2026-06-13-roadmap-staged-planner.spec.md`.
> Branch: `feature/roadmap-staged-planner`.

## User's request (verbatim)

Original `/renmark:feature` arg:
> "enhance the roadmap feature to literaly create a list of stages breat down
> tasks and each have brainstorming, plan, dispatch, qa to each, provide research
> and suggest how to improve this and in which pipelines and or wich other skill
> can it use to enhance"

Clarifying answer (verbatim):
> "if evoked from start should be feature planner, if evoked from feature then
> staged, what I want is to work with loop and backlog so it [can] if approved
> then just run the roadmap with minimal feedback or human approval since the
> roadmap will be approved unless an issue arises"

## Parsed intent

Enhance `/renmark:roadmap` into a **staged program planner that drives autonomous
execution**:

1. **Planning** — produce a list of **stages**, each broken into **tasks**, where
   each stage/task is annotated with the **pipeline phases** it needs:
   brainstorm → plan → dispatch (orchestrate) → qa (verify).
2. **Autonomous execution** — once the human approves the staged roadmap ONCE,
   roadmap drives each stage through the existing pipeline via **Loop Mode +
   backlog** with **minimal human feedback**: proceed stage-to-stage
   automatically **unless an issue arises** (failed verify, a blocker, or a
   human-gate like merge/release).
3. **Entry-point-aware behavior**:
   - invoked from `/renmark:start` → behaves as a **"feature planner"**.
   - invoked from `/renmark:feature` → produces the **"staged"** breakdown.
4. **Composition, not new autonomy** — it wires together existing skills:
   `brainstorm`, `plan`, `orchestrate`, `verify`, `loop`, `backlog`, `approve`.
5. The user also asked for **research + recommendations**: how to improve this,
   and which pipelines / other skills it should leverage.

## PRD alignment (done in router, 2026-06-13)

**Verdict: `aligned`** (haiku ALIGN subagent). Rationale: this composes the
already-shipped bounded Loop Mode + backlog (REQ-9/10/11/13/18) within their
stated limits — one upfront approval, bounded loop (budget + max-iterations),
stop-on-issue. It does NOT introduce the PRD's *deferred* "indefinite autonomous
loops" or "autonomous scheduled/PR-triggered execution." No PRD change required.

## Open questions for brainstorm to resolve

- **Granularity**: do brainstorm/plan/dispatch/qa attach to each STAGE, each TASK,
  or both? (User wrote "each" ambiguously.)
- **Human gates inside autonomy**: which gates MUST remain per stage? REQ-12 keeps
  merge/release/budget-escalation/destructive human-gated; REQ-18 keeps
  `/renmark:approve` the sole grant surface. "Minimal approval" ≠ no approval —
  define exactly where it stops for the human vs proceeds.
- **"Issue arises" detection**: what concretely pauses the program? (failed
  verify, plan BLOCK, loop budget/max-iter hit, usage-limit pause, codereview
  Critical, ...). Map each to surface-and-stop vs auto-continue.
- **Single-writer constraint**: PRD's "only one code-writing loop per working
  tree" — how does a multi-stage program serialize? (one stage's loop at a time).
- **Reuse vs new**: how much is roadmap ALREADY able to do via `--gaps` + loop +
  backlog? What is genuinely NEW vs an orchestration wrapper? (run the reuse check).
- **Entry-point divergence**: how should start-mode ("feature planner") vs
  feature-mode ("staged") actually differ in output/behavior?
- **State**: where does the program/stage plan persist? (`.renmark/state/` —
  resumable across `/clear`, per REQ-3/10).
- **Research deliverable**: the user wants explicit recommendations on which
  pipelines/skills to leverage and how to improve — brainstorm's Step 3 research +
  Step 4 approaches should produce this.

## Resume instructions (post-/clear)

Run `/renmark:resume` (reads lifecycle.json → recommends brainstorm), or directly
`/renmark:brainstorm` — and point brainstorm at THIS brief
(`.renmark/specs/2026-06-13-roadmap-staged-planner.brief.md`) as the starting
intent. Feature identity is already persisted; PRD alignment already passed.

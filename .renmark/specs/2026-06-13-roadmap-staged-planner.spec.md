---
artifact_type: spec
schema_version: 1
created_at: 2026-06-13
source_sha: b5b252e
generator: brainstorm
related_plan: null
dependency_refs:
  - .renmark/specs/2026-06-13-roadmap-staged-planner.brief.md
  - .renmark/research/2026-06-13-roadmap-staged-planner-reuse.research.md
  - .renmark/research/2026-06-13-roadmap-staged-planner-bestpractice.research.md
status: brainstorm-complete
---

# Spec — roadmap-staged-planner

## Context

renmark today has all the pieces to build software in stages but no surface that
**turns intent into a sequenced, self-driving program**. `/renmark:roadmap` is
retrospective (status table from git + usage) with a one-gap `--gaps` advisory;
`/renmark:prd` writes a human-owned PRD as mostly-prose with flat `REQ-n` ids that
nothing ingests to generate ordered work; `prd-alignment` is reactive-only (it
checks an *already-proposed* feature for drift). There is **no forward pipeline**
of `PRD → ordered stages → execute`.

This feature adds that pipeline. The owner's governing principle: **spend the
effort up front (PRD + roadmap), then do not deviate** — once the staged roadmap
is approved, execution runs stage-to-stage with minimal feedback, pausing only
when something genuinely goes wrong or a hard gate is reached.

It is **composition, not new autonomy**: it wires together already-shipped
skills (`brainstorm`, `plan`, `orchestrate`, `verify`, `loop`, `backlog`,
`approve`, `roadmap`) and stays inside the PRD's bounded-loop limits
(REQ-9/10/11/12/13/18) — one upfront approval, bounded loop, stop-on-issue. It
does **not** introduce indefinite autonomous loops or scheduled/PR-triggered
execution (those remain PRD-deferred).

## Goals

1. **Staged program planner** — produce an ordered list of **stages**, each
   broken into **tasks**, persisted as machine state (`program.json`) + a human
   checklist (`program.md`). Granularity is **hybrid**: each *stage* carries
   brainstorm + plan; each *task* carries dispatch (orchestrate) + qa (verify).
2. **PRD-anchored** — when a `PRD.md` exists, the planner derives the stage
   sequence **from the PRD as-is** (in a bounded subagent — orchestrator never
   sees the PRD body). Each stage records `serves: REQ-n`. The existing ALIGN
   subagent runs at **each stage boundary** as the anti-drift gate.
3. **Semi-autonomous driver** — after one human approval of the staged roadmap,
   drive each stage through the existing pipeline (via `loop`), proceeding
   stage-to-stage on success, stopping only on a defined "issue."
4. **Live progress** — `program.md` is a living checklist, ticked by
   deterministic code as each stage/task completes; `/renmark:roadmap` renders
   it; the orchestrator reads only a bounded position line.
5. **Per-task summaries** — surface each finished task's ≤5-line "what it did"
   summary live, plus a consolidated digest at each stage boundary.
6. **Entry-point aware** — three entry points converge on one program model +
   driver (see Components).
7. **Resumable** — survives `/clear`; `/renmark:resume` surfaces an in-flight
   program.

## Non-goals (feature-scoped)

- No change to `/renmark:prd` or the PRD schema — the planner consumes the PRD
  as-is. (Structured/ordered-requirements PRD is a separate, human-gated
  enhancement, explicitly deferred.)
- No new autonomy beyond the bounded loop — no indefinite loops, no
  scheduled/PR-triggered runs, no auto-merge/-release/-PR (REQ-12 stands).
- No multi-tree parallelism — one code-writing stage loop at a time
  (single-writer per working tree, per PRD).
- Product-level direction stays in `PRD.md` (referenced, not copied here).

## Architecture

A thin **program driver** layered above the existing single-item `loop` and
`backlog`. The driver owns sequencing and progress; each *stage* is executed by
the existing pipeline, so almost all build work is reused, not rebuilt.

```
PRD.md ──(bounded subagent: derive ordered stages)──► program.json + program.md
                                                              │
                                              one human approval gate (REQ-18)
                                                              │
                              ┌───────────── program driver (NEW) ─────────────┐
                              │  for each stage in program.json:               │
                              │    1. ALIGN gate: stage serves REQ-n? drift?   │  ── drift ⇒ stop
                              │    2. stage brainstorm + plan (existing)       │
                              │    3. check-plan (existing)  ── BLOCK ⇒ stop   │
                              │    4. loop → orchestrate→verify→decide tasks   │  ── verify/QA fail ⇒ stop
                              │       · tick program.md per task (deterministic)│
                              │       · emit live per-task summary             │
                              │       · codereview ── Critical ⇒ stop          │
                              │       · retry_count ≥ 3 ⇒ circuit-break, stop  │
                              │    5. snapshot stage_completion_sha            │
                              │    6. emit stage digest; write program.json    │
                              └────────────────────────────────────────────────┘
                                                              │
                                         /renmark:roadmap renders program.md
                                         REQ-12 hard gates (merge/release) → /renmark:approve
```

### Stop conditions (the "issue arose" set)

All read from **structured artifact fields**, never LLM-interpreted success
(per best-practice research). Each is **surface-and-stop**, resumable:

| Trigger | Source signal | Disposition |
|---|---|---|
| Failed verify / QA | verify `completion_state` / `validation_status` | stop for human |
| Plan BLOCK | `check-plan` verdict | stop for human |
| Codereview Critical | codereview severity summary | stop for human |
| Retry circuit-break | task `retry_count ≥ 3` | stop for human (not transient) |
| PRD drift at stage boundary | ALIGN subagent `verdict: drift` | stop for human |
| Budget / max-iter / usage-limit | loop terminal status / pause state | surface-and-pause, **no approval needed**, resumable |
| Merge / release / destructive | REQ-12 hard gate | stop → `/renmark:approve` |

On success of a stage, the driver **advances automatically** — no per-stage
go/no-go (this is the "minimal feedback" contract).

## Components

1. **Program data model** (NEW) — `renmark/program.py`:
   - `program.json` (runtime state, gitignored under `.renmark/state/`): ordered
     stages → tasks; per-node `status`, `serves: REQ-n`, `retry_count`,
     `stage_completion_sha`, pipeline-phase annotations.
   - `program.md` (committed checklist): stages → tasks as checkboxes, ticked
     **deterministically** by code as work completes. Carries provenance
     frontmatter. The single source of truth for "where are we."
   - Read/write helpers + a bounded `position()` accessor (one-line:
     "Stage N/M · task i/k done") — the ONLY thing the orchestrator reads.
2. **Planner** (roadmap forward `plan` mode) — derives the ordered stage
   sequence. From PRD (bounded subagent) when present; from a feature spec when
   entered via `/renmark:feature`; from a fresh brainstorm when entered via
   `/renmark:start`. Emits `program.json` + `program.md`. Human-gated (REQ-18).
3. **Program driver** (NEW) — the stage loop above. Reuses `loop` per stage;
   never reads generated code/diffs into the orchestrator (G11).
4. **Progress surfacing** — deterministic `program.md` ticks; live per-task
   summary (source: `.renmark/state/wave-summaries/*` `summary_lines`) +
   per-stage digest rollup.
5. **roadmap renderer** — `/renmark:roadmap` reads `program.md`/`program.json`
   and renders the staged position table (zero-LLM), in addition to today's
   retrospective table.
6. **Entry-point divergence**:
   - `/renmark:start` → **feature-planner** mode (greenfield: brainstorm the
     program from scratch).
   - `/renmark:feature` → **staged** mode (decompose an approved feature into
     stages).
   - `/renmark:roadmap` + PRD present → **whole-product program** mode
     (derive the program from the PRD).
   - `/renmark:roadmap --setup` → **brownfield reconciliation** mode (an
     already-in-development project): (a) derive the staged roadmap from the PRD
     (same planner), THEN (b) reconcile it against what is already built —
     marking each stage/task `done | partial | needed` — THEN (c) print the
     roadmap with position so the user sees what exists vs. where work is still
     needed. The "what is built" signal comes from a **bounded subagent** that
     reads `.renmark/memory/project-map.md` (the `/renmark:init` repo scan) +
     git history + the existing `roadmap --gaps` PRD-vs-shipped ALIGN logic —
     **never** code into the orchestrator (REQ-5/G11). If `project-map.md` is
     missing or stale, `--setup` halts and recommends `/renmark:init` first
     (mirrors `/renmark:blueprint`'s map-freshness guard). The reconciled
     statuses pre-populate `program.md` so the driver resumes mid-product rather
     than rebuilding what exists.
   All four emit the same `program.json` + drive via the same program driver.
7. **Resumability** — driver writes `program.json` **before returning** from
   each stage (Temporal-style); `stage_completion_sha` guards plan-time drift
   (warn if source moved since planning); `/renmark:resume` surfaces an
   in-flight program and its next stage.

## Data flow

PRD/spec/brainstorm → planner (bounded) → `program.json` + `program.md` →
**one approval** → driver iterates stages → each stage: ALIGN gate →
brainstorm/plan/check-plan → `loop` over tasks (orchestrate→verify→decide,
deterministic `program.md` ticks, live summaries) → codereview → sha snapshot →
stage digest → write `program.json` → advance. Stop conditions interrupt and
persist; `/renmark:roadmap` renders position on demand; REQ-12 gates route to
`/renmark:approve`.

## Error handling

- **Stop-on-issue** uses structured fields only; an unparseable/missing field is
  treated as `confidence: low, validation_status: unvalidated` → stop (G9).
- **Circuit-break** at `retry_count ≥ 3` per task — escalate to human, never
  loop forever.
- **Plan-time drift** — `stage_completion_sha` mismatch warns before a stage
  executes on stale assumptions.
- **Interruption / `/clear`** — `program.json` written before each stage return;
  recovery is from disk, never conversation (G7/G10/G12).
- **Single-writer** — only one stage's code-writing loop runs at a time.

## Success criteria

1. From a project with a `PRD.md`, `/renmark:roadmap` (forward mode) produces a
   `program.json` + `program.md` of ordered stages→tasks, each tagged
   `serves: REQ-n`, after exactly **one** approval gate.
2. The driver advances stage-to-stage on success with **no** additional approval,
   and **stops** on each defined issue (verify fail, plan BLOCK, codereview
   Critical, retry≥3, PRD drift), persisting resumable state each time.
3. `program.md` reflects live position (ticked per task by deterministic code);
   the orchestrator reads only the bounded position line (≤5 lines, G3).
4. Each finished task surfaces a live ≤5-line summary; each stage emits a digest.
5. A `/clear` mid-program is fully recoverable via `/renmark:resume`.
6. No orchestrator context ever ingests the PRD body, generated code, or diffs
   (REQ-5 / G11 honored throughout).
7. REQ-12 hard gates (merge/release/destructive) remain human-gated via
   `/renmark:approve`; no auto-merge/-release.
8. On an in-development project, `/renmark:roadmap --setup` produces a roadmap
   from the PRD, reconciles it against what is already built (statuses
   `done | partial | needed`), and prints the position — without ingesting code
   into the orchestrator and without rebuilding what already exists. Halts to
   `/renmark:init` when `project-map.md` is missing/stale.

## Prior art & references

- Internal reuse map: `.renmark/research/2026-06-13-roadmap-staged-planner-reuse.research.md`
  (verdict `partial` — reuse loop/backlog/orchestrate/verify/approve/roadmap;
  new = stage+task model, driver, program.md, entry-point divergence, digest).
- External best practices: `.renmark/research/2026-06-13-roadmap-staged-planner-bestpractice.research.md`
  (LangGraph single interrupt-before-execution; Temporal write-state-before-return;
  structured-field stop signals over LLM-interpreted; retry circuit-break;
  plan-time-drift sha snapshot).
- Pre-brainstorm intent + added requirements:
  `.renmark/specs/2026-06-13-roadmap-staged-planner.brief.md`.
- Bounded-loop / approval / single-writer constraints: `PRD.md` (REQ-9/10/11/12/13/18).

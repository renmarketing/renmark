---
artifact_type: spec
schema_version: 1
created_at: 2026-07-02T00:00:00Z
source_sha: 875e776f8e68d2762005cc335c6493564959672d
related_plan: null
generator: brainstorm
stale_after: null
dependency_refs:
  - .renmark/specs/2026-07-02-agency-mode.request.md
  - .renmark/memory/features.md
  - renmark/mode.py
  - renmark/finish_lanes.py
  - renmark/cost.py
  - renmark/subagent_profiles.py
  - plugin/skills/_shared/context-taxonomy.md
  - plugin/skills/_shared/deterministic-first.md
---

# Agency Mode — design spec (MVP: walking skeleton)

> Scaffolded by `/renmark:brainstorm`. Consumed next by `/renmark:plan`.
> Upstream: the queued request at `.renmark/specs/2026-07-02-agency-mode.request.md`.

## Context

Renmark today runs in one of two operating modes chosen at session entry and
persisted (`renmark/mode.py`): **Conductor** (hands-on, small-step) and
**Orchestrator** (goal-level, scoped subagents). Agency Mode is the third
delivery modality named on the roadmap — a full project-delivery loop, "like
hiring a software agency," where the owner gives intent and signs off milestones
while renmark runs the lifecycle behind the scenes.

The prerequisite (`cost-control-finish-lanes`, v0.28.0) has shipped, so Agency
Mode is unblocked. Per the queued request, this spec's job is to answer the six
design questions and define the **smallest MVP** — not a full implementation.

## Owner decisions locked (this session)

1. **Architecture:** Agency Mode is a **higher-level delivery workflow** that
   *uses* Orchestrator internally — **NOT** a third persisted value in
   `renmark/mode.py`. (Answers design question #1.) Rationale: the non-goals
   forbid rebuilding Orchestrator; a workflow layer reuses it instead of
   duplicating it, and keeps mode selection a two-value question.
2. **MVP shape:** **Walking skeleton** — prove the delivery loop end-to-end on a
   core pipeline spine, defer breadth.
3. **Activation:** **Explicit opt-in** via `/renmark:start` (an offered Agency
   lane), never auto-detected. Predictable; matches "owner gives intent."

## Goals

- Add Agency Mode as an **optional** higher-level delivery workflow that sits
  above Conductor/Orchestrator and does not replace them (AC1, AC2).
- Support the delivery loop discovery → PRD → roadmap → milestones → build →
  demo → feedback → signoff (AC6), driven by owner-level decisions, with a
  main agent talking to the owner while scoped background agents do the work
  (AC7, AC8).
- Persist lightweight agency project state so the loop is resumable across
  `/clear` and restarts (AC9).
- Make pipelines agency-aware via **dynamic skill loading** — agency metadata
  upfront, full agency instructions loaded only when Agency Mode is active
  (AC4).
- Reuse — never re-implement — the cost-control / finish-lane / deterministic-
  first infrastructure (AC5).
- Prove via behavior tests that Agency Mode changes renmark's behavior without
  loading every skill body (AC11), and document it (AC10).

## Non-goals (this feature)

- Not a replacement for Conductor/Orchestrator (they remain the execution
  engines Agency drives).
- Not a rebuild of dynamic skill loading, the eval runner, Codex routing, the
  verification system, or cost-control infra — all reused.
- **Full 9-pipeline coverage is out of scope for this MVP.** The walking skeleton
  covers the core spine only; the remaining pipelines are a documented
  fast-follow (see "Deferred to fast-follow").
- Product-level scope governance lives in `PRD.md` (see PRD gate below), not
  duplicated here.

## Answers to the six design questions

1. **Third mode vs higher-level workflow?** → Higher-level workflow (locked
   above). Agency state is a separate lightweight artifact, not a `mode.py`
   value; `mode.py` stays Conductor/Orchestrator.
2. **Which pipelines become agency-aware?** → MVP: the **core spine**
   `start → prd → roadmap → finish → resume`. Fast-follow: `feature`, `plan`,
   `orchestrate`, `verify`, `codereview`.
3. **What does each pipeline do differently under Agency?** → See
   "Per-pipeline agency behavior (MVP spine)" below. In short: owner-level
   framing, milestone awareness, and checkpoint/signoff gates layered on top of
   existing behavior — additive, never a rewrite.
4. **Which skills/fragments are loaded/referenced?** → A new shared fragment
   `plugin/skills/_shared/agency-delivery.md` (the agency contract), loaded on
   demand only when Agency is active. Pipelines reference it by pointer, not by
   inlining it.
5. **How does Agency reuse cost-control infra?** → Directly: `finish_lanes`
   (`recommend_lane`/`resolve_lane`) for per-milestone finish; `cost.py`
   (`estimate_cost`/`requires_escalation`) for pre-wave cost previews;
   `context_budget_hint` for the long delivery loop; `subagent_profiles` for
   scoped background agents; `model-routing.md` / `subagent-budget.md` /
   `deterministic-first.md` for dispatch discipline and milestone-readiness
   checks (no model calls for infra validation, AC6-equiv).
6. **How to make pipelines agency-aware without loading every body?** → Same
   pattern already used for skills: metadata/pointer upfront via preamble;
   the `agency-delivery.md` body and per-pipeline agency blocks load on demand
   only when agency state is active. The orchestrator carries the agency
   *contract pointer*, never the bodies.

## Architecture

Agency Mode = **state + contract fragment + mode-conditioned preamble** layered
over the existing pipeline router. No new execution engine.

```
Owner intent
   │
   ▼
/renmark:start  ──(offers Agency lane; owner opts in)──► agency state initialized
   │
   ▼
agency-delivery contract (loaded on demand) shapes each pipeline's behavior:
   discovery → PRD agreement → roadmap/milestones → [build loop via Orchestrator]
   → demo/verify → owner feedback → signoff → finish-lane release
   │                                              ▲
   └──────────── milestone checkpoints ───────────┘  (pause for owner sign-off)
```

### Components (MVP)

| Component | Path (proposed) | Responsibility |
|---|---|---|
| Agency state | `renmark/agency.py` + `.renmark/state/agency.json` | Lightweight, resumable: `active`, `current_phase`, `current_milestone`, `next_checkpoint`, `signoff_status`, `cost_lane`, `roadmap_ref`. Read/write helpers, ≤1KB guard like lifecycle. |
| Agency contract | `plugin/skills/_shared/agency-delivery.md` | The shared agency delivery contract (owner-level questioning, milestone/checkpoint/signoff rules, background-agent + cost-reuse discipline). Loaded on demand only when agency is active. |
| Preamble wiring | `renmark/lifecycle.py` (or `state/skills.py`) | When agency state is active, `skill_preamble` surfaces a one-line agency hint + pointer to `agency-delivery.md` for the current pipeline. Metadata only — never the body. |
| Pipeline agency blocks | core-spine `SKILL.md` files | Small "When Agency Mode is active" section per spine skill, referencing the fragment by pointer. |
| Help/docs | `plugin/skills/help` + `CLAUDE.md`/`AGENTS.md` | Explain Agency Mode as the third delivery modality. |
| Tests | `tests/` | Behavior checks: agency-active changes preamble/pipeline behavior; bodies not eagerly loaded; state persists/resumes. |

### Per-pipeline agency behavior (MVP spine)

- **/renmark:start** — Agency discovery entry + the opt-in point. Discovery-call
  framing (intent, users, problem, outcome, owner-level questions), project
  classification, then initializes agency state on opt-in.
- **/renmark:prd** — Agency agreement point: PRD create/update with owner
  approval as the source-of-truth lock; change control when feedback shifts
  scope.
- **/renmark:roadmap** — emit milestones with checkpoints, demo points, and
  signoff points; sequencing + risk/dependency notes; write `roadmap_ref` into
  agency state.
- **/renmark:finish** — milestone demo summary + owner signoff gate + finish-lane
  selection via `finish_lanes.recommend_lane`; on new feedback, update roadmap
  and recommend the next milestone.
- **/renmark:resume** — resume from last milestone/checkpoint from
  `agency.json`; summarize where we left off; continue without re-discovery.

### Deferred to fast-follow (documented, not built here)

`feature`, `plan`, `orchestrate`, `verify`, `codereview` agency-awareness. The
walking skeleton runs the loop through the spine; these deepen coverage next.
Called out explicitly so the MVP's bounded coverage is honest, not silent.

## Data flow / state

- `agency.json` is **runtime-adjacent workflow state** (resumable), distinct from
  `lifecycle.json` (per-feature stage) and `pipeline.json` (wave runtime). Keep
  it small (≤1KB guard) and additive — Agency reads lifecycle/pipeline; it does
  not absorb them.
- Milestones/checkpoints reference roadmap artifacts by path, never by inlined
  content (context hygiene, REQ-5).

## Error handling / edge cases

- Agency off → zero behavior change anywhere (bodies never load; preamble hint
  absent). This is the load-bearing "does not replace Conductor/Orchestrator"
  guarantee and gets a dedicated test.
- Missing/corrupt `agency.json` → treat as agency-inactive, never crash a
  pipeline.
- Bloat guard on `agency.json` mirrors `LifecycleBloatError`.

## Success criteria (maps to the request's acceptance criteria)

1. Agency Mode clearly defined as an optional higher-level delivery workflow
   (AC1). ✔ architecture section.
2. Conductor/Orchestrator unchanged and still selectable (AC2). ✔ off-path test.
3. Affected pipelines defined (AC3). ✔ spine + deferred list.
4. Dynamic loading, not eager bodies (AC4, AC11). ✔ preamble-pointer + test.
5. Reuses cost-control/finish-lane/deterministic-first infra (AC5). ✔ reuse map.
6. Supports discovery → … → signoff on the spine (AC6). ✔ per-pipeline behavior.
7. Owner-level questions, not needless technical ones (AC7). ✔ contract fragment.
8. Main agent communicates; scoped background agents work (AC8). ✔ subagent
   profiles + budget contract reused.
9. Milestones/checkpoints persisted + resumable (AC9). ✔ `agency.json` + resume.
10. Help/docs explain Agency Mode (AC10). ✔ help + CLAUDE/AGENTS.
11. Behavior tests prove Agency changes behavior w/o loading all bodies (AC11).
    ✔ tests component.

## PRD gate (human-gated — pending owner approval)

The PRD-alignment check returned **drift**: Agency Mode extends product scope
beyond the current PRD. Proposed addition (to route through `/renmark:prd`, not
written here):

> `REQ-22` **Agency Mode** — an optional higher-level delivery workflow (does not
> replace Conductor/Orchestrator) adding sustained project governance: owner
> intent → PRD agreement → tech-stack recommendation → roadmap/milestones →
> iterative build → demo/feedback → verification → signoff → release. Includes
> lightweight phase state (phase, milestone, signoff), owner-level approval gates
> distinct from technical gates, milestone checkpoints that pause for owner
> feedback, and reuse of cost-control, finish-lanes, and deterministic-first
> infra. Extends REQ-3 (resumable), REQ-4 (PRD source of truth), REQ-5 (context
> hygiene), REQ-21 (deterministic-first milestone-readiness checks).

**This gate must be resolved before build.** `/renmark:plan` may decompose the
spec, but orchestration should not start until REQ-22 is approved (or the scope
narrowed).

## Prior art & references

Internal reuse (no external research needed — this is a renmark-internal feature
on a fixed stack): existing mode machinery (`renmark/mode.py`), lifecycle
persistence pattern (`renmark/lifecycle.py`, the ≤1KB bloat guard), dynamic
skill loading (`renmark/context.py`, `skillmeta`), and the entire cost-control
suite listed in the reuse map above. Agency Mode is composed from these
primitives, not invented.

## Out of scope (feature-scoped)

- Auto-detection of Agency Mode (explicit opt-in only).
- Full 9-pipeline agency coverage (fast-follow).
- Any new inference/execution engine.

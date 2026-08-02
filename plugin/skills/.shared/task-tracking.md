# Native Task Tracking — Reference (single source of truth)

**Shared by every pipeline that dispatches agents** — `/renmark:start`,
`/renmark:feature`, `/renmark:debug`, `/renmark:rethink`, `/renmark:orchestrate`,
`/renmark:codereview`, and `/renmark:finish` — via the dispatch-packet
contract in `_shared/subagent-budget.md`. This is the one place native
task-tracking mechanics live so skills can't drift: when to create a native
task, how to move it through its lifecycle, and what stays informational
versus what stays a Renmark artifact. Implements `PRD.md` REQ-31 and is
itself bound by REQ-30 (orchestration efficiency is a protected capability)
— task tracking is informational scaffolding around the existing dispatch
contract, never a second execution path, a new Owner gate, or retained
orchestrator context.

**Two enforcement layers, not one — do not confuse them:**

1. **Primary, requirement-1 mechanism: the live host's native Task tools.**
   Whenever a Claude Code (or equivalent host) session is *itself* running a
   renmark skill and calls the `Agent` tool to dispatch a subagent, that
   session MUST call the host's real `TaskCreate` before the dispatch and
   `TaskUpdate` through its lifecycle — the actual tool calls, appearing in
   the transcript, not a description of them. This is the mechanism REQ-31
   requirement 1 names, and it is what an interactive `/renmark:start`,
   `/renmark:feature`, `/renmark:rethink`, `/renmark:codereview`, or
   `/renmark:finish` run does every time it dispatches an `Agent` call. There
   is no way to satisfy requirement 1 from Python — only the live agent
   executing the skill can call its own host's tools, which is exactly why
   this is a **skill instruction to the agent**, not a library call.
2. **Secondary, headless-only fallback: `renmark.task_tracking`.** The
   `renmark-execute` CLI's `execute_plan` dispatches to `codex`/host-agent
   executors as a **subprocess with no live Claude Code session and no Task
   tools to call** — there is nothing native to invoke there. For that one
   execution path only, `renmark.task_tracking` (`.renmark/state/tasks.json`,
   atomic writes, never-raising reads) mirrors the same lifecycle
   mechanically — one parent task per plan run, one worker task per
   dispatched task, one linked verification task per worker, completed only
   via `complete_worker_task`, which enforces no-self-approval by reusing
   `renmark.ledger.check_dispatch_independence`. See
   `tests/test_task_tracking.py` and `tests/test_task_tracking_engine_wiring.py`.
   **This does not satisfy requirement 1 for a live agent session** — it
   satisfies requirement 12's graceful-degradation intent for the one path
   where native tools genuinely cannot exist. When a live agent IS present
   (any interactive Claude Code run of a renmark skill), layer 1 applies and
   is not optional.

---

## When to create a native task

**If you are the live agent executing a renmark skill in an interactive
session, this means you, right now, calling your own `TaskCreate`/
`TaskUpdate` tools** — not delegating it to a Python file. Create one native
task for:

- **One parent task per milestone** — a Program stage, a feature build, a
  rethink transformation, a release.
- **One bounded task per dispatch** — each `Agent`/subagent call that does
  real work (research, implementation, review, verification).

**Do not** create a native task for trivial internal reasoning, a
deterministic check (grep, git status, a parser call), or any step that
doesn't involve dispatching an agent or advancing a milestone. The task list
tracks milestone progress and dispatched work — not every tool call, file
read, or internal step (REQ-30's "no routine status interruptions" applies
here too).

---

## Required task content

Every dispatched task's `description` (or an equivalent bounded field) states:

| Field | Content |
|---|---|
| Title | Short, outcome-focused (`subject` field — imperative, names the result). |
| Role/agent | The assigned role or agent type (`renmark:<role>` or `general-purpose`), mirroring the dispatch packet's `role` field. |
| Scope and expected result | What this dispatch covers and what "done" looks like — the dispatch packet's `mission` + `stop_condition`. |
| Dependencies/blockers | Other tasks this one is `addBlockedBy`/`addBlocks`, or a recorded blocker. |
| Acceptance/verification requirement | How this will be checked — points to the dispatch packet's `verification_expectation`. |

This is the same information the dispatch-packet contract (`subagent-budget.md`)
already requires before a dispatch is sent — native task tracking surfaces
it, it does not add a second thing to compute.

---

## Lifecycle

- **`pending`** — the task exists, the dispatch has not gone out yet.
- **`in_progress`** — set immediately before the dispatch call, not after.
- **Blockers, retries, reassignment, failure** — recorded via `TaskUpdate`
  (metadata or description append) the moment they occur, on the same task —
  never a silent retry with no trace.
- **`completed`** — only when the required output AND its verification
  evidence exist (artifact path, PASS/FAIL, exit code). A worker returning a
  result is not, by itself, grounds for `completed` if a review/verification
  task is still required (see "No self-approval," below).

A `retry_once` or reassignment does not create a fresh task — it updates the
existing one, consistent with the recurrence ledger's monotonic
`retry_count` (REQ-24) and REQ-30's anti-re-dispatch rule.

---

## No self-approval

A worker task's own completion never completes its parent milestone task. If
independent verification or review is required (REQ-4/REQ-12 gates, the
Discovery Direction/Solution/Execution gates in REQ-28/REQ-29, or an
Inspector verdict), create an **explicit verification/review task**, link it
to the worker task via `addBlockedBy`/`addBlocks`, and leave the parent
milestone task `in_progress` until that verification task reaches
`completed`. The pattern mirrors `renmark.ledger`'s dispatch-identity
independence check (R-0.4) — a worker cannot be its own inspector, and a
worker task cannot be its own milestone approval.

---

## Resume and scope changes

**On interruption or resume:** reload existing tasks (`TaskList`/`TaskGet`)
before creating anything. A task whose artifact already exists and whose
gate (if any) already cleared is reused, never recreated — this is the same
rule REQ-30 and REQ-28/29's gate contracts already state for artifacts;
native tasks follow it too. Never redispatch a completed or accepted task
just because the session restarted.

**On scope change:** update the existing task's `description`/`metadata`, or
set it `deleted` with a one-line reason recorded first — never silently
abandon a task with no trace. Create a replacement task only after the
original is explicitly closed, and preserve the reason in the parent
milestone's summary or artifact (not just in the deleted task, which may not
be retrievable later).

---

## What stays out of the native task

- **No raw research, transcripts, diffs, or logs.** A native task carries
  bounded status, dependencies, a short result summary, and an artifact
  path — the same ≤5-line/≤300-token discipline REQ-5/REQ-30 already require
  of orchestrator-visible output.
- **No new Owner gate.** Task tracking is informational. It never asks a
  question, never blocks on an approval that isn't already one of the
  pipeline's existing named gates, and never adds an agent dispatch of its
  own.
- **No retained orchestrator context.** Creating/updating a task is a
  cheap, bounded call — it must not become a place to paste worker output
  "for visibility." Detailed evidence stays in the Renmark artifact the
  dispatch already writes; the task points at it.

---

## Graceful degradation

This applies to a genuinely tool-less path — a headless/non-interactive run
(`renmark-execute` invoked as a bare subprocess with no live Claude Code
session attached) — never to an interactive session where `TaskCreate`/
`TaskUpdate` are simply present in the tool palette. In an interactive
Claude Code (or equivalent host) session, calling them is not optional and
"unavailable" is not a valid excuse.

When they are genuinely unavailable, **say so plainly** — "live task
tracking isn't available in this session" — and continue the pipeline
exactly as it already does: durable Renmark artifacts
(`.renmark/state/pipeline.json`, `lifecycle.json`, wave-summaries, stage
artifacts, and — for the headless `renmark-execute` path specifically —
`renmark.task_tracking`'s own state) remain the source of truth regardless.
Never claim a native task was created or updated when the live host tool
was not actually called — a fabricated "tracked" status is worse than an
honest "not tracked here."

---

## Dispatch reference (for skill authors)

When citing this contract in a SKILL.md, write:

> *Before calling `Agent` to dispatch a subagent, call `TaskCreate` yourself
> — your own host tool call, not a description of one. Immediately before
> the dispatch, call `TaskUpdate` to `in_progress`. After the subagent
> returns, call `TaskUpdate` to `completed` only once verification evidence
> exists. Full contract:
> `${CLAUDE_PLUGIN_ROOT}/skills/.shared/task-tracking.md` — one native task
> per dispatch, one parent per milestone, no self-approval, resume reuses
> existing tasks. Informational only — never a new gate, never retained
> context. `renmark.task_tracking` is a Python mirror for the headless
> `renmark-execute` CLI path only — it does not substitute for calling
> `TaskCreate`/`TaskUpdate` yourself in an interactive session.*

Do not paste the lifecycle table or examples into the calling SKILL.md —
cite this file, the same way skills cite `subagent-budget.md` rather than
restating its dispatch-packet contract.

---

## Why a shared file

Wiring native task tracking into eight pipelines independently would drift
the moment one skill invented its own status vocabulary or forgot the
no-self-approval rule. Centralizing here means:

- One edit point for lifecycle states, required fields, and the
  no-self-approval / resume-reuse / no-new-gate rules.
- Reuses the existing dispatch-packet contract's fields (`subagent-budget.md`)
  instead of inventing a parallel schema.
- Symmetric with `subagent-profiles.md`, `context-taxonomy.md`, and
  `agency-delivery.md` — same pattern, same precedent.

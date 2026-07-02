---
name: help
description: "Use when the user types /renmark:help or asks \"what can renmark do\", \"list renmark commands\", \"renmark overview\"."
disable-model-invocation: true
---

# help

## Overview

Teaches the renmark workflow. Prints the user-facing **pipelines** first (each
with the internal stages it runs), then the full skill list grouped by purpose
with each skill's common modifiers. Pure text output, no API calls.

**What renmark is.** renmark is an agentic-engineering / vibe-coding **harness on
top of Claude Code** — not a replacement for it. Claude Code supplies the model,
the tools, and the interactive reasoning loop; renmark is the harness that shapes
*how* that horsepower gets used: planning, scoping, delegation to the cheapest
capable executor, verification, docs, and — above all — context economy. renmark
runs in one of two **operating modes**, and the mode is asked **once** at your
first meaningful workflow, persisted, then applied with a smart per-skill default
thereafter. Override any time with
`renmark-execute --set-mode conductor|orchestrator`.

**Conductor Mode.** For hands-on, interactive work where you stay in the loop.
The harness keeps you close to each decision: it does more work in the primary
context, pauses more readily at gates, and favors visibility over throughput.
Best when the task is small, exploratory, or when you want to steer step by step.

**Orchestrator Mode.** For larger builds you want driven to completion. The
harness decomposes the work, dispatches each task to an isolated subagent /
executor, aggregates only compact PASS/FAIL summaries back to the primary
context, and advances wave by wave. It maximizes throughput and protects the
orchestrator's context window, pausing only at real gates. Best for multi-task
plans (`/renmark:orchestrate`, `/renmark:loop`).

**Agency Mode.** The third delivery modality — a higher-level project-delivery
workflow above Conductor and Orchestrator (does not replace them). Explicit
opt-in via `/renmark:start`. Drives the full discovery → PRD → roadmap →
milestones → build → demo → feedback → signoff → release loop with owner
approval gating each milestone checkpoint. Best for managed projects with
stakeholder sign-off.

All modes enforce the same non-negotiables:

- **Context hygiene** — the primary context is a degrading resource, not durable
  memory. Never read generated file contents, full diffs, or large logs into the
  conversation; work from summaries, counts, paths, and metadata.
- **Subagent discipline** — each task runs in isolation, receiving only its spec,
  file paths, and upstream artifact *pointers*; it returns a bounded summary
  (≤ 5 lines) plus a durable artifact. Subagent transcripts never merge back.
- **Memory / docs** — canonical state lives on disk under `.renmark/` (specs,
  plans, reviews, memory logs, lifecycle/pipeline state), not in chat history.
  These survive `/clear` and `/compact` and make every workflow resumable.
- **Verification** — evidence before claim. Re-run the verifier fresh before
  declaring any task or plan complete; a green earlier wave is not proof now.

## When invoked

Print exactly this block (update individual entries when a command is added or
renamed — `/renmark:audit`'s `description_drift` pass catches stale entries).
Keep it honest: only describe stages and modifiers that exist today.

```
renmark — an agentic-engineering harness on top of Claude Code

Think in pipelines, not commands. Pick the one that matches your situation and
renmark runs the whole sequence, continuing on its own and pausing only at real
decisions: unclear intent, PRD approval, scope change, risky action, cost,
a blocker, or merge/release.

Two operating modes shape how the work runs — Conductor (hands-on, you stay in
the loop) or Orchestrator (decompose → dispatch isolated subagents → aggregate
compact summaries). renmark asks once at your first real workflow, remembers it,
and applies a smart per-skill default after. Override:
  renmark-execute --set-mode conductor|orchestrator

Above both sits Agency Mode — an optional higher-level delivery workflow that
runs the whole discovery → PRD → roadmap → milestones → build → demo → signoff →
release loop with owner sign-off at each milestone. It does not replace the two
modes; opt in explicitly via /renmark:start.

── Pipelines ───────────────────────────────────────────────────────────────
  /renmark:init      Make a repo renmark-ready.
      repo scan → stack/test detect → CLAUDE/AGENTS → project map →
      standards → PRD check → lifecycle-ready

  /renmark:start [idea]      Build something new.
      intent → brainstorm (if fuzzy) → PRD → roadmap → first feature →
      plan → build → verify → review

  /renmark:feature [name]    Add or change a feature in an existing build.
      PRD alignment → reuse check → plan → build → verify → review → finish

  /renmark:debug [symptom]   Fix what's broken.
      reproduce → root cause → fix → regression test → verify → review

  /renmark:roadmap           Find gaps and decide what's next.
      status → gap discovery → backlog proposals → next-feature pick

  /renmark:finish            Verify, review, and ship.
      re-verify → QA/review as needed → report → debug if it fails →
      PR / merge / release menu
      Lanes: quick (re-verify + report) · release (verify + PR/tag) ·
             self-update (renmark-on-renmark install sync) · full (all)

  Which one?
    new app → start          existing app → feature     broke → debug
    what's next? → roadmap    adopt renmark → init       ship → finish

── All skills (grouped) ────────────────────────────────────────────────────
  Format:  command — what it does — common modifiers

  Product / spec
    /renmark:start      — plain-English entry point for a new build
    /renmark:feature    — feature with branch isolation — --lite, --full
    /renmark:prd        — create/update the PRD (product source of truth)
    /renmark:brainstorm — turn a fuzzy idea into a spec, one question at a time
    /renmark:blueprint  — living schematic + UI prototype

  Planning / build
    /renmark:plan        — decompose a spec into routed single-file tasks
    /renmark:check-plan  — validate a plan — PASS / WARN / BLOCK
    /renmark:orchestrate — execute a plan, task-isolated, per-wave summaries
    /renmark:loop        — iterate until a verifier passes — --verify, --budget, --max-iterations
    /renmark:backlog     — triage and approve tracked work items

  Verification / QA
    /renmark:verify      — goal-backward smoke test — --qa, --deep-qa
    /renmark:codereview  — diff-proportional review — --full, --skip, --focus

  Debug / autofix
    /renmark:debug       — reproduce → root cause → fix → regression test
    /renmark:scan        — read-only QA proposer lane — --propose, --emit-cron

  Governance / maintenance
    /renmark:init        — onboard / document a repo (front door)
    /renmark:setup       — refresh renmark rule blocks (alias of init's merge)
    /renmark:audit       — plugin/registry health audit — --quick, --inventory-only, --fix
    /renmark:inventory   — flat inventory of every command and skill
    /renmark:hygiene     — GC stale artifacts, prune memory — --apply, --ttl-days, --memory-days, --include-memory
    /renmark:doctor      — diagnose plugin install health — --fix
    /renmark:approve     — clear a human-approval gate
    /renmark:roadmap     — status + gap discovery — --gaps, --research

  Reporting / release
    /renmark:finish      — close a branch: PR, merge, or release
    /renmark:usage       — observed local usage (pause state, 5h window)
    /renmark:analytics   — build-health: shipped/blocked, loop rate, cost
    /renmark:resume      — cold-start recovery: prints the next command
    /renmark:guide       — interactive decision-tree: picks the right pipeline for you
    /renmark:help        — this message

── Where things live ───────────────────────────────────────────────────────
  .renmark/specs/    — designs from brainstorm (committed)
  .renmark/plans/    — task plans from plan (committed)
  .renmark/reviews/  — review reports (committed)
  .renmark/memory/   — living project docs (committed)
                       features.md, bugs.md, decisions.md, stack.md,
                       architecture.md, conventions.md, routing.md, learnings.md
  .renmark/state/    — runtime: usage ledger, pause file, escalations (gitignored)
  .renmark/debug/    — debug session state (gitignored)

Reference: ${CLAUDE_PLUGIN_ROOT}/ (plugin install directory)
```

If the user asks for more detail on a specific command, refer them to that
skill's SKILL.md or invoke it directly.

## What's next

`help` is a class-3 aux/terminal skill under
`${CLAUDE_PLUGIN_ROOT}/skills/_shared/next-steps.md` (resume-pipeline + local
actions). To keep `help` zero-cost / no-LLM, do **not** call
`renmark.lifecycle.next_steps` here — emit a **static** pointer instead: after
printing the block, append one line steering the user back to a pipeline. If a
feature appears to be in flight, point to `/renmark:resume` to pick up where it
stopped; otherwise point to `/renmark:start` (new build) or `/renmark:init`
(adopt renmark into an existing repo). This is a fixed suggestion, not a
state-derived `AskUserQuestion` choice — no file reads, no subprocesses, no LLM
calls.

## Do not

- Make any HTTP calls or run subprocesses for `/renmark:help`. It's pure documentation.
- Advertise a pipeline stage or a modifier flag that the skill doesn't actually
  implement. Help is the workflow's contract; keep it honest.
- Reorder the pipeline list without strong reason — `init → start → feature →
  debug → roadmap → finish` is the documented user-facing model.

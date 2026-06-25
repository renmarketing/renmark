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

## When invoked

Print exactly this block (update individual entries when a command is added or
renamed — `/renmark:audit`'s `description_drift` pass catches stale entries).
Keep it honest: only describe stages and modifiers that exist today.

```
renmark — guided build assistant

Think in pipelines, not commands. Pick the one that matches your situation and
renmark runs the whole sequence, continuing on its own and pausing only at real
decisions: unclear intent, PRD approval, scope change, risky action, cost,
a blocker, or merge/release.

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

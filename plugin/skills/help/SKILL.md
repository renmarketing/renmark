---
name: help
description: Use when the user types /renmark:help or asks "what can renmark do", "list renmark commands", "renmark overview". Prints all /renmark:* commands with one-sentence descriptions and the typical workflow order. Zero-cost — no LLM calls.
---

# help

## Overview

Lists the renmark plugin's commands with brief descriptions and the recommended workflow order. Pure text output, no API calls.

## When invoked

Print exactly this block (update individual entries when a command is added or
renamed — `/renmark:audit`'s `description_drift` pass now catches stale entries):

```
renmark — guided build assistant

Renmark is a wizard pipeline. Start anywhere; each command offers to
hand off to the next when its job is done:

  /renmark:start  →  /renmark:brainstorm  →  /renmark:plan
    →  /renmark:orchestrate  →  /renmark:verify  →  /renmark:finish

Each transition is an explicit user prompt (Y / n / wait), so nothing
spends tokens without your approval. /renmark:debug runs ad-hoc, anytime.

── Pipeline ──────────────────────────────────────────────────────────────
  /renmark:start [description]
      Plain-English entry point for vibe coders. One open question, at
      most 2 follow-ups, then routes to plan or brainstorm automatically.

  /renmark:brainstorm <topic>
      Flesh out an idea into a spec. One question at a time, Opus-driven,
      research-backed. Bootstraps fresh projects (CLAUDE.md, AGENTS.md,
      .renmark/).

  /renmark:plan <spec>
      Decompose a spec into atomic single-file tasks. Auto-routes each to
      opus, codex, sonnet, or haiku based on complexity. Emits cost preview.

  /renmark:orchestrate <plan>
      Execute a plan. Tasks in the same parallel_group run concurrently;
      commits land serially per wave. Reports per-task PASS/FAIL summaries.

  /renmark:verify
      Goal-backward smoke tests derived from the plan's stated feature
      goal. Three modes: default shell smoke, --qa (live browser happy
      path), --deep-qa (3 live-browser edge cases).

  /renmark:feature <name>
      Full feature pipeline with branch isolation: plan → check-plan →
      orchestrate → verify → finish. Supports --lite and --full overrides.

  /renmark:finish
      Close a feature branch — create PR, merge, or release. Refreshes
      the project map and routes to roadmap gap discovery.

  /renmark:prd
      Create or update the project's PRD — the per-project source of
      truth that plans and features align to.

  /renmark:blueprint
      Generate the project's living schematic (Container-granularity
      Mermaid diagram, always) and a self-contained UI prototype (when
      the project has a browser surface).

── Quality gates ─────────────────────────────────────────────────────────
  /renmark:check-plan <plan>
      Validate a plan deterministically (renmark.plan_lint — shared with
      orchestrate pre-flight): task count, verifier presence, parallel-
      group safety, isolation hygiene. Returns PASS, WARN, or BLOCK.
      Invoked automatically by plan and orchestrate.

  /renmark:codereview [ref]
      Diff-proportional review: scope and model tier scale with the size
      and risk of the change. Writes a timestamped review artifact.

  /renmark:debug <symptom>
      Systematic reproduce → hypothesize → investigate → fix loop. Routes
      cheap inspection to Haiku/Bash, multi-file traces to Codex, and
      cross-system reasoning to Opus. State survives /clear.

── Terminal / meta ───────────────────────────────────────────────────────
  /renmark:init
      Non-destructive front door: scaffolds missing files, back-fills
      rule blocks, scans the repo, writes the project map and dev-
      standards health report. Renmark's analog to Claude Code's /init.

  /renmark:setup
      Thin alias — refreshes/back-fills renmark rule blocks in an
      existing project by delegating to init's rule-block merge.

  /renmark:doctor [--fix]
      Diagnose Claude Code plugin install health. Run when /renmark:*
      commands aren't appearing or after a version bump. --fix applies
      safe auto-repairs.

  /renmark:hygiene [--apply]
      Garbage-collect stale artifacts and prune append-only memory logs.
      Dry-run by default; --apply archives to .renmark/archive/YYYY-MM/.

  /renmark:help
      This message.

── Recovery ──────────────────────────────────────────────────────────────
  /renmark:resume
      Cold-start recovery: reads lifecycle.json and prints the
      recommended next command. Zero LLM calls. Run after /clear.

  /renmark:loop [--max N]
      Bounded iterate-until-verified engine. Repeats a build step until
      the verifier passes or a budget/iteration cap is hit.

  /renmark:backlog
      Triage and approve backlog items interactively. "Approve and build"
      launches bounded Loop Mode on a managed branch.

── Governance / reporting ────────────────────────────────────────────────
  /renmark:roadmap [--gaps]
      Status table: task | llm | status | tokens | $ | commit, built from
      git log and usage.jsonl. --gaps dispatches bounded subagents to
      surface uncovered PRD requirements. Zero LLM calls for the default
      table.

  /renmark:usage
      Observed local usage status: pause state, rolling 5-hour window,
      local limits. Zero LLM calls.

  /renmark:analytics
      Project build-health summary: shipped/blocked features, loop
      success rate, token/cost by feature. Zero LLM calls.

  /renmark:approve
      Human approval gate for lifecycle transitions that require explicit
      sign-off (release, merge, security overrides). AI generates; the
      human owns the merge.

  /renmark:audit [--fix]      ← new in 0.9.0
      Composable audit: lint_all + modularity + registry-sync +
      description_drift + strict-YAML frontmatter check. Surfaces
      stale help entries, ghost skills, and spec drift. --fix routes
      auto-fixable issues to the appropriate skill.

  /renmark:inventory           ← new in 0.9.0
      Snapshot of every skill, shim, template, and memory file with
      freshness and pairing health. Zero LLM calls.

── Meta ──────────────────────────────────────────────────────────────────

Where things live:
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
printing the command list, append one line steering the user back to the
pipeline. If a feature appears to be in flight, point to `/renmark:resume` to
pick up where it stopped; otherwise point to `/renmark:start`. This is a fixed
suggestion, not a state-derived `AskUserQuestion` choice — no file reads, no
subprocesses, no LLM calls.

## Do not

- Make any HTTP calls or run subprocesses for `/renmark:help`. It's pure documentation.
- Rewrite the workflow order without strong reason; the brainstorm → plan → orchestrate sequence is the documented contract.

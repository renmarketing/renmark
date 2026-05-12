---
name: help
description: Use when the user types /renmark:help or asks "what can renmark do", "list renmark commands", "renmark overview". Prints all six /renmark:* commands with one-sentence descriptions and the typical workflow order. Zero-cost — no LLM calls.
---

# help

## Overview

Lists the renmark plugin's six commands with brief descriptions and the recommended workflow order. Pure text output, no API calls.

## When invoked

Print exactly this block (or its current equivalent if commands have been added/renamed since):

```
renmark — multi-LLM orchestration plugin (v0.0.x)

Renmark is a wizard pipeline. Start anywhere; each command offers to
hand off to the next when its job is done:

  /renmark:brainstorm  →  /renmark:plan  →  /renmark:orchestrate  →  /renmark:codereview

Each transition is an explicit user prompt (Y / n / wait), so nothing
spends tokens without your approval. /renmark:debug runs ad-hoc, anytime.

Commands:
  /renmark:brainstorm <topic>
      Flesh out an idea into a spec. One question at a time, Opus-driven.
      Bootstraps fresh projects (creates CLAUDE.md, AGENTS.md, .renmark/).

  /renmark:plan <spec>
      Decompose a spec into atomic single-file tasks. Auto-routes each to
      nim, codex, opus, or sonnet based on complexity. Emits cost preview.

  /renmark:orchestrate <plan>
      Execute a plan. Tasks in the same parallel_group run concurrently;
      commits land serially per wave. Reports per-task PASS/FAIL summaries.

  /renmark:debug <symptom>
      Systematic reproduce → hypothesize → investigate → fix loop. Routes
      cheap inspection to NIM, multi-file traces to Codex, reasoning to Opus.

  /renmark:codereview <ref>
      Multi-pass diff review: codex (adversarial bug-finding), sonnet
      (quality), opus (architecture/security on hot files).

  /renmark:help
      This message.

Where things live:
  .renmark/specs/    — designs from brainstorm (committed)
  .renmark/plans/    — task plans from plan (committed)
  .renmark/reviews/  — review reports (committed)
  .renmark/memory/   — living project docs (committed)
                       features.md, bugs.md, decisions.md, stack.md,
                       architecture.md, conventions.md, routing.md, learnings.md
  .renmark/state/    — runtime: usage ledger, pause file, escalations (gitignored)
  .renmark/debug/    — debug session state (gitignored)

Reference: PLAN.md in the install dir (~/.claude/plugins/renmark/ via symlink
to /home/renmark/projects/ai-system/).
```

Adapt the version number if it has changed. If the user asks for more detail on a specific command, refer them to that skill's SKILL.md or invoke it directly.

## Do not

- Make any HTTP calls or run subprocesses for `/renmark:help`. It's pure documentation.
- Rewrite the workflow order without strong reason; the brainstorm → plan → orchestrate sequence is the documented contract.

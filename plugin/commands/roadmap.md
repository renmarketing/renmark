---
description: "Use for the Maintenance / Gap pipeline — what's stale, missing, or next. Typed as /renmark:roadmap, \"show the roadmap\", \"what's been built\", \"what's next\". Default prints a zero-cost status table (task | llm | status | tokens | $ | commit) from usage.jsonl + git log; --gaps dispatches bounded subagents to compare PRD vs shipped work and propose backlog items; --research adds web research. Also handles forward planning (PRD → staged/whole-product program) and --setup brownfield reconciliation."
argument-hint: '[--gaps] [--research] [--setup]'
---

Read `${CLAUDE_PLUGIN_ROOT}/skills/roadmap/SKILL.md` and follow its instructions exactly. The user provided this input: $ARGUMENTS

If `$ARGUMENTS` is empty, begin the roadmap skill's flow.

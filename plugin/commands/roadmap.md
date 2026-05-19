---
description: Use when the user wants a status report on what renmark has built in this project — typed as /renmark:roadmap, "show the roadmap", "what's been built", "token usage report". Prints a table of task | llm | status | tokens | $ | commit, synthesized from features.md, usage.jsonl, and git log. Zero LLM calls.
---

Read `${CLAUDE_PLUGIN_ROOT}/skills/roadmap/SKILL.md` and follow its instructions exactly. The user provided this input: $ARGUMENTS

If `$ARGUMENTS` is empty, begin the roadmap skill's flow.

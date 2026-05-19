---
description: Use to execute a renmark plan — `/renmark:orchestrate` or "execute the plan", "build it", "run the plan". Reads the plan, dispatches each task in an isolated subagent context (G11), aggregates per-wave summaries to `.renmark/state/wave-summaries/`, commits passing tasks, updates `pipeline.json` + `lifecycle.json`. The orchestrator NEVER reads generated code into conversation — subagent transcripts, diffs, and bodies live in artifacts only.
argument-hint: '[path to plan or empty to use latest]'
---

Read `${CLAUDE_PLUGIN_ROOT}/skills/orchestrate/SKILL.md` and follow its instructions exactly. The user provided this input: $ARGUMENTS

If `$ARGUMENTS` is empty, begin the orchestrate skill's flow.

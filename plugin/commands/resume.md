---
description: Use after `/clear` or `/compact`, or at the start of a fresh session, to discover where the in-flight renmark feature stopped. Reads `.renmark/state/lifecycle.json` and prints the recommended next command. Zero LLM calls — pure file IO. This is the cold-start recovery surface that makes "AI workflows survive context death."
---

Read `${CLAUDE_PLUGIN_ROOT}/skills/resume/SKILL.md` and follow its instructions exactly. The user provided this input: $ARGUMENTS

If `$ARGUMENTS` is empty, begin the resume skill's flow.

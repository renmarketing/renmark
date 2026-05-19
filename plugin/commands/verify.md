---
description: Use after `/renmark:orchestrate` completes — runs goal-backward smoke tests derived from the plan's stated feature goal, cross-references open bugs for regressions, reports how many requirements were confirmed, writes a `.verification.md` artifact, and appends a learning entry. Never reads source code into conversation.
---

Read `${CLAUDE_PLUGIN_ROOT}/skills/verify/SKILL.md` and follow its instructions exactly. The user provided this input: $ARGUMENTS

If `$ARGUMENTS` is empty, begin the verify skill's flow.

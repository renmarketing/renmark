---
description: "Use for the Debug pipeline (/renmark:debug) when something is broken — plain requests like \"fix X\", \"why is X failing\", \"find the root cause\", \"investigate the error\", \"make X work\". Keeps scope tight to the fix (no feature expansion); for adding or changing behavior that isn't broken, use /renmark:feature."
argument-hint: '[symptom or error message]'
---

Read `${CLAUDE_PLUGIN_ROOT}/skills/debug/SKILL.md` and follow its instructions exactly. The user provided this input: $ARGUMENTS

If `$ARGUMENTS` is empty, begin the debug skill's flow.

---
description: "Use when the user wants a bounded agentic loop toward a verifier — typed as /renmark:loop or phrases like \"loop until X passes\", \"keep iterating until green\". Cycles build → verify under a budget and max-iteration cap, stopping on success or exhaustion; loop state survives /clear."
argument-hint: '[goal] [--verify <cmd>] [--budget <n>] [--max-iterations <n>]'
---

Read `${CLAUDE_PLUGIN_ROOT}/skills/loop/SKILL.md` and follow its instructions exactly. The user provided this input: $ARGUMENTS

If `$ARGUMENTS` is empty, begin the loop skill's flow.

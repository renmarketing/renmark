---
description: Use to run a bounded agentic loop — `/renmark:loop` or "loop on this until it passes", "keep iterating until the verifier is green". Drives a goal toward a verifier under an explicit budget and max-iteration cap, re-running the verifier each pass and stopping on success, budget exhaustion, or the iteration ceiling. Persists loop state so the run survives `/clear`.
argument-hint: '[goal] [--verifier <cmd>] [--budget <n>] [--max-iterations <n>]'
---

Read `${CLAUDE_PLUGIN_ROOT}/skills/loop/SKILL.md` and follow its instructions exactly. The user provided this input: $ARGUMENTS

If `$ARGUMENTS` is empty, begin the loop skill's flow.

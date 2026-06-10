---
description: "Use to clear a pending human-approval gate — `/renmark:approve` is the ONLY surface that flips `human_review_completed` in lifecycle.json. Reviews what needs approval, asks for explicit confirmation, and records the decision. Zero LLM judgment — the human decides."
argument-hint: '[approve | reject]'
---

Read `${CLAUDE_PLUGIN_ROOT}/skills/approve/SKILL.md` and follow its instructions exactly. The user provided this input: $ARGUMENTS

If `$ARGUMENTS` is empty, begin the approve skill's flow.

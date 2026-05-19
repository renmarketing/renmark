---
description: Use when the user reports a bug or unexpected behavior — typed as /renmark:debug or phrases like "debug this", "why is X failing", "investigate the error", "find the root cause". Systematic reproduce → hypothesize → investigate → fix loop. Routes cheap investigation (greps, line counts) to Haiku/Bash, multi-file traces to Codex, and cross-system reasoning to Opus. State preserved in .renmark/debug/<session-id>/ so the session survives /clear.
argument-hint: '[symptom or error message]'
---

Read `${CLAUDE_PLUGIN_ROOT}/skills/debug/SKILL.md` and follow its instructions exactly. The user provided this input: $ARGUMENTS

If `$ARGUMENTS` is empty, begin the debug skill's flow.

---
description: Use for the Debug pipeline when something is broken — typed as /renmark:debug or phrases like "debug this", "why is X failing", "investigate the error", "find the root cause". Runs reproduce → root cause → fix → regression test → verify, keeping scope tight (no feature expansion). Routes cheap investigation (greps, line counts) to Haiku/Bash, multi-file traces to Codex, and cross-system reasoning to Opus. State preserved in .renmark/debug/<session-id>/ so the session survives /clear.
argument-hint: '[symptom or error message]'
---

Read `${CLAUDE_PLUGIN_ROOT}/skills/debug/SKILL.md` and follow its instructions exactly. The user provided this input: $ARGUMENTS

If `$ARGUMENTS` is empty, begin the debug skill's flow.

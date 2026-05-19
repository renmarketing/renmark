---
description: Use before executing a renmark plan — validates task count, verifier presence, and parallel group safety. Returns PASS, WARN, or BLOCK. Invoked automatically by /renmark:orchestrate pre-flight.
argument-hint: '[path to plan or empty to use latest]'
---

Read `${CLAUDE_PLUGIN_ROOT}/skills/check-plan/SKILL.md` and follow its instructions exactly. The user provided this input: $ARGUMENTS

If `$ARGUMENTS` is empty, begin the check-plan skill's flow.

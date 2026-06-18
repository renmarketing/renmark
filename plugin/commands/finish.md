---
description: Use for the Ship / Readiness pipeline when implementation is complete — re-runs verifiers, shows the commit summary, routes failures to debug, then offers PR / merge / release / nothing. Release builds a version-anchored distribution zip + unpacked snapshot into .renmark/version/ (always, offline) and a matching git tag, plus a GitHub release when a remote + gh are available. Merge and release are Pause-Policy gates — never default. Thin branch-close wrapper around gh and git.
---

Read `${CLAUDE_PLUGIN_ROOT}/skills/finish/SKILL.md` and follow its instructions exactly. The user provided this input: $ARGUMENTS

If `$ARGUMENTS` is empty, begin the finish skill's flow.

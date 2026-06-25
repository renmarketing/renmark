---
description: Use after a build or `/renmark:orchestrate` to confirm it works — the post-build check that runs a shell smoke test by default, a live-browser happy-path flow with `--qa`, or 3 browser edge-case flows with `--deep-qa`.
argument-hint: '[empty for shell smoke | --qa for live-browser happy path | --deep-qa for 3 live-browser edge cases]'
---

Read `${CLAUDE_PLUGIN_ROOT}/skills/verify/SKILL.md` and follow its instructions exactly. The user provided this input: $ARGUMENTS

Mode selection — parse `$ARGUMENTS`:
- contains `--deep-qa` → Deep QA mode (runs the gate, the risk-rank plan pass, then 3 edge-case browser flows)
- contains `--qa` → QA mode (1 happy-path browser flow)
- otherwise → default Smoke mode

If `$ARGUMENTS` is empty, begin the verify skill's default Smoke flow.

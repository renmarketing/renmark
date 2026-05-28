---
description: Use after `/renmark:orchestrate` completes — three modes selected by flag. Default (no flag) runs the goal-backward shell smoke test. `--qa` runs one live-browser happy-path flow via Chrome DevTools MCP. `--deep-qa` runs 3 risk-ranked edge-case flows in the browser (gated behind a passing `--qa` for the current sha). All modes report a bounded ≤5-line verdict, dump heavy evidence to disk, append to `learnings.md`, and log failures to `bugs.md`. Never reads source code into conversation.
argument-hint: '[empty for shell smoke | --qa for live-browser happy path | --deep-qa for 3 live-browser edge cases]'
---

Read `${CLAUDE_PLUGIN_ROOT}/skills/verify/SKILL.md` and follow its instructions exactly. The user provided this input: $ARGUMENTS

Mode selection — parse `$ARGUMENTS`:
- contains `--deep-qa` → Deep QA mode (runs the gate, the risk-rank plan pass, then 3 edge-case browser flows)
- contains `--qa` → QA mode (1 happy-path browser flow)
- otherwise → default Smoke mode

If `$ARGUMENTS` is empty, begin the verify skill's default Smoke flow.

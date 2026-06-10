---
description: "Use to start a new feature or significant change with branch isolation — typed as /renmark:feature or phrases like \"new feature X\", \"build X\", \"start feature\". Creates a branch then runs the full pipeline: plan → check-plan → orchestrate → verify → finish."
argument-hint: '[feature name or short description]'
---

Read `${CLAUDE_PLUGIN_ROOT}/skills/feature/SKILL.md` and follow its instructions exactly. The user provided this input: $ARGUMENTS

If `$ARGUMENTS` is empty, begin the feature skill's flow.

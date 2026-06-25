---
description: "Use when the user wants to author or maintain the project's Product Requirements Document — typed as /renmark:prd or phrases like \"write the PRD\", \"update requirements\", \"update the product spec\". Creates the PRD when none exists or reconciles a requested change as a human-gated diff."
argument-hint: '[create | update | change description]'
---

Read `${CLAUDE_PLUGIN_ROOT}/skills/prd/SKILL.md` and follow its instructions exactly. The user provided this input: $ARGUMENTS

If `$ARGUMENTS` is empty, begin the prd skill's flow.

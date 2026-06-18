---
description: "Use for the Feature pipeline — adding or changing something in an existing build, with branch isolation. Typed as /renmark:feature or phrases like \"new feature X\", \"build X\", \"start feature\". Runs setup check → PRD alignment (creates a PRD only if none exists) → reuse check → plan → check-plan → build → verify → review → finish, continuing automatically and pausing only at real decisions."
argument-hint: '[feature name or short description] [--lite | --full]'
---

Read `${CLAUDE_PLUGIN_ROOT}/skills/feature/SKILL.md` and follow its instructions exactly. The user provided this input: $ARGUMENTS

If `$ARGUMENTS` is empty, begin the feature skill's flow.

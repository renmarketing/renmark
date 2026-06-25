---
description: "Use when the user wants to review or act on tracked work items — typed as `/renmark:backlog` or phrases like \"show the backlog\", \"what's pending review\", \"approve and build X\". Opens an interactive list and per-item detail view; 'Approve and build' builds the item on a managed branch."
argument-hint: '[item-id]'
---

Read `${CLAUDE_PLUGIN_ROOT}/skills/backlog/SKILL.md` and follow its instructions exactly. The user provided this input: $ARGUMENTS

If `$ARGUMENTS` is empty, begin the backlog skill's flow.

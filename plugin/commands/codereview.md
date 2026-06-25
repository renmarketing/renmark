---
description: "Use when the user wants a diff or PR reviewed — typed as /renmark:codereview or phrases like \"review this\", \"review my changes\", \"check this PR\", \"code review HEAD~3..HEAD\". Depth scales to the diff: a small/doc diff gets a quick in-context review, a larger one gets the full sandboxed review pass."
argument-hint: '[ref range like HEAD~3..HEAD] [--full | --skip] [--focus optimize|standards]'
---

Read `${CLAUDE_PLUGIN_ROOT}/skills/codereview/SKILL.md` and follow its instructions exactly. The user provided this input: $ARGUMENTS

If `$ARGUMENTS` is empty, begin the codereview skill's flow.

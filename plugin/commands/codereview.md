---
description: "Use when the user wants a diff or PR reviewed — typed as /renmark:codereview or phrases like \"review this\", \"review my changes\", \"check this PR\", \"code review HEAD~3..HEAD\". Review depth is proportional to the diff: a lite/doc diff runs the built-in cheap /review in-context by default (then offers a one-keystroke escalate to the full codex pass); a standard/full diff runs the full codex review pass in a read-only sandbox, emitting a structured markdown report at .renmark/reviews/YYYY-MM-DD-<sha>.review.md. Opus only reads the severity summary — never the diff itself, to keep context lean."
argument-hint: '[ref range like HEAD~3..HEAD] [--full | --skip] [--focus optimize|standards]'
---

Read `${CLAUDE_PLUGIN_ROOT}/skills/codereview/SKILL.md` and follow its instructions exactly. The user provided this input: $ARGUMENTS

If `$ARGUMENTS` is empty, begin the codereview skill's flow.

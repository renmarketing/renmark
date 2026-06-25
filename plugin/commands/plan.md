---
description: "Use when the user has a spec and wants it decomposed into an executable task list — typed as /renmark:plan or phrases like \"write a plan\", \"decompose this\", \"create the plan for X\". Splits the spec into atomic tasks and emits a cost preview."
argument-hint: "[path to spec or '.renmark/specs/...' — leave empty to use latest]"
---

Read `${CLAUDE_PLUGIN_ROOT}/skills/plan/SKILL.md` and follow its instructions exactly. The user provided this input: $ARGUMENTS

If `$ARGUMENTS` is empty, begin the plan skill's flow.

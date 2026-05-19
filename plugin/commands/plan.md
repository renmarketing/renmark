---
description: Use when the user has a spec and wants it decomposed into an executable task list — typed as /renmark:plan or phrases like "write a plan", "decompose this", "create the plan for X". Opus reads the spec, splits it into atomic single-file tasks, scores complexity, auto-routes each task to the cheapest model that can do it (haiku, codex, sonnet, opus), groups tasks for parallel execution, and emits a cost preview.
argument-hint: '[path to spec or '.renmark/specs/...' — leave empty to use latest]'
---

Read `${CLAUDE_PLUGIN_ROOT}/skills/plan/SKILL.md` and follow its instructions exactly. The user provided this input: $ARGUMENTS

If `$ARGUMENTS` is empty, begin the plan skill's flow.

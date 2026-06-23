---
description: "Use for the New Build pipeline — the plain-English entry point when a vibe coder wants to build, develop, make, or create something new and doesn't know where to begin. Triggers on plain dev requests like \"build out X\", \"develop X\", \"implement X\", \"add X\", \"create X\", \"code up X\". Adaptive: one open question, at most 2 follow-ups, then establishes a PRD and routes to plan, brainstorm, or a staged program automatically. Runs intent → PRD → roadmap → first feature → plan → build → verify → review, pausing only at real decisions."
argument-hint: '[free-text description of what you want to build]'
---

Read `${CLAUDE_PLUGIN_ROOT}/skills/start/SKILL.md` and follow its instructions exactly. The user provided this input: $ARGUMENTS

If `$ARGUMENTS` is empty, begin the start skill's flow.

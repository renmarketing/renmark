---
description: Use when the user wants to flesh out an idea into a concrete spec — typed as /renmark:brainstorm or phrases like "let's brainstorm this", "I have an idea", "help me think through X". Asks one question at a time using Opus, writes a design doc at the end. Bootstraps fresh projects by creating CLAUDE.md, AGENTS.md, and .renmark/ when invoked in an empty folder.
argument-hint: '[topic or idea — leave empty for guided flow]'
---

Read `${CLAUDE_PLUGIN_ROOT}/skills/brainstorm/SKILL.md` and follow its instructions exactly. The user provided this input: $ARGUMENTS

If `$ARGUMENTS` is empty, begin the brainstorm skill's flow.

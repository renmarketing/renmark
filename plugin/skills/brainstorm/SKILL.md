---
name: brainstorm
description: Use when the user wants to flesh out an idea into a concrete spec — typed as /renmark:brainstorm or phrases like "let's brainstorm this", "I have an idea", "help me think through X". Asks one question at a time using Opus, writes a design doc at the end. Bootstraps fresh projects by creating CLAUDE.md, AGENTS.md, and .renmark/ when invoked in an empty folder.
---

# brainstorm

## Overview

One-question-at-a-time spec discovery, Opus-driven. Output: a design doc at `.renmark/specs/YYYY-MM-DD-<topic>.spec.md` that `/renmark:plan` consumes next.

If the current directory has no `CLAUDE.md`, no `AGENTS.md`, and no `.renmark/`, ask the user whether to scaffold a fresh project before starting the brainstorm.

## When to Use

- "Let's brainstorm a /healthz endpoint"
- "I have an idea for a CLI tool"
- "Help me design X"
- Empty/near-empty directory + user wants to start a new project

**Do NOT use:**
- For executing existing plans — use `/renmark:orchestrate`
- For debugging — use `/renmark:debug`

## Steps

### 1. Empty-folder bootstrap (only if needed)

Check the cwd:
```bash
test -e CLAUDE.md || test -e AGENTS.md || test -d .renmark
```

If none exist, ask the user: *"This looks like a fresh project. Scaffold `CLAUDE.md`, `AGENTS.md`, and `.renmark/` to organize work? [Y/n]"*

On yes:
- Read templates from `~/.claude/plugins/renmark/templates/` (CLAUDE.md.template, AGENTS.md.template, memory/INDEX.md, etc.).
- Substitute placeholders for project name and date.
- Write `CLAUDE.md`, `AGENTS.md`, `.gitignore` (with `.renmark/state/` and `.renmark/debug/` entries), and the `.renmark/` directory tree.
- `git init -b main && git add -A && git commit -q -m "chore: renmark scaffold"`

### 2. Brainstorm

Ask the user questions ONE at a time. Prefer multiple-choice when possible. Cover:
- Goal / problem being solved (the WHY)
- Constraints (deadlines, environment, dependencies)
- Success criteria (how do you know it worked?)
- Out-of-scope explicitly

Stop asking once you can describe what's being built in 2-3 paragraphs.

### 3. Propose 2-3 approaches

With trade-offs. Lead with your recommendation.

### 4. Present the design

In sections, scaled to complexity. Get approval per section. Cover: architecture, components, data flow, error handling, testing.

### 5. Write the spec

Save to `.renmark/specs/YYYY-MM-DD-<topic>.spec.md`. Include: context, goals, non-goals, architecture, components, success criteria.

Also update `.renmark/memory/project.md` with any new project facts learned (tech stack, conventions).

### 6. Hand off

Tell the user: *"Spec written to `<path>`. Next: run `/renmark:plan <path>` to decompose into tasks with per-task model assignments."*

## Common Mistakes

| Mistake | Fix |
|---|---|
| Asking multiple questions at once | One at a time — easier to answer, less context churn |
| Implementing during brainstorm | Brainstorm ends with a spec, not code. Implementation is `/renmark:orchestrate`'s job |
| Skipping the bootstrap question | Empty projects benefit from CLAUDE.md + AGENTS.md before any work starts |
| Writing the spec without user approval | Present the design, get section-by-section approval, then write |

## Reference

- Plan format spec: `PLAN.md` in the renmark install
- Template files: `~/.claude/plugins/renmark/templates/`

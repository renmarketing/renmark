---
name: plan
description: Use when the user has a spec and wants it decomposed into an executable task list — typed as /renmark:plan or phrases like "write a plan", "decompose this", "create the plan for X". Opus reads the spec, splits it into atomic single-file tasks, scores complexity, auto-routes each task to the cheapest model that can do it (nim, codex, opus, sonnet), groups tasks for parallel execution, and emits a cost preview.
---

# plan

## Overview

Reads a spec (from `/renmark:brainstorm` or any markdown file) and emits a renmark-format plan at `.renmark/plans/YYYY-MM-DD-<topic>.plan.md`. Each task in the plan declares:

- `mode` — A (new file) or B (edit existing)
- `target` — exactly one file path
- `complexity` — simple / medium / hard
- `executor` — nim / codex / opus / sonnet (auto-assigned)
- `parallel_group` — tasks sharing a group run concurrently
- `verifier` — shell command that exits 0 when the task is done
- `est_tokens` and `est_cost_usd` — planner's estimates
- `spec` — prose telling the executor what to build

The plan is consumed by `/renmark:orchestrate`.

## When to Use

- After `/renmark:brainstorm` produces a spec
- When the user has a feature description and wants it broken into tasks
- When an existing plan needs to be re-decomposed

**Do NOT use:**
- Without a spec or clear feature description — route to `/renmark:brainstorm` first
- For executing — that's `/renmark:orchestrate`

## Steps

### 1. Read the spec

Open the spec file. Also read `.renmark/memory/INDEX.md` (cheap) and pull any of `routing.md`, `conventions.md`, `learnings.md` that look relevant.

### 2. Decompose into atomic tasks

Rules:
- **One file per task.** If a feature touches `server.py` and `tests/test_server.py`, that's two tasks.
- **Order so verifiers pass.** Implementation before tests. Static assets before code that references them.
- **No mode C** (cross-file refactors). Decompose into A/B per file.
- **Drop non-emission steps.** `mkdir`, `git init`, `git commit`, manual smoke tests are not tasks — the orchestrator handles directories and commits itself.

### 3. Score each task

For each task, set `complexity`:
- **simple** — `.gitignore`, plain HTML, simple CSS, JSON config, single-line file
- **medium** — single-file Python module with clear spec, server routing with edge cases, test scaffolding
- **hard** — game logic, state machines, coordinate math, DOM APIs, threading, regex parsing

### 4. Auto-route executor

Default routing (override if `.renmark/memory/routing.md` says otherwise):

| Signal | Executor |
|---|---|
| simple, mechanical | `nim` |
| `tests/**`, fixtures, multi-file context | `codex` |
| hard / state machines / coord math / DOM / threading | `opus` |
| medium domain reasoning, refactors | `sonnet` |

### 5. Assign parallel_group

Tasks that touch disjoint files AND don't depend on each other's outputs get the same `parallel_group`. Conservative default: each task in its own group (serial). Set the same group only when you're confident the targets won't collide.

### 6. Estimate cost

For each task:
- `nim` → free (NVIDIA free tier)
- `codex` → ~$0.01-$0.05/kT × estimated output tokens
- `opus` → in-context (no separate API charge; consumes orchestrator's context)
- `sonnet` → ~$0.003/kT × estimated output tokens

Show a per-task and total cost preview.

### 7. Write the plan

Save to `.renmark/plans/YYYY-MM-DD-<topic>.plan.md`. Include:
- Title + context (1 paragraph)
- Task blocks in the format above
- Cost preview at the bottom

### 8. Hand off

Tell the user: *"Plan written to `<path>` with N tasks (M parallel groups, ~$X estimated). Next: run `/renmark:orchestrate <path>` to execute."*

## Plan file format example

```markdown
### Task 1: gitignore
- **mode:** A
- **target:** .gitignore
- **complexity:** simple
- **executor:** nim
- **parallel_group:** 1
- **est_tokens:** 150
- **est_cost_usd:** 0.00
- **verifier:** test -f .gitignore
- **spec:**
  Create a .gitignore with __pycache__/, *.pyc, .venv/, .pytest_cache/.

### Task 2: server module
- **mode:** A
- **target:** server.py
- **complexity:** medium
- **executor:** nim
- **parallel_group:** 1
- **est_tokens:** 900
- **est_cost_usd:** 0.00
- **verifier:** python3 -m py_compile server.py
- **spec:**
  ...
```

## Reference

- Auto-routing heuristics: `PLAN.md` § "Auto-routing heuristics"
- Memory files: `.renmark/memory/routing.md`, `learnings.md`, `conventions.md`

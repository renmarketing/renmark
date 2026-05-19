---
name: check-plan
description: Use before executing a renmark plan — validates task count, verifier presence, and parallel group safety. Returns PASS, WARN, or BLOCK. Invoked automatically by /renmark:orchestrate pre-flight.
---

# check-plan

## Overview

Lightweight plan validator. Three checks before any tokens are spent:
1. Task count ≤ 15
2. Every task has a non-empty verifier
3. No two tasks in the same `parallel_group` target the same file

## When to Use

- Automatically by `/renmark:orchestrate` pre-flight
- Manually after `/renmark:plan` if you want to review before dispatching

**Do NOT use:**
- As a substitute for `/renmark:plan` — this validates an existing plan, it does not create one

## Steps

### 1. Read the plan

Open the plan file. Note: task count, executors, parallel groups, verifiers.

### 2. Run checks

**Count check:** If task count > 15 → BLOCK: plan must be split into `part1`/`part2` files before orchestrate will accept it.

**Verifier check:** For each task, confirm `verifier:` is present and non-empty.
- Missing verifier → BLOCK for that task
- `test -f <file>` alone → WARN (proves existence, not behavior)
- `python3 -m py_compile` or `node -e "require(...)"` → OK
- Command exercising actual behavior → best

**Parallel group safety:** For each `parallel_group` value, collect all `target` paths. If two tasks in the same group share a target → BLOCK.

### 3. Report

```
check-plan: <plan-name>
Tasks: N  Executors: haiku×a codex×b sonnet×c opus×d

BLOCK (must fix before running):
- Task N: <reason>

WARN (review before running):
- Task N: verifier proves existence only — consider adding a behavioral check

PASS: structural constraints met
```

Exit 1 on any BLOCK. Exit 0 with WARNs listed or clean PASS.

### 4. Hand off (wizard step)

Renmark is a wizard pipeline. After reporting results:

- **BLOCK** → stop. Fix the flagged issues in the plan file, then re-run `/renmark:check-plan`.
- **PASS or WARN** → prompt:

> *"Plan validated. Ready to dispatch?*
> *  [y] Yes — run /renmark:orchestrate now*
> *  [n] No — stop, I'll run it later"*

On **y** → immediately invoke `/renmark:orchestrate`. On **n** → stop.

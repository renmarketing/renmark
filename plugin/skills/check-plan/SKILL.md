---
name: check-plan
description: Use before executing a renmark plan — validates task count, verifier presence, and parallel group safety. Returns PASS, WARN, or BLOCK. Invoked automatically by /renmark:orchestrate pre-flight.
---

# check-plan

## Overview

Lightweight plan validator. Structural + hygiene + isolation checks before any tokens are spent:

**Structural (G3):**
1. Task count ≤ 15
2. Every task has a non-empty verifier
3. No two tasks in the same `parallel_group` target the same file

**Hygiene + isolation (G3, G5, G11 — added v0.3.0):**
4. No task reads >1 file with >200 lines unless `executor: codex | haiku` (G5)
5. No task spec asks the executor to "show me the code" / "explain the change" / "paste the diff" — those imply transcript leakage (G11)
6. No plan dependency requires reading the **full output** of a prior task instead of its `dependency_notes` (G11)
7. No verifier emits unbounded stdout without piping through `head` / `tail` / `grep` (G3)
8. Spec length ≤ 80 lines (WARN if exceeded — encourages decomposition)

## When to Use

- **Automatically by `/renmark:plan`** — plan runs this validation right after writing the plan, before the dispatch gate (v0.3.3+). You rarely invoke it by hand.
- Automatically by `/renmark:orchestrate` pre-flight (defense in depth).
- Manually on any existing `.plan.md` you want to re-check.

**Do NOT use:**
- As a substitute for `/renmark:plan` — this validates an existing plan, it does not create one

**Note on auto-invocation:** when `/renmark:plan` runs these checks, it suppresses this skill's own orchestrate hand-off (Step 4) — plan owns the dispatch/cost-approval gate. The hand-off below fires only when check-plan is invoked directly.

## Steps

**Step 0 — Context check.** Call `lifecycle.skill_preamble(repo, 'check-plan')`. If it returns a non-None hint, surface as a one-line note.

**Final step — Lifecycle update.** On PASS verdict (or WARN that the user explicitly accepts), call `lifecycle.write_lifecycle(repo, stage='plan-validated')`. On BLOCK, do NOT update lifecycle — the plan must be fixed and re-validated first.

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

### 2.5. Hygiene + isolation checks (G3, G5, G11)

**Heavy-read check (G5):** For each task, count `context_files` whose on-disk line count is > 200. If a task has ≥ 1 such file AND `executor` is `sonnet` or `opus`, **BLOCK**:

> Task N reads `<file>` (M lines) with executor `<executor>`. Heavy reads belong in Codex or Haiku (G5 / `executor-dispatch-rule`). Either reassign the task to `executor: codex`, or split the read into a Codex pre-task that produces a summary artifact.

**Transcript-leak phrase check (G11):** Grep each task `spec:` field for case-insensitive matches against this denylist:

```
show me the code
paste the diff
return the contents
include the full
print the file
explain the change in your response
output the code
```

Any match → **BLOCK**:

> Task N spec contains the phrase `<match>`. This implies the subagent will paste generated content into its response, violating G11 task isolation. The artifact lives in the file at the task's target; the orchestrator reads only summary fields. Rewrite the spec to ask for behavior, not output.

**Dependency-graph hygiene check (G11):** If a task has a `depends_on:` field, confirm the dependency reference reads a *summary* or *interface*, not the prior task's full output. Heuristic: spec mentions "depends on the output of task N" or "uses what task N produced" without specifying an artifact path → **BLOCK**:

> Task N depends on the full output of task M. Downstream tasks must reference only `dependency_notes` from the prior wave's `.renmark/state/wave-summaries/wave-X.json`, not "what task M did." Rewrite the spec to name the specific interface (function name, file path, exported symbol) it depends on.

**Verifier-output-bound check (G3):** For each task's `verifier:` field, parse the shell command. If it includes any of these without a downstream cap (`head`, `tail`, `grep`, `wc`, `awk 'NR<=N'`, redirect to `/dev/null`, etc.) → **WARN**:

- `cat` (unbounded)
- `find` without `-name` (whole-tree)
- `git diff` without `--stat` or path filter
- `git log` without `-n N`
- `node ... ` / `python ...` that prints arbitrary computed output

Verifiers should answer pass/fail in ≤ 3 lines of stdout. WARN means "review before running"; if the user accepts, the run proceeds.

**Spec length check:** If `len(task.spec.splitlines()) > 80` → **WARN**:

> Task N spec is N lines. Long specs hide multiple implicit tasks. Consider splitting into 2 atomic tasks, or extracting context into a sibling `.md` file (`scope-contract.md` pattern).

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
> *  1. [d] Dispatch — spin up AI subagents to implement the validated plan, then auto-verify on completion*
> *  2. [n] No — stop here; the plan stays validated on disk to run later"*

**Present this as an interactive `AskUserQuestion` choice when available** (PRIMARY): arrow-selectable choices `Dispatch [d]` and `No [n]`. **Fallback** (tool unavailable / non-interactive / headless, OR the picker is declined, errors, returns no valid selection, or would show no visible options): print the numbered list above and accept a number or bracket letter — pass options as real `AskUserQuestion` choices (never embedded in the question text), and never end on the question with no visible choices. A choice is required either way — never auto-proceed.

On **1 / d** → immediately invoke `/renmark:orchestrate`. On **2 / n** → stop.

The recommended next step on PASS is `/renmark:orchestrate`, derived from the shared next-step contract (check-plan is a class-1 pipeline skill):

> *End by calling `renmark.lifecycle.next_steps(repo, "check-plan")` and render the
> result per `${CLAUDE_PLUGIN_ROOT}/skills/_shared/next-steps.md` (class 1 —
> Tier-0 stage routing). Present via `AskUserQuestion` (handoff-menu.md rules
> 6–9); the state-derived next command is the `(Recommended)` option. Require an
> explicit choice — never auto-proceed.*

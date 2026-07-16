---
name: check-plan
description: "Use before executing a renmark plan to validate it — typed as /renmark:check-plan. Returns PASS, WARN, or BLOCK."
disable-model-invocation: false
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

### 1–2.5. Run the deterministic engine

```bash
python -m renmark.plan_lint <plan>
```

Run this via the venv (e.g. `source .venv/bin/activate && python -m renmark.plan_lint <plan>`). Pass its bounded stdout through to the user unchanged — the format is the contract.

The engine implements exactly these 10 checks (severities are fixed — do not re-derive them):

1. Task count ≤ 15 → **BLOCK**
2. Non-empty verifier per task → **BLOCK**; `test -f` alone → **WARN**
3. No duplicate target within a `parallel_group` → **BLOCK**
4. No context_file > 200 lines with `executor: sonnet|opus|fable` (G5) → **BLOCK**
5. No transcript-leak phrase in `spec:` (7-phrase denylist, G11) → **BLOCK**
6. No dependency reference to a prior task’s full output without an artifact path (G11) → **BLOCK**
7. No unbounded `cat`/`find`/`git diff`/`git log` in verifier without a cap (G3) → **WARN**
8. Spec length ≤ 80 lines → **WARN**
9. No `executor: fable` task in a project without a declared `top_tier: fable` (.renmark/memory/routing.md ## Model tiers) → **BLOCK**
10. No `executor: fable` task with `complexity: simple` (mechanical/bulk — REQ-2 unconditional prohibition) → **BLOCK**

**Advisory (LLM only, never verdict-changing):** Judgment-only smells — naming sanity, spec quality, coherence — remain the LLM’s job and are strictly advisory; they never change the engine’s PASS/WARN/BLOCK verdict.

### 3. Report

```
check-plan: <plan-name>
Tasks: N  Executors: haiku×a codex×b sonnet×c opus×d fable×e

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
> *  1. [d] Dispatch (Recommended) — spin up AI subagents to implement the validated plan, then auto-verify on completion*
> *  2. [n] No — stop here; the plan stays validated on disk to run later"*

Present through `renmark.interaction.build_selector`, with `Dispatch [d]` as the
sole recommendation at index 0. Use the returned host selector when available;
otherwise print its recommended-first fallback. A choice is required either way.

On **1 / d** → immediately invoke `/renmark:orchestrate`. On **2 / n** → stop.

The recommended next step on PASS is `/renmark:orchestrate`, derived from the shared next-step contract (check-plan is a class-1 pipeline skill):

> *End by calling `renmark.lifecycle.next_steps(repo, "check-plan")` and render the
> result per `${CLAUDE_PLUGIN_ROOT}/skills/.shared/next-steps.md` (class 1 —
> Tier-0 stage routing). Present via `AskUserQuestion` (handoff-menu.md rules
> 6–9); the state-derived next command is the `(Recommended)` option. Require an
> explicit choice — never auto-proceed.*

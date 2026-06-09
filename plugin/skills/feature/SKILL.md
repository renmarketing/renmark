---
name: feature
description: Use to start a new feature or significant change with branch isolation — typed as /renmark:feature or phrases like "new feature X", "build X", "start feature". Creates a branch then runs the full pipeline: plan → check-plan → orchestrate → verify → finish.
---

# feature

## Overview

Full feature pipeline with branch isolation. Creates a feature branch, runs the renmark wizard end-to-end, and offers PR or merge on finish.

**Pipeline (proportional — cost tracks size/risk):**
```
/renmark:plan            (Scope Contract + decomposition)
  → /renmark:check-plan  (auto — validates before tokens flow; ALWAYS)
  → sizing.classify_plan(tasks) → tier {lite | standard | full}   (deterministic, surfaced in cost preview)
  → lite lane:           orchestrate → verify (ALWAYS) → proportional codereview (cheap /review + escalate) → land on main
     standard / full:    branch → orchestrate → verify (ALWAYS) → full codex codereview → finish (PR / merge / release)
```

The **lane decision is made AFTER `plan-validated`** — classification needs the
validated task list. Overrides are resolved by `sizing.resolve_override` (NOT a
blind override): `--full` always escalates to full, but `--lite` only narrows a
`standard` classification — it is **refused** when the change carries hard / core /
full signals (lite must never skip the full review on a risky change).
**plan validation and goal-backward verify (REQ-7) run on every tier, no exceptions.**

## When to Use

- New functionality that warrants isolation before merging
- Significant refactors or migrations
- Any work where you want a reviewable PR

**Use plain `/renmark:plan` + `/renmark:orchestrate` on main instead for:**
- Small edits, config changes, single-file fixes

**Invocation & overrides:**
- `/renmark:feature <name>` — classify by heuristic (default; see Step 3.5).
- `/renmark:feature <name> --full` — force the full pipeline (branch → codex review → PR/release). `--full` ALWAYS wins (escalation is the safe direction).
- `/renmark:feature <name> --lite` — REQUEST the **lite lane** (land on main, cheap review, no PR/codex/release). `--lite` only narrows a `standard` classification to lite; it is **REFUSED** when the classifier returns `full` or hard / core / full signals are present (surface a clear one-line message and keep the classified tier).
- Override resolution is deterministic via `sizing.resolve_override(classified_tier, override)`: `--full` always escalates to full; `--lite` downgrades to lite ONLY when `classified_tier == 'standard'`. Even with an override,
  **plan validation and goal-backward verify (REQ-7) still run** — those never skip.

## Steps

**Step 0 — Context check.** Call `lifecycle.skill_preamble(repo, 'feature')`. If it returns a non-None hint, surface as a one-line note.

**Router contract reminder:** `/renmark:feature` is a **workflow router**, not a reasoning agent. It must NOT plan, code, test, review, or document. Its only actions are: read `lifecycle.json` → determine next stage → dispatch the right stage skill → receive a bounded summary → update `lifecycle.json` → recommend next action. See the plan's Section 3 ("/renmark:feature is a router, not an engineer") for the MUST/MUST NOT list.

### 1. Create branch

```bash
SLUG=$(echo "<feature name>" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/-/g' | sed 's/--*/-/g')
git checkout -b feature/$SLUG
```

Confirm branch name with user before continuing.

**Write the feature identity to `lifecycle.json` (required — do NOT skip).** Immediately after the branch exists (whether newly created or switched to), persist this feature's identity so every downstream stage writes against the correct `feature`/`branch` instead of inheriting the previous feature's:

```python
from renmark import lifecycle
lifecycle.begin_feature(repo, feature="<slug>", branch="feature/<slug>")
```

`begin_feature` resets lifecycle to a clean `init` state for the new feature (empty `stages_completed`, empty `artifacts`). Skipping this is the identity bug that left `/renmark:finish`'s ADR and lifecycle pointing at the *prior* feature — the router owns identity; stage skills only advance `stage`.

### 2. PRD Alignment

Before planning, dispatch the PRD alignment subagent per
`plugin/skills/_shared/prd-alignment.md` (the single source of truth — do NOT inline its logic here).

*Dispatch the PRD alignment subagent from
`${CLAUDE_PLUGIN_ROOT}/skills/_shared/prd-alignment.md`: Agent tool call,
passing ONLY `feature_description` + `file_scope`. Receive ONLY the ≤5-line
verdict summary. Do NOT read PRD.md in the orchestrator context.*

The router MUST NOT read the `PRD.md` body. It passes only the feature description
and file scope to the subagent and receives only the bounded `verdict`.

**Route on verdict:**

| Verdict | Action |
|---|---|
| `aligned` | Proceed to Plan (Step 3). |
| `drift` | Route the `proposed_prd_addition` into `/renmark:prd` update mode (human-gated). **Pause the feature plan until the human approves or rejects the PRD addition.** Do not proceed to planning while `drift` is unresolved. |

`prd-alignment` is the contract key for this gate — see the shared file for the
full bounded-return format and examples.

### 3. Plan

Invoke `/renmark:plan <description or spec-path>`. The plan skill runs the Scope Contract discovery (Q1–Q3), writes CHANGELOG + stack.md, then decomposes into tasks.

**Plan runs in validation-only mode here (single-gate contract).** Because `feature`
is the wrapper, `plan` **suppresses its own Step 8b dispatch gate**: it stops after
auto-validation at stage `plan-validated` and returns control to this router. `feature`
owns the **one** dispatch approval (Step 4). This is the mirror of the contract documented
in `plan/SKILL.md` §8b — there must never be two dispatch gates, and orchestrate must
never be reached without an explicit human approval.

### 3.5. Size-tier classification (lane decision)

After `plan` reaches `plan-validated` (Step 3), classify the validated task list to
pick the lane. This is a **deterministic, zero-LLM** step — the router calls the
classifier, it does not reason about size itself:

```python
from renmark import sizing
tier = sizing.classify_plan(tasks)   # → 'lite' | 'standard' | 'full'
```

`sizing.classify_plan` is pure and never raises — it **degrades to `'standard'`
(the safe middle) on any uncertainty**, so the router never falls into `lite` by
accident.

**Override resolution (deterministic, safety-floored — call `sizing.resolve_override`):**

The router does NOT apply overrides by hand. It resolves them through the
classifier so `--lite` can never bypass the safety floor:

```python
from renmark import sizing
classified = sizing.classify_plan(tasks)            # 'lite' | 'standard' | 'full'
tier = sizing.resolve_override(classified, override)  # override ∈ {None,'lite','full'}
```

| Invocation | `classified` | Effective `tier` | Note |
|---|---|---|---|
| `--full` | any | `full` | always escalates — the safe direction |
| `--lite` | `standard` | `lite` | the ONLY case `--lite` narrows the lane |
| `--lite` | `full` | `full` | **REFUSED** — surface a one-line message; lite can't skip the full review on a risky change |
| `--lite` | `lite` | `lite` | no-op |
| neither | (any) | `classified` | heuristic stands |

**When `--lite` is refused** (i.e. you passed `override='lite'` but
`resolve_override` returned a non-`lite` tier), surface a clear one-line note,
e.g. *"`--lite` refused: change carries full/core/hard signals — running the
full lane to keep the full review."* Do NOT silently downgrade.

**Lane routing by tier:**

| Tier | Lane |
|---|---|
| `lite` | **Lite lane** (Step 4 → 6, lands on `main`) — orchestrate → verify (ALWAYS) → proportional codereview (cheap `/review`, escalate on demand) → land on `main`. No feature branch ceremony, no codex review, no PR, no release. |
| `standard` / `full` | **Full lane** (unchanged) — branch → orchestrate → verify → full codex codereview → finish (PR / merge / release). |

**Mechanism note (behavior is what matters; leave exact mechanics to execution):**
the lane decision happens **after `plan-validated`**, so the branch-vs-main choice is
made here, not at Step 1. Lite work **lands on `main`** — either by classifying before
creating the branch, or by branching then fast-forwarding `main` on lite finish. Per the
**single-branch-rule**, small changes land directly on `main` without a PR. Standard/full
keep the existing branch → PR/merge → (optional) release flow untouched.

**Always run regardless of tier:** plan validation (Step 3) and goal-backward verify
(Step 6, REQ-7). The lite lane shrinks the *finish* ceremony and the *review* cost — it
never skips validation or verification.

### 4. Execute

**Dispatch gate (the single approval point for the wrapper flow).** Since `plan`
suppressed its gate in Step 3, `feature` owns the dispatch approval before any tokens
flow. **Surface the classified `tier` (Step 3.5), which stages will run for that tier,
and the est-token band** as part of this cost preview — never blind, never silent — then
require an explicit human approval to proceed (orchestrate's own pre-flight cost-preview
`Proceed? [y/N]` satisfies this when you invoke it — do not bypass it). Never
auto-dispatch silently. This remains the **single** dispatch gate — adding the tier
preview does not add a second gate.

On approval, invoke `/renmark:orchestrate` with the produced plan. Orchestrate runs
check-plan in pre-flight, executes waves, re-verifies on completion, and shows the
hand-off menu. If the user declines, stop with the validated plan on disk.

### 5. Blueprint Update

After orchestrate completes (whether or not all tasks pass), invoke `/renmark:blueprint`
as a non-blocking touchpoint to keep the living blueprint current.

**This is an artifact touchpoint, NOT a new lifecycle stage.** It does not gate
the build — the pipeline continues regardless of the blueprint result.

*Dispatch as a non-blocking subagent call (Agent tool, bounded return):*

- The subagent simply invokes `/renmark:blueprint` as-is. Blueprint reads
  architecture exclusively from `.renmark/memory/project-map.md` (and `stack.md`);
  do NOT feed it diff content, touched-file lists, or wave summaries — those are
  never architecture inputs.
- The fact that a feature shipped may be used ONLY as a signal for whether it is
  worth re-running blueprint (e.g. skip if no files were changed). It must not
  be used to drive architecture updates.
- It MUST NOT fabricate architecture. If `project-map.md` is missing or stale
  (older than the current feature branch), route to `/renmark:init` first to
  regenerate the map, then re-invoke blueprint.
- The subagent returns ONLY: `updated_artifacts` (list of paths written) +
  `skipped_reason` (if nothing was updated) ≤ 3 lines total. The orchestrator
  does NOT read the blueprint body — only the bounded return.

**Route on result:**

| Result | Action |
|---|---|
| `updated` | Continue to Verify + Finish (Step 6). |
| `skipped` (project-map stale / missing) | Dispatch `/renmark:init`, then re-invoke blueprint, then continue. |
| `skipped` (nothing to reconcile) | Continue to Step 6 — no action needed. |

### 6. Verify + Finish

**Verify runs on every tier (REQ-7) — never skipped.**

After orchestrate completes a clean run it **auto-invokes** `/renmark:verify` (goal-backward
smoke tests — ALWAYS, all tiers; there is no menu choice for this since v0.3.3).
- Then route the **review + finish** by the tier resolved in Step 3.5:

**Lite lane (`tier == lite`):**
- **Proportional codereview** → `/renmark:codereview` runs its cheap built-in `/review`
  by default and offers a one-keystroke escalate to full codex. Defer the detail to the
  codereview skill — the router only routes; it does not review. Never silently skipped.
- **Land on `main`** → no PR, no codex review by default, no release ceremony, per the
  **single-branch-rule**. `/renmark:finish` closes the work onto `main`.

**Standard / full lane (unchanged):**
- Full codex codereview → **[f] Finish** → `/renmark:finish` shows branch summary and
  offers PR / merge / release. The branch created in step 1 is the source branch for the PR.

**Next-step hand-off (pipeline skill, class 1):**

> *End by calling `renmark.lifecycle.next_steps(repo, "feature")` and render the
> result per `${CLAUDE_PLUGIN_ROOT}/skills/_shared/next-steps.md` (class 1 —
> Tier-0 stage routing). Present via `AskUserQuestion` (handoff-menu.md rules
> 6–9); the state-derived next command is the `(Recommended)` option. Require an
> explicit choice — never auto-proceed.*

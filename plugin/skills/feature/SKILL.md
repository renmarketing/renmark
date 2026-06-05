---
name: feature
description: Use to start a new feature or significant change with branch isolation — typed as /renmark:feature or phrases like "new feature X", "build X", "start feature". Creates a branch then runs the full pipeline: plan → check-plan → orchestrate → verify → finish.
---

# feature

## Overview

Full feature pipeline with branch isolation. Creates a feature branch, runs the renmark wizard end-to-end, and offers PR or merge on finish.

**Pipeline:**
```
git checkout -b feature/<slug>
  → /renmark:plan          (Scope Contract + decomposition)
  → /renmark:check-plan    (auto — validates before tokens flow)
  → /renmark:orchestrate   (wave execution + commits)
  → /renmark:verify        (goal-backward smoke test)
  → /renmark:finish        (PR / merge to main)
```

## When to Use

- New functionality that warrants isolation before merging
- Significant refactors or migrations
- Any work where you want a reviewable PR

**Use plain `/renmark:plan` + `/renmark:orchestrate` on main instead for:**
- Small edits, config changes, single-file fixes

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

### 4. Execute

Invoke `/renmark:orchestrate` with the produced plan. Orchestrate runs check-plan in pre-flight, executes waves, re-verifies on completion, and shows the hand-off menu.

### 5. Blueprint Update

After orchestrate completes (whether or not all tasks pass), invoke `/renmark:blueprint`
to reconcile the living blueprint with this feature's delta.

**This is an artifact touchpoint, NOT a new lifecycle stage.** It does not gate
the build — the pipeline continues regardless of the blueprint result.

*Dispatch as a non-blocking subagent call (Agent tool, bounded return):*

- Subagent reads `SCHEMATIC.md` and `PROTOTYPE.html` (if present) and reconciles
  them against the feature's touched files and wave summaries.
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

From orchestrate's menu:
- Choose **[v] Verify** → `/renmark:verify` runs goal-backward smoke tests
- Then **[f] Finish** → `/renmark:finish` shows branch summary and offers PR or merge

The branch created in step 1 is the source branch for the PR.

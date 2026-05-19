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

**Step 0 — Context check.** Call `state.context_budget_check(repo, 'feature', 'build')`. If `'clear'` returned, surface as a one-line note. Then call `state.record_skill_invocation(repo, 'feature', 'build')`.

**Router contract reminder:** `/renmark:feature` is a **workflow router**, not a reasoning agent. It must NOT plan, code, test, review, or document. Its only actions are: read `lifecycle.json` → determine next stage → dispatch the right stage skill → receive a bounded summary → update `lifecycle.json` → recommend next action. See the plan's Section 3 ("/renmark:feature is a router, not an engineer") for the MUST/MUST NOT list.

### 1. Create branch

```bash
SLUG=$(echo "<feature name>" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/-/g' | sed 's/--*/-/g')
git checkout -b feature/$SLUG
```

Confirm branch name with user before continuing.

### 2. Plan

Invoke `/renmark:plan <description or spec-path>`. The plan skill runs the Scope Contract discovery (Q1–Q3), writes CHANGELOG + stack.md, then decomposes into tasks.

### 3. Execute

Invoke `/renmark:orchestrate` with the produced plan. Orchestrate runs check-plan in pre-flight, executes waves, re-verifies on completion, and shows the hand-off menu.

### 4. Verify + Finish

From orchestrate's menu:
- Choose **[v] Verify** → `/renmark:verify` runs goal-backward smoke tests
- Then **[f] Finish** → `/renmark:finish` shows branch summary and offers PR or merge

The branch created in step 1 is the source branch for the PR.

---
name: resume
description: Use after `/clear` or `/compact`, or at the start of a fresh session, to discover where the in-flight renmark feature stopped. Reads `.renmark/state/lifecycle.json` and prints the recommended next command. Zero LLM calls — pure file IO. This is the cold-start recovery surface that makes "AI workflows survive context death."
---

# resume

## Overview

`/renmark:resume` is the **cold-start recovery command**. It exists because conversation history is not authoritative state (G2) — when context is cleared, the renmark workflow continues from `.renmark/state/lifecycle.json`, not from chat reasoning.

Cost: **one file read, zero LLM calls.** Output: a single-line recommendation (≤ 5 lines if approval is pending) of what to do next.

## When to Use

- Immediately after `/clear` to find out where the current feature left off
- At the start of a new session in any project that has used renmark before
- When you've been away from a project and don't remember what stage you're in
- Inside `/renmark:feature` after each stage handoff (the router calls it implicitly)

**Do NOT use:**
- To make decisions — `/renmark:resume` only reports state, never modifies it
- To validate work — for that, run the verifier (`/renmark:verify`)
- As a replacement for `/renmark:roadmap` (which shows project-wide status across releases; resume shows only the current in-flight feature)

## Steps

### 0. Context check

Call `state.context_budget_check(repo, 'resume', 'meta')`. Resume is a `meta` domain skill — it rarely triggers a cross-domain prompt because it touches no work. If it does suggest `/clear`, ignore: resume is cheap and should always run.

Then call `state.record_skill_invocation(repo, 'resume', 'meta')`.

### 1. Read lifecycle state

```bash
python3 -c "
from pathlib import Path
from renmark import lifecycle
state = lifecycle.read_lifecycle(Path('.'))
if state is None:
    print('No in-flight feature.')
    print('Recommended: /renmark:start  (begin a new feature)')
else:
    print(f'Feature: {state.feature}')
    print(f'Branch:  {state.branch}')
    print(f'Stage:   {state.stage}')
    if state.stages_completed:
        print(f'Done:    {\", \".join(state.stages_completed)}')
    if state.human_review_required and not state.human_review_completed:
        print(f'⚠  Awaiting human approval for: {state.human_review_for}')
        print(f'Recommended: /renmark:approve')
    else:
        print(f'Recommended: {state.next_recommended}')
"
```

### 2. Surface pending approval gates

If `human_review_required` is true and `human_review_completed` is false, the user MUST be told about the pending gate before any other recommendation. The next action is always `/renmark:approve` until the gate is cleared.

### 3. Print the recommendation

Surface ≤ 5 lines total. The orchestrator's output for `/renmark:resume` MUST stay within G3 bounds — this is a one-glance status check, not a report.

Format:

```
Feature: <feature-name>
Stage:   <stage>
Done:    <comma-separated completed stages>
Next:    <recommended command>
```

If pending approval:

```
Feature: <feature-name>
Stage:   <stage>
⚠  Approval pending: <human_review_for>
Next:    /renmark:approve
```

If no feature in flight:

```
No feature in flight.
Next: /renmark:start
```

### 4. No state changes

`/renmark:resume` writes nothing except the skill-invocation marker (Step 0). It does not mutate `lifecycle.json`, does not advance any stage, does not start any subprocess. The user reads the output and decides what to do.

## Hand off (wizard step)

Resume is a reporting skill — there is no automatic handoff. The user reads the recommendation and invokes it themselves. This is intentional: the human is the final merge authority (principle #7), and any automatic chaining from resume would undermine that.

## Governance compliance

| # | Rule | How this skill complies |
|---|---|---|
| G2 | Canonical state | Reads lifecycle.json; doesn't depend on conversation. |
| G3 | Summary boundary | Output capped at 5 lines. |
| G5 | Executor isolation | N/A — no heavy cognition; pure file IO. |
| G6 | Artifact governance | N/A — emits no artifact. |
| G7 | Compact semantics | Resume IS the compact-safety mechanism: it works the moment after `/compact` because lifecycle.json survived. |
| G8 | Compounding verification | N/A — not a verifier. |
| G9 | Failure transparency | If lifecycle.json is corrupt or missing, reports cleanly and recommends `/renmark:start`. |
| G10 | Workflow recovery | This skill IS the recovery surface — reads pipeline state to recommend `/renmark:orchestrate --resume` if a partial wave is in flight. |
| G11 | Task isolation | N/A — dispatches nothing. |
| G12 | Lifecycle persistence | Reads lifecycle.json; doesn't write workflow state. |

---
name: loop
description: Use to run a bounded, verified, resumable agentic loop — `/renmark:loop "<goal>"` or "keep iterating until X works", "loop until the goal is met". One upfront approval gate (goal + verify cmd + budget + max-iterations + cost preview), then autonomously cycles orchestrate → verify → decide, committing each passing iteration to the branch, until a terminal status (done / budget-hit / max-iter / awaiting-approval / stalled). Never merges, releases, PRs, or makes destructive changes on its own (REQ-12) — it stops at the gate and hands off to /renmark:finish. Reads only verify metadata + the spend ledger + bounded summaries — never code or diffs.
---

# loop

## Overview

`/renmark:loop` is renmark's bounded execution engine: a **single upfront approval, then
autonomous** loop that wraps `orchestrate → verify → decide` and runs until it reaches a
terminal state. It honors the single-dispatch-gate doctrine — there is **exactly one
approval prompt** for the whole run, never a per-iteration prompt.

The deterministic state machine lives in `renmark/loop.py` (`LoopState`, `parse_budget`,
`build_decision`, `stop_reason`, `read_loop`/`write_loop`, `refresh_spent`). **This skill
DRIVES the loop; the module OWNS the state.** The driver invokes orchestrate/verify and
builds the decision; the module persists `loop.json`, parses the budget, and evaluates
stop conditions.

**Context hygiene (REQ-5/11):** the loop reads ONLY verify metadata (`.verification.md`),
the spend ledger (`usage.jsonl` via `usage_by_run_id`), and bounded per-iteration
summaries. It NEVER reads generated code, diffs, or artifact bodies into conversation.

> Vibe coders never type `/renmark:loop` — `/renmark:start` routes them into Loop Mode
> under the hood and never says "loop." This is the expert surface.

## When to Use

- The user wants something built and iterated on **until it verifiably works**, within a
  cost/iteration ceiling, without babysitting each step.
- "Keep going until the tests pass", "loop until the goal is met", "iterate autonomously".

**Do NOT use:**
- For a single well-scoped task → `/renmark:orchestrate` once.
- To brainstorm/design → `/renmark:brainstorm`.
- To merge/release/PR → that's `/renmark:finish` (the loop stops *before* those, by design).

## Arguments

| Flag | Default | Meaning |
|---|---|---|
| `--goal "<text>"` (or positional) | required | The goal the loop verifies backward against. |
| `--verify <cmd>` | (goal-backward only) | A shell verifier run alongside verify's goal-backward smoke. |
| `--budget <tokens\|$amount>` | **300000 tokens** (`DEFAULT_BUDGET_TOKENS`) | Spend ceiling. `parse_budget` accepts a token count (`300000`, `300_000`, `300,000`) OR a `$` amount (`$3.00`) — both resolve to tokens, the measurable unit, with a `$` estimate shown. |
| `--max-iterations <n>` | **5** (`DEFAULT_MAX_ITERATIONS`) | Hard iteration ceiling. |

Parse the budget once via `renmark.loop.parse_budget(value)` → `(budget_tokens, usd_estimate)`.
A blank / unparseable / non-positive value degrades to the bounded default — never unbounded.

## Steps

**Step 0 — Context check.** Call `lifecycle.skill_preamble(repo, 'loop')`. If it returns a
non-None hint, surface it as a one-line note. Also call `read_loop(repo, loop_id)` for any
in-flight loop — if one is `running` or `awaiting-approval`, surface the resume command and
iteration / budget-remaining instead of starting fresh.

### 1. Single upfront approval gate

This is the **ONLY approval during the run.** Resolve the budget with `parse_budget`, then
present a cost preview and ask once:

```
Loop Mode — about to run autonomously to a terminal state.
  Goal:           <goal>
  Verify cmd:     <--verify cmd, or "goal-backward smoke only">
  Budget:         <budget_tokens> tokens  (~<usd_estimate>)
  Max iterations: <n>
  Cost preview:   up to <n> × orchestrate+verify cycles, capped at the budget above
Proceed? [y/N]
```

If declined, stop — write nothing. **There are NO further prompts until a terminal status**
(single-dispatch-gate doctrine).

### 2. Initialize the loop

```python
from renmark import loop
lid = loop.loop_id(date, slug)                 # caller passes date/slug — deterministic
state = loop.LoopState(
    goal=<goal>, verify_cmd=<verify_cmd>,
    budget_tokens=<budget_tokens>, budget_usd_estimate=<usd_estimate>,
    run_id=<run_id>, max_iterations=<n>, iteration=0, status="running",
)
loop.write_loop(repo, lid, state)              # creates .renmark/loops/<id>/, status=running
```

Also write sibling `goal.md` for provenance. `loop.json` is the runtime sibling of
`pipeline.json` — NOT `lifecycle.json` (G12 / 1KB guard).

### 3. Drive the loop (autonomous, no prompts)

Per-iteration order is **check budget+max-iter → dispatch → verify → refresh_spent → decide**.
The budget gate is a **PREFLIGHT** — it runs BEFORE the orchestrate dispatch so an approved
budget is never overshot by a full cycle's spend (REQ-9).

While `stop_reason(state)` is `None`:

0. **Budget preflight (BEFORE dispatch).** Check the budget AND the iteration ceiling
   *before* spending anything this iteration:
   ```python
   if not loop.should_continue_budget(state):   # budget_remaining < BUDGET_FLOOR_TOKENS
       state.status = "budget-hit"
       loop.write_loop(repo, lid, state)
       break                                     # STOP before dispatch — never overshoot
   if stop_reason(state) is not None:            # max-iter / awaiting-approval / terminal
       break
   ```
   This is the load-bearing fix for REQ-9: the budget is gated *before* orchestrate, not
   after `refresh_spent`. Stopping after spending would overshoot by one full iteration.
1. **Orchestrate** — invoke `/renmark:orchestrate` on the current plan / `next_action`. It
   plans + dispatches, **commits passing work to the feature branch**, and ledgers spend
   under the loop's `run_id`.
2. **Verify** — invoke `/renmark:verify` (goal-backward + the `--verify` cmd). It writes a
   `.verification.md` with machine-readable metadata.
3. **refresh_spent** — recompute measured spend from the ledger:
   ```python
   state = loop.refresh_spent(repo, state)     # spent_tokens from usage.jsonl (real spend)
   ```
4. **Decide** — read ONLY the verify metadata (`renmark.summary.read_metadata`) and the
   ledger spend delta; build the decision:
   ```python
   decision = loop.build_decision(verification_meta, spent_delta)
   ```
   **The driver supplies/refines `next_action`.** On a failed verify, `build_decision`
   DERIVES a best-effort `next_action` from the verification `summary_lines` (the
   `failed: <names>` line and/or the `run /renmark:debug ... symptom: "<...>"` line →
   `address: <symptom>`). A failing verify with an actionable symptom **CONTINUES** the
   loop (within budget/max-iter) — it is NOT stalled. The driver reads that bounded
   failure and may further refine `next_action` for the next iteration's orchestrate.
5. **Record** — write `iterations/NNN-summary.md` (bounded) and update `loop.json`:
   ```python
   state.iteration += 1
   if decision["goal_reached"]:
       state.status = "done"
   elif not decision["next_action"].strip():
       # 'stalled' ONLY when there is genuinely NO actionable next step — e.g. the verify
       # reported NO failed behaviors (failed: none) and the goal was not reached. A failed
       # verify that DID yield an actionable symptom has a non-blank next_action and so
       # does NOT stall — it iterates. Never set 'stalled' on every failed verify.
       state.status = "stalled"
   loop.write_loop(repo, lid, state)           # written before the iteration returns → resumable
   ```
6. **Check** — `stop_reason(state)`. If non-None, the loop is terminal; break.
7. **Progress line** — emit **ONE bounded line** per iteration (≤ summary cap), e.g.
   `iter 2/5 · verify FAIL · spent 80k/300k (~$0.80) · next: add null-guard`.
   **No per-iteration prompt.**

The budget ceiling is preflighted before each dispatch AND checked first among `stop_reason`'s
live stop conditions — an approved budget is never exceeded; raising it requires a *new*
upfront approval.

### 4. Terminal status → bounded verdict → hand off

Stop conditions (all terminal):

| `status` | Trigger |
|---|---|
| `done` | verify PASS — goal verified backward |
| `budget-hit` | ledger spend ≥ approved budget |
| `max-iter` | iteration ≥ `--max-iterations` |
| `awaiting-approval` | a REQ-12 gate (merge/release/PR/destructive/budget-escalation) is pending |
| `stalled` | verify reported NO failed behaviors yet goal not reached, OR a failed verify yielded no actionable symptom (blank derived `next_action`) — NOT set on a failed verify that produced an actionable symptom (that one iterates) |

Report a bounded ≤5-line verdict (status, iterations used, spend vs budget, last evidence),
then hand off to `/renmark:finish` — which carries the **REQ-12 merge/release approval gate**.

### REQ-12 — autonomous within bounds, gated at the edge

The loop **commits each passing iteration** to the feature branch (safe / revertable) but
**NEVER merges, releases, opens a PR, escalates the budget, or makes destructive changes
autonomously.** When such a step would be required it sets `pending_step`, reaches
`awaiting-approval`, and stops. AI may generate and commit code; the human owns merges and
releases. Only `/renmark:approve` flips the human-approval bit.

## Resumability (REQ-10)

`loop.json` is written before each iteration returns, so a crash / `/clear` / `/compact` /
new session recovers the iteration index, remaining budget, and pending step. After a
clear, `/renmark:resume` detects a `running` / `awaiting-approval` `loop.json` and prints
the resume command + iteration / budget-remaining (zero LLM calls). The loop driver never
raises into chat — a ledger/verify read failure degrades to a clean STOP with a status, not
a crash.

## Governance compliance

Upholds G3/G5/G11/G12 and REQ-5/9/10/11/12. The load-bearing invariants are enforced in
`renmark/loop.py`: stop logic degrades toward stopping (never unbounded), `build_decision`
consumes only metadata + the ledger (never code/diffs), `refresh_spent` enforces the budget
against measured spend, and `loop.json` carries runtime state only (not `lifecycle.json`).

## Next step

*End by calling `renmark.lifecycle.next_steps(repo, "loop")` and render the
result per `${CLAUDE_PLUGIN_ROOT}/skills/_shared/next-steps.md` (class 1 —
Tier-0 stage routing). Present via `AskUserQuestion` (handoff-menu.md rules
6–9); the state-derived next command (`/renmark:finish` at a terminal loop) is
the `(Recommended)` option. Require an explicit choice — never auto-proceed.*

Do not paste the rendering rules — cite the file.

*Mirror any rule changes in `AGENTS.md` in the same commit.*

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

Call `lifecycle.skill_preamble(repo, 'resume')`. Resume is a `meta` domain skill — it rarely triggers a cross-domain prompt because it touches no work. If it does return a hint, ignore: resume is cheap and should always run.

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

### 1.5 Validate artifact freshness

Cross-check that every artifact referenced in lifecycle state still exists and is current. Still **zero LLM calls** — one extra file read per artifact (frontmatter only).

```bash
python3 -c "
from pathlib import Path
from renmark.lifecycle import validate_artifact_refs
issues = validate_artifact_refs(Path('.'))
for i in issues:
    icon = '❌ BLOCK' if i['severity'] == 'BLOCK' else '⚠ WARN'
    print(f\"{icon} {i['kind']}: {i['artifact']} @ {i['path']} — {i['detail']}\")
if any(i['severity'] == 'BLOCK' for i in issues):
    raise SystemExit(2)
"
```

Each WARN prints as `⚠ <kind>: <artifact> @ <path>`; each BLOCK prints as `❌ BLOCK <kind>: <artifact> @ <path>`. On any BLOCK the skill exits non-zero (code 2) so the user investigates before continuing.

### 1.75 Surface any in-flight loop

A `/renmark:loop` run persists its runtime state to `.renmark/loops/<id>/loop.json`
(the outer-loop sibling of `pipeline.json` — never `lifecycle.json`). On resume,
if any loop directory holds a `loop.json` whose `status` is `running` or
`awaiting-approval`, surface it so a `/clear` mid-loop is recoverable. Still
**zero LLM calls** — pure file IO: glob the loop dirs, read each `loop.json` via
`renmark.loop.read_loop`, no source reads, no analysis.

```bash
python3 -c "
from pathlib import Path
from renmark.loop import read_loop, budget_remaining, estimate_usd, LOOPS_SUBDIR
from renmark.state import RENMARK_DIR_NAME
loops_root = Path('.') / RENMARK_DIR_NAME / LOOPS_SUBDIR
for d in sorted(loops_root.glob('loop-*')) if loops_root.is_dir() else []:
    st = read_loop('.', d.name)
    if st is None or st.status not in ('running', 'awaiting-approval'):
        continue
    remaining = budget_remaining(st)
    print(f'⟳  Loop in flight: {d.name}  [{st.status}]')
    print(f'   Iteration: {st.iteration}/{st.max_iterations}')
    print(f'   Budget:    {remaining} tokens left ({estimate_usd(remaining)} of {estimate_usd(st.budget_tokens)})')
    if st.pending_step:
        print(f'   Pending:   {st.pending_step}')
    print(f'   Resume:    /renmark:loop --resume {d.name}')
"
```

Output, when a loop is in flight (one block per active loop, ≤5 lines each):

```
⟳  Loop in flight: <loop-id>  [running|awaiting-approval]
   Iteration: <iteration>/<max_iterations>
   Budget:    <remaining> tokens left (<$remaining> of <$budget>)
   Pending:   <pending_step>            # only if a REQ-12 gate is awaiting approval
   Resume:    /renmark:loop --resume <loop-id>
```

If **no** loop is in flight, this step prints nothing and resume behaves exactly
as it does today — the lifecycle recovery below is unchanged. A loop in
`awaiting-approval` is a pending gate: the lifecycle path (Step 2) still drives
the `/renmark:approve` recommendation; this block only adds the `--resume` hint
so the user knows which loop to re-enter after approving.

### 1.8 Surface usage-limit paused runs

A `/renmark:loop` or continuous run may be paused by a local usage-limit guard.
When `renmark.state.read_pause(repo)` returns a `PauseState` with
`pause_kind == "usage_limit"`, surface it so the user knows the run is
**persisted and resumable**. Still **zero LLM calls** — one extra file read
(`read_pause` reads a single file).

```bash
python3 -c "
from pathlib import Path
from renmark.state import read_pause
ps = read_pause(Path('.'))
if ps is not None and ps.pause_kind == 'usage_limit':
    resume_hint = str(ps.resume_after) if ps.resume_after else 'unknown'
    feature_hint = f'  Feature:  {ps.feature}' if ps.feature else ''
    loop_hint = f'  Loop:     {ps.loop_id}  (iteration {ps.iteration}/{ps.max_iterations})' if ps.loop_id else ''
    print('⏸  Loop/run paused because a usage limit was reached.')
    if feature_hint:
        print(feature_hint)
    if loop_hint:
        print(loop_hint)
    print(f'   Suggested resume time: {resume_hint}')
    print('   Observed local usage only. Provider-side account limits may differ.')
    print('   You can resume now (state is persisted) or wait until the suggested time.')
    print()
    print('   Resume now: /renmark:loop --resume  (or re-invoke the paused command)')
"
```

Output when a usage-limit pause is active (≤8 lines, then blank line):

```
⏸  Loop/run paused because a usage limit was reached.
   Feature:  <feature>          # only if available
   Loop:     <loop-id>  (iteration <N>/<max>)   # only if available
   Suggested resume time: <resume_after>
   Observed local usage only. Provider-side account limits may differ.
   You can resume now (state is persisted) or wait until the suggested time.

   Resume now: /renmark:loop --resume  (or re-invoke the paused command)
```

If `read_pause` returns `None` or `pause_kind != "usage_limit"`, this step
prints nothing. The existing lifecycle-based resume (Steps 1–1.75 and Step 2
onward) is **unchanged** — this is an additive surfacing branch only.

### 1.85 Surface any in-flight staged program

A `/renmark:roadmap` run or orchestrated stage update persists its state to
`.renmark/state/program.json`. On resume, if a program exists AND is not fully
done, surface it so the user knows a multi-stage build is in flight. Still
**zero LLM calls** — pure file IO: `renmark.program.read_program`, no source
reads, no analysis.

```bash
python3 -c "
from pathlib import Path
from renmark.program import read_program, position
prog = read_program(Path('.'))
if prog is not None:
    # Check if any stage is not done (else program is complete).
    has_work = any(s.status != 'done' for s in prog.stages)
    if has_work:
        pos = position(prog)
        print(f'⟳  Program in flight: {prog.feature}  [{prog.mode}]')
        print(f'   {pos}')
        print(f'   Resume: /renmark:roadmap  (view/continue)')
"
```

Output when a program is in flight with work remaining (≤3 lines):

```
⟳  Program in flight: <feature>  [<mode>]
   Stage <N>/<total> · task <M>/<total> done · current: <stage-title>
   Resume: /renmark:roadmap  (view/continue)
```

If `read_program` returns `None` or all stages are done, this step prints
nothing. The existing lifecycle-based resume (Steps 1–1.75 and Step 2 onward)
is **unchanged** — this is an additive surfacing branch only.

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

Resume is a **class 3 (aux / terminal) skill** in the next-step contract. It already derives and prints the recommended next command from `lifecycle.json` (Steps 1–3) — that recommendation IS the contract's class-3 **resume-pipeline** option. For the canonical hand-off format and class definition, see — by static reference, never pasted, and **without changing resume's zero-LLM / pure-file-IO cold-start logic**:

> *Render the printed recommendation per `${CLAUDE_PLUGIN_ROOT}/skills/_shared/next-steps.md` (class 3 — resume-pipeline + 1–2 local actions). The in-flight feature's next command is `(Recommended)`. Resume is zero-LLM, so it uses the printed numbered form (handoff-menu.md rule 7), not the interactive `AskUserQuestion` picker — and never auto-proceeds.*

## Governance compliance

Resume IS the G7/G10/G12 recovery surface — it reads `lifecycle.json` (+ `pipeline.json` for `--resume` hints, + each `.renmark/loops/<id>/loop.json` for in-flight loop recovery) and recommends the next step in ≤5 lines per surface (G3), zero LLM calls, writing no workflow state. Other G-rules are N/A (it dispatches nothing and emits no artifact). See `CLAUDE.md` governance rules for definitions.

- Step 1.5 reads frontmatter from each referenced artifact (`spec`, `plan`, …) to cross-check `source_sha` + `stale_after`. Still zero LLM calls; bounded output (one line per issue, at most a few issues per healthy lifecycle).

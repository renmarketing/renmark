---
name: orchestrate
description: Use to execute a renmark plan — `/renmark:orchestrate` or "execute the plan", "build it", "run the plan". Reads the plan, dispatches each task in an isolated subagent context (G11), aggregates per-wave summaries to `.renmark/state/wave-summaries/`, commits passing tasks, updates `pipeline.json` + `lifecycle.json`. The orchestrator NEVER reads generated code into conversation — subagent transcripts, diffs, and bodies live in artifacts only.
---

# orchestrate

## Overview

Dispatches plan tasks in waves with **strict task isolation** (G11). Within a `parallel_group`, tasks run concurrently. Two dispatch paths — never mix them:

| Executor | Dispatch path | Quota consumed |
|---|---|---|
| `codex` | Bash call to `renmark-execute` (subprocess) | Codex account (OpenAI subscription) |
| `haiku`, `sonnet`, `opus` | Agent tool calls (no model override) | Claude Code account (Anthropic subscription) |

After each wave, the skill writes `.renmark/state/wave-summaries/wave-N.json` (the per-task `SubagentOutput` dicts) and commits passing tasks serially in task-index order.

**Token-isolation contract (G11):**
- Every task runs in an **isolated subagent context**.
- Each subagent receives only: task spec · required file paths · upstream artifact pointers · dependency summaries from the prior wave's `wave-summaries/` file · verifier expectations.
- Each subagent emits only the `SubagentOutput` schema (status, artifact_path, touched_files, sha, summary_lines ≤ 5, dependency_notes, token_count, completion_state, confidence, retry_count).
- The orchestrator validates the response via `renmark.dispatch.parse_subagent_response` — any extra field (transcript, diff, generated_code, reasoning) raises `IsolationViolation` and the task is FAIL.
- **The orchestrator never reads generated code into the conversation.** Period.

## When to Use

- User has a `.renmark/plans/*.plan.md` file ready and wants it executed
- After `/renmark:plan` + `/renmark:check-plan` complete (stage = `plan-validated`)
- To `--resume` a paused run

**Do NOT use:**
- Without a validated plan → `/renmark:plan` first, then `/renmark:check-plan`
- For brainstorming or design — that's `/renmark:brainstorm`
- To "look at the generated code" — that's a context-hygiene violation; route to `/renmark:debug` instead

## Steps

**Step 0 — Context check.** Call `lifecycle.skill_preamble(repo, 'orchestrate')`. If it returns a non-None hint, surface as a one-line note. Also check `state.read_pipeline_state(repo)` — if `current_phase == "orchestrate"` and `pipeline_is_resumable(repo)`, surface: *"Existing orchestrate run paused at wave N — use `--resume` to continue, or clear pipeline state to start fresh."*

### 1. Discover plan

If the user gave a path, use it. Otherwise:

```bash
ls -1t .renmark/plans/*.plan.md 2>/dev/null | head -1
```

Confirm the path with the user before continuing.

### 2. Pre-flight (free)

**Pipeline state check** — `state.read_pipeline_state(repo)`. If a prior run was paused, offer resume vs reset. New runs initialize fresh state:

```python
from renmark import state
state.write_pipeline_state(repo, current_phase="orchestrate", current_plan=<plan>,
                           wave_index=0, wave_total=<computed>, clear_tasks=True)
```

**Executor check** — `command -v codex` if the plan has any `executor: codex` tasks. If missing, stop and tell the user before running.

**Plan validation** — invoke `/renmark:check-plan <plan>` before spending tokens. If it exits 1 (BLOCK), fix the plan first. WARNs can proceed.

**Refactor safety** — if the plan has any `complexity: hard` task or the spec mentions "refactor"/"rename"/"restructure"/"migrate":
1. Confirm clean working tree (`git status`).
2. Checkpoint commit: `git -c user.name="renmark-orchestrate" -c user.email="orchestrate@renmark.local" commit --allow-empty -m "chore: checkpoint before <plan name>"`.
3. Baseline each affected verifier — if any fails now, **stop**: do not orchestrate into a broken baseline.

**Changelog check** — read the last 3 entries in `CHANGELOG.md`; flag any "Do not change" guards that overlap with the plan's target files.

**Cost preview** — `renmark-execute --dry-run <plan>` shows the task list + estimated cost. Ask: *"Proceed? [y/N]"*

### 3. Dispatch tasks in waves (G11 isolation)

For each wave in `dispatch.group_tasks_by_wave(plan.tasks)`:

**3a. Build dependency context for this wave**

Read prior wave summary if any:

```python
from renmark import state
prior = state.read_wave_summary(repo, wave_index - 1) if wave_index > 0 else None
dependency_summaries = []
if prior:
    for task_output in prior["task_outputs"]:
        if task_output.get("dependency_notes"):
            dependency_summaries.append(
                f"task {task_output['task_id']}: {task_output['dependency_notes']}"
            )
```

**The orchestrator does NOT load any wave's full output.** Only the `dependency_notes` field crosses the boundary.

**3b. Dispatch each task in this wave (parallel)**

For `executor: codex` tasks:

> **RED FLAG — never dispatch a `codex` task as an Agent call.** Codex tasks run exclusively through `renmark-execute` (a Bash subprocess). Dispatching them as Agents runs them on the parent Claude model, consuming Anthropic credits and ignoring the cost/routing intent.
>
> **RED FLAG — never merge a subagent transcript into orchestrator context.** The subagent's reasoning lives in its artifact file. The orchestrator reads only the parsed `SubagentOutput` JSON.

```bash
# Pre-create target dirs so codex doesn't scaffold extras
mkdir -p "$(dirname <target>)"
# Dispatch the whole wave (renmark-execute handles parallelism internally)
renmark-execute <plan>
```

`renmark-execute` returns one JSON line per task with the `SubagentOutput` shape. The orchestrator passes each through `dispatch.parse_subagent_response()`, which raises `IsolationViolation` on any extra field.

For `executor: haiku | sonnet | opus` tasks:

Plain `Agent` call — no `model` override. Build the subagent prompt from `dispatch.build_subagent_input(task, dependency_summaries=...)`. The Agent prompt MUST instruct the subagent:

> "Your final response MUST be valid JSON matching this shape:
> ```json
> {"status": "PASS|FAIL|SKIP", "artifact_path": "<path>",
>  "touched_files": [...], "sha": "<sha or null>",
>  "summary_lines": ["<≤5 lines>"], "dependency_notes": "<what downstream tasks need>",
>  "token_count": <int>, "completion_state": "complete|partial|failed",
>  "confidence": "low|medium|high", "retry_count": 0}
> ```
> The generated code goes in the artifact file at `<artifact_path>`, NOT in your response. Do not paste code or diffs back. If you cannot complete with the inputs provided, return `status: FAIL` with a one-line reason."

After the Agent returns, parse its response through `dispatch.parse_subagent_response()`. If it raises `IsolationViolation`, mark the task as FAIL with reason "subagent leaked forbidden fields" — do not retry.

**Ledger the call.** Immediately after parsing each successful Agent return, log the spend so `/renmark:roadmap` reports honestly:

```python
from renmark import state
from renmark.roadmap import AGENT_OVERHEAD_TOKENS
state.log_agent_call(
    repo,
    task_id=task.index,
    model=task.executor,                            # 'haiku' | 'sonnet' | 'opus'
    tokens_in=AGENT_OVERHEAD_TOKENS,                # ~10k system + spec overhead per call
    tokens_out=out.token_count,                     # SubagentOutput.token_count
    run_id=<run_id>,
)
```

Codex tasks are ledgered by `renmark-execute` directly — do NOT call `log_agent_call` for them or spend will be double-counted.

**3c. Run verifier per task**

For each task that returned PASS status, run its verifier via `summary.verifier_tail(cmd, tail_lines=3)`. Orchestrator-visible output is bounded: `exit <code> | <first 3 lines>`. If the verifier fails, downgrade the task to FAIL.

**3d. Escalation decision log**

When a task is escalated to a higher-tier executor, an ADR is appended to `.renmark/memory/decisions.md` via `memory.log_escalation_decision()`. This is automatic — handled inside `renmark/cli/_engine.py`'s `_record_escalation` when `escalated_to=` is passed. Idempotent on (title, date): re-running the same escalation on the same day does not duplicate the ADR. Best-effort: decision-logging failures do NOT break orchestrate. Pointer-only — the orchestrator never reads `decisions.md` into conversation.

### 4. Aggregate wave summary

After all tasks in the wave finish:

```python
state.write_wave_summary(repo, wave_index, task_outputs=[out.to_dict() for out in outputs])
state.write_pipeline_state(repo, wave_index=wave_index,
                           add_completed_task=..., add_failed_task=...)
```

Then commit PASSing tasks serially in task-index order. For each commit, append to `CHANGELOG.md`:

```markdown
## [YYYY-MM-DD] — <task title>
**Request:** <1-2 sentence summary>
**Built:** <what was implemented (from task's summary_lines)>
**Files changed:**
- `<target>` — <touched_files[0]>
**Do not change:**
- <invariants surfaced by the task or by check-plan>
```

Use the task's `summary_lines` and `touched_files` from `SubagentOutput` to fill these — never go read the actual file diff.

### 5. Interpret outcome

| Outcome | Action |
|---|---|
| All tasks PASS | Continue to next wave or finalize |
| Any FAIL in wave | Pause via `state.write_pause(...)`; show resume command; stop |
| `IsolationViolation` raised | Mark task FAIL; aggregate summary anyway; alert user to skill-side bug |
| Plan parse error | Route to `/renmark:plan` |

### 6. Update memory

Use `renmark.memory` helpers — do NOT hand-edit memory files directly:

```python
from renmark.memory import log_feature, append_routing, append_learning, log_bug
```

### 7. Finalize

When all waves complete cleanly:

```python
state.clear_pipeline_state(repo)
lifecycle.write_lifecycle(repo, stage="created")
```

The `created` stage is the canonical "code is written, not yet verified" state. **Verification then runs automatically** (Step 8 below auto-invokes `/renmark:verify`) — clearing pipeline state first is what lets verify run without tripping its in-flight guard.

### 8. Auto-verify, then hand off (wizard step)

**Re-verify task verifiers before proceeding** — see CLAUDE.md § verify-before-done-rule. Re-run all task verifiers in index order. Report any that now fail.

**Then run `/renmark:verify` automatically.** A clean orchestrate run flows straight into feature-level verification — the user does NOT invoke it separately. Pipeline state was cleared in Step 7 and the stage is `created`, so verify's in-flight/stage guards pass. Verify runs its goal-backward smoke tests, writes its artifact, advances the stage to `verified`, and presents its own hand-off (codereview / finish / debug-on-failure).

Report the orchestrate completion line first, then let verify take over:

> *"All N tasks committed (M commits, ~$X spent). Running verification…"*

→ invoke `/renmark:verify`. From here the user follows verify's hand-off:
> *  [c] Code review — run an adversarial Codex pass over the diff via /renmark:codereview*
> *  [f] Finish — close the branch (PR or merge) via /renmark:finish*
> *  [d] Debug — investigate the failure verify surfaced via /renmark:debug*
> *  [n] Nothing — stop here; work stays committed*

**Only auto-verify on a fully clean run.** If any task failed (paused / escalated), do NOT auto-verify and do NOT offer the next step — surface the failure and the resume command first. Verification of a half-built feature is noise.

## Governance compliance

Upholds G2/G3/G5/G6/G7/G8/G9/G10/G11/G12 — see `CLAUDE.md` governance rules for definitions. The load-bearing caps are enforced in code, not prose: `dispatch.parse_subagent_response` refuses transcripts/diffs/code (G11), `SubagentOutput` caps summaries at 5 lines × 1200 chars (G3), and `summary.verifier_tail(tail_lines=3)` bounds verifier output (G3). State separation (lifecycle.json vs pipeline.json) and codex-subprocess isolation (G5) are described in the Steps above.

## Reference

- CLI flags: `renmark-execute --help`
- Plan format: `PLAN.md` § "Plan file format" (or `.renmark/plans/*.plan.md` examples)
- State dir: `.renmark/state/{pipeline.json, wave-summaries/, escalations/}`
- Memory dir: `.renmark/memory/`
- Hygiene contract: `plugin/templates/CLAUDE.md.template` § `context-hygiene-rule`, `task-isolation-rule`, `summary-boundary-rule`

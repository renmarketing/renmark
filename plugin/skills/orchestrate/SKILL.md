---
name: orchestrate
description: "Use to execute a renmark plan — `/renmark:orchestrate` or \"execute the plan\", \"build it\", \"run the plan\". Dispatches each task in an isolated subagent and commits passing tasks."
---

# orchestrate

## Overview

Dispatches plan tasks in waves with **strict task isolation** (G11). Within a `parallel_group`, tasks run concurrently. Two dispatch paths — never mix them:

| Executor | Dispatch path | Quota consumed |
|---|---|---|
| `codex` | Bash call to `renmark-execute` (subprocess) | Codex account (OpenAI subscription) |
| `haiku`, `sonnet`, `opus` | Agent tool calls (no model override) | Claude Code account (Anthropic subscription) |
| `fable` | Agent tool call with `model: "fable"` override (one-shot fallback to no override — opus tier — if fable is unavailable; see Step 3b) | Claude Code account (Anthropic subscription) |

After each wave, the skill writes `.renmark/state/wave-summaries/wave-N.json` (the per-task `SubagentOutput` dicts) and commits passing tasks serially in task-index order.

**Token-isolation contract (G11):**
- Every task runs in an **isolated subagent context**.
- Each subagent receives only: task spec · required file paths · upstream artifact pointers · dependency summaries from the prior wave's `wave-summaries/` file · verifier expectations.
- Each subagent emits only the `SubagentOutput` schema (status, artifact_path, touched_files, sha, summary_lines ≤ 5, dependency_notes, token_count, completion_state, confidence, retry_count).
- The orchestrator validates the response via `renmark.dispatch.parse_subagent_response` — any extra field (transcript, diff, generated_code, reasoning) raises `IsolationViolation` and the task is FAIL.
- **The orchestrator never reads generated code into the conversation.** Period.

## Operating mode

**Orchestrator** is orchestrate's default: dispatch parallel scoped subagents, offload bulk/single-file emissions to Codex, and advance on reviewed PASS/FAIL outcomes. In **Conductor** mode, prefer serial single-task execution with tighter user checkpoints between tasks. Either mode keeps the G11 isolation/aggregation contract above unchanged.

## When to Use

- User has a `.renmark/plans/*.plan.md` file ready and wants it executed
- After `/renmark:plan` + `/renmark:check-plan` complete (stage = `plan-validated`)
- To `--resume` a paused run

**Do NOT use:**
- Without a validated plan → `/renmark:plan` first, then `/renmark:check-plan`
- For brainstorming or design — that's `/renmark:brainstorm`
- To "look at the generated code" — that's a context-hygiene violation; route to `/renmark:debug` instead

## Steps

**Step 0 — Context check.** Call `lifecycle.skill_preamble(repo, 'orchestrate')`. If it returns a non-None hint, surface as a one-line note. Also check `state.read_pipeline_state(repo)` — if `current_phase == "orchestrate"` and `pipeline_is_resumable(repo)`, surface: *"Existing orchestrate run paused at wave N — use `--resume` to continue, or clear pipeline state to start fresh."*  When the user passes `--resume` and an existing run is resumed from pipeline state, emit:
```python
from renmark import usage, state, analytics
analytics.record_event(repo, ts=state.now_iso(), kind="resume")  # kind registered in EVENT_KINDS
```

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

**Plan validation** — run `python -m renmark.plan_lint <plan>` directly before spending tokens. If it exits 1 (BLOCK), fix the plan first; WARNs can proceed with user acknowledgment. (Defense-in-depth: the same engine validated the plan at plan-time; running it again at dispatch-time means check-plan and orchestrate can never drift.)

**Refactor safety** — if the plan has any `complexity: hard` task or the spec mentions "refactor"/"rename"/"restructure"/"migrate":
1. Confirm clean working tree (`git status`).
2. Checkpoint commit: `git -c user.name="renmark-orchestrate" -c user.email="orchestrate@renmark.local" commit --allow-empty -m "chore: checkpoint before <plan name>"`.
3. Baseline each affected verifier — if any fails now, **stop**: do not orchestrate into a broken baseline.

**Changelog / decisions check** — read the last 5 entries in `CHANGELOG.md`, and when `.renmark/memory/decisions.md` is present, also read its decision titles + guard text (titles and guards only — never full bodies; REQ-5). Flag any "Do not change" guard or recorded decision the plan would contradict. A contradiction is **semantic**: the plan would undo or overwrite a guarded decision — and this binds even when there is **no target-file overlap** (a plan can violate a decision without touching the same file). On any such contradiction, surface it and **PAUSE for reconciliation** before dispatching; never silently overwrite a recorded decision.

**Cost preview** — `renmark-execute --dry-run <plan>` shows the task list + estimated cost.

**Headless gate (cost approval).** Before the `Proceed? [y/N]` prompt below, consult the headless contract (`plugin/skills/_shared/headless-contract.md`):

```python
from renmark import headless
envelope = headless.resolve_gate(
    repo, "cost", kind="dangerous",
    originating_skill="orchestrate",
    what="~$X across N tasks",   # the dry-run estimate
)
```

- **Headless** (`envelope["mode"] != "interactive"`) → emit the `needs_input` JSON block + `headless.render_return(envelope)` prose line and **STOP** — do not dispatch.
- **Interactive** (`{"mode": "interactive"}`) → fall through to the prompt below, unchanged.

This human cost-approval gate is **distinct** from the Tier-1 usage-limit pause in 3a-bis (which auto-pauses on an already-exceeded local limit); leave that intact.

Interactive prompt: *"Proceed? [y/N]"*

### 3. Dispatch tasks in waves (G11 isolation)

For each wave in `dispatch.group_tasks_by_wave(tasks)` — where `tasks = parser.parse_plan(Path(plan_path))`, a plain `list[Task]` (`parse_plan` returns no object with a `.tasks` attribute):

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
                f"task {task_output.get('task_id', '?')}: {task_output['dependency_notes']}"
            )
```

**The orchestrator does NOT load any wave's full output.** Only the `dependency_notes` field crosses the boundary.

**3a-bis. Usage preflight (Tier-1, free) — pause before spending if a local limit is already exceeded**

Before dispatching any task in this wave, compute the bounded usage view and check it against the configured local limits in `.renmark/analytics/limits.json`. This is a deterministic file-IO check — **never read raw usage logs into conversation**; `build_usage_view` returns the bounded summary dict only.

```python
from renmark import usage, state, analytics
view = usage.build_usage_view(repo, now=state.now_iso())
if view.get("limit_exceeded"):  # a configured local limit is already over budget
    pause = usage.classify_usage_pause(
        run_id=<run_id>, plan_path=<plan>, last_task_index=wave_first_task_index,
        now=state.now_iso(), feature=<feature or "">, repo=repo,
    )
    state.write_pause(repo, pause)
    analytics.record_event(repo, ts=state.now_iso(), kind="pause")  # kind registered in EVENT_KINDS
    # Surface the resume command and STOP — do NOT dispatch this wave.
```

The PauseState carries `pause_kind="usage_limit"` and a `resume_after` timestamp (provider reset if known, else the next local rolling-window boundary, else now+60min). Surface: *"Local usage limit reached — orchestrate paused before wave N. Resume with `/renmark:orchestrate --resume` after `resume_after`."* Then stop; do not enter 3b. MVP: no polling, no auto-retry — the user (or `/renmark:resume`) re-enters later.

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

For `executor: haiku | sonnet | opus | fable` tasks:

Plain `Agent` call — no `model` override for `haiku | sonnet | opus`; for `executor: fable`, pass `model: "fable"` on the Agent call. Build the subagent prompt from `dispatch.build_subagent_input(task, dependency_summaries=...)`. The Agent prompt MUST instruct the subagent:

> "Your final response MUST be valid JSON matching this shape:
> ```json
> {"status": "PASS|FAIL|SKIP", "artifact_path": "<path>",
>  "touched_files": [...], "sha": "<sha or null>",
>  "summary_lines": ["<≤5 lines>"], "dependency_notes": "<what downstream tasks need>",
>  "token_count": <int>, "completion_state": "complete|partial|failed",
>  "confidence": "low|medium|high", "retry_count": 0}
> ```
> The generated code goes in the artifact file at `<artifact_path>`, NOT in your response. Do not paste code or diffs back. If you cannot complete with the inputs provided, return `status: FAIL` with a one-line reason."

The Agent prompt MUST also include the canonical reasoning instruction blockquote — the one under "The canonical reasoning instruction (verbatim — single source)" in `${CLAUDE_PLUGIN_ROOT}/skills/_shared/reasoning-contract.md`, NOT the skill-author "Dispatch reference" blockquote — read it from that file at dispatch time and append it verbatim to the subagent prompt. This applies to BOTH dispatch paths: Agent-path dispatches above AND codex ad-hoc task specs (`renmark-execute --task`).

After the Agent returns, parse its response through `dispatch.parse_subagent_response()`. If it raises `IsolationViolation`, mark the task as FAIL with reason "subagent leaked forbidden fields" — do not retry.

**Fable-unavailable fallback (defense-in-depth).** If an Agent call with `model: "fable"` errors **on dispatch** — the model is unavailable or the override is rejected by the harness — retry the task **exactly once** with no `model` override (the opus tier, same as `executor: opus`). Requirements (all mandatory — degradation is never silent):

- record `fallback: fable→opus` in that task's wave-summary entry — in `dependency_notes` or a dedicated note field — so downstream waves and `/renmark:verify` see what actually ran;
- log the fallback via `memory.append_routing(repo, signature=<task signature>, executor="opus", outcome=<"passed"|"failed">)` so repeated fable fallbacks accumulate as routing evidence in `.renmark/memory/routing.md`;
- ledger the fallback call with `model="opus"` (not `task.executor`) so spend attribution matches what ran.

One retry only: if the no-override retry also fails, that is an ordinary task FAIL — no further reroutes, no second fallback tier. Note that orchestrate's pre-flight `plan_lint` fable gates (checks 9–10: undeclared `top_tier: fable`, fable-on-mechanical) make an undeclared fable dispatch unreachable in the normal flow — this fallback is defense-in-depth for harness-side unavailability, not a routing surface. It is distinct from and complementary to the codex-side "Reroute-first on codex limits" rule in Step 5: that rule handles usage limits on the subprocess path; this one handles model availability on the Agent path.

**Ledger the call.** Immediately after parsing each successful Agent return, log the spend so `/renmark:roadmap` reports honestly:

```python
from renmark import state
from renmark.roadmap import AGENT_OVERHEAD_TOKENS
state.log_agent_call(
    repo,
    task_id=task.index,
    model=task.executor,                            # 'haiku' | 'sonnet' | 'opus' | 'fable'
    tokens_in=AGENT_OVERHEAD_TOKENS,                # ~10k system + spec overhead per call
    tokens_out=out.token_count,                     # SubagentOutput.token_count
    run_id=<run_id>,
)
```

Codex tasks are ledgered by `renmark-execute` directly — do NOT call `log_agent_call` for them or spend will be double-counted.

**3c. Run verifier per task**

For each task that returned PASS status, run its verifier via `summary.verifier_tail(cmd, cwd=repo, tail_lines=3)` (`cwd` is a required keyword-only argument). Orchestrator-visible output is bounded: `exit <code> | <first 3 lines>`. If the verifier fails, downgrade the task to FAIL.

**3d. Escalation decision log**

When a task is escalated to a higher-tier executor, an ADR is appended to `.renmark/memory/decisions.md` via `memory.log_escalation_decision()`. This is automatic — handled inside `renmark/cli/_engine.py`'s `_record_escalation` when `escalated_to=` is passed. Idempotent on (title, date): re-running the same escalation on the same day does not duplicate the ADR. Best-effort: decision-logging failures do NOT break orchestrate. Pointer-only — the orchestrator never reads `decisions.md` into conversation.

### 4. Aggregate wave summary

After all tasks in the wave finish:

```python
state.write_wave_summary(repo, wave_index, task_outputs=[
    # to_dict() carries no task_id — stamp it here so step 3a can attribute notes
    {"task_id": task.index, **out.to_dict()}
    for out, task in zip(outputs, wave_tasks)
])
state.write_pipeline_state(repo, wave_index=wave_index,
                           add_completed_task=..., add_failed_task=...)
```

**Record one analytics event per task (bounded — from the WaveResult summary, NEVER transcripts).** After the wave summary is persisted, emit a structured run event for each task so usage/limits stay current. Source every field from the parsed `SubagentOutput` / verifier result already in hand — do not re-read artifacts, diffs, or raw logs.

```python
from renmark import analytics, state
for out, task in zip(outputs, wave_tasks):
    analytics.record_task_run(
        repo, ts=state.now_iso(), task_id=task.index, title=task.title,
        executor=task.executor, model=task.executor, provider="",
        status=out.status,
        # verifier_result MUST be a normalized verdict token ("pass"/"fail") —
        # analytics._agg_tasks classifies on these, NOT on a free-text exit summary.
        verifier_result=("pass" if out.status == "PASS" else "fail"),
        retry_count=out.retry_count,
        failure_reason=<one-line reason if FAIL else "">,  # human-readable tail lives here
        total_tokens=out.token_count, sha=(out.sha or ""),
    )
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
| Task failed on a **provider usage signal** (rate-limit / quota / retry-later / usage-exceeded) | Classify as **PAUSED, not FAIL** — see Tier-2 below; STOP the wave so `/renmark:resume` continues later |
| Any other FAIL in wave | Pause via `state.write_pause(...)`; show resume command; stop |
| `IsolationViolation` raised | Mark task FAIL; aggregate summary anyway; alert user to skill-side bug |
| Plan parse error | Route to `/renmark:plan` |

**Tier-2 — provider-error classification (usage_limit, not failure).** When a task's failure signal is a provider rate-limit / quota / `retry-later` / usage-exceeded error (from `renmark-execute` output or an Agent error), do NOT record it as `status: FAIL`. Reclassify the run as paused for usage and stop the wave — this is a transient quota event, not a broken task. MVP: no polling, no auto-retry; `/renmark:resume` re-enters once the window clears.

```python
from renmark import usage, state, analytics
pause = usage.classify_usage_pause(
    run_id=<run_id>, plan_path=<plan>, last_task_index=task.index,
    now=state.now_iso(), provider=<provider>, model=<model>,
    observed_usage=<bounded error signal>, provider_reset_at=<reset ts if surfaced>,
    feature=<feature or "">, repo=repo,
)
state.write_pause(repo, pause)  # pause_reason="usage_limit", pause_kind="usage_limit"
# Emit a classified event — use "rate_limit" or "quota" based on the observed signal (both registered in EVENT_KINDS)
analytics.record_event(repo, ts=state.now_iso(),
    kind="rate_limit" if <is_rate_limit_signal> else "quota")
```

Surface: *"Provider usage limit hit at task <index> — paused (not failed). Resume with `/renmark:orchestrate --resume` after `resume_after`."* The PauseState's `resume_after` follows the same fallback rule as the preflight pause (provider reset → next local window → now+60min).

**Reroute-first on codex limits (owner rule, 2026-06-11).** When the usage signal is
CODEX-side and the blocked tasks are non-bulk (test scaffolding, single-file emissions —
the typical codex wave), do NOT stop by default. Offer the pause-vs-reroute choice; on no
answer, default-forward (handoff-menu.md rule 8) **re-routes the blocked codex tasks to
`sonnet` Agent calls and continues the wave**. Reroute requirements (all mandatory):
- ledger each reroute via `memory.append_routing(...)` (signature: codex→sonnet, reason: usage_limit) — degradation is never silent;
- mark the wave-summary entry `executor: sonnet (rerouted: codex usage-limit)`;
- `state.log_agent_call` the sonnet spend (reroutes bill Anthropic; never also ledger codex for the same task — no double counting).

Claude-side limits still pause — there is no cheaper tier to re-route onto. Pausing also
remains correct when the user explicitly chooses it or the blocked codex work is
bulk-heavy (> 5 tasks or > ~3k est_tokens each): bulk emission is codex's role and
shifting it to sonnet burns the user's Claude quota against REQ-2's intent.

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

→ invoke `/renmark:verify`. From here the user follows verify's hand-off menu, rendered per `${CLAUDE_PLUGIN_ROOT}/skills/_shared/handoff-menu.md` (an interactive `AskUserQuestion` choice when available, numbered text only as fallback; the user must pick a choice to continue).

**Next step is state-derived (pipeline skill, next-steps.md class 1).** Orchestrate's own next action after a clean run is the stage-routed `next_recommended(repo)` (= `/renmark:verify` at stage `created`), which it auto-invokes above. On a paused/failed run it does NOT advance — it surfaces the resume command. Per `${CLAUDE_PLUGIN_ROOT}/skills/_shared/next-steps.md` (class 1 — Tier-0 stage routing); orchestrate hands directly to verify rather than rendering a separate picker.

**Browser QA recommendation (not automatic).** The default auto-verify above stays a shell smoke test — browser QA is **not automatic**. When a clean run's changed files / feature scope touch user-visible or browser surfaces (templates, frontend JS/CSS, page routes/controllers, forms/buttons, settings, preview/render UI, checkout/pricing, browser-facing pages), Recommend `/renmark:verify --qa` for a live happy-path flow — and `--deep-qa` for risky UI/runtime changes or after a normal `--qa` passes. This is a recommendation surfaced to the user, not an automatic step.

**Only auto-verify on a fully clean run.** If any task failed (paused / escalated), do NOT auto-verify and do NOT offer the next step — surface the failure and the resume command first. Verification of a half-built feature is noise.

## Governance compliance

Upholds G2/G3/G5/G6/G7/G8/G9/G10/G11/G12 — see `CLAUDE.md` governance rules for definitions. The load-bearing caps are enforced in code, not prose: `dispatch.parse_subagent_response` refuses transcripts/diffs/code (G11), `SubagentOutput` caps summaries at 5 lines × 1200 chars (G3), and `summary.verifier_tail(cmd, cwd=repo, tail_lines=3)` bounds verifier output (G3). State separation (lifecycle.json vs pipeline.json) and codex-subprocess isolation (G5) are described in the Steps above.

## Reference

- CLI flags: `renmark-execute --help`
- Plan format: `PLAN.md` § "Plan file format" (or `.renmark/plans/*.plan.md` examples)
- State dir: `.renmark/state/{pipeline.json, wave-summaries/, escalations/}`
- Memory dir: `.renmark/memory/`
- Hygiene contract: `plugin/templates/CLAUDE.md.template` § `context-hygiene-rule`, `task-isolation-rule`, `summary-boundary-rule`

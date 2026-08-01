# R-0.0 / WP-4 Stage 2 — Instrumentation Design

**Design only. No code has been written or modified.** Per Owner-confirmed narrowed scope (`telemetry-coverage-table.md`): covers only **replans** and **dispatch-wave/worker-dispatch granularity**. Duration/tokens are captured externally by the WP-5 harness; test-execution counts come from the harness's own command log — neither needs `renmark/**` instrumentation.

**This design requires a separate `contract.yaml` `allowed_paths` amendment — naming the exact two files below — before any implementation may begin.** That amendment is not part of this design pass.

## Gap 1: Replans

**Definition used (grounded in existing code, not invented):** a replan is any time `renmark/program_driver.py`'s `evaluate_stop`/`evaluate_stop_for_stage` (lines 235, 304) returns `StopReason.PLAN_BLOCK` or `StopReason.PRD_DRIFT` — the two existing `StopReason` members that already mean "the current plan needs to be reconsidered before the roadmap proceeds" (per that module's own docstring: "the SKILL must re-plan / approve before the roadmap proceeds").

**Why not also track re-invocation of `/renmark:plan` on an existing plan?** That would require hooking `plugin/skills/plan/SKILL.md`'s prose flow, which is `plugin/**` — explicitly prohibited for R-0.0, and outside what a Python-level opt-in trace can observe anyway (the skill is prose the agent follows, not a function call). Scoping the replan signal to the two existing `StopReason` values keeps this fully mechanical and inside `renmark/**` only.

**Hook location:** `renmark/program_driver.py`, inside `evaluate_stop` (line 235) — add one line immediately before each `return StopReason.PLAN_BLOCK` / `return StopReason.PRD_DRIFT` in the function body:

```python
if os.environ.get("RENMARK_BASELINE_TRACE") == "1":
    _append_baseline_trace(repo, {"ts": ts, "kind": "replan_signal", "stop_reason": "plan_block"})
return StopReason.PLAN_BLOCK
```

(Illustrative shape only — exact insertion points depend on `evaluate_stop`'s actual return statements, which is why `repo`/`ts` availability at each return site needs to be checked against the real function signature before implementation; `evaluate_stop` today takes only `stage_result: dict`, no `repo`/`ts` — the function signature itself may need a narrowly-scoped, backward-compatible optional-kwarg addition, e.g. `evaluate_stop(stage_result, *, repo: str | None = None, ts: str | None = None)`, a no-op change when both are `None`. This is exactly the kind of signature-shape decision that belongs in implementation, not this design doc — flagging it here so it isn't discovered as a surprise later.)

**Behavior neutrality:** the `if os.environ.get(...) == "1"` guard means the added line executes (and even then, only writes to disk) only under the opt-in env var; the `return StopReason.PLAN_BLOCK` statement itself and its position in the function are unchanged. No routing/planning/retry/verification decision is touched — this is purely an observer on an already-computed return value.

## Gap 2: Dispatch-wave / worker-dispatch granularity

**Hook location:** `renmark/dispatch.py`, inside `dispatch_wave` (line 97) — at entry, before any task in the wave is dispatched:

```python
if os.environ.get("RENMARK_BASELINE_TRACE") == "1":
    _append_baseline_trace(repo, {
        "ts": ts,
        "kind": "wave_dispatch",
        "wave_size": len(wave),
        "parallel_groups": sorted({t.parallel_group for t in wave if t.parallel_group is not None}),
        "task_targets": [t.target for t in wave],
    })
```

**Behavior neutrality:** `dispatch_wave` already receives `repo: Path` as a parameter (line 100); `ts` would need to come from the caller the same way `program_driver.py`'s functions would. The added block executes only under the opt-in guard, runs before any dispatch logic, and reads already-available `wave`/`repo` values — it does not alter `run_task` invocation, `max_workers` handling, or the returned `WaveResult`.

## Shared plumbing

**New trace ledger:** `.renmark/analytics/baseline-trace.jsonl`, reusing the existing append-only JSONL pattern (`renmark/analytics.py`'s `_append` helper, or a narrowly-scoped equivalent if `_append` isn't importable without pulling in unrelated `analytics.py` surface — a real implementation-time decision, not resolved here). This satisfies "reuse the current append-only analytics path where practical" without modifying `analytics.py`'s existing writers (`record_task_run` etc. stay untouched).

**Env var:** `RENMARK_BASELINE_TRACE=1` (opt-in, unset by default — matches the existing pattern of `RENMARK_TOP_TIER`/`RENMARK_HOST` env overrides already used elsewhere in the codebase, per `current-system-audit.md`).

## Test plan (proves behavior neutrality, per Owner requirement)

1. **Neutrality test (both hook sites):** with `RENMARK_BASELINE_TRACE` unset, run `evaluate_stop`/`evaluate_stop_for_stage` and `dispatch_wave` against fixed fixture inputs; assert the return value is byte-identical to a captured pre-instrumentation baseline (a snapshot test using the *current*, un-instrumented function output as the golden value). This is the empirical "byte-identical output on a fixed test input" proof the Owner's original correction required.
2. **Positive test:** with `RENMARK_BASELINE_TRACE=1`, run the same fixtures; assert `baseline-trace.jsonl` receives exactly the expected rows (one `replan_signal` row per `PLAN_BLOCK`/`PRD_DRIFT` return, one `wave_dispatch` row per `dispatch_wave` call) and that the function's *return value* is still identical to the neutrality test's golden value — the trace write must be a pure side effect, never influencing the return.
3. **Full suite regression:** the complete existing 1683-test suite still passes with instrumentation present and `RENMARK_BASELINE_TRACE` unset (matches `contract.yaml`'s `engineering_acceptance`).

## Exact `allowed_paths` amendment needed (not yet made — separate gate)

```yaml
allowed_paths:
  - "renmark/program_driver.py"   # evaluate_stop / evaluate_stop_for_stage only
  - "renmark/dispatch.py"         # dispatch_wave only
  - "tests/test_program_driver.py"   # or wherever program_driver tests live — neutrality + positive tests
  - "tests/test_dispatch.py"          # same, for dispatch_wave
  - ".renmark/analytics/baseline-trace.jsonl"   # new ledger file, output only
```

This is a proposal for the next gate — `contract.yaml`'s `prohibited_paths` still blocks `renmark/**` as of this design pass. Implementation does not begin until this amendment is explicitly approved.

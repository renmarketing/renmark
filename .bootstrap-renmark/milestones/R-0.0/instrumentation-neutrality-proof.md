# R-0.0 Instrumentation Behavior-Neutrality Proof

Required by `internal-acceptance-scenario.md` criterion 5. This is the
dedicated proof artifact — not a restatement of `instrumentation-design.md`
(the design intent) or the unit tests (regression guards). This is the actual
fixed-input before/after run, executed and recorded for R-0.0 acceptance.

## Diff review

Both hooks (`renmark/program_driver.py::decide_milestone_execution`,
`renmark/dispatch.py::dispatch_wave`) are additive-only: the pre-existing
logic is unchanged (`decide_milestone_execution` delegates to the renamed
`_decide_milestone_execution_impl`; `dispatch_wave`'s new block sits before
its existing return-value construction and does not touch it). Neither hook
mutates its return value based on the trace env var — the var only gates a
side-effecting file append.

## Fixed-input run (executed 2026-08-01)

`decide_milestone_execution` called twice with identical `(program, stage_id,
metadata, repo)` inputs — once with `RENMARK_BASELINE_TRACE` unset, once with
it set to `"1"` — using metadata that triggers a `PLAN_BLOCK` disposition
(the one case that appends a trace row when enabled):

```
trace-off: MilestoneDecision(action='stop', advance_allowed=False,
           reason=StopReason.PLAN_BLOCK, repair_package=None)
trace-on : MilestoneDecision(action='stop', advance_allowed=False,
           reason=StopReason.PLAN_BLOCK, repair_package=None)
return values identical: True

off ledger (.renmark/analytics/baseline-trace.jsonl) exists: False
on  ledger (.renmark/analytics/baseline-trace.jsonl) exists: True
  -> {"kind": "replan_signal", "stage_id": "build",
      "stop_reason": "plan_block", "ts": "2026-08-01T14:14:12.013132+00:00"}
```

**Result:** the function's return value is byte-identical regardless of the
trace flag. The only observable difference with the flag on is a new
append-only file under `.renmark/analytics/` — no behavior change to the
caller.

## Regression coverage

The same guarantee is pinned by unit tests so it can't silently regress:
- `tests/test_program_driver.py::test_decide_milestone_execution_is_byte_identical_when_trace_env_unset`
- `tests/test_dispatch.py::test_dispatch_wave_is_byte_identical_when_trace_env_unset`

Both pass as of this proof (`51 passed` across `test_program_driver.py` +
`test_dispatch.py`, run 2026-08-01).

## Verdict

Criterion 5 (instrumentation is behavior-neutral when disabled): **PASS**,
independently checkable via the run above and the pinned regression tests,
not the General Contractor's word alone.

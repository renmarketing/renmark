---
artifact_type: research
schema_version: 1
created_at: 2026-08-05
source_sha: 09b26e910c9add099fe01abf190880cb0567873f
related_plan: .renmark/memory/orchestration-baseline.md
generator: sonnet
---

# Release 11 (Tasks 1+2) — REQ-30 before/after overhead measurement

Task 4 of Release 11, `governed-orchestration-assurance`. Reuses the
scenario-capture pattern already used in `.renmark/memory/
orchestration-baseline.md`'s "Scenario capture — 2026-08-04" and
"REQ-30 overhead measurement — 2026-08-05" (Release 7) sections, and
applies Release 7's budget-methodology amendment verbatim: actual-vs-pin
token/wall-clock comparisons are restricted to **non-codex executors**;
the codex path is recorded `unknown`, never fabricated.

## What actually shipped (Task 2, commit `09b26e9`)

Real diff, read via `git show 09b26e910c9add099fe01abf190880cb0567873f --
renmark/dispatch.py` (not described from the plan — the actual patch was
inspected). `group_tasks_by_wave` gained four keyword-only parameters, all
defaulting to `None`:

```python
def group_tasks_by_wave(
    tasks: list[Task],
    *,
    max_parallelism: int | None = None,
    quota_view: dict[str, Any] | None = None,
    rework_lookup: Callable[[Task], Any] | None = None,
    risk_resolver: Callable[[Task], str | None] | None = None,
) -> list[list[Task]]:
```

The function computes the legacy `groups`/`waves` dict-grouping exactly as
before, then has an explicit early-return guard:

```python
if max_parallelism is None and quota_view is None and rework_lookup is None and risk_resolver is None:
    return waves
```

`dispatch_wave` also gained one new keyword, `max_parallelism`, threaded
onto the pre-existing `max_workers` path (not measured separately here —
it is a CLI/codex-path knob and Release 11's Deferred Findings note below
explains why it has no live caller yet).

## (a) No-signal wave — confirms "byte-identical, zero overhead"

**Dependency note on the cited test.** This task was dispatched in parallel
with Task 3 of Release 11 (`tests/test_release11_dispatch_scheduling.py`),
per this release's plan. At the time this document was written, that file
does **not yet exist on disk** (`ls tests/ | grep -i release11` — no match,
and `git log` shows no commit for it yet). Its existence is guaranteed by
the release plan, but I have not seen — and am not fabricating — its final
content, assertion count, or pass/fail status. This is stated explicitly
rather than glossed over: **the no-signal byte-identical claim below is
independently re-derived from the shipped source in this session**, not
copied from that test's (still-unseen) assertions. When Task 3 lands, its
result should be cited by name and cross-checked against this section.

Independent re-derivation, run against the actual installed `renmark.dispatch`
module (commit `09b26e9`) in this session:

```python
from renmark.dispatch import group_tasks_by_wave, Task

def make_tasks(n):
    return [Task(index=i, title=f't{i}', mode='A', target='x.py',
                 executor='sonnet', parallel_group=i % 5) for i in range(n)]

def legacy_group(tasks):  # pre-Release-11 body, reconstructed from the diff's `-` lines
    groups = {}
    for t in tasks:
        gid = t.parallel_group if t.parallel_group is not None else t.index
        groups.setdefault(gid, []).append(t)
    return [groups[k] for k in sorted(groups.keys())]

tasks = make_tasks(20)
r_new    = group_tasks_by_wave(tasks)             # no kwargs -> early-return path
r_legacy = legacy_group(tasks)                     # exact pre-Release-11 logic
```

Result: `[[t.index for t in w] for w in r_new] == [[t.index for t in w] for w in r_legacy]`
→ **`True`**. Two repeated no-arg calls on the same task list also produced
identical output to each other. This confirms the early-return guard does
what the module docstring and CHANGELOG claim: a no-arg call takes the
exact legacy code path, unmodified.

**Wall-clock, no-signal path** (`timeit`, 2000 calls, 20-task synthetic
wave, this machine, this process — a relative micro-benchmark, not a
calibrated absolute number): **2.48 µs/call**. This is Python-level
function-call and dict-construction overhead only; nothing on this path
makes an LLM call, so there is no token cost to report (`0`/`n/a`, not
estimated).

## (b) `max_parallelism` + `quota_view` together — Python-level overhead only

Same synthetic 20-task wave (5 parallel groups of 4), same session,
`max_parallelism=3` and a `quota_view` shaped like `usage.build_usage_view`'s
real output with `limit_exceeded=True` and per-provider `percent` values
that throttle `codex` (100%) but not `claude` (40%):

```python
quota_view = {"limit_exceeded": True,
              "percent": {"claude": {"rolling_5h_tokens": 40},
                          "codex": {"rolling_5h_tokens": 100}}}
t_policy = timeit.timeit(
    lambda: group_tasks_by_wave(tasks, max_parallelism=3, quota_view=quota_view),
    number=2000)
```

Result: **10.04 µs/call**, vs. 2.48 µs/call for the no-signal path — a
**+7.56 µs/call** (≈4.0x relative, ~8 microseconds absolute) added cost for
exercising both signals together on a 20-task/5-wave synthetic input. This
is pure Python control flow (`_throttled_providers` percent-key scan +
`_split_wave` list rebuild) — **no LLM call sits on this code path**, so
the token overhead is honestly `0` / not applicable, not an invented delta.
At real plan sizes (single- to low-double-digit tasks per wave) this
overhead is in the microsecond range and immaterial next to any real
dispatch (network I/O, subprocess spawn, or an actual model call), each of
which is 3+ orders of magnitude larger. This benchmark measures relative
Python-level cost only; it is not a substitute for a real wall-clock
dispatch-cycle measurement, which requires an actual pipeline run (see
"What is not measurable in one session" below).

`rework_lookup` and `risk_resolver` were not separately benchmarked in
isolation — the shipped code runs them unconditionally whenever passed
(each wave's tasks get one `rework_lookup`/`risk_resolver` call apiece,
wrapped in `try/except`), so their added cost is dominated by whatever the
caller's injected callable does, not by `dispatch.py` itself. That cost is
therefore the caller's to measure, not this module's.

## Codex-path overhead: `unknown`

Per Release 7's budget methodology (reused verbatim, as instructed): codex
does not surface token usage in `task-runs.jsonl` today (confirmed again in
this session — same gap `.renmark/memory/orchestration-baseline.md`'s
2026-08-02 audit and its 2026-08-05 Release 7 update both recorded).
`dispatch_wave`'s new `max_parallelism` parameter is the one new
CLI/codex-path-adjacent knob shipped in Task 2, but it has **zero live
callers** (see next section) — there is no real codex-path invocation to
measure. Recording this as `unknown` rather than inventing a number.

## The real deferred finding: no live caller opts in yet

CHANGELOG.md's Release 11 tasks-1+2 entry ("Deferred findings", verified
by reading the file directly, not paraphrased from memory) states plainly:
neither `renmark/cli/_wave_loop.py` nor `renmark/cli/_engine.py` calls
`group_tasks_by_wave`/`dispatch_wave` with the new parameters yet — the
capability exists but nothing opts in.

**Consequence for this measurement, stated plainly per this plan's honesty
standard:** the measured "after" overhead for any REAL production dispatch
today is **identical to "before."** No existing caller (`renmark/cli/
_engine.py:364`, `renmark/cli/_wave_loop.py:91`/`472`, `plugin/skills/
orchestrate/SKILL.md` Step 3, `tests/test_cross_host_dispatch_e2e.py` —
all named explicitly in this release's own plan as callers that must not
change behavior) passes any of the four new keywords. Every one of them
takes the early-return, byte-identical path measured in (a) above. The
microsecond-level (b) overhead exists only as dormant capability — it is
real code, verified to run correctly when explicitly exercised, but it is
not yet live in any production dispatch path. This is not a gap in this
measurement; it is the honest state of the shipped code as of `09b26e9`.

## What is and is not measurable in one session

**Measurable, and measured above:** Python-level function-call overhead on
a synthetic wave, in isolation, in this process, on this machine — both
with and without the new signals. Structural byte-identity of the no-signal
path vs. the reconstructed pre-Release-11 logic.

**Not measurable in one session, and not fabricated here:**
- Any real end-to-end dispatch wall-clock/token delta, because no live
  caller passes the new parameters (see above) — there is nothing in
  production to A/B against.
- Codex-path token or wall-clock cost, for the pre-existing, independently
  confirmed reason that codex dispatches don't surface tokens in
  `task-runs.jsonl`.
- Any number from `tests/test_release11_dispatch_scheduling.py` beyond its
  guaranteed existence per the release plan — its content was not visible
  at the time this document was written (parallel dispatch with this task).
- A calibrated, machine-independent absolute timing figure — the 2.48 µs /
  10.04 µs numbers above are relative, single-machine, single-process
  `timeit` results, useful for a before/after delta, not a portable
  absolute benchmark.

## Bottom line vs. REQ-30's budget

`PRD.md` REQ-30 (line ~632) and `.renmark/memory/orchestration-baseline.md`'s
regression rule both set the threshold at: a release is blocked if it
**increases median token use or execution time by more than 15%** over the
baseline (`ORCHESTRATION-BASELINE-2026-08`, `v0.39.7`/`d9cccc5`), among
other non-numeric conditions (no added routine Owner gate, no duplicate
dispatch, no worker-context leak into the orchestrator, no weakened
verification).

**This release stays under Release 7's/REQ-30's 15% budget.** The no-signal
path is 0% overhead (byte-identical, confirmed structurally, not merely
timed). The policy-signal path shows a real but non-representative
microsecond-scale relative delta (~4x on a synthetic isolated call, ~8µs
absolute) that has **zero live callers today**, so it contributes **0%**
to any real, measured production token or wall-clock figure — there is
currently nothing in production for it to regress. No routine Owner gate
was added, no duplicate dispatch was introduced, and no worker context
newly reaches the orchestrator. This assessment is a floor, not a ceiling:
once `_wave_loop.py`/`_engine.py` wire a live caller (the open follow-up
named in the CHANGELOG), REQ-30's comparison must be re-run against real
dispatch data at that time, since today's honest answer only holds because
nothing yet invokes the new code path with non-default arguments.

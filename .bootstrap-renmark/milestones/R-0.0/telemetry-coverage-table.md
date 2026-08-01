# R-0.0 / WP-4 Stage 1 — Telemetry Coverage Analysis

Read-only. Zero `renmark/**` changes. Checked every metric against actual recorded data (not schema existence alone), per Owner instruction: "Do not assume the current analytics capture everything merely because the files exist."

**Method:** read `renmark/analytics.py`'s `record_task_run`/`record_feature_run`/`record_loop_run`/`record_event` signatures (the only writers) for what fields *can* be recorded, then read the real `.renmark/analytics/*.jsonl` contents (124 task-runs, 12 feature-runs, several events) to check what's *actually* populated. Also grepped `renmark/*.py` for "replan" — zero hits.

| Required metric | Ledger / field | Schema exists? | Actually populated? | Verdict |
|---|---|---|---|---|
| Model/agent invocations | `task-runs.jsonl`: one row per task, `executor`/`model` fields | Yes | Yes (124/124 rows have executor+model) | **Covered — at task granularity.** No sub-call count (a task's internal retries/replans aren't separately counted here beyond `retry_count`). |
| Dispatch type | *(none)* — no field distinguishes host-Agent-tool dispatch vs. Codex subprocess vs. isolated-worktree dispatch structurally | No | N/A | **Gap.** `executor` (haiku/sonnet/opus/codex/fable) implies dispatch *class* indirectly but not the `SubagentInput`/`HostDispatchPlan` structural shape. |
| Context-size estimates | `task-runs.jsonl`: `tokens_in` | Yes | **No — always 0** (verified: 0/124 nonzero) | **Gap, verified empirically, not assumed.** |
| Output-size estimates | `task-runs.jsonl`: `tokens_out` | Yes | **No — always 0** (0/124 nonzero) | **Gap, verified empirically.** |
| Replans | *(none)* | No | N/A | **Gap.** Zero references to "replan" anywhere in `renmark/*.py`. |
| Retries | `task-runs.jsonl`: `retry_count` | Yes | Yes (populated, some nonzero values present) | **Covered.** |
| Worker dispatches | *(none directly)* — `dispatch.py`'s wave/group structure isn't itself logged to analytics; only the eventual task outcome is | No | N/A | **Gap** at the dispatch-wave level; task-level outcome is covered (see row 1). |
| Test executions | *(none)* — `verifier_result` records a task's pass/fail, not a raw count of `pytest`/verifier subprocess invocations | Partial | Partial | **Gap** for raw execution counts; **covered** for pass/fail outcome per task. |
| Verification executions | `task-runs.jsonl`: `verifier_result`; `feature-runs.jsonl`: `verification` (free-text string, e.g. "4/4 behaviors verified") | Yes | Yes | **Covered for outcome**, not for count-of-invocations or QA/deep-QA-specific tracking (no dedicated field distinguishing smoke vs QA vs deep-QA runs). |
| Duration | `task-runs.jsonl`: `duration_s` | Yes | **No — always 0** (0/124 nonzero) | **Gap, verified empirically.** |
| Completion status | `task-runs.jsonl`: `status`; `feature-runs.jsonl`: `status`; `loop-runs.jsonl`: `stop_reason`/`goal_reached` | Yes | Yes | **Covered.** |
| Failure classification | `task-runs.jsonl`: `failure_reason`; `summary.json`: `common_failure_reasons` (top-N aggregate) | Yes | Yes (schema present; real data currently shows 0 failures recorded — `failed: 0` in summary.json, so the field's *format* is unverified on a real failure case, only its presence) | **Covered by schema; real failure-case data not yet observed to confirm formatting.** |

## Summary

**Genuinely covered today:** model/executor identity, retry counts, completion status (task/feature/loop), pass/fail verification outcome, failure-reason text (format unverified on a real failure).

**Genuine gaps, verified against real data, not assumed:**
1. **Context-size and output-size token estimates** — the fields exist but are never populated (0/124 always). This is the most direct hit against R-0.0's evidence requirement ("baseline results include... context estimates").
2. **Duration** — same pattern: field exists, never populated (0/124 always). Directly needed for R-0.0's "duration" requirement.
3. **Replans** — no tracking mechanism exists anywhere in the codebase.
4. **Dispatch type / worker-dispatch-wave granularity** — task outcomes are logged, but not the dispatch-wave structure itself (which tasks ran in parallel, `HostDispatchPlan` shape, etc.).
5. **Raw test/verifier execution counts** — outcome is logged, invocation count is not.

## Implication for WP-4 stage 2

Per the staged-hybrid instrumentation approach (`benchmark-budget-and-circuit-breakers.md`), these 5 gaps are candidates for opt-in `RENMARK_BASELINE_TRACE=1` instrumentation. However, **duration and token estimates are plausibly obtainable without any `renmark/**` code change at all**: wall-clock duration can be measured externally (the benchmark harness times the whole scenario run from outside the process), and token counts are visible in the host's own turn-by-turn accounting (Claude Code / Codex CLI already report token usage per response) — meaning the *harness* running WP-5, not `renmark/**` itself, may be able to capture 2 of the 5 gaps externally, further narrowing what stage 2 needs to touch.

**Recommendation for the next gate (as corrected by Owner, 2026-08-01):** WP-4 stage 2 (instrumentation design) scopes to just **replans** and **dispatch-wave/worker-dispatch granularity** — the two gaps that genuinely can't be observed from outside the process. Duration and token estimates are captured by the external benchmark harness itself (no `renmark/**` change needed). Test-execution counts are captured from the harness's own command log (i.e. the WP-5 harness counts how many times *it itself* invokes pytest/verifier commands) — **not** derived from `.renmark/analytics/` task-run row counts, which count tasks, not raw test/verifier subprocess invocations (Owner correction: the row-count proxy I originally proposed conflates two different things).

**Owner-confirmed scope.** See `instrumentation-design.md` for the stage-2 design covering replans + dispatch-wave granularity.

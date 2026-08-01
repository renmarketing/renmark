# R-0.1 / WP-5 — Benchmark Comparison Against R-0.0 Baseline

**Executed:** 2026-08-01. Budget approved by Owner via `AskUserQuestion`
("proceed with this budget"): ≤2 invocations, ≤40,000 tokens, ≤10 minutes,
one pass, disposable worktree, never merged.

## What this demonstrates

The primary, qualitative result: R-0.1's Layer B scope enforcement
(`renmark.fast_path.verify_worker_scope`) ran for real, independently of the
subagent, against the subagent's actual `git diff --name-status` output —
and passed. This is the first time this mechanism has run against a live
Worker rather than only against synthetic unit-test fixtures (WP-4's 16
`test_fast_path.py` cases used constructed git repos, not a real subagent).

## What happened

1. Disposable worktree cut from `main` HEAD (`8589315`, R-0.1/WP-4's commit).
2. `claude_agent.build_fast_path_agent_dispatch()` composed the real dispatch
   prompt for R-0.0's exact Scenario A task text (re-used verbatim — the test
   it adds doesn't exist on `main`, since R-0.0's own Scenario A run was
   itself in a disposable, discarded worktree).
3. One live subagent dispatched with that exact prompt.
4. After completion, independently verified (not trusting the subagent's own
   report):
   - `git status --porcelain` / `git diff --stat` in the worktree: only
     `tests/test_hosts.py` changed.
   - `renmark.fast_path.verify_worker_scope(scope, worktree, base_sha)`
     called directly: **PASSED**, zero violations.
   - `pytest tests/test_hosts.py` re-run independently: 14/14 passed.
5. Worktree removed.

## Budget

| Metric | Ceiling | Observed | Utilization |
|---|---|---|---|
| Invocations | ≤2 | 1 | 50% |
| Wall-clock | ≤10 min | 21.0s | 3.5% |
| Tokens | ≤40,000 (target) | 41,260 | **103.2% — over target by 1,260 tokens (3.2%)** |

The token target was modestly exceeded. Flagged here rather than rounded
away or omitted. It does not trip either hard ceiling (invocations,
wall-clock) and no circuit breaker fired.

## Comparison to R-0.0's Scenario A

| Metric | R-0.0 (baseline) | R-0.1 (fast path) | Delta |
|---|---|---|---|
| Agent invocations | 1 | 1 | 0 |
| Subagent-reported tokens | 29,839 | 41,260 | +38.3% |
| Wall-clock | 28.5s | 21.0s | −26.3% |
| Test executions | 1 | 1 | 0 |

**This is not a controlled A/B, and is not presented as one:**
- Different starting commits (R-0.0: `173542e`; this run: `8589315`, ~10
  commits and R-0.1's own WP-1–WP-4 artifacts later) — the repository itself
  is not identical between the two measurements.
- The fast-path prompt is longer and more structured than the plain
  non-fast-path prompt used in R-0.0 (explicit scope enumeration, explicit
  delete/rename and no-nested-dispatch language). The token increase is
  plausibly attributable to that prompt overhead rather than worse Worker
  behavior, but a single sample per condition cannot separate the two
  causes.
- n=1 per condition, matching R-0.0's own one-pass-per-scenario budget — not
  statistically powered for a real behavioral claim either way.

## Verdict

**PASS**, with a caveat: the qualitative goal (real, independently-run scope
enforcement, distinct from Worker self-report, exercised end-to-end against
a live subagent) is demonstrated. The quantitative token/time deltas versus
R-0.0 are noisy at n=1 and should not be cited as proof the fast path is
cheaper or more expensive than the existing flow — that would need a larger,
controlled sample, which is out of this WP-5's approved budget and scope.

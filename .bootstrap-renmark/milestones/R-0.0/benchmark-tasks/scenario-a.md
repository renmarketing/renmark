# Benchmark Scenario A — Small Local Change

Part of R-0.0/WP-3. Defines the task by construction so re-running it is expected to land within the stated tolerance — see `benchmark-budget-and-circuit-breakers.md`'s "Reproducibility" section for why this replaces an empirical rerun.

**Executed 2026-08-01 as part of WP-5.** Result: passed cleanly. See `.bootstrap-renmark/metrics/baseline-scenario-a.json` and `baseline-report.md`.

## Fixed starting state

- **Repository:** `/home/renmark/projects/renmark`
- **Starting commit:** `173542ee4d46f903a138c27b6dab5c96357b0909` (`fix-interaction-name-askuserquestion-explicitly`, current `main` HEAD as of WP-3 drafting)
- **Branch:** a fresh isolated worktree/branch cut from the starting commit, e.g. `benchmark/scenario-a-run-1` — never the R-0.0 release branch itself (see "Isolation" below)

## Exact task text (verbatim prompt to give the agent)

> In `tests/test_hosts.py`, add one new test case verifying that `HostKind.UNKNOWN`'s capabilities have `selector_available == False`. Follow the existing test style in that file. Do not modify `renmark/hosts.py` or any other file.

## Scoring rubric

| Criterion | Pass condition |
|---|---|
| Scope | Only `tests/test_hosts.py` was modified |
| Correctness | The new test actually asserts `capabilities_for(HostKind.UNKNOWN).selector_available is False` (or equivalent) and passes when run |
| No regression | Full `tests/test_hosts.py` file still passes after the addition |
| Completion | Agent reports done without requiring a follow-up clarification from the operator |

## Budget (per `benchmark-budget-and-circuit-breakers.md`)

- Max 2 model/agent invocations
- Max 10 minutes wall-clock
- Target ≤40,000 estimated tokens (context + output combined)
- Circuit breakers per that document apply unchanged

## Isolation (flagged for Owner confirmation before WP-5, not assumed)

R-0.0's own `contract.yaml` prohibits touching `renmark/**`/`plugin/**` **for R-0.0's own release scope**. This scenario, by design, produces a real (if trivial) code change to measure genuine current-system behavior — that change is not part of R-0.0's deliverables. Proposed resolution: run each scenario in a disposable worktree/branch, capture the measurement, then discard the branch (do not merge). **Owner-confirmed** ("Confirmed — disposable worktree/branch") and executed as described.

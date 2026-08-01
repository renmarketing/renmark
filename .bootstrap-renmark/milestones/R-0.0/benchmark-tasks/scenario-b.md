# Benchmark Scenario B — Normal Feature

Part of R-0.0/WP-3. See `scenario-a.md` for the shared reproducibility-by-construction rationale and the isolation caveat (applies identically here — not repeated in full below).

**Executed 2026-08-01 as part of WP-5.** Result: task-authoring flaw found — the `--json` flag already existed at the starting commit, so this scenario's low resource usage is not representative "normal feature" baseline data. See `.bootstrap-renmark/metrics/baseline-scenario-b.json` (`evidence_quality_caveat`) and `baseline-report.md`.

## Fixed starting state

- **Repository:** `/home/renmark/projects/renmark`
- **Starting commit:** `173542ee4d46f903a138c27b6dab5c96357b0909` (same as Scenario A)
- **Branch:** a fresh isolated worktree/branch, e.g. `benchmark/scenario-b-run-1`

## Exact task text (verbatim prompt to give the agent)

> Add a `--json` flag to `renmark doctor` that outputs the diagnosis as machine-readable JSON (a list of check objects: `name`, `status` [pass/warn/fail], `detail`, `fix_cmd` if present) instead of the default prose report. Keep the existing prose output as the default when `--json` is not passed. Add a test covering the JSON output shape. Modify only `renmark/doctor.py` and its corresponding test file.

## Scoring rubric

| Criterion | Pass condition |
|---|---|
| Scope | Only `renmark/doctor.py` and its test file modified |
| Correctness | `renmark doctor --json` produces valid JSON matching the specified shape; default (no flag) behavior unchanged |
| No regression | Full existing `renmark doctor` test suite still passes |
| Test coverage | A new test exercises the `--json` path specifically |
| Completion | Agent reports done without requiring a follow-up clarification |

## Budget (per `benchmark-budget-and-circuit-breakers.md`)

- Max 6 model/agent invocations
- Max 25 minutes wall-clock
- Target ≤120,000 estimated tokens
- Circuit breakers per that document apply unchanged

## Isolation

Same disposable-worktree approach as Scenario A — Owner-confirmed and executed.

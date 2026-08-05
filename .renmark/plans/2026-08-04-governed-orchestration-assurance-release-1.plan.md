# Plan: governed-orchestration-assurance — Release 1 (Baseline and compatibility coverage)

Program `governed-orchestration-assurance` (`.renmark/state/program.json`),
stage `release-1-baseline-compat-coverage`, serves REQ-30. Turns
`.renmark/rethink/governed-orchestration-assurance/baseline.md`'s 9
compatibility checks into runnable pytest regressions and replaces
`.renmark/memory/orchestration-baseline.md`'s still-unpopulated REQ-30
scenario table with real, already-observed numbers (mined from
`.renmark/analytics/*.jsonl` and the 2026-08-02 audit) rather than spending
fresh tokens on live pipeline runs. Test-only + doc-only; no production code
moves.

### Task 1: compat regression tests (fill genuine gaps, don't duplicate)
- **mode:** A
- **target:** tests/test_governed_orchestration_baseline_compat.py
- **complexity:** medium
- **executor:** codex
- **role:** test-writer
- **parallel_group:** 1
- **est_tokens:** 1800
- **est_cost_usd:** 0.054
- **verifier:** pytest tests/test_governed_orchestration_baseline_compat.py -q
- **serves:** REQ-30
- **spec:**
  Reuse check confirmed 7 of the 9 protected behaviors in
  `.renmark/rethink/governed-orchestration-assurance/baseline.md` §4 already
  have runnable pytest coverage: fast_path 5-signal contract +
  `verify_worker_scope` in `tests/test_fast_path.py`; `ledger.VERDICTS` +
  `check_dispatch_independence` in `tests/test_ledger.py` /
  `tests/test_ledger_wiring.py`; `complete_worker_task`'s no-self-approval
  gate in `tests/test_task_tracking*.py`; `assert_metadata_only` in
  `tests/test_context.py`; REQ-30 structural guarantees in
  `tests/test_orchestration_efficiency_requirement.py`. Do NOT re-write
  these — that would create duplicate, divergent coverage.

  This task adds only the 2 genuinely missing pieces, plus a thin index so
  the 9-check compat contract is traceable from one place:

  1. **Pytest count floor** (baseline.md check #1, currently missing
     anywhere in `tests/`): a new test that runs `pytest -q` as a subprocess
     (same pattern as `tests/test_r0_2_dispatch_regression_baseline.py`) and
     asserts `failed == 0` and `passed >= 1970` — do not hardcode the exact
     skip count (31); only assert the floor, since baseline.md allows the
     skip count to shift with a documented reason.
  2. **`renmark:inspector` read-only allowlist** (baseline.md check #9,
     no dedicated test yet — only a precedent pattern for `reviewer.md` in
     `test_r0_2_dispatch_regression_baseline.py`): assert
     `plugin/agents/inspector.md`'s declared `tools:` frontmatter excludes
     `Write`/`Edit`, and that `renmark/subagent_profiles.py`'s inspector
     entry (`~line 146`) scopes `allowed_targets` to `.renmark/ledger/**`.
  3. **Index docstring**: a module docstring listing all 9 baseline.md
     checks, each with a one-line pointer to the test file/function that
     already covers it (checks 2–8) or is added here (checks 1, 9) — so a
     future release can grep this one file to find every compat guard
     instead of re-deriving the list from baseline.md each time.

  Do not modify any file outside this new test file, and do not edit any of
  the existing test files named above.

### Task 2: baseline scenario capture from observed data
- **mode:** B
- **target:** .renmark/memory/orchestration-baseline.md
- **complexity:** medium
- **executor:** sonnet
- **role:** researcher
- **parallel_group:** 1
- **est_tokens:** 1200
- **est_cost_usd:** 0.0336
- **verifier:** grep -q "Scenario capture" .renmark/memory/orchestration-baseline.md
- **serves:** REQ-30
- **spec:**
  Replace the "still needs to be captured" open item's four blank scenario
  rows with real numbers mined from data that already exists on disk —
  do NOT invoke `/renmark:start`, `/renmark:feature`, `/renmark:orchestrate`,
  or `/renmark:rethink` fresh; that would spend new tokens and this task's
  cost/scope does not include a live-pipeline run.

  Read `.renmark/analytics/task-runs.jsonl`, `.renmark/analytics/events.jsonl`,
  `.renmark/analytics/summary.json`, and
  `.renmark/audits/orchestration-baseline-audit-2026-08-02.md` (already cited
  in the file you're editing). That audit already mined real dispatch-count/
  verification/gate-timestamp data for two scenarios: Feature/Fix
  (`add-rethink-pipeline-skill`, 2026-08-02) and Orchestrate (M2 milestone +
  R-0.2/R-0.3, 2026-07-30/08-01). Pull the concrete numbers it found
  (tokens where `measured: true`, dispatch counts, gate counts) into a new
  dated `## Scenario capture — 2026-08-04` section, in the table format the
  file already specifies (Scenario / tokens / wall-clock / dispatch count /
  Owner-gate count / notes).

  For Start and Rethink: the audit already established these are honestly
  `unknown` (Start predates telemetry by 16 days; Rethink had never been
  invoked as of that audit). Re-check whether that's still true — if
  `/renmark:rethink` has since been run for real (this very
  `governed-orchestration-assurance` rethink is itself one execution),
  mine its dispatch/token data from `.renmark/analytics/` the same way; if
  no measurable data exists for a scenario, record it as `unknown` with a
  one-line reason — never fabricate a number.

  Add machine-readable provenance to the new section: source files read,
  date, and a one-line note that fresh-pipeline scenario capture (for any
  scenario still `unknown`) remains a distinct future action requiring its
  own cost-preview + Owner go-ahead, per this file's existing rule.

---

## Cost preview

| Task | Executor | Role | Est. tokens (incl. overhead) | Est. cost |
|---|---|---|---|---|
| 1. compat regression tests | codex | test-writer | 1,800 | $0.054 |
| 2. baseline scenario capture | sonnet | researcher | 11,200 | $0.0336 |

**Total tasks:** 2 (1 parallel group)
**Total tokens (incl. ~10k agent overhead on the sonnet task):** ~13,000
**Total cost:** **$0.09**
**Executors:** codex×1, sonnet×1 (no haiku/opus/fable)

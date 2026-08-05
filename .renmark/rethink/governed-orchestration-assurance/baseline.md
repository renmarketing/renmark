---
artifact_type: rethink-baseline
schema_version: 1
created_at: 2026-08-04T00:00:00Z
source_sha: e6898917ddf3a30505bb01b1b0569c28a187d792
related_plan: .renmark/rethink/governed-orchestration-assurance/intake.md
generator: sonnet
stale_after: null
dependency_refs:
  - .renmark/rethink/governed-orchestration-assurance/intake.md
  - .renmark/memory/orchestration-baseline.md
  - .renmark/analytics/summary.json
  - renmark/fast_path.py
  - renmark/ledger.py
  - renmark/task_tracking.py
  - renmark/dispatch.py
---

# Stage 2 — Behavioral baseline: governed-orchestration-assurance

Documents what **currently works and must not break**, independent of
whether it is the "right" behavior per the proposal. Not a PRD compliance
check (that is Stage 3).

## 1. Real current test suite (measured, not historical)

```
pytest -q
```
Result: **1970 passed, 31 skipped in 62.04s**, 0 failed. (`s` = skip markers
at collection start, all pre-existing skips, no xfail/xpass observed.)
This supersedes any test-count figure quoted in memory files or the Owner's
proposal — per intake.md's constraint, historical counts are context only.

## 2. Lint / type-check

Tools resolved from PATH (`ruff`, `mypy` — both present in this environment,
via an adjacent project's `.venv/bin`, but ran correctly against this repo's
`renmark/`/`tests/` trees):

- `ruff check .` → **17 errors** (10 auto-fixable, 6 more via
  `--unsafe-fixes`). All observed are pre-existing style/hygiene issues, not
  correctness bugs: unused imports (`pytest` in
  `tests/test_r0_2_dispatch_regression_baseline.py`, `renmark.fast_path` in
  `tests/test_wp8_scope_wiring.py`), an unsorted import block in
  `tests/test_wp8_r008_wiring.py`, and similar. No `renmark/*.py` production
  file flagged beyond the ones listed.
- `mypy .` → **4 errors, 84 source files checked**:
  - `renmark/ledger.py:283` — `Returning Any from function declared to
    return "list[str]"` (`no-any-return`)
  - `renmark/subagent_gate.py:309`, `:311` — `Missing type arguments for
    generic type "dict"` (`type-arg`)
  - `renmark/cli/_run_lifecycle.py:71` — `Returning Any from function
    declared to return "set[int]"` (`no-any-return`)

None of these 21 lint/type findings are new regressions from this stage —
they are the current steady state. They are recorded as-is; this
transformation is not required to fix them, but must not add to the count
in files it touches without a documented reason.

## 3. Current observable outputs / acceptance examples

### 3a. `/renmark:orchestrate` end-to-end (task creation → dispatch → verification → completion)

Governed by `renmark/dispatch.py` (1052 lines) + `renmark/task_tracking.py`
(436 lines) + `renmark/ledger.py` (558 lines):

1. **Wave planning**: `dispatch_wave` (`renmark/dispatch.py:138`) validates a
   wave of tasks (`validate_wave` checks `context_files` don't overlap
   in-wave targets — the same invariant `fast_path.classify_fast_path`
   Signal 4 re-checks independently for the fast path).
2. **Dispatch packet construction**: `build_subagent_input`
   (`renmark/dispatch.py:606`) builds the per-task dispatch packet —
   required-skill **metadata only** (name + pointer), enforced by
   `context.assert_metadata_only` (REQ-20/G11 contract): a subagent never
   receives full skill bodies, only task spec + file paths + upstream
   artifact pointers + verifier expectations.
3. **Isolated execution**: `dispatch_task_isolated`
   (`renmark/dispatch.py:912`) runs one task in an isolated subagent/executor
   context; the orchestrator does not carry implementation context between
   tasks unless the dependency graph requires it.
4. **Task-tracking wiring** (REQ-31, `renmark/task_tracking.py`): each
   dispatch gets a `TaskRecord` (`create_or_reuse_task` →
   `mark_in_progress` → `complete_task`/`record_failure`/`record_blocker`).
   `complete_worker_task` (line 342) is the **no-self-approval enforcement
   point**: it requires a separate, already-`completed` verification task
   whose `dispatch_identity` is provably independent of the worker's — it
   calls `ledger.check_dispatch_independence` and raises
   `SelfApprovalError` if the verifier's identity is empty or equal to the
   worker's. A worker cannot mark its own task complete by self-attesting.
5. **Ledger emission** (`renmark/ledger.py`): `WorkOrder` / `WorkResult` /
   `InspectionReport` / `Escalation` dataclasses, each with a
   `validate_*` schema-check function and one append-only JSONL sink
   (`append_ledger_event`, `ledger_path`). `InspectionReport.verdict` is
   constrained to `VERDICTS = ("pass", "fail", "escalate")` (line 444).
6. Completion is `PASS`/`FAIL`/`SKIP` (or `pass`/`fail`/`escalate` at ledger
   level) — the orchestrator aggregates only that verdict, artifact path,
   token count, dependency status, and next-wave readiness; it never
   re-absorbs subagent transcript, generated code, diff, or long reasoning
   (per `CLAUDE.md`'s orchestrate-isolation contract, code-verified here).

### 3b. Fast-path classifier — current accept/reject (`renmark/fast_path.py`, R-0.1, WP-1/WP-2)

`classify_fast_path(tasks)` is a **pure, deterministic, no-model-call**
function. ALL 5 signals must pass for `eligible=True`; on any failure it
returns every failed signal name (not just the first), for a complete
ledger justification:

1. **`scope_size`** — at most `MAX_FAST_PATH_FILES = 2` distinct explicitly
   named targets; any glob/wildcard/directory target (`*`, `?`, trailing
   `/`) fails.
2. **`action_type`** — Task mode must be `"A"` (create) or `"B"` (modify);
   delete/rename cannot be expressed as a Task at all (structural, not
   runtime-checked here — caught instead by `verify_worker_scope`'s "D"/"R"
   rule below).
3. **`production_target`** — no target under `renmark/**` or `plugin/**`.
4. **`cross_file_dependency`** — no task's `context_files` may overlap this
   wave's target set.
5. **`verifier_not_single_command`** — verifier must be non-empty and
   contain no shell chain operator (`&&`, `||`, `;`, `|`).

Post-execution enforcement (Layer B, deterministic, distinct from Layer A's
host-side live permission prompt which Python cannot implement):
`verify_worker_scope(scope, repo, base_sha)` runs a real, read-only
`git diff --name-status base_sha..HEAD` — **never** the Worker's
self-reported `touched_files`. Any path outside `scope.allowed_paths` is a
violation (`out_of_scope`); any `D` (delete) or `R` (rename) status is
**always** a violation on the fast path regardless of path
(`disallowed_action`). A git failure degrades to a **failing** verdict
(`diff_unavailable`), never a silent pass. A failing `ScopeVerdict` means
"do not commit/merge — escalate," per the module's documented call
sequence.

### 3c. Current Inspector (R-0.4) — what it verifies and how

- **Dispatch-independence enforcement**: `ledger.check_dispatch_independence`
  raises `DispatchIndependenceError` unless the inspector's dispatch
  identity is non-empty AND different from the work result's dispatch
  identity. Empty inspector identity = "independence unproven," never
  "independence assumed." This is a hard raise, not a log-and-continue.
- **Verdict emission**: `ledger.emit_inspection_verdict(..., verdict=...)`
  is the only path that may write an `InspectionReport`; `verdict` is
  normalized (stripped/lowercased) and must be one of `VERDICTS = ("pass",
  "fail", "escalate")` or it raises.
- **Role wiring**: `renmark:inspector` (`plugin/agents/`) is declared
  read-only (`Read, Grep, Glob, Bash` — no `Write`/`Edit`); its
  `allowed_targets` in `renmark/subagent_profiles.py:146` is
  `.renmark/ledger/** (read-only; emits verdicts via
  ledger.emit_inspection_verdict only)`.
- **Consumer**: `task_tracking.complete_worker_task` is the one production
  call site chaining these together — it requires a completed, independent
  verification task before a worker task can close, using
  `check_dispatch_independence` under the hood.

## 4. Compatibility contract — MUST stay green through this transformation

These are concrete, mechanically checkable behaviors this rethink's later
stages/releases are held to (protected-behavior contract):

1. **`pytest -q` stays at 1970 passed / 0 failed** (skip count of 31 may
   shift only with an explicit, documented reason — an unexplained skip
   delta is a regression signal).
2. **`fast_path.classify_fast_path`**'s 5-signal contract (scope_size ≤2
   named targets no globs, action_type A/B only, no `renmark/**`/`plugin/**`
   target, no cross-file `context_files` overlap, single-command verifier)
   — extend only, never replace with a second fast path (per intake.md's
   protected-behavior list).
3. **`fast_path.verify_worker_scope`**'s Layer B semantics: comparison
   against real `git diff`, never `touched_files`; `D`/`R` always a
   violation; unverifiable diff degrades to `passed=False`, never
   `passed=True`.
4. **`ledger.check_dispatch_independence`**: empty inspector identity always
   raises; identical worker/inspector identity always raises; this is the
   sole no-self-approval enforcement primitive and must not be bypassable
   by a new dispatch path that skips calling it.
5. **`ledger.VERDICTS = ("pass", "fail", "escalate")`** and
   `emit_inspection_verdict`/`validate_inspection_report` as the only
   schema-legal way to write an `InspectionReport` — a new inspection
   surface must reuse or supersede this, not fork a parallel verdict
   vocabulary silently.
6. **`task_tracking.complete_worker_task`**'s no-self-approval gate
   (`MissingVerificationError`/`SelfApprovalError`/`MissingEvidenceError`)
   stays the enforcement point for REQ-31 task completion; a worker must
   never be able to mark itself `completed` without an independent,
   already-`completed` verification task.
7. **REQ-20 metadata-only dispatch**: `dispatch.build_subagent_input` +
   `context.assert_metadata_only` — subagent dispatch packets carry
   required-skill metadata (name + pointer), never full skill bodies.
8. **REQ-30 orchestration-baseline structural guarantees** (see §5 below):
   ≤5-line/≤300-token orchestrator-visible output per task; deterministic-
   first gate before model calls; one bounded worker per task by default;
   cheapest-capable-model routing; fast-path skip of full ceremony; `/renmark:resume`
   as a single ≤1KB read with zero LLM calls and no re-dispatch of completed
   work.
9. **`renmark:inspector` role stays read-only** (no `Write`/`Edit` tools) and
   scoped to `.renmark/ledger/**`, emitting verdicts only through
   `ledger.emit_inspection_verdict`.

Count: **9 compatibility checks** identified (some, e.g. #1–#6, are directly
executable as regression tests today via the existing test suite files
named `test_r0_2_dispatch_regression_baseline.py`,
`test_wp8_scope_wiring.py`, `test_wp8_r008_wiring.py`, etc.; #7–#9 are
structural/code-review-checkable).

## 5. Performance/cost/quality baseline

`.renmark/memory/orchestration-baseline.md` (REQ-30, pinned to `v0.39.7` /
`d9cccc5`) documents the **qualitative** baseline and explicitly states its
own open item: it does **not yet contain measured token/wall-clock/
dispatch-count numbers** for the four representative scenarios (Start,
Feature/Fix, Orchestrate, Rethink) — capturing those requires actually
running them, which the file itself flags as real-token spend requiring a
cost preview + go-ahead, not something to fabricate.

Verified against current repo state (this stage did not invent new numbers,
only checked what's already recorded):
- `.renmark/analytics/summary.json` — generated **2026-07-06**, stale
  relative to `source_sha` history (many commits since); it records 107
  historical tasks (106 passed, 0 failed, 1 skipped), 12 shipped features,
  23 releases, and token totals by executor/model — but explicitly under
  `"source": "local-observed"`, i.e. mined from real runs, not fabricated.
  This is a *point-in-time* dataset, not a live baseline for this
  transformation's scenarios.
- `.renmark/analytics/task-runs.jsonl` — 140 lines, most recent entries
  dated **2026-08-02**, `measured: true/false` mixed (some `total_tokens: 0`
  with `measured: false`, e.g. the codex-executed "escalation-check tests"
  row) — confirming the orchestration-baseline audit's headline finding
  still holds: per-run token/wall-clock telemetry remains **partially
  unmeasured** (some rows measured, some `total_tokens: 0`/`measured:
  false`).
- No new Start/Feature/Orchestrate/Rethink scenario capture exists beyond
  what `orchestration-baseline.md` already logs under "Update on
  `milestone_context_checkpoint`" — the four-scenario numeric baseline table
  in that file is still unpopulated as of this stage.

**Holding rule**: this transformation must not silently regress the
*qualitative* REQ-30 guarantees in §4 item 8, and any change to routing,
context limits, dispatch policy, model escalation, Owner-gate frequency, or
artifact-reuse behavior requires the REQ-30 PRD UPDATE-gate path — but there
is currently no committed *numeric* baseline (tokens/wall-clock/dispatch
count) to regress against for Start/Feature/Orchestrate/Rethink; populating
that table remains a distinct, not-yet-done prerequisite noted in the
memory file itself, not something this stage should invent.

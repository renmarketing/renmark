# Plan — Release 13: Durable-events field completeness + orphan-detection spike (#24) + analytics reconciliation

Implements Release 13 of the `governed-orchestration-assurance` transformation
program (`.renmark/rethink/governed-orchestration-assurance/roadmap.md`),
gated on Release 3's reconciled `WorkOrder` schema. Per this program's
established Release 8 pattern (risk-tier spike), Task 1 is a bounded,
evidence-only SPIKE: it self-benchmarks renmark's own resume/recovery
correctness against a handful of deliberately-interrupted runs, reusing
`heartbeat.py`'s existing `PAUSED`/usage-limit-pause path as the test
harness, and produces a scenario table (pass/fail on "no duplicate, no
orphan") plus a recommendation. It does **not** decide whether any surfaced
gap is acceptable — that is an Owner decision made after this plan's Task 1
lands and is reviewed. **This plan does not include a "fix whatever gaps the
spike finds" implementation task** — that scope is necessarily unknown until
Task 1's findings exist. If Task 1 finds a genuine orphan/duplicate-
integration gap, a SEPARATE follow-up plan (capped at ~2 sessions per the
roadmap, escalated to the Owner if that proves insufficient) will be created
after Task 1 lands and is reviewed. **Note for the Owner:** the roadmap's
Release 13 section (as currently on disk, revised 2026-08-05 for peer-review
Gap 5) additionally describes a bounded "(a2)" committed implementation step
inside this same release, budget-capped at 2 sessions, with AC-11 closure
gated on it. This plan deliberately does NOT include that step (per this
plan's explicit dispatch instructions, which mirror the Release 8 spike-first
pattern instead) — flagging this as a live conflict between the roadmap text
and this plan's actual scope for Owner reconciliation before AC-11 is
considered closed.

Tasks 2-3 are independent of the spike's outcome and are planned/dispatched
now: Task 2 adds additive `schema_version`/`attempt_id`/`correlation_id`
fields to the ledger event kinds that don't yet carry them (`WorkOrder`
already has `schema_version`/`correlation_id` from Release 3 — this task adds
`attempt_id` to it and all three fields to `WorkResult`, `InspectionReport`,
`Escalation`). Task 3 reconciles `analytics.py` — investigation found it is
**not** a full duplicate of `ledger.py`: `analytics.py`'s four ledgers
(`task-runs`, `feature-runs`, `loop-runs`, generic `events`) track cost/
token/success telemetry that `ledger.py` doesn't carry, while `ledger.py`
tracks dispatch-governance lifecycle (`work_order`/`work_result`/
`inspection_report`/`escalation`) that `analytics.py` doesn't carry. The
reconciliation is therefore additive and narrow: a new `analytics.py` reader
that sources escalation counts and inspection-verdict pass/fail/escalate
counts from `ledger.py` (for Release 14's guardrail metrics) instead of a
future release inventing a second escalation-tracking mechanism inside
`analytics.py`'s own `events.jsonl`. Task 2 lands before Task 3 so the new
ledger fields are on disk before analytics' reader is tested against them.
Tasks 4-5 are tests: backward-compatibility + new-field coverage for
`ledger.py`, and reconciled-reader coverage for `analytics.py`.

## Tasks

### Task 1: Orphan-detection spike finding (evidence only, no code changes)
- **mode:** A
- **target:** .renmark/rethink/governed-orchestration-assurance/release-13-orphan-detection-spike-finding.md
- **complexity:** hard
- **executor:** sonnet
- **role:** researcher
- **parallel_group:** 1
- **est_tokens:** 3000
- **est_cost_usd:** 0.04
- **verifier:** test -f .renmark/rethink/governed-orchestration-assurance/release-13-orphan-detection-spike-finding.md && grep -qi "scenario table" .renmark/rethink/governed-orchestration-assurance/release-13-orphan-detection-spike-finding.md && grep -qi "no duplicate" .renmark/rethink/governed-orchestration-assurance/release-13-orphan-detection-spike-finding.md
- **serves:** AC-11
- **spec:**
  Bounded spike, one session, no production code changes — this task must
  not edit any `.py` file. Self-benchmark renmark's own resume/recovery
  correctness against deliberately-interrupted runs of `renmark-execute`
  orchestration, favoring SIMULATION over real live-process kills for
  safety and reproducibility (construct/inspect the on-disk state files a
  real interruption would leave, rather than actually killing a live
  `renmark-execute` process, unless you judge a specific scenario safe to
  reproduce for real in this sandboxed repo — your call, but default to
  simulation).

  Read first, to ground the harness design: `renmark/heartbeat.py` in full
  (its `PAUSED`-file / `resume_after` pause-and-resume contract is the
  reusable test-harness shape — `auto_resume` shells out to
  `renmark-execute --resume`, which is exactly the recovery path this spike
  is benchmarking); `renmark/cli/_engine.py`'s `_setup_resume_state` and
  `_cross_check_skip_list` functions (the resume skip-list logic that
  decides which already-committed tasks to skip on re-entry — the
  documented "single most expensive observed failure mode" this spike is
  probing for regressions in); the on-disk state shape at
  `.renmark/state/PAUSED`, `.renmark/state/pipeline.json` (or equivalent
  runtime state file — confirm the exact current filename by reading
  `_engine.py`/`renmark/state/pause.py`), and `.renmark/state/handoffs/` (a
  real interruption's `git log` + resume-state footprint on this very
  repo — recent examples are visible under `.renmark/state/handoffs/`).

  Design 3-5 deliberately-interrupted scenarios covering distinct
  interruption points in the wave/dispatch/ledger lifecycle, for example:
  (1) kill mid-wave (interrupted after task N of a wave commits but before
  the wave's remaining tasks dispatch); (2) kill mid-commit (interrupted
  after a subagent's file edits land but before the orchestrator's commit
  step runs); (3) kill after a ledger `work_order` event is appended but
  before its matching `work_result` event; (4) kill during
  `_cross_check_skip_list` itself (a stale/partial skip-list re-entering a
  live run); (5) (optional, if time permits) kill during a `PAUSED`
  usage-limit window and resume via `heartbeat.auto_resume`. For each
  scenario, construct or identify representative real/simulated state
  (existing `.renmark/state/handoffs/*.brief.md`, `.renmark/ledger/
  events.jsonl` entries, `git log`, and/or hand-built fixture state files
  in a scratch location — never mutate this repo's real `.renmark/state/`
  in a way that could corrupt an in-flight run) and evaluate, on resume,
  whether the task/commit in question is (a) correctly skipped exactly
  once (no duplicate dispatch/commit) and (b) never silently dropped as an
  "orphan" (a task the current plan still expects but the skip-list
  incorrectly treats as done, or vice versa — a task that ran but whose
  ledger/commit evidence never gets picked up on resume).

  Produce a scenario table (columns: scenario name, interruption point,
  state constructed/simulated, expected resume behavior, observed resume
  behavior, pass/fail on "no duplicate, no orphan") and a written
  recommendation. The recommendation must classify the overall finding as
  one of: "no gaps found — AC-11 closable on this evidence alone", "gaps
  found — [name them], recommend a follow-up plan capped at ~2 sessions
  per the roadmap", or "gaps found that appear to exceed a 2-session fix
  budget — recommend Owner escalation with this evidence attached". Do NOT
  attempt to fix any gap found — report and recommend only.

  Write the finding to the target path with: (1) a top metadata block
  matching this program's other artifacts (`artifact_type:
  spike-finding`, `schema_version: 1`, `created_at`, `source_sha`,
  `related_plan:
  .renmark/plans/2026-08-05-governed-orchestration-assurance-release-13.plan.md`,
  `generator: sonnet`); (2) the scenario table; (3) the recommendation
  classification above, stated explicitly; (4) enough evidence detail
  (state snapshots, ledger excerpts, git log excerpts) that a human or a
  follow-up planning task can act on it without re-running the spike.

### Task 2: Additive `schema_version`/`attempt_id`/`correlation_id` fields
- **mode:** B
- **target:** renmark/ledger.py
- **complexity:** medium
- **executor:** sonnet
- **role:** code-implementer
- **parallel_group:** 2
- **est_tokens:** 1200
- **est_cost_usd:** 0.03
- **verifier:** python3 -c "import dataclasses; from renmark import ledger; wr={f.name for f in dataclasses.fields(ledger.WorkResult)}; ir={f.name for f in dataclasses.fields(ledger.InspectionReport)}; es={f.name for f in dataclasses.fields(ledger.Escalation)}; wo={f.name for f in dataclasses.fields(ledger.WorkOrder)}; need={'schema_version','attempt_id','correlation_id'}; ok = need <= wr and need <= ir and need <= es and need <= wo and ledger.VERDICTS == ('pass','fail','escalate'); print('OK' if ok else 'FAIL'); assert ok" | tail -1 | grep -q OK && python3 -m py_compile renmark/ledger.py
- **serves:** AC-11
- **spec:**
  `WorkOrder` already has `schema_version: int = 1` and `correlation_id: str
  | None = None` (Release 3). Add `attempt_id: str | None = None` to
  `WorkOrder` as a new additive field (append after `idempotency_key`, do
  not reorder existing fields — this is a dataclass and field order
  matters for any positional construction, though this codebase's
  convention is kwargs-only per `work_order_for_task`).

  Add all three fields — `schema_version: int = 1`, `attempt_id: str |
  None = None`, `correlation_id: str | None = None` — to `WorkResult`,
  `InspectionReport`, and `Escalation` (append at the end of each
  dataclass body). Purpose: `schema_version` lets a future reader
  distinguish old-shape rows from new-shape rows without guessing;
  `attempt_id` lets a retried/repaired dispatch's events be told apart
  from the original attempt; `correlation_id` ties an event back to its
  originating `WorkOrder.correlation_id` (Release 3's placeholder field) so
  a work_order → work_result → inspection_report → escalation chain for
  one dispatch can be reconstructed by matching `correlation_id` across
  event kinds.

  Update `validate_work_result()`, `validate_inspection_report()`, and
  `validate_escalation()` to accept the two new optional string fields via
  the existing `_check_opt_str` helper (do not add new validation
  helpers) and `schema_version` should NOT be validated as required
  (already-required-field style would break old rows; skip validating its
  type explicitly unless you also confirm doing so cannot reject any
  currently-valid payload — safest is to add no validation for
  `schema_version` at all, since it already has a dataclass default and
  the validators here validate the *dict payload* on write, not read).
  `validate_work_order()` needs no change for `attempt_id`/
  `correlation_id`/`schema_version` unless you choose to add the same
  optional-field checks there for consistency — if you do, use
  `_check_opt_str`/skip `schema_version` the same way.

  **Backward compatibility is the hard constraint.** `read_ledger_events`
  (the reader) does not run these validators at all — it just
  `json.loads` each line — so old JSONL rows written before this change
  (lacking `schema_version`/`attempt_id`/`correlation_id`) already parse
  fine as plain dicts; do not change `read_ledger_events`'s behavior. Do
  not touch `append_ledger_event`, `check_dispatch_independence`,
  `emit_inspection_verdict`, `latest_verdict_for`, `classify_risk_tier`,
  `InspectionContract`, or any function/dataclass in this file outside the
  four event dataclasses and their three validators. `VERDICTS` and
  `RISK_TIERS` must remain byte-for-byte unchanged.

### Task 3: `analytics.py` reads ledger escalation/verdict data
- **mode:** B
- **target:** renmark/analytics.py
- **complexity:** medium
- **executor:** sonnet
- **role:** code-implementer
- **parallel_group:** 3
- **est_tokens:** 1400
- **est_cost_usd:** 0.03
- **verifier:** python3 -c "from renmark import analytics; import inspect; src = inspect.getsource(analytics); assert 'ledger' in src; assert hasattr(analytics, 'aggregate')" && python3 -m py_compile renmark/analytics.py
- **serves:** AC-11
- **spec:**
  Investigation finding (do not re-derive): `analytics.py` is NOT a full
  duplicate of `ledger.py`. `analytics.py`'s four ledgers
  (`task-runs.jsonl`, `feature-runs.jsonl`, `loop-runs.jsonl`,
  `events.jsonl`) track cost/token/executor/success telemetry per
  dispatch/feature/loop run — data `ledger.py` does not carry.
  `ledger.py`'s four kinds (`work_order`/`work_result`/
  `inspection_report`/`escalation`) track dispatch-governance lifecycle —
  verdicts, dispatch independence, escalation reasons — data
  `analytics.py` does not carry today. There is no field-level duplication
  to remove. The reconciliation this task performs is additive: give
  `analytics.py` a read path INTO `ledger.py`'s data so a future release
  (Release 14's guardrail metrics) can report on escalation/inspection
  outcomes without a new release inventing a second, parallel way to
  record escalations inside `analytics.py`'s own `events.jsonl` (which
  today only has generic `"kind"` strings like `"pause"`/`"rate_limit"`,
  not a structured escalation/verdict shape).

  Add a new function `_agg_ledger_guardrails(repo: str | Path) -> dict[str,
  object]` (module-private, matching this file's `_agg_features`/
  `_agg_tasks`/`_agg_loops`/`_agg_events`/`_agg_usage` naming and
  never-raise style) that calls `renmark.ledger.read_ledger_events(repo,
  kind=renmark.ledger.KIND_ESCALATION)` and `read_ledger_events(repo,
  kind=renmark.ledger.KIND_INSPECTION_REPORT)`, and returns bounded counts
  only (no raw rows — matches this module's G3 summary-boundary
  discipline): `escalations_total`, `escalations_blocking` (count where
  `blocking` is true), `inspection_verdicts` (a dict of
  `pass`/`fail`/`escalate` counts, matching `ledger.VERDICTS`), and
  `inspection_total`. Import `renmark.ledger` inside the function body
  (not at module top) to avoid introducing a new module-level import
  cycle risk between `analytics.py` and `ledger.py`, mirroring how
  `ledger.py` itself imports `subagent_gate`/`schemas` lazily inside
  functions. Never raise — wrap the ledger read in a `try/except` that
  degrades to all-zero counts on any failure (missing ledger file, import
  problem, malformed row), matching every other `_agg_*` helper in this
  file.

  Wire `_agg_ledger_guardrails(repo)`'s result into `aggregate()` under a
  new top-level `"guardrails"` key in the returned/written `summary`
  dict (add it alongside the existing `"features"`/`"tasks"`/`"loops"`
  keys — do not replace or rename any existing key). Do not wire it into
  `build_health_report()`'s returned dict yet unless doing so is a
  one-line addition consistent with the existing pattern (`
  "guardrails": summary.get("guardrails", {})` is acceptable; do not
  invent new markdown rendering in `render_health_md` beyond a single
  optional line if `guardrails` is non-empty, mirroring the existing
  `if dispositions:` / `if by_feature:` conditional-line style). Do not
  touch `record_event`, `record_task_run`, `record_feature_run`,
  `record_loop_run`, `close_feature_disposition`, or any existing
  `_agg_*` function's existing behavior/return keys — this task only adds
  the new function and wires its output into `aggregate()`.

### Task 4: Ledger field + backward-compat tests
- **mode:** A
- **target:** tests/test_ledger_field_completeness.py
- **complexity:** medium
- **executor:** codex
- **role:** test-writer
- **parallel_group:** 4
- **est_tokens:** 700
- **est_cost_usd:** 0.02
- **verifier:** pytest -q tests/test_ledger_field_completeness.py
- **serves:** AC-11
- **spec:**
  Write pytest tests against `renmark.ledger`. Cover: (1) `WorkOrder`,
  `WorkResult`, `InspectionReport`, and `Escalation` each construct with
  default values and have `schema_version`, `attempt_id`, and
  `correlation_id` attributes present (use `dataclasses.fields` or direct
  attribute access); (2) `append_ledger_event` + `read_ledger_events`
  round-trip a `WorkResult`/`InspectionReport`/`Escalation` constructed
  WITH explicit `attempt_id`/`correlation_id` values and the values
  survive the round trip (use `tmp_path` as the repo root, matching this
  test suite's existing ledger-test convention — check an existing
  `tests/test_ledger*.py` file for the exact fixture pattern before
  writing); (3) **backward compatibility**: hand-write an OLD-SHAPE JSONL
  line to `.renmark/ledger/events.jsonl` (a `work_result`/
  `inspection_report`/`escalation` dict WITHOUT `schema_version`/
  `attempt_id`/`correlation_id` keys at all, matching what a pre-Release-13
  event looked like) and assert `read_ledger_events` still parses it
  without raising and returns it as a normal dict (the missing keys simply
  absent, not defaulted-in by the reader — `read_ledger_events` is a raw
  JSON reader, it does not rehydrate dataclass defaults); (4) a guard test
  asserting `ledger.VERDICTS == ('pass', 'fail', 'escalate')` and
  `ledger.RISK_TIERS == ('low', 'medium', 'high', 'critical')` remain
  unchanged by this release.

### Task 5: Analytics ledger-reconciliation tests
- **mode:** A
- **target:** tests/test_analytics_ledger_guardrails.py
- **complexity:** medium
- **executor:** codex
- **role:** test-writer
- **parallel_group:** 4
- **est_tokens:** 600
- **est_cost_usd:** 0.02
- **verifier:** pytest -q tests/test_analytics_ledger_guardrails.py
- **serves:** AC-11
- **spec:**
  Write pytest tests against `renmark.analytics`'s new ledger-reading
  guardrail aggregation (Task 3). Use `tmp_path` as the repo root. Cover:
  (1) with no ledger file present, `analytics.aggregate(tmp_path,
  now=...)` includes a `"guardrails"` key with all-zero/empty counts and
  does not raise; (2) write real `ledger.Escalation` and
  `ledger.InspectionReport` events via
  `renmark.ledger.append_ledger_event` (2-3 escalations, a mix of
  `verdict="pass"`/`"fail"`/`"escalate"` inspection reports) into
  `tmp_path`'s ledger, then assert `analytics.aggregate(tmp_path,
  now=...)["guardrails"]` reflects the correct counts (escalation total,
  blocking count, per-verdict inspection counts, inspection total); (3) a
  malformed/corrupt ledger file (hand-write invalid JSON lines) does not
  raise from `aggregate()` — degrades to zero/empty guardrails, matching
  this module's documented never-raise contract; (4) assert `aggregate()`
  still returns its pre-existing `"features"`/`"tasks"`/`"loops"` keys
  unchanged in shape (this task is additive-only — existing summary keys
  must not regress).

## Cost Preview

| Executor | Count |
|---|---|
| sonnet | 3 |
| codex | 2 |

Total tokens (incl. ~10k Agent overhead/task for sonnet):
**~36,900 tokens**

Total cost: **~$0.14**

Parallel groups: 4 (1: orphan-detection spike → 2: ledger.py field
additions → 3: analytics.py ledger-reconciliation reader → 4: both test
tasks in parallel).

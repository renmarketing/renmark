# Plan — Release 8: Risk-tier spike (#10b) + risk-tiered `InspectionContract` + lenses

Implements Release 8 of the `governed-orchestration-assurance` transformation
program (`.renmark/rethink/governed-orchestration-assurance/roadmap.md`,
revised 2026-08-05), gated on Release 7's closed REQ-30 clause (j). This
release has a real structural split: Task 1 is a bounded, evidence-only
SPIKE (no production code changes) that designs and hand-validates a
deterministic (no-model-call) risk-tier classifier against 15-20 real past
dispatches sampled from this repo's own `.renmark/plans/*.plan.md` +
`.renmark/analytics/task-runs.jsonl` + `.renmark/ledger/events.jsonl`, and
reports (never decides) a disagreement rate. Tasks 2-4 are real schema/policy
work gated on that spike's recommended tier-boundary rule: Task 2 replaces
`ledger.WorkOrder.risk_tier`'s untyped placeholder with a real `RiskTier`
vocabulary + a `classify_risk_tier()` function and adds additive
`risk_tier`/`lens` fields to `InspectionReport`; Task 3 adds
`subagent_gate.resolve_lens_for(work_order) -> LensName` as a SEPARATE policy
function (never merged into `check_capability_envelope` or
`cost.requires_escalation` — different concern, mirrors `cost.py`'s
policy-not-mechanism style); Task 4 builds the actual versioned, pre-dispatch
`InspectionContract` object and wires it onto `WorkOrder` via
`work_order_for_task`, plus an `InspectionReport.contract_ref` field so every
report cites which contract version it was graded against. Tasks 5-8 are
tests covering the classifier, the lens policy, the contract wiring, and a
compatibility guard proving `ledger.VERDICTS = ("pass", "fail", "escalate")`
is untouched — `risk_tier`/`lens`/`contract_ref` are additive fields only,
never a second verdict enum. **Flag for the orchestrator**: if Task 1's
finding reports a disagreement rate that is not obviously acceptable or
unacceptable, that is a genuine Owner judgment call — Task 1 itself must
only report the rate and recommend a tier-boundary rule, never decide
acceptability. The orchestrator should present that decision to the Owner
before dispatching Tasks 2-4 if the finding flags it as such.

## Tasks

### Task 1: Risk-tier spike finding (evidence only, no code changes)
- **mode:** A
- **target:** .renmark/rethink/governed-orchestration-assurance/release-8-risk-tier-spike-finding.md
- **complexity:** hard
- **executor:** sonnet
- **role:** researcher
- **parallel_group:** 1
- **est_tokens:** 3000
- **est_cost_usd:** 0.04
- **verifier:** test -f .renmark/rethink/governed-orchestration-assurance/release-8-risk-tier-spike-finding.md && grep -q "disagreement rate" .renmark/rethink/governed-orchestration-assurance/release-8-risk-tier-spike-finding.md
- **serves:** AC-5
- **spec:**
  Bounded spike, one session, no production wiring — this task makes NO
  changes to any code file. Design a deterministic (zero model-call at
  runtime) risk-tier classifier for a `ledger.WorkOrder`, using only signals
  already on that dataclass or trivially derivable from it: `file_scope`
  breadth (count of files), target-module criticality (whether any path in
  `file_scope` matches a small fixed "critical module" set — propose one,
  e.g. `renmark/ledger.py`, `renmark/dispatch.py`, `renmark/subagent_gate.py`,
  `renmark/fast_path.py`, `renmark/cost.py`, `renmark/cli/_engine.py` — vs. a
  test file, doc, or config), wave/task count context if available, and the
  task's declared `complexity` (simple/medium/hard) if available from the
  originating plan task. The output must be one of exactly four tiers:
  `low`, `medium`, `high`, `critical`.

  Hand-validate this proposed rule against 15-20 REAL historical dispatches
  from this repo. Sample them by reading `.renmark/plans/*.plan.md` files
  (each task block there has `target`, `complexity`, `mode`, `executor`) —
  favor this program's own Release 1-7 plans
  (`.renmark/plans/2026-08-0*-governed-orchestration-assurance-release-*.plan.md`)
  plus a few from earlier plans for variety — and cross-reference by task
  title against `.renmark/analytics/task-runs.jsonl` (has `title`,
  `executor`, `status`, `total_tokens`) and `.renmark/ledger/events.jsonl`
  for any real `WorkOrder`/`InspectionReport` entries, to see what actually
  shipped. For each of the 15-20 sampled dispatches, record: target file(s),
  complexity, a hand-assigned "what tier should this have been" judgment
  (your own considered judgment — e.g. a one-line edit to a `.gitignore` is
  obviously `low`; a change to `ledger.py`'s core dataclasses or
  `dispatch.py`'s packet-construction path is obviously `high` or
  `critical`), and the proposed rule's classifier output. Compute the
  disagreement rate = (dispatches where hand-judgment != rule output) /
  total sampled.

  Write the finding to the target path with: (1) a top metadata block
  matching this program's other artifacts
  (`artifact_type: spike-finding`, `schema_version: 1`, `created_at`,
  `source_sha`, `related_plan: .renmark/plans/2026-08-05-governed-orchestration-assurance-release-8.plan.md`,
  `generator: sonnet`); (2) the sample table (dispatch, target, hand tier,
  rule tier, match/mismatch); (3) the disagreement rate, stated explicitly
  as a percentage; (4) a concrete, implementable tier-boundary rule
  recommendation for Task 2 to code (e.g. exact matching logic, not prose
  vibes); (5) an EXPLICIT closing statement classifying the disagreement
  rate as one of: "obviously acceptable" (say why), "obviously
  unacceptable — needs a re-spike" (say why), or "a genuine Owner judgment
  call — flagging for Owner review before Release 8's schema/policy tasks
  dispatch" (say why). Do NOT decide acceptability yourself if it's
  ambiguous — only report and flag. This task produces the finding
  document only; it must not edit any `.py` file.

### Task 2: `RiskTier` vocabulary + classifier + `InspectionReport` fields
- **mode:** B
- **target:** renmark/ledger.py
- **complexity:** medium
- **executor:** sonnet
- **role:** code-implementer
- **parallel_group:** 2
- **est_tokens:** 1200
- **est_cost_usd:** 0.03
- **verifier:** python3 -c "from renmark import ledger; assert hasattr(ledger, 'RISK_TIERS'); assert ledger.RISK_TIERS == ('low', 'medium', 'high', 'critical'); assert hasattr(ledger, 'classify_risk_tier'); assert ledger.VERDICTS == ('pass', 'fail', 'escalate')" && python3 -m py_compile renmark/ledger.py
- **serves:** AC-5
- **spec:**
  Read Task 1's finding at
  `.renmark/rethink/governed-orchestration-assurance/release-8-risk-tier-spike-finding.md`
  (already written and committed by the prior task in this same run) and
  implement its recommended tier-boundary rule as code. Do not re-derive
  the rule — use the one the finding recommends.

  Add a module-level `RISK_TIERS: tuple[str, ...] = ("low", "medium",
  "high", "critical")` constant, mirroring the existing `VERDICTS: tuple[str,
  ...] = ("pass", "fail", "escalate")` style exactly (same module, same
  plain-tuple pattern — do NOT introduce `enum.Enum` or `typing.Literal`
  here; this module currently has neither). Add a `RiskTier = str` type
  alias immediately above it for documentation/typing clarity only (no
  runtime behavior change).

  Change `WorkOrder.risk_tier`'s docstring note (currently describes it as
  an "untyped placeholder... the real RiskTier enum is Release 8's
  responsibility") to instead point at `RISK_TIERS`/`classify_risk_tier`
  now that they exist — the field itself stays `risk_tier: str | None =
  None` (unchanged type, now documented against `RISK_TIERS` instead of
  being a placeholder). This is additive/compatible — existing placeholder
  string values remain valid.

  Add `def classify_risk_tier(work_order: WorkOrder) -> str:` implementing
  Task 1's hand-validated rule. Never raises — on any missing/malformed
  input (e.g. `work_order is None`, `file_scope` missing) it degrades to
  `"low"` (the conservative default that never over-escalates a broken
  input) rather than raising. Validate its return value is always one of
  `RISK_TIERS`.

  Add two additive fields to `InspectionReport`: `risk_tier: str | None =
  None` and `lens: str | None = None`. Do NOT touch `VERDICTS` or
  `verdict`'s existing semantics — `InspectionReport.verdict` stays exactly
  `pass|fail|escalate`, unchanged. Update `validate_inspection_report()` to
  accept these as optional fields (use the existing `_check_opt_str`
  helper — do not add new validation helpers). Do not touch `WorkResult`,
  `Escalation`, or any function outside this file's `InspectionReport`/
  `WorkOrder`/new classifier additions.

### Task 3: `resolve_lens_for` policy function
- **mode:** B
- **target:** renmark/subagent_gate.py
- **complexity:** medium
- **executor:** sonnet
- **role:** code-implementer
- **parallel_group:** 3
- **est_tokens:** 900
- **est_cost_usd:** 0.03
- **verifier:** python3 -c "from renmark import subagent_gate as sg; assert hasattr(sg, 'LENS_NAMES'); assert sg.LENS_NAMES == ('maintainer', 'skeptical_user', 'competitor'); assert hasattr(sg, 'resolve_lens_for'); r = sg.resolve_lens_for(None); assert r in sg.LENS_NAMES" && python3 -m py_compile renmark/subagent_gate.py
- **serves:** AC-5
- **spec:**
  Add a NEW, SEPARATE policy function in this module — explicitly NOT the
  same function as, and NOT calling, `check_capability_envelope` or
  `cost.requires_escalation`. Capability envelope governs what a Worker may
  touch; `resolve_lens_for` governs which falsification perspective an
  Inspector should apply — a different concern, same orbit, mirroring how
  `ENVELOPE_CONTROL_STATUS`/`control_status` are their own self-contained
  table+function pair in this file.

  Add `LENS_NAMES: tuple[str, ...] = ("maintainer", "skeptical_user",
  "competitor")` — this is the lens vocabulary named in the original
  proposal (grounded by `survey.md`'s Requirement 5 section, which greps
  for exactly `"maintainer lens"`, `"skeptical user"`, `"competitor
  lens"` as the proposal's own established names). `LensName = str` type
  alias immediately above it (plain string typing, matching this module's
  existing style — no `Enum`/`Literal`).

  Add `def resolve_lens_for(work_order) -> str:` — duck-typed on `work_order`
  (reads `getattr(work_order, "risk_tier", None)` and `getattr(work_order,
  "file_scope", None)`, never assumes a real `ledger.WorkOrder` instance, to
  avoid importing `ledger` at module import time — mirrors this module's
  existing duck-typing style, e.g. `work_order_for_task`'s approach in
  `ledger.py`). Never raises — on `None`, a missing `risk_tier`, or any
  malformed input, degrades to the safe default `"maintainer"` (the
  general-purpose lens). Policy: `risk_tier in ("high", "critical")`
  selects `"skeptical_user"` (an outside adversarial read is warranted at
  elevated risk); a work order whose `file_scope` touches more than one
  file at `risk_tier == "medium"` selects `"competitor"` (cross-file
  changes benefit from a rival-implementation read); everything else
  (including `risk_tier in (None, "low")`) selects `"maintainer"` (the
  default, lowest-cost lens). Add a short module comment near
  `resolve_lens_for` explicitly stating it is deliberately NOT wired into
  `check_capability_envelope` and NOT the same function as
  `cost.requires_escalation` (different concerns), so a future reader does
  not try to merge them. Do not modify any existing function in this file.

### Task 4: `InspectionContract` + `WorkOrder`/`InspectionReport` wiring
- **mode:** B
- **target:** renmark/ledger.py
- **complexity:** hard
- **executor:** opus
- **role:** code-implementer
- **parallel_group:** 4
- **est_tokens:** 1800
- **est_cost_usd:** 0.18
- **verifier:** python3 -c "import dataclasses; from renmark import ledger; fields={f.name for f in dataclasses.fields(ledger.InspectionContract)}; wo={f.name for f in dataclasses.fields(ledger.WorkOrder)}; ir={f.name for f in dataclasses.fields(ledger.InspectionReport)}; ok = {'risk_tier','lenses','deterministic_gates','semantic_rubric_ref','independent_judge_required','evidence_required','allowed_verdicts','contract_id','version'} <= fields and 'inspection_contract' in wo and 'contract_ref' in ir and ledger.VERDICTS == ('pass','fail','escalate'); print('OK' if ok else 'FAIL'); assert ok" | tail -1 | grep -q OK && python3 -m py_compile renmark/ledger.py
- **serves:** AC-5
- **spec:**
  This is architecture-level cross-cutting work within a single file — the
  design decision from `target-blueprint.md` §3.5 and the roadmap's Release
  8 revision (peer-review Gap 3): `InspectionContract` is the versioned,
  PRE-DISPATCH plan for what inspection SHOULD happen; `InspectionReport`
  (already existing) is the post-dispatch record of what DID happen. They
  stay two separate dataclasses connected only by a reference field — do
  NOT merge them.

  Add `@dataclass class InspectionContract:` with fields: `contract_id: str
  = ""`, `version: int = 1`, `risk_tier: str | None = None`, `lenses:
  list[str] = field(default_factory=list)`, `deterministic_gates:
  list[str] = field(default_factory=list)`, `semantic_rubric_ref: str |
  None = None`, `independent_judge_required: bool = False`,
  `evidence_required: list[str] = field(default_factory=list)`,
  `allowed_verdicts: tuple[str, ...] = VERDICTS` (reuse the existing
  `VERDICTS` tuple as the default — do NOT invent a second verdict
  vocabulary; this field exists so a contract could theoretically narrow
  the allowed set for a given inspection, never widen it beyond
  `VERDICTS`). Add a short docstring citing this file's existing
  `WorkOrder`/`InspectionReport` docstring style.

  Add `inspection_contract: InspectionContract | None = None` as a new
  additive field on `WorkOrder` (append it after the existing `lens: str |
  None = None` field in the dataclass body — do not reorder existing
  fields, this is a dataclass and field order matters for any positional
  construction, though the codebase's own convention per `work_order_for_task`
  is kwargs-only construction).

  Extend `work_order_for_task()` so that when the caller does not already
  supply `inspection_contract` via `**kwargs`, and only when a real
  `risk_tier` is being resolved for this order (do not force-classify for
  every call if the caller has explicitly opted out — check for an
  `auto_contract: bool = True` keyword-only parameter you add to the
  function signature, defaulting to `True`, so existing call sites are
  unaffected unless they pass a `risk_tier`/`lens` explicitly and still get
  the same values back), construct one: call `classify_risk_tier` on the
  in-progress `WorkOrder` for `risk_tier` if not already supplied, import
  `resolve_lens_for` from `renmark.subagent_gate` (import inside the
  function body, not at module top, to avoid introducing a new module-level
  import cycle risk between `ledger.py` and `subagent_gate.py`) for
  `lenses=[resolve_lens_for(wo)]`, and populate a minimal `InspectionContract`
  (`contract_id=f"{order_id}-contract"`, `version=1`,
  `deterministic_gates=[]`, `semantic_rubric_ref=None`,
  `independent_judge_required=(risk_tier in ("high", "critical"))`,
  `evidence_required=[]`). This function must never raise — wrap the
  contract construction in a try/except that falls back to
  `inspection_contract=None` on any failure (missing `subagent_gate`
  import, bad classifier output, etc.) so a broken contract-construction
  path can never break work-order construction itself.

  Add `contract_ref: str | None = None` as an additive field to
  `InspectionReport` (documented as "contract_id:version this report was
  graded against", e.g. `"task-3-contract:1"`). Update
  `validate_inspection_report()` with `_check_opt_str(data, "contract_ref")`.
  Do not add a `validate_inspection_contract()` function unless you also
  wire it into `_VALIDATOR_BY_KIND` and `LedgerEvent`/`_KIND_BY_TYPE` — if
  you do add contract validation, keep it consistent with the existing
  four-shape `_VALIDATOR_BY_KIND` pattern rather than a one-off. Confirm
  `VERDICTS` itself is untouched (no new entries, no rename) — this is the
  hard compatibility line for this whole release.

### Task 5: risk classifier tests
- **mode:** A
- **target:** tests/test_ledger_risk_tier.py
- **complexity:** medium
- **executor:** codex
- **role:** test-writer
- **parallel_group:** 5
- **est_tokens:** 700
- **est_cost_usd:** 0.02
- **verifier:** pytest -q tests/test_ledger_risk_tier.py
- **serves:** AC-5
- **spec:**
  Write pytest tests against `renmark.ledger.classify_risk_tier` and
  `RISK_TIERS`. Cover: (1) a `WorkOrder` touching a critical module (e.g.
  `file_scope=["renmark/ledger.py"]`) classifies as `high` or `critical`
  (assert it's in that pair per whatever exact boundary Task 2 implemented
  — read `renmark/ledger.py`'s actual implementation and Task 1's finding
  doc to assert the real boundary, don't guess); (2) a `WorkOrder` touching
  only a test file or doc classifies as `low`; (3) `classify_risk_tier(None)`
  never raises and returns a value in `RISK_TIERS`; (4) `classify_risk_tier`
  always returns a value that is a member of `RISK_TIERS` across at least 5
  varied constructed `WorkOrder` inputs (fuzz-lite, not property-based);
  (5) a guard test asserting `ledger.VERDICTS == ("pass", "fail",
  "escalate")` is unchanged by this release. Use `renmark.ledger.WorkOrder`
  directly to construct fixtures — no mocking needed, this is pure-function
  testing.

### Task 6: lens policy tests
- **mode:** A
- **target:** tests/test_subagent_gate_lens.py
- **complexity:** medium
- **executor:** codex
- **role:** test-writer
- **parallel_group:** 5
- **est_tokens:** 500
- **est_cost_usd:** 0.02
- **verifier:** pytest -q tests/test_subagent_gate_lens.py
- **serves:** AC-5
- **spec:**
  Write pytest tests against `renmark.subagent_gate.resolve_lens_for` and
  `LENS_NAMES`. Cover: (1) `resolve_lens_for(None)` never raises and
  returns `"maintainer"`; (2) a duck-typed object with `risk_tier="high"`
  resolves to `"skeptical_user"`; (3) a duck-typed object with
  `risk_tier="critical"` resolves to `"skeptical_user"`; (4) a duck-typed
  object with `risk_tier="medium"` and `file_scope` of 2+ files resolves to
  `"competitor"`; (5) a duck-typed object with `risk_tier="low"` resolves
  to `"maintainer"`; (6) the return value is always a member of
  `LENS_NAMES` across all cases tested. Use a small local
  `types.SimpleNamespace` or a plain stub class for the duck-typed
  work-order fixtures — do not import `renmark.ledger.WorkOrder` unless
  needed, to keep this test decoupled per this module's existing
  duck-typing convention.

### Task 7: `InspectionContract` construction + wiring tests
- **mode:** A
- **target:** tests/test_ledger_inspection_contract.py
- **complexity:** medium
- **executor:** codex
- **role:** test-writer
- **parallel_group:** 5
- **est_tokens:** 700
- **est_cost_usd:** 0.02
- **verifier:** pytest -q tests/test_ledger_inspection_contract.py
- **serves:** AC-5
- **spec:**
  Write pytest tests against `renmark.ledger.InspectionContract`,
  `WorkOrder.inspection_contract`, `InspectionReport.contract_ref`, and
  `work_order_for_task`'s auto-population. Cover: (1) `InspectionContract()`
  constructs with all-default values, `allowed_verdicts == VERDICTS`; (2) a
  `WorkOrder` constructed via `work_order_for_task` (build a minimal
  duck-typed task stub with `.spec`, `.target`, `.context_files`,
  `.verifier`, `.index` attributes, matching the pattern already documented
  in `work_order_for_task`'s docstring) ends up with a non-`None`
  `inspection_contract` whose `risk_tier` matches
  `classify_risk_tier(<the same order>)` and whose `lenses` is a non-empty
  list containing a member of `subagent_gate.LENS_NAMES`; (3) passing
  `auto_contract=False` to `work_order_for_task` leaves
  `inspection_contract` at its default (`None`, unless explicitly supplied
  via kwargs); (4) an `InspectionReport(contract_ref="task-1-contract:1")`
  round-trips through `validate_inspection_report()` with no issues; (5) a
  guard test that `InspectionContract`'s `allowed_verdicts` default is
  exactly `ledger.VERDICTS` (identity of values, not a hardcoded
  duplicate tuple) so the two can never silently drift apart.

### Task 8: risk-tier/lens behavioral-eval fixture (for Release 15)
- **mode:** A
- **target:** tests/behavioral/risk_tier_lens_selection.behavior.json
- **complexity:** medium
- **executor:** codex
- **role:** test-writer
- **parallel_group:** 5
- **est_tokens:** 400
- **est_cost_usd:** 0.02
- **verifier:** python3 -c "import json; d = json.load(open('tests/behavioral/risk_tier_lens_selection.behavior.json')); ok = bool(d.get('skill')) and 'deterministic' in d and 'eval' in d; print('OK' if ok else 'FAIL'); assert ok" | tail -1 | grep -q OK
- **serves:** AC-5
- **spec:**
  Author one behavioral-eval fixture in the exact JSON shape already used
  by `tests/behavioral/mode.behavior.json` (top-level `skill`, `prompt`,
  `deterministic: {call, assertions: [...]}`, `eval: {contract,
  golden_ref}`) — read that file first as the template. This release only
  AUTHORS the fixture (per roadmap migration step (e): "for Release 15 to
  wire in") — do not add any new test runner or wire it into
  `renmark/behavior.py`'s `DeterministicSpec`/`EvalSpec` registry; that
  wiring is explicitly out of scope for this release.

  Set `"skill": "plan"` (risk-tier/lens selection happens at the
  `ledger.work_order_for_task` boundary `plan`/`orchestrate` call into).
  `"deterministic".call` should reference a fully-qualified callable path
  string, e.g. `"ledger.classify_risk_tier"`, with `"assertions"` a list of
  simple string checks in the same `"contains:..."`/`"not_contains:..."`
  style as the template (this fixture's assertions describe intended
  behavior for a future runner to check against golden transcripts — they
  do not execute in this release). `"eval".contract` should be one or two
  sentences stating the behavioral claim this fixture will eventually
  prove: that a dispatch touching a critical module gets classified at
  `high`/`critical` and receives the `skeptical_user` lens, while a
  low-risk dispatch gets `low`/`maintainer`. `"eval".golden_ref` can be a
  placeholder string like `"risk_tier_lens_selection.golden"` (no golden
  file needs to exist yet — Release 15's job).

## Cost Preview

| Executor | Count |
|---|---|
| sonnet | 3 |
| opus | 1 |
| codex | 4 |

Total tokens (incl. ~10k Agent overhead/task for haiku/sonnet/opus):
**~49,200 tokens**

Total cost: **~$0.35**

Parallel groups: 5 (1: spike → 2: RiskTier/classifier → 3: lens policy →
4: InspectionContract wiring → 5: all four test/fixture tasks in parallel).

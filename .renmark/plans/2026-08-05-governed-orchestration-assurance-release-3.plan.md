# Plan: governed-orchestration-assurance — Release 3 (Canonical work-order reconciliation)

Context: Release 3 of the 16-release `governed-orchestration-assurance`
program. Source: `.renmark/rethink/governed-orchestration-assurance/roadmap.md`
"Release 3" section (revised 2026-08-05). REFACTOR-TAGGED: this plan touches
≥3 files and is a schema/funnel change (field rename across dataclass +
callers) — `/renmark:orchestrate` MUST run its pre-refactor safety protocol
(clean-tree check, checkpoint commit, baseline `pytest -q` run) before
dispatching Task 1.

Scope: unify `ledger.WorkOrder`, `dispatch.SubagentInput`, and
`dispatch.RepairWorkOrder` around one canonical anchor. (1) Add the accepted
`RenmarkWorkOrder` contract fields to `ledger.WorkOrder` as additive/optional
(`risk_tier: str | None` — untyped placeholder per Release 3's design
decision; the real `RiskTier` enum lands in Release 8, not here).
(2) Add `ledger.work_order_for_task(task, role, ...) -> WorkOrder`. (3) Call
it once inside `dispatch.build_subagent_input` — the single funnel all 6
dispatch call sites (fast-path, feature, debug, orchestrate, rethink, resume)
already use via its 3 wrapper functions (`build_workflow_fanout_args`,
`build_host_dispatch_plan`, `dispatch_task_isolated`); `SubagentInput`'s
public field names stay unchanged (compat #7). (4) Rename
`RepairWorkOrder.work_order_id` to `order_id`. Investigation found the real
blast radius of that rename is narrower than "5 files touch `work_order_id`"
suggests — see the plan-time finding at the bottom.

**Investigation finding — `work_order_id` string collisions are NOT part of
this rename's blast radius.** `grep -rln "work_order_id" tests/` returns 5
files, but only `tests/test_repair_work_order.py` actually references
`RepairWorkOrder.work_order_id` (the dataclass field being renamed):
- `tests/test_subagent_gate_r008.py` and `tests/test_wp8_r008_wiring.py` use
  `"work_order_id"` as a dict/kwarg key for the unrelated R-008
  `subagent_gate.R008Checklist.work_order_id` field — a different dataclass
  entirely. Not touched.
- `tests/test_ledger.py` uses `work_order_id=` as a keyword arg to
  `ledger.emit_inspection_verdict(..., work_order_id=...)` — a function
  parameter name (task description already flagged this as a decoy). Not
  touched.
- `tests/test_wp8_repair_wiring.py` calls
  `dispatch.build_repair_work_order(finding, work_order_id="WO-100")` — that
  factory function's *parameter* name is intentionally left unrenamed (only
  the `RepairWorkOrder` dataclass field renames); this file never accesses
  `.work_order_id` as an attribute, so it needs no edit.
- A production (non-test) caller was found that the roadmap's file list
  didn't name: `renmark/delivery_state.py::log_repair_work_order` reads
  `work_order.work_order_id` at line ~495. This is added as Task 3 below.

**Plan-time finding on migration step (d)'s "require it to resolve to a real
`WorkOrder.order_id`":** interpreted as a *documented type contract*
(rename the field, update the docstring to state the id should be a real
`WorkOrder.order_id` when one exists) rather than new runtime
cross-validation inside `build_repair_work_order`. Adding runtime validation
that `order_id` must match an already-constructed `WorkOrder` would break
`tests/test_repair_work_order.py`'s 6 non-protected tests, which pass
synthetic ids (`"WO-1"`..`"WO-8"`) with no backing `WorkOrder` — none of
those tests are in the "must stay green unmodified" list, but rewriting them
to fabricate a full `WorkOrder` per case is a larger, unscoped change the
terse roadmap line doesn't clearly ask for. Flagging for owner review before
Release 8 (which does own real `RiskTier`/lens enforcement) — a stricter
runtime check can be added later as an explicit follow-up if desired.

Reuse check: none — this is new schema/plumbing inside an existing,
already-investigated module pair (`renmark/ledger.py`, `renmark/dispatch.py`);
no existing skill, MCP tool, spec, or feature covers a canonical
work-order-anchor reconciliation.

### Task 1: ledger WorkOrder schema + work_order_for_task
- **mode:** B
- **target:** renmark/ledger.py
- **complexity:** medium
- **executor:** sonnet
- **role:** code-implementer
- **parallel_group:** 1
- **est_tokens:** 1800
- **est_cost_usd:** 0.0354
- **verifier:** python3 -m py_compile renmark/ledger.py && python3 -c "from renmark import ledger; import dataclasses; f={x.name for x in dataclasses.fields(ledger.WorkOrder)}; assert {'risk_tier','capability_envelope_ref','lens','schema_version','correlation_id','idempotency_key','dependencies','scope','budget','routing','constraints','interaction_policy'} <= f; assert callable(ledger.work_order_for_task); print('OK')" | tail -1
- **serves:** AC-1 (Req 1)
- **spec:**
  Add additive/optional fields to the `WorkOrder` dataclass in
  `renmark/ledger.py` (currently: `order_id`, `task`, `role`, `file_scope`,
  `verifier`, `is_repair`, `repairs_finding_ref`). Every new field must have
  a default so no existing `WorkOrder(...)` construction site breaks
  (compatibility guarantee #1 — `pytest -q` count must not regress):

  - `risk_tier: str | None = None` — **untyped placeholder, not an enum.**
    Per Release 3's recorded design decision, the real `RiskTier` enum is
    Release 8's responsibility (it lives at the
    `subagent_profiles.py`/`ledger.InspectionReport` "lens selection"
    module boundary, not here). Do not define a `RiskTier` type in this
    task.
  - `capability_envelope_ref: str | None = None`
  - `lens: str | None = None`
  - `schema_version: int = 1`
  - `correlation_id: str | None = None`
  - `idempotency_key: str | None = None`
  - `dependencies: list[str] = field(default_factory=list)`
  - `scope: dict | None = None`
  - `budget: dict | None = None`
  - `routing: dict | None = None`
  - `constraints: dict | None = None`
  - `interaction_policy: dict | None = None`

  Add a short docstring note above the new fields citing
  `.renmark/rethink/governed-orchestration-assurance/roadmap.md` Release 3's
  field table: these fields are schema-present now; most have their real
  enforcement/consumption deferred to later releases (Release 4/6/8/10/11/13
  per the table) — this task only adds the schema slot, it does not wire
  enforcement for any of them.

  Then add a new function near `WorkOrder`:

  ```python
  def work_order_for_task(task, role: str, *, order_id: str | None = None, **kwargs) -> WorkOrder:
  ```

  It builds and returns a `WorkOrder` from a `renmark.parser.Task`-like
  object (avoid a hard import-time dependency on `renmark.parser.Task` if it
  would create an import cycle — a structural/duck-typed read of
  `task.target`, `task.verifier`, `task.index` etc. is fine, matching the
  pattern `dispatch.build_subagent_input` already uses for `Task`). Populate
  at minimum: `task` (from `task.spec` or a task title/description field —
  match whatever `build_subagent_input` uses for its own `task_spec`),
  `role` (the passed-in `role` param), `file_scope` (from `task.target` +
  `task.context_files`), `verifier` (from `task.verifier`). Generate
  `order_id` deterministically when not supplied (e.g. from `task.index`) —
  do not leave it empty, since Release 3's value proposition is closing the
  `order_id` reference gap. Leave the new placeholder/deferred fields at
  their defaults unless the caller supplies them via `**kwargs` — this
  function's job is constructing a valid canonical `WorkOrder`, not
  performing enforcement.

  Do not touch `validate_work_order` — the new fields are optional/additive
  and the existing required-field checks (`order_id`, `task`, `role`,
  `file_scope`) stay correct without changes.

  Do not touch `dispatch.py`, `delivery_state.py`, or any test file in this
  task — those are separate tasks.

### Task 2: dispatch funnel wiring + RepairWorkOrder rename
- **mode:** B
- **target:** renmark/dispatch.py
- **complexity:** hard
- **executor:** sonnet
- **role:** code-implementer
- **parallel_group:** 2
- **est_tokens:** 2400
- **est_cost_usd:** 0.0372
- **verifier:** python3 -m py_compile renmark/dispatch.py && python3 -c "from renmark import dispatch; import dataclasses; assert 'order_id' in {f.name for f in dataclasses.fields(dispatch.RepairWorkOrder)}; assert 'work_order_id' not in {f.name for f in dataclasses.fields(dispatch.RepairWorkOrder)}; print('OK')" | tail -1
- **serves:** AC-1 (Req 1)
- **spec:**
  Two changes to `renmark/dispatch.py`, both required, in this file only.
  Depends on Task 1 (`renmark.ledger.work_order_for_task`) already landing.

  **(a) Funnel wiring.** Inside `build_subagent_input` (around line 606),
  call `ledger.work_order_for_task(task, role)` once, after `role` is
  resolved (either the passed-in `role` or the value resolved via
  `subagent_profiles.resolve_profile(task)`), to construct the canonical
  `WorkOrder` for this dispatch. Do NOT add a new field to `SubagentInput`
  and do NOT change any of `SubagentInput`'s existing public field names or
  `to_dict()` output shape — compatibility guarantee #7 requires
  `task_spec`/`required_files`/`verifier_expectations` etc. stay exactly as
  they are; the constructed `WorkOrder` is populated by reading off the same
  `Task` the rest of the function already reads, it does not change what
  crosses the SubagentInput boundary. Import `ledger` at the top of
  `dispatch.py` (function-local import if a `ledger` <-> `dispatch` import
  cycle risk exists — check first with
  `python3 -c "import renmark.ledger"` and `python3 -c "import renmark.dispatch"`
  before deciding; mirror the existing function-local `from renmark import
  context` / `from renmark import subagent_profiles` pattern in this same
  function if a cycle is possible).

  **(b) `RepairWorkOrder.work_order_id` -> `order_id` rename.** In the
  `RepairWorkOrder` dataclass (around line 989) rename the field
  `work_order_id: str` to `order_id: str`. Update:
  - The class docstring (currently says "Fields per design doc §4.1:
    ``work_order_id``, ...") to say `order_id`, and note this id should be a
    real `WorkOrder.order_id` (e.g. one produced by `work_order_for_task`)
    when a canonical work order is available for the repair.
  - `build_repair_work_order`'s body (around line 1043) — it currently does
    `RepairWorkOrder(work_order_id=work_order_id, ...)`; change only the
    dataclass keyword to `RepairWorkOrder(order_id=work_order_id, ...)`.
    **Do not rename `build_repair_work_order`'s own `work_order_id`
    parameter** — its external call signature stays the same; only the
    `RepairWorkOrder` dataclass field itself renames. This keeps
    `tests/test_wp8_repair_wiring.py`'s calls (which pass
    `work_order_id="WO-100"` as a kwarg to the factory function, not to the
    dataclass) green unmodified.

  Do not touch `renmark/delivery_state.py` or any test file in this task —
  those are Tasks 3-5. Do not touch `emit_inspection_verdict` or
  `check_dispatch_independence` in `ledger.py` — their `work_order_id`
  parameter is an unrelated function argument name, not this field.

  **Compatibility check before finishing:** confirm none of
  `tests/test_dispatch.py`, `tests/test_dispatch_isolation.py`,
  `tests/test_dispatch_scope_generalization.py`,
  `tests/test_cross_host_dispatch_e2e.py`,
  `tests/test_r0_2_dispatch_regression_baseline.py` reference
  `RepairWorkOrder.work_order_id` or assert on `SubagentInput`'s field set
  changing (`grep -n "work_order_id\|RepairWorkOrder" <file>` on each — this
  repo investigation already found zero hits, so this should be a no-op
  confirmation, not new work). If any of the 5 break, STOP and report — do
  not edit those files to work around it.

### Task 3: delivery_state repair-work-order rename follow-through
- **mode:** B
- **target:** renmark/delivery_state.py
- **complexity:** simple
- **executor:** haiku
- **role:** code-implementer
- **parallel_group:** 3
- **est_tokens:** 300
- **est_cost_usd:** 0.0010
- **verifier:** python3 -m py_compile renmark/delivery_state.py && grep -n "work_order.order_id" renmark/delivery_state.py && ! grep -n "work_order.work_order_id" renmark/delivery_state.py
- **serves:** AC-1 (Req 1)
- **spec:**
  In `renmark/delivery_state.py`, function `log_repair_work_order` (around
  line 495), change the one reference
  `f"{work_order.work_order_id} ({work_order.severity}): {work_order.description}"`
  to use `work_order.order_id` instead of `work_order.work_order_id` — this
  follows Task 2's `RepairWorkOrder.work_order_id` -> `order_id` rename.
  Change only this attribute access; `severity`/`description` stay as-is.
  Depends on Task 2 already having landed (the `order_id` field must exist
  on `RepairWorkOrder` first). Touch no other file.

### Task 4: test_repair_work_order.py rename follow-through
- **mode:** B
- **target:** tests/test_repair_work_order.py
- **complexity:** simple
- **executor:** haiku
- **role:** test-writer
- **parallel_group:** 3
- **est_tokens:** 300
- **est_cost_usd:** 0.0010
- **verifier:** python3 -m pytest -q tests/test_repair_work_order.py 2>&1 | tail -3
- **serves:** AC-1 (Req 1)
- **spec:**
  Update `tests/test_repair_work_order.py` for Task 2's
  `RepairWorkOrder.work_order_id` -> `order_id` rename:
  - Line ~23: `assert order.work_order_id == "WO-1"` -> `assert
    order.order_id == "WO-1"`.
  - Lines ~105 and ~119: the two direct `dispatch.RepairWorkOrder(
    work_order_id="WO-7", ...)` / `(work_order_id="WO-8", ...)`
    constructions -> change the keyword to `order_id="WO-7"` /
    `order_id="WO-8"`.
  Do NOT change any of the `dispatch.build_repair_work_order(finding,
  work_order_id="WO-...")` factory-function calls (lines ~19, 38, 52, 66,
  79, 92) — that function's own parameter name is unchanged by Task 2, only
  the dataclass field is renamed. Depends on Task 2 already having landed.
  Touch no other file.

### Task 5: cross-entry-point work-order funnel test
- **mode:** A
- **target:** tests/test_work_order_funnel_wiring.py
- **complexity:** medium
- **executor:** codex
- **role:** test-writer
- **parallel_group:** 3
- **est_tokens:** 1200
- **est_cost_usd:** 0.03
- **verifier:** python3 -m pytest -q tests/test_work_order_funnel_wiring.py 2>&1 | tail -3
- **serves:** AC-1 (Req 1)
- **spec:**
  New test file `tests/test_work_order_funnel_wiring.py`. Two things to
  prove, per Release 3's roadmap "Observability hook":

  1. **Funnel test.** `renmark.dispatch.build_subagent_input` is the single
     shared point where a `ledger.WorkOrder` gets constructed for a
     dispatch, and its 3 existing callers within `dispatch.py`
     (`build_workflow_fanout_args`, `build_host_dispatch_plan`,
     `dispatch_task_isolated` — grep `renmark/dispatch.py` for
     `build_subagent_input(` to confirm these are still the only 3
     call sites before writing assertions) all route through it rather than
     constructing a bespoke `WorkOrder`-shaped dict of their own. Build a
     minimal `renmark.parser.Task` fixture (mode/target/verifier/spec) and
     call `dispatch.build_subagent_input(task)` directly; assert it
     succeeds and (via monkeypatching `renmark.ledger.work_order_for_task`
     with a spy, or by any other reliable means) assert
     `work_order_for_task` is actually invoked once per call — this is the
     "not a bespoke path" proof. Then call the 3 wrapper functions
     (`build_workflow_fanout_args([task])`,
     `build_host_dispatch_plan([task], host="claude")`,
     `dispatch_task_isolated(task, subagent_runner=<a stub returning a
     minimal valid SubagentOutput dict>)`) and assert each one still
     succeeds unchanged in its existing public output shape (this is the
     regression guard proving the funnel wiring didn't alter
     `SubagentInput`'s or the wrapper functions' existing contracts —
     compat guarantee #7).
  2. **Schema completeness test.** Assert every field in Release 3's field
     table is present on `ledger.WorkOrder` with the stated default/type:
     `risk_tier` (`None` default, untyped — assert it is NOT an enum
     instance, i.e. `WorkOrder().risk_tier is None` and setting it to a
     plain string does not raise), `capability_envelope_ref`, `lens`,
     `schema_version` (default `1`), `correlation_id`, `idempotency_key`,
     `dependencies` (default `[]`), `scope`, `budget`, `routing`,
     `constraints`, `interaction_policy` (all default `None` unless noted
     above). Use `dataclasses.fields(ledger.WorkOrder)` plus constructing a
     bare `WorkOrder()` and reading defaults.

  Depends on Task 1 and Task 2 already having landed. Do not modify
  `renmark/ledger.py`, `renmark/dispatch.py`, or any other test file — this
  task only creates the new test file.

---

## Cost preview

| Executor | Tasks | Tokens (incl. overhead) | Cost |
|---|---|---|---|
| sonnet | 2 | 24,200 | $0.0726 |
| haiku | 2 | 20,600 | $0.0020 |
| codex | 1 | 1,200 | $0.03 |

**Total tokens (incl. ~10k Agent overhead/task for haiku/sonnet, none for codex): ~46,000**
**Total cost: ~$0.1046**

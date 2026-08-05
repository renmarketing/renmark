---
artifact_type: rethink-modularity-assessment
schema_version: 1
created_at: 2026-08-04T00:00:00Z
source_sha: e6898917ddf3a30505bb01b1b0569c28a187d792
related_plan: null
generator: sonnet
stale_after: null
dependency_refs:
  - .renmark/rethink/renmark-architecture/modularity-assessment.md
  - .renmark/rethink/renmark-architecture/target-blueprint.md
  - .renmark/rethink/governed-orchestration-assurance/intake.md
---

# Modularity/scalability/maintainability assessment — DELTA for governed-orchestration-assurance
## Stage 5 of `/renmark:rethink`, run 2 (governance/assurance scope)

Scope of THIS pass: the modules the proposal's new governance capabilities
would touch — `dispatch.py`, `ledger.py`, `fast_path.py`, `subagent_gate.py`,
`judge.py`, `task_tracking.py`, `interaction.py`, `hosts.py`, `cost.py`,
`codex_routing.py`, `subagent_profiles.py`, `agency.py`, `program.py`,
`recurrence.py`, `context.py`, `lifecycle/`. Does NOT re-derive the whole-repo
structure (already done in `renmark-architecture`'s assessment/blueprint,
fully shipped as of `e689891`). Method: direct reads of each module's
docstring, dataclasses, `def`/`class` list, and import block; targeted grep
for cross-module references and circular-import risk; test-file inventory.

## 0. Headline finding

**The proposal is not asking for new architecture — it is asking to finish
wiring, unify, and enforce architecture that already exists in fragments.**
Every one of the proposal's 13 requirements maps to an existing module that
already carries a partial or schema-ready version of that concept:

| Proposal concept | Existing module/shape | State |
|---|---|---|
| Canonical work-order/receipt contract | `ledger.WorkOrder`/`WorkResult`/`InspectionReport`/`Escalation` (R-0.3) | Schema + JSONL writer exist; **not the only work-order shape** (see §1) |
| Independent inspection / dispatch-independence | `ledger.check_dispatch_independence`, `emit_inspection_verdict` (R-0.4) | Implemented, wired at some call sites |
| Role capability envelope | `subagent_profiles.ProfileSpec.allowed_targets` | Field exists, docstring says **"informational for now; enforced in future Agency Mode"** — literally the proposal's ask |
| Task tracker bound to real dispatch | `task_tracking.py` (REQ-31) | Idempotent create/complete + `MissingEvidenceError`/`SelfApprovalError` exist; reuses `ledger.check_dispatch_independence` already |
| Selector/headless contract | `interaction.py` | Full `ChoiceSet`/native-page/fallback machinery exists; "enforced" vs "advisory" is the delta |
| Failure-derived constraint registry | `recurrence.py` | Bounded, fingerprinted, capped-at-512-entries recurrence ledger with `RemediationClass = "patch"\|"durable_guard"` already — structurally *is* a failure-rule registry, just not yet read by a pre-dispatch gate |
| Calibrated blind LLM-judging | `judge.py` | Escalation-only, injectable-runner, defensive-parse judge exists; "blind"/bias-control/calibration is the delta |
| Deterministic pre-dispatch gate | `subagent_gate.py` | Exists (Q1-Q4 gate); is the natural pre-action capability-envelope enforcement point |
| Policy-aware dispatch scheduling | `cost.py` (routing policy authority, leaf) + `codex_routing.py` | Exists but scattered (per prior assessment §6, carried forward, not yet fixed) |
| Context/memory governance | `context.py` | Taxonomy + dynamic-loading primitives exist; explicitly documents it does NOT define a competing packet dataclass |
| Durable events/recovery | `ledger.py` (append-only JSONL) + `state/pipeline.py` | Event log exists; "recovery" replay logic is the delta |
| Owner→GC→Architect→Worker→Inspector role model | `agency.py` (`AgencyState`, milestone/signoff) + `subagent_profiles.PROFILES` | Role model exists at two altitudes (agency-level phase, dispatch-level profile) — not yet unified |

This changes the framing for Stage 6/7: the transformation's dominant risk is
**schema/seam proliferation** (a fourth work-order shape, a second capability
envelope, a competing event log) if new code is written from scratch instead
of extending these seams, not "there's nowhere for this to live."

## 1. Domain/service boundaries — module-by-module

- **`ledger.py`** (558L) — genuinely the closest thing to a canonical
  work-order/receipt store today. Owns `.renmark/ledger/events.jsonl`
  (append-only, fail-loud on write, degrade-to-empty on read), 4 dataclasses
  (`WorkOrder`/`WorkResult`/`InspectionReport`/`Escalation`), schema
  validators, `check_dispatch_independence`, `emit_inspection_verdict`,
  `latest_verdict_for`. Imports only `state._core` — a near-leaf. Its own
  docstring is explicit about scope: "schema + read/write primitives ONLY...
  No dispatch/review/pause call site is wired here" — confirming the
  proposal's "extend enforcement, don't duplicate" instruction is achievable
  from this module's existing surface, not a rewrite.
- **`dispatch.py`** (1052L) — the wave/task dispatch engine PLUS three
  separate dataclass families: `SubagentInput`/`SubagentOutput` (the actual
  packet sent to/received from a subagent, G3/G9/G11 isolation rules),
  `InspectorFinding`/`RepairWorkOrder` (a second, independently-shaped
  "work order" for repairs), and `HostDispatchCall`/`HostDispatchPlan`
  (cross-host dispatch shape). Low external coupling (imports only
  `fast_path`, `parser`, `providers.claude_agent` at module level; `context`,
  `schemas`, `subagent_profiles`, `codex_routing` are function-local imports
  to dodge cycles — a pattern already used 5x in this one file, a coupling
  smell even though it "works").
- **`fast_path.py`** (217L) — clean, small, single-purpose:
  `ClassificationVerdict` (5-signal eligibility) + `WorkerScope`/
  `ScopeVerdict` (post-hoc git-diff scope enforcement). Imports only
  `parser.Task`. This is the best-isolated module in the delta set and the
  one `RepairWorkOrder.scope` already reuses (good precedent).
- **`subagent_gate.py`** (423L) — pure, side-effect-free pre-dispatch
  challenge function (`SubagentVerdict`). Imports `cost`, `subagent_profiles`
  at module level (both leaves) — clean dependency direction. This is
  structurally the pre-action gate: today it answers "was a subagent needed
  at all," not "is this role allowed to do this," but the shape (pure
  function, returns a verdict with a structured `challenge` code, never
  raises) is exactly the shape a capability-envelope check should have.
- **`judge.py`** (384L) — escalation-only, cost-labeled
  (`JUDGE_EST_COST_USD`), injectable `subagent_runner`, defensive JSON
  parsing that never silently promotes a parse failure to "pass." Imports
  nothing from `renmark.*` — a leaf. Clean extension point.
- **`task_tracking.py`** (436L) — idempotent `create_or_reuse_task`,
  `MissingEvidenceError`, `SelfApprovalError`, `MissingVerificationError`.
  Docstring states it "reuses `renmark.ledger`'s dispatch-independence check
  ... rather than reimplementing it" — confirmed by grep, no duplicate
  self-approval logic found. Own JSON store (`tasks.json`), correctly
  described as informational/non-load-bearing per REQ-31.
- **`interaction.py`** (578L) — `Choice`/`ChoiceSet`/`ContinuationResult`,
  native-page building, numbered fallback, refusal detection. Imports only
  `hosts` (leaf). The single largest module in this delta set by
  def-count (20 functions) but cohesive — one concern (selector rendering +
  continuation), not several.
- **`hosts.py`** (163L), **`cost.py`** (448L), **`codex_routing.py`** (154L),
  **`subagent_profiles.py`** (410L) — all leaves or near-leaves (zero/near-zero
  `renmark.*` imports), consistent with the prior assessment's finding that
  routing/host/cost modules are the codebase's best-isolated tier.
  `subagent_profiles.ProfileSpec` is the pre-existing role/capability model;
  its `allowed_targets` field is currently descriptive text, not an enforced
  glob — this is the literal seam the proposal's capability envelope needs.
- **`agency.py`** (424L) — imports `delivery_state` (leaf). Owns
  `AgencyState`/milestone/signoff tracking — the *project-phase* altitude of
  the Owner→GC→Architect→Worker→Inspector model, distinct from
  `subagent_profiles`'s *per-dispatch-role* altitude. These two role notions
  are not currently unified by one type; a work-order's `role` field
  (`ledger.WorkOrder.role`, `dispatch.SubagentInput.role`) is a
  `subagent_profiles`-level string, while `agency.py`'s phase/signoff model
  operates one level up. Not a bug, but worth naming explicitly before a
  capability envelope is bolted onto one and assumed to cover the other.
- **`program.py`** (846L) + `recurrence.py` (680L) — `program.py` is the
  rethink/roadmap staged-program engine (already flagged as a third parallel
  "what's next" engine in the prior assessment, unchanged, Keep). `recurrence.py`
  is a strong, underused asset for this transformation specifically: bounded
  (`MAX_ENTRIES = 512`), fingerprinted (`content_fingerprint` from `scan.py`),
  with `RemediationClass = Literal["patch", "durable_guard"]` and
  `AcknowledgementAction` already modeling "this failure needs a durable rule,
  not another retry" — the proposal's failure-derived constraint registry
  requirement is 70% built here already, importing only `scan.py`.
- **`context.py`** (352L) — taxonomy + dynamic skill loading. Explicitly
  documents (own docstring) that it is "the taxonomy layer beneath the
  production dispatch packet (`dispatch.SubagentInput`); it deliberately does
  NOT define a competing packet dataclass" — a positive discipline example
  the new governance code should follow (name a taxonomy, don't fork a
  packet shape).
- **`lifecycle/` package** — already split (prior rethink). `lifecycle/stage.py`
  imports `schemas` (function-local, line 407) — same cycle-avoidance pattern
  seen in `dispatch.py`; not new to this pass, noted for completeness since
  a new receipt schema module would need to avoid the same trap.

## 2. Coupling and dependency direction

**No circular imports found** among the 15 modules read this pass (module-level
grep + targeted read). Confirmed clean: `ledger.py` <- `state._core` only;
`fast_path.py` <- `parser` only; `judge.py`, `hosts.py`, `cost.py`,
`codex_routing.py`, `task_tracking.py` are leaves or near-leaves at module
level. `dispatch.py` avoids cycles with **5 function-local imports**
(`context`, `schemas`, `subagent_profiles` x3, `codex_routing`) rather than
module-level ones — this is a working pattern already established in this
codebase (also used by `lifecycle/stage.py` -> `schemas`), so a new
governance module following the same convention is idiomatic, not a new risk
— but it is a real signal that `dispatch.py` sits at a genuine dependency
crossroads (parser/fast_path DOWN, schemas/context/subagent_profiles/
codex_routing sideways-avoided-as-cycles). Adding a capability-envelope check
or a work-order validator INTO `dispatch.py` itself would add a 6th
function-local import; routing it instead through a lower-level shared module
that both `dispatch.py` and `ledger.py` import from cleanly is the better
seam (see §4).

**`task_tracking.py` -> `ledger.py`** is a correctly-directed, already-real
dependency (confirmed via grep: `task_tracking.py` references
`ledger.check_dispatch_independence` 3x, in prose and in its own
`complete_worker_task` docstring) — the task tracker already treats the
ledger as upstream authority for identity/independence, which is exactly the
direction the proposal's "task tracker bound to real dispatches" needs.

**No inversion found** in this delta set analogous to the prior pass's
`schemas.py` finding (already fixed). `schemas.py` today owns
`SUBAGENT_OUTPUT_*`/`STAGES` as its own constants (confirmed, lines 86-104);
`dispatch.py` imports them back down from `schemas.py` (confirmed, dispatch.py
line 597 comment: "schemas ↔ dispatch cycle... avoided").

## 3. Oversized modules / duplicated logic — the real finding

**No module in this delta set is oversized relative to its cohesion**
(`interaction.py` at 578L/20 defs is the largest, and it is one coherent
concern). The risk in this transformation is not size — it is **schema
duplication across 3 dispatch-adjacent modules**:

1. `ledger.WorkOrder` — `order_id, task, role, file_scope, verifier,
   is_repair, repairs_finding_ref` (the canonical R-0.3 shape).
2. `dispatch.SubagentInput` — `task_spec, required_files,
   upstream_artifact_pointers, dependency_summaries, verifier_expectations,
   required_skills, role` (the actual packet a subagent receives — different
   field names for overlapping concepts: `task` vs `task_spec`, `file_scope`
   vs `required_files`, `verifier` vs `verifier_expectations`).
3. `dispatch.RepairWorkOrder` — `work_order_id, source_inspection_id,
   severity, scope, description, acceptance_criteria` — a THIRD shape, with
   `work_order_id` (not `order_id`) naming the same concept `ledger.WorkOrder`
   calls `order_id`. Its own comment block (dispatch.py lines 960-964)
   explicitly reasons about reusing `fast_path.WorkerScope` to avoid "a
   parallel shape" for scope — but does not extend that discipline to the
   work-order identity/shape itself, so the field-name drift (`order_id` vs
   `work_order_id`) is already live, not hypothetical.

This is the single most concrete piece of evidence for the "smallest boundary
change" question below: a canonical `RenmarkWorkOrder` must not become a
FOURTH shape. It must absorb/rename toward one of the three existing ones
(recommend `ledger.WorkOrder` as the anchor — it is already the schema-
validated, ledger-persisted one) and have `dispatch.SubagentInput` /
`RepairWorkOrder` either construct themselves FROM it or gain a documented,
tested projection to/from it.

**No duplicate role/capability decision logic found** beyond the two-altitude
split noted in §1 (`agency.py` project-phase vs `subagent_profiles.py`
per-dispatch-role) — these are legitimately different concerns, not
accidental duplication, but a capability envelope needs to declare which
altitude it enforces at (per-dispatch role, almost certainly — `agency.py`'s
phase gates are a different, milestone-level concern already covered by
existing lifecycle/agency gates).

## 4. Data ownership: where does a canonical work-order/receipt schema live?

**Recommendation: extend `renmark/ledger.py` in place; do not create a new
top-level schema module next to it.** Reasoning, grounded in what's already
true of the codebase:

- `ledger.py` already owns the 4-shape family, the JSONL append-only store,
  and schema validation with the exact "fail loud, no partial write" contract
  the proposal wants for receipts. Its own docstring already scopes itself as
  "schema + read/write primitives" — a canonical `RenmarkWorkOrder` is an
  in-family addition (a 5th/refined shape), not a new domain.
- `schemas.py` is the *validator* for OTHER canonical JSON files
  (`lifecycle.json`, `pipeline.json`, `limits.json`, etc.) — it validates
  `dispatch.SUBAGENT_OUTPUT_FIELDS` shape today but does not own a ledger
  event schema; putting the work-order schema there would recreate exactly
  the inversion the prior rethink just fixed (a "validator" importing/owning
  a domain shape it doesn't persist). Keep `schemas.py` as validate-only;
  keep `ledger.py` as the domain owner that both defines AND persists its
  shapes.
- Concretely: add `RenmarkWorkOrder` (or extend `WorkOrder` in place with the
  fields the proposal needs — capability-envelope reference, risk tier,
  lens selection) to `ledger.py`, add one pure projection function per
  existing call site shape (`WorkOrder -> SubagentInput`,
  `WorkOrder -> RepairWorkOrder` fields) so `dispatch.py`'s two existing
  dataclasses become *views* constructed from the ledger shape rather than
  independently-typed siblings. This is additive (new function, no field
  renamed under existing callers) and keeps `dispatch.py`'s public dataclass
  names/fields stable for its own tests (5 test files, see §6) while
  correcting the identity drift only at the projection boundary.

## 5. Public API / contract surface for dispatch call sites

Traced actual call sites: `fast_path` (classification), `feature`/`debug`/
`orchestrate`/`rethink`/`resume` skills all reach dispatch through
`cli/_engine.py` -> `dispatch.dispatch_wave` / `dispatch_task_isolated` /
`build_subagent_input`, per the prior assessment's confirmed CLI-is-the-
contract finding (unchanged this pass). **The uniformity gap**: none of these
call sites currently construct or validate a `ledger.WorkOrder` before
dispatching — `ledger.append_ledger_event` exists but (per its own docstring)
is not wired to any live dispatch call site yet ("WP-4, a separate task").
**Smallest boundary change to share one work-order validator across all
call sites without a rewrite**: add one function, e.g.
`ledger.work_order_for_task(task, role, ...) -> WorkOrder`, called once inside
`dispatch.build_subagent_input` (the one function every dispatch path already
funnels through per `dispatch.py`'s own docstring framing) — this makes
`WorkOrder` construction a side effect of the existing shared entry point
rather than requiring 5+ call sites (fast-path/feature/debug/orchestrate/
rethink/resume) to each learn a new API. `subagent_gate.py`'s pre-dispatch
verdict function is the second shared funnel point (already called before
dispatch per its own docstring's numbered sequence) — a capability-envelope
check is a second, composable verdict added there, not a rewrite of the gate.

## 6. Extension points for lens selection + failure-rule registry (no new prompt-injection path)

- **Failure-rule registry**: extend `recurrence.py`, do not create a new
  module. It already has bounded/capped storage, fingerprinting via
  `scan.content_fingerprint`, and a `RemediationClass` distinction between a
  one-off `patch` and a `durable_guard`. The proposal's registry is
  `recurrence.py`'s `durable_guard` entries read back as constraints at
  dispatch time — a new *reader* function (`recurrence.active_guards_for(...)`)
  consumed by `subagent_gate.py`'s pre-dispatch check, not a new store. This
  avoids a second parallel "rules that constrain a prompt" pathway — the
  constraint text still only ever reaches a dispatch packet through the
  existing `dispatch.SubagentInput`/`build_subagent_input` funnel (§5), so
  there is exactly one place text is composed into what a subagent sees, not
  two.
- **Lens selection (risk-tiered inspection)**: `ledger.InspectionReport`
  already carries `verdict`/`findings`/`generator`/`dispatch_identity`. A risk
  tier + lens name are additive fields on this existing dataclass (or a
  thin wrapper `RiskTier` enum consumed by `emit_inspection_verdict`'s
  caller), not a new inspection pathway — `subagent_profiles.py`'s existing
  role model (`inspector` role, read-only enforcement already documented in
  `CLAUDE.md`) is the natural place a lens-selection *policy* function
  (`resolve_lens_for(work_order) -> LensName`) would live, mirroring
  `cost.py`'s existing role of being the "policy, not mechanism" module for
  tier selection (prior assessment §6) — same shape of seam, different
  policy domain. This keeps lens selection out of `dispatch.py`'s packet-
  construction path entirely (no new prompt-injection surface), consistent
  with `context.py`'s already-enforced discipline that dispatch packets carry
  metadata pointers, never composed prose bodies.

## 7. Test isolation/testability of these modules today

This is a genuine strength, confirmed by direct file inventory — a sharp
contrast to the prior assessment's `lifecycle.py`/`_engine.py` findings:

| Module | Test files | Note |
|---|---|---|
| `dispatch.py` | 5 (`test_dispatch.py`, `test_dispatch_isolation.py`, `test_dispatch_scope_generalization.py`, `test_cross_host_dispatch_e2e.py`, `test_r0_2_dispatch_regression_baseline.py`) | Scenario-named, includes a regression-baseline pin |
| `ledger.py` | 2 (`test_ledger.py`, `test_ledger_wiring.py`) | Split between schema tests and wiring tests — good separation |
| `task_tracking.py` | 3 (`test_task_tracking.py`, `test_task_tracking_contract.py`, `test_task_tracking_engine_wiring.py`) | Contract test distinct from engine-wiring test — exactly the split a capability-envelope addition would want to extend |
| `subagent_gate.py` | 2 (`test_subagent_gate.py`, `test_subagent_gate_r008.py`) | R-008-specific regression test already named — precedent for adding an R-0.x-style named test for a new gate rule |
| `agency.py` | 2 | behavior test split from state test |
| `program.py` | 2 (`+program_driver`) | |
| `fast_path.py`, `judge.py`, `interaction.py`, `hosts.py`, `cost.py`, `codex_routing.py`, `subagent_profiles.py`, `recurrence.py`, `context.py` | 1 each (`context.py` has 2, incl. checkpoint) | 1:1 module:test-file, but each module is small/cohesive enough (per §3) that 1:1 is appropriate here, unlike `lifecycle.py`'s prior 1:50-defs ratio |

**Implication**: unlike the prior pass's `_engine.py`/`lifecycle.py` (coarse
1:many test ratios flagged as a refactor-safety risk), this delta set's
modules are already at a testability grain where adding new fields/functions
(a capability-envelope check, a lens-selection function, a recurrence-registry
reader) can get a dedicated new test file following the existing
`_contract.py` / `_wiring.py` / `_r0XX.py` naming convention already
established in `task_tracking`/`subagent_gate` — no test-infrastructure work
is a prerequisite.

## 8. Adding capability-envelope enforcement without touching every dispatch call site

Traced: every dispatch path (fast-path, feature, debug, orchestrate, rethink,
resume) funnels through exactly two shared functions today —
`dispatch.build_subagent_input` (packet construction) and, upstream of that,
`subagent_gate`'s pre-dispatch verdict (already called before Agent-tool
issuance per its own docstring's numbered live-call sequence in §"Live call
sequence"). **This means capability-envelope enforcement is a ONE-function
addition, not an N-call-site rewrite**: add a
`subagent_gate.check_capability_envelope(role, requested_scope) -> EnvelopeVerdict`
pure function (same shape/style as the existing `SubagentVerdict`), called
from the same place `subagent_gate`'s existing check is already called from.
Every one of the 6 named call sites gets the enforcement "for free" because
they already call into `subagent_gate` (fast-path) or `dispatch.py`'s shared
`build_subagent_input`/`dispatch_task_isolated` (the rest) — this is the
concrete evidence for "smallest boundary change," not a general claim.

## 9. Explicitly NOT justified — flag against over-abstraction

- **No new microservice/daemon/broker for the event log.** `ledger.py`'s
  flat-file JSONL append-only store, already schema-validated and
  fail-loud-on-write, fully satisfies "durable events/recovery" for a
  single-process, file-backed CLI tool — a database or message broker here
  would be pure speculative complexity, and the proposal's own non-goals list
  explicitly excludes this.
- **No new top-level "governance" package.** Every governance concept traced
  in this assessment has an existing, correctly-scoped home
  (`ledger.py` for receipts, `subagent_gate.py` for pre-dispatch checks,
  `recurrence.py` for the failure registry, `subagent_profiles.py` for
  capability envelopes, `judge.py` for calibrated judging, `interaction.py`
  for selector/headless enforcement). Introducing a new `renmark/governance/`
  package would fragment ownership that is already correctly distributed —
  it would recreate, at package granularity, the same "competing shape"
  problem identified in §3 at the dataclass granularity.
- **No second work-order/receipt schema.** Covered in §3/§4 — this is the
  one place a new module WOULD be unjustified scope creep; the fix is
  extension of `ledger.py`, not a parallel `renmark/work_orders.py`.
- **No new prompt-composition pathway for lens/constraint text.** Covered in
  §6 — lens selection and failure-rule text must reach a subagent only
  through the existing `dispatch.build_subagent_input` packet funnel; a
  second "inject this into the prompt" mechanism would reopen exactly the
  context-hygiene/G3 leak the existing `SubagentInput`/`context.py` machinery
  was built to close.

## 10. Current-state module/dependency map (delta from prior assessment)

```
   plugin/skills/*/SKILL.md (fast-path, feature, debug, orchestrate, rethink, resume)
                 |  (renmark-execute <subcmd>, via cli/_engine.py — unchanged from prior pass)
                 v
   ┌─────────────────────────── dispatch.py (1052L, dispatch/packet engine) ───────────────────────────┐
   │  SubagentInput/SubagentOutput (packet)     InspectorFinding/RepairWorkOrder (2nd work-order shape) │
   │  imports (module-level): fast_path, parser, providers.claude_agent                                 │
   │  imports (function-local, cycle-avoid): context, schemas, subagent_profiles x3, codex_routing       │
   └───────────────────────────────────────────────────────────────────────────────────────────────────┘
        |                    |                          |
        v                    v                          v
   fast_path.py         subagent_gate.py            subagent_profiles.py (leaf)
   (leaf: parser)       (leaf-ish: cost,             ProfileSpec.allowed_targets:
   WorkerScope,          subagent_profiles)           "informational... future
   ClassificationVerdict  <- pre-dispatch verdict      Agency Mode" (UNENFORCED)
                            funnel point (§8)
   ledger.py (558L, near-leaf: state._core only)
   WorkOrder/WorkResult/InspectionReport/Escalation  <-- 1st (canonical, schema-validated) work-order shape
   check_dispatch_independence, emit_inspection_verdict
        ^
        | (already-correct direction, confirmed)
   task_tracking.py (436L) --reuses check_dispatch_independence--> ledger.py
   own store: tasks.json; MissingEvidenceError/SelfApprovalError

   judge.py (leaf)        interaction.py (leaf: hosts)      recurrence.py (leaf: scan)
   escalation-only,        ChoiceSet/native-page/fallback     bounded fingerprinted store,
   injectable runner,      ALREADY exists; enforced vs        RemediationClass patch|
   defensive parse         advisory is the delta              durable_guard ALREADY exists

   cost.py (leaf, policy authority)   codex_routing.py (leaf)   hosts.py (leaf)
   agency.py --> delivery_state (leaf)        context.py --> skillmeta, lifecycle (taxonomy only,
   (project-phase role altitude)               explicitly no competing packet dataclass)

   NO circular imports found in this 15-module delta set.
   3 competing "work order" shapes confirmed: ledger.WorkOrder / dispatch.SubagentInput /
   dispatch.RepairWorkOrder (field-name drift: order_id vs work_order_id already live).
```

## 11. Target module map — where the proposal's new concepts should live

```
   ledger.py  (EXTENDED, not replaced)
     + RenmarkWorkOrder fields added to existing WorkOrder (risk tier, capability-
       envelope ref, lens name) OR a documented projection between WorkOrder and
       dispatch.SubagentInput/RepairWorkOrder — removes the 3-shape drift (§3/§4)
     + work_order_for_task(...) -> WorkOrder, called from dispatch.build_subagent_input
       (single funnel, §5) — wires WP-4 (previously deferred) without new call sites

   subagent_gate.py  (EXTENDED)
     + check_capability_envelope(role, requested_scope) -> EnvelopeVerdict
       (pure fn, same style as existing SubagentVerdict; reads
       subagent_profiles.ProfileSpec.allowed_targets — makes the field's
       docstring promise real) — called from the same pre-dispatch funnel
       every call site already uses (§8)
     + active_guards_for(...) reader against recurrence.py's durable_guard
       entries (§6) — failure-rule registry consumed here, not composed
       into a prompt anywhere else

   recurrence.py  (EXTENDED)
     + read-side accessor for "active durable guards relevant to this task"
       consumed only by subagent_gate.py — no new store, no new schema

   judge.py  (EXTENDED)
     + calibration/bias-control parameters on Verdict / compose_judge_prompt
       (blind inputs, e.g. redact which side is baseline vs candidate before
       the prompt is composed) — stays escalation-only, stays a leaf

   interaction.py  (EXTENDED)
     + "enforced" mode: reject a non-selector fallback where the host
       capability (hosts.capabilities_for) says a native picker is available
       — turns today's advisory ChoiceSet/fallback split into a hard check,
       same dataclasses, no new module

   subagent_profiles.py  (EXTENDED)
     + allowed_targets becomes a real glob/frozenset checked by
       subagent_gate's new envelope function, not prose

   task_tracking.py  (EXTENDED)
     + bind task creation to a real ledger.WorkOrder.order_id instead of an
       independently-chosen task_id, closing REQ-31's "bound to real
       dispatches" gap using the existing reuse pattern already proven for
       check_dispatch_independence

   NEW module: none required.
   NEW top-level package: none required (explicitly rejected, §9).
```

**Allowed dependency directions (target):** `ledger.py` stays near-leaf
(`state._core` only) and gains no new outward dependency — it is extended
in place, so other modules keep importing FROM it, not the reverse.
`subagent_gate.py` gains `recurrence` as a new import (currently imports
`cost`, `subagent_profiles`) — still leaf-consuming, no new cycle risk
(`recurrence.py` imports only `scan.py`). `judge.py` and `interaction.py`
stay leaves. No proposed change requires `dispatch.py` to gain a new
module-level import — the capability-envelope and work-order wiring both
route through `subagent_gate.py` and `ledger.py` respectively, which
`dispatch.py` already touches via existing function-local imports.

## 12. Migration seams / sequencing notes for Stage 6-8

1. **Resolve the 3-shape work-order drift FIRST** (§3/§4) — every other
   governance capability (capability envelope, receipts, task-tracker
   binding) references "the work order," so fixing its identity/shape once
   is a prerequisite that materially reduces rework risk for everything
   downstream, per the intake's own instruction to sequence prerequisite
   refactors only where they measurably reduce risk. This one qualifies.
2. **Capability-envelope enforcement (§8) and failure-rule registry wiring
   (§6) can proceed in parallel** — different files (`subagent_profiles.py`
   vs `recurrence.py`), same consumer (`subagent_gate.py`), no shared
   mutable state, additive functions only.
3. **Judge calibration and interaction enforcement (§11) are independent
   leaves** — no ordering dependency on the above, can slot into any release.
4. **Every extension in §11 preserves existing dataclass field names and
   existing public functions** — none require the `renmark/state/`-style
   package-split treatment the prior assessment used for `lifecycle.py`/
   `_engine.py`; these are additive-field/additive-function changes to
   already-well-tested, already-cohesive, already-correctly-directed modules.

## 13. Summary

**Module count assessed:** 15 (`dispatch.py`, `ledger.py`, `fast_path.py`,
`subagent_gate.py`, `judge.py`, `task_tracking.py`, `interaction.py`,
`hosts.py`, `cost.py`, `codex_routing.py`, `subagent_profiles.py`,
`agency.py`, `program.py`, `recurrence.py`, `context.py`) + the `lifecycle/`
package for the schemas cross-reference.

**Biggest risk:** three independently-shaped "work order" dataclasses already
coexist (`ledger.WorkOrder`, `dispatch.SubagentInput`, `dispatch.RepairWorkOrder`)
with real field-name drift (`order_id` vs `work_order_id`) — building the
proposal's canonical work-order contract without first reconciling these
would create a fourth shape and lock in the drift rather than resolve it.

**No circular imports; no oversized/low-cohesion modules** in this delta set
— test coverage per module is materially better-grained than the prior
pass's `lifecycle.py`/`_engine.py` findings, and every governance capability
the proposal names maps onto an existing, correctly-scoped module rather than
requiring a new one.

---

## Discovery Direction Gate — decision (2026-08-04)

**Chosen direction:** Evidence-sequenced, full scope (all 13 proposal
requirements stay in scope). Reordered ahead of the proposal's literal
Release A-H sequence per stage 1-5 evidence:

1. Reconcile the 3 disjoint work-order shapes (`ledger.WorkOrder`,
   `dispatch.SubagentInput`, `dispatch.RepairWorkOrder`) into one canonical
   schema first — stage 5's top finding. No new schema may be added before
   this reconciliation.
2. Close R-0.2's known scope-enforcement production-caller gap (F1) via
   Claude Code `PreToolUse` hooks as an early win for Requirement 2 —
   backed by stage 4's external-benchmark finding that current practice
   favors code/hook enforcement over prompt-only restriction.
3. Land the REQ-30 update release (per the exception check-in decision
   above, and in `prd-acceptance-map.md`) before any Critical-tier gate or
   dispatch-scheduling (Requirement 9) work begins.
4. Build Requirements 5/6/7 (risk-tiered inspection + falsification lenses,
   calibrated judge, failure-derived constraint registry) as genuinely new
   capability layered on the reconciled work-order/receipt foundation —
   these are entirely greenfield in code today (confirmed by stage 1 survey
   and the peer-supplied Req 5-7 deep dive).
5. Upgrade `/renmark:rethink` itself (Requirement 12) last, once the
   assurance contracts it needs to consume (work order, inspection
   contract, receipts) actually exist to consume.

**Rejected alternatives:** the proposal's literal Release A-H order (loses
the evidence-driven reordering, notably front-loading schema reconciliation
and the REQ-30 update); narrowing scope to Req 1/2/3 only and deferring
Req 5/6/7/9 to a separate later transformation (rejected — Owner kept full
scope).

This decision governs Stage 6 classification and Stage 7 blueprint
sequencing below.

---
artifact_type: rethink-roadmap
schema_version: 1
created_at: 2026-08-04T00:00:00Z
revised_at: 2026-08-05T00:00:00Z
source_sha: e6898917ddf3a30505bb01b1b0569c28a187d792
related_plan: null
generator: sonnet
stale_after: null
dependency_refs:
  - .renmark/rethink/governed-orchestration-assurance/intake.md
  - .renmark/rethink/governed-orchestration-assurance/classification.md
  - .renmark/rethink/governed-orchestration-assurance/target-blueprint.md
  - .renmark/rethink/governed-orchestration-assurance/baseline.md
  - .renmark/rethink/governed-orchestration-assurance/prd-acceptance-map.md
  - .renmark/rethink/governed-orchestration-assurance/modularity-assessment.md
---

# Incremental transformation roadmap — Stage 8 of `/renmark:rethink` (governed-orchestration-assurance)

Sixteen small, independently usable, Owner-testable releases — never a
big-bang rewrite. Built as a `renmark.program` (`Program`/`StageNode`/
`TaskNode`, same shapes `/renmark:roadmap` and the closed
`renmark-architecture` rethink already used — no parallel format invented).
Release 1 is fixed as "baseline and compatibility coverage" per the
pipeline's hard default rule; no Owner override was given, so it is not
reordered. All other ordering follows the binding sequencing from the
Discovery Direction Gate (modularity-assessment.md) and the Exception
check-in decision (prd-acceptance-map.md):

1. Work-order reconciliation first (releases 3-4).
2. `PreToolUse` scope-enforcement gap closed early (releases 5-6).
3. REQ-30 update release (release 7) before any Critical-tier-gate or
   dispatch-scheduling work.
4. Requirements 5/6/7 built on the reconciled foundation (releases 8-10),
   gated on release 7 closing.
5. `/renmark:rethink` self-upgrade (release 16) last.

The 7 Unknown-needs-a-spike classification items are folded in as their own
budget-boxed spike tasks (never open-ended) inside the release whose design
question they answer, per classification.md's stop conditions.

---

## Stage 8 revision — 2026-08-05

An independent peer review of the full 16-release roadmap (performed after the
Execution Gate approved it and after Release 1 ran, partially — see
`.renmark/reviews/2026-08-05-8ea7b27.verification.md`, corrected to
`completion_state: partial`) found 6 specific, credible gaps in Releases 3,
6, 8, 10, 13, and 15. This revision fixes those 6 releases in place, reusing
Stages 1-7's artifacts (`intake.md`, `survey.md`, `baseline.md`,
`prd-acceptance-map.md`, `external-benchmark.md`, `modularity-assessment.md`,
`classification.md`, `target-blueprint.md`) unchanged — Stages 1-7 were not
rerun. **Releases 1 and 2 were not flagged and were not touched**, with one
narrow exception required by Gap 6 below: Gap 6 (test sequencing) itself
names small, additive edits to the "Migration steps" bullet of Releases 1, 4,
and 9 (adding one fixture-authorship line each, and correcting one piece of
Release 1's compat-guarantee prose to match the test file's actual floor
semantics) — no other content in Releases 1, 2, 4, 9 changed. All 16 release
numbers, their ordering, and the release-sequence table are unchanged. The
6 gaps and this release's fixes are summarized inline in each affected
release's section below.

---

## Program state — materialization note (read before Stage 9)

**`write_program` was NOT invoked for this roadmap.** `renmark.program.
write_program(repo, program)` is a plain, standalone-callable function
(`Program` in, `Path` out — no other live state required), so it is
mechanically usable from a one-off script. It was deliberately not called
here because `.renmark/state/program.json` currently holds the **prior**
`renmark-architecture-rethink-roadmap` program, and its own stored state is
inconsistent with what `intake.md` claims: intake.md states "all 7 releases
shipped 2026-08-04," but the live `program.json` still shows task
`r1-req30-baseline-measurement` (Release 1, that program) at `status:
"pending"`, not `"done"` — only 6 of 7 stages are actually marked `done`
Stage-1's second task never got closed out. Overwriting `program.json` now
would silently lose that unresolved task's resumable state, exactly the
failure mode `ProgramStateError`/atomic-write is designed to prevent at the
file level but cannot prevent at the *call* level (there is only one active
program slot).

**What Stage 9 (Execution Gate) must do before materializing this roadmap
as the active program:**
1. Resolve the stale prior program first — either close
   `r1-req30-baseline-measurement` for real (confirm whether the
   REQ-30 numeric baseline that release 7 below now measures makes that
   old task retroactively satisfiable) or explicitly mark it `partial`/
   `blocked` with a one-line reason.
2. Snapshot/archive the resolved prior program's `program.json`/`program.md`
   to `.renmark/rethink/renmark-architecture/archive/` (the same pattern
   that program's own roadmap.md used for the program it superseded), so no
   historical state is silently lost.
3. Construct a new `Program(feature="governed-orchestration-assurance-roadmap",
   mode="staged", source_sha=<current HEAD>, stages=[...])` from the 16
   releases below (one `StageNode` per release, `serves` set to the primary
   proposal `Req-n`/PRD `REQ-n` id, one `TaskNode` per migration-step
   group) and call `write_program(repo, program)` once, at Stage 9, as part
   of the Execution Gate approval — not before an Owner has actually
   approved starting execution.

This mirrors the hard requirement itself ("if `write_program` requires live
pipeline state that doesn't make sense to fabricate at this stage, note that
clearly ... and say what's needed to materialize it for real at stage 9").

---

## Release sequence

| # | Stage id | Title | Primary Req/AC | Gated by |
|---|---|---|---|---|
| 1 | `release-1-baseline-compat-coverage` | Baseline and compatibility coverage | REQ-30, all 9 baseline checks | — (hard-default first) |
| 2 | `release-2-role-altitude-adr` | Role-model altitude ADR (spike #28) | cross-cutting (Req 1/2/12) | Release 1 |
| 3 | `release-3-work-order-reconciliation` | Canonical work-order reconciliation | AC-1 (Req 1) | Release 2 |
| 4 | `release-4-task-tracker-selector-binding` | Task tracker bound to `WorkOrder.order_id` + selector bypass guard | AC-3, AC-4 (Req 3, Req 4) | Release 3 |
| 5 | `release-5-pretooluse-spike` | `PreToolUse` capability-envelope spike (#7) | AC-2 (Req 2) | Release 3 |
| 6 | `release-6-capability-envelope-wiring` | Capability-envelope enforcement wiring | AC-2 (Req 2) | Release 5 |
| 7 | `release-7-req30-update` | REQ-30 update release (measure + PRD gate) | REQ-30, item 9 | Release 1 |
| 8 | `release-8-risk-tiered-inspection` | Risk-tier spike (#10b) + risk-tiered `InspectionContract` + lenses | AC-5 (Req 5) | Release 7 |
| 9 | `release-9-calibrated-judge` | Calibrated blind LLM-judge (3-state + bias controls) | AC-6 (Req 6) | Release 7 |
| 10 | `release-10-failure-rule-registry` | Failure-derived constraint registry | AC-7 (Req 7) | Release 7 |
| 11 | `release-11-dispatch-scheduling` | Routing-overlap spike (#18) + policy-aware dispatch scheduling | AC-9 (Req 9) | Release 7 |
| 12 | `release-12-context-memory-governance` | Context/memory governance extension + state-fragmentation spike (#22) | AC-10 (Req 10) | Release 1 |
| 13 | `release-13-durable-events-recovery` | Durable-events field completeness + orphan-detection spike (#24) + analytics reconciliation | AC-11 (Req 11) | Release 3 |
| 14 | `release-14-guardrail-metrics` | Guardrail metrics | AC-13 (Req 13) | Release 6, Release 13 |
| 15 | `release-15-behavioral-eval-suite` | 20-case behavioral eval suite authorship | AC-8 (Req 8) | Releases 3, 6, 8, 9, 10 |
| 16 | `release-16-rethink-self-upgrade` | `/renmark:rethink` self-upgrade | AC-12 (Req 12) | Releases 3, 8, 9, 10, 13 (last, by Discovery Direction Gate) |

All 13 proposal requirements traced: Req1→R3, Req2→R5/R6, Req3→R4, Req4→R4,
Req5→R8, Req6→R9, Req7→R10, Req8→R15, Req9→R11, Req10→R12, Req11→R13,
Req12→R16, Req13→R14.

---

### Release 1 — Baseline and compatibility coverage (hard-default first release)

- **User-observable value**: `baseline.md`'s 9 compatibility checks and its
  still-unpopulated REQ-30 numeric table stop being point-in-time prose and
  become runnable regression guards + real measured numbers. No architecture
  change.
- **AC-ids satisfied/advanced**: none of AC-1..13 directly (this release is
  the prerequisite substrate); unblocks REQ-30's numeric baseline that
  release 7 depends on.
- **Compatibility guarantee** *(prose corrected 2026-08-05 — peer-review
  Gap 6a: this bullet described the count as pinned, stricter than what the
  actual test asserts)*: all 9 baseline.md checks turned into executable
  assertions (1: `pytest -q` >= 1970 passed — a floor/no-regression
  assertion, matching `tests/test_governed_orchestration_baseline_compat.py`
  's `assert passed >= 1970`, not a pinned-exact count; 31 skipped is the
  baseline figure, also not itself pinned exact; 2: `classify_fast_path`
  5-signal contract; 3: `verify_worker_scope` Layer-B
  git-diff semantics; 4: `check_dispatch_independence` raise conditions;
  5: `VERDICTS` vocabulary closed-set; 6: `complete_worker_task` no-self-
  approval gate; 7: `assert_metadata_only`; 8: REQ-30 qualitative guarantees
  as a lint/test; 9: `renmark:inspector` read-only tool allowlist).
  Verification: fresh `pytest -q` (not reused from a prior wave) +
  `renmark-execute --behavior`.
- **Migration steps**: add tests only (one new `test_baseline_compat_*.py`
  file per check group, or extend existing scenario-named files where a
  direct one already exists) — no production code moves. Separately, run
  and record the four representative scenarios (Start, Feature/Fix,
  Orchestrate, Rethink) into `.renmark/memory/orchestration-baseline.md`'s
  currently-unpopulated table (real token/wall-clock/dispatch-count spend —
  requires its own cost-preview + Owner go-ahead per that file's own flag).
  Per Gap 6's fixture-split (2026-08-05), also author the "fast-path
  accept/reject" behavioral-eval fixture(s) against `classify_fast_path`'s
  contract here, for Release 15 to wire into the full 20-case suite.
- **Observability hook**: `.renmark/memory/orchestration-baseline.md` gets
  real numbers in place of "not yet measured"; the 9 checks become part of
  the standard `pytest -q` run so any future release's compat claim is
  mechanically checkable, not asserted.
- **Rollback path**: revert the test-only commit(s); zero production blast
  radius.
- **Owner acceptance scenario**: Owner runs `pytest -q`, sees the 9
  compatibility checks passing as named tests, and sees
  `orchestration-baseline.md` carrying real figures instead of "not yet
  measured."

### Release 2 — Role-model altitude ADR (spike #28)

- **Value**: closes the one open design question a capability envelope
  (release 6) needs answered before it is built — does it enforce at the
  per-dispatch-role altitude (`subagent_profiles.py`) or the project-phase
  altitude (`agency.py`), or both?
- **AC-ids**: cross-cutting, touches Req 1/2/12; prd-acceptance-map's
  deferrable spec debt item ("REQ-22's Agency/Orchestrator mapping ...
  needs a short PRD note, not new code, before Release B").
- **Compatibility guarantee**: #7 (REQ-20 metadata-only dispatch, unaffected
  — no code change) and #9 (`renmark:inspector` read-only, unaffected).
- **Migration steps (bounded spike, 1 session, no code)**: produce one ADR
  paragraph confirming modularity-assessment §1's lean ("per-dispatch role,
  almost certainly — `agency.py`'s phase gates are a different,
  milestone-level concern already covered by existing lifecycle/agency
  gates"), get Owner/maintainer sign-off. Stop condition: ADR note accepted;
  no code change unless the confirmation contradicts the lean.
- **Observability hook**: ADR note committed under `.renmark/memory/` (or
  a `decisions.md` entry) referenced by release 6's design.
- **Rollback path**: n/a — no code changed; a wrong ADR conclusion is
  corrected by a follow-up note, not a revert.
- **Owner acceptance scenario**: Owner reads the one-paragraph ADR and
  confirms (or corrects) which altitude the capability envelope will
  enforce at.

### Release 3 — Canonical work-order reconciliation

*(Revised 2026-08-05 — peer-review Gap 1: this section was too thin and
forward-referenced an undefined `RiskTier` type; see the design decision and
expanded scope below.)*

- **Value**: the three independently-shaped "work order" dataclasses
  (`ledger.WorkOrder`, `dispatch.SubagentInput`, `dispatch.RepairWorkOrder`)
  become one canonical anchor + two projections, closing the field-name
  drift (`order_id` vs `work_order_id`) that blocks every downstream
  governance capability from having one thing to reference — and the anchor
  now carries schema room for the full accepted `RenmarkWorkOrder` contract,
  not just 4 fields, so later releases aren't retrofitting the schema.
- **AC-ids**: AC-1 (Req 1) — target-blueprint.md's Release B.
- **Design decision — `risk_tier` typing (Gap 1)**: Release 3 adds
  `risk_tier` as an **untyped placeholder** (`risk_tier: str | None`), not a
  `RiskTier` enum. Release 8 defines the real `RiskTier` enum and migrates
  the field's type. Chosen over "Release 3 defines a minimal `RiskTier` stub"
  because modularity-assessment.md §6 explicitly places the `RiskTier` enum
  inside the "lens selection (risk-tiered inspection)" extension point —
  "a thin wrapper `RiskTier` enum consumed by `emit_inspection_verdict`'s
  caller" — which is Release 8's module-boundary seam
  (`subagent_profiles.py`/`ledger.InspectionReport` orbit), not Release 3's
  work-order-anchor seam (§5). Defining the enum here would put type
  ownership in the wrong module relative to that stated boundary; the
  placeholder keeps Release 3 additive-only while Release 8 owns the real
  vocabulary (an additive-compatible type narrowing, not a rename, when it
  lands).
- **Compatibility guarantee**: #1 (`pytest -q` count, only additive fields);
  #7 (REQ-20 metadata-only — `SubagentInput`'s public field names
  `task_spec`/`required_files`/`verifier_expectations` stay stable, only
  populated by reading off a constructed `WorkOrder`); the 5 dispatch test
  files (`test_dispatch.py`, `test_dispatch_isolation.py`,
  `test_dispatch_scope_generalization.py`, `test_cross_host_dispatch_e2e.py`,
  `test_r0_2_dispatch_regression_baseline.py`) must stay green unmodified in
  their assertions on field names; all newly-added fields below are
  additive (`Optional`/default-empty), so no existing `WorkOrder`
  construction site breaks.
- **Migration steps**: (a) add additive fields to `ledger.WorkOrder` —
  `risk_tier: str | None` (placeholder, see design decision above),
  `capability_envelope_ref`, `lens: str | None`, `schema_version`, and, to
  cover more of the accepted `RenmarkWorkOrder` contract now rather than
  retrofitting later: `correlation_id: str | None`, `idempotency_key:
  str | None`, `dependencies: list[str]` (default empty), `scope: dict |
  None` (or a minimal `WorkOrderScope` stub), `budget: dict | None`,
  `routing: dict | None`, `constraints: dict | None`, `interaction_policy:
  dict | None` — present in the schema, not necessarily wired to real
  enforcement yet (see the field table below); (b) add
  `ledger.work_order_for_task(task, role, ...) -> WorkOrder`; (c) call it
  once inside `dispatch.build_subagent_input` (the one funnel all 6 dispatch
  call sites already use); (d) rename `RepairWorkOrder.work_order_id` to
  `order_id`, require it to resolve to a real `WorkOrder.order_id` emitted
  by `work_order_for_task`; keep `severity`/`source_inspection_id`/
  `description`/`acceptance_criteria` unchanged (repair-specific, legitimate).
- **Schema fields added now vs. enforcement deferred to which release**:

  | Field | Schema lands | Real enforcement/consumption lands in |
  |---|---|---|
  | `risk_tier` (placeholder `str\|None`) | Release 3 | Release 8 (typed `RiskTier` enum + classifier) |
  | `capability_envelope_ref` | Release 3 | Release 6 (envelope enforcement) |
  | `lens` | Release 3 | Release 8 (lens vocabulary + `resolve_lens_for`) |
  | `schema_version` | Release 3 | Release 3 (self-contained) |
  | `correlation_id` / `idempotency_key` | Release 3 | Release 13 (durable-events field completeness) |
  | `dependencies` | Release 3 | Release 11 (dispatch scheduling) |
  | `scope` | Release 3 | Release 6 (capability-envelope wiring) |
  | `budget` / `routing` | Release 3 | Release 11 (policy-aware dispatch scheduling) |
  | `constraints` | Release 3 | Release 10 (failure-rule registry injection) |
  | `interaction_policy` | Release 3 | Release 4 (selector-bypass guard) |

- **Observability hook**: a new cross-entry-point wiring test asserting
  every one of the 6 dispatch call sites (fast-path, feature, debug,
  orchestrate, rethink, resume) produces a `WorkOrder` via the shared
  funnel, not a bespoke path; a schema test asserting every field in the
  table above is present with the stated default/optional type.
- **Rollback path**: revert the commit; `SubagentInput`'s public shape is
  unchanged so no caller-side rollback is needed.
- **Owner acceptance scenario**: Owner triggers a repair dispatch and
  confirms its `RepairWorkOrder.order_id` resolves to a real, ledger-visible
  `WorkOrder` — closing the "repair-work-order emission is prose-invoked
  only" (F2) residual — and reviews the field table above to confirm which
  fields are schema-only today vs. already enforced.

### Release 4 — Task tracker bound to `WorkOrder.order_id` + selector bypass guard

- **Value**: `task_tracking.py` task identity stops being an independently-
  chosen `task_id` and becomes bound to a real ledger `WorkOrder.order_id`;
  `interaction.py` gains a hard guard so a skill cannot silently print a
  numbered fallback when a native selector is available.
- **AC-ids**: AC-3 (Req 3), AC-4 (Req 4).
- **Compatibility guarantee**: #6 (`complete_worker_task`'s no-self-approval
  gate — binds task creation to `order_id` but does not touch the
  independence-check call itself); #7 (no new prose to a dispatch packet).
- **Migration steps**: (a) `task_tracking.create_or_reuse_task` accepts and
  persists the originating `WorkOrder.order_id`, using release 3's funnel;
  (b) `interaction.py` gains an "enforced" mode: reject a non-selector
  fallback where `hosts.capabilities_for` reports a native picker available
  — same `ChoiceSet`/fallback dataclasses, no new module; (c) cosmetic
  "concise displayed list" format for Role/worker+model/Budget/Verification
  deferred to this release per prd-acceptance-map's own deferral note; (d)
  per Gap 6's fixture-split (2026-08-05), author the "task-tracker
  transitions" behavioral-eval fixture(s) against this release's
  `order_id`-bound task records, for Release 15 to wire in.
- **Observability hook**: a `bugs.md`-style regression test named after the
  2026-06-14 "Hand-off picker not re-rendered on continuation turns"
  incident, proving the enforced-mode guard catches that exact failure mode.
- **Rollback path**: revert the commit; `interaction.py`'s existing advisory
  mode remains available as a fallback flag if the enforced mode regresses
  a host.
- **Owner acceptance scenario**: Owner inspects a task record and sees it
  carries a real `order_id`; Owner also tries to trigger a numbered-fallback
  bypass on a host with a native picker and sees it rejected.

### Release 5 — `PreToolUse` capability-envelope spike (#7)

- **Value**: answers whether pre-action, hook-time, metadata-driven
  allow/deny enforcement is feasible on both Claude Code and Codex before
  any production wiring is built — the load-bearing design question for
  Req 2's "defense-in-depth" ask.
- **AC-ids**: AC-2 (Req 2).
- **Compatibility guarantee**: #3 (`fast_path.verify_worker_scope`'s
  post-action Layer-B semantics stay untouched — this is a prototype for a
  NEW, additive pre-action layer, not a replacement).
- **Migration steps (bounded spike, 1 session, prototype-only)**: read
  Claude Code's `PreToolUse` hook contract (input shape, blocking semantics,
  available metadata); prototype one hook wired to one agent profile's
  `allowed_targets`; separately confirm Codex's own enforcement mechanism
  (prompt-only vs OS-level) since the envelope must work identically on
  both hosts. Evidence requirement: one working hook config + one
  passing/one blocking integration test. Stop condition: hook contract
  supports metadata-driven allow/deny (proceed to release 6's design as
  specified) or it does not (release 6 falls back to post-action-only
  enforcement, documented, escalated to Owner).
- **Observability hook**: the prototype hook's pass/block integration test
  itself, committed as spike evidence even if not wired to production.
- **Rollback path**: n/a — prototype-only, no production call site touched.
- **Owner acceptance scenario**: Owner reviews the spike's one-page finding
  (hook feasible / not feasible, on which host(s)) before release 6 begins.

### Release 6 — Capability-envelope enforcement wiring

*(Revised 2026-08-05 — peer-review Gap 2: this section originally only
covered path enforcement; Req 2 also requires command allowlists,
network-domain, git-action, and external-action restrictions, spend/timeout
restrictions, and honest per-control status reporting. See the expanded
migration steps and the new status table below.)*

- **Value**: closes AC-2's `failed` status across all of Req 2's control
  dimensions, not paths alone — `subagent_profiles.
  ProfileSpec.allowed_targets` stops being "informational for now" prose and
  becomes a real, enforced check; `fast_path.verify_worker_scope`/
  `dispatch.enforce_wave_dispatch_scopes` (fully built, fully tested, never
  called in production) gets a real production caller (closes F1); command,
  spend/timeout, network, git-action, and external-action controls get an
  honest per-control enforcement-status record rather than an implied
  blanket "enforced" claim.
- **AC-ids**: **AC-2 partially advanced (Req 2)** — paths, commands, and
  spend/timeout become mechanically enforced this release; network-domain,
  git-action, and external-action restrictions remain `advisory`/
  `unsupported` pending a scoped follow-up (see status table below). Per the
  cross-cutting acceptance-tracing requirement, this release does not claim
  AC-2 fully "met." Still target-blueprint.md's Release C; still the
  BLOCKING PRD debt named in prd-acceptance-map.md ("Any release sequencing
  must land Release C before claims of Worker/Architect/Inspector
  containment are made") — that debt is resolved for the path/command/
  spend dimensions this release, not for network/git/external-action.
- **Compatibility guarantee**: #3 (Layer-B git-diff semantics stay the
  authoritative post-action check — the new hook, if release 5's spike
  succeeded, is additive defense-in-depth, never a replacement); #9
  (`renmark:inspector` stays read-only — the envelope reads
  `allowed_targets`/the new control fields, it does not grant new write
  targets); the new control dimensions are additive checks on the same
  `EnvelopeVerdict` shape, not a second verdict type.
- **Migration steps**: (a) expand
  `subagent_gate.check_capability_envelope(role, requested_scope) ->
  EnvelopeVerdict` (same shape as existing `SubagentVerdict`, never raises)
  to accept a control dimension — `path`, `command`, `network_domain`,
  `git_action`, `external_action`, `spend_timeout` — called from the same
  pre-dispatch funnel `subagent_gate`'s existing justification check already
  runs from; (b) wire `dispatch_wave()` to actually call
  `enforce_wave_dispatch_scopes` for the `path` dimension (currently never
  called — the concrete F1 fix; becomes `enforced` this release); (c)
  **command allowlist**: extend `subagent_profiles.ProfileSpec` with an
  `allowed_commands` field (mirrors `allowed_targets`), enforced at the same
  pre-dispatch funnel — `enforced` this release, host-independent (pure
  Python check); (d) **spend/timeout restriction**: wire a hard per-dispatch
  spend/timeout ceiling check into the same funnel, reusing `cost.py`'s
  existing budget/tier machinery as the enforcement backend — `enforced`
  this release, host-independent; (e) **network-domain / git-action /
  external-action restrictions**: no OS-level or hook-level mechanism is
  confirmed to exist on either host today (release 5's spike only prototyped
  the path dimension); this release does NOT claim mechanical enforcement of
  these three — they are recorded `advisory` (a constraints-object statement
  in the dispatch packet, no code-level block) or `unsupported` where even
  that isn't wired yet, and full enforcement is rolled to an explicitly
  named, Owner-visible follow-up (not yet a numbered release in this
  program); (f) if release 5's spike confirmed `PreToolUse` hook
  feasibility, wire it for the `path`/`command` dimensions as a second,
  pre-action enforcement moment (one source of truth, two enforcement
  moments — not three competing envelope definitions); if not, document the
  fallback per the spike's stop condition; (g) per Gap 6's fixture-split,
  author the "capability-envelope denial" behavioral-eval fixture(s) against
  this release's own denial paths, for Release 15 to wire into the full
  20-case suite.
- **Per-control status table (new deliverable — Gap 2)**: committed as part
  of this release regardless of which dimensions remain advisory/unsupported
  — either as a small `EnvelopeControlStatus` structure consumed by
  `check_capability_envelope`'s callers, or a documented table in this
  release's own record. Status vocabulary: `enforced` / `verified_after` /
  `advisory` / `unsupported`.

  | Control | Claude Code | Codex |
  |---|---|---|
  | Path/target scope | `enforced` (pre-dispatch + post-action Layer-B) | `verified_after` (post-action only; no pre-dispatch code path confirmed) |
  | Command allowlist | `enforced` | `enforced` |
  | Spend/timeout ceiling | `enforced` | `enforced` |
  | Network-domain restriction | `advisory` | `advisory` |
  | Git-action restriction | `advisory` | `advisory` |
  | External-action restriction | `unsupported` | `unsupported` |

- **Observability hook**: new hook-level (if wired) + pre-dispatch-verdict
  integration tests demonstrating pre-action and pre-dispatch denial for an
  out-of-envelope tool call/scope/command/spend; a test asserting the status
  table's claims match what the code actually does (no `enforced` claim
  without a passing denial-integration test backing it).
- **Rollback path**: revert the wiring commit; `check_capability_envelope`
  is additive so reverting drops enforcement back to today's post-action-
  only state, not a broken state.
- **Owner acceptance scenario**: Owner attempts an out-of-envelope dispatch
  (e.g. a Worker role targeting a path outside its `allowed_targets`, or
  running a disallowed command, or exceeding its spend ceiling) and sees it
  denied before or immediately after the action, with a structured
  challenge/verdict, not a silent pass; Owner also reviews the per-control
  status table and confirms which dimensions are genuinely enforced today
  vs. advisory/unsupported.

### Release 7 — REQ-30 update release (measure + PRD gate)

- **Value**: turns REQ-30's still-unmeasured overhead ceiling into a real,
  named, measured budget that names the proposal's Critical-tier gate as an
  allowed gate — the binding prerequisite the Owner's Exception check-in
  decision requires before any Critical-tier-gate or dispatch-scheduling
  work.
- **AC-ids**: REQ-30 itself (not a proposal AC — a PRD/process gate); its
  closure is required before AC-5 (Req 5 Critical tier) and AC-9 (Req 9)
  can proceed.
- **Compatibility guarantee**: #8 (REQ-30 orchestration-baseline structural
  guarantees) — this release is what makes #8 checkable with real numbers
  instead of qualitative-only assertions; the release itself must not
  increase measured overhead — it is a measurement + PRD-text release, not
  a dispatch-path change.
- **Migration steps**: (a) measure real current per-dispatch baseline
  overhead across the four representative scenarios, reusing release 1's
  captured numbers where still fresh, re-measuring where stale; (b) run
  `/renmark:prd`'s UPDATE gate to formally name the proposal's Critical-tier
  gate as one of REQ-30's allowed named gates and set a measured overhead
  budget; (c) record that every later release in this program (8-16) must
  demonstrate it stays under that budget before it ships — a checklist
  item added to this program's own verification convention, not new code.
- **Observability hook**: `.renmark/memory/orchestration-baseline.md`'s
  table gets its final, PRD-linked numbers; `PRD.md` REQ-30 gets its
  UPDATE-gate diff.
- **Rollback path**: `/renmark:prd`'s own UPDATE-gate revert path (PRD diffs
  are versioned); no production code changed.
- **Owner acceptance scenario**: Owner approves the `/renmark:prd` UPDATE
  gate diff and sees REQ-30 now names the Critical-tier gate as allowed,
  with a stated overhead budget releases 8-16 are held to.

### Release 8 — Risk-tier spike (#10b) + risk-tiered `InspectionContract` + lenses

*(Revised 2026-08-05 — peer-review Gap 3: this section originally only added
`risk_tier`/`lens` fields to `ledger.InspectionReport`, an after-the-fact
record. The proposal's actual ask is a versioned, PRE-DISPATCH
`InspectionContract` that governs what inspection SHOULD happen, distinct
from `InspectionReport`, which records what DID happen. See the new
migration step (c) below.)*

- **Value**: `ledger.InspectionReport` gains a real `risk_tier`/`lens`
  vocabulary and a deterministic (no-model-call) risk classifier; a real,
  versioned, pre-dispatch `InspectionContract` is attached to every
  meaningful work order BEFORE inspection runs — closing AC-5's
  `missing/failed` status with genuinely new capability, not a rewiring.
- **AC-ids**: **AC-5 partially advanced (Req 5)** — target-blueprint.md's
  Release E; gated on release 7 closing per the binding REQ-30 sequencing.
  This release ships the pre-dispatch `InspectionContract` and deterministic
  risk classifier; the Critical-tier mandatory Owner gate (part of Req 5's
  full ask) remains the separately-flagged EXCEPTION-CANDIDATE in
  prd-acceptance-map.md, resolved through Release 7's REQ-30 update gate,
  not claimed complete here.
- **Compatibility guarantee**: #5 (`ledger.VERDICTS = ("pass", "fail",
  "escalate")` stays the only ledger-legal `InspectionReport.verdict`
  vocabulary — `risk_tier`/`lens`/the new contract-reference field are
  additive fields, never a second verdict enum).
- **Migration steps (spike, then build)**: (a) bounded spike (1 session,
  no production wiring): design and hand-validate a deterministic risk-tier
  classifier (file scope, target module, wave size) against 15-20 real past
  dispatches from `.renmark/analytics/task-runs.jsonl`/ledger history,
  documented disagreement rate against a human-assigned tier; stop
  condition: Owner-acceptable disagreement rate, or one re-spike if criteria
  are redefined; (b) add the real `RiskTier` enum (Release 3 left this as an
  untyped `str | None` placeholder on `WorkOrder`; this release defines the
  enum and migrates that field's type — additive-compatible, existing
  placeholder string values remain valid enum-value strings) + `lens:
  str | None` as additive fields to `ledger.InspectionReport`; (c) **NEW —
  build the actual `InspectionContract`**: a versioned, PRE-DISPATCH object
  (`risk_tier`, `lenses: list[LensName]`, `deterministic_gates: list[str]`,
  `semantic_rubric_ref: str | None`, `independent_judge_required: bool`,
  `evidence_required: list[str]`, `allowed_verdicts: tuple[str, ...]`)
  attached to the Release-3-reconciled `WorkOrder` (a new
  `inspection_contract: InspectionContract | None` field, populated by
  `work_order_for_task` via `resolve_lens_for`) BEFORE inspection runs.
  `InspectionContract` = the pre-dispatch plan for what inspection SHOULD
  happen; `InspectionReport` (already existing) = the post-dispatch record
  of what DID happen. `InspectionReport` gains a `contract_ref` (contract
  id + version) field so every report cites which contract version it was
  graded against; (d) add `resolve_lens_for(work_order) -> LensName` policy
  function in the `subagent_profiles.py`/`subagent_gate.py` orbit (mirrors
  `cost.py`'s policy-not-mechanism role; explicitly NOT the same function as
  `cost.requires_escalation`, which stays scoped to model-tier routing), now
  also responsible for constructing the `InspectionContract` given the
  classified risk tier; (e) per Gap 6's fixture-split, author the
  "risk-tier/lens selection" behavioral-eval fixture(s) against this
  release's classifier and contract, for Release 15 to wire in.
- **Observability hook**: the classifier's disagreement-rate table, kept as
  a committed artifact for future recalibration; a new test proving an
  `InspectionReport` cites the `InspectionContract` version/ref it was
  graded against, and that the contract is attached before dispatch (not
  synthesized after the fact).
- **Rollback path**: revert the commit; `InspectionReport`'s existing
  `verdict` vocabulary and callers are unaffected (additive fields only).
- **Owner acceptance scenario**: Owner reviews a sample Medium/High-risk
  dispatch and sees BOTH the pre-dispatch `InspectionContract` (attached to
  its `WorkOrder`, naming required lenses/gates/judge requirement before the
  work ran) and the post-dispatch `InspectionReport` citing that exact
  contract version, with the classifier's disagreement-rate evidence
  available on request.

### Release 9 — Calibrated blind LLM-judge (3-state + bias controls)

- **Value**: `judge.py`'s `Outcome` becomes a real 3-state
  (`pass|fail|uncertain`) vocabulary instead of collapsing every parse
  failure into a `fail`-as-uncertain-proxy; the judge gains input isolation
  (redacting Worker self-assessment/confidence/identity before prompt
  composition) and pairwise order-randomization.
- **AC-ids**: AC-6 (Req 6) — target-blueprint.md's Release E; gated on
  release 7.
- **Compatibility guarantee**: #5 (judge `Outcome` stays a SEPARATE enum
  from `ledger.VERDICTS` — never unified; a judge verdict attaches to
  `InspectionReport` only as an optional `judge_evidence` reference, never
  overriding `InspectionReport.verdict`, per target-blueprint.md §3.5's
  explicit non-goal enforcement); #9 (Inspector role stays read-only,
  reference-only access to judge evidence).
- **Migration steps**: (a) breaking, compile-time-visible change:
  `Outcome = Literal["pass", "fail", "uncertain"]`; every caller
  pattern-matching on `Outcome` must add the third arm (deliberately not a
  silent additive default, per target-blueprint.md §2.2's reasoning); (b)
  `compose_judge_prompt` gains a redaction step at data-assembly time,
  before string composition (not a rendered-prompt filter); (c) pairwise/
  comparison calls gain order-randomization, recorded per call; (d) add
  `InspectionReport.judge_evidence: JudgeEvidenceRef | None` — attachment,
  not a merge; `judge.py` and `ledger.py` keep their current module
  boundary; (e) per Gap 6's fixture-split (2026-08-05), author the "judge
  input-isolation / 3-state outcome" behavioral-eval fixture(s) against
  this release's redaction and `Outcome` change, for Release 15 to wire in.
- **Observability hook**: new judge unit tests for input-isolation,
  independence-recording, and order-randomization; existing eval-tier
  (`renmark-execute --behavior --judge`) usage of the same module gets the
  3-state vocabulary for free since it is the same code path.
- **Rollback path**: revert the commit; this is the one Replace-classified
  item in this release, so rollback restores the 2-state `Outcome` and any
  caller relying on the third arm reverts with it (release notes flag any
  such caller explicitly).
- **Owner acceptance scenario**: Owner triggers a judge call with an
  intentionally ambiguous input and sees `uncertain` returned honestly
  instead of a `fail`-proxy; Owner confirms the judge verdict is recorded
  as `InspectionReport.judge_evidence`, never as `InspectionReport.verdict`
  itself.

### Release 10 — Failure-derived constraint registry

*(Revised 2026-08-05 — peer-review Gap 4: this section wrongly conflated the
registry with `recurrence.py`'s existing `durable_guard` entries, despite
prd-acceptance-map.md explicitly flagging Req 7 and REQ-24 as distinct
concepts. See the ADR requirement and the real `FailureRule` structure
below.)*

- **Value**: a genuinely new `FailureRule` registry structure — distinct
  from, but able to consume, `recurrence.py`'s existing `durable_guard`
  entries as one input signal — becomes real, consulted constraints at
  dispatch time, closing AC-7's `missing` status.
- **AC-ids**: AC-7 (Req 7) — target-blueprint.md's Release E; gated on
  release 7. prd-acceptance-map.md's Part B (REQ-24 row) and its DEFERRABLE
  spec debt section state Req 7 and REQ-24/`recurrence.py` are "distinct...
  do not conflate" and require "an explicit ADR before Release E" — this
  release is that Release E deliverable.
- **Compatibility guarantee**: #7 (constraint text still only reaches a
  subagent through the existing `dispatch.build_subagent_input` funnel —
  rule consumption is consulted by `subagent_gate.py`'s pre-dispatch check,
  which decides pass/challenge/block; it does not itself compose prompt
  text — no second prompt-composition pathway).
- **Migration steps**: (a) **NEW, precondition for (b)-(d)**: write the ADR
  distinguishing Req 7 (a curated, versioned, cross-run failure-derived
  constraint registry) from REQ-24/`recurrence.py` (a per-run/fingerprint-
  scoped recurrence-prevention mechanism that stops a 3rd equivalent
  attempt) — commit under `.renmark/memory/decisions.md` (or equivalent),
  referenced by this release's design; (b) add a genuinely new `FailureRule`
  structure **inside `recurrence.py`** (no new top-level module — honors
  the roadmap's non-goals section and modularity-assessment §6's preference
  to extend `recurrence.py` rather than create a sibling module) with
  fields: `rule_id`, `status` (`proposed`/`active`/`deprecated`), `trigger`,
  `applicability`, `required_behavior`, `prohibited_failure`,
  `source_evidence`, `enforcement` (`prompt`/`validator`/
  `capability_policy`), `regression_test_ref`, `created_at`,
  `last_triggered_at`, `review_after` — a distinct structure from
  `DurableGuard`/`durable_guard`, not a wrapper over it; (c)
  `recurrence.py`'s existing `durable_guard` entries become ONE input signal
  that can seed a `FailureRule`'s `source_evidence` (a durable guard
  observed 3+ times is a legitimate trigger for proposing a rule) — never
  treated as the registry itself; (d) add dedup/contradiction detection over
  `FailureRule` entries (colliding `rule_id`/`trigger`, or two `active`
  rules with conflicting `required_behavior`/`prohibited_failure` for
  overlapping `applicability`) and a `review_after`-driven review mechanism
  (a rule past its `review_after` date surfaces in `/renmark:hygiene`'s
  existing pruning sweep, reusing release 12's extension point); (e)
  `subagent_gate.py` consumes ONLY `status: active` rules from the same
  pre-dispatch funnel release 6 added `check_capability_envelope` to,
  matched against the dispatch's `applicability` and populated into
  `WorkOrder.constraints` (release 3's placeholder field); (f) per Gap 6's
  fixture-split, author the "failure-rule injection" behavioral-eval
  fixture(s) against this release's `FailureRule` consumption, for
  Release 15 to wire in.
- **Observability hook**: dedup/contradiction-detection test cases; a
  lifecycle test (`proposed`→`active`→`deprecated`); a test proving rule
  consumption reads only `FailureRule.status == "active"` entries; a
  separate test proving a bare `durable_guard` entry with no promoted
  `FailureRule` is NOT treated as an active constraint.
- **Rollback path**: revert the commit; `recurrence.py`'s existing
  fingerprinting/REQ-24 behavior is untouched — the new `FailureRule`
  structure is additive.
- **Owner acceptance scenario**: Owner reviews the ADR distinguishing Req 7
  from REQ-24, then triggers a dispatch matching an `active` `FailureRule`
  and sees `subagent_gate` cite the specific `rule_id` in its verdict — not
  a bare `durable_guard` entry.

### Release 11 — Routing-overlap spike (#18) + policy-aware dispatch scheduling

- **Value**: resolves whether `global_routing.py` and `codex_routing.py`
  duplicate logic, then extends `dispatch_wave`'s scheduling with risk-tier,
  quota, and rework-budget-aware signals — closing AC-9's `partial` status.
- **AC-ids**: AC-9 (Req 9) — **gated**, does not start implementation until
  release 7 closes, per the binding Exception check-in decision ("No
  dispatch-scheduling (Req 9) ... work may land before this release
  closes").
- **Compatibility guarantee**: #1 (`pytest -q` count); #8 (REQ-30's measured
  overhead budget from release 7 — this release must demonstrate it stays
  under that budget before it ships, per release 7's own requirement).
- **Migration steps (spike, then build)**: (a) bounded spike (1 read-and-
  diff pass, no code change): read both `global_routing.py` and
  `codex_routing.py` fully, produce a one-page finding — "no overlap,
  boundary is X" or "overlap found at Y, recommend merging into Z"; if
  merge is recommended, that becomes its own scoped item, not decided in
  this spike; (b) extend `dispatch_wave`/`group_tasks_by_wave` with the
  risk tier from release 8, quota/provider-availability signals, a
  configurable max-parallelism knob, and rework-budget-aware scheduling
  (R-0.2 rework caps exist but nothing consults them at schedule time
  today).
- **Observability hook**: new dispatch-planner unit tests; a before/after
  overhead measurement against release 7's budget, recorded alongside the
  release.
- **Rollback path**: revert the scheduling-extension commit; wave grouping
  reverts to today's overlap-safety-only behavior.
- **Owner acceptance scenario**: Owner reviews the routing-overlap finding
  and a sample wave-schedule decision showing risk-tier/quota signals
  factored in, with a measured overhead delta under release 7's budget.

### Release 12 — Context/memory governance extension + state-fragmentation spike (#22)

- **Value**: `memory.py`/`hygiene.py`'s pruning criteria extend toward the
  proposal's 7-way category split (stable preferences / canonical artifacts
  / lifecycle state / bounded task context / failure-rule registry /
  receipts / ephemeral conversation); resolves whether `program.json`/
  `delivery.json` genuinely supersede the documented `pipeline.json` name.
- **AC-ids**: AC-10 (Req 10) — target-blueprint.md's Release G portion not
  gated by REQ-30 (context/memory work is independent of dispatch-
  scheduling/Critical-tier gating).
- **Compatibility guarantee**: #7 (`context.py`'s taxonomy/`
  assert_metadata_only` stays unchanged — Keep item, not touched by this
  release).
- **Migration steps**: (a) bounded spike (1 read-and-diff pass): confirm
  the current authoritative state-file set vs. `CLAUDE.md`'s documented
  set; update `CLAUDE.md` if the doc is stale, flag anything requiring a
  code change as its own future item; (b) extend `hygiene.py`'s pruning
  criteria toward the 7-way category split, reusing checkpoint-before-
  compaction (already real, Keep item) and, once release 10 lands, folding
  a periodic re-verification sweep for constraint-registry entries into
  `/renmark:hygiene` per Tier-3 Recommendation 5.
- **Observability hook**: `renmark:hygiene`'s dry-run output showing the
  new pruning categories; the doc-fix (if any) committed alongside.
- **Rollback path**: revert the pruning-criteria commit; `hygiene.py`'s
  existing `validate_registry_compliance` behavior is unaffected.
- **Owner acceptance scenario**: Owner runs `/renmark:hygiene` (dry-run)
  and sees pruning candidates classified against the 7-way category split
  instead of the current loose two-bucket split.

### Release 13 — Durable-events field completeness + orphan-detection spike (#24) + analytics reconciliation

*(Revised 2026-08-05 — peer-review Gap 5: this section originally left
benchmark-surfaced gaps as "an unspecified future item," meaning AC-11 could
stay open indefinitely. See the new bounded, committed implementation step
(a2) below.)*

- **Value**: `ledger.py`'s 4 event kinds gain finer-grained lifecycle
  fields (`schema_version`, `attempt_id`/`correlation_id`); self-benchmarks
  resume/recovery correctness against deliberately-interrupted runs and
  commits to fixing what it finds, bounded; reconciles `analytics.py` as a
  read-only consumer of `ledger.py` instead of a second parallel "durable
  record" system.
- **AC-ids**: AC-11 (Req 11) — target-blueprint.md's Release G portion;
  gated only on release 3 (needs the reconciled `WorkOrder` schema, including
  its `correlation_id`/`idempotency_key` placeholders, as the field-addition
  target). This release now owns a real path to AC-11 closure, not an
  indefinite benchmark-only deferral.
- **Compatibility guarantee**: #1 (`pytest -q` count); #8 (the JSONL
  append-only mechanism itself is a Keep item — no database/broker
  introduced, per modularity-assessment §9's explicit rejection).
- **Migration steps**: (a) bounded spike (1 session, no new production
  orphan-detection code yet): self-benchmark renmark's own resume/recovery
  correctness against a handful of deliberately-interrupted real or
  simulated runs, reusing `heartbeat.py`'s existing usage-limit-pause path
  as the test harness; produce a scenario table (pass/fail on "no
  duplicate, no orphan"); (a2) **NEW — bounded, committed implementation
  step**: any orphan-detection or duplicate-integration gap the benchmark
  surfaces gets fixed inside this same release, budget-capped at 2 sessions
  total across all surfaced gaps. A gap whose fix would exceed that 2-session
  budget is NOT silently left open — it is escalated to the Owner as its own
  scoped follow-up release proposal, with the scenario-table evidence
  attached, rather than an indefinite deferral. AC-11 is marked closed in
  this release's completion record only once either (i) no gaps were found,
  (ii) all found gaps were fixed within budget, or (iii) remaining gaps are
  Owner-acknowledged as an explicit, evidence-backed follow-up; (b) add
  `schema_version` and `attempt_id`/`correlation_id` fields to the 4
  existing ledger event kinds (additive; `correlation_id` also ties back to
  release 3's placeholder `WorkOrder.correlation_id` field); (c)
  `analytics.py` reads from `ledger.py` as its reconciled source for
  guardrail metrics (release 14) instead of maintaining a second parallel
  event system; (d) per Gap 6's fixture-split, author the "retry/rework
  survives resume" behavioral-eval fixture(s) against this release's
  interrupt/resume evidence, for Release 15 to wire in.
- **Observability hook**: the interrupt-and-resume scenario table, kept
  committed as regression evidence; `analytics.py`'s reconciled read path;
  whatever fix(es) landed under (a2) get their own regression test named
  after the specific interrupted-run scenario they close.
- **Rollback path**: revert the field-addition/reconciliation commit;
  existing `_setup_resume_state`/`_cross_check_skip_list` behavior at the
  plan-task level is untouched; each bounded fix under (a2) gets its own
  revert path noted at commit time.
- **Owner acceptance scenario**: Owner reviews the interrupt-and-resume
  scenario table and confirms found gaps were either fixed-and-tested in
  this release or explicitly escalated with evidence — never silently
  absent from the scenario table's conclusion.

### Release 14 — Guardrail metrics

- **Value**: `analytics.py`'s aggregators gain the proposal's specific
  guardrail fields — false-pass/reopen rate, scope-violation rate,
  Owner-interruptions-per-milestone, percentage-of-dispatches-with-unknown-
  usage, duplicate-artifact rate — closing AC-13's `partial` status.
- **AC-ids**: AC-13 (Req 13) — target-blueprint.md's Release H; the
  scope-violation-rate metric specifically requires release 6 (production
  scope-enforcement wiring) to already be live, and reads from release 13's
  reconciled `analytics.py`↔`ledger.py` source.
- **Compatibility guarantee**: #1 (`pytest -q` count, additive aggregator
  fields only).
- **Migration steps**: extend `_agg_features`/`_agg_tasks`/`_agg_loops`/
  `_agg_events`/`_agg_usage`/`build_health_report` with the named guardrail
  fields, reusing the existing JSONL/analytics paths per the proposal's own
  stated preference; define and measure renmark's own baseline for each
  metric rather than importing an external vendor statistic (explicitly:
  do NOT import the proposal's cited "43%" figure as a target/baseline).
- **Observability hook**: `/renmark:analytics` output gains the new
  guardrail fields, visible in the existing command.
- **Rollback path**: revert the aggregator-extension commit; existing
  `build_health_report` fields are unaffected (additive only).
- **Owner acceptance scenario**: Owner runs `/renmark:analytics` and sees
  the new guardrail metrics (scope-violation rate, false-pass rate, etc.)
  reported with renmark's own measured baseline, not a borrowed target.

### Release 15 — Remaining behavioral eval fixtures + full 20-case suite wiring (CI-gating)

*(Revised 2026-08-05 — peer-review Gap 6: authoring all 20 fixtures in one
end-of-program release meant most of the behavior they test had already
shipped, unverified, releases earlier. Fixtures now split across the release
that builds the capability they exercise, authored alongside that release;
Release 15's scope shrinks accordingly. See the split table below.)*

- **Value**: authors any REMAINING behavioral-eval fixtures not naturally
  tied to an earlier release, wires the full 20-case suite together against
  the ALREADY-EXISTING tiered-eval mechanism (`renmark/behavior.py`,
  CLAUDE.md's P8 tier), and makes the deterministic tier CI-gating — fixture
  authorship + suite wiring, not new infrastructure.
- **AC-ids**: AC-8 (Req 8) — target-blueprint.md's Release F; depends on
  releases 1, 4, 6, 8, 9, 10, 13 having each already authored their own
  tied fixtures per the split below.
- **Compatibility guarantee**: #1 (deterministic tier stays CI-safe, no
  model call, no network, no token spend by default — fixture authorship
  does not change that contract; making it CI-gating enforces the contract
  more strictly, it does not relax it).
- **Fixture split (Gap 6)**: each fixture that exercises a capability from a
  specific earlier release is authored ALONGSIDE that release, not held
  until Release 15:

  | Fixture group | Authored in |
  |---|---|
  | Fast-path accept/reject | Release 1 |
  | Task-tracker transitions | Release 4 |
  | Capability-envelope denial | Release 6 |
  | Risk-tier/lens selection | Release 8 |
  | Judge input-isolation / 3-state outcome | Release 9 |
  | Failure-rule injection | Release 10 |
  | Retry/rework survives resume | Release 13 |
  | Remaining (e.g. worker replan-refusal, inspector-can't-repair, judge-can't-override-deterministic-fail) | Release 15 |

- **Migration steps**: (a) author any fixtures not claimed by an earlier
  release per the split table above, against `renmark/behavior.py`'s
  existing deterministic/eval-tier split; (b) wire the full 20-case suite
  together (fixtures authored here plus those authored in releases 1, 4, 6,
  8, 9, 10, 13); (c) make the deterministic tier CI-gating — a hard
  requirement, not merely "green": CI must fail on a deterministic-tier
  fixture regression; the eval tier remains opt-in via
  `RENMARK_EVAL_RUNNER_CMD` for the live-judge proof, unchanged.
- **Observability hook**: `renmark-execute --behavior` output showing all
  20 cases present and green on the deterministic tier, PLUS the
  deterministic tier wired into CI as a blocking check.
- **Rollback path**: revert the fixture-authoring/CI-wiring commit; no
  runtime behavior change either way (fixtures are test data; CI-gating
  reverts to advisory-only).
- **Owner acceptance scenario**: Owner runs `renmark-execute --behavior`
  and sees all 20 named cases present and green, and confirms CI fails when
  a deterministic-tier fixture regresses.

### Release 16 — `/renmark:rethink` self-upgrade (last, per Discovery Direction Gate)

- **Value**: closes REQ-28's remaining gaps against proposal Req 12 —
  "apply only relevant falsification lenses" (now possible, release 8
  exists) and "challenge the roadmap with an independent Inspector before
  asking for Owner approval" (a genuine PRD wording gap today).
- **AC-ids**: AC-12 (Req 12) — sequenced explicitly LAST because it needs
  the assurance contracts it consumes (work order, inspection contract,
  receipts, lenses, judge, constraint registry) to actually exist first —
  this very Stage 8 run is live evidence of REQ-28's current capability,
  run without any of releases 3-10 yet existing.
- **Compatibility guarantee**: #1 (`pytest -q` count); no other baseline
  check is touched — this release changes `/renmark:rethink`'s own pipeline
  text/gates, not `dispatch.py`/`ledger.py`/`fast_path.py` internals.
- **Migration steps**: (a) close the AC-12/item-8 BLOCKING PRD debt via
  `/renmark:prd`'s UPDATE gate — add a mandatory pre-Execution-Gate
  independent-Inspector challenge step to REQ-28, distinct from the 3
  existing Owner gates; (b) wire rethink's own dispatches through the
  reconciled `RenmarkWorkOrder` (release 3) so rethink's own Stage 6/7
  classification/blueprint work is itself governed by the same contracts
  it recommends for the rest of the codebase; (c) apply lens selection
  (release 8) to rethink's own Stage 5 modularity work where relevant.
- **Observability hook**: a new rethink-pipeline test proving the
  Inspector-challenge-before-Execution-Gate step actually runs (not just
  documented).
- **Rollback path**: revert the PRD-text + pipeline-wiring commit; the
  3-gate structure (Discovery Direction / Solution / Execution) remains
  available as a fallback.
- **Owner acceptance scenario**: Owner runs the next `/renmark:rethink`
  invocation and sees an independent-Inspector challenge step execute
  before the Execution Gate's Owner-approval prompt, not just the 3
  existing gates.

---

## Non-goals reaffirmed (carried from target-blueprint.md §5)

No release above introduces a new top-level package, a fourth work-order
shape, a new event-log store, a competing prompt-composition pathway, or a
second fast path. Old and new components coexist deliberately where the
blueprint calls for it — e.g. `dispatch.SubagentInput` stays a documented
projection of `ledger.WorkOrder` (release 3) rather than being deleted;
`judge.py` stays a separate leaf module from `ledger.InspectionReport`
(release 9) rather than being merged.

## Explicitly excluded from this roadmap

None of classification.md's 28 entries were dropped — all Keep items (4, 5,
13, 16, 19, 20, 23a) are carried forward unchanged and require no release;
all 2 Replace items (3, 11b) and all 14 Improve items (1, 2, 6, 8, 9, 10a,
11a, 12, 14, 15, 17, 21, 23b, 25, 26, 27) and all 7 Unknown-spike items (7,
10b, 18, 22, 24, 28 — plus item 24's Component-B question folded into
release 13) are placed in exactly one release above.

## Next step

Stage 9 (Execution Gate) presents this 16-release sequence for one explicit
`AskUserQuestion` approval before any target production code changes begin —
approving *execution*, not re-litigating the Discovery Direction Gate or
Solution Gate decisions already made. Per the Program state note above,
Stage 9 must also resolve the stale prior `renmark-architecture-rethink-
roadmap` program state before materializing this roadmap via
`write_program`.

---

## Stale-state reconciliation note (2026-08-04)

`.renmark/state/program.json` still holds the PRIOR `renmark-architecture`
rethink's program (`feature: renmark-architecture-rethink-roadmap`,
`source_sha: c674185...`), and its Release 1 task
`r1-req30-baseline-measurement` is still `status: pending` even though
CHANGELOG.md records all 7 of that transformation's releases as shipped.
This corroborates (does not conflict with) this run's own stage 2 finding
that REQ-30's baseline overhead number remains genuinely unmeasured.

**Resolution for Stage 9:** this leftover task is absorbed into THIS
roadmap's Release 7 (REQ-30 update release) rather than treated as a new
ask — Release 7 already requires measuring the real baseline overhead. The
old `program.json` must be archived (not silently overwritten) before the
new `Program` for this transformation is materialized, so the prior
transformation's completion record isn't lost.

---

## Execution Gate — decision (2026-08-04)

**Approved.** Owner approved execution via AskUserQuestion, beginning with
Release 1. Direction (Discovery Direction Gate) and classification/blueprint
(Solution Gate) were already approved separately — this gate approved
starting real production changes. Rethink's responsibility ends here;
execution proceeds through renmark's existing Agency/milestone machinery
starting with Release 1 (baseline and compatibility coverage) via
`/renmark:orchestrate` or `/renmark:feature`, after the stale
`renmark-architecture-rethink-roadmap` program is archived (not overwritten)
and this transformation's Program is materialized.

---
artifact_type: program
schema_version: 1
created_at: 2026-08-05T00:38:23+00:00
source_sha: e6898917ddf3a30505bb01b1b0569c28a187d792
---

# Program — governed-orchestration-assurance

_mode: staged · Stage 5/16 · task 0/1 done · current: Release 5: PreToolUse capability-envelope spike (#7)_

## ◑ Release 1: Baseline and compatibility coverage — serves REQ-30
_phases: plan → build → verify → review → release_

- [x] Turn baseline.md's 9 compatibility checks into runnable tests — Add test-only coverage for the 9 baseline.md checks (pytest count, classify_fast_path, verify_worker_scope, check_dispatch_independence, VERDICTS vocab, complete_worker_task no-self-approval, assert_metadata_only, REQ-30 qualitative guarantees, inspector read-only allowlist). No production code moves. Verify: fresh pytest -q + renmark-execute --behavior.
- [ ] Record real token/wall-clock/dispatch-count numbers for the 4 representative scenarios — Run and record Start/Feature-Fix/Orchestrate/Rethink scenarios into orchestration-baseline.md's unpopulated table, replacing 'not yet measured'. Requires its own cost-preview + Owner go-ahead per that file's flag.

## ● Release 2: Role-model altitude ADR (spike #28) — serves REQ-1, REQ-2, REQ-12
_phases: plan → build → verify → review → release_

- [x] Bounded 1-session spike: confirm capability-envelope enforcement altitude — Produce one ADR paragraph confirming per-dispatch-role altitude (subagent_profiles.py) vs project-phase altitude (agency.py) for release 6's capability envelope. Owner/maintainer sign-off required. Stop condition: ADR accepted, no code change unless contradicted.

## ● Release 3: Canonical work-order reconciliation — serves AC-1 (REQ-1)
_phases: plan → build → verify → review → release_

- [x] Add risk_tier (untyped placeholder), capability_envelope_ref, lens, schema_version, and full RenmarkWorkOrder contract fields to ledger.WorkOrder — Additive fields only, pytest -q count stays green except for new additions. risk_tier is str|None (design decision, Gap 1): Release 8 defines the real RiskTier enum per modularity-assessment.md sec6's module-boundary lean. Also adds correlation_id, idempotency_key, dependencies, scope, budget, routing, constraints, interaction_policy as additive placeholders (enforcement deferred per field table in roadmap.md).
- [x] Add ledger.work_order_for_task(task, role, ...) -> WorkOrder and call it from dispatch.build_subagent_input — One funnel all 6 dispatch call sites already use; SubagentInput public field names stay stable (REQ-20 metadata-only).
- [x] Rename RepairWorkOrder.work_order_id to order_id, require it resolves to a real WorkOrder — Keep severity/source_inspection_id/description/acceptance_criteria unchanged.
- [x] Add wiring test asserting all 6 dispatch call sites produce a WorkOrder via the shared funnel — Fast-path, feature, debug, orchestrate, rethink, resume — no bespoke path.
- [x] Add schema test asserting every RenmarkWorkOrder contract field is present with the stated default/optional type — Covers the field-added-now vs enforcement-deferred table in roadmap.md's revised Release 3 section.

## ● Release 4: Task tracker bound to WorkOrder.order_id + selector bypass guard — serves AC-3, AC-4 (REQ-3, REQ-4)
_phases: plan → build → verify → review → release_

- [x] Bind task_tracking.create_or_reuse_task to the originating WorkOrder.order_id — Uses release 3's funnel.
- [x] Add interaction.py enforced mode rejecting numbered fallback when a native picker is available — Same ChoiceSet/fallback dataclasses, no new module; reads hosts.capabilities_for.
- [x] Deferred cosmetic 'concise displayed list' format for Role/worker+model/Budget/Verification — Per prd-acceptance-map's own deferral note.
- [x] Add regression test named after the 2026-06-14 'Hand-off picker not re-rendered' incident — Proves the enforced-mode guard catches that exact failure mode.

## ○ Release 5: PreToolUse capability-envelope spike (#7) — serves AC-2 (REQ-2) **(current)**
_phases: plan → build → verify → review → release_

- [ ] Bounded 1-session spike: prototype PreToolUse hook for metadata-driven allow/deny — Read Claude Code's PreToolUse hook contract; prototype one hook wired to one agent profile's allowed_targets; confirm Codex's own enforcement mechanism. Evidence: one working hook config + one passing/one blocking integration test. Stop condition: feasible -> proceed to release 6 as specified; not feasible -> release 6 falls back to post-action-only, documented, escalated to Owner.

## ○ Release 6: Capability-envelope enforcement wiring — serves AC-2 (REQ-2)
_phases: plan → build → verify → review → release_

- [ ] Expand subagent_gate.check_capability_envelope(role, requested_scope) -> EnvelopeVerdict to cover path/command/network_domain/git_action/external_action/spend_timeout dimensions — Same shape as existing SubagentVerdict, never raises; called from the same pre-dispatch funnel subagent_gate's justification check already runs from.
- [ ] Wire dispatch_wave() to actually call enforce_wave_dispatch_scopes (path dimension) — Currently never called in production — closes F1. Becomes 'enforced' status this release.
- [ ] Add subagent_profiles.ProfileSpec.allowed_commands, enforced at the pre-dispatch funnel — Mirrors allowed_targets; host-independent Python check, 'enforced' this release (Gap 2).
- [ ] Wire a hard per-dispatch spend/timeout ceiling check into the pre-dispatch funnel, reusing cost.py — Host-independent, 'enforced' this release (Gap 2).
- [ ] Add EnvelopeControlStatus structure/table: per-control per-host status (enforced/verified_after/advisory/unsupported) — Gap 2 honesty requirement — network-domain, git-action, external-action restrictions recorded advisory/unsupported this release, not claimed enforced; full enforcement rolled to a named follow-up.
- [ ] If release 5's spike confirmed feasibility, wire the PreToolUse hook to path/command dimensions — One source of truth, two enforcement moments; if not feasible, document the fallback and escalate per the spike's stop condition.
- [ ] Author 'capability-envelope denial' behavioral-eval fixture(s) (Gap 6 fixture-split) — For Release 15 to wire into the full 20-case suite.

## ○ Release 7: REQ-30 update release (measure + PRD gate) — serves REQ-30
_phases: plan → build → verify → review → release_

- [ ] Measure real current per-dispatch baseline overhead across the 4 representative scenarios — Reuse release 1's captured numbers where still fresh, re-measure where stale.
- [ ] Run /renmark:prd's UPDATE gate to name the Critical-tier gate as a REQ-30 allowed gate + set a measured overhead budget — Releases 8-16 must demonstrate they stay under this budget before shipping.
- [ ] Absorbed: close the renmark-architecture rethink's lingering r1-req30-baseline-measurement task — Carried over from the prior, closed renmark-architecture-rethink-roadmap program (archived at .renmark/rethink/renmark-architecture/archive/closed-program-final-2026-08-04.json), whose Release 1 task r1-req30-baseline-measurement was never marked done. This release's own baseline-overhead measurement (r7-measure-baseline-overhead) satisfies it; not treated as a new ask.

## ○ Release 8: Risk-tier spike (#10b) + risk-tiered InspectionContract + lenses — serves AC-5 (REQ-5)
_phases: plan → build → verify → review → release_

- [ ] Bounded 1-session spike: hand-validate a deterministic risk-tier classifier against 15-20 real past dispatches — Design and validate against .renmark/analytics/task-runs.jsonl / ledger history; document disagreement rate against a human-assigned tier. Stop condition: Owner-acceptable disagreement rate, or one re-spike if criteria redefined.
- [ ] Define the real RiskTier enum; migrate WorkOrder.risk_tier from Release 3's str|None placeholder to the typed enum — Additive-compatible type narrowing, not a rename. Add lens: str|None to InspectionReport. VERDICTS stays the only ledger-legal verdict vocabulary.
- [ ] Build InspectionContract: versioned, pre-dispatch object (risk_tier, lenses, deterministic_gates, semantic_rubric_ref, independent_judge_required, evidence_required, allowed_verdicts) attached to WorkOrder before inspection runs — Gap 3 fix — distinct from InspectionReport (post-dispatch record). InspectionReport gains contract_ref so every report cites the contract version it was graded against.
- [ ] Add resolve_lens_for(work_order) -> LensName policy function; also constructs the InspectionContract — In the subagent_profiles.py/subagent_gate.py orbit; explicitly not cost.requires_escalation.
- [ ] Author 'risk-tier/lens selection' behavioral-eval fixture(s) (Gap 6 fixture-split) — For Release 15 to wire into the full 20-case suite.

## ○ Release 9: Calibrated blind LLM-judge (3-state + bias controls) — serves AC-6 (REQ-6)
_phases: plan → build → verify → review → release_

- [ ] Change judge.py's Outcome to Literal['pass','fail','uncertain'] — Breaking, compile-time-visible; every caller pattern-matching on Outcome must add the third arm.
- [ ] Add a redaction step to compose_judge_prompt before string composition — Redacts Worker self-assessment/confidence/identity at data-assembly time.
- [ ] Add order-randomization to pairwise/comparison calls, recorded per call
- [ ] Add InspectionReport.judge_evidence: JudgeEvidenceRef | None — Attachment, not a merge; never overrides InspectionReport.verdict.

## ○ Release 10: Failure-derived constraint registry — serves AC-7 (REQ-7)
_phases: plan → build → verify → review → release_

- [ ] Write the ADR distinguishing Req 7 (curated cross-run failure-rule registry) from REQ-24 (recurrence.py's per-run/fingerprint role) — precondition for the rest of this release — Flagged as needed 'before Release E' by prd-acceptance-map.md (Gap 4).
- [ ] Add a genuinely new FailureRule structure inside recurrence.py (rule_id, status, trigger, applicability, required_behavior, prohibited_failure, source_evidence, enforcement, regression_test_ref, created_at, last_triggered_at, review_after) — No new top-level module. Distinct from DurableGuard/durable_guard, not a wrapper over it (Gap 4).
- [ ] Wire recurrence.py's existing durable_guard entries as ONE input signal that can seed a FailureRule's source_evidence — Never treated as the registry itself.
- [ ] Add dedup/contradiction detection over FailureRule entries and a review_after-driven review mechanism via /renmark:hygiene — Lifecycle: proposed -> active -> deprecated. Reuses release 12's hygiene extension point.
- [ ] Wire subagent_gate.py to consume only status:active FailureRule entries from the pre-dispatch funnel, populating WorkOrder.constraints — Same funnel release 6 added check_capability_envelope to; consumes release 3's WorkOrder.constraints placeholder field.
- [ ] Author 'failure-rule injection' behavioral-eval fixture(s) (Gap 6 fixture-split) — For Release 15 to wire into the full 20-case suite.

## ○ Release 11: Routing-overlap spike (#18) + policy-aware dispatch scheduling — serves AC-9 (REQ-9)
_phases: plan → build → verify → review → release_

- [ ] Bounded 1-pass spike: read global_routing.py and codex_routing.py fully, produce a one-page overlap finding — 'No overlap, boundary is X' or 'overlap found at Y, recommend merging into Z'; a recommended merge becomes its own scoped item, not decided here.
- [ ] Extend dispatch_wave/group_tasks_by_wave with risk-tier, quota/provider-availability, max-parallelism, and rework-budget-aware scheduling — Must demonstrate it stays under release 7's measured overhead budget before shipping.

## ○ Release 12: Context/memory governance extension + state-fragmentation spike (#22) — serves AC-10 (REQ-10)
_phases: plan → build → verify → review → release_

- [ ] Bounded 1-pass spike: confirm the current authoritative state-file set vs. CLAUDE.md's documented set — Update CLAUDE.md if stale; flag anything requiring a code change as its own future item.
- [ ] Extend hygiene.py's pruning criteria toward the proposal's 7-way category split — Stable preferences / canonical artifacts / lifecycle state / bounded task context / failure-rule registry / receipts / ephemeral conversation. Reuses checkpoint-before-compaction; once release 10 lands, fold a periodic constraint-registry re-verification sweep into /renmark:hygiene per Tier-3 Recommendation 5.

## ○ Release 13: Durable-events field completeness + orphan-detection spike (#24) + analytics reconciliation — serves AC-11 (REQ-11)
_phases: plan → build → verify → review → release_

- [ ] Bounded 1-session spike: self-benchmark resume/recovery correctness against deliberately-interrupted runs — Reuse heartbeat.py's usage-limit-pause path as the test harness; produce a scenario table (pass/fail on no-duplicate/no-orphan).
- [ ] Fix any orphan-detection/duplicate-integration gap the benchmark surfaces, bounded to 2 sessions total; escalate anything over budget as a scoped Owner follow-up — Gap 5 fix — AC-11 closes only once gaps are fixed-in-budget or explicitly Owner-acknowledged as a follow-up; no indefinite deferral.
- [ ] Add schema_version and attempt_id/correlation_id fields to the 4 existing ledger event kinds — Additive only; correlation_id ties back to Release 3's WorkOrder.correlation_id placeholder.
- [ ] Reconcile analytics.py to read from ledger.py as its source for guardrail metrics — Instead of maintaining a second parallel event system.
- [ ] Author 'retry/rework survives resume' behavioral-eval fixture(s) (Gap 6 fixture-split) — For Release 15 to wire into the full 20-case suite.

## ○ Release 14: Guardrail metrics — serves AC-13 (REQ-13)
_phases: plan → build → verify → review → release_

- [ ] Extend _agg_features/_agg_tasks/_agg_loops/_agg_events/_agg_usage/build_health_report with named guardrail fields — False-pass/reopen rate, scope-violation rate, Owner-interruptions-per-milestone, percentage-of-dispatches-with-unknown-usage, duplicate-artifact rate. Define renmark's own measured baseline per metric; do NOT import the proposal's cited external '43%' figure.

## ○ Release 15: 20-case behavioral eval suite authorship — serves AC-8 (REQ-8)
_phases: plan → build → verify → review → release_

- [ ] Author remaining behavioral-eval fixtures not claimed by an earlier release (worker replan-refusal, inspector-can't-repair, judge-can't-override-deterministic-fail, etc.) — Gap 6 fixture-split — fast-path (R1), task-tracker (R4), capability-envelope (R6), risk-tier/lens (R8), judge (R9), failure-rule (R10), retry/rework-resume (R13) authored alongside their own releases; only the remainder lands here.
- [ ] Wire the full 20-case suite together against renmark/behavior.py's existing deterministic/eval-tier split — Combines fixtures authored in releases 1, 4, 6, 8, 9, 10, 13 with this release's own.
- [ ] Make the deterministic tier CI-gating (hard requirement, not merely green) — Eval tier remains opt-in via RENMARK_EVAL_RUNNER_CMD, unchanged. Deterministic tier stays CI-safe: no model call, no network, no spend by default.

## ○ Release 16: /renmark:rethink self-upgrade — serves AC-12 (REQ-12)
_phases: plan → build → verify → review → release_

- [ ] Add a mandatory pre-Execution-Gate independent-Inspector challenge step to REQ-28 via /renmark:prd's UPDATE gate — Distinct from the 3 existing Owner gates (Discovery Direction / Solution / Execution).
- [ ] Wire rethink's own dispatches through the reconciled RenmarkWorkOrder (release 3) — Rethink's own Stage 6/7 classification/blueprint work becomes governed by the same contracts it recommends for the rest of the codebase.
- [ ] Apply lens selection (release 8) to rethink's own Stage 5 modularity work where relevant
- [ ] Add a rethink-pipeline test proving the Inspector-challenge-before-Execution-Gate step actually runs — Not just documented.

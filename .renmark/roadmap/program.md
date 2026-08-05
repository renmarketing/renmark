---
artifact_type: program
schema_version: 1
created_at: 2026-08-05T00:38:23+00:00
source_sha: e6898917ddf3a30505bb01b1b0569c28a187d792
---

# Program — governed-orchestration-assurance

_mode: staged · Stage 1/16 · task 0/2 done · current: Release 1: Baseline and compatibility coverage_

## ○ Release 1: Baseline and compatibility coverage — serves REQ-30 **(current)**
_phases: plan → build → verify → review → release_

- [ ] Turn baseline.md's 9 compatibility checks into runnable tests — Add test-only coverage for the 9 baseline.md checks (pytest count, classify_fast_path, verify_worker_scope, check_dispatch_independence, VERDICTS vocab, complete_worker_task no-self-approval, assert_metadata_only, REQ-30 qualitative guarantees, inspector read-only allowlist). No production code moves. Verify: fresh pytest -q + renmark-execute --behavior.
- [ ] Record real token/wall-clock/dispatch-count numbers for the 4 representative scenarios — Run and record Start/Feature-Fix/Orchestrate/Rethink scenarios into orchestration-baseline.md's unpopulated table, replacing 'not yet measured'. Requires its own cost-preview + Owner go-ahead per that file's flag.

## ○ Release 2: Role-model altitude ADR (spike #28) — serves REQ-1, REQ-2, REQ-12
_phases: plan → build → verify → review → release_

- [ ] Bounded 1-session spike: confirm capability-envelope enforcement altitude — Produce one ADR paragraph confirming per-dispatch-role altitude (subagent_profiles.py) vs project-phase altitude (agency.py) for release 6's capability envelope. Owner/maintainer sign-off required. Stop condition: ADR accepted, no code change unless contradicted.

## ○ Release 3: Canonical work-order reconciliation — serves AC-1 (REQ-1)
_phases: plan → build → verify → review → release_

- [ ] Add risk_tier/capability_envelope_ref/lens/schema_version to ledger.WorkOrder — Additive fields only; pytest -q count stays green except for new additions.
- [ ] Add ledger.work_order_for_task(task, role, ...) -> WorkOrder and call it from dispatch.build_subagent_input — One funnel all 6 dispatch call sites already use; SubagentInput public field names stay stable (REQ-20 metadata-only).
- [ ] Rename RepairWorkOrder.work_order_id to order_id, require it resolves to a real WorkOrder — Keep severity/source_inspection_id/description/acceptance_criteria unchanged.
- [ ] Add wiring test asserting all 6 dispatch call sites produce a WorkOrder via the shared funnel — Fast-path, feature, debug, orchestrate, rethink, resume — no bespoke path.

## ○ Release 4: Task tracker bound to WorkOrder.order_id + selector bypass guard — serves AC-3, AC-4 (REQ-3, REQ-4)
_phases: plan → build → verify → review → release_

- [ ] Bind task_tracking.create_or_reuse_task to the originating WorkOrder.order_id — Uses release 3's funnel.
- [ ] Add interaction.py enforced mode rejecting numbered fallback when a native picker is available — Same ChoiceSet/fallback dataclasses, no new module; reads hosts.capabilities_for.
- [ ] Deferred cosmetic 'concise displayed list' format for Role/worker+model/Budget/Verification — Per prd-acceptance-map's own deferral note.
- [ ] Add regression test named after the 2026-06-14 'Hand-off picker not re-rendered' incident — Proves the enforced-mode guard catches that exact failure mode.

## ○ Release 5: PreToolUse capability-envelope spike (#7) — serves AC-2 (REQ-2)
_phases: plan → build → verify → review → release_

- [ ] Bounded 1-session spike: prototype PreToolUse hook for metadata-driven allow/deny — Read Claude Code's PreToolUse hook contract; prototype one hook wired to one agent profile's allowed_targets; confirm Codex's own enforcement mechanism. Evidence: one working hook config + one passing/one blocking integration test. Stop condition: feasible -> proceed to release 6 as specified; not feasible -> release 6 falls back to post-action-only, documented, escalated to Owner.

## ○ Release 6: Capability-envelope enforcement wiring — serves AC-2 (REQ-2)
_phases: plan → build → verify → review → release_

- [ ] Add subagent_gate.check_capability_envelope(role, requested_scope) -> EnvelopeVerdict — Same shape as existing SubagentVerdict, never raises; called from the same pre-dispatch funnel subagent_gate's justification check already runs from.
- [ ] Wire dispatch_wave() to actually call enforce_wave_dispatch_scopes — Currently never called in production — closes F1.
- [ ] If release 5's spike confirmed feasibility, wire the PreToolUse hook to allowed_targets — One source of truth, two enforcement moments; if not feasible, document the fallback and escalate per the spike's stop condition.

## ○ Release 7: REQ-30 update release (measure + PRD gate) — serves REQ-30
_phases: plan → build → verify → review → release_

- [ ] Measure real current per-dispatch baseline overhead across the 4 representative scenarios — Reuse release 1's captured numbers where still fresh, re-measure where stale.
- [ ] Run /renmark:prd's UPDATE gate to name the Critical-tier gate as a REQ-30 allowed gate + set a measured overhead budget — Releases 8-16 must demonstrate they stay under this budget before shipping.
- [ ] Absorbed: close the renmark-architecture rethink's lingering r1-req30-baseline-measurement task — Carried over from the prior, closed renmark-architecture-rethink-roadmap program (archived at .renmark/rethink/renmark-architecture/archive/closed-program-final-2026-08-04.json), whose Release 1 task r1-req30-baseline-measurement was never marked done. This release's own baseline-overhead measurement (r7-measure-baseline-overhead) satisfies it; not treated as a new ask.

## ○ Release 8: Risk-tier spike (#10b) + risk-tiered InspectionContract + lenses — serves AC-5 (REQ-5)
_phases: plan → build → verify → review → release_

- [ ] Bounded 1-session spike: hand-validate a deterministic risk-tier classifier against 15-20 real past dispatches — Design and validate against .renmark/analytics/task-runs.jsonl / ledger history; document disagreement rate against a human-assigned tier. Stop condition: Owner-acceptable disagreement rate, or one re-spike if criteria redefined.
- [ ] Add RiskTier enum + lens: str | None as additive fields to ledger.InspectionReport — VERDICTS stays the only ledger-legal verdict vocabulary.
- [ ] Add resolve_lens_for(work_order) -> LensName policy function — In the subagent_profiles.py/subagent_gate.py orbit; explicitly not cost.requires_escalation.

## ○ Release 9: Calibrated blind LLM-judge (3-state + bias controls) — serves AC-6 (REQ-6)
_phases: plan → build → verify → review → release_

- [ ] Change judge.py's Outcome to Literal['pass','fail','uncertain'] — Breaking, compile-time-visible; every caller pattern-matching on Outcome must add the third arm.
- [ ] Add a redaction step to compose_judge_prompt before string composition — Redacts Worker self-assessment/confidence/identity at data-assembly time.
- [ ] Add order-randomization to pairwise/comparison calls, recorded per call
- [ ] Add InspectionReport.judge_evidence: JudgeEvidenceRef | None — Attachment, not a merge; never overrides InspectionReport.verdict.

## ○ Release 10: Failure-derived constraint registry — serves AC-7 (REQ-7)
_phases: plan → build → verify → review → release_

- [ ] Add recurrence.active_guards_for(task_context) -> list[Guard] — Read-side accessor over existing durable_guard entries; no new store, no new schema.
- [ ] Wire subagent_gate.py to consume active_guards_for from the pre-dispatch funnel — Same funnel release 6 added check_capability_envelope to.
- [ ] Write the ADR distinguishing Req 7 (constraint registry) from REQ-24 (recurrence.py's existing per-run/fingerprint role) — Flagged as needed 'before Release E' by prd-acceptance-map.

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

- [ ] Bounded 1-session spike: self-benchmark resume/recovery correctness against deliberately-interrupted runs — Reuse heartbeat.py's usage-limit-pause path as the test harness; produce a scenario table (pass/fail on no-duplicate/no-orphan). Stop condition: table produced; gaps become a scoped Improve item.
- [ ] Add schema_version and attempt_id/correlation_id fields to the 4 existing ledger event kinds — Additive only.
- [ ] Reconcile analytics.py to read from ledger.py as its source for guardrail metrics — Instead of maintaining a second parallel event system.

## ○ Release 14: Guardrail metrics — serves AC-13 (REQ-13)
_phases: plan → build → verify → review → release_

- [ ] Extend _agg_features/_agg_tasks/_agg_loops/_agg_events/_agg_usage/build_health_report with named guardrail fields — False-pass/reopen rate, scope-violation rate, Owner-interruptions-per-milestone, percentage-of-dispatches-with-unknown-usage, duplicate-artifact rate. Define renmark's own measured baseline per metric; do NOT import the proposal's cited external '43%' figure.

## ○ Release 15: 20-case behavioral eval suite authorship — serves AC-8 (REQ-8)
_phases: plan → build → verify → review → release_

- [ ] Author the 20 named behavioral-eval fixtures against renmark/behavior.py's existing deterministic/eval-tier split — Fast-path accept/reject, worker replan-refusal, inspector-can't-repair, judge-can't-override-deterministic-fail, blind-judge-input-exclusion, lens-triggering, task-tracker transitions, retry/rework survives resume, etc. Fixture authorship only, no new infrastructure; deterministic tier stays CI-safe (no model call, no network, no spend by default).

## ○ Release 16: /renmark:rethink self-upgrade — serves AC-12 (REQ-12)
_phases: plan → build → verify → review → release_

- [ ] Add a mandatory pre-Execution-Gate independent-Inspector challenge step to REQ-28 via /renmark:prd's UPDATE gate — Distinct from the 3 existing Owner gates (Discovery Direction / Solution / Execution).
- [ ] Wire rethink's own dispatches through the reconciled RenmarkWorkOrder (release 3) — Rethink's own Stage 6/7 classification/blueprint work becomes governed by the same contracts it recommends for the rest of the codebase.
- [ ] Apply lens selection (release 8) to rethink's own Stage 5 modularity work where relevant
- [ ] Add a rethink-pipeline test proving the Inspector-challenge-before-Execution-Gate step actually runs — Not just documented.

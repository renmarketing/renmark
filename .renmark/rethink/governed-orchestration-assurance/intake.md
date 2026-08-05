---
artifact_type: rethink-intake
schema_version: 1
created_at: 2026-08-04T00:00:00Z
source_sha: e689891
related_plan: null
generator: sonnet
stale_after: null
dependency_refs:
  - C:\Users\rrent\Downloads\renmark-governed-orchestration-upgrade-proposal.md (Owner-supplied, copied verbatim below by reference)
  - .renmark/rethink/renmark-architecture/ (prior rethink run, STRUCTURAL-ONLY scope, Execution Gate approved 2026-08-03, all 7 releases shipped 2026-08-04)
  - .bootstrap-renmark/ (R-0.0-R-0.4 governing directive + milestone artifacts, 2026-07-31..2026-08-01)
  - .renmark/memory/orchestration-baseline.md (REQ-30 pin, v0.39.7/d9cccc5)
---

# Transformation Intake — governed-orchestration-assurance

**Target:** renmark itself (this repo). Owner-supplied governing document
(`renmark-governed-orchestration-upgrade-proposal.md`) is the accepted
proposal input, per its own closing instruction: "Begin by running
`/renmark:rethink` ... using this document as the accepted proposal input.
Stop after presenting the repository-grounded roadmap and Owner selector."
No additional Owner round is needed for the fields below — the document
answers them directly and in more detail than a normal intake round would.

**Desired outcome:** Evolve Renmark from a prompt-oriented engineering
harness into a durable, provider-agnostic software-engineering control plane:
bounded structured work orders for every meaningful dispatch, enforced role
authority/capability limits (Owner → General Contractor → Architect → Worker
→ Inspector), independent PASS/FAIL/UNCERTAIN inspection, risk-tiered
falsification-lens review, calibrated blind LLM-judging, a failure-derived
constraint registry (not a growing global prohibition list), a behavioral
regression suite, an accurate task tracker tied to real dispatches, enforced
selector/headless interaction contracts, budgeted context/cost/retry/
parallelism, durable events/recovery for long-running work, and outcome
guardrail metrics — while internal governance stays invisible unless it
produces a blocker, uncertainty, or a required Owner decision. Governing
principle (verbatim): "Workers produce bounded artifacts and evidence.
Renmark alone governs authoritative lifecycle transitions."

**Protected behavior (from the proposal's "Current baseline to preserve"):**
- v0.41.0-era shipped behavior: real per-dispatch usage when available with
  explicit `unknown` fallback, context-lifecycle checkpoints, expensive-model
  routing warnings, artifact-lifecycle controls, byte-aware state trimming,
  completed-work archival fixes.
- The Owner → General Contractor → Architect → Worker → Inspector role model.
- The bounded small-task fast path (deterministic eligibility classification
  + post-run WorkerScope verification) — extend, never replace with a second
  fast path.
- R-0.2 (Controlled Worker Execution) if already drafted/shipped — use as
  foundation where compatible, not superseded.
- `/renmark:rethink` itself — improve, do not build a competing pipeline.
- Existing task-tracking, routing, verification, artifact, and release
  concepts — consolidate enforcement, do not duplicate.
- Existing user-facing approval surfaces stay the default approval surfaces.
- Internal governance stays invisible by default.
- Releases stay incremental, Owner-testable, observable, reversible.

**Constraints:** No hard timeline/budget/platform/team constraint stated.
Sequence prerequisite refactors only where they materially reduce
implementation risk for this proposal's requirements — do not turn unrelated
modernization into a hard prerequisite for every capability in scope.
Historical test counts are context, not proof — the repository's current
test suite must be run and recorded as the real baseline (stage 1/2).

**Non-goals (from the proposal's "Explicit exclusions" — verbatim list):**
- Architecture/operating instructions for external orchestration or business
  systems; content-generation/publishing/campaign/domain-workflow design.
- A new general-purpose distributed scheduler, message broker, database, web
  dashboard, or daemon fleet.
- A permanent multi-agent debate layer or every-perspective-on-every-task
  review.
- An LLM judge treated as truth or allowed to override deterministic
  evidence.
- Prompt-only safety for actions that can be enforced by tools or code.
- Unlimited retries, rework, self-improvement, or autonomous policy
  rewriting.
- Hidden chain-of-thought persistence.
- Reliance on provider prompt caching for correctness.
- A hard dependency on any single model/provider or specific hardware.
- Automatic merge, tag, release, destructive action, external communication,
  or spending without established Owner authority.
- Arbitrary global memory limits copied from another agent without
  Renmark-specific measurement.
- A big-bang rewrite/replacement of the active canonical rethink, fast-path,
  lifecycle, artifact, task, or release systems.
- Changes to a target application's production code, except bounded
  fixtures/example repos required to test Renmark itself.

**Areas open to change:** Everything the proposal's 13 requirements name:
the work-order contract; lifecycle/receipts; capability envelopes
(pre-action + post-action enforcement); the task tracker's binding to real
work orders; the selector/headless interaction contract; the risk-tiered
`InspectionContract` and falsification lenses; the LLM-judge input isolation
and bias controls; the failure-rule registry; the behavioral eval suite;
policy-aware dispatch planning; context/memory governance; durable
events/recovery; `/renmark:rethink` itself (Requirement 12); and outcome
metrics. Stages 1–5 evidence — reconciled explicitly against what
`.bootstrap-renmark`'s R-0.0–R-0.4 and the closed `renmark-architecture`
rethink already shipped — drives what is actually still missing versus
already done, per the proposal's own instruction: "Audit the current Renmark
repository and reconcile this proposal with what is already shipped,
drafted, partially implemented, or missing."

**Known prior/adjacent work to reconcile against (not to re-derive):**
- `.bootstrap-renmark/`: R-0.0 (baseline/PRD reconciliation, RELEASED
  v0.39.3), R-0.1 (bounded small-task fast path, RELEASED v0.39.4,
  ACCEPTED WITH FOLLOW-UP), R-0.2 (Controlled Worker Execution, RELEASED
  v0.39.5, ACCEPTED WITH FOLLOW-UP — F1 residual: scope-enforcement blocking
  has no production caller; F2: repair-work-order emission is prose-invoked
  only; F3 residual: R-008 gate live but lenient-only; F4: rework-cap
  uniformity gaps at fast-path/debug; F5: replan-gate coverage is
  debug-only), R-0.3 (Minimal Canonical Ledger — Work Order/Result/
  Inspection Report/Escalation schemas + real emission call sites, RELEASED
  v0.39.6, ACCEPTED no follow-up, narrow scope — blueprint/milestone-
  contract/closeout schemas, hashing, snapshot/restore, migration adapters,
  universal dispatch-path rewiring deferred), R-0.4 (Minimal Independent
  Inspector, RELEASED v0.39.7, dispatch-independence enforcement + verdict
  emission).
- `.renmark/rethink/renmark-architecture/`: a prior, narrower
  STRUCTURAL-ONLY rethink (Discovery Direction Gate + Solution Gate +
  Execution Gate all approved 2026-08-03), 7 releases shipped through
  2026-08-04 (lifecycle.py → package split, cli/_engine.py split,
  cost.py-centralized routing, schemas.py dependency-direction fix,
  context_budget_hint dead-code removal, skillmeta-completeness lint).
  Different scope from this transformation (structure-only, not governance/
  assurance) — do not re-run or duplicate its stages; treat its shipped
  artifacts as current repository state for this run's stage 1 survey.
- `.renmark/memory/orchestration-baseline.md`: REQ-30 baseline pin
  (`ORCHESTRATION-BASELINE-2026-08`, v0.39.7/`d9cccc5`) — any change to
  routing, context limits, dispatch policy, model escalation, Owner-gate
  frequency, or artifact-reuse behavior in this transformation requires a
  `PRD.md` REQ-30 UPDATE-gate change, not a side effect.
- PRD REQ-28 (rethink pipeline), REQ-30 (orchestration efficiency protected
  capability), REQ-31 (native task tracking) already exist and are directly
  in scope for Requirement 3/4/12 of the proposal.

**Decision log:**
- 2026-08-04: Intake captured directly from the Owner-supplied governing
  document (no AskUserQuestion round needed — the document is more complete
  than a normal intake interview and explicitly instructs rethink to treat
  it as the accepted proposal input). Slug `governed-orchestration-assurance`
  chosen to keep this transformation's artifacts distinct from the closed
  `renmark-architecture` rethink and the `.bootstrap-renmark` R-0.x track.

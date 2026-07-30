---
artifact_type: plan
schema_version: 1
created_at: 2026-07-30T20:15:00-04:00
source_sha: bb25f4a
related_plan: .renmark/plans/2026-07-29-two-mode-milestone-delivery.plan.md
generator: renmark:plan
completion_state: complete
confidence: high
validation_status: validated
retry_count: 0
parser_success: true
schema_compliance: true
dependency_refs:
  - PRD.md#REQ-22
  - .renmark/plans/2026-07-29-two-mode-milestone-delivery.plan.md#milestone-m4
  - .renmark/plans/2026-07-30-m3-milestone-planner-work-packages.plan.md
---

# M4 — Milestone Execution, Verification, Review, and Loops

M4 makes the already-planned milestone/work-package format executable without
turning loops into a third mode.  Each package may change its implementation
and directly related tests together, then follows a bounded build → verify →
review → scoped-fix loop: at most two implementation repairs per package and
three review-fix-review cycles per milestone.  It stops on unresolved verifier
failure, a repeated-evidence fingerprint, scope drift, security/destructive
gates, or any budget expansion.  Results persist at every package and
milestone boundary; resumption always uses stable milestone/package IDs.

## Milestone contract

- **goal:** Execute an approved milestone through fresh verification,
  independent review, bounded repair, and signoff readiness.
- **expected_outcome:** Agency may advance only from a clean milestone
  boundary; direct Orchestrator work receives the same bounded evidence and
  can opt into proportional review.
- **acceptance_evidence:** loop/review/resume tests; an end-to-end synthetic
  milestone with one verifier failure and one review finding; fresh final
  repository quality gates.
- **dependencies:** M1 canonical delivery state, M2 decision contract, M3
  package parser/compiler and cost previews.
- **risks:** scope-changing repair packages, raw review/verifier data leaking
  into canonical state, no-progress retries, or signoff without a fresh review.
- **cost_lane:** standard; no Opus/Fable is planned.  Independent review is a
  bounded read-only Codex/reviewer pass after deterministic checks.
- **demo_point:** Run a synthetic package through failure → scoped repair →
  clean verification → review finding → scoped fix → re-review.
- **signoff_policy:** owner signoff only after clean verification and review.

## Work packages

## WP M4-1 — Milestone-scoped loop identity and persistence
- **goal:** Bind loop runtime state to stable milestone/work-package IDs while
  retaining standalone `/renmark:loop` compatibility.
- **expected_outcome:** A resumed loop finds the same package by ID and cannot
  mark a milestone complete from package-local state alone.
- **acceptance_evidence:** focused loop and delivery-state tests prove bounded,
  atomic state and no index-only continuation.
- **dependencies:** M1, M3.
- **risks:** delivery-state bloat and legacy loop compatibility.
- **allowed_surfaces:** [implementation, tests]
- **cost_lane:** standard
- **demo_point:** persisted package loop state is resumed by stable ID.
- **signoff_policy:** automatic package gate; milestone review required.
- **status:** pending

## WP M4-2 — Verification and recurrence-controlled repair decisions
- **goal:** Turn fresh verifier evidence and recurrence fingerprints into a
  scope-bounded repair decision, never an uncontrolled retry.
- **expected_outcome:** failed evidence can create one scoped repair package;
  the third equivalent attempt stops with actionable evidence.
- **acceptance_evidence:** program-driver and recurrence fixtures cover pass,
  failure, budget, scope, and no-progress stops.
- **dependencies:** M4-1, existing recurrence ledger.
- **risks:** stale evidence or scope-expanding repair packets.
- **allowed_surfaces:** [implementation, tests]
- **cost_lane:** standard
- **demo_point:** one failing verifier produces a bounded repair decision.
- **signoff_policy:** automatic package gate; milestone review required.
- **status:** pending

## WP M4-3 — Independent review findings to scoped fix packages
- **goal:** Export structured review findings as bounded, independently
  verifiable fix packages, followed by fresh verification and re-review.
- **expected_outcome:** Critical/Major findings block signoff; routine review
  progress remains prose and only actual decisions use the M2 choice contract.
- **acceptance_evidence:** review-package and command fixtures cover findings,
  safe refusal, fix creation, and clean re-review.
- **dependencies:** M4-2, M2 interaction contract.
- **risks:** raw review-body leakage, unsafe auto-fixes, or lost refusal paths.
- **allowed_surfaces:** [implementation, tests]
- **cost_lane:** standard
- **demo_point:** a review finding becomes a scoped fix package and blocks
  signoff until re-review passes.
- **signoff_policy:** automatic package gate; milestone review required.
- **status:** pending

## WP M4-4 — Finish/readiness and signoff enforcement
- **goal:** Require fresh verification and clean independent review before
  Agency milestone signoff or release readiness.
- **expected_outcome:** finish reports explicit signoff readiness or an exact
  blocker; no merge/release/security/PRD action is auto-fixed.
- **acceptance_evidence:** lifecycle/finish fixtures prove stale verification,
  failing review, and unresolved gates cannot advance a milestone.
- **dependencies:** M4-1 through M4-3.
- **risks:** accidentally weakening existing finish lanes or approval gates.
- **allowed_surfaces:** [implementation, tests, docs]
- **cost_lane:** standard
- **demo_point:** clean synthetic milestone becomes signoff-ready only after a
  fresh verifier and review.
- **signoff_policy:** owner signoff required.
- **status:** pending

## Executor tasks

### Task 1: Persist milestone/package loop identity
- **mode:** B
- **target:** renmark/loop.py
- **complexity:** hard
- **executor:** sonnet
- **role:** code-implementer
- **parallel_group:** 1
- **est_tokens:** 3000
- **est_cost_usd:** 0.0390
- **verifier:** .venv/bin/pytest -q tests/test_loop.py
- **serves:** REQ-22
- **spec:** Extend the deterministic loop state and helpers with stable milestone and work-package identity, bounded stop metadata, and explicit no-scope-advance semantics. Preserve the current standalone loop API and state compatibility. Do not read source/diffs into state or alter approval handling.

### Task 2: Prove loop identity, resume, and stop boundaries
- **mode:** B
- **target:** tests/test_loop.py
- **complexity:** hard
- **executor:** codex
- **role:** test-writer
- **parallel_group:** 2
- **est_tokens:** 2400
- **est_cost_usd:** 0.0720
- **verifier:** .venv/bin/pytest -q tests/test_loop.py
- **serves:** REQ-22
- **spec:** Add direct coverage for milestone/package identity, stable-ID resume, fresh-evidence requirements, maximum two repair iterations, and no-progress or approval-boundary stops. Keep existing standalone-loop behavior green.

### Task 3: Add repair-decision and recurrence integration
- **mode:** B
- **target:** renmark/program_driver.py
- **complexity:** hard
- **executor:** sonnet
- **role:** code-implementer
- **parallel_group:** 3
- **est_tokens:** 3200
- **est_cost_usd:** 0.0396
- **verifier:** .venv/bin/pytest -q tests/test_program_driver.py
- **serves:** REQ-22, REQ-24
- **spec:** Add deterministic milestone execution decisions that consume fresh verifier metadata, create only scoped repair-package pointers, and invoke the recurrence guard before a third equivalent attempt. Never expand product scope or advance milestone state from a failed/incomplete loop.

### Task 4: Prove verification, scope, and recurrence decisions
- **mode:** B
- **target:** tests/test_program_driver.py
- **complexity:** hard
- **executor:** codex
- **role:** test-writer
- **parallel_group:** 4
- **est_tokens:** 2600
- **est_cost_usd:** 0.0780
- **verifier:** .venv/bin/pytest -q tests/test_program_driver.py
- **serves:** REQ-22, REQ-24
- **spec:** Cover verifier-pass, verifier-fail, stale-evidence, budget-hit, scope-drift, repeated-evidence, and resumption decisions. Assert repair outputs are stable package references and never raw verifier bodies.

### Task 5: Export review findings as safe scoped packages
- **mode:** B
- **target:** renmark/cli/commands.py
- **complexity:** hard
- **executor:** sonnet
- **role:** code-implementer
- **parallel_group:** 5
- **est_tokens:** 3000
- **est_cost_usd:** 0.0390
- **verifier:** .venv/bin/pytest -q tests/test_cli_commands.py
- **serves:** REQ-22
- **spec:** Extend the existing review-package seam to emit bounded, structured finding summaries and safe scoped-fix package references. Route review/fix/re-review decisions through the existing semantic choice contract; preserve refusal/cancel paths and never auto-fix dangerous findings.

### Task 6: Prove review-to-fix and interaction boundaries
- **mode:** B
- **target:** tests/test_cli_commands.py
- **complexity:** hard
- **executor:** codex
- **role:** test-writer
- **parallel_group:** 6
- **est_tokens:** 2400
- **est_cost_usd:** 0.0720
- **verifier:** .venv/bin/pytest -q tests/test_cli_commands.py tests/test_interaction.py
- **serves:** REQ-22, REQ-23
- **spec:** Add fixtures for Critical/Major signoff blocking, bounded finding export, scoped-fix creation, cancellation/refusal reachability, and re-review readiness. Do not freeze a host-specific picker presentation.

### Task 7: Enforce fresh review and verification before readiness
- **mode:** B
- **target:** renmark/lifecycle.py
- **complexity:** hard
- **executor:** sonnet
- **role:** code-implementer
- **parallel_group:** 7
- **est_tokens:** 2600
- **est_cost_usd:** 0.0378
- **verifier:** .venv/bin/pytest -q tests/test_lifecycle.py
- **serves:** REQ-22
- **spec:** Add milestone signoff/readiness predicates requiring fresh verified and reviewed evidence. Preserve lifecycle size limits and all merge/release/security/PRD approval gates. Direct Orchestrator remains proportional; Agency cannot advance without clean milestone evidence.

### Task 8: Prove signoff/readiness gates and final regression coverage
- **mode:** B
- **target:** tests/test_lifecycle.py
- **complexity:** hard
- **executor:** codex
- **role:** test-writer
- **parallel_group:** 8
- **est_tokens:** 2400
- **est_cost_usd:** 0.0720
- **verifier:** .venv/bin/pytest -q tests/test_lifecycle.py tests/test_delivery_state.py
- **serves:** REQ-22
- **spec:** Cover clean signoff readiness, stale verification, failed review, unresolved loop, Agency blocking, direct-Orchestrator proportional behavior, and persisted boundary recovery. Keep legacy lifecycle fixtures valid.

### Task 9: Document the execution/review loop contract
- **mode:** B
- **target:** plugin/skills/.shared/agency-delivery.md
- **complexity:** medium
- **executor:** haiku
- **role:** docs-editor
- **parallel_group:** 9
- **est_tokens:** 900
- **est_cost_usd:** 0.0011
- **verifier:** rg -q 'review.*scoped fix|scoped fix.*review' plugin/skills/.shared/agency-delivery.md && rg -q 'milestone-local' plugin/skills/.shared/agency-delivery.md
- **serves:** REQ-22
- **spec:** Describe the implemented milestone-local build and review loops by pointer-level contract only. State caps, stop conditions, fresh evidence, owner signoff, and the distinction between status prose and real decision menus. Do not claim APIs not implemented and do not edit CLAUDE.md or AGENTS.md; M5 owns managed contract propagation.

## Deterministic gates and dispatch policy

- Preflight: `python3 -m renmark.parser` package parse probe, `python3 -m renmark.plan_lint .renmark/plans/2026-07-30-m4-milestone-execution-review-loops.plan.md`, `python3 -m renmark.subagent_gate .renmark/plans/2026-07-30-m4-milestone-execution-review-loops.plan.md`, baseline `ruff check`, and `mypy .`.
- Per package: implementation + directly related tests, then bounded build → verify → independent review → scoped repair only when needed. Maximum three total review-fix-review cycles per milestone.
- Boundary persistence: write package result, verifier/review metadata pointers, token/cost totals, and next stable package ID before moving forward. Never use task-index resume.
- Hard stops: unresolved test/type/lint failure; a third equivalent attempt; evidence or scope drift; security/destructive/PRD/merge/release gate; or any request to exceed the approved cost cap.

## Cost preview

| Lane | Tasks | Estimated tokens | Estimated cost |
|---|---:|---:|---:|
| Implementation / tests | 8 | 21,600 | $0.45 |
| Documentation | 1 | 10,900 | $0.00 |
| Independent review + bounded repairs reserve | — | 28,000 | $0.42 |
| **M4 approved cap** | **9** | **60,500** | **$0.87** |

No expensive frontier executor is planned. The cheaper alternative is to defer
independent review, but that would not meet REQ-22 and is therefore not
recommended.

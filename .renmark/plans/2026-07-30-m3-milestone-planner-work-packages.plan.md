---
artifact_type: plan
schema_version: 1
created_at: 2026-07-30T17:15:00-04:00
source_sha: ced3f26
related_plan: .renmark/plans/2026-07-29-two-mode-milestone-delivery.plan.md
generator: renmark:plan
completion_state: complete
confidence: high
validation_status: validated
retry_count: 0
parser_success: true
schema_compliance: true
dependency_refs:
  - .renmark/reviews/2026-07-30-wp-m2-a-boundary.md
  - .renmark/reviews/2026-07-30-wp-m2-b-boundary.md
  - .renmark/reviews/2026-07-30-wp-m2-c-boundary.md
---

# M3 — Milestone Planner and Work-Package Compiler

M3 makes milestone-first planning executable without breaking the present
single-file task backend. It delivers stable milestone/work-package identities,
bounded package surfaces, a compiler to current task packets, deterministic
lint/routing gates, and honest cost previews. Execution is not authorized by
this plan; each M3 work package will use its own maximum-three-iteration
build → verify → review → fix loop and persist a boundary artifact.

## Acceptance evidence

- An Agency roadmap and a defined Orchestrator goal both compile into stable,
  resumable milestone/work-package IDs.
- A package may explicitly allow its implementation and directly related tests
  together, while the compiler emits existing one-target task packets.
- Package planning cannot leak transcripts, bypass deterministic-first routing,
  or price work outside a visible package cost preview.

### Task 1: Define milestone and work-package schemas
- **mode:** B
- **target:** renmark/schemas.py
- **complexity:** hard
- **executor:** sonnet
- **role:** code-implementer
- **parallel_group:** 1
- **est_tokens:** 2400
- **est_cost_usd:** 0.0372
- **verifier:** .venv/bin/pytest -q tests/test_schemas.py
- **serves:** REQ-5, REQ-22
- **spec:**
  Add bounded typed validation for milestone and work-package documents: stable
  identifiers, goal, expected outcome, acceptance evidence, dependencies,
  risks, allowed surfaces, cost lane, demo point, signoff policy, and package
  status. Keep delivery.json compact; reject transcript/diff payload fields.

### Task 2: Add schema acceptance coverage
- **mode:** B
- **target:** tests/test_schemas.py
- **complexity:** medium
- **executor:** codex
- **role:** test-writer
- **parallel_group:** 2
- **est_tokens:** 1600
- **est_cost_usd:** 0.0480
- **verifier:** .venv/bin/pytest -q tests/test_schemas.py
- **serves:** REQ-5, REQ-22
- **spec:**
  Cover valid milestone/work-package payloads, ID normalization, bounded text,
  forbidden transcript fields, and invalid status/surface failures.

### Task 3: Parse package-plan markdown beside task plans
- **mode:** B
- **target:** renmark/parser.py
- **complexity:** hard
- **executor:** sonnet
- **role:** code-implementer
- **parallel_group:** 3
- **est_tokens:** 2800
- **est_cost_usd:** 0.0384
- **verifier:** .venv/bin/pytest -q tests/test_parser.py
- **serves:** REQ-5, REQ-22
- **spec:**
  Add a package-plan parser that preserves stable milestone/package IDs and
  allowed file surfaces. Retain the existing Task parser unchanged as the
  compiler backend and reject index-only resume metadata.

### Task 4: Add package-parser round-trip coverage
- **mode:** B
- **target:** tests/test_parser.py
- **complexity:** medium
- **executor:** codex
- **role:** test-writer
- **parallel_group:** 4
- **est_tokens:** 1800
- **est_cost_usd:** 0.0540
- **verifier:** .venv/bin/pytest -q tests/test_parser.py
- **serves:** REQ-5, REQ-22
- **spec:**
  Add parser fixtures for Agency and direct Orchestrator package plans,
  multi-file allowed surfaces, stable IDs across reload, and malformed or
  index-only resume rejection.

### Task 5: Compile packages to current task packets
- **mode:** A
- **target:** renmark/work_packages.py
- **complexity:** hard
- **executor:** sonnet
- **role:** code-implementer
- **parallel_group:** 5
- **est_tokens:** 3600
- **est_cost_usd:** 0.0408
- **verifier:** .venv/bin/pytest -q tests/test_work_packages.py
- **serves:** REQ-5, REQ-22
- **spec:**
  Implement a deterministic compiler from one milestone package to current
  parser.Task packets. Preserve package IDs in task metadata, emit only
  bounded artifact pointers/dependency summaries, and keep the existing
  executor packet shape compatible.

### Task 6: Prove compiler compatibility and rollback
- **mode:** A
- **target:** tests/test_work_packages.py
- **complexity:** medium
- **executor:** codex
- **role:** test-writer
- **parallel_group:** 6
- **est_tokens:** 2200
- **est_cost_usd:** 0.0660
- **verifier:** .venv/bin/pytest -q tests/test_work_packages.py
- **serves:** REQ-5, REQ-22
- **spec:**
  Test package compilation to current Tasks, stable package identity after
  reload, multi-file package boundaries, backend compatibility, and a disabled
  package-parser fallback to current-format plans.

### Task 7: Make plan lint package-aware
- **mode:** B
- **target:** renmark/plan_lint.py
- **complexity:** medium
- **executor:** codex
- **role:** code-implementer
- **parallel_group:** 7
- **est_tokens:** 1800
- **est_cost_usd:** 0.0540
- **verifier:** .venv/bin/pytest -q tests/test_plan_lint.py
- **serves:** REQ-5
- **spec:**
  Add deterministic package-plan checks for bounded allowed surfaces, required
  acceptance evidence, package IDs, artifact-only dependency references, and
  transcript-leak rejection while retaining current task-plan results.

### Task 8: Add package lint regression coverage
- **mode:** B
- **target:** tests/test_plan_lint.py
- **complexity:** medium
- **executor:** codex
- **role:** test-writer
- **parallel_group:** 8
- **est_tokens:** 1400
- **est_cost_usd:** 0.0420
- **verifier:** .venv/bin/pytest -q tests/test_plan_lint.py
- **serves:** REQ-5
- **spec:**
  Cover valid package plans and each package-specific BLOCK condition without
  weakening current task-plan lint fixtures.

### Task 9: Extend deterministic subagent justification to packages
- **mode:** B
- **target:** renmark/subagent_gate.py
- **complexity:** medium
- **executor:** codex
- **role:** code-implementer
- **parallel_group:** 9
- **est_tokens:** 1600
- **est_cost_usd:** 0.0480
- **verifier:** .venv/bin/pytest -q tests/test_subagent_gate.py
- **serves:** REQ-21
- **spec:**
  Evaluate package work against deterministic-first rules before it compiles to
  agents. Require a judgment-based justification for model work and surface
  deterministic package checks as non-model work.

### Task 10: Add package routing-gate coverage
- **mode:** B
- **target:** tests/test_subagent_gate.py
- **complexity:** medium
- **executor:** codex
- **role:** test-writer
- **parallel_group:** 10
- **est_tokens:** 1200
- **est_cost_usd:** 0.0360
- **verifier:** .venv/bin/pytest -q tests/test_subagent_gate.py
- **serves:** REQ-21
- **spec:**
  Add positive and negative package-routing fixtures proving deterministic
  checks are not dispatched and unexplained general-purpose package work is
  challenged.

### Task 11: Price milestones and packages
- **mode:** B
- **target:** renmark/cost.py
- **complexity:** medium
- **executor:** codex
- **role:** code-implementer
- **parallel_group:** 11
- **est_tokens:** 1600
- **est_cost_usd:** 0.0480
- **verifier:** .venv/bin/pytest -q tests/test_cost.py
- **serves:** REQ-22
- **spec:**
  Add deterministic package and milestone cost aggregation with executor,
  overhead, escalation, and cheaper-alternative data. Do not estimate from
  transcripts or hide package totals.

### Task 12: Add milestone cost-preview coverage
- **mode:** B
- **target:** tests/test_cost.py
- **complexity:** medium
- **executor:** codex
- **role:** test-writer
- **parallel_group:** 12
- **est_tokens:** 1200
- **est_cost_usd:** 0.0360
- **verifier:** .venv/bin/pytest -q tests/test_cost.py
- **serves:** REQ-22
- **spec:**
  Prove package totals, milestone aggregation, deterministic-only packages,
  escalation labels, and the visible cost band remain stable.

## Cost preview

- 12 tasks, 12 ordered work packets; direct test tasks stay adjacent to their implementation.
- Estimated total: 52,200 tokens, including 30,000 Sonnet packet overhead; approximately $0.55.
- Executors: Sonnet ×3 for schema/compiler architecture; Codex ×9 for bounded code/tests.
- Expensive models: none. Fable is not required; deep review is an escalation only if the package schema has an unresolved design fork.
- Cheaper alternative: retain the existing task parser/backend and use deterministic schema/lint/cost checks before any implementation dispatch.

## Dispatch constraints

Planning is complete once this document validates. Before M3 execution, present
the package-level cost preview and require a new explicit dispatch approval.
Stop on scope or budget expansion, any security/destructive gate, parser
compatibility regression, or failure to preserve G11 bounded context.

## Planning blocker discovered after validation

The current bounded `delivery.json` cannot accept four additional pending M3
packages without exceeding its 4,096-byte contract (projected: 5,061 bytes).
The atomic writer rejected that update and the M2 state remains intact. M3
execution therefore needs an explicitly approved first package for archival or
compaction of completed package summaries, preserving their boundary artifacts
and provenance pointers. This is a scope amendment, not an implicit retry.

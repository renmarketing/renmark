---
artifact_type: renmark_execution_plan
schema_version: 1
created_at: 2026-07-29T00:00:00-04:00
source_sha: 6a3258c
related_plan: .renmark/plans/2026-07-29-two-mode-milestone-delivery.plan.md
generator: codex
stale_after: null
dependency_refs:
  - PRD.md#REQ-22
  - PRD.md#REQ-25
  - renmark/agency.py
  - renmark/program.py
  - renmark/lifecycle.py
  - renmark/state/pipeline.py
completion_state: complete
confidence: high
validation_status: validated
retry_count: 0
parser_success: validated
schema_compliance: validated
---

# M1 Bootstrap Plan: Canonical Delivery State

## Context

This plan is intentionally executable by the current Renmark engine. The current parser requires each task to name exactly one target file, so this bootstrap milestone uses one-file task packets even when the future work-package format will allow a bounded multi-file surface. That restriction is temporary and is removed by the later milestone-planner/work-package milestone.

M1 implements the foundation for REQ-22 and REQ-25: one per-run delivery aggregate, stable milestone and work-package IDs, schema/version/migration adapters, current-state drift repair, bounded event/provenance support, and tests. Do not change source, tests, docs, state, memory, or templates beyond each task's target.

## Tasks

### Task 1: Add canonical delivery-state model
- **mode:** A
- **target:** renmark/delivery_state.py
- **context_files:** [renmark/agency.py, renmark/program.py, renmark/lifecycle.py, renmark/state/pipeline.py, renmark/mode.py]
- **executor:** codex
- **complexity:** hard
- **role:** code-implementer
- **parallel_group:** 1
- **est_tokens:** 3200
- **est_cost_usd:** 0.096
- **serves:** REQ-22, REQ-25
- **verifier:** python -m py_compile renmark/delivery_state.py && pytest -q tests/test_delivery_state.py
- **spec:**
  Create a stdlib-only `renmark.delivery_state` module.
  Allowed reads: the context files named above and existing schema/state conventions.
  Define dataclasses or typed helpers for a delivery run aggregate with schema_version, run_id, delivery_mode `agency|orchestrator`, execution_policy `guided|direct|async`, active milestone ID, work-package summaries, approval/review/verification/loop statuses, contract_version, source_sha, bounded provenance events, and legacy_refs.
  Provide atomic read/write helpers under `.renmark/state/delivery.json`, missing-file default, corruption reporting, stable ID helpers for milestones and work packages, bounded summary accessors, and bloat protection comparable to lifecycle constraints.
  Invariants: Agency delegates milestone execution to Orchestrator; Conductor is never a public delivery_mode; legacy `conductor` may appear only as execution_policy `guided`.
  Do not touch other files, PRD, templates, or live state.
  Rollback expectation: deleting this new module must leave legacy state readers untouched.

### Task 2: Test canonical delivery-state model
- **mode:** A
- **target:** tests/test_delivery_state.py
- **context_files:** [renmark/delivery_state.py, tests/test_agency.py, tests/test_program.py, tests/test_lifecycle.py]
- **executor:** codex
- **complexity:** hard
- **role:** test-writer
- **parallel_group:** 2
- **est_tokens:** 2600
- **est_cost_usd:** 0.078
- **serves:** REQ-22, REQ-25
- **verifier:** pytest -q tests/test_delivery_state.py
- **spec:**
  Add focused tests for the new delivery state module.
  Allowed reads: the context files named above and existing test style.
  Cover default read behavior, atomic write/read round trip, schema_version preservation, rejection or repair of invalid public modes, legacy conductor mapping to guided policy, stable milestone/work-package ID format, provenance event bounds, bloat protection, and bounded summary output.
  Invariants: tests must not require network, model calls, or writes outside tmp_path.
  Do not modify source or other tests.
  Rollback expectation: removing this test file must not affect existing test collection.

### Task 3: Add delivery-state schema validation
- **mode:** B
- **target:** renmark/schemas.py
- **context_files:** [renmark/schemas.py, renmark/delivery_state.py, renmark/lifecycle.py, renmark/state/pipeline.py]
- **executor:** codex
- **complexity:** medium
- **role:** code-implementer
- **parallel_group:** 3
- **est_tokens:** 1800
- **est_cost_usd:** 0.054
- **serves:** REQ-22, REQ-25
- **verifier:** python -m py_compile renmark/schemas.py && pytest -q tests/test_schemas.py tests/test_delivery_state.py
- **spec:**
  Extend schema validation with a delivery-state validator that checks schema_version, delivery_mode, execution_policy, stable IDs, status vocabularies, bounded event count, contract fields, and legacy_refs shape.
  Allowed reads: the context files named above.
  Keep existing validators behavior-compatible and additive.
  Invariants: no third-party dependency, no PRD reads, no live state writes.
  Do not change unrelated schema rules.
  Rollback expectation: reverting this file should remove only the new validator and leave current pipeline/lifecycle validators intact.

### Task 4: Test delivery-state schema validation
- **mode:** B
- **target:** tests/test_schemas.py
- **context_files:** [tests/test_schemas.py, renmark/schemas.py, renmark/delivery_state.py]
- **executor:** codex
- **complexity:** medium
- **role:** test-writer
- **parallel_group:** 4
- **est_tokens:** 1500
- **est_cost_usd:** 0.045
- **serves:** REQ-22, REQ-25
- **verifier:** pytest -q tests/test_schemas.py tests/test_delivery_state.py
- **spec:**
  Add tests for the delivery-state validator.
  Allowed reads: the context files named above.
  Cover valid aggregate, invalid public mode, invalid execution policy, invalid ID, malformed legacy_refs, too many provenance events, and missing contract_version when contract freshness is declared.
  Invariants: keep all existing schema tests passing; use compact fixtures only.
  Do not edit source files.
  Rollback expectation: removing added cases should restore previous test file behavior.

### Task 5: Add Agency compatibility adapter
- **mode:** B
- **target:** renmark/agency.py
- **context_files:** [renmark/agency.py, renmark/delivery_state.py]
- **executor:** codex
- **complexity:** medium
- **role:** code-implementer
- **parallel_group:** 5
- **est_tokens:** 1800
- **est_cost_usd:** 0.054
- **serves:** REQ-22
- **verifier:** python -m py_compile renmark/agency.py && pytest -q tests/test_agency.py tests/test_delivery_state.py
- **spec:**
  Add a compatibility adapter that can project current AgencyState into the canonical delivery aggregate without changing AgencyState's stored schema.
  Allowed reads: the context files named above.
  Active Agency with empty phase or milestone must become a bounded drift-repair signal or a clear discovery/default milestone state, as defined by delivery_state.
  Invariants: keep `read_agency`, `write_agency`, `activate`, `deactivate`, bloat behavior, and file path unchanged.
  Do not modify program/lifecycle/pipeline files.
  Rollback expectation: reverting this file must restore prior Agency behavior and leave delivery_state module independently usable.

### Task 6: Test Agency compatibility adapter
- **mode:** B
- **target:** tests/test_agency.py
- **context_files:** [tests/test_agency.py, renmark/agency.py, renmark/delivery_state.py]
- **executor:** codex
- **complexity:** medium
- **role:** test-writer
- **parallel_group:** 6
- **est_tokens:** 1500
- **est_cost_usd:** 0.045
- **serves:** REQ-22
- **verifier:** pytest -q tests/test_agency.py tests/test_delivery_state.py
- **spec:**
  Add tests for Agency-to-delivery compatibility.
  Allowed reads: the context files named above.
  Cover inactive Agency, active Agency with milestone fields, active Agency with empty milestone fields, signoff_status mapping, roadmap_ref mapping, and no change to atomic write/bloat tests.
  Invariants: no writes outside tmp_path and no assertions that require public Conductor.
  Do not edit source files.
  Rollback expectation: removing added cases should restore previous test coverage.

### Task 7: Add Program compatibility adapter
- **mode:** B
- **target:** renmark/program.py
- **context_files:** [renmark/program.py, renmark/delivery_state.py]
- **executor:** codex
- **complexity:** medium
- **role:** code-implementer
- **parallel_group:** 7
- **est_tokens:** 1900
- **est_cost_usd:** 0.057
- **serves:** REQ-22
- **verifier:** python -m py_compile renmark/program.py && pytest -q tests/test_program.py tests/test_delivery_state.py
- **spec:**
  Add a compatibility adapter that projects Program stages and tasks into delivery milestones and work-package summaries.
  Allowed reads: the context files named above.
  Preserve Program JSON and rendered markdown behavior; add only additive helper functions or mappings.
  Map Program stage IDs to stable milestone IDs where possible and task IDs to work-package IDs where possible.
  Invariants: no change to status vocabulary unless delivery_state maps it externally; no PRD writes.
  Do not modify agency/lifecycle/pipeline files.
  Rollback expectation: reverting this file must leave program persistence exactly as before.

### Task 8: Test Program compatibility adapter
- **mode:** B
- **target:** tests/test_program.py
- **context_files:** [tests/test_program.py, renmark/program.py, renmark/delivery_state.py]
- **executor:** codex
- **complexity:** medium
- **role:** test-writer
- **parallel_group:** 8
- **est_tokens:** 1500
- **est_cost_usd:** 0.045
- **serves:** REQ-22
- **verifier:** pytest -q tests/test_program.py tests/test_delivery_state.py
- **spec:**
  Add tests for Program-to-delivery compatibility.
  Allowed reads: the context files named above.
  Cover stage status mapping, task summary mapping, current_stage_id mapping, stable milestone/work-package IDs, and preservation of existing program read/write/render tests.
  Invariants: do not depend on full rendered markdown bodies; assert bounded status fields and IDs.
  Do not edit source files.
  Rollback expectation: removing added cases should restore prior test file behavior.

### Task 9: Add lifecycle delivery-state seam and drift repair
- **mode:** B
- **target:** renmark/lifecycle.py
- **context_files:** [renmark/lifecycle.py, renmark/delivery_state.py, renmark/agency.py, renmark/program.py, renmark/state/pipeline.py, renmark/mode.py]
- **executor:** codex
- **complexity:** hard
- **role:** code-implementer
- **parallel_group:** 9
- **est_tokens:** 2600
- **est_cost_usd:** 0.078
- **serves:** REQ-22, REQ-25
- **verifier:** python -m py_compile renmark/lifecycle.py && pytest -q tests/test_lifecycle.py tests/test_delivery_state.py
- **spec:**
  Add a lifecycle-facing helper that reads legacy workflow state and returns the canonical delivery summary plus drift-repair notes.
  Allowed reads: the context files named above.
  It must detect contradictory active states, stale or legacy mode values, active Agency with empty phase, and lifecycle/program stage disagreement using bounded evidence.
  Invariants: do not change existing lifecycle stage names or next_steps behavior except where tests explicitly cover new helper output.
  Do not write PRD, templates, or live state from this helper.
  Rollback expectation: reverting this file must preserve existing lifecycle behavior.

### Task 10: Test lifecycle delivery-state seam
- **mode:** B
- **target:** tests/test_lifecycle.py
- **context_files:** [tests/test_lifecycle.py, renmark/lifecycle.py, renmark/delivery_state.py]
- **executor:** codex
- **complexity:** medium
- **role:** test-writer
- **parallel_group:** 10
- **est_tokens:** 1700
- **est_cost_usd:** 0.051
- **serves:** REQ-22, REQ-25
- **verifier:** pytest -q tests/test_lifecycle.py tests/test_delivery_state.py
- **spec:**
  Add focused tests for the lifecycle delivery-state seam.
  Allowed reads: the context files named above.
  Cover clean lifecycle projection, contradictory lifecycle/program state evidence, legacy conductor mapping to guided policy, empty active Agency repair note, and bounded output from the summary helper.
  Invariants: existing next_steps and approval-gate tests must remain unchanged.
  Do not edit source files.
  Rollback expectation: removing added cases should restore previous test behavior.

### Task 11: Link pipeline runtime state to delivery run
- **mode:** B
- **target:** renmark/state/pipeline.py
- **context_files:** [renmark/state/pipeline.py, renmark/delivery_state.py]
- **executor:** codex
- **complexity:** medium
- **role:** code-implementer
- **parallel_group:** 11
- **est_tokens:** 1700
- **est_cost_usd:** 0.051
- **serves:** REQ-22
- **verifier:** python -m py_compile renmark/state/pipeline.py && pytest -q tests/test_state_pipeline.py tests/test_delivery_state.py
- **spec:**
  Add additive helpers that expose pipeline runtime progress as delivery-run runtime fields without changing pipeline.json structure.
  Allowed reads: the context files named above.
  Map current_plan, wave_index, wave_total, completed_tasks, failed_tasks, and resumable state into bounded delivery runtime summary fields.
  Invariants: keep read_pipeline_state, write_pipeline_state, clear_pipeline_state, pipeline_is_resumable, and wave summaries behavior-compatible.
  Do not modify lifecycle or dispatch.
  Rollback expectation: reverting this file must restore existing pipeline behavior.

### Task 12: Test pipeline delivery runtime mapping
- **mode:** B
- **target:** tests/test_state_pipeline.py
- **context_files:** [tests/test_state_pipeline.py, renmark/state/pipeline.py, renmark/delivery_state.py]
- **executor:** codex
- **complexity:** medium
- **role:** test-writer
- **parallel_group:** 12
- **est_tokens:** 1400
- **est_cost_usd:** 0.042
- **serves:** REQ-22
- **verifier:** pytest -q tests/test_state_pipeline.py tests/test_delivery_state.py
- **spec:**
  Add tests for pipeline-to-delivery runtime mapping.
  Allowed reads: the context files named above.
  Cover idle, orchestrate, paused, completed/failed task lists, missing pipeline state, and resumable flag mapping.
  Invariants: do not inspect wave summary bodies beyond bounded metadata.
  Do not edit source files.
  Rollback expectation: removing added cases should restore prior pipeline tests.

### Task 13: Add CLI current-state check seam
- **mode:** B
- **target:** renmark/cli/_engine.py
- **context_files:** [renmark/cli/_engine.py, renmark/delivery_state.py, renmark/lifecycle.py]
- **executor:** codex
- **complexity:** medium
- **role:** code-implementer
- **parallel_group:** 13
- **est_tokens:** 2100
- **est_cost_usd:** 0.063
- **serves:** REQ-22, REQ-25
- **verifier:** python -m py_compile renmark/cli/_engine.py && pytest -q tests/test_cli_delivery_state.py tests/test_delivery_state.py
- **spec:**
  Add a non-disruptive CLI seam for deterministic current-state inspection, such as an internal helper or flag wired to delivery_state summary if an existing parser pattern supports it.
  Allowed reads: the context files named above.
  The output must be bounded and include delivery_mode, execution_policy, active milestone, contract_version/freshness marker, and drift count when available.
  Invariants: do not remove existing flags, do not change dispatch semantics, and do not ask Codex users for clear/compact/resume commands.
  Do not write state from inspection.
  Rollback expectation: reverting this file must leave existing CLI flags behavior-compatible.

### Task 14: Test CLI current-state check seam
- **mode:** A
- **target:** tests/test_cli_delivery_state.py
- **context_files:** [renmark/cli/_engine.py, renmark/delivery_state.py, tests/test_cli_task_mode.py, tests/test_mode_cli.py]
- **executor:** codex
- **complexity:** medium
- **role:** test-writer
- **parallel_group:** 14
- **est_tokens:** 1700
- **est_cost_usd:** 0.051
- **serves:** REQ-22, REQ-25
- **verifier:** pytest -q tests/test_cli_delivery_state.py tests/test_delivery_state.py
- **spec:**
  Add tests for the CLI current-state inspection seam.
  Allowed reads: the context files named above.
  Cover no state, clean delivery state, legacy conductor mapping in summary output, drift count output, bounded output, and no state mutation during inspection.
  Invariants: tests must run in tmp_path and not depend on a real model provider.
  Do not edit source files.
  Rollback expectation: removing this new test file must not affect existing test collection.

### Task 15: Add M1 integration smoke for canonical state
- **mode:** A
- **target:** tests/test_delivery_state_integration.py
- **context_files:** [renmark/delivery_state.py, renmark/agency.py, renmark/program.py, renmark/lifecycle.py, renmark/state/pipeline.py]
- **executor:** codex
- **complexity:** medium
- **role:** test-writer
- **parallel_group:** 15
- **est_tokens:** 1900
- **est_cost_usd:** 0.057
- **serves:** REQ-22, REQ-25
- **verifier:** pytest -q tests/test_delivery_state_integration.py tests/test_delivery_state.py
- **spec:**
  Add an integration-style smoke test for canonical state projection across legacy state files.
  Allowed reads: the context files named above.
  Create tmp_path legacy Agency, Program, Lifecycle, Pipeline, and legacy mode state, then assert the canonical summary chooses one delivery run, stable milestone/work-package IDs, bounded drift notes, and no public Conductor mode.
  Include a contract_version/freshness field assertion to prepare REQ-25 propagation.
  Invariants: no live repository state writes, no network, no model calls, no template edits.
  Rollback expectation: removing this new test file must not affect existing test collection.

## Cost preview

- **Tasks / parallel groups:** 15 / 15
- **Executors:** codex×15
- **Estimated tokens:** 28,900
- **Pricing source:** `renmark.cost.PRICE_PER_KTOK["codex"] == 0.03`
- **Estimated total:** **$0.867 (medium band)**
- **Agent overhead:** none; Codex runs as the bounded subprocess executor
- **Expensive models:** none
- **Cheaper alternative:** none that preserves the current-engine bootstrap and per-task verification; M2 introduces bounded work-package grouping to reduce future dispatch overhead
- **Subagent gate:** OK — 15 justified, 0 deterministic-eligible

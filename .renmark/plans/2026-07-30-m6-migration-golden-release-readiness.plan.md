---
artifact_type: plan
schema_version: 1
created_at: 2026-07-30T23:45:00-04:00
source_sha: 727221d
related_plan: .renmark/plans/2026-07-29-two-mode-milestone-delivery.plan.md
generator: renmark:plan
completion_state: complete
confidence: high
validation_status: pending
retry_count: 0
parser_success: pending
schema_compliance: pending
dependency_refs:
  - PRD.md#REQ-22
  - PRD.md#REQ-23
  - PRD.md#REQ-25
---

# M6 — Migration, Golden Trajectories, and Release Readiness

M6 proves the finished two-mode product across supported host surfaces, moves
remaining reports from task-index language to milestone/work-package identity,
records the Conductor migration decision, and validates release/package
readiness. It does not merge, tag, publish, or self-update: those are owner
approval gates after this milestone.

### Task 1: Add Agency and direct-Orchestrator golden trajectories
- **mode:** B
- **target:** renmark/agency.py
- **complexity:** hard
- **executor:** sonnet
- **role:** test-writer
- **parallel_group:** 1
- **est_tokens:** 3000
- **est_cost_usd:** 0.0390
- **verifier:** .venv/bin/pytest -q tests/test_behavior.py
- **serves:** REQ-22, REQ-23
- **spec:** Add the minimal deterministic trajectory surface through the canonical Agency approval path in `renmark/agency.py`, with directly related `renmark/behavior.py` adapter and `tests/behavioral/agency.behavior.json` fixture. Prove Agency reaches an approved milestone through Orchestrator and direct Orchestrator starts from a defined goal without Agency discovery. Preserve host-neutral semantic outcomes and explicit owner gates. Do not alter unrelated behavior fixtures.

### Task 2: Add selector/loop/resume cross-host trajectory coverage
- **mode:** B
- **target:** renmark/behavior.py
- **complexity:** hard
- **executor:** codex
- **role:** test-writer
- **parallel_group:** 2
- **est_tokens:** 2800
- **est_cost_usd:** 0.0840
- **verifier:** .venv/bin/pytest -q tests/test_behavior.py tests/test_interaction.py
- **serves:** REQ-23
- **spec:** Add the minimal deterministic cross-host selector/loop trajectory adapter in `renmark/behavior.py` and extend `tests/behavioral/selector_codex.behavior.json` as its directly related fixture. It must render and compare Claude native, Codex Plan, and Codex Default semantic outcomes, and must create then reread a persisted bounded loop pause/resume record. Prove overflow/cancel/continuation retain recommended-first semantics. Do not claim unsupported native clickability or satisfy the proof with static fields.

### Task 3: Report by stable milestone/work-package identity
- **mode:** B
- **target:** renmark/reports.py
- **complexity:** hard
- **executor:** sonnet
- **role:** code-implementer
- **parallel_group:** 3
- **est_tokens:** 3200
- **est_cost_usd:** 0.0396
- **verifier:** .venv/bin/pytest -q tests/test_reports_analytics.py tests/test_cli_delivery_state.py
- **serves:** REQ-22
- **spec:** Add stable delivery milestone/work-package identifiers to status/analytics report rows while retaining legacy task fields for one release. Never infer identity from task index or transcript.

### Task 4: Prove reporting compatibility and recovery identity
- **mode:** A
- **target:** tests/test_m6_reporting.py
- **complexity:** hard
- **executor:** codex
- **role:** test-writer
- **parallel_group:** 4
- **est_tokens:** 2400
- **est_cost_usd:** 0.0720
- **verifier:** .venv/bin/pytest -q tests/test_m6_reporting.py
- **serves:** REQ-22
- **spec:** Cover milestone/package IDs in reports and resume-facing views, legacy reader compatibility, no index-only identity, and bounded output fields.

### Task 5: Record migration ADR and update help language
- **mode:** B
- **target:** .renmark/memory/decisions.md
- **complexity:** medium
- **executor:** haiku
- **role:** docs-editor
- **parallel_group:** 5
- **est_tokens:** 1200
- **est_cost_usd:** 0.0012
- **verifier:** rg -q 'ADR-039' .renmark/memory/decisions.md && rg -q 'supersed' .renmark/memory/decisions.md
- **serves:** REQ-22
- **spec:** Add an explicit ADR superseding ADR-039 after runtime support. Record Agency/Orchestrator as the two public paths, Conductor demoted to internal guided policy, migration compatibility, and rollback constraints. Update help wording only by pointer if needed; do not alter PRD.

### Task 6: Add release-readiness package/install gate
- **mode:** B
- **target:** renmark/release.py
- **complexity:** hard
- **executor:** sonnet
- **role:** release-manager
- **parallel_group:** 6
- **est_tokens:** 3000
- **est_cost_usd:** 0.0390
- **verifier:** .venv/bin/pytest -q tests/test_release_drift.py tests/test_release_snapshot.py
- **serves:** REQ-23, REQ-25
- **spec:** Add deterministic release-readiness checks for version drift, plugin identity, package contents, and installed contract parity. Report blockers only; never tag, publish, or update installations.

### Task 7: Prove release-readiness gates
- **mode:** B
- **target:** tests/test_m6_release_readiness.py
- **complexity:** hard
- **executor:** codex
- **role:** test-writer
- **parallel_group:** 7
- **est_tokens:** 2400
- **est_cost_usd:** 0.0720
- **verifier:** .venv/bin/pytest -q tests/test_m6_release_readiness.py
- **serves:** REQ-23, REQ-25
- **spec:** Test clean package readiness plus version/identity/contract drift failures. Prove all failures block packaging without creating tags, releases, or install mutations.

### Task 8: Document M6 release handoff
- **mode:** B
- **target:** plugin/skills/finish/SKILL.md
- **complexity:** medium
- **executor:** haiku
- **role:** docs-editor
- **parallel_group:** 8
- **est_tokens:** 900
- **est_cost_usd:** 0.0011
- **verifier:** rg -q 'M6\|milestone\|package' plugin/skills/finish/SKILL.md
- **serves:** REQ-22, REQ-25
- **spec:** Document that finish requires clean milestone verification/review, deterministic M6 release-readiness evidence, and explicit owner approval before any merge, tag, release, package, or self-update action. Keep existing lanes and gates intact.

## Milestone gates

- Per package: build → fresh verifier → independent review → scoped repair; max two build repairs and three review cycles.
- Final: `pytest -q`, `ruff check`, `mypy .`, `python -m renmark --behavior`, audit/inventory, release drift, package validation, independent review.
- Stop: host-semantic divergence, golden failure, reporting identity regression, ADR conflict, package/readiness failure, budget expansion, or any release/installation action requiring owner approval.

## Cost preview

| Lane | Tasks | Estimated tokens | Estimated cost |
|---|---:|---:|---:|
| Golden trajectories and reporting | 4 | 21,400 | $0.23 |
| ADR and release-readiness | 4 | 27,500 | $0.16 |
| Independent review / bounded repairs reserve | — | 29,000 | $0.44 |
| **M6 approved cap** | **8** | **77,900** | **$0.83** |

No release is performed by this plan. Package, tag, installation, or publish
actions remain owner-approved finish-lane work after M6 evidence is clean.

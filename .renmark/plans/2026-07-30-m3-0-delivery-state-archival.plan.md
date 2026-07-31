---
artifact_type: milestone_execution_plan
schema_version: 1
created_at: 2026-07-30T17:30:00-04:00
source_sha: 6f7570c
related_plan: .renmark/plans/2026-07-30-m3-milestone-planner-work-packages.plan.md
generator: renmark:orchestrate
completion_state: complete
confidence: high
validation_status: unvalidated
retry_count: 0
parser_success: true
schema_compliance: true
dependency_refs:
  - .renmark/state/delivery.json
---

# M3-0 — Delivery-state archival prerequisite

This amendment is the first M3 work package. It resolves the discovered 4 KB
delivery-state capacity blocker without losing completed M2 boundary evidence.
It stays inside M3's state/schema scope and raises the total estimate to about
57k tokens, still within the approved 45k–70k band.

### Task 1: Archive completed delivery package summaries
- **mode:** B
- **target:** renmark/delivery_state.py
- **complexity:** hard
- **executor:** sonnet
- **role:** code-implementer
- **parallel_group:** 1
- **est_tokens:** 2600
- **est_cost_usd:** 0.0378
- **verifier:** .venv/bin/pytest -q tests/test_delivery_state.py
- **serves:** REQ-5, REQ-22
- **spec:**
  Add an atomic archival/compaction operation for completed work-package
  summaries. Preserve immutable boundary artifact references and provenance in
  a project-local archive, retain active/pending packages in delivery.json,
  and reject any write that still exceeds the 4 KB cap. Never discard failed or
  in-progress package evidence.

### Task 2: Prove archival capacity and recovery behavior
- **mode:** B
- **target:** tests/test_delivery_state.py
- **complexity:** medium
- **executor:** codex
- **role:** test-writer
- **parallel_group:** 2
- **est_tokens:** 1400
- **est_cost_usd:** 0.0420
- **verifier:** .venv/bin/pytest -q tests/test_delivery_state.py
- **serves:** REQ-5, REQ-22
- **spec:**
  Add regression coverage for completed-package archival, active package
  preservation, archive provenance, atomic failed writes, idempotence, and a
  fresh M3 pending package update under the 4 KB cap.

## Cost preview

- 2 tasks in sequence; implementation and its direct tests form one M3-0 package.
- Estimated 14,000 tokens including one Sonnet packet overhead; approximately $0.08.
- No expensive model or destructive action. The archive stays within `.renmark/`.

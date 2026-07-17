---
artifact_type: plan
schema_version: 1
created_at: 2026-07-17T20:07:00Z
source_sha: 17455fb
related_plan: .renmark/plans/2026-07-17-proactive-repeated-issue-monitor.plan.md
generator: renmark:debug
stale_after: null
dependency_refs:
  - .renmark/debug/20260717-200049-c9ee/session.md
  - .renmark/debug/20260717-200049-c9ee/repro.py
completion_state: complete
confidence: high
validation_status: unvalidated
retry_count: 0
parser_success: true
schema_compliance: true
---

# Fix recurrence remediation classification

### Task 1: Classify remediation from the failure kind
- **mode:** B
- **target:** renmark/recurrence.py
- **context_files:** []
- **complexity:** medium
- **executor:** codex
- **role:** code-implementer
- **parallel_group:** 1
- **est_tokens:** 1200
- **est_cost_usd:** 0.0300
- **verifier:** .venv/bin/ruff check renmark/recurrence.py > /dev/null && .venv/bin/mypy renmark/recurrence.py > /dev/null && .venv/bin/python .renmark/debug/20260717-200049-c9ee/repro.py
- **serves:** REQ-24
- **spec:**
  Fix only renmark/recurrence.py; do not touch any other file and do not commit.
  Confirmed root cause: remediation is derived solely from occurrence_count, so every second failure becomes durable_guard even when rule_id identifies a reproducible verifier or executor failure.
  Preserve the existing public API and bounded ledger contract.
  Derive and persist remediation_class from the stable failure kind: verifier-failure and nonzero-executor-exit recommend patch; lane-violation and explicit instruction/contract/workflow failures recommend durable_guard. Unknown implementation/test-like kinds should safely default to patch rather than silently creating a standing instruction.
  Return the stored remediation class from observe, pre-attempt, acknowledge, and resolve decisions instead of recomputing it from count.
  Existing/corrupt ledger entries that lack classification must recover deterministically without raising. Changed fingerprints still start a fresh sequence, raw signals remain unpersisted, and the second equivalent occurrence still blocks an unacknowledged third attempt.
  Make the existing debug repro green and keep Ruff/mypy clean.

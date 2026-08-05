"""
---
artifact_type: pytest-test-module
schema_version: 1
created_at: 2026-08-05T13:04:02Z
source_sha: cb0f960e54489d1ad94611ee3757c22d5713bca0
related_plan: .renmark/plans/2026-08-05-governed-orchestration-assurance-release-8.plan.md
generator: codex
dependency_refs:
  - renmark/ledger.py
  - .renmark/rethink/governed-orchestration-assurance/release-8-risk-tier-spike-finding.md
completion_state: complete
confidence: high
validation_status: unvalidated
retry_count: 0
parser_success: true
schema_compliance: true
---
Risk-tier regression tests for renmark.ledger.
"""

from __future__ import annotations

import pytest

from renmark import ledger


def _make_work_order(file_scope: list[str], *, complexity: str | None = None) -> ledger.WorkOrder:
    order = ledger.WorkOrder(
        order_id="wo-1",
        task="risk-tier probe",
        role="code-implementer",
        file_scope=file_scope,
        verifier="pytest -q tests/test_ledger_risk_tier.py",
    )
    if complexity is not None:
        order.complexity = complexity
    return order


def test_critical_module_classifies_as_high_or_critical() -> None:
    tier = ledger.classify_risk_tier(_make_work_order(["renmark/ledger.py"]))
    assert tier in {"high", "critical"}


@pytest.mark.parametrize("file_scope", [["tests/test_ledger.py"], ["README.md"]])
def test_test_or_doc_only_classifies_low(file_scope: list[str]) -> None:
    assert ledger.classify_risk_tier(_make_work_order(file_scope)) == "low"


def test_none_is_safe_and_returns_a_known_tier() -> None:
    assert ledger.classify_risk_tier(None) in ledger.RISK_TIERS


@pytest.mark.parametrize(
    "work_order",
    [
        ledger.WorkOrder(order_id="wo-empty", task="x", role="code-implementer", file_scope=[]),
        _make_work_order(["tests/test_ledger.py"]),
        _make_work_order(["README.md"]),
        _make_work_order(["renmark/ledger.py"]),
        _make_work_order(["renmark/cost.py"], complexity="hard"),
        _make_work_order(["plugin/skills/.shared/handoff-menu.md"], complexity="medium"),
    ],
)
def test_classify_risk_tier_always_returns_known_tier(work_order: ledger.WorkOrder) -> None:
    assert ledger.classify_risk_tier(work_order) in ledger.RISK_TIERS


def test_verdict_vocabulary_remains_unchanged() -> None:
    assert ledger.VERDICTS == ("pass", "fail", "escalate")


"""
## Summary
- Covered the critical-module boundary with the real ledger classifier output.
- Added low-tier coverage for test-only and doc-only work orders, plus None handling.
- Exercised five-plus varied WorkOrder inputs to keep returns inside RISK_TIERS.
- Guarded VERDICTS so the ledger verdict vocabulary cannot drift in this release.
"""

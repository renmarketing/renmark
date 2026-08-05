"""
---
artifact_type: pytest-test-module
schema_version: 1
created_at: 2026-08-05T00:00:00Z
source_sha: cb0f960e54489d1ad94611ee3757c22d5713bca0
related_plan: .renmark/plans/2026-08-05-governed-orchestration-assurance-release-8.plan.md
generator: codex
dependency_refs:
  - renmark/ledger.py
  - renmark/subagent_gate.py
completion_state: complete
confidence: high
validation_status: validated
retry_count: 0
parser_success: true
schema_compliance: true
---
Inspection-contract construction, validation, and wiring coverage for renmark.ledger.
"""

from __future__ import annotations

from dataclasses import dataclass

from renmark import ledger
from renmark.subagent_gate import LENS_NAMES


@dataclass
class _TaskStub:
    spec: str
    target: str
    context_files: list[str]
    verifier: str
    index: int


def _make_task() -> _TaskStub:
    return _TaskStub(
        spec="verify inspection contract wiring",
        target="renmark/ledger.py",
        context_files=["tests/test_ledger_wiring.py"],
        verifier="pytest -q tests/test_ledger_inspection_contract.py",
        index=1,
    )


def test_inspection_contract_defaults_match_ledger_verdict_vocabulary() -> None:
    contract = ledger.InspectionContract()

    assert contract.contract_id == ""
    assert contract.version == 1
    assert contract.risk_tier is None
    assert contract.lenses == []
    assert contract.deterministic_gates == []
    assert contract.semantic_rubric_ref is None
    assert contract.independent_judge_required is False
    assert contract.evidence_required == []
    assert contract.allowed_verdicts is ledger.VERDICTS


def test_work_order_for_task_auto_populates_inspection_contract() -> None:
    task = _make_task()

    order = ledger.work_order_for_task(task, "code-implementer")

    assert order.inspection_contract is not None
    assert order.inspection_contract.risk_tier == ledger.classify_risk_tier(order)
    assert order.inspection_contract.lenses
    assert any(lens in LENS_NAMES for lens in order.inspection_contract.lenses)


def test_work_order_for_task_auto_contract_false_leaves_default_none() -> None:
    task = _make_task()
    explicit_contract = ledger.InspectionContract(
        contract_id="manual-contract",
        version=2,
        risk_tier="low",
        lenses=["maintainer"],
    )

    order = ledger.work_order_for_task(task, "code-implementer", auto_contract=False)
    explicit_order = ledger.work_order_for_task(
        task,
        "code-implementer",
        auto_contract=False,
        inspection_contract=explicit_contract,
    )

    assert order.inspection_contract is None
    assert explicit_order.inspection_contract is explicit_contract


def test_inspection_report_contract_ref_round_trips_validation() -> None:
    report = ledger.InspectionReport(
        subject_ref="task-1",
        verdict="pass",
        findings=[],
        contract_ref="task-1-contract:1",
    )

    assert ledger.validate_inspection_report(report.__dict__) == []


def test_inspection_contract_allowed_verdicts_defaults_to_verdicts_constant() -> None:
    contract = ledger.InspectionContract()

    assert contract.allowed_verdicts is ledger.VERDICTS
    assert contract.allowed_verdicts == ledger.VERDICTS


"""
## Summary
- Covered InspectionContract defaults, including the shared VERDICTS tuple.
- Verified work_order_for_task auto-populates a contract with matching tier and a known lens.
- Confirmed auto_contract=False preserves the None default and honors an explicit contract.
- Proved InspectionReport.contract_ref validates cleanly with the existing report validator.
"""

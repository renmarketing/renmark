"""
---
artifact_type: pytest-test-module
schema_version: 1
created_at: 2026-08-05T00:00:00Z
source_sha: 213ce5d3d6aad04c2c8dfb3e2915fccd73b457b1
related_plan: Task 4: Ledger field + backward-compat tests
generator: codex
dependency_refs:
  - renmark/ledger.py
completion_state: complete
confidence: high
validation_status: validated
retry_count: 0
parser_success: true
schema_compliance: true
---
Ledger field completeness, append/read round-trip, and backward-compatibility coverage.
"""

from __future__ import annotations

import json
from dataclasses import fields
from pathlib import Path

import pytest

from renmark import ledger


def _identity_field_names(event_type: type[object]) -> set[str]:
    return {field.name for field in fields(event_type)}


@pytest.mark.parametrize(
    ("event_type", "kwargs"),
    [
        (
            ledger.WorkOrder,
            {
                "order_id": "wo-1",
                "task": "assemble ledger tests",
                "role": "code-implementer",
            },
        ),
        (
            ledger.WorkResult,
            {
                "order_id": "wo-1",
                "status": "complete",
            },
        ),
        (
            ledger.InspectionReport,
            {
                "subject_ref": "wo-1",
                "verdict": "pass",
            },
        ),
        (
            ledger.Escalation,
            {
                "reason": "blocked on missing data",
                "originating_skill": "debug",
                "blocking": True,
            },
        ),
    ],
)
def test_default_construction_exposes_identity_fields(
    event_type: type[object], kwargs: dict[str, object]
) -> None:
    event = event_type(**kwargs)  # type: ignore[misc]
    field_names = _identity_field_names(event_type)

    for name in ("schema_version", "attempt_id", "correlation_id"):
        assert name in field_names
        assert hasattr(event, name)
        getattr(event, name)


@pytest.mark.parametrize(
    ("event", "kind", "attempt_id", "correlation_id"),
    [
        (
            ledger.WorkResult(
                order_id="wo-2",
                status="complete",
                summary="finished",
                attempt_id="attempt-work-result",
                correlation_id="corr-work-result",
            ),
            ledger.KIND_WORK_RESULT,
            "attempt-work-result",
            "corr-work-result",
        ),
        (
            ledger.InspectionReport(
                subject_ref="wo-2",
                verdict="pass",
                findings=[],
                attempt_id="attempt-inspection",
                correlation_id="corr-inspection",
            ),
            ledger.KIND_INSPECTION_REPORT,
            "attempt-inspection",
            "corr-inspection",
        ),
        (
            ledger.Escalation(
                reason="needs human review",
                originating_skill="finish",
                blocking=True,
                attempt_id="attempt-escalation",
                correlation_id="corr-escalation",
            ),
            ledger.KIND_ESCALATION,
            "attempt-escalation",
            "corr-escalation",
        ),
    ],
)
def test_append_and_read_round_trip_preserves_identity_fields(
    tmp_path: Path,
    event: object,
    kind: str,
    attempt_id: str,
    correlation_id: str,
) -> None:
    ledger.append_ledger_event(tmp_path, event, ts="2026-08-05T00:00:00+00:00")

    events = ledger.read_ledger_events(tmp_path, kind=kind)
    assert len(events) == 1

    payload = events[0]
    assert payload["attempt_id"] == attempt_id
    assert payload["correlation_id"] == correlation_id


@pytest.mark.parametrize(
    ("kind", "payload"),
    [
        (
            ledger.KIND_WORK_RESULT,
            {
                "kind": ledger.KIND_WORK_RESULT,
                "ts": "2026-08-05T00:00:00+00:00",
                "order_id": "wo-old-1",
                "status": "complete",
                "summary": "legacy row",
            },
        ),
        (
            ledger.KIND_INSPECTION_REPORT,
            {
                "kind": ledger.KIND_INSPECTION_REPORT,
                "ts": "2026-08-05T00:00:01+00:00",
                "subject_ref": "wo-old-1",
                "verdict": "pass",
                "findings": [],
            },
        ),
        (
            ledger.KIND_ESCALATION,
            {
                "kind": ledger.KIND_ESCALATION,
                "ts": "2026-08-05T00:00:02+00:00",
                "reason": "legacy escalation",
                "originating_skill": "debug",
                "blocking": True,
            },
        ),
    ],
)
def test_read_ledger_events_accepts_old_shape_jsonl(
    tmp_path: Path, kind: str, payload: dict[str, object]
) -> None:
    ledger_dir = tmp_path / ".renmark" / "ledger"
    ledger_dir.mkdir(parents=True, exist_ok=True)
    (ledger_dir / "events.jsonl").write_text(f"{json.dumps(payload)}\n", encoding="utf-8")

    events = ledger.read_ledger_events(tmp_path, kind=kind)
    assert len(events) == 1

    parsed = events[0]
    assert parsed["kind"] == kind
    assert "schema_version" not in parsed
    assert "attempt_id" not in parsed
    assert "correlation_id" not in parsed


def test_ledger_vocabularies_remain_unchanged() -> None:
    assert ledger.VERDICTS == ("pass", "fail", "escalate")
    assert ledger.RISK_TIERS == ("low", "medium", "high", "critical")


"""
## Summary
- Added default-construction coverage for WorkOrder, WorkResult, InspectionReport, and Escalation.
- Proved schema_version, attempt_id, and correlation_id are present on each dataclass.
- Verified explicit attempt_id/correlation_id values survive append/read round-trips.
- Added backward-compatibility coverage for old-shape JSONL rows with missing identity fields.
- Guarded VERDICTS and RISK_TIERS against release drift.
"""

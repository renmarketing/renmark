"""Unit tests for renmark.ledger (R-0.3 WP-1/WP-2/WP-3)."""

from __future__ import annotations

from pathlib import Path

import pytest

from renmark import ledger


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    return tmp_path


# ── Happy-path validation per kind ───────────────────────────────────────


def test_validate_work_order_happy_path() -> None:
    event = ledger.WorkOrder(
        order_id="wo-1",
        task="implement ledger",
        role="code-implementer",
        file_scope=["renmark/ledger.py"],
        verifier="pytest tests/test_ledger.py -q",
    )
    from dataclasses import asdict

    assert ledger.validate_work_order(asdict(event)) == []


def test_validate_work_result_happy_path() -> None:
    from dataclasses import asdict

    event = ledger.WorkResult(
        order_id="wo-1",
        status="complete",
        summary="done",
        touched_files=["renmark/ledger.py"],
        artifact_refs=[],
    )
    assert ledger.validate_work_result(asdict(event)) == []


def test_validate_inspection_report_happy_path() -> None:
    from dataclasses import asdict

    event = ledger.InspectionReport(
        subject_ref="wo-1",
        verdict="pass",
        findings=[],
        generator="codereview",
    )
    assert ledger.validate_inspection_report(asdict(event)) == []


def test_validate_escalation_happy_path() -> None:
    from dataclasses import asdict

    event = ledger.Escalation(
        reason="blocked on missing credentials",
        originating_skill="orchestrate",
        blocking=True,
    )
    assert ledger.validate_escalation(asdict(event)) == []


def test_escalation_replannable_variant_validates() -> None:
    from dataclasses import asdict

    event = ledger.Escalation(
        reason="ambiguous scope",
        originating_skill="orchestrate",
        blocking=False,
        is_replannable=True,
        replan_evidence="see .renmark/plans/x.plan.md",
    )
    assert ledger.validate_escalation(asdict(event)) == []


def test_work_order_repair_variant_validates() -> None:
    from dataclasses import asdict

    event = ledger.WorkOrder(
        order_id="wo-2",
        task="repair failing test",
        role="code-implementer",
        is_repair=True,
        repairs_finding_ref=".renmark/reviews/2026-08-01-x.review.json#finding-1",
    )
    assert ledger.validate_work_order(asdict(event)) == []


# ── Malformed-input rejection (>= 2 kinds) ───────────────────────────────


def test_validate_work_order_rejects_missing_required_field() -> None:
    issues = ledger.validate_work_order({"order_id": "wo-1", "role": "worker"})
    assert issues  # missing 'task'


def test_validate_work_order_rejects_wrong_type() -> None:
    issues = ledger.validate_work_order(
        {"order_id": "wo-1", "task": "x", "role": "worker", "file_scope": "not-a-list"}
    )
    assert issues


def test_validate_escalation_rejects_missing_reason() -> None:
    issues = ledger.validate_escalation({"blocking": True})
    assert issues


def test_validate_inspection_report_rejects_bad_findings_type() -> None:
    issues = ledger.validate_inspection_report(
        {"subject_ref": "x", "verdict": "pass", "findings": "not-a-list"}
    )
    assert issues


def test_append_ledger_event_rejects_malformed_work_result(repo: Path) -> None:
    # Missing required 'status' field — simulate by hand-building an invalid
    # payload through validate_work_result directly, then confirming append
    # raises for an event whose dataclass field was blanked incorrectly.
    bad_event = ledger.WorkResult(order_id="", status="complete")
    with pytest.raises(ledger.LedgerValidationError):
        ledger.append_ledger_event(repo, bad_event, ts="2026-08-01T00:00:00+00:00")
    # No partial line written.
    assert not ledger.ledger_path(repo).exists()


def test_append_ledger_event_rejects_empty_ts(repo: Path) -> None:
    event = ledger.WorkOrder(order_id="wo-1", task="x", role="worker")
    with pytest.raises(ledger.LedgerValidationError):
        ledger.append_ledger_event(repo, event, ts="")
    assert not ledger.ledger_path(repo).exists()


# ── Append-then-read round-trip ──────────────────────────────────────────


def test_append_then_read_round_trip(repo: Path) -> None:
    order = ledger.WorkOrder(order_id="wo-1", task="build thing", role="code-implementer")
    ledger.append_ledger_event(repo, order, ts="2026-08-01T00:00:00+00:00")

    result = ledger.WorkResult(order_id="wo-1", status="complete", summary="built it")
    ledger.append_ledger_event(repo, result, ts="2026-08-01T00:05:00+00:00")

    events = ledger.read_ledger_events(repo)
    assert len(events) == 2
    assert events[0]["kind"] == "work_order"
    assert events[0]["order_id"] == "wo-1"
    assert events[0]["ts"] == "2026-08-01T00:00:00+00:00"
    assert events[1]["kind"] == "work_result"
    assert events[1]["status"] == "complete"

    # File is genuinely append-only JSONL.
    lines = ledger.ledger_path(repo).read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2


def test_read_ledger_events_kind_filter(repo: Path) -> None:
    ledger.append_ledger_event(
        repo, ledger.WorkOrder(order_id="wo-1", task="a", role="worker"), ts="t1"
    )
    ledger.append_ledger_event(
        repo, ledger.Escalation(reason="blocked"), ts="t2"
    )
    ledger.append_ledger_event(
        repo, ledger.WorkOrder(order_id="wo-2", task="b", role="worker"), ts="t3"
    )

    only_orders = ledger.read_ledger_events(repo, kind="work_order")
    assert len(only_orders) == 2
    assert all(e["kind"] == "work_order" for e in only_orders)

    only_escalations = ledger.read_ledger_events(repo, kind="escalation")
    assert len(only_escalations) == 1
    assert only_escalations[0]["reason"] == "blocked"


def test_read_ledger_events_limit(repo: Path) -> None:
    for i in range(5):
        ledger.append_ledger_event(
            repo,
            ledger.WorkOrder(order_id=f"wo-{i}", task="x", role="worker"),
            ts=f"t{i}",
        )
    last_two = ledger.read_ledger_events(repo, limit=2)
    assert len(last_two) == 2
    assert [e["order_id"] for e in last_two] == ["wo-3", "wo-4"]


def test_read_ledger_events_missing_file_returns_empty(repo: Path) -> None:
    assert ledger.read_ledger_events(repo) == []
    assert ledger.read_ledger_events(repo, kind="work_order") == []
    assert ledger.read_ledger_events(repo, limit=5) == []

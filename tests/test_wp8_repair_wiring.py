"""Tests for R-0.2 WP-8c: wiring `build_repair_work_order` to a logged ledger.

Covers closeout follow-up F2: `record_repair_work_order` must append a
correctly-shaped provenance event via the existing `append_provenance_event`
mechanism (no parallel ledger), preserve prior events, and round-trip
through `write_delivery_state` / `read_delivery_state_with_report`.
"""

from __future__ import annotations

from pathlib import Path

from renmark import delivery_state, dispatch, fast_path
from renmark.delivery_state import (
    DeliveryProvenanceEvent,
    DeliveryState,
    read_delivery_state_with_report,
    record_repair_work_order,
    write_delivery_state,
)


def _sample_work_order() -> dispatch.RepairWorkOrder:
    finding = dispatch.InspectorFinding(
        finding_id="F-100",
        source_file=".renmark/reviews/2026-08-01-example.review.md",
        verdict="FAIL",
        severity="major",
        target="renmark/example.py",
        title="broken invariant",
    )
    order = dispatch.build_repair_work_order(finding, work_order_id="WO-100")
    assert order is not None
    return order


def test_record_repair_work_order_appends_correctly_shaped_event() -> None:
    state = DeliveryState()
    order = _sample_work_order()

    updated = record_repair_work_order(state, order, ts="2026-08-01T00:00:00+00:00")

    assert len(updated.provenance_events) == 1
    event = updated.provenance_events[0]
    assert isinstance(event, DeliveryProvenanceEvent)
    assert event.kind == "repair-work-order-created"
    assert event.ts == "2026-08-01T00:00:00+00:00"
    # Pointer to the source finding, not the finding body.
    assert event.ref == ".renmark/reviews/2026-08-01-example.review.md#F-100"
    assert "WO-100" in event.detail
    assert event.source == "dispatch.build_repair_work_order"


def test_record_repair_work_order_defaults_timestamp_when_omitted() -> None:
    state = DeliveryState()
    order = _sample_work_order()

    updated = record_repair_work_order(state, order)

    assert updated.provenance_events[0].ts != ""


def test_record_repair_work_order_preserves_existing_events() -> None:
    state = delivery_state.append_provenance_event(
        DeliveryState(),
        ts="2026-07-31T00:00:00+00:00",
        kind="created",
        detail="Delivery loop started",
        source="test",
        ref="evt-1",
    )
    order = _sample_work_order()

    updated = record_repair_work_order(state, order, ts="2026-08-01T00:00:00+00:00")

    assert len(updated.provenance_events) == 2
    assert updated.provenance_events[0].kind == "created"
    assert updated.provenance_events[0].ref == "evt-1"
    assert updated.provenance_events[1].kind == "repair-work-order-created"


def test_record_repair_work_order_round_trips_through_write_and_read(tmp_path: Path) -> None:
    state = DeliveryState()
    order = _sample_work_order()
    updated = record_repair_work_order(state, order, ts="2026-08-01T00:00:00+00:00")

    write_delivery_state(tmp_path, updated)
    read_back, report = read_delivery_state_with_report(tmp_path)

    assert report.state == "loaded"
    assert len(read_back.provenance_events) == 1
    event = read_back.provenance_events[0]
    assert event.kind == "repair-work-order-created"
    assert event.ref == ".renmark/reviews/2026-08-01-example.review.md#F-100"
    assert "WO-100" in event.detail


def test_record_repair_work_order_accepts_critical_severity() -> None:
    finding = dispatch.InspectorFinding(
        finding_id="F-101",
        source_file=".renmark/reviews/2026-08-01-critical.review.md",
        verdict="FAIL",
        severity="critical",
        target="renmark/critical.py",
    )
    order = dispatch.build_repair_work_order(finding, work_order_id="WO-101")
    assert order is not None
    assert isinstance(order.scope, fast_path.WorkerScope)

    updated = record_repair_work_order(DeliveryState(), order, ts="2026-08-01T00:00:00+00:00")

    assert "critical" in updated.provenance_events[0].detail

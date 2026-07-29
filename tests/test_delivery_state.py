"""Unit tests for renmark.delivery_state."""

from __future__ import annotations

from pathlib import Path

import pytest

from renmark import delivery_state
from renmark.delivery_state import (
    PROVENANCE_EVENT_CAP,
    DeliveryProvenanceEvent,
    DeliveryReadReport,
    DeliveryState,
    DeliveryStateBloatError,
    WorkPackageSummary,
    append_provenance_event,
    bounded_provenance_lines,
    bounded_work_package_summaries,
    read_delivery_state,
    read_delivery_state_with_report,
    stable_milestone_id,
    stable_work_package_id,
    write_delivery_state,
)


def _sample_state() -> DeliveryState:
    return DeliveryState(
        schema_version=7,
        run_id="delivery-abc123",
        delivery_mode="agency",
        execution_policy="async",
        active_milestone_id="Milestone One",
        work_packages=[
            WorkPackageSummary(
                package_id="",
                milestone_id="Milestone One",
                title="Draft spec",
                status="in_progress",
                summary="Need tighter acceptance criteria.",
                owner="owner",
                updated_at="2026-07-29T10:00:00Z",
                artifact_ref=".renmark/specs/delivery.md",
            )
        ],
        approval_status="pending",
        review_status="approved",
        verification_status="passed",
        loop_status="blocked",
        contract_version="delivery-state/v7",
        source_sha="abc123",
        provenance_events=[
            DeliveryProvenanceEvent(
                ts="2026-07-29T10:00:00Z",
                kind="created",
                detail="Delivery loop started",
                source="test",
                ref="evt-1",
            )
        ],
        legacy_refs=["legacy/ref-1"],
    )


def test_missing_state_returns_default_and_missing_report(tmp_path: Path) -> None:
    state, report = read_delivery_state_with_report(tmp_path)

    assert state.delivery_mode == "orchestrator"
    assert state.execution_policy == "guided"
    assert state.active_milestone_id == ""
    assert state.work_packages == []
    assert state.provenance_events == []
    assert state.legacy_refs == []
    assert state.run_id.startswith("delivery-")
    assert report == DeliveryReadReport(
        state="missing",
        path=str(delivery_state.delivery_state_path(tmp_path)),
        detail="delivery state file is absent",
    )
    fresh = read_delivery_state(tmp_path)
    assert fresh.delivery_mode == "orchestrator"
    assert fresh.execution_policy == "guided"
    assert fresh.run_id.startswith("delivery-")


def test_write_read_round_trip_preserves_schema_version(tmp_path: Path) -> None:
    state = _sample_state()

    path = write_delivery_state(tmp_path, state)
    loaded, report = read_delivery_state_with_report(tmp_path)

    assert path == delivery_state.delivery_state_path(tmp_path)
    assert loaded.schema_version == 7
    assert loaded.run_id == state.run_id
    assert loaded.delivery_mode == "agency"
    assert loaded.execution_policy == "async"
    assert loaded.active_milestone_id == "milestone-one"
    assert loaded.approval_status == "pending"
    assert loaded.review_status == "approved"
    assert loaded.verification_status == "passed"
    assert loaded.loop_status == "blocked"
    assert loaded.contract_version == "delivery-state/v7"
    assert loaded.source_sha == "abc123"
    assert loaded.legacy_refs == ["legacy/ref-1"]
    assert len(loaded.work_packages) == 1
    assert loaded.work_packages[0].package_id == "milestone-one--draft-spec"
    assert loaded.provenance_events[0].kind == "created"
    assert report.state == "loaded"
    assert report.path == str(path)


def test_invalid_public_modes_repair_to_supported_values() -> None:
    state = DeliveryState(
        delivery_mode="not-public",
        execution_policy="not-supported",
    )

    assert state.delivery_mode == "orchestrator"
    assert state.execution_policy == "guided"


def test_legacy_conductor_mapping_normalizes_to_guided_policy() -> None:
    state = DeliveryState(
        delivery_mode="conductor",
        execution_policy="conductor",
    )

    assert state.delivery_mode == "orchestrator"
    assert state.execution_policy == "guided"


def test_stable_ids_use_slugged_bounded_format() -> None:
    milestone_id = stable_milestone_id("  Launch Week / Phase #1  ")
    package_id = stable_work_package_id("  Launch Week / Phase #1  ", "QA + Demo / Owner Signoff")

    assert milestone_id == "launch-week-phase-1"
    assert package_id == "launch-week-phase-1--qa-demo-owner-signoff"
    assert len(milestone_id) <= 48
    assert "--" in package_id


def test_append_provenance_event_keeps_latest_events_within_cap() -> None:
    state = DeliveryState()

    for index in range(PROVENANCE_EVENT_CAP + 5):
        state = append_provenance_event(
            state,
            ts=f"2026-07-29T10:{index:02d}:00Z",
            kind=f"kind-{index}",
            detail=f"detail {index}\nwith extra whitespace",
            source="test-suite",
            ref=f"ref-{index}",
        )

    assert len(state.provenance_events) == PROVENANCE_EVENT_CAP
    assert state.provenance_events[0].kind == "kind-5"
    assert state.provenance_events[-1].kind == f"kind-{PROVENANCE_EVENT_CAP + 4}"
    assert "\n" not in state.provenance_events[-1].detail


def test_write_rejects_bloated_state(tmp_path: Path) -> None:
    state = DeliveryState(
        provenance_events=[
            DeliveryProvenanceEvent(
                ts=f"2026-07-29T10:{index:02d}:00Z",
                kind=f"kind-{index}",
                detail="x" * 120,
                source="source" * 8,
                ref="ref" * 24,
            )
            for index in range(PROVENANCE_EVENT_CAP)
        ]
    )

    with pytest.raises(DeliveryStateBloatError):
        write_delivery_state(tmp_path, state)


def test_bounded_summary_helpers_return_capped_clean_output() -> None:
    state = DeliveryState(
        work_packages=[
            WorkPackageSummary(
                milestone_id="Milestone A",
                title="Package one",
                status="passed",
                summary="First summary\nwith whitespace",
            ),
            WorkPackageSummary(
                milestone_id="Milestone A",
                title="Package two",
                status="blocked",
                summary="Second summary",
            ),
            WorkPackageSummary(
                milestone_id="Milestone A",
                title="Package three",
                status="pending",
                summary="Third summary",
            ),
        ],
        provenance_events=[
            DeliveryProvenanceEvent(
                ts="2026-07-29T10:00:00Z",
                kind="created",
                detail="Started\ncleanly",
            ),
            DeliveryProvenanceEvent(
                ts="2026-07-29T10:05:00Z",
                kind="updated",
                detail="Added work package",
            ),
            DeliveryProvenanceEvent(
                ts="2026-07-29T10:10:00Z",
                kind="verified",
                detail="Passed checks",
            ),
        ],
    )

    work_lines = bounded_work_package_summaries(state, limit=2)
    provenance_lines = bounded_provenance_lines(state, limit=2)

    assert work_lines == [
        "milestone-a--package-one:passed First summary with whitespace",
        "milestone-a--package-two:blocked Second summary",
    ]
    assert provenance_lines == [
        "2026-07-29T10:00:00Z | created | Started cleanly",
        "2026-07-29T10:05:00Z | updated | Added work package",
    ]

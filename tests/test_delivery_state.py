"""Unit tests for renmark.delivery_state."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from renmark import delivery_state, schemas
from renmark.delivery_state import (
    DELIVERY_JSON_BYTE_BUDGET,
    PROVENANCE_EVENT_CAP,
    DeliveryProvenanceEvent,
    DeliveryReadReport,
    DeliveryState,
    DeliveryStateBloatError,
    WorkPackageSummary,
    append_provenance_event,
    archive_completed_work_packages,
    bounded_provenance_lines,
    bounded_work_package_summaries,
    delivery_archive_path,
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


def test_write_read_round_trip_canonicalizes_schema_metadata(tmp_path: Path) -> None:
    state = _sample_state()

    path = write_delivery_state(tmp_path, state)
    loaded, report = read_delivery_state_with_report(tmp_path)

    assert path == delivery_state.delivery_state_path(tmp_path)
    assert loaded.schema_version == delivery_state.SCHEMA_VERSION
    assert loaded.run_id == state.run_id
    assert loaded.delivery_mode == "agency"
    assert loaded.execution_policy == "async"
    assert loaded.active_milestone_id == "milestone-one"
    assert loaded.approval_status == "pending"
    assert loaded.review_status == "approved"
    assert loaded.verification_status == "passed"
    assert loaded.loop_status == "blocked"
    assert loaded.contract_version == delivery_state.CONTRACT_VERSION
    assert loaded.source_sha == "abc123"
    assert loaded.legacy_refs == ["legacy/ref-1"]
    assert len(loaded.work_packages) == 1
    assert loaded.work_packages[0].package_id == "milestone-one--draft-spec"
    assert loaded.provenance_events[0].kind == "created"
    assert report.state == "loaded"
    assert report.path == str(path)


def test_delivery_state_output_satisfies_canonical_validator() -> None:
    state = DeliveryState(
        schema_version=7,
        contract_version="delivery-state/v7",
        run_id="delivery-abc123",
    )

    assert state.schema_version == delivery_state.SCHEMA_VERSION
    assert state.contract_version == delivery_state.CONTRACT_VERSION
    assert state.run_id.startswith("delivery-")
    assert len(state.run_id) == len("delivery-") + 12
    assert schemas.validate_delivery_state(state.to_dict()) == []


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

    # The count cap is an upper bound, not a target — the byte-budget trim
    # (see test_append_provenance_event_trims_by_byte_budget_not_just_count)
    # can and does keep fewer than PROVENANCE_EVENT_CAP events for this
    # detail size. What must hold: never exceed the cap, always keep the
    # most recent contiguous suffix, and always fit the byte budget.
    assert len(state.provenance_events) <= PROVENANCE_EVENT_CAP
    assert state.provenance_events[-1].kind == f"kind-{PROVENANCE_EVENT_CAP + 4}"
    assert "\n" not in state.provenance_events[-1].detail
    assert len(state.to_json().encode("utf-8")) <= DELIVERY_JSON_BYTE_BUDGET


def test_append_provenance_event_trims_by_byte_budget_not_just_count() -> None:
    """Long-detail events can bloat past the byte budget well under the
    count cap (observed 2026-08-02: 18 events, 5876 bytes vs. 4096 budget).
    append_provenance_event must self-trim by size, keeping the most recent
    events, mirroring the count-cap's keep-most-recent semantics.
    """
    state = DeliveryState()

    # Each event's detail is long enough that far fewer than PROVENANCE_EVENT_CAP
    # of them will exceed the byte budget.
    for index in range(PROVENANCE_EVENT_CAP):
        state = append_provenance_event(
            state,
            ts=f"2026-08-02T10:{index:02d}:00Z",
            kind=f"kind-{index}",
            detail="x" * 100,
            source="source-suite",
            ref=f"ref-{index}",
        )

    assert len(state.to_json().encode("utf-8")) <= DELIVERY_JSON_BYTE_BUDGET
    # Trimmed below the count cap by size, not just by PROVENANCE_EVENT_CAP.
    assert len(state.provenance_events) < PROVENANCE_EVENT_CAP
    # Kept the most recent event, dropped the oldest.
    assert state.provenance_events[-1].kind == f"kind-{PROVENANCE_EVENT_CAP - 1}"
    assert state.provenance_events[0].kind != "kind-0"


def test_append_provenance_event_trimmed_state_writes_without_bloat_error(
    tmp_path: Path,
) -> None:
    """A state that append_provenance_event trimmed by size must actually be
    writable — the trim exists precisely so write_delivery_state never has
    to raise DeliveryStateBloatError on organically-accumulated history."""
    state = DeliveryState()
    for index in range(PROVENANCE_EVENT_CAP):
        state = append_provenance_event(
            state,
            ts=f"2026-08-02T10:{index:02d}:00Z",
            kind=f"kind-{index}",
            detail="x" * 100,
            source="source-suite",
            ref=f"ref-{index}",
        )

    write_delivery_state(tmp_path, state)  # must not raise


def test_append_provenance_event_minimal_details_hit_count_cap_not_byte_trim() -> None:
    """Regression guard: with truly minimal per-event content, the existing
    count cap is still the binding constraint — the byte trim only bites
    when accumulated detail text is long enough to matter, it doesn't fire
    early against ordinary short events.
    """
    state = DeliveryState()

    for _index in range(PROVENANCE_EVENT_CAP + 5):
        state = append_provenance_event(
            state,
            ts="",
            kind="k",
            detail="",
            source="",
            ref="",
        )

    assert len(state.provenance_events) == PROVENANCE_EVENT_CAP
    assert len(state.to_json().encode("utf-8")) <= DELIVERY_JSON_BYTE_BUDGET


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


def test_archive_completed_packages_preserves_active_evidence_and_provenance(
    tmp_path: Path,
) -> None:
    state = DeliveryState(
        run_id="delivery-abc123def456",
        work_packages=[
            WorkPackageSummary(
                milestone_id="M2",
                title="Completed boundary",
                status="passed",
                summary="Immutable completion evidence",
                artifact_ref=".renmark/reviews/m2.json",
                updated_at="2026-07-30T12:00:00Z",
            ),
            *[
                WorkPackageSummary(milestone_id="M3", title=status, status=status)
                for status in ("pending", "in_progress", "failed", "blocked")
            ],
        ],
    )

    archived = archive_completed_work_packages(tmp_path, state)
    archive_payload = json.loads(delivery_archive_path(tmp_path).read_text(encoding="utf-8"))

    assert [package.status for package in archived.work_packages] == [
        "pending",
        "in_progress",
        "failed",
        "blocked",
    ]
    assert archive_payload["work_packages"] == [
        {
            "package_id": "m2--completed-boundary",
            "milestone_id": "m2",
            "run_id": "delivery-abc123def456",
            "artifact_ref": ".renmark/reviews/m2.json",
            "updated_at": "2026-07-30T12:00:00Z",
            "summary": {
                "package_id": "m2--completed-boundary",
                "milestone_id": "m2",
                "title": "Completed boundary",
                "status": "passed",
                "summary": "Immutable completion evidence",
                "owner": "",
                "updated_at": "2026-07-30T12:00:00Z",
                "artifact_ref": ".renmark/reviews/m2.json",
            },
        }
    ]
    assert archived.provenance_events[-1].kind == "work_packages_archived"
    assert archived.provenance_events[-1].ref == ".renmark/state/delivery-archive.json"


def test_archive_is_idempotent_and_restores_capacity_for_fresh_m3_package(tmp_path: Path) -> None:
    archived = archive_completed_work_packages(
        tmp_path,
        DeliveryState(
            work_packages=[
                WorkPackageSummary(milestone_id="M2", title="Passed", status="passed"),
                WorkPackageSummary(milestone_id="M3", title="Active", status="in_progress"),
            ]
        ),
    )
    archive_path = delivery_archive_path(tmp_path)
    first_archive = archive_path.read_text(encoding="utf-8")

    repeated = archive_completed_work_packages(tmp_path, archived)
    repeated_archive = archive_path.read_text(encoding="utf-8")
    repeated.work_packages.append(
        WorkPackageSummary(milestone_id="M3", title="Fresh pending package", status="pending")
    )
    state_path = write_delivery_state(tmp_path, repeated)

    assert repeated_archive == first_archive
    assert len(repeated.provenance_events) == 1
    assert state_path.stat().st_size <= delivery_state.DELIVERY_JSON_BYTE_BUDGET
    assert [item.status for item in read_delivery_state(tmp_path).work_packages] == [
        "in_progress",
        "pending",
    ]


def test_archive_trims_stale_provenance_instead_of_rejecting(tmp_path: Path) -> None:
    """A state that's oversized ONLY because of accumulated provenance history
    (not because of the work_packages content itself) now archives
    successfully — append_provenance_event's byte-budget trim (see above)
    drops enough stale history to fit, rather than blocking a legitimate
    archive of completed work. This supersedes the old hard-reject
    expectation: silently discarding recoverable provenance history (it
    remains in CHANGELOG.md / .renmark/reviews/) is preferable to permanently
    blocking archival on organic history growth.
    """
    oversized = DeliveryState(
        work_packages=[WorkPackageSummary(milestone_id="M2", title="Passed", status="passed")],
        provenance_events=[
            DeliveryProvenanceEvent(
                ts=f"2026-07-30T12:{index:02d}:00Z",
                kind="event" * 8,
                detail="x" * 120,
                source="source" * 8,
                ref="ref" * 24,
            )
            for index in range(PROVENANCE_EVENT_CAP)
        ],
    )

    result = archive_completed_work_packages(tmp_path, oversized)

    assert len(result.to_json().encode("utf-8")) <= DELIVERY_JSON_BYTE_BUDGET
    assert result.work_packages == []  # the one passed package was archived out
    assert delivery_archive_path(tmp_path).exists()


def test_archive_still_rejects_oversize_from_work_packages_themselves(tmp_path: Path) -> None:
    """Provenance trimming can't fix bloat caused by the RETAINED (non-passed)
    work_packages content itself — that still fails loud, with no partial
    state or archive write, exactly as before.
    """
    baseline = DeliveryState(work_packages=[WorkPackageSummary(milestone_id="M3", title="Pending")])
    state_path = write_delivery_state(tmp_path, baseline)
    original_state = state_path.read_text(encoding="utf-8")
    oversized = DeliveryState(
        work_packages=[
            WorkPackageSummary(
                milestone_id=f"M{index}",
                title="Passed",
                status="passed",
                summary="s" * 160,
            )
            for index in range(20)
        ]
        + [
            WorkPackageSummary(
                milestone_id=f"P{index}",
                title="Pending",
                status="pending",
                summary="p" * 160,
            )
            for index in range(20)
        ],
    )

    with pytest.raises(DeliveryStateBloatError):
        archive_completed_work_packages(tmp_path, oversized)

    assert state_path.read_text(encoding="utf-8") == original_state
    assert not delivery_archive_path(tmp_path).exists()

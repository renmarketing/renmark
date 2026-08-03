"""---
artifact_type: renmark_task_output
schema_version: 1
created_at: 2026-07-02T21:25:31Z
source_sha: 1ed4e59
related_plan: "Task 14: agency state tests"
generator: codex
stale_after: null
dependency_refs:
  - renmark/agency.py
  - tests/test_lifecycle.py
---
Agency-state persistence tests for REQ-22 and AC9. The module verifies that
agency.json remains safely resumable: reads never raise on missing or corrupt
state, activation/deactivation preserve the expected active flag semantics, and
oversize writes fail with the dedicated bloat error instead of silently
persisting invalid runtime state.

## Summary
- Covers write/read round-trip and fresh-call resumability.
- Proves missing or corrupt state reads back as inactive without raising.
- Verifies `is_active`, `activate`, and `deactivate` behavior.
- Guards the 1 KB agency-state budget with `AgencyBloatError`.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from renmark.agency import (
    AgencyBloatError,
    AgencyState,
    activate,
    agency_state_path,
    agency_to_delivery_state,
    approve_milestone_for_orchestrator,
    current_agency_to_delivery_state,
    deactivate,
    is_active,
    project_agency_state,
    read_agency,
    write_agency,
)


def test_missing_state_reads_as_inactive_default(tmp_path: Path) -> None:
    """Absent agency.json must deserialize to the inactive default state."""
    assert read_agency(tmp_path) == AgencyState()
    assert is_active(tmp_path) is False


def test_write_read_round_trip_is_resumable_across_fresh_calls(tmp_path: Path) -> None:
    """State written once must be read back unchanged by later fresh reads."""
    state = AgencyState(
        active=True,
        current_phase="discovery",
        current_milestone="M1",
        next_checkpoint="owner-signoff",
        signoff_status="pending",
        cost_lane="balanced",
        roadmap_ref=".renmark/plans/agency.md",
    )

    write_agency(tmp_path, state)

    assert read_agency(tmp_path) == state
    # Fresh call proves resumability from persisted disk state, not in-memory state.
    assert read_agency(tmp_path) == state


def test_corrupt_json_is_treated_as_inactive_without_raising(tmp_path: Path) -> None:
    """Corrupt agency.json must fall back to the inactive default state."""
    path = agency_state_path(tmp_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{not valid json", encoding="utf-8")

    assert read_agency(tmp_path) == AgencyState()
    assert is_active(tmp_path) is False


def test_activate_and_deactivate_toggle_active_flag_correctly(tmp_path: Path) -> None:
    """activate() sets active=True; deactivate() flips it back to False."""
    activated = activate(
        tmp_path,
        current_phase="delivery",
        current_milestone="M2",
        next_checkpoint="demo",
    )
    assert activated.active is True
    assert activated.current_phase == "delivery"
    assert activated.current_milestone == "M2"
    assert is_active(tmp_path) is True

    deactivated = deactivate(tmp_path)
    assert deactivated.active is False
    # deactivate() preserves the rest of the persisted fields.
    assert deactivated.current_phase == "delivery"
    assert deactivated.current_milestone == "M2"
    assert read_agency(tmp_path) == deactivated
    assert is_active(tmp_path) is False


def test_approved_activation_hands_off_milestone_to_orchestrator(tmp_path: Path) -> None:
    """Approved Agency activation persists the canonical delivery handoff."""
    from renmark import delivery_state, lifecycle

    activate(
        tmp_path,
        current_phase="build",
        current_milestone="M6",
        signoff_status="approved",
    )

    persisted = delivery_state.read_delivery_state(tmp_path)
    assert persisted.delivery_mode == "agency"
    assert persisted.execution_policy == "guided"
    assert persisted.active_milestone_id == "m6"
    assert persisted.milestone_execution == "orchestrator"
    assert persisted.approval_status == "approved"
    assert persisted.review_status == "unknown"
    assert persisted.loop_status == "in_progress"

    lifecycle.read_legacy_delivery_summary(tmp_path)

    assert delivery_state.read_delivery_state(tmp_path) == persisted


def test_approved_handoff_preserves_existing_delivery_aggregate(tmp_path: Path) -> None:
    """Agency approval retains delivery evidence and history already on disk."""
    from renmark.delivery_state import (
        DeliveryProvenanceEvent,
        DeliveryState,
        WorkPackageSummary,
        read_delivery_state,
        write_delivery_state,
    )

    existing = DeliveryState(
        run_id="delivery-0123456789ab",
        work_packages=[WorkPackageSummary(package_id="wp1", milestone_id="m5", title="Existing")],
        review_status="passed",
        verification_status="passed",
        source_sha="a" * 40,
        provenance_events=[DeliveryProvenanceEvent(kind="existing", detail="keep")],
        legacy_refs=["legacy:keep"],
    )
    write_delivery_state(tmp_path, existing)

    activate(
        tmp_path,
        current_phase="build",
        current_milestone="M6",
        signoff_status="approved",
    )

    persisted = read_delivery_state(tmp_path)
    assert persisted.run_id == "delivery-0123456789ab"
    assert persisted.work_packages == existing.work_packages
    assert persisted.review_status == "passed"
    assert persisted.verification_status == "passed"
    assert persisted.source_sha == "a" * 40
    assert persisted.legacy_refs == ["legacy:keep"]
    assert persisted.provenance_events[0] == existing.provenance_events[0]
    assert persisted.provenance_events[-1].kind == "agency-approved-handoff"


def test_handoff_rejects_inactive_and_unapproved_agency_state(tmp_path: Path) -> None:
    """Only an active, explicitly approved Agency milestone may be delegated."""
    with pytest.raises(ValueError, match="active Agency milestone"):
        approve_milestone_for_orchestrator(tmp_path)

    activate(tmp_path, current_milestone="M6", signoff_status="pending")

    with pytest.raises(ValueError, match="owner approval"):
        approve_milestone_for_orchestrator(tmp_path)


def test_is_active_reflects_persisted_state(tmp_path: Path) -> None:
    """is_active() should mirror the active flag in persisted state."""
    write_agency(tmp_path, AgencyState(active=False, current_phase="planning"))
    assert is_active(tmp_path) is False

    write_agency(tmp_path, AgencyState(active=True, current_phase="planning"))
    assert is_active(tmp_path) is True


def test_inactive_agency_projects_to_default_delivery_state(tmp_path: Path) -> None:
    """Inactive agency state should not activate delivery compatibility mode."""
    state = AgencyState(
        active=False,
        current_phase="delivery",
        current_milestone="M2",
        next_checkpoint="demo",
        signoff_status="approved",
        roadmap_ref=".renmark/plans/agency.md",
    )

    projected = project_agency_state(state)
    persisted = current_agency_to_delivery_state(tmp_path)

    assert projected.delivery_mode == "orchestrator"
    assert projected.execution_policy == "guided"
    assert projected.active_milestone_id == ""
    assert projected.work_packages == []
    assert projected.approval_status == "unknown"
    assert projected.review_status == "unknown"
    assert projected.loop_status == "unknown"
    assert projected.legacy_refs == []
    assert persisted.delivery_mode == projected.delivery_mode
    assert persisted.execution_policy == projected.execution_policy
    assert persisted.active_milestone_id == projected.active_milestone_id
    assert persisted.work_packages == projected.work_packages
    assert persisted.approval_status == projected.approval_status
    assert persisted.review_status == projected.review_status
    assert persisted.loop_status == projected.loop_status
    assert persisted.legacy_refs == projected.legacy_refs


def test_active_agency_projects_milestone_fields_into_delivery_state() -> None:
    """Active agency state should project milestone fields into delivery state."""
    state = AgencyState(
        active=True,
        current_phase="Delivery Phase",
        current_milestone="Milestone 2",
        signoff_status="pending",
        cost_lane="balanced",
        roadmap_ref=".renmark/plans/agency.md",
    )

    projected = agency_to_delivery_state(state)

    assert projected.delivery_mode == "agency"
    assert projected.execution_policy == "guided"
    assert projected.active_milestone_id == "milestone-2"
    assert projected.approval_status == "pending"
    assert projected.review_status == "pending"
    assert projected.loop_status == "in_progress"
    assert projected.work_packages == []
    assert "agency_phase:Delivery Phase" in projected.legacy_refs
    assert "agency_milestone:Milestone 2" in projected.legacy_refs


def test_active_agency_with_empty_milestone_fields_repairs_projection() -> None:
    """Empty phase and milestone should fall back to discovery without bloat."""
    projected = project_agency_state(
        AgencyState(
            active=True,
            current_phase="",
            current_milestone="",
            next_checkpoint="",
        )
    )

    assert projected.delivery_mode == "agency"
    assert projected.active_milestone_id == "discovery"
    assert projected.work_packages == []
    assert projected.approval_status == "unknown"
    assert projected.review_status == "unknown"
    assert projected.provenance_events == []


@pytest.mark.parametrize(
    ("signoff_status", "expected"),
    [
        ("unknown", "unknown"),
        ("pending", "pending"),
        ("in_progress", "in_progress"),
        ("approved", "approved"),
        ("passed", "passed"),
        ("blocked", "blocked"),
        ("failed", "failed"),
        ("needs-owner", "unknown"),
    ],
)
def test_signoff_status_maps_to_delivery_approval_and_review(
    signoff_status: str,
    expected: str,
) -> None:
    """Agency signoff status should normalize into delivery approval fields."""
    projected = project_agency_state(
        AgencyState(
            active=True,
            current_phase="planning",
            current_milestone="planning",
            signoff_status=signoff_status,
        )
    )

    assert projected.approval_status == expected
    assert projected.review_status == expected


def test_roadmap_ref_is_preserved_in_work_package_and_legacy_refs() -> None:
    """Roadmap refs should survive compatibility projection in legacy refs."""
    projected = project_agency_state(
        AgencyState(
            active=True,
            current_phase="planning",
            current_milestone="milestone alpha",
            roadmap_ref=".renmark/plans/roadmap.md",
            cost_lane="balanced",
        )
    )

    assert "agency_roadmap_ref:.renmark/plans/roadmap.md" in projected.legacy_refs
    assert "agency_cost_lane:balanced" in projected.legacy_refs


def test_byte_budget_enforced(tmp_path: Path) -> None:
    """Oversize agency state must raise the dedicated bloat error."""
    huge_ref = "a/" + "x" * 1024
    with pytest.raises(AgencyBloatError):
        write_agency(
            tmp_path,
            AgencyState(active=True, roadmap_ref=huge_ref),
        )


def test_activate_with_estimated_tokens_threads_through_to_checkpoint(tmp_path: Path) -> None:
    """A live agent's self-reported estimated_tokens, passed at signoff, must
    reach milestone_context_checkpoint and — when it crosses the configured
    threshold — actually produce a checkpoint (real end-to-end proof, not a
    mock of the intermediate call). Omitting it (the default, exercised
    elsewhere in this file) must stay exactly as dormant as before."""
    from renmark import config
    from renmark.delivery_state import read_delivery_state

    config.set_compact_gate_tokens(tmp_path, 1000)
    try:
        activate(
            tmp_path,
            current_phase="delivery",
            current_milestone="M-estimate-test",
            signoff_status="approved",
            estimated_tokens=5000,
        )
        delivery = read_delivery_state(tmp_path)
        kinds = [e.kind for e in delivery.provenance_events]
        assert "context-checkpoint-hint" in kinds
        hint_event = next(e for e in delivery.provenance_events if e.kind == "context-checkpoint-hint")
        assert "/compact" in hint_event.detail
        assert (tmp_path / ".renmark" / "state" / "compact_checkpoint.json").exists()
    finally:
        config.set_compact_gate_tokens(tmp_path, 120_000)


def test_activate_without_estimated_tokens_stays_dormant(tmp_path: Path) -> None:
    """The default (no self-report) must never fabricate a checkpoint trigger
    — approve_milestone_for_orchestrator's own default behavior, unchanged."""
    from renmark.delivery_state import read_delivery_state

    activate(
        tmp_path,
        current_phase="delivery",
        current_milestone="M-no-estimate",
        signoff_status="approved",
    )
    delivery = read_delivery_state(tmp_path)
    kinds = [e.kind for e in delivery.provenance_events]
    assert "context-checkpoint-hint" not in kinds


def test_approve_milestone_for_orchestrator_accepts_estimated_tokens_kwarg(tmp_path: Path) -> None:
    """Direct call (bypassing activate()) also threads estimated_tokens —
    proves the parameter lives on the function signature itself, not just
    activate()'s pass-through."""
    from renmark import config
    from renmark.delivery_state import read_delivery_state

    activate(tmp_path, current_phase="delivery", current_milestone="M-direct")
    from renmark.agency import read_agency, write_agency

    state = read_agency(tmp_path)
    state.signoff_status = "approved"
    write_agency(tmp_path, state)

    config.set_compact_gate_tokens(tmp_path, 100)
    try:
        approve_milestone_for_orchestrator(tmp_path, estimated_tokens=999)
        delivery = read_delivery_state(tmp_path)
        assert any(e.kind == "context-checkpoint-hint" for e in delivery.provenance_events)
    finally:
        config.set_compact_gate_tokens(tmp_path, 120_000)

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
    deactivate,
    is_active,
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


def test_is_active_reflects_persisted_state(tmp_path: Path) -> None:
    """is_active() should mirror the active flag in persisted state."""
    write_agency(tmp_path, AgencyState(active=False, current_phase="planning"))
    assert is_active(tmp_path) is False

    write_agency(tmp_path, AgencyState(active=True, current_phase="planning"))
    assert is_active(tmp_path) is True


def test_byte_budget_enforced(tmp_path: Path) -> None:
    """Oversize agency state must raise the dedicated bloat error."""
    huge_ref = "a/" + "x" * 1024
    with pytest.raises(AgencyBloatError):
        write_agency(
            tmp_path,
            AgencyState(active=True, roadmap_ref=huge_ref),
        )

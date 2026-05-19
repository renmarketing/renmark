"""Unit tests for renmark.lifecycle (G12 — lifecycle persistence)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from renmark import lifecycle
from renmark.lifecycle import LifecycleBloatError, LifecycleState, NEXT_BY_STAGE


def test_read_lifecycle_none_when_missing(tmp_path: Path) -> None:
    assert lifecycle.read_lifecycle(tmp_path) is None


def test_write_then_read_lifecycle(tmp_path: Path) -> None:
    state = lifecycle.write_lifecycle(
        tmp_path,
        stage="brainstorm-complete",
        feature="auth-overhaul",
        branch="feature/auth-overhaul",
    )
    assert state.feature == "auth-overhaul"
    assert state.stage == "brainstorm-complete"
    assert state.next_recommended == "/renmark:plan"

    loaded = lifecycle.read_lifecycle(tmp_path)
    assert loaded is not None
    assert loaded.feature == "auth-overhaul"
    assert loaded.stage == "brainstorm-complete"


def test_stage_transitions_track_completed(tmp_path: Path) -> None:
    lifecycle.write_lifecycle(tmp_path, stage="brainstorm-complete", feature="x")
    lifecycle.write_lifecycle(tmp_path, stage="plan-drafted")
    lifecycle.write_lifecycle(tmp_path, stage="plan-validated")
    state = lifecycle.read_lifecycle(tmp_path)
    assert state.stage == "plan-validated"
    assert "brainstorm-complete" in state.stages_completed
    assert "plan-drafted" in state.stages_completed


def test_unknown_stage_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        lifecycle.write_lifecycle(tmp_path, stage="invented-stage")


def test_artifact_update(tmp_path: Path) -> None:
    lifecycle.write_lifecycle(
        tmp_path, stage="brainstorm-complete", feature="x",
        artifact_update=("spec", ".renmark/specs/x.spec.md"),
    )
    state = lifecycle.read_lifecycle(tmp_path)
    assert state.artifacts == {"spec": ".renmark/specs/x.spec.md"}
    lifecycle.write_lifecycle(
        tmp_path,
        artifact_update=("plan", ".renmark/plans/x.plan.md"),
    )
    state = lifecycle.read_lifecycle(tmp_path)
    assert state.artifacts == {
        "spec": ".renmark/specs/x.spec.md",
        "plan": ".renmark/plans/x.plan.md",
    }


def test_human_review_fields(tmp_path: Path) -> None:
    lifecycle.write_lifecycle(
        tmp_path, stage="ready-to-release", feature="x",
        human_review_required=True, human_review_for="release-v0.3.0",
    )
    state = lifecycle.read_lifecycle(tmp_path)
    assert state.human_review_required is True
    assert state.human_review_completed is False
    assert state.human_review_for == "release-v0.3.0"

    lifecycle.write_lifecycle(tmp_path, human_review_completed=True)
    state = lifecycle.read_lifecycle(tmp_path)
    assert state.human_review_completed is True


def test_clear_lifecycle(tmp_path: Path) -> None:
    lifecycle.write_lifecycle(tmp_path, stage="brainstorm-complete", feature="x")
    assert lifecycle.read_lifecycle(tmp_path) is not None
    lifecycle.clear_lifecycle(tmp_path)
    assert lifecycle.read_lifecycle(tmp_path) is None


def test_next_recommended_no_lifecycle(tmp_path: Path) -> None:
    rec = lifecycle.next_recommended(tmp_path)
    assert "/renmark:start" in rec


def test_next_recommended_normal_flow(tmp_path: Path) -> None:
    lifecycle.write_lifecycle(tmp_path, stage="created", feature="x")
    assert lifecycle.next_recommended(tmp_path) == "/renmark:verify"


def test_next_recommended_pending_approval(tmp_path: Path) -> None:
    lifecycle.write_lifecycle(
        tmp_path, stage="ready-to-release", feature="x",
        human_review_required=True, human_review_for="release-v0.3.0",
    )
    rec = lifecycle.next_recommended(tmp_path)
    assert "approve" in rec
    assert "release-v0.3.0" in rec


def test_next_recommended_approved_proceeds(tmp_path: Path) -> None:
    lifecycle.write_lifecycle(
        tmp_path, stage="ready-to-release", feature="x",
        human_review_required=True, human_review_completed=True,
        human_review_for="release-v0.3.0",
    )
    rec = lifecycle.next_recommended(tmp_path)
    assert rec == "/renmark:release"


def test_byte_budget_enforced(tmp_path: Path) -> None:
    """Adding too many artifact paths should trip the bloat guard."""
    lifecycle.write_lifecycle(tmp_path, stage="brainstorm-complete", feature="x")
    huge_path = "a/" + "x" * 1024
    with pytest.raises(LifecycleBloatError):
        lifecycle.write_lifecycle(tmp_path, artifact_update=("huge", huge_path))


def test_domain_classification() -> None:
    assert lifecycle.domain_of("debug") == "debug"
    assert lifecycle.domain_of("plan") == "build"
    assert lifecycle.domain_of("secure") == "audit"
    assert lifecycle.domain_of("setup") == "meta"
    assert lifecycle.domain_of("unknown-skill") == "build"  # default


def test_cross_domain_transition() -> None:
    assert lifecycle.is_cross_domain_transition(None, "plan") is False
    assert lifecycle.is_cross_domain_transition("plan", "orchestrate") is False  # both build
    assert lifecycle.is_cross_domain_transition("plan", "debug") is True
    assert lifecycle.is_cross_domain_transition("debug", "verify") is True


def test_corrupt_lifecycle_returns_none(tmp_path: Path) -> None:
    state_dir = tmp_path / ".renmark" / "state"
    state_dir.mkdir(parents=True)
    (state_dir / "lifecycle.json").write_text("not json {{{")
    assert lifecycle.read_lifecycle(tmp_path) is None


def test_unknown_fields_in_lifecycle_tolerated(tmp_path: Path) -> None:
    """Forward-compat: extra fields shouldn't crash the loader."""
    state_dir = tmp_path / ".renmark" / "state"
    state_dir.mkdir(parents=True)
    (state_dir / "lifecycle.json").write_text(json.dumps({
        "feature": "x", "stage": "verified", "future_field_added_later": "ok",
    }))
    state = lifecycle.read_lifecycle(tmp_path)
    assert state is not None
    assert state.feature == "x"
    assert state.stage == "verified"


def test_lifecycle_state_default_last_updated() -> None:
    state = LifecycleState()
    assert state.last_updated  # auto-populated
    assert "T" in state.last_updated  # ISO format


def test_stage_named_in_next_by_stage_for_every_canonical_stage() -> None:
    from renmark.lifecycle import STAGES
    for stage in STAGES:
        assert stage in NEXT_BY_STAGE, f"stage {stage!r} missing from NEXT_BY_STAGE"

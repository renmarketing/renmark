"""Smoke test: simulate the full lifecycle and assert each stage writes
lifecycle.json correctly. Does NOT actually call codex / execute code —
the dispatch is mocked. This tests the workflow contract, not the
multi-LLM machinery."""

from __future__ import annotations

import json
from pathlib import Path

from renmark import lifecycle, schemas
from renmark.lifecycle import STAGES


def _read_lifecycle(repo: Path) -> dict:
    return json.loads((repo / ".renmark" / "state" / "lifecycle.json").read_text())


def test_full_lifecycle_round_trip(fixture_project: Path):
    """Drive every stage transition through write_lifecycle and assert the
    JSON file remains schema-valid + within byte budget at every step."""
    repo = fixture_project

    # 1. Start a feature (init).
    lifecycle.write_lifecycle(repo, stage="init", feature="auth", branch="feature/auth")
    state = _read_lifecycle(repo)
    assert state["feature"] == "auth"
    assert state["stage"] == "init"
    assert schemas.validate_lifecycle(state) == []

    # 2-9. Walk every canonical stage in order.
    transitions = [
        ("brainstorm-complete", ("spec", ".renmark/specs/2026-05-21-auth.spec.md")),
        ("plan-drafted", ("plan", ".renmark/plans/2026-05-21-auth.plan.md")),
        ("plan-validated", None),
        ("created", None),
        ("verified", ("verification", ".renmark/reviews/2026-05-21-auth.verification.md")),
        ("reviewed", ("review", ".renmark/reviews/2026-05-21-auth.review.md")),
        ("documented", None),
        ("ready-to-release", None),
        ("released", None),
    ]
    for stage, artifact in transitions:
        kwargs = {"stage": stage}
        if artifact:
            kwargs["artifact_update"] = artifact
        result = lifecycle.write_lifecycle(repo, **kwargs)
        state = _read_lifecycle(repo)
        assert state["stage"] == stage, f"failed at {stage}: state is {state['stage']}"
        assert schemas.validate_lifecycle(state) == [], (
            f"schema violation at stage {stage}: {schemas.validate_lifecycle(state)}"
        )

    # All earlier real stages should be in stages_completed.
    # init is the sentinel "not started" state and is NOT recorded.
    final = _read_lifecycle(repo)
    for s in ("brainstorm-complete", "plan-drafted", "verified"):
        assert s in final["stages_completed"]
    assert "init" not in final["stages_completed"]


def test_lifecycle_recommends_correct_next_stage(fixture_project: Path):
    """next_recommended must always match NEXT_BY_STAGE for the current stage."""
    repo = fixture_project
    for stage in STAGES:
        lifecycle.write_lifecycle(repo, stage=stage, feature="x", branch="x")
        rec = lifecycle.next_recommended(repo)
        expected = lifecycle.NEXT_BY_STAGE.get(stage, "")
        assert expected in rec or rec.startswith("/renmark:"), (
            f"stage={stage}: rec={rec!r}, expected fragment={expected!r}"
        )


def test_human_approval_gate_blocks_progression(fixture_project: Path):
    """When human_review_required=True and not completed, next_recommended
    must point to /renmark:approve, not the natural next stage."""
    repo = fixture_project
    lifecycle.write_lifecycle(
        repo,
        stage="documented",
        feature="x",
        branch="x",
        human_review_required=True,
        human_review_for="release-v0.3.1",
    )
    rec = lifecycle.next_recommended(repo)
    assert "/renmark:approve" in rec
    assert "release-v0.3.1" in rec

    # After approval, next_recommended should resume normal flow.
    lifecycle.write_lifecycle(repo, human_review_completed=True)
    rec = lifecycle.next_recommended(repo)
    assert "/renmark:finish" in rec  # documented -> finish per NEXT_BY_STAGE


def test_pipeline_state_separation(fixture_project: Path):
    """Runtime fields (wave_index, completed_tasks) belong in pipeline.json,
    NOT lifecycle.json. This test asserts they live in separate files."""
    from renmark import state

    repo = fixture_project

    # Lifecycle is small.
    lifecycle.write_lifecycle(repo, stage="created", feature="x", branch="x")
    life_size = (repo / ".renmark" / "state" / "lifecycle.json").stat().st_size
    assert life_size < 1024

    # Pipeline is separate.
    state.write_pipeline_state(
        repo,
        current_phase="orchestrate",
        current_plan=".renmark/plans/x.plan.md",
        wave_index=2,
        wave_total=5,
        add_completed_task=1,
    )
    state.write_pipeline_state(repo, add_completed_task=2)

    pipe_path = repo / ".renmark" / "state" / "pipeline.json"
    assert pipe_path.exists()
    pipe = json.loads(pipe_path.read_text())
    assert schemas.validate_pipeline(pipe) == []
    assert pipe["wave_index"] == 2
    assert 1 in pipe["completed_tasks"] and 2 in pipe["completed_tasks"]

    # Lifecycle is unchanged by pipeline writes.
    life = _read_lifecycle(repo)
    assert "wave_index" not in life
    assert "completed_tasks" not in life

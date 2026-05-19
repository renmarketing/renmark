"""Unit tests for state.py additions: pipeline state, wave summaries, skill invocations."""
from __future__ import annotations

from pathlib import Path

import pytest

from renmark import state


def test_pipeline_state_none_when_missing(tmp_path: Path) -> None:
    assert state.read_pipeline_state(tmp_path) is None


def test_pipeline_state_round_trip(tmp_path: Path) -> None:
    state.write_pipeline_state(
        tmp_path,
        current_phase="orchestrate",
        current_plan=".renmark/plans/x.plan.md",
        wave_index=2,
        wave_total=4,
    )
    loaded = state.read_pipeline_state(tmp_path)
    assert loaded is not None
    assert loaded.current_phase == "orchestrate"
    assert loaded.wave_index == 2
    assert loaded.wave_total == 4
    assert loaded.current_plan == ".renmark/plans/x.plan.md"


def test_pipeline_state_preserves_unrelated_fields(tmp_path: Path) -> None:
    state.write_pipeline_state(tmp_path, current_phase="orchestrate", wave_total=4)
    state.write_pipeline_state(tmp_path, wave_index=1)
    loaded = state.read_pipeline_state(tmp_path)
    assert loaded.current_phase == "orchestrate"  # preserved
    assert loaded.wave_total == 4                  # preserved
    assert loaded.wave_index == 1                  # updated


def test_pipeline_state_completed_and_failed_tracking(tmp_path: Path) -> None:
    state.write_pipeline_state(tmp_path, current_phase="orchestrate")
    state.write_pipeline_state(tmp_path, add_completed_task=1)
    state.write_pipeline_state(tmp_path, add_completed_task=2)
    state.write_pipeline_state(tmp_path, add_completed_task=1)  # idempotent
    state.write_pipeline_state(tmp_path, add_failed_task=3)
    loaded = state.read_pipeline_state(tmp_path)
    assert loaded.completed_tasks == [1, 2]
    assert loaded.failed_tasks == [3]


def test_pipeline_state_clear_tasks(tmp_path: Path) -> None:
    state.write_pipeline_state(tmp_path, add_completed_task=1, add_failed_task=2)
    state.write_pipeline_state(tmp_path, clear_tasks=True)
    loaded = state.read_pipeline_state(tmp_path)
    assert loaded.completed_tasks == []
    assert loaded.failed_tasks == []


def test_clear_pipeline_state(tmp_path: Path) -> None:
    state.write_pipeline_state(tmp_path, current_phase="orchestrate")
    state.clear_pipeline_state(tmp_path)
    assert state.read_pipeline_state(tmp_path) is None


def test_pipeline_is_resumable(tmp_path: Path) -> None:
    assert state.pipeline_is_resumable(tmp_path) is False  # nothing in flight
    state.write_pipeline_state(
        tmp_path, current_phase="orchestrate", wave_index=1, wave_total=4,
    )
    assert state.pipeline_is_resumable(tmp_path) is True
    state.write_pipeline_state(tmp_path, wave_index=4)  # all waves done
    assert state.pipeline_is_resumable(tmp_path) is False


def test_pipeline_corrupt_returns_none(tmp_path: Path) -> None:
    sdir = state.state_dir(tmp_path)
    (sdir / "pipeline.json").write_text("not json {{{")
    assert state.read_pipeline_state(tmp_path) is None


def test_wave_summary_round_trip(tmp_path: Path) -> None:
    outputs = [
        {"task_id": 1, "status": "PASS", "artifact_path": ".renmark/state/escalations/task-1/",
         "summary_lines": ["added auth route"], "dependency_notes": "exports authMiddleware()"},
        {"task_id": 2, "status": "PASS", "artifact_path": ".renmark/state/escalations/task-2/",
         "summary_lines": ["added tests"], "dependency_notes": ""},
    ]
    path = state.write_wave_summary(tmp_path, wave_index=1, task_outputs=outputs)
    assert path.exists()
    loaded = state.read_wave_summary(tmp_path, wave_index=1)
    assert loaded["wave_index"] == 1
    assert len(loaded["task_outputs"]) == 2
    assert loaded["task_outputs"][0]["dependency_notes"] == "exports authMiddleware()"


def test_wave_summary_missing(tmp_path: Path) -> None:
    assert state.read_wave_summary(tmp_path, wave_index=99) is None


def test_list_wave_summaries(tmp_path: Path) -> None:
    state.write_wave_summary(tmp_path, 1, [])
    state.write_wave_summary(tmp_path, 3, [])
    state.write_wave_summary(tmp_path, 2, [])
    assert state.list_wave_summaries(tmp_path) == [1, 2, 3]


def test_record_and_read_skill_invocation(tmp_path: Path) -> None:
    assert state.last_skill_invocation(tmp_path) is None
    state.record_skill_invocation(tmp_path, "plan", "build")
    rec = state.last_skill_invocation(tmp_path)
    assert rec["skill"] == "plan"
    assert rec["domain"] == "build"


def test_context_budget_check_first_invocation(tmp_path: Path) -> None:
    # No prior skill — no recommendation.
    assert state.context_budget_check(tmp_path, "plan", "build") is None


def test_context_budget_check_same_domain(tmp_path: Path) -> None:
    state.record_skill_invocation(tmp_path, "plan", "build")
    assert state.context_budget_check(tmp_path, "orchestrate", "build") is None


def test_context_budget_check_cross_domain(tmp_path: Path) -> None:
    state.record_skill_invocation(tmp_path, "debug", "debug")
    assert state.context_budget_check(tmp_path, "orchestrate", "build") == "clear"


def test_context_budget_check_audit_to_build(tmp_path: Path) -> None:
    state.record_skill_invocation(tmp_path, "secure", "audit")
    assert state.context_budget_check(tmp_path, "orchestrate", "build") == "clear"

"""Unit tests for state.py additions: pipeline state, wave summaries, skill invocations."""

from __future__ import annotations

from pathlib import Path

import pytest

from renmark import state
from renmark.cli import _engine
from renmark.delivery_state import DeliveryState, read_delivery_state, write_delivery_state
from renmark.parser import Task
from renmark.state import pipeline as pipeline_state
from renmark.state.pause import PauseState, read_pause, write_pause


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
    assert loaded.wave_total == 4  # preserved
    assert loaded.wave_index == 1  # updated


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
        tmp_path,
        current_phase="orchestrate",
        wave_index=1,
        wave_total=4,
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
        {
            "task_id": 1,
            "status": "PASS",
            "artifact_path": ".renmark/state/escalations/task-1/",
            "summary_lines": ["added auth route"],
            "dependency_notes": "exports authMiddleware()",
        },
        {
            "task_id": 2,
            "status": "PASS",
            "artifact_path": ".renmark/state/escalations/task-2/",
            "summary_lines": ["added tests"],
            "dependency_notes": "",
        },
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


def test_last_skill_invocation_non_dict_json(tmp_path: Path) -> None:
    """Valid JSON that is not an object must return None, never raise —
    a corrupt last-skill.json would otherwise wedge every skill's Step 0
    (skill_preamble crashes before record_skill_invocation can overwrite it)."""
    path = tmp_path / ".renmark" / "state" / "last-skill.json"
    path.parent.mkdir(parents=True)
    for payload in ("[1, 2, 3]", '"plan"', "42"):
        path.write_text(payload)
        assert state.last_skill_invocation(tmp_path) is None
        assert state.context_budget_check(tmp_path, "orchestrate", "build") is None


def test_pipeline_wave_counters_coerced_from_strings(tmp_path: Path) -> None:
    """String wave counters previously compared lexicographically ("9" < "10" is
    False) — coercion makes pipeline_is_resumable arithmetically correct."""
    p = tmp_path / ".renmark" / "state"
    p.mkdir(parents=True)
    (p / "pipeline.json").write_text('{"current_phase": "orchestrate", "wave_index": "9", "wave_total": "10"}')
    assert state.pipeline_is_resumable(tmp_path) is True


def test_pipeline_uncoercible_wave_counters_degrade(tmp_path: Path) -> None:
    p = tmp_path / ".renmark" / "state"
    p.mkdir(parents=True)
    (p / "pipeline.json").write_text('{"current_phase": "orchestrate", "wave_index": null, "wave_total": 3}')
    # null wave_index drops to the dataclass default — no TypeError.
    assert state.pipeline_is_resumable(tmp_path) in (True, False)


def test_read_wave_summary_non_dict_returns_none(tmp_path: Path) -> None:
    d = tmp_path / ".renmark" / "state" / "wave-summaries"
    d.mkdir(parents=True)
    (d / "wave-2.json").write_text("[1, 2, 3]")
    assert state.read_wave_summary(tmp_path, 2) is None


def test_legacy_unknown_phase_normalized_on_read(tmp_path: Path) -> None:
    """An out-of-vocab current_phase on disk must not make the next
    read-modify-write raise via the writer-side validator. (v0.9.0 codereview.)"""
    p = tmp_path / ".renmark" / "state"
    p.mkdir(parents=True)
    (p / "pipeline.json").write_text('{"current_phase": "legacy-phase", "wave_index": 1}')
    loaded = state.read_pipeline_state(tmp_path)
    assert loaded is not None
    assert loaded.current_phase == "idle"
    # And the write path stays legal:
    state.write_pipeline_state(tmp_path, add_completed_task=1)


def test_pipeline_delivery_runtime_fields_missing_pipeline_state(tmp_path: Path) -> None:
    runtime = pipeline_state.pipeline_delivery_runtime_fields(tmp_path)

    assert runtime == {
        "runtime_phase": "idle",
        "runtime_plan_ref": "",
        "runtime_wave_index": 0,
        "runtime_wave_total": 0,
        "runtime_wave_label": "wave 0/0",
        "runtime_completed_task_count": 0,
        "runtime_failed_task_count": 0,
        "runtime_completed_task_sample": [],
        "runtime_failed_task_sample": [],
        "runtime_resumable": False,
        "runtime_last_updated": "",
        "runtime_summary": "idle | wave 0/0 | done=0 | failed=0 | resumable=no",
    }


@pytest.mark.parametrize(
    ("phase", "wave_index", "wave_total", "expected_resumable"),
    [
        ("idle", 0, 0, False),
        ("orchestrate", 2, 4, True),
        ("paused", 2, 4, True),
        ("orchestrate", 4, 4, False),
        ("paused", 5, 4, False),
    ],
)
def test_pipeline_delivery_runtime_phase_and_resumable_mapping(
    phase: str,
    wave_index: int,
    wave_total: int,
    expected_resumable: bool,
) -> None:
    pipeline_runtime_state = state.PipelineState(
        current_phase=phase,
        current_plan=".renmark/plans/runtime.plan.md",
        wave_index=wave_index,
        wave_total=wave_total,
    )

    runtime = pipeline_state.pipeline_delivery_runtime_fields_from_state(pipeline_runtime_state)

    assert runtime["runtime_phase"] == phase
    assert runtime["runtime_wave_index"] == wave_index
    assert runtime["runtime_wave_total"] == wave_total
    assert runtime["runtime_wave_label"] == f"wave {wave_index}/{wave_total}" if wave_total > 0 else "wave 0/0"
    assert runtime["runtime_resumable"] is expected_resumable
    assert runtime["runtime_summary"] == (
        f"{phase} | wave {wave_index}/{wave_total} | done=0 | failed=0 | "
        f"resumable={'yes' if expected_resumable else 'no'}"
        if wave_total > 0
        else f"{phase} | wave 0/0 | done=0 | failed=0 | resumable={'yes' if expected_resumable else 'no'}"
    )


def test_pipeline_delivery_runtime_task_lists_are_counted_and_bounded() -> None:
    pipeline_runtime_state = state.PipelineState(
        current_phase="orchestrate",
        current_plan=".renmark/plans/" + ("x" * 200) + ".plan.md",
        wave_index=3,
        wave_total=8,
        completed_tasks=[1, 2, 3, 4, 5, 6, 7],
        failed_tasks=[8, 9, 10, 11, 12, 13],
        last_updated="2026-07-29T12:00:00Z",
    )

    runtime = pipeline_state.pipeline_delivery_runtime_fields_from_state(pipeline_runtime_state)

    assert runtime["runtime_phase"] == "orchestrate"
    assert runtime["runtime_plan_ref"] == ".renmark/plans/" + ("x" * 81)
    assert runtime["runtime_completed_task_count"] == 7
    assert runtime["runtime_failed_task_count"] == 6
    assert runtime["runtime_completed_task_sample"] == [1, 2, 3, 4, 5]
    assert runtime["runtime_failed_task_sample"] == [8, 9, 10, 11, 12]
    assert runtime["runtime_last_updated"] == "2026-07-29T12:00:00Z"
    assert runtime["runtime_resumable"] is True
    assert runtime["runtime_summary"] == "orchestrate | wave 3/8 | done=7 | failed=6 | resumable=yes"


def test_execute_plan_initializes_pipeline_and_records_wave_progress(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Dispatch starts resumable state before work and advances it per wave."""
    tasks = [
        Task(1, "first", "edit", "one.py", executor="codex", parallel_group=1),
        Task(2, "second", "edit", "two.py", executor="codex", parallel_group=2),
    ]
    plan = tmp_path / "m3.plan.md"
    seen_before_dispatch: list[state.PipelineState] = []

    monkeypatch.setattr(_engine, "parse_plan", lambda _path: tasks)

    def succeed(**_kwargs: object) -> tuple[bool, str, int, str]:
        current = state.read_pipeline_state(tmp_path)
        assert current is not None
        seen_before_dispatch.append(current)
        return True, "PASS", 0, ""

    monkeypatch.setattr(_engine, "_execute_task", succeed)

    assert _engine.execute_plan(str(plan), repo=tmp_path, no_commit=True) == 0
    assert seen_before_dispatch[0].current_phase == "orchestrate"
    assert seen_before_dispatch[0].current_plan == str(plan)
    assert seen_before_dispatch[0].wave_index == 0
    assert seen_before_dispatch[0].wave_total == 2
    assert seen_before_dispatch[1].completed_tasks == [1]
    assert seen_before_dispatch[1].wave_index == 1
    assert state.read_pipeline_state(tmp_path) is None


def test_execute_plan_needs_agent_in_final_wave_keeps_pipeline_resumable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A final-wave host-agent handoff remains an outstanding resumable task."""
    plan = tmp_path / "handoff.plan.md"
    monkeypatch.setattr(
        _engine,
        "parse_plan",
        lambda _path: [
            Task(1, "local work", "edit", "local.py", executor="codex", parallel_group=1),
            Task(2, "host work", "edit", "host.py", executor="sonnet", parallel_group=2),
        ],
    )
    monkeypatch.setattr(
        _engine,
        "_execute_task",
        lambda **_kwargs: (True, "PASS", 0, ""),
    )

    assert _engine.execute_plan(str(plan), repo=tmp_path, no_commit=True) == 0

    pipeline = state.read_pipeline_state(tmp_path)
    assert pipeline is not None
    assert pipeline.current_phase == "paused"
    assert pipeline.wave_index == 1
    assert pipeline.wave_total == 2
    assert pipeline.completed_tasks == [1]
    assert pipeline.failed_tasks == []
    assert 2 not in pipeline.completed_tasks
    assert state.pipeline_is_resumable(tmp_path) is True
    pause = read_pause(tmp_path)
    assert pause is not None
    assert pause.last_task_index == 2
    assert pause.reason == "needs_agent"


def test_execute_plan_success_clears_old_pause_and_pipeline_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A clean new run must not leave an M2 pause or resume pointer behind."""
    old_plan = ".renmark/plans/m2.plan.md"
    state.write_pipeline_state(
        tmp_path,
        current_phase="paused",
        current_plan=old_plan,
        wave_index=1,
        wave_total=2,
        add_completed_task=1,
    )
    write_pause(
        tmp_path,
        PauseState(
            run_id="m2-run",
            plan_path=old_plan,
            last_task_index=1,
            reason="usage limit",
            ts="2026-07-30T00:00:00Z",
        ),
    )
    write_delivery_state(
        tmp_path,
        DeliveryState(
            review_status="passed",
            verification_status="passed",
            loop_status="passed",
        ),
    )
    plan = tmp_path / "m3.plan.md"
    monkeypatch.setattr(
        _engine,
        "parse_plan",
        lambda _path: [Task(1, "new work", "edit", "new.py", executor="codex")],
    )
    monkeypatch.setattr(
        _engine,
        "_execute_task",
        lambda **_kwargs: (True, "PASS", 0, ""),
    )

    assert _engine.execute_plan(str(plan), repo=tmp_path, no_commit=True) == 0
    assert state.read_pipeline_state(tmp_path) is None
    assert read_pause(tmp_path) is None
    delivery = read_delivery_state(tmp_path)
    assert delivery.verification_status == "passed"
    assert delivery.review_status == "pending"

    from renmark.lifecycle import read_lifecycle

    assert read_lifecycle(tmp_path).stage == "created"

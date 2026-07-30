"""Unit tests for renmark.program."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from renmark import delivery_state, program


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    return tmp_path


def _sample_program() -> program.Program:
    return program.Program(
        feature="Roadmap hardening",
        mode="staged",
        source_sha="abc123",
        current_stage_id="stage-2",
        stages=[
            program.StageNode(
                id="stage-1",
                title="Plan",
                serves="REQ-1",
                status="done",
                pipeline_phases=["brainstorm", "plan"],
                tasks=[
                    program.TaskNode(
                        id="task-1",
                        title="Draft spec",
                        status="done",
                        summary="Spec approved",
                    ),
                    program.TaskNode(
                        id="task-2",
                        title="Review scope",
                        status="blocked",
                    ),
                ],
            ),
            program.StageNode(
                id="stage-2",
                title="Build",
                serves="REQ-2",
                status="in_progress",
                pipeline_phases=["orchestrate", "verify"],
                tasks=[
                    program.TaskNode(
                        id="task-3",
                        title="Implement writer",
                        status="done",
                        retry_count=2,
                        summary="Atomic writes complete",
                    ),
                    program.TaskNode(
                        id="task-4",
                        title="Render roadmap",
                        status="in_progress",
                        summary="Summary with\nextra whitespace",
                    ),
                ],
            ),
        ],
    )


def test_read_program_none_only_when_missing(repo: Path) -> None:
    assert program.read_program(repo) is None


def test_write_read_round_trip_and_rerender_markdown(repo: Path) -> None:
    state = _sample_program()

    json_path = program.write_program(repo, state)
    md_path = program.program_md_path(repo)

    assert json_path == repo / ".renmark" / "state" / "program.json"
    assert md_path == repo / ".renmark" / "roadmap" / "program.md"
    assert json_path.exists()
    assert md_path.exists()

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["feature"] == "Roadmap hardening"
    assert payload["current_stage_id"] == "stage-2"

    loaded = program.read_program(repo)
    assert loaded is not None
    assert loaded.feature == state.feature
    assert loaded.mode == state.mode
    assert loaded.current_stage_id == state.current_stage_id
    assert [stage.id for stage in loaded.stages] == ["stage-1", "stage-2"]
    assert loaded.stages[1].tasks[0].retry_count == 2

    md_path.write_text("stale manual edit", encoding="utf-8")
    program.mark_task(state, "stage-2", "task-4", "done", summary="Roadmap rendered")
    program.write_program(repo, state)

    rendered = md_path.read_text(encoding="utf-8")
    assert "stale manual edit" not in rendered
    assert "- [x] Render roadmap — Roadmap rendered" in rendered


def test_read_program_empty_object_is_valid(repo: Path) -> None:
    json_path = program.program_json_path(repo)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text("{}", encoding="utf-8")

    loaded = program.read_program(repo)
    assert loaded is not None
    assert loaded.feature == ""
    assert loaded.mode == "staged"
    assert loaded.stages == []


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        ("{", "not valid JSON"),
        ("[]", "must be a JSON object"),
        ('{"mode":"bogus"}', "must be one of"),
        ('{"stages":"bad"}', "'stages' must be a list"),
        ('{"stages":[{"status":"bogus"}]}', "must be one of"),
        ('{"stages":[{"tasks":[{"retry_count":"two"}]}]}', "must be an integer"),
        ('{"current_stage_id": 7}', "must be a string or null"),
    ],
)
def test_read_program_raises_on_corrupt_existing_file(
    repo: Path, payload: str, expected: str
) -> None:
    json_path = program.program_json_path(repo)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(payload, encoding="utf-8")

    with pytest.raises(program.ProgramStateError, match=expected):
        program.read_program(repo)


def test_position_returns_bounded_one_line_form() -> None:
    state = _sample_program()

    result = program.position(state)

    assert result == "Stage 2/2 · task 1/2 done · current: Build"
    assert "\n" not in result


def test_render_markdown_matches_status_and_inlines_summaries() -> None:
    rendered = program.render_markdown(_sample_program())

    assert rendered.startswith("---\nartifact_type: program\nschema_version: 1\n")
    assert "# Program — Roadmap hardening" in rendered
    assert "_mode: staged · Stage 2/2 · task 1/2 done · current: Build_" in rendered
    assert "## ● Plan — serves REQ-1" in rendered
    assert "## ◐ Build — serves REQ-2 **(current)**" in rendered
    assert "- [x] Draft spec — Spec approved" in rendered
    assert "- [ ] Review scope" in rendered
    assert "- [x] Implement writer — Atomic writes complete _(retries: 2)_" in rendered
    assert "- [ ] Render roadmap — Summary with extra whitespace" in rendered


def test_mutators_update_state_and_raise_on_invalid_ids_or_status() -> None:
    state = _sample_program()

    returned = program.mark_task(
        state,
        "stage-2",
        "task-4",
        "done",
        summary="Rendered cleanly",
    )
    assert returned is state
    assert state.stages[1].tasks[1].status == "done"
    assert state.stages[1].tasks[1].summary == "Rendered cleanly"

    program.mark_stage(state, "stage-2", "partial")
    assert state.stages[1].status == "partial"

    state.stages[1].tasks[1].retry_count = -4
    program.bump_retry(state, "stage-2", "task-4")
    assert state.stages[1].tasks[1].retry_count == 1
    program.bump_retry(state, "stage-2", "task-4")
    assert state.stages[1].tasks[1].retry_count == 2

    program.snapshot_stage_sha(state, "stage-2", "deadbeef")
    assert state.stage_completion_sha["stage-2"] == "deadbeef"

    with pytest.raises(ValueError, match="invalid status"):
        program.mark_task(state, "stage-2", "task-4", "bogus")
    with pytest.raises(ValueError, match="unknown stage id"):
        program.mark_task(state, "missing-stage", "task-4", "done")
    with pytest.raises(ValueError, match="unknown task id"):
        program.mark_task(state, "stage-2", "missing-task", "done")

    with pytest.raises(ValueError, match="invalid status"):
        program.mark_stage(state, "stage-2", "bogus")
    with pytest.raises(ValueError, match="unknown stage id"):
        program.mark_stage(state, "missing-stage", "done")

    with pytest.raises(ValueError, match="unknown stage id"):
        program.bump_retry(state, "missing-stage", "task-4")
    with pytest.raises(ValueError, match="unknown task id"):
        program.bump_retry(state, "stage-2", "missing-task")

    with pytest.raises(ValueError, match="unknown stage id"):
        program.snapshot_stage_sha(state, "missing-stage", "cafebabe")


def test_stage_digest_is_bounded_to_five_lines() -> None:
    state = program.Program(
        feature="Digest",
        stages=[
            program.StageNode(
                id="stage-1",
                title="Digest stage",
                status="in_progress",
                tasks=[
                    program.TaskNode(id="task-1", title="One", status="done", summary="First summary"),
                    program.TaskNode(id="task-2", title="Two", status="partial", summary="Second summary"),
                    program.TaskNode(id="task-3", title="Three", status="blocked"),
                    program.TaskNode(id="task-4", title="Four", status="needed", summary="Fourth summary"),
                    program.TaskNode(id="task-5", title="Five", status="pending", summary="Fifth summary"),
                ],
            )
        ],
    )

    digest = program.stage_digest(state, "stage-1")
    lines = digest.splitlines()

    assert len(lines) <= 5
    assert lines[0] == "◐ Digest stage [in_progress] — 5 task(s)"
    assert "One: First summary" in lines[1]
    assert "Two: Second summary" in lines[2]
    assert "Three: blocked" in lines[3]
    assert lines[4] == "  - … (+2 more tasks)"


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        ("pending", "pending"),
        ("in_progress", "in_progress"),
        ("done", "passed"),
        ("partial", "blocked"),
        ("needed", "blocked"),
        ("blocked", "blocked"),
        ("unknown-status", "unknown"),
    ],
)
def test_delivery_state_for_program_status_maps_to_bounded_delivery_values(
    status: str, expected: str
) -> None:
    assert program.delivery_state_for_program_status(status) == expected


def test_program_delivery_milestones_projects_current_stage_and_bounded_fields() -> None:
    state = _sample_program()
    program.snapshot_stage_sha(state, "stage-2", "deadbeef")

    milestones = program.program_delivery_milestones(state)

    assert [item["milestone_id"] for item in milestones] == ["stage-1", "stage-2"]
    assert [item["delivery_state"] for item in milestones] == ["passed", "in_progress"]
    assert [item["current"] for item in milestones] == [False, True]
    assert [item["index"] for item in milestones] == [1, 2]
    assert [item["completed_task_count"] for item in milestones] == [1, 1]
    assert milestones[0]["completion_sha"] == ""
    assert milestones[1]["completion_sha"] == "deadbeef"
    assert milestones[1]["status"] == "in_progress"
    assert milestones[1]["task_count"] == 2
    assert milestones[1]["pipeline_phases"] == ["orchestrate", "verify"]
    assert [pkg["package_id"] for pkg in milestones[1]["work_packages"]] == [
        "stage-2--task-3",
        "stage-2--task-4",
    ]
    assert [pkg["delivery_state"] for pkg in milestones[1]["work_packages"]] == [
        "passed",
        "in_progress",
    ]


def test_stage_work_package_summaries_normalize_summary_and_keep_stable_ids() -> None:
    stage = _sample_program().stages[1]

    packages = program.stage_work_package_summaries(stage)

    assert [item["package_id"] for item in packages] == [
        "stage-2--task-3",
        "stage-2--task-4",
    ]
    assert all(item["milestone_id"] == "stage-2" for item in packages)
    assert packages[0]["summary"] == "Atomic writes complete"
    assert packages[1]["summary"] == "Summary with extra whitespace"
    assert packages[1]["status"] == "in_progress"
    assert packages[1]["delivery_state"] == "in_progress"
    assert packages[1]["retry_count"] == 0


def test_stable_program_delivery_ids_match_delivery_state_helpers() -> None:
    stage = program.StageNode(id="Build & Verify", title="Ignored title", serves="REQ-9")
    task = program.TaskNode(id="Task: Render + publish")

    milestone_id = program.stable_milestone_id_for_stage(stage)
    package_id = program.stable_work_package_id_for_task(stage, task)

    assert milestone_id == delivery_state.stable_milestone_id(stage.id)
    assert package_id == delivery_state.stable_work_package_id(milestone_id, task.id)


def test_stable_program_delivery_ids_use_stage_aliases_and_task_title_fallback() -> None:
    stage = program.StageNode(id="", title="Quality Assurance", serves="Verify")
    task = program.TaskNode(id="", title="Review rendered output")

    milestone_id = program.stable_milestone_id_for_stage(stage)
    package_id = program.stable_work_package_id_for_task(stage, task)

    assert milestone_id == "verify"
    assert package_id == "verify--review-rendered-output"


# ── Hardening regressions (codereview 2026-06-14) ───────────────────────────────


def test_read_program_raises_on_invalid_utf8(repo: Path) -> None:
    """An existing file with invalid UTF-8 bytes is corruption → ProgramStateError,
    NOT a leaked UnicodeDecodeError and NOT a silent None."""
    path = program.program_json_path(repo)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\xff\xfe\x00 not utf-8 \xff")
    with pytest.raises(program.ProgramStateError, match="UTF-8"):
        program.read_program(repo)


def test_read_program_raises_on_dangling_current_stage_id(repo: Path) -> None:
    """current_stage_id that names no real stage is corrupt state → raise."""
    path = program.program_json_path(repo)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "feature": "f",
                "stages": [{"id": "s1", "title": "S", "serves": "REQ-1", "tasks": []}],
                "current_stage_id": "ghost",
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(program.ProgramStateError, match="current_stage_id"):
        program.read_program(repo)


def test_read_program_raises_on_dangling_completion_sha(repo: Path) -> None:
    """stage_completion_sha keyed to a non-existent stage is corrupt → raise."""
    path = program.program_json_path(repo)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "feature": "f",
                "stages": [{"id": "s1", "title": "S", "serves": "REQ-1", "tasks": []}],
                "stage_completion_sha": {"ghost": "abc123"},
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(program.ProgramStateError, match="stage_completion_sha"):
        program.read_program(repo)


def test_read_program_raises_on_duplicate_stage_ids(repo: Path) -> None:
    """Duplicate stage ids silently shadow later stages → corrupt → raise."""
    path = program.program_json_path(repo)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "feature": "f",
                "stages": [
                    {"id": "dup", "title": "A", "serves": "REQ-1", "tasks": []},
                    {"id": "dup", "title": "B", "serves": "REQ-2", "tasks": []},
                ],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(program.ProgramStateError, match="duplicate stage id"):
        program.read_program(repo)


def test_write_program_leaves_no_temp_litter(repo: Path) -> None:
    """Atomic durable write cleans up after itself — no .program-*.tmp remains —
    and the round-trip still works."""
    program.write_program(repo, _sample_program())
    state_dir = program.program_json_path(repo).parent
    leftovers = list(state_dir.glob(".program-*.tmp"))
    assert leftovers == [], f"temp litter left behind: {leftovers}"
    assert program.read_program(repo) is not None

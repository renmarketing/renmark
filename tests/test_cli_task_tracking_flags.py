"""End-to-end CLI coverage for the native task-tracking flags."""

from __future__ import annotations

from pathlib import Path

import pytest

from renmark import task_tracking as tt
from renmark.cli import _engine


def _init_repo(repo: Path) -> None:
    (repo / ".renmark" / "state").mkdir(parents=True, exist_ok=True)


def _task_create_argv(repo: Path, task_id: str) -> list[str]:
    return [
        "--repo",
        str(repo),
        "--task-create",
        task_id,
        "--title",
        "T",
        "--role",
        "R",
        "--scope",
        "S",
        "--verification-expectation",
        "V",
    ]


def test_task_create_then_in_progress_then_complete_updates_tasks_json(
    tmp_path: Path, capsys
) -> None:
    _init_repo(tmp_path)
    task_id = "task-1"
    artifact_path = tmp_path / "artifact.md"

    rc = _engine.main(_task_create_argv(tmp_path, task_id))
    assert rc == 0
    assert task_id in capsys.readouterr().out

    created = tt.read_tasks(tmp_path)[task_id]
    assert created.source == "codex-live"
    assert created.status == "pending"

    rc = _engine.main(["--repo", str(tmp_path), "--task-in-progress", task_id])
    assert rc == 0
    capsys.readouterr()

    in_progress = tt.read_tasks(tmp_path)[task_id]
    assert in_progress.status == "in_progress"

    rc = _engine.main(
        [
            "--repo",
            str(tmp_path),
            "--task-complete",
            task_id,
            "--artifact-path",
            str(artifact_path),
            "--result-summary",
            "done",
        ]
    )
    assert rc == 0
    capsys.readouterr()

    completed = tt.read_tasks(tmp_path)[task_id]
    assert completed.status == "completed"
    assert completed.artifact_path == str(artifact_path)


@pytest.mark.parametrize(
    "missing_flag",
    [
        "--title",
        "--role",
        "--scope",
        "--verification-expectation",
    ],
)
def test_task_create_missing_required_flag_returns_2(
    tmp_path: Path, capsys, missing_flag: str
) -> None:
    _init_repo(tmp_path)
    argv = _task_create_argv(tmp_path, "task-1")
    missing_value = {
        "--title": "T",
        "--role": "R",
        "--scope": "S",
        "--verification-expectation": "V",
    }[missing_flag]
    argv.remove(missing_flag)
    argv.remove(missing_value)

    rc = _engine.main(argv)
    assert rc == 2
    captured = capsys.readouterr()
    assert "--task-create requires" in captured.err
    assert missing_flag in captured.err


def test_task_in_progress_unknown_task_returns_2(tmp_path: Path, capsys) -> None:
    _init_repo(tmp_path)

    rc = _engine.main(["--repo", str(tmp_path), "--task-in-progress", "missing-task"])
    assert rc == 2

    captured = capsys.readouterr()
    assert "ERROR:" in captured.err
    assert "missing-task" in captured.err


def test_task_complete_missing_evidence_returns_2_before_task_tracking(
    tmp_path: Path, capsys, monkeypatch
) -> None:
    _init_repo(tmp_path)

    def _boom(*args, **kwargs):  # pragma: no cover - guard should prevent call
        raise AssertionError("task_tracking.complete_task should not be called")

    monkeypatch.setattr(_engine._task_tracking, "complete_task", _boom)

    rc = _engine.main(["--repo", str(tmp_path), "--task-complete", "task-1"])
    assert rc == 2

    captured = capsys.readouterr()
    assert "--task-complete requires" in captured.err
    assert "--artifact-path" in captured.err
    assert "--result-summary" in captured.err


"""Unit tests for renmark.dispatch."""
from __future__ import annotations

import time
from pathlib import Path

import pytest

from renmark import dispatch
from renmark.dispatch import TaskResult, WaveResult
from renmark.parser import Task


def _task(idx: int, target: str, executor: str = "codex",
          parallel_group: int | None = None,
          context_files: list[str] | None = None) -> Task:
    return Task(
        index=idx, title=f"task {idx}", mode="A", target=target,
        context_files=context_files or [],
        verifier="true", verifier_timeout_s=60, spec="noop",
        executor=executor, complexity="simple",
        parallel_group=parallel_group,
    )


def test_group_tasks_by_wave_default_serial() -> None:
    tasks = [_task(1, "a"), _task(2, "b"), _task(3, "c")]
    waves = dispatch.group_tasks_by_wave(tasks)
    assert [len(w) for w in waves] == [1, 1, 1]


def test_group_tasks_by_wave_groups_shared() -> None:
    tasks = [
        _task(1, "a", parallel_group=1),
        _task(2, "b", parallel_group=1),
        _task(3, "c", parallel_group=2),
        _task(4, "d", parallel_group=2),
    ]
    waves = dispatch.group_tasks_by_wave(tasks)
    assert [len(w) for w in waves] == [2, 2]
    assert {t.target for t in waves[0]} == {"a", "b"}


def test_validate_wave_disjoint_targets_ok() -> None:
    wave = [_task(1, "a"), _task(2, "b")]
    dispatch.validate_wave(wave)


def test_validate_wave_rejects_overlapping_targets() -> None:
    wave = [_task(1, "a"), _task(2, "a")]
    with pytest.raises(ValueError, match="overlapping targets"):
        dispatch.validate_wave(wave)


def test_validate_wave_rejects_context_into_wave_target() -> None:
    wave = [_task(1, "a"), _task(2, "b", context_files=["a"])]
    with pytest.raises(ValueError, match="context_files"):
        dispatch.validate_wave(wave)


def test_dispatch_wave_parallel_runs_concurrently(tmp_path: Path) -> None:
    """Two slow tasks in the same wave should run in parallel — total
    elapsed time is closer to one task than two."""
    def slow(task: Task, repo: Path) -> TaskResult:
        time.sleep(0.1)
        return TaskResult(task_index=task.index, executor=task.executor, status="passed")

    wave = [_task(1, "a", parallel_group=1), _task(2, "b", parallel_group=1)]
    start = time.monotonic()
    result = dispatch.dispatch_wave(wave, repo=tmp_path, run_task=slow)
    elapsed = time.monotonic() - start
    assert result.all_passed
    assert len(result.tasks) == 2
    # Should be far less than 2 × 0.1s (serial would be ~0.2; parallel ~0.1).
    assert elapsed < 0.18, f"wave took {elapsed:.3f}s — not parallel"


def test_dispatch_wave_marks_claude_tasks_needs_agent(tmp_path: Path) -> None:
    def runner(task: Task, repo: Path) -> TaskResult:
        return TaskResult(task_index=task.index, executor=task.executor, status="passed")

    wave = [
        _task(1, "a", executor="codex", parallel_group=1),
        _task(2, "b", executor="opus", parallel_group=1),
        _task(3, "c", executor="sonnet", parallel_group=1),
    ]
    result = dispatch.dispatch_wave(wave, repo=tmp_path, run_task=runner)
    statuses = {t.task_index: t.status for t in result.tasks}
    assert statuses[1] == "passed"
    assert statuses[2] == "needs_agent"
    assert statuses[3] == "needs_agent"
    assert len(result.needs_agent) == 2


def test_estimate_wave_cost_sums() -> None:
    tasks = [
        _task(1, "a"), _task(2, "b"),
    ]
    tasks[0].est_tokens = 100; tasks[0].est_cost_usd = 0.01
    tasks[1].est_tokens = 250; tasks[1].est_cost_usd = 0.05
    tok, cost = dispatch.estimate_wave_cost(tasks)
    assert tok == 350
    assert cost == pytest.approx(0.06)


def test_estimate_wave_cost_handles_missing() -> None:
    tok, cost = dispatch.estimate_wave_cost([_task(1, "a")])
    assert tok == 0
    assert cost == 0.0


def test_dispatch_wave_runner_exception_marks_failed(tmp_path: Path) -> None:
    def boom(task: Task, repo: Path) -> TaskResult:
        raise RuntimeError("kaboom")

    wave = [_task(1, "a")]
    result = dispatch.dispatch_wave(wave, repo=tmp_path, run_task=boom)
    assert result.tasks[0].status == "failed"
    assert "kaboom" in result.tasks[0].note


def test_build_agent_dispatch_returns_structured(tmp_path: Path) -> None:
    from renmark.providers import claude_agent
    t = _task(7, "src/foo.py", executor="opus")
    t.spec = "make foo do X"
    d = claude_agent.build_agent_dispatch(t, tmp_path)
    assert d.task_index == 7
    assert d.model == "opus"
    assert d.target == "src/foo.py"
    assert "make foo do X" in d.prompt
    assert "Modify exactly one file" in d.prompt

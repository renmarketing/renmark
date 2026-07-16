"""Unit tests for renmark.dispatch."""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from renmark import dispatch
from renmark.dispatch import TaskResult
from renmark.parser import Task


def _task(
    idx: int,
    target: str,
    executor: str = "codex",
    parallel_group: int | None = None,
    context_files: list[str] | None = None,
) -> Task:
    return Task(
        index=idx,
        title=f"task {idx}",
        mode="A",
        target=target,
        context_files=context_files or [],
        verifier="true",
        verifier_timeout_s=60,
        spec="noop",
        executor=executor,
        complexity="simple",
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


def test_dispatch_wave_routes_fable_through_claude_partition(tmp_path: Path) -> None:
    from renmark.providers import claude_agent

    def runner(task: Task, repo: Path) -> TaskResult:
        return TaskResult(task_index=task.index, executor=task.executor, status="passed")

    wave = [
        _task(1, "a", executor="codex", parallel_group=1),
        _task(2, "b", executor="fable", parallel_group=1),
    ]
    result = dispatch.dispatch_wave(wave, repo=tmp_path, run_task=runner)
    statuses = {t.task_index: t.status for t in result.tasks}
    assert claude_agent.is_claude_executor("fable") is True
    assert statuses[1] == "passed"
    assert statuses[2] == "needs_agent"
    assert [t.task_index for t in result.needs_agent] == [2]


def test_estimate_wave_cost_sums() -> None:
    tasks = [
        _task(1, "a"),
        _task(2, "b"),
    ]
    tasks[0].est_tokens = 100
    tasks[0].est_cost_usd = 0.01
    tasks[1].est_tokens = 250
    tasks[1].est_cost_usd = 0.05
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


def _fanout_expected(tasks: list) -> list:
    """Build expected fanout payloads: SubagentInput.to_dict() + agent_type field."""
    from renmark import subagent_profiles

    result = []
    for task in tasks:
        inp = dispatch.build_subagent_input(task)
        payload = inp.to_dict()
        payload["agent_type"] = inp.role if subagent_profiles.has_native_agent_file(inp.role) else None
        result.append(payload)
    return result


def test_build_workflow_fanout_args_returns_claude_wave_in_order() -> None:
    wave = [
        _task(1, "src/a.py", executor="sonnet", parallel_group=1),
        _task(2, "src/b.py", executor="opus", parallel_group=1),
        _task(3, "src/c.py", executor="fable", parallel_group=1),
    ]

    assert dispatch.build_workflow_fanout_args(wave) == _fanout_expected(wave)


def test_build_workflow_fanout_args_excludes_codex_tasks() -> None:
    wave = [
        _task(1, "src/a.py", executor="codex", parallel_group=1),
        _task(2, "src/b.py", executor="sonnet", parallel_group=1),
        _task(3, "src/c.py", executor="codex", parallel_group=1),
        _task(4, "src/d.py", executor="opus", parallel_group=1),
    ]
    claude_tasks = [t for t in wave if t.executor != "codex"]

    assert dispatch.build_workflow_fanout_args(wave) == _fanout_expected(claude_tasks)


def test_build_workflow_fanout_args_returns_empty_for_all_codex_wave() -> None:
    wave = [
        _task(1, "src/a.py", executor="codex", parallel_group=1),
        _task(2, "src/b.py", executor="codex", parallel_group=1),
    ]

    assert dispatch.build_workflow_fanout_args(wave) == []


def test_build_workflow_fanout_args_includes_agent_type_for_native_roles() -> None:
    """agent_type is pre-resolved: native roles get the role name, others get None."""
    from renmark import subagent_profiles

    # docs-editor target resolves to docs-editor (has native file) → agent_type != None
    wave_doc = [_task(1, "plugin/skills/foo.md", executor="haiku", parallel_group=1)]
    result = dispatch.build_workflow_fanout_args(wave_doc)
    assert len(result) == 1
    role = result[0]["role"]
    if subagent_profiles.has_native_agent_file(role):
        assert result[0]["agent_type"] == role
    else:
        assert result[0]["agent_type"] is None

    # src/a.py resolves to general-purpose → agent_type is None
    wave_gp = [_task(2, "src/a.py", executor="sonnet", parallel_group=1)]
    result_gp = dispatch.build_workflow_fanout_args(wave_gp)
    assert result_gp[0]["agent_type"] is None


def test_host_dispatch_plan_maps_single_task_to_native_tools() -> None:
    task = _task(1, "src/a.py", executor="sonnet")

    claude = dispatch.build_host_dispatch_plan([task], host="claude")
    codex = dispatch.build_host_dispatch_plan([task], host="codex")

    assert claude.strategy == codex.strategy == "single"
    assert claude.task_packets == codex.task_packets
    assert [call.tool for call in claude.calls] == ["Agent"]
    assert [call.tool for call in codex.calls] == ["spawn_agent"]
    assert codex.wait_tool == "wait_agent"
    assert codex.followup_tool == "followup_task"
    assert codex.calls[0].arguments["fork_turns"] == "none"
    assert codex.calls[0].model_route is not None


def test_host_dispatch_plan_maps_parallel_wave_to_native_fanout() -> None:
    wave = [
        _task(1, "src/a.py", executor="sonnet", parallel_group=1),
        _task(2, "src/b.py", executor="opus", parallel_group=1),
    ]

    claude = dispatch.build_host_dispatch_plan(wave, host="claude")
    codex = dispatch.build_host_dispatch_plan(wave, host="codex")

    assert claude.strategy == codex.strategy == "fanout"
    assert claude.task_packets == codex.task_packets
    assert len(claude.calls) == 1
    assert claude.calls[0].tool == "Workflow"
    assert claude.calls[0].task_indices == (1, 2)
    assert [call.tool for call in codex.calls] == ["spawn_agent", "spawn_agent"]
    assert [call.task_indices for call in codex.calls] == [(1,), (2,)]


def test_host_dispatch_plan_leaves_codex_executor_on_subprocess_path() -> None:
    task = _task(1, "src/a.py", executor="codex")

    for host in ("claude", "codex"):
        plan = dispatch.build_host_dispatch_plan([task], host=host)
        assert plan.strategy == "none"
        assert plan.task_packets == ()
        assert plan.calls == ()


def test_bounded_host_prompt_refuses_oversized_packet() -> None:
    task = _task(1, "src/a.py", executor="sonnet")
    task.spec = "x" * dispatch.MAX_HOST_DISPATCH_PROMPT_CHARS
    inp = dispatch.build_subagent_input(task)

    with pytest.raises(dispatch.IsolationViolation, match="bounded-input contract"):
        dispatch.render_bounded_subagent_prompt(inp)


def test_host_prompt_carries_canonical_reasoning_instruction() -> None:
    task = _task(1, "src/a.py", executor="sonnet")
    plan = dispatch.build_host_dispatch_plan(
        [task],
        host="codex",
        reasoning_instruction="Challenge assumptions before editing.",
    )

    assert "CANONICAL_REASONING_INSTRUCTION" in plan.calls[0].arguments["message"]
    assert "Challenge assumptions before editing." in plan.calls[0].arguments["message"]


def test_host_dispatch_plan_rejects_unknown_host() -> None:
    with pytest.raises(ValueError, match="unsupported host"):
        dispatch.build_host_dispatch_plan([_task(1, "src/a.py", executor="sonnet")], host="other")

"""Deterministic Claude/Codex parity trajectories.

These tests prove packet shaping, response validation, ledger/wave persistence,
verifier handling, and loop resume semantics with simulated host returns. They
do not invoke or claim live behavior from Claude Agent/Workflow or Codex
spawn_agent/wait_agent/followup_task.
"""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from renmark import dispatch, loop, state, summary
from renmark.parser import parse_plan


def _write_plan(repo: Path) -> Path:
    repo.mkdir(parents=True, exist_ok=True)
    plan = repo / "parity.plan.md"
    plan.write_text(
        "# Plan: host parity\n\n"
        "## Tasks\n\n"
        "### Task 1: Implement bounded change\n"
        "- **mode:** B\n"
        "- **target:** src/change.py\n"
        "- **context_files:** []\n"
        "- **executor:** sonnet\n"
        "- **complexity:** medium\n"
        "- **parallel_group:** 1\n"
        "- **verifier:** true\n"
        "- **spec:**\n"
        "  Implement the bounded change.\n\n"
        "### Task 2: Add bounded proof\n"
        "- **mode:** A\n"
        "- **target:** tests/test_change.py\n"
        "- **context_files:** []\n"
        "- **executor:** opus\n"
        "- **complexity:** hard\n"
        "- **parallel_group:** 1\n"
        "- **verifier:** true\n"
        "- **spec:**\n"
        "  Add the bounded proof.\n",
        encoding="utf-8",
    )
    return plan


def _simulated_plan_dispatch_verify(repo: Path, host: str) -> dict[str, object]:
    tasks = parse_plan(_write_plan(repo))
    wave = dispatch.group_tasks_by_wave(tasks)[0]
    transport = dispatch.build_host_dispatch_plan(
        wave,
        host=host,
        dependency_summaries=["task 0: approved input"],
    )

    outputs = []
    verifier_lines = []
    ledger_rows = []
    for task in wave:
        out = dispatch.dispatch_task_isolated(
            task,
            dependency_summaries=["task 0: approved input"],
            subagent_runner=lambda _inp, task=task: {
                "status": "PASS",
                "artifact_path": task.target,
                "touched_files": [task.target],
                "sha": f"sha-{task.index}",
                "summary_lines": [f"task {task.index} complete"],
                "dependency_notes": f"task {task.index} verified",
                "token_count": 100 + task.index,
                "completion_state": "complete",
                "confidence": "high",
                "retry_count": 0,
                "validation_status": "validated",
                "parser_success": True,
                "schema_compliance": True,
            },
        )
        outputs.append(out.to_dict())
        verifier_lines.append(summary.verifier_tail(task.verifier, cwd=repo))
        rec = state.log_agent_call(
            repo,
            task_id=task.index,
            model=task.executor,
            tokens_in=10,
            tokens_out=out.token_count,
            run_id=f"{host}-run",
        )
        ledger_rows.append(
            {
                "task_id": rec.task_id,
                "model": rec.model,
                "prompt_tokens": rec.prompt_tokens,
                "completion_tokens": rec.completion_tokens,
            }
        )

    state.write_wave_summary(repo, 0, outputs)
    persisted = state.read_wave_summary(repo, 0)
    assert persisted is not None
    return {
        "strategy": transport.strategy,
        "task_packets": transport.task_packets,
        "outputs": persisted["task_outputs"],
        "verifiers": verifier_lines,
        "ledger": ledger_rows,
    }


def test_simulated_plan_dispatch_verify_has_cross_host_semantic_parity(tmp_path: Path) -> None:
    claude = _simulated_plan_dispatch_verify(tmp_path / "claude", "claude")
    codex = _simulated_plan_dispatch_verify(tmp_path / "codex", "codex")

    assert claude == codex
    verifier_lines = claude["verifiers"]
    assert isinstance(verifier_lines, list)
    assert all(line.startswith("exit 0 |") for line in verifier_lines)


def _simulated_loop_resume(repo: Path, host: str) -> dict[str, object]:
    loop_id = loop.loop_id("2026-07-16", "host parity")
    before = loop.LoopState(
        goal="all checks green",
        verify_cmd="python -c \"assert True\"",
        budget_tokens=10_000,
        budget_usd_estimate="$0.10",
        spent_tokens=400,
        run_id="parity-loop",
        max_iterations=3,
        iteration=1,
        status="running",
        pending_step="",
    )
    assert loop.write_loop(repo, loop_id, before) is not None

    resumed = loop.read_loop(repo, loop_id)
    assert resumed is not None
    failed_decision = loop.build_decision(
        {
            "completion_state": "partial",
            "validation_status": "failed",
            "summary_lines": ["failed: parity verifier"],
        },
        spent_delta=200,
    )
    resumed.iteration += 1
    resumed.spent_tokens += 200
    assert loop.write_loop(repo, loop_id, resumed) is not None

    task = parse_plan(_write_plan(repo))[0]
    transport = dispatch.build_host_dispatch_plan([task], host=host)
    final_decision = loop.build_decision(
        {
            "completion_state": "complete",
            "validation_status": "validated",
            "summary_lines": ["all checks green"],
        },
        spent_delta=100,
    )
    resumed.status = "done" if final_decision["goal_reached"] else "stalled"
    assert loop.write_loop(repo, loop_id, resumed) is not None
    final = loop.read_loop(repo, loop_id)
    assert final is not None
    return {
        "resumed": asdict(resumed),
        "failed_next_action": failed_decision["next_action"],
        "final_goal_reached": final_decision["goal_reached"],
        "stop_reason": loop.stop_reason(final),
        "task_packets": transport.task_packets,
    }


def test_simulated_loop_resume_has_cross_host_semantic_parity(tmp_path: Path) -> None:
    claude = _simulated_loop_resume(tmp_path / "claude-loop", "claude")
    codex = _simulated_loop_resume(tmp_path / "codex-loop", "codex")

    assert claude == codex
    assert claude["failed_next_action"] == "address: parity verifier"
    assert claude["final_goal_reached"] is True
    assert claude["stop_reason"] == "done"

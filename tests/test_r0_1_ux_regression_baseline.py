"""R-0.1/WP-3 UX regression baseline.

Pins TODAY's dispatch/routing/gating behavior for task shapes that do NOT
qualify for R-0.1/WP-1's fast-path classifier (multi-file waves, renmark/**
targets, medium/hard complexity) — before any fast-path code exists. WP-4
must not change any assertion in this file for these shapes; a fast path is
additive, not a replacement of the existing Normal/Architectural Feature
routing this suite locks in. See .bootstrap-renmark/milestones/R-0.1/
contract.yaml WP-3.
"""

from __future__ import annotations

from pathlib import Path

from renmark import dispatch, release
from renmark.parser import Task
from renmark.subagent_gate import justify_task


def _task(
    idx: int,
    target: str,
    executor: str = "sonnet",
    complexity: str = "medium",
    parallel_group: int | None = None,
) -> Task:
    return Task(
        index=idx,
        title=f"task {idx}",
        mode="M",
        target=target,
        context_files=[],
        verifier="pytest",
        verifier_timeout_s=60,
        spec="spec " * 20,
        executor=executor,
        complexity=complexity,
        parallel_group=parallel_group,
    )


def test_single_renmark_target_dispatch_plan_unchanged() -> None:
    """A single-file renmark/** change (would fail WP-1 signal 3) must keep
    routing through the existing single-Agent/code-implementer path."""
    task = _task(1, "renmark/dispatch.py")
    plan = dispatch.build_host_dispatch_plan([task], host="claude")

    assert plan.strategy == "single"
    assert plan.calls[0].tool == "Agent"
    assert plan.calls[0].arguments["subagent_type"] == "renmark:code-implementer"


def test_multi_file_parallel_wave_dispatch_plan_unchanged() -> None:
    """A 2-file parallel wave (fails WP-1 signal 1, "≤2 named files" is
    still a single-file bound in practice — 2 files in one wave already
    exceeds the fast path's single-Worker model) keeps its existing fanout
    routing via Workflow, not a fast-path shortcut."""
    wave = [
        _task(1, "renmark/program_driver.py", parallel_group=1),
        _task(2, "renmark/dispatch.py", executor="opus", parallel_group=1),
    ]
    plan = dispatch.build_host_dispatch_plan(wave, host="claude")

    assert plan.strategy == "fanout"
    assert len(plan.calls) == 1
    assert plan.calls[0].tool == "Workflow"
    assert plan.calls[0].task_indices == (1, 2)


def test_medium_complexity_task_subagent_verdict_unchanged() -> None:
    """A medium-complexity task (not WP-1-classified "simple") keeps
    needing a subagent, routed to code-implementer at sonnet tier."""
    task = _task(1, "src/a.py", complexity="medium")
    verdict = justify_task(task)

    assert verdict.needs_subagent is True
    assert verdict.role == "code-implementer"
    assert verdict.tier == "sonnet"
    assert verdict.challenge is None


def test_version_drift_check_stays_clean() -> None:
    """The existing 8-location version-sync invariant (unrelated to R-0.1)
    must stay intact throughout R-0.1's design/implementation work — a
    regression here would mean a WP silently touched release metadata."""
    assert release.drift_report(Path(__file__).resolve().parents[1]) == []

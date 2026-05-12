"""Wave-based parallel dispatcher.

Groups tasks by parallel_group, validates that tasks sharing a group write
to disjoint targets, and dispatches each task to its executor backend.

Claude-model tasks (opus/sonnet) cannot run from this Python process —
they need an Agent tool call from the host. The dispatcher returns a
`needs_agent` marker for those so the skill can issue Agent calls itself.

Permission-economy: by accepting a list of tasks per wave call, the user
sees one Bash prompt per wave instead of one per task.
"""
from __future__ import annotations

import concurrent.futures
import time
from dataclasses import dataclass, field
from pathlib import Path

from .parser import Task
from .providers import claude_agent


@dataclass
class TaskResult:
    task_index: int
    executor: str
    status: str             # "passed" | "failed" | "needs_agent" | "skipped"
    sha: str = ""
    tokens_in: int = 0
    tokens_out: int = 0
    elapsed_s: float = 0.0
    note: str = ""


@dataclass
class WaveResult:
    group_id: int
    tasks: list[TaskResult] = field(default_factory=list)

    @property
    def all_passed(self) -> bool:
        return all(t.status == "passed" for t in self.tasks)

    @property
    def needs_agent(self) -> list[TaskResult]:
        return [t for t in self.tasks if t.status == "needs_agent"]


def group_tasks_by_wave(tasks: list[Task]) -> list[list[Task]]:
    """Split tasks into waves by parallel_group.

    Tasks without an explicit parallel_group default to their task index
    (= each in its own group = serial). Waves are returned in numerically-
    sorted group order.
    """
    groups: dict[int, list[Task]] = {}
    for t in tasks:
        gid = t.parallel_group if t.parallel_group is not None else t.index
        groups.setdefault(gid, []).append(t)
    return [groups[k] for k in sorted(groups.keys())]


def validate_wave(wave: list[Task]) -> None:
    """A wave must touch disjoint target files, and no task can list
    another's target in its context_files.

    Raises ValueError on conflict.
    """
    targets = {t.target for t in wave}
    if len(targets) != len(wave):
        dup = [t.target for t in wave]
        seen: set[str] = set()
        repeated = [x for x in dup if x in seen or seen.add(x)]
        raise ValueError(
            f"parallel wave has overlapping targets: {sorted(set(repeated))}. "
            f"Tasks in the same parallel_group must touch disjoint files."
        )
    for t in wave:
        for ctx in t.context_files:
            if ctx in targets and ctx != t.target:
                raise ValueError(
                    f"task {t.index} reads `{ctx}` (in context_files) which is "
                    f"another wave-member's target. Move it to a later wave."
                )


def dispatch_wave(
    wave: list[Task],
    *,
    repo: Path,
    run_task,                # callable: (task: Task, repo: Path) -> TaskResult
    max_workers: int | None = None,
) -> WaveResult:
    """Run all non-Claude tasks in a wave concurrently.

    `run_task` is injected (test-friendly). Claude-model tasks (opus/sonnet)
    don't run here — they get `status="needs_agent"` so the skill can issue
    Agent tool calls itself.
    """
    if not wave:
        return WaveResult(group_id=0, tasks=[])

    validate_wave(wave)
    gid = wave[0].parallel_group if wave[0].parallel_group is not None else wave[0].index
    result = WaveResult(group_id=gid)

    # Split: Claude-model tasks marked needs_agent; everything else runs in parallel.
    claude_tasks = [t for t in wave if claude_agent.is_claude_executor(t.executor)]
    runnable = [t for t in wave if not claude_agent.is_claude_executor(t.executor)]

    for t in claude_tasks:
        result.tasks.append(TaskResult(
            task_index=t.index, executor=t.executor, status="needs_agent",
            note="dispatch this via the Agent tool from the orchestrate skill",
        ))

    if not runnable:
        return result

    workers = max_workers or min(len(runnable), 8)
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
        futures = {ex.submit(_run_one, run_task, t, repo): t for t in runnable}
        for fut in concurrent.futures.as_completed(futures):
            result.tasks.append(fut.result())

    # Sort results by task index for deterministic reporting.
    result.tasks.sort(key=lambda r: r.task_index)
    return result


def _run_one(run_task, task: Task, repo: Path) -> TaskResult:
    start = time.monotonic()
    try:
        r = run_task(task, repo)
        r.elapsed_s = time.monotonic() - start
        return r
    except Exception as e:
        return TaskResult(
            task_index=task.index, executor=task.executor, status="failed",
            elapsed_s=time.monotonic() - start, note=f"{type(e).__name__}: {e}",
        )


def estimate_wave_cost(wave: list[Task]) -> tuple[int, float]:
    """Sum est_tokens and est_cost_usd across a wave (treating None as 0)."""
    tok = sum(t.est_tokens or 0 for t in wave)
    cost = sum(t.est_cost_usd or 0.0 for t in wave)
    return tok, cost

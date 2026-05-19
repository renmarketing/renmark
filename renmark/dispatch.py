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


# ─────────────────────────────────────────────────────────────────────────────
# G11 — Task-level isolation contract
# ─────────────────────────────────────────────────────────────────────────────
# Each task or parallel group runs in an isolated subagent context. The
# orchestrator never sees the subagent's transcript, generated code, or diff —
# only the SubagentOutput summary. Inputs are equally bounded.
#
# SubagentInput is what the subagent gets.
# SubagentOutput is what the subagent emits back.
# dispatch_task_isolated enforces the contract: violations raise IsolationViolation.

import json as _json
from typing import Literal


class IsolationViolation(RuntimeError):
    """Raised when a subagent response includes fields outside SubagentOutput,
    or when its summary_lines exceed the G3 cap. The orchestrator refuses to
    merge violating outputs.
    """


# Public schema: these are the ONLY fields the orchestrator considers.
SUBAGENT_OUTPUT_FIELDS = frozenset({
    "status", "artifact_path", "touched_files", "sha", "summary_lines",
    "dependency_notes", "token_count", "completion_state", "confidence",
    "retry_count",
})

SUBAGENT_OUTPUT_STATUS_VALUES = {"PASS", "FAIL", "SKIP"}
SUBAGENT_OUTPUT_COMPLETION_STATES = {"complete", "partial", "failed"}
SUBAGENT_OUTPUT_CONFIDENCE_VALUES = {"low", "medium", "high"}


@dataclass(frozen=True)
class SubagentInput:
    """The ONLY fields a per-task subagent receives. Anything else is a leak."""

    task_spec: str
    required_files: list[str] = field(default_factory=list)
    upstream_artifact_pointers: list[str] = field(default_factory=list)
    dependency_summaries: list[str] = field(default_factory=list)
    verifier_expectations: str = ""

    def to_dict(self) -> dict:
        return {
            "task_spec": self.task_spec,
            "required_files": list(self.required_files),
            "upstream_artifact_pointers": list(self.upstream_artifact_pointers),
            "dependency_summaries": list(self.dependency_summaries),
            "verifier_expectations": self.verifier_expectations,
        }

    def to_json(self) -> str:
        return _json.dumps(self.to_dict(), indent=2)


@dataclass(frozen=True)
class SubagentOutput:
    """The ONLY fields a subagent may emit. Validated by dispatch_task_isolated."""

    status: Literal["PASS", "FAIL", "SKIP"]
    artifact_path: str
    touched_files: list[str] = field(default_factory=list)
    sha: str | None = None
    summary_lines: list[str] = field(default_factory=list)
    dependency_notes: str = ""
    token_count: int = 0
    completion_state: Literal["complete", "partial", "failed"] = "complete"
    confidence: Literal["low", "medium", "high"] = "medium"
    retry_count: int = 0

    def __post_init__(self) -> None:
        # G3 cap: 5 lines max.
        if len(self.summary_lines) > 5:
            raise IsolationViolation(
                f"SubagentOutput.summary_lines has {len(self.summary_lines)} entries; "
                "max 5 (G3)"
            )
        if self.status not in SUBAGENT_OUTPUT_STATUS_VALUES:
            raise IsolationViolation(
                f"SubagentOutput.status={self.status!r} not in {SUBAGENT_OUTPUT_STATUS_VALUES}"
            )
        if self.completion_state not in SUBAGENT_OUTPUT_COMPLETION_STATES:
            raise IsolationViolation(
                f"SubagentOutput.completion_state={self.completion_state!r} invalid"
            )
        if self.confidence not in SUBAGENT_OUTPUT_CONFIDENCE_VALUES:
            raise IsolationViolation(
                f"SubagentOutput.confidence={self.confidence!r} invalid"
            )

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "artifact_path": self.artifact_path,
            "touched_files": list(self.touched_files),
            "sha": self.sha,
            "summary_lines": list(self.summary_lines),
            "dependency_notes": self.dependency_notes,
            "token_count": self.token_count,
            "completion_state": self.completion_state,
            "confidence": self.confidence,
            "retry_count": self.retry_count,
        }


def parse_subagent_response(response: dict | str) -> SubagentOutput:
    """Parse a subagent's response into a SubagentOutput, refusing any
    payload that includes fields outside SUBAGENT_OUTPUT_FIELDS.

    Raises IsolationViolation on leakage (extra fields like 'transcript',
    'generated_code', 'diff', 'reasoning' etc.).
    """
    if isinstance(response, str):
        try:
            payload = _json.loads(response)
        except _json.JSONDecodeError as exc:
            raise IsolationViolation(
                f"subagent response is not valid JSON: {exc}"
            ) from exc
    else:
        payload = response

    if not isinstance(payload, dict):
        raise IsolationViolation(
            f"subagent response must be a JSON object; got {type(payload).__name__}"
        )

    extra_fields = set(payload.keys()) - SUBAGENT_OUTPUT_FIELDS
    if extra_fields:
        raise IsolationViolation(
            f"subagent response includes forbidden fields {sorted(extra_fields)}. "
            "Only these fields are permitted: " + ", ".join(sorted(SUBAGENT_OUTPUT_FIELDS))
        )

    missing = {"status", "artifact_path"} - set(payload.keys())
    if missing:
        raise IsolationViolation(
            f"subagent response missing required fields: {sorted(missing)}"
        )

    # Only pass through known fields (defensive — extra_fields check should
    # have caught everything, but guard against future refactors).
    filtered = {k: v for k, v in payload.items() if k in SUBAGENT_OUTPUT_FIELDS}
    return SubagentOutput(**filtered)


def build_subagent_input(
    task: Task,
    *,
    dependency_summaries: list[str] | None = None,
    upstream_artifact_pointers: list[str] | None = None,
) -> SubagentInput:
    """Construct the bounded input for a single task's subagent.

    Pulls only the task spec + explicit file paths from the Task dataclass.
    No other Task fields cross the boundary."""
    return SubagentInput(
        task_spec=task.spec,
        required_files=[task.target] + list(task.context_files or []),
        upstream_artifact_pointers=list(upstream_artifact_pointers or []),
        dependency_summaries=list(dependency_summaries or []),
        verifier_expectations=task.verifier or "",
    )


def dispatch_task_isolated(
    task: Task,
    *,
    dependency_summaries: list[str] | None = None,
    upstream_artifact_pointers: list[str] | None = None,
    subagent_runner,
) -> SubagentOutput:
    """Run one task in an isolated subagent context with strict I/O bounds.

    ``subagent_runner`` is a callable that takes a SubagentInput and returns
    a dict or JSON string representing the subagent's response. This is the
    injection point for the actual executor (codex subprocess, Agent tool
    call, or a test mock). Whatever it returns is then validated through
    parse_subagent_response — extra fields raise IsolationViolation.
    """
    inp = build_subagent_input(
        task,
        dependency_summaries=dependency_summaries,
        upstream_artifact_pointers=upstream_artifact_pointers,
    )
    response = subagent_runner(inp)
    return parse_subagent_response(response)

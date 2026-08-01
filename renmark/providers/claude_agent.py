"""Claude Agent executor — for opus/sonnet tasks.

Python (renmark-execute CLI) can't call Claude — that's the host's job. So
this module doesn't make an API call. Instead, when the orchestrate skill
encounters a task with executor=opus or executor=sonnet, it:

1. Calls `build_agent_dispatch(task)` to get a structured spec.
2. Issues an `Agent` tool call in its own Claude turn with that prompt and
   the model override (opus or sonnet).
3. After the subagent returns, calls `record_outcome(...)` to log the result
   into `.renmark/state/usage.jsonl` and update memory.

This module's job is to keep the prompt format and bookkeeping in one place
so the skill stays simple.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .. import fast_path
from ..parser import Task

CLAUDE_EXECUTORS = ("haiku", "sonnet", "opus", "fable")


@dataclass
class AgentDispatch:
    """What the skill needs to issue an Agent tool call for one task."""

    task_index: int
    title: str
    model: str  # "haiku", "sonnet", "opus", or "fable" (the Agent tool's model param)
    target: str
    verifier: str
    description: str  # short description for the Agent tool's `description` param
    prompt: str  # the body the subagent receives
    # R-0.1/WP-4: present only for fast-path dispatches (build_fast_path_agent_
    # dispatch). None for the existing build_agent_dispatch path — its absence
    # is exactly what tells a caller "no post-hoc verify_worker_scope check
    # applies here," preserving WP-3's unchanged-behavior guarantee.
    scope: fast_path.WorkerScope | None = None


def is_claude_executor(executor: str) -> bool:
    return executor in CLAUDE_EXECUTORS


def build_agent_dispatch(task: Task, repo: Path) -> AgentDispatch:
    """Compose the Agent-tool prompt for a Claude-model task.

    Mirrors the contract that nim/codex tasks see: single file, prose spec,
    verifier the subagent must satisfy.
    """
    mode_verb = "Create" if task.mode == "A" else "Modify"
    ctx_block = ""
    if task.context_files:
        ctx_block = (
            "\nRead-only context files (you MAY read but MUST NOT modify):\n"
            + "\n".join(f"- {c}" for c in task.context_files)
            + "\n"
        )

    prompt = (
        f"You are an autonomous subagent completing one task in a larger renmark plan.\n\n"
        f"Goal: {mode_verb} `{task.target}` per the spec below.\n\n"
        f"Specification:\n{task.spec}\n\n"
        f"Constraints (HARD):\n"
        f"- Modify exactly one file: `{task.target}`. Do not create or edit any other file.\n"
        f"- Do not commit. The orchestrator handles commits.\n"
        f"- Do not install dependencies.\n"
        f"- Your work is complete when this command exits 0:\n"
        f"    {task.verifier}\n"
        f"- You may run the verifier yourself to check. The orchestrator will re-run it after you finish.\n"
        f"{ctx_block}\n"
        f"When done, summarize in 1-2 sentences what you changed. Do not paste file contents.\n"
    )

    return AgentDispatch(
        task_index=task.index,
        title=task.title,
        model=task.executor,
        target=task.target,
        verifier=task.verifier,
        description=f"renmark task {task.index}: {task.title[:60]}",
        prompt=prompt,
    )


def build_fast_path_agent_dispatch(tasks: list[Task], repo: Path) -> AgentDispatch:
    """Compose the single-Worker Agent-tool dispatch for an R-0.1 fast-path
    wave (1-2 tasks that passed ``fast_path.classify_fast_path``).

    Distinct from :func:`build_agent_dispatch` (never modifies it — see
    ``AgentDispatch.scope``'s docstring): a fast-path dispatch declares its
    scope explicitly and structurally, and prohibits nested dispatch, which
    only makes sense for a wave General Contractor has already classified as
    fast-path-eligible. Raises ``ValueError`` if ``tasks`` is not eligible —
    this function must never silently degrade a rejected wave into a
    fast-path dispatch.
    """
    verdict = fast_path.classify_fast_path(tasks)
    if not verdict.eligible:
        raise ValueError(f"tasks are not fast-path eligible ({verdict.reason()})")
    scope = fast_path.worker_scope_from_verdict(verdict, tasks)
    targets = sorted(scope.allowed_paths)

    task_blocks = []
    for t in tasks:
        mode_verb = "Create" if t.mode == "A" else "Modify"
        task_blocks.append(f"- {mode_verb} `{t.target}` per: {t.spec}")

    verifiers = "\n".join(f"    {t.verifier}" for t in tasks)

    prompt = (
        "You are an autonomous Worker completing a bounded small-task "
        "fast-path dispatch (renmark R-0.1). This is a lower-ceremony path "
        "than a normal renmark plan task — it exists because this change is "
        "small and its scope is fixed in advance.\n\n"
        "Goals:\n" + "\n".join(task_blocks) + "\n\n"
        "Declared scope (HARD, enforced deterministically after you finish "
        "— not by your own report of what you touched):\n"
        f"- You may ADD or MODIFY only these exact files: {', '.join(targets)}\n"
        "- You may not create, edit, delete, or rename any other file.\n"
        "- You may not delete or rename ANY file, including files in the "
        "list above.\n"
        "- You must not invoke another agent, subagent, Task, or Agent tool "
        "call. This dispatch must not nest.\n"
        "- Do not commit. The orchestrator handles commits.\n"
        "- Do not install dependencies.\n"
        "Your work is complete when these commands exit 0:\n"
        f"{verifiers}\n\n"
        "If you discover you genuinely need to touch a file outside this "
        "declared scope, STOP and report completion_state=partial with a "
        "clear dependency_notes explanation — do not make the change.\n\n"
        "When done, summarize in 1-2 sentences what you changed. Do not "
        "paste file contents.\n"
    )

    return AgentDispatch(
        task_index=tasks[0].index,
        title=" + ".join(t.title for t in tasks),
        model=tasks[0].executor,
        target=targets[0],
        verifier=verifiers,
        description=f"renmark fast-path dispatch: {', '.join(targets)}",
        prompt=prompt,
        scope=scope,
    )

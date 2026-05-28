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

from ..parser import Task

CLAUDE_EXECUTORS = ("haiku", "sonnet", "opus")


@dataclass
class AgentDispatch:
    """What the skill needs to issue an Agent tool call for one task."""

    task_index: int
    title: str
    model: str  # "opus" or "sonnet" (the Agent tool's model param)
    target: str
    verifier: str
    description: str  # short description for the Agent tool's `description` param
    prompt: str  # the body the subagent receives


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

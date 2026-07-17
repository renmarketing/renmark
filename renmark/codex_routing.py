"""Codex model routing helpers for Renmark.

This module keeps Codex-specific model names out of the Claude-oriented
``haiku`` / ``sonnet`` / ``opus`` tier language. Callers can keep using task
complexity and subagent role, then ask this module for the Codex-native model
and reasoning-effort pair.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CodexRoute:
    """Resolved Codex model settings for a task or subagent."""

    model: str
    reasoning_effort: str
    tier: str
    reason: str


@dataclass(frozen=True)
class CodexNativeDispatch:
    """Codex host transport for one isolated renmark task.

    The Codex collaboration tool does not expose a per-spawn model override,
    so :attr:`route` is truthful routing metadata rather than a tool argument.
    ``spawn_args`` contains only arguments accepted by ``spawn_agent``.  The
    caller uses ``wait_tool`` to collect the result and ``followup_tool`` only
    for a bounded correction; neither operation changes the G11 packet/output
    schemas owned by :mod:`renmark.dispatch`.
    """

    task_index: int
    task_name: str
    role: str
    route: CodexRoute
    spawn_args: dict[str, str]
    spawn_tool: str = "spawn_agent"
    wait_tool: str = "wait_agent"
    followup_tool: str = "followup_task"


EASY_ROLES: frozenset[str] = frozenset({"docs-editor", "test-writer", "audit-reader"})
HARD_KINDS: frozenset[str] = frozenset({"architecture", "adversarial-review", "design-fork"})


def route_for_task(task: Any) -> CodexRoute:
    """Return the Codex model/effort pair for *task*.

    Easy work routes to ``gpt-5.4-mini`` with low effort. Medium work routes to
    ``gpt-5.5`` with medium effort. Hard structural work routes to ``gpt-5.5``
    with high effort. The function is defensive and never raises into callers.
    """

    try:
        role = _field(task, "role", "") or ""
        complexity = (_field(task, "complexity", "medium") or "medium").strip().lower()
        kind = (_field(task, "kind", "") or "").strip().lower()
        title = (_field(task, "title", "") or "").strip().lower()

        if complexity in {"hard", "high", "complex"} or kind in HARD_KINDS or _has_hard_signal(title):
            return CodexRoute(
                model="gpt-5.5",
                reasoning_effort="high",
                tier="codex-deep",
                reason="hard or structural task",
            )

        if complexity in {"simple", "easy", "low"} or role in EASY_ROLES:
            return CodexRoute(
                model="gpt-5.4-mini",
                reasoning_effort="low",
                tier="codex-mini",
                reason="simple or narrow-scope task",
            )

        return CodexRoute(
            model="gpt-5.5",
            reasoning_effort="medium",
            tier="codex-standard",
            reason="default medium-complexity task",
        )
    except Exception:
        return CodexRoute(
            model="gpt-5.5",
            reasoning_effort="medium",
            tier="codex-standard",
            reason="safe default after routing error",
        )


def build_native_dispatch(
    task: Any,
    *,
    role: str,
    prompt: str,
) -> CodexNativeDispatch:
    """Build a Codex ``spawn_agent`` transport without executing it.

    ``fork_turns='none'`` is load-bearing: the spawned agent receives only the
    bounded task packet rendered in ``prompt``, never the orchestrator's prior
    conversation.  Model/effort routing remains visible on the returned
    contract, but is intentionally absent from ``spawn_args`` because the
    current Codex collaboration tool has no such parameters.
    """

    task_index = _int_field(task, "index", 0)
    title = _field(task, "title", "task") or "task"
    route_input = {
        "role": role,
        "complexity": _field(task, "complexity", "medium"),
        "kind": _field(task, "kind", ""),
        "title": title,
    }
    route = route_for_task(route_input)
    task_name = _task_name(task_index, role, title)
    return CodexNativeDispatch(
        task_index=task_index,
        task_name=task_name,
        role=role,
        route=route,
        spawn_args={
            "task_name": task_name,
            "fork_turns": "none",
            "message": prompt,
        },
    )


def _field(obj: Any, name: str, default: str) -> str:
    value = obj.get(name, default) if isinstance(obj, dict) else getattr(obj, name, default)
    return value if isinstance(value, str) else default


def _int_field(obj: Any, name: str, default: int) -> int:
    value = obj.get(name, default) if isinstance(obj, dict) else getattr(obj, name, default)
    return value if isinstance(value, int) and not isinstance(value, bool) else default


def _task_name(task_index: int, role: str, title: str) -> str:
    """Return a stable collaboration task name accepted by Codex."""

    raw = f"renmark_{task_index}_{role}_{title}".lower()
    safe = re.sub(r"[^a-z0-9]+", "_", raw).strip("_")
    return (safe or f"renmark_{task_index}")[:64].rstrip("_")


def _has_hard_signal(title: str) -> bool:
    return any(signal in title for signal in ("architecture", "adversarial", "design fork", "cross-system"))

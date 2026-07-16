"""Codex model routing helpers for Renmark.

This module keeps Codex-specific model names out of the Claude-oriented
``haiku`` / ``sonnet`` / ``opus`` tier language. Callers can keep using task
complexity and subagent role, then ask this module for the Codex-native model
and reasoning-effort pair.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CodexRoute:
    """Resolved Codex model settings for a task or subagent."""

    model: str
    reasoning_effort: str
    tier: str
    reason: str


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


def _field(obj: Any, name: str, default: str) -> str:
    value = obj.get(name, default) if isinstance(obj, dict) else getattr(obj, name, default)
    return value if isinstance(value, str) else default


def _has_hard_signal(title: str) -> bool:
    return any(signal in title for signal in ("architecture", "adversarial", "design fork", "cross-system"))

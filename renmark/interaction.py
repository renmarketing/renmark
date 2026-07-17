"""Host-neutral choice menus for Claude Code and Codex.

The model-facing skills still invoke the host's selector tool.  This module
owns the deterministic parts of that interaction: exactly one recommendation,
recommended-first ordering, host option limits, and a numbered fallback that
does not confuse a missing selector with a headless session.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, replace
from typing import Any

from .hosts import HostKind, capabilities_for, resolve_host

RECOMMENDED_SUFFIX = " (Recommended)"


class ChoiceError(ValueError):
    """Raised when a choice set cannot satisfy the interaction contract."""


@dataclass(frozen=True)
class Choice:
    """One stable action shown in a host selector or numbered fallback."""

    code: str
    label: str
    description: str
    recommended: bool = False

    @property
    def display_label(self) -> str:
        """Return the visible label with one recommendation suffix at most."""
        base = self.label.removesuffix(RECOMMENDED_SUFFIX).strip()
        return f"{base}{RECOMMENDED_SUFFIX}" if self.recommended else base


def normalize_choices(choices: Iterable[Choice]) -> tuple[Choice, ...]:
    """Validate *choices* and move the sole recommendation to index zero."""
    items = tuple(choices)
    if not items:
        raise ChoiceError("at least one choice is required")
    if len({item.code.casefold() for item in items}) != len(items):
        raise ChoiceError("choice codes must be unique")
    recommended = [item for item in items if item.recommended]
    if len(recommended) != 1:
        raise ChoiceError("exactly one choice must be recommended")
    winner = recommended[0]
    return (winner, *(item for item in items if item is not winner))


def render_numbered(choices: Iterable[Choice]) -> tuple[str, ...]:
    """Render the complete recommended-first fallback list."""
    normalized = normalize_choices(choices)
    return tuple(
        f"{index}. [{item.code}] {item.display_label} — {item.description}"
        for index, item in enumerate(normalized, start=1)
    )


def build_selector(
    question: str,
    choices: Iterable[Choice],
    *,
    header: str = "Next step",
    host: str | HostKind | None = None,
    tool_available: bool | None = None,
) -> dict[str, Any]:
    """Build a host-native selector request plus a complete visible fallback.

    ``tool_available=False`` selects the numbered fallback, but deliberately
    says nothing about whether the session is headless.  The caller must use
    :mod:`renmark.headless` for that separate decision.
    """
    normalized = normalize_choices(choices)
    selected_host = resolve_host(host)
    caps = capabilities_for(selected_host)
    fallback = render_numbered(normalized)

    if tool_available is False or caps.selector_tool is None:
        return {
            "mode": "fallback",
            "host": selected_host.value,
            "question": question,
            "options": fallback,
            "reason": "selector_unavailable",
        }

    visible = normalized[: caps.selector_max_options]
    if len(normalized) > len(visible):
        stop = next((item for item in normalized if item.code.casefold() in {"n", "no"}), None)
        if stop is not None and stop not in visible:
            visible = (*visible[:-1], stop)
    # Codex request_user_input requires 2–3 options. A one-option hand-off is
    # clearer and more portable as a numbered fallback.
    if selected_host is HostKind.CODEX and len(visible) < 2:
        return {
            "mode": "fallback",
            "host": selected_host.value,
            "question": question,
            "options": fallback,
            "reason": "selector_requires_multiple_options",
        }

    option_payload = [
        {"label": item.display_label, "description": item.description}
        for item in visible
    ]
    if selected_host is HostKind.CODEX:
        arguments: dict[str, Any] = {
            "questions": [
                {
                    "header": header[:12],
                    "id": "renmark_choice",
                    "question": question,
                    "options": option_payload,
                }
            ]
        }
    else:
        arguments = {
            "questions": [
                {
                    "header": header,
                    "question": question,
                    "multiSelect": False,
                    "options": option_payload,
                }
            ]
        }

    return {
        "mode": "selector",
        "host": selected_host.value,
        "tool": caps.selector_tool,
        "arguments": arguments,
        "fallback": fallback,
        "overflow": len(normalized) > len(visible),
    }


def resolve_selection(choices: Iterable[Choice], answer: str) -> Choice | None:
    """Resolve a number, bracket code, or exact label; return ``None`` otherwise."""
    normalized = normalize_choices(choices)
    value = answer.strip().casefold()
    if value.isdigit():
        index = int(value) - 1
        return normalized[index] if 0 <= index < len(normalized) else None
    value = value.removeprefix("[").removesuffix("]")
    for item in normalized:
        if value in {item.code.casefold(), item.label.casefold(), item.display_label.casefold()}:
            return item
    return None


def with_recommendation(choices: Iterable[Choice], code: str) -> tuple[Choice, ...]:
    """Return a normalized copy with *code* as the sole recommendation."""
    wanted = code.casefold()
    items = tuple(replace(item, recommended=item.code.casefold() == wanted) for item in choices)
    if not any(item.recommended for item in items):
        raise ChoiceError(f"unknown recommended choice: {code}")
    return normalize_choices(items)

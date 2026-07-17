"""Cross-host selector and fallback contract tests."""

from __future__ import annotations

import pytest

from renmark.hosts import HostKind
from renmark.interaction import (
    Choice,
    ChoiceError,
    build_selector,
    normalize_choices,
    render_numbered,
    resolve_selection,
    with_recommendation,
)


def _choices() -> tuple[Choice, ...]:
    return (
        Choice("r", "Review", "read the plan"),
        Choice("d", "Dispatch", "execute the plan", recommended=True),
        Choice("e", "Edit", "change the plan"),
        Choice("n", "No", "stop here"),
    )


def test_normalize_requires_exactly_one_recommendation() -> None:
    with pytest.raises(ChoiceError, match="exactly one"):
        normalize_choices((Choice("a", "A", "one"), Choice("b", "B", "two")))
    with pytest.raises(ChoiceError, match="exactly one"):
        normalize_choices(
            (Choice("a", "A", "one", True), Choice("b", "B", "two", True))
        )


def test_recommendation_is_first_and_suffix_is_not_duplicated() -> None:
    choices = (
        Choice("a", "A", "one"),
        Choice("b", "B (Recommended)", "two", recommended=True),
    )
    normalized = normalize_choices(choices)
    assert normalized[0].code == "b"
    assert normalized[0].display_label == "B (Recommended)"
    assert render_numbered(choices)[0].startswith("1. [b] B (Recommended)")


def test_claude_selector_uses_four_visible_options_recommended_first() -> None:
    result = build_selector("What next?", _choices(), host=HostKind.CLAUDE_CODE)
    assert result["mode"] == "selector"
    assert result["tool"] == "AskUserQuestion"
    options = result["arguments"]["questions"][0]["options"]
    assert len(options) == 4
    assert options[0]["label"] == "Dispatch (Recommended)"
    assert result["overflow"] is False


def test_codex_selector_uses_three_options_and_keeps_full_fallback() -> None:
    result = build_selector("What next?", _choices(), host=HostKind.CODEX)
    assert result["mode"] == "selector"
    assert result["tool"] == "request_user_input"
    options = result["arguments"]["questions"][0]["options"]
    assert len(options) == 3
    assert options[0]["label"] == "Dispatch (Recommended)"
    assert options[-1]["label"] == "No"
    assert len(result["fallback"]) == 4
    assert result["overflow"] is True


def test_missing_codex_selector_is_fallback_not_headless() -> None:
    result = build_selector(
        "What next?", _choices(), host=HostKind.CODEX, tool_available=False
    )
    assert result == {
        "mode": "fallback",
        "host": "codex",
        "question": "What next?",
        "options": render_numbered(_choices()),
        "reason": "selector_unavailable",
    }
    assert "headless" not in result


def test_selection_accepts_reordered_number_and_code() -> None:
    assert resolve_selection(_choices(), "1").code == "d"  # type: ignore[union-attr]
    assert resolve_selection(_choices(), "[e]").code == "e"  # type: ignore[union-attr]
    assert resolve_selection(_choices(), "not a choice") is None


def test_with_recommendation_reorders_and_rejects_unknown_code() -> None:
    changed = with_recommendation(_choices(), "n")
    assert changed[0].code == "n"
    assert sum(item.recommended for item in changed) == 1
    with pytest.raises(ChoiceError, match="unknown recommended"):
        with_recommendation(_choices(), "missing")

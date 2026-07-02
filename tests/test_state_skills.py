"""Deterministic tests for skill-state helpers."""

from __future__ import annotations

from renmark.state.skills import context_budget_hint


def test_context_budget_hint_tiers_and_invalid_inputs() -> None:
    assert context_budget_hint(99_999) is None
    assert context_budget_hint(100_000) == "≈100k context — summarize the current stage before continuing."
    assert context_budget_hint(119_999) == "≈100k context — summarize the current stage before continuing."
    assert context_budget_hint(120_000) == "≈120k context — recommend `/compact` before the next skill."
    assert context_budget_hint(149_999) == "≈120k context — recommend `/compact` before the next skill."
    assert (
        context_budget_hint(150_000)
        == "≈150k context — strongly recommend `/compact` or a checkpoint before continuing."
    )
    assert context_budget_hint(-1) is None
    assert context_budget_hint("100000") is None
    assert context_budget_hint(True) is None


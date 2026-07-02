"""Deterministic tests for cost preview and escalation helpers."""

from __future__ import annotations

from renmark.cost import cost_band, estimate_cost, requires_escalation


def test_estimate_cost_sums_tokens_overhead_and_prices_per_tier() -> None:
    preview = estimate_cost(
        [
            {"executor": "haiku", "est_tokens": 1000},
            {"executor": "codex", "est_tokens": 2000},
            {"executor": "sonnet", "est_tokens": 3000},
        ]
    )

    assert preview.est_tokens == 26_000
    assert preview.est_cost_usd == 0.1001
    assert preview.cost_band == "medium"
    assert preview.uses_subagents is True
    assert preview.requires_expensive_model is False
    assert preview.cheaper_alternative is None


def test_haiku_only_plan_stays_low_band() -> None:
    preview = estimate_cost([{"executor": "haiku", "est_tokens": 500}])

    assert preview.cost_band == "low"
    assert preview.est_cost_usd == 0.0011
    assert preview.uses_subagents is True


def test_opus_marks_expensive_and_suggests_cheaper_alternative_on_non_hard_work() -> None:
    preview = estimate_cost([{"executor": "opus", "est_tokens": 1000, "complexity": "medium"}])

    assert preview.requires_expensive_model is True
    assert preview.cheaper_alternative is not None
    assert "sonnet/haiku" in preview.cheaper_alternative


def test_unknown_executor_and_missing_tokens_do_not_raise() -> None:
    preview = estimate_cost([{"executor": "mystery-tier"}, {"executor": None, "est_tokens": None}])

    assert preview.est_tokens == 20_000
    assert preview.est_cost_usd == 0.06
    assert preview.uses_subagents is True
    assert preview.cost_band == "low"


def test_cost_band_boundaries() -> None:
    assert cost_band(0.0999) == "low"
    assert cost_band(0.10) == "medium"
    assert cost_band(0.9999) == "medium"
    assert cost_band(1.00) == "high"


def test_requires_escalation_flags_hard_and_adversarial_review_only() -> None:
    assert requires_escalation(complexity="hard") is True
    assert requires_escalation(kind="adversarial-review") is True
    assert requires_escalation(complexity="routine", kind="doc") is False


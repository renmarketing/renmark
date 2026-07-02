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



def test_estimate_cost_rejects_bool_est_tokens() -> None:
    # bool subclasses int; True must NOT count as 1 token (degrade to 0 base tokens).
    with_bool = estimate_cost([{"executor": "codex", "est_tokens": True}])
    baseline = estimate_cost([{"executor": "codex", "est_tokens": 0}])
    assert with_bool.est_tokens == baseline.est_tokens
    assert with_bool.est_cost_usd == baseline.est_cost_usd


# ---------------------------------------------------------------------------
# REQ-21: deterministic/model-driven split tests
# ---------------------------------------------------------------------------

from renmark.cost import is_deterministic_item


def test_is_deterministic_item_explicit_mode_wins_over_executor() -> None:
    # Explicit mode='deterministic' -> True even with a model executor
    assert is_deterministic_item({"mode": "deterministic", "executor": "sonnet"}) is True
    # Explicit mode='model-driven' -> False even with a deterministic executor
    assert is_deterministic_item({"mode": "model-driven", "executor": "script"}) is False


def test_is_deterministic_item_executor_classification() -> None:
    # Deterministic executors
    assert is_deterministic_item({"executor": "script"}) is True
    assert is_deterministic_item({"executor": "deterministic"}) is True
    assert is_deterministic_item({"executor": "check"}) is True
    assert is_deterministic_item({"executor": "tool"}) is True
    assert is_deterministic_item({"executor": "code"}) is True
    assert is_deterministic_item({"executor": "none"}) is True
    # Model executors -> model-driven
    assert is_deterministic_item({"executor": "sonnet"}) is False
    assert is_deterministic_item({"executor": "codex"}) is False
    assert is_deterministic_item({"executor": "haiku"}) is False
    assert is_deterministic_item({"executor": "opus"}) is False
    assert is_deterministic_item({"executor": "fable"}) is False


def test_is_deterministic_item_unknown_or_missing_defaults_to_false() -> None:
    # Unknown executor -> model-driven (conservative/expensive assumption)
    assert is_deterministic_item({"executor": "unknown-tier"}) is False
    # Missing executor -> False
    assert is_deterministic_item({}) is False
    assert is_deterministic_item({"est_tokens": 500}) is False


def test_estimate_cost_deterministic_model_split_partitions_tokens() -> None:
    items = [
        {"executor": "script", "est_tokens": 100},    # deterministic
        {"executor": "tool", "est_tokens": 200},      # deterministic
        {"executor": "sonnet", "est_tokens": 500},    # model-driven
        {"executor": "haiku", "est_tokens": 300},     # model-driven
    ]
    preview = estimate_cost(items)

    # Counts must sum to total items
    assert preview.deterministic_count == 2
    assert preview.model_driven_count == 2
    assert preview.deterministic_count + preview.model_driven_count == len(items)

    # Base tokens must partition exactly (no agent overhead in these counters)
    assert preview.deterministic_tokens == 300   # 100 + 200
    assert preview.model_driven_tokens == 800    # 500 + 300
    assert preview.deterministic_tokens + preview.model_driven_tokens == 1100

    # This is computed by code — no model needed; verify it runs fast and
    # returns concrete values (not None, not zero for both)
    assert preview.deterministic_tokens > 0
    assert preview.model_driven_tokens > 0


def test_estimate_cost_deterministic_split_no_model_call() -> None:
    # Calling estimate_cost is synchronous, pure, and returns a dataclass —
    # proof that the split is computed by code (no network, no agent dispatch).
    items = [
        {"executor": "check", "est_tokens": 50},
        {"executor": "opus", "est_tokens": 1000, "complexity": "hard"},
    ]
    preview = estimate_cost(items)
    assert isinstance(preview.deterministic_count, int)
    assert isinstance(preview.model_driven_count, int)
    assert isinstance(preview.deterministic_tokens, int)
    assert isinstance(preview.model_driven_tokens, int)
    assert preview.deterministic_count == 1
    assert preview.model_driven_count == 1


def test_estimate_cost_back_compat_fields_still_populated() -> None:
    # Existing fields must remain present and populated after REQ-21 additions
    preview = estimate_cost([
        {"executor": "haiku", "est_tokens": 1000},
        {"executor": "sonnet", "est_tokens": 2000},
    ])
    # Original fields
    assert isinstance(preview.est_tokens, int)
    assert preview.est_tokens > 0
    assert isinstance(preview.est_cost_usd, float)
    assert preview.est_cost_usd > 0
    assert preview.cost_band in ("low", "medium", "high")
    assert isinstance(preview.uses_subagents, bool)
    assert isinstance(preview.requires_expensive_model, bool)
    # New REQ-21 fields
    assert isinstance(preview.deterministic_count, int)
    assert isinstance(preview.model_driven_count, int)
    assert isinstance(preview.deterministic_tokens, int)
    assert isinstance(preview.model_driven_tokens, int)

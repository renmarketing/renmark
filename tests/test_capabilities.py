"""---
artifact_type: test_artifact
schema_version: 1
created_at: 2026-06-12T00:00:00Z
source_sha: null
related_plan: null
generator: codex
stale_after: null
dependency_refs:
  - /home/renmark/projects/ai-system/renmark/capabilities.py
completion_state: complete
confidence: high
validation_status: pending
retry_count: 0
parser_success: true
schema_compliance: true
---

Capability routing regression tests for declared top-tier behavior.

This artifact pins default fallback behavior, `RENMARK_TOP_TIER` precedence,
section-bounded parsing, and `effective_executor` handling for `fable`.

## Summary

- Covers missing, explicit, and invalid `top_tier` declarations from `routing.md`.
- Verifies env override precedence and invalid env fallback to file state.
- Pins `effective_executor` pass-through behavior for non-`fable` executors.
- Confirms `fable` stays `fable` only when the repo declares that top tier.
- Asserts parsing stops at the next `## ` heading and ignores lower sections.
- Asserts an indented `## ` heading still terminates the Model tiers block.
- Verifies mixed-case tier values normalize for both env and file paths.
"""

from __future__ import annotations

from renmark import capabilities


def _write_routing(tmp_path, content: str) -> None:
    routing_path = tmp_path / ".renmark" / "memory" / "routing.md"
    routing_path.parent.mkdir(parents=True, exist_ok=True)
    routing_path.write_text(content, encoding="utf-8")


def test_absent_routing_defaults_to_opus(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("RENMARK_TOP_TIER", raising=False)

    assert capabilities.top_tier(tmp_path) == "opus"
    assert capabilities.is_top_tier_declared(tmp_path) is False


def test_declared_fable_sets_top_tier_and_declaration_flag(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("RENMARK_TOP_TIER", raising=False)
    _write_routing(
        tmp_path,
        "# Routing\n\n## Model tiers\n\ntop_tier: fable\n",
    )

    assert capabilities.top_tier(tmp_path) == "fable"
    assert capabilities.is_top_tier_declared(tmp_path) is True


def test_explicit_opus_stays_opus(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("RENMARK_TOP_TIER", raising=False)
    _write_routing(
        tmp_path,
        "## Model tiers\ntop_tier: opus\n",
    )

    assert capabilities.top_tier(tmp_path) == "opus"
    assert capabilities.is_top_tier_declared(tmp_path) is False


def test_invalid_file_value_falls_back_to_opus(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("RENMARK_TOP_TIER", raising=False)
    _write_routing(
        tmp_path,
        "## Model tiers\ntop_tier: gpt9\n",
    )

    assert capabilities.top_tier(tmp_path) == "opus"
    assert capabilities.is_top_tier_declared(tmp_path) is False


def test_env_override_beats_file_and_invalid_env_falls_through(monkeypatch, tmp_path) -> None:
    _write_routing(
        tmp_path,
        "## Model tiers\ntop_tier: opus\n",
    )

    monkeypatch.setenv("RENMARK_TOP_TIER", "fable")
    assert capabilities.top_tier(tmp_path) == "fable"
    assert capabilities.is_top_tier_declared(tmp_path) is True

    monkeypatch.setenv("RENMARK_TOP_TIER", "gpt9")
    assert capabilities.top_tier(tmp_path) == "opus"
    assert capabilities.is_top_tier_declared(tmp_path) is False


def test_effective_executor_handles_passthrough_and_fable_resolution(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("RENMARK_TOP_TIER", raising=False)

    for executor in ("haiku", "codex", "sonnet", "opus"):
        assert capabilities.effective_executor(executor, tmp_path) == executor

    assert capabilities.effective_executor("fable", tmp_path) == "opus"

    _write_routing(
        tmp_path,
        "## Model tiers\ntop_tier: fable\n",
    )

    assert capabilities.effective_executor("fable", tmp_path) == "fable"


def test_model_tiers_parsing_stops_at_next_heading(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("RENMARK_TOP_TIER", raising=False)
    _write_routing(
        tmp_path,
        "# Routing\n\n## Model tiers\ntop_tier: fable\n## Learned overrides\ntop_tier: opus\n",
    )

    assert capabilities.read_tiers(tmp_path) == {"top_tier": "fable"}
    assert capabilities.top_tier(tmp_path) == "fable"
    assert capabilities.is_top_tier_declared(tmp_path) is True


def test_model_tiers_parsing_stops_at_indented_heading(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("RENMARK_TOP_TIER", raising=False)
    _write_routing(
        tmp_path,
        "# Routing\n\n## Model tiers\ntop_tier: opus\n  ## Learned overrides\ntop_tier: fable\n",
    )

    assert capabilities.read_tiers(tmp_path) == {"top_tier": "opus"}
    assert capabilities.top_tier(tmp_path) == "opus"
    assert capabilities.is_top_tier_declared(tmp_path) is False


def test_mixed_case_env_value_normalizes(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("RENMARK_TOP_TIER", "FABLE")
    assert capabilities.top_tier(tmp_path) == "fable"
    assert capabilities.is_top_tier_declared(tmp_path) is True

    monkeypatch.setenv("RENMARK_TOP_TIER", "  Opus  ")
    assert capabilities.top_tier(tmp_path) == "opus"
    assert capabilities.is_top_tier_declared(tmp_path) is False


def test_mixed_case_file_value_normalizes(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("RENMARK_TOP_TIER", raising=False)
    _write_routing(
        tmp_path,
        "## Model tiers\ntop_tier: Fable\n",
    )

    assert capabilities.top_tier(tmp_path) == "fable"
    assert capabilities.is_top_tier_declared(tmp_path) is True
    assert capabilities.effective_executor("fable", tmp_path) == "fable"

# ---
# artifact_type: test
# schema_version: 1
# created_at: 2026-08-05T00:00:00Z
# source_sha: cb0f960e54489d1ad94611ee3757c22d5713bca0
# related_plan: task-6-lens-policy-tests
# generator: codex
# dependency_refs:
#   - renmark.subagent_gate.resolve_lens_for
#   - renmark.subagent_gate.LENS_NAMES
# ---

from types import SimpleNamespace

from renmark.subagent_gate import LENS_NAMES, resolve_lens_for


def test_resolve_lens_for_none_returns_maintainer_and_is_known_lens():
    result = resolve_lens_for(None)

    assert result == "maintainer"
    assert result in LENS_NAMES


def test_resolve_lens_for_high_risk_uses_skeptical_user_and_is_known_lens():
    work_order = SimpleNamespace(risk_tier="high")

    result = resolve_lens_for(work_order)

    assert result == "skeptical_user"
    assert result in LENS_NAMES


def test_resolve_lens_for_critical_risk_uses_skeptical_user_and_is_known_lens():
    work_order = SimpleNamespace(risk_tier="critical")

    result = resolve_lens_for(work_order)

    assert result == "skeptical_user"
    assert result in LENS_NAMES


def test_resolve_lens_for_medium_risk_multi_file_scope_uses_competitor_and_is_known_lens():
    work_order = SimpleNamespace(risk_tier="medium", file_scope=["a.py", "b.py"])

    result = resolve_lens_for(work_order)

    assert result == "competitor"
    assert result in LENS_NAMES


def test_resolve_lens_for_low_risk_uses_maintainer_and_is_known_lens():
    work_order = SimpleNamespace(risk_tier="low")

    result = resolve_lens_for(work_order)

    assert result == "maintainer"
    assert result in LENS_NAMES


# ## Summary
# - Covers the None case plus high, critical, medium multi-file, and low risk tiers.
# - Uses duck-typed SimpleNamespace fixtures instead of importing ledger work-order types.
# - Asserts every tested result is a member of `LENS_NAMES`.

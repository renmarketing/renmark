"""Regression checks for the shared managed-project delivery contract."""

from __future__ import annotations

from pathlib import Path

CONTRACT = (
    Path(__file__).resolve().parents[1]
    / "plugin/skills/.shared/project-delivery-contract.md"
)


def _contract() -> str:
    return " ".join(CONTRACT.read_text(encoding="utf-8").casefold().split())


def test_contract_defines_complementary_agency_and_orchestrator_paths() -> None:
    text = _contract()

    assert "agency" in text
    assert "owner-facing project engagement" in text
    assert "orchestrator" in text
    assert "defined, approved milestone" in text
    assert "agency drives orchestrator" in text


def test_contract_requires_outcomes_evidence_and_bounded_repair() -> None:
    text = _contract()

    for clause in (
        "demonstrable owner outcome",
        "acceptance criteria",
        "surface drift as a human decision",
        "deterministic, fresh evidence",
        "focused verifier",
        "acceptance evidence",
        "bounded, scoped repair attempts",
        "re-verification and independent re-review",
        "stop rather than expand scope",
    ):
        assert clause in text


def test_contract_keeps_coordinator_inputs_pointer_only_and_excludes_payloads() -> None:
    text = _contract()

    assert "bounded package summaries and pointers" in text
    assert "never full skill bodies, transcripts" in text
    assert "deterministic-first.md" in text
    assert "workflow-fanout.md" in text
    assert "subagent-profiles.md" in text
    assert "```" not in text
    assert "user:" not in text
    assert "assistant:" not in text


def test_contract_persists_state_and_preserves_human_gates() -> None:
    text = _contract()

    assert ".renmark/state/" in text
    assert "not conversation history" in text
    assert "approval/signoff" in text
    assert "merge, release" in text
    assert "passing tests alone never clear an owner gate" in text


def test_contract_describes_equivalent_host_fallback_without_host_specific_words() -> None:
    text = _contract()

    assert "native picker" in text
    assert "numbered fallback" in text
    assert "recommended safe option first" in text
    assert "different decision or an automatic approval" in text

"""Unit tests for renmark.headless (P10 — headless gate-resolution contract)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from renmark import headless, lifecycle

# ── resolve_gate: not headless → interactive ──────────────────────────────────


def test_not_headless_returns_interactive(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """RENMARK_HEADLESS=0, tool_available None → interactive envelope, exactly."""
    monkeypatch.setenv("RENMARK_HEADLESS", "0")
    env = headless.resolve_gate(tmp_path, "verify", kind="safe", tool_available=None)
    assert env == {"mode": "interactive"}


# ── resolve_gate: headless + safe → auto-pick recommended ─────────────────────


def test_headless_safe_auto_picks_recommended(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """RENMARK_HEADLESS=1 + kind='safe' → success/auto_picked_recommended, recommended echoed."""
    monkeypatch.setenv("RENMARK_HEADLESS", "1")
    env = headless.resolve_gate(tmp_path, "next-step", kind="safe", recommended="/renmark:verify")
    assert env == {
        "status": "success",
        "mode": "headless",
        "gate": "next-step",
        "decision": "auto_picked_recommended",
        "human_review_required": False,
        "artifacts": [],
        "recommended": "/renmark:verify",
    }


# ── resolve_gate: headless + dangerous → halt for human review ────────────────


def test_headless_dangerous_halts_and_writes_artifact(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """RENMARK_HEADLESS=1 + kind='dangerous' gate='merge' → needs_input; decision
    artifact written; lifecycle gate armed for 'merge'."""
    monkeypatch.setenv("RENMARK_HEADLESS", "1")
    env = headless.resolve_gate(
        tmp_path,
        "merge",
        kind="dangerous",
        originating_skill="finish",
        what="merge approval",
    )
    assert env["status"] == "needs_input"
    assert env["mode"] == "headless"
    assert env["gate"] == "merge"
    assert env["decision"] == "halted_for_human_review"
    assert env["human_review_required"] is True
    assert env["artifacts"] == [".renmark/decisions/merge-approval.json"]

    decision_path = tmp_path / ".renmark" / "decisions" / "merge-approval.json"
    assert decision_path.exists()
    payload = json.loads(decision_path.read_text())
    assert payload["gate"] == "merge"

    state = lifecycle.read_lifecycle(tmp_path)
    assert state is not None
    assert state.human_review_required is True
    assert state.human_review_for == "merge"


# ── selector availability is independent from headless detection ─────────────


def test_tool_unavailable_does_not_force_headless_safe(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A missing selector uses fallback UI; it does not make the run headless."""
    monkeypatch.delenv("RENMARK_HEADLESS", raising=False)
    env = headless.resolve_gate(
        tmp_path, "next-step", kind="safe", recommended="/renmark:verify", tool_available=False
    )
    assert env == {"mode": "interactive"}


def test_tool_unavailable_does_not_force_headless_dangerous(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A missing selector alone does not arm a dangerous human-review gate."""
    monkeypatch.delenv("RENMARK_HEADLESS", raising=False)
    env = headless.resolve_gate(
        tmp_path, "merge", kind="dangerous", originating_skill="finish", tool_available=False
    )
    assert env == {"mode": "interactive"}
    assert lifecycle.read_lifecycle(tmp_path) is None


# ── resolve_gate: tool_available True/None does NOT force headless ────────────


def test_tool_available_true_does_not_force_headless(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Not headless + tool_available=True → interactive (does not force headless)."""
    monkeypatch.setenv("RENMARK_HEADLESS", "0")
    env = headless.resolve_gate(tmp_path, "verify", kind="safe", tool_available=True)
    assert env == {"mode": "interactive"}


def test_tool_available_none_does_not_force_headless(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Not headless + tool_available=None (unknown) → interactive."""
    monkeypatch.delenv("RENMARK_HEADLESS", raising=False)
    env = headless.resolve_gate(tmp_path, "verify", kind="safe", tool_available=None)
    assert env == {"mode": "interactive"}


# ── resolve_gate: unknown kind fails safe (halts) ─────────────────────────────


def test_unknown_kind_headless_fails_safe(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """An unrecognised kind under headless must halt for human review, never
    auto-approve — fail safe."""
    monkeypatch.setenv("RENMARK_HEADLESS", "1")
    env = headless.resolve_gate(tmp_path, "release", kind="weird", originating_skill="finish")
    assert env["status"] == "needs_input"
    assert env["decision"] == "halted_for_human_review"
    assert env["gate"] == "release"

    state = lifecycle.read_lifecycle(tmp_path)
    assert state is not None
    assert state.human_review_required is True
    assert state.human_review_for == "release"


# ── render_return: prose per status ───────────────────────────────────────────


def test_render_return_success_starts_with_result() -> None:
    env = {
        "status": "success",
        "mode": "headless",
        "gate": "next-step",
        "decision": "auto_picked_recommended",
        "recommended": "/renmark:verify",
    }
    line = headless.render_return(env)
    assert line.startswith("result:")


def test_render_return_needs_input_starts_with_needs_input() -> None:
    env = {"status": "needs_input", "mode": "headless", "gate": "merge"}
    line = headless.render_return(env)
    assert line.startswith("needs input:")
    assert "merge" in line


def test_render_return_failed_starts_with_failed() -> None:
    line = headless.render_return({"status": "failed", "reason": "x"})
    assert line.startswith("failed:")
    assert "x" in line


def test_render_return_interactive_is_empty() -> None:
    assert headless.render_return({"mode": "interactive"}) == ""

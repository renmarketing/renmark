"""Structural guards for the host-neutral selector contract."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "plugin" / "skills"


def test_shared_handoff_contract_names_both_host_selectors() -> None:
    text = (SKILLS / ".shared" / "handoff-menu.md").read_text(encoding="utf-8")
    assert "AskUserQuestion" in text
    assert "request_user_input" in text
    assert "exactly one option `recommended=True`" in text
    assert "recommendation to index 0" in text
    assert "Selector unavailability alone does **not** make the session" in text


def test_all_skill_selector_sites_inherit_or_call_shared_adapter() -> None:
    for path in SKILLS.glob("*/SKILL.md"):
        text = path.read_text(encoding="utf-8")
        if "AskUserQuestion" not in text and "request_user_input" not in text:
            continue
        assert any(
            marker in text
            for marker in (
                "renmark.interaction.build_selector",
                "handoff-menu.md",
                "next-steps.md",
            )
        ), f"{path} has a host-specific selector site without the shared adapter"


def test_plan_dispatch_and_finish_lane_recommendations_are_first_and_unique() -> None:
    plan = (SKILLS / "plan" / "SKILL.md").read_text(encoding="utf-8")
    assert "1. [d] Dispatch (Recommended)" in plan
    assert "2. [r] Review" in plan

    finish = (SKILLS / "finish" / "SKILL.md").read_text(encoding="utf-8")
    assert "1. <recommended> (Recommended)" in finish
    assert "5. <recommended> (Recommended)" not in finish


def test_guide_codex_interruption_path_avoids_clear_and_resume_commands() -> None:
    guide = (SKILLS / "guide" / "SKILL.md").read_text(encoding="utf-8")
    assert "Continue an interrupted workflow" in guide
    assert "Codex: continue directly from `.renmark/state/`" in guide
    assert "Never ask a Codex user to run `/clear` or `/resume`" in guide

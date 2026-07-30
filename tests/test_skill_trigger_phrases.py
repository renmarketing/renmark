"""Natural-language trigger coverage shared by Claude Code and Codex."""

from __future__ import annotations

from pathlib import Path

from renmark.lint import parse_frontmatter

PLUGIN_ROOT = Path(__file__).resolve().parents[1] / "plugin"


def _description(skill: str, surface: str = "skills") -> str:
    path = (
        PLUGIN_ROOT / "skills" / skill / "SKILL.md"
        if surface == "skills"
        else PLUGIN_ROOT / "commands" / f"{skill}.md"
    )
    frontmatter = parse_frontmatter(
        path.read_text(encoding="utf-8")
    )
    assert frontmatter is not None
    return frontmatter["description"]


def test_exact_plan_dispatch_and_loop_phrases_are_registered() -> None:
    assert "plan this" in _description("plan")
    assert "dispatch this" in _description("orchestrate")
    assert "loop this" in _description("loop")


def test_primary_entry_phrases_match_on_skill_and_command_surfaces() -> None:
    matrix = {
        "start": ("build x", "create x", "use agency", "use orchestrator"),
        "feature": ("add x", "implement x", "change x"),
        "debug": ("fix x", "why is x failing", "investigate the error"),
        "init": ("adopt renmark", "set renmark up here"),
        "resume": ("where was i", "pick up where i left off"),
    }

    for skill, phrases in matrix.items():
        for surface in ("skills", "commands"):
            description = _description(skill, surface).lower()
            for phrase in phrases:
                assert phrase in description, (skill, surface, phrase)


def test_entry_descriptions_never_expose_conductor_as_public_choice() -> None:
    for skill in ("start", "feature", "debug", "init", "resume"):
        for surface in ("skills", "commands"):
            description = _description(skill, surface).lower()
            assert "conductor" not in description
            assert "status" not in description

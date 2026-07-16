"""Natural-language trigger coverage shared by Claude Code and Codex."""

from __future__ import annotations

from pathlib import Path

from renmark.lint import parse_frontmatter

PLUGIN_ROOT = Path(__file__).resolve().parents[1] / "plugin"


def _description(skill: str) -> str:
    frontmatter = parse_frontmatter(
        (PLUGIN_ROOT / "skills" / skill / "SKILL.md").read_text(encoding="utf-8")
    )
    assert frontmatter is not None
    return frontmatter["description"]


def test_exact_plan_dispatch_and_loop_phrases_are_registered() -> None:
    assert "plan this" in _description("plan")
    assert "dispatch this" in _description("orchestrate")
    assert "loop this" in _description("loop")

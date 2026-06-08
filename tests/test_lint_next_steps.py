"""Tests for renmark.lint.lint_next_steps_citation — the hand-off contract pass.

Every shipped skill must point the user at a next move (cite ``next-steps.md``)
or, for gate skills, ``handoff-menu.md``. Skills that cite neither are dead ends.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from renmark import lint


# ── synthetic plugin fixture builder ─────────────────────────────────────────


def _make_plugin(tmp_path: Path, skills: dict[str, str] | None = None) -> Path:
    """Build a minimal synthetic plugin/ dir with skills/<name>/SKILL.md files."""
    plugin_dir = tmp_path / "plugin"
    (plugin_dir / "skills").mkdir(parents=True)
    for name, body in (skills or {}).items():
        (plugin_dir / "skills" / name).mkdir(parents=True)
        (plugin_dir / "skills" / name / "SKILL.md").write_text(body, encoding="utf-8")
    return plugin_dir


def _skill_body(name: str, *, citation: str = "") -> str:
    """SKILL.md body that optionally cites a hand-off contract file."""
    tail = f"\nSee _shared/{citation} for what to do next.\n" if citation else "\n"
    return f"---\nname: {name}\ndescription: a skill for {name}\n---\n\n# {name}\n{tail}"


# ── synthetic fixtures ───────────────────────────────────────────────────────


def test_cites_next_steps_no_issue(tmp_path: Path):
    """A skill citing next-steps.md satisfies the contract."""
    plugin = _make_plugin(tmp_path, skills={"plan": _skill_body("plan", citation="next-steps.md")})
    assert lint.lint_next_steps_citation(plugin) == []


def test_cites_handoff_menu_no_issue(tmp_path: Path):
    """Gate skills satisfy the contract via handoff-menu.md instead."""
    plugin = _make_plugin(tmp_path, skills={"start": _skill_body("start", citation="handoff-menu.md")})
    assert lint.lint_next_steps_citation(plugin) == []


def test_cites_neither_one_issue_naming_skill(tmp_path: Path):
    """A skill citing neither contract yields exactly one issue naming the skill."""
    plugin = _make_plugin(tmp_path, skills={"deadend": _skill_body("deadend")})
    issues = lint.lint_next_steps_citation(plugin)
    assert len(issues) == 1
    assert "deadend" in issues[0]


def test_skips_underscore_shared_dir(tmp_path: Path):
    """`_shared/` holds reference files, not skills — an uncited *.md there must
    not produce an issue."""
    plugin = _make_plugin(tmp_path, skills={"plan": _skill_body("plan", citation="next-steps.md")})
    shared = plugin / "skills" / "_shared"
    shared.mkdir()
    (shared / "scope-contract.md").write_text("# shared reference, no citation\n", encoding="utf-8")
    assert lint.lint_next_steps_citation(plugin) == []


def test_multiple_skills_only_offender_flagged(tmp_path: Path):
    """With a mix, only the uncited skill is flagged."""
    plugin = _make_plugin(
        tmp_path,
        skills={
            "good": _skill_body("good", citation="next-steps.md"),
            "gate": _skill_body("gate", citation="handoff-menu.md"),
            "bad": _skill_body("bad"),
        },
    )
    issues = lint.lint_next_steps_citation(plugin)
    assert len(issues) == 1
    assert "bad" in issues[0]


# ── live guard ───────────────────────────────────────────────────────────────


def test_live_real_plugin_every_skill_cites_contract():
    """Live guard: every shipped renmark skill must cite the hand-off contract.

    Resolves the real plugin/ relative to this test file so it works regardless
    of the pytest invocation cwd. If this finds a real gap, that is a genuine
    failure — do not weaken the assertion to force green.
    """
    real_plugin = Path(__file__).resolve().parent.parent / "plugin"
    if not real_plugin.exists():
        pytest.skip("not running from repo root")
    issues = lint.lint_next_steps_citation(real_plugin)
    assert issues == [], "every shipped skill must cite next-steps.md/handoff-menu.md:\n  " + "\n  ".join(issues)

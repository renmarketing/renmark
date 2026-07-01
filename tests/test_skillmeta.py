"""Tests for renmark.skillmeta — the per-skill metadata registry (P7).

The registry (`SKILLS`) is the single source of truth for structural facts about
each `plugin/skills/<name>/SKILL.md`. These tests pin the registry against the
SKILL.md files on disk so it cannot silently drift: every skill dir is covered
(no missing / phantom entries), the fields are valid, and the two
"matches reality" contracts — `disable_model_invocation` vs the frontmatter flag,
and `cites` vs the body references — hold.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from renmark import lifecycle, skillmeta

# ── locate the live SKILL.md files ────────────────────────────────────────────

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SKILLS_DIR = _REPO_ROOT / "plugin" / "skills"

_KNOWN_DOMAINS = {"build", "debug", "audit", "meta"}
_KNOWN_BLOCKS = {"reasoning-contract", "next-steps", "handoff-menu"}


def _skill_dirs() -> list[str]:
    """Every `plugin/skills/<name>/` dir that actually contains a SKILL.md."""
    return sorted(
        p.parent.name
        for p in _SKILLS_DIR.glob("*/SKILL.md")
    )


def _split_frontmatter(text: str) -> str:
    """Return the YAML frontmatter block (between the leading `---` fences)."""
    if not text.startswith("---"):
        return ""
    parts = text.split("---", 2)
    # parts[0] == "" (before first fence), parts[1] == frontmatter, parts[2] == body
    return parts[1] if len(parts) >= 3 else ""


def _frontmatter_disables_invocation(skill: str) -> bool:
    """True iff this SKILL.md frontmatter declares `disable-model-invocation: true`."""
    text = (_SKILLS_DIR / skill / "SKILL.md").read_text(encoding="utf-8")
    fm = _split_frontmatter(text)
    for line in fm.splitlines():
        stripped = line.strip()
        if stripped.startswith("disable-model-invocation:"):
            value = stripped.split(":", 1)[1].strip().lower()
            return value == "true"
    return False


def _skill_body(skill: str) -> str:
    return (_SKILLS_DIR / skill / "SKILL.md").read_text(encoding="utf-8")


_SKILL_NAMES = _skill_dirs()


# ── 1. completeness: registry == SKILL.md dirs (no missing, no phantom) ───────


def test_skill_dirs_exist() -> None:
    """Sanity: we actually found SKILL.md files to test against."""
    assert _SKILL_NAMES, f"no SKILL.md dirs found under {_SKILLS_DIR}"


def test_every_skill_dir_has_a_registry_entry() -> None:
    missing = set(_SKILL_NAMES) - set(skillmeta.SKILLS)
    assert not missing, f"SKILL.md dirs with no SKILLS entry: {sorted(missing)}"


def test_no_phantom_registry_entries() -> None:
    phantom = set(skillmeta.SKILLS) - set(_SKILL_NAMES)
    assert not phantom, f"SKILLS entries with no SKILL.md dir: {sorted(phantom)}"


# ── 2. field validity ─────────────────────────────────────────────────────────


@pytest.mark.parametrize("skill", sorted(skillmeta.SKILLS))
def test_next_steps_class_in_range(skill: str) -> None:
    assert skillmeta.SKILLS[skill].next_steps_class in {1, 2, 3}


@pytest.mark.parametrize("skill", sorted(skillmeta.SKILLS))
def test_domain_is_known(skill: str) -> None:
    assert skillmeta.SKILLS[skill].domain in _KNOWN_DOMAINS


@pytest.mark.parametrize("skill", sorted(skillmeta.SKILLS))
def test_cites_subset_of_known_blocks(skill: str) -> None:
    cites = set(skillmeta.SKILLS[skill].cites)
    assert cites <= _KNOWN_BLOCKS, f"{skill} cites unknown block(s): {cites - _KNOWN_BLOCKS}"


@pytest.mark.parametrize("skill", sorted(skillmeta.SKILLS))
def test_cites_has_no_duplicates(skill: str) -> None:
    cites = skillmeta.SKILLS[skill].cites
    assert len(cites) == len(set(cites)), f"{skill} has duplicate cites: {cites}"


# ── 3. disable_model_invocation matches the SKILL.md frontmatter (lint contract)


@pytest.mark.parametrize("skill", _SKILL_NAMES)
def test_disable_model_invocation_matches_frontmatter(skill: str) -> None:
    meta = skillmeta.SKILLS[skill]
    actual = _frontmatter_disables_invocation(skill)
    assert meta.disable_model_invocation == actual, (
        f"{skill}: registry disable_model_invocation={meta.disable_model_invocation} "
        f"but SKILL.md frontmatter says {actual}"
    )


# ── 4. cites match reality: every cited block is referenced in the body ───────


@pytest.mark.parametrize("skill", _SKILL_NAMES)
def test_cites_appear_in_skill_body(skill: str) -> None:
    body = _skill_body(skill)
    for block in skillmeta.SKILLS[skill].cites:
        assert f"{block}.md" in body, (
            f"{skill} cites {block!r} but SKILL.md never references {block}.md"
        )


# ── 5. get(): None for unknown, SkillMeta for known, never raises ─────────────


def test_get_unknown_returns_none() -> None:
    assert skillmeta.get("definitely-not-a-skill") is None


def test_get_known_returns_skillmeta() -> None:
    known = _SKILL_NAMES[0]
    result = skillmeta.get(known)
    assert isinstance(result, skillmeta.SkillMeta)
    assert result is skillmeta.SKILLS[known]


def test_get_non_string_does_not_raise() -> None:
    # Documented contract: get() never raises, even on a non-string key.
    assert skillmeta.get(None) is None  # type: ignore[arg-type]
    assert skillmeta.get(123) is None  # type: ignore[arg-type]


# ── 6. cross-check: lifecycle.domain_for_skill agrees with the registry ───────


@pytest.mark.parametrize(
    "skill",
    ["start", "feature", "debug", "codereview", "audit", "inventory", "help", "roadmap"],
)
def test_lifecycle_domain_agrees_with_registry(skill: str) -> None:
    assert lifecycle.domain_for_skill(skill) == skillmeta.SKILLS[skill].domain

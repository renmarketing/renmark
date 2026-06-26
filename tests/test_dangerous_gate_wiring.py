"""Guard test for P10 dangerous-gate headless wiring in SKILL.md files.

Pure file-content checks: each gated skill must reference the headless
dangerous-gate resolver (`resolve_gate` + `kind="dangerous"`) so the wiring
cannot silently regress. We do NOT import or run the skills.
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

GATED_SKILLS = [
    "plugin/skills/finish/SKILL.md",
    "plugin/skills/plan/SKILL.md",
    "plugin/skills/orchestrate/SKILL.md",
    "plugin/skills/prd/SKILL.md",
]


@pytest.mark.parametrize("rel_path", GATED_SKILLS)
def test_skill_wires_dangerous_gate(rel_path: str) -> None:
    """Each gated SKILL.md must reference resolve_gate + kind="dangerous"."""
    text = (REPO_ROOT / rel_path).read_text(encoding="utf-8")
    assert "resolve_gate" in text, f"{rel_path} missing resolve_gate wiring"
    assert 'kind="dangerous"' in text, f"{rel_path} missing kind=\"dangerous\" gate"


def test_prd_has_two_approval_gates() -> None:
    """prd has two approval gates → at least 2 resolve_gate occurrences."""
    text = (REPO_ROOT / "plugin/skills/prd/SKILL.md").read_text(encoding="utf-8")
    assert text.count("resolve_gate") >= 2, "prd must wire two resolve_gate calls"

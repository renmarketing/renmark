"""Central per-skill metadata registry — single source of truth for P7.

Each ``plugin/skills/<name>/SKILL.md`` has a small set of structural facts that
several P7 consumers (template scaffolding, lint, doc generation) need to agree
on: which domain it belongs to, which ``_shared`` contract fragments it cites,
whether it renders a hand-off menu, whether it is hidden from model invocation,
and which next-steps class drives its menu rendering.

Rather than re-deriving these by re-grepping the SKILL.md files at every call
site (slow, and prone to drift between consumers), they are captured once here
as a frozen registry. The values were harvested by inspecting each SKILL.md:

- ``domain`` seeds from ``lifecycle.DOMAIN_BY_SKILL`` (default ``"build"``).
- ``cites`` is the subset of the three ``_shared`` contract files the SKILL.md
  text references: ``"reasoning-contract"``, ``"next-steps"``, ``"handoff-menu"``.
- ``has_handoff`` is True when the skill cites ``handoff-menu`` or otherwise
  drives a hand-off / next-steps menu.
- ``disable_model_invocation`` mirrors the SKILL.md frontmatter flag.
- ``next_steps_class`` is the class declared in the SKILL.md next-steps
  citation: 1 = pipeline (Tier-0 stage routing), 2 = quality gate (defers to
  the gate sub-menu), 3 = aux / terminal (resume-pipeline). See
  ``plugin/skills/_shared/next-steps.md`` for the canonical definition.

Design constraints (matching ``renmark/config.py`` / ``renmark/lifecycle.py``):
- stdlib-only, frozen dataclass, ``from __future__ import annotations``.
- ``get()`` never raises — an unknown skill returns ``None``.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SkillMeta:
    """Structural metadata for one renmark skill (one SKILL.md)."""

    domain: str
    next_steps_class: int  # 1 = pipeline, 2 = quality gate, 3 = aux / terminal
    cites: tuple[str, ...]  # subset of reasoning-contract / next-steps / handoff-menu
    has_handoff: bool
    disable_model_invocation: bool


# One entry per skill directory under ``plugin/skills/``. Key == skill name ==
# directory name. Harvested from each SKILL.md (frontmatter + body grep) and the
# domain seed in ``lifecycle.DOMAIN_BY_SKILL``.
SKILLS: dict[str, SkillMeta] = {
    "analytics": SkillMeta(
        domain="meta",
        next_steps_class=3,
        cites=("next-steps", "handoff-menu"),
        has_handoff=True,
        disable_model_invocation=True,
    ),
    "approve": SkillMeta(
        domain="meta",
        next_steps_class=3,
        cites=("next-steps", "handoff-menu"),
        has_handoff=True,
        disable_model_invocation=True,
    ),
    "audit": SkillMeta(
        domain="audit",
        next_steps_class=3,
        cites=("reasoning-contract", "next-steps", "handoff-menu"),
        has_handoff=True,
        disable_model_invocation=True,
    ),
    "backlog": SkillMeta(
        domain="build",
        next_steps_class=3,
        cites=("next-steps", "handoff-menu"),
        has_handoff=True,
        disable_model_invocation=False,
    ),
    "blueprint": SkillMeta(
        domain="build",
        next_steps_class=1,
        cites=("next-steps", "handoff-menu"),
        has_handoff=True,
        disable_model_invocation=False,
    ),
    "brainstorm": SkillMeta(
        domain="build",
        next_steps_class=1,
        cites=("reasoning-contract", "next-steps", "handoff-menu"),
        has_handoff=True,
        disable_model_invocation=False,
    ),
    "check-plan": SkillMeta(
        domain="build",
        next_steps_class=1,
        cites=("next-steps", "handoff-menu"),
        has_handoff=True,
        disable_model_invocation=True,
    ),
    "codereview": SkillMeta(
        domain="debug",
        next_steps_class=2,  # quality gate — defers to the gate sub-menu
        cites=("reasoning-contract", "handoff-menu"),
        has_handoff=True,
        disable_model_invocation=False,
    ),
    "debug": SkillMeta(
        domain="debug",
        next_steps_class=3,
        cites=("next-steps", "handoff-menu"),
        has_handoff=True,
        disable_model_invocation=False,
    ),
    "doctor": SkillMeta(
        domain="meta",
        next_steps_class=3,
        cites=("next-steps", "handoff-menu"),
        has_handoff=True,
        disable_model_invocation=True,
    ),
    "feature": SkillMeta(
        domain="build",
        next_steps_class=1,
        cites=("next-steps", "handoff-menu"),
        has_handoff=True,
        disable_model_invocation=False,
    ),
    "finish": SkillMeta(
        domain="build",
        next_steps_class=1,
        cites=("reasoning-contract", "next-steps", "handoff-menu"),
        has_handoff=True,
        disable_model_invocation=False,
    ),
    "guide": SkillMeta(
        domain="meta",
        next_steps_class=3,
        cites=("next-steps",),
        has_handoff=True,
        disable_model_invocation=False,
    ),
    "help": SkillMeta(
        domain="meta",
        next_steps_class=3,
        cites=("next-steps",),
        has_handoff=True,
        disable_model_invocation=True,
    ),
    "hygiene": SkillMeta(
        domain="meta",
        next_steps_class=3,
        cites=("next-steps", "handoff-menu"),
        has_handoff=True,
        disable_model_invocation=True,
    ),
    "init": SkillMeta(
        domain="meta",
        next_steps_class=3,
        cites=("next-steps", "handoff-menu"),
        has_handoff=True,
        disable_model_invocation=False,
    ),
    "inventory": SkillMeta(
        domain="audit",
        next_steps_class=3,
        cites=("next-steps", "handoff-menu"),
        has_handoff=True,
        disable_model_invocation=True,
    ),
    "loop": SkillMeta(
        domain="build",
        next_steps_class=1,
        cites=("next-steps", "handoff-menu"),
        has_handoff=True,
        disable_model_invocation=False,
    ),
    "orchestrate": SkillMeta(
        domain="build",
        next_steps_class=1,
        cites=("reasoning-contract", "next-steps", "handoff-menu"),
        has_handoff=True,
        disable_model_invocation=False,
    ),
    "plan": SkillMeta(
        domain="build",
        next_steps_class=1,
        cites=("next-steps", "handoff-menu"),
        has_handoff=True,
        disable_model_invocation=False,
    ),
    "prd": SkillMeta(
        domain="build",
        next_steps_class=1,
        cites=("reasoning-contract", "next-steps", "handoff-menu"),
        has_handoff=True,
        disable_model_invocation=False,
    ),
    "resume": SkillMeta(
        domain="meta",
        next_steps_class=3,
        cites=("next-steps", "handoff-menu"),
        has_handoff=True,
        disable_model_invocation=True,
    ),
    "roadmap": SkillMeta(
        domain="meta",
        next_steps_class=3,
        cites=("reasoning-contract", "next-steps", "handoff-menu"),
        has_handoff=True,
        disable_model_invocation=False,
    ),
    "scan": SkillMeta(
        domain="audit",
        next_steps_class=3,
        cites=("next-steps", "handoff-menu"),
        has_handoff=True,
        disable_model_invocation=True,
    ),
    "setup": SkillMeta(
        domain="meta",
        next_steps_class=3,
        cites=("next-steps", "handoff-menu"),
        has_handoff=True,
        disable_model_invocation=False,
    ),
    "start": SkillMeta(
        domain="build",
        next_steps_class=1,
        cites=("next-steps", "handoff-menu"),
        has_handoff=True,
        disable_model_invocation=False,
    ),
    "usage": SkillMeta(
        domain="meta",
        next_steps_class=3,
        cites=("next-steps", "handoff-menu"),
        has_handoff=True,
        disable_model_invocation=True,
    ),
    "verify": SkillMeta(
        domain="build",
        next_steps_class=2,  # quality gate — verify is class 2, NOT a pipeline skill
        cites=("reasoning-contract", "handoff-menu"),
        has_handoff=True,
        disable_model_invocation=False,
    ),
}


def get(skill: str) -> SkillMeta | None:
    """Return the :class:`SkillMeta` for ``skill``, or ``None`` if unknown.

    Never raises — an unrecognized skill name (or non-string) degrades to
    ``None`` so call sites can treat absence as "no registered metadata".
    """
    try:
        return SKILLS.get(skill)
    except TypeError:
        return None

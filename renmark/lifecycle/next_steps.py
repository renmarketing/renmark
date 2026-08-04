"""Next-step routing for renmark skills.

Split out of ``renmark/lifecycle/stage.py`` per
`.renmark/rethink/renmark-architecture/target-blueprint.md` §1.2. Behavior is
unchanged — these are the same functions, relocated verbatim.

``next_steps()`` is the contract helper for
``plugin/skills/.shared/next-steps.md`` — the single source of truth for the
"what should the user do next?" hand-off rule across every renmark skill.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path

from ..summary import read_metadata
from .stage import (
    AUX_LOCAL_ACTIONS,
    IMPLEMENTED_SKILLS,
    NEXT_BY_STAGE,
    read_lifecycle,
    skill_class,
)


def next_recommended(repo: Path | str) -> str:
    """Return the recommended next command for the current lifecycle, or a
    cold-start prompt if no lifecycle exists. Zero LLM calls.

    Guarantees the returned hint never points at an unimplemented skill — if
    NEXT_BY_STAGE is somehow stale, the resolver routes to a manual fallback
    instead of sending a vibe coder into a wall.
    """
    state = read_lifecycle(repo)
    if state is None:
        return "/renmark:start (no feature in flight)"

    if state.human_review_required and not state.human_review_completed:
        target = state.human_review_for or "pending action"
        # `/renmark:approve` is the only sanctioned way to flip the gate (G7).
        return f"/renmark:approve (approval pending for: {target})"

    candidate = state.next_recommended or NEXT_BY_STAGE.get(state.stage, "")
    return _resolve_next(candidate, state.stage)


def _resolve_next(candidate: str, stage: str) -> str:
    """Replace any /renmark:<unimplemented> pointer with a manual hint."""
    if not candidate.startswith("/renmark:"):
        return candidate or f"(unknown stage: {stage})"
    skill = candidate.split(":", 1)[1].split()[0]
    if skill in IMPLEMENTED_SKILLS:
        return candidate
    return (
        f"(manual: /renmark:{skill} is not yet implemented — see CHANGELOG / README for next step from stage {stage!r})"
    )


@dataclass
class NextSteps:
    """Structured next-step set for a skill, per the next-steps.md contract.

    JSON-trivial: every field is a str / list[str] / bool. The caller renders
    ``suggestions`` via handoff-menu.md rules 6-9; ``tier0`` is always the
    state-derived ``(Recommended)`` option.
    """

    tier0: str  # deterministic state-derived next command (always present)
    suggestions: list[str]  # ordered options to surface (tier0 first)
    skill_class: str  # 'pipeline' | 'gate' | 'aux'
    defer_to_handoff_menu: bool = False  # gate skills set this
    gates_not_run: list[str] = field(default_factory=list)  # best-effort gate detection

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def next_steps(repo: Path | str, skill: object) -> NextSteps:
    """Compute the structured next-step set for ``skill`` (next-steps.md contract).

    Pure + stdlib/renmark-only. Reads lifecycle via ``read_lifecycle`` and reuses
    the existing routing (``next_recommended`` → ``_resolve_next`` over
    ``NEXT_BY_STAGE``). Per class:

    - ``pipeline`` → ``suggestions = [tier0]`` (the stage transition).
    - ``gate`` → ``defer_to_handoff_menu=True`` plus best-effort ``gates_not_run``
      (review/qa artifacts whose ``source_sha`` != current HEAD or that are
      absent for the current sha; mirrors handoff-menu rule 2).
    - ``aux`` → ``[tier0]`` (resume-pipeline) + up to 2 per-skill local actions.

    ``suggestions`` is the state-derived **recommended next action(s)** — NOT the
    complete rendered menu. The calling SKILL.md adds the standard terminal
    options (Finish / Nothing, and the gate sub-menu for gate skills) per the
    handoff-menu.md rendering rules; do not treat ``suggestions`` as the full,
    choice-complete menu.

    NEVER raises into the caller: ``skill_class`` tolerates non-string input and
    any state-read failure degrades to a minimal result carrying just the
    cold-start ``next_recommended`` string.
    """
    cls = skill_class(skill)
    try:
        tier0 = next_recommended(repo)
    except Exception:
        # Absolute floor — never let a state read raise into a skill's hand-off.
        return NextSteps(
            tier0="/renmark:start (no feature in flight)",
            suggestions=["/renmark:start (no feature in flight)"],
            skill_class=cls,
        )

    if cls == "pipeline":
        return NextSteps(tier0=tier0, suggestions=[tier0], skill_class="pipeline")

    if cls == "gate":
        gates_not_run = _gates_not_run(repo)
        return NextSteps(
            tier0=tier0,
            suggestions=[tier0],
            skill_class="gate",
            defer_to_handoff_menu=True,
            gates_not_run=gates_not_run,
        )

    # aux / terminal
    local = AUX_LOCAL_ACTIONS.get(skill, [])[:2] if isinstance(skill, str) else []
    suggestions = [tier0, *local]
    return NextSteps(tier0=tier0, suggestions=suggestions, skill_class="aux")


def _gates_not_run(repo: Path | str) -> list[str]:
    """Best-effort: which quality gates have NOT run for the current HEAD sha.

    Mirrors handoff-menu rule 2 — scan ``.renmark/reviews/*.qa.md`` and
    ``*.review.md`` for an artifact with ``source_sha == HEAD`` and
    ``completion_state == 'complete'``; any gate without one is "not run".
    Degrades gracefully (returns ``[]``) if git or the summary helpers are
    unavailable.
    """
    try:
        from ..summary import git_head_sha

        head = git_head_sha(repo)
        if not head:
            return []
        reviews = Path(repo) / ".renmark" / "reviews"
        if not reviews.is_dir():
            return ["qa", "codereview"]

        # (glob, required generator) per gate. The generator constraint mirrors
        # handoff-menu rule 2: a gate counts as "run" only when the artifact was
        # produced by the gate's own generator — a stray/foreign .qa.md must not
        # unlock Deep QA. generator=None means "no generator constraint".
        gate_specs: dict[str, tuple[str, str | None]] = {
            "qa": ("*.qa.md", "verify-qa"),
            "codereview": ("*.review.md", None),
        }
        not_run: list[str] = []
        for gate, (pattern, want_gen) in gate_specs.items():
            ran = False
            for artifact in reviews.glob(pattern):
                meta = read_metadata(artifact)
                if (
                    meta.get("source_sha") == head
                    and meta.get("completion_state") == "complete"
                    and (want_gen is None or meta.get("generator") == want_gen)
                ):
                    ran = True
                    break
            if not ran:
                not_run.append(gate)
        return not_run
    except Exception:
        return []

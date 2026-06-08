"""Unit tests for renmark.lifecycle.next_steps / NextSteps / skill_class.

These cover the next-steps.md contract: the structured "what next?" set every
renmark skill surfaces on hand-off. Tests are hermetic — tmp_path lifecycle
fixtures only, no network and no real git mutation beyond `git init` in a
tmp dir.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from renmark import lifecycle
from renmark.lifecycle import (
    AUX_LOCAL_ACTIONS,
    AUX_SKILLS,
    GATE_SKILLS,
    IMPLEMENTED_SKILLS,
    NEXT_BY_STAGE,
    PIPELINE_SKILLS,
    NextSteps,
    next_steps,
    skill_class,
)


def _init_git_repo(path: Path) -> None:
    subprocess.run(["git", "init", str(path)], check=True, capture_output=True)


# ── skill_class classification ────────────────────────────────────────────────


def test_skill_class_pipeline() -> None:
    for skill in PIPELINE_SKILLS:
        assert skill_class(skill) == "pipeline"


def test_skill_class_gate() -> None:
    for skill in GATE_SKILLS:
        assert skill_class(skill) == "gate"


def test_skill_class_aux() -> None:
    for skill in AUX_SKILLS:
        assert skill_class(skill) == "aux"


def test_skill_class_unknown_defaults_aux() -> None:
    assert skill_class("totally-made-up-skill") == "aux"


# ── pipeline skills at major stages ───────────────────────────────────────────


def test_pipeline_skill_at_brainstorm_complete(tmp_path: Path) -> None:
    lifecycle.begin_feature(tmp_path, feature="x", branch="feature/x")
    lifecycle.write_lifecycle(tmp_path, stage="brainstorm-complete")
    ns = next_steps(tmp_path, "plan")
    assert ns.skill_class == "pipeline"
    assert ns.tier0 == NEXT_BY_STAGE["brainstorm-complete"]
    assert ns.tier0 == "/renmark:plan"
    assert ns.suggestions == [ns.tier0]
    assert ns.defer_to_handoff_menu is False


def test_pipeline_skill_at_plan_validated(tmp_path: Path) -> None:
    lifecycle.begin_feature(tmp_path, feature="x", branch="feature/x")
    lifecycle.write_lifecycle(tmp_path, stage="plan-validated")
    ns = next_steps(tmp_path, "orchestrate")
    assert ns.skill_class == "pipeline"
    assert ns.tier0 == NEXT_BY_STAGE["plan-validated"]
    assert ns.tier0 == "/renmark:orchestrate"
    assert ns.suggestions == [ns.tier0]


def test_pipeline_skill_at_created(tmp_path: Path) -> None:
    lifecycle.begin_feature(tmp_path, feature="x", branch="feature/x")
    lifecycle.write_lifecycle(tmp_path, stage="created")
    ns = next_steps(tmp_path, "finish")
    assert ns.skill_class == "pipeline"
    assert ns.tier0 == NEXT_BY_STAGE["created"]
    assert ns.suggestions == [ns.tier0]


def test_pipeline_tier0_matches_next_by_stage_every_pipeline_pointer(tmp_path: Path) -> None:
    """For every stage whose NEXT_BY_STAGE target is an implemented /renmark:
    skill, a pipeline skill's tier0 must equal that target verbatim."""
    for stage, target in NEXT_BY_STAGE.items():
        if stage == "init":
            continue  # init isn't writable via write_lifecycle
        if not target.startswith("/renmark:"):
            continue  # manual-hint stages handled elsewhere
        skill = target.split(":", 1)[1].split()[0]
        if skill not in IMPLEMENTED_SKILLS:
            continue
        lifecycle.clear_lifecycle(tmp_path)
        lifecycle.write_lifecycle(tmp_path, stage=stage, feature="x")
        ns = next_steps(tmp_path, "plan")
        assert ns.tier0 == target, f"stage {stage!r} tier0 drift"
        assert ns.suggestions == [ns.tier0]


# ── unimplemented-skill safety ────────────────────────────────────────────────


def test_unimplemented_target_routes_to_fallback_not_dead_pointer() -> None:
    """If a stage's NEXT_BY_STAGE target ever points at a skill with no SKILL.md,
    the resolver must emit a manual-hint string, NOT a dead /renmark:<x>."""
    # Pick a skill that is intentionally NOT implemented (document is in the
    # planned-but-unshipped set per NEXT_BY_STAGE_PLANNED).
    unimplemented = "document"
    assert unimplemented not in IMPLEMENTED_SKILLS
    resolved = lifecycle._resolve_next(f"/renmark:{unimplemented}", "reviewed")
    assert not resolved.startswith(f"/renmark:{unimplemented} "), "dead pointer leaked"
    assert resolved.startswith("(manual")
    assert unimplemented in resolved


def test_no_canonical_stage_emits_dead_pointer(tmp_path: Path) -> None:
    """End-to-end: across every canonical stage, next_steps().tier0 is never a
    /renmark:<unimplemented> pointer."""
    from renmark.lifecycle import STAGES

    for stage in STAGES:
        if stage == "init":
            continue
        lifecycle.clear_lifecycle(tmp_path)
        lifecycle.write_lifecycle(tmp_path, stage=stage, feature="x")
        tier0 = next_steps(tmp_path, "plan").tier0
        if tier0.startswith("/renmark:"):
            skill = tier0.split(":", 1)[1].split()[0]
            assert skill in IMPLEMENTED_SKILLS, f"stage {stage!r} -> dead /renmark:{skill}"


# ── aux skills ────────────────────────────────────────────────────────────────


def test_aux_skill_debug(tmp_path: Path) -> None:
    lifecycle.begin_feature(tmp_path, feature="x", branch="feature/x")
    lifecycle.write_lifecycle(tmp_path, stage="created")
    ns = next_steps(tmp_path, "debug")
    assert ns.skill_class == "aux"
    assert ns.tier0  # non-empty resume-pipeline string
    assert isinstance(ns.tier0, str)
    # tier0 (resume) + at least one local action.
    assert len(ns.suggestions) >= 2
    assert ns.suggestions[0] == ns.tier0
    assert ns.defer_to_handoff_menu is False
    # Local actions come from AUX_LOCAL_ACTIONS, capped at 2.
    expected_local = AUX_LOCAL_ACTIONS["debug"][:2]
    assert ns.suggestions[1:] == expected_local


def test_aux_skill_caps_local_actions_at_two(tmp_path: Path) -> None:
    lifecycle.begin_feature(tmp_path, feature="x", branch="feature/x")
    lifecycle.write_lifecycle(tmp_path, stage="created")
    ns = next_steps(tmp_path, "debug")
    # tier0 + at most 2 local actions.
    assert len(ns.suggestions) <= 3


# ── gate skills ───────────────────────────────────────────────────────────────


def test_gate_skill_verify_defers_to_handoff(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    lifecycle.begin_feature(tmp_path, feature="x", branch="feature/x")
    lifecycle.write_lifecycle(tmp_path, stage="created")
    ns = next_steps(tmp_path, "verify")
    assert ns.skill_class == "gate"
    assert ns.defer_to_handoff_menu is True
    assert ns.tier0
    assert ns.suggestions == [ns.tier0]
    # gates_not_run is best-effort: either reports 'qa' as not-yet-run (no
    # .qa.md artifact for HEAD) OR degrades to [] when git/state unavailable.
    assert isinstance(ns.gates_not_run, list)
    assert ns.gates_not_run == [] or "qa" in ns.gates_not_run


def test_gate_skill_codereview_is_gate_class(tmp_path: Path) -> None:
    lifecycle.begin_feature(tmp_path, feature="x", branch="feature/x")
    lifecycle.write_lifecycle(tmp_path, stage="verified")
    ns = next_steps(tmp_path, "codereview")
    assert ns.skill_class == "gate"
    assert ns.defer_to_handoff_menu is True


def test_gate_non_git_degrades_gracefully(tmp_path: Path) -> None:
    """No git repo at all — gate detection must degrade to [] without raising."""
    lifecycle.begin_feature(tmp_path, feature="x", branch="feature/x")
    lifecycle.write_lifecycle(tmp_path, stage="created")
    ns = next_steps(tmp_path, "verify")
    assert ns.skill_class == "gate"
    assert ns.defer_to_handoff_menu is True
    assert ns.gates_not_run == []  # no HEAD sha -> graceful []


# ── graceful degradation ──────────────────────────────────────────────────────


def test_no_lifecycle_returns_cold_start(tmp_path: Path) -> None:
    """No lifecycle.json: must not raise; tier0 is the cold-start string."""
    ns = next_steps(tmp_path, "plan")
    assert isinstance(ns, NextSteps)
    assert ns.tier0 == "/renmark:start (no feature in flight)"
    assert ns.tier0 in ns.suggestions
    assert ns.skill_class == "pipeline"


def test_corrupt_lifecycle_returns_minimal(tmp_path: Path) -> None:
    """A corrupt lifecycle.json must degrade to a minimal, non-empty result."""
    state_dir = tmp_path / ".renmark" / "state"
    state_dir.mkdir(parents=True)
    (state_dir / "lifecycle.json").write_text("not json {{{")
    ns = next_steps(tmp_path, "debug")
    assert isinstance(ns, NextSteps)
    assert isinstance(ns.tier0, str)
    assert ns.tier0  # non-empty
    # read_lifecycle treats corrupt as None -> cold-start tier0.
    assert ns.tier0 == "/renmark:start (no feature in flight)"


def test_as_dict_is_json_trivial(tmp_path: Path) -> None:
    """NextSteps.as_dict() must round-trip to a JSON-safe dict with all fields."""
    import json

    ns = next_steps(tmp_path, "plan")
    d = ns.as_dict()
    assert set(d) == {
        "tier0",
        "suggestions",
        "skill_class",
        "defer_to_handoff_menu",
        "gates_not_run",
    }
    # Must serialize without error.
    json.dumps(d)

"""Unit tests for renmark.lifecycle (G12 — lifecycle persistence)."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from renmark import lifecycle
from renmark.lifecycle import NEXT_BY_STAGE, LifecycleBloatError, LifecycleState
from renmark.summary import write_artifact


def _init_git_repo(path: Path) -> None:
    subprocess.run(["git", "init", str(path)], check=True, capture_output=True)


def test_read_lifecycle_none_when_missing(tmp_path: Path) -> None:
    assert lifecycle.read_lifecycle(tmp_path) is None


def test_write_then_read_lifecycle(tmp_path: Path) -> None:
    state = lifecycle.write_lifecycle(
        tmp_path,
        stage="brainstorm-complete",
        feature="auth-overhaul",
        branch="feature/auth-overhaul",
    )
    assert state.feature == "auth-overhaul"
    assert state.stage == "brainstorm-complete"
    assert state.next_recommended == "/renmark:plan"

    loaded = lifecycle.read_lifecycle(tmp_path)
    assert loaded is not None
    assert loaded.feature == "auth-overhaul"
    assert loaded.stage == "brainstorm-complete"


def test_stage_transitions_track_completed(tmp_path: Path) -> None:
    lifecycle.write_lifecycle(tmp_path, stage="brainstorm-complete", feature="x")
    lifecycle.write_lifecycle(tmp_path, stage="plan-drafted")
    lifecycle.write_lifecycle(tmp_path, stage="plan-validated")
    state = lifecycle.read_lifecycle(tmp_path)
    assert state.stage == "plan-validated"
    assert "brainstorm-complete" in state.stages_completed
    assert "plan-drafted" in state.stages_completed


def test_begin_feature_writes_identity(tmp_path: Path) -> None:
    """After /renmark:feature enters a branch, lifecycle.json must reflect THIS
    feature's identity at a clean init stage."""
    state = lifecycle.begin_feature(tmp_path, feature="verify-browser-qa", branch="feature/verify-browser-qa")
    assert state.feature == "verify-browser-qa"
    assert state.branch == "feature/verify-browser-qa"
    assert state.stage == "init"
    assert state.stages_completed == []
    assert state.artifacts == {}

    loaded = lifecycle.read_lifecycle(tmp_path)
    assert loaded is not None
    assert loaded.feature == "verify-browser-qa"
    assert loaded.branch == "feature/verify-browser-qa"
    assert loaded.stage == "init"


def test_begin_feature_resets_prior_feature_state(tmp_path: Path) -> None:
    """The identity bug: a new feature must NOT inherit the prior feature's
    identity, stage history, or artifact pointers."""
    # Simulate a previous feature that ran to ready-to-release.
    lifecycle.write_lifecycle(
        tmp_path,
        stage="plan-drafted",
        feature="old-feature",
        branch="feature/old-feature",
        artifact_update=("plan", ".renmark/plans/old.plan.md"),
    )
    lifecycle.write_lifecycle(tmp_path, stage="ready-to-release")

    # Entering a new feature wipes the slate.
    lifecycle.begin_feature(tmp_path, feature="new-feature", branch="feature/new-feature")
    state = lifecycle.read_lifecycle(tmp_path)
    assert state is not None
    assert state.feature == "new-feature"
    assert state.branch == "feature/new-feature"
    assert state.stage == "init"
    assert state.stages_completed == []  # no stale "plan-drafted"/"ready-to-release"
    assert state.artifacts == {}  # no stale plan pointer


def test_unknown_stage_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        lifecycle.write_lifecycle(tmp_path, stage="invented-stage")


def test_artifact_update(tmp_path: Path) -> None:
    lifecycle.write_lifecycle(
        tmp_path,
        stage="brainstorm-complete",
        feature="x",
        artifact_update=("spec", ".renmark/specs/x.spec.md"),
    )
    state = lifecycle.read_lifecycle(tmp_path)
    assert state.artifacts == {"spec": ".renmark/specs/x.spec.md"}
    lifecycle.write_lifecycle(
        tmp_path,
        artifact_update=("plan", ".renmark/plans/x.plan.md"),
    )
    state = lifecycle.read_lifecycle(tmp_path)
    assert state.artifacts == {
        "spec": ".renmark/specs/x.spec.md",
        "plan": ".renmark/plans/x.plan.md",
    }


def test_human_review_fields(tmp_path: Path) -> None:
    lifecycle.write_lifecycle(
        tmp_path,
        stage="ready-to-release",
        feature="x",
        human_review_required=True,
        human_review_for="release-v0.3.0",
    )
    state = lifecycle.read_lifecycle(tmp_path)
    assert state.human_review_required is True
    assert state.human_review_completed is False
    assert state.human_review_for == "release-v0.3.0"

    lifecycle.write_lifecycle(tmp_path, human_review_completed=True)
    state = lifecycle.read_lifecycle(tmp_path)
    assert state.human_review_completed is True


def test_clear_lifecycle(tmp_path: Path) -> None:
    lifecycle.write_lifecycle(tmp_path, stage="brainstorm-complete", feature="x")
    assert lifecycle.read_lifecycle(tmp_path) is not None
    lifecycle.clear_lifecycle(tmp_path)
    assert lifecycle.read_lifecycle(tmp_path) is None


def test_next_recommended_no_lifecycle(tmp_path: Path) -> None:
    rec = lifecycle.next_recommended(tmp_path)
    assert "/renmark:start" in rec


def test_next_recommended_normal_flow(tmp_path: Path) -> None:
    lifecycle.write_lifecycle(tmp_path, stage="created", feature="x")
    assert lifecycle.next_recommended(tmp_path) == "/renmark:verify"


def test_next_recommended_pending_approval(tmp_path: Path) -> None:
    """When approval is pending, route to /renmark:approve (the only sanctioned
    gate-flip per G7) and name the pending target."""
    lifecycle.write_lifecycle(
        tmp_path,
        stage="ready-to-release",
        feature="x",
        human_review_required=True,
        human_review_for="release-v0.3.0",
    )
    rec = lifecycle.next_recommended(tmp_path)
    assert "release-v0.3.0" in rec
    assert "/renmark:approve" in rec


def test_next_recommended_approved_proceeds(tmp_path: Path) -> None:
    """ready-to-release with approval recorded routes to a manual release hint —
    no /renmark:release skill ships."""
    lifecycle.write_lifecycle(
        tmp_path,
        stage="ready-to-release",
        feature="x",
        human_review_required=True,
        human_review_completed=True,
        human_review_for="release-v0.3.0",
    )
    rec = lifecycle.next_recommended(tmp_path)
    assert rec.startswith("(manual")
    assert "release" in rec.lower()


def test_next_recommended_never_points_at_unimplemented_skill(tmp_path: Path) -> None:
    """Guard the lifecycle dead-pointer regression. Iterate every canonical
    stage and confirm the recommendation is either a manual-hint string or
    a skill that actually exists in plugin/skills/."""
    from renmark.lifecycle import IMPLEMENTED_SKILLS, STAGES

    for stage in STAGES:
        if stage == "init":
            # init isn't writable via write_lifecycle (it's the implicit start state).
            continue
        lifecycle.clear_lifecycle(tmp_path)
        lifecycle.write_lifecycle(tmp_path, stage=stage, feature="x")
        rec = lifecycle.next_recommended(tmp_path)
        if rec.startswith("/renmark:"):
            skill = rec.split(":", 1)[1].split()[0]
            assert skill in IMPLEMENTED_SKILLS, f"stage {stage!r} routes to /renmark:{skill} which has no SKILL.md"


def test_byte_budget_enforced(tmp_path: Path) -> None:
    """Adding too many artifact paths should trip the bloat guard."""
    lifecycle.write_lifecycle(tmp_path, stage="brainstorm-complete", feature="x")
    huge_path = "a/" + "x" * 1024
    with pytest.raises(LifecycleBloatError):
        lifecycle.write_lifecycle(tmp_path, artifact_update=("huge", huge_path))


def test_domain_classification() -> None:
    assert lifecycle.domain_of("debug") == "debug"
    assert lifecycle.domain_of("plan") == "build"
    assert lifecycle.domain_of("audit") == "audit"
    assert lifecycle.domain_of("inventory") == "audit"
    assert lifecycle.domain_of("setup") == "meta"
    assert lifecycle.domain_of("unknown-skill") == "build"  # default


def test_hygiene_is_meta_domain() -> None:
    assert lifecycle.DOMAIN_BY_SKILL["hygiene"] == "meta"


# Previously this tolerated the registry listing approve/audit/inventory before
# their dirs were scaffolded. Those dirs now exist, so parity is EXACT — the
# tolerance set is empty and any registry entry without a backing dir is a ghost.
_REGISTRY_AHEAD_OF_DIRS: set[str] = set()


def _skill_dirs() -> set[str]:
    """Every plugin/skills/<name>/ dir (with a SKILL.md), minus _shared."""
    repo_root = Path(__file__).resolve().parent.parent
    skills = repo_root / "plugin" / "skills"
    return {d.name for d in skills.iterdir() if d.is_dir() and d.name != "_shared" and (d / "SKILL.md").exists()}


def test_registry_covers_every_skill_dir() -> None:
    """Dirs-side parity: every shipped skill DIR must be in both
    IMPLEMENTED_SKILLS and DOMAIN_BY_SKILL — no skill ships without routing."""
    dirs = _skill_dirs()
    assert dirs, "no skill dirs discovered — path resolution broke"
    missing_impl = dirs - set(lifecycle.IMPLEMENTED_SKILLS)
    missing_domain = dirs - set(lifecycle.DOMAIN_BY_SKILL)
    assert not missing_impl, f"skill dirs absent from IMPLEMENTED_SKILLS: {sorted(missing_impl)}"
    assert not missing_domain, f"skill dirs absent from DOMAIN_BY_SKILL: {sorted(missing_domain)}"


def test_registry_has_no_ghost_skills() -> None:
    """Registry-side parity: the only registry entries WITHOUT a backing dir are
    the wave-2 skills (approve/audit/inventory). Any other entry is a ghost.

    DOMAIN_BY_SKILL carries `unknown-skill`-style synthetic names? No — it must
    not. Once the wave-2 dirs land, _REGISTRY_AHEAD_OF_DIRS should empty out and
    this becomes an exact-match check."""
    dirs = _skill_dirs()
    for registry, name in (
        (set(lifecycle.IMPLEMENTED_SKILLS), "IMPLEMENTED_SKILLS"),
        (set(lifecycle.DOMAIN_BY_SKILL), "DOMAIN_BY_SKILL"),
    ):
        ghosts = registry - dirs - _REGISTRY_AHEAD_OF_DIRS
        assert not ghosts, f"{name} has ghost skills (no dir, not wave-2): {sorted(ghosts)}"


def test_cross_domain_transition() -> None:
    assert lifecycle.is_cross_domain_transition(None, "plan") is False
    assert lifecycle.is_cross_domain_transition("plan", "orchestrate") is False  # both build
    assert lifecycle.is_cross_domain_transition("plan", "debug") is True
    assert lifecycle.is_cross_domain_transition("debug", "verify") is True


def _write_declared_fable_routing(repo: Path) -> None:
    routing = repo / ".renmark" / "memory" / "routing.md"
    routing.parent.mkdir(parents=True, exist_ok=True)
    routing.write_text("## Model tiers\n\ntop_tier: fable\n")


def test_skill_preamble_declared_repo_brainstorm_adds_tier_hint(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("RENMARK_TOP_TIER", raising=False)
    _write_declared_fable_routing(tmp_path)

    hint = lifecycle.skill_preamble(tmp_path, "brainstorm")

    assert hint is not None
    assert "declared top tier: fable" in hint


def test_skill_preamble_declared_repo_verify_omits_tier_hint(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("RENMARK_TOP_TIER", raising=False)
    _write_declared_fable_routing(tmp_path)

    hint = lifecycle.skill_preamble(tmp_path, "verify")

    assert "declared top tier: fable" not in (hint or "")


def test_skill_preamble_undeclared_repo_brainstorm_omits_tier_hint(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("RENMARK_TOP_TIER", raising=False)

    hint = lifecycle.skill_preamble(tmp_path, "brainstorm")

    assert "declared top tier: fable" not in (hint or "")


def test_preamble_hint_fires_on_env_declaration(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """BY DESIGN (PRD REQ-2): `RENMARK_TOP_TIER` is a legitimate PER-USER declaration
    form — "a committed `## Model tiers` block…, per-user overridable with
    `RENMARK_TOP_TIER`". An undeclared repo (no routing.md) + RENMARK_TOP_TIER=fable
    IS declared, so the tier hint must fire; this is not a bypass."""
    monkeypatch.setenv("RENMARK_TOP_TIER", "fable")
    # No _write_declared_fable_routing() call — the repo itself stays undeclared.

    hint = lifecycle.skill_preamble(tmp_path, "brainstorm")

    assert hint is not None
    assert "declared top tier: fable" in hint


def test_skill_preamble_cross_domain_and_tier_hints_joined(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("RENMARK_TOP_TIER", raising=False)
    _write_declared_fable_routing(tmp_path)
    lifecycle.skill_preamble(tmp_path, "debug")

    hint = lifecycle.skill_preamble(tmp_path, "brainstorm")

    assert hint is not None
    assert "context: cross-domain transition" in hint
    assert "declared top tier: fable" in hint
    assert " | " in hint


def test_corrupt_lifecycle_returns_none(tmp_path: Path) -> None:
    state_dir = tmp_path / ".renmark" / "state"
    state_dir.mkdir(parents=True)
    (state_dir / "lifecycle.json").write_text("not json {{{")
    assert lifecycle.read_lifecycle(tmp_path) is None


def test_non_dict_lifecycle_returns_none(tmp_path: Path) -> None:
    """Valid JSON whose top level is not an object must degrade to None,
    never raise — a corrupt file must not kill cold-start recovery."""
    state_dir = tmp_path / ".renmark" / "state"
    state_dir.mkdir(parents=True)
    for payload in ("[]", '"x"', "42"):
        (state_dir / "lifecycle.json").write_text(payload)
        assert lifecycle.read_lifecycle(tmp_path) is None


def test_wrong_typed_fields_dropped(tmp_path: Path) -> None:
    """Wrong-typed values degrade to dataclass defaults instead of raising."""
    state_dir = tmp_path / ".renmark" / "state"
    state_dir.mkdir(parents=True)
    (state_dir / "lifecycle.json").write_text(json.dumps({"stage": ["a"], "artifacts": ["a"], "feature": 7}))
    state = lifecycle.read_lifecycle(tmp_path)
    assert state is not None
    assert state.stage == "init"
    assert state.artifacts == {}
    assert state.feature == ""


def test_non_dict_lifecycle_does_not_break_writes(tmp_path: Path) -> None:
    """write_lifecycle resets from a corrupt file instead of raising."""
    state_dir = tmp_path / ".renmark" / "state"
    state_dir.mkdir(parents=True)
    (state_dir / "lifecycle.json").write_text("[]")
    state = lifecycle.write_lifecycle(tmp_path, stage="brainstorm-complete")
    assert state.stage == "brainstorm-complete"


def test_field_type_map_matches_dataclass() -> None:
    """Drift guard: the read-time type filter must cover every dataclass field."""
    assert set(lifecycle._LIFECYCLE_FIELD_TYPES) == set(lifecycle.LifecycleState.__dataclass_fields__)


def test_validate_artifact_refs_survives_corrupt_state(tmp_path: Path) -> None:
    state_dir = tmp_path / ".renmark" / "state"
    state_dir.mkdir(parents=True)
    (state_dir / "lifecycle.json").write_text('{"stage": "init", "artifacts": ["a"]}')
    assert lifecycle.validate_artifact_refs(tmp_path) == []


def test_unknown_fields_in_lifecycle_tolerated(tmp_path: Path) -> None:
    """Forward-compat: extra fields shouldn't crash the loader."""
    state_dir = tmp_path / ".renmark" / "state"
    state_dir.mkdir(parents=True)
    (state_dir / "lifecycle.json").write_text(
        json.dumps(
            {
                "feature": "x",
                "stage": "verified",
                "future_field_added_later": "ok",
            }
        )
    )
    state = lifecycle.read_lifecycle(tmp_path)
    assert state is not None
    assert state.feature == "x"
    assert state.stage == "verified"


def test_lifecycle_state_default_last_updated() -> None:
    state = LifecycleState()
    assert state.last_updated  # auto-populated
    assert "T" in state.last_updated  # ISO format


def test_stage_named_in_next_by_stage_for_every_canonical_stage() -> None:
    from renmark.lifecycle import STAGES

    for stage in STAGES:
        assert stage in NEXT_BY_STAGE, f"stage {stage!r} missing from NEXT_BY_STAGE"


def test_validate_artifact_refs_no_lifecycle(tmp_path: Path) -> None:
    assert lifecycle.validate_artifact_refs(tmp_path) == []


def test_validate_artifact_refs_all_ok(tmp_path: Path) -> None:
    lifecycle.write_lifecycle(
        tmp_path,
        stage="brainstorm-complete",
        feature="x",
        artifact_update=("plan", "p.md"),
    )
    write_artifact(
        tmp_path / "p.md",
        artifact_type="plan",
        body="plan body",
        summary_lines=["ok"],
        source_sha="null",
        generator="test",
    )

    assert lifecycle.validate_artifact_refs(tmp_path) == []


def test_validate_artifact_refs_missing_plan_blocks(tmp_path: Path) -> None:
    state = lifecycle.write_lifecycle(
        tmp_path,
        stage="brainstorm-complete",
        feature="x",
        artifact_update=("plan", "missing.md"),
    )

    issues = lifecycle.validate_artifact_refs(tmp_path, state)

    assert len(issues) == 1
    assert issues[0]["severity"] == "BLOCK"
    assert issues[0]["kind"] == "missing_path"


def test_validate_artifact_refs_missing_aux_warns(tmp_path: Path) -> None:
    state = lifecycle.write_lifecycle(
        tmp_path,
        stage="brainstorm-complete",
        feature="x",
        artifact_update=("notes", "missing.md"),
    )

    issues = lifecycle.validate_artifact_refs(tmp_path, state)

    assert len(issues) == 1
    assert issues[0]["severity"] == "WARN"
    assert issues[0]["kind"] == "missing_path"


def test_validate_artifact_refs_unreachable_sha(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _init_git_repo(tmp_path)
    state = lifecycle.write_lifecycle(
        tmp_path,
        stage="brainstorm-complete",
        feature="x",
        artifact_update=("notes", "p.md"),
    )
    write_artifact(
        tmp_path / "p.md",
        artifact_type="notes",
        body="notes body",
        summary_lines=["ok"],
        source_sha="deadbeefdeadbeef",
        generator="test",
    )

    def fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        return subprocess.CompletedProcess(args=args[0], returncode=1, stdout=b"", stderr=b"")

    monkeypatch.setattr(lifecycle.subprocess, "run", fake_run)

    issues = lifecycle.validate_artifact_refs(tmp_path, state)

    assert len(issues) == 1
    assert issues[0]["severity"] == "WARN"
    assert issues[0]["kind"] == "unreachable_sha"


def test_validate_artifact_refs_stale_artifact(tmp_path: Path) -> None:
    state = lifecycle.write_lifecycle(
        tmp_path,
        stage="brainstorm-complete",
        feature="x",
        artifact_update=("notes", "p.md"),
    )
    write_artifact(
        tmp_path / "p.md",
        artifact_type="notes",
        body="notes body",
        summary_lines=["ok"],
        source_sha="null",
        generator="test",
        stale_after="2020-01-01T00:00:00Z",
    )

    issues = lifecycle.validate_artifact_refs(tmp_path, state)

    assert len(issues) == 1
    assert issues[0]["severity"] == "WARN"
    assert issues[0]["kind"] == "stale_artifact"


def test_validate_artifact_refs_absolute_outside_repo_warns(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    state = lifecycle.write_lifecycle(
        tmp_path,
        stage="brainstorm-complete",
        feature="x",
        artifact_update=("plan", "/tmp/escape.plan.md"),
    )

    issues = lifecycle.validate_artifact_refs(tmp_path, state)

    assert len(issues) == 1
    assert issues[0]["severity"] == "WARN"
    assert issues[0]["kind"] == "out_of_tree"


def test_validate_artifact_refs_dotdot_escape_warns(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    state = lifecycle.write_lifecycle(
        tmp_path,
        stage="brainstorm-complete",
        feature="x",
        artifact_update=("plan", "../../../etc/passwd"),
    )

    issues = lifecycle.validate_artifact_refs(tmp_path, state)

    assert len(issues) == 1
    assert issues[0]["severity"] == "WARN"
    assert issues[0]["kind"] == "out_of_tree"


def test_validate_artifact_refs_order_block_first(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    state = lifecycle.write_lifecycle(
        tmp_path,
        stage="brainstorm-complete",
        feature="x",
        artifact_update=("plan", "missing.md"),
    )
    state = lifecycle.write_lifecycle(
        tmp_path,
        artifact_update=("alpha", "../../../etc/passwd"),
    )
    state = lifecycle.write_lifecycle(
        tmp_path,
        artifact_update=("notes", "notes.md"),
    )
    write_artifact(
        tmp_path / "notes.md",
        artifact_type="notes",
        body="notes body",
        summary_lines=["ok"],
        source_sha="null",
        generator="test",
        stale_after="2020-01-01T00:00:00Z",
    )

    issues = lifecycle.validate_artifact_refs(tmp_path, state)

    assert [issue["severity"] for issue in issues] == ["BLOCK", "WARN", "WARN"]
    assert [issue["kind"] for issue in issues] == [
        "missing_path",
        "out_of_tree",
        "stale_artifact",
    ]

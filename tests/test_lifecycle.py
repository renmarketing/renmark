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

    # Cross-domain gate takes priority — returns CONTEXT_GATE_CLEAR early; tier
    # hint is not appended when the gate fires (gate short-circuits the join).
    assert hint is not None
    assert hint.startswith("CONTEXT_GATE_CLEAR:")
    assert "cross-domain transition" in hint


def test_skill_preamble_bypass_skill_no_gate_prefix(tmp_path: Path) -> None:
    """finish/approve/resume must never return the CONTEXT_GATE_CLEAR prefix."""
    # Set up a debug-domain last invocation
    lifecycle.skill_preamble(tmp_path, "debug")
    # finish is in _CONTEXT_BYPASS_SKILLS — gate must not fire
    hint = lifecycle.skill_preamble(tmp_path, "finish")
    assert hint is None or not (isinstance(hint, str) and hint.startswith("CONTEXT_GATE_CLEAR:"))


def test_persist_compact_checkpoint_writes_file(tmp_path: Path) -> None:
    """persist_compact_checkpoint writes the expected JSON fields."""
    import json

    lifecycle.persist_compact_checkpoint(tmp_path, "start", "clear")
    cp = tmp_path / ".renmark" / "state" / "compact_checkpoint.json"
    assert cp.exists(), "compact_checkpoint.json must be created"
    data = json.loads(cp.read_text(encoding="utf-8"))
    assert data["skill"] == "start"
    assert data["reason"] == "clear"
    assert data["resume_cmd"] == "/renmark:resume"
    assert "timestamp" in data


def test_persist_compact_checkpoint_never_raises() -> None:
    """persist_compact_checkpoint must not raise even with an invalid path."""
    # /nonexistent/... will fail at mkdir — must be silently swallowed.
    lifecycle.persist_compact_checkpoint("/nonexistent/path/xyz", "debug", "compact")


def test_cross_domain_checkpoint_written(tmp_path: Path) -> None:
    """skill_preamble writes compact_checkpoint.json before returning CONTEXT_GATE_CLEAR."""
    import json

    lifecycle.skill_preamble(tmp_path, "debug")
    hint = lifecycle.skill_preamble(tmp_path, "start")
    assert hint is not None and hint.startswith("CONTEXT_GATE_CLEAR:")
    cp = tmp_path / ".renmark" / "state" / "compact_checkpoint.json"
    assert cp.exists(), "checkpoint must be written when the clear gate fires"
    data = json.loads(cp.read_text(encoding="utf-8"))
    assert data["reason"] == "clear"


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


def test_preamble_tier_classifies_skills() -> None:
    for skill in ("resume", "help", "usage", "analytics", "approve", "doctor", "hygiene", "check-plan"):
        assert lifecycle.PREAMBLE_TIER_BY_SKILL[skill] == "minimal"
        assert lifecycle.preamble_tier(skill) == "minimal"

    for skill in ("audit", "scan", "inventory"):
        assert lifecycle.PREAMBLE_TIER_BY_SKILL[skill] == "standard"
        assert lifecycle.preamble_tier(skill) == "standard"

    for skill in ("orchestrate", "feature", "nonesuch"):
        assert lifecycle.preamble_tier(skill) == "full"


def test_skill_preamble_minimal_skill_returns_none_after_cross_domain_transition(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("RENMARK_TOP_TIER", raising=False)
    lifecycle.skill_preamble(tmp_path, "debug")

    assert lifecycle.skill_preamble(tmp_path, "resume") is None


def test_skill_preamble_minimal_skill_still_records_invocation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from renmark.state import last_skill_invocation

    monkeypatch.delenv("RENMARK_TOP_TIER", raising=False)
    lifecycle.skill_preamble(tmp_path, "debug")
    lifecycle.skill_preamble(tmp_path, "resume")

    assert last_skill_invocation(tmp_path)["skill"] == "resume"


def test_skill_preamble_standard_skill_surfaces_only_cross_domain_hint(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("RENMARK_TOP_TIER", raising=False)
    _write_declared_fable_routing(tmp_path)
    lifecycle.skill_preamble(tmp_path, "debug")

    hint = lifecycle.skill_preamble(tmp_path, "audit")

    assert hint is not None
    assert "cross-domain transition" in hint
    assert "declared top tier: fable" not in hint


def test_skill_preamble_minimal_midlink_preserves_downstream_detection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Chain full(A) -> minimal(B) -> full(C): C must detect the B->C cross-domain
    transition, which only works if the minimal mid-link B recorded its own domain.

    A and C share the SAME domain ('build'); B is a different domain ('meta'). So C
    surfaces the /clear hint ONLY if it compared against B (meta != build). If the
    minimal mid-link had skipped record_skill_invocation, C would compare against A
    (build == build) and stay silent — this test would then fail. It is the guard on
    the load-bearing invariant that a minimal-tier skill is never 'transparent' to
    downstream cross-domain detection.
    """
    monkeypatch.delenv("RENMARK_TOP_TIER", raising=False)

    assert lifecycle.preamble_tier("orchestrate") == "full"  # A
    assert lifecycle.preamble_tier("resume") == "minimal"  # B (mid-link)
    assert lifecycle.preamble_tier("feature") == "full"  # C
    assert lifecycle.domain_of("orchestrate") == lifecycle.domain_of("feature")
    assert lifecycle.domain_of("resume") != lifecycle.domain_of("feature")

    lifecycle.skill_preamble(tmp_path, "orchestrate")  # A: records build
    assert lifecycle.skill_preamble(tmp_path, "resume") is None  # B: minimal, records meta
    hint = lifecycle.skill_preamble(tmp_path, "feature")  # C: must see B (meta)

    assert hint is not None
    assert "cross-domain transition" in hint


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


# ── Operating-mode preamble (Conductor vs Orchestrator) ───────────────────────

_CONDUCTOR_DIRECTIVE = (
    "Operating mode: Conductor — hands-on; prefer single-file scoped edits, "
    "avoid subagents unless necessary, explain the next move before editing."
)
_ORCHESTRATOR_DIRECTIVE = (
    "Operating mode: Orchestrator — goal-level; use narrow scoped subagents "
    "where useful, load skills on demand, review outcomes not keystrokes."
)


def test_skill_preamble_mode_conductor_emits_conductor_directive(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """mode=conductor → the conductor directive, never the orchestrator one."""
    from renmark import mode

    monkeypatch.delenv("RENMARK_TOP_TIER", raising=False)
    monkeypatch.delenv("RENMARK_HEADLESS", raising=False)
    mode.set_mode(tmp_path, "conductor")

    hint = lifecycle.skill_preamble(tmp_path, "feature")

    assert hint is not None
    assert "Operating mode: Conductor" in hint
    assert _CONDUCTOR_DIRECTIVE in hint
    assert _ORCHESTRATOR_DIRECTIVE not in hint


def test_skill_preamble_mode_orchestrator_differs_from_conductor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC#3 by-mode diff: orchestrator directive differs from conductor output."""
    from renmark import mode

    monkeypatch.delenv("RENMARK_TOP_TIER", raising=False)
    monkeypatch.delenv("RENMARK_HEADLESS", raising=False)

    mode.set_mode(tmp_path, "conductor")
    conductor_hint = lifecycle.skill_preamble(tmp_path, "feature")

    mode.set_mode(tmp_path, "orchestrator")
    orchestrator_hint = lifecycle.skill_preamble(tmp_path, "feature")

    assert orchestrator_hint is not None
    assert "Operating mode: Orchestrator" in orchestrator_hint
    assert _ORCHESTRATOR_DIRECTIVE in orchestrator_hint
    assert orchestrator_hint != conductor_hint


def test_skill_preamble_mode_unset_entry_skill_prompts_choice(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Unset mode + entry skill → prompt the user to pick Conductor vs Orchestrator."""
    monkeypatch.delenv("RENMARK_TOP_TIER", raising=False)
    monkeypatch.delenv("RENMARK_HEADLESS", raising=False)

    hint = lifecycle.skill_preamble(tmp_path, "feature")

    assert hint is not None
    assert "Operating mode: not yet set" in hint
    assert "Conductor vs Orchestrator" in hint


def test_skill_preamble_mode_unset_non_entry_skill_omits_mode_line(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Unset mode + a non-entry skill emits NO operating-mode line at all."""
    monkeypatch.delenv("RENMARK_TOP_TIER", raising=False)
    monkeypatch.delenv("RENMARK_HEADLESS", raising=False)

    hint = lifecycle.skill_preamble(tmp_path, "help")

    assert "Operating mode" not in (hint or "")


def test_skill_preamble_mode_read_failure_degrades_gracefully(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If reading mode raises, skill_preamble still returns the base hint without
    crashing (and without emitting a mode line)."""
    from renmark import mode

    monkeypatch.delenv("RENMARK_TOP_TIER", raising=False)
    monkeypatch.delenv("RENMARK_HEADLESS", raising=False)

    def _boom(*args: object, **kwargs: object) -> object:
        raise RuntimeError("mode read failed")

    monkeypatch.setattr(mode, "read_mode", _boom)

    # Must not raise; a bare repo with no other triggers yields None.
    hint = lifecycle.skill_preamble(tmp_path, "feature")

    assert "Operating mode" not in (hint or "")


# ── Headless contract (P10) ───────────────────────────────────────────────────


def test_skill_preamble_headless_env_adds_note(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """With RENMARK_HEADLESS=1, skill_preamble surfaces the headless-mode note."""
    monkeypatch.delenv("RENMARK_TOP_TIER", raising=False)
    monkeypatch.setenv("RENMARK_HEADLESS", "1")

    hint = lifecycle.skill_preamble(tmp_path, "orchestrate")

    assert hint is not None
    assert "headless mode active" in hint


def test_skill_preamble_headless_off_omits_note(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Headless off (no env, no config) must NOT mention headless mode."""
    monkeypatch.delenv("RENMARK_TOP_TIER", raising=False)
    monkeypatch.delenv("RENMARK_HEADLESS", raising=False)

    hint = lifecycle.skill_preamble(tmp_path, "orchestrate")

    assert "headless mode active" not in (hint or "")


def test_halt_for_human_review_writes_artifact_and_arms_gate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A headless halt writes a decision artifact, arms the lifecycle gate, and
    returns a needs_input envelope (fresh repo — write_lifecycle stays under budget)."""
    monkeypatch.delenv("RENMARK_HEADLESS", raising=False)

    result = lifecycle.halt_for_human_review(
        tmp_path,
        "merge",
        originating_skill="finish",
        what="merge approval",
    )

    decision_path = tmp_path / ".renmark" / "decisions" / "merge-approval.json"
    assert decision_path.exists()
    payload = json.loads(decision_path.read_text())
    assert payload["gate"] == "merge"
    assert payload["human_review_required"] is True

    state = lifecycle.read_lifecycle(tmp_path)
    assert state is not None
    assert state.human_review_required is True
    assert state.human_review_for == "merge"

    assert result["status"] == "needs_input"
    assert result["decision"] == "halted_for_human_review"
    assert "merge" in result["gate"]
    assert result["artifacts"]


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


def test_agency_hint_inactive_is_passthrough(tmp_path):
    from renmark import lifecycle
    result = lifecycle._with_agency_note(tmp_path, "start", "some hint")
    assert result == "some hint"


def test_agency_hint_inactive_none_is_passthrough(tmp_path):
    from renmark import lifecycle
    result = lifecycle._with_agency_note(tmp_path, "start", None)
    assert result is None


def test_agency_hint_active_contains_marker(tmp_path):
    from renmark import agency, lifecycle
    agency.activate(tmp_path)
    result = lifecycle._with_agency_note(tmp_path, "start", None)
    assert result is not None
    assert lifecycle._AGENCY_HINT_MARKER in result


def test_agency_hint_non_aware_skill_is_passthrough(tmp_path):
    from renmark import agency, lifecycle
    agency.activate(tmp_path)
    result = lifecycle._with_agency_note(tmp_path, "help", "original")
    assert result == "original"

"""Deterministic tests for finish-lane selection and descriptions."""

from __future__ import annotations

from pathlib import Path

from renmark.finish_lanes import (
    LANE_FULL,
    LANE_QUICK,
    LANE_RELEASE,
    LANE_SELF_UPDATE,
    LANES,
    describe_lane,
    is_renmark_repo,
    lane_table,
    recommend_lane,
    resolve_lane,
)


def _make_renmark_repo(root: Path) -> Path:
    (root / "renmark").mkdir(parents=True, exist_ok=True)
    skill = root / "plugin" / "skills" / "finish" / "SKILL.md"
    skill.parent.mkdir(parents=True, exist_ok=True)
    skill.write_text("# finish\n", encoding="utf-8")
    return root


def test_lane_registry_fields_and_fixed_profiles() -> None:
    for spec in LANES.values():
        assert isinstance(spec.merges, bool)
        assert isinstance(spec.releases, bool)
        assert isinstance(spec.packages, bool)
        assert isinstance(spec.updates_wsl, bool)
        assert isinstance(spec.cleans_worktrees, bool)
        assert isinstance(spec.verification, str)
        assert spec.verification
        assert isinstance(spec.cost_level, str)
        assert spec.cost_level

    quick = LANES[LANE_QUICK]
    assert quick.merges is False
    assert quick.releases is False
    assert quick.packages is False
    assert quick.updates_wsl is False

    self_update = LANES[LANE_SELF_UPDATE]
    assert self_update.merges is True
    assert self_update.releases is True
    assert self_update.packages is True
    assert self_update.updates_wsl is True
    assert self_update.cleans_worktrees is True

    full = LANES[LANE_FULL]
    assert full.merges is True
    assert full.releases is True
    assert full.packages is True
    assert full.updates_wsl is True
    assert full.cleans_worktrees is True


def test_recommend_lane_uses_stage_self_and_never_returns_full(tmp_path: Path) -> None:
    assert recommend_lane(tmp_path, lifecycle_stage="init") == LANE_QUICK
    assert recommend_lane(tmp_path, lifecycle_stage="brainstorm-complete") == LANE_QUICK
    assert recommend_lane(tmp_path, lifecycle_stage="reviewed") == LANE_RELEASE
    assert recommend_lane(tmp_path, lifecycle_stage="ready-to-release") == LANE_RELEASE
    assert recommend_lane(tmp_path, is_self=True, lifecycle_stage="init") == LANE_SELF_UPDATE

    repo = _make_renmark_repo(tmp_path / "self-repo")
    assert recommend_lane(repo) == LANE_SELF_UPDATE

    for stage in (None, "init", "reviewed", "ready-to-release", "released", "weird-stage"):
        assert recommend_lane(tmp_path, lifecycle_stage=stage) != LANE_FULL
        assert recommend_lane(repo, lifecycle_stage=stage) != LANE_FULL


def test_is_renmark_repo_checks_both_markers(tmp_path: Path) -> None:
    repo = _make_renmark_repo(tmp_path / "repo")
    assert is_renmark_repo(repo) is True
    assert is_renmark_repo(tmp_path / "empty") is False


def test_resolve_lane_honors_full_and_ignores_unknown_override(tmp_path: Path) -> None:
    recommended = recommend_lane(tmp_path, lifecycle_stage="reviewed")
    assert resolve_lane(recommended, "full") == LANE_FULL
    assert resolve_lane(recommended, "not-a-lane") == recommended
    assert resolve_lane(recommended, None) == recommended


def test_lane_text_helpers_return_non_empty_strings() -> None:
    table = lane_table()
    assert isinstance(table, str)
    assert table
    assert "Lane" in table

    for lane_name in (LANE_QUICK, LANE_RELEASE, LANE_SELF_UPDATE, LANE_FULL):
        description = describe_lane(lane_name)
        assert isinstance(description, str)
        assert description
        assert lane_name in description

    assert describe_lane("unknown")


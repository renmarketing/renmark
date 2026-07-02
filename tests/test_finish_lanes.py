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



def test_resolve_lane_accepts_menu_aliases() -> None:
    from renmark.finish_lanes import resolve_lane

    # numbered menu positions (1=quick .. 4=full)
    assert resolve_lane(LANE_QUICK, "1") == LANE_QUICK
    assert resolve_lane(LANE_QUICK, "3") == LANE_SELF_UPDATE
    assert resolve_lane(LANE_QUICK, "4") == LANE_FULL
    # exact name and unique prefix
    assert resolve_lane(LANE_QUICK, "self-update") == LANE_SELF_UPDATE
    assert resolve_lane(LANE_QUICK, "self") == LANE_SELF_UPDATE
    assert resolve_lane(LANE_QUICK, "rel") == LANE_RELEASE
    # explicit full always honored
    assert resolve_lane(LANE_QUICK, "full") == LANE_FULL
    # empty / whitespace / None / out-of-range / unknown → recommended (no silent collapse to a WRONG lane)
    assert resolve_lane(LANE_RELEASE, "") == LANE_RELEASE
    assert resolve_lane(LANE_RELEASE, "   ") == LANE_RELEASE
    assert resolve_lane(LANE_RELEASE, None) == LANE_RELEASE
    assert resolve_lane(LANE_RELEASE, "9") == LANE_RELEASE
    assert resolve_lane(LANE_RELEASE, "bogus") == LANE_RELEASE


# ---------------------------------------------------------------------------
# REQ-21: release_readiness gates + lane_table Worktree column
# ---------------------------------------------------------------------------

from renmark.finish_lanes import GateResult, ReadinessReport, release_readiness


def test_release_readiness_returns_readiness_report(tmp_path: Path) -> None:
    # Call on a tmp dir (not a real renmark repo) — gates will mostly fail,
    # but the function must return a ReadinessReport dataclass, not raise.
    report = release_readiness(tmp_path)
    assert isinstance(report, ReadinessReport)
    assert isinstance(report.ready, bool)
    assert isinstance(report.gates, tuple)
    assert len(report.gates) > 0


def test_release_readiness_gates_include_required_checks(tmp_path: Path) -> None:
    report = release_readiness(tmp_path)
    gate_names = {g.name for g in report.gates}
    # These three are required by the spec
    assert "version_consistent" in gate_names
    assert "tree_clean" in gate_names
    assert "package_buildable" in gate_names


def test_release_readiness_each_gate_has_bool_passed_and_detail(tmp_path: Path) -> None:
    report = release_readiness(tmp_path)
    for gate in report.gates:
        assert isinstance(gate, GateResult)
        assert isinstance(gate.name, str) and gate.name
        assert isinstance(gate.passed, bool)
        assert isinstance(gate.detail, str) and gate.detail


def test_release_readiness_is_pure_same_gate_names_twice(tmp_path: Path) -> None:
    # Pure: calling twice returns the same gate names (no randomness, no model)
    first = release_readiness(tmp_path)
    second = release_readiness(tmp_path)
    assert [g.name for g in first.gates] == [g.name for g in second.gates]


def test_release_readiness_no_network_returns_fast() -> None:
    # Proof that it runs deterministically with no model/network call:
    # it must complete synchronously and return a dataclass (not a coroutine).
    import time

    start = time.monotonic()
    report = release_readiness(".")
    elapsed = time.monotonic() - start
    assert isinstance(report, ReadinessReport)
    # 10 seconds is a very generous upper bound — a model call would be far slower
    assert elapsed < 10.0


def test_lane_table_contains_worktree_column_header() -> None:
    table = lane_table()
    assert "Worktree" in table


def test_lane_table_self_update_and_full_show_check_mark_in_worktree_column() -> None:
    table = lane_table()
    lines = table.splitlines()
    # Find the column index of "Worktree" in the header row
    header = next(ln for ln in lines if "Worktree" in ln)
    col_idx = header.index("Worktree")

    def _worktree_cell(row_line: str) -> str:
        """Extract the Worktree cell value from a table row string."""
        # Split by '|' to get cells; strip whitespace from each
        cells = [c.strip() for c in row_line.split("|")]
        # Header: | Lane | Merges | Releases | Packages | WSL | Worktree | ...
        # cell[0] = '', cell[1] = 'Lane', ..., cell[6] = 'Worktree'
        # Use col_idx to find the right cell position by counting pipes
        header_cells = [c.strip() for c in header.split("|")]
        worktree_pos = next(i for i, c in enumerate(header_cells) if "Worktree" in c)
        return cells[worktree_pos] if worktree_pos < len(cells) else ""

    # Find data rows by lane name
    self_update_row = next(ln for ln in lines if "self-update" in ln)
    full_row = next(ln for ln in lines if ln.strip().startswith("| full"))
    quick_row = next(ln for ln in lines if ln.strip().startswith("| quick"))

    self_update_cell = _worktree_cell(self_update_row)
    full_cell = _worktree_cell(full_row)
    quick_cell = _worktree_cell(quick_row)

    # self-update and full have cleans_worktrees=True → ✓
    assert self_update_cell == "✓", f"self-update Worktree cell was {self_update_cell!r}"
    assert full_cell == "✓", f"full Worktree cell was {full_cell!r}"
    # quick has cleans_worktrees=False → ✗
    assert quick_cell == "✗", f"quick Worktree cell was {quick_cell!r}"

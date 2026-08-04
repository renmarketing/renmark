"""Deterministic tests for renmark.worktree — REQ-21 helpers.

All tests use a real throwaway git repo created via tmp_path + subprocess so
they are fully hermetic and do not depend on the renmark repo state.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from renmark.worktree import (
    current_branch,
    diff_stat,
    divergence,
    is_clean_tree,
    is_merged,
    list_worktrees,
    stale_local_branches,
    stale_worktrees,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Run a git command in *repo*; raise on non-zero return code."""
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result


def _init_repo(path: Path, branch: str = "main") -> Path:
    """Create a minimal git repo with one commit at *path*."""
    path.mkdir(parents=True, exist_ok=True)
    _git(path, "init", "-b", branch)
    _git(path, "config", "user.email", "test@example.com")
    _git(path, "config", "user.name", "Test User")
    # Initial commit so HEAD exists
    (path / "README.md").write_text("hello\n", encoding="utf-8")
    _git(path, "add", "README.md")
    _git(path, "commit", "-m", "init")
    return path


# ---------------------------------------------------------------------------
# current_branch
# ---------------------------------------------------------------------------


def test_current_branch_returns_branch_name(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path / "repo", branch="main")
    assert current_branch(repo) == "main"


def test_current_branch_reflects_new_branch(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path / "repo")
    _git(repo, "checkout", "-b", "feature-x")
    assert current_branch(repo) == "feature-x"


def test_current_branch_returns_none_on_nonexistent_path(tmp_path: Path) -> None:
    result = current_branch(tmp_path / "does-not-exist")
    assert result is None


# ---------------------------------------------------------------------------
# is_clean_tree
# ---------------------------------------------------------------------------


def test_is_clean_tree_true_after_commit(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path / "repo")
    assert is_clean_tree(repo) is True


def test_is_clean_tree_false_after_untracked_file(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path / "repo")
    (repo / "untracked.txt").write_text("surprise\n", encoding="utf-8")
    assert is_clean_tree(repo) is False


def test_is_clean_tree_false_after_modified_file(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path / "repo")
    (repo / "README.md").write_text("changed\n", encoding="utf-8")
    assert is_clean_tree(repo) is False


def test_is_clean_tree_false_on_nonexistent_path(tmp_path: Path) -> None:
    # Conservative: unknown = dirty
    assert is_clean_tree(tmp_path / "does-not-exist") is False


# ---------------------------------------------------------------------------
# is_merged
# ---------------------------------------------------------------------------


def test_is_merged_true_for_merged_branch(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path / "repo")
    # Create and merge a feature branch
    _git(repo, "checkout", "-b", "feature-merged")
    (repo / "feature.txt").write_text("feature\n", encoding="utf-8")
    _git(repo, "add", "feature.txt")
    _git(repo, "commit", "-m", "add feature")
    _git(repo, "checkout", "main")
    _git(repo, "merge", "--no-ff", "feature-merged", "-m", "merge feature")
    assert is_merged(repo, "feature-merged", into="main") is True


def test_is_merged_false_for_unmerged_branch(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path / "repo")
    _git(repo, "checkout", "-b", "feature-unmerged")
    (repo / "unmerged.txt").write_text("unmerged\n", encoding="utf-8")
    _git(repo, "add", "unmerged.txt")
    _git(repo, "commit", "-m", "unmerged commit")
    # Do NOT merge back into main — this is the cleanup gate (must not delete)
    assert is_merged(repo, "feature-unmerged", into="main") is False


def test_is_merged_false_on_nonexistent_branch(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path / "repo")
    # A non-existent branch returns False (graceful degradation)
    assert is_merged(repo, "ghost-branch", into="main") is False


# ---------------------------------------------------------------------------
# divergence
# ---------------------------------------------------------------------------


def test_divergence_ahead_behind_counts(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path / "repo")

    # Add 2 commits to main beyond the fork point
    _git(repo, "checkout", "-b", "topic")
    for i in range(3):
        (repo / f"topic_{i}.txt").write_text(f"topic {i}\n", encoding="utf-8")
        _git(repo, "add", f"topic_{i}.txt")
        _git(repo, "commit", "-m", f"topic commit {i}")

    # Add 2 commits to main (diverge)
    _git(repo, "checkout", "main")
    for i in range(2):
        (repo / f"main_{i}.txt").write_text(f"main {i}\n", encoding="utf-8")
        _git(repo, "add", f"main_{i}.txt")
        _git(repo, "commit", "-m", f"main commit {i}")

    result = divergence(repo, base="main", head="topic")
    # topic is 3 ahead (its own commits), 2 behind (main-only commits)
    assert result["ahead"] == 3
    assert result["behind"] == 2


def test_divergence_zero_for_same_commit(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path / "repo")
    result = divergence(repo, base="main", head="main")
    assert result == {"ahead": 0, "behind": 0}


def test_divergence_returns_zeros_on_bad_ref(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path / "repo")
    result = divergence(repo, base="nonexistent-ref", head="HEAD")
    assert result == {"ahead": 0, "behind": 0}


# ---------------------------------------------------------------------------
# diff_stat
# ---------------------------------------------------------------------------


def test_diff_stat_detects_working_tree_changes(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path / "repo")
    # Modify a tracked file — staged diff
    (repo / "README.md").write_text("line1\nline2\nline3\n", encoding="utf-8")
    stat = diff_stat(repo)  # working tree diff (no base)
    assert stat["files_changed"] >= 1
    assert stat["insertions"] >= 2  # added at least 2 new lines
    assert isinstance(stat["deletions"], int)


def test_diff_stat_known_change_vs_base(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path / "repo")
    # Create a feature branch with 1 new file (3 lines)
    _git(repo, "checkout", "-b", "diff-branch")
    (repo / "newfile.txt").write_text("a\nb\nc\n", encoding="utf-8")
    _git(repo, "add", "newfile.txt")
    _git(repo, "commit", "-m", "add newfile")
    stat = diff_stat(repo, base="main")
    assert stat["files_changed"] == 1
    assert stat["insertions"] == 3
    assert stat["deletions"] == 0


def test_diff_stat_zeros_on_nonexistent_base(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path / "repo")
    result = diff_stat(repo, base="ghost-ref")
    assert result == {"files_changed": 0, "insertions": 0, "deletions": 0}


# ---------------------------------------------------------------------------
# list_worktrees
# ---------------------------------------------------------------------------


def test_list_worktrees_returns_at_least_main_worktree(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path / "repo")
    worktrees = list_worktrees(repo)
    assert len(worktrees) >= 1
    paths = [str(wt.get("path", "")) for wt in worktrees]
    assert any(str(repo) in p for p in paths)


def test_list_worktrees_returns_empty_list_on_bad_path(tmp_path: Path) -> None:
    result = list_worktrees(tmp_path / "not-a-repo")
    assert result == []


def test_list_worktrees_each_entry_has_required_keys(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path / "repo")
    worktrees = list_worktrees(repo)
    for wt in worktrees:
        assert "path" in wt
        assert "head" in wt
        assert "branch" in wt
        assert "is_bare" in wt
        assert "is_detached" in wt


# ---------------------------------------------------------------------------
# Determinism assertions — calling twice yields identical results
# ---------------------------------------------------------------------------


def test_current_branch_is_deterministic(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path / "repo")
    assert current_branch(repo) == current_branch(repo)


def test_is_clean_tree_is_deterministic(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path / "repo")
    assert is_clean_tree(repo) == is_clean_tree(repo)


def test_list_worktrees_is_deterministic(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path / "repo")
    first = list_worktrees(repo)
    second = list_worktrees(repo)
    assert first == second


def test_divergence_is_deterministic(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path / "repo")
    assert divergence(repo, base="main") == divergence(repo, base="main")


# ---------------------------------------------------------------------------
# Graceful degradation — non-existent branch returns typed empty/False/None
# ---------------------------------------------------------------------------


def test_is_merged_degrades_gracefully_on_missing_branch(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path / "repo")
    assert is_merged(repo, "missing-branch") is False


def test_divergence_degrades_gracefully_on_missing_branch(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path / "repo")
    result = divergence(repo, base="missing-branch")
    assert isinstance(result, dict)
    assert result.get("ahead") == 0
    assert result.get("behind") == 0


def test_stale_worktrees_returns_list_type(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path / "repo")
    result = stale_worktrees(repo)
    assert isinstance(result, list)


# ---------------------------------------------------------------------------
# stale_local_branches — regression coverage for the "release leaves merged
# branches behind" gap: a plain `git merge` (no worktree involved) that
# never got `git branch -d` run on it must be detected.
# ---------------------------------------------------------------------------


def test_stale_local_branches_detects_merged_undeleted_branch(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path / "repo", branch="main")
    _git(repo, "checkout", "-b", "feature/done")
    (repo / "feature.txt").write_text("done\n", encoding="utf-8")
    _git(repo, "add", "feature.txt")
    _git(repo, "commit", "-m", "feature work")
    _git(repo, "checkout", "main")
    _git(repo, "merge", "--no-ff", "feature/done", "-m", "merge feature/done")
    # Branch is merged but was never deleted with `git branch -d`.
    assert stale_local_branches(repo) == ["feature/done"]


def test_stale_local_branches_excludes_unmerged_branch(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path / "repo", branch="main")
    _git(repo, "checkout", "-b", "feature/wip")
    (repo / "wip.txt").write_text("wip\n", encoding="utf-8")
    _git(repo, "add", "wip.txt")
    _git(repo, "commit", "-m", "in progress")
    _git(repo, "checkout", "main")
    assert stale_local_branches(repo) == []


def test_stale_local_branches_excludes_default_and_checked_out_branch(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path / "repo", branch="main")
    _git(repo, "checkout", "-b", "feature/current")
    # Currently checked out, and trivially "merged" (no new commits) — must
    # never be reported as stale (deleting what's checked out is unsafe).
    assert stale_local_branches(repo) == []


def test_stale_local_branches_after_delete_is_clean(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path / "repo", branch="main")
    _git(repo, "checkout", "-b", "feature/done")
    (repo / "feature.txt").write_text("done\n", encoding="utf-8")
    _git(repo, "add", "feature.txt")
    _git(repo, "commit", "-m", "feature work")
    _git(repo, "checkout", "main")
    _git(repo, "merge", "--no-ff", "feature/done", "-m", "merge feature/done")
    _git(repo, "branch", "-d", "feature/done")
    # Proper cleanup (like finish's `git branch -d` step) leaves it clean.
    assert stale_local_branches(repo) == []


def test_stale_local_branches_returns_list_type_on_bad_path(tmp_path: Path) -> None:
    result = stale_local_branches(tmp_path / "does-not-exist")
    assert result == []

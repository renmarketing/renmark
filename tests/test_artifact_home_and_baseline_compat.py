"""Artifact-home compatibility tests.

STAGES order, byte-budget, and capabilities_for coverage are covered elsewhere.
"""

from __future__ import annotations

from pathlib import Path

from renmark import bootstrap, lifecycle, memory, state
from renmark.state._core import _find_repo_root


def test_bootstrap_puts_scaffold_dirs_under_renmark(tmp_path: Path) -> None:
    repo_root = tmp_path / "project"

    bootstrap.bootstrap(repo_root, project_name="demo", init_git=False)

    for subdir in ("specs", "plans", "reviews"):
        assert (repo_root / ".renmark" / subdir / ".gitkeep").is_file()
        assert not (repo_root / subdir).exists()


def test_find_repo_root_walks_up_from_nested_path_and_handles_missing_marker(tmp_path: Path) -> None:
    repo_root = tmp_path / "outer" / "middle" / "inner" / "repo"
    (repo_root / ".renmark").mkdir(parents=True)
    nested = repo_root / ".renmark" / "state" / "wave-summaries" / "deep" / "leaf"
    nested.mkdir(parents=True)

    assert _find_repo_root(nested) == repo_root

    missing_root = tmp_path / "no-marker" / "deep" / "leaf"
    missing_root.mkdir(parents=True)
    assert _find_repo_root(missing_root) is None


def test_canonical_writers_resolve_under_renmark(tmp_path: Path) -> None:
    repo_root = tmp_path / "nested" / "project"
    repo_root.mkdir(parents=True)

    state.write_pipeline_state(repo_root)
    assert (repo_root / ".renmark" / "state" / "pipeline.json").is_file()

    memory.log_feature(repo_root, title="Ship artifact-home compat", date="2026-08-03")
    assert (repo_root / ".renmark" / "memory" / "features.md").is_file()

    lifecycle.write_lifecycle(repo_root, stage="init", feature="artifact-home compat")
    assert (repo_root / ".renmark" / "state" / "lifecycle.json").is_file()

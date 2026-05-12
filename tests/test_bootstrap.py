"""Unit tests for renmark.bootstrap."""
from __future__ import annotations

from pathlib import Path

from renmark import bootstrap


def test_is_empty_project_detects_empty(tmp_path: Path) -> None:
    assert bootstrap.is_empty_project(tmp_path) is True


def test_is_empty_project_detects_non_empty(tmp_path: Path) -> None:
    (tmp_path / "CLAUDE.md").write_text("existing\n")
    assert bootstrap.is_empty_project(tmp_path) is False


def test_bootstrap_creates_skeleton(tmp_path: Path) -> None:
    result = bootstrap.bootstrap(tmp_path, project_name="testproj", init_git=False)
    assert (tmp_path / "CLAUDE.md").is_file()
    assert (tmp_path / "AGENTS.md").is_file()
    assert (tmp_path / ".gitignore").is_file()
    assert (tmp_path / ".renmark" / "memory" / "INDEX.md").is_file()
    assert (tmp_path / ".renmark" / "specs" / ".gitkeep").is_file()
    assert (tmp_path / ".renmark" / "plans" / ".gitkeep").is_file()
    assert (tmp_path / ".renmark" / "reviews" / ".gitkeep").is_file()
    assert "testproj" in (tmp_path / "CLAUDE.md").read_text()


def test_bootstrap_idempotent(tmp_path: Path) -> None:
    bootstrap.bootstrap(tmp_path, project_name="x", init_git=False)
    (tmp_path / "CLAUDE.md").write_text("USER-EDITED\n")
    bootstrap.bootstrap(tmp_path, project_name="x", init_git=False)
    # Second call should not overwrite existing files.
    assert (tmp_path / "CLAUDE.md").read_text() == "USER-EDITED\n"


def test_bootstrap_appends_to_existing_gitignore(tmp_path: Path) -> None:
    (tmp_path / ".gitignore").write_text("node_modules/\n")
    bootstrap.bootstrap(tmp_path, project_name="x", init_git=False)
    text = (tmp_path / ".gitignore").read_text()
    assert "node_modules/" in text
    assert ".renmark/state/" in text


def test_bootstrap_git_init(tmp_path: Path) -> None:
    result = bootstrap.bootstrap(tmp_path, project_name="x", init_git=True)
    assert result.git_initialized is True
    assert (tmp_path / ".git").is_dir()

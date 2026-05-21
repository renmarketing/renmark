"""Tests for renmark.release — version-file drift detection."""
from __future__ import annotations

import json
import textwrap
from pathlib import Path

import pytest

from renmark import release


def _make_repo(tmp_path: Path, version: str = "0.3.1",
               *, mismatch: dict[str, str] | None = None) -> Path:
    """Build a synthetic repo with all VERSION_FILES filled in. mismatch overrides
    individual files with bad values."""
    mismatch = mismatch or {}

    def v(path: str) -> str:
        return mismatch.get(path, version)

    (tmp_path / "VERSION").write_text(v("VERSION") + "\n")
    (tmp_path / "pyproject.toml").write_text(textwrap.dedent(f'''\
        [project]
        name = "renmark"
        version = "{v("pyproject.toml")}"
    '''))
    (tmp_path / "renmark").mkdir()
    (tmp_path / "renmark" / "__init__.py").write_text(
        f'__version__ = "{v("renmark/__init__.py")}"\n'
    )
    (tmp_path / "plugin" / ".claude-plugin").mkdir(parents=True)
    (tmp_path / "plugin" / ".claude-plugin" / "plugin.json").write_text(json.dumps({
        "name": "renmark",
        "version": v("plugin/.claude-plugin/plugin.json"),
        "description": "test",
    }))
    (tmp_path / ".claude-plugin").mkdir()
    (tmp_path / ".claude-plugin" / "marketplace.json").write_text(json.dumps({
        "name": "renmark-local",
        "metadata": {"version": v(".claude-plugin/marketplace.json:metadata")},
        "plugins": [{"name": "renmark",
                     "version": v(".claude-plugin/marketplace.json:plugin"),
                     "source": "./plugin"}],
    }))
    (tmp_path / "README.md").write_text(
        f"# renmark v{v('README.md')}\n\nsome body\n"
    )
    return tmp_path


# ── extractors ───────────────────────────────────────────────────────────────


def test_extract_plain():
    assert release._extract_plain("0.3.1\n") == "0.3.1"
    assert release._extract_plain("") is None


def test_extract_pyproject():
    assert release._extract_pyproject('version = "1.2.3"\n') == "1.2.3"
    assert release._extract_pyproject("no version here") is None


def test_extract_init():
    assert release._extract_init('__version__ = "0.3.1"\n') == "0.3.1"


def test_extract_plugin_json():
    assert release._extract_plugin_json('{"version": "1.2.3"}') == "1.2.3"
    assert release._extract_plugin_json("{not json") is None


def test_extract_marketplace_metadata():
    text = json.dumps({"metadata": {"version": "0.3.1"}})
    assert release._extract_marketplace(text) == "0.3.1"


def test_extract_marketplace_nested():
    text = json.dumps({"plugins": [{"version": "0.3.1"}]})
    assert release._extract_marketplace_plugin(text) == "0.3.1"


def test_extract_readme_header():
    assert release._extract_readme_header("# renmark v0.3.1\nbody") == "0.3.1"
    assert release._extract_readme_header("# something else") is None


# ── check_drift / drift_report ──────────────────────────────────────────────


def test_current_version(tmp_path: Path):
    repo = _make_repo(tmp_path, version="0.3.1")
    assert release.current_version(repo) == "0.3.1"


def test_check_drift_all_in_sync(tmp_path: Path):
    repo = _make_repo(tmp_path, version="0.3.1")
    assert release.drift_report(repo) == []


def test_check_drift_catches_pyproject(tmp_path: Path):
    repo = _make_repo(tmp_path, version="0.3.1",
                      mismatch={"pyproject.toml": "0.3.0"})
    issues = release.drift_report(repo)
    assert any("pyproject.toml" in i and "0.3.0" in i and "0.3.1" in i for i in issues)


def test_check_drift_catches_init_drift(tmp_path: Path):
    repo = _make_repo(tmp_path, version="0.3.1",
                      mismatch={"renmark/__init__.py": "0.2.0"})
    issues = release.drift_report(repo)
    assert any("__init__.py" in i for i in issues)


def test_check_drift_catches_marketplace_inner_disagreement(tmp_path: Path):
    """Marketplace JSON has two version fields. Catch when they disagree."""
    repo = _make_repo(tmp_path, version="0.3.1",
                      mismatch={".claude-plugin/marketplace.json:plugin": "0.3.0"})
    issues = release.drift_report(repo)
    assert any("plugins[0]" in i for i in issues)


def test_check_drift_catches_readme_drift(tmp_path: Path):
    repo = _make_repo(tmp_path, version="0.3.1",
                      mismatch={"README.md": "0.2.5"})
    issues = release.drift_report(repo)
    assert any("README" in i for i in issues)


def test_check_drift_catches_missing_file(tmp_path: Path):
    repo = _make_repo(tmp_path, version="0.3.1")
    (repo / "pyproject.toml").unlink()
    issues = release.drift_report(repo)
    assert any("pyproject.toml" in i and "could not extract" in i for i in issues)


# ── CLI ─────────────────────────────────────────────────────────────────────


def test_cli_check_passes_in_sync(tmp_path: Path, monkeypatch):
    repo = _make_repo(tmp_path, version="0.3.1")
    monkeypatch.chdir(repo)
    assert release.main(["check"]) == 0


def test_cli_check_fails_on_drift(tmp_path: Path, monkeypatch):
    repo = _make_repo(tmp_path, version="0.3.1",
                      mismatch={"renmark/__init__.py": "0.0.0"})
    monkeypatch.chdir(repo)
    assert release.main(["check"]) == 1


def test_cli_current_prints_canonical(tmp_path: Path, monkeypatch, capsys):
    repo = _make_repo(tmp_path, version="0.3.7")
    monkeypatch.chdir(repo)
    release.main(["current"])
    captured = capsys.readouterr()
    assert "0.3.7" in captured.out


def test_cli_rejects_unknown_command():
    assert release.main(["bogus"]) == 2


def test_cli_rejects_empty():
    assert release.main([]) == 2


def test_check_drift_on_real_repo():
    """End-to-end: the real renmark repo MUST be in sync. If this fails,
    a release shipped with mismatched version strings — fix before commit."""
    repo = Path(__file__).resolve().parent.parent
    if not (repo / "VERSION").exists():
        pytest.skip("not running from repo root")
    issues = release.drift_report(repo)
    assert issues == [], (
        "VERSION_FILES drift detected — bump all of them or fix renmark.release:\n  "
        + "\n  ".join(issues)
    )

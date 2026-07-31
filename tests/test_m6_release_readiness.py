"""Release-readiness acceptance tests for M6's read-only report."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from renmark.release import release_readiness_report

VERSION = "6.0.0"


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def _make_ready_repo(tmp_path: Path) -> Path:
    """Create the smallest complete source tree accepted by readiness."""
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "VERSION").write_text(f"{VERSION}\n", encoding="utf-8")
    (repo / "pyproject.toml").write_text(
        f'[project]\nname = "renmark"\nversion = "{VERSION}"\n', encoding="utf-8"
    )
    (repo / "renmark").mkdir()
    (repo / "renmark" / "__init__.py").write_text(
        f'__version__ = "{VERSION}"\n', encoding="utf-8"
    )
    manifest = {"name": "renmark", "version": VERSION, "skills": "skills"}
    _write_json(repo / "plugin" / ".claude-plugin" / "plugin.json", manifest)
    _write_json(repo / "plugin" / ".codex-plugin" / "plugin.json", manifest)
    (repo / "plugin" / "skills").mkdir()
    _write_json(
        repo / ".claude-plugin" / "marketplace.json",
        {"metadata": {"version": VERSION}, "plugins": [{"name": "renmark", "version": VERSION}]},
    )
    (repo / "README.md").write_text(f"# renmark v{VERSION}\n", encoding="utf-8")
    return repo


def _copy_installed_contract(repo: Path, tmp_path: Path) -> Path:
    installed = tmp_path / "installed"
    for rel in ("plugin/.claude-plugin/plugin.json", "plugin/.codex-plugin/plugin.json"):
        target = installed / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((repo / rel).read_bytes())
    return installed


def _files(root: Path) -> dict[str, bytes]:
    return {str(path.relative_to(root)): path.read_bytes() for path in root.rglob("*") if path.is_file()}


def _tags(repo: Path) -> tuple[str, ...]:
    result = subprocess.run(["git", "-C", str(repo), "tag", "--list"], check=True, capture_output=True, text=True)
    return tuple(sorted(result.stdout.splitlines()))


def _read_only_report(repo: Path, installed: Path) -> dict[str, object]:
    subprocess.run(["git", "-C", str(repo), "init", "--quiet"], check=True)
    subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "-c",
            "user.name=Release Readiness Test",
            "-c",
            "user.email=readiness@example.invalid",
            "commit",
            "--quiet",
            "-m",
            "fixture",
        ],
        check=True,
    )
    subprocess.run(["git", "-C", str(repo), "tag", "before-readiness"], check=True)
    source_before, installed_before, tags_before = _files(repo), _files(installed), _tags(repo)

    report = release_readiness_report(repo, installed_root=installed)

    assert _files(repo) == source_before, "readiness must not create a release artifact or modify sources"
    assert _files(installed) == installed_before, "readiness must not install or update an installed plugin"
    assert _tags(repo) == tags_before, "readiness must not create or change git tags"
    assert not (repo / ".renmark").exists(), "readiness must not create a release artifact directory"
    return report


def test_clean_release_readiness_is_ready_and_read_only(tmp_path: Path) -> None:
    repo = _make_ready_repo(tmp_path)
    report = _read_only_report(repo, _copy_installed_contract(repo, tmp_path))

    assert report == {
        "ready": True,
        "blockers": [],
        "checks": {
            "version_drift": [],
            "plugin_identity": [],
            "package_contents": [],
            "installed_contract_parity": [],
        },
    }


def test_release_readiness_blocks_version_drift_without_mutation(tmp_path: Path) -> None:
    repo = _make_ready_repo(tmp_path)
    (repo / "pyproject.toml").write_text('[project]\nversion = "0.0.1"\n', encoding="utf-8")
    report = _read_only_report(repo, _copy_installed_contract(repo, tmp_path))

    assert report["ready"] is False
    assert any("pyproject.toml" in blocker for blocker in report["checks"]["version_drift"])


def test_release_readiness_blocks_plugin_identity_drift_without_mutation(tmp_path: Path) -> None:
    repo = _make_ready_repo(tmp_path)
    codex_manifest = repo / "plugin" / ".codex-plugin" / "plugin.json"
    _write_json(codex_manifest, {"name": "other", "version": VERSION, "skills": "skills"})
    report = _read_only_report(repo, _copy_installed_contract(repo, tmp_path))

    assert report["ready"] is False
    assert any("host manifest names disagree" in blocker for blocker in report["checks"]["plugin_identity"])


def test_release_readiness_blocks_installed_contract_drift_without_mutation(tmp_path: Path) -> None:
    repo = _make_ready_repo(tmp_path)
    installed = _copy_installed_contract(repo, tmp_path)
    _write_json(installed / "plugin" / ".codex-plugin" / "plugin.json", {"name": "renmark", "version": "0.0.1"})
    report = _read_only_report(repo, installed)

    assert report["ready"] is False
    assert any("Codex manifest differs" in blocker for blocker in report["checks"]["installed_contract_parity"])

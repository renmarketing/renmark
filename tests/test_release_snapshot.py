"""Tests for renmark.release.build_version_snapshot."""
from __future__ import annotations

import json
import subprocess
import zipfile
from pathlib import Path

from renmark import release

# ── fixture helpers ──────────────────────────────────────────────────────────


def _make_snapshot_repo(tmp_path: Path, version: str = "1.2.3") -> Path:
    """Build a minimal tmp repo suitable for build_version_snapshot tests."""
    # Canonical version file
    (tmp_path / "VERSION").write_text(version + "\n")

    # Plugin manifest (needed for package_basename)
    plugin_dir = tmp_path / "plugin" / ".claude-plugin"
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "plugin.json").write_text(
        json.dumps({"name": "renmark", "version": version, "description": "test"})
    )

    # CHANGELOG with a real section containing a unique marker
    (tmp_path / "CHANGELOG.md").write_text(
        f"## v{version} — 2026-06-09 (x)\n\nUNIQUE_CHANGELOG_MARKER\n\n## v1.0.0 — older\n\nOld.\n"
    )

    # Verification artifact under .renmark/reviews/
    reviews_dir = tmp_path / ".renmark" / "reviews"
    reviews_dir.mkdir(parents=True)
    (reviews_dir / "2026-01-01-x.verification.md").write_text(
        "UNIQUE_VERIFICATION_MARKER\n"
    )

    # Application files that SHOULD be packaged
    (tmp_path / "renmark").mkdir(exist_ok=True)
    (tmp_path / "renmark" / "foo.py").write_text("# foo\n")
    (tmp_path / "README.md").write_text(f"# renmark v{version}\n\nsome body\n")

    # Junk that MUST NOT appear in the snapshot
    (tmp_path / ".git").mkdir(exist_ok=True)
    (tmp_path / ".git" / "config").write_text("[core]\n")
    (tmp_path / "node_modules").mkdir(exist_ok=True)
    (tmp_path / "node_modules" / "x.js").write_text("// x\n")
    (tmp_path / "__pycache__").mkdir(exist_ok=True)
    (tmp_path / "__pycache__" / "y.pyc").write_bytes(b"\x00\x00")
    baks_dir = tmp_path / ".renmark" / "baks"
    baks_dir.mkdir(parents=True, exist_ok=True)
    (baks_dir / "old.zip").write_bytes(b"PK\x05\x06" + b"\x00" * 18)

    # Optionally init a real git repo so git-dependent helpers have something
    # to talk to — but tests must not depend on it, only on fallback behaviour.
    try:
        subprocess.run(
            ["git", "-C", str(tmp_path), "init", "--quiet"],
            check=True, capture_output=True,
        )
        subprocess.run(
            ["git", "-C", str(tmp_path), "config", "user.email", "test@test.com"],
            check=True, capture_output=True,
        )
        subprocess.run(
            ["git", "-C", str(tmp_path), "config", "user.name", "Test"],
            check=True, capture_output=True,
        )
        subprocess.run(
            ["git", "-C", str(tmp_path), "add", "-A"],
            check=True, capture_output=True,
        )
        subprocess.run(
            ["git", "-C", str(tmp_path), "commit", "-m", "init", "--quiet"],
            check=True, capture_output=True,
        )
    except (OSError, subprocess.CalledProcessError):
        pass  # git absent or broken — fallbacks tested below

    return tmp_path


# ── main snapshot tests ──────────────────────────────────────────────────────


def test_snapshot_zip_exists(tmp_path: Path):
    repo = _make_snapshot_repo(tmp_path)
    result = release.build_version_snapshot(str(tmp_path), now="2026-06-09T00:00:00")
    zip_path = tmp_path / ".renmark" / "version" / "renmark-v1.2.3.zip"
    assert zip_path.exists(), f"zip not found at {zip_path}"
    assert result["zip"] == str(zip_path)
    assert result["version"] == "1.2.3"


def test_snapshot_dir_and_metadata_files_exist(tmp_path: Path):
    _make_snapshot_repo(tmp_path)
    result = release.build_version_snapshot(str(tmp_path), now="2026-06-09T00:00:00")
    snap = tmp_path / ".renmark" / "version" / "v1.2.3"
    assert snap.is_dir(), f"snapshot dir not found: {snap}"
    assert result["snapshot_dir"] == str(snap)
    for fname in ("manifest.json", "release.md", "verification.md", "files-changed.txt"):
        assert (snap / fname).exists(), f"missing metadata file: {fname}"
    assert result["manifest"] == str(snap / "manifest.json")


def test_snapshot_unpacked_contains_app_files(tmp_path: Path):
    _make_snapshot_repo(tmp_path)
    release.build_version_snapshot(str(tmp_path), now="2026-06-09T00:00:00")
    snap = tmp_path / ".renmark" / "version" / "v1.2.3"
    assert (snap / "renmark" / "foo.py").exists(), "renmark/foo.py missing from snapshot"
    assert (snap / "README.md").exists(), "README.md missing from snapshot"


def test_snapshot_excludes_junk_dirs(tmp_path: Path):
    _make_snapshot_repo(tmp_path)
    release.build_version_snapshot(str(tmp_path), now="2026-06-09T00:00:00")
    snap = tmp_path / ".renmark" / "version" / "v1.2.3"

    assert not (snap / ".git").exists(), ".git leaked into snapshot"
    assert not (snap / "node_modules").exists(), "node_modules leaked into snapshot"
    assert not (snap / "__pycache__").exists(), "__pycache__ leaked into snapshot"

    # .renmark subtree itself must not recurse (no baks/ inside snapshot)
    assert not (snap / ".renmark").exists(), ".renmark subtree leaked into snapshot"


def test_snapshot_manifest_fields(tmp_path: Path):
    _make_snapshot_repo(tmp_path)
    result = release.build_version_snapshot(str(tmp_path), now="2026-06-09T00:00:00")
    manifest_path = Path(result["manifest"])
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert manifest["version"] == "1.2.3"
    assert manifest["tag"] == "v1.2.3"
    assert manifest["created_at"] == "2026-06-09T00:00:00"
    assert isinstance(manifest["file_count"], int)
    assert manifest["file_count"] >= 1
    assert isinstance(manifest["excludes"], list)
    assert len(manifest["excludes"]) > 0


def test_snapshot_release_md_contains_changelog_marker(tmp_path: Path):
    _make_snapshot_repo(tmp_path)
    release.build_version_snapshot(str(tmp_path), now="2026-06-09T00:00:00")
    snap = tmp_path / ".renmark" / "version" / "v1.2.3"
    text = (snap / "release.md").read_text(encoding="utf-8")
    assert "UNIQUE_CHANGELOG_MARKER" in text, "CHANGELOG marker not found in release.md"


def test_snapshot_verification_md_contains_marker(tmp_path: Path):
    _make_snapshot_repo(tmp_path)
    release.build_version_snapshot(str(tmp_path), now="2026-06-09T00:00:00")
    snap = tmp_path / ".renmark" / "version" / "v1.2.3"
    text = (snap / "verification.md").read_text(encoding="utf-8")
    assert "UNIQUE_VERIFICATION_MARKER" in text, "verification marker not found"


def test_snapshot_files_changed_exists_and_nonempty(tmp_path: Path):
    """files-changed.txt must exist and be non-empty.

    Content depends on git availability — either a real diff or the
    '# (git unavailable)' fallback. We assert existence + non-empty only.
    """
    _make_snapshot_repo(tmp_path)
    release.build_version_snapshot(str(tmp_path), now="2026-06-09T00:00:00")
    snap = tmp_path / ".renmark" / "version" / "v1.2.3"
    fc = snap / "files-changed.txt"
    assert fc.exists(), "files-changed.txt missing"
    assert len(fc.read_text(encoding="utf-8").strip()) > 0, "files-changed.txt is empty"


def test_snapshot_zip_contains_app_files(tmp_path: Path):
    """The distribution zip must also include app files (not just unpacked copy)."""
    _make_snapshot_repo(tmp_path)
    release.build_version_snapshot(str(tmp_path), now="2026-06-09T00:00:00")
    zip_path = tmp_path / ".renmark" / "version" / "renmark-v1.2.3.zip"
    names = zipfile.ZipFile(zip_path).namelist()
    joined = "\n".join(names)
    assert any("foo.py" in n for n in names), "renmark/foo.py missing from zip"
    assert any("README.md" in n for n in names), "README.md missing from zip"
    # excluded dirs must not appear in zip either
    assert ".git" not in joined
    assert "node_modules" not in joined
    assert "__pycache__" not in joined
    assert ".renmark/" not in joined


def test_snapshot_idempotent_no_raise(tmp_path: Path):
    """Calling build_version_snapshot twice with the same version must not raise
    and must rebuild the snapshot dir cleanly."""
    _make_snapshot_repo(tmp_path)
    result1 = release.build_version_snapshot(str(tmp_path), now="2026-06-09T00:00:00")
    # Mutate snap dir to prove it gets rebuilt
    snap = Path(result1["snapshot_dir"])
    sentinel = snap / "sentinel.txt"
    sentinel.write_text("should be gone after rebuild")

    result2 = release.build_version_snapshot(str(tmp_path), now="2026-06-09T00:00:00")
    assert result2["version"] == "1.2.3"
    assert not sentinel.exists(), "snapshot dir was NOT rebuilt on second call"
    assert Path(result2["snapshot_dir"]).is_dir()


def test_snapshot_fallback_release_md_when_no_changelog_section(tmp_path: Path):
    """When CHANGELOG.md has no matching section, release.md gets the stub fallback."""
    _make_snapshot_repo(tmp_path)
    # Overwrite CHANGELOG with a section for a different version
    (tmp_path / "CHANGELOG.md").write_text("## v9.9.9 — unrelated\n\nNothing here.\n")
    release.build_version_snapshot(str(tmp_path), now="2026-06-09T00:00:00")
    snap = tmp_path / ".renmark" / "version" / "v1.2.3"
    text = (snap / "release.md").read_text(encoding="utf-8")
    assert "See CHANGELOG.md" in text


def test_snapshot_fallback_verification_md_when_no_reviews(tmp_path: Path):
    """When .renmark/reviews/ has no *.verification.md, verification.md is the stub."""
    _make_snapshot_repo(tmp_path)
    # Remove the verification file seeded in _make_snapshot_repo
    vf = tmp_path / ".renmark" / "reviews" / "2026-01-01-x.verification.md"
    if vf.exists():
        vf.unlink()
    release.build_version_snapshot(str(tmp_path), now="2026-06-09T00:00:00")
    snap = tmp_path / ".renmark" / "version" / "v1.2.3"
    text = (snap / "verification.md").read_text(encoding="utf-8")
    assert "No verification artifact found" in text


def test_snapshot_file_count_matches_manifest(tmp_path: Path):
    """file_count in the manifest must match the returned file_count string."""
    _make_snapshot_repo(tmp_path)
    result = release.build_version_snapshot(str(tmp_path), now="2026-06-09T00:00:00")
    manifest = json.loads(Path(result["manifest"]).read_text(encoding="utf-8"))
    assert str(manifest["file_count"]) == result["file_count"]

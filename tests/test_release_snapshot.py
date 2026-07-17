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
    (plugin_dir / "plugin.json").write_text(json.dumps({"name": "renmark", "version": version, "description": "test"}))
    codex_plugin_dir = tmp_path / "plugin" / ".codex-plugin"
    codex_plugin_dir.mkdir(parents=True)
    (codex_plugin_dir / "plugin.json").write_text(
        json.dumps({"name": "renmark", "version": version, "description": "test"})
    )

    # CHANGELOG with a real section containing a unique marker
    (tmp_path / "CHANGELOG.md").write_text(
        f"## v{version} — 2026-06-09 (x)\n\nUNIQUE_CHANGELOG_MARKER\n\n## v1.0.0 — older\n\nOld.\n"
    )

    # Verification artifact under .renmark/reviews/
    reviews_dir = tmp_path / ".renmark" / "reviews"
    reviews_dir.mkdir(parents=True)
    (reviews_dir / "2026-01-01-x.verification.md").write_text("UNIQUE_VERIFICATION_MARKER\n")

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
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "-C", str(tmp_path), "config", "user.email", "test@test.com"],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "-C", str(tmp_path), "config", "user.name", "Test"],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "-C", str(tmp_path), "add", "-A"],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "-C", str(tmp_path), "commit", "-m", "init", "--quiet"],
            check=True,
            capture_output=True,
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


# ── codereview-finding regression tests ──────────────────────────────────────


def test_symlink_outside_repo_not_archived(tmp_path: Path):
    """FINDING 1: a repo-local symlink pointing OUTSIDE the repo must NOT be
    dereferenced into the zip or the unpacked snapshot (host-secret leak)."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _make_snapshot_repo(repo)

    # A secret living OUTSIDE the repo
    secret = tmp_path / "host_secret.txt"
    secret.write_text("SUPER_SECRET_HOST_TOKEN\n")

    # Repo-local symlink that points at the outside secret
    link = repo / "leak.txt"
    try:
        link.symlink_to(secret)
    except (OSError, NotImplementedError):
        import pytest

        pytest.skip("symlinks not supported on this platform")

    result = release.build_version_snapshot(str(repo), now="2026-06-09T00:00:00")

    # Not in the unpacked snapshot
    snap = Path(result["snapshot_dir"])
    assert not (snap / "leak.txt").exists(), "symlink leaked into unpacked snapshot"

    # Not in the zip, and the secret content is absent
    zf = zipfile.ZipFile(result["zip"])
    names = zf.namelist()
    assert not any("leak.txt" in n for n in names), "symlink leaked into zip"
    for n in names:
        if n.endswith("/"):
            continue
        assert b"SUPER_SECRET_HOST_TOKEN" not in zf.read(n), f"secret leaked via {n}"


def test_changelog_section_exact_version_match(tmp_path: Path):
    """FINDING 2: requesting 1.2.3 must NOT match a ## v1.2.30 heading, and
    MUST match the real ## v1.2.3 heading."""
    _make_snapshot_repo(tmp_path, version="1.2.3")
    # v1.2.30 appears FIRST so a substring match would wrongly grab it.
    (tmp_path / "CHANGELOG.md").write_text(
        "## v1.2.30 — decoy\n\nDECOY_MARKER_30\n\n## v1.2.3 — real\n\nCORRECT_MARKER_3\n\n## v1.0.0 — older\n\nOld.\n"
    )
    release.build_version_snapshot(str(tmp_path), now="2026-06-09T00:00:00")
    snap = tmp_path / ".renmark" / "version" / "v1.2.3"
    text = (snap / "release.md").read_text(encoding="utf-8")
    assert "CORRECT_MARKER_3" in text, "did not select the real ## v1.2.3 section"
    assert "DECOY_MARKER_30" not in text, "wrongly matched ## v1.2.30"


def test_verification_artifact_matches_head_sha(tmp_path: Path):
    """FINDING 3: with two *.verification.md artifacts, the one whose filename
    contains the current HEAD sha must be chosen."""
    _make_snapshot_repo(tmp_path)
    head = subprocess.run(
        ["git", "-C", str(tmp_path), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
    )
    if head.returncode != 0 or not head.stdout.strip():
        import pytest

        pytest.skip("git unavailable — cannot resolve HEAD sha")
    sha = head.stdout.strip()

    reviews = tmp_path / ".renmark" / "reviews"
    # Remove the seeded artifact; create two: one matching HEAD, one not.
    for f in reviews.glob("*.verification.md"):
        f.unlink()
    # Lexicographically LAST is the decoy, to prove sha-match beats sort order.
    (reviews / f"2026-01-01-{sha}.verification.md").write_text("HEAD_MATCH_MARKER\n")
    (reviews / "2099-12-31-deadbeef.verification.md").write_text("DECOY_MARKER\n")

    release.build_version_snapshot(str(tmp_path), now="2026-06-09T00:00:00")
    snap = tmp_path / ".renmark" / "version" / "v1.2.3"
    text = (snap / "verification.md").read_text(encoding="utf-8")
    assert "HEAD_MATCH_MARKER" in text, "did not select the HEAD-sha artifact"
    assert "DECOY_MARKER" not in text, "wrongly selected the lexicographically-last artifact"


def test_snapshot_dest_dir_and_archive_stem(tmp_path: Path):
    """FINDING 4: dest_dir + archive_stem write the zip AND the unpacked dir
    under the given dest, named by the stem."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _make_snapshot_repo(repo)
    out = tmp_path / "out"

    result = release.build_version_snapshot(
        str(repo),
        now="2026-06-09T00:00:00",
        dest_dir=str(out),
        archive_stem="custom",
    )

    zip_path = out / "custom.zip"
    snap_dir = out / "custom"
    assert zip_path.exists(), f"zip not written under dest_dir: {zip_path}"
    assert snap_dir.is_dir(), f"unpacked dir not written under dest_dir: {snap_dir}"
    assert result["zip"] == str(zip_path)
    assert result["snapshot_dir"] == str(snap_dir)
    assert (snap_dir / "manifest.json").exists()
    # Default location must NOT have been used
    assert not (repo / ".renmark" / "version" / "v1.2.3").exists()


def test_snapshot_stale_symlink_target_no_raise(tmp_path: Path):
    """FINDING 5: when the target unpacked dir is a stale (dangling) symlink,
    rebuilding the snapshot must not raise."""
    _make_snapshot_repo(tmp_path)
    version_dir = tmp_path / ".renmark" / "version"
    version_dir.mkdir(parents=True, exist_ok=True)
    snap = version_dir / "v1.2.3"
    try:
        snap.symlink_to(tmp_path / "does_not_exist")
    except (OSError, NotImplementedError):
        import pytest

        pytest.skip("symlinks not supported on this platform")

    # Must not raise even though snap is a dangling symlink.
    result = release.build_version_snapshot(str(tmp_path), now="2026-06-09T00:00:00")
    assert Path(result["snapshot_dir"]).is_dir()
    assert not Path(result["snapshot_dir"]).is_symlink()

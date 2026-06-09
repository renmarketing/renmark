"""Version-file drift detection — Layer 1 guardrail.

Pulled forward from the v0.4.0 release skill: the full `/renmark:release`
skill ships later, but `check_drift` lands now as a pre-commit guard so
versions can't silently fall out of sync between releases.

VERSION_FILES catalogs every file in the repo that carries a copy of the
canonical version string. Adding a new file is a one-line change here.

CLI:
    python -m renmark.release check            # exit 0 if all in sync, 1 if drifted
    python -m renmark.release current          # print the canonical version
    python -m renmark.release scan PATH        # show all version strings found in PATH

Bump / tag / zip operations are deferred to v0.4.0 — this module is
read-only by design at v0.3.1.
"""

from __future__ import annotations

import contextlib
import json
import re
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

# ── Version-file catalog ─────────────────────────────────────────────────────


@dataclass(frozen=True)
class VersionFile:
    """One location in the repo that carries a copy of the canonical version.

    ``extract`` parses the version out of the file's text. ``replace`` is
    reserved for the v0.4.0 release skill — left as None at v0.3.1.
    """

    path: str
    extract: Callable[[str], str | None]
    replace: Callable[[str, str], str] | None = None
    description: str = ""


def _extract_plain(text: str) -> str | None:
    """For a file that contains nothing but the version (e.g. VERSION)."""
    line = text.strip().splitlines()[0] if text.strip() else ""
    return line or None


_PYPROJECT_RE = re.compile(r'^version\s*=\s*"([^"]+)"', re.MULTILINE)


def _extract_pyproject(text: str) -> str | None:
    m = _PYPROJECT_RE.search(text)
    return m.group(1) if m else None


_INIT_VERSION_RE = re.compile(r'^__version__\s*=\s*"([^"]+)"', re.MULTILINE)


def _extract_init(text: str) -> str | None:
    m = _INIT_VERSION_RE.search(text)
    return m.group(1) if m else None


def _extract_plugin_json(text: str) -> str | None:
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None
    v = data.get("version")
    return v if isinstance(v, str) else None


def _extract_marketplace(text: str) -> str | None:
    """Marketplace JSON has TWO version fields — both must agree.

    Returns the metadata.version. If the nested plugins[0].version disagrees,
    check_drift will catch it because we list the file twice with different
    extractors.
    """
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None
    v = data.get("metadata", {}).get("version")
    return v if isinstance(v, str) else None


def _extract_marketplace_plugin(text: str) -> str | None:
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None
    plugins = data.get("plugins", [])
    if not plugins:
        return None
    v = plugins[0].get("version")
    return v if isinstance(v, str) else None


_README_HEADER_RE = re.compile(r"^# renmark v(\S+)", re.MULTILINE)


def _extract_readme_header(text: str) -> str | None:
    m = _README_HEADER_RE.search(text)
    return m.group(1) if m else None


# Catalog. Adding a new version-bearing file is one entry here.
VERSION_FILES: list[VersionFile] = [
    VersionFile("VERSION", _extract_plain, description="canonical version (1 line)"),
    VersionFile("pyproject.toml", _extract_pyproject, description="pip package metadata"),
    VersionFile("renmark/__init__.py", _extract_init, description="Python __version__"),
    VersionFile(
        "plugin/.claude-plugin/plugin.json",
        _extract_plugin_json,
        description="Claude Code plugin manifest",
    ),
    VersionFile(
        ".claude-plugin/marketplace.json",
        _extract_marketplace,
        description="marketplace metadata.version",
    ),
    VersionFile(
        ".claude-plugin/marketplace.json",
        _extract_marketplace_plugin,
        description="marketplace plugins[0].version",
    ),
    VersionFile("README.md", _extract_readme_header, description="README h1 header"),
]


# ── Packaging ─────────────────────────────────────────────────────────────────
# Builds a versioned distribution zip into the PROJECT's .renmark/baks/ — a
# local mirror of what would be attached to the matching GitHub release tag
# v<version>. Pure-Python (no rsync/zip CLI dependency). Honors the
# project-write-boundary rule: writes only inside the project.

import fnmatch
import shutil
import subprocess
import zipfile
from datetime import datetime

BAKS_SUBDIR = ".renmark/baks"  # legacy release home — still readable, no longer the default
VERSION_SUBDIR = ".renmark/version"

# Anything matching these (by path segment or glob) is left out of the package.
PACKAGE_EXCLUDES: tuple[str, ...] = (
    ".git",
    ".venv",
    "venv",
    ".pytest_cache",
    "__pycache__",
    "*.pyc",
    "*.egg-info",
    ".env*",
    "*Zone.Identifier*",
    ".claude",
    ".renmark",
    "PLAN.md",
    "node_modules",
    # Secret-bearing files must never reach a zip that finish can upload to a
    # (potentially public) GitHub release.
    "*.pem",
    "*.key",
    "*.p12",
    "id_rsa*",
    "id_ed25519*",
    "credentials*.json",
    "service-account*.json",
    ".npmrc",
    ".pypirc",
    ".netrc",
)

# Non-secret env documentation files stay packageable despite ".env*".
PACKAGE_ALLOW: tuple[str, ...] = (".env.example", ".env.sample", ".env.template")


def _is_excluded(rel_parts: tuple[str, ...]) -> bool:
    """True if any path segment matches a PACKAGE_EXCLUDES pattern."""
    for seg in rel_parts:
        if seg in PACKAGE_ALLOW:
            continue
        for pat in PACKAGE_EXCLUDES:
            if fnmatch.fnmatch(seg, pat):
                return True
    return False


def package_basename(repo: Path | str = ".") -> str:
    """Archive base name = plugin manifest name, falling back to the repo dir."""
    repo = Path(repo)
    manifest = repo / "plugin" / ".claude-plugin" / "plugin.json"
    if manifest.exists():
        try:
            name = json.loads(manifest.read_text(encoding="utf-8")).get("name")
            if isinstance(name, str) and name:
                return name
        except (json.JSONDecodeError, OSError):
            pass
    return repo.resolve().name


def build_package(
    repo: Path | str = ".",
    *,
    version: str | None = None,
    dest_dir: Path | str | None = None,
    archive_stem: str | None = None,
) -> Path:
    """Build a versioned distribution zip.

    Default (consumer project): writes to `<repo>/.renmark/version/<basename>-v<version>.zip`,
    version-anchored so it matches the git tag `v<version>` and the GitHub
    release of the same version. The zip's top-level folder equals the archive
    stem (clean extraction). Returns the zip path. (`.renmark/baks/` was the
    previous default and remains readable as a legacy location.)

    Overrides (maintainer escape hatch — e.g. packaging renmark's OWN release
    to a sibling directory rather than into a managed project):
    - `dest_dir`   — write the zip here instead of `<repo>/.renmark/version/`.
    - `archive_stem` — full archive name without extension (also the zip's
      top-level folder). Lets callers match an existing naming convention such
      as `ai-system-renmark-v0.3.3-20260527`.

    Pure-Python, offline, no external CLI. By default writes only inside the
    project (project-write-boundary rule); `dest_dir` is an explicit opt-out for
    maintainer release builds. Overwrites an existing same-name zip.
    """
    repo = Path(repo)
    ver = version or current_version(repo)
    stem = archive_stem or f"{package_basename(repo)}-v{ver}"

    out_dir = Path(dest_dir).expanduser() if dest_dir is not None else repo / VERSION_SUBDIR
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{stem}.zip"
    if out.exists():
        out.unlink()

    files: list[Path] = []
    for p in sorted(repo.rglob("*")):
        # Skip symlinks BEFORE is_file() so a repo-local symlink pointing
        # OUTSIDE the repo is never dereferenced and archived (host-secret
        # leak). Simplest safe fix — do not follow.
        if p.is_symlink():
            continue
        if not p.is_file():
            continue
        rel = p.relative_to(repo)
        if _is_excluded(rel.parts):
            continue
        files.append(p)

    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in files:
            rel = p.relative_to(repo)
            zf.write(p, f"{stem}/{rel.as_posix()}")
    return out


def _git_stdout(repo: Path, args: list[str]) -> str | None:
    """Run a git command under ``repo`` and return stripped stdout, or None on failure.

    Never raises — any subprocess/OS error degrades to None so callers can fall
    back gracefully (git-unavailable, not-a-repo, command error all → None).
    """
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo), *args],
            capture_output=True,
            text=True,
        )
    except (OSError, ValueError):
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout.strip()


def _changelog_section(repo: Path, ver: str) -> str:
    """Extract the CHANGELOG.md section for ``ver``.

    Finds the first ``## `` heading line containing ``ver`` as a whole token
    (covers ``## [date]`` blocks naming the version and ``## v{ver}``
    headings), then includes lines until the next ``## `` heading. The token
    boundary ensures ``1.2.3`` does NOT match ``## v1.2.30``. Falls back to a
    stub if the file or section is missing.
    """
    fallback = f"# Release v{ver}\n\nSee CHANGELOG.md."
    changelog = repo / "CHANGELOG.md"
    try:
        text = changelog.read_text(encoding="utf-8")
    except OSError:
        return fallback

    lines = text.splitlines()
    start: int | None = None
    # Match ``ver`` as a whole token, allowing an optional ``v`` prefix
    # (``## v1.2.3``). The leading boundary sits before the optional ``v`` so
    # the prefix doesn't break the lookbehind; the trailing ``(?![\w.])`` keeps
    # ``1.2.3`` from matching ``## v1.2.30``.
    ver_token_re = re.compile(r"(?<![\w.])v?" + re.escape(ver) + r"(?![\w.])")
    for idx, line in enumerate(lines):
        if line.startswith("## ") and ver_token_re.search(line):
            start = idx
            break
    if start is None:
        return fallback

    section = [lines[start]]
    for line in lines[start + 1 :]:
        if line.startswith("## "):
            break
        section.append(line)
    return "\n".join(section).strip() + "\n"


def _latest_verification(
    repo: Path, ver: str, verification_path: str | None = None
) -> str:
    """Return the text of the relevant ``.renmark/reviews/*.verification.md``.

    Selection order (artifacts are named ``YYYY-MM-DD-<sha>.verification.md``):
    (a) if ``verification_path`` is given and exists, use it;
    (b) else the artifact whose filename contains the current full HEAD sha
        (so the snapshot embeds THIS run's verification, not an unrelated run);
    (c) else the lexicographically-last artifact as a last resort;
    (d) else the "No verification artifact found" fallback.

    Never raises — any read error degrades to the fallback.
    """
    fallback = f"No verification artifact found for v{ver}."

    # (a) explicit path wins
    if verification_path is not None:
        explicit = Path(verification_path)
        if explicit.exists():
            try:
                return explicit.read_text(encoding="utf-8")
            except OSError:
                return fallback

    reviews = repo / ".renmark" / "reviews"
    if not reviews.is_dir():
        return fallback
    candidates = sorted(reviews.glob("*.verification.md"))
    if not candidates:
        return fallback

    # (b) prefer the artifact whose filename contains the current HEAD sha
    head_sha = _git_stdout(repo, ["rev-parse", "HEAD"])
    if head_sha:
        for cand in candidates:
            if head_sha in cand.name:
                try:
                    return cand.read_text(encoding="utf-8")
                except OSError:
                    return fallback

    # (c) lexicographically-last as a last resort
    try:
        return candidates[-1].read_text(encoding="utf-8")
    except OSError:
        return fallback


def _files_changed(repo: Path, ver: str) -> str:
    """Return ``git diff --name-only <prev>..HEAD`` text, or a degraded fallback.

    ``<prev>`` is the previous ``v*`` tag (newest-first, skipping the current
    ``v{ver}``). With no prior tag, falls back to ``git ls-files``. Any git
    failure yields the single line ``# (git unavailable)``. Never raises.
    """
    unavailable = "# (git unavailable)\n"
    tags_out = _git_stdout(repo, ["tag", "--list", "v*", "--sort=-v:refname"])
    if tags_out is None:
        return unavailable

    cur = f"v{ver}"
    prev: str | None = None
    for tag in (t for t in tags_out.splitlines() if t.strip()):
        if tag == cur:
            continue
        prev = tag
        break

    if prev is None:
        listing = _git_stdout(repo, ["ls-files"])
        if listing is None:
            return unavailable
        return listing + "\n" if listing else ""

    diff = _git_stdout(repo, ["diff", "--name-only", f"{prev}..HEAD"])
    if diff is None:
        return unavailable
    return diff + "\n" if diff else ""


def _rmtree_robust(target: Path) -> None:
    """Remove ``target`` robustly; never raise.

    - If ``target`` is a symlink (possibly stale/dangling), unlink it rather
      than recursing through it.
    - Otherwise ``shutil.rmtree`` with an onerror handler that chmods +w and
      retries (handles read-only files on some filesystems).
    """
    if target.is_symlink():
        with contextlib.suppress(OSError):
            target.unlink()
        return

    def _on_error(func: Callable[..., object], path: str, _exc: object) -> None:
        import os
        import stat

        with contextlib.suppress(OSError):
            os.chmod(path, stat.S_IWRITE)
            func(path)

    with contextlib.suppress(OSError):
        shutil.rmtree(target, onerror=_on_error)


def build_version_snapshot(
    repo: Path | str = ".",
    *,
    version: str | None = None,
    now: str | None = None,
    dest_dir: Path | str | None = None,
    archive_stem: str | None = None,
    verification_path: str | None = None,
) -> dict[str, str]:
    """Build a full version snapshot.

    Produces, for version ``ver`` (``version`` arg or ``current_version(repo)``):
    - a distribution zip ``<basename>-v<ver>.zip`` (via ``build_package``), and
    - an unpacked copy mirroring the packaged file set (same ``_is_excluded``
      filter — so ``.git``, ``node_modules``, ``__pycache__``, ``.venv`` and
      ALL of ``.renmark`` are skipped, no recursion into the snapshot itself,
      symlinks are skipped), plus four metadata files written INTO the dir:
      ``manifest.json``, ``release.md``, ``verification.md``, ``files-changed.txt``.

    Default (no overrides): both the zip and the ``v<ver>/`` unpacked dir are
    written under ``<repo>/.renmark/version/``.

    Maintainer escape hatch:
    - ``dest_dir``     — write the zip AND the unpacked dir under this directory
      instead of ``<repo>/.renmark/version/``. The unpacked dir is named after
      ``archive_stem`` when given, else ``v<ver>/``.
    - ``archive_stem`` — passed through to ``build_package`` as the zip's name
      and top-level folder; also names the unpacked dir under ``dest_dir``.
    - ``verification_path`` — explicit verification artifact to embed; see
      ``_latest_verification`` for the full selection order.

    Reuses ``build_package`` / ``package_basename`` / ``current_version`` /
    ``PACKAGE_EXCLUDES`` / ``_is_excluded``. Never raises on git/verification/
    changelog absence — each degrades to a documented fallback.
    """
    repo = Path(repo)
    ver = version or current_version(repo)
    base = Path(dest_dir).expanduser() if dest_dir is not None else repo / VERSION_SUBDIR
    base.mkdir(parents=True, exist_ok=True)

    zip_path = build_package(repo, version=ver, dest_dir=base, archive_stem=archive_stem)

    snap_name = archive_stem if archive_stem is not None else f"v{ver}"
    snap = base / snap_name
    if snap.exists() or snap.is_symlink():
        _rmtree_robust(snap)
    snap.mkdir(parents=True, exist_ok=True)

    file_count = 0
    for p in sorted(repo.rglob("*")):
        # Skip symlinks BEFORE is_file() — a repo-local symlink pointing
        # OUTSIDE the repo must never be dereferenced and copied (secret leak).
        if p.is_symlink():
            continue
        if not p.is_file():
            continue
        rel = p.relative_to(repo)
        if _is_excluded(rel.parts):
            continue
        dest = snap / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, dest)
        file_count += 1

    source_sha = _git_stdout(repo, ["rev-parse", "HEAD"]) or ""
    created_at = now if now is not None else datetime.now().isoformat()
    manifest = {
        "version": ver,
        "tag": f"v{ver}",
        "source_sha": source_sha,
        "created_at": created_at,
        "file_count": file_count,
        "basename": package_basename(repo),
        "excludes": list(PACKAGE_EXCLUDES),
    }
    (snap / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    (snap / "release.md").write_text(_changelog_section(repo, ver), encoding="utf-8")
    (snap / "verification.md").write_text(
        _latest_verification(repo, ver, verification_path), encoding="utf-8"
    )
    (snap / "files-changed.txt").write_text(_files_changed(repo, ver), encoding="utf-8")

    return {
        "version": ver,
        "zip": str(zip_path),
        "snapshot_dir": str(snap),
        "manifest": str(snap / "manifest.json"),
        "file_count": str(file_count),
    }


# ── API ──────────────────────────────────────────────────────────────────────


def current_version(repo: Path | str = ".") -> str:
    """Read VERSION as the canonical truth."""
    p = Path(repo) / "VERSION"
    return p.read_text(encoding="utf-8").strip()


def check_drift(repo: Path | str = ".") -> dict[str, str | None]:
    """Read every VERSION_FILES entry and return a dict {path/desc: extracted_version}.

    Caller compares against current_version(repo). A drift exists if any
    extracted version != canonical, or if any extraction returned None.
    """
    repo = Path(repo)
    out: dict[str, str | None] = {}
    for vf in VERSION_FILES:
        target = repo / vf.path
        if not target.exists():
            out[f"{vf.path} :: {vf.description}"] = None
            continue
        try:
            text = target.read_text(encoding="utf-8")
        except OSError:
            out[f"{vf.path} :: {vf.description}"] = None
            continue
        out[f"{vf.path} :: {vf.description}"] = vf.extract(text)
    return out


def drift_report(repo: Path | str = ".") -> list[str]:
    """Return a list of human-readable drift issues. Empty list = all in sync."""
    canonical = current_version(repo)
    issues: list[str] = []
    found = check_drift(repo)
    for label, version in found.items():
        if version is None:
            issues.append(f"{label}: could not extract version")
        elif version != canonical:
            issues.append(f"{label}: found {version!r}, expected {canonical!r}")
    return issues


# ── CLI ──────────────────────────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        sys.stderr.write(
            "usage: python -m renmark.release "
            "{check|current|scan PATH|package [PATH]|snapshot [PATH]}\n"
        )
        return 2

    cmd = argv[0]

    if cmd == "current":
        sys.stdout.write(current_version() + "\n")
        return 0

    if cmd == "package":
        rest = argv[1:]
        dest = None
        name = None
        positional: list[str] = []
        i = 0
        while i < len(rest):
            if rest[i] == "--dest" and i + 1 < len(rest):
                dest = rest[i + 1]
                i += 2
            elif rest[i] == "--name" and i + 1 < len(rest):
                name = rest[i + 1]
                i += 2
            else:
                positional.append(rest[i])
                i += 1
        repo = Path(positional[0]) if positional else Path(".")
        issues = drift_report(repo)
        if issues:
            sys.stderr.write("refusing to package — version drift:\n")
            for issue in issues:
                sys.stderr.write(f"  - {issue}\n")
            return 1
        out = build_package(repo, dest_dir=dest, archive_stem=name)
        sys.stdout.write(f"OK  built {out}  (v{current_version(repo)})\n")
        return 0

    if cmd == "snapshot":
        rest = argv[1:]
        snap_dest = None
        snap_name = None
        snap_positional: list[str] = []
        i = 0
        while i < len(rest):
            if rest[i] == "--dest" and i + 1 < len(rest):
                snap_dest = rest[i + 1]
                i += 2
            elif rest[i] == "--name" and i + 1 < len(rest):
                snap_name = rest[i + 1]
                i += 2
            else:
                snap_positional.append(rest[i])
                i += 1
        repo = Path(snap_positional[0]) if snap_positional else Path(".")
        issues = drift_report(repo)
        if issues:
            sys.stderr.write("refusing to snapshot — version drift:\n")
            for issue in issues:
                sys.stderr.write(f"  - {issue}\n")
            return 1
        result = build_version_snapshot(repo, dest_dir=snap_dest, archive_stem=snap_name)
        sys.stdout.write(f"OK  snapshot v{result['version']} → {result['snapshot_dir']}\n")
        sys.stdout.write(f"    zip: {result['zip']}\n")
        return 0

    if cmd == "check":
        repo = Path(argv[1]) if len(argv) > 1 else Path(".")
        canonical = current_version(repo)
        issues = drift_report(repo)
        if issues:
            sys.stderr.write(f"Canonical version (VERSION): {canonical}\n")
            for issue in issues:
                sys.stderr.write(f"  - {issue}\n")
            sys.stderr.write(f"FAIL ({len(issues)} drift{'s' if len(issues) != 1 else ''})\n")
            return 1
        sys.stdout.write(f"OK  all {len(VERSION_FILES)} version locations at v{canonical}\n")
        return 0

    if cmd == "scan":
        if len(argv) < 2:
            sys.stderr.write("usage: python -m renmark.release scan <repo-path>\n")
            return 2
        repo = Path(argv[1])
        found = check_drift(repo)
        for label, version in found.items():
            sys.stdout.write(f"  {version or '<missing>':>10}  {label}\n")
        return 0

    sys.stderr.write(f"unknown command: {cmd}\n")
    return 2


if __name__ == "__main__":
    sys.exit(main())

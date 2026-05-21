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

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

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
    VersionFile("plugin/.claude-plugin/plugin.json", _extract_plugin_json,
                description="Claude Code plugin manifest"),
    VersionFile(".claude-plugin/marketplace.json", _extract_marketplace,
                description="marketplace metadata.version"),
    VersionFile(".claude-plugin/marketplace.json", _extract_marketplace_plugin,
                description="marketplace plugins[0].version"),
    VersionFile("README.md", _extract_readme_header, description="README h1 header"),
]


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
        sys.stderr.write("usage: python -m renmark.release {check|current|scan PATH}\n")
        return 2

    cmd = argv[0]

    if cmd == "current":
        sys.stdout.write(current_version() + "\n")
        return 0

    if cmd == "check":
        repo = Path(argv[1]) if len(argv) > 1 else Path(".")
        canonical = current_version(repo)
        issues = drift_report(repo)
        if issues:
            sys.stderr.write(f"Canonical version (VERSION): {canonical}\n")
            for i in issues:
                sys.stderr.write(f"  - {i}\n")
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

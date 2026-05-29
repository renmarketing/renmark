"""Lifecycle hygiene — artifact GC + memory pruning + CLI.

Single source of truth for renmark's diagnostic hygiene operations. Walks the
canonical artifact subtrees under ``.renmark/``, archives stale + unreferenced
files into a date-bucketed archive, and prunes the memory logs via
``renmark.memory``. Never writes to ``lifecycle.json`` — hygiene is read-only
from the workflow-state perspective.

Stdlib only. Mypy-strict clean.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from renmark import lifecycle, memory, summary

# ── Constants ────────────────────────────────────────────────────────────────

_ARTIFACT_SUBDIRS: tuple[str, ...] = (
    "specs",
    "plans",
    "reviews",
    "research",
    "state/wave-summaries",
)
_ARTIFACT_SUFFIXES: tuple[str, ...] = (".md", ".yaml", ".yml", ".json")
_MEMORY_LOGS: tuple[str, ...] = ("learnings.md", "bugs.md", "features.md")


# ── Data ─────────────────────────────────────────────────────────────────────


@dataclass
class ScanReport:
    scanned: int = 0
    archived: int = 0
    kept: int = 0
    ghost_refs: int = 0
    archived_paths: list[Path] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


@dataclass
class PruneReport:
    deduped: int = 0
    aged_out: int = 0
    files_touched: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


# ── Helpers ──────────────────────────────────────────────────────────────────


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _default_archive_root(repo: Path) -> Path:
    bucket = _now_utc().strftime("%Y-%m")
    return repo / ".renmark" / "archive" / bucket


def _ensure_archive_under_renmark(repo: Path, archive_root: Path) -> Path:
    """Refuse archive roots that resolve outside ``repo/.renmark``."""
    renmark_root = (repo / ".renmark").resolve()
    resolved = archive_root.resolve()
    try:
        resolved.relative_to(renmark_root)
    except ValueError as e:
        raise ValueError(f"archive_root must live under {renmark_root}, got {resolved}") from e
    return resolved


def _parse_iso(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _is_older_than(dt: datetime, days: int) -> bool:
    cutoff = _now_utc().timestamp() - (days * 86400)
    return dt.timestamp() < cutoff


def _file_mtime_utc(path: Path) -> datetime:
    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)


def _normalize_ref(repo: Path, ref: str) -> Path | None:
    """Return a canonical absolute resolved Path for a lifecycle artifact ref,
    or None if the ref is malformed (empty/whitespace/unreadable)."""
    if not ref or not ref.strip():
        return None
    try:
        p = Path(ref)
        return p.resolve() if p.is_absolute() else (repo / p).resolve()
    except (OSError, RuntimeError):
        return None


def _referenced_paths(repo: Path) -> set[Path]:
    state = lifecycle.read_lifecycle(repo)
    if state is None:
        return set()
    refs: set[Path] = set()
    for value in state.artifacts.values():
        norm = _normalize_ref(repo, value)
        if norm is not None:
            refs.add(norm)
    return refs


def _ghost_count(repo: Path) -> int:
    state = lifecycle.read_lifecycle(repo)
    if state is None:
        return 0
    n = 0
    for value in state.artifacts.values():
        candidate = _normalize_ref(repo, value)
        if candidate is None:
            continue
        if not candidate.exists():
            n += 1
    return n


def _unique_destination(dest: Path) -> Path:
    if not dest.exists():
        return dest
    i = 1
    while True:
        candidate = dest.with_name(dest.name + f".{i}")
        if not candidate.exists():
            return candidate
        i += 1


def _archive_file(repo: Path, src: Path, archive_root: Path) -> Path:
    """Move ``src`` under ``archive_root`` preserving repo-relative path."""
    rel = src.resolve().relative_to(repo.resolve())
    dest = archive_root / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    final = _unique_destination(dest)
    shutil.move(str(src), str(final))
    return final


def _is_stale_for_gc(path: Path, ttl_days: int) -> bool:
    """Combine summary.is_stale + created_at TTL + mtime fallback."""
    if summary.is_stale(path):
        return True
    meta = summary.read_metadata(path)
    created_at = meta.get("created_at")
    created_dt = _parse_iso(created_at)
    if created_dt is not None:
        return _is_older_than(created_dt, ttl_days)
    # No created_at — fall back to mtime.
    try:
        return _is_older_than(_file_mtime_utc(path), ttl_days)
    except OSError:
        return False


# ── Public API ───────────────────────────────────────────────────────────────


def scan_artifacts(
    repo: Path,
    *,
    ttl_days: int = 90,
    dry_run: bool = True,
    archive_root: Path | None = None,
) -> ScanReport:
    """Walk artifact subtrees; archive stale + unreferenced files."""
    repo = Path(repo)
    if archive_root is None:
        archive_root = _default_archive_root(repo)
    archive_root = _ensure_archive_under_renmark(repo, archive_root)

    report = ScanReport()
    referenced = _referenced_paths(repo)
    archive_root_str = str(archive_root.resolve())

    for sub in _ARTIFACT_SUBDIRS:
        root = repo / ".renmark" / sub
        if not root.exists() or not root.is_dir():
            continue
        for path in root.rglob("*"):
            try:
                if not path.is_file():
                    continue
                if path.suffix.lower() not in _ARTIFACT_SUFFIXES:
                    continue
                # Skip anything already inside the archive tree.
                if str(path.resolve()).startswith(archive_root_str):
                    continue
                report.scanned += 1

                resolved = path.resolve()
                is_referenced = resolved in referenced
                stale = _is_stale_for_gc(path, ttl_days)

                if stale and not is_referenced:
                    if dry_run:
                        report.archived_paths.append(path)
                    else:
                        moved = _archive_file(repo, path, archive_root)
                        report.archived += 1
                        report.archived_paths.append(moved)
                else:
                    report.kept += 1
            except OSError as e:
                report.errors.append(f"{path}: {e}")

    try:
        report.ghost_refs = _ghost_count(repo)
    except OSError as e:
        report.errors.append(f"ghost-scan: {e}")

    return report


def prune_memory(
    repo: Path,
    *,
    days: int = 180,
    dry_run: bool = True,
    archive_root: Path | None = None,
) -> PruneReport:
    """Dedupe + age-out each allowed memory log."""
    repo = Path(repo)
    if archive_root is None:
        archive_root = _default_archive_root(repo)
    archive_root = _ensure_archive_under_renmark(repo, archive_root)

    report = PruneReport()
    for name in _MEMORY_LOGS:
        try:
            report.deduped += memory.dedupe_memory_log(repo, name, dry_run=dry_run)
            report.aged_out += memory.age_out_memory_log(repo, name, days, archive_root, dry_run=dry_run)
            report.files_touched.append(name)
        except OSError as e:
            report.errors.append(f"{name}: {e}")
    return report


# ── CLI ──────────────────────────────────────────────────────────────────────


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="renmark.hygiene",
        description=(
            "Lifecycle hygiene — archive stale artifacts and prune memory logs. "
            "Defaults to dry-run; pass --apply to make changes."
        ),
    )
    parser.add_argument("subcommand", choices=("scan", "prune", "all"))
    parser.add_argument("--repo", default=".", help="Project root (default: .)")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Make changes on disk (default is dry-run).",
    )
    parser.add_argument("--ttl-days", type=int, default=90)
    parser.add_argument("--memory-days", type=int, default=180)
    parser.add_argument(
        "--include-memory",
        action="store_true",
        help="When subcommand=scan, also run prune afterwards.",
    )
    return parser


def _write_error_log(repo: Path, errors: list[str]) -> Path:
    log_dir = repo / ".renmark" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    stamp = _now_utc().strftime("%Y-%m-%d")
    path = log_dir / f"hygiene-{stamp}.log"
    with path.open("a", encoding="utf-8") as f:
        for line in errors:
            f.write(line.rstrip("\n") + "\n")
    return path


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        # argparse exits 2 on argument error — preserve that.
        return int(e.code) if isinstance(e.code, int) else 2

    repo = Path(args.repo).resolve()
    dry_run = not args.apply
    mode_label = "apply" if args.apply else "dry-run"

    # Step 0 — skill preamble (cross-domain hint).
    try:
        hint = lifecycle.skill_preamble(repo, "hygiene")
    except Exception:
        hint = None
    if hint:
        print(hint)

    sub = args.subcommand
    run_scan = sub in ("scan", "all")
    run_prune = sub in ("prune", "all") or (sub == "scan" and args.include_memory)

    scan_report: ScanReport | None = None
    prune_report: PruneReport | None = None

    if run_scan:
        scan_report = scan_artifacts(repo, ttl_days=args.ttl_days, dry_run=dry_run)
    if run_prune:
        prune_report = prune_memory(repo, days=args.memory_days, dry_run=dry_run)

    if scan_report is not None:
        archived_n = scan_report.archived if args.apply else len(scan_report.archived_paths)
        print(
            f"HYGIENE  mode={mode_label}  scanned={scan_report.scanned}  "
            f"archived={archived_n}  kept={scan_report.kept}  "
            f"ghost_refs={scan_report.ghost_refs}"
        )
    else:
        # prune-only invocation still wants a header line.
        print(f"HYGIENE  mode={mode_label}  scanned=0  archived=0  kept=0  ghost_refs=0")

    if prune_report is not None:
        files_csv = ",".join(n.removesuffix(".md") for n in prune_report.files_touched)
        print(f"MEMORY   deduped={prune_report.deduped}  aged_out={prune_report.aged_out}  files={files_csv}")

    # Error handling — only persist when --apply was used.
    all_errors: list[str] = []
    if scan_report is not None:
        all_errors.extend(scan_report.errors)
    if prune_report is not None:
        all_errors.extend(prune_report.errors)

    if all_errors and args.apply:
        log_path = _write_error_log(repo, all_errors)
        stamp = _now_utc().strftime("%Y-%m-%d")
        rel = log_path.relative_to(repo) if log_path.is_relative_to(repo) else log_path
        print(f"ERRORS    {len(all_errors)} — see {rel.as_posix()}")
        # Keep rel format aligned with spec example.
        del stamp  # unused — formatted into filename already

    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())

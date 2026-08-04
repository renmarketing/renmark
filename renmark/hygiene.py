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
import json
import re
import shutil
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from renmark import lifecycle, memory, schemas, summary

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


@dataclass(frozen=True)
class ArtifactTypeSpec:
    """One row of the ``.renmark/`` artifact-type registry.

    ``path_glob`` is relative to ``repo/.renmark`` and may use a single
    ``{a,b,c}`` brace-expansion group (Python's ``glob`` does not support
    brace expansion natively — see ``_expand_braces``).
    """

    name: str
    path_glob: str
    art_class: str  # active-context | canonical-evidence | archived-history | ephemeral
    owner: str
    regenerable: bool
    budget_count: int | None
    budget_bytes: int | None
    budget_age_days: int | None
    warn_pct: float = 0.8


# Copied verbatim (paths/class/budget/owner/regenerable) from
# .renmark/rethink/artifact-lifecycle/implementation-proposal.md §1.
ARTIFACT_REGISTRY: tuple[ArtifactTypeSpec, ...] = (
    ArtifactTypeSpec("audits", "audits/**", "ephemeral", "audit", True, 60, 1_500_000, 60),
    ArtifactTypeSpec("plans", "plans/**", "canonical-evidence", "plan", False, 150, 3_000_000, None),
    ArtifactTypeSpec("reviews", "reviews/**", "canonical-evidence", "review", False, 250, 1_500_000, None),
    ArtifactTypeSpec(
        "state-live",
        "state/{lifecycle,program,delivery,mode,agency,tasks,compact_checkpoint,last-skill}.json",
        "active-context",
        "lifecycle",
        False,
        None,
        51_200,
        None,
    ),
    ArtifactTypeSpec(
        "state-scratch",
        "state/{escalations,_wave-prompts,handoffs,adhoc-specs}/**",
        "ephemeral",
        "dispatch",
        True,
        200,
        1_000_000,
        14,
    ),
    ArtifactTypeSpec("memory", "memory/*.md", "active-context", "memory", False, 16, None, None),
    ArtifactTypeSpec("ledger", "ledger/events.jsonl", "canonical-evidence", "ledger", False, None, 25_000_000, None),
    ArtifactTypeSpec("reports", "reports/features/*/*", "archived-history", "reports", True, 100, 500_000, None),
    ArtifactTypeSpec("rethink", "rethink/*/*.md", "canonical-evidence", "rethink", False, None, 500_000, None),
    ArtifactTypeSpec("roadmap", "roadmap/*.md", "active-context", "roadmap", False, 2, 307_200, None),
    ArtifactTypeSpec("specs", "specs/*.md", "canonical-evidence", "brainstorm", False, 100, 500_000, None),
    ArtifactTypeSpec("debug", "debug/*/*", "ephemeral", "debug", True, 40, 1_000_000, 90),
    # budget_age_days=7: short enough that a stale unpacked version tree is
    # reclaimed promptly (it's a pure build byproduct, budget_count=1 means
    # only the single most-recent version's tree should ever be kept), but
    # long enough that the CURRENT (just-unpacked) version's tree is never
    # old enough to qualify on its own — the safe-deletion predicate already
    # protects the single newest-mtime file unconditionally (see
    # `_apply_hygiene`'s ephemeral+regenerable pass), and 7 days is a wide
    # margin against any mtime skew across files within the same unpack.
    ArtifactTypeSpec("version-unpacked", "version/v*/**", "ephemeral", "release", True, 1, None, 7),
    ArtifactTypeSpec("version-zip", "version/*.zip", "canonical-evidence", "release", False, None, None, None),
)

# Top-level names under .renmark/ that are never registry-governed content.
_REGISTRY_SKIP_TOP_DIRS: frozenset[str] = frozenset({"archive", "logs"})
_REGISTRY_SKIP_TOP_FILES: frozenset[str] = frozenset({"config.json", "README.md"})


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


@dataclass
class BudgetEntry:
    name: str
    count: int
    total_bytes: int
    oldest_days: int | None
    budget_count: int | None
    budget_bytes: int | None
    status: str  # ok | warn | block


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


def _expand_braces(pattern: str) -> list[str]:
    """Expand a single ``{a,b,c}`` group in a glob pattern.

    Python's ``pathlib.Path.glob`` does not support brace expansion, so
    registry entries that use it (``state-live``, ``state-scratch``) must be
    pre-expanded into one concrete glob per option.
    """
    m = re.search(r"\{([^{}]*)\}", pattern)
    if not m:
        return [pattern]
    options = m.group(1).split(",")
    prefix, suffix = pattern[: m.start()], pattern[m.end() :]
    return [f"{prefix}{opt}{suffix}" for opt in options]


def _iter_registry_files(repo: Path, spec: ArtifactTypeSpec) -> list[Path]:
    """Resolve every live file matching ``spec.path_glob`` under ``.renmark/``."""
    renmark_root = repo / ".renmark"
    if not renmark_root.exists():
        return []
    files: set[Path] = set()
    for sub_glob in _expand_braces(spec.path_glob):
        # Path.glob("x/**") only matches "x/" itself (depth 0) — it does NOT
        # descend into files, unlike shell globstar. "x/**/*" is required to
        # actually enumerate files at any depth (including immediate
        # children). Normalize trailing "**" so registry authors can write
        # the natural "dir/**" form.
        patterns = [sub_glob]
        if sub_glob.endswith("/**"):
            patterns.append(sub_glob + "/*")
        for pattern in patterns:
            for path in renmark_root.glob(pattern):
                if path.is_file():
                    files.add(path.resolve())
    return sorted(files)


def _registry_stats(files: list[Path]) -> tuple[int, int, int | None]:
    """Return (count, total_bytes, oldest_age_days) for a set of files."""
    count = len(files)
    total_bytes = 0
    oldest_days: int | None = None
    now = _now_utc().timestamp()
    for path in files:
        try:
            st = path.stat()
        except OSError:
            continue
        total_bytes += st.st_size
        age_days = int((now - st.st_mtime) / 86400)
        if oldest_days is None or age_days > oldest_days:
            oldest_days = age_days
    return count, total_bytes, oldest_days


def _budget_status(spec: ArtifactTypeSpec, count: int, total_bytes: int, oldest_days: int | None) -> str:
    """ok / warn / block against whichever budget dimensions are bounded."""
    ratios: list[float] = []
    if spec.budget_count is not None and spec.budget_count > 0:
        ratios.append(count / spec.budget_count)
    if spec.budget_bytes is not None and spec.budget_bytes > 0:
        ratios.append(total_bytes / spec.budget_bytes)
    if spec.budget_age_days is not None and spec.budget_age_days > 0 and oldest_days is not None:
        ratios.append(oldest_days / spec.budget_age_days)
    if not ratios:
        return "ok"
    worst = max(ratios)
    if worst >= 1.0:
        return "block"
    if worst >= spec.warn_pct:
        return "warn"
    return "ok"


def compute_budget_report(repo: Path) -> list[BudgetEntry]:
    """Live count/bytes/oldest-age + status for every ``ARTIFACT_REGISTRY`` type."""
    repo = Path(repo)
    entries: list[BudgetEntry] = []
    for spec in ARTIFACT_REGISTRY:
        files = _iter_registry_files(repo, spec)
        count, total_bytes, oldest_days = _registry_stats(files)
        status = _budget_status(spec, count, total_bytes, oldest_days)
        entries.append(
            BudgetEntry(
                name=spec.name,
                count=count,
                total_bytes=total_bytes,
                oldest_days=oldest_days,
                budget_count=spec.budget_count,
                budget_bytes=spec.budget_bytes,
                status=status,
            )
        )
    return entries


def _read_meta_if_present(path: Path) -> dict[str, Any]:
    """Parse frontmatter (``.md``) or a top-level metadata object (``.json``).

    Returns ``{}`` when the file carries no recognizable artifact metadata —
    callers should skip validation in that case rather than flag a file that
    was never meant to carry a provenance block.
    """
    suffix = path.suffix.lower()
    if suffix == ".md":
        return summary.read_metadata(path)
    if suffix == ".json":
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        if isinstance(data, dict) and "artifact_type" in data:
            return data
        return {}
    return {}


def _add_dependency_refs_from_meta(repo: Path, meta: dict[str, Any], refs: set[Path]) -> None:
    """Normalize and add each ``dependency_refs`` entry from a parsed
    artifact-metadata dict into ``refs`` — shared by both the ``.md``
    frontmatter path and the whole-document ``.json`` path so they converge
    on identical string-to-Path resolution."""
    deps = meta.get("dependency_refs")
    if not isinstance(deps, list):
        return
    for dep in deps:
        if isinstance(dep, str):
            norm = _normalize_ref(repo, dep)
            if norm is not None:
                refs.add(norm)


def _all_dependency_refs(repo: Path) -> set[Path]:
    """Union of lifecycle.json artifact refs and ``dependency_refs`` declared
    in either ``.md`` frontmatter or whole-document ``.json`` metadata across
    ``.renmark/`` — best-effort inbound-reference set for the ephemeral
    safe-deletion predicate. Extends ``_referenced_paths`` (which only covers
    ``lifecycle.json``) with a repo-wide frontmatter + JSON-metadata scan."""
    refs = set(_referenced_paths(repo))
    renmark_root = repo / ".renmark"
    if not renmark_root.exists():
        return refs
    for path in renmark_root.rglob("*.md"):
        if not path.is_file():
            continue
        try:
            meta = summary.read_metadata(path)
        except OSError:
            continue
        _add_dependency_refs_from_meta(repo, meta, refs)
    for path in renmark_root.rglob("*.json"):
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(data, dict):
            continue
        _add_dependency_refs_from_meta(repo, data, refs)
    return refs


def validate_registry_compliance(repo: Path) -> list[str]:
    """Repo-wide placement/metadata/budget/ownership check against
    ``ARTIFACT_REGISTRY``. Distinct from ``schemas.validate_artifact_metadata``
    (single-document contract) — this walks the whole ``.renmark/`` tree."""
    repo = Path(repo)
    renmark_root = repo / ".renmark"
    issues: list[str] = []
    if not renmark_root.exists():
        return ["no .renmark directory found"]

    registry_files: set[Path] = set()
    for spec in ARTIFACT_REGISTRY:
        registry_files |= set(_iter_registry_files(repo, spec))

    # (a) placement + (b) metadata.
    for path in sorted(renmark_root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.resolve().relative_to(renmark_root.resolve())
        parts = rel.parts
        if parts and parts[0] in _REGISTRY_SKIP_TOP_DIRS:
            continue
        if "archive" in parts:
            continue
        if len(parts) == 1 and parts[0] in _REGISTRY_SKIP_TOP_FILES:
            continue

        if path.resolve() not in registry_files:
            issues.append(f"no registry entry: {rel.as_posix()}")

        if path.suffix.lower() in (".md", ".json"):
            meta = _read_meta_if_present(path)
            if meta:
                issues.extend(schemas.validate_artifact_metadata(meta))

    # (c) budget.
    for entry in compute_budget_report(repo):
        if entry.status == "block":
            issues.append(f"BLOCK {entry.name}: count={entry.count} bytes={entry.total_bytes}")
        elif entry.status == "warn":
            issues.append(f"WARN {entry.name}: count={entry.count} bytes={entry.total_bytes}")

    # (d) canonical ownership — project-map.md is the sole structural home;
    # inventory/survey files must cite it.
    project_map = renmark_root / "memory" / "project-map.md"
    if not project_map.exists():
        issues.append("missing canonical file: .renmark/memory/project-map.md")
    else:
        citation_files: list[Path] = []
        citation_files.extend((renmark_root / "audits").glob("inventory-*.md"))
        citation_files.extend((renmark_root / "rethink").glob("*/survey.md"))
        for cand in citation_files:
            if not cand.is_file():
                continue
            meta = summary.read_metadata(cand)
            refs = meta.get("dependency_refs")
            refs = refs if isinstance(refs, list) else []
            has_pointer = any(isinstance(r, str) and r.endswith("memory/project-map.md") for r in refs)
            if not has_pointer:
                rel = cand.resolve().relative_to(repo.resolve())
                issues.append(f"no project-map.md pointer: {rel.as_posix()}")

    return issues


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

    # Type-aware ephemeral+regenerable safe-deletion (additive, registry-driven).
    # A file is only ever a delete (not archive) candidate on --apply when ALL
    # of: (i) older than its type's budget_age_days, (ii) zero inbound
    # dependency_refs, (iii) not the single most-recent file of its type.
    # canonical-evidence / active-context types are never touched here.
    ephemeral_specs = [
        s for s in ARTIFACT_REGISTRY if s.art_class == "ephemeral" and s.regenerable and s.budget_age_days is not None
    ]
    if ephemeral_specs:
        dep_refs = _all_dependency_refs(repo)
        for spec in ephemeral_specs:
            age_days = spec.budget_age_days
            if age_days is None:
                continue
            files = [f for f in _iter_registry_files(repo, spec) if not str(f).startswith(archive_root_str)]
            if not files:
                continue
            try:
                newest = max(files, key=lambda p: p.stat().st_mtime)
            except OSError:
                continue
            for candidate in files:
                if candidate == newest:
                    continue  # (iii) never delete the sole most-recent file
                try:
                    if not _is_older_than(_file_mtime_utc(candidate), age_days):
                        continue  # (i) not old enough
                except OSError:
                    continue
                if candidate in dep_refs:
                    continue  # (ii) has an inbound reference — keep

                report.scanned += 1
                if dry_run:
                    report.archived_paths.append(candidate)
                else:
                    try:
                        candidate.unlink()
                        report.archived += 1
                        report.archived_paths.append(candidate)
                    except OSError as e:
                        report.errors.append(f"{candidate}: {e}")

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
    parser.add_argument("subcommand", choices=("scan", "prune", "all", "budget", "validate"))
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

    # budget/validate are read-only, registry-driven reports — handled and
    # returned before the scan/prune/all dispatch below.
    if sub == "budget":
        for entry in compute_budget_report(repo):
            cap_count = entry.budget_count if entry.budget_count is not None else "-"
            cap_bytes = entry.budget_bytes if entry.budget_bytes is not None else "-"
            print(
                f"BUDGET  {entry.name}  count={entry.count}/{cap_count}  "
                f"bytes={entry.total_bytes}/{cap_bytes}  status={entry.status}"
            )
        return 0

    if sub == "validate":
        issues = validate_registry_compliance(repo)
        print(f"VALIDATE  issues={len(issues)}")
        for issue in issues:
            print(issue)
        return 0

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

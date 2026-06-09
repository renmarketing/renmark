"""Bounded local report builders (REQ-15).

Assembles per-feature and per-run report artifacts under
``.renmark/reports/{tasks,loops,backlog,features,releases}/``. Reports are the
durable, human-readable record of what a feature / loop / release actually did —
metrics in JSON, a bounded narrative in Markdown.

Conventions mirror ``renmark.lifecycle`` and ``renmark.loop``:
- repo paths via ``Path(repo) / ".renmark" / ...``
- atomic writes: write a sibling ``.tmp`` then ``os.replace`` (crash-consistent)
- file ops degrade gracefully (non-raising) where the codebase does

This module never calls ``datetime.now()``. Callers pass ``now`` (use
``renmark.state.now_iso()`` at the call site) so reports stay deterministic and
testable.
"""

from __future__ import annotations

import contextlib
import json
import os
from pathlib import Path

# Generic run-report kinds (per-feature reports use write_feature_report).
RUN_REPORT_KINDS: frozenset[str] = frozenset({"tasks", "loops", "backlog", "releases"})

# Ordered metrics keys assembled by build_feature_report (REQ-15).
FEATURE_REPORT_KEYS: tuple[str, ...] = (
    "feature",
    "branch",
    "sha",
    "version_path",
    "release_link",
    "verification",
    "codereview",
    "files_changed",
    "token_cost",
    "loop_iterations",
    "stop_reason",
    "branch_disposition",
    "shipped",
    "deferred",
    "next_backlog",
    "task_id",
    "backlog_item_id",
    "loop_id",
    "created_at",
)


# ── Paths ──────────────────────────────────────────────────────────────────


def reports_dir(repo: Path | str) -> Path:
    """Return ``.renmark/reports/`` for ``repo`` (no mkdir — write helpers do that)."""
    return Path(repo) / ".renmark" / "reports"


def feature_reports_dir(repo: Path | str, slug: str) -> Path:
    """Return ``.renmark/reports/features/<slug>/`` (no mkdir)."""
    return reports_dir(repo) / "features" / slug


def _version_dir(repo: Path | str) -> Path:
    return Path(repo) / ".renmark" / "version"


def _resolve_release_link(repo: Path | str, version_path: str) -> str:
    """Best-effort link into ``.renmark/version/<version>/``.

    If ``version_path`` is given, return it. Otherwise, if a single version dir
    exists under ``.renmark/version/``, link it. Else return "".
    """
    if version_path:
        return version_path
    vdir = _version_dir(repo)
    try:
        if not vdir.is_dir():
            return ""
        subdirs = sorted(p for p in vdir.iterdir() if p.is_dir())
    except OSError:
        return ""
    if len(subdirs) == 1:
        return str(subdirs[0])
    return ""


# ── Builders ───────────────────────────────────────────────────────────────


def build_feature_report(
    repo: Path | str,
    *,
    feature: str,
    branch: str = "",
    sha: str = "",
    version_path: str = "",
    verification: str = "",
    codereview: str = "",
    files_changed: int = 0,
    token_cost: dict[str, int] | None = None,
    loop_iterations: int = 0,
    stop_reason: str = "",
    branch_disposition: str = "",
    shipped: list[str] | None = None,
    deferred: list[str] | None = None,
    next_backlog: list[str] | None = None,
    task_id: str = "",
    backlog_item_id: str = "",
    loop_id: str = "",
    now: str = "",
) -> dict[str, object]:
    """Assemble a bounded metrics dict carrying all REQ-15 feature-report fields.

    None lists are normalized to ``[]``; ``token_cost`` None becomes ``{}``.
    ``release_link`` is resolved best-effort from ``version_path`` or a single
    existing version dir under ``.renmark/version/``.
    """
    return {
        "feature": feature,
        "branch": branch,
        "sha": sha,
        "version_path": version_path,
        "release_link": _resolve_release_link(repo, version_path),
        "verification": verification,
        "codereview": codereview,
        "files_changed": files_changed,
        "token_cost": token_cost if token_cost is not None else {},
        "loop_iterations": loop_iterations,
        "stop_reason": stop_reason,
        "branch_disposition": branch_disposition,
        "shipped": list(shipped) if shipped is not None else [],
        "deferred": list(deferred) if deferred is not None else [],
        "next_backlog": list(next_backlog) if next_backlog is not None else [],
        "task_id": task_id,
        "backlog_item_id": backlog_item_id,
        "loop_id": loop_id,
        "created_at": now,
    }


def _bullets(items: object) -> list[str]:
    if isinstance(items, list) and items:
        return [f"- {item}" for item in items]
    return ["- (none)"]


def render_report_md(report: dict[str, object]) -> str:
    """Render a bounded, human-readable ``report.md`` from a metrics dict.

    Bounded by design: identity / results / loop / disposition / shipped /
    deferred / next-backlog sections only — NO code, NO diffs.
    """
    feature = report.get("feature", "") or "(unnamed feature)"
    lines: list[str] = [f"# Feature report — {feature}", ""]

    created = report.get("created_at", "")
    if created:
        lines.append(f"_Generated: {created}_")
        lines.append("")

    lines.append("## Identity")
    lines.append(f"- branch: {report.get('branch', '') or '(none)'}")
    lines.append(f"- sha: {report.get('sha', '') or '(none)'}")
    version = report.get("version_path", "") or report.get("release_link", "")
    lines.append(f"- version: {version or '(none)'}")
    lines.append("")

    lines.append("## Results")
    lines.append(f"- verification: {report.get('verification', '') or '(none)'}")
    lines.append(f"- codereview: {report.get('codereview', '') or '(none)'}")
    lines.append(f"- files_changed: {report.get('files_changed', 0)}")
    lines.append("")

    lines.append("## Loop")
    lines.append(f"- iterations: {report.get('loop_iterations', 0)}")
    lines.append(f"- stop_reason: {report.get('stop_reason', '') or '(none)'}")
    lines.append("")

    lines.append("## Disposition")
    lines.append(f"- {report.get('branch_disposition', '') or '(none)'}")
    lines.append("")

    lines.append("## Shipped")
    lines.extend(_bullets(report.get("shipped")))
    lines.append("")

    lines.append("## Deferred")
    lines.extend(_bullets(report.get("deferred")))
    lines.append("")

    lines.append("## Next backlog")
    lines.extend(_bullets(report.get("next_backlog")))
    lines.append("")

    return "\n".join(lines)


# ── Atomic writes ────────────────────────────────────────────────────────────


def _atomic_write(path: Path, text: str) -> Path | None:
    """Write ``text`` to ``path`` via a ``.tmp`` sibling + ``os.replace``.

    Crash-consistent (no fsync). Returns the path, or ``None`` on IO failure —
    never raises into the caller.
    """
    tmp = path.with_suffix(path.suffix + ".tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_text(text, encoding="utf-8")
        os.replace(tmp, path)
    except OSError:
        try:
            if tmp.exists():
                tmp.unlink()
        except OSError:
            pass
        return None
    return path


def write_feature_report(
    repo: Path | str, slug: str, report: dict[str, object]
) -> tuple[Path, Path]:
    """Atomically write ``report.md`` + ``metrics.json`` under the feature dir.

    Returns ``(md_path, json_path)`` — the intended paths even if a write
    degraded to ``None`` internally (caller can re-check existence).
    """
    out_dir = feature_reports_dir(repo, slug)
    with contextlib.suppress(OSError):
        out_dir.mkdir(parents=True, exist_ok=True)
    md_path = out_dir / "report.md"
    json_path = out_dir / "metrics.json"
    _atomic_write(md_path, render_report_md(report))
    _atomic_write(json_path, json.dumps(report, indent=2))
    return md_path, json_path


def write_run_report(
    repo: Path | str, kind: str, run_id: str, report: dict[str, object]
) -> Path:
    """Atomically write a generic run report to ``.renmark/reports/<kind>/<run_id>.json``.

    ``kind`` should be one of ``RUN_REPORT_KINDS`` (tasks/loops/backlog/releases).
    Returns the intended path (mkdir is non-raising).
    """
    out_dir = reports_dir(repo) / kind
    with contextlib.suppress(OSError):
        out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{run_id}.json"
    _atomic_write(path, json.dumps(report, indent=2))
    return path

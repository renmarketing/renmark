"""Completed-task detection by scanning git commit subjects."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

# Recognizes: "[renmark] task N: ...", "[codex] task N: ...", "[nim] task N: ...",
# "[manual] task N: ...", and bare (unbracketed) variants of each.
# A recognized prefix is REQUIRED — bare "task N:" is rejected to avoid
# false-positives on unrelated commits.
_COMMIT_TASK_RE = re.compile(
    r"^\[?(?:renmark|codex|nim|manual)\]?\s+task\s+(\d+)\s*(?:\([^)]*\))?\s*:(?P<title>.*)$",
    re.IGNORECASE,
)


def normalize_task_title(title: str) -> str:
    """Canonical form used to compare a commit subject's title to a plan title.

    Case-insensitive and whitespace-normalized: titles are re-typed by planners
    and re-emitted by executors, so they are rarely byte-identical across runs.
    """
    return " ".join(title.split()).casefold()


def _scan_commit_subjects(repo_root: str | Path, since_ref: str | None) -> list[str]:
    cmd = ["git", "-C", str(repo_root), "log", "--pretty=%s"]
    if since_ref:
        cmd.append(f"{since_ref}..HEAD")
    try:
        out = subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=10).stdout
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        return []
    return out.splitlines()


def completed_task_indices(repo_root: str | Path, since_ref: str | None = None) -> set[int]:
    """Scan git log for commits matching '[renmark] task N:', '[codex] task N:', etc.

    Returns the set of completed task indices. Empty set if not a git repo or
    no matching commits.

    NOTE: an index alone is NOT sufficient to prove a task in the CURRENT plan
    was completed — task numbers are reused across plans.  Callers that resume
    execution must use :func:`completed_task_titles` and cross-check the title.
    """
    return set(completed_task_titles(repo_root, since_ref))


def completed_task_titles(
    repo_root: str | Path, since_ref: str | None = None
) -> dict[int, set[str]]:
    """Like :func:`completed_task_indices`, but also captures the commit titles.

    Returns ``{index: {normalized_title, ...}}``.  An index maps to a SET
    because the same index legitimately appears many times across a repo's
    history — once per plan that ever numbered a task ``N``.  Keeping every
    observed title lets a resume cross-check demand an index+title match
    instead of trusting a bare index number.

    Titles are normalized via :func:`normalize_task_title`.  Empty/missing
    titles are recorded as ``""`` so they can never accidentally match a real
    plan title.
    """
    completed: dict[int, set[str]] = {}
    for line in _scan_commit_subjects(repo_root, since_ref):
        m = _COMMIT_TASK_RE.match(line.strip())
        if m:
            idx = int(m.group(1))
            completed.setdefault(idx, set()).add(normalize_task_title(m.group("title") or ""))
    return completed

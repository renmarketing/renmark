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
    r"^\[?(?:renmark|codex|nim|manual)\]?\s+task\s+(\d+)\s*(?:\([^)]*\))?\s*:",
    re.IGNORECASE,
)


def completed_task_indices(repo_root: str | Path, since_ref: str | None = None) -> set[int]:
    """Scan git log for commits matching '[renmark] task N:', '[codex] task N:', etc.

    Returns the set of completed task indices. Empty set if not a git repo or
    no matching commits.
    """
    cmd = ["git", "-C", str(repo_root), "log", "--pretty=%s"]
    if since_ref:
        cmd.append(f"{since_ref}..HEAD")
    try:
        out = subprocess.run(
            cmd, check=True, capture_output=True, text=True, timeout=10
        ).stdout
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        return set()
    completed: set[int] = set()
    for line in out.splitlines():
        m = _COMMIT_TASK_RE.match(line.strip())
        if m:
            completed.add(int(m.group(1)))
    return completed

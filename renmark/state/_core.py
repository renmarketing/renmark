"""Foundational paths, time helpers, and the dir-rotation primitive.

Everything here is dependency-free within the package — other state submodules
import from `_core`, never the reverse.
"""
from __future__ import annotations

import datetime as dt
import secrets
from pathlib import Path


RENMARK_DIR_NAME = ".renmark"
STATE_SUBDIR = "state"
MEMORY_SUBDIR = "memory"
DEBUG_SUBDIR = "debug"
LOGS_SUBDIR = "logs"
USAGE_LEDGER = "usage.jsonl"
PAUSED_FILE = "PAUSED"
ESCALATIONS_DIR = "escalations"
ARCHIVE_SUBDIR = "archive"
PIPELINE_JSON = "pipeline.json"
WAVE_SUMMARIES_SUBDIR = "wave-summaries"
LAST_SKILL_FILE = "last-skill.json"

# Rotation caps — entries beyond these move to .renmark/state/archive/<stamp>/.
# Tuned for "one vibe coder, one project, many features." Bump for power users.
WAVE_SUMMARIES_KEEP = 50      # keep last N wave summaries hot
LOGS_KEEP = 50                # keep last N log files hot
ESCALATIONS_KEEP = 20         # escalations are rarer but bigger

# Back-compat alias for code that still references STATE_DIR_NAME.
# .renmark/state/ is the canonical runtime state directory in v0.1.0+.
STATE_DIR_NAME = f"{RENMARK_DIR_NAME}/{STATE_SUBDIR}"


def new_run_id() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d-%H%M%S") + "-" + secrets.token_hex(2)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def state_dir(repo_root: str | Path) -> Path:
    d = Path(repo_root) / STATE_DIR_NAME
    d.mkdir(parents=True, exist_ok=True)
    return d


def _archive_root(repo_root: str | Path) -> Path:
    d = state_dir(repo_root) / ARCHIVE_SUBDIR
    d.mkdir(parents=True, exist_ok=True)
    return d


def _find_repo_root(start: Path) -> Path | None:
    """Walk up from `start` until we see a `.renmark/` directory; return its
    parent. Returns None if no .renmark/ is found before filesystem root."""
    cur = start.resolve()
    while True:
        if cur.name == RENMARK_DIR_NAME:
            return cur.parent
        if cur.parent == cur:
            return None
        cur = cur.parent


def rotate_dir(
    target: Path,
    *,
    keep: int,
    subdir_in_archive: str,
    glob: str = "*",
) -> int:
    """Cap `target` at `keep` entries (files OR dirs), moving overflow into
    `.renmark/state/archive/<subdir_in_archive>/<timestamp>/`.

    Newest entries (by mtime) are kept hot. Returns the count moved.

    Best-effort: any OS error during move is swallowed — rotation must never
    break a running orchestrate. Caller decides whether to log the miss.

    Repo root is derived by walking up from `target` until a `.renmark/`
    directory is found, so both `.renmark/state/wave-summaries/` and
    `.renmark/logs/` work with the same helper.
    """
    if not target.exists() or keep <= 0:
        return 0
    entries = sorted(
        [p for p in target.glob(glob) if p.name != ARCHIVE_SUBDIR],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    overflow = entries[keep:]
    if not overflow:
        return 0

    repo_root = _find_repo_root(target)
    if repo_root is None:
        return 0  # outside a renmark project — silently skip

    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S")
    dest = _archive_root(repo_root) / subdir_in_archive / stamp
    dest.mkdir(parents=True, exist_ok=True)

    moved = 0
    for p in overflow:
        try:
            p.rename(dest / p.name)
            moved += 1
        except OSError:
            continue
    return moved

"""Per-invocation troubleshooting logs (.renmark/logs/).

Gitignored — transient runtime data, regenerable. One file per command run.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Any

from . import _core
from ._core import (
    LOGS_SUBDIR,
    RENMARK_DIR_NAME,
    new_run_id,
    now_iso,
    rotate_dir,
)


def logs_dir(repo_root: str | Path) -> Path:
    d = Path(repo_root) / RENMARK_DIR_NAME / LOGS_SUBDIR
    d.mkdir(parents=True, exist_ok=True)
    return d


def open_log(repo_root: str | Path, command: str, run_id: str | None = None) -> Path:
    """Open (create + return path) a log file for one command invocation.

    Filename is `<command>-<run_id>.log`. If run_id is omitted, a fresh one is
    generated. The file is created empty; callers append text as the run
    progresses. Returns the path so callers can decide buffered vs unbuffered.

    Rotates `.renmark/logs/` if it grows past LOGS_KEEP entries.
    """
    safe_cmd = "".join(c if c.isalnum() or c in "-_" else "_" for c in command)
    rid = run_id or new_run_id()
    d = logs_dir(repo_root)
    path = d / f"{safe_cmd}-{rid}.log"
    if not path.exists():
        path.write_text(
            f"# renmark log\ncommand: {command}\nrun_id: {rid}\nstarted: {now_iso()}\n\n",
            encoding="utf-8",
        )
    # Logs dir lives at .renmark/logs/ (not .renmark/state/) — archive goes
    # to .renmark/state/archive/ regardless, since that path is gitignored.
    rotate_dir(d, keep=_core.LOGS_KEEP, subdir_in_archive="logs", glob="*.log")
    return path


def append_log(log_path: Path, *messages: str) -> None:
    """Append one or more lines to a log file. Adds an ISO timestamp prefix."""
    ts = now_iso()
    with log_path.open("a", encoding="utf-8") as fh:
        for m in messages:
            fh.write(f"[{ts}] {m}\n")


def recent_logs(repo_root: str | Path, n: int = 10) -> list[dict[str, Any]]:
    """Return the n most-recent log entries with name, size, modified-time.

    Sorted newest first.
    """
    d = logs_dir(repo_root)
    items: list[dict[str, Any]] = []
    for f in d.glob("*.log"):
        try:
            st = f.stat()
        except OSError:
            # Log rotated/deleted mid-glob — skip rather than crash the listing.
            continue
        items.append(
            {
                "name": f.name,
                "path": str(f),
                "size": st.st_size,
                "mtime": dt.datetime.fromtimestamp(st.st_mtime, dt.timezone.utc).isoformat(timespec="seconds"),
                "_raw_mtime": st.st_mtime,
            }
        )
    # Sort by raw float so logs created within the same second still order
    # deterministically by actual write time.
    items.sort(key=lambda x: x["_raw_mtime"], reverse=True)
    for it in items:
        it.pop("_raw_mtime", None)
    return items[:n]

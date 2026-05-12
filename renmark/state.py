"""Persistent state for nim-execute: usage ledger, pause file, completed-task detection."""
from __future__ import annotations

import datetime as dt
import json
import os
import subprocess
import re
import secrets
from dataclasses import dataclass, asdict
from pathlib import Path


RENMARK_DIR_NAME = ".renmark"
STATE_SUBDIR = "state"
MEMORY_SUBDIR = "memory"
DEBUG_SUBDIR = "debug"
LOGS_SUBDIR = "logs"
USAGE_LEDGER = "usage.jsonl"
PAUSED_FILE = "PAUSED"
ESCALATIONS_DIR = "escalations"

# Back-compat alias for code that still references STATE_DIR_NAME.
# .renmark/state/ is the canonical runtime state directory in v0.1.0+.
STATE_DIR_NAME = f"{RENMARK_DIR_NAME}/{STATE_SUBDIR}"

# Recognizes any of: "[nim] task N: ...", "[manual] task N: ...",
# "nim task N: ...", "manual task N: ...", "nim task N (manual): ...",
# "manual task N (nim): ...". A bracketed or bare "nim"/"manual" prefix
# is REQUIRED — bare "task N:" is rejected so we don't false-positive on
# unrelated commits.
_COMMIT_TASK_RE = re.compile(
    r"^\[?(?:nim|manual)\]?\s+task\s+(\d+)\s*(?:\([^)]*\))?\s*:",
    re.IGNORECASE,
)


@dataclass
class UsageRecord:
    ts: str
    run_id: str
    task_id: int
    model: str
    prompt_tokens: int
    completion_tokens: int

    def as_jsonl(self) -> str:
        return json.dumps(asdict(self), separators=(",", ":"))


@dataclass
class PauseState:
    run_id: str
    plan_path: str
    last_task_index: int
    reason: str
    ts: str


def new_run_id() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d-%H%M%S") + "-" + secrets.token_hex(2)


def state_dir(repo_root: str | Path) -> Path:
    d = Path(repo_root) / STATE_DIR_NAME
    d.mkdir(parents=True, exist_ok=True)
    return d


def append_usage(repo_root: str | Path, rec: UsageRecord) -> None:
    path = state_dir(repo_root) / USAGE_LEDGER
    with path.open("a", encoding="utf-8") as fh:
        fh.write(rec.as_jsonl() + "\n")


def read_usage(repo_root: str | Path) -> list[dict]:
    path = state_dir(repo_root) / USAGE_LEDGER
    if not path.exists():
        return []
    out: list[dict] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        raw = raw.strip()
        if not raw:
            continue
        try:
            out.append(json.loads(raw))
        except json.JSONDecodeError:
            continue
    return out


def usage_today(repo_root: str | Path) -> int:
    today = dt.datetime.now(dt.timezone.utc).date().isoformat()
    total = 0
    for r in read_usage(repo_root):
        if r.get("ts", "").startswith(today):
            total += int(r.get("prompt_tokens", 0)) + int(r.get("completion_tokens", 0))
    return total


def usage_this_month(repo_root: str | Path) -> int:
    prefix = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m")
    total = 0
    for r in read_usage(repo_root):
        if r.get("ts", "").startswith(prefix):
            total += int(r.get("prompt_tokens", 0)) + int(r.get("completion_tokens", 0))
    return total


def write_pause(repo_root: str | Path, state: PauseState) -> None:
    path = state_dir(repo_root) / PAUSED_FILE
    path.write_text(json.dumps(asdict(state), indent=2), encoding="utf-8")


def read_pause(repo_root: str | Path) -> PauseState | None:
    path = state_dir(repo_root) / PAUSED_FILE
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return PauseState(**data)


def clear_pause(repo_root: str | Path) -> None:
    path = state_dir(repo_root) / PAUSED_FILE
    if path.exists():
        path.unlink()


def escalation_dir(repo_root: str | Path, task_index: int) -> Path:
    d = state_dir(repo_root) / ESCALATIONS_DIR / f"task-{task_index}"
    d.mkdir(parents=True, exist_ok=True)
    return d


# --- Logs (.renmark/logs/) -------------------------------------------------
# Per-invocation troubleshooting logs. One file per command run.
# Gitignored — transient runtime data, regenerable.

def logs_dir(repo_root: str | Path) -> Path:
    d = Path(repo_root) / RENMARK_DIR_NAME / LOGS_SUBDIR
    d.mkdir(parents=True, exist_ok=True)
    return d


def open_log(repo_root: str | Path, command: str, run_id: str | None = None) -> Path:
    """Open (create + return path) a log file for one command invocation.

    Filename is `<command>-<run_id>.log`. If run_id is omitted, a fresh one is
    generated. The file is created empty; callers append text as the run
    progresses. Returns the path so callers can decide buffered vs unbuffered.
    """
    safe_cmd = "".join(c if c.isalnum() or c in "-_" else "_" for c in command)
    rid = run_id or new_run_id()
    path = logs_dir(repo_root) / f"{safe_cmd}-{rid}.log"
    if not path.exists():
        path.write_text(
            f"# renmark log\ncommand: {command}\nrun_id: {rid}\nstarted: {now_iso()}\n\n",
            encoding="utf-8",
        )
    return path


def append_log(log_path: Path, *messages: str) -> None:
    """Append one or more lines to a log file. Adds an ISO timestamp prefix."""
    ts = now_iso()
    with log_path.open("a", encoding="utf-8") as fh:
        for m in messages:
            fh.write(f"[{ts}] {m}\n")


def recent_logs(repo_root: str | Path, n: int = 10) -> list[dict]:
    """Return the n most-recent log entries with name, size, modified-time.

    Sorted newest first.
    """
    d = logs_dir(repo_root)
    items: list[dict] = []
    for f in d.glob("*.log"):
        st = f.stat()
        items.append({
            "name": f.name,
            "path": str(f),
            "size": st.st_size,
            "mtime": dt.datetime.fromtimestamp(st.st_mtime, dt.timezone.utc).isoformat(timespec="seconds"),
            "_raw_mtime": st.st_mtime,
        })
    # Sort by raw float so logs created within the same second still order
    # deterministically by actual write time.
    items.sort(key=lambda x: x["_raw_mtime"], reverse=True)
    for it in items:
        it.pop("_raw_mtime", None)
    return items[:n]


def completed_task_indices(repo_root: str | Path, since_ref: str | None = None) -> set[int]:
    """Scan git log for commits matching '[nim] task N:' or '[manual] task N:'.

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


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")

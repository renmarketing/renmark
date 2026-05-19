"""Persistent state for renmark-execute: usage ledger, pause file, completed-task detection."""
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

# Recognizes: "[renmark] task N: ...", "[codex] task N: ...", "[nim] task N: ...",
# "[manual] task N: ...", and bare (unbracketed) variants of each.
# A recognized prefix is REQUIRED — bare "task N:" is rejected to avoid
# false-positives on unrelated commits.
_COMMIT_TASK_RE = re.compile(
    r"^\[?(?:renmark|codex|nim|manual)\]?\s+task\s+(\d+)\s*(?:\([^)]*\))?\s*:",
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


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


# --- Pipeline state (.renmark/state/pipeline.json) -------------------------
# G10 (workflow recovery) + G11 (task isolation) runtime state.
# Strict separation from lifecycle.json: pipeline.json carries RUNTIME fields
# only (wave indices, task indices, retry counts, subprocess state). Workflow
# fields (feature identity, stage names, approval state) live in lifecycle.json.

PIPELINE_JSON = "pipeline.json"
WAVE_SUMMARIES_SUBDIR = "wave-summaries"
LAST_SKILL_FILE = "last-skill.json"


@dataclass
class PipelineState:
    """Runtime state of an in-flight /renmark:orchestrate execution."""

    current_phase: str = "idle"                  # idle | orchestrate | paused
    current_plan: str = ""                       # path to plan file
    wave_index: int = 0
    wave_total: int = 0
    completed_tasks: list[int] = None           # type: ignore[assignment]
    failed_tasks: list[int] = None              # type: ignore[assignment]
    last_updated: str = ""

    def __post_init__(self) -> None:
        if self.completed_tasks is None:
            self.completed_tasks = []
        if self.failed_tasks is None:
            self.failed_tasks = []
        if not self.last_updated:
            self.last_updated = now_iso()


def _pipeline_path(repo_root: str | Path) -> Path:
    return state_dir(repo_root) / PIPELINE_JSON


def read_pipeline_state(repo_root: str | Path) -> PipelineState | None:
    """Return the current PipelineState, or None if none exists."""
    path = _pipeline_path(repo_root)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    known = {f for f in PipelineState.__dataclass_fields__}
    filtered = {k: v for k, v in data.items() if k in known}
    return PipelineState(**filtered)


def write_pipeline_state(
    repo_root: str | Path,
    *,
    current_phase: str | None = None,
    current_plan: str | None = None,
    wave_index: int | None = None,
    wave_total: int | None = None,
    add_completed_task: int | None = None,
    add_failed_task: int | None = None,
    clear_tasks: bool = False,
) -> PipelineState:
    """Update pipeline.json. Read-modify-write preserves unrelated fields."""
    current = read_pipeline_state(repo_root) or PipelineState()
    if current_phase is not None:
        current.current_phase = current_phase
    if current_plan is not None:
        current.current_plan = current_plan
    if wave_index is not None:
        current.wave_index = wave_index
    if wave_total is not None:
        current.wave_total = wave_total
    if clear_tasks:
        current.completed_tasks = []
        current.failed_tasks = []
    if add_completed_task is not None and add_completed_task not in current.completed_tasks:
        current.completed_tasks.append(add_completed_task)
    if add_failed_task is not None and add_failed_task not in current.failed_tasks:
        current.failed_tasks.append(add_failed_task)
    current.last_updated = now_iso()

    path = _pipeline_path(repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(current), indent=2), encoding="utf-8")
    return current


def clear_pipeline_state(repo_root: str | Path) -> None:
    path = _pipeline_path(repo_root)
    if path.exists():
        path.unlink()


def pipeline_is_resumable(repo_root: str | Path) -> bool:
    """G10: True if an interrupted orchestrate run has resumable state."""
    state = read_pipeline_state(repo_root)
    if state is None:
        return False
    return state.current_phase in {"orchestrate", "paused"} and state.wave_index < state.wave_total


# --- Wave summaries (.renmark/state/wave-summaries/) -----------------------
# G11: per-wave aggregated subagent outputs. Next wave reads dependency_notes
# from here, never from prior conversation.

def _wave_summaries_dir(repo_root: str | Path) -> Path:
    d = state_dir(repo_root) / WAVE_SUMMARIES_SUBDIR
    d.mkdir(parents=True, exist_ok=True)
    return d


def write_wave_summary(repo_root: str | Path, wave_index: int, task_outputs: list[dict]) -> Path:
    """Write the aggregated per-task summaries for one wave.

    task_outputs is a list of dicts conforming to SubagentOutput (status,
    artifact_path, summary_lines, dependency_notes, etc.). The orchestrator
    reads this file for the next wave's dependency context — NOT the conversation.
    """
    payload = {
        "wave_index": wave_index,
        "completed_at": now_iso(),
        "task_outputs": task_outputs,
    }
    path = _wave_summaries_dir(repo_root) / f"wave-{wave_index}.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def read_wave_summary(repo_root: str | Path, wave_index: int) -> dict | None:
    path = _wave_summaries_dir(repo_root) / f"wave-{wave_index}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def list_wave_summaries(repo_root: str | Path) -> list[int]:
    """Return sorted list of wave indices that have summaries on disk."""
    d = _wave_summaries_dir(repo_root)
    indices: list[int] = []
    for f in d.glob("wave-*.json"):
        try:
            indices.append(int(f.stem.split("-", 1)[1]))
        except (ValueError, IndexError):
            continue
    return sorted(indices)


# --- Skill invocation tracking (.renmark/state/last-skill.json) ------------
# G4: subject-change detection for context-contamination prompts.

def _last_skill_path(repo_root: str | Path) -> Path:
    return state_dir(repo_root) / LAST_SKILL_FILE


def record_skill_invocation(repo_root: str | Path, skill_name: str, domain: str) -> None:
    """Append-style record of which skill ran last and in which domain.

    Used by context_budget_check to detect cross-domain transitions and
    suggest /clear (per G4 / context-contamination-rule).
    """
    payload = {
        "skill": skill_name,
        "domain": domain,
        "timestamp": now_iso(),
    }
    path = _last_skill_path(repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def last_skill_invocation(repo_root: str | Path) -> dict | None:
    path = _last_skill_path(repo_root)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def context_budget_check(repo_root: str | Path, new_skill: str, new_domain: str) -> str | None:
    """Return 'clear' if cross-domain transition detected; else None.

    The %-utilization branch ('compact' recommendation) is NOT detectable from
    inside a skill — the harness doesn't expose context size. That side lives
    in the rule prose (context-budget-rule in CLAUDE.md) which the orchestrator
    self-monitors. This helper handles only the local-state half.
    """
    last = last_skill_invocation(repo_root)
    if last is None:
        return None
    prev_domain = last.get("domain")
    if prev_domain and prev_domain != new_domain:
        return "clear"
    return None

"""Pause file + escalation buckets (.renmark/state/PAUSED, escalations/)."""
from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path

from . import _core
from ._core import (
    ESCALATIONS_DIR,
    PAUSED_FILE,
    rotate_dir,
    state_dir,
)


@dataclass
class PauseState:
    run_id: str
    plan_path: str
    last_task_index: int
    reason: str
    ts: str


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
    parent = state_dir(repo_root) / ESCALATIONS_DIR
    parent.mkdir(parents=True, exist_ok=True)
    d = parent / f"task-{task_index}"
    d.mkdir(parents=True, exist_ok=True)
    # Rotate stale escalation buckets in the background; never errors the caller.
    rotate_dir(parent, keep=_core.ESCALATIONS_KEEP, subdir_in_archive="escalations", glob="task-*")
    return d

"""Pause file + escalation buckets (.renmark/state/PAUSED, escalations/)."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Any

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
    # Usage-limit pause fields (REQ-16). All keyword-defaulted so older PAUSED
    # files — which carry only the five fields above — still load via
    # PauseState(**data) without error.
    pause_kind: str = ""  # e.g. "usage_limit"
    provider: str = ""
    model: str = ""
    observed_usage: str = ""  # one-line summary
    provider_reset_at: str = ""
    resume_after: str = ""
    fallback_retry_minutes: int = 60
    feature: str = ""
    loop_id: str = ""
    iteration: int = 0
    max_iterations: int = 0


def usage_limit_pause(*, run_id: str, plan_path: str, last_task_index: int, ts: str,
                      provider: str = "", model: str = "", observed_usage: str = "",
                      provider_reset_at: str = "", resume_after: str = "",
                      fallback_retry_minutes: int = 60, feature: str = "",
                      loop_id: str = "", iteration: int = 0,
                      max_iterations: int = 0) -> PauseState:
    """Build a PauseState representing a usage-limit pause.

    Sets reason="usage limit reached" and pause_kind="usage_limit"; the caller
    supplies ts (no clock is read here).
    """
    return PauseState(
        run_id=run_id,
        plan_path=plan_path,
        last_task_index=last_task_index,
        reason="usage limit reached",
        ts=ts,
        pause_kind="usage_limit",
        provider=provider,
        model=model,
        observed_usage=observed_usage,
        provider_reset_at=provider_reset_at,
        resume_after=resume_after,
        fallback_retry_minutes=fallback_retry_minutes,
        feature=feature,
        loop_id=loop_id,
        iteration=iteration,
        max_iterations=max_iterations,
    )


def write_pause(repo_root: str | Path, state: PauseState) -> None:
    path = state_dir(repo_root) / PAUSED_FILE
    path.write_text(json.dumps(asdict(state), indent=2), encoding="utf-8")


def read_pause(repo_root: str | Path) -> PauseState | None:
    """Read the PAUSED file, or return None if it is absent/unreadable.

    Non-raising by contract (callers invoke this unguarded): a missing,
    corrupt, or schema-incompatible file degrades to None. Unknown extra keys
    are filtered out (forward-compat); missing-required keys yield None.
    """
    path = state_dir(repo_root) / PAUSED_FILE
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    known = {f.name for f in fields(PauseState)}
    filtered: dict[str, Any] = {k: v for k, v in data.items() if k in known}
    try:
        return PauseState(**filtered)
    except (TypeError, ValueError):
        return None


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

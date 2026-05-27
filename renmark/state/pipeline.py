"""Pipeline runtime state + per-wave summaries.

G10 (workflow recovery) + G11 (task isolation) runtime state. Strict
separation from lifecycle.json: pipeline.json carries RUNTIME fields only
(wave indices, task indices, retry counts, subprocess state). Workflow fields
(feature identity, stage names, approval state) live in lifecycle.json.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path

from . import _core
from ._core import (
    PIPELINE_JSON,
    WAVE_SUMMARIES_SUBDIR,
    now_iso,
    rotate_dir,
    state_dir,
)


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

    Rotates the wave-summaries dir if it grows past WAVE_SUMMARIES_KEEP entries.
    """
    payload = {
        "wave_index": wave_index,
        "completed_at": now_iso(),
        "task_outputs": task_outputs,
    }
    d = _wave_summaries_dir(repo_root)
    path = d / f"wave-{wave_index}.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    # Read cap via _core at call-time so tests can monkeypatch the canonical source.
    rotate_dir(d, keep=_core.WAVE_SUMMARIES_KEEP, subdir_in_archive="wave-summaries")
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

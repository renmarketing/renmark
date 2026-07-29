"""Pipeline runtime state + per-wave summaries.

G10 (workflow recovery) + G11 (task isolation) runtime state. Strict
separation from lifecycle.json: pipeline.json carries RUNTIME fields only
(wave indices, task indices, retry counts, subprocess state). Workflow fields
(feature identity, stage names, approval state) live in lifecycle.json.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, cast

from . import _core
from ._core import (
    PIPELINE_JSON,
    WAVE_SUMMARIES_SUBDIR,
    now_iso,
    rotate_dir,
    state_dir,
)

DELIVERY_RUNTIME_TEXT_LIMIT = 96
DELIVERY_RUNTIME_TASK_SAMPLE_LIMIT = 5


@dataclass
class PipelineState:
    """Runtime state of an in-flight /renmark:orchestrate execution."""

    current_phase: str = "idle"  # idle | orchestrate | paused
    current_plan: str = ""  # path to plan file
    wave_index: int = 0
    wave_total: int = 0
    completed_tasks: list[int] = field(default_factory=list)
    failed_tasks: list[int] = field(default_factory=list)
    last_updated: str = ""

    def __post_init__(self) -> None:
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
    if not isinstance(data, dict):
        return None
    known = {f for f in PipelineState.__dataclass_fields__}
    filtered = {k: v for k, v in data.items() if k in known}
    # Backward compat: legacy pipeline.json (pre-v0.5.4) may have null for
    # these list fields; coerce so the constructor receives clean defaults.
    for list_field in ("completed_tasks", "failed_tasks"):
        if filtered.get(list_field) is None:
            filtered.pop(list_field, None)
    # Coerce wave counters: string values would make pipeline_is_resumable
    # compare lexicographically ("10" < "9" → True) — silently wrong; mixed
    # types would raise. Uncoercible values drop to dataclass defaults.
    for int_field in ("wave_index", "wave_total"):
        if int_field in filtered:
            try:
                filtered[int_field] = int(filtered[int_field])
            except (TypeError, ValueError):
                filtered.pop(int_field, None)
    # Legacy tolerance (mirrors lifecycle's): an out-of-vocab current_phase on
    # disk would make the writer-side validate_pipeline raise on the next
    # read-modify-write — normalize unknown phases to the default instead.
    phase = filtered.get("current_phase")
    if phase is not None and phase not in ("idle", "orchestrate", "paused"):
        filtered.pop("current_phase", None)
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

    payload = asdict(current)

    # Writer-side validation: a writer producing structurally-invalid pipeline
    # state is a bug. Function-local import keeps the state package free of a
    # top-level schemas dependency (schemas imports lifecycle/dispatch).
    from renmark import schemas

    issues = schemas.validate_pipeline(payload)
    if issues:
        raise ValueError(f"write_pipeline_state would produce invalid state: {issues}")

    path = _pipeline_path(repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
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


def delivery_runtime_summary_from_pipeline_state(state: PipelineState | None) -> dict[str, object]:
    """Return a bounded delivery-runtime view of pipeline progress.

    This is intentionally additive and read-only: callers can surface pipeline
    progress in delivery-run runtime fields without changing pipeline.json.
    """
    current_plan = ""
    current_phase = "idle"
    wave_index = 0
    wave_total = 0
    completed_tasks: list[int] = []
    failed_tasks: list[int] = []
    last_updated = ""
    resumable = False

    if state is not None:
        current_plan = _bounded_text(state.current_plan, DELIVERY_RUNTIME_TEXT_LIMIT)
        current_phase = state.current_phase
        wave_index = state.wave_index
        wave_total = state.wave_total
        completed_tasks = _bounded_task_sample(state.completed_tasks)
        failed_tasks = _bounded_task_sample(state.failed_tasks)
        last_updated = state.last_updated
        resumable = state.current_phase in {"orchestrate", "paused"} and state.wave_index < state.wave_total

    return {
        "runtime_phase": current_phase,
        "runtime_plan_ref": current_plan,
        "runtime_wave_index": wave_index,
        "runtime_wave_total": wave_total,
        "runtime_wave_label": _wave_label(wave_index, wave_total),
        "runtime_completed_task_count": len(state.completed_tasks) if state is not None else 0,
        "runtime_failed_task_count": len(state.failed_tasks) if state is not None else 0,
        "runtime_completed_task_sample": completed_tasks,
        "runtime_failed_task_sample": failed_tasks,
        "runtime_resumable": resumable,
        "runtime_last_updated": last_updated,
        "runtime_summary": _runtime_summary_line(
            current_phase=current_phase,
            wave_index=wave_index,
            wave_total=wave_total,
            completed_count=len(state.completed_tasks) if state is not None else 0,
            failed_count=len(state.failed_tasks) if state is not None else 0,
            resumable=resumable,
        ),
    }


def delivery_runtime_summary_from_pipeline(repo_root: str | Path) -> dict[str, object]:
    """Read pipeline.json and expose its delivery-runtime summary fields."""
    return delivery_runtime_summary_from_pipeline_state(read_pipeline_state(repo_root))


def pipeline_delivery_runtime_fields(repo_root: str | Path) -> dict[str, object]:
    """Backward-friendly alias for delivery runtime field extraction."""
    return delivery_runtime_summary_from_pipeline(repo_root)


def pipeline_delivery_runtime_fields_from_state(state: PipelineState | None) -> dict[str, object]:
    """Backward-friendly alias for delivery runtime field extraction from state."""
    return delivery_runtime_summary_from_pipeline_state(state)


def _bounded_text(value: str, limit: int) -> str:
    return " ".join(value.split())[:limit]


def _bounded_task_sample(values: list[int]) -> list[int]:
    return list(values[:DELIVERY_RUNTIME_TASK_SAMPLE_LIMIT])


def _wave_label(wave_index: int, wave_total: int) -> str:
    if wave_total <= 0:
        return "wave 0/0"
    return f"wave {max(wave_index, 0)}/{wave_total}"


def _runtime_summary_line(
    *,
    current_phase: str,
    wave_index: int,
    wave_total: int,
    completed_count: int,
    failed_count: int,
    resumable: bool,
) -> str:
    parts = [
        current_phase or "idle",
        _wave_label(wave_index, wave_total),
        f"done={completed_count}",
        f"failed={failed_count}",
        f"resumable={'yes' if resumable else 'no'}",
    ]
    return " | ".join(parts)


# --- Wave summaries (.renmark/state/wave-summaries/) -----------------------
# G11: per-wave aggregated subagent outputs. Next wave reads dependency_notes
# from here, never from prior conversation.


def _wave_summaries_dir(repo_root: str | Path) -> Path:
    d = state_dir(repo_root) / WAVE_SUMMARIES_SUBDIR
    d.mkdir(parents=True, exist_ok=True)
    return d


def write_wave_summary(repo_root: str | Path, wave_index: int, task_outputs: list[dict[str, Any]]) -> Path:
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


def read_wave_summary(repo_root: str | Path, wave_index: int) -> dict[str, Any] | None:
    path = _wave_summaries_dir(repo_root) / f"wave-{wave_index}.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    if not isinstance(data, dict):
        # Valid JSON but not an object — same contract as corruption.
        return None
    return cast(dict[str, Any], data)


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

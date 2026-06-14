"""Staged-program data model + persistence — the single source of truth for
"where are we" in a staged / whole-product build (feature
``feature/roadmap-staged-planner``).

A :class:`Program` is an ordered list of :class:`StageNode`, each an ordered
list of :class:`TaskNode`. It is the *outer* roadmap state that spans many
pipeline runs: a stage maps to a requirement (or "new" work) and carries the
pipeline phases it moves through; a task is one unit of work inside a stage
with its own phase trail, retry count, and one-line summary.

Design contract (mirrors ``renmark/loop.py`` + ``renmark/lifecycle.py``):

- **Two persisted views, ONE source of truth.** The canonical state lives in
  ``.renmark/state/program.json`` (gitignored runtime). ``program.md`` under
  ``.renmark/roadmap/`` is a *rendered* committed checklist — re-derived from
  the JSON on every :func:`write_program`. The markdown is never read back as
  state; editing it by hand is overwritten on the next write.
- **Atomic write.** ``program.json`` is written via a sibling ``.tmp`` file +
  ``os.replace`` (atomic on the same filesystem), so a crash mid-write never
  leaves a half-written program and the roadmap stays resumable.
- **Never raises into the caller on read.** A missing / corrupt / non-dict
  ``program.json`` degrades to ``None`` — schema drift drops unknown fields
  and bad-typed values rather than crashing recovery.
- **Pure, deterministic renderers + accessors.** :func:`render_markdown`,
  :func:`position`, and :func:`stage_digest` are NO-LLM / NO-network string
  functions. :func:`position` and :func:`stage_digest` are the only
  orchestrator-visible accessors — both bounded.
- **Mutators are pure transforms.** ``mark_task`` / ``mark_stage`` /
  ``bump_retry`` / ``snapshot_stage_sha`` mutate-and-return the program; the
  CALLER persists via :func:`write_program`. ``retry_count`` is monotonic.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

# ── Status / mode taxonomy ─────────────────────────────────────────────────────

#: Status values a stage or task may carry. ``done`` is terminal-good;
#: ``partial`` / ``needed`` / ``blocked`` are terminal-attention states.
TaskStatus = Literal["pending", "in_progress", "done", "partial", "needed", "blocked"]
StageStatus = TaskStatus  # same vocabulary at both levels

#: The full ordered status vocabulary (used to validate mutator input).
STATUSES: tuple[str, ...] = (
    "pending",
    "in_progress",
    "done",
    "partial",
    "needed",
    "blocked",
)

#: Build modes a program can run in. ``feature-planner`` = a single feature
#: decomposed into stages; ``staged`` = a multi-stage roadmap; ``whole-product``
#: = full product build; ``setup`` = bootstrap / onboarding roadmap.
ProgramMode = Literal["feature-planner", "staged", "whole-product", "setup"]

MODES: tuple[str, ...] = ("feature-planner", "staged", "whole-product", "setup")

#: Status glyphs for the rendered checklist headings. Deterministic, ASCII-safe
#: where possible; chosen to read at a glance in a committed markdown file.
_STATUS_GLYPH: dict[str, str] = {
    "pending": "○",
    "in_progress": "◐",
    "done": "●",
    "partial": "◑",
    "needed": "!",
    "blocked": "✗",
}

ARTIFACT_TYPE = "program"
SCHEMA_VERSION = 1

# ── Canonical paths ────────────────────────────────────────────────────────────

#: Runtime state (gitignored) — the canonical source of truth.
PROGRAM_JSON_REL = os.path.join(".renmark", "state", "program.json")
#: Committed checklist (rendered view) — never the source of truth.
PROGRAM_MD_REL = os.path.join(".renmark", "roadmap", "program.md")


def program_json_path(repo: Path | str) -> Path:
    """Return the absolute path to ``.renmark/state/program.json``."""
    return Path(repo) / ".renmark" / "state" / "program.json"


def program_md_path(repo: Path | str) -> Path:
    """Return the absolute path to ``.renmark/roadmap/program.md``."""
    return Path(repo) / ".renmark" / "roadmap" / "program.md"


# ── Data model ─────────────────────────────────────────────────────────────────


@dataclass
class TaskNode:
    """One unit of work inside a stage. JSON-trivial (str/int/list only)."""

    id: str = ""
    title: str = ""
    status: str = "pending"  # one of STATUSES
    retry_count: int = 0  # monotonic — only ever increases
    pipeline_phases: list[str] = field(default_factory=list)  # e.g. ["dispatch", "qa"]
    summary: str | None = None  # ≤5-line optional one/few-liner


@dataclass
class StageNode:
    """One stage of the roadmap — maps to a requirement or "new" work and owns
    an ordered list of tasks plus the pipeline phases it moves through."""

    id: str = ""
    title: str = ""
    serves: str = ""  # "REQ-n" or "new"
    status: str = "pending"  # one of STATUSES
    pipeline_phases: list[str] = field(default_factory=list)  # e.g. ["brainstorm", "plan"]
    tasks: list[TaskNode] = field(default_factory=list)


@dataclass
class Program:
    """The staged-program root — the single source of truth for "where are we".

    Persisted to ``.renmark/state/program.json``; re-rendered to
    ``.renmark/roadmap/program.md`` on every write.
    """

    feature: str = ""
    mode: str = "staged"  # one of MODES
    created_at: str = ""
    source_sha: str | None = None
    stages: list[StageNode] = field(default_factory=list)
    #: Map stage-id → git sha captured when the stage completed.
    stage_completion_sha: dict[str, str] = field(default_factory=dict)
    current_stage_id: str | None = None

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = _now()

    def to_json(self) -> str:
        """Serialise to pretty JSON. Round-trips through :func:`asdict` so nested
        dataclasses become plain dicts (JSON-safe)."""
        return json.dumps(asdict(self), indent=2, sort_keys=False)


# ── Read / write ───────────────────────────────────────────────────────────────


def read_program(repo: Path | str) -> Program | None:
    """Return the persisted :class:`Program`, or ``None`` if absent/corrupt.

    Never raises: a missing file, unreadable bytes, invalid JSON, or a non-dict
    payload all yield ``None``. Unknown fields are dropped and bad-typed values
    degrade to defaults so schema drift cannot crash cold-start recovery.
    """
    path = program_json_path(repo)
    try:
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    try:
        return _coerce_program(data)
    except (TypeError, ValueError):
        return None


def write_program(repo: Path | str, program: Program) -> Path:
    """Persist ``program`` ATOMICALLY to ``program.json`` AND re-render
    ``program.md`` from the same state. Creates parent dirs as needed.

    The JSON is the source of truth; the markdown is a rendered view written on
    every call so the committed checklist never drifts from runtime state. The
    JSON write is atomic (tmp file + ``os.replace`` — atomic on the same
    filesystem) so a crash mid-write never leaves a half-written program.

    Returns the path to the written ``program.json``. The markdown render is
    best-effort: a failure to write ``program.md`` does NOT corrupt or roll back
    the authoritative JSON (the rendered view can always be regenerated).
    """
    json_path = program_json_path(repo)
    json_path.parent.mkdir(parents=True, exist_ok=True)

    payload = program.to_json()
    tmp = json_path.with_suffix(json_path.suffix + ".tmp")
    tmp.write_text(payload, encoding="utf-8")
    os.replace(tmp, json_path)  # atomic on the same filesystem

    # Re-render the committed checklist from the SAME state. Best-effort — the
    # JSON is already durable; a markdown write failure must not undo it.
    try:
        md_path = program_md_path(repo)
        md_path.parent.mkdir(parents=True, exist_ok=True)
        md_path.write_text(render_markdown(program), encoding="utf-8")
    except OSError:
        pass

    return json_path


# ── Coercion (tolerant read) ─────────────────────────────────────────────────


def _coerce_str(value: object, default: str = "") -> str:
    """Coerce ``value`` to a str field value; ``None`` → default, else ``str``."""
    if isinstance(value, str):
        return value
    if value is None:
        return default
    try:
        return str(value)
    except Exception:  # pragma: no cover — str() on a pathological object
        return default


def _coerce_opt_str(value: object) -> str | None:
    """Coerce to ``str | None`` — JSON ``null`` / missing → ``None``."""
    if value is None:
        return None
    if isinstance(value, str):
        return value
    try:
        return str(value)
    except Exception:  # pragma: no cover
        return None


def _coerce_int(value: object, default: int = 0) -> int:
    """Coerce ``value`` to a non-negative int; bad/garbage → ``default``."""
    if isinstance(value, bool):  # bool is an int subclass — treat as absent.
        return default
    if isinstance(value, int):
        return value if value >= 0 else default
    if isinstance(value, float):
        try:
            i = int(value)
        except (ValueError, OverflowError):
            return default
        return i if i >= 0 else default
    if isinstance(value, str):
        raw = value.strip().replace("_", "").replace(",", "")
        if not raw:
            return default
        try:
            i = int(float(raw))
        except (ValueError, OverflowError):
            return default
        return i if i >= 0 else default
    return default


def _coerce_status(value: object, default: str = "pending") -> str:
    """Coerce ``value`` to a known status; unknown / non-str → ``default``."""
    if isinstance(value, str) and value in STATUSES:
        return value
    return default


def _coerce_mode(value: object, default: str = "staged") -> str:
    """Coerce ``value`` to a known mode; unknown / non-str → ``default``."""
    if isinstance(value, str) and value in MODES:
        return value
    return default


def _coerce_phases(value: object) -> list[str]:
    """Coerce ``value`` to a list of phase strings; non-list → ``[]``."""
    if not isinstance(value, list):
        return []
    return [_coerce_str(item) for item in value if item is not None]


def _coerce_task(data: object) -> TaskNode | None:
    """Build a :class:`TaskNode` from arbitrary JSON; non-dict → ``None``."""
    if not isinstance(data, dict):
        return None
    summary_raw = data.get("summary")
    return TaskNode(
        id=_coerce_str(data.get("id")),
        title=_coerce_str(data.get("title")),
        status=_coerce_status(data.get("status")),
        retry_count=_coerce_int(data.get("retry_count")),
        pipeline_phases=_coerce_phases(data.get("pipeline_phases")),
        summary=_coerce_opt_str(summary_raw) if summary_raw is not None else None,
    )


def _coerce_stage(data: object) -> StageNode | None:
    """Build a :class:`StageNode` from arbitrary JSON; non-dict → ``None``."""
    if not isinstance(data, dict):
        return None
    raw_tasks = data.get("tasks")
    tasks: list[TaskNode] = []
    if isinstance(raw_tasks, list):
        for item in raw_tasks:
            task = _coerce_task(item)
            if task is not None:
                tasks.append(task)
    return StageNode(
        id=_coerce_str(data.get("id")),
        title=_coerce_str(data.get("title")),
        serves=_coerce_str(data.get("serves")),
        status=_coerce_status(data.get("status")),
        pipeline_phases=_coerce_phases(data.get("pipeline_phases")),
        tasks=tasks,
    )


def _coerce_completion_sha(value: object) -> dict[str, str]:
    """Coerce the stage-id → sha map; non-dict / bad entries dropped."""
    if not isinstance(value, dict):
        return {}
    out: dict[str, str] = {}
    for key, val in value.items():
        if isinstance(key, str) and isinstance(val, str):
            out[key] = val
    return out


def _coerce_program(data: dict[str, Any]) -> Program:
    """Build a :class:`Program` from arbitrary JSON, coercing every field. Never
    raises on bad types — unknown keys dropped, bad values degrade to defaults."""
    raw_stages = data.get("stages")
    stages: list[StageNode] = []
    if isinstance(raw_stages, list):
        for item in raw_stages:
            stage = _coerce_stage(item)
            if stage is not None:
                stages.append(stage)
    return Program(
        feature=_coerce_str(data.get("feature")),
        mode=_coerce_mode(data.get("mode")),
        created_at=_coerce_str(data.get("created_at")) or _now(),
        source_sha=_coerce_opt_str(data.get("source_sha")),
        stages=stages,
        stage_completion_sha=_coerce_completion_sha(data.get("stage_completion_sha")),
        current_stage_id=_coerce_opt_str(data.get("current_stage_id")),
    )


# ── Markdown render (pure) ─────────────────────────────────────────────────────


def render_markdown(program: Program) -> str:
    """Render ``program`` as a deterministic committed checklist (PURE string).

    Stages are ``##`` headings prefixed with a status glyph; tasks are
    ``- [x]`` / ``- [ ]`` checkboxes (checked iff status == ``done``), with the
    task's one-line summary appended inline when present. Carries G6 provenance
    frontmatter. NO LLM, NO network — deterministic for a given program.
    """
    lines: list[str] = []

    # Provenance frontmatter (G6).
    lines.append("---")
    lines.append(f"artifact_type: {ARTIFACT_TYPE}")
    lines.append(f"schema_version: {SCHEMA_VERSION}")
    lines.append(f"created_at: {program.created_at or _now()}")
    lines.append(f"source_sha: {program.source_sha or 'null'}")
    lines.append("---")
    lines.append("")

    feature = program.feature or "(unnamed)"
    lines.append(f"# Program — {feature}")
    lines.append("")
    lines.append(f"_mode: {program.mode} · {position(program)}_")
    lines.append("")

    if not program.stages:
        lines.append("_No stages yet._")
        lines.append("")
        return "\n".join(lines)

    for stage in program.stages:
        glyph = _STATUS_GLYPH.get(stage.status, "?")
        title = stage.title or stage.id or "(untitled stage)"
        serves = f" — serves {stage.serves}" if stage.serves else ""
        marker = " **(current)**" if stage.id and stage.id == program.current_stage_id else ""
        lines.append(f"## {glyph} {title}{serves}{marker}")
        if stage.pipeline_phases:
            lines.append(f"_phases: {' → '.join(stage.pipeline_phases)}_")
        lines.append("")

        if not stage.tasks:
            lines.append("- _(no tasks)_")
        else:
            for task in stage.tasks:
                box = "x" if task.status == "done" else " "
                ttitle = task.title or task.id or "(untitled task)"
                retry = f" _(retries: {task.retry_count})_" if task.retry_count else ""
                summary = ""
                if task.summary:
                    one_line = " ".join(task.summary.split())
                    summary = f" — {one_line}"
                lines.append(f"- [{box}] {ttitle}{summary}{retry}")
        lines.append("")

    return "\n".join(lines)


# ── Bounded accessors (orchestrator-visible) ────────────────────────────────────


def position(program: Program) -> str:
    """Return the ONE bounded orchestrator-visible position line.

    Example: ``"Stage 2/5 · task 3/4 done · current: <stage title>"``. When no
    current stage is set, falls back to the first stage. Always a single line.
    """
    total_stages = len(program.stages)
    if total_stages == 0:
        return "Stage 0/0 · no stages · current: (none)"

    # Resolve the current stage: explicit current_stage_id, else first stage.
    index = 0
    current: StageNode | None = None
    if program.current_stage_id:
        for i, stage in enumerate(program.stages):
            if stage.id == program.current_stage_id:
                index, current = i, stage
                break
    if current is None:
        current = program.stages[0]
        index = 0

    stage_no = index + 1
    done_tasks = sum(1 for t in current.tasks if t.status == "done")
    total_tasks = len(current.tasks)
    title = current.title or current.id or "(untitled)"
    return f"Stage {stage_no}/{total_stages} · task {done_tasks}/{total_tasks} done · current: {title}"


def stage_digest(program: Program, stage_id: str) -> str:
    """Return a bounded (≤5-line) rollup of a stage's task summaries.

    Pure string accessor for the orchestrator: the stage heading line plus up to
    4 task summary lines (so the total stays ≤ 5 lines). Tasks without a summary
    contribute their title + status. An unknown ``stage_id`` yields a single
    ``"(stage <id> not found)"`` line. Never raises.
    """
    stage = _find_stage(program, stage_id)
    if stage is None:
        return f"(stage {stage_id} not found)"

    glyph = _STATUS_GLYPH.get(stage.status, "?")
    title = stage.title or stage.id or "(untitled stage)"
    header = f"{glyph} {title} [{stage.status}] — {len(stage.tasks)} task(s)"

    body: list[str] = []
    for task in stage.tasks[:4]:  # header + ≤4 tasks == ≤5 lines
        ttitle = task.title or task.id or "(untitled task)"
        if task.summary:
            detail = " ".join(task.summary.split())
        else:
            detail = task.status
        body.append(f"  - {ttitle}: {detail}")

    lines = [header, *body]
    if len(stage.tasks) > 4:
        # Replace the 5th line with an overflow marker to stay ≤5 lines.
        lines = lines[:4] + [f"  - … (+{len(stage.tasks) - 3} more tasks)"]
    return "\n".join(lines[:5])


# ── Mutators (pure transforms — caller persists) ────────────────────────────────


def mark_task(
    program: Program,
    stage_id: str,
    task_id: str,
    status: str,
    summary: str | None = None,
) -> Program:
    """Set ``status`` (and optionally ``summary``) on a task; return ``program``.

    Mutates in place and returns the same object (caller persists via
    :func:`write_program`). An unknown stage/task is a no-op. An invalid status
    leaves the existing status untouched. A ``summary`` of ``None`` leaves any
    existing summary in place; pass an empty string to clear it.
    """
    stage = _find_stage(program, stage_id)
    if stage is None:
        return program
    task = _find_task(stage, task_id)
    if task is None:
        return program
    if status in STATUSES:
        task.status = status
    if summary is not None:
        task.summary = summary
    return program


def mark_stage(program: Program, stage_id: str, status: str) -> Program:
    """Set a stage's ``status``; return ``program``. Unknown stage / invalid
    status is a no-op. Mutates in place (caller persists)."""
    stage = _find_stage(program, stage_id)
    if stage is None:
        return program
    if status in STATUSES:
        stage.status = status
    return program


def bump_retry(program: Program, stage_id: str, task_id: str) -> Program:
    """Increment a task's ``retry_count`` (monotonic); return ``program``.

    Retry count only ever increases — a corrupt negative value is normalised to
    0 before the increment. Unknown stage/task is a no-op. Mutates in place.
    """
    stage = _find_stage(program, stage_id)
    if stage is None:
        return program
    task = _find_task(stage, task_id)
    if task is None:
        return program
    current = task.retry_count if isinstance(task.retry_count, int) and task.retry_count >= 0 else 0
    task.retry_count = current + 1
    return program


def snapshot_stage_sha(program: Program, stage_id: str, sha: str) -> Program:
    """Record the git ``sha`` captured when ``stage_id`` completed; return
    ``program``. Records the map entry even for an unknown stage id (the sha
    map is keyed independently of the stages list). Mutates in place."""
    program.stage_completion_sha[stage_id] = sha
    return program


# ── Internal helpers ─────────────────────────────────────────────────────────


def _find_stage(program: Program, stage_id: str) -> StageNode | None:
    for stage in program.stages:
        if stage.id == stage_id:
            return stage
    return None


def _find_task(stage: StageNode, task_id: str) -> TaskNode | None:
    for task in stage.tasks:
        if task.id == task_id:
            return task
    return None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


__all__ = [
    "ARTIFACT_TYPE",
    "MODES",
    "PROGRAM_JSON_REL",
    "PROGRAM_MD_REL",
    "SCHEMA_VERSION",
    "STATUSES",
    "Program",
    "ProgramMode",
    "StageNode",
    "StageStatus",
    "TaskNode",
    "TaskStatus",
    "bump_retry",
    "mark_stage",
    "mark_task",
    "position",
    "program_json_path",
    "program_md_path",
    "read_program",
    "render_markdown",
    "snapshot_stage_sha",
    "stage_digest",
    "write_program",
]

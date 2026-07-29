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
- **Fail loud on corruption; ``None`` ONLY when absent.** A *missing*
  ``program.json`` yields ``None`` (there is no in-flight program). A file that
  EXISTS but is unreadable, invalid JSON, not a JSON object, or carries invalid
  schema / status / mode / type values raises :class:`ProgramStateError`.
  ``program.json`` is correctness-critical resumable state — masking its
  corruption as "no program" would let ``/renmark:resume`` skip a real
  in-flight program and would hide broken driver behaviour, so corruption fails
  loud rather than degrading to ``None``.
- **Pure, deterministic renderers + accessors.** :func:`render_markdown`,
  :func:`position`, and :func:`stage_digest` are NO-LLM / NO-network string
  functions. :func:`position` and :func:`stage_digest` are the only
  orchestrator-visible accessors — both bounded.
- **Mutators are pure transforms.** ``mark_task`` / ``mark_stage`` /
  ``bump_retry`` / ``snapshot_stage_sha`` mutate-and-return the program; the
  CALLER persists via :func:`write_program`. ``retry_count`` is monotonic.
"""

from __future__ import annotations

import contextlib
import json
import os
import tempfile
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

# ── Errors ──────────────────────────────────────────────────────────────────────


class ProgramStateError(Exception):
    """Raised when ``program.json`` exists but is corrupt / malformed / invalid.

    A *missing* state file is NOT an error (:func:`read_program` returns
    ``None``). A present-but-broken file — unreadable bytes, invalid JSON, a
    non-object payload, or invalid schema / status / mode / type values — raises
    this so corruption of resumable state is never silently masked.
    """


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

# Compatibility adapter: program stage/task status stays in the program
# vocabulary; delivery-facing callers can opt into this external mapping.
_DELIVERY_STATE_BY_STATUS: dict[str, str] = {
    "pending": "pending",
    "in_progress": "in_progress",
    "done": "passed",
    "partial": "blocked",
    "needed": "blocked",
    "blocked": "blocked",
}

# Stable milestone aliases for stage ids that already describe a delivery
# milestone. Unknown ids fall back to the shared slugging logic below.
_STAGE_MILESTONE_ID_ALIASES: dict[str, str] = {
    "brainstorm": "discovery",
    "discovery": "discovery",
    "prd": "prd",
    "requirements": "prd",
    "plan": "plan",
    "planning": "plan",
    "build": "build",
    "implement": "build",
    "implementation": "build",
    "verify": "verify",
    "verification": "verify",
    "qa": "verify",
    "review": "review",
    "docs": "documented",
    "documented": "documented",
    "release": "release",
    "ship": "release",
}

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
    """Return the persisted :class:`Program`, or ``None`` IFF the state file is
    absent.

    ``None`` means exactly one thing: there is no ``program.json`` (no in-flight
    program). A file that EXISTS but is unreadable, not valid JSON, not a JSON
    object, or carries invalid schema / status / mode / type values raises
    :class:`ProgramStateError`. ``program.json`` is correctness-critical
    resumable state; masking its corruption as "no program" would let
    ``/renmark:resume`` skip a real in-flight program and would hide broken
    driver behaviour — so corruption fails loud.
    """
    path = program_json_path(repo)
    if not path.exists():
        return None
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ProgramStateError(f"program.json exists but is unreadable: {exc}") from exc
    except UnicodeDecodeError as exc:
        # Invalid UTF-8 bytes in an existing file are corruption, not "absent".
        # UnicodeDecodeError is a ValueError (not an OSError), so it must be
        # caught explicitly or it would leak past read_program uncaught.
        raise ProgramStateError(f"program.json is not valid UTF-8: {exc}") from exc
    try:
        data = json.loads(raw)
    except ValueError as exc:
        raise ProgramStateError(f"program.json is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ProgramStateError(
            f"program.json must be a JSON object, got {type(data).__name__}"
        )
    return _parse_program(data)


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
    # Atomic durable write: a UNIQUE temp file in the SAME dir (so os.replace is
    # a rename, not a cross-device copy), fsync'd before the swap so a crash
    # right after replace cannot surface a torn file. A unique name (not a shared
    # ``.tmp``) also keeps two writers from clobbering each other's temp —
    # defense-in-depth; the program is single-writer by design.
    fd, tmp_name = tempfile.mkstemp(
        dir=str(json_path.parent), prefix=".program-", suffix=".json.tmp"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(payload)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp_name, json_path)  # atomic on the same filesystem
    except OSError:
        # Never leave a temp file behind on failure.
        with contextlib.suppress(OSError):
            os.unlink(tmp_name)
        raise

    # Re-render the committed checklist from the SAME state. Best-effort — the
    # JSON is already durable; a markdown write failure must not undo it.
    try:
        md_path = program_md_path(repo)
        md_path.parent.mkdir(parents=True, exist_ok=True)
        md_path.write_text(render_markdown(program), encoding="utf-8")
    except OSError:
        pass

    return json_path


# ── Strict parse (loud on corruption) ───────────────────────────────────────────
#
# Read-side validation FAILS LOUD: a present ``program.json`` with a bad type or
# an out-of-vocabulary status/mode raises :class:`ProgramStateError`. Genuinely
# *absent* optional fields fall back to the dataclass default (an empty program
# file ``{}`` is valid); only *present* values are type/enum-checked. ``where``
# threads a JSON path (e.g. ``program.stages[0].tasks[2]``) into every message so
# corruption is actionable.


def _str_field(data: dict[str, Any], key: str, where: str, *, default: str = "") -> str:
    """Read a required-string field; absent/``null`` → ``default``; wrong type raises."""
    if key not in data or data[key] is None:
        return default
    value = data[key]
    if not isinstance(value, str):
        raise ProgramStateError(
            f"{where}: {key!r} must be a string, got {type(value).__name__}"
        )
    return value


def _opt_str_field(data: dict[str, Any], key: str, where: str) -> str | None:
    """Read a ``str | None`` field; absent/``null`` → ``None``; wrong type raises."""
    if key not in data or data[key] is None:
        return None
    value = data[key]
    if not isinstance(value, str):
        raise ProgramStateError(
            f"{where}: {key!r} must be a string or null, got {type(value).__name__}"
        )
    return value


def _status_field(
    data: dict[str, Any], key: str, where: str, *, default: str = "pending"
) -> str:
    """Read a status field; absent/``null`` → ``default``; non-str or unknown raises."""
    if key not in data or data[key] is None:
        return default
    value = data[key]
    if not isinstance(value, str) or value not in STATUSES:
        raise ProgramStateError(
            f"{where}: {key!r} must be one of {STATUSES}, got {value!r}"
        )
    return value


def _mode_field(
    data: dict[str, Any], key: str, where: str, *, default: str = "staged"
) -> str:
    """Read the mode field; absent/``null`` → ``default``; non-str or unknown raises."""
    if key not in data or data[key] is None:
        return default
    value = data[key]
    if not isinstance(value, str) or value not in MODES:
        raise ProgramStateError(f"{where}: {key!r} must be one of {MODES}, got {value!r}")
    return value


def _int_field(data: dict[str, Any], key: str, where: str, *, default: int = 0) -> int:
    """Read a non-negative int field; absent/``null`` → ``default``; non-int or
    negative raises (``bool`` is rejected — it is not a valid count)."""
    if key not in data or data[key] is None:
        return default
    value = data[key]
    if isinstance(value, bool) or not isinstance(value, int):
        raise ProgramStateError(
            f"{where}: {key!r} must be an integer, got {type(value).__name__}"
        )
    if value < 0:
        raise ProgramStateError(f"{where}: {key!r} must be >= 0, got {value}")
    return value


def _phases_field(data: dict[str, Any], key: str, where: str) -> list[str]:
    """Read a list-of-strings field; absent/``null`` → ``[]``; non-list or a
    non-str element raises."""
    if key not in data or data[key] is None:
        return []
    value = data[key]
    if not isinstance(value, list):
        raise ProgramStateError(
            f"{where}: {key!r} must be a list, got {type(value).__name__}"
        )
    out: list[str] = []
    for i, item in enumerate(value):
        if not isinstance(item, str):
            raise ProgramStateError(
                f"{where}: {key!r}[{i}] must be a string, got {type(item).__name__}"
            )
        out.append(item)
    return out


def _completion_sha_field(data: dict[str, Any], key: str, where: str) -> dict[str, str]:
    """Read the stage-id → sha map; absent/``null`` → ``{}``; non-dict or a
    non-string key/value raises."""
    if key not in data or data[key] is None:
        return {}
    value = data[key]
    if not isinstance(value, dict):
        raise ProgramStateError(
            f"{where}: {key!r} must be an object, got {type(value).__name__}"
        )
    out: dict[str, str] = {}
    for k, v in value.items():
        if not isinstance(k, str) or not isinstance(v, str):
            raise ProgramStateError(f"{where}: {key!r} must map string → string")
        out[k] = v
    return out


def _parse_task(data: object, where: str) -> TaskNode:
    """Build a :class:`TaskNode` from JSON; non-object or bad field raises."""
    if not isinstance(data, dict):
        raise ProgramStateError(
            f"{where}: task must be an object, got {type(data).__name__}"
        )
    return TaskNode(
        id=_str_field(data, "id", where),
        title=_str_field(data, "title", where),
        status=_status_field(data, "status", where),
        retry_count=_int_field(data, "retry_count", where),
        pipeline_phases=_phases_field(data, "pipeline_phases", where),
        summary=_opt_str_field(data, "summary", where),
    )


def _parse_stage(data: object, where: str) -> StageNode:
    """Build a :class:`StageNode` from JSON; non-object or bad field raises."""
    if not isinstance(data, dict):
        raise ProgramStateError(
            f"{where}: stage must be an object, got {type(data).__name__}"
        )
    raw_tasks = data.get("tasks")
    tasks: list[TaskNode] = []
    if raw_tasks is not None:
        if not isinstance(raw_tasks, list):
            raise ProgramStateError(
                f"{where}: 'tasks' must be a list, got {type(raw_tasks).__name__}"
            )
        tasks = [_parse_task(item, f"{where}.tasks[{i}]") for i, item in enumerate(raw_tasks)]
    return StageNode(
        id=_str_field(data, "id", where),
        title=_str_field(data, "title", where),
        serves=_str_field(data, "serves", where),
        status=_status_field(data, "status", where),
        pipeline_phases=_phases_field(data, "pipeline_phases", where),
        tasks=tasks,
    )


def _parse_program(data: dict[str, Any]) -> Program:
    """Build a :class:`Program` from a JSON object, validating every field.

    Raises :class:`ProgramStateError` on the first invalid field — never coerces
    a bad value into a default."""
    where = "program"
    raw_stages = data.get("stages")
    stages: list[StageNode] = []
    if raw_stages is not None:
        if not isinstance(raw_stages, list):
            raise ProgramStateError(
                f"{where}: 'stages' must be a list, got {type(raw_stages).__name__}"
            )
        stages = [_parse_stage(item, f"{where}.stages[{i}]") for i, item in enumerate(raw_stages)]
    # Stage ids MUST be unique: mark_stage / next_stage / position all resolve a
    # stage by first-id match, so a duplicate id silently shadows a later stage —
    # corrupt state that fails loud here rather than mis-sequencing the driver.
    non_empty_ids = [stage.id for stage in stages if stage.id]
    dupes = sorted({sid for sid in non_empty_ids if non_empty_ids.count(sid) > 1})
    if dupes:
        raise ProgramStateError(f"{where}: duplicate stage id(s) {dupes}")
    # Referential integrity: current_stage_id and every stage_completion_sha key
    # MUST name a real stage. A dangling reference is corrupt state — failing
    # loud here is what keeps position()/the driver from silently misreporting
    # against a stale pointer (mirrors snapshot_stage_sha's mutator-side guard).
    stage_ids = {stage.id for stage in stages}
    current_stage_id = _opt_str_field(data, "current_stage_id", where)
    if current_stage_id and current_stage_id not in stage_ids:
        raise ProgramStateError(
            f"{where}: current_stage_id {current_stage_id!r} does not match any stage id"
        )
    completion_sha = _completion_sha_field(data, "stage_completion_sha", where)
    dangling = sorted(k for k in completion_sha if k not in stage_ids)
    if dangling:
        raise ProgramStateError(
            f"{where}: stage_completion_sha references unknown stage id(s) {dangling}"
        )
    return Program(
        feature=_str_field(data, "feature", where),
        mode=_mode_field(data, "mode", where),
        created_at=_str_field(data, "created_at", where) or _now(),
        source_sha=_opt_str_field(data, "source_sha", where),
        stages=stages,
        stage_completion_sha=completion_sha,
        current_stage_id=current_stage_id,
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
        detail = " ".join(task.summary.split()) if task.summary else task.status
        body.append(f"  - {ttitle}: {detail}")

    lines = [header, *body]
    if len(stage.tasks) > 4:
        # Replace the 5th line with an overflow marker to stay ≤5 lines.
        lines = [*lines[:4], f"  - … (+{len(stage.tasks) - 3} more tasks)"]
    return "\n".join(lines[:5])


# ── Delivery compatibility adapter (pure, additive) ───────────────────────────


def delivery_state_for_program_status(status: str) -> str:
    """Map a program status into the delivery-state vocabulary.

    Program persistence keeps its existing status words. This adapter is
    delivery-facing only and never writes back into ``Program``.
    """
    return _DELIVERY_STATE_BY_STATUS.get(status, "unknown")


def stable_milestone_id_for_stage(stage: StageNode) -> str:
    """Project a :class:`StageNode` into a stable delivery milestone id."""
    for candidate in (stage.id, stage.serves, stage.title):
        token = _milestone_alias(candidate)
        if token:
            return token
    return "milestone"


def stable_work_package_id_for_task(stage: StageNode, task: TaskNode) -> str:
    """Project a task into a stable delivery work-package id."""
    milestone_id = stable_milestone_id_for_stage(stage)
    token = _stable_slug(task.id) or _stable_slug(task.title)
    return f"{milestone_id}--{token or 'work-package'}"


def program_delivery_milestones(program: Program) -> list[dict[str, Any]]:
    """Return delivery-facing milestone summaries projected from ``program``.

    The projection is bounded, pure, and additive: it does not affect program
    JSON, markdown rendering, or mutator behavior.
    """
    milestones: list[dict[str, Any]] = []
    for index, stage in enumerate(program.stages, start=1):
        milestone_id = stable_milestone_id_for_stage(stage)
        work_packages = stage_work_package_summaries(stage)
        milestones.append(
            {
                "milestone_id": milestone_id,
                "stage_id": stage.id,
                "title": stage.title or stage.id or "(untitled stage)",
                "serves": stage.serves,
                "status": stage.status,
                "delivery_state": delivery_state_for_program_status(stage.status),
                "current": bool(stage.id and stage.id == program.current_stage_id),
                "index": index,
                "task_count": len(stage.tasks),
                "completed_task_count": sum(1 for task in stage.tasks if task.status == "done"),
                "pipeline_phases": list(stage.pipeline_phases),
                "completion_sha": program.stage_completion_sha.get(stage.id, ""),
                "work_packages": work_packages,
            }
        )
    return milestones


def stage_work_package_summaries(stage: StageNode) -> list[dict[str, Any]]:
    """Return delivery-facing work-package summaries for one stage."""
    milestone_id = stable_milestone_id_for_stage(stage)
    packages: list[dict[str, Any]] = []
    for task in stage.tasks:
        packages.append(
            {
                "package_id": stable_work_package_id_for_task(stage, task),
                "milestone_id": milestone_id,
                "stage_id": stage.id,
                "task_id": task.id,
                "title": task.title or task.id or "(untitled task)",
                "status": task.status,
                "delivery_state": delivery_state_for_program_status(task.status),
                "summary": " ".join(task.summary.split()) if task.summary else "",
                "retry_count": task.retry_count,
                "pipeline_phases": list(task.pipeline_phases),
            }
        )
    return packages


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
    :func:`write_program`). Fails loud: an unknown ``stage_id`` / ``task_id``
    raises :class:`ValueError`, and an invalid ``status`` raises
    :class:`ValueError` — silent no-ops would let the driver believe a state
    transition happened when it did not. A ``summary`` of ``None`` leaves any
    existing summary in place; pass an empty string to clear it.
    """
    if status not in STATUSES:
        raise ValueError(f"invalid status {status!r}; must be one of {STATUSES}")
    stage = _find_stage(program, stage_id)
    if stage is None:
        raise ValueError(f"unknown stage id {stage_id!r}")
    task = _find_task(stage, task_id)
    if task is None:
        raise ValueError(f"unknown task id {task_id!r} in stage {stage_id!r}")
    task.status = status
    if summary is not None:
        task.summary = summary
    return program


def mark_stage(program: Program, stage_id: str, status: str) -> Program:
    """Set a stage's ``status``; return ``program``. Mutates in place (caller
    persists). Fails loud: an unknown ``stage_id`` or an invalid ``status``
    raises :class:`ValueError` rather than silently no-op'ing."""
    if status not in STATUSES:
        raise ValueError(f"invalid status {status!r}; must be one of {STATUSES}")
    stage = _find_stage(program, stage_id)
    if stage is None:
        raise ValueError(f"unknown stage id {stage_id!r}")
    stage.status = status
    return program


def bump_retry(program: Program, stage_id: str, task_id: str) -> Program:
    """Increment a task's ``retry_count`` (monotonic); return ``program``.

    Retry count only ever increases — a corrupt negative value is normalised to
    0 before the increment. Fails loud: an unknown ``stage_id`` / ``task_id``
    raises :class:`ValueError`. Mutates in place.
    """
    stage = _find_stage(program, stage_id)
    if stage is None:
        raise ValueError(f"unknown stage id {stage_id!r}")
    task = _find_task(stage, task_id)
    if task is None:
        raise ValueError(f"unknown task id {task_id!r} in stage {stage_id!r}")
    current = task.retry_count if isinstance(task.retry_count, int) and task.retry_count >= 0 else 0
    task.retry_count = current + 1
    return program


def snapshot_stage_sha(program: Program, stage_id: str, sha: str) -> Program:
    """Record the git ``sha`` captured for ``stage_id``; return ``program``.

    Fails loud: ``stage_id`` MUST name a stage present in the program — an
    unknown stage id raises :class:`ValueError` (the sha map must not accumulate
    keys for stages that do not exist). Mutates in place; caller persists.
    """
    if _find_stage(program, stage_id) is None:
        raise ValueError(
            f"unknown stage id {stage_id!r}; cannot snapshot sha for a stage not in the program"
        )
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


def _milestone_alias(value: str) -> str:
    token = _stable_slug(value)
    if not token:
        return ""
    return _STAGE_MILESTONE_ID_ALIASES.get(token, token)


def _stable_slug(value: str) -> str:
    chars: list[str] = []
    previous_dash = False
    for ch in value.lower():
        if ch.isalnum():
            chars.append(ch)
            previous_dash = False
            continue
        if chars and not previous_dash:
            chars.append("-")
            previous_dash = True
    return "".join(chars).strip("-")[:48]


__all__ = [
    "ARTIFACT_TYPE",
    "MODES",
    "PROGRAM_JSON_REL",
    "PROGRAM_MD_REL",
    "SCHEMA_VERSION",
    "STATUSES",
    "Program",
    "ProgramMode",
    "ProgramStateError",
    "StageNode",
    "StageStatus",
    "TaskNode",
    "TaskStatus",
    "bump_retry",
    "delivery_state_for_program_status",
    "mark_stage",
    "mark_task",
    "position",
    "program_delivery_milestones",
    "program_json_path",
    "program_md_path",
    "read_program",
    "render_markdown",
    "snapshot_stage_sha",
    "stable_milestone_id_for_stage",
    "stable_work_package_id_for_task",
    "stage_work_package_summaries",
    "stage_digest",
    "write_program",
]

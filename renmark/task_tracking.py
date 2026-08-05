"""Native task-lifecycle tracking for dispatched work (REQ-31).

Models the same lifecycle a host's native Task tools expose (``pending`` ->
``in_progress`` -> ``completed``) as a small, host-independent, testable data
layer that the real dispatch engine (:mod:`renmark.cli._engine`) calls at
each actual dispatch point — not documentation the orchestrator is merely
supposed to follow.

Design mirrors :mod:`renmark.agency` / :mod:`renmark.delivery_state` (single
JSON state file, atomic write) and reuses :mod:`renmark.ledger`'s
dispatch-independence check for the no-self-approval rule rather than
reimplementing it.

- **State lives at** ``.renmark/state/tasks.json`` — gitignored runtime
  state, same tier as ``pipeline.json``/``agency.json``: it survives
  interruption/resume within a project but is not itself the durable,
  committed record (that stays in ``.renmark/ledger/`` and pipeline
  artifacts, per REQ-5/REQ-30).
- **Reads never raise.** A missing, unreadable, or corrupt file returns an
  empty task map so a tracking-layer failure never blocks a real dispatch
  (REQ-30/REQ-31: tracking is informational, never load-bearing for
  execution).
- **Writes are atomic** — a temp file in the same directory is
  ``os.replace``d into place.
- **Creation is idempotent (resume-reuse).** :func:`create_or_reuse_task`
  returns the existing record unchanged if the task_id already exists and
  is not ``deleted`` — a resumed run never recreates a task, and a caller
  can call it unconditionally at every dispatch site without checking first.
- **No silent completion without evidence.** :func:`complete_task` raises
  :class:`MissingEvidenceError` if no artifact path or result summary is
  given.
- **No self-approval.** :func:`complete_worker_task` requires a linked
  verification task whose ``dispatch_identity`` is independent of the
  worker's, checked via :func:`renmark.ledger.check_dispatch_independence` —
  the exact mechanism R-0.4 already uses to keep an Inspector mechanically
  distinct from the Worker it inspects.
"""

from __future__ import annotations

import contextlib
import json
import os
import tempfile
from dataclasses import asdict, dataclass, field, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from .ledger import DispatchIndependenceError, check_dispatch_independence
from .state._core import RENMARK_DIR_NAME

# ── Errors ──────────────────────────────────────────────────────────────────


class TaskTrackingError(RuntimeError):
    """Base error for this module — never raised by reads, only by writes
    that would otherwise silently violate an invariant (missing evidence,
    self-approval, unknown task, double-close).
    """


class UnknownTaskError(TaskTrackingError):
    """Raised when a lifecycle transition names a ``task_id`` that was never
    created (or was created then closed and is being addressed as if live).
    """


class MissingEvidenceError(TaskTrackingError):
    """Raised by :func:`complete_task` when no artifact path or result
    summary is supplied — a task cannot be marked ``completed`` on the
    strength of "the dispatch returned", only on the strength of recorded
    evidence (REQ-31).
    """


class SelfApprovalError(TaskTrackingError):
    """Raised by :func:`complete_worker_task` when the linked verification
    task is not provably independent of the worker task — re-exposes
    :class:`renmark.ledger.DispatchIndependenceError` under this module's own
    name so callers importing ``task_tracking`` don't need to know about
    ``ledger`` internals to catch it.
    """


class MissingVerificationError(TaskTrackingError):
    """Raised by :func:`complete_worker_task` when the named verification
    task does not exist or has not itself reached ``completed``.
    """


# ── Paths ───────────────────────────────────────────────────────────────────

TASKS_SUBDIR = "state"
TASKS_FILE = "tasks.json"

Status = Literal[
    "pending", "in_progress", "blocked", "failed", "completed", "deleted"
]

_TERMINAL_STATUSES: frozenset[str] = frozenset({"completed", "deleted"})


def tasks_dir(repo: Path | str) -> Path:
    return Path(repo) / RENMARK_DIR_NAME / TASKS_SUBDIR


def tasks_path(repo: Path | str) -> Path:
    """Return the path to ``.renmark/state/tasks.json``."""
    return tasks_dir(repo) / TASKS_FILE


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Data model ────────────────────────────────────────────────────────────


@dataclass
class TaskRecord:
    """One native task's current lifecycle state.

    ``history`` is a short, append-only log of dated one-line notes — the
    mechanism that satisfies "preserve the history of the decision" (REQ-31
    requirement 8) without a separate event-sourced ledger: every mutating
    call appends exactly one line here before returning. ``order_id`` is an
    optional dispatch-correlation field (alongside ``dispatch_identity``)
    that lets a caller tie this task record back to an external order/batch
    identifier.
    """

    task_id: str = ""
    title: str = ""
    role: str = ""
    scope: str = ""
    verification_expectation: str = ""
    status: Status = "pending"
    parent_id: str | None = None
    depends_on: tuple[str, ...] = ()
    dispatch_identity: str = ""
    order_id: str = ""
    verified_by: str | None = None
    blocker: str | None = None
    retry_count: int = 0
    artifact_path: str | None = None
    result_summary: str | None = None
    close_reason: str | None = None
    history: list[str] = field(default_factory=list)

    def _note(self, line: str) -> None:
        self.history.append(f"{_now_iso()} {line}")


# ── Persistence ───────────────────────────────────────────────────────────


def read_tasks(repo: Path | str) -> dict[str, TaskRecord]:
    """Read all task records. Never raises — a missing, unreadable, or
    corrupt file returns ``{}`` so a tracking-layer failure never blocks a
    real dispatch (REQ-30/REQ-31).
    """
    path = tasks_path(repo)
    if not path.exists():
        return {}
    try:
        raw = path.read_text(encoding="utf-8")
        payload = json.loads(raw)
    except (OSError, UnicodeDecodeError, ValueError):
        return {}
    if not isinstance(payload, dict):
        return {}
    out: dict[str, TaskRecord] = {}
    for task_id, fields in payload.items():
        if not isinstance(fields, dict):
            continue
        try:
            fields = dict(fields)
            fields["depends_on"] = tuple(fields.get("depends_on", ()))
            out[task_id] = TaskRecord(**fields)
        except TypeError:
            continue
    return out


def write_tasks(repo: Path | str, tasks: dict[str, TaskRecord]) -> Path:
    """Atomically persist all task records."""
    path = tasks_path(repo)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        task_id: {**asdict(rec), "depends_on": list(rec.depends_on)}
        for task_id, rec in tasks.items()
    }
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=path.name + ".tmp.")
    os.close(fd)
    tmp = Path(tmp_name)
    try:
        tmp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        os.replace(tmp, path)
    except OSError:
        with contextlib.suppress(OSError):
            tmp.unlink()
        raise
    return path


# ── Lifecycle ─────────────────────────────────────────────────────────────


def create_or_reuse_task(
    repo: Path | str,
    task_id: str,
    *,
    title: str,
    role: str,
    scope: str,
    verification_expectation: str,
    parent_id: str | None = None,
    depends_on: tuple[str, ...] = (),
    dispatch_identity: str = "",
    order_id: str = "",
) -> TaskRecord:
    """Create a task, or return the existing one unchanged (resume-reuse).

    Idempotent by design: a caller at a real dispatch site calls this
    unconditionally, every time, without checking "does this already
    exist?" first — a resumed run naturally reuses the prior record instead
    of recreating it, satisfying REQ-31's "reload and reuse existing tasks"
    rule without extra caller-side branching. ``order_id`` is recorded on
    the newly-created record only — like every other field, a resumed call
    with a different ``order_id`` does not overwrite an already-created
    record.
    """
    tasks = read_tasks(repo)
    existing = tasks.get(task_id)
    if existing is not None and existing.status != "deleted":
        return existing
    rec = TaskRecord(
        task_id=task_id,
        title=title,
        role=role,
        scope=scope,
        verification_expectation=verification_expectation,
        status="pending",
        parent_id=parent_id,
        depends_on=tuple(depends_on),
        dispatch_identity=dispatch_identity,
        order_id=order_id,
    )
    rec._note(f"created (role={role})")
    tasks[task_id] = rec
    write_tasks(repo, tasks)
    return rec


def _require_task(tasks: dict[str, TaskRecord], task_id: str) -> TaskRecord:
    rec = tasks.get(task_id)
    if rec is None:
        raise UnknownTaskError(f"no task tracked with task_id={task_id!r}")
    return rec


def mark_in_progress(repo: Path | str, task_id: str) -> TaskRecord:
    """Set ``in_progress`` immediately before dispatch — called only once
    per real dispatch attempt (a retry calls :func:`record_retry`, not this).
    """
    tasks = read_tasks(repo)
    rec = _require_task(tasks, task_id)
    rec = replace(rec, status="in_progress", history=list(rec.history))
    rec._note("in_progress (dispatched)")
    tasks[task_id] = rec
    write_tasks(repo, tasks)
    return rec


def record_blocker(repo: Path | str, task_id: str, blocker: str) -> TaskRecord:
    tasks = read_tasks(repo)
    rec = _require_task(tasks, task_id)
    rec = replace(rec, status="blocked", blocker=blocker, history=list(rec.history))
    rec._note(f"blocked: {blocker}")
    tasks[task_id] = rec
    write_tasks(repo, tasks)
    return rec


def record_retry(repo: Path | str, task_id: str, note: str = "") -> TaskRecord:
    """Record a retry on the SAME task — never a new task_id. Monotonic
    ``retry_count`` mirrors :mod:`renmark.recurrence`'s convention.
    """
    tasks = read_tasks(repo)
    rec = _require_task(tasks, task_id)
    rec = replace(
        rec,
        status="in_progress",
        retry_count=rec.retry_count + 1,
        blocker=None,
        history=list(rec.history),
    )
    suffix = f": {note}" if note else ""
    rec._note(f"retry #{rec.retry_count}{suffix}")
    tasks[task_id] = rec
    write_tasks(repo, tasks)
    return rec


def record_failure(repo: Path | str, task_id: str, reason: str) -> TaskRecord:
    tasks = read_tasks(repo)
    rec = _require_task(tasks, task_id)
    rec = replace(rec, status="failed", blocker=reason, history=list(rec.history))
    rec._note(f"failed: {reason}")
    tasks[task_id] = rec
    write_tasks(repo, tasks)
    return rec


def complete_task(
    repo: Path | str,
    task_id: str,
    *,
    artifact_path: str,
    result_summary: str,
) -> TaskRecord:
    """Mark ``completed`` — only when real evidence is supplied.

    Raises :class:`MissingEvidenceError` (never silently no-ops) if either
    ``artifact_path`` or ``result_summary`` is falsy. This is the mechanical
    form of REQ-31's "`completed` only when required output and evidence
    exist."
    """
    if not artifact_path or not result_summary:
        raise MissingEvidenceError(
            f"task {task_id!r} cannot be completed without both an "
            "artifact_path and a result_summary"
        )
    tasks = read_tasks(repo)
    rec = _require_task(tasks, task_id)
    rec = replace(
        rec,
        status="completed",
        artifact_path=artifact_path,
        result_summary=result_summary,
        blocker=None,
        history=list(rec.history),
    )
    rec._note(f"completed (artifact={artifact_path})")
    tasks[task_id] = rec
    write_tasks(repo, tasks)
    return rec


def complete_worker_task(
    repo: Path | str,
    worker_task_id: str,
    *,
    verification_task_id: str,
    artifact_path: str,
    result_summary: str,
) -> TaskRecord:
    """Complete a worker task whose completion requires independent
    verification — the no-self-approval enforcement point (REQ-31
    requirement 5).

    Raises :class:`MissingVerificationError` if the verification task does
    not exist or is not itself ``completed``. Raises
    :class:`SelfApprovalError` if the verification task's
    ``dispatch_identity`` is not provably independent of the worker task's
    (reusing :func:`renmark.ledger.check_dispatch_independence` — empty or
    matching identities are rejected, never assumed independent). Only after
    both checks pass does the worker task move to ``completed``, and its
    ``verified_by`` field records which task proved it.
    """
    tasks = read_tasks(repo)
    worker = _require_task(tasks, worker_task_id)
    verifier = tasks.get(verification_task_id)
    if verifier is None or verifier.status != "completed":
        raise MissingVerificationError(
            f"worker task {worker_task_id!r} cannot complete: verification "
            f"task {verification_task_id!r} is not completed"
        )
    try:
        check_dispatch_independence(
            repo, worker.dispatch_identity, verifier.dispatch_identity
        )
    except DispatchIndependenceError as exc:
        raise SelfApprovalError(
            f"worker task {worker_task_id!r} cannot self-approve via "
            f"verification task {verification_task_id!r}: {exc}"
        ) from exc
    if not artifact_path or not result_summary:
        raise MissingEvidenceError(
            f"task {worker_task_id!r} cannot be completed without both an "
            "artifact_path and a result_summary"
        )
    worker = replace(
        worker,
        status="completed",
        artifact_path=artifact_path,
        result_summary=result_summary,
        verified_by=verification_task_id,
        blocker=None,
        history=list(worker.history),
    )
    worker._note(f"completed (verified_by={verification_task_id})")
    tasks[worker_task_id] = worker
    write_tasks(repo, tasks)
    return worker


def close_task(repo: Path | str, task_id: str, *, reason: str) -> TaskRecord:
    """Close a task (scope change, superseded, cancelled) with a required
    reason recorded in its history BEFORE any replacement task is created —
    REQ-31 requirement 8. Never a silent disappearance.
    """
    if not reason:
        raise TaskTrackingError(f"close_task requires a reason for {task_id!r}")
    tasks = read_tasks(repo)
    rec = _require_task(tasks, task_id)
    rec = replace(rec, status="deleted", close_reason=reason, history=list(rec.history))
    rec._note(f"closed: {reason}")
    tasks[task_id] = rec
    write_tasks(repo, tasks)
    return rec


def should_skip_dispatch(repo: Path | str, task_id: str) -> bool:
    """True when ``task_id`` already reached a terminal, accepted status —
    the resume-reuse anti-re-dispatch check (REQ-31 requirement 7). A
    ``deleted`` (closed) task is NOT skip-worthy — closing a task explicitly
    means it needs a replacement, not that its slot is done.
    """
    tasks = read_tasks(repo)
    rec = tasks.get(task_id)
    return rec is not None and rec.status == "completed"


def parent_progress(repo: Path | str, parent_id: str) -> dict[str, int]:
    """Bounded milestone-progress summary for tasks under ``parent_id`` —
    what a task LIST view shows (counts by status), never full task bodies.
    """
    tasks = read_tasks(repo)
    counts: dict[str, int] = {}
    for rec in tasks.values():
        if rec.parent_id == parent_id:
            counts[rec.status] = counts.get(rec.status, 0) + 1
    return counts

"""Canonical ledger for the four core Renmark artifact kinds — Work Order,
Work Result, Inspection Report, Escalation (R-0.3, WP-1/WP-2/WP-3).

Today these four artifact kinds exist only as ad hoc free-form files (dispatch
prose, ``.renmark/reviews/*.json``, ``PAUSED``-file prose) with no shared
schema and no single append-only record. This module gives each kind a small
dataclass shape, a schema-validation function, and one append-only JSONL
ledger (``.renmark/ledger/events.jsonl``) so a session can reconstruct "what
was ordered, what came back, what was inspected, what was escalated" from one
stream.

Design mirrors :mod:`renmark.program` and :mod:`renmark.lifecycle`:

- Dataclasses are JSON-trivial (str/int/bool/list/dict/None only).
- No external ``jsonschema`` dependency — the project has none declared, so
  validation is explicit dataclass-field/type checking, same style as
  ``program.py``'s ``_str_field`` / ``_status_field`` helpers.
- **Fail loud on write.** :func:`append_ledger_event` raises
  :class:`LedgerValidationError` on a malformed event and writes NOTHING —
  no partial/corrupt line ever lands in ``events.jsonl`` (the contract's
  "Failure behavior": reject, don't silently corrupt).
- **Caller-supplied timestamps.** Every event carries a caller-supplied ISO8601
  ``ts`` string; this module never calls ``datetime.now()`` internally, so
  callers/tests control time and the module stays a pure writer/reader.
- **Reader degrades gracefully.** :func:`read_ledger_events` returns ``[]`` for
  a missing ledger file rather than raising — the ledger is additive/optional
  until WP-4 wires real emission call sites.

This module is schema + read/write primitives ONLY (WP-1/WP-2/WP-3). No
dispatch/review/pause call site is wired here — that is WP-4, a separate task.
``WorkOrder.is_repair`` / ``repairs_finding_ref`` and ``Escalation.is_replannable``
/ ``replan_evidence`` exist so the schema can represent a repair work order
(F2) and a ``ReplannableEscalation`` (F5) once a future caller constructs one;
neither is wired to any live caller here.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .state._core import RENMARK_DIR_NAME

# ── Errors ──────────────────────────────────────────────────────────────────


class LedgerValidationError(ValueError):
    """Raised when an event fails schema validation before it is written.

    Never write a partial/malformed line on this error — the caller's event is
    rejected in full; the ledger file is untouched.
    """


# ── Paths ───────────────────────────────────────────────────────────────────

LEDGER_SUBDIR = "ledger"
LEDGER_FILE = "events.jsonl"

KIND_WORK_ORDER = "work_order"
KIND_WORK_RESULT = "work_result"
KIND_INSPECTION_REPORT = "inspection_report"
KIND_ESCALATION = "escalation"

KINDS: tuple[str, ...] = (
    KIND_WORK_ORDER,
    KIND_WORK_RESULT,
    KIND_INSPECTION_REPORT,
    KIND_ESCALATION,
)


def ledger_dir(repo: Path | str) -> Path:
    """Return the (not-yet-created) ``.renmark/ledger/`` directory path."""
    return Path(repo) / RENMARK_DIR_NAME / LEDGER_SUBDIR


def ledger_path(repo: Path | str) -> Path:
    """Return the path to ``.renmark/ledger/events.jsonl``."""
    return ledger_dir(repo) / LEDGER_FILE


# ── Data model ────────────────────────────────────────────────────────────
#
# Each dataclass is JSON-trivial. ``kind`` is NOT stored on the dataclass
# itself (it's implied by the type / attached at write time) — this mirrors
# how program.py keeps its dataclasses free of persistence-envelope fields.


@dataclass
class WorkOrder:
    """A dispatch instruction — what a Worker is being asked to do.

    ``is_repair`` / ``repairs_finding_ref`` let this shape represent a repair
    work order (F2 — schema-ready, no wiring): a repair order's
    ``repairs_finding_ref`` names the review/verifier finding it addresses.
    """

    order_id: str = ""
    task: str = ""
    role: str = ""  # e.g. "code-implementer", "reviewer" — the dispatch role
    file_scope: list[str] = field(default_factory=list)
    verifier: str = ""
    is_repair: bool = False
    repairs_finding_ref: str | None = None


@dataclass
class WorkResult:
    """What a Worker returns for a given :class:`WorkOrder`."""

    order_id: str = ""
    status: str = ""  # e.g. "complete" | "partial" | "failed"
    summary: str = ""
    touched_files: list[str] = field(default_factory=list)
    artifact_refs: list[str] = field(default_factory=list)


@dataclass
class InspectionReport:
    """What a reviewer/verifier produces for a piece of work.

    Shape follows the fields already in live use across
    ``.renmark/reviews/*.json`` (verdict/findings/generator).
    """

    subject_ref: str = ""  # what was inspected (order_id, file, artifact path)
    verdict: str = ""  # e.g. "pass" | "fail" | "changes_requested"
    findings: list[str] = field(default_factory=list)
    generator: str = ""


@dataclass
class Escalation:
    """A blocker/pause/replan-worthy event.

    ``is_replannable`` / ``replan_evidence`` let this shape represent a
    ``ReplannableEscalation`` (F5 — schema-ready, no wiring): a replannable
    escalation's ``replan_evidence`` carries the evidence justifying a replan
    rather than a hard stop.
    """

    reason: str = ""
    originating_skill: str = ""
    blocking: bool = True
    is_replannable: bool = False
    replan_evidence: str | None = None


LedgerEvent = WorkOrder | WorkResult | InspectionReport | Escalation

_KIND_BY_TYPE: dict[type, str] = {
    WorkOrder: KIND_WORK_ORDER,
    WorkResult: KIND_WORK_RESULT,
    InspectionReport: KIND_INSPECTION_REPORT,
    Escalation: KIND_ESCALATION,
}


# ── Schema validation (no external jsonschema dependency) ───────────────────
#
# pyproject.toml declares no jsonschema dependency, so validation is explicit
# field/type checking — same style as program.py's _str_field/_status_field
# helpers, scaled down to "raise a list of issue strings" rather than
# raise-on-first-issue, so a caller can see every problem at once.


def _check_str(data: dict[str, Any], key: str, *, required: bool = True) -> list[str]:
    if key not in data:
        return [f"missing required field {key!r}"] if required else []
    value = data[key]
    if not isinstance(value, str):
        return [f"{key!r} must be a string, got {type(value).__name__}"]
    if required and not value.strip():
        return [f"{key!r} must not be empty"]
    return []


def _check_opt_str(data: dict[str, Any], key: str) -> list[str]:
    if key not in data or data[key] is None:
        return []
    if not isinstance(data[key], str):
        return [f"{key!r} must be a string or null, got {type(data[key]).__name__}"]
    return []


def _check_bool(data: dict[str, Any], key: str) -> list[str]:
    if key not in data:
        return []
    if not isinstance(data[key], bool):
        return [f"{key!r} must be a bool, got {type(data[key]).__name__}"]
    return []


def _check_str_list(data: dict[str, Any], key: str) -> list[str]:
    if key not in data:
        return []
    value = data[key]
    if not isinstance(value, list):
        return [f"{key!r} must be a list, got {type(value).__name__}"]
    for i, item in enumerate(value):
        if not isinstance(item, str):
            return [f"{key!r}[{i}] must be a string, got {type(item).__name__}"]
    return []


def validate_work_order(data: dict[str, Any]) -> list[str]:
    """Return a list of validation issues for a Work Order payload (empty = valid)."""
    issues: list[str] = []
    issues += _check_str(data, "order_id")
    issues += _check_str(data, "task")
    issues += _check_str(data, "role")
    issues += _check_str_list(data, "file_scope")
    issues += _check_str(data, "verifier", required=False)
    issues += _check_bool(data, "is_repair")
    issues += _check_opt_str(data, "repairs_finding_ref")
    return issues


def validate_work_result(data: dict[str, Any]) -> list[str]:
    """Return a list of validation issues for a Work Result payload (empty = valid)."""
    issues: list[str] = []
    issues += _check_str(data, "order_id")
    issues += _check_str(data, "status")
    issues += _check_str(data, "summary", required=False)
    issues += _check_str_list(data, "touched_files")
    issues += _check_str_list(data, "artifact_refs")
    return issues


def validate_inspection_report(data: dict[str, Any]) -> list[str]:
    """Return a list of validation issues for an Inspection Report payload (empty = valid)."""
    issues: list[str] = []
    issues += _check_str(data, "subject_ref")
    issues += _check_str(data, "verdict")
    issues += _check_str_list(data, "findings")
    issues += _check_str(data, "generator", required=False)
    return issues


def validate_escalation(data: dict[str, Any]) -> list[str]:
    """Return a list of validation issues for an Escalation payload (empty = valid)."""
    issues: list[str] = []
    issues += _check_str(data, "reason")
    issues += _check_str(data, "originating_skill", required=False)
    issues += _check_bool(data, "blocking")
    issues += _check_bool(data, "is_replannable")
    issues += _check_opt_str(data, "replan_evidence")
    return issues


_VALIDATOR_BY_KIND: dict[str, Any] = {
    KIND_WORK_ORDER: validate_work_order,
    KIND_WORK_RESULT: validate_work_result,
    KIND_INSPECTION_REPORT: validate_inspection_report,
    KIND_ESCALATION: validate_escalation,
}


def validate_event(kind: str, data: dict[str, Any]) -> list[str]:
    """Dispatch to the per-kind validator; unknown ``kind`` is itself an issue."""
    validator = _VALIDATOR_BY_KIND.get(kind)
    if validator is None:
        return [f"unknown ledger event kind {kind!r}; must be one of {KINDS}"]
    return validator(data)


# ── Writer (WP-2) ─────────────────────────────────────────────────────────


def append_ledger_event(repo: Path | str, event: LedgerEvent, *, ts: str) -> None:
    """Validate ``event`` and append one JSON line to ``.renmark/ledger/events.jsonl``.

    ``ts`` is a caller-supplied ISO8601 string — this function never calls
    ``datetime.now()``/``time.time()`` internally so callers/tests control
    time. On a schema validation failure this raises
    :class:`LedgerValidationError` and writes NOTHING (no partial/malformed
    line — validate-then-append, never append-then-validate).
    """
    kind = _KIND_BY_TYPE.get(type(event))
    if kind is None:
        raise LedgerValidationError(
            f"unsupported event type {type(event).__name__}; expected one of "
            "WorkOrder, WorkResult, InspectionReport, Escalation"
        )
    if not isinstance(ts, str) or not ts.strip():
        raise LedgerValidationError("ts must be a non-empty ISO8601 string")

    payload = asdict(event)
    issues = validate_event(kind, payload)
    if issues:
        raise LedgerValidationError(
            f"invalid {kind} event: {'; '.join(issues)}"
        )

    line: dict[str, Any] = {"kind": kind, "ts": ts, **payload}

    path = ledger_path(repo)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(line, sort_keys=False))
        fh.write("\n")


# ── Reader (WP-3) ─────────────────────────────────────────────────────────


def read_ledger_events(
    repo: Path | str,
    kind: str | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """Read ``.renmark/ledger/events.jsonl`` and return parsed events.

    Returns ``[]`` if the ledger file does not exist yet — this is a normal
    "nothing emitted so far" state, not an error. Malformed lines (bad JSON,
    non-object) are skipped rather than raising, so one corrupt line can never
    break `resume`-style consumption of the rest of the ledger.

    Events are returned in file order (oldest first, i.e. append order —
    most-recent-last). When ``kind`` is given, only events of that kind are
    returned. When ``limit`` is given, only the last N matching events are
    returned (still oldest-first within that tail).
    """
    path = ledger_path(repo)
    if not path.exists():
        return []

    events: list[dict[str, Any]] = []
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return []

    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            parsed = json.loads(line)
        except ValueError:
            continue
        if not isinstance(parsed, dict):
            continue
        if kind is not None and parsed.get("kind") != kind:
            continue
        events.append(parsed)

    if limit is not None and limit >= 0:
        events = events[-limit:] if limit > 0 else []

    return events


__all__ = [
    "KINDS",
    "KIND_ESCALATION",
    "KIND_INSPECTION_REPORT",
    "KIND_WORK_ORDER",
    "KIND_WORK_RESULT",
    "LEDGER_FILE",
    "LEDGER_SUBDIR",
    "Escalation",
    "InspectionReport",
    "LedgerEvent",
    "LedgerValidationError",
    "WorkOrder",
    "WorkResult",
    "append_ledger_event",
    "ledger_dir",
    "ledger_path",
    "read_ledger_events",
    "validate_escalation",
    "validate_event",
    "validate_inspection_report",
    "validate_work_order",
    "validate_work_result",
]

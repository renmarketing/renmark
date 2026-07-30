"""Delivery-run aggregate state persisted to ``.renmark/state/delivery.json``.

This module is stdlib-only and intentionally self-contained. It defines a
bounded runtime aggregate for the owner-facing delivery loop while preserving
legacy compatibility rules:

- Public ``delivery_mode`` is ONLY ``"agency"`` or ``"orchestrator"``.
- ``"conductor"`` is never a public delivery mode; a legacy ``"conductor"``
  token is tolerated ONLY as execution policy and normalised to ``"guided"``.
- Agency owns milestone selection but delegates milestone execution to
  Orchestrator. Callers should treat :func:`milestone_executor` as the single
  source of truth for that delegation.
- Reads never raise. A missing file returns the default state. Corruption also
  degrades to the default state, but callers can inspect the structured read
  report to surface what went wrong.
- Writes are atomic and strict. Oversize state raises
  :class:`DeliveryStateBloatError`; real IO failures propagate.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import tempfile
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal

SCHEMA_VERSION = 1
CONTRACT_VERSION = "delivery-state/v1"
DELIVERY_JSON_REL = ".renmark/state/delivery.json"
DELIVERY_JSON_BYTE_BUDGET = 4096
PROVENANCE_EVENT_CAP = 24
WORK_PACKAGE_CAP = 32
LEGACY_REF_CAP = 16
SUMMARY_TEXT_LIMIT = 160

DeliveryMode = Literal["agency", "orchestrator"]
ExecutionPolicy = Literal["guided", "direct", "async"]
StatusValue = Literal["unknown", "pending", "in_progress", "approved", "passed", "blocked", "failed"]
MilestoneExecution = Literal["orchestrator"]

_VALID_DELIVERY_MODES: frozenset[str] = frozenset({"agency", "orchestrator"})
_VALID_EXECUTION_POLICIES: frozenset[str] = frozenset({"guided", "direct", "async"})
_VALID_STATUSES: frozenset[str] = frozenset(
    {"unknown", "pending", "in_progress", "approved", "passed", "blocked", "failed"}
)
_VALID_MILESTONE_EXECUTION: frozenset[str] = frozenset({"orchestrator"})


class DeliveryStateBloatError(RuntimeError):
    """Raised when ``delivery.json`` would exceed its byte budget."""


@dataclass(frozen=True)
class DeliveryReadReport:
    """Outcome metadata for a delivery-state read."""

    state: str = "missing"  # missing | loaded | corrupt
    detail: str = ""
    path: str = ""

    @property
    def is_corrupt(self) -> bool:
        return self.state == "corrupt"


@dataclass
class DeliveryProvenanceEvent:
    """One bounded provenance record kept inline with the aggregate."""

    ts: str = ""
    kind: str = ""
    detail: str = ""
    source: str = ""
    ref: str = ""

    def normalized(self) -> DeliveryProvenanceEvent:
        return DeliveryProvenanceEvent(
            ts=_clean_text(self.ts, 48),
            kind=_clean_text(self.kind, 40),
            detail=_clean_text(self.detail, 120),
            source=_clean_text(self.source, 40),
            ref=_clean_text(self.ref, 72),
        )


@dataclass
class WorkPackageSummary:
    """Compact milestone child summary."""

    package_id: str = ""
    milestone_id: str = ""
    title: str = ""
    status: str = "pending"
    summary: str = ""
    owner: str = ""
    updated_at: str = ""
    artifact_ref: str = ""

    def normalized(self) -> WorkPackageSummary:
        status = self.status if self.status in _VALID_STATUSES else "pending"
        return WorkPackageSummary(
            package_id=stable_work_package_id(self.milestone_id, self.package_id or self.title),
            milestone_id=stable_milestone_id(self.milestone_id),
            title=_clean_text(self.title, 80),
            status=status,
            summary=_clean_text(self.summary, SUMMARY_TEXT_LIMIT),
            owner=_clean_text(self.owner, 40),
            updated_at=_clean_text(self.updated_at, 48),
            artifact_ref=_clean_text(self.artifact_ref, 96),
        )


@dataclass
class DeliveryState:
    """Persisted aggregate for one delivery run."""

    schema_version: int = SCHEMA_VERSION
    run_id: str = ""
    delivery_mode: str = "orchestrator"
    execution_policy: str = "guided"
    active_milestone_id: str = ""
    milestone_execution: str = "orchestrator"
    work_packages: list[WorkPackageSummary] = field(default_factory=list)
    approval_status: str = "unknown"
    review_status: str = "unknown"
    verification_status: str = "unknown"
    loop_status: str = "unknown"
    contract_version: str = CONTRACT_VERSION
    source_sha: str = ""
    provenance_events: list[DeliveryProvenanceEvent] = field(default_factory=list)
    legacy_refs: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        normalized = _normalized_state(self)
        self.schema_version = normalized.schema_version
        self.run_id = normalized.run_id
        self.delivery_mode = normalized.delivery_mode
        self.execution_policy = normalized.execution_policy
        self.active_milestone_id = normalized.active_milestone_id
        self.milestone_execution = normalized.milestone_execution
        self.work_packages = normalized.work_packages
        self.approval_status = normalized.approval_status
        self.review_status = normalized.review_status
        self.verification_status = normalized.verification_status
        self.loop_status = normalized.loop_status
        self.contract_version = normalized.contract_version
        self.source_sha = normalized.source_sha
        self.provenance_events = normalized.provenance_events
        self.legacy_refs = normalized.legacy_refs

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2) + "\n"


def delivery_state_path(repo: str | Path) -> Path:
    return Path(repo) / DELIVERY_JSON_REL


def default_delivery_state() -> DeliveryState:
    return DeliveryState()


def milestone_executor(state: DeliveryState | None = None) -> MilestoneExecution:
    """Agency delegates milestone execution to Orchestrator; this never varies."""
    del state
    return "orchestrator"


def stable_milestone_id(value: str) -> str:
    token = _slug(value)
    return token or "milestone"


def stable_work_package_id(milestone_id: str, value: str) -> str:
    milestone = stable_milestone_id(milestone_id)
    qualified_prefix = f"{milestone}--"
    raw_value = " ".join(value.split()).strip().lower()
    token = (
        _slug(raw_value[len(qualified_prefix) :])
        if raw_value.startswith(qualified_prefix)
        else _slug(value)
    )
    return f"{milestone}--{token or 'work-package'}"


def new_run_id() -> str:
    return f"delivery-{uuid.uuid4().hex[:12]}"


def stable_delivery_run_id(*identity_parts: object) -> str:
    """Derive a host-independent run ID from persisted legacy identity fields."""
    normalized = "\x1f".join(
        " ".join(str(part).split()) if part is not None else ""
        for part in identity_parts
    )
    digest = hashlib.sha256((normalized or "legacy-delivery-run").encode("utf-8")).hexdigest()
    return f"delivery-{digest[:12]}"


def read_delivery_state(repo: str | Path) -> DeliveryState:
    state, _report = read_delivery_state_with_report(repo)
    return state


def read_delivery_state_with_report(repo: str | Path) -> tuple[DeliveryState, DeliveryReadReport]:
    path = delivery_state_path(repo)
    if not path.exists():
        return default_delivery_state(), DeliveryReadReport(
            state="missing",
            path=str(path),
            detail="delivery state file is absent",
        )
    try:
        raw = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return default_delivery_state(), DeliveryReadReport(
            state="corrupt",
            path=str(path),
            detail=f"delivery state unreadable: {exc}",
        )
    try:
        payload = json.loads(raw)
    except ValueError as exc:
        return default_delivery_state(), DeliveryReadReport(
            state="corrupt",
            path=str(path),
            detail=f"delivery state invalid JSON: {exc}",
        )
    if not isinstance(payload, dict):
        return default_delivery_state(), DeliveryReadReport(
            state="corrupt",
            path=str(path),
            detail=f"delivery state must be a JSON object, got {type(payload).__name__}",
        )
    try:
        state = _state_from_dict(payload)
    except ValueError as exc:
        return default_delivery_state(), DeliveryReadReport(
            state="corrupt",
            path=str(path),
            detail=str(exc),
        )
    return state, DeliveryReadReport(state="loaded", path=str(path))


def write_delivery_state(repo: str | Path, state: DeliveryState) -> Path:
    normalized = _normalized_state(state)
    payload = normalized.to_json()
    size = len(payload.encode("utf-8"))
    if size > DELIVERY_JSON_BYTE_BUDGET:
        raise DeliveryStateBloatError(
            f"delivery.json would be {size} bytes; budget {DELIVERY_JSON_BYTE_BUDGET}"
        )
    path = delivery_state_path(repo)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=path.name + ".tmp.")
    os.close(fd)
    tmp = Path(tmp_name)
    try:
        tmp.write_text(payload, encoding="utf-8")
        os.replace(tmp, path)
    except OSError:
        with contextlib.suppress(OSError):
            tmp.unlink()
        raise
    return path


def bounded_work_package_summaries(
    state: DeliveryState,
    *,
    limit: int = 5,
) -> list[str]:
    cap = max(0, limit)
    lines: list[str] = []
    for item in state.work_packages[:cap]:
        line = f"{item.package_id}:{item.status}"
        if item.summary:
            line += f" {_clean_text(item.summary, 80)}"
        lines.append(line)
    return lines


def bounded_provenance_lines(
    state: DeliveryState,
    *,
    limit: int = 5,
) -> list[str]:
    cap = max(0, limit)
    lines: list[str] = []
    for event in state.provenance_events[:cap]:
        parts = [part for part in (event.ts, event.kind, event.detail) if part]
        lines.append(" | ".join(parts)[:120])
    return lines


def append_provenance_event(
    state: DeliveryState,
    *,
    ts: str,
    kind: str,
    detail: str = "",
    source: str = "",
    ref: str = "",
) -> DeliveryState:
    events = list(state.provenance_events)
    events.append(
        DeliveryProvenanceEvent(
            ts=ts,
            kind=kind,
            detail=detail,
            source=source,
            ref=ref,
        ).normalized()
    )
    state.provenance_events = events[-PROVENANCE_EVENT_CAP:]
    return _normalized_state(state)


def update_active_milestone(state: DeliveryState, milestone_id: str) -> DeliveryState:
    state.active_milestone_id = stable_milestone_id(milestone_id)
    return _normalized_state(state)


def upsert_work_package(state: DeliveryState, summary: WorkPackageSummary) -> DeliveryState:
    normalized = summary.normalized()
    packages = [item for item in state.work_packages if item.package_id != normalized.package_id]
    packages.append(normalized)
    state.work_packages = packages
    if normalized.milestone_id and not state.active_milestone_id:
        state.active_milestone_id = normalized.milestone_id
    return _normalized_state(state)


def _state_from_dict(data: dict[str, Any]) -> DeliveryState:
    schema_version = data.get("schema_version", SCHEMA_VERSION)
    if not isinstance(schema_version, int):
        raise ValueError("delivery state schema_version must be an int")

    work_packages_raw = data.get("work_packages", [])
    if work_packages_raw is None:
        work_packages_raw = []
    if not isinstance(work_packages_raw, list):
        raise ValueError("delivery state work_packages must be a list")
    work_packages: list[WorkPackageSummary] = []
    for item in work_packages_raw:
        if not isinstance(item, dict):
            raise ValueError("delivery state work package entries must be objects")
        work_packages.append(
            WorkPackageSummary(
                package_id=_expect_str(item, "package_id"),
                milestone_id=_expect_str(item, "milestone_id"),
                title=_expect_str(item, "title"),
                status=_expect_str(item, "status", "pending"),
                summary=_expect_str(item, "summary"),
                owner=_expect_str(item, "owner"),
                updated_at=_expect_str(item, "updated_at"),
                artifact_ref=_expect_str(item, "artifact_ref"),
            ).normalized()
        )

    events_raw = data.get("provenance_events", [])
    if events_raw is None:
        events_raw = []
    if not isinstance(events_raw, list):
        raise ValueError("delivery state provenance_events must be a list")
    events: list[DeliveryProvenanceEvent] = []
    for item in events_raw:
        if not isinstance(item, dict):
            raise ValueError("delivery state provenance event entries must be objects")
        events.append(
            DeliveryProvenanceEvent(
                ts=_expect_str(item, "ts"),
                kind=_expect_str(item, "kind"),
                detail=_expect_str(item, "detail"),
                source=_expect_str(item, "source"),
                ref=_expect_str(item, "ref"),
            ).normalized()
        )

    legacy_refs_raw = data.get("legacy_refs", [])
    if legacy_refs_raw is None:
        legacy_refs_raw = []
    if not isinstance(legacy_refs_raw, list):
        raise ValueError("delivery state legacy_refs must be a list")
    legacy_refs = [_coerce_legacy_ref(item) for item in legacy_refs_raw]

    state = DeliveryState(
        schema_version=schema_version,
        run_id=_expect_str(data, "run_id"),
        delivery_mode=_expect_str(data, "delivery_mode", "orchestrator"),
        execution_policy=_expect_str(data, "execution_policy", "guided"),
        active_milestone_id=_expect_str(data, "active_milestone_id"),
        milestone_execution=_expect_str(data, "milestone_execution", "orchestrator"),
        work_packages=work_packages,
        approval_status=_expect_str(data, "approval_status", "unknown"),
        review_status=_expect_str(data, "review_status", "unknown"),
        verification_status=_expect_str(data, "verification_status", "unknown"),
        loop_status=_expect_str(data, "loop_status", "unknown"),
        contract_version=_expect_str(data, "contract_version", CONTRACT_VERSION),
        source_sha=_expect_str(data, "source_sha"),
        provenance_events=events,
        legacy_refs=legacy_refs,
    )
    return _normalized_state(state)


def _normalized_state(state: DeliveryState) -> DeliveryState:
    delivery_mode = state.delivery_mode
    execution_policy = state.execution_policy

    if delivery_mode == "conductor":
        delivery_mode = "orchestrator"
    if delivery_mode not in _VALID_DELIVERY_MODES:
        delivery_mode = "orchestrator"

    if execution_policy == "conductor":
        execution_policy = "guided"
    if execution_policy not in _VALID_EXECUTION_POLICIES:
        execution_policy = "guided"

    active_milestone_id = stable_milestone_id(state.active_milestone_id)
    work_packages = [item.normalized() for item in state.work_packages[:WORK_PACKAGE_CAP]]
    if active_milestone_id == "milestone":
        for item in work_packages:
            if item.milestone_id and item.milestone_id != "milestone":
                active_milestone_id = item.milestone_id
                break

    return _build_state(
        schema_version=SCHEMA_VERSION,
        run_id=_normalize_run_id(state.run_id),
        delivery_mode=delivery_mode,
        execution_policy=execution_policy,
        active_milestone_id=active_milestone_id if active_milestone_id != "milestone" else "",
        milestone_execution="orchestrator",
        work_packages=work_packages,
        approval_status=_normalize_status(state.approval_status),
        review_status=_normalize_status(state.review_status),
        verification_status=_normalize_status(state.verification_status),
        loop_status=_normalize_status(state.loop_status),
        contract_version=CONTRACT_VERSION,
        source_sha=_clean_text(state.source_sha, 64),
        provenance_events=[
            item.normalized() for item in state.provenance_events[-PROVENANCE_EVENT_CAP:]
        ],
        legacy_refs=[_coerce_legacy_ref(item) for item in state.legacy_refs[-LEGACY_REF_CAP:]],
    )


def _build_state(
    *,
    schema_version: int,
    run_id: str,
    delivery_mode: str,
    execution_policy: str,
    active_milestone_id: str,
    milestone_execution: str,
    work_packages: list[WorkPackageSummary],
    approval_status: str,
    review_status: str,
    verification_status: str,
    loop_status: str,
    contract_version: str,
    source_sha: str,
    provenance_events: list[DeliveryProvenanceEvent],
    legacy_refs: list[str],
) -> DeliveryState:
    state = object.__new__(DeliveryState)
    state.schema_version = schema_version
    state.run_id = run_id
    state.delivery_mode = delivery_mode
    state.execution_policy = execution_policy
    state.active_milestone_id = active_milestone_id
    state.milestone_execution = milestone_execution
    state.work_packages = work_packages
    state.approval_status = approval_status
    state.review_status = review_status
    state.verification_status = verification_status
    state.loop_status = loop_status
    state.contract_version = contract_version
    state.source_sha = source_sha
    state.provenance_events = provenance_events
    state.legacy_refs = legacy_refs
    return state


def _normalize_status(value: str) -> str:
    cleaned = _clean_text(value, 24)
    if cleaned not in _VALID_STATUSES:
        return "unknown"
    return cleaned


def _normalize_run_id(value: str) -> str:
    cleaned = _clean_text(value, 48).lower()
    prefix = "delivery-"
    suffix = cleaned[len(prefix) :] if cleaned.startswith(prefix) else ""
    if len(suffix) == 12 and all(ch in "0123456789abcdef" for ch in suffix):
        return f"{prefix}{suffix}"
    return new_run_id()


def _expect_str(data: dict[str, Any], key: str, default: str = "") -> str:
    value = data.get(key, default)
    if value is None:
        return default
    if not isinstance(value, str):
        raise ValueError(f"delivery state {key} must be a string")
    return value


def _coerce_legacy_ref(value: object) -> str:
    if not isinstance(value, str):
        raise ValueError("delivery state legacy_refs entries must be strings")
    return _clean_text(value, 96)


def _clean_text(value: str, limit: int) -> str:
    compact = " ".join(value.split())
    return compact[:limit]


def _slug(value: str) -> str:
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

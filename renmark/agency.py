"""Lightweight, resumable Agency project state persisted to ``.renmark/state/agency.json``.

Agency Mode is the third delivery modality above Conductor/Orchestrator.  This
module persists its runtime state — active flag, current phase, milestone
tracking, signoff status, cost lane, and a roadmap reference — to a small JSON
file under ``.renmark/state/``.

Design constraints (mirroring :mod:`renmark.mode` and :mod:`renmark.lifecycle`):
- stdlib json only (no third-party deps).
- Reads NEVER raise — a missing, unreadable, or corrupt file always returns the
  default inactive state so callers can safely call ``is_active`` without
  guarding against exceptions.
- Writes ARE NOT swallowed: an oversize file raises :class:`AgencyBloatError`
  so callers never report success on a persistence that did not happen.  The
  write is atomic — a temp file in the same ``.renmark/state`` dir is
  ``os.replace``d into place so a concurrent reader never sees a partial write.
- :data:`AGENCY_JSON_BYTE_BUDGET` mirrors ``LIFECYCLE_JSON_BYTE_BUDGET`` from
  :mod:`renmark.lifecycle` (both 1 KB).  Exceeding the budget means runtime
  cruft has leaked in — move it to ``pipeline.json``.
"""

from __future__ import annotations

import contextlib
import json
import os
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path

from renmark.delivery_state import (
    DeliveryState,
    WorkPackageSummary,
    append_provenance_event,
    default_delivery_state,
    read_delivery_state,
    update_active_milestone,
    write_delivery_state,
)

# ── Budget / error ────────────────────────────────────────────────────────────

AGENCY_JSON_BYTE_BUDGET: int = 1024  # 1 KB — exceeding this is a bug


class AgencyBloatError(RuntimeError):
    """Raised when the serialised agency.json would exceed the byte budget.

    Mirrors :class:`renmark.lifecycle.LifecycleBloatError`.
    """


# ── Path helper ───────────────────────────────────────────────────────────────

_AGENCY_REL = ".renmark/state/agency.json"


def agency_state_path(repo: str | Path) -> Path:
    """Return the absolute path where agency state is persisted.

    This is the single source of truth for the agency-state location
    (``<repo>/.renmark/state/agency.json``).  User-facing strings MUST derive
    their path text from here so they can never drift from the actual write
    location.

    Note: the parent directory is NOT created here — only :func:`write_agency`
    does that, on first write.
    """
    return Path(repo) / _AGENCY_REL


# ── Schema (dataclass) ────────────────────────────────────────────────────────

@dataclass
class AgencyState:
    """Minimal runtime state for an active Agency Mode workflow.

    All string fields default to ``""`` so the JSON remains small even when
    most fields are unused.  ``active`` defaults to ``False`` — the initial
    state is always inactive.
    """

    active: bool = False
    current_phase: str = ""
    current_milestone: str = ""
    next_checkpoint: str = ""
    signoff_status: str = ""
    cost_lane: str = ""
    roadmap_ref: str = ""

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2) + "\n"


# ── Field type registry (used for safe read deserialisation) ──────────────────

_AGENCY_FIELD_TYPES: dict[str, type] = {
    "active": bool,
    "current_phase": str,
    "current_milestone": str,
    "next_checkpoint": str,
    "signoff_status": str,
    "cost_lane": str,
    "roadmap_ref": str,
}

# ── Read ──────────────────────────────────────────────────────────────────────


def read_agency(repo: str | Path) -> AgencyState:
    """Return the persisted :class:`AgencyState` for the project at *repo*.

    Returns the default inactive state (``active=False``, all strings ``""``)
    when the file is MISSING or CORRUPT (bad JSON, wrong type) — NEVER raises
    into a caller.
    """
    try:
        text = agency_state_path(repo).read_text(encoding="utf-8")
        data = json.loads(text)
    except Exception:
        return AgencyState()

    if not isinstance(data, dict):
        return AgencyState()

    # Accept only recognised fields with the right type — ignore extras to
    # survive schema drift without crashing.
    filtered: dict[str, object] = {
        k: v
        for k, v in data.items()
        if k in _AGENCY_FIELD_TYPES and isinstance(v, _AGENCY_FIELD_TYPES[k])
    }
    return AgencyState(**filtered)  # type: ignore[arg-type]


# ── Write ─────────────────────────────────────────────────────────────────────


def write_agency(repo: str | Path, state: AgencyState) -> None:
    """Atomically persist *state* to ``.renmark/state/agency.json``.

    Creates ``.renmark/state/`` if missing.  Raises :class:`AgencyBloatError`
    when the serialised JSON exceeds :data:`AGENCY_JSON_BYTE_BUDGET` — runtime
    cruft has leaked in.  A genuine write failure (read-only FS, ENOSPC,
    permission denied) is NOT swallowed; it propagates as :class:`OSError` so
    callers never report success on a persistence that did not happen.

    The write is atomic: a temp file in the same ``.renmark/state`` directory is
    ``os.replace``d into place so a concurrent reader never observes a
    partially-written file.
    """
    payload = state.to_json()
    if len(payload.encode("utf-8")) > AGENCY_JSON_BYTE_BUDGET:
        raise AgencyBloatError(
            f"agency.json would be {len(payload.encode('utf-8'))} bytes; "
            f"budget {AGENCY_JSON_BYTE_BUDGET}. "
            "Runtime cruft has leaked in — move it to pipeline.json."
        )

    p = agency_state_path(repo)
    p.parent.mkdir(parents=True, exist_ok=True)
    # Unique temp file in the SAME dir (so os.replace is atomic) — a bare
    # pid-derived name would let two same-process writers clobber each other's
    # temp. mkstemp guarantees a unique path per call.
    fd, tmp_name = tempfile.mkstemp(dir=p.parent, prefix=p.name + ".tmp.")
    os.close(fd)
    tmp = Path(tmp_name)
    try:
        tmp.write_text(payload, encoding="utf-8")
        os.replace(tmp, p)
    except OSError:
        with contextlib.suppress(OSError):
            tmp.unlink()
        raise


# ── Convenience helpers ───────────────────────────────────────────────────────


def is_active(repo: str | Path) -> bool:
    """Return ``True`` when Agency Mode is currently active for *repo*.

    Convenience wrapper over :func:`read_agency` — never raises.
    """
    return read_agency(repo).active


def activate(repo: str | Path, **fields: str) -> AgencyState:
    """Set ``active=True``, optionally updating other string fields, and persist.

    Keyword arguments map to :class:`AgencyState` string fields:
    ``current_phase``, ``current_milestone``, ``next_checkpoint``,
    ``signoff_status``, ``cost_lane``, ``roadmap_ref``.  Unknown keys are
    silently ignored to allow forward-compatible callers.

    Returns the updated :class:`AgencyState`.
    Raises :class:`AgencyBloatError` or :class:`OSError` on write failure.
    """
    state = read_agency(repo)
    state.active = True
    _string_fields = {
        "current_phase",
        "current_milestone",
        "next_checkpoint",
        "signoff_status",
        "cost_lane",
        "roadmap_ref",
    }
    for key, value in fields.items():
        if key in _string_fields:
            setattr(state, key, value)
    write_agency(repo, state)
    if _map_status(fields.get("signoff_status", "")) == "approved":
        approve_milestone_for_orchestrator(repo)
    return state


def deactivate(repo: str | Path) -> AgencyState:
    """Set ``active=False`` and persist, preserving all other fields.

    Returns the updated :class:`AgencyState`.
    Raises :class:`AgencyBloatError` or :class:`OSError` on write failure.
    """
    state = read_agency(repo)
    state.active = False
    write_agency(repo, state)
    return state


def approve_milestone_for_orchestrator(repo: str | Path) -> DeliveryState:
    """Persist an owner-approved Agency milestone for Orchestrator execution.

    Agency remains the owner-facing discovery and approval surface.  Once its
    persisted signoff is explicitly ``approved``, this transition writes the
    canonical delivery aggregate whose fixed ``milestone_execution`` contract
    assigns the selected milestone to Orchestrator.  It never fabricates an
    approval: inactive Agency state, or any status other than ``approved``, is
    rejected before the delivery state is written.
    """
    state = read_agency(repo)
    if not state.active:
        raise ValueError("an active Agency milestone is required before handoff")
    if _map_status(state.signoff_status) != "approved":
        raise ValueError("owner approval is required before Orchestrator handoff")

    milestone = _clean_text(state.current_milestone) or _clean_text(state.current_phase)
    if not milestone:
        raise ValueError("an Agency milestone is required before Orchestrator handoff")

    # Preserve the active aggregate so an Agency approval does not discard the
    # run, work-package, verification, review, or provenance state already
    # produced for this delivery boundary.
    delivery = read_delivery_state(repo)
    delivery.delivery_mode = "agency"
    delivery.execution_policy = "guided"
    delivery.approval_status = "approved"
    delivery.loop_status = "in_progress"
    delivery = update_active_milestone(delivery, milestone)
    delivery = append_provenance_event(
        delivery,
        ts="",
        kind="agency-approved-handoff",
        detail="owner-approved milestone delegated to Orchestrator",
        source="agency",
        ref="agency.json",
    )
    write_delivery_state(repo, delivery)
    return read_delivery_state(repo)


def project_agency_state(state: AgencyState) -> DeliveryState:
    """Project legacy agency runtime state into the canonical delivery aggregate.

    This is a compatibility adapter only: it does NOT alter the persisted
    :class:`AgencyState` schema or storage format.
    """
    delivery = default_delivery_state()
    if not state.active:
        return delivery

    phase = _clean_text(state.current_phase)
    milestone = _clean_text(state.current_milestone)
    checkpoint = _clean_text(state.next_checkpoint)
    signoff = _map_status(state.signoff_status)

    provenance_details: list[str] = []
    if not phase and not milestone:
        phase = "discovery"
        milestone = "discovery"
    else:
        if not phase:
            phase = milestone or "discovery"
            provenance_details.append(
                "active agency state missing current_phase; projected milestone as phase"
            )
        if not milestone:
            milestone = phase or "discovery"
            provenance_details.append(
                "active agency state missing current_milestone; projected phase as milestone"
            )

    work_packages: list[WorkPackageSummary] = []
    if checkpoint:
        work_packages.append(
            WorkPackageSummary(
                milestone_id=milestone,
                title=checkpoint,
                status="pending",
                summary=phase,
                owner="agency",
                artifact_ref=_clean_text(state.roadmap_ref, limit=96),
            )
        )

    legacy_refs = [
        ref
        for ref in (
            _legacy_ref("agency_phase", phase),
            _legacy_ref("agency_milestone", milestone),
            _legacy_ref("agency_checkpoint", checkpoint),
            _legacy_ref("agency_cost_lane", state.cost_lane),
            _legacy_ref("agency_roadmap_ref", state.roadmap_ref),
        )
        if ref
    ]

    delivery = DeliveryState(
        delivery_mode="agency",
        execution_policy="guided",
        active_milestone_id=milestone,
        work_packages=work_packages,
        approval_status=signoff,
        review_status=signoff,
        verification_status="unknown",
        loop_status="in_progress",
        legacy_refs=legacy_refs,
    )

    for detail in provenance_details[:1]:
        delivery = append_provenance_event(
            delivery,
            ts="",
            kind="compat-drift-repair",
            detail=detail,
            source="agency",
            ref="agency.json",
        )
    return delivery


def project_current_agency(repo: str | Path) -> DeliveryState:
    """Project the current persisted agency runtime state into delivery state."""
    return project_agency_state(read_agency(repo))


def agency_to_delivery_state(state: AgencyState) -> DeliveryState:
    """Compatibility alias for projecting an :class:`AgencyState`."""
    return project_agency_state(state)


def current_agency_to_delivery_state(repo: str | Path) -> DeliveryState:
    """Compatibility alias for projecting persisted agency state."""
    return project_current_agency(repo)


def _map_status(value: str) -> str:
    normalized = _clean_text(value, limit=24)
    if normalized in {"unknown", "pending", "in_progress", "approved", "passed", "blocked", "failed"}:
        return normalized
    return "unknown"


def _legacy_ref(label: str, value: str) -> str:
    cleaned = _clean_text(value, limit=80)
    if not cleaned:
        return ""
    return _clean_text(f"{label}:{cleaned}", limit=96)


def _clean_text(value: str, *, limit: int = 48) -> str:
    return " ".join(value.split())[:limit]

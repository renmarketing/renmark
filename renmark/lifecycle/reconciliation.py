"""Cross-store reconciliation for renmark lifecycle state.

Split out of ``renmark/lifecycle/stage.py`` per
`.renmark/rethink/renmark-architecture/target-blueprint.md` §1.2. Behavior is
unchanged — these are the same functions, relocated verbatim.

This module is the deliberately-isolated home for **read-only cross-store
reconciliation**: the logic that compares lifecycle state, agency state,
program state, pipeline state, and delivery state against one another and
reports readiness or drift. It is the repeat-offender staleness hotspot
(3+ documented CHANGELOG bugs across R-0.1/R-0.2/R-0.3), so it lives in one
focused file rather than buried in the much larger stage module.

Nothing here writes state: no lifecycle write, no delivery write, no repair
artifact. Readiness predicates cannot clear approval gates or advance stages,
and the legacy projection degrades to defaults plus bounded drift notes rather
than mutating anything it read.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from ..agency import AgencyState, project_agency_state, read_agency
from ..delivery_state import (
    DeliveryState,
    append_provenance_event,
    default_delivery_state,
    read_delivery_state_with_report,
)
from ..program import Program, delivery_state_for_program_status, stable_milestone_id_for_stage
from ..state.pipeline import PipelineState, read_pipeline_state
from .stage import (
    _LIFECYCLE_MILESTONE_BY_STAGE,
    LegacyDeliverySummary,
    LifecycleState,
    MilestoneReadiness,
    _agency_milestone,
    _current_head_sha,
    _current_program_stage,
    _has_fresh_milestone_evidence,
    _legacy_delivery_run_id,
    _lifecycle_milestone,
    _normalize_mode_note,
    _program_milestone,
    _read_raw_mode_token,
    _safe_read_program,
    _signoff_milestone_id,
    _work_package_summaries_for_stage,
    read_lifecycle,
)


def milestone_signoff_readiness(
    repo: Path | str,
    *,
    agency: bool | None = None,
    require_review: bool | None = None,
    milestone_id: str | None = None,
) -> MilestoneReadiness:
    """Return whether a milestone has the fresh evidence needed to advance.

    Agency delivery always requires a fresh, clean verifier result and an
    independently-produced clean review. Direct Orchestrator delivery still
    requires fresh verification, while review is proportional unless explicitly
    requested by its caller. The predicate is read-only: it cannot clear
    approval gates or advance lifecycle state.
    """
    repo_path = Path(repo)
    agency_state: AgencyState | None = None
    try:
        agency_state = read_agency(repo_path)
    except Exception:
        # A corrupt or unreadable Agency overlay must never create a boundary
        # binding from guessed state.
        agency_state = None
    if agency is None:
        agency = bool(agency_state and agency_state.active)
    review_required = bool(agency) if require_review is None else bool(require_review)

    # A persisted delivery loop is authoritative while it is active.  A loaded
    # non-passing loop must finish before signoff; an unavailable loop defers
    # to the active Agency boundary when one is persisted.
    try:
        delivery, delivery_report = read_delivery_state_with_report(repo_path)
    except Exception:
        delivery = None
        delivery_report = None

    # Evidence must be tied to the actual boundary when one is known.  The
    # optional argument supports callers that are signing off a named milestone;
    # otherwise the active persisted delivery milestone is authoritative.  An
    # unscoped legacy flow deliberately retains its existing HEAD-only behavior.
    active_milestone = _signoff_milestone_id(milestone_id)
    if not active_milestone and delivery is not None:
        active_milestone = _signoff_milestone_id(delivery.active_milestone_id)
    if not active_milestone and agency and agency_state is not None and agency_state.active:
        # A missing, corrupt, unreadable, or unscoped delivery loop cannot be
        # allowed to unbind an active Agency boundary. Preserve explicit caller
        # and usable delivery-loop precedence above, then use the persisted
        # Agency milestone so only evidence for that boundary can satisfy
        # signoff.
        active_milestone = _signoff_milestone_id(agency_state.current_milestone)

    head = _current_head_sha(repo_path)
    verification_ready = _has_fresh_milestone_evidence(
        repo_path,
        head,
        pattern="*.qa.md",
        verifier=True,
        milestone_id=active_milestone,
    )
    review_ready = _has_fresh_milestone_evidence(
        repo_path,
        head,
        pattern="*.review.md",
        verifier=False,
        milestone_id=active_milestone,
    )

    blockers: list[str] = []
    if not head:
        blockers.append("current revision is unavailable; freshness cannot be proven")
    if not verification_ready:
        blockers.append("fresh verified milestone evidence is required")
    if review_required and not review_ready:
        blockers.append("fresh clean independent review evidence is required")
    if (
        delivery_report is not None
        and delivery_report.state == "loaded"
        and delivery is not None
        and delivery.loop_status != "passed"
    ):
        blockers.append(f"delivery loop is unresolved ({delivery.loop_status})")

    return MilestoneReadiness(
        ready=not blockers,
        verification_ready=verification_ready,
        review_ready=review_ready,
        review_required=review_required,
        blockers=tuple(blockers),
    )


def read_legacy_delivery_summary(repo: Path | str) -> LegacyDeliverySummary:
    """Read legacy workflow state and project it into a canonical delivery summary.

    This helper is read-only and additive: it never writes delivery state,
    lifecycle state, or any repair artifact. It tolerates legacy/corrupt reads
    by degrading to the default delivery summary plus bounded drift notes.
    """
    repo_path = Path(repo)
    notes: list[str] = []

    lifecycle_state = read_lifecycle(repo_path)
    agency_state = read_agency(repo_path)
    pipeline_state = read_pipeline_state(repo_path)
    program_state = _safe_read_program(repo_path, notes)

    delivery = (
        project_agency_state(agency_state)
        if agency_state.active
        else _project_workflow_delivery(lifecycle_state, program_state, pipeline_state)
    )
    delivery = replace(
        delivery,
        run_id=_legacy_delivery_run_id(
            repo_path,
            lifecycle_state=lifecycle_state,
            agency_state=agency_state,
            program_state=program_state,
        ),
    )

    raw_mode_token = _read_raw_mode_token(repo_path)
    mode_note, execution_policy = _normalize_mode_note(raw_mode_token)
    if mode_note:
        notes.append(mode_note)
    if execution_policy:
        delivery = replace(delivery, execution_policy=execution_policy)

    notes.extend(
        _workflow_drift_notes(
            lifecycle_state=lifecycle_state,
            agency_state=agency_state,
            program_state=program_state,
            pipeline_state=pipeline_state,
        )
    )
    bounded_notes = notes[:5]
    for detail in bounded_notes[:3]:
        delivery = append_provenance_event(
            delivery,
            ts="",
            kind="compat-drift-repair",
            detail=detail,
            source="lifecycle",
            ref="legacy-workflow-state",
        )
    return LegacyDeliverySummary(delivery=delivery, drift_repair_notes=bounded_notes)


# Back-compat aliases for callers/tests that prefer a function-style name.
legacy_delivery_summary = read_legacy_delivery_summary
read_delivery_summary_from_legacy_state = read_legacy_delivery_summary


def _project_workflow_delivery(
    lifecycle_state: LifecycleState | None,
    program_state: Program | None,
    pipeline_state: PipelineState | None,
) -> DeliveryState:
    delivery = default_delivery_state()
    delivery.delivery_mode = "orchestrator"

    current_program_stage = _current_program_stage(program_state)
    if current_program_stage is not None:
        delivery.active_milestone_id = stable_milestone_id_for_stage(current_program_stage)
        delivery.work_packages = _work_package_summaries_for_stage(current_program_stage)
        delivery.loop_status = delivery_state_for_program_status(current_program_stage.status)

    if lifecycle_state is not None:
        lifecycle_milestone = _LIFECYCLE_MILESTONE_BY_STAGE.get(lifecycle_state.stage, "")
        if lifecycle_milestone and not delivery.active_milestone_id:
            delivery.active_milestone_id = lifecycle_milestone
        if lifecycle_state.stage in {"verified", "reviewed", "documented", "ready-to-release", "released"}:
            delivery.verification_status = "passed"
        if lifecycle_state.stage in {"reviewed", "documented", "ready-to-release", "released"}:
            delivery.review_status = "passed"
        if lifecycle_state.stage in {"ready-to-release", "released"}:
            delivery.approval_status = "approved"
        if lifecycle_state.stage == "released":
            delivery.loop_status = "passed"

    if pipeline_state is not None and pipeline_state.current_phase in {"orchestrate", "paused"}:
        delivery.loop_status = "in_progress"

    return replace(delivery)


def _workflow_drift_notes(
    *,
    lifecycle_state: LifecycleState | None,
    agency_state: AgencyState,
    program_state: Program | None,
    pipeline_state: PipelineState | None,
) -> list[str]:
    notes: list[str] = []

    if agency_state.active and not " ".join(agency_state.current_phase.split()):
        projected = " ".join(agency_state.current_milestone.split()) or "discovery"
        notes.append(
            f"agency repair: active agency had empty current_phase; projected {projected!r} as phase"
        )

    lifecycle_milestone = _lifecycle_milestone(lifecycle_state)
    program_milestone = _program_milestone(program_state)
    agency_milestone = _agency_milestone(agency_state)

    active_markers = [
        marker
        for marker in (
            f"agency:{agency_milestone}" if agency_state.active else "",
            f"lifecycle:{lifecycle_milestone}" if lifecycle_milestone else "",
            f"program:{program_milestone}" if program_milestone else "",
        )
        if marker
    ]
    distinct_active = {marker.split(":", 1)[1] for marker in active_markers}
    if len(active_markers) > 1 and len(distinct_active) > 1:
        notes.append(
            f"contradictory active states: {', '.join(active_markers[:3])}"
        )

    if lifecycle_milestone and program_milestone and lifecycle_milestone != program_milestone:
        lifecycle_stage = lifecycle_state.stage if lifecycle_state is not None else "unknown"
        program_stage = _current_program_stage(program_state)
        program_stage_id = program_stage.id if program_stage is not None else "unknown"
        notes.append(
            "lifecycle/program drift: "
            f"lifecycle stage {lifecycle_stage!r}->{lifecycle_milestone}, "
            f"program stage {program_stage_id!r}->{program_milestone}"
        )

    if (
        pipeline_state is not None
        and pipeline_state.current_phase in {"orchestrate", "paused"}
        and lifecycle_state is not None
        and lifecycle_state.stage in {"init", "brainstorm-complete", "plan-drafted", "plan-validated"}
    ):
        notes.append(
            "runtime/workflow drift: "
            f"pipeline phase {pipeline_state.current_phase!r} active while lifecycle stage is {lifecycle_state.stage!r}"
        )

    return notes[:5]

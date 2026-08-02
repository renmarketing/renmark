"""Lifecycle state for renmark features — enforces G12 (lifecycle persistence)
and the canonical multi-stage workflow: Brainstorm → Plan → Create → Test →
Review → Document → Release.

Lifecycle state lives in ``.renmark/state/lifecycle.json``. It is the source
of truth for cold-start recovery: any session can read this file after
``/clear`` and know exactly where the in-flight feature is.

Strict separation from ``pipeline.json``:
- lifecycle.json carries WORKFLOW state (feature, stage, artifacts, approval).
- pipeline.json carries RUNTIME state (wave indices, retry counts, subprocess).

If lifecycle.json exceeds ~1KB it's a bug — runtime cruft has leaked in.

``next_steps()`` is the contract helper for
``plugin/skills/.shared/next-steps.md`` — the single source of truth for the
"what should the user do next?" hand-off rule across every renmark skill.
"""

from __future__ import annotations

import contextlib
import json
import os
import subprocess
from dataclasses import asdict, dataclass, field, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import skillmeta
from .agency import AgencyState, project_agency_state, read_agency
from .delivery_state import (
    DeliveryState,
    WorkPackageSummary,
    append_provenance_event,
    default_delivery_state,
    read_delivery_state_with_report,
    stable_delivery_run_id,
    stable_milestone_id,
)
from .hosts import HostKind, capabilities_for
from .mode import mode_state_path
from .program import (
    Program,
    ProgramStateError,
    StageNode,
    delivery_state_for_program_status,
    program_delivery_milestones,
    read_program,
    stable_milestone_id_for_stage,
    stable_work_package_id_for_task,
)
from .state.pipeline import PipelineState, read_pipeline_state
from .summary import is_stale, read_metadata

# ── Stage taxonomy ────────────────────────────────────────────────────────────

# Canonical stages in order. Skills update lifecycle.json with one of these.
STAGES: list[str] = [
    "init",  # lifecycle created, no work yet
    "brainstorm-complete",  # spec written
    "plan-drafted",  # plan written, not yet validated
    "plan-validated",  # check-plan PASS
    "created",  # orchestrate complete
    "verified",  # verify PASS
    "reviewed",  # codereview + (optional) secure complete
    "documented",  # document complete
    "ready-to-release",  # finish flipped the marker
    "released",  # release tagged + zip built
]

# Skills that actually have a `plugin/skills/<name>/SKILL.md`. Stages that
# point at anything outside this set are routed through a manual-hint fallback
# in `next_recommended()` — vibe coders never get sent to a non-existent skill.
IMPLEMENTED_SKILLS: frozenset[str] = frozenset(
    {
        "analytics",
        "approve",
        "audit",
        "backlog",
        "blueprint",
        "brainstorm",
        "check-plan",
        "codereview",
        "debug",
        "doctor",
        "eval",
        "feature",
        "finish",
        "guide",
        "heartbeat",
        "help",
        "hygiene",
        "init",
        "inventory",
        "loop",
        "orchestrate",
        "plan",
        "prd",
        "resume",
        "rethink",
        "roadmap",
        "scan",
        "setup",
        "start",
        "usage",
        "verify",
    }
)

# Stage transitions — the router uses this to compute next_recommended.
# `reviewed` and `released` are real stages whose SKILL writers land alongside
# this release: codereview marks `reviewed` (→ finish), finish marks `released`
# (terminal). `documented` is dormant — no skill writes it, but it routes
# sensibly through finish if a legacy file carries it. `ready-to-release` has no
# shipped release skill yet, so it surfaces a manual tag/zip hint.
NEXT_BY_STAGE: dict[str, str] = {
    "init": "/renmark:brainstorm",
    "brainstorm-complete": "/renmark:plan",
    "plan-drafted": "/renmark:check-plan",
    "plan-validated": "/renmark:orchestrate",
    "created": "/renmark:verify",
    "verified": "/renmark:codereview",
    # codereview marks `reviewed`; the natural next step is closing the branch.
    "reviewed": "/renmark:finish",
    # `documented` is dormant (no writer) — route through finish if it appears.
    "documented": "/renmark:finish",
    # `release` skill is not implemented yet — finish marks ready-to-release;
    # actual release is a manual `git tag` + `bash install.sh` zip step.
    "ready-to-release": "(manual: tag the release and build the zip; see README § Release)",
    "released": "(feature complete — start a new one with /renmark:start)",
}

# Domain classification for context-contamination detection (G4).
# Back-compat alias DERIVED from the skillmeta registry — `skillmeta.SKILLS`
# is the single source of truth for per-skill domains (P7). Existing importers
# (`audit.py`, tests) and `monkeypatch.setattr` on this attribute keep working.
DOMAIN_BY_SKILL: dict[str, str] = {
    name: meta.domain for name, meta in skillmeta.SKILLS.items()
}

# Preamble tier — controls how much boilerplate skill_preamble injects.
# "minimal" → record invocation only; no budget check, no fragments (zero LLM
#             context overhead; safe for meta/zero-LLM skills).
# "standard" → budget check + cross-domain hint; NO fable synthesis hint.
# "full" (default, not listed) → budget check + cross-domain hint + fable hint.
PREAMBLE_TIER_BY_SKILL: dict[str, str] = {
    # minimal — meta/zero-LLM skills
    "resume": "minimal",
    "help": "minimal",
    "guide": "minimal",
    "doctor": "minimal",
    "usage": "minimal",
    "analytics": "minimal",
    "approve": "minimal",
    "hygiene": "minimal",
    "check-plan": "minimal",
    # standard — audit-domain skills: budget check but no fable hint
    "audit": "standard",
    "scan": "standard",
    "inventory": "standard",
}

# ── Skill classes (next-steps.md contract) ────────────────────────────────────
#
# Three classes from plugin/skills/.shared/next-steps.md. The class decides what
# `next_steps()` surfaces. Mirror the DOMAIN_BY_SKILL style — module-level
# frozensets, names aligned with the contract.

# Class 1 — pipeline skills: Tier-0 stage routing (advance the lifecycle).
PIPELINE_SKILLS: frozenset[str] = frozenset(
    {
        "start",
        "rethink",
        "brainstorm",
        "plan",
        "check-plan",
        "orchestrate",
        "finish",
        "feature",
        "prd",
        "blueprint",
        "loop",
    }
)

# Class 2 — quality gates: defer to handoff-menu.md's gate sub-menu.
GATE_SKILLS: frozenset[str] = frozenset(
    {
        "verify",
        "codereview",
    }
)

# Class 3 — aux / terminal skills: resume-pipeline + 1–2 local actions.
AUX_SKILLS: frozenset[str] = frozenset(
    {
        "debug",
        "eval",
        "doctor",
        "hygiene",
        "roadmap",
        "init",
        "setup",
        "help",
        "guide",
        "resume",
        "backlog",
        "usage",
        "analytics",
        "approve",
        "audit",
        "heartbeat",
        "inventory",
        "scan",
    }
)

# Synthesis skills — ideation/strategy-heavy stages that benefit from running
# the session on the declared top reasoning tier (Fable 5 when available).
SYNTHESIS_SKILLS: frozenset[str] = frozenset(
    {
        "brainstorm",
        "plan",
        "prd",
        "blueprint",
    }
)

# Per-skill local follow-ups for class 3 (up to 2 surfaced). Resume-pipeline is
# always the recommended option; these are the domain-appropriate alternates.
AUX_LOCAL_ACTIONS: dict[str, list[str]] = {
    "debug": ["/renmark:verify the fix", "re-run the failing verifier"],
    "doctor": ["re-run the failing skill", "/renmark:doctor --fix"],
    "hygiene": ["/renmark:hygiene --apply", "review flagged artifacts"],
    "roadmap": ["open the top-ranked roadmap item", "/renmark:plan"],
    "init": ["/renmark:start", "/renmark:brainstorm"],
    "setup": ["/renmark:start", "/renmark:brainstorm"],
    "help": ["/renmark:start", "/renmark:resume"],
    "resume": ["/renmark:start"],
    "backlog": ["/renmark:backlog (refresh the list)", "/renmark:finish"],
}


def skill_class(skill: object) -> str:
    """Return the next-steps class ('pipeline' | 'gate' | 'aux') for a skill.

    Unknown skills default to 'aux' — the safest class (resume-pipeline floor,
    never a stage advance the skill didn't earn). Non-string / unhashable input
    also degrades to 'aux' rather than raising, so callers (e.g. ``next_steps``)
    can honour their "never raise" contract.
    """
    if not isinstance(skill, str):
        return "aux"
    if skill in PIPELINE_SKILLS:
        return "pipeline"
    if skill in GATE_SKILLS:
        return "gate"
    return "aux"


# ── Size guard ────────────────────────────────────────────────────────────────

LIFECYCLE_JSON_BYTE_BUDGET = 1024  # 1KB — exceeding this is a bug (G12 audit)


class LifecycleBloatError(RuntimeError):
    """Raised when lifecycle.json grows past its budget — runtime cruft has leaked."""


# ── Data ──────────────────────────────────────────────────────────────────────


@dataclass
class LifecycleState:
    """Workflow state for one in-flight feature. Persisted to disk as JSON."""

    feature: str = ""
    branch: str = ""
    github_issue: int | None = None
    stage: str = "init"
    stages_completed: list[str] = field(default_factory=list)
    artifacts: dict[str, str] = field(default_factory=dict)
    # Human approval gate (G7 / principle #7)
    human_review_required: bool = False
    human_review_completed: bool = False
    human_review_for: str | None = None
    next_recommended: str = ""
    last_updated: str = ""

    def __post_init__(self) -> None:
        if not self.last_updated:
            self.last_updated = _now()
        if not self.next_recommended:
            self.next_recommended = NEXT_BY_STAGE.get(self.stage, "")

    def to_json(self) -> str:
        # Round-trip through dict to guarantee JSON-safe values.
        return json.dumps(asdict(self), indent=2, sort_keys=False)


# ── Paths ────────────────────────────────────────────────────────────────────


def _state_dir(repo: Path | str) -> Path:
    return Path(repo) / ".renmark" / "state"


def _lifecycle_path(repo: Path | str) -> Path:
    return _state_dir(repo) / "lifecycle.json"


# ── Public API ────────────────────────────────────────────────────────────────


# Accepted JSON types per LifecycleState field. Values of any other type are
# dropped at read time so corrupt or hand-edited state degrades to defaults
# instead of raising mid-recovery (a reader that raises is a resume-killer).
_LIFECYCLE_FIELD_TYPES: dict[str, type | tuple[type, ...]] = {
    "feature": str,
    "branch": str,
    "github_issue": (int, type(None)),
    "stage": str,
    "stages_completed": list,
    "artifacts": dict,
    "human_review_required": bool,
    "human_review_completed": bool,
    "human_review_for": (str, type(None)),
    "next_recommended": str,
    "last_updated": str,
}


def read_lifecycle(repo: Path | str) -> LifecycleState | None:
    """Return the current LifecycleState, or None if no lifecycle exists."""
    path = _lifecycle_path(repo)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    if not isinstance(data, dict):
        # Valid JSON but not an object — same contract as malformed: None.
        return None
    # Tolerate unknown fields and wrong-typed values — drop them rather than
    # crashing on schema drift.
    filtered: dict[str, Any] = {
        k: v for k, v in data.items() if k in _LIFECYCLE_FIELD_TYPES and isinstance(v, _LIFECYCLE_FIELD_TYPES[k])
    }
    return LifecycleState(**filtered)


def write_lifecycle(
    repo: Path | str,
    *,
    stage: str | None = None,
    feature: str | None = None,
    branch: str | None = None,
    github_issue: int | None = None,
    artifact_update: tuple[str, str] | None = None,
    human_review_required: bool | None = None,
    human_review_completed: bool | None = None,
    human_review_for: str | None = None,
) -> LifecycleState:
    """Update lifecycle.json with the provided fields. Reads-modifies-writes
    so existing fields not overridden are preserved. Returns the new state.

    Raises LifecycleBloatError if the resulting file exceeds the budget.
    """
    current = read_lifecycle(repo) or LifecycleState()

    if stage is not None:
        if stage not in STAGES:
            raise ValueError(f"unknown stage {stage!r}; must be one of {STAGES}")
        if current.stage != stage and current.stage != "init" and current.stage not in current.stages_completed:
            # Promote previous stage into stages_completed (idempotent).
            current.stages_completed.append(current.stage)
        current.stage = stage
        current.next_recommended = NEXT_BY_STAGE.get(stage, "")

    if feature is not None:
        current.feature = feature
    if branch is not None:
        current.branch = branch
    if github_issue is not None:
        current.github_issue = github_issue
    if artifact_update is not None:
        key, value = artifact_update
        current.artifacts[key] = value
    if human_review_required is not None:
        current.human_review_required = human_review_required
    if human_review_completed is not None:
        current.human_review_completed = human_review_completed
    if human_review_for is not None:
        current.human_review_for = human_review_for

    current.last_updated = _now()

    path = _lifecycle_path(repo)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = current.to_json()

    # Byte-budget guard runs FIRST: an oversize file is its own dedicated error
    # (LifecycleBloatError), and validate_lifecycle would otherwise pre-empt it
    # with a generic ValueError on the same 1KB budget.
    if len(payload.encode("utf-8")) > LIFECYCLE_JSON_BYTE_BUDGET:
        raise LifecycleBloatError(
            f"lifecycle.json would be {len(payload)} bytes; budget {LIFECYCLE_JSON_BYTE_BUDGET}. "
            "Runtime cruft has leaked in — move it to pipeline.json."
        )

    # Writer-side validation (never a hard gate at readers): a writer producing
    # structurally-invalid lifecycle state is a bug. Function-local import
    # avoids the schemas ↔ lifecycle circular import (schemas imports STAGES).
    from renmark import schemas

    issues = schemas.validate_lifecycle(json.loads(payload))
    if issues:
        raise ValueError(f"write_lifecycle would produce invalid state: {issues}")

    path.write_text(payload, encoding="utf-8")
    return current


def clear_lifecycle(repo: Path | str) -> None:
    """Delete lifecycle.json. The `/renmark:finish` SKILL calls this on a
    merged/released branch so the next `/renmark:start` is not redirected to
    resume forever; also called when the user wants a clean slate. Not dead
    code — keep it even when grep shows no in-tree caller (the caller is a
    SKILL.md, not Python)."""
    path = _lifecycle_path(repo)
    if path.exists():
        path.unlink()


def begin_feature(repo: Path | str, *, feature: str, branch: str) -> LifecycleState:
    """Establish a clean lifecycle for a newly started feature.

    Called by ``/renmark:feature`` immediately after creating or switching to
    the feature branch. Resets to a fresh state — stage ``init``, empty
    ``stages_completed``, empty ``artifacts`` — so a new feature never inherits
    the previous feature's identity, stage history, or artifact pointers. This
    is the canonical feature-entry write; downstream stage skills then advance
    ``stage`` on top of the correct identity. Without it, stage writes silently
    keep whatever ``feature``/``branch`` the prior feature left behind.
    """
    clear_lifecycle(repo)
    return write_lifecycle(repo, stage="init", feature=feature, branch=branch)


def next_recommended(repo: Path | str) -> str:
    """Return the recommended next command for the current lifecycle, or a
    cold-start prompt if no lifecycle exists. Zero LLM calls.

    Guarantees the returned hint never points at an unimplemented skill — if
    NEXT_BY_STAGE is somehow stale, the resolver routes to a manual fallback
    instead of sending a vibe coder into a wall.
    """
    state = read_lifecycle(repo)
    if state is None:
        return "/renmark:start (no feature in flight)"

    if state.human_review_required and not state.human_review_completed:
        target = state.human_review_for or "pending action"
        # `/renmark:approve` is the only sanctioned way to flip the gate (G7).
        return f"/renmark:approve (approval pending for: {target})"

    candidate = state.next_recommended or NEXT_BY_STAGE.get(state.stage, "")
    return _resolve_next(candidate, state.stage)


def _resolve_next(candidate: str, stage: str) -> str:
    """Replace any /renmark:<unimplemented> pointer with a manual hint."""
    if not candidate.startswith("/renmark:"):
        return candidate or f"(unknown stage: {stage})"
    skill = candidate.split(":", 1)[1].split()[0]
    if skill in IMPLEMENTED_SKILLS:
        return candidate
    return (
        f"(manual: /renmark:{skill} is not yet implemented — see CHANGELOG / README for next step from stage {stage!r})"
    )


@dataclass
class NextSteps:
    """Structured next-step set for a skill, per the next-steps.md contract.

    JSON-trivial: every field is a str / list[str] / bool. The caller renders
    ``suggestions`` via handoff-menu.md rules 6-9; ``tier0`` is always the
    state-derived ``(Recommended)`` option.
    """

    tier0: str  # deterministic state-derived next command (always present)
    suggestions: list[str]  # ordered options to surface (tier0 first)
    skill_class: str  # 'pipeline' | 'gate' | 'aux'
    defer_to_handoff_menu: bool = False  # gate skills set this
    gates_not_run: list[str] = field(default_factory=list)  # best-effort gate detection

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass
class LegacyDeliverySummary:
    """Canonical delivery summary projected from legacy workflow state.

    ``delivery`` is the normalized delivery-facing summary. ``drift_repair_notes``
    is a bounded list of concise compatibility/drift findings derived from the
    legacy state readers; callers can surface it directly without scanning the
    full underlying state files.
    """

    delivery: DeliveryState
    drift_repair_notes: list[str] = field(default_factory=list)

    @property
    def canonical_delivery(self) -> DeliveryState:
        return self.delivery

    @property
    def notes(self) -> list[str]:
        return self.drift_repair_notes

    def as_dict(self) -> dict[str, object]:
        return {
            "delivery": self.delivery.to_dict(),
            "drift_repair_notes": list(self.drift_repair_notes),
        }


@dataclass(frozen=True)
class MilestoneReadiness:
    """A bounded, read-only disposition for a milestone boundary.

    This deliberately contains only booleans and short blockers. Verifier and
    review bodies remain in their artifacts, rather than leaking into the
    lifecycle file or owner-facing state.
    """

    ready: bool
    verification_ready: bool
    review_ready: bool
    review_required: bool
    blockers: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, object]:
        return {
            "ready": self.ready,
            "verification_ready": self.verification_ready,
            "review_ready": self.review_ready,
            "review_required": self.review_required,
            "blockers": list(self.blockers),
        }


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


def milestone_signoff_ready(repo: Path | str) -> bool:
    """True only when Agency may offer owner milestone signoff."""
    return milestone_signoff_readiness(repo, agency=True).ready


def milestone_release_ready(repo: Path | str) -> bool:
    """True only when release readiness has fresh verification and review."""
    return milestone_signoff_readiness(repo, require_review=True).ready


def _current_head_sha(repo: Path) -> str:
    """Return HEAD for evidence comparison, degrading safely outside git."""
    try:
        from .summary import git_head_sha

        head = git_head_sha(repo)
        return head if isinstance(head, str) else ""
    except Exception:
        return ""


def _has_fresh_milestone_evidence(
    repo: Path,
    head: str,
    *,
    pattern: str,
    verifier: bool,
    milestone_id: str = "",
) -> bool:
    """Whether one clean, complete evidence artifact proves the current HEAD.

    ``*.qa.md`` is accepted only from the verification generator with a
    validated result. Reviews use an explicitly allowed independent-review
    generator and a validated result, which prevents a failed verifier or
    arbitrary artifact from self-certifying readiness.
    """
    if not head:
        return False
    reviews = repo / ".renmark" / "reviews"
    if not reviews.is_dir():
        return False
    for artifact in reviews.glob(pattern):
        try:
            metadata = read_metadata(artifact)
            stale = is_stale(artifact)
        except Exception:
            continue
        if stale or metadata.get("source_sha") != head:
            continue
        artifact_milestone = _signoff_milestone_id(metadata.get("milestone_id"))
        if milestone_id and artifact_milestone != milestone_id:
            continue
        if metadata.get("completion_state") != "complete":
            continue
        generator = metadata.get("generator")
        if verifier:
            if generator != "verify-qa" or metadata.get("validation_status") != "validated":
                continue
        elif (
            generator not in _INDEPENDENT_REVIEW_GENERATORS
            or metadata.get("validation_status") != "validated"
        ):
            continue
        if _evidence_has_failure(metadata):
            continue
        return True
    return False


# A signoff review must come from a dedicated reviewer, not merely any artifact
# writer that happens to use the ``.review.md`` suffix.
_INDEPENDENT_REVIEW_GENERATORS: frozenset[str] = frozenset({"codereview"})


def _signoff_milestone_id(value: object) -> str:
    """Return a stable signoff milestone token, or empty when unscoped."""
    if (
        not isinstance(value, str)
        or not value.strip()
        or not any(character.isalnum() for character in value)
    ):
        return ""
    return stable_milestone_id(value)


def _evidence_has_failure(metadata: dict[str, object]) -> bool:
    """Recognize the compact negative verdict tokens used by evidence writers."""
    failed = {"fail", "failed", "block", "blocked", "blocking", "changes_requested"}
    for key in ("verdict", "status", "review_status"):
        value = metadata.get(key)
        if isinstance(value, str) and value.strip().lower().replace(" ", "_") in failed:
            return True
    return False


def next_steps(repo: Path | str, skill: object) -> NextSteps:
    """Compute the structured next-step set for ``skill`` (next-steps.md contract).

    Pure + stdlib/renmark-only. Reads lifecycle via ``read_lifecycle`` and reuses
    the existing routing (``next_recommended`` → ``_resolve_next`` over
    ``NEXT_BY_STAGE``). Per class:

    - ``pipeline`` → ``suggestions = [tier0]`` (the stage transition).
    - ``gate`` → ``defer_to_handoff_menu=True`` plus best-effort ``gates_not_run``
      (review/qa artifacts whose ``source_sha`` != current HEAD or that are
      absent for the current sha; mirrors handoff-menu rule 2).
    - ``aux`` → ``[tier0]`` (resume-pipeline) + up to 2 per-skill local actions.

    ``suggestions`` is the state-derived **recommended next action(s)** — NOT the
    complete rendered menu. The calling SKILL.md adds the standard terminal
    options (Finish / Nothing, and the gate sub-menu for gate skills) per the
    handoff-menu.md rendering rules; do not treat ``suggestions`` as the full,
    choice-complete menu.

    NEVER raises into the caller: ``skill_class`` tolerates non-string input and
    any state-read failure degrades to a minimal result carrying just the
    cold-start ``next_recommended`` string.
    """
    cls = skill_class(skill)
    try:
        tier0 = next_recommended(repo)
    except Exception:
        # Absolute floor — never let a state read raise into a skill's hand-off.
        return NextSteps(
            tier0="/renmark:start (no feature in flight)",
            suggestions=["/renmark:start (no feature in flight)"],
            skill_class=cls,
        )

    if cls == "pipeline":
        return NextSteps(tier0=tier0, suggestions=[tier0], skill_class="pipeline")

    if cls == "gate":
        gates_not_run = _gates_not_run(repo)
        return NextSteps(
            tier0=tier0,
            suggestions=[tier0],
            skill_class="gate",
            defer_to_handoff_menu=True,
            gates_not_run=gates_not_run,
        )

    # aux / terminal
    local = AUX_LOCAL_ACTIONS.get(skill, [])[:2] if isinstance(skill, str) else []
    suggestions = [tier0, *local]
    return NextSteps(tier0=tier0, suggestions=suggestions, skill_class="aux")


def _gates_not_run(repo: Path | str) -> list[str]:
    """Best-effort: which quality gates have NOT run for the current HEAD sha.

    Mirrors handoff-menu rule 2 — scan ``.renmark/reviews/*.qa.md`` and
    ``*.review.md`` for an artifact with ``source_sha == HEAD`` and
    ``completion_state == 'complete'``; any gate without one is "not run".
    Degrades gracefully (returns ``[]``) if git or the summary helpers are
    unavailable.
    """
    try:
        from .summary import git_head_sha

        head = git_head_sha(repo)
        if not head:
            return []
        reviews = Path(repo) / ".renmark" / "reviews"
        if not reviews.is_dir():
            return ["qa", "codereview"]

        # (glob, required generator) per gate. The generator constraint mirrors
        # handoff-menu rule 2: a gate counts as "run" only when the artifact was
        # produced by the gate's own generator — a stray/foreign .qa.md must not
        # unlock Deep QA. generator=None means "no generator constraint".
        gate_specs: dict[str, tuple[str, str | None]] = {
            "qa": ("*.qa.md", "verify-qa"),
            "codereview": ("*.review.md", None),
        }
        not_run: list[str] = []
        for gate, (pattern, want_gen) in gate_specs.items():
            ran = False
            for artifact in reviews.glob(pattern):
                meta = read_metadata(artifact)
                if (
                    meta.get("source_sha") == head
                    and meta.get("completion_state") == "complete"
                    and (want_gen is None or meta.get("generator") == want_gen)
                ):
                    ran = True
                    break
            if not ran:
                not_run.append(gate)
        return not_run
    except Exception:
        return []


def domain_of(skill: str) -> str:
    """Return the domain bucket for a skill name (G4 contamination detection).

    Resolves via the `skillmeta` registry (single source of truth, P7);
    unknown skills default to ``"build"``. `DOMAIN_BY_SKILL` remains a derived
    back-compat alias, but is consulted first so a test `monkeypatch` of that
    attribute still takes effect.
    """
    if skill in DOMAIN_BY_SKILL:
        return DOMAIN_BY_SKILL[skill]
    meta = skillmeta.get(skill)
    return meta.domain if meta is not None else "build"


# Back-compat alias: `domain_for_skill` is the registry-facing name.
domain_for_skill = domain_of


def preamble_tier(skill: str) -> str:
    """Return the preamble tier for a skill ('minimal' | 'standard' | 'full').

    Unknown skills default to 'full'. Never raises.
    """
    return PREAMBLE_TIER_BY_SKILL.get(skill, "full")


def persist_compact_checkpoint(
    repo: Path | str,
    skill: str,
    reason: str,
    host: str | HostKind | None = None,
) -> None:
    """Write a compact checkpoint to .renmark/state/compact_checkpoint.json.

    Called by skill_preamble before emitting a context gate message so the
    user can resume after a host-supported context reset. Never raises. Hosts
    without a manual resume command persist ``resume_cmd: null``.
    """
    import json as _json

    from . import state as _state  # lazy — avoid circular import at module load

    try:
        host_capabilities = capabilities_for(_lifecycle_host(host))
        state_path = _state.state_dir(repo) / "compact_checkpoint.json"
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(
            _json.dumps(
                {
                    "skill": skill,
                    "reason": reason,
                    "resume_cmd": (
                        "/renmark:resume"
                        if host_capabilities.supports_resume
                        else None
                    ),
                    "timestamp": _state.now_iso(),
                },
                indent=2,
            ),
            encoding="utf-8",
        )
    except Exception:
        pass


def skill_preamble(
    repo: Path | str,
    skill: str,
    host: str | HostKind | None = None,
) -> str | None:
    """Single-call Step-0 boilerplate for every SKILL.md.

    Performs the calls every skill used to inline by hand, gated by tier:
        - ALL tiers: record invocation (load-bearing cross-domain detection for
          the NEXT skill — runs unconditionally so minimal-tier skills still
          register their domain in last-skill state).
        - minimal: returns None immediately; no budget check, no fragments.
        - standard: cross-domain/compact hint only; no fable synthesis hint.
        - full (default): cross-domain/compact hint + fable synthesis hint.

    Cross-domain detection for the CURRENT skill requires context_budget_check
    to read last-skill state BEFORE record_skill_invocation overwrites it, so
    for standard/full tier the budget check runs first. record_skill_invocation
    is then called unconditionally to keep the state file current for the next
    skill — this is the load-bearing ordering invariant.

    Returns the hint string the skill should surface to the user, or None when
    no hint is needed. Domain is resolved from `DOMAIN_BY_SKILL` — callers do
    not need to pass it, so the per-skill prose can't drift. Host resolution is
    explicit argument → ``RENMARK_HOST`` → backward-compatible Claude default.
    Hosts that do not support manual clear/resume commands record the domain
    transition and continue without presenting an unusable gate.
    """
    # Imported lazily to avoid a state ↔ lifecycle circular import at module load.
    from . import state as _state

    domain = domain_of(skill)
    tier = preamble_tier(skill)
    host_capabilities = capabilities_for(_lifecycle_host(host))

    if tier == "minimal":
        # INVARIANT: record_skill_invocation runs for ALL tiers so that the next
        # skill can detect cross-domain transitions even when this one is minimal.
        _state.record_skill_invocation(repo, skill, domain)
        return _with_agency_note(repo, skill, _with_headless_note(repo, None))

    # For standard/full: budget check MUST read last-skill state before
    # record_skill_invocation overwrites it — ordering is load-bearing.
    # Read last-skill state once here so prev_domain is available for the gate message.
    last = _state.last_skill_invocation(repo)
    verdict = _state.context_budget_check(repo, skill, domain)

    fragments: list[str] = []
    if verdict == "clear" and skill not in _CONTEXT_BYPASS_SKILLS:
        prev_domain = last.get("domain", "?") if last else "?"
        if not host_capabilities.supports_clear:
            # Codex and unknown hosts have no user-runnable /clear + resume
            # pair. Treat the transition as observed, record it below, and
            # continue without manufacturing an unsupported command gate.
            verdict = None
        else:
            persist_compact_checkpoint(repo, skill, reason="clear", host=host)
        # Headless: skip the interactive gate so non-interactive runs are not blocked.
        from . import config as _config
        if verdict == "clear" and _config.is_headless(repo):
            # Record now — headless runs proceed automatically past the gate.
            _state.record_skill_invocation(repo, skill, domain)
            return _with_agency_note(
                repo, skill,
                _with_mode_note(
                    repo, skill,
                    _with_headless_note(
                        repo,
                        f"context: cross-domain transition into `{domain}` "
                        f"(prev: `{prev_domain}`) "
                        "\u2014 headless mode: skipping interactive gate, proceeding automatically",
                    ),
                ),
            )
        # Interactive: return the gate prefix WITHOUT recording the invocation.
        # Not recording keeps the gate live on re-entry — the user must choose
        # explicitly before the skill proceeds.
        if verdict == "clear":
            return (
                f"CONTEXT_GATE_CLEAR: cross-domain transition detected "
                f"(prev: `{prev_domain}` \u2192 `{domain}`).\n"
                "State persisted to .renmark/state/compact_checkpoint.json.\n"
                "Present the user with AskUserQuestion before proceeding with this skill:\n"
                '  header: "Context hygiene"\n'
                '  question: "Domain change detected. Run /clear to start fresh '
                '(memory survives), or continue with accumulated context?"\n'
                "  options:\n"
                "    1. Stop here \u2014 I will run /clear then /renmark:resume (Recommended)\n"
                "    2. Continue in same context (this step only)\n"
                "    3. Queue this as next task after current work finishes\n"
                "    4. Cancel"
            )

    # Record the invocation here — after the gate, so a gated-then-stopped skill
    # does not corrupt the domain state for subsequent cross-domain detection.
    _state.record_skill_invocation(repo, skill, domain)

    if verdict == "clear" and host_capabilities.supports_clear:
        # Must be a bypass skill (finish/approve/resume) — advisory only.
        fragments.append(
            f"context: cross-domain transition into `{domain}` — consider `/clear` "
            "before continuing (`.renmark/memory/` survives clears)"
        )
    elif verdict == "compact" and host_capabilities.supports_compact:
        fragments.append("context: approaching budget — consider `/compact` before continuing")

    if tier == "full" and skill in SYNTHESIS_SKILLS:
        # Imported lazily to keep capability resolution off the module-load path.
        from . import capabilities as _capabilities

        if _capabilities.top_tier(Path(repo)) == "fable":
            fragments.append(
                "declared top tier: fable — for best ideation/strategy results "
                "run this session on Fable 5 (/model fable)"
            )

    base = " | ".join(fragments) if fragments else None
    return _with_agency_note(repo, skill, _with_mode_note(repo, skill, _with_headless_note(repo, base)))


# ── Delivery-mode directive (Agency vs Orchestrator) ──────────────────────────
#
# Set-mode directive lines (persisted mode → one hint line). Kept as module
# constants so the behavior test (T14) and unit test (T12) can assert the exact
# text without duplicating string literals.
_MODE_DIRECTIVE: dict[str, str] = {
    "agency": (
        "Delivery mode: Agency — owner-facing milestone delivery; discover and "
        "agree outcomes, then delegate bounded milestone execution to Orchestrator."
    ),
    "orchestrator": (
        "Delivery mode: Orchestrator — execute goal-level work packages through "
        "bounded build → verify → review → fix loops and persist each boundary."
    ),
}

# Only unresolved adoption/new-build entry points ask. Existing-project flows
# use their deterministic default and resume never re-asks.
_MODE_PROMPT_SKILLS: frozenset[str] = frozenset({"init", "start"})
_MODE_DEFAULT_SKILLS: frozenset[str] = frozenset(
    {"feature", "debug", "roadmap", "finish", "orchestrate"}
)

# Skills whose flows must not be blocked mid-stream by context gates.
# finish/approve/resume: urgent paths that must not be interrupted halfway.
_CONTEXT_BYPASS_SKILLS: frozenset[str] = frozenset({"finish", "approve", "resume"})


def _choose_mode_hint(skill: str) -> str:
    """Choose-mode instruction emitted for an entry-point skill with no mode set.

    Tells the orchestrator to ask the user Agency vs Orchestrator via
    AskUserQuestion, recommending the per-skill default, then persist the choice.
    """
    from . import mode as _mode

    recommended = _mode.default_mode_for_skill(skill)
    return (
        "Delivery mode: not yet set — ask the user Agency vs Orchestrator via "
        f"AskUserQuestion (recommend: {recommended}), then persist with "
        "renmark.mode.set_mode(repo, <choice>)."
    )


def _with_mode_note(repo: Path | str, skill: str, hint: str | None) -> str | None:
    """ADDITIVE: append the operating-mode directive to ``hint``.

    Runs strictly AFTER the existing tier logic and the headless note — never
    reorders the record-before-check invariant. DEGRADES GRACEFULLY: any
    exception in mode resolution falls back to ``hint`` unchanged, so mode is a
    pure enhancement and never a hard dependency of the preamble.

    - Mode SET  → append the Agency/Orchestrator directive line.
    - Mode UNSET + entry-point skill → append a choose-mode instruction.
    - Mode UNSET + non-entry skill → no mode line (returns ``hint`` unchanged).
    """
    try:
        from . import mode as _mode

        current = _mode.read_mode(repo)
        if current is None and skill in _MODE_DEFAULT_SKILLS:
            resolved = _mode.default_delivery_state_for_skill(skill)
            _mode.write_delivery_state(repo, resolved)
            current = resolved.delivery_mode
        if current is not None:
            line = _MODE_DIRECTIVE.get(current)
            if line is None:  # unrecognised (read_mode shouldn't yield this)
                return hint
        elif skill in _MODE_PROMPT_SKILLS:
            line = _choose_mode_hint(skill)
        else:
            return hint
    except Exception:
        return hint
    return line if hint is None else f"{hint} | {line}"


# Pipeline skills that receive an Agency Mode hint when agency is active.
# v0.30.0 shipped the spine (start/prd/roadmap/finish/resume); the fast-follow
# extends coverage to the remaining pipelines (feature/plan/orchestrate/verify/
# codereview) so the whole delivery loop is agency-aware.
_AGENCY_AWARE_SKILLS: frozenset[str] = frozenset(
    {
        "start", "prd", "roadmap", "finish", "resume",
        "feature", "plan", "orchestrate", "verify", "codereview",
    }
)

# Back-compat alias: the original spine-only name still resolves.
_AGENCY_SPINE_SKILLS: frozenset[str] = _AGENCY_AWARE_SKILLS

# Marker string used to identify the agency hint line — load-bearing for
# behavior tests (T15): assert active preamble contains this prefix and
# inactive preamble does NOT.
_AGENCY_HINT_MARKER: str = "Agency Mode active"


def _with_agency_note(repo: Path | str, skill: str, hint: str | None) -> str | None:
    """ADDITIVE: append an Agency Mode hint to ``hint`` when agency is active.

    Only surfaces the hint for AGENCY-AWARE pipeline skills (the spine —
    start/prd/roadmap/finish/resume — plus feature/plan/orchestrate/verify/
    codereview) — all other skills are passed through unchanged regardless of
    agency state.

    When agency is INACTIVE the return value is byte-identical to ``hint``
    (the inactive-path guarantee). DEGRADES GRACEFULLY: any exception in
    agency/context resolution falls back to ``hint`` unchanged, so agency is
    a pure enhancement and never a hard dependency of the preamble.

    Follows the same additive pattern as :func:`_with_mode_note` and
    :func:`_with_headless_note`.
    """
    if skill not in _AGENCY_AWARE_SKILLS:
        return hint
    try:
        from . import agency as _agency
        from . import context as _context
        from . import mode as _mode

        # Canonical delivery.json wins over the legacy agency overlay. This
        # prevents split-brain hints after an explicit Orchestrator choice.
        if _mode.read_mode(repo) == "orchestrator":
            return hint
        if not _agency.is_active(repo):
            return hint
        state = _agency.read_agency(repo)
        pointer = _context.fragment_pointer("agency-delivery")
        line = (
            f"{_AGENCY_HINT_MARKER} — phase {state.current_phase}, "
            f"milestone {state.current_milestone}. Contract: {pointer}"
        )
    except Exception:
        return hint
    return line if hint is None else f"{hint} | {line}"


def _with_headless_note(repo: Path | str, hint: str | None) -> str | None:
    """ADDITIVE: append a headless-mode note to ``hint`` when headless is active.

    Runs strictly AFTER the existing tier logic — never reorders the
    record-before-check invariant above. When headless is off this is a
    pass-through (returns ``hint`` unchanged, including None). When on it
    appends one line; if ``hint`` was None the note becomes the whole return.
    Never raises — config helpers are themselves no-raise.
    """
    from . import config as _config

    try:
        if not _config.is_headless(repo):
            return hint
        note = f"headless mode active (source: {_config.headless_source(repo)})"
    except Exception:
        return hint
    return note if hint is None else f"{hint} | {note}"


def is_cross_domain_transition(prev_skill: str | None, new_skill: str) -> bool:
    """G4: True if moving from prev_skill to new_skill crosses domain boundaries.
    First invocation (prev_skill=None) is never cross-domain.
    """
    if prev_skill is None:
        return False
    return domain_of(prev_skill) != domain_of(new_skill)


# ── Headless human-review gate (P10) ──────────────────────────────────────────


def halt_for_human_review(
    repo: Path | str,
    gate: str,
    *,
    originating_skill: str,
    what: str,
) -> dict[str, Any]:
    """Halt a headless run at a human-approval gate (P10 headless contract).

    A headless executor cannot prompt; instead of silently proceeding through a
    Pause-Policy gate it writes a decision artifact and arms the existing
    lifecycle human-review gate so a later interactive ``/renmark:approve`` can
    clear it. Returns a machine-readable ``needs_input`` envelope.

    Side effects:
      - ensures ``.renmark/decisions/`` exists (never raises if missing);
      - writes ``.renmark/decisions/<gate>-approval.json`` (stdlib json);
      - sets ``human_review_required=True`` / ``human_review_for=<gate>`` via the
        EXISTING :func:`write_lifecycle` gate fields (no new state files).
    """
    decisions_dir = Path(repo) / ".renmark" / "decisions"
    # Dir creation is best-effort too — the halt contract is "never raise". If
    # mkdir fails (permissions/OS error) the artifact write below is suppressed
    # and we still return the needs_input envelope; the armed gate is the safe state.
    with contextlib.suppress(OSError):
        decisions_dir.mkdir(parents=True, exist_ok=True)
    decision_path = decisions_dir / f"{gate}-approval.json"

    # Current stage is best-effort: a halt may precede any lifecycle write.
    state = read_lifecycle(repo)
    stage = state.stage if state is not None else None

    payload = {
        "gate": gate,
        "timestamp": _now(),
        "what": what,
        "originating_skill": originating_skill,
        "stage": stage,
        "human_review_required": True,
    }

    # Arm the gate on existing lifecycle fields FIRST — keeps the ≤1KB budget
    # intact. The halt contract is "RETURN needs_input, never raise"; write_lifecycle
    # can raise (LifecycleBloatError / validation), so guard it. A halted state is
    # the safe state — never propagate; we still return the envelope below.
    with contextlib.suppress(Exception):
        write_lifecycle(repo, human_review_required=True, human_review_for=gate)

    # Best-effort artifact write — never raise out of a halt.
    with contextlib.suppress(OSError), decision_path.open(
        "w", encoding="utf-8"
    ) as fh:
        json.dump(payload, fh, indent=2)

    # Repo-relative path per the artifact-reference convention (never absolute).
    rel_path = f".renmark/decisions/{gate}-approval.json"
    return {
        "status": "needs_input",
        "mode": "headless",
        "gate": gate,
        "decision": "halted_for_human_review",
        "human_review_required": True,
        "artifacts": [rel_path],
    }


# ── Artifact reference validation ─────────────────────────────────────────────


def _validate_one_artifact(
    key: str,
    path_str: str,
    repo_path: Path,
) -> list[dict[str, str]]:
    """Perform all checks for a single artifact reference.

    Returns a list of issue dicts (each with ``severity``, ``kind``,
    ``artifact``, ``path``, ``detail`` set). Returns an empty list when the
    artifact passes all checks. Callers route BLOCK vs WARN issues to the
    appropriate accumulator — this helper never mutates external state.
    """
    # ── inside-repo check ─────────────────────────────────────────────────
    raw = Path(path_str)
    try:
        resolved = raw.resolve() if raw.is_absolute() else (repo_path / raw).resolve()
        resolved.relative_to(repo_path.resolve())  # raises ValueError if outside
        inside_repo = True
    except (ValueError, OSError):
        inside_repo = False

    if not inside_repo:
        return [
            {
                "severity": "WARN",
                "kind": "out_of_tree",
                "artifact": key,
                "path": path_str,
                "detail": f"artifact {key!r} resolves outside project subtree"[:120],
            }
        ]

    # ── exists check ──────────────────────────────────────────────────────
    if not resolved.exists():
        severity = "BLOCK" if key in {"plan", "spec"} else "WARN"
        return [
            {
                "severity": severity,
                "kind": "missing_path",
                "artifact": key,
                "path": path_str,
                "detail": f"artifact {key!r} missing at {path_str}"[:120],
            }
        ]

    # ── provenance and freshness checks ───────────────────────────────────
    issues: list[dict[str, str]] = []

    try:
        meta = read_metadata(resolved)
    except Exception:
        meta = {}

    source_sha = meta.get("source_sha")
    if isinstance(source_sha, str) and source_sha and source_sha != "null":
        try:
            result = subprocess.run(
                ["git", "-C", str(repo_path), "cat-file", "-e", source_sha],
                capture_output=True,
                timeout=5,
                check=False,
            )
            if result.returncode != 0:
                issues.append(
                    {
                        "severity": "WARN",
                        "kind": "unreachable_sha",
                        "artifact": key,
                        "path": path_str,
                        "detail": f"source_sha {source_sha[:12]} for {key!r} not reachable in git"[:120],
                    }
                )
        except (subprocess.TimeoutExpired, OSError):
            pass

    try:
        stale = is_stale(resolved)
    except Exception:
        stale = False
    if stale:
        issues.append(
            {
                "severity": "WARN",
                "kind": "stale_artifact",
                "artifact": key,
                "path": path_str,
                "detail": f"artifact {key!r} past its stale_after timestamp"[:120],
            }
        )

    return issues


def validate_artifact_refs(
    repo: Path | str,
    state: LifecycleState | None = None,
) -> list[dict[str, str]]:
    """Validate that artifacts referenced in lifecycle state actually exist and
    are reachable. Pure read — does not mutate lifecycle state.

    Returns a list of issue dicts with keys: severity, kind, artifact, path,
    detail. BLOCK issues come first (in artifacts insertion order), then WARN
    issues sorted by artifact key alphabetically.

    Issue ``kind`` values: ``missing_path`` (BLOCK for plan/spec, else WARN),
    ``out_of_tree`` (WARN — path is absolute or escapes the project subtree;
    further checks are skipped), ``unreachable_sha`` (WARN), ``stale_artifact``
    (WARN).
    """
    if state is None:
        state = read_lifecycle(repo)
    if state is None:
        return []

    # Widen to object so the corrupt/hand-built guards below are type-checkable
    # (the dataclass declares dict[str, str], but disk state may lie).
    artifacts: object = state.artifacts
    if not isinstance(artifacts, dict):
        # Hand-built or corrupt state — nothing to validate.
        return []

    repo_path = Path(repo)
    block_issues: list[dict[str, str]] = []
    warn_issues: list[dict[str, str]] = []

    for key, path_str in artifacts.items():
        if not isinstance(path_str, str):
            continue
        for issue in _validate_one_artifact(key, path_str, repo_path):
            if issue["severity"] == "BLOCK":
                block_issues.append(issue)
            else:
                warn_issues.append(issue)

    warn_issues.sort(key=lambda i: i["artifact"])
    return block_issues + warn_issues


_LIFECYCLE_MILESTONE_BY_STAGE: dict[str, str] = {
    "init": "discovery",
    "brainstorm-complete": "discovery",
    "plan-drafted": "plan",
    "plan-validated": "plan",
    "created": "build",
    "verified": "verify",
    "reviewed": "review",
    "documented": "documented",
    "ready-to-release": "release",
    "released": "release",
}

_MODE_POLICY_BY_TOKEN: dict[str, str] = {
    "conductor": "guided",
    "orchestrator": "async",
    # Legacy/stale tokens tolerated as execution policies.
    "guided": "guided",
    "direct": "direct",
    "async": "async",
}


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


def _safe_read_program(repo: Path, notes: list[str]) -> Program | None:
    try:
        return read_program(repo)
    except ProgramStateError as exc:
        notes.append(f"program state unreadable; ignored legacy program drift ({str(exc).splitlines()[0][:72]})")
        return None


def _legacy_delivery_run_id(
    repo: Path,
    *,
    lifecycle_state: LifecycleState | None,
    agency_state: AgencyState,
    program_state: Program | None,
) -> str:
    lifecycle_artifacts = lifecycle_state.artifacts if lifecycle_state is not None else {}
    return stable_delivery_run_id(
        "legacy",
        getattr(program_state, "created_at", ""),
        getattr(program_state, "source_sha", ""),
        getattr(program_state, "feature", ""),
        lifecycle_state.feature if lifecycle_state is not None else "",
        lifecycle_state.branch if lifecycle_state is not None else "",
        lifecycle_state.github_issue if lifecycle_state is not None else "",
        lifecycle_artifacts.get("plan", ""),
        getattr(agency_state, "roadmap_ref", ""),
        repo.name,
    )


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


def _current_program_stage(program_state: Program | None) -> StageNode | None:
    if program_state is None or not program_state.stages:
        return None
    if program_state.current_stage_id:
        for stage in program_state.stages:
            if stage.id == program_state.current_stage_id:
                return stage
    for milestone in program_delivery_milestones(program_state):
        if milestone.get("delivery_state") not in {"passed"}:
            stage_id = milestone.get("stage_id")
            for stage in program_state.stages:
                if stage.id == stage_id:
                    return stage
    return program_state.stages[-1]


def _work_package_summaries_for_stage(stage: StageNode) -> list[WorkPackageSummary]:
    packages: list[WorkPackageSummary] = []
    milestone_id = stable_milestone_id_for_stage(stage)
    for task in stage.tasks[:8]:
        packages.append(
            WorkPackageSummary(
                package_id=stable_work_package_id_for_task(stage, task),
                milestone_id=milestone_id,
                title=task.title or task.id or "(untitled task)",
                status=delivery_state_for_program_status(task.status),
                summary=" ".join(task.summary.split()) if task.summary else "",
                owner="program",
            )
        )
    return packages


def _lifecycle_milestone(state: LifecycleState | None) -> str:
    if state is None:
        return ""
    return _LIFECYCLE_MILESTONE_BY_STAGE.get(state.stage, "")


def _program_milestone(state: Program | None) -> str:
    stage = _current_program_stage(state)
    return stable_milestone_id_for_stage(stage) if stage is not None else ""


def _agency_milestone(state: AgencyState) -> str:
    if not state.active:
        return ""
    milestone = " ".join(state.current_milestone.split())
    phase = " ".join(state.current_phase.split())
    token = milestone or phase or "discovery"
    from .delivery_state import stable_milestone_id

    return stable_milestone_id(token)


def _read_raw_mode_token(repo: Path) -> str:
    path = mode_state_path(repo)
    if not path.exists():
        return ""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError):
        return ""
    if not isinstance(payload, dict):
        return ""
    raw = payload.get("mode")
    return raw if isinstance(raw, str) else ""


def _normalize_mode_note(raw_mode_token: str) -> tuple[str, str]:
    token = " ".join(raw_mode_token.split()).lower()
    if not token:
        return "", ""
    policy = _MODE_POLICY_BY_TOKEN.get(token, "")
    if token in {"guided", "direct", "async"}:
        return (
            f"mode repair: legacy mode token {token!r} treated as execution_policy {policy!r}",
            policy,
        )
    if token not in {"conductor", "orchestrator"}:
        return (f"mode drift: stale mode token {token!r} ignored", "")
    return "", policy


def _lifecycle_host(host: str | HostKind | None) -> str | HostKind:
    """Lifecycle-local host resolution contract.

    This module preserves the historical behavior documented in its own
    preamble helpers: explicit ``host`` wins, then ``RENMARK_HOST``, and with
    neither set it defaults to Claude-compatible capabilities. That keeps the
    lifecycle/preamble contract stable even when the surrounding process is a
    Codex-hosted test runner.
    """
    if host is not None:
        return host
    raw = os.getenv("RENMARK_HOST")
    if raw and raw.strip():
        return raw
    return "claude"


# ── Internal ──────────────────────────────────────────────────────────────────


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

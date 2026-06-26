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
``plugin/skills/_shared/next-steps.md`` — the single source of truth for the
"what should the user do next?" hand-off rule across every renmark skill.
"""

from __future__ import annotations

import contextlib
import json
import subprocess
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

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
        "feature",
        "finish",
        "guide",
        "help",
        "hygiene",
        "init",
        "inventory",
        "loop",
        "orchestrate",
        "plan",
        "prd",
        "resume",
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
DOMAIN_BY_SKILL: dict[str, str] = {
    "debug": "debug",
    "codereview": "debug",
    "start": "build",
    "brainstorm": "build",
    "plan": "build",
    "check-plan": "build",
    "orchestrate": "build",
    "verify": "build",
    "finish": "build",
    "feature": "build",
    "prd": "build",
    "blueprint": "build",
    "backlog": "build",
    "loop": "build",
    "audit": "audit",
    "inventory": "audit",
    "scan": "audit",
    "setup": "meta",
    "roadmap": "meta",
    "help": "meta",
    "guide": "meta",
    "resume": "meta",
    "approve": "meta",
    "hygiene": "meta",
    "doctor": "meta",
    "init": "meta",
    "usage": "meta",
    "analytics": "meta",
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
# Three classes from plugin/skills/_shared/next-steps.md. The class decides what
# `next_steps()` surfaces. Mirror the DOMAIN_BY_SKILL style — module-level
# frozensets, names aligned with the contract.

# Class 1 — pipeline skills: Tier-0 stage routing (advance the lifecycle).
PIPELINE_SKILLS: frozenset[str] = frozenset(
    {
        "start",
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
    """Return the domain bucket for a skill name (G4 contamination detection)."""
    return DOMAIN_BY_SKILL.get(skill, "build")


def preamble_tier(skill: str) -> str:
    """Return the preamble tier for a skill ('minimal' | 'standard' | 'full').

    Unknown skills default to 'full'. Never raises.
    """
    return PREAMBLE_TIER_BY_SKILL.get(skill, "full")


def skill_preamble(repo: Path | str, skill: str) -> str | None:
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
    not need to pass it, so the per-skill prose can't drift.
    """
    # Imported lazily to avoid a state ↔ lifecycle circular import at module load.
    from . import state as _state

    domain = domain_of(skill)
    tier = preamble_tier(skill)

    if tier == "minimal":
        # INVARIANT: record_skill_invocation runs for ALL tiers so that the next
        # skill can detect cross-domain transitions even when this one is minimal.
        _state.record_skill_invocation(repo, skill, domain)
        return _with_headless_note(repo, None)

    # For standard/full: budget check MUST read last-skill state before
    # record_skill_invocation overwrites it — ordering is load-bearing.
    verdict = _state.context_budget_check(repo, skill, domain)
    _state.record_skill_invocation(repo, skill, domain)

    fragments: list[str] = []
    if verdict == "clear":
        fragments.append(
            f"context: cross-domain transition into `{domain}` — consider `/clear` "
            "before continuing (`.renmark/memory/` survives clears)"
        )
    elif verdict == "compact":
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
    return _with_headless_note(repo, base)


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
        raw = Path(path_str)
        try:
            resolved = raw.resolve() if raw.is_absolute() else (repo_path / raw).resolve()
            resolved.relative_to(repo_path.resolve())  # raises ValueError if outside
            inside_repo = True
        except (ValueError, OSError):
            inside_repo = False

        if not inside_repo:
            warn_issues.append(
                {
                    "severity": "WARN",
                    "kind": "out_of_tree",
                    "artifact": key,
                    "path": path_str,
                    "detail": f"artifact {key!r} resolves outside project subtree"[:120],
                }
            )
            continue

        if not resolved.exists():
            severity = "BLOCK" if key in {"plan", "spec"} else "WARN"
            issue: dict[str, str] = {
                "severity": severity,
                "kind": "missing_path",
                "artifact": key,
                "path": path_str,
                "detail": f"artifact {key!r} missing at {path_str}"[:120],
            }
            if severity == "BLOCK":
                block_issues.append(issue)
            else:
                warn_issues.append(issue)
            continue

        # File exists — check provenance and freshness.
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
                    warn_issues.append(
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
            warn_issues.append(
                {
                    "severity": "WARN",
                    "kind": "stale_artifact",
                    "artifact": key,
                    "path": path_str,
                    "detail": f"artifact {key!r} past its stale_after timestamp"[:120],
                }
            )

    warn_issues.sort(key=lambda i: i["artifact"])
    return block_issues + warn_issues


# ── Internal ──────────────────────────────────────────────────────────────────


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

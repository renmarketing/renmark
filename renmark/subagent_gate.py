"""Enforced subagent-justification gate — the deterministic-first check that runs
BEFORE any subagent is dispatched (strengthens REQ-21 from advice into a gate).

Renmark already ships the *advice* (``.shared/deterministic-first.md`` 4-question
gate, ``.shared/subagent-budget.md``) and the cost machinery that *tags*
deterministic vs model-driven work (``renmark.cost``). What was missing is a pure,
zero-LLM function the dispatch path can actually CALL to challenge a spawn — so a
subagent-heavy, deterministic-eligible plan gets flagged before tokens flow.

This module composes the existing pieces — it does NOT re-implement them:
- ``renmark.cost.is_deterministic_item`` — the deterministic/model-driven signal.
- ``renmark.cost._get`` — the dict/attr accessor.
- ``renmark.subagent_profiles.resolve_profile`` / ``profile_tier`` — the scoped
  role + cheapest-capable tier (``general-purpose`` is fallback-only).

Every function is pure and NEVER raises — on any bad input it degrades to the
safe/conservative answer (assume a subagent IS needed rather than silently
suppressing one), so the gate can never break a real dispatch.

The 4 questions (deterministic-first.md), answered mechanically where possible:
  Q1 Can git/grep/read/parser/state answer this?     → deterministic-eligible
  Q2 Can a deterministic script/check answer this?    → deterministic-eligible
  Q3 Can the orchestrator do this directly (no agent)? → trivial/simple + tiny
  Q4 Is it large/ambiguous enough to justify a subagent? → complexity/size
"""

from __future__ import annotations

import fnmatch
import os
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from renmark import cost, recurrence, subagent_profiles

# Complexity labels that, on their own, justify a subagent (Q4).
_SUBAGENT_JUSTIFYING_COMPLEXITY: frozenset[str] = frozenset({"hard", "medium"})

# Below this token estimate a "simple" task is cheap enough for the orchestrator
# to do inline (Q3) rather than paying ~10k agent-overhead to dispatch it.
_DIRECT_TOKEN_CEILING: int = 400


@dataclass(frozen=True)
class SubagentVerdict:
    """The per-task justification verdict.

    ``needs_subagent`` — the gate's recommendation (False = answerable without a
    subagent). ``challenge`` — a non-None one-liner when the spawn is
    questionable (deterministic-eligible, orchestrator-doable, or an unjustified
    general-purpose role); None means the spawn is clean.
    """

    needs_subagent: bool
    deterministic_eligible: bool
    role: str
    tier: str
    reason: str
    challenge: str | None = None
    # Structured challenge kind so callers don't string-match the human message:
    # "" (none) | "deterministic" | "inlineable" | "missing_role_reason" |
    # "no_signal" | "unclassified".
    challenge_code: str = ""


@dataclass(frozen=True)
class PlanChallenge:
    """Plan-level rollup used by the cost preview to challenge a plan."""

    total: int = 0
    subagent_tasks: int = 0
    deterministic_eligible: int = 0
    unjustified: int = 0
    general_purpose: int = 0
    flagged_indices: tuple[int, ...] = field(default_factory=tuple)
    challenged: bool = False
    message: str = ""


def _q3_inlineable(complexity: str, est_known: bool, est_tokens: int) -> bool:
    """Return True when the task is simple/tiny enough to execute inline.

    A *simple* complexity is inline-able unless a known estimate exceeds the
    ceiling.  An unspecified complexity only inlines when a known-tiny estimate
    is present (total unknowns are not auto-inlined).
    """
    return (complexity == "simple" and (not est_known or est_tokens <= _DIRECT_TOKEN_CEILING)) or (
        complexity == "" and est_known and est_tokens <= _DIRECT_TOKEN_CEILING
    )


def _q4_justified(complexity: str, est_known: bool, est_tokens: int) -> bool:
    """Return True when a subagent is positively warranted by complexity or size."""
    return complexity in _SUBAGENT_JUSTIFYING_COMPLEXITY or (
        est_known and est_tokens > _DIRECT_TOKEN_CEILING
    )


def justify_task(task: Any) -> SubagentVerdict:
    """Return the justification :class:`SubagentVerdict` for one planned task.

    Pure, zero-LLM, never raises. Accepts a dict or any object exposing
    ``executor`` / ``complexity`` / ``est_tokens`` / ``role`` / ``role_reason``.
    """
    try:
        # A package can be marked as a deterministic work package before it is
        # compiled into legacy task packets.  That work must not consume an
        # agent dispatch simply because it has no legacy executor field yet.
        cost_lane = str(cost._get(task, "cost_lane", "") or "").strip().lower()
        if cost_lane in {"deterministic", "check", "script", "tool", "none"}:
            return SubagentVerdict(
                needs_subagent=False,
                deterministic_eligible=True,
                role="deterministic",
                tier="none",
                reason="deterministic package cost lane",
                challenge="deterministic package work — resolve via a check/script, not a subagent",
                challenge_code="deterministic",
            )
        # Q1 + Q2 — a deterministic path exists → no subagent needed.
        if cost.is_deterministic_item(task):
            return SubagentVerdict(
                needs_subagent=False,
                deterministic_eligible=True,
                role="deterministic",
                tier="none",
                reason="deterministic path (git/grep/parser/state or deterministic executor)",
                challenge="deterministic-eligible — resolve via a check/script, not a subagent",
                challenge_code="deterministic",
            )

        role = subagent_profiles.resolve_profile(task)
        tier = subagent_profiles.profile_tier(role)
        complexity = str(cost._get(task, "complexity", "") or "").strip().lower()
        raw_tokens = cost._get(task, "est_tokens", None)
        # Distinguish a KNOWN positive estimate from unknown/0/negative/bool.
        est_known = (
            isinstance(raw_tokens, int) and not isinstance(raw_tokens, bool) and raw_tokens > 0
        )
        est_tokens: int = raw_tokens if est_known else 0  # type: ignore[assignment]
        tok_str = f"~{est_tokens} tok" if est_known else "no estimate"

        # Q3 — a trivial/simple task the orchestrator can do inline. A "simple"
        # task is inline-able unless it carries a KNOWN estimate above the ceiling
        # (a missing estimate must NOT force a subagent — that was a false
        # positive). An unspecified-complexity task only inlines on a known-tiny
        # estimate (we don't inline total unknowns).
        inlineable = _q3_inlineable(complexity, est_known, est_tokens)
        if inlineable:
            return SubagentVerdict(
                needs_subagent=False,
                deterministic_eligible=False,
                role=role,
                tier=tier,
                reason=f"{complexity or 'unspecified'} + {tok_str} — orchestrator can do this inline",
                challenge="small/simple — do it inline or route to haiku, not a scoped subagent",
                challenge_code="inlineable",
            )

        # Q4 — large/ambiguous enough → a subagent is justified.
        justified = _q4_justified(complexity, est_known, est_tokens)

        challenge: str | None = None
        challenge_code = ""
        if role == "general-purpose":
            reason_field = str(cost._get(task, "role_reason", "") or "").strip()
            if not reason_field:
                challenge = (
                    "general-purpose without a scoped role — assign a specialized "
                    "profile (docs-editor/code-implementer/test-writer/reviewer/…) "
                    "or state role_reason"
                )
                challenge_code = "missing_role_reason"
        elif not justified:
            challenge = "no hard/medium/large signal — confirm a subagent is warranted"
            challenge_code = "no_signal"

        return SubagentVerdict(
            needs_subagent=justified or role != "general-purpose",
            deterministic_eligible=False,
            role=role,
            tier=tier,
            reason=f"{complexity or 'unspecified'} complexity, {tok_str}, role={role}",
            challenge=challenge,
            challenge_code=challenge_code,
        )
    except Exception:
        # Conservative fallback: assume a subagent is needed (never suppress work
        # by accident), but flag it so the human still sees the uncertainty.
        return SubagentVerdict(
            needs_subagent=True,
            deterministic_eligible=False,
            role="general-purpose",
            tier="sonnet",
            reason="gate could not classify this task",
            challenge="gate could not classify — review before dispatch",
            challenge_code="unclassified",
        )


def challenge_plan(tasks: Any, *, unjustified_share_threshold: float = 0.5) -> PlanChallenge:
    """Roll :func:`justify_task` up across a plan and decide whether to challenge it.

    ``challenged`` is True when at least ``unjustified_share_threshold`` of the
    would-be-subagent tasks are unjustified (deterministic-eligible, inline-able,
    or unexplained general-purpose), OR when any general-purpose spawn lacks a
    reason. Pure, never raises — an unusable ``tasks`` yields an empty, unchallenged
    rollup.
    """
    try:
        items = list(tasks)
    except Exception:
        return PlanChallenge()

    total = 0
    subagent_tasks = 0            # non-deterministic tasks that would spawn a subagent
    deterministic_eligible = 0    # tasks a check/script should replace (NOT spawns)
    unjustified = 0              # spawns that are challenged (inline-able / gp-no-reason / no-signal)
    general_purpose = 0
    gp_without_reason = False
    flagged: list[int] = []

    for idx, task in enumerate(items):
        total += 1
        v = justify_task(task)
        if v.deterministic_eligible:
            # A deterministic path exists — this is a "make it a check" win, not a
            # subagent spawn. Bucket it separately and flag it for the human.
            deterministic_eligible += 1
            flagged.append(idx)
            continue
        # Every non-deterministic task is an INTENDED model spawn in the plan.
        subagent_tasks += 1
        if v.role == "general-purpose":
            general_purpose += 1
            # Only an EXPLICIT missing-role-reason flags gp_without_reason —
            # not an inline-able or no-signal challenge that happens to also be
            # general-purpose (structured code, not string-match).
            if v.challenge_code == "missing_role_reason":
                gp_without_reason = True
        if v.challenge is not None:
            unjustified += 1
            flagged.append(idx)

    share = (unjustified / subagent_tasks) if subagent_tasks else 0.0
    challenged = (
        (subagent_tasks > 0 and share >= unjustified_share_threshold)
        or gp_without_reason
        or deterministic_eligible > 0
    )

    message = (
        f"{unjustified} of {subagent_tasks} subagent(s) unjustified; "
        f"{deterministic_eligible} deterministic-eligible; "
        f"{general_purpose} general-purpose"
        if challenged
        else f"subagent plan OK ({subagent_tasks} justified, "
        f"{deterministic_eligible} deterministic)"
    )

    return PlanChallenge(
        total=total,
        subagent_tasks=subagent_tasks,
        deterministic_eligible=deterministic_eligible,
        unjustified=unjustified,
        general_purpose=general_purpose,
        flagged_indices=tuple(flagged),
        challenged=challenged,
        message=message,
    )


def preview_line(challenge: PlanChallenge) -> str:
    """One bounded line for the cost preview (deterministic-first labelling)."""
    tag = "⚠ CHALLENGE" if challenge.challenged else "✓ subagent gate"
    return f"{tag}: {challenge.message}"


# ── R-008: dispatch-reason/budget checklist ─────────────────────────────────
#
# R-008 ("No speculative agents — every dispatch requires a work-order ID,
# contract, reason, scope, expected artifact, budget reservation") per
# .renmark/plans/r-0.2/dispatch-reason-budget-design.md. This extends the
# existing justification gate above rather than forking a new module — the
# Q1-Q4 checks answer "should this be a subagent at all"; the checklist below
# answers "does this dispatch carry the six required fields", checked BEFORE
# any inference call.
#
# Migration path (design doc §8): ships lenient by default (Phase 1 —
# warn + infer, never hard-reject) so today's callers keep working; a
# ``strict=True`` caller opts into hard rejection ahead of the eventual
# strict-by-default phase.


class R008DispatchRejected(ValueError):
    """Raised in strict mode when a dispatch is missing required R-008 fields."""

    def __init__(self, missing: list[str]) -> None:
        self.missing = list(missing)
        joined = ", ".join(self.missing)
        super().__init__(f"R-008 dispatch rejected: missing required field(s): {joined}")


@dataclass(frozen=True)
class R008Checklist:
    """R-008 dispatch requirements — must be present before inference call."""

    work_order_id: str | None
    contract: str | None
    reason: str | None
    scope: dict | None  # {target_files, read_only_files, prohibited_files}
    expected_artifact: str | None
    budget_reservation: dict | None  # {max_input_tokens, max_output_tokens, max_attempts}

    @property
    def all_present(self) -> bool:
        """True iff all six required fields are present and non-empty."""
        return all(
            [
                self.work_order_id,
                self.contract,
                self.reason,
                self.scope,
                self.expected_artifact,
                self.budget_reservation,
            ]
        )

    def missing_fields(self) -> list[str]:
        """Return list of field names that are missing or empty."""
        missing = []
        if not self.work_order_id:
            missing.append("work_order_id")
        if not self.contract:
            missing.append("contract")
        if not self.reason:
            missing.append("reason")
        if not self.scope:
            missing.append("scope")
        if not self.expected_artifact:
            missing.append("expected_artifact")
        if not self.budget_reservation:
            missing.append("budget_reservation")
        return missing


def _r008_checklist_from_spec(dispatch_spec: Any) -> R008Checklist:
    """Build an :class:`R008Checklist` from a dict-like (or attr-like) dispatch spec."""
    getter = dispatch_spec.get if isinstance(dispatch_spec, dict) else None

    def _field(name: str) -> Any:
        if getter is not None:
            return getter(name)
        return getattr(dispatch_spec, name, None)

    return R008Checklist(
        work_order_id=_field("work_order_id"),
        contract=_field("contract"),
        reason=_field("reason"),
        scope=_field("scope"),
        expected_artifact=_field("expected_artifact"),
        budget_reservation=_field("budget_reservation"),
    )


def validate_r008_dispatch(dispatch_spec: Any) -> tuple[bool, list[str]]:
    """Check that a dispatch carries all R-008 required fields.

    Returns: (is_valid, missing_field_names). Pure function, never raises —
    an unusable ``dispatch_spec`` degrades to "all six fields missing" rather
    than raising, matching the module's conservative-degrade convention.
    """
    try:
        checklist = _r008_checklist_from_spec(dispatch_spec)
    except Exception:
        checklist = R008Checklist(None, None, None, None, None, None)
    return checklist.all_present, checklist.missing_fields()


def enforce_r008_dispatch(dispatch_spec: Any, *, strict: bool = False) -> list[str]:
    """Pre-dispatch R-008 gate — call BEFORE any inference/Agent call.

    Lenient mode (``strict=False``, the default — Phase 1 of the migration
    path in the design doc): missing fields never block dispatch. Returns the
    list of missing field names (empty when the checklist is fully satisfied)
    so a caller can log a warning without breaking existing dispatch sites.

    Strict mode (``strict=True``): raises :class:`R008DispatchRejected` naming
    every missing field when the checklist is not fully satisfied. Never
    silently proceeds in strict mode.
    """
    valid, missing = validate_r008_dispatch(dispatch_spec)
    if not valid and strict:
        raise R008DispatchRejected(missing)
    return missing


# ── Capability envelope: per-control × per-host enforcement status ───────────
#
# The capability envelope answers a different question than the two gates
# above.  ``justify_task`` answers "should this be a subagent at all";
# ``validate_r008_dispatch`` answers "does this dispatch carry its six
# required fields"; :func:`check_capability_envelope` answers "for the scope
# this dispatch is asking for, which controls are actually ENFORCED on this
# host, and which are only advisory or verified after the fact".
#
# All three are separate, composable, zero-LLM checks a caller runs together
# in the same pre-dispatch funnel — none calls the others.  A caller runs
# ``justify_task`` → ``validate_r008_dispatch`` → ``check_capability_envelope``
# and decides on the combined result; keeping them independent means a caller
# that only needs one does not pay for the other two, and adding a control
# dimension here never perturbs the justification or R-008 verdicts.
# A fourth, equally independent check, :func:`check_failure_rule_constraints`,
# joins this same funnel further below — it answers "does any active,
# curated failure rule constrain this dispatch's applicability" and likewise
# calls none of the other three.
#
# The honesty requirement is the point of this table: a ``passed=True`` on a
# dimension whose status is ``"advisory"``, ``"unsupported"``, or
# ``"verified_after"`` is NOT evidence the control was enforced pre-dispatch.
# Each verdict therefore carries its ``status`` alongside ``passed`` and says
# so in ``reason``, so no caller can read a pass as an enforcement claim.

#: Per-control × per-host enforcement status.  One of:
#:   ``"enforced"``       — checked pre-dispatch by code in this repo.
#:   ``"verified_after"`` — not checked pre-dispatch on this host; the actual
#:                          check happens post-action (``fast_path.verify_worker_scope``).
#:   ``"advisory"``       — recorded as a constraints-object statement only;
#:                          no code-level enforcement mechanism confirmed.
#:   ``"unsupported"``    — no enforcement mechanism wired at all.
#: This is the table approved at the dispatch gate for this release — it is a
#: statement of what is true today, not an aspiration.  Do not upgrade a
#: status here without landing the mechanism that backs it.
ENVELOPE_CONTROL_STATUS: dict[str, dict[str, str]] = {
    "path": {"claude": "enforced", "codex": "verified_after"},
    "command": {"claude": "enforced", "codex": "enforced"},
    "spend_timeout": {"claude": "enforced", "codex": "enforced"},
    "network_domain": {"claude": "advisory", "codex": "advisory"},
    "git_action": {"claude": "advisory", "codex": "advisory"},
    "external_action": {"claude": "unsupported", "codex": "unsupported"},
}

#: Stable evaluation order for :func:`check_capability_envelope` — callers get
#: one verdict per dimension, always in this order.
ENVELOPE_CONTROLS: tuple[str, ...] = (
    "path",
    "command",
    "spend_timeout",
    "network_domain",
    "git_action",
    "external_action",
)

_ADVISORY_REASON: str = (
    "advisory only — no code-level enforcement mechanism confirmed this "
    "release; recorded as a constraints-object statement only."
)
_UNSUPPORTED_REASON: str = "unsupported — no enforcement mechanism wired for this control."


def control_status(control: str, host: str) -> str:
    """Return the enforcement status for *control* on *host*.

    Never raises and never yields a ``KeyError``: an unknown control, an
    unknown host, or a non-string argument all degrade to ``"unsupported"`` —
    the conservative answer, since an unrecognised pair demonstrably has no
    enforcement mechanism behind it.
    """
    try:
        return ENVELOPE_CONTROL_STATUS.get(str(control), {}).get(str(host), "unsupported")
    except Exception:
        return "unsupported"


@dataclass(frozen=True)
class EnvelopeVerdict:
    """One control dimension's pre-dispatch verdict.

    Same non-raising verdict shape convention :class:`SubagentVerdict` uses.
    ``passed`` is only an enforcement claim when ``status == "enforced"`` —
    for ``"verified_after"`` / ``"advisory"`` / ``"unsupported"`` a
    ``passed=True`` means "this gate did not and cannot decide here", and
    ``reason`` says so explicitly.
    """

    passed: bool
    control: str
    host: str
    status: str
    reason: str
    violations: tuple[str, ...] = ()


def _envelope_globs(allowed_targets: Any) -> tuple[str, ...]:
    """Split a profile's ``allowed_targets`` string into fnmatch globs.

    ``allowed_targets`` is a comma-separated human-readable field: several
    profiles append a parenthetical annotation (``".renmark/reviews/**/*.md
    (read-only review of any file)"``) and ``general-purpose`` declares the
    sentinel ``"any (fallback — no target restriction)"``.  Annotations are
    stripped so they can never become a glob that matches nothing, and an
    empty result means "no restriction declared" — matching the module-wide
    non-denial-by-default convention (see ``ProfileSpec.allowed_commands``).
    """
    if not isinstance(allowed_targets, str):
        return ()
    globs: list[str] = []
    for chunk in allowed_targets.split(","):
        piece = chunk.strip()
        # Drop a trailing parenthetical annotation, then re-strip.
        if "(" in piece:
            piece = piece.split("(", 1)[0].strip()
        if not piece or piece.lower() == "any":
            continue
        globs.append(piece)
    return tuple(globs)


def _envelope_path_verdict(role: str, requested_scope: dict, host: str) -> EnvelopeVerdict:
    """Path-scope dimension — enforced on Claude, verified post-action on Codex."""
    status = control_status("path", host)
    if status != "enforced":
        return EnvelopeVerdict(
            passed=True,
            control="path",
            host=host,
            status=status,
            reason=(
                f"{host}: path scope verified post-action via "
                "fast_path.verify_worker_scope only, not pre-dispatch — "
                "passed=True here is NOT an enforcement claim."
            ),
        )

    paths = requested_scope.get("paths") or []
    if not isinstance(paths, (list, tuple)):
        paths = []
    spec = subagent_profiles.profile_of(role)
    globs = _envelope_globs(getattr(spec, "allowed_targets", None))
    if not globs:
        return EnvelopeVerdict(
            passed=True,
            control="path",
            host=host,
            status=status,
            reason=f"role={role}: no target restriction declared — nothing to enforce",
        )

    violations = tuple(
        str(p)
        for p in paths
        if not any(fnmatch.fnmatch(str(p).replace("\\", "/"), g) for g in globs)
    )
    if violations:
        return EnvelopeVerdict(
            passed=False,
            control="path",
            host=host,
            status=status,
            reason=(
                f"role={role}: {len(violations)} requested path(s) outside "
                f"allowed_targets ({', '.join(globs)})"
            ),
            violations=violations,
        )
    return EnvelopeVerdict(
        passed=True,
        control="path",
        host=host,
        status=status,
        reason=f"role={role}: all {len(paths)} requested path(s) within allowed_targets",
    )


def _envelope_command_verdict(role: str, requested_scope: dict, host: str) -> EnvelopeVerdict:
    """Command-allowlist dimension — enforced pre-dispatch on both hosts."""
    status = control_status("command", host)
    commands = requested_scope.get("commands") or []
    if not isinstance(commands, (list, tuple)):
        commands = []
    spec = subagent_profiles.profile_of(role)
    allowed = getattr(spec, "allowed_commands", ()) or ()
    if not allowed:
        return EnvelopeVerdict(
            passed=True,
            control="command",
            host=host,
            status=status,
            reason=f"role={role}: empty allowed_commands — no command restriction declared",
        )

    allowed_set = {str(c) for c in allowed}
    violations = tuple(str(c) for c in commands if str(c) not in allowed_set)
    if violations:
        return EnvelopeVerdict(
            passed=False,
            control="command",
            host=host,
            status=status,
            reason=(
                f"role={role}: {len(violations)} requested command(s) outside "
                f"allowed_commands ({', '.join(sorted(allowed_set))})"
            ),
            violations=violations,
        )
    return EnvelopeVerdict(
        passed=True,
        control="command",
        host=host,
        status=status,
        reason=f"role={role}: all {len(commands)} requested command(s) in allowed_commands",
    )


def _envelope_spend_verdict(role: str, requested_scope: dict, host: str) -> EnvelopeVerdict:
    """Spend/timeout-ceiling dimension — delegates to ``cost.check_spend_timeout_ceiling``."""
    status = control_status("spend_timeout", host)
    verdict = cost.check_spend_timeout_ceiling(
        requested_scope.get("budget"), tier=subagent_profiles.profile_tier(role)
    )
    return EnvelopeVerdict(
        passed=bool(verdict.passed),
        control="spend_timeout",
        host=host,
        status=status,
        reason=str(verdict.reason),
        violations=() if verdict.passed else (str(verdict.reason),),
    )


def check_capability_envelope(
    role: str, requested_scope: dict, *, host: str = "claude"
) -> tuple[EnvelopeVerdict, ...]:
    """Evaluate EVERY capability-envelope control for *role* on *host*.

    Returns one :class:`EnvelopeVerdict` per dimension in
    :data:`ENVELOPE_CONTROLS` order — never a single collapsed verdict, because
    a caller must be able to see which controls were actually enforced and
    which merely reported ``passed=True`` because nothing enforces them here.

    ``requested_scope`` is a caller-built dict with optional keys
    ``paths: list[str]``, ``commands: list[str]``, ``budget: dict | None``.
    A missing key means "nothing requested on that dimension" and passes.

    Composability: this is a peer of :func:`justify_task` and
    :func:`validate_r008_dispatch`, not a caller of either — the same
    relationship those two already have with one another.  Run them together
    in the pre-dispatch funnel and combine the results.

    **Never raises.**  On any unexpected internal error it returns a single
    conservative-failure verdict rather than silently passing.
    """
    try:
        scope: dict = requested_scope if isinstance(requested_scope, dict) else {}
        resolved_host = str(host)
        role_name = str(role)
        return (
            _envelope_path_verdict(role_name, scope, resolved_host),
            _envelope_command_verdict(role_name, scope, resolved_host),
            _envelope_spend_verdict(role_name, scope, resolved_host),
            EnvelopeVerdict(
                passed=True,
                control="network_domain",
                host=resolved_host,
                status=control_status("network_domain", resolved_host),
                reason=_ADVISORY_REASON,
            ),
            EnvelopeVerdict(
                passed=True,
                control="git_action",
                host=resolved_host,
                status=control_status("git_action", resolved_host),
                reason=_ADVISORY_REASON,
            ),
            EnvelopeVerdict(
                passed=True,
                control="external_action",
                host=resolved_host,
                status=control_status("external_action", resolved_host),
                reason=_UNSUPPORTED_REASON,
            ),
        )
    except Exception:
        return (
            EnvelopeVerdict(
                passed=False,
                control="unknown",
                host=str(host) if isinstance(host, str) else "claude",
                status="unsupported",
                reason="gate could not classify — review before dispatch",
            ),
        )


# ── Failure-rule constraints: does an active curated rule bind this dispatch ─
#
# A fourth, independent, zero-LLM, pure, never-raising check — a peer of
# ``justify_task``, ``validate_r008_dispatch``, and ``check_capability_envelope``
# in the same pre-dispatch funnel, calling none of them.  It answers "does any
# ACTIVE curated failure rule (``renmark.recurrence.load_failure_rules``)
# constrain the applicability this dispatch is asking for" — a ``proposed`` or
# ``deprecated`` rule is never matched, only ``status == "active"``.


@dataclass(frozen=True)
class FailureRuleVerdict:
    """The failure-rule-constraint verdict for one dispatch's applicability.

    Same non-raising verdict-shape convention :class:`SubagentVerdict` /
    :class:`EnvelopeVerdict` already use in this file. ``challenge`` is
    non-None (and names each matched rule's ``rule_id`` + ``prohibited_failure``)
    when one or more active rules match; ``reason`` always names the matched
    ``rule_id``(s) when any exist, never a bare summary with no id.
    """

    passed: bool
    matched_rule_ids: tuple[str, ...]
    challenge: str | None
    reason: str


def check_failure_rule_constraints(
    repo: str | os.PathLike[str], applicability: str, *, host: str = "claude"
) -> FailureRuleVerdict:
    """Check *applicability* against the repo's ACTIVE curated failure rules.

    Matches a rule when its ``applicability`` string and the caller's
    ``applicability`` argument share at least one case-insensitive
    whitespace-split token — simple, deterministic keyword overlap, no fuzzy
    matching, no LLM call. Only ``status == "active"`` rules are ever matched;
    a ``proposed`` or ``deprecated`` rule is never matched.

    **Never raises.** On any error reading the registry (missing repo,
    malformed state, etc.) this degrades to the conservative "no constraints"
    answer — matching this module's never-raises, safe-degrade convention —
    rather than blocking a dispatch on a registry the gate cannot read.
    """
    try:
        rules = recurrence.load_failure_rules(repo)
    except Exception:
        return FailureRuleVerdict(
            passed=True,
            matched_rule_ids=(),
            challenge=None,
            reason="failure-rule registry unavailable; treated as no constraints",
        )

    try:
        caller_tokens = {tok.lower() for tok in str(applicability or "").split()}
        matched: list[recurrence.FailureRule] = []
        for rule in rules:
            if rule.status != "active":
                continue
            rule_tokens = {tok.lower() for tok in str(rule.applicability or "").split()}
            if caller_tokens & rule_tokens:
                matched.append(rule)

        if not matched:
            return FailureRuleVerdict(
                passed=True,
                matched_rule_ids=(),
                challenge=None,
                reason=f"no active failure rule matches applicability={applicability!r}",
            )

        matched_ids = tuple(rule.rule_id for rule in matched)
        challenge = "; ".join(
            f"{rule.rule_id}: {rule.prohibited_failure}" for rule in matched
        )
        reason = f"matched active failure rule(s): {', '.join(matched_ids)}"
        return FailureRuleVerdict(
            passed=False,
            matched_rule_ids=matched_ids,
            challenge=challenge,
            reason=reason,
        )
    except Exception:
        return FailureRuleVerdict(
            passed=True,
            matched_rule_ids=(),
            challenge=None,
            reason="failure-rule registry unavailable; treated as no constraints",
        )


def apply_failure_rule_constraints(
    existing_constraints: dict | None,
    verdict: FailureRuleVerdict,
    rules: Sequence[Any],
) -> dict:
    """Return a NEW constraints dict with matched failure rules attached.

    Pure — never mutates ``existing_constraints`` in place. Populates a
    ``"failure_rules"`` key listing, for each id in
    ``verdict.matched_rule_ids``, a small ``{"rule_id", "required_behavior",
    "prohibited_failure"}`` dict pulled from ``rules``. This is the function a
    caller uses to populate ``WorkOrder.constraints`` (Release 3's placeholder
    field) — it does not call ``dispatch.build_subagent_input`` or write
    prompt text anywhere; the existing ``dispatch.build_subagent_input``
    funnel remains the sole prompt-composition pathway.
    """
    result = dict(existing_constraints or {})
    by_id = {getattr(rule, "rule_id", None): rule for rule in rules}
    failure_rules: list[dict[str, str]] = []
    for rule_id in verdict.matched_rule_ids:
        rule = by_id.get(rule_id)
        if rule is None:
            continue
        failure_rules.append(
            {
                "rule_id": rule.rule_id,
                "required_behavior": rule.required_behavior,
                "prohibited_failure": rule.prohibited_failure,
            }
        )
    result["failure_rules"] = failure_rules
    return result


# ── Inspector lens selection: which falsification perspective to apply ───────
#
# This answers a different question than everything above.  ``justify_task``
# decides whether a subagent is warranted at all; ``validate_r008_dispatch``
# checks a dispatch's required fields; ``check_capability_envelope`` decides
# which controls are actually ENFORCED for what a Worker may touch.
# :func:`resolve_lens_for` answers none of that — it picks which falsification
# perspective an *Inspector* (the independent reviewer, not the Worker) should
# apply when assessing a Work Result.  Same orbit, deliberately NOT wired into
# ``check_capability_envelope`` and NOT the same function as, nor a caller of,
# ``cost.requires_escalation`` — that decides model-tier escalation, this
# decides review perspective.  A future reader should not try to merge them;
# they answer different questions and are kept as separate, self-contained
# table+function pairs, mirroring ``ENVELOPE_CONTROL_STATUS``/``control_status``
# above.

LensName = str

#: The lens vocabulary named in the original proposal (survey.md Requirement 5:
#: "maintainer lens", "skeptical user", "competitor lens").
LENS_NAMES: tuple[str, ...] = ("maintainer", "skeptical_user", "competitor")


def resolve_lens_for(work_order: Any) -> str:
    """Return the falsification lens an Inspector should apply for *work_order*.

    Duck-typed on ``work_order`` — reads ``getattr(work_order, "risk_tier",
    None)`` and ``getattr(work_order, "file_scope", None)`` — never assumes a
    real ``ledger.WorkOrder`` instance, so this module never needs to import
    ``ledger`` at module import time.

    Policy:
      - ``risk_tier in ("high", "critical")`` → ``"skeptical_user"`` (an
        outside adversarial read is warranted at elevated risk).
      - ``risk_tier == "medium"`` and ``file_scope`` touches more than one
        file → ``"competitor"`` (cross-file changes benefit from a
        rival-implementation read).
      - everything else, including ``risk_tier in (None, "low")`` or any
        malformed/missing input → ``"maintainer"`` (the default, lowest-cost
        lens).

    Never raises: on ``None``, a missing ``risk_tier``, or any malformed
    input, degrades to the safe default ``"maintainer"``.
    """
    try:
        risk_tier = str(getattr(work_order, "risk_tier", None) or "").strip().lower()
        if risk_tier in ("high", "critical"):
            return "skeptical_user"
        if risk_tier == "medium":
            file_scope = getattr(work_order, "file_scope", None)
            try:
                scope_len = len(file_scope) if file_scope is not None else 0
            except Exception:
                scope_len = 0
            if scope_len > 1:
                return "competitor"
        return "maintainer"
    except Exception:
        return "maintainer"


def main(argv: list[str] | None = None) -> int:
    """CLI: ``python -m renmark.subagent_gate <plan.md>``.

    Deterministic pre-flight gate — mirrors ``python -m renmark.plan_lint``. Prints
    the one-line challenge verdict and exits 0 when the subagent plan is clean, 1
    when it is challenged (a deterministic path exists, an unjustified spawn, or an
    unexplained general-purpose role). Exit 2 on a usage/parse error. Zero-LLM.
    """
    import sys

    from renmark import parser

    args = argv if argv is not None else sys.argv[1:]
    if not args:
        sys.stderr.write("usage: python -m renmark.subagent_gate <plan.md>\n")
        return 2
    try:
        tasks = parser.parse_plan(args[0])
    except Exception as exc:
        sys.stderr.write(f"subagent-gate: cannot read plan: {exc}\n")
        return 2
    ch = challenge_plan(tasks)
    sys.stdout.write(preview_line(ch) + "\n")
    return 1 if ch.challenged else 0


if __name__ == "__main__":
    raise SystemExit(main())

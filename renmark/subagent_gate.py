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

from dataclasses import dataclass, field
from typing import Any

from renmark import cost, subagent_profiles

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

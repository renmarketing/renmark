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


class DispatchIndependenceError(LedgerValidationError):
    """Raised when an :class:`InspectionReport` fails the dispatch-independence
    check against the :class:`WorkResult` it inspects (R-0.4, WP-2).

    Raised — never returned as ``False``/logged-and-continued — when the
    inspector's ``dispatch_identity`` equals the worker's, or when the
    inspector's ``dispatch_identity`` is empty (an unset identity cannot prove
    independence, so it is treated as "independence unproven", not
    "independence assumed").
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

    The fields below ``repairs_finding_ref`` are additive/optional per
    ``.renmark/rethink/governed-orchestration-assurance/roadmap.md``
    Release 3's field table. They are schema-present as of Release 3 but
    most have their real enforcement/consumption deferred to later
    releases (Release 4/6/8/10/11/13 per that table) — adding them here
    only reserves the schema slot; it does not wire enforcement.
    ``risk_tier`` stays a plain ``str | None`` (no runtime type change) but
    is now backed by :data:`RISK_TIERS` and :func:`classify_risk_tier`
    (Release 8) — valid values are one of ``RISK_TIERS``
    (``"low"``/``"medium"``/``"high"``/``"critical"``), and
    :func:`classify_risk_tier` is the deterministic, zero-model-call rule
    that derives a tier from a ``WorkOrder``'s ``file_scope`` (plus an
    optional caller-attached ``complexity`` duck-typed attribute).
    Existing placeholder string values already stored on this field
    remain valid — this is additive documentation, not a schema change.

    ``inspection_contract`` (Release 8, additive/optional) carries the
    PRE-dispatch :class:`InspectionContract` for this order — what
    inspection *should* happen. It stays ``None`` for hand-constructed
    orders; :func:`work_order_for_task` populates a minimal one by default
    (opt out with ``auto_contract=False``).
    """

    order_id: str = ""
    task: str = ""
    role: str = ""  # e.g. "code-implementer", "reviewer" — the dispatch role
    file_scope: list[str] = field(default_factory=list)
    verifier: str = ""
    is_repair: bool = False
    repairs_finding_ref: str | None = None
    risk_tier: str | None = None
    capability_envelope_ref: str | None = None
    lens: str | None = None
    inspection_contract: InspectionContract | None = None
    schema_version: int = 1
    correlation_id: str | None = None
    idempotency_key: str | None = None
    dependencies: list[str] = field(default_factory=list)
    scope: dict | None = None
    budget: dict | None = None
    routing: dict | None = None
    constraints: dict | None = None
    interaction_policy: dict | None = None


def work_order_for_task(
    task: Any,
    role: str,
    *,
    order_id: str | None = None,
    auto_contract: bool = True,
    **kwargs: Any,
) -> WorkOrder:
    """Build a :class:`WorkOrder` from a ``renmark.parser.Task``-like object.

    Duck-typed on purpose (reads ``task.spec``/``task.target``/
    ``task.context_files``/``task.verifier``/``task.index``) rather than
    importing ``renmark.parser.Task`` at module import time, to avoid an
    import cycle — this mirrors the pattern
    ``dispatch.build_subagent_input`` already uses when it reads the same
    ``Task`` fields to build a ``SubagentInput``.

    ``task`` (the payload string) comes from ``task.spec``, matching what
    ``build_subagent_input`` uses for its own ``task_spec``. ``file_scope``
    is ``task.target`` plus ``task.context_files``. ``verifier`` is
    ``task.verifier``. When ``order_id`` is not supplied it is generated
    deterministically from ``task.index`` (falling back to ``task.title``
    when no ``index`` is present) — Release 3's value proposition is
    closing the ``order_id`` reference gap, so this never leaves
    ``order_id`` empty.

    Any of the new Release-3 schema-only fields (``risk_tier``,
    ``capability_envelope_ref``, ``lens``, ``schema_version``,
    ``correlation_id``, ``idempotency_key``, ``dependencies``, ``scope``,
    ``budget``, ``routing``, ``constraints``, ``interaction_policy``) can
    be supplied via ``**kwargs``; unsupplied ones stay at their
    dataclass defaults. This function only constructs a valid canonical
    ``WorkOrder`` — it performs no enforcement.

    **Auto-contract (Release 8).** Unless the caller supplies
    ``inspection_contract`` explicitly (or passes ``auto_contract=False``),
    a minimal :class:`InspectionContract` is attached: ``risk_tier`` comes
    from the caller's explicit ``risk_tier`` kwarg when present, otherwise
    from :func:`classify_risk_tier` on the in-progress order; ``lenses``
    comes from ``subagent_gate.resolve_lens_for``. Contract construction
    never mutates the order's own ``risk_tier``/``lens`` fields — a caller
    that passed those explicitly gets exactly those values back — and
    **never raises**: any failure (import problem, bad classifier output)
    degrades to ``inspection_contract=None`` so a broken contract path can
    never break work-order construction itself.
    """
    if order_id is None:
        index = getattr(task, "index", None)
        if index is not None:
            order_id = f"task-{index}"
        else:
            title = getattr(task, "title", "") or ""
            order_id = f"task-{title}" if title else "task-unknown"

    task_spec = getattr(task, "spec", "") or ""
    target = getattr(task, "target", None)
    context_files = getattr(task, "context_files", None) or []
    file_scope = [f for f in [target, *context_files] if f]
    verifier = getattr(task, "verifier", "") or ""

    order = WorkOrder(
        order_id=order_id,
        task=task_spec,
        role=role,
        file_scope=file_scope,
        verifier=verifier,
        **kwargs,
    )

    if auto_contract and kwargs.get("inspection_contract") is None:
        order.inspection_contract = _auto_inspection_contract(order)

    return order


def _auto_inspection_contract(order: WorkOrder) -> InspectionContract | None:
    """Build the default :class:`InspectionContract` for *order*, or ``None``.

    Never raises — every failure path returns ``None`` (see
    :func:`work_order_for_task`'s auto-contract contract).
    """
    try:
        from .subagent_gate import resolve_lens_for

        risk_tier = order.risk_tier or classify_risk_tier(order)
        if risk_tier not in RISK_TIERS:
            return None

        # Resolve the lens against the EFFECTIVE tier without mutating the
        # order: a caller-supplied risk_tier/lens must round-trip unchanged.
        lens_probe = WorkOrder(file_scope=list(order.file_scope), risk_tier=risk_tier)
        lens = resolve_lens_for(lens_probe)

        return InspectionContract(
            contract_id=f"{order.order_id}-contract",
            version=1,
            risk_tier=risk_tier,
            lenses=[lens],
            deterministic_gates=[],
            semantic_rubric_ref=None,
            independent_judge_required=risk_tier in ("high", "critical"),
            evidence_required=[],
        )
    except Exception:
        return None


@dataclass
class WorkResult:
    """What a Worker returns for a given :class:`WorkOrder`."""

    order_id: str = ""
    status: str = ""  # e.g. "complete" | "partial" | "failed"
    summary: str = ""
    touched_files: list[str] = field(default_factory=list)
    artifact_refs: list[str] = field(default_factory=list)
    dispatch_identity: str = ""  # who/what dispatch produced this result (R-0.4, WP-2)


@dataclass
class InspectionReport:
    """What a reviewer/verifier produces for a piece of work.

    Shape follows the fields already in live use across
    ``.renmark/reviews/*.json`` (verdict/findings/generator).

    ``risk_tier`` / ``lens`` are additive Release 8 fields (schema-only —
    no enforcement wired here). ``verdict`` keeps its existing
    ``pass``/``fail``/``escalate`` semantics (:data:`VERDICTS`) unchanged;
    ``risk_tier`` is a separate, orthogonal axis (see :data:`RISK_TIERS` /
    :func:`classify_risk_tier`), not a replacement for it.

    ``contract_ref`` (additive, Release 8) names the
    ``contract_id:version`` of the :class:`InspectionContract` this report
    was graded against — e.g. ``"task-3-contract:1"``. It is the ONLY link
    between the pre-dispatch contract and this post-dispatch record; the
    two shapes stay separate on purpose.

    ``judge_evidence`` (additive, Release 9) is an optional reference-only
    pointer at a ``judge.JudgeEvidenceRef`` — the evidence produced by the
    live LLM-as-judge eval tier. It is attached to this report, never
    merged into it, and it does NOT override ``verdict``: ``VERDICTS``
    remains the sole verdict vocabulary, and ``judge_evidence`` cannot set
    or change a report's ``verdict`` value.
    """

    subject_ref: str = ""  # what was inspected (order_id, file, artifact path)
    verdict: str = ""  # e.g. "pass" | "fail" | "changes_requested"
    findings: list[str] = field(default_factory=list)
    generator: str = ""
    dispatch_identity: str = ""  # who/what dispatch produced this verdict (R-0.4, WP-2)
    risk_tier: str | None = None
    lens: str | None = None
    contract_ref: str | None = None  # "contract_id:version" graded against
    judge_evidence: "JudgeEvidenceRef | None" = None  # reference-only, never overrides verdict


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
    issues += _check_str(data, "dispatch_identity", required=False)
    return issues


def validate_inspection_report(data: dict[str, Any]) -> list[str]:
    """Return a list of validation issues for an Inspection Report payload (empty = valid)."""
    issues: list[str] = []
    issues += _check_str(data, "subject_ref")
    issues += _check_str(data, "verdict")
    issues += _check_str_list(data, "findings")
    issues += _check_str(data, "generator", required=False)
    issues += _check_str(data, "dispatch_identity", required=False)
    issues += _check_opt_str(data, "risk_tier")
    issues += _check_opt_str(data, "lens")
    issues += _check_opt_str(data, "contract_ref")
    if "judge_evidence" in data and data["judge_evidence"] is not None:
        if not isinstance(data["judge_evidence"], dict):
            issues.append(
                f"'judge_evidence' must be a dict or null, got "
                f"{type(data['judge_evidence']).__name__}"
            )
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


# ── Dispatch independence check (R-0.4, WP-2) ────────────────────────────
#
# Pure check — no I/O, no ledger write. Callers (WP-4) invoke this before
# appending an InspectionReport so a same-identity self-graded verdict is
# rejected before it ever reaches the ledger. This function raises on
# failure; it never returns False or logs-and-continues.


def check_dispatch_independence(
    repo: Path | str,
    work_result_dispatch_identity: str,
    inspector_dispatch_identity: str,
) -> None:
    """Raise :class:`DispatchIndependenceError` unless the inspector's dispatch
    is provably independent of the worker's dispatch.

    ``repo`` is accepted (unused by this pure comparison today) so the
    signature matches this module's other ``repo``-first functions and so a
    future revision can look up ledger context without changing callers.

    Rejects (raises) when:

    - ``inspector_dispatch_identity`` is empty/blank — an unset inspector
      identity cannot prove independence, so it is treated as "independence
      unproven", never "independence assumed".
    - ``inspector_dispatch_identity == work_result_dispatch_identity`` and
      both are non-empty — the mechanical self-grading signal: the same
      dispatch invocation producing both the work and its own inspection.

    An empty ``work_result_dispatch_identity`` does not by itself fail this
    check (an old, pre-R-0.4 WorkResult may legitimately have no identity
    recorded); it is the inspector side emptiness that is disqualifying,
    per WP-1's design decision.
    """
    del repo  # unused today; kept for signature consistency with this module

    inspector = inspector_dispatch_identity.strip() if isinstance(
        inspector_dispatch_identity, str
    ) else ""
    worker = work_result_dispatch_identity.strip() if isinstance(
        work_result_dispatch_identity, str
    ) else ""

    if not inspector:
        raise DispatchIndependenceError(
            "inspector dispatch_identity is empty; independence unproven "
            "(an unset inspector identity can never demonstrate independence "
            "from the worker that produced the work being inspected)"
        )

    if worker and inspector == worker:
        raise DispatchIndependenceError(
            f"inspector dispatch_identity {inspector_dispatch_identity!r} "
            "matches the work result's dispatch_identity; a dispatch cannot "
            "independently inspect its own work"
        )


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


# ── Inspector verdict emit/read helpers (R-0.4, WP-3) ────────────────────
#
# Per WP-1's design (`.renmark/plans/2026-08-01-r-0.4-wp1-inspector-design.md`
# §1), `InspectionReport` has no separate "work_result_id"/"work_order_id"
# field — `WorkResult` carries `order_id`, not its own id, and
# `WorkOrder.order_id == WorkResult.order_id` for a given pair, so the
# existing `subject_ref` field unambiguously identifies both the order and
# the result being inspected. `emit_inspection_verdict` therefore writes
# `subject_ref = work_result_id` (callers pass `work_order_id` too, for
# call-site clarity/future divergence, but today it must equal
# `work_result_id` — mismatches are rejected loud rather than silently
# picking one).

VERDICTS: tuple[str, ...] = ("pass", "fail", "escalate")


# ── Inspection contract (Release 8) ──────────────────────────────────────
#
# Declared HERE rather than beside the other dataclasses above because its
# ``allowed_verdicts`` default is :data:`VERDICTS`, which is defined at this
# point in the module. ``from __future__ import annotations`` makes the
# forward reference on ``WorkOrder.inspection_contract`` (declared earlier)
# a lazy string, so the split placement is safe.


@dataclass
class InspectionContract:
    """The PRE-dispatch plan for what inspection *should* happen.

    Deliberately separate from :class:`InspectionReport`, which is the
    POST-dispatch record of what inspection *did* happen (per
    ``.renmark/rethink/governed-orchestration-assurance/
    target-blueprint.md`` §3.5 and the Release 8 roadmap revision,
    peer-review Gap 3). The two shapes are connected only by a reference
    field — :attr:`InspectionReport.contract_ref` — and are never merged:
    a contract is versioned and authored before any work is dispatched; a
    report is evidence produced after the fact.

    ``allowed_verdicts`` defaults to :data:`VERDICTS` and exists so a
    contract can *narrow* the verdict vocabulary for a given inspection.
    It must never widen it beyond :data:`VERDICTS` — there is exactly one
    verdict vocabulary in this module and it is :data:`VERDICTS`.

    Schema-only as of Release 8: no validator is registered in
    ``_VALIDATOR_BY_KIND`` and this is not a :data:`LedgerEvent` member, so
    an ``InspectionContract`` is never written to the ledger on its own —
    it travels nested inside :attr:`WorkOrder.inspection_contract`.
    """

    contract_id: str = ""
    version: int = 1
    risk_tier: str | None = None
    lenses: list[str] = field(default_factory=list)
    deterministic_gates: list[str] = field(default_factory=list)
    semantic_rubric_ref: str | None = None
    independent_judge_required: bool = False
    evidence_required: list[str] = field(default_factory=list)
    allowed_verdicts: tuple[str, ...] = VERDICTS


# ── Risk-tier classification (Release 8) ─────────────────────────────────
#
# Deterministic, zero-model-call classifier per
# ``.renmark/rethink/governed-orchestration-assurance/
# release-8-risk-tier-spike-finding.md``. That finding hand-validated a
# rule (v1), found a 25% disagreement rate against hand judgment, revised
# it (v2), re-spiked v2 against a fresh 20-dispatch sample (also 25%
# disagreement, different composition), and the Owner then approved
# coding v3 = v2 + four named fixes (2026-08-05 decision at the bottom of
# that finding):
#
#   1. Branch-order fix — ``is_test`` is checked BEFORE the
#      ``complexity == "hard"`` short-circuit, so a hard-complexity test
#      file is floored by its test-ness (never bare "high"/"critical"
#      just because it's expensive to write).
#   2. ``renmark/lifecycle.py`` added to the critical-module set (it
#      gates merge/release/security signoff and was missing from both
#      v1's and v2's lists — the re-spike's #8 mismatch).
#   3. The pipeline-skill doc exception is extended to also cover
#      ``plugin/skills/.shared/*.md`` governance fragments (not just
#      ``plugin/skills/*/SKILL.md``) — the re-spike's #9 mismatch.
#   4. The "non-test, non-doc production file floors at 'medium'
#      regardless of declared complexity" branch is kept AS-IS even
#      though it over-classifies some trivial changes (re-spike's #19).
#      This is a deliberate fail-safer-not-lenient design choice, not a
#      bug: over-classification costs extra review time, never safety,
#      and both spike passes agreed that direction is the tolerable one.

RiskTier = str

RISK_TIERS: tuple[str, ...] = ("low", "medium", "high", "critical")

#: Fixed critical-module set (Release 8's v3 rule). Originally 6 entries
#: (Release-8 spike v1), expanded to 9 (v2, adding the three modules
#: responsible for v1's cluster-1 mismatches:
#: ``subagent_profiles.py``/``plan_lint.py``/``cli/_wave_loop.py``), then
#: to 10 (v3 Owner fix #2, adding ``lifecycle.py``).
_CRITICAL_MODULES: frozenset[str] = frozenset(
    {
        "renmark/ledger.py",
        "renmark/dispatch.py",
        "renmark/subagent_gate.py",
        "renmark/fast_path.py",
        "renmark/cost.py",
        "renmark/cli/_engine.py",
        "renmark/subagent_profiles.py",
        "renmark/plan_lint.py",
        "renmark/cli/_wave_loop.py",
        "renmark/lifecycle.py",
    }
)

#: Pipeline `SKILL.md` files whose doc-floor exception applies (v2's fix
#: for v1's cluster-2 mismatch — these are operationally load-bearing
#: dispatch-behavior contracts, not inert reference prose).
_PIPELINE_CRITICAL_SKILLS: frozenset[str] = frozenset(
    {
        "plugin/skills/orchestrate/SKILL.md",
        "plugin/skills/finish/SKILL.md",
        "plugin/skills/debug/SKILL.md",
        "plugin/skills/feature/SKILL.md",
        "plugin/skills/rethink/SKILL.md",
        "plugin/skills/start/SKILL.md",
    }
)

#: v3 Owner fix #3 — the `.shared/*.md` governance fragments those
#: pipeline skills cite normatively get the same doc-floor exception as
#: the named `SKILL.md` files above, matched by path prefix rather than
#: an exhaustive list (this class of file grows independently of any one
#: pipeline).
_PIPELINE_CRITICAL_SHARED_PREFIX = "plugin/skills/.shared/"


def _is_pipeline_critical_doc(path: str) -> bool:
    """True for a doc exempt from the blanket doc-floor-to-``low`` branch."""
    if path in _PIPELINE_CRITICAL_SKILLS:
        return True
    return path.startswith(_PIPELINE_CRITICAL_SHARED_PREFIX) and path.endswith(".md")


def classify_risk_tier(work_order: "WorkOrder") -> str:
    """Deterministically classify ``work_order`` into one of :data:`RISK_TIERS`.

    Zero-model-call, purely field-based rule (Release 8 spike v3 — see the
    module-level comment above this function for the rule's provenance
    and the four Owner-approved v2->v3 fixes). Signals used:

    - ``files`` — ``work_order.file_scope``.
    - ``complexity`` — read via ``getattr(work_order, "complexity", None)``,
      duck-typed the same way ``cost.py``/``sizing.py``/``subagent_gate.py``
      read it off a plan ``Task``. ``WorkOrder`` itself declares no
      ``complexity`` field (that lives on the plan task, not the dispatch
      order); a caller that wants complexity to influence the tier attaches
      it dynamically before calling this function. Missing/unrecognized
      complexity is treated as unknown, never as "hard".

    **Never raises.** Any missing/malformed input — ``work_order is None``,
    a missing/non-list/non-string ``file_scope``, or any unexpected
    exception while inspecting it — degrades to ``"low"``, the
    conservative default that never over-escalates a broken input. The
    return value is always validated to be one of :data:`RISK_TIERS`
    before it is returned; if somehow it were not (defensive-only, should
    be unreachable given the branches below), this also degrades to
    ``"low"`` rather than returning an invalid tier.
    """
    try:
        tier = _classify_risk_tier_inner(work_order)
    except Exception:
        return "low"
    return tier if tier in RISK_TIERS else "low"


def _classify_risk_tier_inner(work_order: "WorkOrder") -> str:
    if work_order is None:
        return "low"

    raw_files = getattr(work_order, "file_scope", None)
    if not isinstance(raw_files, list) or not raw_files:
        return "low"
    files = [f for f in raw_files if isinstance(f, str) and f]
    if not files:
        return "low"

    raw_complexity = getattr(work_order, "complexity", None)
    complexity = raw_complexity.strip().lower() if isinstance(raw_complexity, str) else ""

    hits_critical = any(f in _CRITICAL_MODULES for f in files)
    is_test = all(f.startswith("tests/") or "/test_" in f or f.startswith("test_") for f in files)
    is_doc = all(f.endswith((".md", ".json", ".toml", ".gitignore")) for f in files)
    is_pipeline_critical_doc = is_doc and any(_is_pipeline_critical_doc(f) for f in files)

    if hits_critical and complexity == "hard":
        return "critical"
    if hits_critical:
        return "high"

    # Fix #1 (v3): is_test is checked BEFORE the hard-complexity
    # short-circuit below, so a hard-complexity test file is floored by
    # its test-ness rather than bare-returning "high".
    if is_test:
        return "medium" if complexity == "hard" else "low"

    if complexity == "hard":
        return "high"

    if is_doc and not is_pipeline_critical_doc:
        return "low"

    # Fix #4 (v3, deliberate): any non-test, non-doc production file
    # floors at "medium" regardless of declared complexity — complexity
    # is effort, not blast radius. Kept even though it over-classifies
    # some trivial changes; over-classification costs review time, not
    # safety.
    if not is_doc:
        return "medium"

    # Remaining case: a pipeline-critical doc (SKILL.md / .shared/*.md)
    # that isn't hard-complexity — resolve by declared complexity.
    if complexity == "medium":
        return "medium"
    if complexity == "simple":
        return "low"
    return "medium"  # unknown/unspecified complexity — fail safer, not lenient


def emit_inspection_verdict(
    repo: Path | str,
    *,
    work_result_id: str,
    work_order_id: str,
    verdict: str,
    evidence: list[str],
    inspector_dispatch_identity: str,
    work_result_dispatch_identity: str,
    ts: str,
) -> InspectionReport:
    """Check dispatch independence, then construct + append an
    :class:`InspectionReport` verdict for a Work Result, and return it.

    Order of operations (never reordered):

    1. :func:`check_dispatch_independence` runs FIRST. If it raises
       :class:`DispatchIndependenceError`, this function propagates the
       error unchanged and writes NOTHING to the ledger.
    2. On success, an :class:`InspectionReport` is constructed with
       ``subject_ref = work_result_id`` (see module-level note above),
       ``verdict``, ``findings = evidence``, and
       ``dispatch_identity = inspector_dispatch_identity``.
    3. :func:`append_ledger_event` persists it with the caller-supplied
       ``ts``.

    Raises :class:`LedgerValidationError` if ``work_order_id !=
    work_result_id`` (today's schema has one reference field, so a caller
    claiming they differ is a contract violation, not silently resolved),
    or if ``verdict`` is not one of :data:`VERDICTS`.
    """
    check_dispatch_independence(
        repo, work_result_dispatch_identity, inspector_dispatch_identity
    )

    if work_order_id != work_result_id:
        raise LedgerValidationError(
            f"work_order_id {work_order_id!r} != work_result_id "
            f"{work_result_id!r}; InspectionReport has a single subject_ref "
            "field and cannot represent two different reference ids"
        )

    normalized_verdict = verdict.strip().lower() if isinstance(verdict, str) else ""
    if normalized_verdict not in VERDICTS:
        raise LedgerValidationError(
            f"verdict {verdict!r} must be one of {VERDICTS}"
        )

    report = InspectionReport(
        subject_ref=work_result_id,
        verdict=normalized_verdict,
        findings=list(evidence),
        generator="inspector",
        dispatch_identity=inspector_dispatch_identity,
    )
    append_ledger_event(repo, report, ts=ts)
    return report


def latest_verdict_for(
    repo: Path | str, work_result_id: str
) -> InspectionReport | None:
    """Return the most recent :class:`InspectionReport` for ``work_result_id``
    (matched against ``subject_ref``), or ``None`` if none exist.

    Reads via :func:`read_ledger_events` (kind-filtered to
    ``KIND_INSPECTION_REPORT``), which already returns events oldest-first;
    the last matching event in that order is the latest verdict.
    """
    events = read_ledger_events(repo, kind=KIND_INSPECTION_REPORT)
    matching = [e for e in events if e.get("subject_ref") == work_result_id]
    if not matching:
        return None
    latest = matching[-1]
    return InspectionReport(
        subject_ref=latest.get("subject_ref", ""),
        verdict=latest.get("verdict", ""),
        findings=list(latest.get("findings", [])),
        generator=latest.get("generator", ""),
        dispatch_identity=latest.get("dispatch_identity", ""),
    )


__all__ = [
    "KINDS",
    "KIND_ESCALATION",
    "KIND_INSPECTION_REPORT",
    "KIND_WORK_ORDER",
    "KIND_WORK_RESULT",
    "LEDGER_FILE",
    "LEDGER_SUBDIR",
    "RISK_TIERS",
    "VERDICTS",
    "DispatchIndependenceError",
    "Escalation",
    "InspectionContract",
    "InspectionReport",
    "LedgerEvent",
    "LedgerValidationError",
    "RiskTier",
    "WorkOrder",
    "WorkResult",
    "append_ledger_event",
    "check_dispatch_independence",
    "classify_risk_tier",
    "emit_inspection_verdict",
    "latest_verdict_for",
    "ledger_dir",
    "ledger_path",
    "read_ledger_events",
    "validate_escalation",
    "validate_event",
    "validate_inspection_report",
    "validate_work_order",
    "validate_work_result",
    "work_order_for_task",
]

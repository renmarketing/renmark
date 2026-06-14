"""Staged-program DRIVER — the deterministic stage-sequencing state machine that
sits ABOVE the single-item loop (feature ``feature/roadmap-staged-planner``).

Where :mod:`renmark.loop` owns the *inner* bounded loop (budget / decide / stop
for one goal+verifier), this module owns the *outer* roadmap: it sequences a
:class:`renmark.program.Program`'s stages, evaluates the per-stage stop
condition from structured signals, advances on success, and warns on drift.

Design contract (mirrors :mod:`renmark.loop` + :mod:`renmark.program`):

- **No LLMs, no generated code.** This module reads ONLY the structured
  :class:`~renmark.program.Program` model and a structured ``stage_result``
  dict of machine-readable signals. It NEVER opens source files, diffs,
  artifact bodies, or LLM-interpreted prose. A pass is never inferred from
  free text — only from explicit typed fields.
- **State, not work.** The roadmap SKILL drives the actual
  brainstorm/plan/orchestrate/verify invocations per stage; this module decides
  *which* stage is next, *whether* to stop, and persists the advance.
- **Write-state-before-return (Temporal).** :func:`advance_on_success` persists
  the program via :func:`renmark.program.write_program` BEFORE returning, so a
  crash / ``/clear`` mid-advance is recoverable from
  ``.renmark/state/program.json``.
- **Stops degrade toward stopping.** A missing signal means "that stop does not
  fire" — never "infer a pass". :func:`evaluate_stop` is total and tolerant of
  absent keys, but never reads a pass out of prose.

stage_result dict contract (input to :func:`evaluate_stop`)
-----------------------------------------------------------
A flat dict of structured signals harvested by the SKILL from each phase's
artifact METADATA (never its body). Every key is OPTIONAL — an absent key means
that signal was not produced, so its stop does NOT fire. Recognised keys::

    {
      # verify phase (renmark.verify metadata):
      "completion_state":   "complete" | "partial" | "failed",
      "validation_status":  "validated" | "unvalidated" | "failed",

      # check-plan phase (renmark.check-plan verdict):
      "verdict":            "PASS" | "WARN" | "BLOCK",

      # codereview phase (renmark.codereview severity rollup):
      "critical_count":     int,            # > 0 → critical findings exist
      "severity":           "critical" | ...,

      # circuit-break (max per-task retry across the stage's tasks):
      # read from the Program model, NOT this dict — see note below.

      # prd-alignment phase (align verdict):
      "align_verdict":      "aligned" | "drift",

      # resumable / non-fatal dispositions:
      "budget_status":      "exhausted" | "ok",   # loop budget-hit
      "max_iter_hit":       bool,                 # loop iteration ceiling
      "usage_limited":      bool,                 # provider usage limit
      "paused":             bool,                 # explicit pause request

      # REQ-12 human-gate dispositions:
      "gate":               "merge" | "release" | "destructive" | <any truthy>,
      "awaiting_approval":  bool,
    }

Note on RETRY_EXHAUSTED: per-task ``retry_count >= MAX_TASK_RETRIES`` is read
from the live :class:`~renmark.program.Program`, not from ``stage_result`` — so
the caller may either pass a ``max_retry_count`` int in ``stage_result`` OR rely
on :func:`evaluate_stop_for_stage` which derives it from the program directly.

Severity ordering (FIRST MATCH WINS) for :func:`evaluate_stop`
--------------------------------------------------------------
Hard stops are evaluated most-blocking first:

    1. RETRY_EXHAUSTED      — circuit-break; a task hit the retry ceiling
                              (a persistent BLOCKER, not a transient failure)
    2. PLAN_BLOCK           — check-plan returned BLOCK (cannot safely execute)
    3. PRD_DRIFT            — work drifted from the PRD source of truth
    4. CODEREVIEW_CRITICAL  — a critical-severity review finding
    5. VERIFY_FAILED        — verify did not reach complete + validated

Non-hard dispositions are evaluated ONLY after no hard stop fires:

    6. AWAITING_APPROVAL    — a REQ-12 gate (merge/release/destructive) is pending
    7. PAUSED               — budget / max-iter / usage-limit (resumable, NO approval)

:func:`is_hard_stop` and :data:`HARD_STOPS` treat 1-5 as hard stops;
``AWAITING_APPROVAL`` and ``PAUSED`` are NOT hard stops (the roadmap is
resumable from them — one via ``/renmark:approve``, the other once budget /
limits clear).
"""

from __future__ import annotations

from enum import Enum

from renmark import program as _program
from renmark.program import Program, StageNode
from renmark.summary import git_head_sha

# ── Tunable constants ──────────────────────────────────────────────────────────

#: Per-task retry ceiling. A task whose ``retry_count`` reaches this is a
#: circuit-break BLOCKER (RETRY_EXHAUSTED) — not a transient failure to retry.
MAX_TASK_RETRIES: int = 3

#: Stage statuses the driver treats as RUNNABLE (selectable by :func:`next_stage`).
#: ``pending`` / ``needed`` are not-yet-started; ``in_progress`` resumes. ``done``
#: is skipped; ``partial`` / ``blocked`` are terminal-attention states that need a
#: stop disposition, so they are NEVER auto-selected as the next stage.
_RUNNABLE_STATUSES: frozenset[str] = frozenset({"pending", "needed", "in_progress"})

#: The completion / validation values that count as a clean verify PASS (mirrors
#: ``renmark.loop._COMPLETE_STATE`` / ``_PASS_VALIDATION``).
_COMPLETE_STATE: str = "complete"
_PASS_VALIDATION: str = "validated"


# ── Stop reasons ───────────────────────────────────────────────────────────────


class StopReason(str, Enum):
    """Why the driver halted (or paused) BEFORE / AFTER running a stage.

    A ``str`` Enum (``loop.py`` ``Literal`` style, but as a real enum so the set
    is closed and members compare equal to their string value). The five HARD
    stops require human / re-plan intervention; ``PAUSED`` and
    ``AWAITING_APPROVAL`` are resumable dispositions, NOT hard stops.
    """

    VERIFY_FAILED = "verify_failed"
    PLAN_BLOCK = "plan_block"
    CODEREVIEW_CRITICAL = "codereview_critical"
    RETRY_EXHAUSTED = "retry_exhausted"
    PRD_DRIFT = "prd_drift"
    # Non-hard dispositions:
    AWAITING_APPROVAL = "awaiting_approval"  # REQ-12 gate — clears via /renmark:approve
    PAUSED = "paused"  # budget / max-iter / usage-limit — resumable, no approval

    def __str__(self) -> str:  # keep ``str(StopReason.X)`` == the value
        return self.value


#: The HARD stops — reaching any of these halts the roadmap pending human action
#: or a re-plan. Deliberately EXCLUDES ``PAUSED`` + ``AWAITING_APPROVAL`` (both
#: resumable). Used by :func:`is_hard_stop`.
HARD_STOPS: frozenset[StopReason] = frozenset(
    {
        StopReason.RETRY_EXHAUSTED,
        StopReason.PLAN_BLOCK,
        StopReason.PRD_DRIFT,
        StopReason.CODEREVIEW_CRITICAL,
        StopReason.VERIFY_FAILED,
    }
)


def is_hard_stop(reason: StopReason | None) -> bool:
    """Return ``True`` iff ``reason`` is a HARD stop (in :data:`HARD_STOPS`).

    ``None`` (no stop), ``PAUSED``, and ``AWAITING_APPROVAL`` all return
    ``False`` — they are continue / resumable dispositions, not hard halts.
    """
    return reason in HARD_STOPS


# ── Stage sequencing ────────────────────────────────────────────────────────────


def next_stage(program: Program) -> StageNode | None:
    """Return the next RUNNABLE stage, or ``None`` when none should run now.

    Selection policy (a roadmap is a SEQUENTIAL program, so order matters):

    1. **Resume active work first.** If any stage is ``in_progress``, return it —
       resuming an interrupted stage outranks starting a new one.
    2. **Otherwise walk in declared order and HALT at an attention state.** Skip
       ``done`` stages; return the first ``pending`` / ``needed`` stage. But if an
       earlier stage is ``blocked`` / ``partial`` (terminal-attention — the SKILL
       must re-plan / approve before the roadmap proceeds), return ``None`` rather
       than skipping past it: a blocked earlier stage must not be silently jumped
       so a later stage runs out of order.

    ``None`` therefore means *nothing should auto-run now* — either every stage is
    ``done``, or the next stage in line needs human attention first.
    """
    # 1. Resume an actively in-progress stage before starting anything new.
    for stage in program.stages:
        if stage.status == "in_progress":
            return stage
    # 2. Walk in order; the first not-yet-run stage is next, but an attention
    #    state halts progression instead of being skipped.
    for stage in program.stages:
        if stage.status == "done":
            continue
        if stage.status in ("pending", "needed"):
            return stage
        # blocked / partial → attention required before any later stage runs.
        return None
    return None


# ── Stop evaluation (structured fields only) ─────────────────────────────────────


def evaluate_stop(stage_result: dict[str, object]) -> StopReason | None:
    """Map a structured ``stage_result`` to a :class:`StopReason`, or ``None``.

    Reads ONLY the machine-readable signals documented in the module docstring's
    *stage_result dict contract* — NEVER LLM-interpreted prose. Evaluated in the
    documented severity order (FIRST MATCH WINS); see the module docstring.

    Tolerant of missing keys: an absent signal means that stop does NOT fire
    (the safe direction is to keep going, EXCEPT verify — see below). It never
    infers a pass from text. ``None`` means "no stop condition met — proceed".

    Per-task RETRY_EXHAUSTED: this function reads an optional integer
    ``max_retry_count`` from ``stage_result`` (the SKILL passes the max
    ``retry_count`` across the stage's tasks). When the caller has the
    :class:`Program` in hand, prefer :func:`evaluate_stop_for_stage`, which
    derives that value from the model directly.
    """
    sr = stage_result if isinstance(stage_result, dict) else {}

    # 1. RETRY_EXHAUSTED — circuit-break BLOCKER, most blocking; checked first.
    max_retry = _as_int(sr.get("max_retry_count"))
    if max_retry is not None and max_retry >= MAX_TASK_RETRIES:
        return StopReason.RETRY_EXHAUSTED

    # 2. PLAN_BLOCK — check-plan verdict BLOCK.
    verdict = _as_str(sr.get("verdict")).upper()
    if verdict == "BLOCK":
        return StopReason.PLAN_BLOCK

    # 3. PRD_DRIFT — align verdict reports drift.
    if _as_str(sr.get("align_verdict")).lower() == "drift":
        return StopReason.PRD_DRIFT

    # 4. CODEREVIEW_CRITICAL — a critical-severity review finding.
    critical_count = _as_int(sr.get("critical_count"))
    severity = _as_str(sr.get("severity")).lower()
    if (critical_count is not None and critical_count > 0) or severity == "critical":
        return StopReason.CODEREVIEW_CRITICAL

    # 5. VERIFY_FAILED — verify must reach complete + validated. We only judge
    #    verify when at least one verify signal is PRESENT (absent == this phase
    #    did not run this stage_result; do NOT fabricate a failure from silence).
    completion = _as_str(sr.get("completion_state"))
    validation = _as_str(sr.get("validation_status"))
    if (completion or validation) and (
        completion != _COMPLETE_STATE or validation != _PASS_VALIDATION
    ):
        return StopReason.VERIFY_FAILED

    # ── Non-hard dispositions (only after no hard stop fired) ────────────────
    # 6. AWAITING_APPROVAL — a REQ-12 gate is pending.
    if _truthy(sr.get("awaiting_approval")) or _truthy(sr.get("gate")):
        return StopReason.AWAITING_APPROVAL

    # 7. PAUSED — budget / max-iter / usage-limit / explicit pause (resumable).
    if (
        _as_str(sr.get("budget_status")).lower() == "exhausted"
        or _truthy(sr.get("max_iter_hit"))
        or _truthy(sr.get("usage_limited"))
        or _truthy(sr.get("paused"))
    ):
        return StopReason.PAUSED

    return None


def evaluate_stop_for_stage(
    program: Program, stage_id: str, stage_result: dict[str, object]
) -> StopReason | None:
    """:func:`evaluate_stop` with RETRY_EXHAUSTED derived from the live program.

    Convenience for callers holding the :class:`Program`: computes the max
    ``retry_count`` across ``stage_id``'s tasks and injects it as
    ``max_retry_count`` before delegating, so the circuit-break is read from
    authoritative model state rather than a hand-passed field. An unknown
    ``stage_id`` contributes no tasks (max stays 0). Never mutates the program.
    """
    merged: dict[str, object] = dict(stage_result) if isinstance(stage_result, dict) else {}
    max_retry = 0
    for stage in program.stages:
        if stage.id == stage_id:
            for task in stage.tasks:
                rc = task.retry_count if isinstance(task.retry_count, int) else 0
                if rc > max_retry:
                    max_retry = rc
            break
    # Only inject when the caller did not already supply one (caller wins).
    merged.setdefault("max_retry_count", max_retry)
    return evaluate_stop(merged)


# ── Advance on success (write-state-before-return) ───────────────────────────────


def advance_on_success(program: Program, stage_id: str, repo: str) -> Program:
    """Mark ``stage_id`` done, advance ``current_stage_id`` to the NEXT stage,
    snapshot the NEXT stage's baseline sha, and persist — BEFORE returning.

    Steps (Temporal write-state-before-return):

    1. ``mark_stage(program, stage_id, "done")`` — fails loud on unknown id.
    2. Resolve the NEXT stage AFTER ``stage_id`` in declared order.
    3. Set ``program.current_stage_id`` to that next stage's id (or ``None`` when
       ``stage_id`` was the LAST stage).
    4. **Snapshot the NEXT stage's** ``stage_completion_sha`` to the current git
       HEAD sha — KEYED BY THE NEXT STAGE'S ID (owner decision: the snapshot is
       the baseline the next stage is later drift-checked against, so it belongs
       to the next stage, NOT the completed one). When ``stage_id`` was the last
       stage there is no next stage → snapshot NOTHING.
    5. Persist via :func:`renmark.program.write_program` BEFORE returning.

    Returns the (mutated, persisted) program. Raises :class:`ValueError` (from
    :func:`~renmark.program.mark_stage`) on an unknown ``stage_id``.
    """
    # 1. Mark the just-completed stage done (loud on unknown id).
    _program.mark_stage(program, stage_id, "done")

    # 2. Resolve the NEXT stage after stage_id, in declared order.
    next_node = _next_after(program, stage_id)

    if next_node is None:
        # 3a. stage_id was the last stage — no next; snapshot NOTHING.
        program.current_stage_id = None
    else:
        # 3b. Advance the cursor to the next stage.
        program.current_stage_id = next_node.id
        # 4. Snapshot the NEXT stage's baseline sha, KEYED BY THE NEXT STAGE.
        #    Only snapshot when we have a real sha (None == not a git repo /
        #    detached; a missing snapshot simply yields no drift warning later).
        sha = git_head_sha(repo)
        if sha:
            # next_node is in program.stages, so snapshot_stage_sha won't raise.
            _program.snapshot_stage_sha(program, next_node.id, sha)

    # 5. Persist BEFORE returning (write-state-before-return).
    _program.write_program(repo, program)
    return program


def _next_after(program: Program, stage_id: str) -> StageNode | None:
    """Return the stage immediately AFTER ``stage_id`` in declared order, or
    ``None`` when ``stage_id`` is the last stage or is not found."""
    for i, stage in enumerate(program.stages):
        if stage.id == stage_id:
            nxt = i + 1
            return program.stages[nxt] if nxt < len(program.stages) else None
    return None


# ── Drift warning ────────────────────────────────────────────────────────────────


def drift_warning(program: Program, stage_id: str, current_sha: str) -> str | None:
    """Warn when the recorded baseline sha for ``stage_id`` differs from
    ``current_sha``; ``None`` on a match or when no snapshot exists.

    The baseline is the sha snapshotted (by :func:`advance_on_success`) when this
    stage became current — i.e. the tree state the stage was planned against. A
    mismatch means the tree moved underneath the stage (other commits landed), so
    upstream artifacts may be stale. Pure string accessor; never raises.
    """
    baseline = program.stage_completion_sha.get(stage_id)
    if not baseline:
        return None
    if not current_sha or baseline == current_sha:
        return None
    return (
        f"drift: stage {stage_id!r} baseline {baseline[:8]} "
        f"!= current {current_sha[:8]} — upstream artifacts may be stale"
    )


# ── Bounded status (orchestrator-visible) ────────────────────────────────────────


def driver_status(program: Program) -> str:
    """Return a bounded (≤5-line) driver status the orchestrator may read.

    Pure string accessor: the program position line, the next runnable stage (or
    a terminal note), and a tally of stage statuses. Never reads bodies / diffs /
    code; never raises. Always ≤ 5 lines.
    """
    lines: list[str] = [_program.position(program)]

    nxt = next_stage(program)
    if nxt is None:
        if program.stages and all(s.status == "done" for s in program.stages):
            lines.append("next: (none) — all stages done")
        else:
            lines.append("next: (none) — no runnable stage (blocked/partial pending)")
    else:
        title = nxt.title or nxt.id or "(untitled stage)"
        lines.append(f"next: {title} [{nxt.status}]")

    done = sum(1 for s in program.stages if s.status == "done")
    total = len(program.stages)
    attention = sum(1 for s in program.stages if s.status in ("partial", "needed", "blocked"))
    tally = f"stages: {done}/{total} done"
    if attention:
        tally += f" · {attention} need attention"
    lines.append(tally)

    return "\n".join(lines[:5])


__all__ = [
    "HARD_STOPS",
    "MAX_TASK_RETRIES",
    "StopReason",
    "advance_on_success",
    "drift_warning",
    "driver_status",
    "evaluate_stop",
    "evaluate_stop_for_stage",
    "is_hard_stop",
    "next_stage",
]


# ── Internal coercion helpers (tolerant, never raise) ────────────────────────────


def _as_str(value: object) -> str:
    """Return ``value`` as a stripped string (``""`` when absent / non-str)."""
    return value.strip() if isinstance(value, str) else ""


def _as_int(value: object) -> int | None:
    """Return ``value`` as an int, or ``None`` when absent / non-int.

    ``bool`` is rejected (it is an int subclass but never a valid count here);
    numeric strings are accepted so a metadata-parsed ``"3"`` still circuit-breaks.
    """
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        raw = value.strip()
        if raw.lstrip("-").isdigit():
            try:
                return int(raw)
            except ValueError:
                return None
    return None


def _truthy(value: object) -> bool:
    """Structured-truthiness: ``True`` for a truthy bool, a positive int, or a
    non-empty / non-``false``/``no``/``0`` string. NEVER infers truth from prose
    beyond these explicit sentinels."""
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value > 0
    if isinstance(value, str):
        v = value.strip().lower()
        return bool(v) and v not in ("false", "no", "0", "none", "null", "")
    return False

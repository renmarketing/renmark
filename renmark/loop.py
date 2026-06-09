"""Loop Mode state machine — the deterministic core of renmark's bounded,
verified, resumable agentic loop (REQ-9/10/11; spec
``.renmark/specs/2026-06-09-loop-mode.spec.md``).

The loop wraps ``orchestrate → verify → decide`` and runs autonomously within
a single upfront-approved budget + iteration ceiling until it reaches a
terminal state. **This module owns the STATE, not the work**: the
``/renmark:loop`` SKILL drives the actual orchestrate/verify invocations; this
module persists ``loop.json``, parses the budget, builds the per-iteration
decision object, and evaluates the stop conditions.

Design contract (mirrors ``renmark/sizing.py`` + ``renmark/lifecycle.py``):

- **Reads ONLY metadata + ledger.** ``build_decision`` consumes a verification
  *metadata dict* (already parsed by ``renmark.summary.read_metadata``) — it
  never opens source files, diffs, or artifact bodies (REQ-5/11). The budget
  gate reads the token ledger via ``usage_by_run_id`` — never the conversation.
- **Never raises into the caller.** Every IO / parse / read step is wrapped; a
  missing or corrupt ``loop.json`` degrades to a fresh default (or ``None``),
  not an exception. Stop logic degrades toward stopping, never toward running
  unbounded.
- **Deterministic / testable.** No ``datetime.now()``, no ``random``: the
  caller passes the ``date``/``slug`` for the loop id. Every threshold is a
  documented, tunable module-level constant.
- **Bounded + resumable.** ``loop.json`` is written before each iteration
  returns, so a crash / ``/clear`` / new session can recover the iteration
  index, remaining budget, and pending step. This is the runtime sibling of
  ``pipeline.json`` — NOT ``lifecycle.json`` (G12 / the 1KB workflow-state
  guard; loop runtime state must not leak into lifecycle.json).
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

from .state import RENMARK_DIR_NAME, usage_by_run_id

# ── Tunable constants ──────────────────────────────────────────────────────────

#: Default iteration ceiling when ``--max-iterations`` is not supplied.
DEFAULT_MAX_ITERATIONS: int = 5

#: Default token budget when ``--budget`` is not supplied (300k tokens).
DEFAULT_BUDGET_TOKENS: int = 300_000

#: Blended cost assumption for the token<->dollar conversion, USD per 1k tokens.
#:
#: Loop Mode tracks spend in TOKENS (the measurable unit the ledger records);
#: the ``$`` figure is only an *estimate* shown to the human. A renmark loop is
#: orchestrated by Sonnet/Opus but does the bulk emit on Codex, so the realised
#: blend sits between the per-model rates in ``roadmap.COST_PER_KT``
#: (haiku 0.0001 · sonnet 0.003 · opus 0.015 · codex 0.05 per 1k). We assume a
#: single conservative blended rate of **$0.01 / 1k tokens** — deliberately on
#: the high side so a ``$`` budget never under-buys iterations and the estimate
#: errs toward caution. Tune as the realised mix / pricing shifts.
COST_PER_KTOKEN_USD: float = 0.01

#: Terminal + active loop statuses persisted in ``loop.json``.
LoopStatus = Literal[
    "running",  # active; not yet terminal
    "done",  # goal verified (terminal)
    "budget-hit",  # spend reached the approved ceiling (terminal)
    "max-iter",  # iteration ceiling reached (terminal)
    "awaiting-approval",  # a REQ-12 gate is pending (terminal until /renmark:approve)
    "stalled",  # no fresh evidence / empty next_action (terminal)
]

#: The non-running statuses — reaching any of these ends the loop.
TERMINAL_STATUSES: frozenset[str] = frozenset(
    {"done", "budget-hit", "max-iter", "awaiting-approval", "stalled"}
)

#: ``loop.json`` filename inside each loop directory.
LOOP_JSON: str = "loop.json"

#: Subdir under ``.renmark/`` that holds every loop's directory.
LOOPS_SUBDIR: str = "loops"

#: Verification ``completion_state`` value that signals the run finished cleanly.
_COMPLETE_STATE: str = "complete"

#: Verification metadata values that count as a PASS-equivalent verdict. The
#: verify skill records its goal-backward result in ``validation_status``
#: (``validated`` == PASS) and the body summary; we treat ``validated`` as the
#: machine-readable PASS signal and require ``completion_state == complete``.
_PASS_VALIDATION: frozenset[str] = frozenset({"validated"})


# ── Loop state ──────────────────────────────────────────────────────────────


@dataclass
class LoopState:
    """Runtime state of one bounded loop. Persisted to ``loop.json``.

    Pure runtime — the loop's identity/goal plus the live counters. The inner
    orchestrate run keeps its own ``pipeline.json``; this is the *outer* loop's
    state. Kept JSON-trivial (str/int/bool only) so read/write never needs a
    serializer beyond ``json``.
    """

    goal: str = ""
    verify_cmd: str = ""
    budget_tokens: int = DEFAULT_BUDGET_TOKENS
    budget_usd_estimate: str = ""
    spent_tokens: int = 0
    run_id: str = ""
    max_iterations: int = DEFAULT_MAX_ITERATIONS
    iteration: int = 0
    status: str = "running"  # one of LoopStatus
    pending_step: str = ""  # the REQ-12 gate awaiting approval, if any

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2, sort_keys=False)


# ── Paths ────────────────────────────────────────────────────────────────────


def loop_id(date: str, slug: str) -> str:
    """Build the canonical loop id ``loop-<date>-<slug>``.

    ``date`` and ``slug`` are passed in by the caller (no ``datetime.now()`` —
    the loop stays deterministic/testable). The slug is sanitised to a safe
    path component: lowercased, non-alphanumerics collapsed to ``-``, trimmed.
    A blank slug degrades to ``loop``.
    """
    safe = re.sub(r"[^a-z0-9]+", "-", str(slug).strip().lower()).strip("-")
    safe = safe or "loop"
    return f"loop-{str(date).strip()}-{safe}"


def loop_dir(repo: str | Path, loop_id_value: str) -> Path:
    """Return ``.renmark/loops/<id>/`` for ``loop_id_value`` (not created)."""
    return Path(repo) / RENMARK_DIR_NAME / LOOPS_SUBDIR / loop_id_value


def _loop_json_path(repo: str | Path, loop_id_value: str) -> Path:
    return loop_dir(repo, loop_id_value) / LOOP_JSON


# ── loop.json read / write ─────────────────────────────────────────────────


def read_loop(repo: str | Path, loop_id_value: str) -> LoopState | None:
    """Return the persisted :class:`LoopState`, or ``None`` if absent/corrupt.

    Never raises: a missing directory, missing file, unreadable bytes, invalid
    JSON, or a non-dict payload all yield ``None`` (the caller then knows there
    is no resumable loop). Unknown fields are dropped so schema drift can't
    crash the constructor.
    """
    path = _loop_json_path(repo, loop_id_value)
    try:
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    known = set(LoopState.__dataclass_fields__)
    filtered = {k: v for k, v in data.items() if k in known}
    try:
        return LoopState(**filtered)
    except (TypeError, ValueError):
        return None


def write_loop(repo: str | Path, loop_id_value: str, state: LoopState) -> Path | None:
    """Persist ``state`` to ``.renmark/loops/<id>/loop.json`` (atomic-ish).

    Writes to a sibling ``.tmp`` file then ``os.replace``-style renames it over
    the target, so a crash mid-write never leaves a half-written ``loop.json``
    (the loop stays resumable from the last good state). Returns the written
    path, or ``None`` on any IO failure — never raises into the caller.
    """
    path = _loop_json_path(repo, loop_id_value)
    tmp = path.with_suffix(path.suffix + ".tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_text(state.to_json(), encoding="utf-8")
        tmp.replace(path)  # atomic on the same filesystem
    except OSError:
        try:
            if tmp.exists():
                tmp.unlink()
        except OSError:
            pass
        return None
    return path


# ── Budget parsing ─────────────────────────────────────────────────────────


def parse_budget(value: str | int) -> tuple[int, str]:
    """Parse a budget given as EITHER a token count OR a ``$`` amount.

    Accepts:
    - an ``int`` (e.g. ``300000``) → that many tokens;
    - a numeric string (e.g. ``"300000"``, ``"300_000"``, ``"300,000"``) →
      tokens;
    - a ``$`` string (e.g. ``"$3.00"``, ``"$3"``) → converted to tokens via
      :data:`COST_PER_KTOKEN_USD`.

    Returns ``(budget_tokens, usd_estimate_str)``. The estimate is always
    derived from the resolved token count via :func:`estimate_usd`, so both the
    token-input and ``$``-input paths report a consistent ``$`` figure.

    Never raises: a blank / unparseable / non-positive value degrades to
    :data:`DEFAULT_BUDGET_TOKENS` (the safe, bounded default — never unbounded).
    """
    tokens = _coerce_budget_tokens(value)
    if tokens <= 0:
        tokens = DEFAULT_BUDGET_TOKENS
    return tokens, estimate_usd(tokens)


def estimate_usd(tokens: int) -> str:
    """Return the ``$`` estimate string for a token budget (``"$N.NN"``).

    Uses the blended :data:`COST_PER_KTOKEN_USD` rate. Never raises — a
    non-positive / non-int token count yields ``"$0.00"``.
    """
    try:
        t = int(tokens)
    except (TypeError, ValueError):
        return "$0.00"
    if t <= 0:
        return "$0.00"
    dollars = (t / 1000.0) * COST_PER_KTOKEN_USD
    return f"${dollars:.2f}"


def _coerce_budget_tokens(value: str | int) -> int:
    """Resolve a raw budget value to a token count. ``<= 0`` / unparseable → 0
    (the caller substitutes the default). Never raises."""
    if isinstance(value, bool):  # bool is an int subclass — reject explicitly.
        return 0
    if isinstance(value, int):
        return value
    if not isinstance(value, str):
        # Defensive: callers are typed str|int, but a runtime caller may pass
        # something else. Degrade to 0 rather than raising on ``.strip()``.
        return 0  # type: ignore[unreachable]

    raw = value.strip()
    if not raw:
        return 0

    is_dollar = raw.startswith("$")
    if is_dollar:
        raw = raw[1:].strip()

    # Allow human-friendly separators in either form.
    cleaned = raw.replace("_", "").replace(",", "")
    if not cleaned:
        return 0

    try:
        amount = float(cleaned)
    except ValueError:
        return 0
    if amount <= 0:
        return 0

    if is_dollar:
        if COST_PER_KTOKEN_USD <= 0:
            return 0
        return round((amount / COST_PER_KTOKEN_USD) * 1000.0)
    # Bare number → token count (truncate any fractional tokens).
    return int(amount)


# ── Decision object ─────────────────────────────────────────────────────────


def build_decision(verification_meta: dict[str, object], spent_delta: int) -> dict[str, object]:
    """Build the SubagentOutput-shaped decision for one iteration.

    Consumes ONLY the verification *metadata dict* (as returned by
    ``renmark.summary.read_metadata`` over the iteration's ``.verification.md``)
    plus the ledger ``spent_delta`` for this iteration. It NEVER opens source
    files, diffs, or artifact bodies (REQ-5/11) — the verdict is read straight
    from the metadata fields the verify skill already records.

    Returns::

        {
          "goal_reached": bool,            # completion_state==complete AND PASS
          "evidence": list[str],           # bounded evidence lines from meta
          "next_action": str,              # "" when goal reached / no step
          "model_recommendation": str,     # suggested executor for next iter
          "estimated_next_cost": str,      # "$N.NN" for the next iteration
        }

    Never raises: a missing/odd metadata dict degrades to ``goal_reached=False``
    with empty evidence (the stop logic then treats an empty ``next_action`` as
    ``stalled`` — the safe, bounded direction).
    """
    meta = verification_meta if isinstance(verification_meta, dict) else {}

    completion = _meta_str(meta, "completion_state")
    validation = _meta_str(meta, "validation_status")
    goal_reached = completion == _COMPLETE_STATE and validation in _PASS_VALIDATION

    evidence = _evidence_lines(meta)

    # When the goal is reached there is no next action; otherwise carry whatever
    # actionable next step the verify metadata recorded. A blank next_action is
    # the signal for the stalled stop condition.
    next_action = "" if goal_reached else _meta_str(meta, "next_action")

    model_recommendation = _meta_str(meta, "model_recommendation") or "sonnet"

    # Cost estimate for the *next* iteration: reuse this iteration's spend delta
    # as a forward proxy (the loop's best deterministic estimate without
    # guessing). A non-positive / unknown delta yields "$0.00".
    try:
        delta = int(spent_delta)
    except (TypeError, ValueError):
        delta = 0
    estimated_next_cost = estimate_usd(delta) if delta > 0 else "$0.00"

    return {
        "goal_reached": goal_reached,
        "evidence": evidence,
        "next_action": next_action,
        "model_recommendation": model_recommendation,
        "estimated_next_cost": estimated_next_cost,
    }


def _evidence_lines(meta: dict[str, object]) -> list[str]:
    """Pull bounded evidence lines from verification metadata.

    Prefers an explicit ``summary_lines`` list; falls back to a single
    ``summary`` string. Coerces every entry to ``str`` and drops blanks. Capped
    at 5 lines to honour the G3 summary boundary — never returns the body.
    """
    raw = meta.get("summary_lines")
    lines: list[str] = []
    if isinstance(raw, list):
        for item in raw:
            text = str(item).strip()
            if text:
                lines.append(text)
    if not lines:
        single = meta.get("summary")
        if isinstance(single, str) and single.strip():
            lines.append(single.strip())
    return lines[:5]


def _meta_str(meta: dict[str, object], key: str) -> str:
    """Return ``meta[key]`` as a stripped ``str`` (``""`` if absent/non-str)."""
    value = meta.get(key)
    return value.strip() if isinstance(value, str) else ""


# ── Stop logic ───────────────────────────────────────────────────────────────


def stop_reason(state: LoopState) -> str | None:
    """Return the terminal status the loop should adopt, or ``None`` to continue.

    Evaluated in safety order — the first matching condition wins:

    1. ``status`` already terminal → return it (idempotent re-entry).
    2. spend ≥ budget → ``"budget-hit"`` (checked first among live conditions so
       an approved ceiling is never exceeded).
    3. iteration ≥ max_iterations → ``"max-iter"``.
    4. a pending REQ-12 gate (non-empty ``pending_step``) → ``"awaiting-approval"``.
    5. goal reached (status already flipped to ``"done"`` by the caller, OR an
       empty ``pending_step`` with status ``"done"``) → ``"done"``.

    The caller sets ``status="done"`` when ``build_decision`` returns
    ``goal_reached=True``; this function then confirms it as terminal. A blank
    ``next_action`` (no fresh evidence) maps to ``"stalled"`` — but that signal
    lives in the decision object, so the caller records it on ``state.status``
    before calling here. To keep the rule total and never raise, this function
    treats a ``"stalled"`` status as terminal too.

    Never raises: a malformed ``state`` (non-int counters) degrades to a stop
    (``"stalled"``) rather than looping unbounded.
    """
    try:
        status = getattr(state, "status", "") or ""
        if status in TERMINAL_STATUSES:
            return status

        spent = int(getattr(state, "spent_tokens", 0) or 0)
        budget = int(getattr(state, "budget_tokens", 0) or 0)
        iteration = int(getattr(state, "iteration", 0) or 0)
        max_iter = int(getattr(state, "max_iterations", 0) or 0)
        pending = (getattr(state, "pending_step", "") or "").strip()

        # Budget ceiling is checked first — never exceed the approved spend.
        if budget > 0 and spent >= budget:
            return "budget-hit"
        if max_iter > 0 and iteration >= max_iter:
            return "max-iter"
        if pending:
            return "awaiting-approval"
        return None
    except (TypeError, ValueError):
        # A malformed state must stop the loop, not run it unbounded.
        return "stalled"


# ── Budget gate ───────────────────────────────────────────────────────────────


def refresh_spent(repo: str | Path, state: LoopState) -> LoopState:
    """Recompute ``state.spent_tokens`` from the real ledger for this run_id.

    The budget gate is enforced against measured spend, not an estimate: this
    reads ``usage.jsonl`` via :func:`usage_by_run_id` (which itself never
    raises → 0). Mutates and returns ``state`` for caller convenience. A blank
    ``run_id`` leaves ``spent_tokens`` untouched (nothing to attribute yet).
    """
    run_id = (getattr(state, "run_id", "") or "").strip()
    if run_id:
        state.spent_tokens = usage_by_run_id(repo, run_id)
    return state


def budget_remaining(state: LoopState) -> int:
    """Tokens left before the budget ceiling (never negative). 0 == exhausted."""
    try:
        remaining = int(state.budget_tokens) - int(state.spent_tokens)
    except (TypeError, ValueError):
        return 0
    return max(0, remaining)


__all__ = [
    "COST_PER_KTOKEN_USD",
    "DEFAULT_BUDGET_TOKENS",
    "DEFAULT_MAX_ITERATIONS",
    "LOOPS_SUBDIR",
    "LOOP_JSON",
    "TERMINAL_STATUSES",
    "LoopState",
    "LoopStatus",
    "budget_remaining",
    "build_decision",
    "estimate_usd",
    "loop_dir",
    "loop_id",
    "parse_budget",
    "read_loop",
    "refresh_spent",
    "stop_reason",
    "write_loop",
]

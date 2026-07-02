"""Deterministic cost-preview and escalation-gate helpers — zero-LLM, stdlib-only.

This module is the **single source of truth** for executor pricing, per-task token
estimation, cost banding, and the "escalate only when justified" gate used by the
finish lane and, in future, Agency Mode.

It is reusable by any caller that needs a cost preview before dispatching:

- **plan preview** — ``estimate_cost(items)`` runs on the validated task list to
  produce a :class:`CostPreview` before any token is spent (complements plan §6
  inline math, which is left untouched).
- **finish lane** — the finish skill calls ``estimate_cost`` to surface a cost
  summary and ``requires_escalation`` to gate opus/fable dispatch.
- **Agency Mode (future)** — the same helpers wire into the autonomous dispatch
  loop without any change to this module.

The "escalate only when justified" contract:
  Opus and Fable are reserved for genuinely hard work — ``complexity == "hard"``
  or structural tasks (architecture, adversarial-review, design-fork).  Routing
  them on medium/simple work is a cost violation; ``requires_escalation`` is the
  programmatic gate that enforces this.

Design contract:

- Pure functions of their inputs.
- **Never raises into the caller.** Every access step is defensive; missing or
  garbage fields degrade to ``0`` tokens / sonnet pricing.
- Every threshold and price is a documented, tunable module-level constant.
"""

from __future__ import annotations

from dataclasses import dataclass

# ── Pricing (USD per 1 000 tokens) ──────────────────────────────────────────

#: Per-executor price in USD per 1 000 tokens.
#: Codex ``0.03`` is the midpoint of the observed ``0.01``–``0.05`` range.
#: Unknown executors are priced at the ``"sonnet"`` rate (conservative default).
PRICE_PER_KTOK: dict[str, float] = {
    "haiku": 0.0001,
    "codex": 0.03,
    "sonnet": 0.003,
    "opus": 0.015,
    "fable": 0.030,
}

# ── Overhead ─────────────────────────────────────────────────────────────────

#: Extra tokens added per non-codex agent task to account for system-prompt,
#: tool definitions, and routing overhead — matches plan §6 inline math.
#: Codex is a subprocess executor; it has NO agent overhead.
AGENT_OVERHEAD_TOKENS: int = 10_000

# ── Cost-band thresholds ─────────────────────────────────────────────────────

#: A run priced below this is "low" band (green light, no gate).
BAND_LOW_MAX_USD: float = 0.10

#: A run priced below this (but >= BAND_LOW_MAX_USD) is "medium" band (proceed
#: with a note). At or above this threshold the run is "high" (pause for approval).
BAND_MEDIUM_MAX_USD: float = 1.00

# ── Executor sets ────────────────────────────────────────────────────────────

#: Executors that run as Claude Code agent calls (carry agent overhead).
_AGENT_EXECUTORS: frozenset[str] = frozenset({"haiku", "sonnet", "opus", "fable"})

#: Executors classified as expensive (trigger ``requires_expensive_model``).
_EXPENSIVE_EXECUTORS: frozenset[str] = frozenset({"opus", "fable"})

#: Task kinds that always warrant escalation to opus/fable.
_ESCALATION_KINDS: frozenset[str] = frozenset({"architecture", "adversarial-review", "design-fork"})

# ── Public types ──────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class CostPreview:
    """Immutable cost estimate for a set of planned tasks.

    Produced by :func:`estimate_cost`; consumed by the finish lane and plan
    preview callers.  All monetary values are in USD.
    """

    #: Total estimated tokens across all tasks (including agent overhead).
    est_tokens: int
    #: Total estimated cost in USD, rounded to 4 decimal places.
    est_cost_usd: float
    #: Cost band: ``"low"``, ``"medium"``, or ``"high"``.
    cost_band: str
    #: True if any task uses a Claude Code agent executor (haiku/sonnet/opus/fable).
    uses_subagents: bool
    #: True if any task routes to opus or fable.
    requires_expensive_model: bool
    #: One-line suggestion when opus/fable is routed on non-hard work, else None.
    cheaper_alternative: str | None
    #: Sorted tuple of distinct role/profile strings seen across items (empty when none provided).
    roles: tuple[str, ...] = ()


# ── Public API ────────────────────────────────────────────────────────────────


def cost_band(usd: float) -> str:
    """Map a USD cost to a cost-band string.

    Returns ``"low"`` if ``usd < BAND_LOW_MAX_USD``, ``"medium"`` if
    ``usd < BAND_MEDIUM_MAX_USD``, else ``"high"``.  Never raises — bad input
    is coerced to ``0.0`` and classified as ``"low"``.
    """
    try:
        amount = float(usd)
    except (TypeError, ValueError):
        amount = 0.0
    if amount < BAND_LOW_MAX_USD:
        return "low"
    if amount < BAND_MEDIUM_MAX_USD:
        return "medium"
    return "high"


def estimate_cost(items: list) -> CostPreview:
    """Estimate the cost of a set of planned tasks.

    Each item in ``items`` may be a :class:`dict` or any object exposing:

    - ``executor`` (str) — the executor name (e.g. ``"haiku"``, ``"codex"``).
      Unknown values are priced at the ``"sonnet"`` rate.
    - ``est_tokens`` (int | None, optional) — planner token estimate; treated
      as ``0`` when absent or non-positive.
    - ``complexity`` (str | None, optional) — task complexity label.  Used to
      detect cheaper-alternative opportunities.

    Returns a :class:`CostPreview`.  **Never raises** — any missing or garbage
    field degrades to ``0`` tokens / sonnet pricing.
    """
    try:
        total_tokens: int = 0
        total_cost: float = 0.0
        uses_subagents: bool = False
        requires_expensive_model: bool = False
        has_expensive_non_hard: bool = False
        seen_roles: set[str] = set()

        for item in items:
            try:
                raw_exec = _get(item, "executor", None)
                executor = raw_exec.strip().lower() if isinstance(raw_exec, str) and raw_exec.strip() else "sonnet"
                if executor not in PRICE_PER_KTOK:
                    executor = "sonnet"

                raw_tokens = _get(item, "est_tokens", None)
                base_tokens = raw_tokens if isinstance(raw_tokens, int) and raw_tokens > 0 else 0

                overhead = AGENT_OVERHEAD_TOKENS if executor in _AGENT_EXECUTORS else 0
                item_tokens = base_tokens + overhead

                price = PRICE_PER_KTOK[executor]
                item_cost = item_tokens / 1000.0 * price

                total_tokens += item_tokens
                total_cost += item_cost

                if executor in _AGENT_EXECUTORS:
                    uses_subagents = True

                if executor in _EXPENSIVE_EXECUTORS:
                    requires_expensive_model = True
                    raw_complexity = _get(item, "complexity", None)
                    complexity = raw_complexity.strip().lower() if isinstance(raw_complexity, str) else ""
                    if complexity != "hard":
                        has_expensive_non_hard = True

                raw_role = _get(item, "role", None)
                if isinstance(raw_role, str) and raw_role.strip():
                    seen_roles.add(raw_role.strip())

            except Exception:  # noqa: BLE001 — item-level failure degrades, never propagates
                pass

        cheaper_alternative: str | None = None
        if has_expensive_non_hard:
            cheaper_alternative = "Task(s) route opus/fable on non-hard work — consider sonnet/haiku"

        return CostPreview(
            est_tokens=total_tokens,
            est_cost_usd=round(total_cost, 4),
            cost_band=cost_band(total_cost),
            uses_subagents=uses_subagents,
            requires_expensive_model=requires_expensive_model,
            cheaper_alternative=cheaper_alternative,
            roles=tuple(sorted(seen_roles)),
        )
    except Exception:  # noqa: BLE001 — top-level guard; return a safe zero preview
        return CostPreview(
            est_tokens=0,
            est_cost_usd=0.0,
            cost_band="low",
            uses_subagents=False,
            requires_expensive_model=False,
            cheaper_alternative=None,
        )


def requires_escalation(*, complexity: str | None = None, kind: str | None = None) -> bool:
    """Return True iff this task warrants escalation to opus or fable.

    Escalation is justified when:

    - ``complexity == "hard"`` — the task is explicitly labelled hard, OR
    - ``kind`` is one of ``{"architecture", "adversarial-review", "design-fork"}``
      — structural task kinds where frontier reasoning pays off.

    All other inputs (including None, garbage, or unrecognised values) return
    False.  **Never raises.**
    """
    try:
        if isinstance(complexity, str) and complexity.strip().lower() == "hard":
            return True
        if isinstance(kind, str) and kind.strip().lower() in _ESCALATION_KINDS:
            return True
        return False
    except Exception:  # noqa: BLE001
        return False


# ── Internal helpers ─────────────────────────────────────────────────────────


def _get(item: object, key: str, default: object) -> object:
    """Read ``key`` from ``item`` whether it is a dict or an object attribute.

    Dict items use ``item[key]``; object items use ``getattr(item, key, default)``.
    Missing keys return ``default``.  Never raises.
    """
    try:
        if isinstance(item, dict):
            return item.get(key, default)
        return getattr(item, key, default)
    except Exception:  # noqa: BLE001
        return default

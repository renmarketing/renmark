"""Deterministic gate-resolution helper bridging the P10 headless contract to
skills (single source of truth: ``plugin/skills/_shared/headless-contract.md``).

When renmark runs non-interactively there is no human to answer an
``AskUserQuestion`` picker. A skill that reaches a Pause-Policy gate calls
:func:`resolve_gate` to decide, deterministically, what to do:

- **interactive** — a human is present; the skill renders its normal menu.
- **headless + safe gate** — auto-pick the recommended option and continue.
- **headless + dangerous gate (or any unrecognised kind — fail safe)** — halt
  via :func:`renmark.lifecycle.halt_for_human_review`, returning a
  ``needs_input`` envelope and a decision artifact.

:func:`render_return` turns any of these envelopes into the one
classifier-friendly prose line the background-job state extractor recognises
(`result:` / `needs input:` / `failed:`).

Design constraints (match :mod:`renmark.config` / :mod:`renmark.lifecycle`):
- stdlib-only, type hints, docstrings.
- never raises — both the config layer and ``halt_for_human_review`` are
  themselves no-raise, and uncertainty about the gate kind always halts rather
  than auto-approving (fail safe).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from . import config, lifecycle


def resolve_gate(
    repo: str | Path,
    gate: str,
    *,
    kind: str,
    recommended: str | None = None,
    tool_available: bool | None = None,
    originating_skill: str | None = None,
    what: str | None = None,
) -> dict[str, Any]:
    """Resolve a Pause-Policy gate for the project at *repo*.

    Detection precedence (headless-contract.md §1): :func:`config.is_headless`
    owns the env/config layers; layer-4 (tool availability) is supplied by the
    skill via *tool_available*. If the config/env verdict is interactive **and**
    ``tool_available is False`` (``AskUserQuestion`` absent from a spawned
    subagent's tool list), the run is forced headless — a picker that can never
    be answered must not stall the run. ``tool_available`` of ``None`` (unknown)
    or ``True`` (present) does not force headless.

    *kind* is ``"safe"`` or ``"dangerous"``:

    - **interactive** → ``{"mode": "interactive"}``; the skill renders its own
      ``AskUserQuestion`` menu (the contract is inert when a human is present).
    - **headless + safe** → success envelope with
      ``decision="auto_picked_recommended"`` carrying *recommended*.
    - **headless + dangerous** (or any other / unrecognised *kind* — uncertainty
      halts, never auto-approves) → the ``needs_input`` envelope from
      :func:`lifecycle.halt_for_human_review`, which also writes the decision
      artifact and arms the lifecycle human-review gate.

    Never raises.
    """
    headless = config.is_headless(repo)
    # Layer-4 fallback: a forced-interactive verdict still degrades to headless
    # when the picker tool is provably absent (spawned subagent). Only an
    # explicit False forces it; None (unknown) / True leave the verdict alone.
    if not headless and tool_available is False:
        headless = True

    if not headless:
        return {"mode": "interactive"}

    if kind == "safe":
        return {
            "status": "success",
            "mode": "headless",
            "gate": gate,
            "decision": "auto_picked_recommended",
            "human_review_required": False,
            "artifacts": [],
            "recommended": recommended,
        }

    # Dangerous, or any unrecognised kind: fail safe — halt for human review
    # rather than risk auto-approving a merge/release/destructive op.
    return lifecycle.halt_for_human_review(
        repo,
        gate,
        originating_skill=originating_skill or "",
        what=what or gate,
    )


def render_return(envelope: dict[str, Any]) -> str:
    """Render *envelope* as one classifier-friendly prose line.

    Uses the repo's background-job classifier vocabulary verbatim
    (`result:` / `needs input:` / `failed:`) so the job-list state extractor
    catches the outcome. Returns ``""`` for an interactive envelope — the skill
    renders its own menu and there is no headless prose to emit. Never raises.
    """
    if envelope.get("mode") == "interactive":
        return ""

    status = envelope.get("status")
    if status == "success":
        return f"result: {envelope.get('decision') or envelope.get('recommended') or 'done'}"
    if status == "needs_input":
        gate = envelope.get("gate")
        return f"needs input: {gate} approval required; headless mode cannot approve {gate}"
    if status == "failed":
        return f"failed: {envelope.get('reason', 'blocked')}"

    # Unknown / malformed envelope — degrade to a blocked-failure line rather
    # than raising into a skill's hand-off.
    return f"failed: {envelope.get('reason', 'blocked')}"

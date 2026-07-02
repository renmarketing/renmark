"""Skill-invocation tracking (.renmark/state/last-skill.json).

G4: subject-change detection for context-contamination prompts.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from ._core import LAST_SKILL_FILE, now_iso, state_dir

# Absolute context-token thresholds for context_budget_hint.
# These COMPLEMENT the existing 60%/80% self-monitored budget rules in CLAUDE.md
# (which the orchestrator self-monitors) and the cross-domain /clear hint produced
# by context_budget_check — none of those are altered here.
CTX_SUMMARIZE = 100_000
CTX_COMPACT = 120_000
CTX_CHECKPOINT = 150_000


def context_budget_hint(tokens: int) -> str | None:
    """Return a human-readable budget hint for the given absolute token count.

    Returns None when tokens is below CTX_SUMMARIZE or invalid (non-int, bool,
    negative).  Never raises.

    These absolute tiers COMPLEMENT the existing 60%/80% self-monitored budget
    rule and the cross-domain /clear hint from context_budget_check — neither of
    those is altered by this helper.

    Tiers:
      CTX_SUMMARIZE (100k) — summarize the current stage.
      CTX_COMPACT   (120k) — recommend /compact before the next skill.
      CTX_CHECKPOINT(150k) — strongly recommend /compact or a checkpoint.
    """
    # Guard: booleans are ints in Python; treat them as invalid.
    if isinstance(tokens, bool):
        return None
    if not isinstance(tokens, int):
        return None
    if tokens < 0:
        return None
    if tokens < CTX_SUMMARIZE:
        return None
    if tokens < CTX_COMPACT:
        return "≈100k context — summarize the current stage before continuing."
    if tokens < CTX_CHECKPOINT:
        return "≈120k context — recommend `/compact` before the next skill."
    return "≈150k context — strongly recommend `/compact` or a checkpoint before continuing."


def _last_skill_path(repo_root: str | Path) -> Path:
    return state_dir(repo_root) / LAST_SKILL_FILE


def record_skill_invocation(repo_root: str | Path, skill_name: str, domain: str) -> None:
    """Append-style record of which skill ran last and in which domain.

    Used by context_budget_check to detect cross-domain transitions and
    suggest /clear (per G4 / context-contamination-rule).
    """
    payload = {
        "skill": skill_name,
        "domain": domain,
        "timestamp": now_iso(),
    }
    path = _last_skill_path(repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def last_skill_invocation(repo_root: str | Path) -> dict[str, Any] | None:
    path = _last_skill_path(repo_root)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    if not isinstance(data, dict):
        # Valid JSON but not an object — treat like corruption, never raise:
        # this runs inside every skill's Step 0 preamble.
        return None
    return cast(dict[str, Any], data)


def context_budget_check(repo_root: str | Path, new_skill: str, new_domain: str) -> str | None:
    """Return 'clear' if cross-domain transition detected; else None.

    The %-utilization branch ('compact' recommendation) is NOT detectable from
    inside a skill — the harness doesn't expose context size. That side lives
    in the rule prose (context-budget-rule in CLAUDE.md) which the orchestrator
    self-monitors. This helper handles only the local-state half.
    """
    last = last_skill_invocation(repo_root)
    if last is None:
        return None
    prev_domain = last.get("domain")
    if prev_domain and prev_domain != new_domain:
        return "clear"
    return None

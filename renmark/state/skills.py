"""Skill-invocation tracking (.renmark/state/last-skill.json).

G4: subject-change detection for context-contamination prompts.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from ._core import LAST_SKILL_FILE, now_iso, state_dir


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
        return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))
    except (json.JSONDecodeError, OSError):
        return None


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

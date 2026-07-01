"""Persisted operating-mode state for renmark (Conductor vs Orchestrator).

The operating mode is chosen at pipeline entry and controls how much the
orchestrator drives vs. delegates.  It is *runtime* state — it lives at
``.renmark/state/mode.json`` (gitignored), alongside ``pipeline.json``, not the
committed ``.renmark/config.json`` which holds durable user preferences.

Design constraints (mirroring :mod:`renmark.config` and :mod:`renmark.state`):
- stdlib json only (no third-party deps).
- Reads never raise: a missing file, unreadable file, corrupt JSON, non-dict
  payload, or unrecognised mode value all degrade to ``None`` — the caller
  treats "no mode set" as "fall back to the skill default".
- ``set_mode`` *does* validate its argument and raises ``ValueError`` on an
  unknown mode, because that is a programming error, not a state-file quirk.
- ``clear_mode`` is idempotent — removing an absent file is a no-op.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

Mode = Literal["conductor", "orchestrator"]

_MODE_REL = ".renmark/state/mode.json"

_VALID_MODES: frozenset[str] = frozenset({"conductor", "orchestrator"})

# Per-skill default mode.  Debug/brainstorm are conductor (tight, orchestrator
# stays hands-on); the build pipelines are orchestrator (fan-out to isolated
# subagents).  Anything unmapped (roadmap / meta / unknown) falls back to
# orchestrator.
_DEFAULT_BY_SKILL: dict[str, Mode] = {
    "debug": "conductor",
    "brainstorm": "conductor",
    "start": "orchestrator",
    "feature": "orchestrator",
    "orchestrate": "orchestrator",
    "finish": "orchestrator",
    "loop": "orchestrator",
}

_FALLBACK_MODE: Mode = "orchestrator"


def _mode_path(repo: str | Path) -> Path:
    return Path(repo) / _MODE_REL


def read_mode(repo: str | Path) -> Mode | None:
    """Return the persisted operating mode for the project at *repo*.

    Returns ``"conductor"`` or ``"orchestrator"`` when a valid mode is on disk,
    else ``None``.  Never raises — a missing / unreadable / corrupt / non-dict
    file, or an unrecognised ``"mode"`` value, all degrade to ``None`` so the
    caller falls through to :func:`default_mode_for_skill`.
    """
    try:
        text = _mode_path(repo).read_text(encoding="utf-8")
        data = json.loads(text)
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    val = data.get("mode")
    if val == "conductor":
        return "conductor"
    if val == "orchestrator":
        return "orchestrator"
    return None


def set_mode(repo: str | Path, mode: str) -> None:
    """Persist the operating *mode* for the project at *repo*.

    Creates ``.renmark/state/`` if missing and writes ``mode.json``.  Raises
    :class:`ValueError` on any mode other than ``"conductor"`` /
    ``"orchestrator"`` — an invalid mode is a caller bug, not silent state.
    The write itself is best-effort and does not raise on OS errors.
    """
    if mode not in _VALID_MODES:
        raise ValueError(
            f"invalid mode {mode!r}: expected 'conductor' or 'orchestrator'"
        )
    try:
        p = _mode_path(repo)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({"mode": mode}, indent=2) + "\n", encoding="utf-8")
    except Exception:
        pass


def clear_mode(repo: str | Path) -> None:
    """Remove the persisted mode for the project at *repo*.

    Idempotent — clearing when no mode is set is a no-op.  Never raises.
    """
    try:
        _mode_path(repo).unlink()
    except FileNotFoundError:
        pass
    except Exception:
        pass


def default_mode_for_skill(skill: str) -> Mode:
    """Return the default operating mode for *skill*.

    ``"conductor"`` for ``debug`` / ``brainstorm``; ``"orchestrator"`` for the
    build pipelines (``start`` / ``feature`` / ``orchestrate`` / ``finish`` /
    ``loop``); ``"orchestrator"`` fallback for anything else (roadmap / meta /
    unknown).
    """
    return _DEFAULT_BY_SKILL.get(skill, _FALLBACK_MODE)

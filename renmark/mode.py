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
  A *write* failure (read-only FS, ENOSPC, permission denied) is NOT swallowed:
  it propagates as ``OSError`` so the caller can report it and exit non-zero
  rather than falsely claiming success.  The write is atomic — a temp file in
  the same ``.renmark/state`` dir is ``os.replace``d into place, so a concurrent
  reader never observes a partially-written ``mode.json``.
- ``clear_mode`` is idempotent — removing an absent file is a no-op (no raise) —
  but a genuine delete failure (permission denied, etc.) propagates as ``OSError``.
"""

from __future__ import annotations

import contextlib
import json
import os
from pathlib import Path
from typing import Literal

Mode = Literal["conductor", "orchestrator"]

MODE_REL = ".renmark/state/mode.json"
# Backwards-compatible alias for the module-relative constant.
_MODE_REL = MODE_REL

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


def mode_state_path(repo: str | Path) -> Path:
    """Return the absolute path where the operating mode is persisted.

    This is the single source of truth for the mode-state location
    (``<repo>/.renmark/state/mode.json``).  User-facing help / success strings
    MUST derive their path text from here so they can never drift from the
    actual write location.
    """
    return Path(repo) / MODE_REL


def _mode_path(repo: str | Path) -> Path:
    return mode_state_path(repo)


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

    A genuine write failure (read-only FS, ENOSPC, permission denied) is NOT
    swallowed — it propagates as :class:`OSError` — so a caller never reports
    success on a persistence that did not happen.  The write is atomic: the
    JSON is written to a temp file in the same ``.renmark/state`` directory and
    ``os.replace``d into place, so a concurrent reader never observes a
    partially-written file.
    """
    if mode not in _VALID_MODES:
        raise ValueError(
            f"invalid mode {mode!r}: expected 'conductor' or 'orchestrator'"
        )
    p = _mode_path(repo)
    p.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps({"mode": mode}, indent=2) + "\n"
    tmp = p.with_name(p.name + f".tmp.{os.getpid()}")
    try:
        tmp.write_text(payload, encoding="utf-8")
        os.replace(tmp, p)
    except OSError:
        # Best-effort cleanup of the temp file, then surface the real failure.
        with contextlib.suppress(OSError):
            tmp.unlink()
        raise


def clear_mode(repo: str | Path) -> None:
    """Remove the persisted mode for the project at *repo*.

    Idempotent — clearing when no mode is set is a no-op (an absent file counts
    as success and does not raise).  A genuine delete failure (permission
    denied, etc.) is surfaced as :class:`OSError`, never silently swallowed.
    """
    with contextlib.suppress(FileNotFoundError):
        _mode_path(repo).unlink()


def default_mode_for_skill(skill: str) -> Mode:
    """Return the default operating mode for *skill*.

    ``"conductor"`` for ``debug`` / ``brainstorm``; ``"orchestrator"`` for the
    build pipelines (``start`` / ``feature`` / ``orchestrate`` / ``finish`` /
    ``loop``); ``"orchestrator"`` fallback for anything else (roadmap / meta /
    unknown).
    """
    return _DEFAULT_BY_SKILL.get(skill, _FALLBACK_MODE)

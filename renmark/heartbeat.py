"""Proactive heartbeat checker for usage-limit pauses.

Polls ``.renmark/state/PAUSED`` and, when a ``usage_limit`` pause has reached
(or passed) its ``resume_after`` window, prints a human-readable nudge so the
user knows the limit may have cleared.

Design contract:
- **Zero LLM calls.** Pure deterministic Python — no model invocations anywhere.
- **No clock reads inside** :func:`check`. The caller always injects ``now`` as
  an ISO8601 string, making the function fully testable without mocking.
- **Print-only** :func:`emit_cron`. Returns a string describing how to wire the
  heartbeat to cron / Windows Task Scheduler; never writes any file.
- **Optional auto-resume** :func:`auto_resume`. Delegates to
  ``renmark-execute --resume`` as a pure subprocess; zero LLM calls.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from renmark.state.pause import PauseState, read_pause

HEARTBEAT_OK = "HEARTBEAT_OK"


@dataclass
class HeartbeatResult:
    """Result of a single heartbeat check."""

    should_notify: bool
    """True → caller should print ``message``; False → silent (HEARTBEAT_OK)."""

    message: str
    """Either :data:`HEARTBEAT_OK` or a human-readable 3-line-max status."""

    pause_state: PauseState | None = None
    """The raw pause state that was read, if any."""

    check_ts: str = ""
    """ISO8601 timestamp injected by the caller via the ``now`` parameter."""


def check(repo: Path | str, *, now: str) -> HeartbeatResult:
    """Read pause state; compare ``resume_after`` to *now* (caller injects time).

    Parameters
    ----------
    repo:
        Path to the repository root (``state_dir`` is resolved relative to it).
    now:
        Current time as an ISO8601 string supplied by the caller — never read
        from the clock internally, so tests can inject any timestamp.

    Returns
    -------
    HeartbeatResult
        ``should_notify=False`` (silent) when:

        * No PAUSED file exists.
        * ``pause_kind != "usage_limit"``.
        * ``resume_after`` is set **and** ``now < resume_after`` (still waiting).

        ``should_notify=True`` when ``resume_after`` is empty **or**
        ``now >= resume_after`` — the usage window may have cleared.
    """
    ps = read_pause(repo)

    if ps is None or ps.pause_kind != "usage_limit":
        return HeartbeatResult(
            should_notify=False,
            message=HEARTBEAT_OK,
            pause_state=ps,
            check_ts=now,
        )

    # If resume_after is set and we haven't reached it yet → stay silent.
    if ps.resume_after and now < ps.resume_after:
        return HeartbeatResult(
            should_notify=False,
            message=HEARTBEAT_OK,
            pause_state=ps,
            check_ts=now,
        )

    # Limit may have cleared — build the human-readable nudge (≤3 lines).
    lines: list[str] = ["Usage limit may have cleared."]

    # Build the context line only from non-empty fields.
    context_parts: list[str] = []
    if ps.feature:
        context_parts.append(f"Feature: {ps.feature}")
    if ps.loop_id:
        iter_str = f"iter {ps.iteration}/{ps.max_iterations}" if ps.max_iterations else f"iter {ps.iteration}"
        context_parts.append(f"Loop: {ps.loop_id} {iter_str}")
    if context_parts:
        lines.append("  ".join(context_parts))

    lines.append("Run: renmark-execute --resume  (or /renmark:resume)")

    return HeartbeatResult(
        should_notify=True,
        message="\n".join(lines),
        pause_state=ps,
        check_ts=now,
    )


def auto_resume(repo: Path | str) -> int:
    """Invoke ``renmark-execute --resume`` as a subprocess and return exit code.

    Zero LLM calls — purely a CLI subprocess delegation. Intended for the
    ``--auto-resume`` CLI flag so a scheduled cron job can self-heal after a
    usage-limit window expires.

    Parameters
    ----------
    repo:
        Repository root passed as ``cwd`` to the subprocess.

    Returns
    -------
    int
        Exit code from ``renmark-execute --resume``.
    """
    result = subprocess.run(
        ["renmark-execute", "--resume"],
        cwd=Path(repo),
    )
    return result.returncode


def emit_cron(repo: Path | str, *, interval_minutes: int = 30) -> str:
    """Return (PRINT-only, never writes) the cron / Task Scheduler setup text.

    The PRIMARY emitted trigger is ``renmark-execute --heartbeat`` — a pure-Python
    zero-LLM check that prints a nudge when the usage-limit window has cleared.
    An OPTIONAL ``--auto-resume`` variant is also shown; it calls
    ``renmark-execute --resume`` automatically when the limit clears.

    Parameters
    ----------
    repo:
        Repository root (used to render the ``cd <repo>`` prefix in the crontab
        line).
    interval_minutes:
        How often to run the heartbeat check. Defaults to 30.

    Returns
    -------
    str
        A comment block suitable for pasting into crontab or a scheduler config.
        Pure string — never writes, never raises.
    """
    repo = Path(repo)
    cron_freq = f"*/{interval_minutes}" if interval_minutes > 1 else "*"
    crontab_line = f"{cron_freq} * * * * cd {repo} && renmark-execute --heartbeat"
    crontab_auto = f"{cron_freq} * * * * cd {repo} && renmark-execute --heartbeat --auto-resume"

    return (
        f"# renmark:heartbeat — proactive usage-limit cleared notifier\n"
        f"# repo: {repo}\n"
        f"#\n"
        f"# ============================================================\n"
        f"# PRIMARY — pure-Python, zero LLM calls.\n"
        f"#   Reads .renmark/state/PAUSED; if a usage_limit pause has reached\n"
        f"#   (or passed) its resume_after window, prints a one-line nudge so\n"
        f"#   you know the limit may have cleared. Silent (exit 0) otherwise.\n"
        f"#   No Claude token required — only the repo checkout + Python on PATH.\n"
        f"# ============================================================\n"
        f"#   cd {repo} && renmark-execute --heartbeat\n"
        f"#\n"
        f"# crontab (run every {interval_minutes} min):\n"
        f"#   {crontab_line}\n"
        f"#\n"
        f"# ------------------------------------------------------------\n"
        f"# OPTIONAL — auto-resume variant.\n"
        f"#   Same heartbeat check, but also calls renmark-execute --resume\n"
        f"#   automatically when the limit has cleared. Use only if you trust\n"
        f"#   unattended resume (no human gate). Still zero LLM calls for the\n"
        f"#   heartbeat check itself; the --resume subprocess may invoke the model.\n"
        f"# ------------------------------------------------------------\n"
        f"#   cd {repo} && renmark-execute --heartbeat --auto-resume\n"
        f"#\n"
        f"# crontab (auto-resume variant):\n"
        f"#   {crontab_auto}\n"
        f"#\n"
        f"# Windows Task Scheduler equivalent (PowerShell):\n"
        f"#   $action = New-ScheduledTaskAction -Execute 'renmark-execute'"
        f" -Argument '--heartbeat' -WorkingDirectory '{repo}'\n"
        f"#   $trigger = New-ScheduledTaskTrigger"
        f" -RepetitionInterval (New-TimeSpan -Minutes {interval_minutes})"
        f" -Once -At (Get-Date)\n"
        f"#   Register-ScheduledTask -TaskName 'renmark-heartbeat'"
        f" -Action $action -Trigger $trigger\n"
    )


__all__ = ["HEARTBEAT_OK", "HeartbeatResult", "check", "auto_resume", "emit_cron"]

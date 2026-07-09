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

import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path

from renmark.state.pause import PauseState, read_pause

HEARTBEAT_OK = "HEARTBEAT_OK"


def _parse_iso(ts: str) -> "datetime.datetime":
    """Parse an ISO8601 timestamp string, normalising the trailing ``Z``."""
    import datetime
    return datetime.datetime.fromisoformat(ts.replace("Z", "+00:00"))


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
    """Run all registered proactive checks and aggregate results.

    Fans out to heartbeat_checks.run_all_checks() — each individual check
    handles its own exceptions and returns a CheckResult. Never raises.
    """
    from renmark.heartbeat_checks import run_all_checks

    results = run_all_checks(repo, now=now)

    if not results:
        return HeartbeatResult(
            should_notify=False,
            message=HEARTBEAT_OK,
            pause_state=None,
            check_ts=now,
        )

    return HeartbeatResult(
        should_notify=True,
        message="\n---\n".join(r.message for r in results),
        pause_state=None,
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
    try:
        result = subprocess.run(
            ["renmark-execute", "--resume"],
            cwd=Path(repo),
            timeout=300,
        )
        return result.returncode
    except subprocess.TimeoutExpired:
        return 1
    except OSError:
        return 1


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
    if interval_minutes <= 0:
        raise ValueError(f"interval_minutes must be positive, got {interval_minutes}")
    repo = Path(repo)
    cron_freq = f"*/{interval_minutes}" if interval_minutes > 1 else "*"
    crontab_line = f"{cron_freq} * * * * cd {shlex.quote(str(repo))} && renmark-execute --heartbeat"
    crontab_auto = f"{cron_freq} * * * * cd {shlex.quote(str(repo))} && renmark-execute --heartbeat --auto-resume"

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

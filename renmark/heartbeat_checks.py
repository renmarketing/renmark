"""
Proactive heartbeat check functions for renmark.

Each function is:
- Non-raising (returns CheckResult(should_notify=False) on any error)
- Zero LLM calls
- Pure file IO + timestamp comparison
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from renmark.heartbeat import _parse_iso  # shared ISO parser

TERMINAL_LIFECYCLE_STAGES = {"init", "released"}
STUCK_BACKLOG_STATUSES = {"in progress", "needs approval", "blocked"}


@dataclass
class CheckResult:
    check_name: str
    should_notify: bool
    message: str = ""  # empty string when should_notify=False


def check_usage_limit_pause(repo: Path | str, *, now: str) -> CheckResult:
    """Usage-limit pause: notify when resume_after window has cleared."""
    try:
        from renmark.state.pause import read_pause

        ps = read_pause(repo)
        if ps is None or ps.pause_kind != "usage_limit":
            return CheckResult(check_name="usage_limit_pause", should_notify=False)

        if ps.resume_after:
            try:
                if _parse_iso(now) < _parse_iso(ps.resume_after):
                    return CheckResult(check_name="usage_limit_pause", should_notify=False)
            except (ValueError, TypeError):
                pass  # Unparseable timestamps → assume limit cleared

        lines: list[str] = ["Usage limit may have cleared."]
        context_parts: list[str] = []
        if ps.feature:
            context_parts.append(f"Feature: {ps.feature}")
        if ps.loop_id:
            iter_str = (
                f"iter {ps.iteration}/{ps.max_iterations}"
                if ps.max_iterations
                else f"iter {ps.iteration}"
            )
            context_parts.append(f"Loop: {ps.loop_id} {iter_str}")
        if context_parts:
            lines.append("  ".join(context_parts))
        lines.append("Run: renmark-execute --resume  (or /renmark:resume)")

        return CheckResult(
            check_name="usage_limit_pause",
            should_notify=True,
            message="\n".join(lines),
        )
    except Exception:
        return CheckResult(check_name="usage_limit_pause", should_notify=False)


def check_stalled_feature(
    repo: Path | str, *, now: str, stall_hours: float = 4.0
) -> CheckResult:
    """Feature lifecycle stuck in intermediate stage for > stall_hours."""
    try:
        from renmark.lifecycle import read_lifecycle

        lc = read_lifecycle(repo)
        if lc is None:
            return CheckResult(check_name="stalled_feature", should_notify=False)

        # Approval gate check — takes priority over stall timer.
        if lc.human_review_required and not lc.human_review_completed:
            msg = (
                f"Feature '{lc.feature}' is awaiting human approval.\n"
                f"  Next: /renmark:approve"
            )
            return CheckResult(
                check_name="stalled_feature", should_notify=True, message=msg
            )

        if lc.stage in TERMINAL_LIFECYCLE_STAGES:
            return CheckResult(check_name="stalled_feature", should_notify=False)

        if not lc.last_updated:
            return CheckResult(check_name="stalled_feature", should_notify=False)

        try:
            updated = _parse_iso(lc.last_updated)
            current = _parse_iso(now)
            elapsed_hours = (current - updated).total_seconds() / 3600.0
        except (ValueError, TypeError):
            return CheckResult(check_name="stalled_feature", should_notify=False)

        if elapsed_hours <= stall_hours:
            return CheckResult(check_name="stalled_feature", should_notify=False)

        next_hint = lc.next_recommended or "/renmark:resume"
        msg = (
            f"Feature '{lc.feature}' has been at stage '{lc.stage}'"
            f" for {elapsed_hours:.1f} hours.\n"
            f"  Next: {next_hint}"
        )
        return CheckResult(check_name="stalled_feature", should_notify=True, message=msg)
    except Exception:
        return CheckResult(check_name="stalled_feature", should_notify=False)


def check_stalled_pipeline(
    repo: Path | str, *, now: str, stall_hours: float = 2.0
) -> CheckResult:
    """Pipeline wave stuck in 'orchestrate' phase for > stall_hours."""
    try:
        from renmark.state.pipeline import read_pipeline_state

        ps = read_pipeline_state(repo)
        if ps is None or ps.current_phase != "orchestrate":
            return CheckResult(check_name="stalled_pipeline", should_notify=False)

        if not ps.last_updated:
            return CheckResult(check_name="stalled_pipeline", should_notify=False)

        try:
            updated = _parse_iso(ps.last_updated)
            current = _parse_iso(now)
            elapsed_hours = (current - updated).total_seconds() / 3600.0
        except (ValueError, TypeError):
            return CheckResult(check_name="stalled_pipeline", should_notify=False)

        if elapsed_hours <= stall_hours:
            return CheckResult(check_name="stalled_pipeline", should_notify=False)

        msg = (
            f"Pipeline wave {ps.wave_index}/{ps.wave_total} has not advanced"
            f" in {elapsed_hours:.1f} hours.\n"
            f"  Next: /renmark:resume"
        )
        return CheckResult(
            check_name="stalled_pipeline", should_notify=True, message=msg
        )
    except Exception:
        return CheckResult(check_name="stalled_pipeline", should_notify=False)


def check_blocked_backlog(
    repo: Path | str, *, now: str, stall_hours: float = 48.0
) -> CheckResult:
    """Backlog items stuck in non-terminal states for > stall_hours."""
    try:
        backlog_dir = Path(repo) / ".renmark" / "state" / "backlog"
        if not backlog_dir.is_dir():
            return CheckResult(check_name="blocked_backlog", should_notify=False)

        stuck: list[tuple[float, str, str]] = []  # (elapsed_hours, id, title_or_id)
        for item_path in backlog_dir.glob("BL-*.json"):
            try:
                data = json.loads(item_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if not isinstance(data, dict):
                continue

            status = str(data.get("status", "")).lower()
            disposition = str(data.get("disposition", ""))
            updated_at = str(data.get("updated_at", ""))
            item_id = str(data.get("id", item_path.stem))

            if status not in STUCK_BACKLOG_STATUSES:
                continue
            if disposition != "":
                continue
            if not updated_at:
                continue

            try:
                updated = _parse_iso(updated_at)
                current = _parse_iso(now)
                elapsed_hours = (current - updated).total_seconds() / 3600.0
            except (ValueError, TypeError):
                continue

            if elapsed_hours > stall_hours:
                title = str(data.get("title", item_id))
                stuck.append((elapsed_hours, item_id, title))

        if not stuck:
            return CheckResult(check_name="blocked_backlog", should_notify=False)

        # Sort by oldest first.
        stuck.sort(key=lambda x: x[0], reverse=True)
        _oldest_elapsed, oldest_id, oldest_title = stuck[0]
        count = len(stuck)
        msg = (
            f"{count} backlog item(s) have not moved in >{stall_hours:.0f}h"
            f" (oldest: {oldest_id} '{oldest_title}').\n"
            f"  Next: /renmark:backlog"
        )
        return CheckResult(
            check_name="blocked_backlog", should_notify=True, message=msg
        )
    except Exception:
        return CheckResult(check_name="blocked_backlog", should_notify=False)


def check_awaiting_loop(repo: Path | str) -> CheckResult:
    """Loops blocked on human approval gate or in stalled state."""
    try:
        loops_dir = Path(repo) / ".renmark" / "loops"
        if not loops_dir.is_dir():
            return CheckResult(check_name="awaiting_loop", should_notify=False)

        blocked: list[tuple[str, str]] = []  # (loop_id, pending_step)
        for loop_json in loops_dir.glob("*/loop.json"):
            try:
                data = json.loads(loop_json.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if not isinstance(data, dict):
                continue

            status = str(data.get("status", ""))
            if status not in ("awaiting-approval", "stalled"):
                continue

            loop_id = loop_json.parent.name
            pending_step = str(data.get("pending_step", ""))
            blocked.append((loop_id, pending_step))

        if not blocked:
            return CheckResult(check_name="awaiting_loop", should_notify=False)

        loop_id, pending_step = blocked[0]
        pending_desc = f" (pending: {pending_step})" if pending_step else ""
        msg = (
            f"Loop {loop_id} is awaiting approval{pending_desc}.\n"
            f"  Next: /renmark:approve"
        )
        return CheckResult(
            check_name="awaiting_loop", should_notify=True, message=msg
        )
    except Exception:
        return CheckResult(check_name="awaiting_loop", should_notify=False)


def run_all_checks(repo: Path | str, *, now: str) -> list[CheckResult]:
    """Run all registered checks; return only those with should_notify=True."""
    checks = [
        check_usage_limit_pause(repo, now=now),
        check_stalled_feature(repo, now=now),
        check_stalled_pipeline(repo, now=now),
        check_blocked_backlog(repo, now=now),
        check_awaiting_loop(repo),
    ]
    return [c for c in checks if c.should_notify]


__all__ = [
    "CheckResult",
    "check_awaiting_loop",
    "check_blocked_backlog",
    "check_stalled_feature",
    "check_stalled_pipeline",
    "check_usage_limit_pause",
    "run_all_checks",
]

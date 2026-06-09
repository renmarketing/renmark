"""Usage-status engine (REQ-15/REQ-16).

Bounded, non-raising views over the local usage ledger plus a fallback-rule
classifier that builds a usage-limit ``PauseState``. This module reads no clock
of its own — callers inject ``now`` (ISO-8601) so views and pauses are
deterministic and testable. Provider-side account quotas are NEVER fabricated:
a provider used/limit/reset block is surfaced only when an actual ledger row is
``source == "provider-reported"``.

Public API (for CLI ``cmd_usage`` + orchestrate/loop preflight):
  build_usage_view(repo, *, now) -> dict
  render_usage_md(view) -> str
  classify_usage_pause(...) -> PauseState
  read_limits(repo) -> dict
  percent_used(observed, limit) -> float | None
  DISCLAIMER
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any

from renmark import state

DISCLAIMER = "Observed local usage only. Provider-side account limits may differ."

_LIMIT_EVENT_KINDS = {"rate_limit", "quota"}
_FIVE_HOURS = 5 * 3600
_ONE_WEEK = 7 * 24 * 3600
_NO_LOCAL_LIMIT = "no configured local limit"


def read_limits(repo: str | Path) -> dict[str, Any]:
    """Read ``.renmark/analytics/limits.json``; ``{}`` if absent/corrupt.

    Schema (all keys optional): {"claude": {"rolling_5h_tokens": int,
    "weekly_tokens": int, "rolling_5h_requests": int, "weekly_requests": int},
    "codex": {...}}. Non-raising: any read/parse error yields ``{}``.
    """
    path = Path(repo) / ".renmark" / "analytics" / "limits.json"
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return {}
    try:
        parsed = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def percent_used(observed: int, limit: int | None) -> float | None:
    """Percent of ``limit`` consumed by ``observed``; None when no usable limit."""
    if limit is None:
        return None
    try:
        lim = int(limit)
    except (TypeError, ValueError):
        return None
    if lim <= 0:
        return None
    try:
        obs = int(observed)
    except (TypeError, ValueError):
        obs = 0
    return round(100 * obs / lim, 1)


def _provider_limit(limits: dict[str, Any], provider: str, key: str) -> int | None:
    """Pull an int limit ``key`` for ``provider`` from ``limits``; None if absent."""
    block = limits.get(provider)
    if not isinstance(block, dict):
        return None
    value = block.get(key)
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _provider_percent(limits: dict[str, Any], provider: str, key: str,
                      observed: int) -> float | str | None:
    """Percent for one provider/key, or the no-local-limit sentinel when unset."""
    limit = _provider_limit(limits, provider, key)
    if limit is None:
        return _NO_LOCAL_LIMIT
    return percent_used(observed, limit)


def _recent_limit_events(repo: str | Path) -> list[dict[str, str]]:
    """Last 5 ledger rows whose kind is a limit event; bounded fields only."""
    events: list[dict[str, str]] = []
    for r in state.read_usage(repo):
        kind = r.get("kind", "")
        if kind in _LIMIT_EVENT_KINDS:
            events.append({
                "ts": str(r.get("ts", "")),
                "provider": str(r.get("provider", "")),
                "kind": str(kind),
            })
    return events[-5:]


def _provider_reported_block(repo: str | Path) -> dict[str, str] | None:
    """A used/limit/reset block from the latest provider-reported row, else None.

    Never fabricated: returns None unless some ledger row carries
    ``source == "provider-reported"``.
    """
    latest: dict[str, Any] | None = None
    for r in state.read_usage(repo):
        if isinstance(r, dict) and r.get("source") == "provider-reported":
            latest = r
    if latest is None:
        return None
    return {
        "used": str(latest.get("used", latest.get("total_tokens", ""))),
        "limit": str(latest.get("limit", "")),
        "reset": str(latest.get("reset", latest.get("provider_reset_at", ""))),
        "provider": str(latest.get("provider", "")),
    }


def _paused_run(repo: str | Path) -> dict[str, str] | None:
    """Usage-limit pause summary from PAUSED state, else None."""
    pause = state.read_pause(repo)
    if pause is None or pause.pause_kind != "usage_limit":
        return None
    return {
        "resume_after": pause.resume_after,
        "provider": pause.provider,
        "observed_usage": pause.observed_usage,
        "reason": pause.reason,
    }


def build_usage_view(repo: str | Path, *, now: str) -> dict[str, Any]:
    """Assemble the bounded usage view dict (no raw ledger rows leak out)."""
    rolling_5h = state.usage_last_5h(repo, now=now)
    weekly = state.usage_last_week(repo, now=now)
    limits = read_limits(repo)
    view: dict[str, Any] = {
        "now": now,
        "rolling_5h": rolling_5h,
        "weekly": weekly,
        "limits": limits,
        "percent": {
            "claude": {
                "rolling_5h_tokens": _provider_percent(
                    limits, "claude", "rolling_5h_tokens",
                    rolling_5h.get("total_tokens", 0)),
                "weekly_tokens": _provider_percent(
                    limits, "claude", "weekly_tokens",
                    weekly.get("total_tokens", 0)),
            },
            "codex": {
                "rolling_5h_tokens": _provider_percent(
                    limits, "codex", "rolling_5h_tokens",
                    rolling_5h.get("total_tokens", 0)),
                "weekly_tokens": _provider_percent(
                    limits, "codex", "weekly_tokens",
                    weekly.get("total_tokens", 0)),
            },
        },
        "top_features": state.tokens_by_feature(
            repo, now=now, seconds=_ONE_WEEK, top=5),
        "recent_limit_events": _recent_limit_events(repo),
        "paused_run": _paused_run(repo),
        "disclaimer": DISCLAIMER,
    }
    provider_reported = _provider_reported_block(repo)
    if provider_reported is not None:
        view["provider_reported"] = provider_reported
    return view


def _parse_iso(value: str) -> dt.datetime | None:
    """Parse a (Z-tolerant) ISO-8601 string to an aware datetime; None on error."""
    if not value or not isinstance(value, str):
        return None
    candidate = value.strip()
    if candidate.endswith("Z"):
        candidate = candidate[:-1] + "+00:00"
    try:
        parsed = dt.datetime.fromisoformat(candidate)
    except (ValueError, TypeError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed


def _has_rolling_5h_window(limits: dict[str, Any], provider: str) -> bool:
    """True when ``provider`` has a configured rolling-5h token/request limit."""
    return (_provider_limit(limits, provider, "rolling_5h_tokens") is not None
            or _provider_limit(limits, provider, "rolling_5h_requests") is not None)


def _compute_resume_after(*, now: str, provider: str,
                          provider_reset_at: str,
                          limits: dict[str, Any]) -> str:
    """Fallback rule for resume_after: provider reset > local 5h window > +60m."""
    if provider_reset_at:
        return provider_reset_at
    base = _parse_iso(now)
    if base is None:
        return provider_reset_at  # cannot compute; echo (possibly empty) input
    if _has_rolling_5h_window(limits, provider):
        return (base + dt.timedelta(seconds=_FIVE_HOURS)).isoformat()
    return (base + dt.timedelta(minutes=60)).isoformat()


def classify_usage_pause(*, run_id: str, plan_path: str, last_task_index: int,
                         now: str, provider: str = "", model: str = "",
                         observed_usage: str = "", provider_reset_at: str = "",
                         limits: dict[str, Any] | None = None,
                         feature: str = "", loop_id: str = "",
                         iteration: int = 0,
                         max_iterations: int = 0) -> state.PauseState:
    """Build a usage-limit PauseState with resume_after by the fallback rule.

    No polling, no retry scheduling — purely computes resume_after and delegates
    to ``state.usage_limit_pause``. ``ts`` is the injected ``now``.
    """
    resolved_limits = limits if isinstance(limits, dict) else {}
    resume_after = _compute_resume_after(
        now=now, provider=provider, provider_reset_at=provider_reset_at,
        limits=resolved_limits)
    return state.usage_limit_pause(
        run_id=run_id, plan_path=plan_path, last_task_index=last_task_index,
        ts=now, provider=provider, model=model, observed_usage=observed_usage,
        provider_reset_at=provider_reset_at, resume_after=resume_after,
        fallback_retry_minutes=60, feature=feature, loop_id=loop_id,
        iteration=iteration, max_iterations=max_iterations)


def _percent_str(value: float | str | None) -> str:
    """Human string for a percent cell (float, sentinel, or None)."""
    if value is None:
        return "no configured local limit is set"
    if isinstance(value, str):
        return "no configured local limit is set"
    return f"{value}%"


def _window_block(title: str, window: dict[str, Any],
                  percents: dict[str, dict[str, Any]], key: str) -> list[str]:
    """Markdown lines for one rolling/weekly window with per-provider percent."""
    lines = [
        f"## {title}",
        f"- total tokens: {window.get('total_tokens', 0)} "
        f"(prompt {window.get('prompt_tokens', 0)}, "
        f"completion {window.get('completion_tokens', 0)})",
        f"- requests: {window.get('requests', 0)}; "
        f"agent calls: {window.get('agent_calls', 0)}",
    ]
    for provider in ("claude", "codex"):
        cell = percents.get(provider, {}).get(key)
        lines.append(f"- {provider}: {_percent_str(cell)}")
    return lines


def render_usage_md(view: dict[str, Any]) -> str:
    """Bounded human-readable markdown for ``view`` (never dumps raw rows).

    The final line is exactly ``DISCLAIMER``.
    """
    percents = view.get("percent", {}) if isinstance(view.get("percent"), dict) else {}
    lines: list[str] = ["# Usage status"]
    lines += _window_block(
        "Rolling 5h", view.get("rolling_5h", {}), percents, "rolling_5h_tokens")
    lines += _window_block(
        "Weekly", view.get("weekly", {}), percents, "weekly_tokens")

    provider_reported = view.get("provider_reported")
    if isinstance(provider_reported, dict):
        lines.append("## Provider-reported")
        lines.append(
            f"- {provider_reported.get('provider', '')}: "
            f"used {provider_reported.get('used', '')} / "
            f"limit {provider_reported.get('limit', '')}; "
            f"reset {provider_reported.get('reset', '')}")

    lines.append("## Top features (last 7d)")
    top = view.get("top_features") or []
    if top:
        for name, tokens in top:
            lines.append(f"- {name}: {tokens} tokens")
    else:
        lines.append("- (none)")

    paused = view.get("paused_run")
    if isinstance(paused, dict):
        lines.append("## Paused run")
        lines.append(
            f"- {paused.get('reason', '')} "
            f"({paused.get('provider', '')}); "
            f"observed {paused.get('observed_usage', '')}")
        lines.append(f"- suggested resume after: {paused.get('resume_after', '')}")

    lines.append("## Recent limit events")
    events = view.get("recent_limit_events") or []
    if events:
        for ev in events:
            lines.append(
                f"- {ev.get('ts', '')} {ev.get('provider', '')} {ev.get('kind', '')}")
    else:
        lines.append("- (none)")

    lines.append("")
    lines.append(DISCLAIMER)
    return "\n".join(lines)

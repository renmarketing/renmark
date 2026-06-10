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
    if not isinstance(parsed, dict):
        return {}

    # Non-raising validation: a malformed limits.json must not crash preflight.
    # validate_limits reports issues per provider entry; drop any provider whose
    # ceilings block is not a dict or carries a non-positive / non-int ceiling,
    # returning only the valid subset. Function-local import avoids any cycle.
    from renmark import schemas

    if not schemas.validate_limits(parsed):
        return parsed
    clean: dict[str, Any] = {}
    for provider, ceilings in parsed.items():
        if not isinstance(ceilings, dict):
            continue
        block: dict[str, Any] = {}
        for key, value in ceilings.items():
            # Mirror schemas._isinstance int handling (bool is not an int here).
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                continue
            block[key] = value
        if block:
            clean[provider] = block
    return clean


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


def _provider_percent(limits: dict[str, Any], provider: str, key: str, observed: int) -> float | str | None:
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
            events.append(
                {
                    "ts": str(r.get("ts", "")),
                    "provider": str(r.get("provider", "")),
                    "kind": str(kind),
                }
            )
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
    # Per-provider percentages MUST use that provider's own filtered window
    # totals — using the combined total overstates every provider on a mixed
    # Claude/Codex ledger.
    percent: dict[str, dict[str, Any]] = {}
    for provider in ("claude", "codex"):
        p_5h = state.usage_last_5h(repo, now=now, provider=provider)
        p_week = state.usage_last_week(repo, now=now, provider=provider)
        percent[provider] = {
            "rolling_5h_tokens": _provider_percent(limits, provider, "rolling_5h_tokens", p_5h.get("total_tokens", 0)),
            "weekly_tokens": _provider_percent(limits, provider, "weekly_tokens", p_week.get("total_tokens", 0)),
        }
    # A configured local limit is breached when any real (non-sentinel) percent
    # is at or over 100. This is the signal Tier-1 preflight reads to pause
    # before spend; it is False whenever no local limit is configured.
    limit_exceeded = any(
        isinstance(v, (int, float)) and v >= 100.0 for cells in percent.values() for v in cells.values()
    )
    view: dict[str, Any] = {
        "now": now,
        "rolling_5h": rolling_5h,
        "weekly": weekly,
        "limits": limits,
        "percent": percent,
        "limit_exceeded": limit_exceeded,
        "top_features": state.tokens_by_feature(repo, now=now, seconds=_ONE_WEEK, top=5),
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
    return (
        _provider_limit(limits, provider, "rolling_5h_tokens") is not None
        or _provider_limit(limits, provider, "rolling_5h_requests") is not None
    )


def _earliest_in_window_ts(repo: str | Path, *, base: dt.datetime, provider: str, seconds: int) -> dt.datetime | None:
    """Earliest parseable ts for ``provider`` within ``[base - seconds, base]``.

    Bounded + non-raising: scans the ledger, returns the oldest contributing
    row's aware timestamp, or None when there are no in-window rows.
    """
    lower = base - dt.timedelta(seconds=max(0, int(seconds)))
    earliest: dt.datetime | None = None
    for r in state.read_usage(repo):
        if r.get("provider") != provider:
            continue
        ts = _parse_iso(str(r.get("ts", "")))
        if ts is None or ts < lower or ts > base:
            continue
        if earliest is None or ts < earliest:
            earliest = ts
    return earliest


def _fallback_reference(repo: str | Path | None, provider: str) -> dt.datetime:
    """Best-effort aware reference when ``now`` is unparseable (never raises).

    Prefers the latest parseable ledger ts (any provider, biased to the matching
    one); otherwise the UNIX epoch. Always timezone-aware.
    """
    latest: dt.datetime | None = None
    if repo is not None:
        for r in state.read_usage(repo):
            ts = _parse_iso(str(r.get("ts", "")))
            if ts is None:
                continue
            if latest is None or ts > latest:
                latest = ts
    if latest is not None:
        return latest
    return dt.datetime(1970, 1, 1, tzinfo=dt.timezone.utc)


def _compute_resume_after(
    *,
    now: str,
    provider: str,
    provider_reset_at: str,
    limits: dict[str, Any],
    repo: str | Path | None = None,
    fallback_minutes: int = 60,
) -> str:
    """Resume_after rule — ALWAYS a non-empty, timezone-aware ISO timestamp.

    Order: provider reset (clamped to the future if stale) > earliest-in-window
    row + 5h when a rolling-5h limit is configured > now + 5h > now + fallback.
    When ``now`` is unparseable, a best-effort aware reference is synthesized so
    the result is never empty/naive.
    """
    base = _parse_iso(now)
    fallback = dt.timedelta(minutes=max(1, int(fallback_minutes)))
    reset = _parse_iso(provider_reset_at)

    if base is None:
        ref = _fallback_reference(repo, provider)
        if reset is not None and reset > ref:
            return provider_reset_at  # future reset; preserve verbatim input
        return (ref + fallback).isoformat()

    if reset is not None:
        # Future reset → preserve the verbatim input string (back-compat); a
        # stale reset is clamped to a future retry (aware ISO).
        if reset > base:
            return provider_reset_at
        return (base + fallback).isoformat()

    if _has_rolling_5h_window(limits, provider):
        if repo is not None:
            earliest = _earliest_in_window_ts(repo, base=base, provider=provider, seconds=_FIVE_HOURS)
            if earliest is not None:
                resume = earliest + dt.timedelta(seconds=_FIVE_HOURS)
                # Stay conservative — never hand back a past time.
                return (resume if resume > base else base + dt.timedelta(seconds=_FIVE_HOURS)).isoformat()
        return (base + dt.timedelta(seconds=_FIVE_HOURS)).isoformat()
    return (base + fallback).isoformat()


def classify_usage_pause(
    *,
    run_id: str,
    plan_path: str,
    last_task_index: int,
    now: str,
    provider: str = "",
    model: str = "",
    observed_usage: str = "",
    provider_reset_at: str = "",
    limits: dict[str, Any] | None = None,
    feature: str = "",
    loop_id: str = "",
    iteration: int = 0,
    max_iterations: int = 0,
    repo: str | Path | None = None,
) -> state.PauseState:
    """Build a usage-limit PauseState with resume_after by the fallback rule.

    No polling, no retry scheduling — purely computes resume_after and delegates
    to ``state.usage_limit_pause``. ``ts`` is the injected ``now``. Pass ``repo``
    so the rolling-5h fallback can anchor on the oldest in-window row.
    """
    resolved_limits = limits if isinstance(limits, dict) else {}
    resume_after = _compute_resume_after(
        now=now,
        provider=provider,
        provider_reset_at=provider_reset_at,
        limits=resolved_limits,
        repo=repo,
        fallback_minutes=60,
    )
    return state.usage_limit_pause(
        run_id=run_id,
        plan_path=plan_path,
        last_task_index=last_task_index,
        ts=now,
        provider=provider,
        model=model,
        observed_usage=observed_usage,
        provider_reset_at=provider_reset_at,
        resume_after=resume_after,
        fallback_retry_minutes=60,
        feature=feature,
        loop_id=loop_id,
        iteration=iteration,
        max_iterations=max_iterations,
    )


def _percent_str(value: float | str | None) -> str:
    """Human string for a percent cell (float, sentinel, or None)."""
    if value is None:
        return "no configured local limit is set"
    if isinstance(value, str):
        return "no configured local limit is set"
    return f"{value}%"


def _window_block(title: str, window: dict[str, Any], percents: dict[str, dict[str, Any]], key: str) -> list[str]:
    """Markdown lines for one rolling/weekly window with per-provider percent."""
    lines = [
        f"## {title}",
        f"- total tokens: {window.get('total_tokens', 0)} "
        f"(prompt {window.get('prompt_tokens', 0)}, "
        f"completion {window.get('completion_tokens', 0)})",
        f"- requests: {window.get('requests', 0)}; agent calls: {window.get('agent_calls', 0)}",
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
    lines += _window_block("Rolling 5h", view.get("rolling_5h", {}), percents, "rolling_5h_tokens")
    lines += _window_block("Weekly", view.get("weekly", {}), percents, "weekly_tokens")

    provider_reported = view.get("provider_reported")
    if isinstance(provider_reported, dict):
        lines.append("## Provider-reported")
        lines.append(
            f"- {provider_reported.get('provider', '')}: "
            f"used {provider_reported.get('used', '')} / "
            f"limit {provider_reported.get('limit', '')}; "
            f"reset {provider_reported.get('reset', '')}"
        )

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
            f"- {paused.get('reason', '')} ({paused.get('provider', '')}); observed {paused.get('observed_usage', '')}"
        )
        lines.append(f"- suggested resume after: {paused.get('resume_after', '')}")

    lines.append("## Recent limit events")
    events = view.get("recent_limit_events") or []
    if events:
        for ev in events:
            lines.append(f"- {ev.get('ts', '')} {ev.get('provider', '')} {ev.get('kind', '')}")
    else:
        lines.append("- (none)")

    lines.append("")
    lines.append(DISCLAIMER)
    return "\n".join(lines)

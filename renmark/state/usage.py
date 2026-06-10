"""Token-usage ledger (.renmark/state/usage.jsonl).

Codex tasks are ledgered by renmark-execute; Claude-model Agent calls via
`log_agent_call`. /renmark:roadmap reads this file for spend reporting.
"""

from __future__ import annotations

import datetime as dt
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from ._core import USAGE_LEDGER, new_run_id, now_iso, state_dir


@dataclass
class UsageRecord:
    ts: str
    run_id: str
    task_id: int
    model: str
    prompt_tokens: int
    completion_tokens: int
    # Retry/attempt counter (default 0). Part of the dedup key in append_usage:
    # codex retries legitimately re-ledger the same (run_id, task_id) — a higher
    # attempt is a genuine new row, but a replayed SAME attempt is idempotent.
    attempt: int = 0
    # Optional, keyword-defaulted enrichment fields (REQ-15). All default so
    # construction from old rows / call sites stays back-compatible, and old
    # usage.jsonl rows (without these keys) still parse via read_usage().
    provider: str = ""
    cached_tokens: int = 0
    context_window_tokens: int = 0
    agent_calls: int = 0
    requests: int = 0
    feature: str = ""
    # source: local-observed | configured-local-limit | provider-reported
    #         | estimated | unknown
    source: str = "local-observed"
    # kind: "" | "rate_limit" | "quota"
    kind: str = ""

    def as_jsonl(self) -> str:
        return json.dumps(asdict(self), separators=(",", ":"))


def append_usage(repo_root: str | Path, rec: UsageRecord) -> None:
    """Append a usage row, idempotent on (run_id, task_id, attempt, model).

    A replayed ledgering of the SAME attempt (e.g. a crash-resume that
    re-ledgers without re-dispatching) is skipped so spend isn't double-counted.
    Genuine retries increment ``attempt`` and DO append a new row. Dedup only
    fires when ``run_id`` is non-empty — adhoc rows with no run_id always append
    (they carry no stable identity to dedup against).
    """
    path = state_dir(repo_root) / USAGE_LEDGER
    # Dedup fires ONLY for explicit retries (attempt > 0): a task may make many
    # legitimate calls within attempt 0 (one row each — roadmap counts them to
    # detect retries), so attempt-0 rows always append. A replayed retry
    # ledgering (same attempt > 0) is idempotent.
    if rec.run_id and rec.attempt > 0:
        for existing in read_usage(repo_root):
            if (
                existing.get("run_id") == rec.run_id
                and existing.get("task_id") == rec.task_id
                and int(existing.get("attempt", 0) or 0) == rec.attempt
                and existing.get("model") == rec.model
            ):
                return  # already ledgered this exact attempt — idempotent
    with path.open("a", encoding="utf-8") as fh:
        fh.write(rec.as_jsonl() + "\n")


def log_agent_call(
    repo_root: str | Path,
    *,
    task_id: int,
    model: str,
    tokens_in: int = 0,
    tokens_out: int = 0,
    run_id: str | None = None,
    attempt: int = 0,
) -> UsageRecord:
    """Record one Agent-tool call (haiku/sonnet/opus) in usage.jsonl.

    The orchestrate skill calls this after every Agent return so
    /renmark:roadmap reports honest spend. Codex tasks are ledgered by
    renmark-execute directly; this helper is for the Claude-model path.

    If `tokens_in` is 0 but `tokens_out` is set, the caller likely only has
    SubagentOutput.token_count (total) — pass it as tokens_out and treat
    tokens_in as the Agent-overhead constant in render code.
    """
    rec = UsageRecord(
        ts=now_iso(),
        run_id=run_id or new_run_id(),
        task_id=int(task_id),
        model=model,
        prompt_tokens=int(tokens_in),
        completion_tokens=int(tokens_out),
        attempt=int(attempt),
    )
    append_usage(repo_root, rec)
    return rec


def read_usage(repo_root: str | Path) -> list[dict[str, Any]]:
    path = state_dir(repo_root) / USAGE_LEDGER
    if not path.exists():
        return []
    # Tolerate invalid UTF-8 bytes in the ledger: decode with ``errors="replace"``
    # so a corrupt byte mangles only its own line (which then fails JSON parse and
    # is skipped) rather than raising a UnicodeDecodeError for the whole file.
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    out: list[dict[str, Any]] = []
    for raw in text.splitlines():
        raw = raw.strip()
        if not raw:
            continue
        try:
            parsed = json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            continue
        if isinstance(parsed, dict):
            out.append(parsed)
    return out


def usage_today(repo_root: str | Path) -> int:
    today = dt.datetime.now(dt.timezone.utc).date().isoformat()
    total = 0
    for r in read_usage(repo_root):
        ts = r.get("ts", "")
        if isinstance(ts, str) and ts.startswith(today):
            total += _clamp_tokens(r.get("prompt_tokens", 0)) + _clamp_tokens(r.get("completion_tokens", 0))
    return total


def usage_this_month(repo_root: str | Path) -> int:
    prefix = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m")
    total = 0
    for r in read_usage(repo_root):
        ts = r.get("ts", "")
        if isinstance(ts, str) and ts.startswith(prefix):
            total += _clamp_tokens(r.get("prompt_tokens", 0)) + _clamp_tokens(r.get("completion_tokens", 0))
    return total


def usage_by_run_id(repo: str | Path, run_id: str) -> int:
    """Total tokens (prompt + completion) ledgered under one run_id.

    The spend-measurement primitive behind the loop budget gate. Pure and
    defensive: a missing, empty, or corrupt ledger — or any unreadable line —
    yields 0 rather than raising. Bad lines are skipped (`read_usage` already
    drops JSON-undecodable rows); malformed token fields are coerced to 0.
    """
    total = 0
    try:
        records = read_usage(repo)
    except OSError:
        return 0
    for r in records:
        if not isinstance(r, dict) or r.get("run_id") != run_id:
            continue
        # Clamp each token field to >= 0 so a negative / garbage value counts as
        # 0 rather than under-counting real spend (which would let the loop run
        # past its approved budget). A non-coercible field is skipped (→ 0).
        total += _clamp_tokens(r.get("prompt_tokens", 0))
        total += _clamp_tokens(r.get("completion_tokens", 0))
    return total


def _clamp_tokens(value: Any) -> int:
    """Coerce a ledger token field to ``max(0, int(value))``; bad input → 0."""
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0


def _parse_ts(ts: str) -> float | None:
    """Parse an ISO-8601 timestamp to epoch seconds; None on bad/missing input.

    Tolerant: a trailing 'Z' (UTC) is normalised to '+00:00' so the stdlib
    ``datetime.fromisoformat`` accepts it. Naive timestamps (no offset) are
    treated as UTC so comparisons against an injected UTC ``now`` are stable.
    """
    if not ts or not isinstance(ts, str):
        return None
    candidate = ts.strip()
    if candidate.endswith("Z"):
        candidate = candidate[:-1] + "+00:00"
    try:
        parsed = dt.datetime.fromisoformat(candidate)
    except (ValueError, TypeError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.timestamp()


def usage_in_window(repo: str | Path, *, now: str, seconds: int, provider: str | None = None) -> dict[str, int]:
    """Aggregate ledger rows whose ts falls within ``[now - seconds, now]``.

    ``now`` is injected (ISO-8601) — this reader never calls datetime.now().
    Non-raising: a missing/corrupt ledger or an unparseable ``now`` yields all
    zeros. ``total_tokens`` is prompt + completion summed; ``requests`` and
    ``agent_calls`` are summed from those row fields (0 when absent).

    When ``provider`` is given, only rows whose ``provider`` field equals it are
    summed; ``provider=None`` (default) sums every row (back-compatible).
    """
    zero = {
        "total_tokens": 0,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "requests": 0,
        "agent_calls": 0,
        "rows": 0,
    }
    now_epoch = _parse_ts(now)
    if now_epoch is None:
        return zero
    lower = now_epoch - max(0, int(seconds))
    prompt = completion = requests = agent_calls = rows = 0
    for r in read_usage(repo):
        if provider is not None and r.get("provider") != provider:
            continue
        ts_epoch = _parse_ts(r.get("ts", ""))
        if ts_epoch is None or ts_epoch < lower or ts_epoch > now_epoch:
            continue
        prompt += _clamp_tokens(r.get("prompt_tokens", 0))
        completion += _clamp_tokens(r.get("completion_tokens", 0))
        requests += _clamp_tokens(r.get("requests", 0))
        agent_calls += _clamp_tokens(r.get("agent_calls", 0))
        rows += 1
    return {
        "total_tokens": prompt + completion,
        "prompt_tokens": prompt,
        "completion_tokens": completion,
        "requests": requests,
        "agent_calls": agent_calls,
        "rows": rows,
    }


def usage_last_5h(repo: str | Path, *, now: str, provider: str | None = None) -> dict[str, int]:
    """Usage aggregated over the trailing 5-hour window ending at ``now``.

    Pass ``provider`` to restrict the sum to one provider's rows.
    """
    return usage_in_window(repo, now=now, seconds=5 * 3600, provider=provider)


def usage_last_week(repo: str | Path, *, now: str, provider: str | None = None) -> dict[str, int]:
    """Usage aggregated over the trailing 7-day window ending at ``now``.

    Pass ``provider`` to restrict the sum to one provider's rows.
    """
    return usage_in_window(repo, now=now, seconds=7 * 24 * 3600, provider=provider)


def tokens_by_feature(repo: str | Path, *, now: str, seconds: int, top: int = 5) -> list[tuple[str, int]]:
    """Top-N (feature, tokens) within ``[now - seconds, now]``, desc by tokens.

    Tokens are prompt + completion summed. Rows with an empty/missing feature
    are skipped. Non-raising: bad ledger or unparseable ``now`` → empty list.
    """
    now_epoch = _parse_ts(now)
    if now_epoch is None:
        return []
    lower = now_epoch - max(0, int(seconds))
    totals: dict[str, int] = {}
    for r in read_usage(repo):
        feature = r.get("feature", "")
        if not isinstance(feature, str) or not feature:
            continue
        ts_epoch = _parse_ts(r.get("ts", ""))
        if ts_epoch is None or ts_epoch < lower or ts_epoch > now_epoch:
            continue
        tokens = _clamp_tokens(r.get("prompt_tokens", 0)) + _clamp_tokens(r.get("completion_tokens", 0))
        totals[feature] = totals.get(feature, 0) + tokens
    ranked = sorted(totals.items(), key=lambda kv: (-kv[1], kv[0]))
    return ranked[: max(0, int(top))]

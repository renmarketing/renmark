"""Analytics event ledgers + Python aggregation (REQ-15).

Append-only JSONL ledgers under ``.renmark/analytics/`` capture the events
renmark emits across its lifecycle — task runs, feature runs, loop runs, and
free-form events. A small Python aggregation rolls these ledgers (plus the
EXISTING token ledger via :func:`renmark.state.read_usage`) into a bounded
``summary.json`` and a ``/renmark:analytics`` health report.

Design contract (mirrors ``renmark/lifecycle.py`` + ``renmark/loop.py``):

- **Append-only + atomic summary.** Each record is one compact JSON line
  appended via ``open("a", ...)`` (mkdir parents first). ``summary.json`` is
  written atomically (``.tmp`` + ``os.replace``) so a crash never leaves a
  half-written summary.
- **No ``datetime.now()``.** Every timestamp (``ts``) and the aggregation
  anchor (``now``) is injected by the caller — this module is deterministic.
- **Reads, never duplicates, the token ledger.** Token usage is read via
  :func:`renmark.state.read_usage`; this module does NOT write usage rows.
- **Non-raising throughout.** Every IO / parse step is wrapped; a missing or
  corrupt ledger degrades to empty/zero, never an exception. An empty project
  aggregates cleanly.
- **Bounded output.** ``aggregate`` / ``build_health_report`` return counts and
  short lists only — never raw rows (G3 summary boundary).
"""

from __future__ import annotations

import contextlib
import json
import os
import tempfile
from collections import Counter
from pathlib import Path

from .state import read_usage

# ── Tunables ────────────────────────────────────────────────────────────────

#: Default provenance for records emitted by a local observer (the orchestrator
#: counting its own dispatches), distinguishing them from provider-reported data.
DEFAULT_SOURCE: str = "local-observed"

#: How many "common failure reasons" to surface (top-N by count).
TOP_FAILURE_REASONS: int = 5

#: Cap on the length of name lists in the bounded health report.
HEALTH_LIST_CAP: int = 10

#: Cap on the number of keys retained in each per-key breakdown map returned by
#: :func:`aggregate` (top-N by count) so the summary stays bounded.
MAP_CAP: int = 10

#: Status strings (case-insensitive) that mean a task/feature/loop succeeded.
SUCCESS_STATUSES: frozenset[str] = frozenset({"completed", "complete", "pass", "passed", "shipped"})

#: Status strings (case-insensitive) that mean a task/feature/loop was blocked.
BLOCKED_STATUSES: frozenset[str] = frozenset({"blocked", "failed", "fail"})

#: Registered ``record_event`` kinds. Observational only — record_event still
#: persists an UNregistered kind (events are never load-bearing), but stamps
#: ``unregistered_kind: True`` on it so drift is visible. Mirrored by
#: :func:`renmark.schemas.validate_event`.
EVENT_KINDS: frozenset[str] = frozenset(
    {
        "loop_iteration",
        "pause",
        "resume",
        "rate_limit",
        "quota",
        "release",
        "backlog_completed",
        "backlog_blocked",
        "backlog_rejected",
    }
)

#: Ledger filenames under ``.renmark/analytics/``.
EVENTS_LEDGER: str = "events.jsonl"
TASK_RUNS_LEDGER: str = "task-runs.jsonl"
FEATURE_RUNS_LEDGER: str = "feature-runs.jsonl"
LOOP_RUNS_LEDGER: str = "loop-runs.jsonl"
SUMMARY_JSON: str = "summary.json"


# ── Paths ─────────────────────────────────────────────────────────────────────


def analytics_dir(repo: str | Path) -> Path:
    """Return ``.renmark/analytics/`` for ``repo`` (callers mkdir on write)."""
    return Path(repo) / ".renmark" / "analytics"


# ── Shared JSONL reader ─────────────────────────────────────────────────────


def read_jsonl(path: str | Path) -> list[dict[str, object]]:
    """Read a JSONL ledger into a list of dicts. Never raises.

    Skips blank and corrupt lines (and any line that isn't a JSON object);
    returns ``[]`` for a missing/unreadable file. Invalid UTF-8 bytes are
    decoded with ``errors="replace"`` so one bad byte only mangles its own line.
    """
    p = Path(path)
    if not p.exists():
        return []
    try:
        text = p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    out: list[dict[str, object]] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        try:
            parsed = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            continue
        if isinstance(parsed, dict):
            out.append(parsed)
    return out


# ── Append helpers ──────────────────────────────────────────────────────────


def _append(repo: str | Path, filename: str, record: dict[str, object]) -> None:
    """Append one compact JSON line to ``.renmark/analytics/<filename>``.

    Mkdir parents first; stamps a default ``source`` if absent. Never raises —
    an IO failure is swallowed (analytics is observational, never load-bearing).
    """
    record.setdefault("source", DEFAULT_SOURCE)
    path = analytics_dir(repo) / filename
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, separators=(",", ":")) + "\n")
    except (OSError, TypeError, ValueError):
        return


def record_event(repo: str | Path, *, ts: str, kind: str, **fields: object) -> None:
    """Append a free-form event (``events.jsonl``).

    ``kind`` is the marker the aggregation buckets on (e.g. ``"pause"``,
    ``"resume"``, ``"rate_limit"``, ``"quota"``, ``"release"``,
    ``"backlog_completed"``). Extra ``fields`` are stored verbatim.

    Unregistered kinds (not in :data:`EVENT_KINDS`) are STILL recorded — events
    are observational, never load-bearing — but stamped ``unregistered_kind:
    True`` so registry drift surfaces in the ledger.
    """
    record: dict[str, object] = {"ts": ts, "kind": kind}
    record.update(fields)
    if kind not in EVENT_KINDS:
        record["unregistered_kind"] = True
    _append(repo, EVENTS_LEDGER, record)


def record_task_run(
    repo: str | Path,
    *,
    ts: str,
    task_id: int,
    title: str = "",
    executor: str = "",
    model: str = "",
    provider: str = "",
    status: str = "",
    verifier_result: str = "",
    retry_count: int = 0,
    failure_reason: str = "",
    duration_s: float = 0.0,
    tokens_in: int = 0,
    tokens_out: int = 0,
    total_tokens: int = 0,
    est_cost_usd: float = 0.0,
    sha: str = "",
    measured: bool = False,
) -> None:
    """Append one orchestrate task-run record (``task-runs.jsonl``)."""
    _append(
        repo,
        TASK_RUNS_LEDGER,
        {
            "ts": ts,
            "task_id": task_id,
            "title": title,
            "executor": executor,
            "model": model,
            "provider": provider,
            "status": status,
            "verifier_result": verifier_result,
            "retry_count": retry_count,
            "failure_reason": failure_reason,
            "duration_s": duration_s,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "total_tokens": total_tokens,
            "est_cost_usd": est_cost_usd,
            "sha": sha,
            "measured": measured,
        },
    )


def record_feature_run(
    repo: str | Path,
    *,
    ts: str,
    feature: str,
    branch: str = "",
    status: str = "",
    sha: str = "",
    files_changed: int = 0,
    verification: str = "",
    token_cost: dict[str, int] | None = None,
    branch_disposition: str = "",
) -> None:
    """Append one feature-run record (``feature-runs.jsonl``).

    Idempotent on (feature, sha, status, branch_disposition): re-running
    /renmark:finish for the same closed feature must not double-count it in
    summary.json / the health report.
    """
    for row in read_jsonl(analytics_dir(repo) / FEATURE_RUNS_LEDGER):
        if (
            row.get("feature") == feature
            and row.get("sha") == sha
            and row.get("status") == status
            and row.get("branch_disposition") == branch_disposition
        ):
            return
    _append(
        repo,
        FEATURE_RUNS_LEDGER,
        {
            "ts": ts,
            "feature": feature,
            "branch": branch,
            "status": status,
            "sha": sha,
            "files_changed": files_changed,
            "verification": verification,
            "token_cost": token_cost or {},
            "branch_disposition": branch_disposition,
        },
    )


#: ``branch_disposition`` values treated as non-terminal — a closing pass may
#: still transform them. ``""``/``"open"`` are pre-close; ``"merged"`` is the
#: legacy non-canonical value finish step 2.5 writes before the disposition is
#: finalized.
_NONTERMINAL_DISPOSITIONS: frozenset[str] = frozenset({"", "open", "merged"})


def close_feature_disposition(
    repo: str | Path,
    *,
    feature: str,
    branch: str = "",
    sha: str = "",
    disposition: str = "merged-deleted",
) -> bool:
    """Transform a feature run's ``branch_disposition`` to a terminal value.

    Matching is **feature-primary**: the feature name is the stable identity, so
    rows are first selected by ``feature`` plus a still-non-terminal
    ``branch_disposition`` (``""``, ``"open"``, or the legacy ``"merged"``).

    ``branch`` is the **stable narrowing key**: the feature slug is reusable, so
    matching by feature alone can close the wrong (or multiple) non-terminal
    rows when a slug is reused across runs. ``branch`` is stable across a merge
    (unlike ``sha``, which finish's ``[m]`` merge path rewrites to the
    merge-commit sha) and is recorded by :func:`record_feature_run`. When
    ``branch`` is given and matches one or more open feature rows, only that
    run's rows are closed; when it matches **none**, the fallback is
    **legacy-only** — it closes solely the candidates that carry no recorded
    ``branch`` (pre-branch-field data), never rows carrying a *different*
    branch (those belong to other runs, so closing them would over-close).

    ``sha`` is a further *optional narrowing* (applied after any branch
    narrowing) with the same safety fallback: when ``sha`` is given and matches
    one or more of the (branch-narrowed) open rows, only the sha-matched subset
    is closed; but when ``sha`` matches **no** such row (e.g. finish's ``[m]``
    merge path records the merge-commit sha, not the feature-tip sha step 2.5
    stored), it falls back to closing the current candidate set anyway. This
    guarantees a stale/wrong sha can never cause a silent no-op. When both
    ``branch`` and ``sha`` are empty, all open feature rows are closed. The
    whole ledger is rewritten (never appended) atomically (``tempfile.mkstemp``
    + ``os.replace``).

    Returns ``True`` if at least one row changed (ledger rewritten), ``False``
    otherwise — no matching non-terminal row means a no-op (no append, no
    rewrite), so this is idempotent and safe to re-run. Never raises; analytics
    is observational, never load-bearing, so any IO/parse failure returns
    ``False``.
    """
    path = analytics_dir(repo) / FEATURE_RUNS_LEDGER
    try:
        rows = read_jsonl(path)
        feature_candidates = [
            row
            for row in rows
            if row.get("feature") == feature
            and str(row.get("branch_disposition", "")) in _NONTERMINAL_DISPOSITIONS
        ]
        if branch:
            branch_narrowed = [row for row in feature_candidates if row.get("branch") == branch]
            if branch_narrowed:
                feature_candidates = branch_narrowed
            else:
                # branch given but matched no candidate: fall back ONLY to legacy
                # rows with no recorded branch (pre-branch-field data). Never close
                # rows that carry a DIFFERENT branch — those are other runs (no
                # over-close).
                feature_candidates = [
                    row for row in feature_candidates if not str(row.get("branch", ""))
                ]
        if sha:
            narrowed = [row for row in feature_candidates if row.get("sha") == sha]
            to_transform = narrowed if narrowed else feature_candidates
        else:
            to_transform = feature_candidates
        changed = False
        for row in to_transform:
            row["branch_disposition"] = disposition
            changed = True
        if not changed:
            return False
        tmp_path: str | None = None
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            payload = "".join(json.dumps(row, separators=(",", ":")) + "\n" for row in rows)
            fd, tmp_path = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(payload)
            os.replace(tmp_path, path)
            tmp_path = None
        finally:
            if tmp_path is not None:
                with contextlib.suppress(OSError):
                    os.unlink(tmp_path)
        return True
    except (OSError, TypeError, ValueError):
        return False


def record_loop_run(
    repo: str | Path,
    *,
    ts: str,
    loop_id: str,
    goal: str = "",
    backlog_item_id: str = "",
    max_iterations: int = 0,
    iterations_used: int = 0,
    stop_reason: str = "",
    goal_reached: bool = False,
    total_tokens: int = 0,
    est_cost_usd: float = 0.0,
    branch_disposition: str = "",
) -> None:
    """Append one loop-run record (``loop-runs.jsonl``)."""
    _append(
        repo,
        LOOP_RUNS_LEDGER,
        {
            "ts": ts,
            "loop_id": loop_id,
            "goal": goal,
            "backlog_item_id": backlog_item_id,
            "max_iterations": max_iterations,
            "iterations_used": iterations_used,
            "stop_reason": stop_reason,
            "goal_reached": goal_reached,
            "total_tokens": total_tokens,
            "est_cost_usd": est_cost_usd,
            "branch_disposition": branch_disposition,
        },
    )


# ── Coercion helpers ──────────────────────────────────────────────────────────


def _as_str(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def _as_int(value: object) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        try:
            return int(value)
        except (TypeError, ValueError, OverflowError):
            return 0
    if isinstance(value, str):
        try:
            return int(float(value.strip().replace("_", "").replace(",", "")))
        except (TypeError, ValueError, OverflowError):
            return 0
    return 0


def _as_float(value: object) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except (TypeError, ValueError):
            return 0.0
    return 0.0


def _as_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in ("true", "1", "yes", "y")
    return bool(value)


def _is_success_status(status: str) -> bool:
    """True if ``status`` (any case) names a successful/shipped run."""
    return status.strip().lower() in SUCCESS_STATUSES


def _is_blocked_status(status: str) -> bool:
    """True if ``status`` (any case) names a blocked/failed run."""
    return status.strip().lower() in BLOCKED_STATUSES


def _cap_map(counter: dict[str, int]) -> dict[str, int]:
    """Return the top ``MAP_CAP`` keys of ``counter`` by count (ties: key asc).

    Caps the per-key breakdown only; scalar totals are computed separately and
    stay accurate. Keeps the returned summary bounded (G3 boundary).
    """
    items = sorted(counter.items(), key=lambda kv: (-kv[1], kv[0]))
    return dict(items[:MAP_CAP])


# ── Aggregation ────────────────────────────────────────────────────────────────


def _agg_features(rows: list[dict[str, object]]) -> dict[str, object]:
    """Roll up feature-runs: status counts + branch dispositions + shipped/blocked names."""
    status_c: Counter[str] = Counter()
    disposition_c: Counter[str] = Counter()
    shipped: list[str] = []
    blocked: list[str] = []
    completed_count = 0
    blocked_count = 0
    for r in rows:
        status = _as_str(r.get("status")).lower()
        status_c[status or "unknown"] += 1
        disp = _as_str(r.get("branch_disposition"))
        if disp:
            disposition_c[disp] += 1
        name = _as_str(r.get("feature"))
        if _is_success_status(status):
            completed_count += 1
            if name:
                shipped.append(name)
        elif _is_blocked_status(status):
            blocked_count += 1
            if name:
                blocked.append(name)
    return {
        "started": len(rows),
        "completed": completed_count,
        "blocked": blocked_count,
        "by_status": dict(status_c),
        "branch_dispositions": _cap_map(dict(disposition_c)),
        "shipped_names": shipped[:HEALTH_LIST_CAP],
        "blocked_names": blocked[:HEALTH_LIST_CAP],
    }


def _agg_tasks(rows: list[dict[str, object]]) -> dict[str, object]:
    """Roll up task-runs: success/failure/skip + verification + failure reasons + by-executor tokens."""
    status_c: Counter[str] = Counter()
    verifier_c: Counter[str] = Counter()
    failure_c: Counter[str] = Counter()
    tokens_by_executor: Counter[str] = Counter()
    tokens_by_model: Counter[str] = Counter()
    tokens_by_provider: Counter[str] = Counter()
    passed = failed = skipped = 0
    measured_tokens_total = 0
    unmeasured_task_count = 0
    for r in rows:
        raw_status = _as_str(r.get("status"))
        status = raw_status.upper()
        status_c[status or "UNKNOWN"] += 1
        if _is_success_status(raw_status):
            passed += 1
        elif _is_blocked_status(raw_status):
            failed += 1
        elif status == "SKIP" or raw_status.strip().lower() == "skipped":
            skipped += 1
        verdict = _as_str(r.get("verifier_result")).lower()
        if verdict:
            verifier_c[verdict] += 1
        reason = _as_str(r.get("failure_reason"))
        if reason:
            failure_c[reason] += 1
        tokens = _as_int(r.get("total_tokens")) or (_as_int(r.get("tokens_in")) + _as_int(r.get("tokens_out")))
        if tokens:
            tokens_by_executor[_as_str(r.get("executor")) or "unknown"] += tokens
            tokens_by_model[_as_str(r.get("model")) or "unknown"] += tokens
            tokens_by_provider[_as_str(r.get("provider")) or "unknown"] += tokens
        if r.get("measured"):
            measured_tokens_total += tokens
        else:
            unmeasured_task_count += 1
    return {
        "total": len(rows),
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "verification_pass": verifier_c.get("pass", 0),
        "verification_fail": verifier_c.get("fail", 0),
        "common_failure_reasons": failure_c.most_common(TOP_FAILURE_REASONS),
        "tokens_by_executor": _cap_map(dict(tokens_by_executor)),
        "tokens_by_model": _cap_map(dict(tokens_by_model)),
        "tokens_by_provider": _cap_map(dict(tokens_by_provider)),
        "measured_tokens_total": measured_tokens_total,
        "unmeasured_task_count": unmeasured_task_count,
    }


def _agg_loops(rows: list[dict[str, object]]) -> dict[str, object]:
    """Roll up loop-runs: success/failure + avg iterations + stop-reason + dispositions."""
    success = 0
    iterations_total = 0
    stop_c: Counter[str] = Counter()
    disposition_c: Counter[str] = Counter()
    for r in rows:
        if _as_bool(r.get("goal_reached")):
            success += 1
        iterations_total += _as_int(r.get("iterations_used"))
        stop = _as_str(r.get("stop_reason"))
        if stop:
            stop_c[stop] += 1
        disp = _as_str(r.get("branch_disposition"))
        if disp:
            disposition_c[disp] += 1
    total = len(rows)
    return {
        "total": total,
        "success": success,
        "failure": total - success,
        "avg_iterations": round(iterations_total / total, 2) if total else 0.0,
        "by_stop_reason": _cap_map(dict(stop_c)),
        "branch_dispositions": _cap_map(dict(disposition_c)),
    }


def _agg_events(rows: list[dict[str, object]]) -> dict[str, object]:
    """Roll up events.jsonl by ``kind`` — pause/resume/rate-limit/quota/backlog/release counts."""
    kind_c: Counter[str] = Counter()
    for r in rows:
        kind = _as_str(r.get("kind"))
        if kind:
            kind_c[kind] += 1
    return {
        "by_kind": _cap_map(dict(kind_c)),
        "backlog_completed": kind_c.get("backlog_completed", 0),
        "backlog_blocked": kind_c.get("backlog_blocked", 0),
        "backlog_rejected": kind_c.get("backlog_rejected", 0),
        "releases_created": kind_c.get("release", 0) + kind_c.get("release_created", 0),
        "pause_events": kind_c.get("pause", 0),
        "resume_events": kind_c.get("resume", 0),
        "rate_limit_events": kind_c.get("rate_limit", 0),
        "quota_events": kind_c.get("quota", 0),
    }


def _agg_ledger_guardrails(repo: str | Path) -> dict[str, object]:
    """Roll up ``ledger.py``'s escalation/inspection events into bounded counts.

    Reads :func:`renmark.ledger.read_ledger_events` for
    ``KIND_ESCALATION`` and ``KIND_INSPECTION_REPORT`` and returns counts
    only (no raw rows — G3 summary boundary). This is a READ path into
    ``ledger.py``'s dispatch-governance data; it does not write to the
    ledger and does not duplicate any ``analytics.py`` ledger. Never
    raises — any failure (missing ledger file, import problem, malformed
    row) degrades to all-zero counts, matching every other ``_agg_*``
    helper in this module.
    """
    escalations_total = 0
    escalations_blocking = 0
    inspection_total = 0
    verdict_c: Counter[str] = Counter()
    try:
        from renmark import ledger

        escalation_rows = ledger.read_ledger_events(repo, kind=ledger.KIND_ESCALATION)
        inspection_rows = ledger.read_ledger_events(repo, kind=ledger.KIND_INSPECTION_REPORT)
        escalations_total = len(escalation_rows)
        escalations_blocking = sum(1 for r in escalation_rows if _as_bool(r.get("blocking")))
        inspection_total = len(inspection_rows)
        for r in inspection_rows:
            verdict = _as_str(r.get("verdict")).lower()
            if verdict in ledger.VERDICTS:
                verdict_c[verdict] += 1
    except Exception:
        return {
            "escalations_total": 0,
            "escalations_blocking": 0,
            "inspection_verdicts": {},
            "inspection_total": 0,
        }
    return {
        "escalations_total": escalations_total,
        "escalations_blocking": escalations_blocking,
        "inspection_verdicts": dict(verdict_c),
        "inspection_total": inspection_total,
    }


def _agg_usage(repo: str | Path) -> dict[str, object]:
    """Roll up the EXISTING token ledger (read_usage) — never duplicated here."""
    by_provider: Counter[str] = Counter()
    by_model: Counter[str] = Counter()
    by_feature: Counter[str] = Counter()
    requests = agent_calls = total_tokens = 0
    rate_limit = quota = 0
    try:
        rows = read_usage(repo)
    except Exception:
        rows = []
    for r in rows:
        tokens = _as_int(r.get("prompt_tokens")) + _as_int(r.get("completion_tokens"))
        total_tokens += tokens
        by_provider[_as_str(r.get("provider")) or "unknown"] += tokens
        by_model[_as_str(r.get("model")) or "unknown"] += tokens
        feature = _as_str(r.get("feature"))
        if feature:
            by_feature[feature] += tokens
        requests += _as_int(r.get("requests"))
        agent_calls += _as_int(r.get("agent_calls"))
        kind = _as_str(r.get("kind"))
        if kind == "rate_limit":
            rate_limit += 1
        elif kind == "quota":
            quota += 1
    return {
        "total_tokens": total_tokens,
        "by_provider": _cap_map(dict(by_provider)),
        "by_model": _cap_map(dict(by_model)),
        "by_feature": dict(sorted(by_feature.items(), key=lambda kv: (-kv[1], kv[0]))[:HEALTH_LIST_CAP]),
        "requests": requests,
        "agent_calls": agent_calls,
        "rate_limit_events": rate_limit,
        "quota_events": quota,
    }


def _write_summary_atomic(repo: str | Path, summary: dict[str, object]) -> None:
    """Write ``summary.json`` atomically. Never raises.

    Serializes to a UNIQUE per-call temp file (``tempfile.mkstemp``) in the same
    directory, then ``os.replace``s it onto ``summary.json``. The unique temp
    name means concurrent :func:`aggregate` calls never share a temp path, so
    one writer can't truncate another's in-flight file.
    """
    path = analytics_dir(repo) / SUMMARY_JSON
    tmp_path: str | None = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(summary, indent=2, sort_keys=False)
        fd, tmp_path = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(payload)
        os.replace(tmp_path, path)
        tmp_path = None
    except (OSError, TypeError, ValueError):
        if tmp_path is not None:
            with contextlib.suppress(OSError):
                os.unlink(tmp_path)


def aggregate(repo: str | Path, *, now: str) -> dict[str, object]:
    """Roll up every ledger (+ the token ledger) into a bounded ``summary.json``.

    Reads the four analytics ledgers and the EXISTING token ledger
    (:func:`read_usage`), computes counts + small ranked lists only, writes the
    result atomically to ``.renmark/analytics/summary.json``, and returns it.
    Never raises — a missing/empty/corrupt project aggregates to zeros.
    """
    base = analytics_dir(repo)
    features = _agg_features(read_jsonl(base / FEATURE_RUNS_LEDGER))
    tasks = _agg_tasks(read_jsonl(base / TASK_RUNS_LEDGER))
    loops = _agg_loops(read_jsonl(base / LOOP_RUNS_LEDGER))
    events = _agg_events(read_jsonl(base / EVENTS_LEDGER))
    usage = _agg_usage(repo)
    guardrails = _agg_ledger_guardrails(repo)
    summary: dict[str, object] = {
        "generated_at": now,
        "source": DEFAULT_SOURCE,
        "features": features,
        "tasks": tasks,
        "loops": loops,
        "guardrails": guardrails,
        "backlog": {
            "completed": events["backlog_completed"],
            "blocked": events["backlog_blocked"],
            "rejected": events["backlog_rejected"],
        },
        "verification": {
            "pass": tasks["verification_pass"],
            "fail": tasks["verification_fail"],
        },
        "releases_created": events["releases_created"],
        "branch_dispositions": features["branch_dispositions"],
        "common_failure_reasons": tasks["common_failure_reasons"],
        "events": events["by_kind"],
        "quota_rate_limit": {
            "rate_limit": _as_int(events["rate_limit_events"]) + _as_int(usage["rate_limit_events"]),
            "quota": _as_int(events["quota_events"]) + _as_int(usage["quota_events"]),
            "pause": events["pause_events"],
            "resume": events["resume_events"],
        },
        "tokens": {
            "total": usage["total_tokens"],
            "by_provider": usage["by_provider"],
            "by_model": usage["by_model"],
            "by_executor": tasks["tokens_by_executor"],
            "by_feature": usage["by_feature"],
            "requests": usage["requests"],
            "agent_calls": usage["agent_calls"],
        },
    }
    # Analytics is documented never-raise. Validate as an observation only: on
    # any structural issue still write the summary, but stamp a bounded
    # validation_issues count so a downstream reader can notice drift.
    from renmark import schemas

    issues = schemas.validate_analytics_summary(summary)
    if issues:
        summary["validation_issues"] = len(issues)
    _write_summary_atomic(repo, summary)
    return summary


# ── Health report ──────────────────────────────────────────────────────────────


def build_health_report(repo: str | Path, *, now: str) -> dict[str, object]:
    """Build the bounded ``/renmark:analytics`` health view (NEVER raw rows).

    Reuses :func:`aggregate` internally (which also refreshes summary.json),
    then projects it into the human-facing health fields: shipped/blocked
    feature names, recent releases, recent verification failures, loop success
    rate + avg iterations, backlog throughput, branch-disposition summary,
    token/cost by recent feature, and common failure reasons. Never raises.
    """
    summary = aggregate(repo, now=now)
    features = _dict(summary.get("features"))
    loops = _dict(summary.get("loops"))
    tasks = _dict(summary.get("tasks"))
    backlog = _dict(summary.get("backlog"))
    tokens = _dict(summary.get("tokens"))

    loop_total = _as_int(loops.get("total"))
    loop_success = _as_int(loops.get("success"))
    success_rate = round(loop_success / loop_total, 2) if loop_total else 0.0

    return {
        "generated_at": now,
        "shipped_features": features.get("shipped_names", []),
        "blocked_features": features.get("blocked_names", []),
        "releases_created": _as_int(summary.get("releases_created")),
        "verification_failures": _as_int(_dict(summary.get("verification")).get("fail")),
        "loop_success_rate": success_rate,
        "loop_avg_iterations": _as_float(loops.get("avg_iterations")),
        "backlog_throughput": {
            "completed": _as_int(backlog.get("completed")),
            "blocked": _as_int(backlog.get("blocked")),
            "rejected": _as_int(backlog.get("rejected")),
        },
        "branch_dispositions": summary.get("branch_dispositions", {}),
        "tokens_by_feature": tokens.get("by_feature", {}),
        "total_tokens": _as_int(tokens.get("total")),
        "common_failure_reasons": tasks.get("common_failure_reasons", []),
        "guardrails": summary.get("guardrails", {}),
    }


def _dict(value: object) -> dict[str, object]:
    """Return ``value`` if it's a dict, else an empty dict (non-raising helper)."""
    return value if isinstance(value, dict) else {}


def _list(value: object) -> list[object]:
    """Return ``value`` if it's a list, else an empty list (non-raising helper)."""
    return value if isinstance(value, list) else []


def render_health_md(report: dict[str, object]) -> str:
    """Render the health report as a bounded markdown summary. No raw rows.

    Pure formatter over the :func:`build_health_report` dict — counts and short
    lists only. Never raises: missing fields degrade to zeros / empty lists.
    """
    r = report if isinstance(report, dict) else {}
    shipped = _list(r.get("shipped_features"))
    blocked = _list(r.get("blocked_features"))
    backlog = _dict(r.get("backlog_throughput"))
    dispositions = _dict(r.get("branch_dispositions"))
    by_feature = _dict(r.get("tokens_by_feature"))
    failures = _list(r.get("common_failure_reasons"))
    guardrails = _dict(r.get("guardrails"))

    lines: list[str] = ["# renmark analytics"]
    gen = _as_str(r.get("generated_at"))
    if gen:
        lines.append(f"_generated {gen}_")
    lines.append("")
    shipped_tail = f" — {', '.join(map(str, shipped[:HEALTH_LIST_CAP]))}" if shipped else ""
    blocked_tail = f" — {', '.join(map(str, blocked[:HEALTH_LIST_CAP]))}" if blocked else ""
    lines.append(f"- Shipped features: {len(shipped)}{shipped_tail}")
    lines.append(f"- Blocked features: {len(blocked)}{blocked_tail}")
    lines.append(f"- Releases created: {_as_int(r.get('releases_created'))}")
    lines.append(f"- Verification failures: {_as_int(r.get('verification_failures'))}")
    lines.append(
        f"- Loop success rate: {_as_float(r.get('loop_success_rate'))} "
        f"(avg {_as_float(r.get('loop_avg_iterations'))} iterations)"
    )
    lines.append(
        f"- Backlog: {_as_int(backlog.get('completed'))} completed, "
        f"{_as_int(backlog.get('blocked'))} blocked, {_as_int(backlog.get('rejected'))} rejected"
    )
    lines.append(f"- Total tokens: {_as_int(r.get('total_tokens'))}")

    if dispositions:
        disp = ", ".join(f"{k}={_as_int(v)}" for k, v in dispositions.items())
        lines.append(f"- Branch dispositions: {disp}")
    if by_feature:
        feats = ", ".join(f"{k}={_as_int(v)}" for k, v in list(by_feature.items())[:HEALTH_LIST_CAP])
        lines.append(f"- Tokens by feature: {feats}")
    if failures:
        top = ", ".join(f"{_pair_name(item)} ({_pair_count(item)})" for item in failures[:TOP_FAILURE_REASONS])
        lines.append(f"- Common failures: {top}")
    if guardrails:
        verdicts = _dict(guardrails.get("inspection_verdicts"))
        verdicts_str = ", ".join(f"{k}={_as_int(v)}" for k, v in verdicts.items())
        lines.append(
            f"- Guardrails: {_as_int(guardrails.get('escalations_total'))} escalations "
            f"({_as_int(guardrails.get('escalations_blocking'))} blocking), "
            f"{_as_int(guardrails.get('inspection_total'))} inspections"
            + (f" [{verdicts_str}]" if verdicts_str else "")
        )

    return "\n".join(lines) + "\n"


def _pair_name(item: object) -> str:
    """Name half of a ``(reason, count)`` pair (tolerates list or tuple)."""
    if isinstance(item, (list, tuple)) and len(item) >= 1:
        return str(item[0])
    return str(item)


def _pair_count(item: object) -> int:
    """Count half of a ``(reason, count)`` pair (0 if malformed)."""
    if isinstance(item, (list, tuple)) and len(item) >= 2:
        return _as_int(item[1])
    return 0


__all__ = [
    "BLOCKED_STATUSES",
    "DEFAULT_SOURCE",
    "EVENTS_LEDGER",
    "EVENT_KINDS",
    "FEATURE_RUNS_LEDGER",
    "HEALTH_LIST_CAP",
    "LOOP_RUNS_LEDGER",
    "MAP_CAP",
    "SUCCESS_STATUSES",
    "SUMMARY_JSON",
    "TASK_RUNS_LEDGER",
    "TOP_FAILURE_REASONS",
    "aggregate",
    "analytics_dir",
    "build_health_report",
    "close_feature_disposition",
    "read_jsonl",
    "record_event",
    "record_feature_run",
    "record_loop_run",
    "record_task_run",
    "render_health_md",
]

"""Bounded, deterministic recurrence tracking for repeated issue signals.

Only structured recurrence metadata is persisted.  Raw signals are accepted long
enough to derive a fingerprint and bounded decision summary, then discarded.
"""

from __future__ import annotations

import importlib
import json
import os
import tempfile
import time
import warnings
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager, suppress
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Literal

from renmark.scan import content_fingerprint, finding_key_from_parts

RemediationClass = Literal["patch", "durable_guard"]
AcknowledgementAction = Literal["patch", "durable_guard", "retry_once"]

STATE_VERSION = 1
MAX_ENTRIES = 512
MAX_SUMMARY_LINES = 5
MAX_SUMMARY_LINE_CHARS = 240
_MAX_EVENT_TIMESTAMPS = 50
LOCK_TIMEOUT_SECONDS = 2.0
_SHORT_FINGERPRINT_CHARS = 16
_MAX_SOURCE_CHARS = 160
_MAX_TARGET_CHARS = 1024
_MAX_RUN_ID_CHARS = 160
_MAX_IDENTITY_CHARS = 160
_DURABLE_GUARD_RULE_MARKERS = ("instruction", "contract", "lane", "policy", "workflow")


class RecurrenceStateError(RuntimeError):
    """Raised when recurrence state cannot be safely read or persisted."""


class RecurrenceLockError(RecurrenceStateError):
    """Raised when the recurrence state lock remains busy past its timeout."""


@dataclass(frozen=True, slots=True)
class IssueObservation:
    """A single in-memory issue signal.

    ``summary_text`` can contain the current verifier signal.  It is never
    persisted and is used only for the content fingerprint and bounded return.
    """

    check: str
    rule_id: str
    target: str
    title: str
    summary_text: str
    source: str
    run_id: str
    observed_at: datetime | str | None = None


@dataclass(frozen=True, slots=True)
class RecurrenceDecision:
    """Bounded result for observation, query, acknowledgement, or resolution."""

    key: str
    fingerprint: str
    occurrence_count: int
    retry_blocked: bool
    remediation_class: RemediationClass
    summary_lines: tuple[str, ...]
    acknowledged: bool = False
    resolved: bool = False

    @property
    def stable_key(self) -> str:
        """Alias describing the stability contract of ``key``."""

        return self.key

    @property
    def short_fingerprint(self) -> str:
        """Alias for the bounded fingerprint exposed by the decision."""

        return self.fingerprint

    @property
    def total_occurrence_count(self) -> int:
        """Alias for the occurrence total in the current fingerprint sequence."""

        return self.occurrence_count

    @property
    def another_retry_blocked(self) -> bool:
        """Alias stating whether the next attempt is blocked."""

        return self.retry_blocked


def observe_issue(repo: str | os.PathLike[str], observation: IssueObservation) -> RecurrenceDecision:
    """Record an issue observation and return its bounded recurrence decision.

    The second equivalent observation reaches the proactive threshold.  From
    that point, an unacknowledged next attempt is blocked.  A changed
    fingerprint or a previously resolved entry starts a fresh sequence.
    """

    key = finding_key_from_parts(
        check=observation.check,
        rule_id=observation.rule_id,
        target=observation.target,
    )
    fingerprint = _short_fingerprint(
        content_fingerprint(
            title=observation.title,
            summary_text=observation.summary_text,
            target=observation.target,
        )
    )
    observed_at = _normalise_timestamp(observation.observed_at)
    current_summary = _bounded_signal_summary(observation.title, observation.summary_text)
    state_path, lock_path = _state_paths(repo)

    with _advisory_lock(lock_path):
        state, _ = _read_state(state_path)
        entries = state["entries"]
        previous = entries.get(key)
        starts_fresh = (
            previous is None
            or previous.get("fingerprint") != fingerprint
            or bool(previous.get("resolved"))
        )
        if starts_fresh:
            entry = _new_entry(key, fingerprint, observation, observed_at)
            if previous is not None and bool(previous.get("resolved")) and previous.get(
                "fingerprint"
            ) == fingerprint:
                entry["reopen_count"] = _positive_int(previous.get("reopen_count"), 0) + 1
                entry["reopen_timestamps"] = (
                    [*previous.get("reopen_timestamps", []), observed_at]
                )[-_MAX_EVENT_TIMESTAMPS:]
                # Carry forward resolved-event history across the reopen so
                # trailing-window guardrail metrics (reopen_rate) can still
                # see resolutions that predate this reopen.
                entry["resolved_timestamps"] = list(previous.get("resolved_timestamps", []))[
                    -_MAX_EVENT_TIMESTAMPS:
                ]
        else:
            entry = dict(previous)
            entry["occurrence_count"] = _positive_int(entry.get("occurrence_count"), 1) + 1
            entry["last_observed_at"] = observed_at
            entry["last_run_id"] = _bounded_text(observation.run_id, _MAX_RUN_ID_CHARS)
            entry["check"] = _bounded_text(observation.check, _MAX_IDENTITY_CHARS)
            entry["rule_id"] = _bounded_text(observation.rule_id, _MAX_IDENTITY_CHARS)
            entry["source"] = _bounded_text(observation.source, _MAX_SOURCE_CHARS)
            entry["target"] = _bounded_text(observation.target, _MAX_TARGET_CHARS)
            entry["remediation_class"] = _remediation_for(observation.rule_id)
            entry["resolved"] = False
            entry["resolved_at"] = None
            entry["resolved_run_id"] = None
        entries[key] = entry
        _write_state(state_path, state)

    return _decision(entry, current_summary)


def pre_attempt(
    repo: str | os.PathLike[str],
    *,
    check: str,
    rule_id: str,
    target: str,
) -> RecurrenceDecision | None:
    """Query whether an attempt may proceed for the logical issue key.

    If a ``retry_once`` acknowledgement is present at the block threshold, this
    call consumes it and permits exactly this one attempt.  A second query is
    blocked unless a new acknowledgement is recorded.
    """

    key = finding_key_from_parts(check=check, rule_id=rule_id, target=target)
    state_path, lock_path = _state_paths(repo)
    with _advisory_lock(lock_path):
        state, recovered = _read_state(state_path)
        raw_entry = state["entries"].get(key)
        if raw_entry is None:
            if recovered:
                _write_state(state_path, state)
            return None
        entry = dict(raw_entry)
        consumed_retry = bool(entry.get("retry_once_available")) and _is_blocked(entry)
        if consumed_retry:
            entry["retry_once_available"] = False
            entry["retry_once_consumed_at"] = _normalise_timestamp(None)
            state["entries"][key] = entry
            _write_state(state_path, state)
        elif recovered:
            _write_state(state_path, state)

    summary = _structured_summary(entry, permitted_once=consumed_retry)
    return _decision(entry, summary, retry_override=consumed_retry)


def acknowledge_issue(
    repo: str | os.PathLike[str],
    *,
    key: str,
    action: AcknowledgementAction,
    fingerprint: str | None = None,
    run_id: str = "",
    acknowledged_at: datetime | str | None = None,
) -> RecurrenceDecision | None:
    """Acknowledge a stored issue with a remediation action.

    ``patch`` and ``durable_guard`` remain acknowledged until resolution or a
    fresh fingerprint sequence.  ``retry_once`` is a transient permit consumed
    by :func:`pre_attempt`.  A fingerprint can be supplied to make stale
    acknowledgements a no-op.
    """

    if action not in ("patch", "durable_guard", "retry_once"):
        raise ValueError(f"unsupported acknowledgement action: {action!r}")
    state_path, lock_path = _state_paths(repo)
    with _advisory_lock(lock_path):
        state, recovered = _read_state(state_path)
        raw_entry = state["entries"].get(key)
        if raw_entry is None or (
            fingerprint is not None
            and raw_entry.get("fingerprint") != _short_fingerprint(fingerprint)
        ):
            if recovered:
                _write_state(state_path, state)
            return None
        entry = dict(raw_entry)
        entry["acknowledgement_action"] = action
        entry["acknowledged_at"] = _normalise_timestamp(acknowledged_at)
        entry["acknowledged_run_id"] = _bounded_text(run_id, _MAX_RUN_ID_CHARS)
        if action == "retry_once":
            entry["acknowledged"] = False
            entry["retry_once_available"] = True
            entry["retry_once_consumed_at"] = None
        else:
            entry["acknowledged"] = True
            entry["retry_once_available"] = False
            entry["retry_once_consumed_at"] = None
        state["entries"][key] = entry
        _write_state(state_path, state)

    return _decision(entry, _structured_summary(entry))


def resolve_issue(
    repo: str | os.PathLike[str],
    *,
    key: str,
    action: RemediationClass,
    fingerprint: str | None = None,
    run_id: str = "",
    resolved_at: datetime | str | None = None,
) -> RecurrenceDecision | None:
    """Resolve a stored issue through ``patch`` or ``durable_guard``.

    A subsequent equivalent observation reopens as occurrence one.  An optional
    fingerprint makes a stale resolution request a no-op.
    """

    if action not in ("patch", "durable_guard"):
        raise ValueError(f"unsupported resolution action: {action!r}")
    state_path, lock_path = _state_paths(repo)
    with _advisory_lock(lock_path):
        state, recovered = _read_state(state_path)
        raw_entry = state["entries"].get(key)
        if raw_entry is None or (
            fingerprint is not None
            and raw_entry.get("fingerprint") != _short_fingerprint(fingerprint)
        ):
            if recovered:
                _write_state(state_path, state)
            return None
        entry = dict(raw_entry)
        entry["acknowledged"] = True
        entry["acknowledgement_action"] = action
        entry["resolved"] = True
        timestamp = _normalise_timestamp(resolved_at)
        entry["resolved_at"] = timestamp
        entry["resolved_timestamps"] = (
            [*raw_entry.get("resolved_timestamps", []), timestamp]
        )[-_MAX_EVENT_TIMESTAMPS:]
        entry["resolved_run_id"] = _bounded_text(run_id, _MAX_RUN_ID_CHARS)
        entry["retry_once_available"] = False
        entry["retry_once_consumed_at"] = None
        state["entries"][key] = entry
        _write_state(state_path, state)

    return _decision(entry, _structured_summary(entry))


def _new_entry(
    key: str,
    fingerprint: str,
    observation: IssueObservation,
    observed_at: str,
) -> dict[str, Any]:
    return {
        "key": key,
        "fingerprint": fingerprint,
        "occurrence_count": 1,
        "check": _bounded_text(observation.check, _MAX_IDENTITY_CHARS),
        "rule_id": _bounded_text(observation.rule_id, _MAX_IDENTITY_CHARS),
        "source": _bounded_text(observation.source, _MAX_SOURCE_CHARS),
        "target": _bounded_text(observation.target, _MAX_TARGET_CHARS),
        "first_observed_at": observed_at,
        "last_observed_at": observed_at,
        "last_run_id": _bounded_text(observation.run_id, _MAX_RUN_ID_CHARS),
        "remediation_class": _remediation_for(observation.rule_id),
        "acknowledged": False,
        "acknowledgement_action": None,
        "acknowledged_at": None,
        "acknowledged_run_id": None,
        "retry_once_available": False,
        "retry_once_consumed_at": None,
        "resolved": False,
        "resolved_at": None,
        "resolved_run_id": None,
        "reopen_count": 0,
        "reopen_timestamps": [],
        "resolved_timestamps": [],
    }


def _decision(
    entry: Mapping[str, Any],
    summary_lines: Sequence[str],
    *,
    retry_override: bool = False,
) -> RecurrenceDecision:
    count = _positive_int(entry.get("occurrence_count"), 1)
    return RecurrenceDecision(
        key=str(entry["key"]),
        fingerprint=_short_fingerprint(str(entry["fingerprint"])),
        occurrence_count=count,
        retry_blocked=_is_blocked(entry) and not retry_override,
        remediation_class=_entry_remediation(entry),
        summary_lines=tuple(summary_lines[:MAX_SUMMARY_LINES]),
        acknowledged=bool(entry.get("acknowledged")),
        resolved=bool(entry.get("resolved")),
    )


def _is_blocked(entry: Mapping[str, Any]) -> bool:
    return (
        _positive_int(entry.get("occurrence_count"), 1) >= 2
        and not bool(entry.get("acknowledged"))
        and not bool(entry.get("resolved"))
    )


def _remediation_for(rule_id: object) -> RemediationClass:
    normalized = _bounded_text(rule_id, _MAX_IDENTITY_CHARS).lower().replace("_", "-")
    if any(marker in normalized.split("-") for marker in _DURABLE_GUARD_RULE_MARKERS):
        return "durable_guard"
    return "patch"


def _identity_from_key(key: object, index: int) -> str:
    parts = str(key).split(":", 2)
    return parts[index] if len(parts) == 3 else ""


def _entry_remediation(entry: Mapping[str, Any]) -> RemediationClass:
    rule_id = entry.get("rule_id") or _identity_from_key(entry.get("key"), 1)
    return _remediation_for(rule_id)


def _bounded_signal_summary(title: str, signal: str) -> tuple[str, ...]:
    candidates = [title, *signal.splitlines()]
    lines: list[str] = []
    for candidate in candidates:
        bounded = _bounded_text(candidate, MAX_SUMMARY_LINE_CHARS)
        if bounded and bounded not in lines:
            lines.append(bounded)
        if len(lines) == MAX_SUMMARY_LINES:
            break
    return tuple(lines)


def _structured_summary(
    entry: Mapping[str, Any],
    *,
    permitted_once: bool = False,
) -> tuple[str, ...]:
    count = _positive_int(entry.get("occurrence_count"), 1)
    status = (
        "resolved"
        if entry.get("resolved")
        else "acknowledged"
        if entry.get("acknowledged")
        else "open"
    )
    lines = (
        (
            f"{_bounded_text(entry.get('source'), _MAX_SOURCE_CHARS)}: "
            f"{_bounded_text(entry.get('target'), MAX_SUMMARY_LINE_CHARS)}"
        ),
        f"occurrences={count}; remediation={_entry_remediation(entry)}; status={status}",
        (
            "one-time retry permitted"
            if permitted_once
            else "next attempt blocked"
            if _is_blocked(entry)
            else "next attempt permitted"
        ),
    )
    return tuple(_bounded_text(line, MAX_SUMMARY_LINE_CHARS) for line in lines if line)


def _short_fingerprint(value: str) -> str:
    return str(value).strip()[:_SHORT_FINGERPRINT_CHARS]


def _bounded_text(value: object, limit: int) -> str:
    collapsed = " ".join(str(value or "").split())
    if len(collapsed) <= limit:
        return collapsed
    return collapsed[: max(0, limit - 1)].rstrip() + "…"


def _positive_int(value: object, default: int) -> int:
    if isinstance(value, bool):
        return default
    if not isinstance(value, (int, str)):
        return default
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


def _normalise_timestamp(value: datetime | str | None) -> str:
    if value is None:
        parsed = datetime.now(timezone.utc)
    elif isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        candidate = value.strip().replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(candidate)
        except ValueError as exc:
            raise ValueError(f"invalid ISO timestamp: {value!r}") from exc
    else:
        raise TypeError("timestamp must be datetime, ISO string, or None")
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_timestamp(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    candidate = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def reopen_rate(
    repo: str | os.PathLike[str],
    *,
    window_days: int = 30,
    now: str | None = None,
) -> dict[str, object]:
    """Count in-window resolve/reopen events across all recurrence entries.

    Counts individual events (not entries) whose timestamp parses and falls
    within ``[window_start, now]`` inclusive. Never raises; degrades to a
    zeroed result with a best-effort window on any error.
    """

    try:
        now_dt = _parse_timestamp(now) if now is not None else datetime.now(timezone.utc)
        if now_dt is None:
            now_dt = datetime.now(timezone.utc)
    except Exception:
        now_dt = datetime.now(timezone.utc)

    window_start_dt = now_dt - timedelta(days=window_days)
    window_start = _normalise_timestamp(window_start_dt)
    window_end = _normalise_timestamp(now_dt)

    try:
        state_path, _ = _state_paths(repo)
        state, _ = _read_state(state_path)
        resolved_total = 0
        reopened_total = 0
        for entry in state["entries"].values():
            for timestamp in entry.get("resolved_timestamps", []) or []:
                parsed = _parse_timestamp(timestamp)
                if parsed is not None and window_start_dt <= parsed <= now_dt:
                    resolved_total += 1
            for timestamp in entry.get("reopen_timestamps", []) or []:
                parsed = _parse_timestamp(timestamp)
                if parsed is not None and window_start_dt <= parsed <= now_dt:
                    reopened_total += 1
        return {
            "resolved_total": resolved_total,
            "reopened_total": reopened_total,
            "window_days": window_days,
            "window_start": window_start,
            "window_end": window_end,
        }
    except Exception:
        return {
            "resolved_total": 0,
            "reopened_total": 0,
            "window_days": window_days,
            "window_start": window_start,
            "window_end": window_end,
        }


def _state_paths(repo: str | os.PathLike[str]) -> tuple[Path, Path]:
    state_dir = Path(repo) / ".renmark" / "state"
    return state_dir / "recurrences.json", state_dir / "recurrences.lock"


def _empty_state() -> dict[str, Any]:
    return {"version": STATE_VERSION, "entries": {}}


def _read_state(path: Path) -> tuple[dict[str, Any], bool]:
    if not path.exists():
        return _empty_state(), False
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return _empty_state(), True
    if not isinstance(payload, dict) or not isinstance(payload.get("entries"), dict):
        return _empty_state(), True

    clean_entries: dict[str, dict[str, Any]] = {}
    recovered = False
    for raw_key, raw_entry in payload["entries"].items():
        clean = _clean_entry(raw_key, raw_entry)
        if clean is None:
            recovered = True
            continue
        clean_entries[clean["key"]] = clean
    if len(clean_entries) > MAX_ENTRIES:
        clean_entries = _prune_entries(clean_entries)
        recovered = True
    if payload.get("version") != STATE_VERSION:
        recovered = True
    return {"version": STATE_VERSION, "entries": clean_entries}, recovered


def _clean_entry(raw_key: object, raw_entry: object) -> dict[str, Any] | None:
    if not isinstance(raw_key, str) or not isinstance(raw_entry, dict):
        return None
    key = str(raw_entry.get("key", raw_key)).strip()
    fingerprint = _short_fingerprint(str(raw_entry.get("fingerprint", "")))
    if not key or key != raw_key or not fingerprint:
        return None
    count = _positive_int(raw_entry.get("occurrence_count"), 0)
    if count <= 0:
        return None
    check = _bounded_text(
        raw_entry.get("check") or _identity_from_key(key, 0),
        _MAX_IDENTITY_CHARS,
    )
    rule_id = _bounded_text(
        raw_entry.get("rule_id") or _identity_from_key(key, 1),
        _MAX_IDENTITY_CHARS,
    )
    remediation = _remediation_for(rule_id)
    action = raw_entry.get("acknowledgement_action")
    if action not in (None, "patch", "durable_guard", "retry_once"):
        action = None
    return {
        "key": key,
        "fingerprint": fingerprint,
        "occurrence_count": count,
        "check": check,
        "rule_id": rule_id,
        "source": _bounded_text(raw_entry.get("source"), _MAX_SOURCE_CHARS),
        "target": _bounded_text(raw_entry.get("target"), _MAX_TARGET_CHARS),
        "first_observed_at": _optional_bounded(raw_entry.get("first_observed_at")),
        "last_observed_at": _optional_bounded(raw_entry.get("last_observed_at")),
        "last_run_id": _optional_bounded(raw_entry.get("last_run_id"), _MAX_RUN_ID_CHARS),
        "remediation_class": remediation,
        "acknowledged": bool(raw_entry.get("acknowledged")),
        "acknowledgement_action": action,
        "acknowledged_at": _optional_bounded(raw_entry.get("acknowledged_at")),
        "acknowledged_run_id": _optional_bounded(raw_entry.get("acknowledged_run_id"), _MAX_RUN_ID_CHARS),
        "retry_once_available": bool(raw_entry.get("retry_once_available")),
        "retry_once_consumed_at": _optional_bounded(raw_entry.get("retry_once_consumed_at")),
        "resolved": bool(raw_entry.get("resolved")),
        "resolved_at": _optional_bounded(raw_entry.get("resolved_at")),
        "resolved_run_id": _optional_bounded(raw_entry.get("resolved_run_id"), _MAX_RUN_ID_CHARS),
        "reopen_count": _positive_int(raw_entry.get("reopen_count"), 0),
        "reopen_timestamps": _clean_timestamp_list(raw_entry.get("reopen_timestamps")),
        "resolved_timestamps": _clean_timestamp_list(raw_entry.get("resolved_timestamps")),
    }


def _optional_bounded(value: object, limit: int = 64) -> str | None:
    if value is None:
        return None
    bounded = _bounded_text(value, limit)
    return bounded or None


def _clean_timestamp_list(value: object) -> list[str]:
    if not isinstance(value, (list, tuple)):
        return []
    cleaned = [str(item) for item in value if isinstance(item, str) and item.strip()]
    return cleaned[-_MAX_EVENT_TIMESTAMPS:]


def _prune_entries(entries: Mapping[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    ranked = sorted(
        entries.items(),
        key=lambda item: (str(item[1].get("last_observed_at") or ""), item[0]),
        reverse=True,
    )[:MAX_ENTRIES]
    return dict(sorted(ranked))


def _write_state(path: Path, state: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    raw_entries = state.get("entries", {})
    if not isinstance(raw_entries, Mapping):
        raise RecurrenceStateError("recurrence entries must be a mapping")
    entries = _prune_entries(
        {str(key): dict(value) for key, value in raw_entries.items() if isinstance(value, Mapping)}
    )
    payload = {"version": STATE_VERSION, "entries": entries}
    temporary: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary = handle.name
            json.dump(payload, handle, sort_keys=True, separators=(",", ":"))
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        temporary = None
        _best_effort_sync_directory(path.parent)
    except OSError as exc:
        raise RecurrenceStateError(f"unable to persist recurrence state: {exc}") from exc
    finally:
        if temporary is not None:
            with suppress(FileNotFoundError):
                os.unlink(temporary)


def _best_effort_sync_directory(directory: Path) -> None:
    flags = getattr(os, "O_DIRECTORY", 0) | os.O_RDONLY
    try:
        descriptor = os.open(directory, flags)
    except OSError:
        return
    try:
        os.fsync(descriptor)
    except OSError:
        pass
    finally:
        os.close(descriptor)


@contextmanager
def _advisory_lock(path: Path) -> Iterator[bool]:
    """Acquire a bounded-wait advisory lock, or warn if locks are unavailable."""

    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        handle = path.open("a+b")
    except OSError as exc:
        raise RecurrenceLockError(f"unable to open recurrence lock: {exc}") from exc

    unlock: Any = None
    acquired = False
    try:
        try:
            fcntl: Any = importlib.import_module("fcntl")

            deadline = time.monotonic() + LOCK_TIMEOUT_SECONDS
            while True:
                try:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    acquired = True

                    def unlock_posix() -> None:
                        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

                    unlock = unlock_posix
                    break
                except BlockingIOError as exc:
                    if time.monotonic() >= deadline:
                        raise RecurrenceLockError(
                            "timed out waiting for recurrence lock"
                        ) from exc
                    time.sleep(0.025)
        except ModuleNotFoundError:
            try:
                msvcrt: Any = importlib.import_module("msvcrt")

                if path.stat().st_size == 0:
                    handle.write(b"\0")
                    handle.flush()
                deadline = time.monotonic() + LOCK_TIMEOUT_SECONDS
                while True:
                    try:
                        handle.seek(0)
                        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                        acquired = True

                        def unlock_windows() -> None:
                            handle.seek(0)
                            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)

                        unlock = unlock_windows
                        break
                    except OSError as exc:
                        if time.monotonic() >= deadline:
                            raise RecurrenceLockError(
                                "timed out waiting for recurrence lock"
                            ) from exc
                        time.sleep(0.025)
            except ModuleNotFoundError:
                warnings.warn(
                    "advisory file locking is unavailable; recurrence writes are not process-safe",
                    RuntimeWarning,
                    stacklevel=2,
                )
        yield acquired
    finally:
        if acquired and unlock is not None:
            try:
                unlock()
            except OSError:
                warnings.warn(
                    "recurrence advisory lock could not be released cleanly",
                    RuntimeWarning,
                    stacklevel=2,
                )
        handle.close()


# --- Durable failure-rule registry (additive; not part of REQ-24) ----------
#
# This section adds a curated, human-reviewed failure-rule registry.  It is
# deliberately independent of the recurrence tracking above: it has its own
# storage location, its own lock/state pair, and its own lifecycle.  Nothing
# above this marker is modified by this section.

import dataclasses

FailureRuleStatus = Literal["proposed", "active", "deprecated"]

_FAILURE_RULE_MAX_EVIDENCE_ENTRIES = 32
_FAILURE_RULE_MAX_EVIDENCE_CHARS = 512


@dataclass(frozen=True, slots=True)
class FailureRuleEnforcement:
    """How a failure rule is enforced, if at all."""

    prompt: str | None = None
    validator: str | None = None
    capability_policy: str | None = None


@dataclass(frozen=True, slots=True)
class FailureRule:
    """A single curated, durable failure-prevention rule."""

    rule_id: str
    status: FailureRuleStatus
    trigger: str
    applicability: str
    required_behavior: str
    prohibited_failure: str
    source_evidence: tuple[str, ...]
    enforcement: FailureRuleEnforcement
    regression_test_ref: str
    created_at: str
    last_triggered_at: str | None = None
    review_after: str | None = None


@dataclass(frozen=True, slots=True)
class RuleConflict:
    """A detected duplicate or contradiction between two failure rules."""

    rule_id_a: str
    rule_id_b: str
    kind: Literal["duplicate_trigger", "contradiction"]
    detail: str


def _failure_rule_registry_path(repo: str | os.PathLike[str]) -> Path:
    """Path to the curated failure-rule registry.

    Unlike ``recurrences.json`` (gitignored, per-run scratch state living
    under ``.renmark/state/``), this registry lives under
    ``.renmark/memory/`` because it is curated and versioned like
    ``decisions.md``: it is meant to survive ``/renmark:hygiene``, to be
    read and reviewed by a human, and to be committed to the repo — not
    ephemeral per-run runtime state.
    """

    return Path(repo) / ".renmark" / "memory" / "failure_rules.jsonl"


def _failure_rule_lock_path(repo: str | os.PathLike[str]) -> Path:
    return Path(repo) / ".renmark" / "memory" / ".failure_rules.jsonl.lock"


def _failure_rule_enforcement_to_dict(enforcement: FailureRuleEnforcement) -> dict[str, Any]:
    return {
        "prompt": enforcement.prompt,
        "validator": enforcement.validator,
        "capability_policy": enforcement.capability_policy,
    }


def _failure_rule_enforcement_from_dict(raw: object) -> FailureRuleEnforcement:
    if not isinstance(raw, Mapping):
        return FailureRuleEnforcement()
    return FailureRuleEnforcement(
        prompt=_optional_str(raw.get("prompt")),
        validator=_optional_str(raw.get("validator")),
        capability_policy=_optional_str(raw.get("capability_policy")),
    )


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


def _failure_rule_to_dict(rule: FailureRule) -> dict[str, Any]:
    return {
        "rule_id": rule.rule_id,
        "status": rule.status,
        "trigger": rule.trigger,
        "applicability": rule.applicability,
        "required_behavior": rule.required_behavior,
        "prohibited_failure": rule.prohibited_failure,
        "source_evidence": list(rule.source_evidence),
        "enforcement": _failure_rule_enforcement_to_dict(rule.enforcement),
        "regression_test_ref": rule.regression_test_ref,
        "created_at": rule.created_at,
        "last_triggered_at": rule.last_triggered_at,
        "review_after": rule.review_after,
    }


def _failure_rule_from_dict(raw: object) -> FailureRule | None:
    if not isinstance(raw, Mapping):
        return None
    try:
        rule_id = str(raw["rule_id"]).strip()
        status = raw["status"]
        trigger = str(raw["trigger"])
        applicability = str(raw["applicability"])
        required_behavior = str(raw["required_behavior"])
        prohibited_failure = str(raw["prohibited_failure"])
        created_at = str(raw["created_at"])
    except (KeyError, TypeError):
        return None
    if not rule_id or status not in ("proposed", "active", "deprecated"):
        return None
    raw_evidence = raw.get("source_evidence")
    source_evidence = (
        tuple(str(item) for item in raw_evidence) if isinstance(raw_evidence, (list, tuple)) else ()
    )
    return FailureRule(
        rule_id=rule_id,
        status=status,
        trigger=trigger,
        applicability=applicability,
        required_behavior=required_behavior,
        prohibited_failure=prohibited_failure,
        source_evidence=source_evidence,
        enforcement=_failure_rule_enforcement_from_dict(raw.get("enforcement")),
        regression_test_ref=str(raw.get("regression_test_ref", "")),
        created_at=created_at,
        last_triggered_at=_optional_str(raw.get("last_triggered_at")),
        review_after=_optional_str(raw.get("review_after")),
    )


def load_failure_rules(repo: str | os.PathLike[str]) -> tuple[FailureRule, ...]:
    """Load the curated failure-rule registry.

    Tolerant of a missing file (returns ``()``) and of malformed lines
    (skipped, never raised).
    """

    path = _failure_rule_registry_path(repo)
    if not path.exists():
        return ()
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return ()
    rules: list[FailureRule] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            raw = json.loads(line)
        except json.JSONDecodeError:
            continue
        rule = _failure_rule_from_dict(raw)
        if rule is not None:
            rules.append(rule)
    return tuple(rules)


def _save_failure_rules(repo: str | os.PathLike[str], rules: Sequence[FailureRule]) -> None:
    """Atomically rewrite the failure-rule registry in full.

    Mirrors ``_write_state``'s tempfile + ``os.replace`` pattern but targets
    the registry's own path -- this never touches ``recurrences.json`` or
    its lock.
    """

    path = _failure_rule_registry_path(repo)
    path.parent.mkdir(parents=True, exist_ok=True)
    ordered = sorted(rules, key=lambda rule: rule.rule_id)
    temporary: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary = handle.name
            for rule in ordered:
                json.dump(_failure_rule_to_dict(rule), handle, sort_keys=True, separators=(",", ":"))
                handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        temporary = None
        _best_effort_sync_directory(path.parent)
    except OSError as exc:
        raise RecurrenceStateError(f"unable to persist failure rule registry: {exc}") from exc
    finally:
        if temporary is not None:
            with suppress(FileNotFoundError):
                os.unlink(temporary)


def _find_failure_rule(rules: Sequence[FailureRule], rule_id: str) -> tuple[int, FailureRule]:
    for index, rule in enumerate(rules):
        if rule.rule_id == rule_id:
            return index, rule
    raise ValueError(f"unknown failure rule id: {rule_id!r}")


def propose_failure_rule(
    repo: str | os.PathLike[str],
    *,
    rule_id: str,
    trigger: str,
    applicability: str,
    required_behavior: str,
    prohibited_failure: str,
    source_evidence: Sequence[str],
    enforcement: FailureRuleEnforcement | None = None,
    regression_test_ref: str = "",
    review_after: str | None = None,
    created_at: datetime | str | None = None,
) -> FailureRule:
    """Propose a new failure rule with status ``"proposed"``.

    Raises ``ValueError`` if ``rule_id`` already exists in the registry --
    no silent overwrite of a curated entry.
    """

    lock_path = _failure_rule_lock_path(repo)
    with _advisory_lock(lock_path):
        rules = list(load_failure_rules(repo))
        if any(rule.rule_id == rule_id for rule in rules):
            raise ValueError(f"failure rule already exists: {rule_id!r}")
        rule = FailureRule(
            rule_id=rule_id,
            status="proposed",
            trigger=trigger,
            applicability=applicability,
            required_behavior=required_behavior,
            prohibited_failure=prohibited_failure,
            source_evidence=tuple(source_evidence),
            enforcement=enforcement or FailureRuleEnforcement(),
            regression_test_ref=regression_test_ref,
            created_at=_normalise_timestamp(created_at),
            last_triggered_at=None,
            review_after=review_after,
        )
        rules.append(rule)
        _save_failure_rules(repo, rules)
    return rule


def activate_failure_rule(repo: str | os.PathLike[str], rule_id: str) -> FailureRule:
    """Activate a proposed failure rule.

    Only legal from ``"proposed"``; the lifecycle is forward-only
    (proposed -> active -> deprecated), so calling this on an already
    ``"active"`` or ``"deprecated"`` rule raises ``ValueError``.
    """

    lock_path = _failure_rule_lock_path(repo)
    with _advisory_lock(lock_path):
        rules = list(load_failure_rules(repo))
        index, rule = _find_failure_rule(rules, rule_id)
        if rule.status != "proposed":
            raise ValueError(
                f"failure rule {rule_id!r} cannot be activated from status {rule.status!r}"
            )
        updated = dataclasses.replace(rule, status="active")
        rules[index] = updated
        _save_failure_rules(repo, rules)
    return updated


def deprecate_failure_rule(
    repo: str | os.PathLike[str],
    rule_id: str,
    *,
    reason: str = "",
) -> FailureRule:
    """Deprecate a proposed or active failure rule.

    Legal from ``"proposed"`` or ``"active"``.  A non-empty ``reason`` is
    appended into ``source_evidence`` as a bounded trailing entry so the
    deprecation rationale is not lost.
    """

    lock_path = _failure_rule_lock_path(repo)
    with _advisory_lock(lock_path):
        rules = list(load_failure_rules(repo))
        index, rule = _find_failure_rule(rules, rule_id)
        if rule.status not in ("proposed", "active"):
            raise ValueError(
                f"failure rule {rule_id!r} cannot be deprecated from status {rule.status!r}"
            )
        evidence = rule.source_evidence
        if reason:
            trailing = _bounded_text(reason, _FAILURE_RULE_MAX_EVIDENCE_CHARS)
            evidence = (*evidence, f"deprecated: {trailing}")[-_FAILURE_RULE_MAX_EVIDENCE_ENTRIES:]
        updated = dataclasses.replace(rule, status="deprecated", source_evidence=evidence)
        rules[index] = updated
        _save_failure_rules(repo, rules)
    return updated


def _normalise_compare(value: str) -> str:
    return " ".join(str(value or "").split()).casefold()


def detect_failure_rule_conflicts(rules: Sequence[FailureRule]) -> tuple[RuleConflict, ...]:
    """Pairwise-detect duplicate or contradictory failure rules.

    Pure function: it never loads state and never mutates the registry --
    it only flags conflicts for a human to resolve.  A deprecated rule
    never conflicts with anything.
    """

    conflicts: list[RuleConflict] = []
    live = [rule for rule in rules if rule.status in ("proposed", "active")]
    for i in range(len(live)):
        for j in range(i + 1, len(live)):
            a, b = live[i], live[j]
            if _normalise_compare(a.trigger) != _normalise_compare(b.trigger):
                continue
            if _normalise_compare(a.applicability) != _normalise_compare(b.applicability):
                continue
            same_behavior = _normalise_compare(a.required_behavior) == _normalise_compare(
                b.required_behavior
            )
            same_failure = _normalise_compare(a.prohibited_failure) == _normalise_compare(
                b.prohibited_failure
            )
            kind: Literal["duplicate_trigger", "contradiction"] = (
                "duplicate_trigger" if same_behavior and same_failure else "contradiction"
            )
            rule_id_a, rule_id_b = sorted((a.rule_id, b.rule_id))
            detail = (
                f"same trigger/applicability; behavior_match={same_behavior}, "
                f"failure_match={same_failure}"
            )
            conflicts.append(
                RuleConflict(rule_id_a=rule_id_a, rule_id_b=rule_id_b, kind=kind, detail=detail)
            )
    return tuple(conflicts)


def failure_rules_due_for_review(
    repo: str | os.PathLike[str],
    *,
    as_of: datetime | str | None = None,
) -> tuple[FailureRule, ...]:
    """Return active rules whose ``review_after`` has passed.

    Read-only: never changes ``status`` and never touches ``review_after``.
    This is the read the roadmap's Release 12 ``/renmark:hygiene``
    pruning-sweep extension point is expected to call; this release adds
    only the read -- it does not wire the hygiene call site (deferred).
    """

    cutoff = _normalise_timestamp(as_of)
    due: list[FailureRule] = []
    for rule in load_failure_rules(repo):
        if rule.status != "active" or not rule.review_after:
            continue
        if rule.review_after <= cutoff:
            due.append(rule)
    return tuple(due)


def durable_guard_seed_candidates(
    repo: str | os.PathLike[str],
    *,
    min_occurrences: int = 3,
) -> tuple[dict[str, Any], ...]:
    """Surface ``durable_guard`` recurrence entries as evidence candidates.

    This reads ``durable_guard`` entries as evidence; it does not consume,
    mutate, or replace ``recurrence.py``'s REQ-24 state.  It never
    constructs or persists a ``FailureRule`` -- it only returns bounded
    dicts suitable to pass as evidence text in a future
    ``propose_failure_rule(..., source_evidence=[...])`` call; a human or a
    future release decides whether to actually make that call.
    """

    state_path, _ = _state_paths(repo)
    state, _ = _read_state(state_path)
    candidates: list[dict[str, Any]] = []
    for entry in state["entries"].values():
        if entry.get("remediation_class") != "durable_guard":
            continue
        if bool(entry.get("resolved")):
            continue
        count = _positive_int(entry.get("occurrence_count"), 0)
        if count < min_occurrences:
            continue
        candidates.append(
            {
                "key": entry.get("key"),
                "occurrence_count": count,
                "target": entry.get("target"),
                "last_observed_at": entry.get("last_observed_at"),
            }
        )
    return tuple(candidates)


__all__ = [
    "MAX_ENTRIES",
    "AcknowledgementAction",
    "FailureRule",
    "FailureRuleEnforcement",
    "FailureRuleStatus",
    "IssueObservation",
    "RecurrenceDecision",
    "RecurrenceLockError",
    "RecurrenceStateError",
    "RemediationClass",
    "RuleConflict",
    "acknowledge_issue",
    "activate_failure_rule",
    "deprecate_failure_rule",
    "detect_failure_rule_conflicts",
    "durable_guard_seed_candidates",
    "failure_rules_due_for_review",
    "load_failure_rules",
    "observe_issue",
    "pre_attempt",
    "propose_failure_rule",
    "reopen_rate",
    "resolve_issue",
]

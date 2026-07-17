"""Bounded, deterministic recurrence tracking for repeated issue signals.

Only structured recurrence metadata is persisted.  Raw signals are accepted long
enough to derive a fingerprint and bounded decision summary, then discarded.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import tempfile
import time
from typing import Any, Iterator, Literal, Mapping, Sequence
import warnings

from renmark.scan import content_fingerprint, finding_key_from_parts


RemediationClass = Literal["patch", "durable_guard"]
AcknowledgementAction = Literal["patch", "durable_guard", "retry_once"]

STATE_VERSION = 1
MAX_ENTRIES = 512
MAX_SUMMARY_LINES = 5
MAX_SUMMARY_LINE_CHARS = 240
LOCK_TIMEOUT_SECONDS = 2.0
_SHORT_FINGERPRINT_CHARS = 16
_MAX_SOURCE_CHARS = 160
_MAX_TARGET_CHARS = 1024
_MAX_RUN_ID_CHARS = 160


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
        else:
            entry = dict(previous)
            entry["occurrence_count"] = _positive_int(entry.get("occurrence_count"), 1) + 1
            entry["last_observed_at"] = observed_at
            entry["last_run_id"] = _bounded_text(observation.run_id, _MAX_RUN_ID_CHARS)
            entry["source"] = _bounded_text(observation.source, _MAX_SOURCE_CHARS)
            entry["target"] = _bounded_text(observation.target, _MAX_TARGET_CHARS)
            entry["remediation_class"] = _remediation_for(entry["occurrence_count"])
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
        "source": _bounded_text(observation.source, _MAX_SOURCE_CHARS),
        "target": _bounded_text(observation.target, _MAX_TARGET_CHARS),
        "first_observed_at": observed_at,
        "last_observed_at": observed_at,
        "last_run_id": _bounded_text(observation.run_id, _MAX_RUN_ID_CHARS),
        "remediation_class": "patch",
        "acknowledged": False,
        "acknowledgement_action": None,
        "acknowledged_at": None,
        "acknowledged_run_id": None,
        "retry_once_available": False,
        "retry_once_consumed_at": None,
        "resolved": False,
        "resolved_at": None,
        "resolved_run_id": None,
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
        remediation_class=_remediation_for(count),
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


def _remediation_for(occurrence_count: int) -> RemediationClass:
    return "durable_guard" if occurrence_count >= 2 else "patch"


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
    status = "resolved" if entry.get("resolved") else "acknowledged" if entry.get("acknowledged") else "open"
    lines = (
        f"{_bounded_text(entry.get('source'), _MAX_SOURCE_CHARS)}: {_bounded_text(entry.get('target'), MAX_SUMMARY_LINE_CHARS)}",
        f"occurrences={count}; remediation={_remediation_for(count)}; status={status}",
        "one-time retry permitted" if permitted_once else "next attempt blocked" if _is_blocked(entry) else "next attempt permitted",
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
    try:
        parsed = int(value)  # type: ignore[arg-type]
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
    remediation = _remediation_for(count)
    action = raw_entry.get("acknowledgement_action")
    if action not in (None, "patch", "durable_guard", "retry_once"):
        action = None
    return {
        "key": key,
        "fingerprint": fingerprint,
        "occurrence_count": count,
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
    }


def _optional_bounded(value: object, limit: int = 64) -> str | None:
    if value is None:
        return None
    bounded = _bounded_text(value, limit)
    return bounded or None


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
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass


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
            import fcntl  # type: ignore[import-not-found]

            deadline = time.monotonic() + LOCK_TIMEOUT_SECONDS
            while True:
                try:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    acquired = True
                    unlock = lambda: fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
                    break
                except BlockingIOError:
                    if time.monotonic() >= deadline:
                        raise RecurrenceLockError("timed out waiting for recurrence lock")
                    time.sleep(0.025)
        except ImportError:
            try:
                import msvcrt  # type: ignore[import-not-found]

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
                    except OSError:
                        if time.monotonic() >= deadline:
                            raise RecurrenceLockError("timed out waiting for recurrence lock")
                        time.sleep(0.025)
            except ImportError:
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


__all__ = [
    "AcknowledgementAction",
    "IssueObservation",
    "MAX_ENTRIES",
    "RecurrenceDecision",
    "RecurrenceLockError",
    "RecurrenceStateError",
    "RemediationClass",
    "acknowledge_issue",
    "observe_issue",
    "pre_attempt",
    "resolve_issue",
]

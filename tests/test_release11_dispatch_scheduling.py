"""
---
artifact_type: pytest-test-module
schema_version: 1
created_at: 2026-08-05T18:48:21Z
source_sha: 09b26e9
related_plan: "Release 11 task 3: scheduling regression + signal-consumption tests"
generator: codex
stale_after: null
dependency_refs:
  - renmark/dispatch.py
  - tests/test_dispatch.py
  - renmark/usage.py
completion_state: complete
confidence: medium
validation_status: unvalidated
retry_count: 0
parser_success: true
schema_compliance: true
---

Regression coverage for Release 11 dispatch scheduling signals.

## Summary
- Guards the no-signal path against the legacy scheduling output across three
  existing task-list shapes from `tests/test_dispatch.py`.
- Verifies `max_parallelism` splitting, including the no-op cases for `0` and
  `None`.
- Exercises quota throttling with a literal usage-view-shaped stub and confirms
  the throttled provider is serialized while the other provider is not.
- Confirms `rework_lookup` writes `rework_note` without changing wave
  membership, and `risk_resolver` only changes ordering when present.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from renmark import dispatch
from tests.test_dispatch import _task

REWORK_NOTE = "rework signal at or over budget (log-only; not a retry gate)"


def _freeze(value: Any) -> Any:
    if isinstance(value, dict):
        return tuple((key, _freeze(val)) for key, val in sorted(value.items()))
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, tuple):
        return tuple(_freeze(item) for item in value)
    return value


def _task_signature(task: Any) -> tuple[Any, ...]:
    return tuple((key, _freeze(val)) for key, val in sorted(task.__dict__.items()))


def _wave_signature(waves: list[list[Any]]) -> tuple[tuple[tuple[Any, ...], ...], ...]:
    return tuple(tuple(_task_signature(task) for task in wave) for wave in waves)


def _serial_fixture_tasks() -> list[Any]:
    return [_task(1, "a"), _task(2, "b"), _task(3, "c")]


def _shared_group_fixture_tasks() -> list[Any]:
    return [
        _task(1, "a", parallel_group=1),
        _task(2, "b", parallel_group=1),
        _task(3, "c", parallel_group=2),
        _task(4, "d", parallel_group=2),
    ]


def _fanout_fixture_tasks() -> list[Any]:
    return [
        _task(1, "src/a.py", executor="sonnet", parallel_group=1),
        _task(2, "src/b.py", executor="opus", parallel_group=1),
        _task(3, "src/c.py", executor="fable", parallel_group=1),
    ]


def _five_same_group_tasks() -> list[Any]:
    return [
        _task(1, "a", parallel_group=1),
        _task(2, "b", parallel_group=1),
        _task(3, "c", parallel_group=1),
        _task(4, "d", parallel_group=1),
        _task(5, "e", parallel_group=1),
    ]


def _assert_legacy_compatibility(task_factory: Callable[[], list[Any]]) -> None:
    baseline = dispatch.group_tasks_by_wave(task_factory())
    explicit_none = dispatch.group_tasks_by_wave(
        task_factory(),
        max_parallelism=None,
        quota_view=None,
        rework_lookup=None,
        risk_resolver=None,
    )

    assert _wave_signature(explicit_none) == _wave_signature(baseline)


def test_group_tasks_by_wave_legacy_compatibility_regression_guard() -> None:
    for task_factory in (
        _serial_fixture_tasks,
        _shared_group_fixture_tasks,
        _fanout_fixture_tasks,
    ):
        _assert_legacy_compatibility(task_factory)


def test_group_tasks_by_wave_max_parallelism_splits_stably() -> None:
    waves = dispatch.group_tasks_by_wave(_five_same_group_tasks(), max_parallelism=2)

    assert [len(subwave) for subwave in waves] == [2, 2, 1]
    assert [[task.target for task in subwave] for subwave in waves] == [
        ["a", "b"],
        ["c", "d"],
        ["e"],
    ]


def test_group_tasks_by_wave_max_parallelism_zero_and_none_are_noops() -> None:
    baseline = _wave_signature(dispatch.group_tasks_by_wave(_five_same_group_tasks()))

    assert _wave_signature(dispatch.group_tasks_by_wave(_five_same_group_tasks(), max_parallelism=0)) == baseline
    assert _wave_signature(dispatch.group_tasks_by_wave(_five_same_group_tasks(), max_parallelism=None)) == baseline


def test_group_tasks_by_wave_quota_signal_serializes_only_the_throttled_provider() -> None:
    wave = [
        _task(1, "a", executor="sonnet", parallel_group=1),
        _task(2, "b", executor="sonnet", parallel_group=1),
        _task(3, "c", executor="sonnet", parallel_group=1),
        _task(4, "d", executor="codex", parallel_group=1),
        _task(5, "e", executor="codex", parallel_group=1),
    ]
    quota_view = {
        "limit_exceeded": True,
        "percent": {
            "claude": {
                "rolling_5h_tokens": 125.0,
                "weekly_tokens": 125.0,
            },
            "codex": {
                "rolling_5h_tokens": 15.0,
                "weekly_tokens": 10.0,
            },
        },
        "rolling_5h": {"total_tokens": 140, "rows": 2},
        "weekly": {"total_tokens": 210, "rows": 3},
        "top_features": [],
        "disclaimer": "",
    }

    waves = dispatch.group_tasks_by_wave(wave, quota_view=quota_view)

    assert [len(subwave) for subwave in waves] == [1, 1, 3]
    assert [[task.target for task in subwave] for subwave in waves] == [
        ["a"],
        ["b"],
        ["c", "d", "e"],
    ]
    assert [task.executor for task in waves[-1]] == ["sonnet", "codex", "codex"]


def test_group_tasks_by_wave_rework_lookup_annotates_without_reordering() -> None:
    wave = [
        _task(1, "a", parallel_group=1),
        _task(2, "b", parallel_group=1),
        _task(3, "c", parallel_group=1),
    ]

    waves = dispatch.group_tasks_by_wave(
        wave,
        rework_lookup=lambda task: True if task.target == "b" else False,
    )

    assert len(waves) == 1
    assert [task.target for task in waves[0]] == ["a", "b", "c"]
    assert getattr(waves[0][1], "rework_note", None) == REWORK_NOTE
    assert getattr(waves[0][0], "rework_note", None) is None
    assert getattr(waves[0][2], "rework_note", None) is None


def test_group_tasks_by_wave_risk_resolver_prioritizes_high_risk_and_none_matches_baseline() -> None:
    baseline = dispatch.group_tasks_by_wave(
        [_task(1, "a", parallel_group=1), _task(2, "b", parallel_group=1), _task(3, "c", parallel_group=1)]
    )
    riskless = dispatch.group_tasks_by_wave(
        [_task(1, "a", parallel_group=1), _task(2, "b", parallel_group=1), _task(3, "c", parallel_group=1)],
        risk_resolver=None,
    )
    risky = dispatch.group_tasks_by_wave(
        [_task(1, "a", parallel_group=1), _task(2, "b", parallel_group=1), _task(3, "c", parallel_group=1)],
        risk_resolver=lambda task: "high" if task.target == "b" else None,
    )

    assert _wave_signature(riskless) == _wave_signature(baseline)
    assert [task.target for task in risky[0]] == ["b", "a", "c"]

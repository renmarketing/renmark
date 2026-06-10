import json

from renmark.state.pause import PauseState, read_pause, usage_limit_pause, write_pause
from renmark.state.usage import (
    UsageRecord,
    append_usage,
    read_usage,
    tokens_by_feature,
    usage_in_window,
    usage_last_5h,
    usage_last_week,
)


def test_read_pause_loads_old_paused_dict_with_defaults(tmp_path):
    paused_path = tmp_path / ".renmark" / "state" / "PAUSED"
    paused_path.parent.mkdir(parents=True)
    paused_path.write_text(
        json.dumps(
            {
                "run_id": "r1",
                "plan_path": "plan.md",
                "last_task_index": 3,
                "reason": "manual pause",
                "ts": "2026-06-09T12:00:00Z",
            }
        )
    )

    state = read_pause(tmp_path)

    assert state == PauseState(
        run_id="r1",
        plan_path="plan.md",
        last_task_index=3,
        reason="manual pause",
        ts="2026-06-09T12:00:00Z",
    )
    assert state.pause_kind == ""
    assert state.fallback_retry_minutes == 60


def test_usage_limit_pause_round_trips_through_pause_file(tmp_path):
    # write_pause now validates a usage_limit pause (validate_usage_pause):
    # resume_after must be non-empty. classify_usage_pause always computes one;
    # supply it here so the persisted pause is contractually valid.
    state = usage_limit_pause(
        run_id="r",
        plan_path="p",
        last_task_index=0,
        ts="2026-06-09T12:00:00Z",
        provider="claude",
        resume_after="2026-06-09T17:00:00Z",
    )

    assert state.pause_kind == "usage_limit"

    write_pause(tmp_path, state)
    loaded = read_pause(tmp_path)

    assert loaded == state


def test_write_pause_rejects_invalid_usage_limit_pause(tmp_path):
    """A usage_limit pause missing its required resume_after is a writer bug —
    write_pause raises rather than persisting unrecoverable pause state."""
    import pytest

    bad = usage_limit_pause(
        run_id="r", plan_path="p", last_task_index=0,
        ts="2026-06-09T12:00:00Z", provider="claude",  # no resume_after
    )
    with pytest.raises(ValueError):
        write_pause(tmp_path, bad)


def test_write_pause_allows_plain_manual_pause(tmp_path):
    """validate_usage_pause no-ops for non-usage_limit kinds — a plain pause
    (no resume_after) must still write cleanly."""
    plain = PauseState(
        run_id="r", plan_path="p", last_task_index=0,
        reason="manual pause", ts="2026-06-09T12:00:00Z",
    )
    write_pause(tmp_path, plain)
    assert read_pause(tmp_path) == plain


def test_usage_record_round_trips_with_new_fields(tmp_path):
    rec = UsageRecord(
        ts="2026-06-09T12:00:00Z",
        run_id="run-1",
        task_id=7,
        model="claude-sonnet",
        prompt_tokens=100,
        completion_tokens=25,
        provider="claude",
        feature="orchestrate",
        source="provider-export",
        kind="usage_limit",
        cached_tokens=9,
    )

    append_usage(tmp_path, rec)
    rows = read_usage(tmp_path)

    assert rows == [
        {
            "ts": "2026-06-09T12:00:00Z",
            "run_id": "run-1",
            "task_id": 7,
            "model": "claude-sonnet",
            "prompt_tokens": 100,
            "completion_tokens": 25,
            "attempt": 0,
            "provider": "claude",
            "cached_tokens": 9,
            "context_window_tokens": 0,
            "agent_calls": 0,
            "requests": 0,
            "feature": "orchestrate",
            "source": "provider-export",
            "kind": "usage_limit",
        }
    ]


def test_usage_windows_only_count_rows_inside_injected_now(tmp_path):
    now = "2026-06-09T12:00:00Z"
    append_usage(
        tmp_path,
        UsageRecord(
            ts=now,
            run_id="r",
            task_id=1,
            model="m",
            prompt_tokens=10,
            completion_tokens=5,
        ),
    )
    append_usage(
        tmp_path,
        UsageRecord(
            ts="2026-06-09T06:00:00Z",
            run_id="r",
            task_id=2,
            model="m",
            prompt_tokens=20,
            completion_tokens=7,
        ),
    )

    in_window = usage_in_window(tmp_path, now=now, seconds=5 * 3600)
    last_5h = usage_last_5h(tmp_path, now=now)
    last_week = usage_last_week(tmp_path, now=now)

    assert in_window["total_tokens"] == 15
    assert in_window["rows"] == 1
    assert last_5h["total_tokens"] == 15
    assert last_5h["rows"] == 1
    assert last_week["total_tokens"] == 42
    assert last_week["rows"] == 2


def test_tokens_by_feature_ranks_descending_and_respects_top(tmp_path):
    now = "2026-06-09T12:00:00Z"
    append_usage(
        tmp_path,
        UsageRecord(
            ts=now,
            run_id="r",
            task_id=1,
            model="m",
            prompt_tokens=10,
            completion_tokens=5,
            feature="alpha",
        ),
    )
    append_usage(
        tmp_path,
        UsageRecord(
            ts=now,
            run_id="r",
            task_id=2,
            model="m",
            prompt_tokens=20,
            completion_tokens=7,
            feature="beta",
        ),
    )
    append_usage(
        tmp_path,
        UsageRecord(
            ts=now,
            run_id="r",
            task_id=3,
            model="m",
            prompt_tokens=3,
            completion_tokens=1,
            feature="gamma",
        ),
    )

    ranked = tokens_by_feature(tmp_path, now=now, seconds=7 * 24 * 3600, top=2)

    assert ranked == [("beta", 27), ("alpha", 15)]

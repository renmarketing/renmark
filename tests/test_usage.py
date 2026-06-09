import json
from datetime import datetime, timedelta, timezone

import renmark.state as state
import renmark.usage as usage


NOW = "2026-06-09T12:00:00Z"


def _write_limits(repo, payload):
    analytics_dir = repo / ".renmark" / "analytics"
    analytics_dir.mkdir(parents=True, exist_ok=True)
    (analytics_dir / "limits.json").write_text(
        json.dumps(payload),
        encoding="utf-8",
    )


def _write_usage_rows(repo, rows):
    ledger_path = state.state_dir(repo) / state.USAGE_LEDGER
    with ledger_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")


def _build_repo_with_usage(repo):
    _write_limits(
        repo,
        {
            "claude": {"rolling_5h_tokens": 1000, "weekly_tokens": 5000},
            "codex": {"rolling_5h_tokens": 2000, "weekly_tokens": 8000},
        },
    )
    _write_usage_rows(
        repo,
        [
            {
                "ts": "2026-06-09T11:00:00Z",
                "feature": "alpha",
                "prompt_tokens": 30,
                "completion_tokens": 70,
                "requests": 1,
                "agent_calls": 0,
            },
            {
                "ts": "2026-06-09T10:30:00Z",
                "feature": "alpha",
                "prompt_tokens": 40,
                "completion_tokens": 60,
                "requests": 1,
                "agent_calls": 1,
            },
            {
                "ts": "2026-06-08T12:30:00Z",
                "feature": "beta",
                "prompt_tokens": 100,
                "completion_tokens": 200,
                "requests": 1,
                "agent_calls": 0,
            },
            {
                "ts": "2026-06-03T12:00:00Z",
                "feature": "gamma",
                "prompt_tokens": 5,
                "completion_tokens": 5,
                "requests": 1,
                "agent_calls": 0,
            },
        ],
    )


def _parse_iso(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def test_read_limits_returns_empty_without_file_and_parses_written_file(tmp_path):
    assert usage.read_limits(tmp_path) == {}

    payload = {
        "claude": {"rolling_5h_tokens": 1111, "weekly_tokens": 7777},
        "codex": {"rolling_5h_requests": 42},
    }
    _write_limits(tmp_path, payload)

    assert usage.read_limits(tmp_path) == payload


def test_percent_used_handles_missing_or_zero_limit_and_positive_limit():
    assert usage.percent_used(25, None) is None
    assert usage.percent_used(25, 0) is None
    assert usage.percent_used(25, 200) == 12.5


def test_build_usage_view_includes_expected_blocks_top_features_and_disclaimer(
    tmp_path,
):
    _build_repo_with_usage(tmp_path)

    view = usage.build_usage_view(tmp_path, now=NOW)

    assert view["rolling_5h"]["total_tokens"] == 200
    assert view["rolling_5h"]["rows"] == 2
    assert view["weekly"]["total_tokens"] == 510
    assert view["weekly"]["rows"] == 4
    assert view["top_features"] == [("beta", 300), ("alpha", 200), ("gamma", 10)]
    assert view["disclaimer"] == usage.DISCLAIMER


def test_build_usage_view_surfaces_resume_after_from_usage_limit_pause(tmp_path):
    _build_repo_with_usage(tmp_path)
    pause = state.usage_limit_pause(
        run_id="run-123",
        plan_path="/tmp/plan.md",
        last_task_index=2,
        ts=NOW,
        provider="claude",
        observed_usage="95%",
        provider_reset_at="",
        resume_after="2026-06-09T14:00:00Z",
    )
    state.write_pause(tmp_path, pause)

    view = usage.build_usage_view(tmp_path, now=NOW)

    assert view["paused_run"] == {
        "resume_after": "2026-06-09T14:00:00Z",
        "provider": "claude",
        "observed_usage": "95%",
        "reason": "usage limit reached",
    }


def test_classify_usage_pause_fallback_rule():
    by_provider_reset = usage.classify_usage_pause(
        run_id="run-1",
        plan_path="/tmp/plan.md",
        last_task_index=1,
        now=NOW,
        provider="claude",
        provider_reset_at="2026-06-09T13:15:00Z",
        limits={},
    )
    assert by_provider_reset.pause_kind == "usage_limit"
    assert by_provider_reset.resume_after == "2026-06-09T13:15:00Z"

    by_local_window = usage.classify_usage_pause(
        run_id="run-2",
        plan_path="/tmp/plan.md",
        last_task_index=1,
        now=NOW,
        provider="claude",
        provider_reset_at="",
        limits={"claude": {"rolling_5h_tokens": 100}},
    )
    assert by_local_window.pause_kind == "usage_limit"
    assert _parse_iso(by_local_window.resume_after) > _parse_iso(NOW)

    by_default = usage.classify_usage_pause(
        run_id="run-3",
        plan_path="/tmp/plan.md",
        last_task_index=1,
        now=NOW,
        provider="claude",
        provider_reset_at="",
        limits={},
    )
    assert by_default.pause_kind == "usage_limit"
    assert _parse_iso(by_default.resume_after) == _parse_iso(NOW) + timedelta(
        minutes=60
    )


def test_render_usage_md_ends_with_exact_disclaimer_and_hides_raw_jsonl(tmp_path):
    _build_repo_with_usage(tmp_path)
    state.write_pause(
        tmp_path,
        state.usage_limit_pause(
            run_id="run-123",
            plan_path="/tmp/plan.md",
            last_task_index=2,
            ts=NOW,
            provider="claude",
            observed_usage="95%",
            resume_after="2026-06-09T14:00:00Z",
        ),
    )
    view = usage.build_usage_view(tmp_path, now=NOW)

    markdown = usage.render_usage_md(view)

    assert markdown.endswith(usage.DISCLAIMER)
    assert '{"ts":' not in markdown
    assert '"prompt_tokens"' not in markdown

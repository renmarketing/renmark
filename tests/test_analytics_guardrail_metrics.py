"""
---
artifact_type: pytest_test_artifact
schema_version: 1
created_at: 2026-08-06T00:00:00-04:00
source_sha: 781dc705ad7ca520282b96366f523211d6af80c0
related_plan: .renmark/plans/2026-08-05-governed-orchestration-assurance-release-14.plan.md
generator: codex
stale_after: null
dependency_refs:
  - renmark.analytics
  - renmark.recurrence
  - tests/test_reports_analytics.py
---

Pytest coverage for guardrail metric aggregation and health-report wiring.

The tests below verify denominator semantics, window exclusion, recurrence
reopen accounting, empty-repo fallbacks, and the existing analytics summary
shape that should stay intact while the new guardrail metrics are added.

## Summary
- Covers `_agg_guardrail_metrics` denominator, window, and note-field semantics.
- Exercises recurrence reopen behavior through `aggregate()` and health-report wiring.
- Verifies empty repos degrade to zero rates and no exceptions.
- Confirms `guardrail_metrics` is added without changing the existing summary/health shapes.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from renmark import analytics, recurrence, schemas


NOW = "2026-08-06T12:00:00Z"


def _iso_days_ago(days: int) -> str:
    now_dt = datetime.fromisoformat(NOW.replace("Z", "+00:00"))
    return (now_dt - timedelta(days=days)).isoformat().replace("+00:00", "Z")


def _task_row(*, ts: str, task_id: int, measured: bool) -> dict[str, object]:
    return {"ts": ts, "task_id": task_id, "measured": measured}


def _scope_check_row(*, ts: str, passed: bool) -> dict[str, object]:
    return {"ts": ts, "kind": "scope_check", "passed": passed}


def _observation(
    *,
    rule_id: str = "verifier-failure",
    target: str = "tests/test_widget.py",
    signal: str = "stable failure",
    run_id: str = "run-1",
) -> recurrence.IssueObservation:
    return recurrence.IssueObservation(
        check="codex-retry",
        rule_id=rule_id,
        target=target,
        title=f"Codex {rule_id}",
        summary_text=signal,
        source="test",
        run_id=run_id,
    )


def _assert_guardrail_window_fields(metrics: dict[str, object], *, window_days: int) -> None:
    assert metrics["window_days"] == window_days
    assert metrics["window_end"] == NOW
    assert metrics["window_start"] == _iso_days_ago(window_days)
    assert metrics["owner_interruptions_per_milestone"] is None
    assert metrics["owner_interruptions_note"]
    assert metrics["duplicate_artifact_rate"] is None
    assert metrics["duplicate_artifact_note"]


def _assert_summary_shape(summary: dict[str, object]) -> None:
    assert set(summary) == {
        "backlog",
        "branch_dispositions",
        "common_failure_reasons",
        "events",
        "features",
        "generated_at",
        "guardrail_metrics",
        "guardrails",
        "loops",
        "quota_rate_limit",
        "releases_created",
        "source",
        "tasks",
        "tokens",
        "verification",
    }
    assert summary["features"].keys() == {
        "started",
        "completed",
        "blocked",
        "by_status",
        "branch_dispositions",
        "shipped_names",
        "blocked_names",
    }
    assert summary["tasks"].keys() == {
        "total",
        "passed",
        "failed",
        "skipped",
        "verification_pass",
        "verification_fail",
        "common_failure_reasons",
        "tokens_by_executor",
        "tokens_by_model",
        "tokens_by_provider",
        "measured_tokens_total",
        "unmeasured_task_count",
    }
    assert summary["loops"].keys() == {
        "total",
        "success",
        "failure",
        "avg_iterations",
        "by_stop_reason",
        "branch_dispositions",
    }
    assert isinstance(summary["events"], dict)
    assert set(summary["quota_rate_limit"]) == {"pause", "quota", "rate_limit", "resume"}
    assert summary["tokens"].keys() == {
        "agent_calls",
        "by_executor",
        "by_feature",
        "by_model",
        "by_provider",
        "requests",
        "total",
    }


def test_agg_guardrail_metrics_uses_scope_checks_not_task_rows_and_records_window_metadata(
    tmp_path: Path,
) -> None:
    checks = [
        _scope_check_row(ts=NOW, passed=True),
        _scope_check_row(ts=NOW, passed=True),
        _scope_check_row(ts=NOW, passed=False),
        _scope_check_row(ts=NOW, passed=False),
    ]
    four_tasks = [_task_row(ts=NOW, task_id=index, measured=True) for index in range(1, 5)]
    ten_tasks = [_task_row(ts=NOW, task_id=index, measured=True) for index in range(1, 11)]

    metrics = analytics._agg_guardrail_metrics(
        tmp_path,
        task_rows=four_tasks,
        event_rows=checks,
        now=NOW,
    )

    assert metrics["scope_violation_rate"] == 0.5
    assert metrics["unknown_usage_rate"] == 0.0
    _assert_guardrail_window_fields(metrics, window_days=30)

    wider = analytics._agg_guardrail_metrics(
        tmp_path,
        task_rows=ten_tasks,
        event_rows=checks,
        now=NOW,
        window_days=7,
    )

    assert wider["scope_violation_rate"] == 0.5
    assert wider["unknown_usage_rate"] == 0.0
    _assert_guardrail_window_fields(wider, window_days=7)


def test_agg_guardrail_metrics_counts_unmeasured_tasks_and_excludes_stale_rows(
    tmp_path: Path,
) -> None:
    fresh = NOW
    stale = _iso_days_ago(40)
    task_rows = [
        _task_row(ts=fresh, task_id=1, measured=True),
        _task_row(ts=fresh, task_id=2, measured=True),
        _task_row(ts=fresh, task_id=3, measured=True),
        _task_row(ts=stale, task_id=4, measured=False),
    ]
    event_rows = [
        _scope_check_row(ts=fresh, passed=True),
        _scope_check_row(ts=fresh, passed=True),
        _scope_check_row(ts=fresh, passed=True),
        _scope_check_row(ts=stale, passed=False),
    ]

    metrics = analytics._agg_guardrail_metrics(
        tmp_path,
        task_rows=task_rows,
        event_rows=event_rows,
        now=NOW,
    )

    assert metrics["scope_violation_rate"] == 0.0
    assert metrics["unknown_usage_rate"] == 0.0
    assert metrics["scope_violation_rate"] != 0.25
    assert metrics["unknown_usage_rate"] != 0.25


def test_agg_guardrail_metrics_false_pass_reopen_rate_tracks_event_timestamps(
    tmp_path: Path,
) -> None:
    open_repo = tmp_path / "open"
    open_repo.mkdir()

    first = recurrence.observe_issue(open_repo, _observation())
    resolved = recurrence.resolve_issue(
        open_repo,
        key=first.key,
        action="patch",
        fingerprint=first.fingerprint,
        run_id="resolved-now",
        resolved_at=NOW,
    )
    reopened = recurrence.observe_issue(open_repo, _observation(run_id="reopened-now"))

    assert resolved is not None
    assert reopened.occurrence_count == 1

    windowed = recurrence.reopen_rate(open_repo, window_days=30, now=NOW)
    assert windowed["resolved_total"] == 1
    assert windowed["reopened_total"] == 1

    metrics = analytics._agg_guardrail_metrics(
        open_repo,
        task_rows=[],
        event_rows=[],
        now=NOW,
    )
    assert metrics["false_pass_reopen_rate"] == 1.0

    stale_repo = tmp_path / "stale"
    stale_repo.mkdir()

    first = recurrence.observe_issue(stale_repo, _observation(run_id="stale-open"))
    resolved = recurrence.resolve_issue(
        stale_repo,
        key=first.key,
        action="patch",
        fingerprint=first.fingerprint,
        run_id="resolved-40d-ago",
        resolved_at=_iso_days_ago(40),
    )
    reopened = recurrence.observe_issue(stale_repo, _observation(run_id="reopened-now"))

    assert resolved is not None
    assert reopened.occurrence_count == 1

    windowed = recurrence.reopen_rate(stale_repo, window_days=30, now=NOW)
    assert windowed["resolved_total"] == 0
    assert windowed["reopened_total"] == 1

    metrics = analytics._agg_guardrail_metrics(
        stale_repo,
        task_rows=[],
        event_rows=[],
        now=NOW,
    )
    assert metrics["false_pass_reopen_rate"] == 0.0


def test_aggregate_build_health_and_render_health_surface_guardrail_metrics(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()

    for index in range(4):
        analytics.record_task_run(
            repo,
            ts=NOW,
            task_id=index + 1,
            title=f"Task {index + 1}",
            executor="codex",
            model="gpt-5",
            provider="openai",
            status="PASS",
            verifier_result="PASS",
            measured=index != 0,
            total_tokens=10,
            sha=f"sha-{index + 1}",
        )

    for passed in (True, True, False, False):
        analytics.record_event(repo, ts=NOW, kind="scope_check", passed=passed)

    first = recurrence.observe_issue(repo, _observation())
    recurrence.resolve_issue(
        repo,
        key=first.key,
        action="patch",
        fingerprint=first.fingerprint,
        run_id="resolved-now",
        resolved_at=NOW,
    )
    recurrence.observe_issue(repo, _observation(run_id="reopened-now"))

    summary = analytics.aggregate(repo, now=NOW)
    assert "guardrail_metrics" in summary
    assert schemas.validate_analytics_summary(summary) == []
    _assert_summary_shape(summary)
    assert summary["events"] == {"scope_check": 4}
    assert summary["quota_rate_limit"] == {
        "pause": 0,
        "quota": 0,
        "rate_limit": 0,
        "resume": 0,
    }
    assert summary["guardrail_metrics"]["scope_violation_rate"] == 0.5
    assert summary["guardrail_metrics"]["unknown_usage_rate"] == 0.25
    assert summary["guardrail_metrics"]["false_pass_reopen_rate"] == 1.0
    assert summary["events"] == {"scope_check": 4}
    assert summary["tasks"]["unmeasured_task_count"] == 1

    health = analytics.build_health_report(repo, now=NOW)
    assert health["guardrail_metrics"] == summary["guardrail_metrics"]
    assert health["guardrails"] == summary["guardrails"]
    assert health["guardrail_metrics"]["window_days"] == 30
    assert health["guardrail_metrics"]["window_end"] == NOW
    assert health["guardrail_metrics"]["window_start"] == _iso_days_ago(30)

    md = analytics.render_health_md(health)
    assert "- Guardrail metrics: scope-violation 50.0%, unknown-usage 25.0%, reopen 100.0%" in md
    assert "Owner-interruptions and duplicate-artifact rate: not yet measured" in md


def test_aggregate_empty_repo_degrades_guardrail_metrics_to_zero(tmp_path: Path) -> None:
    summary = analytics.aggregate(tmp_path, now=NOW)
    health = analytics.build_health_report(tmp_path, now=NOW)

    assert schemas.validate_analytics_summary(summary) == []
    assert summary["guardrail_metrics"]["scope_violation_rate"] == 0.0
    assert summary["guardrail_metrics"]["unknown_usage_rate"] == 0.0
    assert summary["guardrail_metrics"]["false_pass_reopen_rate"] == 0.0
    _assert_guardrail_window_fields(summary["guardrail_metrics"], window_days=30)
    assert health["guardrail_metrics"] == summary["guardrail_metrics"]
    assert health["guardrail_metrics"]["scope_violation_rate"] == 0.0
    assert health["guardrail_metrics"]["unknown_usage_rate"] == 0.0
    assert health["guardrail_metrics"]["false_pass_reopen_rate"] == 0.0
    assert analytics.render_health_md(health)

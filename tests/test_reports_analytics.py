import json

from renmark import analytics, reports, schemas

NOW = "2026-06-09T12:00:00Z"


def test_build_and_write_feature_report(tmp_path):
    repo = tmp_path

    report = reports.build_feature_report(
        repo,
        feature="reporting-and-usage-analytics",
        branch="feature/x",
        sha="abc",
        files_changed=3,
        verification="PASS",
        shipped=["usage.py"],
        now=NOW,
    )

    assert report["feature"] == "reporting-and-usage-analytics"
    assert report["branch"] == "feature/x"
    assert report["sha"] == "abc"
    assert report["files_changed"] == 3
    assert report["verification"] == "PASS"
    assert report["shipped"] == ["usage.py"]
    assert report["created_at"] == NOW

    report_path, metrics_path = reports.write_feature_report(
        repo,
        "reporting-and-usage-analytics",
        report,
    )

    expected_dir = repo / ".renmark" / "reports" / "features" / "reporting-and-usage-analytics"
    assert report_path == expected_dir / "report.md"
    assert metrics_path == expected_dir / "metrics.json"
    assert report_path.is_file()
    assert metrics_path.is_file()

    metrics = json.loads(metrics_path.read_text())
    assert schemas.validate_report_metrics(metrics) == []


def test_feature_report_uses_version_path_for_release_link(tmp_path):
    report = reports.build_feature_report(
        tmp_path,
        feature="reporting-and-usage-analytics",
        branch="feature/x",
        sha="abc",
        files_changed=3,
        verification="PASS",
        shipped=["usage.py"],
        version_path=".renmark/version/v0.7.9/",
        now=NOW,
    )

    assert report["version_path"] == ".renmark/version/v0.7.9/"
    assert report["release_link"]


def test_record_functions_append_parseable_jsonl(tmp_path):
    repo = tmp_path

    analytics.record_task_run(
        repo,
        ts=NOW,
        task_id=1,
        title="Test task",
        executor="codex",
        model="gpt-5",
        provider="openai",
        status="PASS",
        verifier_result="PASS",
        retry_count=0,
        failure_reason="",
        duration_s=1.5,
        tokens_in=10,
        tokens_out=20,
        total_tokens=30,
        est_cost_usd=0.12,
        sha="abc",
    )
    analytics.record_feature_run(
        repo,
        ts=NOW,
        feature="reporting-and-usage-analytics",
        branch="feature/x",
        status="PASS",
        sha="abc",
        files_changed=3,
        verification="PASS",
        token_cost={"total_tokens": 30},
        branch_disposition="kept",
    )
    analytics.record_loop_run(
        repo,
        ts=NOW,
        loop_id="loop-1",
        goal="Ship analytics",
        backlog_item_id="backlog-1",
        max_iterations=5,
        iterations_used=2,
        stop_reason="goal_reached",
        goal_reached=True,
        total_tokens=30,
        est_cost_usd=0.12,
        branch_disposition="kept",
    )
    analytics.record_event(
        repo,
        ts=NOW,
        kind="quota",
        scope="feature",
        state="pause",
    )

    analytics_dir = repo / ".renmark" / "analytics"
    for name in (
        "task-runs.jsonl",
        "feature-runs.jsonl",
        "loop-runs.jsonl",
        "events.jsonl",
    ):
        path = analytics_dir / name
        assert path.is_file()
        rows = path.read_text().splitlines()
        assert rows
        for row in rows:
            assert isinstance(json.loads(row), dict)


def test_aggregate_and_health_report_cover_seeded_and_empty_projects(tmp_path):
    repo = tmp_path / "seeded"
    repo.mkdir()

    analytics.record_task_run(
        repo,
        ts=NOW,
        task_id=1,
        title="Pass task",
        executor="codex",
        model="gpt-5",
        provider="openai",
        status="PASS",
        verifier_result="PASS",
        total_tokens=30,
        sha="abc",
    )
    analytics.record_task_run(
        repo,
        ts=NOW,
        task_id=2,
        title="Fail task",
        executor="codex",
        model="gpt-5",
        provider="openai",
        status="FAIL",
        verifier_result="FAIL",
        failure_reason="timeout",
        total_tokens=12,
        sha="def",
    )
    analytics.record_feature_run(
        repo,
        ts=NOW,
        feature="reporting-and-usage-analytics",
        branch="feature/x",
        status="PASS",
        sha="abc",
        files_changed=3,
        verification="PASS",
        token_cost={"total_tokens": 42},
        branch_disposition="merged",
    )
    analytics.record_feature_run(
        repo,
        ts=NOW,
        feature="blocked-feature",
        branch="feature/y",
        status="BLOCKED",
        sha="def",
        files_changed=1,
        verification="FAIL",
        branch_disposition="abandoned",
    )
    analytics.record_loop_run(
        repo,
        ts=NOW,
        loop_id="loop-1",
        goal="Ship analytics",
        max_iterations=5,
        iterations_used=2,
        stop_reason="goal_reached",
        goal_reached=True,
        total_tokens=40,
        est_cost_usd=0.2,
        branch_disposition="merged",
    )
    analytics.record_loop_run(
        repo,
        ts=NOW,
        loop_id="loop-2",
        goal="Fix blocker",
        max_iterations=5,
        iterations_used=4,
        stop_reason="quota",
        goal_reached=False,
        total_tokens=15,
        est_cost_usd=0.08,
        branch_disposition="abandoned",
    )
    analytics.record_event(repo, ts=NOW, kind="quota")
    analytics.record_event(repo, ts=NOW, kind="pause")
    analytics.record_event(repo, ts=NOW, kind="resume")
    analytics.record_event(repo, ts=NOW, kind="rate_limit")

    summary = analytics.aggregate(repo, now=NOW)
    summary_path = repo / ".renmark" / "analytics" / "summary.json"
    written_summary = json.loads(summary_path.read_text())
    assert summary_path.is_file()
    assert schemas.validate_analytics_summary(summary) == []
    assert schemas.validate_analytics_summary(written_summary) == []
    assert written_summary["generated_at"] == summary["generated_at"]
    assert written_summary["tasks"]["total"] == summary["tasks"]["total"]
    assert written_summary["features"]["started"] == summary["features"]["started"]
    assert written_summary["loops"]["total"] == summary["loops"]["total"]
    assert summary["generated_at"] == NOW
    assert summary["tasks"]["total"] == 2
    assert summary["tasks"]["passed"] == 1
    assert summary["tasks"]["failed"] == 1
    assert summary["features"]["started"] == 2
    assert summary["features"]["by_status"]["pass"] == 1
    assert summary["features"]["by_status"]["blocked"] == 1
    assert summary["loops"]["total"] == 2
    assert summary["events"]["quota"] == 1
    assert summary["quota_rate_limit"] == {
        "pause": 1,
        "quota": 1,
        "rate_limit": 1,
        "resume": 1,
    }

    health = analytics.build_health_report(repo, now=NOW)
    assert set(health) == {
        "backlog_throughput",
        "blocked_features",
        "branch_dispositions",
        "common_failure_reasons",
        "generated_at",
        "guardrails",
        "loop_avg_iterations",
        "loop_success_rate",
        "releases_created",
        "shipped_features",
        "tokens_by_feature",
        "total_tokens",
        "verification_failures",
    }
    assert "rows" not in health
    assert health["generated_at"] == NOW
    assert health["blocked_features"] == ["blocked-feature"]
    assert health["loop_avg_iterations"] == 3.0
    assert health["loop_success_rate"] == 0.5

    empty_repo = tmp_path / "empty"
    empty_repo.mkdir()
    empty_summary = analytics.aggregate(empty_repo, now=NOW)
    empty_health = analytics.build_health_report(empty_repo, now=NOW)
    assert schemas.validate_analytics_summary(empty_summary) == []
    assert empty_summary["tasks"]["total"] == 0
    assert empty_summary["features"]["started"] == 0
    assert empty_summary["loops"]["total"] == 0
    assert empty_health["blocked_features"] == []
    assert empty_health["shipped_features"] == []
    assert empty_health["total_tokens"] == 0
    assert empty_health["loop_avg_iterations"] == 0.0
    assert empty_health["loop_success_rate"] == 0.0


def test_record_feature_run_idempotent_on_rerun(tmp_path):
    """Re-running /renmark:finish for the same closed feature must not
    double-count it in the health report."""
    repo = tmp_path
    for _ in range(2):
        analytics.record_feature_run(
            repo,
            ts=NOW,
            feature="feat-x",
            status="shipped",
            sha="abc",
            branch_disposition="merged",
        )
    ledger = analytics.analytics_dir(repo) / analytics.FEATURE_RUNS_LEDGER
    assert len(analytics.read_jsonl(ledger)) == 1
    # A genuinely different run (new sha) still appends.
    analytics.record_feature_run(
        repo,
        ts=NOW,
        feature="feat-x",
        status="shipped",
        sha="def",
        branch_disposition="merged",
    )
    assert len(analytics.read_jsonl(ledger)) == 2


def test_close_feature_disposition_transforms_not_appends(tmp_path):
    repo = tmp_path
    analytics.record_feature_run(
        repo,
        ts=NOW,
        feature="f1",
        branch="feature/f1",
        status="completed",
        sha="s1",
        branch_disposition="open",
    )

    changed = analytics.close_feature_disposition(
        repo,
        feature="f1",
        sha="s1",
        disposition="merged-deleted",
    )

    ledger = analytics.analytics_dir(repo) / analytics.FEATURE_RUNS_LEDGER
    rows = analytics.read_jsonl(ledger)
    matching = [row for row in rows if row["feature"] == "f1" and row["sha"] == "s1"]

    assert changed is True
    assert len(matching) == 1
    assert matching[0]["branch_disposition"] == "merged-deleted"


def test_close_feature_disposition_no_double_count_in_rollup(tmp_path):
    repo = tmp_path
    analytics.record_feature_run(
        repo,
        ts=NOW,
        feature="f1",
        branch="feature/f1",
        status="completed",
        sha="s1",
        branch_disposition="open",
    )
    analytics.close_feature_disposition(
        repo,
        feature="f1",
        sha="s1",
        disposition="merged-deleted",
    )

    health = analytics.build_health_report(repo, now=NOW)

    assert health["branch_dispositions"].get("merged-deleted") == 1
    assert health["branch_dispositions"].get("open", 0) == 0


def test_close_feature_disposition_idempotent(tmp_path):
    repo = tmp_path
    analytics.record_feature_run(
        repo,
        ts=NOW,
        feature="f1",
        branch="feature/f1",
        status="completed",
        sha="s1",
        branch_disposition="open",
    )
    analytics.close_feature_disposition(
        repo,
        feature="f1",
        sha="s1",
        disposition="merged-deleted",
    )

    second_changed = analytics.close_feature_disposition(
        repo,
        feature="f1",
        sha="s1",
        disposition="merged-deleted",
    )

    ledger = analytics.analytics_dir(repo) / analytics.FEATURE_RUNS_LEDGER
    rows = analytics.read_jsonl(ledger)
    matching = [row for row in rows if row["feature"] == "f1" and row["sha"] == "s1"]

    assert second_changed is False
    assert len(matching) == 1
    assert matching[0]["branch_disposition"] == "merged-deleted"


def test_close_feature_disposition_absent_is_noop(tmp_path):
    repo = tmp_path
    ledger = analytics.analytics_dir(repo) / analytics.FEATURE_RUNS_LEDGER
    before = analytics.read_jsonl(ledger)

    changed = analytics.close_feature_disposition(repo, feature="nope", sha="nope")

    after = analytics.read_jsonl(ledger)

    assert changed is False
    assert len(after) == len(before)


def test_close_feature_disposition_treats_legacy_merged_as_nonterminal(tmp_path):
    repo = tmp_path
    analytics.record_feature_run(
        repo,
        ts=NOW,
        feature="f2",
        branch="feature/f2",
        status="completed",
        sha="s2",
        branch_disposition="merged",
    )

    changed = analytics.close_feature_disposition(repo, feature="f2", sha="s2")

    ledger = analytics.analytics_dir(repo) / analytics.FEATURE_RUNS_LEDGER
    rows = analytics.read_jsonl(ledger)
    matching = [row for row in rows if row["feature"] == "f2" and row["sha"] == "s2"]

    assert changed is True
    assert len(matching) == 1
    assert matching[0]["branch_disposition"] == "merged-deleted"


def test_close_feature_disposition_sha_mismatch_falls_back_to_feature(tmp_path):
    """Post-merge HEAD is the merge-commit sha, not the feature-tip sha step 2.5
    recorded — the close-out must still close by feature identity (fallback)."""
    repo = tmp_path
    analytics.record_feature_run(
        repo,
        ts=NOW,
        feature="fX",
        branch="feature/fX",
        status="completed",
        sha="real-sha",
        branch_disposition="open",
    )

    changed = analytics.close_feature_disposition(
        repo,
        feature="fX",
        sha="WRONG-merge-sha",
        disposition="merged-deleted",
    )

    ledger = analytics.analytics_dir(repo) / analytics.FEATURE_RUNS_LEDGER
    rows = analytics.read_jsonl(ledger)
    matching = [row for row in rows if row["feature"] == "fX"]

    assert changed is True
    assert len(matching) == 1
    assert matching[0]["branch_disposition"] == "merged-deleted"


def test_close_feature_disposition_branch_narrows_when_feature_slug_reused(tmp_path):
    """The feature slug is reusable, so two concurrent runs can share a feature
    name on different branches. Closing one branch's run must NOT over-close the
    other branch's still-open run — ``branch`` is the stable narrowing key."""
    repo = tmp_path
    analytics.record_feature_run(
        repo,
        ts=NOW,
        feature="dup",
        branch="feature/dup",
        status="completed",
        sha="sha-dup-1",
        branch_disposition="open",
    )
    analytics.record_feature_run(
        repo,
        ts=NOW,
        feature="dup",
        branch="feature/dup-2",
        status="completed",
        sha="sha-dup-2",
        branch_disposition="open",
    )

    changed = analytics.close_feature_disposition(
        repo,
        feature="dup",
        branch="feature/dup",
        disposition="merged-deleted",
    )

    ledger = analytics.analytics_dir(repo) / analytics.FEATURE_RUNS_LEDGER
    rows = analytics.read_jsonl(ledger)
    by_branch = {row["branch"]: row for row in rows if row["feature"] == "dup"}

    assert changed is True
    assert by_branch["feature/dup"]["branch_disposition"] == "merged-deleted"
    # The other run (same slug, different branch) was NOT over-closed.
    assert by_branch["feature/dup-2"]["branch_disposition"] == "open"


def test_close_feature_disposition_wrong_branch_does_not_overclose(tmp_path):
    """A WRONG/stale branch on a reused feature slug must close nothing. When the
    given ``branch`` matches no candidate, the fallback is legacy-only (rows with
    no recorded branch) — it must NEVER close rows carrying a *different* branch,
    which belong to other runs (over-close is the exact bug branch narrowing
    prevents)."""
    repo = tmp_path
    analytics.record_feature_run(
        repo,
        ts=NOW,
        feature="reuse",
        branch="feature/reuse-a",
        status="completed",
        sha="sha-reuse-a",
        branch_disposition="open",
    )
    analytics.record_feature_run(
        repo,
        ts=NOW,
        feature="reuse",
        branch="feature/reuse-b",
        status="completed",
        sha="sha-reuse-b",
        branch_disposition="open",
    )

    changed = analytics.close_feature_disposition(
        repo,
        feature="reuse",
        branch="feature/NONEXISTENT",
        disposition="merged-deleted",
    )

    ledger = analytics.analytics_dir(repo) / analytics.FEATURE_RUNS_LEDGER
    rows = analytics.read_jsonl(ledger)
    by_branch = {row["branch"]: row for row in rows if row["feature"] == "reuse"}

    # A wrong branch closed nothing — both other-run rows remain open.
    assert changed is False
    assert by_branch["feature/reuse-a"]["branch_disposition"] == "open"
    assert by_branch["feature/reuse-b"]["branch_disposition"] == "open"

import json
from pathlib import Path

from renmark import analytics
from renmark.state.usage import UsageRecord, read_usage

NOW = "2026-08-02T12:00:00Z"


def _usage_ledger(repo: Path) -> Path:
    return repo / ".renmark" / "state" / "usage.jsonl"


def _task_runs_ledger(repo: Path) -> Path:
    return repo / ".renmark" / "analytics" / analytics.TASK_RUNS_LEDGER


def test_usage_record_defaults_and_round_trips_measured_flag(tmp_path: Path) -> None:
    rec = UsageRecord(
        ts="2026-08-02T12:00:00Z",
        run_id="run-1",
        task_id=1,
        model="claude-sonnet",
        prompt_tokens=100,
        completion_tokens=25,
    )
    assert rec.measured is False

    measured = UsageRecord(
        ts="2026-08-02T12:00:00Z",
        run_id="run-2",
        task_id=2,
        model="claude-sonnet",
        prompt_tokens=7,
        completion_tokens=3,
        measured=True,
    )

    ledger = _usage_ledger(tmp_path)
    ledger.parent.mkdir(parents=True, exist_ok=True)
    ledger.write_text(rec.as_jsonl() + "\n" + measured.as_jsonl() + "\n", encoding="utf-8")

    rows = read_usage(tmp_path)

    assert rows[0]["measured"] is False
    assert rows[1]["measured"] is True


def test_record_task_run_persists_measured_flag(tmp_path: Path) -> None:
    analytics.record_task_run(
        tmp_path,
        ts=NOW,
        task_id=1,
        title="measured task",
        executor="codex",
        model="gpt-5",
        provider="openai",
        status="completed",
        total_tokens=42,
        measured=True,
    )
    analytics.record_task_run(
        tmp_path,
        ts=NOW,
        task_id=2,
        title="unmeasured task",
        executor="codex",
        model="gpt-5",
        provider="openai",
        status="completed",
        total_tokens=7,
    )

    rows = analytics.read_jsonl(_task_runs_ledger(tmp_path))

    assert rows[0]["measured"] is True
    assert rows[1]["measured"] is False


def test_aggregate_tasks_counts_measured_only_for_new_metric_and_keeps_existing_totals(
    tmp_path: Path,
) -> None:
    analytics.record_task_run(
        tmp_path,
        ts=NOW,
        task_id=1,
        title="measured task",
        executor="codex",
        model="gpt-5",
        provider="openai",
        status="completed",
        total_tokens=10,
        measured=True,
    )
    analytics.record_task_run(
        tmp_path,
        ts=NOW,
        task_id=2,
        title="unmeasured task",
        executor="codex",
        model="gpt-5",
        provider="openai",
        status="completed",
        total_tokens=20,
    )
    ledger = _task_runs_ledger(tmp_path)
    ledger.parent.mkdir(parents=True, exist_ok=True)
    ledger.write_text(
        ledger.read_text(encoding="utf-8")
        + json.dumps(
            {
                "ts": NOW,
                "task_id": 3,
                "title": "legacy unmeasured task",
                "executor": "codex",
                "model": "gpt-5",
                "provider": "openai",
                "status": "completed",
                "total_tokens": 30,
            },
            separators=(",", ":"),
        )
        + "\n",
        encoding="utf-8",
    )

    summary = analytics.aggregate(tmp_path, now=NOW)
    tasks = summary["tasks"]

    assert tasks["measured_tokens_total"] == 10
    assert tasks["unmeasured_task_count"] == 2
    assert tasks["tokens_by_executor"] == {"codex": 60}
    assert tasks["tokens_by_model"] == {"gpt-5": 60}
    assert tasks["tokens_by_provider"] == {"openai": 60}


def test_aggregate_tasks_tolerates_missing_measured_key_in_task_runs_ledger(tmp_path: Path) -> None:
    ledger = _task_runs_ledger(tmp_path)
    ledger.parent.mkdir(parents=True, exist_ok=True)
    ledger.write_text(
        json.dumps(
            {
                "ts": NOW,
                "task_id": 99,
                "title": "preexisting task row",
                "executor": "codex",
                "model": "gpt-5",
                "provider": "openai",
                "status": "completed",
                "total_tokens": 11,
            },
            separators=(",", ":"),
        )
        + "\n",
        encoding="utf-8",
    )

    summary = analytics.aggregate(tmp_path, now=NOW)
    tasks = summary["tasks"]

    assert tasks["measured_tokens_total"] == 0
    assert tasks["unmeasured_task_count"] == 1
    assert tasks["tokens_by_executor"] == {"codex": 11}
    assert tasks["tokens_by_model"] == {"gpt-5": 11}
    assert tasks["tokens_by_provider"] == {"openai": 11}

"""Unit tests for renmark.heartbeat_checks — proactive heartbeat checkers."""

from __future__ import annotations

import datetime
import json
from pathlib import Path

import pytest

from renmark.heartbeat_checks import (
    CheckResult,
    check_awaiting_loop,
    check_blocked_backlog,
    check_stalled_feature,
    check_stalled_pipeline,
    check_usage_limit_pause,
    run_all_checks,
)


def _now_iso() -> str:
    """Current UTC time in ISO format."""
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _now_iso_minus_hours(hours: float) -> str:
    """UTC time N hours in the past, in ISO format."""
    past = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(
        hours=hours
    )
    return past.isoformat()


class TestCheckUsageLimitPause:
    """Tests for check_usage_limit_pause()."""

    def test_no_paused_file_returns_no_notify(self, tmp_path: Path) -> None:
        """No PAUSED file exists → should_notify=False."""
        result = check_usage_limit_pause(tmp_path, now=_now_iso())
        assert result.check_name == "usage_limit_pause"
        assert result.should_notify is False
        assert result.message == ""

    def test_usage_limit_pause_resume_after_in_future(self, tmp_path: Path) -> None:
        """usage_limit pause, resume_after in future → should_notify=False."""
        state_dir = tmp_path / ".renmark" / "state"
        state_dir.mkdir(parents=True)

        future_resume = datetime.datetime.now(
            datetime.timezone.utc
        ) + datetime.timedelta(hours=2)

        pause_file = state_dir / "PAUSED"
        pause_file.write_text(
            json.dumps(
                {
                    "run_id": "test-run",
                    "plan_path": "test.plan.md",
                    "last_task_index": 0,
                    "reason": "usage limit reached",
                    "ts": _now_iso(),
                    "pause_kind": "usage_limit",
                    "provider": "anthropic",
                    "model": "claude-3-5-sonnet-20241022",
                    "observed_usage": "87% capacity",
                    "provider_reset_at": future_resume.isoformat(),
                    "resume_after": future_resume.isoformat(),
                    "fallback_retry_minutes": 60,
                    "feature": "test-feature",
                    "loop_id": "",
                    "iteration": 0,
                    "max_iterations": 0,
                }
            ),
            encoding="utf-8",
        )

        result = check_usage_limit_pause(tmp_path, now=_now_iso())
        assert result.check_name == "usage_limit_pause"
        assert result.should_notify is False

    def test_usage_limit_pause_resume_after_in_past(self, tmp_path: Path) -> None:
        """usage_limit pause, resume_after in past → should_notify=True."""
        state_dir = tmp_path / ".renmark" / "state"
        state_dir.mkdir(parents=True)

        past_resume = datetime.datetime.now(
            datetime.timezone.utc
        ) - datetime.timedelta(hours=2)

        pause_file = state_dir / "PAUSED"
        pause_file.write_text(
            json.dumps(
                {
                    "run_id": "test-run",
                    "plan_path": "test.plan.md",
                    "last_task_index": 1,
                    "reason": "usage limit reached",
                    "ts": _now_iso(),
                    "pause_kind": "usage_limit",
                    "provider": "anthropic",
                    "model": "claude-3-5-sonnet-20241022",
                    "observed_usage": "95% capacity",
                    "provider_reset_at": past_resume.isoformat(),
                    "resume_after": past_resume.isoformat(),
                    "fallback_retry_minutes": 60,
                    "feature": "important-feature",
                    "loop_id": "loop-001",
                    "iteration": 2,
                    "max_iterations": 5,
                }
            ),
            encoding="utf-8",
        )

        result = check_usage_limit_pause(tmp_path, now=_now_iso())
        assert result.check_name == "usage_limit_pause"
        assert result.should_notify is True
        assert "Usage limit may have cleared" in result.message
        assert "important-feature" in result.message
        assert "loop-001" in result.message
        assert "iter 2/5" in result.message
        assert "renmark-execute --resume" in result.message


class TestCheckStalledFeature:
    """Tests for check_stalled_feature()."""

    def test_no_lifecycle_file_returns_no_notify(self, tmp_path: Path) -> None:
        """No lifecycle.json exists → should_notify=False."""
        result = check_stalled_feature(tmp_path, now=_now_iso())
        assert result.check_name == "stalled_feature"
        assert result.should_notify is False
        assert result.message == ""

    def test_feature_in_terminal_stage_init(self, tmp_path: Path) -> None:
        """Feature in 'init' stage (terminal) → should_notify=False."""
        state_dir = tmp_path / ".renmark" / "state"
        state_dir.mkdir(parents=True)

        lc_file = state_dir / "lifecycle.json"
        lc_file.write_text(
            json.dumps(
                {
                    "feature": "test-feature",
                    "stage": "init",
                    "last_updated": _now_iso_minus_hours(100),
                    "next_recommended": "/renmark:brainstorm",
                    "human_review_required": False,
                    "human_review_completed": False,
                }
            ),
            encoding="utf-8",
        )

        result = check_stalled_feature(tmp_path, now=_now_iso())
        assert result.should_notify is False

    def test_feature_in_terminal_stage_released(self, tmp_path: Path) -> None:
        """Feature in 'released' stage (terminal) → should_notify=False."""
        state_dir = tmp_path / ".renmark" / "state"
        state_dir.mkdir(parents=True)

        lc_file = state_dir / "lifecycle.json"
        lc_file.write_text(
            json.dumps(
                {
                    "feature": "completed-feature",
                    "stage": "released",
                    "last_updated": _now_iso_minus_hours(10),
                    "next_recommended": None,
                    "human_review_required": False,
                    "human_review_completed": False,
                }
            ),
            encoding="utf-8",
        )

        result = check_stalled_feature(tmp_path, now=_now_iso())
        assert result.should_notify is False

    def test_feature_stalled_in_intermediate_stage(self, tmp_path: Path) -> None:
        """Feature stuck in 'plan-validated' stage > stall_hours → should_notify=True."""
        state_dir = tmp_path / ".renmark" / "state"
        state_dir.mkdir(parents=True)

        # Stalled for 5 hours; stall_hours=4 → should trigger
        stalled_time = _now_iso_minus_hours(5.0)

        lc_file = state_dir / "lifecycle.json"
        lc_file.write_text(
            json.dumps(
                {
                    "feature": "stuck-feature",
                    "stage": "plan-validated",
                    "last_updated": stalled_time,
                    "next_recommended": "/renmark:orchestrate",
                    "human_review_required": False,
                    "human_review_completed": False,
                }
            ),
            encoding="utf-8",
        )

        result = check_stalled_feature(tmp_path, now=_now_iso(), stall_hours=4.0)
        assert result.check_name == "stalled_feature"
        assert result.should_notify is True
        assert "stuck-feature" in result.message
        assert "plan-validated" in result.message
        assert "/renmark:orchestrate" in result.message

    def test_feature_awaiting_human_approval_gate(self, tmp_path: Path) -> None:
        """Feature with human_review_required=True and human_review_completed=False → should_notify=True."""
        state_dir = tmp_path / ".renmark" / "state"
        state_dir.mkdir(parents=True)

        lc_file = state_dir / "lifecycle.json"
        lc_file.write_text(
            json.dumps(
                {
                    "feature": "approval-pending",
                    "stage": "created",
                    "last_updated": _now_iso(),
                    "next_recommended": "/renmark:approve",
                    "human_review_required": True,
                    "human_review_completed": False,
                }
            ),
            encoding="utf-8",
        )

        result = check_stalled_feature(tmp_path, now=_now_iso(), stall_hours=4.0)
        assert result.check_name == "stalled_feature"
        assert result.should_notify is True
        assert "awaiting human approval" in result.message
        assert "approval-pending" in result.message
        assert "/renmark:approve" in result.message


class TestCheckStalledPipeline:
    """Tests for check_stalled_pipeline()."""

    def test_no_pipeline_file_returns_no_notify(self, tmp_path: Path) -> None:
        """No pipeline.json exists → should_notify=False."""
        result = check_stalled_pipeline(tmp_path, now=_now_iso())
        assert result.check_name == "stalled_pipeline"
        assert result.should_notify is False
        assert result.message == ""

    def test_pipeline_in_idle_phase_returns_no_notify(self, tmp_path: Path) -> None:
        """Pipeline in 'idle' phase → should_notify=False."""
        state_dir = tmp_path / ".renmark" / "state"
        state_dir.mkdir(parents=True)

        ps_file = state_dir / "pipeline.json"
        ps_file.write_text(
            json.dumps(
                {
                    "current_phase": "idle",
                    "wave_index": 1,
                    "wave_total": 3,
                    "last_updated": _now_iso_minus_hours(10),
                    "tasks_completed": 0,
                }
            ),
            encoding="utf-8",
        )

        result = check_stalled_pipeline(tmp_path, now=_now_iso())
        assert result.should_notify is False

    def test_pipeline_in_orchestrate_not_stalled(self, tmp_path: Path) -> None:
        """Pipeline in 'orchestrate' but updated recently → should_notify=False."""
        state_dir = tmp_path / ".renmark" / "state"
        state_dir.mkdir(parents=True)

        # Updated 1 hour ago; stall_hours=2 → not stalled
        ps_file = state_dir / "pipeline.json"
        ps_file.write_text(
            json.dumps(
                {
                    "current_phase": "orchestrate",
                    "wave_index": 2,
                    "wave_total": 5,
                    "last_updated": _now_iso_minus_hours(1.0),
                    "tasks_completed": 3,
                }
            ),
            encoding="utf-8",
        )

        result = check_stalled_pipeline(tmp_path, now=_now_iso(), stall_hours=2.0)
        assert result.should_notify is False

    def test_pipeline_in_orchestrate_stalled(self, tmp_path: Path) -> None:
        """Pipeline in 'orchestrate' + last_updated > stall_hours → should_notify=True."""
        state_dir = tmp_path / ".renmark" / "state"
        state_dir.mkdir(parents=True)

        # Updated 3 hours ago; stall_hours=2 → stalled
        ps_file = state_dir / "pipeline.json"
        ps_file.write_text(
            json.dumps(
                {
                    "current_phase": "orchestrate",
                    "wave_index": 2,
                    "wave_total": 5,
                    "last_updated": _now_iso_minus_hours(3.0),
                    "tasks_completed": 5,
                }
            ),
            encoding="utf-8",
        )

        result = check_stalled_pipeline(tmp_path, now=_now_iso(), stall_hours=2.0)
        assert result.check_name == "stalled_pipeline"
        assert result.should_notify is True
        assert "wave 2/5" in result.message
        assert "has not advanced" in result.message
        assert "/renmark:resume" in result.message


class TestCheckBlockedBacklog:
    """Tests for check_blocked_backlog()."""

    def test_no_backlog_directory_returns_no_notify(self, tmp_path: Path) -> None:
        """No backlog directory exists → should_notify=False."""
        result = check_blocked_backlog(tmp_path, now=_now_iso())
        assert result.check_name == "blocked_backlog"
        assert result.should_notify is False
        assert result.message == ""

    def test_backlog_with_only_completed_items(self, tmp_path: Path) -> None:
        """Backlog items with status='completed' only → should_notify=False."""
        backlog_dir = tmp_path / ".renmark" / "state" / "backlog"
        backlog_dir.mkdir(parents=True)

        item_file = backlog_dir / "BL-0001.json"
        item_file.write_text(
            json.dumps(
                {
                    "id": "BL-0001",
                    "title": "Completed task",
                    "status": "completed",
                    "disposition": "",
                    "updated_at": _now_iso_minus_hours(24),
                }
            ),
            encoding="utf-8",
        )

        result = check_blocked_backlog(tmp_path, now=_now_iso())
        assert result.should_notify is False

    def test_backlog_item_in_progress_not_stalled(self, tmp_path: Path) -> None:
        """Backlog item 'in progress' but updated recently → should_notify=False."""
        backlog_dir = tmp_path / ".renmark" / "state" / "backlog"
        backlog_dir.mkdir(parents=True)

        item_file = backlog_dir / "BL-0002.json"
        item_file.write_text(
            json.dumps(
                {
                    "id": "BL-0002",
                    "title": "Active task",
                    "status": "in progress",
                    "disposition": "",
                    "updated_at": _now_iso_minus_hours(12),
                }
            ),
            encoding="utf-8",
        )

        # stall_hours=48 (default) → not stalled at 12 hours
        result = check_blocked_backlog(tmp_path, now=_now_iso(), stall_hours=48.0)
        assert result.should_notify is False

    def test_backlog_item_in_progress_stalled(self, tmp_path: Path) -> None:
        """Backlog item 'in progress' + updated > stall_hours → should_notify=True."""
        backlog_dir = tmp_path / ".renmark" / "state" / "backlog"
        backlog_dir.mkdir(parents=True)

        # Updated 60 hours ago; stall_hours=48 → stalled
        item_file = backlog_dir / "BL-0003.json"
        item_file.write_text(
            json.dumps(
                {
                    "id": "BL-0003",
                    "title": "Stuck backlog item",
                    "status": "in progress",
                    "disposition": "",
                    "updated_at": _now_iso_minus_hours(60),
                }
            ),
            encoding="utf-8",
        )

        result = check_blocked_backlog(tmp_path, now=_now_iso(), stall_hours=48.0)
        assert result.check_name == "blocked_backlog"
        assert result.should_notify is True
        assert "1 backlog item(s)" in result.message
        assert "BL-0003" in result.message
        assert "Stuck backlog item" in result.message
        assert "/renmark:backlog" in result.message

    def test_backlog_multiple_stuck_items_reports_oldest(self, tmp_path: Path) -> None:
        """Multiple stuck items → report oldest one."""
        backlog_dir = tmp_path / ".renmark" / "state" / "backlog"
        backlog_dir.mkdir(parents=True)

        # Oldest: 100 hours ago
        item1 = backlog_dir / "BL-0001.json"
        item1.write_text(
            json.dumps(
                {
                    "id": "BL-0001",
                    "title": "Oldest stuck",
                    "status": "needs approval",
                    "disposition": "",
                    "updated_at": _now_iso_minus_hours(100),
                }
            ),
            encoding="utf-8",
        )

        # Newer stuck: 60 hours ago
        item2 = backlog_dir / "BL-0002.json"
        item2.write_text(
            json.dumps(
                {
                    "id": "BL-0002",
                    "title": "Newer stuck",
                    "status": "blocked",
                    "disposition": "",
                    "updated_at": _now_iso_minus_hours(60),
                }
            ),
            encoding="utf-8",
        )

        result = check_blocked_backlog(tmp_path, now=_now_iso(), stall_hours=48.0)
        assert result.should_notify is True
        assert "2 backlog item(s)" in result.message
        # Should mention the oldest one
        assert "BL-0001" in result.message
        assert "Oldest stuck" in result.message

    def test_backlog_item_with_disposition_ignored(self, tmp_path: Path) -> None:
        """Backlog item with disposition set → ignored even if old."""
        backlog_dir = tmp_path / ".renmark" / "state" / "backlog"
        backlog_dir.mkdir(parents=True)

        item_file = backlog_dir / "BL-0010.json"
        item_file.write_text(
            json.dumps(
                {
                    "id": "BL-0010",
                    "title": "Disposed item",
                    "status": "in progress",
                    "disposition": "closed",  # Has disposition → skip
                    "updated_at": _now_iso_minus_hours(100),
                }
            ),
            encoding="utf-8",
        )

        result = check_blocked_backlog(tmp_path, now=_now_iso(), stall_hours=48.0)
        assert result.should_notify is False


class TestCheckAwaitingLoop:
    """Tests for check_awaiting_loop()."""

    def test_no_loops_directory_returns_no_notify(self, tmp_path: Path) -> None:
        """No loops directory exists → should_notify=False."""
        result = check_awaiting_loop(tmp_path)
        assert result.check_name == "awaiting_loop"
        assert result.should_notify is False
        assert result.message == ""

    def test_loop_with_status_done(self, tmp_path: Path) -> None:
        """Loop with status='done' → should_notify=False."""
        loops_dir = tmp_path / ".renmark" / "loops" / "loop-001"
        loops_dir.mkdir(parents=True)

        loop_file = loops_dir / "loop.json"
        loop_file.write_text(
            json.dumps(
                {
                    "id": "loop-001",
                    "status": "done",
                    "pending_step": "",
                    "iteration": 5,
                    "max_iterations": 5,
                }
            ),
            encoding="utf-8",
        )

        result = check_awaiting_loop(tmp_path)
        assert result.should_notify is False

    def test_loop_with_status_awaiting_approval(self, tmp_path: Path) -> None:
        """Loop with status='awaiting-approval' → should_notify=True."""
        loops_dir = tmp_path / ".renmark" / "loops" / "loop-feedback-001"
        loops_dir.mkdir(parents=True)

        loop_file = loops_dir / "loop.json"
        loop_file.write_text(
            json.dumps(
                {
                    "id": "loop-feedback-001",
                    "status": "awaiting-approval",
                    "pending_step": "prd_approval",
                    "iteration": 2,
                    "max_iterations": 10,
                }
            ),
            encoding="utf-8",
        )

        result = check_awaiting_loop(tmp_path)
        assert result.check_name == "awaiting_loop"
        assert result.should_notify is True
        assert "loop-feedback-001" in result.message
        assert "awaiting approval" in result.message
        assert "prd_approval" in result.message
        assert "/renmark:approve" in result.message

    def test_loop_with_status_stalled(self, tmp_path: Path) -> None:
        """Loop with status='stalled' → should_notify=True."""
        loops_dir = tmp_path / ".renmark" / "loops" / "loop-issue-002"
        loops_dir.mkdir(parents=True)

        loop_file = loops_dir / "loop.json"
        loop_file.write_text(
            json.dumps(
                {
                    "id": "loop-issue-002",
                    "status": "stalled",
                    "pending_step": "",
                    "iteration": 3,
                    "max_iterations": 5,
                }
            ),
            encoding="utf-8",
        )

        result = check_awaiting_loop(tmp_path)
        assert result.should_notify is True
        assert "loop-issue-002" in result.message

    def test_loop_awaiting_approval_multiple_loops_reports_first(
        self, tmp_path: Path
    ) -> None:
        """Multiple loops awaiting approval → report first one found."""
        loops_dir = tmp_path / ".renmark" / "loops"

        # Loop 1: awaiting-approval
        loop1_dir = loops_dir / "loop-001"
        loop1_dir.mkdir(parents=True)
        loop1_file = loop1_dir / "loop.json"
        loop1_file.write_text(
            json.dumps(
                {
                    "id": "loop-001",
                    "status": "awaiting-approval",
                    "pending_step": "step1",
                }
            ),
            encoding="utf-8",
        )

        # Loop 2: done (should not be reported)
        loop2_dir = loops_dir / "loop-002"
        loop2_dir.mkdir(parents=True)
        loop2_file = loop2_dir / "loop.json"
        loop2_file.write_text(
            json.dumps({"id": "loop-002", "status": "done", "pending_step": ""})
        ),

        result = check_awaiting_loop(tmp_path)
        assert result.should_notify is True
        assert "loop-001" in result.message


class TestRunAllChecks:
    """Tests for run_all_checks()."""

    def test_nothing_to_notify_returns_empty_list(self, tmp_path: Path) -> None:
        """No checks fire → returns empty list."""
        result = run_all_checks(tmp_path, now=_now_iso())
        assert isinstance(result, list)
        assert len(result) == 0

    def test_single_check_fires_returns_list_of_one(self, tmp_path: Path) -> None:
        """One check fires → returns list of length 1."""
        # Create a stalled feature
        state_dir = tmp_path / ".renmark" / "state"
        state_dir.mkdir(parents=True)

        lc_file = state_dir / "lifecycle.json"
        lc_file.write_text(
            json.dumps(
                {
                    "feature": "test-feature",
                    "stage": "plan-validated",
                    "last_updated": _now_iso_minus_hours(5.0),
                    "next_recommended": "/renmark:orchestrate",
                    "human_review_required": False,
                    "human_review_completed": False,
                }
            ),
            encoding="utf-8",
        )

        result = run_all_checks(tmp_path, now=_now_iso())
        assert len(result) == 1
        assert result[0].check_name == "stalled_feature"
        assert result[0].should_notify is True

    def test_multiple_checks_fire_returns_all(self, tmp_path: Path) -> None:
        """Multiple checks fire → returns all of them."""
        state_dir = tmp_path / ".renmark" / "state"
        state_dir.mkdir(parents=True)

        # Stalled feature
        lc_file = state_dir / "lifecycle.json"
        lc_file.write_text(
            json.dumps(
                {
                    "feature": "test-feature",
                    "stage": "plan-validated",
                    "last_updated": _now_iso_minus_hours(5.0),
                    "next_recommended": "/renmark:orchestrate",
                    "human_review_required": False,
                    "human_review_completed": False,
                }
            ),
            encoding="utf-8",
        )

        # Stalled pipeline
        ps_file = state_dir / "pipeline.json"
        ps_file.write_text(
            json.dumps(
                {
                    "current_phase": "orchestrate",
                    "wave_index": 1,
                    "wave_total": 3,
                    "last_updated": _now_iso_minus_hours(3.0),
                    "tasks_completed": 0,
                }
            ),
            encoding="utf-8",
        )

        result = run_all_checks(tmp_path, now=_now_iso())
        assert len(result) == 2
        check_names = {c.check_name for c in result}
        assert check_names == {"stalled_feature", "stalled_pipeline"}

    def test_run_all_checks_does_not_raise_on_missing_files(
        self, tmp_path: Path
    ) -> None:
        """run_all_checks does not raise even if all state files missing."""
        # Empty repo directory
        result = run_all_checks(tmp_path, now=_now_iso())
        assert isinstance(result, list)
        assert len(result) == 0

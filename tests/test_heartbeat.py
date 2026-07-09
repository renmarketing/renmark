"""Unit tests for renmark.heartbeat — proactive usage-limit pause checker."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from renmark import heartbeat
from renmark.state.pause import usage_limit_pause, write_pause


class TestCheck:
    """Tests for heartbeat.check()."""

    def test_no_paused_file_returns_ok(self, tmp_path: Path) -> None:
        """No PAUSED file exists → should_notify=False, message == HEARTBEAT_OK."""
        result = heartbeat.check(tmp_path, now="2026-07-09T12:00:00Z")
        assert result.should_notify is False
        assert result.message == heartbeat.HEARTBEAT_OK
        assert result.pause_state is None

    def test_pause_kind_not_usage_limit_returns_ok(self, tmp_path: Path) -> None:
        """pause_kind != 'usage_limit' → should_notify=False, message == HEARTBEAT_OK."""
        # Write a manual pause (no usage_limit)
        state_dir = tmp_path / ".renmark" / "state"
        state_dir.mkdir(parents=True)

        # Write a pause with a different kind (empty pause_kind defaults to "")
        pause_file = state_dir / "PAUSED"
        pause_file.write_text(
            """{
                "run_id": "test-run",
                "plan_path": "test.plan.md",
                "last_task_index": 0,
                "reason": "manual pause",
                "ts": "2026-07-09T10:00:00Z",
                "pause_kind": "manual"
            }""",
            encoding="utf-8",
        )

        result = heartbeat.check(tmp_path, now="2026-07-09T12:00:00Z")
        assert result.should_notify is False
        assert result.message == heartbeat.HEARTBEAT_OK
        assert result.pause_state is not None
        assert result.pause_state.pause_kind == "manual"

    def test_usage_limit_resume_after_in_future_silent(self, tmp_path: Path) -> None:
        """usage_limit pause, resume_after in future (now < resume_after) → should_notify=False."""
        # Create a usage_limit pause with resume_after in the future
        pause = usage_limit_pause(
            run_id="test-run",
            plan_path="test.plan.md",
            last_task_index=0,
            ts="2026-07-09T10:00:00Z",
            provider="anthropic",
            model="claude-3-5-sonnet-20241022",
            observed_usage="87% capacity",
            provider_reset_at="2026-07-10T00:00:00Z",
            resume_after="2026-07-10T10:00:00Z",  # In the future
            feature="test-feature",
            loop_id="loop-1",
            iteration=1,
            max_iterations=3,
        )

        state_dir = tmp_path / ".renmark" / "state"
        state_dir.mkdir(parents=True)
        write_pause(tmp_path, pause)

        # Now is before resume_after
        result = heartbeat.check(tmp_path, now="2026-07-10T08:00:00Z")
        assert result.should_notify is False
        assert result.message == heartbeat.HEARTBEAT_OK
        assert result.pause_state is not None
        assert result.pause_state.pause_kind == "usage_limit"

    def test_usage_limit_resume_after_in_past_notifies(self, tmp_path: Path) -> None:
        """usage_limit pause, resume_after in past (now > resume_after) → should_notify=True."""
        pause = usage_limit_pause(
            run_id="test-run",
            plan_path="test.plan.md",
            last_task_index=2,
            ts="2026-07-09T10:00:00Z",
            provider="anthropic",
            model="claude-3-5-sonnet-20241022",
            observed_usage="90% capacity",
            provider_reset_at="2026-07-10T00:00:00Z",
            resume_after="2026-07-10T06:00:00Z",  # In the past
            feature="important-feature",
            loop_id="loop-2",
            iteration=2,
            max_iterations=5,
        )

        state_dir = tmp_path / ".renmark" / "state"
        state_dir.mkdir(parents=True)
        write_pause(tmp_path, pause)

        # Now is after resume_after
        result = heartbeat.check(tmp_path, now="2026-07-10T12:00:00Z")
        assert result.should_notify is True
        assert "Usage limit may have cleared." in result.message
        assert "renmark-execute --resume" in result.message
        assert "important-feature" in result.message
        assert "loop-2" in result.message
        assert result.pause_state is not None

    def test_usage_limit_resume_after_empty_notifies(self, tmp_path: Path) -> None:
        """usage_limit pause, resume_after empty → should_notify=True.

        Note: write_pause validates and prevents empty resume_after, so we write
        the JSON directly to test the heartbeat.check() defensive handling.
        """
        state_dir = tmp_path / ".renmark" / "state"
        state_dir.mkdir(parents=True)

        # Write a usage_limit pause with empty resume_after directly (bypassing validation)
        pause_file = state_dir / "PAUSED"
        pause_file.write_text(
            """{
                "run_id": "test-run",
                "plan_path": "test.plan.md",
                "last_task_index": 1,
                "reason": "usage limit reached",
                "ts": "2026-07-09T10:00:00Z",
                "pause_kind": "usage_limit",
                "provider": "anthropic",
                "model": "claude-3-5-sonnet-20241022",
                "observed_usage": "95% capacity",
                "provider_reset_at": "2026-07-10T00:00:00Z",
                "resume_after": "",
                "fallback_retry_minutes": 60,
                "feature": "another-feature",
                "loop_id": "",
                "iteration": 0,
                "max_iterations": 0
            }""",
            encoding="utf-8",
        )

        result = heartbeat.check(tmp_path, now="2026-07-10T12:00:00Z")
        assert result.should_notify is True
        assert "Usage limit may have cleared." in result.message
        assert "renmark-execute --resume" in result.message
        assert "another-feature" in result.message

    def test_check_ts_field_populated(self, tmp_path: Path) -> None:
        """HeartbeatResult.check_ts field is populated with the 'now' parameter."""
        result = heartbeat.check(tmp_path, now="2026-07-09T14:30:45Z")
        assert result.check_ts == "2026-07-09T14:30:45Z"

    def test_message_excludes_empty_context_fields(self, tmp_path: Path) -> None:
        """Pause message excludes feature/loop_id when empty."""
        pause = usage_limit_pause(
            run_id="test-run",
            plan_path="test.plan.md",
            last_task_index=0,
            ts="2026-07-09T10:00:00Z",
            provider="anthropic",
            model="claude-3-5-sonnet-20241022",
            observed_usage="usage at cap",
            provider_reset_at="2026-07-10T00:00:00Z",
            resume_after="2026-07-09T11:00:00Z",
            feature="",  # Empty
            loop_id="",  # Empty
        )

        state_dir = tmp_path / ".renmark" / "state"
        state_dir.mkdir(parents=True)
        write_pause(tmp_path, pause)

        result = heartbeat.check(tmp_path, now="2026-07-10T12:00:00Z")
        assert result.should_notify is True
        lines = result.message.split("\n")
        # Should have 2 lines (header + resume instruction), not 4
        assert len(lines) == 2
        assert "Feature:" not in result.message
        assert "Loop:" not in result.message


class TestEmitCron:
    """Tests for heartbeat.emit_cron()."""

    def test_emit_cron_default_interval(self, tmp_path: Path) -> None:
        """emit_cron with default interval returns string with */30."""
        output = heartbeat.emit_cron(tmp_path)
        assert "renmark-execute --heartbeat" in output
        assert "*/30" in output
        assert f"cd {tmp_path}" in output

    def test_emit_cron_custom_interval_60(self, tmp_path: Path) -> None:
        """emit_cron with interval_minutes=60 returns string with */60."""
        output = heartbeat.emit_cron(tmp_path, interval_minutes=60)
        assert "renmark-execute --heartbeat" in output
        assert "*/60" in output
        assert "60 minutes" in output or "60" in output

    def test_emit_cron_custom_interval_1(self, tmp_path: Path) -> None:
        """emit_cron with interval_minutes=1 returns string with * (every minute)."""
        output = heartbeat.emit_cron(tmp_path, interval_minutes=1)
        assert "renmark-execute --heartbeat" in output
        # interval=1 should produce "*" (not "*/1")
        assert "* * * * *" in output

    def test_emit_cron_contains_auto_resume_variant(self, tmp_path: Path) -> None:
        """emit_cron output includes both PRIMARY and OPTIONAL (auto-resume) variants."""
        output = heartbeat.emit_cron(tmp_path)
        assert "PRIMARY" in output
        assert "OPTIONAL" in output
        assert "--heartbeat --auto-resume" in output

    def test_emit_cron_contains_windows_task_scheduler_instructions(self, tmp_path: Path) -> None:
        """emit_cron output includes Windows Task Scheduler PowerShell example."""
        output = heartbeat.emit_cron(tmp_path)
        assert "Windows Task Scheduler" in output
        assert "New-ScheduledTaskAction" in output
        assert "New-ScheduledTaskTrigger" in output
        assert "Register-ScheduledTask" in output

    def test_emit_cron_is_pure_string_no_side_effects(self, tmp_path: Path) -> None:
        """emit_cron returns a string and writes nothing."""
        initial_files = set((tmp_path / ".renmark" / "state").glob("*")) if (tmp_path / ".renmark" / "state").exists() else set()

        output = heartbeat.emit_cron(tmp_path)

        # No files should have been written
        final_files = set((tmp_path / ".renmark" / "state").glob("*")) if (tmp_path / ".renmark" / "state").exists() else set()
        assert final_files == initial_files
        assert isinstance(output, str)


class TestAutoResume:
    """Tests for heartbeat.auto_resume()."""

    def test_auto_resume_calls_subprocess_with_correct_args(self, tmp_path: Path) -> None:
        """auto_resume invokes subprocess.run with ['renmark-execute', '--resume']."""
        with patch("renmark.heartbeat.subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0

            exit_code = heartbeat.auto_resume(tmp_path)

            # Verify subprocess.run was called with the right command
            mock_run.assert_called_once()
            call_args = mock_run.call_args
            assert call_args[0][0] == ["renmark-execute", "--resume"]
            assert call_args[1]["cwd"] == tmp_path

    def test_auto_resume_returns_exit_code_zero(self, tmp_path: Path) -> None:
        """auto_resume returns the subprocess exit code (success case)."""
        with patch("renmark.heartbeat.subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0

            exit_code = heartbeat.auto_resume(tmp_path)
            assert exit_code == 0

    def test_auto_resume_returns_exit_code_nonzero(self, tmp_path: Path) -> None:
        """auto_resume returns a non-zero exit code when subprocess fails."""
        with patch("renmark.heartbeat.subprocess.run") as mock_run:
            mock_run.return_value.returncode = 1

            exit_code = heartbeat.auto_resume(tmp_path)
            assert exit_code == 1

    def test_auto_resume_converts_str_to_path(self, tmp_path: Path) -> None:
        """auto_resume accepts str path and converts to Path for cwd."""
        repo_str = str(tmp_path)

        with patch("renmark.heartbeat.subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0

            exit_code = heartbeat.auto_resume(repo_str)

            call_args = mock_run.call_args
            # cwd should be a Path object
            assert isinstance(call_args[1]["cwd"], Path)
            assert call_args[1]["cwd"] == tmp_path

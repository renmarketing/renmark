"""Unit tests for renmark.state log helpers."""
from __future__ import annotations

import time
from pathlib import Path

from renmark import state


def test_logs_dir_created(tmp_path: Path) -> None:
    d = state.logs_dir(tmp_path)
    assert d == tmp_path / ".renmark" / "logs"
    assert d.is_dir()


def test_open_log_creates_file_with_header(tmp_path: Path) -> None:
    p = state.open_log(tmp_path, "orchestrate", run_id="20260512-100000-abcd")
    assert p.is_file()
    text = p.read_text()
    assert "command: orchestrate" in text
    assert "run_id: 20260512-100000-abcd" in text
    assert "started:" in text


def test_open_log_sanitizes_command_name(tmp_path: Path) -> None:
    p = state.open_log(tmp_path, "weird/command name!", run_id="rid")
    # Sanitized: only alnum, -, _ kept.
    assert "weird_command_name_" in p.name


def test_append_log_adds_timestamp_prefix(tmp_path: Path) -> None:
    p = state.open_log(tmp_path, "test", run_id="rid")
    state.append_log(p, "first line", "second line")
    text = p.read_text()
    assert "first line" in text
    assert "second line" in text
    # Each appended line should start with [<timestamp>]
    appended_lines = [
        line for line in text.splitlines()
        if line.startswith("[") and ("first line" in line or "second line" in line)
    ]
    assert len(appended_lines) == 2


def test_recent_logs_sorted_newest_first(tmp_path: Path) -> None:
    p1 = state.open_log(tmp_path, "a", run_id="r1")
    time.sleep(0.02)
    p2 = state.open_log(tmp_path, "b", run_id="r2")
    items = state.recent_logs(tmp_path, n=10)
    assert len(items) == 2
    # Newest (p2 / b) should be first.
    assert items[0]["name"].startswith("b-")
    assert items[1]["name"].startswith("a-")


def test_recent_logs_limit(tmp_path: Path) -> None:
    for i in range(5):
        state.open_log(tmp_path, f"cmd{i}", run_id=f"r{i}")
    items = state.recent_logs(tmp_path, n=3)
    assert len(items) == 3

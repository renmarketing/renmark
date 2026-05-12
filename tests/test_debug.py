"""Unit tests for renmark.debug session helpers."""
from __future__ import annotations

from pathlib import Path

from renmark import debug


def test_new_session_creates_skeleton(tmp_path: Path) -> None:
    s = debug.new_session(tmp_path, "GET /healthz returns 500")
    assert s.path.is_file()
    text = s.path.read_text()
    assert "## Symptom" in text
    assert "GET /healthz returns 500" in text
    assert "## Hypotheses" in text
    assert "## Investigation log" in text
    assert "## Root cause" in text


def test_add_hypothesis_inserts_under_header(tmp_path: Path) -> None:
    s = debug.new_session(tmp_path, "x")
    debug.add_hypothesis(s, 1, "Missing import", "high")
    debug.add_hypothesis(s, 2, "Wrong port", "low")
    text = s.path.read_text()
    assert "Missing import" in text
    assert "Wrong port" in text


def test_log_investigation_appends(tmp_path: Path) -> None:
    s = debug.new_session(tmp_path, "x")
    debug.log_investigation(
        s, hypothesis="Missing import", inspector="nim",
        finding="no `import foo` in src/", rules_out=False,
    )
    debug.log_investigation(
        s, hypothesis="Wrong port", inspector="codex",
        finding="config says 8000 but server binds 8001", rules_out=True,
    )
    text = s.path.read_text()
    assert "**Missing import** (via nim)" in text
    assert "RULES OUT: config says 8000" in text


def test_set_root_cause_replaces_placeholder(tmp_path: Path) -> None:
    s = debug.new_session(tmp_path, "x")
    debug.set_root_cause(s, "Server binds wrong port due to PORT env var typo")
    text = s.path.read_text()
    assert "Server binds wrong port" in text
    assert "_(unknown)_" not in text


def test_close_session_writes_to_bugs_md(tmp_path: Path) -> None:
    s = debug.new_session(tmp_path, "x")
    debug.close_session(
        s, tmp_path,
        title="PORT env typo", severity="major",
        symptom="server binds wrong port",
        root_cause="config file used PROT instead of PORT",
        fix="renamed env var to PORT; commit abc123",
        lesson="grep for typos in env var names before deploying",
    )
    bugs = (tmp_path / ".renmark" / "memory" / "bugs.md").read_text()
    assert "PORT env typo" in bugs
    assert "**Severity:** major" in bugs
    learnings = (tmp_path / ".renmark" / "memory" / "learnings.md").read_text()
    assert "grep for typos" in learnings


def test_latest_session_returns_newest(tmp_path: Path) -> None:
    import time
    a = debug.new_session(tmp_path, "first")
    time.sleep(0.02)
    b = debug.new_session(tmp_path, "second")
    latest = debug.latest_session(tmp_path)
    assert latest is not None
    assert latest.session_id == b.session_id


def test_suggest_inspector_routing() -> None:
    assert debug.suggest_inspector("grep") == "nim"
    assert debug.suggest_inspector("file-read") == "nim"
    assert debug.suggest_inspector("multi-file-trace") == "codex"
    assert debug.suggest_inspector("reasoning") == "opus"
    assert debug.suggest_inspector("race-condition") == "opus"
    # Unknown defaults to codex.
    assert debug.suggest_inspector("ESP32-debug") == "codex"

"""Unit tests for renmark.verifier."""

from __future__ import annotations

from pathlib import Path

from renmark.verifier import run_verifier


def test_pass(tmp_path: Path) -> None:
    res = run_verifier("true", cwd=tmp_path)
    assert res.ok
    assert res.exit_code == 0


def test_fail_captures_stderr(tmp_path: Path) -> None:
    res = run_verifier("echo boom >&2; exit 1", cwd=tmp_path)
    assert not res.ok
    assert res.exit_code == 1
    assert "boom" in res.output
    assert "boom" in res.tail


def test_timeout(tmp_path: Path) -> None:
    res = run_verifier("sleep 5", cwd=tmp_path, timeout_s=1)
    assert not res.ok
    assert res.timed_out is True
    assert res.exit_code == 124
    assert "timed out" in res.output


def test_tail_truncation(tmp_path: Path) -> None:
    res = run_verifier(
        'for i in $(seq 1 200); do echo "line $i"; done; exit 1',
        cwd=tmp_path,
        tail_lines=10,
    )
    assert res.exit_code == 1
    assert res.tail.count("\n") <= 10
    assert "line 200" in res.tail
    assert "line 1\n" not in res.tail  # truncated


def test_empty_command(tmp_path: Path) -> None:
    res = run_verifier("   ", cwd=tmp_path)
    assert res.exit_code == 2
    assert "empty" in res.output

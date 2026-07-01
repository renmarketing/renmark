"""
---
artifact_type: task_output
schema_version: 1
created_at: 2026-07-01T00:00:00-04:00
source_sha: ecd28f1
related_plan: null
generator: codex
completion_state: complete
confidence: high
validation_status: unvalidated
retry_count: 0
parser_success: true
schema_compliance: true
dependency_refs:
  - renmark/cli/_engine.py
  - renmark/mode.py
---
Pytest CLI coverage for the persisted operating-mode flags on ``python -m
renmark``. The tests invoke the public CLI with ``--repo <tmp_path>`` and
assert on exit codes, stdout/stderr, and the mode state file written under the
temporary repo root.

## Summary
- Verifies ``--set-mode conductor`` persists state and ``--get-mode`` returns it.
- Verifies ``--set-mode orchestrator`` persists state and ``--get-mode`` returns it.
- Confirms ``--clear-mode`` removes persisted state and subsequent reads return ``unset``.
- Covers ``--get-mode`` when nothing is set yet.
- Asserts invalid ``--set-mode bogus`` exits via argparse with code ``2`` and preserves state.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _mode_path(repo: Path) -> Path:
    return repo / ".renmark" / "state" / "mode.json"


def _run_cli(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "renmark", "--repo", str(repo), *args],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )


def test_set_mode_conductor_then_get_mode(tmp_path: Path) -> None:
    set_result = _run_cli(tmp_path, "--set-mode", "conductor")
    assert set_result.returncode == 0
    assert "operating mode set to conductor" in set_result.stdout

    get_result = _run_cli(tmp_path, "--get-mode")
    assert get_result.returncode == 0
    assert get_result.stdout.strip() == "conductor"
    assert _mode_path(tmp_path).exists()


def test_set_mode_orchestrator_then_get_mode(tmp_path: Path) -> None:
    set_result = _run_cli(tmp_path, "--set-mode", "orchestrator")
    assert set_result.returncode == 0
    assert "operating mode set to orchestrator" in set_result.stdout

    get_result = _run_cli(tmp_path, "--get-mode")
    assert get_result.returncode == 0
    assert get_result.stdout.strip() == "orchestrator"
    assert _mode_path(tmp_path).exists()


def test_clear_mode_then_get_mode_returns_unset(tmp_path: Path) -> None:
    seed_result = _run_cli(tmp_path, "--set-mode", "conductor")
    assert seed_result.returncode == 0
    assert _mode_path(tmp_path).exists()

    clear_result = _run_cli(tmp_path, "--clear-mode")
    assert clear_result.returncode == 0
    assert "operating mode cleared" in clear_result.stdout

    get_result = _run_cli(tmp_path, "--get-mode")
    assert get_result.returncode == 0
    assert get_result.stdout.strip() == "unset"


def test_get_mode_with_nothing_set_returns_unset(tmp_path: Path) -> None:
    result = _run_cli(tmp_path, "--get-mode")
    assert result.returncode == 0
    assert result.stdout.strip() == "unset"
    assert not _mode_path(tmp_path).exists()


def test_set_mode_bogus_exits_2_and_writes_no_state(tmp_path: Path) -> None:
    result = _run_cli(tmp_path, "--set-mode", "bogus")
    assert result.returncode == 2
    assert "invalid choice" in result.stderr

    get_result = _run_cli(tmp_path, "--get-mode")
    assert get_result.returncode == 0
    assert get_result.stdout.strip() == "unset"
    assert not _mode_path(tmp_path).exists()


def test_set_mode_bogus_preserves_prior_value(tmp_path: Path) -> None:
    seed_result = _run_cli(tmp_path, "--set-mode", "conductor")
    assert seed_result.returncode == 0
    before = _mode_path(tmp_path).read_text(encoding="utf-8")

    result = _run_cli(tmp_path, "--set-mode", "bogus")
    assert result.returncode == 2
    assert "invalid choice" in result.stderr

    after = _mode_path(tmp_path).read_text(encoding="utf-8")
    assert after == before

    get_result = _run_cli(tmp_path, "--get-mode")
    assert get_result.returncode == 0
    assert get_result.stdout.strip() == "conductor"

"""End-to-end: when codex CLI is absent, an `executor: codex` task should
NOT crash the dispatch. Either the orchestrator surfaces a clean error,
or the executor falls back to a sonnet-style runner.

This test stubs $PATH so codex is unfindable, then exercises the dispatch
path that would normally shell out."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def test_renmark_execute_runs_without_codex_on_path(repo_root: Path, tmp_path: Path):
    """`renmark-execute --help` must work even when codex CLI is unfindable.
    The CLI is the entrypoint to Codex tasks — it should be robust to codex
    being absent on the host."""
    fake_path = tmp_path / "empty-bin"
    fake_path.mkdir()
    # PATH contains ONLY the empty dir + python's dir (so we can find python).
    env = os.environ.copy()
    env["PATH"] = f"{fake_path}:{Path(sys.executable).parent}"
    env["PYTHONPATH"] = str(repo_root)

    result = subprocess.run(
        [sys.executable, "-m", "renmark", "--help"],
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
    )
    # Help should succeed regardless of codex availability.
    assert result.returncode == 0, (
        f"renmark --help failed without codex on PATH:\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )


def test_codex_missing_emits_diagnostic(repo_root: Path, tmp_path: Path):
    """When user actually tries to invoke a codex task and codex is gone,
    the failure should be a clear diagnostic, not a Python traceback."""
    # Write a tiny task spec.
    task_path = tmp_path / "task.json"
    task_path.write_text(
        '{"task_spec": "do x", "required_files": [], '
        '"upstream_artifact_pointers": [], '
        '"dependency_summaries": [], '
        '"verifier_expectations": ""}'
    )
    out_path = tmp_path / "out.json"

    fake_path = tmp_path / "empty-bin"
    fake_path.mkdir()
    env = os.environ.copy()
    env["PATH"] = f"{fake_path}:{Path(sys.executable).parent}"
    env["PYTHONPATH"] = str(repo_root)

    result = subprocess.run(
        [sys.executable, "-m", "renmark", "--task", str(task_path), "--output", str(out_path)],
        env=env,
        capture_output=True,
        text=True,
        timeout=15,
    )
    # Acceptable outcomes:
    #   exit 127 (executable missing)
    #   exit 1 with stderr message containing "codex"
    #   exit 0 with output JSON noting fallback
    if result.returncode == 127:
        return  # explicit "command not found" signal
    if result.returncode == 0 and out_path.exists():
        import json

        out = json.loads(out_path.read_text())
        # Should at minimum carry a status field even if fallback.
        assert "status" in out
        return
    # Otherwise must mention codex in diagnostic.
    combined = result.stdout + result.stderr
    assert "codex" in combined.lower() or "executable" in combined.lower(), (
        f"unclear failure mode (exit {result.returncode}):\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )

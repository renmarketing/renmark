"""Tests for the audit fixes in renmark.cli._engine and renmark.providers.codex:

1. Budget/deadline exhaustion is an honest FAIL (pause + non-zero exit + full
   skipped list), never a silent "All tasks completed." exit 0.
2. Parallel codex change-detection uses a pre/post delta and excludes sibling
   wave-targets, so concurrent in-flight files never look out-of-lane.
3. Mode-A failed-task rollback deletes an UNTRACKED target (checkout can't
   restore it) instead of silently leaving the rejected artifact on disk.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from renmark.cli import _engine
from renmark.providers import codex as codex_provider

# ── helpers ───────────────────────────────────────────────────────────────────


def _init_repo(path: Path) -> None:
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=path, check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.name", "t"], check=True)
    (path / "seed.txt").write_text("seed")
    subprocess.run(["git", "-C", str(path), "add", "seed.txt"], check=True)
    subprocess.run(["git", "-C", str(path), "commit", "-q", "-m", "init"], check=True)


def _write_plan(path: Path, n_tasks: int) -> Path:
    """A plan with N serial tasks (each its own wave)."""
    blocks = []
    for i in range(1, n_tasks + 1):
        blocks.append(
            f"### Task {i}: task {i}\n"
            f"- **mode:** A\n"
            f"- **target:** out/file{i}.txt\n"
            f"- **context_files:** []\n"
            f"- **verifier:** true\n"
            f"- **verifier_timeout_s:** 5\n"
            f"- **spec:**\n"
            f"  make file {i}\n"
        )
    p = path / "plan.md"
    p.write_text("\n".join(blocks))
    return p


# ── Task 1: budget / deadline honesty ──────────────────────────────────────────


def test_deadline_exhaustion_pauses_and_exits_nonzero(tmp_path, monkeypatch, capsys):
    """A zero-minute deadline trips the time gate on wave 1: the run must write
    a pause, mark ALL tasks skipped, and exit non-zero — not exit 0."""
    _init_repo(tmp_path)
    plan = _write_plan(tmp_path, 3)

    monkeypatch.setenv("RENMARK_MAX_MINUTES_PER_RUN", "0")
    # codex never runs (gate trips first), but be safe and force it "available".
    monkeypatch.setattr(_engine, "codex_available", lambda: True)

    rc = _engine.execute_plan(str(plan), repo=tmp_path)

    assert rc == 10, "budget exhaustion must use the failure exit code, not 0"
    out = capsys.readouterr().out
    assert "All tasks completed." not in out
    assert "PAUSED" in out
    # Pause file written, keyed to the first skipped task.
    from renmark import state

    pause = state.read_pause(tmp_path)
    assert pause is not None
    assert pause.reason == "deadline"
    assert pause.last_task_index == 1
    # All three tasks recorded as skipped (not just wave 1).
    assert "[1, 2, 3]" in out


# ── Task 2: parallel change-detection delta + sibling exclusion ─────────────────


def test_codex_delta_excludes_preexisting_sibling_changes(tmp_path, monkeypatch):
    """run_codex_task reports only files changed BY the task (post minus pre).
    A sibling's in-flight file present before the call is not attributed here."""
    _init_repo(tmp_path)

    from renmark.parser import Task

    task = Task(index=1, title="t", mode="A", target="out/a.txt", verifier="true", spec="x")

    calls = {"n": 0}

    def fake_status(repo):
        calls["n"] += 1
        if calls["n"] == 1:
            # pre: a sibling already touched sibling.txt
            return ["sibling.txt"]
        # post: sibling still there + this task's own file
        return ["sibling.txt", "out/a.txt"]

    monkeypatch.setattr(codex_provider, "_git_status_porcelain", fake_status)
    monkeypatch.setattr(codex_provider, "codex_available", lambda: True)

    class FakeProc:
        returncode = 0
        stdout = "done"
        stderr = ""

    monkeypatch.setattr(codex_provider.subprocess, "run", lambda *a, **k: FakeProc())

    result = codex_provider.run_codex_task(task, tmp_path, timeout_s=5)
    assert result.changed_files == ["out/a.txt"], "sibling's pre-existing change must drop out"
    assert "sibling.txt" in result.pre_changed_files


def test_check_only_target_excludes_sibling_targets():
    """A sibling wave-target leaking into this task's delta must not trip the
    lane check (waves are disjoint, so this can't mask a real over-write)."""
    ok, reason = codex_provider.check_only_target_modified(
        ["out/a.txt", "out/b.txt"], "out/a.txt", sibling_targets=["out/b.txt"]
    )
    assert ok, reason
    # Without the sibling exclusion, the same input is out-of-lane.
    bad, _ = codex_provider.check_only_target_modified(["out/a.txt", "out/b.txt"], "out/a.txt")
    assert not bad


# ── Task 3 + 2: path-scoped rollback (untracked delete, tracked checkout) ───────


def test_rollback_deletes_untracked_target(tmp_path):
    """A newly-created (untracked) file is DELETED on rollback — checkout would
    be a no-op and leave the rejected artifact poisoning the next task."""
    _init_repo(tmp_path)
    new_file = tmp_path / "out" / "new.txt"
    new_file.parent.mkdir(parents=True)
    new_file.write_text("rejected artifact")

    untracked = _engine._untracked_paths(tmp_path, ["out/new.txt"])
    assert "out/new.txt" in untracked

    _engine._rollback_paths(tmp_path, ["out/new.txt"], untracked_before=untracked)
    assert not new_file.exists(), "untracked target must be deleted, not left on disk"


def test_rollback_restores_tracked_target(tmp_path):
    """A tracked file is restored to its committed content on rollback."""
    _init_repo(tmp_path)
    seed = tmp_path / "seed.txt"
    seed.write_text("CORRUPTED by a failed task")

    untracked = _engine._untracked_paths(tmp_path, ["seed.txt"])
    assert untracked == set()  # seed.txt is tracked

    _engine._rollback_paths(tmp_path, ["seed.txt"], untracked_before=untracked)
    assert seed.read_text() == "seed", "tracked target must be restored to committed content"


def test_rollback_leaves_sibling_untouched(tmp_path):
    """Rollback of one task's path must not touch a concurrent sibling's file."""
    _init_repo(tmp_path)
    sibling = tmp_path / "sibling.txt"
    sibling.write_text("sibling in-flight work")  # untracked sibling change
    mine = tmp_path / "out" / "mine.txt"
    mine.parent.mkdir(parents=True)
    mine.write_text("my rejected artifact")

    # Roll back ONLY my path.
    _engine._rollback_paths(tmp_path, ["out/mine.txt"], untracked_before={"out/mine.txt"})
    assert not mine.exists()
    assert sibling.exists(), "sibling's in-flight work must survive my rollback"
    assert sibling.read_text() == "sibling in-flight work"

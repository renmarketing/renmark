"""Tests for the --resume skip-list cross-check (P5 anti-re-dispatch doctrine).

The bug: completed_task_indices() scans git log with a regex that accepts
``(task N)``-suffix commits and any bracketed prefix.  When task numbers are
reused across different plans, or when commits from a previous plan bleed into
the skip-list, a task that was never run in THIS plan can be silently marked
"done" and dropped — the single most expensive observed orchestration failure.

The fix: _cross_check_skip_list() compares the git-log-derived skip-list
against the current live plan's task indices.  Any index not present in the
current plan is "orphaned" and must NOT be silently skipped.

Tests:
1. clean case — all done indices are in the plan → all safe to skip, zero ambiguous.
2. conflated / orphaned index — an index from git log is absent in the plan →
   flagged as ambiguous, NOT included in safe_to_skip.
3. mixed bag — some indices valid, some orphaned → correct partition.
4. integration: execute_plan --resume with an orphaned skip-list entry emits a
   warning and does NOT silently drop the task from execution.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from renmark.cli import _engine
from renmark.parser import Task

# ── helpers ───────────────────────────────────────────────────────────────────


def _make_task(index: int, target: str = "") -> Task:
    return Task(
        index=index,
        title=f"task {index}",
        mode="A",
        target=target or f"out/file{index}.txt",
        verifier="true",
        spec=f"make file {index}",
    )


def _init_repo(path: Path) -> None:
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=path, check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.name", "t"], check=True)
    (path / "seed.txt").write_text("seed")
    subprocess.run(["git", "-C", str(path), "add", "seed.txt"], check=True)
    subprocess.run(["git", "-C", str(path), "commit", "-q", "-m", "init"], check=True)


def _commit_task(path: Path, index: int, message_suffix: str = "") -> None:
    """Commit a dummy file with a renmark-style subject so git-log picks it up."""
    f = path / f"dummy_{index}.txt"
    f.write_text(f"task {index}")
    subprocess.run(["git", "-C", str(path), "add", str(f)], check=True)
    subject = f"[renmark] task {index}: dummy task {index}{message_suffix}"
    subprocess.run(
        ["git", "-C", str(path), "commit", "-q", "-m", subject], check=True
    )


def _write_plan(path: Path, n_tasks: int, target_prefix: str = "out/file") -> Path:
    """A plan with N serial tasks."""
    blocks = []
    for i in range(1, n_tasks + 1):
        blocks.append(
            f"### Task {i}: task {i}\n"
            f"- **mode:** A\n"
            f"- **target:** {target_prefix}{i}.txt\n"
            f"- **context_files:** []\n"
            f"- **verifier:** true\n"
            f"- **verifier_timeout_s:** 5\n"
            f"- **spec:**\n"
            f"  make file {i}\n"
        )
    p = path / "plan.md"
    p.write_text("\n".join(blocks))
    return p


# ── Unit tests for _cross_check_skip_list ─────────────────────────────────────


def test_crosscheck_clean_all_valid():
    """All done indices match current plan → all safe, none ambiguous."""
    tasks = [_make_task(1), _make_task(2), _make_task(3)]
    done = {1, 2, 3}
    safe, ambiguous = _engine._cross_check_skip_list(done, tasks)
    assert safe == {1, 2, 3}
    assert ambiguous == set()


def test_crosscheck_orphaned_index_flagged():
    """An index from git log that is absent in the current plan is orphaned.

    Scenario: previous plan had 5 tasks; current plan only has 3.  Index 5
    appears in git log (from the old plan) but is not a valid task in the new
    plan.  It must NOT be included in safe_to_skip.
    """
    tasks = [_make_task(1), _make_task(2), _make_task(3)]
    done = {1, 5}  # 5 is orphaned — no task 5 in this plan
    safe, ambiguous = _engine._cross_check_skip_list(done, tasks)
    assert safe == {1}, "only index 1 belongs to the current plan"
    assert ambiguous == {5}, "index 5 must be flagged as orphaned"


def test_crosscheck_mixed_bag():
    """Some indices valid, some orphaned — correct two-way partition."""
    tasks = [_make_task(1), _make_task(2), _make_task(3)]
    done = {1, 2, 4, 7}  # 4 and 7 are orphaned
    safe, ambiguous = _engine._cross_check_skip_list(done, tasks)
    assert safe == {1, 2}
    assert ambiguous == {4, 7}


def test_crosscheck_empty_done_is_noop():
    """Empty done set → both outputs empty (no false positives)."""
    tasks = [_make_task(1), _make_task(2)]
    safe, ambiguous = _engine._cross_check_skip_list(set(), tasks)
    assert safe == set()
    assert ambiguous == set()


def test_crosscheck_empty_plan_all_orphaned():
    """If the plan has no tasks (pathological), every done index is orphaned."""
    safe, ambiguous = _engine._cross_check_skip_list({1, 2}, [])
    assert safe == set()
    assert ambiguous == {1, 2}


def test_crosscheck_disjoint_sets():
    """safe and ambiguous are always disjoint subsets of done."""
    tasks = [_make_task(i) for i in range(1, 6)]
    done = {1, 3, 6, 9}
    safe, ambiguous = _engine._cross_check_skip_list(done, tasks)
    # Disjoint
    assert safe & ambiguous == set()
    # Union covers done exactly
    assert safe | ambiguous == done
    # Correct partition
    assert safe == {1, 3}
    assert ambiguous == {6, 9}


# ── Integration: execute_plan --resume emits warning for orphaned index ───────


def test_resume_warns_on_orphaned_skip_entry(tmp_path, monkeypatch, capsys):
    """execute_plan --resume with an orphaned git-log entry must:
    1. Print a warning about the orphaned index.
    2. NOT silently skip the task — the task shows up as runnable (not DONE).

    We simulate the scenario where git log reports task index 5 as "done" but
    the current plan only has tasks 1-3.  Index 5 is orphaned.
    """
    _init_repo(tmp_path)
    # Commit a "task 5" into git log (as if from a previous, now-replaced plan).
    _commit_task(tmp_path, 5)

    plan = _write_plan(tmp_path, 3)

    # Make codex unavailable so tasks fail fast without running anything real.
    monkeypatch.setattr(_engine, "codex_available", lambda: False)

    rc = _engine.execute_plan(str(plan), repo=tmp_path, resume=True)

    out = capsys.readouterr().out
    # Warning must be emitted about the orphaned index 5.
    assert "orphaned" in out.lower() or "cross-check" in out.lower(), (
        f"expected cross-check warning in output, got:\n{out}"
    )
    assert "5" in out, "the orphaned index must be named in the warning"
    # Non-vacuous: the orphaned index 5 must be EXCLUDED from the safe skip-list.
    # If the cross-check failed to exclude it, the engine would print the skip
    # line with 5 in it ("skipping already-committed tasks: [5]"). The fix means
    # the safe set is empty, so that exact line must never appear.
    assert "skipping already-committed tasks: [5]" not in out, (
        "orphaned index 5 was wrongly included in the resume skip-list"
    )


def test_resume_skips_genuinely_completed_tasks(tmp_path, monkeypatch, capsys):
    """Clean case: when tasks 1 and 2 are genuinely committed for this plan,
    --resume skips them and only runs task 3.

    This test pins that the cross-check does NOT break the happy path.
    """
    _init_repo(tmp_path)
    # Commit tasks 1 and 2 as genuinely completed for this 3-task plan.
    _commit_task(tmp_path, 1)
    _commit_task(tmp_path, 2)

    plan = _write_plan(tmp_path, 3)

    # codex unavailable → task 3 will fail, but tasks 1+2 must be logged DONE.
    monkeypatch.setattr(_engine, "codex_available", lambda: False)

    _engine.execute_plan(str(plan), repo=tmp_path, resume=True)

    out = capsys.readouterr().out
    # No cross-check warning — both indices are valid plan members.
    assert "orphaned" not in out.lower()
    assert "cross-check" not in out.lower()
    # Tasks 1 and 2 must appear as DONE (prev run).
    assert "(prev run)" in out, f"expected DONE lines for tasks 1+2, got:\n{out}"
    # The skip line must name both.
    assert "skipping already-committed tasks" in out
    assert "1" in out and "2" in out

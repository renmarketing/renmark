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

from renmark.cli import _codex_runner, _engine
from renmark.parser import Task
from renmark.providers.codex import CodexError

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


def _commit_task(
    path: Path, index: int, message_suffix: str = "", title: str | None = None
) -> None:
    """Commit a dummy file with a renmark-style subject so git-log picks it up.

    The subject mirrors what ``_codex_runner`` really writes:
    ``[renmark] task <index>: <task title>`` — the title matters now that the
    resume cross-check compares it against the current plan.
    """
    subject = f"[renmark] task {index}: {title or f'task {index}'}{message_suffix}"
    f = path / f"dummy_{index}.txt"
    # Content varies with the subject so repeated commits for the same index
    # (different plans) are never empty commits.
    f.write_text(subject)
    subprocess.run(["git", "-C", str(path), "add", str(f)], check=True)
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


# ── Title-aware cross-check (cross-plan reused-index false positive) ──────────


def test_crosscheck_title_match_still_safe():
    """Same plan, same index AND same title → still safe_to_skip (unchanged)."""
    tasks = [_make_task(1), _make_task(2), _make_task(3)]
    done_titles = {1: {"task 1"}, 2: {"task 2"}}
    safe, ambiguous = _engine._cross_check_skip_list({1, 2}, tasks, done_titles)
    assert safe == {1, 2}
    assert ambiguous == set()


def test_crosscheck_title_mismatch_is_ambiguous():
    """REGRESSION: cross-plan reused index (same N, different title) must NOT skip.

    The git-log scan is unbounded over the whole repo history, so an unrelated
    older plan's "[renmark] task 1: something else" made task 1 of the CURRENT
    plan look already-done.  It must land in ``ambiguous`` and be re-run.
    """
    tasks = [_make_task(1), _make_task(2)]
    done_titles = {1: {"wire up the old exporter"}, 2: {"task 2"}}
    safe, ambiguous = _engine._cross_check_skip_list({1, 2}, tasks, done_titles)
    assert safe == {2}, "only the genuine index+title match may be skipped"
    assert ambiguous == {1}, "reused index with a foreign title must be re-run"


def test_crosscheck_title_match_is_case_and_whitespace_insensitive():
    """Titles are compared normalized — minor formatting drift must not re-run."""
    tasks = [_make_task(1)]
    done_titles = {1: {"  TASK   1 "}}
    from renmark.state import normalize_task_title

    safe, ambiguous = _engine._cross_check_skip_list(
        {1}, tasks, {1: {normalize_task_title("  TASK   1 ")}}
    )
    assert safe == {1}
    assert ambiguous == set()
    assert normalize_task_title(next(iter(done_titles[1]))) == "task 1"


def test_crosscheck_missing_title_entry_is_ambiguous():
    """An index with no recorded title cannot be proven — prefer re-running."""
    tasks = [_make_task(1)]
    safe, ambiguous = _engine._cross_check_skip_list({1}, tasks, {})
    assert safe == set()
    assert ambiguous == {1}


def test_crosscheck_multiple_titles_for_index_matches_any():
    """A repo may hold many commits for index N; one correct title is enough."""
    tasks = [_make_task(1)]
    done_titles = {1: {"an old unrelated task", "task 1"}}
    safe, ambiguous = _engine._cross_check_skip_list({1}, tasks, done_titles)
    assert safe == {1}
    assert ambiguous == set()


def test_completed_task_titles_captures_index_and_title(tmp_path):
    """completed_task_titles() returns normalized titles keyed by index."""
    from renmark.state import completed_task_indices, completed_task_titles

    _init_repo(tmp_path)
    _commit_task(tmp_path, 1, title="Build The Thing")
    _commit_task(tmp_path, 1, title="a different plan's task 1")

    titles = completed_task_titles(tmp_path)
    assert titles == {1: {"build the thing", "a different plan's task 1"}}
    # Backward compatibility: the index-only API is unchanged.
    assert completed_task_indices(tmp_path) == {1}


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
    def unavailable(*_args, **_kwargs):
        raise CodexError("codex unavailable in test")

    monkeypatch.setattr(_codex_runner, "run_codex_task", unavailable)

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


def test_resume_does_not_skip_cross_plan_reused_index(tmp_path, monkeypatch, capsys):
    """REGRESSION (Finding A): an unrelated older plan's ``[renmark] task 1: ...``
    commit must not mark task 1 of the CURRENT plan as already-done.

    Index 1 exists in the current plan, so the old index-only cross-check
    passed it straight into the skip-list.  With the title cross-check it must
    be flagged and re-run instead.
    """
    _init_repo(tmp_path)
    # A commit from a DIFFERENT, long-gone plan that also numbered a task 1.
    _commit_task(tmp_path, 1, title="port the legacy exporter")
    # Task 2 genuinely completed for THIS plan.
    _commit_task(tmp_path, 2)

    plan = _write_plan(tmp_path, 3)

    def unavailable(*_args, **_kwargs):
        raise CodexError("codex unavailable in test")

    monkeypatch.setattr(_codex_runner, "run_codex_task", unavailable)

    _engine.execute_plan(str(plan), repo=tmp_path, resume=True)

    out = capsys.readouterr().out
    assert "skipping already-committed tasks: [2]" in out, (
        f"only the genuine index+title match may be skipped, got:\n{out}"
    )
    assert "orphaned" in out.lower() or "cross-check" in out.lower(), (
        f"expected a cross-check warning for the reused index, got:\n{out}"
    )
    assert "[1]" in out or "[1," in out or "(es) [1]" in out, (
        f"the reused index 1 must be named in the warning, got:\n{out}"
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
    def unavailable(*_args, **_kwargs):
        raise CodexError("codex unavailable in test")

    monkeypatch.setattr(_codex_runner, "run_codex_task", unavailable)

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

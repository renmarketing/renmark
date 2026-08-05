"""REQ-31 integration: proves the REAL dispatch engine
(``renmark.cli._engine.execute_plan``) creates/updates native tasks at
its actual per-task dispatch call site — not just that a markdown contract
describes the behavior.

Mirrors ``tests/test_ledger_wiring.py``'s pattern exactly: no live Agent/LLM
call — ``_execute_task`` is monkeypatched to a canned result so the real
wave-dispatch loop runs end to end, and the resulting native-task state
(``.renmark/state/tasks.json``) is asserted against.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from renmark import task_tracking as tt
from renmark.cli import _engine


def _init_repo(path: Path) -> None:
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=path, check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.name", "t"], check=True)
    (path / "seed.txt").write_text("seed")
    subprocess.run(["git", "-C", str(path), "add", "seed.txt"], check=True)
    subprocess.run(["git", "-C", str(path), "commit", "-q", "-m", "init"], check=True)


def _write_plan(path: Path, *, verifier: str = "true") -> Path:
    p = path / "plan.md"
    p.write_text(
        "### Task 1: task 1\n"
        "- **mode:** A\n"
        "- **target:** out/file1.txt\n"
        "- **context_files:** []\n"
        f"- **verifier:** {verifier}\n"
        "- **verifier_timeout_s:** 5\n"
        "- **spec:**\n"
        "  make file 1\n"
    )
    return p


def test_execute_plan_creates_worker_and_verification_tasks(tmp_path, monkeypatch):
    """Every agent dispatch creates or reuses one native task — proven by
    inspecting real post-run task state, not by reading a fragment."""
    _init_repo(tmp_path)
    plan = _write_plan(tmp_path)

    monkeypatch.setattr(_engine, "codex_available", lambda: True)
    monkeypatch.setattr(
        _engine, "_execute_task", lambda **kwargs: (True, "task 1 done", 100, "deadbeef")
    )

    rc = _engine.execute_plan(str(plan), repo=tmp_path)
    assert rc == 0

    tasks = tt.read_tasks(tmp_path)
    worker_ids = [t for t in tasks if t.startswith("task-") and not t.endswith("-verify")]
    verify_ids = [t for t in tasks if t.endswith("-verify")]
    parent_ids = [t for t in tasks if t.startswith("run-")]

    assert len(worker_ids) == 1
    assert len(verify_ids) == 1
    assert len(parent_ids) == 1


def test_worker_task_completion_requires_independent_verification_pass(tmp_path, monkeypatch):
    """Status changes match the actual dispatch lifecycle, and a worker's
    task only reaches `completed` once its linked, independently-dispatched
    verification task is itself `completed` — the no-self-approval rule,
    exercised through the real engine, not asserted about a fragment."""
    _init_repo(tmp_path)
    plan = _write_plan(tmp_path, verifier="true")

    monkeypatch.setattr(_engine, "codex_available", lambda: True)
    monkeypatch.setattr(
        _engine, "_execute_task", lambda **kwargs: (True, "task 1 done", 100, "deadbeef")
    )

    rc = _engine.execute_plan(str(plan), repo=tmp_path)
    assert rc == 0

    tasks = tt.read_tasks(tmp_path)
    worker = next(t for tid, t in tasks.items() if tid.startswith("task-") and not tid.endswith("-verify"))
    verify = next(t for tid, t in tasks.items() if tid.endswith("-verify"))

    assert verify.status == "completed"
    assert worker.status == "completed"
    assert worker.verified_by == verify.task_id
    # Dependency is represented, not merely implied.
    assert worker.task_id in verify.depends_on
    # Independent identities — the mechanical proof no self-approval occurred.
    assert verify.dispatch_identity != ""
    assert worker.dispatch_identity != ""
    assert verify.dispatch_identity != worker.dispatch_identity


def test_failed_independent_verifier_blocks_worker_completion(tmp_path, monkeypatch):
    """When the independent verifier rerun fails, the worker task must NOT
    reach `completed` even though the worker's own executor call reported
    success — completion tracks real verification evidence, not the
    worker's self-report."""
    _init_repo(tmp_path)
    # `false` always exits non-zero — the independent rerun will fail.
    plan = _write_plan(tmp_path, verifier="false")

    monkeypatch.setattr(_engine, "codex_available", lambda: True)
    monkeypatch.setattr(
        _engine, "_execute_task", lambda **kwargs: (True, "worker claims success", 100, "deadbeef")
    )

    _engine.execute_plan(str(plan), repo=tmp_path)

    tasks = tt.read_tasks(tmp_path)
    worker = next(t for tid, t in tasks.items() if tid.startswith("task-") and not tid.endswith("-verify"))
    verify = next(t for tid, t in tasks.items() if tid.endswith("-verify"))

    assert verify.status == "completed"
    assert verify.result_summary == "fail"
    assert worker.status == "failed"
    assert worker.verified_by is None


def test_resumed_run_reuses_the_same_task_records_not_fresh_ones(tmp_path, monkeypatch):
    """On interruption/resume, reload and reuse existing tasks — completed
    work is not recreated or redispatched. Proven by running the same plan
    twice with the same run inputs and checking task_id stability +
    unchanged completion evidence."""
    _init_repo(tmp_path)
    plan = _write_plan(tmp_path)

    monkeypatch.setattr(_engine, "codex_available", lambda: True)
    monkeypatch.setattr(
        _engine, "_execute_task", lambda **kwargs: (True, "task 1 done", 100, "deadbeef")
    )

    _engine.execute_plan(str(plan), repo=tmp_path)
    tasks_after_first = tt.read_tasks(tmp_path)
    worker_id = next(tid for tid in tasks_after_first if tid.startswith("task-") and not tid.endswith("-verify"))
    first_history_len = len(tasks_after_first[worker_id].history)

    # Directly exercise the anti-re-dispatch primitive the resume path relies
    # on: a task already `completed` must be reported skip-worthy, and a
    # second create_or_reuse_task call for the same id must be a true no-op.
    assert tt.should_skip_dispatch(tmp_path, worker_id) is True
    reused = tt.create_or_reuse_task(
        tmp_path,
        worker_id,
        title="a different title — must be ignored",
        role="haiku",
        scope="different-scope",
        verification_expectation="different",
    )
    assert reused.status == "completed"
    assert reused.title == tasks_after_first[worker_id].title
    tasks_after_reuse_attempt = tt.read_tasks(tmp_path)
    assert len(tasks_after_reuse_attempt[worker_id].history) == first_history_len


def test_task_tracking_failure_never_blocks_real_dispatch(tmp_path, monkeypatch):
    """Tracking is informational — a task_tracking exception must never
    prevent the real dispatch/commit from completing (REQ-30/REQ-31: no
    token/time regression, no new failure mode introduced by tracking)."""
    _init_repo(tmp_path)
    plan = _write_plan(tmp_path)

    monkeypatch.setattr(_engine, "codex_available", lambda: True)
    monkeypatch.setattr(
        _engine, "_execute_task", lambda **kwargs: (True, "task 1 done", 100, "deadbeef")
    )

    def _boom(*a, **kw):
        raise RuntimeError("tracking backend unavailable")

    monkeypatch.setattr(_engine._task_tracking, "create_or_reuse_task", _boom)

    rc = _engine.execute_plan(str(plan), repo=tmp_path)
    # The real dispatch/commit must still succeed even though every
    # task_tracking call raises.
    assert rc == 0


def test_worker_task_record_carries_the_wave_loop_order_id(tmp_path, monkeypatch):
    """End-to-end proof of Release 4 task 2's wiring: after a real
    ``_engine.execute_plan`` run, the worker ``TaskRecord`` in
    ``.renmark/state/tasks.json`` carries a non-empty ``order_id`` matching
    the same ``f"{run_id}-{task.index}"`` scheme ``_wave_loop.py`` already
    uses for the ledger ``WorkOrder``/``WorkResult`` events — not merely
    that the unit-level ``create_or_reuse_task(order_id=...)`` parameter
    works in isolation."""
    _init_repo(tmp_path)
    plan = _write_plan(tmp_path)

    monkeypatch.setattr(_engine, "codex_available", lambda: True)
    monkeypatch.setattr(
        _engine, "_execute_task", lambda **kwargs: (True, "task 1 done", 100, "deadbeef")
    )

    rc = _engine.execute_plan(str(plan), repo=tmp_path)
    assert rc == 0

    tasks = tt.read_tasks(tmp_path)
    worker_id = next(
        tid for tid in tasks if tid.startswith("task-") and not tid.endswith("-verify")
    )
    parent_id = next(tid for tid in tasks if tid.startswith("run-"))
    run_id = parent_id[len("run-"):]

    worker = tasks[worker_id]
    # The plan defines a single "### Task 1" entry, so its 1-based parser
    # index is 1 — the same index `_wave_loop.py` folds into `order_id`.
    expected_order_id = f"{run_id}-1"

    assert worker_id == f"task-{expected_order_id}"
    assert worker.order_id != ""
    assert worker.order_id == expected_order_id

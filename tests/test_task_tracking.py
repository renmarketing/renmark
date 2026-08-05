"""Unit tests for renmark.task_tracking — the real Python enforcement layer
behind REQ-31 (native task tracking for dispatched work).

These exercise actual behavior (creation, lifecycle transitions, the
no-self-approval invariant, resume-reuse, evidence requirements) against the
module directly — not just markdown presence.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from renmark import task_tracking as tt


def test_create_or_reuse_task_creates_pending(tmp_path: Path):
    rec = tt.create_or_reuse_task(
        tmp_path,
        "t1",
        title="Do X",
        role="sonnet",
        scope="file.py",
        verification_expectation="pytest",
    )
    assert rec.status == "pending"
    assert rec.title == "Do X"
    assert "created" in rec.history[-1]


def test_create_or_reuse_task_is_idempotent_resume_reuse(tmp_path: Path):
    first = tt.create_or_reuse_task(
        tmp_path, "t1", title="Do X", role="sonnet", scope="a", verification_expectation="v"
    )
    tt.mark_in_progress(tmp_path, "t1")
    tt.complete_task(tmp_path, "t1", artifact_path="out", result_summary="ok")

    # A second "dispatch" attempt for the same task_id must NOT recreate or
    # reset the task — this is the resume-reuse / anti-re-dispatch rule.
    second = tt.create_or_reuse_task(
        tmp_path, "t1", title="Do X (again)", role="sonnet", scope="a", verification_expectation="v"
    )
    assert second.status == "completed"
    assert second.title == "Do X"  # unchanged, not overwritten by the re-call
    assert second.artifact_path == "out"


def test_create_or_reuse_task_persists_order_id(tmp_path: Path):
    rec = tt.create_or_reuse_task(
        tmp_path,
        "t1",
        title="Do X",
        role="sonnet",
        scope="a",
        verification_expectation="v",
        order_id="run-1-3",
    )
    assert rec.order_id == "run-1-3"
    assert tt.read_tasks(tmp_path)["t1"].order_id == "run-1-3"


def test_create_or_reuse_task_keeps_original_order_id_on_resume_reuse(tmp_path: Path):
    first = tt.create_or_reuse_task(
        tmp_path,
        "t1",
        title="Do X",
        role="sonnet",
        scope="a",
        verification_expectation="v",
        order_id="run-1-3",
    )
    second = tt.create_or_reuse_task(
        tmp_path,
        "t1",
        title="Do X again",
        role="sonnet",
        scope="a",
        verification_expectation="v",
        order_id="run-2-3",
    )

    assert first.order_id == "run-1-3"
    assert second.order_id == "run-1-3"
    assert tt.read_tasks(tmp_path)["t1"].order_id == "run-1-3"


def test_lifecycle_pending_to_in_progress_to_completed(tmp_path: Path):
    tt.create_or_reuse_task(
        tmp_path, "t1", title="X", role="sonnet", scope="a", verification_expectation="v"
    )
    rec = tt.mark_in_progress(tmp_path, "t1")
    assert rec.status == "in_progress"
    rec = tt.complete_task(tmp_path, "t1", artifact_path="a.py", result_summary="done")
    assert rec.status == "completed"
    assert rec.artifact_path == "a.py"


def test_complete_task_requires_evidence(tmp_path: Path):
    tt.create_or_reuse_task(
        tmp_path, "t1", title="X", role="sonnet", scope="a", verification_expectation="v"
    )
    tt.mark_in_progress(tmp_path, "t1")
    with pytest.raises(tt.MissingEvidenceError):
        tt.complete_task(tmp_path, "t1", artifact_path="", result_summary="")
    with pytest.raises(tt.MissingEvidenceError):
        tt.complete_task(tmp_path, "t1", artifact_path="a.py", result_summary="")


def test_record_blocker_retry_failure_update_same_task(tmp_path: Path):
    tt.create_or_reuse_task(
        tmp_path, "t1", title="X", role="sonnet", scope="a", verification_expectation="v"
    )
    tt.mark_in_progress(tmp_path, "t1")
    blocked = tt.record_blocker(tmp_path, "t1", "waiting on upstream")
    assert blocked.status == "blocked"
    assert blocked.blocker == "waiting on upstream"

    retried = tt.record_retry(tmp_path, "t1", "resumed after unblock")
    assert retried.status == "in_progress"
    assert retried.retry_count == 1
    assert retried.blocker is None

    failed = tt.record_failure(tmp_path, "t1", "verifier failed twice")
    assert failed.status == "failed"

    # All of this happened on the SAME task_id — never a fresh task.
    all_tasks = tt.read_tasks(tmp_path)
    assert list(all_tasks.keys()) == ["t1"]
    assert len(all_tasks["t1"].history) >= 4  # created, in_progress, blocked, retry, failed


def test_no_self_approval_blocks_matching_dispatch_identity(tmp_path: Path):
    tt.create_or_reuse_task(
        tmp_path,
        "worker",
        title="Do X",
        role="sonnet",
        scope="a",
        verification_expectation="v",
        dispatch_identity="sonnet:run1-1",
    )
    tt.mark_in_progress(tmp_path, "worker")
    tt.create_or_reuse_task(
        tmp_path,
        "verify",
        title="Verify X",
        role="inspector",
        scope="a",
        verification_expectation="v",
        dispatch_identity="sonnet:run1-1",  # SAME identity as the worker — self-grading
    )
    tt.mark_in_progress(tmp_path, "verify")
    tt.complete_task(tmp_path, "verify", artifact_path="out", result_summary="pass")

    with pytest.raises(tt.SelfApprovalError):
        tt.complete_worker_task(
            tmp_path,
            "worker",
            verification_task_id="verify",
            artifact_path="a.py",
            result_summary="ok",
        )
    # The worker task must remain un-completed after the rejection.
    assert tt.read_tasks(tmp_path)["worker"].status == "in_progress"


def test_no_self_approval_blocks_empty_verifier_identity(tmp_path: Path):
    tt.create_or_reuse_task(
        tmp_path,
        "worker",
        title="X",
        role="sonnet",
        scope="a",
        verification_expectation="v",
        dispatch_identity="sonnet:run1-1",
    )
    tt.mark_in_progress(tmp_path, "worker")
    tt.create_or_reuse_task(
        tmp_path, "verify", title="V", role="inspector", scope="a", verification_expectation="v"
    )
    tt.mark_in_progress(tmp_path, "verify")
    tt.complete_task(tmp_path, "verify", artifact_path="out", result_summary="pass")

    with pytest.raises(tt.SelfApprovalError):
        tt.complete_worker_task(
            tmp_path, "worker", verification_task_id="verify", artifact_path="a", result_summary="ok"
        )


def test_independent_verification_allows_completion(tmp_path: Path):
    tt.create_or_reuse_task(
        tmp_path,
        "worker",
        title="X",
        role="sonnet",
        scope="a",
        verification_expectation="v",
        dispatch_identity="sonnet:run1-1",
    )
    tt.mark_in_progress(tmp_path, "worker")
    tt.create_or_reuse_task(
        tmp_path,
        "verify",
        title="V",
        role="inspector",
        scope="a",
        verification_expectation="v",
        dispatch_identity="inspector:fixed",
    )
    tt.mark_in_progress(tmp_path, "verify")
    tt.complete_task(tmp_path, "verify", artifact_path="out", result_summary="pass")

    rec = tt.complete_worker_task(
        tmp_path, "worker", verification_task_id="verify", artifact_path="a.py", result_summary="ok"
    )
    assert rec.status == "completed"
    assert rec.verified_by == "verify"


def test_complete_worker_task_requires_verification_task_completed(tmp_path: Path):
    tt.create_or_reuse_task(
        tmp_path,
        "worker",
        title="X",
        role="sonnet",
        scope="a",
        verification_expectation="v",
        dispatch_identity="sonnet:run1-1",
    )
    tt.mark_in_progress(tmp_path, "worker")
    tt.create_or_reuse_task(
        tmp_path,
        "verify",
        title="V",
        role="inspector",
        scope="a",
        verification_expectation="v",
        dispatch_identity="inspector:fixed",
    )
    tt.mark_in_progress(tmp_path, "verify")  # never completed

    with pytest.raises(tt.MissingVerificationError):
        tt.complete_worker_task(
            tmp_path, "worker", verification_task_id="verify", artifact_path="a", result_summary="ok"
        )


def test_close_task_requires_reason_and_records_history(tmp_path: Path):
    tt.create_or_reuse_task(
        tmp_path, "t1", title="X", role="sonnet", scope="a", verification_expectation="v"
    )
    with pytest.raises(tt.TaskTrackingError):
        tt.close_task(tmp_path, "t1", reason="")
    rec = tt.close_task(tmp_path, "t1", reason="scope changed, superseded by t2")
    assert rec.status == "deleted"
    assert rec.close_reason == "scope changed, superseded by t2"
    assert "closed" in rec.history[-1]

    # A closed task IS NOT skip-worthy — closing means "needs a replacement",
    # not "done, skip re-dispatch."
    assert tt.should_skip_dispatch(tmp_path, "t1") is False

    # After closing, a "replacement" task under a fresh id is a fresh create.
    replacement = tt.create_or_reuse_task(
        tmp_path, "t2", title="X (rescoped)", role="sonnet", scope="b", verification_expectation="v"
    )
    assert replacement.status == "pending"


def test_should_skip_dispatch_true_only_for_completed(tmp_path: Path):
    tt.create_or_reuse_task(
        tmp_path, "t1", title="X", role="sonnet", scope="a", verification_expectation="v"
    )
    assert tt.should_skip_dispatch(tmp_path, "t1") is False
    tt.mark_in_progress(tmp_path, "t1")
    assert tt.should_skip_dispatch(tmp_path, "t1") is False
    tt.complete_task(tmp_path, "t1", artifact_path="a", result_summary="ok")
    assert tt.should_skip_dispatch(tmp_path, "t1") is True
    assert tt.should_skip_dispatch(tmp_path, "does-not-exist") is False


def test_unknown_task_transition_raises():
    import tempfile

    with tempfile.TemporaryDirectory() as d, pytest.raises(tt.UnknownTaskError):
        tt.mark_in_progress(Path(d), "ghost")


def test_read_tasks_never_raises_on_missing_or_corrupt_state(tmp_path: Path):
    assert tt.read_tasks(tmp_path) == {}
    state_file = tt.tasks_path(tmp_path)
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text("not valid json{{{", encoding="utf-8")
    assert tt.read_tasks(tmp_path) == {}


def test_parent_progress_counts_by_status(tmp_path: Path):
    tt.create_or_reuse_task(
        tmp_path, "parent-1", title="Milestone", role="orchestrator", scope="plan.md",
        verification_expectation="all pass",
    )
    tt.create_or_reuse_task(
        tmp_path, "w1", title="A", role="sonnet", scope="a", verification_expectation="v",
        parent_id="parent-1",
    )
    tt.create_or_reuse_task(
        tmp_path, "w2", title="B", role="sonnet", scope="b", verification_expectation="v",
        parent_id="parent-1",
    )
    tt.mark_in_progress(tmp_path, "w1")
    tt.complete_task(tmp_path, "w1", artifact_path="a", result_summary="ok")

    counts = tt.parent_progress(tmp_path, "parent-1")
    assert counts == {"completed": 1, "pending": 1}


def test_writes_are_atomic_no_partial_file_on_crash(tmp_path: Path, monkeypatch):
    tt.create_or_reuse_task(
        tmp_path, "t1", title="X", role="sonnet", scope="a", verification_expectation="v"
    )

    original_replace = tt.os.replace

    def _boom(*a, **kw):
        raise OSError("disk full")

    monkeypatch.setattr(tt.os, "replace", _boom)
    with pytest.raises(OSError):
        tt.mark_in_progress(tmp_path, "t1")
    monkeypatch.setattr(tt.os, "replace", original_replace)

    # The prior good state must still be readable — no partial/corrupt write.
    rec = tt.read_tasks(tmp_path)["t1"]
    assert rec.status == "pending"
    # No leftover .tmp files.
    leftovers = list(tt.tasks_dir(tmp_path).glob("*.tmp.*"))
    assert leftovers == []

from __future__ import annotations

from renmark.program import Program, StageNode, TaskNode, read_program
from renmark.program_driver import (
    MilestoneDecision,
    StopReason,
    advance_on_success,
    decide_milestone_execution,
    drift_warning,
    evaluate_stop,
    next_stage,
)


def make_program(*stages: StageNode) -> Program:
    return Program(feature="feature", created_at="2026-06-14T00:00:00Z", stages=list(stages))


def test_next_stage_skips_done_stages() -> None:
    program = make_program(
        StageNode(id="brainstorm", status="done"),
        StageNode(id="plan", status="pending"),
        StageNode(id="build", status="pending"),
    )

    assert next_stage(program) == program.stages[1]


def test_next_stage_resumes_in_progress_stage() -> None:
    program = make_program(
        StageNode(id="brainstorm", status="done"),
        StageNode(id="plan", status="in_progress"),
        StageNode(id="build", status="pending"),
    )

    assert next_stage(program) == program.stages[1]


def test_next_stage_returns_none_when_all_done() -> None:
    program = make_program(
        StageNode(id="brainstorm", status="done"),
        StageNode(id="plan", status="done"),
    )

    assert next_stage(program) is None


def test_evaluate_stop_maps_verify_failed_from_incomplete_completion() -> None:
    reason = evaluate_stop(
        {
            "completion_state": "partial",
            "validation_status": "validated",
        }
    )

    assert reason is StopReason.VERIFY_FAILED


def test_evaluate_stop_maps_verify_failed_from_failed_validation() -> None:
    reason = evaluate_stop(
        {
            "completion_state": "complete",
            "validation_status": "failed",
        }
    )

    assert reason is StopReason.VERIFY_FAILED


def test_evaluate_stop_maps_plan_block() -> None:
    assert evaluate_stop({"verdict": "BLOCK"}) is StopReason.PLAN_BLOCK


def test_evaluate_stop_maps_codereview_critical() -> None:
    assert evaluate_stop({"critical_count": 1}) is StopReason.CODEREVIEW_CRITICAL


def test_evaluate_stop_maps_retry_exhausted_at_threshold() -> None:
    assert evaluate_stop({"max_retry_count": 3}) is StopReason.RETRY_EXHAUSTED


def test_evaluate_stop_maps_prd_drift() -> None:
    assert evaluate_stop({"align_verdict": "drift"}) is StopReason.PRD_DRIFT


def test_evaluate_stop_maps_budget_and_usage_signals_to_paused() -> None:
    assert evaluate_stop({"budget_status": "exhausted"}) is StopReason.PAUSED
    assert evaluate_stop({"usage_limited": True}) is StopReason.PAUSED


def test_evaluate_stop_maps_req_12_gate_to_awaiting_approval() -> None:
    assert evaluate_stop({"awaiting_approval": True}) is StopReason.AWAITING_APPROVAL
    assert evaluate_stop({"gate": True}) is StopReason.AWAITING_APPROVAL


def test_advance_on_success_marks_done_snapshots_next_sha_and_persists_before_return(
    monkeypatch, tmp_path
) -> None:
    program = make_program(
        StageNode(
            id="plan",
            status="in_progress",
            tasks=[TaskNode(id="t1", title="Write plan", status="done")],
        ),
        StageNode(
            id="build",
            status="pending",
            tasks=[TaskNode(id="t2", title="Implement", status="pending")],
        ),
    )
    expected_sha = "abcdef1234567890"
    observed = {}
    from renmark.program import write_program as original_write_program

    monkeypatch.setattr("renmark.program_driver.git_head_sha", lambda repo: expected_sha)

    def recording_write_program(repo, candidate):
        observed["repo"] = repo
        observed["statuses"] = [stage.status for stage in candidate.stages]
        observed["current_stage_id"] = candidate.current_stage_id
        observed["stage_completion_sha"] = dict(candidate.stage_completion_sha)
        return original_write_program(repo, candidate)

    monkeypatch.setattr("renmark.program_driver._program.write_program", recording_write_program)

    returned = advance_on_success(program, "plan", str(tmp_path))
    persisted = read_program(tmp_path)

    assert [stage.status for stage in returned.stages] == ["done", "pending"]
    assert returned.current_stage_id == "build"
    assert returned.stage_completion_sha == {"build": expected_sha}
    assert observed == {
        "repo": str(tmp_path),
        "statuses": ["done", "pending"],
        "current_stage_id": "build",
        "stage_completion_sha": {"build": expected_sha},
    }
    assert persisted is not None
    assert [stage.status for stage in persisted.stages] == ["done", "pending"]
    assert persisted.current_stage_id == "build"
    assert persisted.stage_completion_sha == {"build": expected_sha}


def test_drift_warning_fires_on_sha_mismatch_and_is_silent_on_match() -> None:
    program = make_program(StageNode(id="build", status="pending"))
    program.stage_completion_sha["build"] = "abcdef1234567890"

    assert drift_warning(program, "build", "abcdef1234567890") is None

    warning = drift_warning(program, "build", "fedcba0987654321")

    assert warning is not None
    assert "build" in warning
    assert "abcdef12" in warning
    assert "fedcba09" in warning


# ── next_stage ordering regressions (codereview 2026-06-14) ─────────────────────


def test_next_stage_halts_at_earlier_blocked_stage() -> None:
    """A blocked earlier stage must NOT be skipped past to run a later stage —
    selection halts (None) until the attention state is resolved."""
    program = make_program(
        StageNode(id="plan", status="done"),
        StageNode(id="build", status="blocked"),
        StageNode(id="ship", status="pending"),
    )
    assert next_stage(program) is None


def test_next_stage_halts_at_earlier_partial_stage() -> None:
    program = make_program(
        StageNode(id="plan", status="done"),
        StageNode(id="build", status="partial"),
        StageNode(id="ship", status="pending"),
    )
    assert next_stage(program) is None


def test_next_stage_prioritizes_in_progress_over_earlier_pending() -> None:
    """Resuming active work outranks starting an earlier not-yet-run stage."""
    program = make_program(
        StageNode(id="plan", status="pending"),
        StageNode(id="build", status="in_progress"),
    )
    assert next_stage(program) == program.stages[1]


# ── Milestone verifier / repair decisions (M4) ──────────────────────────────────────────────


def milestone_program() -> Program:
    return make_program(
        StageNode(
            id="build",
            status="in_progress",
            tasks=[TaskNode(id="implement-widget", title="Implement widget", status="done")],
        )
    )


def fresh_verifier_metadata(**overrides: object) -> dict[str, object]:
    metadata: dict[str, object] = {
        "fresh": True,
        "artifact_ref": ".renmark/reviews/build-verify.json",
        "completion_state": "complete",
        "validation_status": "validated",
    }
    metadata.update(overrides)
    return metadata


def test_decide_milestone_execution_advances_only_on_fresh_complete_validation(tmp_path) -> None:
    decision = decide_milestone_execution(
        milestone_program(), "build", fresh_verifier_metadata(), repo=str(tmp_path)
    )

    assert decision == MilestoneDecision("advance", True, None)


def test_decide_milestone_execution_emits_pointer_only_scoped_repair(tmp_path) -> None:
    raw_verifier_body = "FAIL: proprietary verifier details must never escape"
    decision = decide_milestone_execution(
        milestone_program(),
        "build",
        fresh_verifier_metadata(
            completion_state="partial",
            validation_status="failed",
            verifier_output=raw_verifier_body,
        ),
        repo=str(tmp_path),
        milestone_id="milestone-build",
        work_package_id="implement-widget",
    )

    assert decision.action == "repair"
    assert decision.advance_allowed is False
    assert decision.reason is StopReason.VERIFY_FAILED
    assert decision.repair_package is not None
    assert decision.repair_package.milestone_id == "milestone-build"
    assert decision.repair_package.work_package_id == "implement-widget"
    assert decision.repair_package.artifact_ref == ".renmark/reviews/build-verify.json"
    assert raw_verifier_body not in repr(decision)
    assert not hasattr(decision.repair_package, "verifier_output")


def test_decide_milestone_execution_stops_on_stale_evidence(tmp_path) -> None:
    decision = decide_milestone_execution(
        milestone_program(),
        "build",
        fresh_verifier_metadata(fresh=False, completion_state="partial", validation_status="failed"),
        repo=str(tmp_path),
    )

    assert decision == MilestoneDecision("stop", False, StopReason.VERIFY_FAILED)


def test_decide_milestone_execution_stops_for_budget_or_scope_drift(tmp_path) -> None:
    program = milestone_program()

    budget = decide_milestone_execution(
        program, "build", fresh_verifier_metadata(budget_status="exhausted"), repo=str(tmp_path)
    )
    scope = decide_milestone_execution(
        program, "build", fresh_verifier_metadata(scope_drift=True), repo=str(tmp_path)
    )

    assert budget == MilestoneDecision("stop", False, StopReason.PAUSED)
    assert scope == MilestoneDecision("stop", False, StopReason.PRD_DRIFT)


def test_decide_milestone_execution_does_not_repair_a_failed_verifier_when_budget_is_paused(
    tmp_path,
) -> None:
    decision = decide_milestone_execution(
        milestone_program(),
        "build",
        fresh_verifier_metadata(
            completion_state="partial",
            validation_status="failed",
            budget_status="exhausted",
        ),
        repo=str(tmp_path),
        milestone_id="milestone-build",
        work_package_id="implement-widget",
    )

    assert decision == MilestoneDecision("stop", False, StopReason.PAUSED)
    assert decision.repair_package is None


def test_decide_milestone_execution_blocks_third_equivalent_repair(tmp_path) -> None:
    program = milestone_program()
    failed = fresh_verifier_metadata(completion_state="partial", validation_status="failed")

    first = decide_milestone_execution(program, "build", failed, repo=str(tmp_path))
    second = decide_milestone_execution(program, "build", failed, repo=str(tmp_path))
    third = decide_milestone_execution(program, "build", failed, repo=str(tmp_path))

    assert first.action == second.action == "repair"
    assert third == MilestoneDecision("stop", False, StopReason.RETRY_EXHAUSTED)

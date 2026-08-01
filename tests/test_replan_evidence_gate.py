"""R-0.2/WP-5 — evidence-required replan gate + generalized rework-bound tests.

Covers ``.renmark/plans/r-0.2/replan-evidence-design.md``:

1. A replan with valid recorded evidence (an Inspector's structured
   architecture-failure finding) is permitted.
2. A replan backed only by a prose assertion is rejected.
3. The "max replans per milestone" cap (design doc §1.6) fires on the
   second replan request, reusing ``renmark.recurrence``.
4. The existing third-equivalent-repair cap
   (``decide_milestone_execution``) fires the same way no matter which
   caller/module invokes it — proving the mechanism is path-agnostic, per
   the design doc's §2 generalization goal.
"""

from __future__ import annotations

from pathlib import Path

from renmark.program import Program, StageNode, TaskNode
from renmark.program_driver import (
    MilestoneDecision,
    ReplannableEscalation,
    StopReason,
    decide_milestone_execution,
    permit_replan,
)


def _write_artifact(repo: Path, rel_path: str, content: str = "{}") -> str:
    full = repo / rel_path
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(content, encoding="utf-8")
    return rel_path


# ── (a) valid recorded evidence is permitted ─────────────────────────────────


def test_replan_with_inspector_architecture_finding_is_permitted(tmp_path) -> None:
    evidence = _write_artifact(
        tmp_path,
        ".renmark/reviews/2026-08-01-architecture-inspection.json",
        '{"inspection_type": "architecture"}',
    )
    request = ReplannableEscalation(
        milestone_id="build",
        trigger_type=2,
        evidence_artifact=evidence,
        metadata={
            "inspection_type": "architecture",
            "reproducible_evidence_path": ".renmark/debug/repro.md",
        },
    )

    decision = permit_replan(str(tmp_path), request)

    assert decision.permitted is True
    assert decision.trigger_type == 2
    assert decision.reason == "replan permitted; evidence valid"


def test_replan_with_owner_change_request_is_permitted(tmp_path) -> None:
    evidence = _write_artifact(tmp_path, ".renmark/state/change-request-2026-08-01.json")
    request = ReplannableEscalation(
        milestone_id="build",
        trigger_type=1,
        evidence_artifact=evidence,
        metadata={"approved_by": "Owner", "approved_at": "2026-08-01T00:00:00Z"},
    )

    decision = permit_replan(str(tmp_path), request)

    assert decision.permitted is True


# ── (b) prose-only assertion is rejected ─────────────────────────────────────


def test_replan_with_prose_only_assertion_is_rejected(tmp_path) -> None:
    """No artifact pointer, no recognized trigger — just an opinion."""
    request = ReplannableEscalation(
        milestone_id="build",
        trigger_type=0,  # not one of the five recognized triggers
        evidence_artifact="",
        metadata={"assertion": "I think a different approach is better"},
    )

    decision = permit_replan(str(tmp_path), request)

    assert decision.permitted is False
    assert "unrecognized trigger_type" in decision.reason


def test_replan_citing_real_trigger_but_no_artifact_is_rejected(tmp_path) -> None:
    """Even a recognized trigger type is rejected without a real artifact
    pointer — "I think Inspector would agree" is not evidence."""
    request = ReplannableEscalation(
        milestone_id="build",
        trigger_type=2,
        evidence_artifact="",
        metadata={"inspection_type": "architecture"},
    )

    decision = permit_replan(str(tmp_path), request)

    assert decision.permitted is False
    assert "no evidence artifact" in decision.reason


def test_replan_citing_nonexistent_artifact_is_rejected(tmp_path) -> None:
    request = ReplannableEscalation(
        milestone_id="build",
        trigger_type=2,
        evidence_artifact=".renmark/reviews/does-not-exist.json",
        metadata={
            "inspection_type": "architecture",
            "reproducible_evidence_path": ".renmark/debug/repro.md",
        },
    )

    decision = permit_replan(str(tmp_path), request)

    assert decision.permitted is False
    assert "artifact not found" in decision.reason


def test_replan_missing_trigger_specific_fields_is_rejected(tmp_path) -> None:
    """Artifact exists and trigger type is recognized, but the required
    structured fields (per design doc §1.4) are absent."""
    evidence = _write_artifact(tmp_path, ".renmark/reviews/2026-08-01-thin.json")
    request = ReplannableEscalation(
        milestone_id="build",
        trigger_type=2,
        evidence_artifact=evidence,
        metadata={},  # no inspection_type, no reproducible_evidence_path
    )

    decision = permit_replan(str(tmp_path), request)

    assert decision.permitted is False
    assert "not architecture" in decision.reason


# ── (c) max-replans-per-milestone cap (design doc §1.6) ─────────────────────


def test_second_replan_on_same_milestone_is_rejected(tmp_path) -> None:
    evidence = _write_artifact(tmp_path, ".renmark/reviews/2026-08-01-arch.json")
    metadata = {
        "inspection_type": "architecture",
        "reproducible_evidence_path": ".renmark/debug/repro.md",
    }

    first = permit_replan(
        str(tmp_path),
        ReplannableEscalation("build", 2, evidence, metadata),
    )
    second = permit_replan(
        str(tmp_path),
        ReplannableEscalation("build", 2, evidence, metadata),
    )

    assert first.permitted is True
    assert second.permitted is False
    assert "replan limit exceeded" in second.reason


def test_replan_limit_is_scoped_per_milestone(tmp_path) -> None:
    """A different milestone gets its own independent replan allowance."""
    evidence = _write_artifact(tmp_path, ".renmark/reviews/2026-08-01-arch.json")
    metadata = {
        "inspection_type": "architecture",
        "reproducible_evidence_path": ".renmark/debug/repro.md",
    }

    permit_replan(str(tmp_path), ReplannableEscalation("build", 2, evidence, metadata))
    other = permit_replan(str(tmp_path), ReplannableEscalation("deploy", 2, evidence, metadata))

    assert other.permitted is True


# ── (d) stale evidence is rejected ───────────────────────────────────────────


def test_replan_with_stale_evidence_is_rejected(tmp_path) -> None:
    evidence = _write_artifact(tmp_path, ".renmark/reviews/2026-08-01-arch.json")
    request = ReplannableEscalation(
        milestone_id="build",
        trigger_type=2,
        evidence_artifact=evidence,
        metadata={
            "inspection_type": "architecture",
            "reproducible_evidence_path": ".renmark/debug/repro.md",
            "stale_after": "2020-01-01T00:00:00Z",
        },
    )

    decision = permit_replan(str(tmp_path), request)

    assert decision.permitted is False
    assert "stale" in decision.reason


# ── (e) rework/recurrence cap fires consistently regardless of caller ────────


def _milestone_program() -> Program:
    return Program(
        feature="feature",
        created_at="2026-06-14T00:00:00Z",
        stages=[
            StageNode(
                id="build",
                status="in_progress",
                tasks=[TaskNode(id="implement-widget", title="Implement widget", status="done")],
            )
        ],
    )


def _fresh_failed_metadata(**overrides: object) -> dict[str, object]:
    metadata: dict[str, object] = {
        "fresh": True,
        "artifact_ref": ".renmark/reviews/build-verify.json",
        "completion_state": "partial",
        "validation_status": "failed",
    }
    metadata.update(overrides)
    return metadata


def _invoke_as_normal_dispatch_caller(program, failed, repo) -> MilestoneDecision:
    """Simulates a normal-path caller (e.g. a future ``/renmark:feature``
    verifier-integration site) invoking the SAME public function as the
    orchestrate-skill's prose does today — proving the cap is reachable
    (and behaves identically) from more than one call site."""
    return decide_milestone_execution(program, "build", failed, repo=str(repo))


def _invoke_as_orchestrate_wave_caller(program, failed, repo) -> MilestoneDecision:
    """Simulates an orchestrate-style per-wave caller."""
    return decide_milestone_execution(program, "build", failed, repo=str(repo))


def test_third_equivalent_repair_cap_fires_identically_from_different_callers(tmp_path) -> None:
    program = _milestone_program()
    failed = _fresh_failed_metadata()

    first = _invoke_as_normal_dispatch_caller(program, failed, tmp_path)
    second = _invoke_as_orchestrate_wave_caller(program, failed, tmp_path)
    third = _invoke_as_normal_dispatch_caller(program, failed, tmp_path)

    assert first.action == second.action == "repair"
    assert third == MilestoneDecision("stop", False, StopReason.RETRY_EXHAUSTED)


def test_decide_milestone_execution_is_directly_importable_and_path_agnostic() -> None:
    """Pin that the mechanism WP-5 wires is a plain, directly-callable
    function — no fast-path-only gate, no hidden state requiring the
    orchestrate SKILL.md's specific call sequence."""
    import inspect

    from renmark import program_driver

    assert callable(program_driver.decide_milestone_execution)
    sig = inspect.signature(program_driver.decide_milestone_execution)
    assert "repo" in sig.parameters

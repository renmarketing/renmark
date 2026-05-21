"""Tests for renmark.schemas — validators for lifecycle.json, pipeline.json,
SubagentOutput, ArtifactMetadata."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from renmark import schemas


# ── lifecycle ────────────────────────────────────────────────────────────────


def _valid_lifecycle() -> dict:
    return {
        "feature": "demo",
        "branch": "feature/demo",
        "github_issue": None,
        "stage": "init",
        "stages_completed": [],
        "artifacts": {},
        "human_review_required": False,
        "human_review_completed": False,
        "human_review_for": None,
        "next_recommended": "/renmark:brainstorm",
        "last_updated": "2026-05-21T00:00:00+00:00",
    }


def test_validate_lifecycle_accepts_valid():
    assert schemas.validate_lifecycle(_valid_lifecycle()) == []


def test_validate_lifecycle_rejects_non_object():
    assert schemas.validate_lifecycle("not an object")
    assert schemas.validate_lifecycle([1, 2, 3])


def test_validate_lifecycle_rejects_missing_field():
    data = _valid_lifecycle()
    del data["stage"]
    issues = schemas.validate_lifecycle(data)
    assert any("stage" in i and "missing" in i for i in issues)


def test_validate_lifecycle_rejects_unknown_stage():
    data = _valid_lifecycle()
    data["stage"] = "totally-fake-stage"
    issues = schemas.validate_lifecycle(data)
    assert any("not in canonical STAGES" in i for i in issues)


def test_validate_lifecycle_rejects_bad_type():
    data = _valid_lifecycle()
    data["human_review_required"] = "yes"  # should be bool
    issues = schemas.validate_lifecycle(data)
    assert any("human_review_required" in i for i in issues)


def test_validate_lifecycle_flags_runtime_cruft():
    """If lifecycle.json grew past 1KB, that's pipeline-state leakage."""
    data = _valid_lifecycle()
    # Inflate artifacts to over 1KB.
    data["artifacts"] = {f"key{i}": "x" * 100 for i in range(20)}
    issues = schemas.validate_lifecycle(data)
    assert any("budget" in i for i in issues)


def test_validate_lifecycle_rejects_unknown_stage_in_completed():
    data = _valid_lifecycle()
    data["stages_completed"] = ["init", "bogus-stage"]
    issues = schemas.validate_lifecycle(data)
    assert any("stages_completed" in i and "bogus-stage" in i for i in issues)


# ── pipeline ────────────────────────────────────────────────────────────────


def _valid_pipeline() -> dict:
    return {
        "current_phase": "orchestrate",
        "current_plan": ".renmark/plans/demo.plan.md",
        "wave_index": 1,
        "wave_total": 3,
        "completed_tasks": [1, 2],
        "failed_tasks": [],
        "last_updated": "2026-05-21T00:00:00+00:00",
    }


def test_validate_pipeline_accepts_valid():
    assert schemas.validate_pipeline(_valid_pipeline()) == []


def test_validate_pipeline_rejects_bad_phase():
    data = _valid_pipeline()
    data["current_phase"] = "running"  # not in PIPELINE_PHASES
    issues = schemas.validate_pipeline(data)
    assert any("current_phase" in i for i in issues)


def test_validate_pipeline_rejects_non_int_task_index():
    data = _valid_pipeline()
    data["completed_tasks"] = [1, "two", 3]
    issues = schemas.validate_pipeline(data)
    assert any("completed_tasks[1]" in i for i in issues)


# ── subagent output ─────────────────────────────────────────────────────────


def _valid_subagent_output() -> dict:
    return {
        "status": "PASS",
        "artifact_path": ".renmark/reviews/2026-05-21-abc.review.md",
        "touched_files": ["src/main.py"],
        "sha": "abc123",
        "summary_lines": ["task complete", "tests green"],
        "dependency_notes": "",
        "token_count": 1234,
        "completion_state": "complete",
        "confidence": "high",
        "retry_count": 0,
    }


def test_validate_subagent_output_accepts_valid():
    assert schemas.validate_subagent_output(_valid_subagent_output()) == []


def test_validate_subagent_output_rejects_extra_fields():
    """G11 task isolation: transcript/diff/reasoning leakage MUST be caught."""
    data = _valid_subagent_output()
    data["transcript"] = "this is a transcript leak"
    data["generated_code"] = "def evil(): pass"
    issues = schemas.validate_subagent_output(data)
    assert any("isolation violation" in i.lower() for i in issues)
    assert any("transcript" in i for i in issues)
    assert any("generated_code" in i for i in issues)


def test_validate_subagent_output_rejects_bad_status():
    data = _valid_subagent_output()
    data["status"] = "WIN"
    issues = schemas.validate_subagent_output(data)
    assert any("status" in i for i in issues)


def test_validate_subagent_output_rejects_oversize_summary():
    data = _valid_subagent_output()
    data["summary_lines"] = [f"line {i}" for i in range(10)]
    issues = schemas.validate_subagent_output(data)
    assert any("G3 cap is 5" in i for i in issues)


def test_validate_subagent_output_rejects_oversize_line():
    data = _valid_subagent_output()
    data["summary_lines"] = ["x" * 1500]
    issues = schemas.validate_subagent_output(data)
    assert any("1200" in i for i in issues)


def test_validate_subagent_output_rejects_missing_required():
    data = _valid_subagent_output()
    del data["status"]
    issues = schemas.validate_subagent_output(data)
    assert any("status" in i and "missing" in i for i in issues)


# ── artifact metadata ───────────────────────────────────────────────────────


def _valid_artifact() -> dict:
    return {
        "artifact_type": "verification",
        "schema_version": "1",
        "created_at": "2026-05-21T00:00:00+00:00",
        "source_sha": "abc123",
        "related_plan": ".renmark/plans/demo.plan.md",
        "generator": "renmark.verify",
        "stale_after": None,
        "dependency_refs": [],
        "completion_state": "complete",
        "confidence": "high",
        "validation_status": "validated",
        "retry_count": 0,
        "parser_success": True,
        "schema_compliance": True,
    }


def test_validate_artifact_accepts_valid():
    assert schemas.validate_artifact_metadata(_valid_artifact()) == []


def test_validate_artifact_rejects_bad_confidence():
    data = _valid_artifact()
    data["confidence"] = "very-high"
    issues = schemas.validate_artifact_metadata(data)
    assert any("confidence" in i for i in issues)


def test_validate_artifact_rejects_bad_completion_state():
    data = _valid_artifact()
    data["completion_state"] = "partly"
    issues = schemas.validate_artifact_metadata(data)
    assert any("completion_state" in i for i in issues)


# ── CLI ─────────────────────────────────────────────────────────────────────


def test_cli_validates_lifecycle_file(tmp_path: Path):
    path = tmp_path / "lifecycle.json"
    path.write_text(json.dumps(_valid_lifecycle()))
    exit_code = schemas.main(["lifecycle", str(path)])
    assert exit_code == 0


def test_cli_fails_on_bad_lifecycle_file(tmp_path: Path):
    path = tmp_path / "lifecycle.json"
    bad = _valid_lifecycle()
    bad["stage"] = "nonsense"
    path.write_text(json.dumps(bad))
    exit_code = schemas.main(["lifecycle", str(path)])
    assert exit_code == 1


def test_cli_rejects_unknown_kind():
    exit_code = schemas.main(["bogus", "/tmp/x"])
    assert exit_code == 2


def test_cli_reports_missing_file():
    exit_code = schemas.main(["lifecycle", "/nonexistent/path/lifecycle.json"])
    assert exit_code == 2


def test_cli_subagent_catches_isolation_leak(tmp_path: Path):
    """End-to-end: bad SubagentOutput JSON → exit 1 with leak message."""
    path = tmp_path / "sub.json"
    leaky = _valid_subagent_output()
    leaky["transcript"] = "leak"
    path.write_text(json.dumps(leaky))
    exit_code = schemas.main(["subagent", str(path)])
    assert exit_code == 1

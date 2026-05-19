"""Unit tests for G11 task-isolation contract in dispatch.py."""
from __future__ import annotations

import json

import pytest

from renmark.dispatch import (
    IsolationViolation,
    SubagentInput,
    SubagentOutput,
    SUBAGENT_OUTPUT_FIELDS,
    build_subagent_input,
    dispatch_task_isolated,
    parse_subagent_response,
)
from renmark.parser import Task


def make_task(**overrides):
    """Construct a minimal Task for testing."""
    defaults = dict(
        index=1, title="t", mode="A", target="src/foo.py",
        context_files=[], executor="codex", complexity="simple",
        parallel_group=None, verifier="echo ok", spec="implement foo",
        est_tokens=None, est_cost_usd=None,
    )
    defaults.update(overrides)
    return Task(**defaults)


# ── SubagentInput ─────────────────────────────────────────────────────────────


def test_subagent_input_serializes_to_json() -> None:
    inp = SubagentInput(
        task_spec="implement foo",
        required_files=["src/foo.py"],
        upstream_artifact_pointers=[".renmark/specs/x.spec.md"],
        dependency_summaries=["task 5 exports getUser()"],
        verifier_expectations="pytest tests/test_foo.py",
    )
    payload = json.loads(inp.to_json())
    assert payload["task_spec"] == "implement foo"
    assert payload["required_files"] == ["src/foo.py"]
    assert payload["dependency_summaries"] == ["task 5 exports getUser()"]


def test_build_subagent_input_bounds_inputs() -> None:
    task = make_task(target="src/a.py", context_files=["src/b.py", "src/c.py"], spec="do thing")
    inp = build_subagent_input(task, dependency_summaries=["x"], upstream_artifact_pointers=["y"])
    assert inp.task_spec == "do thing"
    assert "src/a.py" in inp.required_files
    assert "src/b.py" in inp.required_files
    assert inp.dependency_summaries == ["x"]
    assert inp.upstream_artifact_pointers == ["y"]
    assert inp.verifier_expectations == "echo ok"


# ── SubagentOutput ────────────────────────────────────────────────────────────


def test_subagent_output_valid() -> None:
    out = SubagentOutput(
        status="PASS", artifact_path=".renmark/state/escalations/task-1/",
        summary_lines=["added auth", "tests pass"], token_count=500,
    )
    assert out.status == "PASS"
    assert out.completion_state == "complete"  # default


def test_subagent_output_rejects_too_many_summary_lines() -> None:
    with pytest.raises(IsolationViolation):
        SubagentOutput(
            status="PASS", artifact_path="x",
            summary_lines=["a", "b", "c", "d", "e", "f"],  # 6 lines
        )


def test_subagent_output_rejects_bad_status() -> None:
    with pytest.raises(IsolationViolation):
        SubagentOutput(status="MAYBE", artifact_path="x")  # type: ignore[arg-type]


def test_subagent_output_rejects_bad_completion_state() -> None:
    with pytest.raises(IsolationViolation):
        SubagentOutput(
            status="PASS", artifact_path="x",
            completion_state="kinda-done",  # type: ignore[arg-type]
        )


def test_subagent_output_rejects_bad_confidence() -> None:
    with pytest.raises(IsolationViolation):
        SubagentOutput(
            status="PASS", artifact_path="x",
            confidence="yolo",  # type: ignore[arg-type]
        )


# ── parse_subagent_response ───────────────────────────────────────────────────


def test_parse_response_dict() -> None:
    payload = {
        "status": "PASS", "artifact_path": "x",
        "summary_lines": ["a", "b"], "dependency_notes": "exports X",
        "token_count": 100,
    }
    out = parse_subagent_response(payload)
    assert out.status == "PASS"
    assert out.dependency_notes == "exports X"


def test_parse_response_json_string() -> None:
    payload = json.dumps({
        "status": "PASS", "artifact_path": "x", "summary_lines": ["a"],
    })
    out = parse_subagent_response(payload)
    assert out.status == "PASS"


def test_parse_response_rejects_inline_transcript() -> None:
    """The core G11 enforcement — transcripts must NOT cross the boundary."""
    payload = {
        "status": "PASS", "artifact_path": "x",
        "summary_lines": ["done"],
        "transcript": "Here's everything I thought about and 500 lines of generated code...",
    }
    with pytest.raises(IsolationViolation) as exc_info:
        parse_subagent_response(payload)
    assert "transcript" in str(exc_info.value)


def test_parse_response_rejects_inline_diff() -> None:
    payload = {
        "status": "PASS", "artifact_path": "x", "summary_lines": ["done"],
        "diff": "--- a/foo.py\n+++ b/foo.py\n@@ ...",
    }
    with pytest.raises(IsolationViolation):
        parse_subagent_response(payload)


def test_parse_response_rejects_inline_generated_code() -> None:
    payload = {
        "status": "PASS", "artifact_path": "x", "summary_lines": ["done"],
        "generated_code": "def foo(): pass\n",
    }
    with pytest.raises(IsolationViolation):
        parse_subagent_response(payload)


def test_parse_response_rejects_inline_reasoning() -> None:
    payload = {
        "status": "PASS", "artifact_path": "x", "summary_lines": ["done"],
        "reasoning": "I thought about it like this...",
    }
    with pytest.raises(IsolationViolation):
        parse_subagent_response(payload)


def test_parse_response_missing_required_fields() -> None:
    with pytest.raises(IsolationViolation) as exc_info:
        parse_subagent_response({"summary_lines": ["done"]})
    assert "status" in str(exc_info.value) or "artifact_path" in str(exc_info.value)


def test_parse_response_invalid_json_string() -> None:
    with pytest.raises(IsolationViolation):
        parse_subagent_response("not json {{{")


def test_parse_response_non_dict_top_level() -> None:
    with pytest.raises(IsolationViolation):
        parse_subagent_response("[1, 2, 3]")


def test_subagent_output_fields_match_dataclass() -> None:
    """Schema drift guard: SUBAGENT_OUTPUT_FIELDS must match the dataclass exactly."""
    from dataclasses import fields
    dc_fields = {f.name for f in fields(SubagentOutput)}
    assert dc_fields == SUBAGENT_OUTPUT_FIELDS


# ── dispatch_task_isolated ────────────────────────────────────────────────────


def test_dispatch_task_isolated_happy_path() -> None:
    task = make_task(spec="implement foo")

    def fake_runner(inp: SubagentInput) -> dict:
        # Verify the runner ONLY sees bounded input fields.
        assert inp.task_spec == "implement foo"
        assert inp.required_files
        return {
            "status": "PASS", "artifact_path": ".renmark/state/escalations/task-1/",
            "touched_files": ["src/foo.py"], "sha": "abc123",
            "summary_lines": ["implemented foo"], "dependency_notes": "exports foo()",
            "token_count": 250, "completion_state": "complete",
            "confidence": "high", "retry_count": 0,
        }

    out = dispatch_task_isolated(task, subagent_runner=fake_runner)
    assert out.status == "PASS"
    assert out.sha == "abc123"
    assert out.summary_lines == ["implemented foo"]


def test_dispatch_task_isolated_refuses_leaky_runner() -> None:
    task = make_task()

    def leaky_runner(inp: SubagentInput) -> dict:
        return {
            "status": "PASS", "artifact_path": "x",
            "summary_lines": ["done"],
            "full_generated_code": "thousands of lines here...",  # LEAK
        }

    with pytest.raises(IsolationViolation):
        dispatch_task_isolated(task, subagent_runner=leaky_runner)


def test_dispatch_task_isolated_passes_dependency_summaries() -> None:
    task = make_task(spec="extend X")

    captured: dict = {}
    def capturing_runner(inp: SubagentInput) -> dict:
        captured["deps"] = inp.dependency_summaries
        captured["pointers"] = inp.upstream_artifact_pointers
        return {
            "status": "PASS", "artifact_path": "x", "summary_lines": ["done"],
        }

    dispatch_task_isolated(
        task,
        dependency_summaries=["task 5 exports getUser()", "task 7 exports getOrder()"],
        upstream_artifact_pointers=[".renmark/specs/x.spec.md"],
        subagent_runner=capturing_runner,
    )
    assert captured["deps"] == ["task 5 exports getUser()", "task 7 exports getOrder()"]
    assert captured["pointers"] == [".renmark/specs/x.spec.md"]

"""End-to-end dispatch isolation: feed realistic adversarial subagent
responses through parse_subagent_response and assert G11 enforcement.

This is more end-to-end than test_dispatch_isolation.py because the
mock subagent_runner returns content shaped exactly like what a real
codex or Agent subprocess would produce, including the failure modes
that have actually been observed."""

from __future__ import annotations

import json

import pytest

from renmark.dispatch import (
    IsolationViolation,
    SubagentInput,
    build_subagent_input,
    dispatch_task_isolated,
)
from renmark.parser import Task


def _task() -> Task:
    return Task(
        index=1,
        title="t",
        mode="A",
        target="src/x.py",
        spec="do a thing",
        verifier="true",
        executor="codex",
    )


# ── Pristine path ────────────────────────────────────────────────────────────


def test_pristine_response_round_trips():
    def runner(inp: SubagentInput) -> dict:
        return {
            "status": "PASS",
            "artifact_path": ".renmark/reviews/x.review.md",
            "touched_files": ["src/x.py"],
            "summary_lines": ["wrote constant", "verifier green"],
            "token_count": 1234,
        }

    out = dispatch_task_isolated(_task(), subagent_runner=runner)
    assert out.status == "PASS"
    assert out.summary_lines == ["wrote constant", "verifier green"]


# ── Adversarial: real leakage patterns ───────────────────────────────────────


@pytest.mark.parametrize(
    "leaked_field,leaked_value",
    [
        ("transcript", "USER: ...\nASSISTANT: ..."),
        ("generated_code", "def evil():\n    pass\n"),
        ("diff", "@@ -1 +1 @@\n-x\n+y\n"),
        ("reasoning", "I will now think step by step..."),
        ("conversation", [{"role": "user"}, {"role": "assistant"}]),
        ("raw_output", "...long output dump..."),
        ("trace", "stack trace stuff"),
    ],
)
def test_extra_field_raises_isolation_violation(leaked_field, leaked_value):
    def runner(inp):
        return {
            "status": "PASS",
            "artifact_path": "x.md",
            "summary_lines": ["ok"],
            leaked_field: leaked_value,  # the leak
        }

    with pytest.raises(IsolationViolation):
        dispatch_task_isolated(_task(), subagent_runner=runner)


def test_string_json_response_is_parsed():
    def runner(inp):
        return json.dumps(
            {
                "status": "PASS",
                "artifact_path": "x.md",
                "summary_lines": ["ok"],
            }
        )

    out = dispatch_task_isolated(_task(), subagent_runner=runner)
    assert out.status == "PASS"


def test_oversize_summary_raises():
    def runner(inp):
        return {
            "status": "PASS",
            "artifact_path": "x.md",
            "summary_lines": [f"line {i}" for i in range(10)],  # > G3 cap
        }

    with pytest.raises(IsolationViolation):
        dispatch_task_isolated(_task(), subagent_runner=runner)


def test_invalid_status_raises():
    def runner(inp):
        return {"status": "WIN", "artifact_path": "x.md", "summary_lines": []}

    with pytest.raises(IsolationViolation):
        dispatch_task_isolated(_task(), subagent_runner=runner)


def test_failing_subagent_still_contracts():
    """Even a failing subagent must produce a valid SubagentOutput."""

    def runner(inp):
        return {
            "status": "FAIL",
            "artifact_path": "x.md",
            "summary_lines": ["verifier exited 1", "stderr: AssertionError"],
            "completion_state": "failed",
            "retry_count": 1,
        }

    out = dispatch_task_isolated(_task(), subagent_runner=runner)
    assert out.status == "FAIL"
    assert out.completion_state == "failed"
    assert out.retry_count == 1


def test_subagent_input_does_not_carry_orchestrator_context():
    """SubagentInput must contain ONLY sanctioned bounded fields — no
    orchestrator transcripts or session metadata leaks downstream.

    ``required_skills`` (AC5 / REQ-20) is a deliberate, bounded addition: it
    carries required-skill *metadata* (name + pointer), never full skill bodies,
    and is guarded at build time by ``context.assert_metadata_only``. It is a
    sanctioned field, not a leak — hence it is in ``allowed``."""
    inp = build_subagent_input(_task())
    allowed = {
        "task_spec",
        "required_files",
        "upstream_artifact_pointers",
        "dependency_summaries",
        "verifier_expectations",
        "required_skills",
    }
    d = inp.to_dict()
    extra = set(d.keys()) - allowed
    assert not extra, f"SubagentInput leaked fields: {extra}"

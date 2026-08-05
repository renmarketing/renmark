"""
---
artifact_type: renmark_task_output
schema_version: 1
created_at: 2026-08-05T00:00:00Z
source_sha: unknown
related_plan: "Release 3 Task 5: cross-entry-point work-order funnel test"
generator: codex
stale_after: null
dependency_refs:
  - renmark/dispatch.py
  - renmark/ledger.py
  - renmark/parser.py
completion_state: complete
confidence: medium
validation_status: unvalidated
retry_count: 0
parser_success: true
schema_compliance: true
---

Regression tests for the Release 3 work-order funnel wiring.

## Summary
- Proves `build_subagent_input` calls `ledger.work_order_for_task` exactly once per dispatch.
- Guards the three wrapper entry points against regressing their public output shapes.
- Verifies every Release 3 `WorkOrder` field is present with the documented defaults.
"""

from __future__ import annotations

from dataclasses import fields
from pathlib import Path

from renmark import dispatch, ledger
from renmark.parser import Task


def _task() -> Task:
    return Task(
        index=1,
        title="wire funnel",
        mode="A",
        target="src/example.py",
        verifier="python -m pytest -q",
        spec="exercise the work-order funnel",
        executor="sonnet",
        complexity="medium",
    )


def test_build_subagent_input_and_wrappers_route_through_work_order_funnel(
    monkeypatch,
) -> None:
    task = _task()
    calls: list[tuple[str, str]] = []

    def spy_work_order_for_task(task_obj: Task, role: str, *, order_id=None, **kwargs):
        calls.append((task_obj.spec, role))
        return ledger.WorkOrder(
            order_id=order_id or "task-1",
            task=task_obj.spec,
            role=role,
            file_scope=[task_obj.target, *task_obj.context_files],
            verifier=task_obj.verifier,
            **kwargs,
        )

    monkeypatch.setattr(ledger, "work_order_for_task", spy_work_order_for_task)

    inp = dispatch.build_subagent_input(task)
    assert calls == [(task.spec, inp.role)]
    assert inp.task_spec == task.spec
    assert inp.required_files == [task.target]

    fanout = dispatch.build_workflow_fanout_args([task])
    assert calls[-1] == (task.spec, inp.role)
    assert len(calls) == 2
    assert fanout == [
        {
            "task_spec": task.spec,
            "required_files": [task.target],
            "upstream_artifact_pointers": [],
            "dependency_summaries": [],
            "verifier_expectations": task.verifier,
            "required_skills": [],
            "role": inp.role,
            "agent_type": fanout[0]["agent_type"],
        }
    ]

    plan = dispatch.build_host_dispatch_plan([task], host="claude")
    assert len(calls) == 3
    assert plan.host == "claude"
    assert plan.strategy == "single"
    assert plan.task_packets == (inp.to_dict(),)
    assert plan.calls[0].tool == "Agent"

    def stub_runner(subagent_input: dispatch.SubagentInput) -> dict[str, object]:
        assert subagent_input.task_spec == task.spec
        return {
            "status": "PASS",
            "artifact_path": "artifacts/work-order.md",
            "touched_files": [],
            "sha": None,
            "summary_lines": [],
            "dependency_notes": "",
            "token_count": 0,
            "completion_state": "complete",
            "confidence": "medium",
            "retry_count": 0,
            "validation_status": "validated",
            "parser_success": True,
            "schema_compliance": True,
        }

    out = dispatch.dispatch_task_isolated(task, subagent_runner=stub_runner)
    assert len(calls) == 4
    assert out.status == "PASS"
    assert out.artifact_path == "artifacts/work-order.md"
    assert out.validation_status == "validated"


def test_work_order_schema_matches_release_3_defaults() -> None:
    order = ledger.WorkOrder()
    field_names = [field.name for field in fields(ledger.WorkOrder)]

    assert field_names == [
        "order_id",
        "task",
        "role",
        "file_scope",
        "verifier",
        "is_repair",
        "repairs_finding_ref",
        "risk_tier",
        "capability_envelope_ref",
        "lens",
        "schema_version",
        "correlation_id",
        "idempotency_key",
        "dependencies",
        "scope",
        "budget",
        "routing",
        "constraints",
        "interaction_policy",
    ]
    assert order.risk_tier is None
    order.risk_tier = "triage"
    assert order.risk_tier == "triage"
    assert order.capability_envelope_ref is None
    assert order.lens is None
    assert order.schema_version == 1
    assert order.correlation_id is None
    assert order.idempotency_key is None
    assert order.dependencies == []
    assert order.scope is None
    assert order.budget is None
    assert order.routing is None
    assert order.constraints is None
    assert order.interaction_policy is None

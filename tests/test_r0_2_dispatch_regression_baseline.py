"""R-0.2/WP-4 dispatch/gating regression baseline.

Pins TODAY's (pre-WP-5) behavior for the five shapes WP-1/WP-2/WP-3's design
docs identify as the "before" picture their later implementation work
(WP-5) will change:

1. Normal-path ``build_agent_dispatch()`` carries no ``scope`` (unscoped /
   no ``verify_worker_scope`` enforcement) — WP-1 will generalize scope.
2. ``plugin/agents/reviewer.md``'s current declared ``tools:`` allowlist
   still includes ``Write`` — WP-2a will remove Write/Edit.
3. ``renmark/subagent_gate.py::justify_task``'s current justification
   verdict shape, before WP-2b adds reason/scope/budget fields.
4. ``renmark/program_driver.py::decide_milestone_execution``'s current
   third-equivalent-repair cap and its current (non-)wiring — WP-3 will
   generalize it across dispatch paths.
5. R-0.1's fast-path behavior stays intact (``tests/test_fast_path.py``
   still passes) — this file adds baselines, it does not touch fast-path
   code.

Per the R-0.2 contract's ``allowed_paths``/``prohibited_paths`` (still
``[]``/``renmark/**``+``plugin/**`` at WP-4 time), this file is a pure
addition under ``tests/`` — same amendment precedent as R-0.1/WP-3, which
added ``tests/test_r0_1_ux_regression_baseline.py`` before ``allowed_paths``
named it explicitly. No file outside ``tests/test_r0_2_dispatch_regression_
baseline.py`` is created or modified by this work package.

WP-5 must not change any assertion in this file for these "before" shapes
without a corresponding, deliberate update explaining why the baseline
moved.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from renmark.program import Program, StageNode, TaskNode
from renmark.program_driver import MilestoneDecision, StopReason, decide_milestone_execution
from renmark.providers import claude_agent
from renmark.parser import Task
from renmark.subagent_gate import justify_task

REPO_ROOT = Path(__file__).resolve().parents[1]


def _task(
    idx: int,
    target: str,
    executor: str = "sonnet",
    complexity: str = "medium",
) -> Task:
    return Task(
        index=idx,
        title=f"task {idx}",
        mode="M",
        target=target,
        context_files=[],
        verifier="pytest",
        verifier_timeout_s=60,
        spec="spec " * 20,
        executor=executor,
        complexity=complexity,
    )


# ── Shape 1: normal-path dispatch carries no scope today ────────────────────


def test_build_agent_dispatch_has_no_scope_today() -> None:
    """Pre-WP-5: build_agent_dispatch() (normal, non-fast-path path) never
    populates AgentDispatch.scope. Its absence is exactly what tells a
    caller today that no post-hoc verify_worker_scope check applies to a
    normal-path dispatch — the gap WP-1's design doc documents and WP-5
    will (optionally) close."""
    task = _task(1, "renmark/dispatch.py")
    dispatch = claude_agent.build_agent_dispatch(task, REPO_ROOT)

    assert dispatch.scope is None
    assert "declared scope" not in dispatch.prompt.lower()
    assert "verify_worker_scope" not in dispatch.prompt


def test_agent_dispatch_scope_field_exists_but_defaults_none() -> None:
    """The AgentDispatch dataclass already carries an optional ``scope``
    field (added ahead of R-0.2 for the fast path); pin that it is
    Optional and defaults to None so a future normal-path population is a
    backward-compatible amendment, not a breaking one."""
    field_names = {f.name for f in claude_agent.AgentDispatch.__dataclass_fields__.values()}
    assert "scope" in field_names
    default = claude_agent.AgentDispatch.__dataclass_fields__["scope"].default
    assert default is None


# ── Shape 2: reviewer.md's tools: allowlist ──────────────────────────────────


def test_reviewer_agent_tools_allowlist_excludes_write_and_edit() -> None:
    """WP-5 deliberately moved this baseline: reviewer.md's frontmatter
    ``tools:`` line no longer includes Write (Edit was already absent), per
    ADR-046 / R-006 (inspector/repair separation). This pins the "after"
    picture — an Inspector-role dispatch can no longer call Write/Edit at
    all, structurally enforced by the host's tool allowlist."""
    reviewer_md = REPO_ROOT / "plugin" / "agents" / "reviewer.md"
    text = reviewer_md.read_text(encoding="utf-8")
    lines = [line for line in text.splitlines() if line.startswith("tools:")]
    assert len(lines) == 1
    tools_line = lines[0]
    tools = {t.strip() for t in tools_line.removeprefix("tools:").split(",")}

    assert tools == {"Read", "Grep", "Glob", "Bash"}
    assert "Write" not in tools
    assert "Edit" not in tools


# ── Shape 3: subagent_gate.py's current justification behavior ──────────────


def test_justify_task_medium_complexity_verdict_shape_today() -> None:
    """Pin today's SubagentVerdict shape for a representative medium-
    complexity task, before WP-2b adds mechanical reason/scope/budget
    requirements to the gate."""
    task = _task(1, "src/a.py", complexity="medium")
    verdict = justify_task(task)

    assert verdict.needs_subagent is True
    assert verdict.role == "code-implementer"
    assert verdict.tier == "sonnet"
    assert verdict.challenge is None
    assert verdict.challenge_code == ""
    # Today's verdict carries no reason/scope/budget requirement fields.
    assert not hasattr(verdict, "budget")
    assert not hasattr(verdict, "declared_scope")


def test_justify_task_general_purpose_without_role_reason_is_challenged_today() -> None:
    """Pin today's sole "missing justification" signal: an unscoped
    general-purpose role with no role_reason. WP-2b generalizes this into
    a mechanical reason+scope+budget gate; today only role_reason is
    checked, and only for general-purpose."""
    task = {
        "index": 1,
        "target": "misc/thing.py",
        "executor": "sonnet",
        "complexity": "medium",
        "role": "general-purpose",
    }
    verdict = justify_task(task)

    assert verdict.role == "general-purpose"
    assert verdict.challenge_code == "missing_role_reason"
    assert verdict.challenge is not None


# ── Shape 4: program_driver.py's current recurrence/repair cap scope ────────


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


def test_decide_milestone_execution_blocks_third_equivalent_repair_today(tmp_path) -> None:
    """Pin the CURRENT third-equivalent-repair cap: decide_milestone_
    execution() itself already enforces the recurrence-ledger stop after
    two repairs, regardless of dispatch path — WP-3 will generalize its
    *wiring* (which paths actually call it), not this core behavior."""
    program = _milestone_program()
    failed = _fresh_failed_metadata()

    first = decide_milestone_execution(program, "build", failed, repo=str(tmp_path))
    second = decide_milestone_execution(program, "build", failed, repo=str(tmp_path))
    third = decide_milestone_execution(program, "build", failed, repo=str(tmp_path))

    assert first.action == second.action == "repair"
    assert third == MilestoneDecision("stop", False, StopReason.RETRY_EXHAUSTED)


def test_decide_milestone_execution_not_wired_into_normal_dispatch_paths_today() -> None:
    """Pin today's scope of applicability: decide_milestone_execution is a
    generic, path-agnostic function (no fast-path-only guard inside it),
    but it is NOT called from renmark/providers/claude_agent.py (the
    normal Claude-model dispatch composer) — its only production callers
    today are the orchestrate skill's own instructions
    (plugin/skills/orchestrate/SKILL.md), not renmark/fast_path.py or
    renmark/providers/claude_agent.py directly. This confirms the cap is
    not mechanically fast-path-exclusive in program_driver.py itself, but
    is also not yet uniformly wired into every dispatch path — exactly the
    gap WP-3's generalization targets."""
    driver_src = (REPO_ROOT / "renmark" / "program_driver.py").read_text(encoding="utf-8")
    claude_agent_src = (REPO_ROOT / "renmark" / "providers" / "claude_agent.py").read_text(
        encoding="utf-8"
    )
    fast_path_src = (REPO_ROOT / "renmark" / "fast_path.py").read_text(encoding="utf-8")

    # decide_milestone_execution's own body has no fast-path branch/guard.
    assert "fast_path" not in driver_src
    assert "fast-path" not in driver_src.lower()

    # Neither the normal-path dispatch composer nor fast_path.py itself
    # calls the recurrence gate directly today.
    assert "decide_milestone_execution" not in claude_agent_src
    assert "pre_attempt" not in claude_agent_src
    assert "decide_milestone_execution" not in fast_path_src
    assert "pre_attempt" not in fast_path_src


# ── Shape 5: R-0.1 fast-path behavior stays intact ───────────────────────────


def test_fast_path_suite_still_passes() -> None:
    """This baseline file adds regression coverage; it must never be the
    thing that breaks R-0.1's fast-path suite. Re-run it live rather than
    asserting anything about its content."""
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "tests/test_fast_path.py"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stdout[-4000:] + result.stderr[-2000:]

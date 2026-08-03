from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from renmark import memory
from renmark.parser import parse_plan
from renmark.plan_lint import escalation_reason_for, lint_plan

_BASE_HEADER = "# Test Plan\n\n## Tasks\n\n"


def _write(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "plan.md"
    path.write_text(body, encoding="utf-8")
    return path


def _task(
    *,
    index: int = 1,
    title: str = "do something",
    executor: str = "sonnet",
    complexity: str = "medium",
    target: str = "a.py",
    verifier: str = "true",
    spec: str = "  noop\n",
    role: str | None = None,
    extra_fields: str = "",
) -> str:
    lines = [
        f"### Task {index}: {title}\n",
        "- **mode:** A\n",
        f"- **target:** {target}\n",
        f"- **executor:** {executor}\n",
    ]
    if role is not None:
        lines.append(f"- **role:** {role}\n")
    lines.append(f"- **complexity:** {complexity}\n")
    if extra_fields:
        lines.append(extra_fields)
    lines.append(f"- **verifier:** {verifier}\n")
    lines.append("- **spec:**\n")
    lines.append(spec)
    return "".join(lines)


def _first_task(plan_path: Path):
    return parse_plan(plan_path)[0]


def _routing_line(repo: Path) -> str:
    text = (repo / ".renmark" / "memory" / "routing.md").read_text(encoding="utf-8")
    return next(
        line
        for line in text.splitlines()
        if "target=tests/**, complexity=medium" in line and "run=20260512-100000-abcd" in line
    )


def test_opus_without_justification_warns_and_mentions_model_routing(tmp_path: Path) -> None:
    plan = _write(tmp_path, _BASE_HEADER + _task(executor="opus", complexity="simple"))

    report = lint_plan(plan)

    assert report.verdict == "WARN"
    assert len(report.issues) == 1
    assert "model-routing.md" in report.issues[0]
    assert not any(issue.startswith("BLOCK") for issue in report.issues)


def test_opus_hard_state_machine_is_justified(tmp_path: Path) -> None:
    plan = _write(
        tmp_path,
        _BASE_HEADER
        + _task(
            executor="opus",
            complexity="hard",
            spec="  state machine refactor with bounded transitions\n",
        ),
    )

    task = _first_task(plan)

    assert escalation_reason_for(task) is None
    report = lint_plan(plan)
    assert report.verdict == "PASS"
    assert report.issues == []


def test_opus_reviewer_role_is_justified(tmp_path: Path) -> None:
    plan = _write(
        tmp_path,
        _BASE_HEADER
        + _task(
            executor="opus",
            complexity="simple",
            role="reviewer",
        ),
    )

    task = _first_task(plan)

    assert escalation_reason_for(task) is None
    report = lint_plan(plan)
    assert report.verdict == "PASS"
    assert report.issues == []


@pytest.mark.parametrize("executor", ["sonnet", "codex", "haiku", "fable"])
def test_non_opus_executors_skip_check_12(tmp_path: Path, executor: str) -> None:
    plan = _write(
        tmp_path,
        _BASE_HEADER
        + _task(
            executor=executor,
            complexity="medium",
        ),
    )

    task = _first_task(plan)

    assert escalation_reason_for(task) is None


def test_check_plan_regression_guard_warn_only(tmp_path: Path) -> None:
    plan = _write(tmp_path, _BASE_HEADER + _task(executor="opus", complexity="simple"))

    report = lint_plan(plan)
    assert report.verdict == "WARN"
    assert len(report.issues) == 1
    assert report.issues[0].startswith("WARN:")
    assert "model-routing.md" in report.issues[0]

    result = subprocess.run(
        [sys.executable, "-m", "renmark.plan_lint", str(plan)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "WARN (review before running):" in result.stdout
    assert "BLOCK (must fix before running):" not in result.stdout


def test_append_routing_escalation_reason_preserves_existing_output(tmp_path: Path) -> None:
    base_repo = tmp_path / "base"
    escalated_repo = tmp_path / "escalated"

    kwargs = {
        "signature": "target=tests/**, complexity=medium",
        "executor": "codex",
        "outcome": "passed",
        "run_id": "20260512-100000-abcd",
        "date": "2026-05-12",
    }

    memory.append_routing(base_repo, **kwargs)
    memory.append_routing(escalated_repo, **kwargs, escalation_reason="architecture review")

    plain_line = _routing_line(base_repo)
    escalated_line = _routing_line(escalated_repo)

    assert plain_line == (
        "- (2026-05-12) `target=tests/**, complexity=medium` → **codex** "
        "(passed, run=20260512-100000-abcd)"
    )
    assert "escalation=" not in plain_line
    assert escalated_line == plain_line[:-1] + ", escalation=architecture review)"

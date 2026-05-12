"""Unit tests for renmark.parser."""
from __future__ import annotations

from pathlib import Path

import pytest

from renmark.parser import PlanError, parse_plan

FIXTURES = Path(__file__).parent / "fixtures"


def _write(tmp_path: Path, body: str) -> Path:
    p = tmp_path / "plan.md"
    p.write_text(body, encoding="utf-8")
    return p


def test_simple_plan_parses() -> None:
    tasks = parse_plan(FIXTURES / "simple-plan.md")
    assert len(tasks) == 2
    t1, t2 = tasks
    assert t1.index == 1
    assert t1.mode == "A"
    assert t1.target == "src/constants.py"
    assert t1.context_files == []
    assert t1.model is None
    assert t1.verifier.startswith("python -c")
    assert "PI = 3.14" in t1.spec
    assert "E = 2.718" in t1.spec
    assert t1.verifier_timeout_s == 60

    assert t2.mode == "B"
    assert t2.context_files == ["src/app.py", "src/constants.py"]
    assert t2.model == "mistralai/codestral-22b-instruct-v0.1"
    assert t2.verifier_timeout_s == 30


def test_mode_c_rejected(tmp_path: Path) -> None:
    plan = _write(
        tmp_path,
        "# X\n\n## Tasks\n\n"
        "### Task 1: bad\n"
        "- **mode:** C\n"
        "- **target:** a.py\n"
        "- **verifier:** true\n"
        "- **spec:**\n"
        "  do something\n",
    )
    with pytest.raises(PlanError, match="mode C"):
        parse_plan(plan)


def test_missing_required_field(tmp_path: Path) -> None:
    plan = _write(
        tmp_path,
        "# X\n\n## Tasks\n\n"
        "### Task 1: missing verifier\n"
        "- **mode:** A\n"
        "- **target:** a.py\n"
        "- **spec:**\n"
        "  do something\n",
    )
    with pytest.raises(PlanError, match="verifier"):
        parse_plan(plan)


def test_target_traversal_rejected(tmp_path: Path) -> None:
    plan = _write(
        tmp_path,
        "# X\n\n## Tasks\n\n"
        "### Task 1: bad path\n"
        "- **mode:** A\n"
        "- **target:** ../etc/passwd\n"
        "- **verifier:** true\n"
        "- **spec:**\n"
        "  noop\n",
    )
    with pytest.raises(PlanError, match=r"\.\."):
        parse_plan(plan)


def test_absolute_target_rejected(tmp_path: Path) -> None:
    plan = _write(
        tmp_path,
        "# X\n\n## Tasks\n\n"
        "### Task 1: absolute\n"
        "- **mode:** A\n"
        "- **target:** /etc/passwd\n"
        "- **verifier:** true\n"
        "- **spec:**\n"
        "  noop\n",
    )
    with pytest.raises(PlanError, match="absolute"):
        parse_plan(plan)


def test_no_tasks_rejected(tmp_path: Path) -> None:
    plan = _write(tmp_path, "# X\n\nsome prose, no tasks\n")
    with pytest.raises(PlanError, match="no tasks"):
        parse_plan(plan)


def test_non_contiguous_indices_rejected(tmp_path: Path) -> None:
    plan = _write(
        tmp_path,
        "# X\n\n## Tasks\n\n"
        "### Task 1: first\n"
        "- **mode:** A\n"
        "- **target:** a.py\n"
        "- **verifier:** true\n"
        "- **spec:**\n"
        "  noop\n\n"
        "### Task 3: skipped 2\n"
        "- **mode:** A\n"
        "- **target:** b.py\n"
        "- **verifier:** true\n"
        "- **spec:**\n"
        "  noop\n",
    )
    with pytest.raises(PlanError, match="contiguous"):
        parse_plan(plan)


def test_context_files_list_parses(tmp_path: Path) -> None:
    plan = _write(
        tmp_path,
        "# X\n\n## Tasks\n\n"
        "### Task 1: x\n"
        "- **mode:** B\n"
        "- **target:** a.py\n"
        "- **context_files:** [a.py, b.py, \"c d.py\"]\n"
        "- **verifier:** true\n"
        "- **spec:**\n"
        "  noop\n",
    )
    tasks = parse_plan(plan)
    assert tasks[0].context_files == ["a.py", "b.py", "c d.py"]


def test_unknown_field_rejected(tmp_path: Path) -> None:
    plan = _write(
        tmp_path,
        "# X\n\n## Tasks\n\n"
        "### Task 1: x\n"
        "- **mode:** A\n"
        "- **target:** a.py\n"
        "- **bogus:** 1\n"
        "- **verifier:** true\n"
        "- **spec:**\n"
        "  noop\n",
    )
    with pytest.raises(PlanError, match="unknown field"):
        parse_plan(plan)


def test_executor_defaults_to_nim(tmp_path: Path) -> None:
    plan = _write(
        tmp_path,
        "# X\n\n## Tasks\n\n"
        "### Task 1: x\n"
        "- **mode:** A\n"
        "- **target:** a.py\n"
        "- **verifier:** true\n"
        "- **spec:**\n"
        "  noop\n",
    )
    tasks = parse_plan(plan)
    assert tasks[0].executor == "nim"


def test_executor_codex_parses(tmp_path: Path) -> None:
    plan = _write(
        tmp_path,
        "# X\n\n## Tasks\n\n"
        "### Task 1: hard one\n"
        "- **mode:** A\n"
        "- **target:** a.py\n"
        "- **executor:** codex\n"
        "- **verifier:** true\n"
        "- **spec:**\n"
        "  noop\n",
    )
    tasks = parse_plan(plan)
    assert tasks[0].executor == "codex"


def test_executor_invalid_rejected(tmp_path: Path) -> None:
    plan = _write(
        tmp_path,
        "# X\n\n## Tasks\n\n"
        "### Task 1: x\n"
        "- **mode:** A\n"
        "- **target:** a.py\n"
        "- **executor:** claude\n"
        "- **verifier:** true\n"
        "- **spec:**\n"
        "  noop\n",
    )
    with pytest.raises(PlanError, match="executor must be"):
        parse_plan(plan)

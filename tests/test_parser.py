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


def test_executor_defaults_to_codex(tmp_path: Path) -> None:
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
    assert tasks[0].executor == "codex"


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


def test_executor_claude_models_accepted(tmp_path: Path) -> None:
    for ex in ("haiku", "sonnet", "opus"):
        plan = _write(
            tmp_path,
            "# X\n\n## Tasks\n\n"
            "### Task 1: x\n"
            "- **mode:** A\n"
            f"- **target:** a_{ex}.py\n"
            f"- **executor:** {ex}\n"
            "- **verifier:** true\n"
            "- **spec:**\n"
            "  noop\n",
        )
        tasks = parse_plan(plan)
        assert tasks[0].executor == ex


def test_executor_nim_rejected(tmp_path: Path) -> None:
    plan = _write(
        tmp_path,
        "# X\n\n## Tasks\n\n"
        "### Task 1: x\n"
        "- **mode:** A\n"
        "- **target:** a.py\n"
        "- **executor:** nim\n"
        "- **verifier:** true\n"
        "- **spec:**\n"
        "  noop\n",
    )
    with pytest.raises(PlanError, match="executor must be"):
        parse_plan(plan)


def test_executor_provider_string_accepted(tmp_path: Path) -> None:
    plan = _write(
        tmp_path,
        "# X\n\n## Tasks\n\n"
        "### Task 1: ollama task\n"
        "- **mode:** A\n"
        "- **target:** a.py\n"
        "- **executor:** ollama_chat/qwen2.5-coder:7b\n"
        "- **verifier:** true\n"
        "- **spec:**\n"
        "  noop\n",
    )
    tasks = parse_plan(plan)
    assert tasks[0].executor == "ollama_chat/qwen2.5-coder:7b"


def test_complexity_field_parses(tmp_path: Path) -> None:
    plan = _write(
        tmp_path,
        "# X\n\n## Tasks\n\n"
        "### Task 1: hard one\n"
        "- **mode:** A\n"
        "- **target:** a.py\n"
        "- **complexity:** hard\n"
        "- **verifier:** true\n"
        "- **spec:**\n"
        "  noop\n",
    )
    tasks = parse_plan(plan)
    assert tasks[0].complexity == "hard"


def test_complexity_defaults_to_medium(tmp_path: Path) -> None:
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
    assert tasks[0].complexity == "medium"


def test_complexity_invalid_rejected(tmp_path: Path) -> None:
    plan = _write(
        tmp_path,
        "# X\n\n## Tasks\n\n"
        "### Task 1: x\n"
        "- **mode:** A\n"
        "- **target:** a.py\n"
        "- **complexity:** trivial\n"
        "- **verifier:** true\n"
        "- **spec:**\n"
        "  noop\n",
    )
    with pytest.raises(PlanError, match="complexity must be"):
        parse_plan(plan)


def test_parallel_group_field_parses(tmp_path: Path) -> None:
    plan = _write(
        tmp_path,
        "# X\n\n## Tasks\n\n"
        "### Task 1: a\n"
        "- **mode:** A\n"
        "- **target:** a.py\n"
        "- **parallel_group:** 2\n"
        "- **verifier:** true\n"
        "- **spec:**\n"
        "  noop\n\n"
        "### Task 2: b\n"
        "- **mode:** A\n"
        "- **target:** b.py\n"
        "- **parallel_group:** 2\n"
        "- **verifier:** true\n"
        "- **spec:**\n"
        "  noop\n",
    )
    tasks = parse_plan(plan)
    assert tasks[0].parallel_group == 2
    assert tasks[1].parallel_group == 2


def test_parallel_group_non_int_rejected(tmp_path: Path) -> None:
    plan = _write(
        tmp_path,
        "# X\n\n## Tasks\n\n"
        "### Task 1: a\n"
        "- **mode:** A\n"
        "- **target:** a.py\n"
        "- **parallel_group:** wave-one\n"
        "- **verifier:** true\n"
        "- **spec:**\n"
        "  noop\n",
    )
    with pytest.raises(PlanError, match="parallel_group must be int"):
        parse_plan(plan)


def test_est_tokens_and_cost_parse(tmp_path: Path) -> None:
    plan = _write(
        tmp_path,
        "# X\n\n## Tasks\n\n"
        "### Task 1: x\n"
        "- **mode:** A\n"
        "- **target:** a.py\n"
        "- **est_tokens:** 4500\n"
        "- **est_cost_usd:** 0.07\n"
        "- **verifier:** true\n"
        "- **spec:**\n"
        "  noop\n",
    )
    tasks = parse_plan(plan)
    assert tasks[0].est_tokens == 4500
    assert tasks[0].est_cost_usd == 0.07


def test_est_tokens_non_int_rejected(tmp_path: Path) -> None:
    plan = _write(
        tmp_path,
        "# X\n\n## Tasks\n\n"
        "### Task 1: x\n"
        "- **mode:** A\n"
        "- **target:** a.py\n"
        "- **est_tokens:** lots\n"
        "- **verifier:** true\n"
        "- **spec:**\n"
        "  noop\n",
    )
    with pytest.raises(PlanError, match="est_tokens must be int"):
        parse_plan(plan)


def test_serves_field_parses(tmp_path: Path) -> None:
    """The optional PRD-traceability `serves:` field parses onto Task.serves."""
    plan = _write(
        tmp_path,
        "# X\n\n## Tasks\n\n"
        "### Task 1: x\n"
        "- **mode:** A\n"
        "- **target:** a.py\n"
        "- **verifier:** true\n"
        "- **serves:** REQ-3\n"
        "- **spec:**\n"
        "  noop\n",
    )
    tasks = parse_plan(plan)
    assert tasks[0].serves == "REQ-3"


def test_serves_defaults_to_none(tmp_path: Path) -> None:
    """`serves:` is optional — absent means None, never an error."""
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
    assert tasks[0].serves is None

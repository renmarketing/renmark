"""Tests for renmark.plan_lint — pin every check defined in SKILL.md.

Fixture style mirrors tests/test_parser.py: _write() creates a minimal valid
plan file in tmp_path; each test case builds the minimal plan that exercises
one check and asserts on the PlanLintReport verdict / issues.

CLI exit-code tests run a subprocess so they test the __main__ path.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from renmark.plan_lint import PlanLintReport, lint_plan

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_BASE_HEADER = "# Test Plan\n\n## Tasks\n\n"


def _write(tmp_path: Path, body: str) -> Path:
    """Write *body* to tmp_path/plan.md and return the path."""
    p = tmp_path / "plan.md"
    p.write_text(body, encoding="utf-8")
    return p


def _task(
    *,
    index: int = 1,
    title: str = "do something",
    mode: str = "A",
    target: str = "a.py",
    executor: str = "sonnet",
    verifier: str = "true",
    spec: str = "  noop\n",
    parallel_group: int | None = None,
    context_files: str | None = None,
    est_tokens: int | str | None = None,
    extra_fields: str = "",
) -> str:
    """Return a minimal task block string."""
    lines = [
        f"### Task {index}: {title}\n",
        f"- **mode:** {mode}\n",
        f"- **target:** {target}\n",
        f"- **executor:** {executor}\n",
    ]
    if parallel_group is not None:
        lines.append(f"- **parallel_group:** {parallel_group}\n")
    if context_files is not None:
        lines.append(f"- **context_files:** {context_files}\n")
    if est_tokens is not None:
        lines.append(f"- **est_tokens:** {est_tokens}\n")
    if extra_fields:
        lines.append(extra_fields)
    lines.append(f"- **verifier:** {verifier}\n")
    lines.append("- **spec:**\n")
    lines.append(spec)
    return "".join(lines)


def _run_cli(plan_path: Path) -> subprocess.CompletedProcess[str]:
    """Run python -m renmark.plan_lint <path> and return the CompletedProcess."""
    return subprocess.run(
        [sys.executable, "-m", "renmark.plan_lint", str(plan_path)],
        capture_output=True,
        text=True,
    )


# ---------------------------------------------------------------------------
# 1. Valid plan → PASS + CLI exit 0
# ---------------------------------------------------------------------------


def test_valid_plan_pass(tmp_path: Path) -> None:
    plan = _write(tmp_path, _BASE_HEADER + _task())
    report = lint_plan(plan)
    assert report.verdict == "PASS"
    assert report.task_count == 1
    assert report.issues == []


def test_valid_plan_cli_exit_0(tmp_path: Path) -> None:
    plan = _write(tmp_path, _BASE_HEADER + _task())
    result = _run_cli(plan)
    assert result.returncode == 0


# ---------------------------------------------------------------------------
# 2. Missing verifier → BLOCK
# ---------------------------------------------------------------------------


def test_missing_verifier_block(tmp_path: Path) -> None:
    # The parser itself raises PlanError when verifier is absent, so
    # lint_plan must catch it and return BLOCK gracefully.
    body = (
        _BASE_HEADER
        + "### Task 1: no verifier\n"
        "- **mode:** A\n"
        "- **target:** a.py\n"
        "- **executor:** sonnet\n"
        "- **spec:**\n"
        "  noop\n"
    )
    plan = _write(tmp_path, body)
    report = lint_plan(plan)
    assert report.verdict == "BLOCK"
    assert any("BLOCK" in issue for issue in report.issues)


# ---------------------------------------------------------------------------
# 3. 16 tasks → BLOCK
# ---------------------------------------------------------------------------


def test_too_many_tasks_block(tmp_path: Path) -> None:
    tasks_str = ""
    for i in range(1, 17):  # 16 tasks
        tasks_str += _task(index=i, target=f"file_{i}.py")
        if i < 16:
            tasks_str += "\n"
    plan = _write(tmp_path, _BASE_HEADER + tasks_str)
    report = lint_plan(plan)
    assert report.verdict == "BLOCK"
    assert any("16" in issue or "count" in issue.lower() for issue in report.issues)


# ---------------------------------------------------------------------------
# 4. Duplicate target in same parallel_group → BLOCK
# ---------------------------------------------------------------------------


def test_duplicate_target_same_group_block(tmp_path: Path) -> None:
    t1 = _task(index=1, target="shared.py", parallel_group=1)
    t2 = _task(index=2, target="shared.py", parallel_group=1)
    plan = _write(tmp_path, _BASE_HEADER + t1 + "\n" + t2)
    report = lint_plan(plan)
    assert report.verdict == "BLOCK"
    assert any("parallel_group" in issue or "shared.py" in issue for issue in report.issues)


def test_same_target_different_groups_pass(tmp_path: Path) -> None:
    """Same target in different parallel groups is allowed."""
    t1 = _task(index=1, target="shared.py", parallel_group=1)
    t2 = _task(index=2, target="shared.py", parallel_group=2)
    plan = _write(tmp_path, _BASE_HEADER + t1 + "\n" + t2)
    report = lint_plan(plan)
    # No BLOCK from parallel-group check (may have WARN from other checks)
    block_issues = [i for i in report.issues if i.startswith("BLOCK")]
    assert not any("parallel_group" in i for i in block_issues)


# ---------------------------------------------------------------------------
# 5. Invalid executor → BLOCK via parse error
# ---------------------------------------------------------------------------


def test_invalid_executor_block(tmp_path: Path) -> None:
    body = (
        _BASE_HEADER
        + "### Task 1: bad executor\n"
        "- **mode:** A\n"
        "- **target:** a.py\n"
        "- **executor:** claude-3\n"
        "- **verifier:** true\n"
        "- **spec:**\n"
        "  noop\n"
    )
    plan = _write(tmp_path, body)
    report = lint_plan(plan)
    assert report.verdict == "BLOCK"


# ---------------------------------------------------------------------------
# 6. Invalid mode (C) → BLOCK via parse error
# ---------------------------------------------------------------------------


def test_invalid_mode_c_block(tmp_path: Path) -> None:
    body = (
        _BASE_HEADER
        + "### Task 1: bad mode\n"
        "- **mode:** C\n"
        "- **target:** a.py\n"
        "- **verifier:** true\n"
        "- **spec:**\n"
        "  noop\n"
    )
    plan = _write(tmp_path, body)
    report = lint_plan(plan)
    assert report.verdict == "BLOCK"


# ---------------------------------------------------------------------------
# 7. Bad est_tokens type → BLOCK gracefully (parse error caught, no exception)
# ---------------------------------------------------------------------------


def test_bad_est_tokens_type_block_no_exception(tmp_path: Path) -> None:
    body = (
        _BASE_HEADER
        + "### Task 1: bad tokens\n"
        "- **mode:** A\n"
        "- **target:** a.py\n"
        "- **executor:** sonnet\n"
        "- **est_tokens:** lots\n"
        "- **verifier:** true\n"
        "- **spec:**\n"
        "  noop\n"
    )
    plan = _write(tmp_path, body)
    # Must not raise — lint_plan never raises
    report = lint_plan(plan)
    assert isinstance(report, PlanLintReport)
    assert report.verdict == "BLOCK"


# ---------------------------------------------------------------------------
# 8. Empty file → BLOCK verdict, no exception
# ---------------------------------------------------------------------------


def test_empty_file_block_no_exception(tmp_path: Path) -> None:
    plan = _write(tmp_path, "")
    report = lint_plan(plan)
    assert isinstance(report, PlanLintReport)
    assert report.verdict == "BLOCK"


# ---------------------------------------------------------------------------
# 9. Non-plan garbage → BLOCK verdict, no exception
# ---------------------------------------------------------------------------


def test_garbage_file_block_no_exception(tmp_path: Path) -> None:
    plan = _write(tmp_path, "this is just random garbage text\nnot a plan at all\n")
    report = lint_plan(plan)
    assert isinstance(report, PlanLintReport)
    assert report.verdict == "BLOCK"


# ---------------------------------------------------------------------------
# 10. `test -f` only verifier → WARN (not BLOCK)
# ---------------------------------------------------------------------------


def test_test_f_only_verifier_warn(tmp_path: Path) -> None:
    plan = _write(tmp_path, _BASE_HEADER + _task(verifier="test -f a.py"))
    report = lint_plan(plan)
    assert report.verdict == "WARN"
    assert any("existence only" in issue or "test -f" in issue for issue in report.issues)
    # Must NOT be BLOCK for this alone
    block_issues = [i for i in report.issues if i.startswith("BLOCK")]
    assert block_issues == []


# ---------------------------------------------------------------------------
# 11. Unbounded `cat` verifier → WARN
# ---------------------------------------------------------------------------


def test_unbounded_cat_verifier_warn(tmp_path: Path) -> None:
    plan = _write(tmp_path, _BASE_HEADER + _task(verifier="cat output.txt"))
    report = lint_plan(plan)
    assert report.verdict == "WARN"
    assert any("unbounded" in issue or "cat" in issue for issue in report.issues)


# ---------------------------------------------------------------------------
# 12. >80-line spec → WARN
# ---------------------------------------------------------------------------


def test_long_spec_warn(tmp_path: Path) -> None:
    # Build a spec with 81 lines
    long_spec = "  " + "\n  ".join(f"line {i}" for i in range(81)) + "\n"
    plan = _write(tmp_path, _BASE_HEADER + _task(spec=long_spec))
    report = lint_plan(plan)
    assert report.verdict == "WARN"
    assert any("spec" in issue.lower() and "line" in issue.lower() for issue in report.issues)


# ---------------------------------------------------------------------------
# 13. Heavy-read: context_file >200 lines + executor sonnet → BLOCK
# ---------------------------------------------------------------------------


def test_heavy_read_sonnet_block(tmp_path: Path) -> None:
    # Create a context file with 201 lines
    ctx_file = tmp_path / "big_context.md"
    ctx_file.write_text("\n".join(f"line {i}" for i in range(201)), encoding="utf-8")

    # Write plan in the same tmp_path so relative path resolves
    plan_body = (
        _BASE_HEADER
        + "### Task 1: heavy read\n"
        "- **mode:** A\n"
        "- **target:** a.py\n"
        "- **executor:** sonnet\n"
        "- **context_files:** [big_context.md]\n"
        "- **verifier:** true\n"
        "- **spec:**\n"
        "  noop\n"
    )
    plan = _write(tmp_path, plan_body)

    # lint_plan uses Path.cwd() as repo_root — we need to patch it
    import unittest.mock as mock

    with mock.patch("renmark.plan_lint.Path.cwd", return_value=tmp_path):
        report = lint_plan(plan)

    assert report.verdict == "BLOCK"
    assert any("heavy" in issue.lower() or "G5" in issue for issue in report.issues)


def test_heavy_read_haiku_no_block(tmp_path: Path) -> None:
    """haiku is exempt from the heavy-read check."""
    ctx_file = tmp_path / "big_context.md"
    ctx_file.write_text("\n".join(f"line {i}" for i in range(201)), encoding="utf-8")

    plan_body = (
        _BASE_HEADER
        + "### Task 1: heavy read haiku\n"
        "- **mode:** A\n"
        "- **target:** a.py\n"
        "- **executor:** haiku\n"
        "- **context_files:** [big_context.md]\n"
        "- **verifier:** true\n"
        "- **spec:**\n"
        "  noop\n"
    )
    plan = _write(tmp_path, plan_body)

    import unittest.mock as mock

    with mock.patch("renmark.plan_lint.Path.cwd", return_value=tmp_path):
        report = lint_plan(plan)

    block_issues = [i for i in report.issues if i.startswith("BLOCK")]
    assert not any("heavy" in i.lower() or "G5" in i for i in block_issues)


# ---------------------------------------------------------------------------
# 14. Denylist phrase in spec → BLOCK
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "phrase",
    [
        "show me the code",
        "paste the diff",
        "return the contents",
        "include the full",
        "print the file",
        "explain the change in your response",
        "output the code",
    ],
)
def test_denylist_phrase_in_spec_block(tmp_path: Path, phrase: str) -> None:
    spec = f"  Please {phrase} in the output.\n"
    plan = _write(tmp_path, _BASE_HEADER + _task(spec=spec))
    report = lint_plan(plan)
    assert report.verdict == "BLOCK"
    assert any(phrase in issue for issue in report.issues)


def test_denylist_case_insensitive(tmp_path: Path) -> None:
    """Denylist check must be case-insensitive."""
    spec = "  SHOW ME THE CODE when done.\n"
    plan = _write(tmp_path, _BASE_HEADER + _task(spec=spec))
    report = lint_plan(plan)
    assert report.verdict == "BLOCK"


# ---------------------------------------------------------------------------
# 15. Negative est_tokens → WARN
# ---------------------------------------------------------------------------


def test_negative_est_tokens_warn(tmp_path: Path) -> None:
    plan = _write(tmp_path, _BASE_HEADER + _task(est_tokens=-100))
    report = lint_plan(plan)
    assert report.verdict == "WARN"
    assert any("negative" in issue.lower() or "est_tokens" in issue for issue in report.issues)
    block_issues = [i for i in report.issues if i.startswith("BLOCK")]
    assert block_issues == []


# ---------------------------------------------------------------------------
# 16. CLI exit codes
# ---------------------------------------------------------------------------


def test_cli_pass_exit_0(tmp_path: Path) -> None:
    plan = _write(tmp_path, _BASE_HEADER + _task())
    result = _run_cli(plan)
    assert result.returncode == 0
    assert "PASS" in result.stdout


def test_cli_warn_exit_0(tmp_path: Path) -> None:
    """WARN verdict must exit 0 (WARNs can proceed with acknowledgment)."""
    plan = _write(tmp_path, _BASE_HEADER + _task(verifier="test -f a.py"))
    result = _run_cli(plan)
    assert result.returncode == 0
    assert "WARN" in result.stdout


def test_cli_block_exit_1(tmp_path: Path) -> None:
    """BLOCK verdict must exit 1."""
    plan = _write(tmp_path, "")  # empty → BLOCK
    result = _run_cli(plan)
    assert result.returncode == 1


def test_cli_output_format(tmp_path: Path) -> None:
    """CLI output should include the check-plan header format."""
    plan = _write(tmp_path, _BASE_HEADER + _task())
    result = _run_cli(plan)
    assert "check-plan:" in result.stdout
    assert "Tasks:" in result.stdout


# ---------------------------------------------------------------------------
# 17. executor_counts reflects actual executors
# ---------------------------------------------------------------------------


def test_executor_counts_populated(tmp_path: Path) -> None:
    t1 = _task(index=1, target="a.py", executor="haiku")
    t2 = _task(index=2, target="b.py", executor="haiku")
    t3 = _task(index=3, target="c.py", executor="sonnet")
    plan = _write(tmp_path, _BASE_HEADER + t1 + "\n" + t2 + "\n" + t3)
    report = lint_plan(plan)
    assert report.executor_counts.get("haiku") == 2
    assert report.executor_counts.get("sonnet") == 1


# ---------------------------------------------------------------------------
# 18. lint_plan never raises (robustness)
# ---------------------------------------------------------------------------


def test_lint_plan_never_raises_on_nonexistent_file() -> None:
    report = lint_plan("/nonexistent/path/totally-fake-plan.md")
    assert isinstance(report, PlanLintReport)
    assert report.verdict == "BLOCK"


# ---------------------------------------------------------------------------
# 19. Single-source-of-truth pin — both skill files must reference the engine
#
# NOTE: plugin/skills/orchestrate/SKILL.md is being added by a PARALLEL task
# in this same wave (Task 4). If that task has not yet landed, this test will
# fail. The orchestrator verifier runs AFTER the wave, so a mid-wave failure
# here is expected. Do NOT xfail or skip this test.
# ---------------------------------------------------------------------------

_PLUGIN_ROOT = Path(__file__).parent.parent / "plugin" / "skills"
_CHECK_PLAN_SKILL = _PLUGIN_ROOT / "check-plan" / "SKILL.md"
_ORCHESTRATE_SKILL = _PLUGIN_ROOT / "orchestrate" / "SKILL.md"
_ENGINE_INVOCATION = "python -m renmark.plan_lint"


def test_check_plan_skill_references_engine() -> None:
    """check-plan/SKILL.md must contain the literal engine invocation."""
    assert _CHECK_PLAN_SKILL.exists(), f"Missing: {_CHECK_PLAN_SKILL}"
    content = _CHECK_PLAN_SKILL.read_text(encoding="utf-8")
    assert _ENGINE_INVOCATION in content, (
        f"{_CHECK_PLAN_SKILL} does not contain `{_ENGINE_INVOCATION}`. "
        "Task 3 in the plan must add this reference."
    )


def test_orchestrate_skill_references_engine() -> None:
    """orchestrate/SKILL.md must contain the literal engine invocation.

    This test may fail mid-wave if Task 4 (add reference to orchestrate SKILL)
    has not yet completed. That is expected — the orchestrator verifier runs
    after the full wave lands.
    """
    assert _ORCHESTRATE_SKILL.exists(), (
        f"Missing: {_ORCHESTRATE_SKILL} — Task 4 adds this reference; "
        "may be incomplete mid-wave."
    )
    content = _ORCHESTRATE_SKILL.read_text(encoding="utf-8")
    assert _ENGINE_INVOCATION in content, (
        f"{_ORCHESTRATE_SKILL} does not contain `{_ENGINE_INVOCATION}`. "
        "Task 4 in the plan must add this reference."
    )


# ── v0.10.0 codereview refinements (verifier-bound shapes) ─────────────────────


def _one_task_plan(tmp_path, verifier: str):
    return _write(
        tmp_path,
        "# P\n\n### Task 1: t\n- **mode:** A\n- **target:** a.py\n"
        f"- **verifier:** {verifier}\n- **spec:**\n  x\n",
    )


def _warns_of(report):
    return [i for i in report.issues if i.startswith("WARN")]


def test_find_with_name_is_bounded(tmp_path):
    from renmark.plan_lint import lint_plan

    assert not _warns_of(lint_plan(_one_task_plan(tmp_path, "find . -name foo.py | head -3")))
    assert _warns_of(lint_plan(_one_task_plan(tmp_path, "find .")))


def test_git_log_cap_variants_are_bounded(tmp_path):
    from renmark.plan_lint import lint_plan

    for v in ("git log -n 1", "git log -n1", "git log -5", "git log --max-count=1"):
        assert not _warns_of(lint_plan(_one_task_plan(tmp_path, v))), v
    assert _warns_of(lint_plan(_one_task_plan(tmp_path, "git log")))


def test_python_verifier_bound_shapes(tmp_path):
    """SKILL §2.5: node/python printing arbitrary output WARNs unless capped;
    py_compile is the sanctioned bounded form (v0.10.0 codereview fix)."""
    from renmark.plan_lint import lint_plan

    assert _warns_of(lint_plan(_one_task_plan(tmp_path, "python compute_stuff.py")))
    assert _warns_of(lint_plan(_one_task_plan(tmp_path, "node check.js")))
    assert not _warns_of(lint_plan(_one_task_plan(tmp_path, "python3 -m py_compile a.py")))
    assert not _warns_of(lint_plan(_one_task_plan(tmp_path, "python -m pytest -q 2>&1 | tail -1")))

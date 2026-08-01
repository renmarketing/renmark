"""Unit tests for renmark.fast_path — R-0.1/WP-4 implementation.

Includes the literal R-0.0 Scenario C reproduction required by
scope-enforcement-design.md §4: a scope excluding the pre-existing audit
files, against a diff that deletes them, must FAIL.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from renmark import fast_path
from renmark.providers import claude_agent
from renmark.parser import Task


def _task(
    idx: int,
    target: str,
    mode: str = "B",
    context_files: list[str] | None = None,
    verifier: str = "pytest tests/test_x.py::test_y",
) -> Task:
    return Task(
        index=idx,
        title=f"task {idx}",
        mode=mode,
        target=target,
        context_files=context_files or [],
        verifier=verifier,
        verifier_timeout_s=60,
        spec="spec",
        executor="sonnet",
        complexity="simple",
    )


# ── classify_fast_path ────────────────────────────────────────────────────────


def test_classify_fast_path_eligible_single_file() -> None:
    verdict = fast_path.classify_fast_path([_task(1, "tests/test_hosts.py")])
    assert verdict.eligible is True
    assert verdict.failed_signals == ()


def test_classify_fast_path_rejects_too_many_files() -> None:
    tasks = [_task(1, "a.py"), _task(2, "b.py"), _task(3, "c.py")]
    verdict = fast_path.classify_fast_path(tasks)
    assert verdict.eligible is False
    assert "scope_size" in verdict.failed_signals


def test_classify_fast_path_rejects_renmark_target() -> None:
    verdict = fast_path.classify_fast_path([_task(1, "renmark/dispatch.py")])
    assert verdict.eligible is False
    assert "production_target" in verdict.failed_signals


def test_classify_fast_path_rejects_plugin_target() -> None:
    verdict = fast_path.classify_fast_path([_task(1, "plugin/skills/foo/SKILL.md")])
    assert verdict.eligible is False
    assert "production_target" in verdict.failed_signals


def test_classify_fast_path_rejects_cross_file_dependency() -> None:
    verdict = fast_path.classify_fast_path(
        [_task(1, "a.py", context_files=["b.py"]), _task(2, "b.py")]
    )
    assert verdict.eligible is False
    assert "cross_file_dependency" in verdict.failed_signals


def test_classify_fast_path_rejects_chained_verifier() -> None:
    verdict = fast_path.classify_fast_path([_task(1, "a.py", verifier="pytest a.py && pytest b.py")])
    assert verdict.eligible is False
    assert "verifier_not_single_command" in verdict.failed_signals


def test_classify_fast_path_rejects_empty_task_set() -> None:
    verdict = fast_path.classify_fast_path([])
    assert verdict.eligible is False
    assert verdict.failed_signals == ("empty_task_set",)


def test_classify_fast_path_reports_all_failed_signals_not_just_first() -> None:
    verdict = fast_path.classify_fast_path([_task(1, "renmark/x.py", verifier="a && b")])
    assert verdict.eligible is False
    assert "production_target" in verdict.failed_signals
    assert "verifier_not_single_command" in verdict.failed_signals


def test_classification_verdict_reason_strings() -> None:
    ok = fast_path.classify_fast_path([_task(1, "a.py")])
    assert ok.reason() == "all 5 signals passed"
    bad = fast_path.classify_fast_path([_task(1, "renmark/x.py")])
    assert bad.reason() == "failed: production_target"


# ── worker_scope_from_verdict ─────────────────────────────────────────────────


def test_worker_scope_from_verdict_builds_allowed_paths() -> None:
    tasks = [_task(1, "a.py")]
    verdict = fast_path.classify_fast_path(tasks)
    scope = fast_path.worker_scope_from_verdict(verdict, tasks)
    assert scope.allowed_paths == frozenset({"a.py"})


def test_worker_scope_from_verdict_rejects_non_eligible() -> None:
    tasks = [_task(1, "renmark/x.py")]
    verdict = fast_path.classify_fast_path(tasks)
    with pytest.raises(ValueError, match="non-eligible"):
        fast_path.worker_scope_from_verdict(verdict, tasks)


# ── verify_worker_scope (Layer B) ────────────────────────────────────────────


def _init_repo_with_files(tmp_path: Path, files: dict[str, str]) -> str:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "t@example.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=tmp_path, check=True)
    for rel, content in files.items():
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "base"], cwd=tmp_path, check=True)
    base_sha = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=tmp_path, check=True, capture_output=True, text=True
    ).stdout.strip()
    return base_sha


def test_verify_worker_scope_passes_for_in_scope_modify(tmp_path: Path) -> None:
    base_sha = _init_repo_with_files(tmp_path, {"a.py": "x = 1\n"})
    (tmp_path / "a.py").write_text("x = 2\n")
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "modify"], cwd=tmp_path, check=True)

    scope = fast_path.WorkerScope(allowed_paths=frozenset({"a.py"}))
    verdict = fast_path.verify_worker_scope(scope, tmp_path, base_sha)

    assert verdict.passed is True
    assert verdict.violations == ()


def test_verify_worker_scope_fails_for_out_of_scope_file(tmp_path: Path) -> None:
    base_sha = _init_repo_with_files(tmp_path, {"a.py": "x = 1\n"})
    (tmp_path / "b.py").write_text("y = 1\n")
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "add out of scope"], cwd=tmp_path, check=True)

    scope = fast_path.WorkerScope(allowed_paths=frozenset({"a.py"}))
    verdict = fast_path.verify_worker_scope(scope, tmp_path, base_sha)

    assert verdict.passed is False
    assert verdict.violations[0].path == "b.py"
    assert verdict.violations[0].kind == "out_of_scope"


def test_verify_worker_scope_reproduces_r0_0_scenario_c_finding(tmp_path: Path) -> None:
    """Literal reproduction required by scope-enforcement-design.md §4: a
    scope that does NOT include 4 pre-existing audit files, against a diff
    that deletes them, must FAIL with all 4 listed as violations."""
    audit_files = {
        f".renmark/audits/audit-report-{i}.json": "{}" for i in range(4)
    }
    base_sha = _init_repo_with_files(tmp_path, {"a.py": "x = 1\n", **audit_files})

    # The Worker's declared scope is only a.py — it was never authorized to
    # touch the audit files.
    scope = fast_path.WorkerScope(allowed_paths=frozenset({"a.py"}))

    # The Worker (rogue, per Scenario C) deletes the 4 pre-existing files it
    # did not create and was not authorized to touch.
    for rel in audit_files:
        (tmp_path / rel).unlink()
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "rogue delete"], cwd=tmp_path, check=True)

    verdict = fast_path.verify_worker_scope(scope, tmp_path, base_sha)

    assert verdict.passed is False
    assert len(verdict.violations) == 4
    assert all(v.kind == "disallowed_action" and v.status_code == "D" for v in verdict.violations)
    assert {v.path for v in verdict.violations} == set(audit_files)


def test_verify_worker_scope_fails_for_in_scope_delete(tmp_path: Path) -> None:
    """A delete is disallowed on the fast path even if the path IS in
    allowed_paths — action type, not just path, is enforced."""
    base_sha = _init_repo_with_files(tmp_path, {"a.py": "x = 1\n"})
    (tmp_path / "a.py").unlink()
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "delete in-scope file"], cwd=tmp_path, check=True)

    scope = fast_path.WorkerScope(allowed_paths=frozenset({"a.py"}))
    verdict = fast_path.verify_worker_scope(scope, tmp_path, base_sha)

    assert verdict.passed is False
    assert verdict.violations[0].kind == "disallowed_action"
    assert verdict.violations[0].status_code == "D"


def test_verify_worker_scope_fails_closed_on_unreadable_repo(tmp_path: Path) -> None:
    """An unverifiable scope (bad repo/base_sha) must never be treated as a
    clean pass."""
    not_a_repo = tmp_path / "not-a-repo"
    not_a_repo.mkdir()
    scope = fast_path.WorkerScope(allowed_paths=frozenset({"a.py"}))

    verdict = fast_path.verify_worker_scope(scope, not_a_repo, "deadbeef")

    assert verdict.passed is False
    assert verdict.violations[0].kind == "diff_unavailable"


# ── build_fast_path_agent_dispatch (live-wiring, WP-4) ───────────────────────


def test_build_fast_path_agent_dispatch_carries_real_scope() -> None:
    task = _task(1, "tests/test_hosts.py")
    dispatch = claude_agent.build_fast_path_agent_dispatch([task], Path("."))

    assert dispatch.scope is not None
    assert dispatch.scope.allowed_paths == frozenset({"tests/test_hosts.py"})
    assert dispatch.target == "tests/test_hosts.py"
    assert dispatch.model == "sonnet"


def test_build_fast_path_agent_dispatch_prompt_declares_scope_and_forbids_nesting() -> None:
    task = _task(1, "a.py")
    dispatch = claude_agent.build_fast_path_agent_dispatch([task], Path("."))

    assert "You may ADD or MODIFY only these exact files: a.py" in dispatch.prompt
    assert "may not delete or rename ANY file" in dispatch.prompt
    assert "must not invoke another agent, subagent, Task, or Agent tool call" in dispatch.prompt


def test_build_fast_path_agent_dispatch_rejects_non_eligible_tasks() -> None:
    task = _task(1, "renmark/x.py")
    with pytest.raises(ValueError, match="not fast-path eligible"):
        claude_agent.build_fast_path_agent_dispatch([task], Path("."))


def test_build_agent_dispatch_unaffected_by_fast_path_addition() -> None:
    """WP-3's guarantee, re-asserted at the unit level: the existing
    non-fast-path dispatch composer's prompt is untouched by this module's
    addition — it has no scope field populated and no fast-path language."""
    task = _task(1, "a.py")
    dispatch = claude_agent.build_agent_dispatch(task, Path("."))

    assert dispatch.scope is None
    assert "fast-path" not in dispatch.prompt
    assert "must not invoke another agent" not in dispatch.prompt

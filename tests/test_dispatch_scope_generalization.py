"""R-0.2/WP-5 — generalized scope enforcement for normal-path dispatch.

Proves ``.renmark/plans/r-0.2/scope-enforcement-generalization-design.md``'s
§4/§5 recommendation: ``build_agent_dispatch()`` MAY carry an optional
``scope: fast_path.WorkerScope | None`` (default ``None``, preserving R-0.1's
regression baseline exactly), and ``renmark.dispatch.verify_agent_dispatch_scope``
performs the post-hoc Layer-B check by reusing (not forking)
``fast_path.verify_worker_scope`` when a scope was declared.

Multi-wave/cumulative verification (design doc §3/§7) is out of scope here —
see the TODO comment above ``verify_agent_dispatch_scope`` in
``renmark/dispatch.py``.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from renmark import dispatch, fast_path
from renmark.parser import Task
from renmark.providers import claude_agent

REPO_ROOT = Path(__file__).resolve().parents[1]


def _task(idx: int, target: str) -> Task:
    return Task(
        index=idx,
        title=f"task {idx}",
        mode="B",
        target=target,
        context_files=[],
        verifier="pytest",
        verifier_timeout_s=60,
        spec="spec",
        executor="sonnet",
        complexity="simple",
    )


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


# ── (a) unscoped dispatch: byte-identical to R-0.1 baseline ─────────────────


def test_unscoped_dispatch_carries_no_scope_and_is_never_verified(tmp_path: Path) -> None:
    task = _task(1, "a.py")
    dispatch_obj = claude_agent.build_agent_dispatch(task, REPO_ROOT)

    assert dispatch_obj.scope is None

    base_sha = _init_repo_with_files(tmp_path, {"a.py": "x = 1\n"})
    (tmp_path / "b.py").write_text("out of scope\n")  # would violate IF checked
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "unscoped change"], cwd=tmp_path, check=True)

    verdict = dispatch.verify_agent_dispatch_scope(dispatch_obj, tmp_path, base_sha)

    # No scope was declared -> no verification is performed at all.
    assert verdict is None


# ── (b) scoped dispatch, Worker stays in scope -> passes ────────────────────


def test_scoped_dispatch_in_scope_change_passes(tmp_path: Path) -> None:
    task = _task(1, "a.py")
    scope = fast_path.WorkerScope(allowed_paths=frozenset({"a.py"}))
    dispatch_obj = claude_agent.build_agent_dispatch(task, REPO_ROOT, scope=scope)

    assert dispatch_obj.scope is scope

    base_sha = _init_repo_with_files(tmp_path, {"a.py": "x = 1\n"})
    (tmp_path / "a.py").write_text("x = 2\n")
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "in-scope modify"], cwd=tmp_path, check=True)

    verdict = dispatch.verify_agent_dispatch_scope(dispatch_obj, tmp_path, base_sha)

    assert verdict is not None
    assert verdict.passed is True
    assert verdict.violations == ()


# ── (c) scoped dispatch, Worker violates scope (R-0.0 Scenario C) -> fails ──


def test_scoped_dispatch_out_of_scope_delete_fails_verification(tmp_path: Path) -> None:
    """Mirrors R-0.1's fast-path Scenario C reproduction, now on the
    normal-path build_agent_dispatch() call site."""
    audit_files = {f".renmark/audits/audit-report-{i}.json": "{}" for i in range(4)}
    task = _task(1, "src/feature.py")
    scope = fast_path.WorkerScope(allowed_paths=frozenset({"src/feature.py"}))
    dispatch_obj = claude_agent.build_agent_dispatch(task, REPO_ROOT, scope=scope)

    base_sha = _init_repo_with_files(
        tmp_path, {"src/feature.py": "x = 1\n", **audit_files}
    )

    # Rogue Worker: makes its authorized change AND illegally deletes the 4
    # pre-existing audit files (R-0.0 Scenario C).
    (tmp_path / "src" / "feature.py").write_text("x = 2\n")
    for rel in audit_files:
        (tmp_path / rel).unlink()
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "rogue delete"], cwd=tmp_path, check=True)

    verdict = dispatch.verify_agent_dispatch_scope(dispatch_obj, tmp_path, base_sha)

    assert verdict is not None
    assert verdict.passed is False
    assert len(verdict.violations) == 4
    assert all(v.kind == "disallowed_action" and v.status_code == "D" for v in verdict.violations)
    assert {v.path for v in verdict.violations} == set(audit_files)

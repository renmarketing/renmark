"""R-6 — baseline for host-agent dispatch scope enforcement, written BEFORE
Task 8 wires it into production.

Task 8 will add two new `renmark.dispatch` functions plus a new field on
`HostDispatchPlan`:

- `build_host_dispatch_plan_with_scope(wave, *, host, ...) -> HostDispatchPlan`
  — extends `build_host_dispatch_plan` to also populate a
  `scoped_dispatches: dict[int, fast_path.WorkerScope]` attribute on the
  returned `HostDispatchPlan`, using the SAME eligibility logic
  `dispatch._maybe_scoped_claude_dispatch` already uses (single Claude task,
  passes `fast_path.classify_fast_path`).
- `enforce_host_agent_dispatch_scope(host_plan, repo, base_sha) -> None` —
  raises `dispatch.WaveScopeViolationError` on violation, no-op when
  `host_plan.scoped_dispatches` is empty. Mirrors
  `enforce_wave_dispatch_scopes`'s exact contract (see
  `tests/test_wp9_scope_enforcement_wiring.py`), reusing
  `fast_path.verify_worker_scope` under the hood rather than reimplementing
  it.

Until Task 8 lands, neither name exists on `renmark.dispatch` yet — the
module-level import below is EXPECTED to raise `ImportError` at collection
time. That is the correct, intentional state for this test-first file: it
documents the API contract Task 8 must satisfy, and it must not be made to
pass by stubbing the missing functions here.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from renmark import dispatch, fast_path
from renmark.dispatch import (  # noqa: F401  (import-time contract check — see module docstring)
    build_host_dispatch_plan_with_scope,
    enforce_host_agent_dispatch_scope,
)
from renmark.parser import Task


def _task(idx: int, target: str, *, executor: str = "sonnet", mode: str = "B", verifier: str = "pytest") -> Task:
    return Task(
        index=idx,
        title=f"task {idx}",
        mode=mode,
        target=target,
        context_files=[],
        verifier=verifier,
        verifier_timeout_s=60,
        spec="spec",
        executor=executor,
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


# ── (1) allowed dispatch passes through unchanged ───────────────────────────


def test_allowed_host_dispatch_passes_through_unchanged(tmp_path: Path) -> None:
    base_sha = _init_repo_with_files(tmp_path, {"src/feature.py": "x = 1\n"})

    task = _task(1, "src/feature.py")
    wave = [task]

    host_plan = build_host_dispatch_plan_with_scope(wave, host="claude")
    assert 1 in host_plan.scoped_dispatches
    assert isinstance(host_plan.scoped_dispatches[1], fast_path.WorkerScope)

    # In-scope git commit.
    (tmp_path / "src" / "feature.py").write_text("x = 2\n")
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "in-scope change"], cwd=tmp_path, check=True)

    # Must not raise.
    enforce_host_agent_dispatch_scope(host_plan, tmp_path, base_sha)


# ── (2) out-of-envelope dispatch is denied with a clear error ───────────────


def test_out_of_scope_host_dispatch_is_denied(tmp_path: Path) -> None:
    audit_files = {f".renmark/audits/audit-{i}.json": "{}" for i in range(2)}
    base_sha = _init_repo_with_files(tmp_path, {"src/feature.py": "x = 1\n", **audit_files})

    task = _task(1, "src/feature.py")
    wave = [task]

    host_plan = build_host_dispatch_plan_with_scope(wave, host="claude")
    assert 1 in host_plan.scoped_dispatches

    # Rogue Worker: authorized change AND illegal out-of-scope deletes.
    (tmp_path / "src" / "feature.py").write_text("x = 2\n")
    for rel in audit_files:
        (tmp_path / rel).unlink()
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "rogue delete"], cwd=tmp_path, check=True)

    with pytest.raises(dispatch.WaveScopeViolationError) as excinfo:
        enforce_host_agent_dispatch_scope(host_plan, tmp_path, base_sha)

    violations = excinfo.value.violations
    assert len(violations) == 1
    v = violations[0]
    assert isinstance(v, dispatch.WaveScopeViolation)
    assert v.task_index == 1
    assert v.verdict.passed is False
    assert len(v.verdict.violations) == 2
    # The exception message names the violating task — never a silent drop.
    assert "task 1" in str(excinfo.value)


# ── (3) unscoped multi-task Claude wave stays a silent no-op ────────────────


def test_multi_task_claude_wave_has_empty_scoped_dispatches_and_noop_enforce(tmp_path: Path) -> None:
    """A multi-task Claude wave never gets a scope (matches
    `_maybe_scoped_claude_dispatch`'s documented single-task-only
    eligibility) — `scoped_dispatches` must stay empty and enforcement over
    an empty map must be a silent, non-raising no-op, matching the R-0.1
    no-enforcement-without-opt-in baseline WP-9 already established."""
    base_sha = _init_repo_with_files(tmp_path, {"a.py": "x = 1\n", "b.py": "y = 1\n"})

    wave = [
        _task(1, "a.py", executor="sonnet"),
        _task(2, "b.py", executor="opus"),
    ]

    host_plan = build_host_dispatch_plan_with_scope(wave, host="claude")
    assert host_plan.scoped_dispatches == {}

    # Nothing to verify — must not raise even though no commit happened after
    # base_sha (there is no scoped dispatch to check against it).
    enforce_host_agent_dispatch_scope(host_plan, tmp_path, base_sha)

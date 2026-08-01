"""R-0.2/WP-9 — `verify_wave_dispatch_scopes` gets a fail-loud counterpart.

The WP-8 independent re-review (`.renmark/reviews/2026-08-01-r-0.2-closeout.md`,
"WP-8 Wiring Re-Review") found that `_maybe_scoped_claude_dispatch` correctly
constructs a scope on the real `dispatch_wave` path, but the actual post-hoc
enforcement check (`verify_wave_dispatch_scopes`) was a function nothing ever
called — a tuple return a caller could inspect or just as easily ignore.

This proves the new `enforce_wave_dispatch_scopes` raising wrapper:
(a) a real `dispatch_wave` call for a scoped single-task wave, where the
    resulting diff stays in scope, completes normally (no raise).
(b) the same call where the diff violates scope raises `WaveScopeViolationError`
    carrying the structured violation(s) — never silently dropped.
(c) unscoped waves (multi-task Claude, non-Claude/codex) are completely
    unaffected: no verification is attempted (there's nothing to verify).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from renmark import dispatch
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


# ── (a) in-scope diff — real dispatch_wave call, enforcement is a no-op ─────


def test_enforce_wave_dispatch_scopes_passes_silently_for_in_scope_diff(tmp_path: Path) -> None:
    task = _task(1, "src/feature.py")
    wave = [task]

    result = dispatch.dispatch_wave(wave, repo=tmp_path, run_task=lambda t, r: None)  # type: ignore[arg-type]
    assert 1 in result.scoped_dispatches

    base_sha = _init_repo_with_files(tmp_path, {"src/feature.py": "x = 1\n"})
    (tmp_path / "src" / "feature.py").write_text("x = 2\n")
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "in-scope change"], cwd=tmp_path, check=True)

    # Must not raise.
    dispatch.enforce_wave_dispatch_scopes(result, tmp_path, base_sha)


# ── (b) out-of-scope diff — enforcement raises, carrying the violation(s) ───


def test_enforce_wave_dispatch_scopes_raises_on_violation(tmp_path: Path) -> None:
    task = _task(1, "src/feature.py")
    wave = [task]

    result = dispatch.dispatch_wave(wave, repo=tmp_path, run_task=lambda t, r: None)  # type: ignore[arg-type]
    assert 1 in result.scoped_dispatches

    audit_files = {f".renmark/audits/audit-{i}.json": "{}" for i in range(2)}
    base_sha = _init_repo_with_files(tmp_path, {"src/feature.py": "x = 1\n", **audit_files})

    # Rogue Worker: authorized change AND an illegal out-of-scope delete.
    (tmp_path / "src" / "feature.py").write_text("x = 2\n")
    for rel in audit_files:
        (tmp_path / rel).unlink()
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "rogue delete"], cwd=tmp_path, check=True)

    with pytest.raises(dispatch.WaveScopeViolationError) as excinfo:
        dispatch.enforce_wave_dispatch_scopes(result, tmp_path, base_sha)

    violations = excinfo.value.violations
    assert len(violations) == 1
    v = violations[0]
    assert isinstance(v, dispatch.WaveScopeViolation)
    assert v.task_index == 1
    assert v.verdict.passed is False
    assert len(v.verdict.violations) == 2
    # The exception message names the violating task — never a silent drop.
    assert "task 1" in str(excinfo.value)


# ── (c) unscoped waves are completely unaffected ────────────────────────────


def test_enforce_wave_dispatch_scopes_noop_for_multi_task_claude_wave(tmp_path: Path) -> None:
    """A multi-task Claude wave never gets a scope (WP-8a's documented
    follow-up) — enforcement over an empty scoped_dispatches map must be a
    silent, non-raising no-op, matching baseline (unenforced) R-0.1 behavior."""
    wave = [
        _task(1, "a.py", executor="sonnet"),
        _task(2, "b.py", executor="opus"),
    ]

    result = dispatch.dispatch_wave(wave, repo=tmp_path, run_task=lambda t, r: None)  # type: ignore[arg-type]
    assert result.scoped_dispatches == {}

    base_sha = _init_repo_with_files(tmp_path, {"a.py": "x = 1\n", "b.py": "y = 1\n"})
    # Nothing to verify — must not raise even though no commit happened after
    # base_sha (there is no scoped dispatch to check against it).
    dispatch.enforce_wave_dispatch_scopes(result, tmp_path, base_sha)


def test_enforce_wave_dispatch_scopes_noop_for_non_claude_wave(tmp_path: Path) -> None:
    """A codex/deterministic task never enters the Claude scoping path — the
    wave's dispatches actually run synchronously via run_task, and
    enforcement remains a no-op since no scope was ever declared."""
    task = _task(1, "a.py", executor="codex")
    wave = [task]

    def run_task(t: Task, r: Path) -> dispatch.TaskResult:
        return dispatch.TaskResult(task_index=t.index, executor=t.executor, status="passed")

    result = dispatch.dispatch_wave(wave, repo=tmp_path, run_task=run_task)
    assert result.scoped_dispatches == {}

    base_sha = _init_repo_with_files(tmp_path, {"a.py": "x = 1\n"})
    dispatch.enforce_wave_dispatch_scopes(result, tmp_path, base_sha)

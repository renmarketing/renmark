"""R-0.2/WP-8a — wiring scope construction/verification into a real
`dispatch.py` call site (Follow-up F1 from the R-0.2 closeout).

Proves:
(a) a real wave-dispatch call for a single-file-scoped Claude task actually
    constructs a `WorkerScope`/`AgentDispatch` and exposes it for the
    verifier to be called against (mocked/injected verification point — no
    live Agent call).
(b) an out-of-scope violation is detected via `verify_wave_dispatch_scopes`
    and surfaces as a structured, non-empty result — never silently dropped.
(c) existing wave-dispatch behavior for tasks that don't qualify for a scope
    (multi-task Claude waves, wide targets, etc.) is unchanged: no entries in
    `WaveResult.scoped_dispatches`, tasks still report `status="needs_agent"`.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from renmark import dispatch, fast_path
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


# ── (a) single-file Claude task -> a real wave-dispatch call constructs a
#        scope and an AgentDispatch the verifier can be pointed at ──────────


def test_single_scoped_claude_task_wave_constructs_scope_and_dispatch(tmp_path: Path) -> None:
    task = _task(1, "src/feature.py")
    wave = [task]

    result = dispatch.dispatch_wave(wave, repo=tmp_path, run_task=lambda t, r: None)  # type: ignore[arg-type]

    # Unchanged shape: Claude tasks report needs_agent, no run_task call happened.
    assert len(result.tasks) == 1
    assert result.tasks[0].status == "needs_agent"

    # New wiring: a scope + AgentDispatch was constructed for this task.
    assert 1 in result.scoped_dispatches
    agent_dispatch = result.scoped_dispatches[1]
    assert agent_dispatch.scope is not None
    assert agent_dispatch.scope.allowed_paths == frozenset({"src/feature.py"})

    # The verification point is real and callable (mocked git state below,
    # not a live Agent call) — this is the "would call the verifier" proof.
    base_sha = _init_repo_with_files(tmp_path, {"src/feature.py": "x = 1\n"})
    (tmp_path / "src" / "feature.py").write_text("x = 2\n")
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "in-scope change"], cwd=tmp_path, check=True)

    violations = dispatch.verify_wave_dispatch_scopes(result.scoped_dispatches, tmp_path, base_sha)
    assert violations == ()


# ── (b) an out-of-scope violation surfaces as a structured, non-empty result


def test_out_of_scope_violation_surfaces_structured_not_silently_dropped(tmp_path: Path) -> None:
    task = _task(1, "src/feature.py")
    wave = [task]

    result = dispatch.dispatch_wave(wave, repo=tmp_path, run_task=lambda t, r: None)  # type: ignore[arg-type]
    assert 1 in result.scoped_dispatches

    audit_files = {f".renmark/audits/audit-{i}.json": "{}" for i in range(3)}
    base_sha = _init_repo_with_files(tmp_path, {"src/feature.py": "x = 1\n", **audit_files})

    # Rogue Worker: authorized change AND an illegal out-of-scope delete.
    (tmp_path / "src" / "feature.py").write_text("x = 2\n")
    for rel in audit_files:
        (tmp_path / rel).unlink()
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "rogue delete"], cwd=tmp_path, check=True)

    violations = dispatch.verify_wave_dispatch_scopes(result.scoped_dispatches, tmp_path, base_sha)

    assert len(violations) == 1
    v = violations[0]
    assert isinstance(v, dispatch.WaveScopeViolation)
    assert v.task_index == 1
    assert v.verdict.passed is False
    assert len(v.verdict.violations) == 3
    assert all(sv.kind == "disallowed_action" and sv.status_code == "D" for sv in v.verdict.violations)


# ── (c) unchanged behavior for tasks that don't qualify for a scope ─────────


def test_multi_task_claude_wave_stays_unscoped_documented_follow_up(tmp_path: Path) -> None:
    wave = [
        _task(1, "a.py", executor="sonnet"),
        _task(2, "b.py", executor="opus"),
    ]

    result = dispatch.dispatch_wave(wave, repo=tmp_path, run_task=lambda t, r: None)  # type: ignore[arg-type]

    assert result.scoped_dispatches == {}
    assert all(t.status == "needs_agent" for t in result.tasks)


def test_wide_target_claude_task_stays_unscoped(tmp_path: Path) -> None:
    """A target that fails fast_path's own eligibility signals (e.g. a
    renmark/** production target) must not get a scope constructed for it —
    reuses the same 5-signal threshold, doesn't invent a looser one."""
    task = _task(1, "renmark/dispatch.py")
    wave = [task]

    result = dispatch.dispatch_wave(wave, repo=tmp_path, run_task=lambda t, r: None)  # type: ignore[arg-type]

    assert result.scoped_dispatches == {}
    assert result.tasks[0].status == "needs_agent"


def test_non_claude_task_wave_unaffected(tmp_path: Path) -> None:
    """A codex/deterministic task never enters the Claude scoping path at
    all — proves the wiring is additive, not a behavior change for the
    existing runnable-task path."""
    task = _task(1, "a.py", executor="codex")
    wave = [task]

    called: list[int] = []

    def run_task(t: Task, r: Path) -> dispatch.TaskResult:
        called.append(t.index)
        return dispatch.TaskResult(task_index=t.index, executor=t.executor, status="passed")

    result = dispatch.dispatch_wave(wave, repo=tmp_path, run_task=run_task)

    assert called == [1]
    assert result.scoped_dispatches == {}
    assert result.tasks[0].status == "passed"


# ── unscoped dispatch: verify_wave_dispatch_scopes over an empty map is a
#    no-op, non-blocking pass ────────────────────────────────────────────────


def test_verify_wave_dispatch_scopes_empty_map_passes_trivially(tmp_path: Path) -> None:
    assert dispatch.verify_wave_dispatch_scopes({}, tmp_path, "HEAD") == ()

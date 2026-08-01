"""WP-8b (R-0.2): the R-008 dispatch checklist gate must have a real caller.

Prior to this change ``enforce_r008_dispatch`` (renmark/subagent_gate.py,
WP-5b) had no production call site — a dispatch-agency review flagged it as
dormant (closeout follow-up F3). This wires it into the real per-task
dispatch-orchestration point in ``renmark/cli/_engine.py`` (the ``_runner``
closure inside ``execute_plan``, which hands every runnable task to the live
codex executor) in LENIENT mode: missing R-008 fields warn, never block.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from types import SimpleNamespace

from renmark.cli import _engine
from renmark.parser import Task


# ── helpers (mirrors tests/test_engine_budget_and_rollback.py) ─────────────


def _init_repo(path: Path) -> None:
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=path, check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.name", "t"], check=True)
    (path / "seed.txt").write_text("seed")
    subprocess.run(["git", "-C", str(path), "add", "seed.txt"], check=True)
    subprocess.run(["git", "-C", str(path), "commit", "-q", "-m", "init"], check=True)


def _write_plan(path: Path, n_tasks: int = 1) -> Path:
    blocks = []
    for i in range(1, n_tasks + 1):
        blocks.append(
            f"### Task {i}: task {i}\n"
            f"- **mode:** A\n"
            f"- **target:** out/file{i}.txt\n"
            f"- **context_files:** []\n"
            f"- **verifier:** true\n"
            f"- **verifier_timeout_s:** 5\n"
            f"- **spec:**\n"
            f"  make file {i}\n"
        )
    p = path / "plan.md"
    p.write_text("\n".join(blocks))
    return p


# ── (a) the real _engine.py call site invokes the R-008 checker ────────────


def test_r008_precheck_helper_exists_and_delegates_to_subagent_gate(monkeypatch):
    """``_r008_precheck`` is the wired call site; it must actually call
    ``subagent_gate.enforce_r008_dispatch`` (not reimplement the check)."""
    from renmark import subagent_gate

    calls = []
    orig = subagent_gate.enforce_r008_dispatch

    def _spy(dispatch_spec, *, strict=False):
        calls.append((dispatch_spec, strict))
        return orig(dispatch_spec, strict=strict)

    monkeypatch.setattr(subagent_gate, "enforce_r008_dispatch", _spy)

    task = Task(index=1, title="t", mode="A", target="out/a.txt", verifier="true", spec="x")
    missing = _engine._r008_precheck(task)

    assert len(calls) == 1
    assert calls[0][1] is False  # strict=False — lenient mode, per migration plan
    assert missing  # a bare Task carries none of the 6 R-008 fields yet


def test_runner_inside_execute_plan_invokes_r008_precheck(tmp_path, monkeypatch, capsys):
    """End-to-end: running a plan through execute_plan's real dispatch path
    (_runner, called from dispatch_wave) triggers the R-008 gate and prints a
    visible warning — proving the checker is wired at the live call site, not
    just callable in isolation."""
    _init_repo(tmp_path)
    plan = _write_plan(tmp_path, 1)
    monkeypatch.setattr(_engine, "codex_available", lambda: True)

    calls = []
    orig = _engine._r008_precheck

    def _spy(task):
        calls.append(task.index)
        return orig(task)

    monkeypatch.setattr(_engine, "_r008_precheck", _spy)

    _engine.execute_plan(str(plan), repo=tmp_path)

    assert calls == [1]
    out = capsys.readouterr().out
    assert "R-008 WARN" in out


# ── (b) fully-specified dispatch → no warnings ──────────────────────────────


def test_fully_specified_dispatch_produces_no_warnings(capsys):
    spec = SimpleNamespace(
        index=1,
        title="t",
        work_order_id="WO-1",
        contract="C-1",
        reason="user requested feature X",
        scope={"target_files": ["a.py"], "read_only_files": [], "prohibited_files": []},
        expected_artifact="a.py updated",
        budget_reservation={"max_input_tokens": 1000, "max_output_tokens": 500, "max_attempts": 1},
    )

    missing = _engine._r008_precheck(spec)  # type: ignore[arg-type]

    assert missing == []
    out = capsys.readouterr().out
    assert "R-008 WARN" not in out


# ── (c) missing fields → visible warning, but NEVER blocks (lenient) ───────


def test_missing_fields_warn_but_do_not_block(tmp_path, monkeypatch, capsys):
    """A pre-R-0.2 style Task (no R-008 fields at all) must dispatch and PASS
    normally, with only a warning surfaced — lenient mode must never reject."""
    _init_repo(tmp_path)
    plan = _write_plan(tmp_path, 1)
    monkeypatch.setattr(_engine, "codex_available", lambda: True)
    # Stub out the actual codex call — this test only proves the R-008 gate
    # never blocks a task from reaching/completing dispatch, not codex I/O.
    monkeypatch.setattr(
        _engine,
        "_execute_task_codex",
        lambda **kwargs: (True, "", 10, "deadbeef"),
    )

    rc = _engine.execute_plan(str(plan), repo=tmp_path)

    out = capsys.readouterr().out
    assert "R-008 WARN" in out
    assert "work_order_id" in out and "budget_reservation" in out
    # Lenient mode: the missing checklist must not turn into a hard failure by
    # itself. rc reflects normal task pass/fail (verifier "true" passes).
    assert rc == 0


def test_r008_precheck_never_raises_on_missing_fields():
    task = Task(index=1, title="t", mode="A", target="out/a.txt", verifier="true", spec="x")
    missing = _engine._r008_precheck(task)
    assert set(missing) == {
        "work_order_id",
        "contract",
        "reason",
        "scope",
        "expected_artifact",
        "budget_reservation",
    }

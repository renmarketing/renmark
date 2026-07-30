"""Tests for the audit fixes in renmark.cli._engine and renmark.providers.codex:

1. Budget/deadline exhaustion is an honest FAIL (pause + non-zero exit + full
   skipped list), never a silent "All tasks completed." exit 0.
2. Parallel codex change-detection uses a pre/post delta and excludes sibling
   wave-targets, so concurrent in-flight files never look out-of-lane.
3. Mode-A failed-task rollback deletes an UNTRACKED target (checkout can't
   restore it) instead of silently leaving the rejected artifact on disk.
4. Porcelain snapshots use `git status --porcelain -z` (NUL-separated): unicode
   and space filenames survive un-mangled (no octal-escaping/quoting), and
   rename/copy entries yield the NEW path only (the original NUL token is
   skipped, never double-counted).
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from renmark.cli import _codex_runner, _engine
from renmark.parser import Task
from renmark.providers import codex as codex_provider
from renmark.providers.codex import CodexError, CodexResult

# ── helpers ───────────────────────────────────────────────────────────────────


def _init_repo(path: Path) -> None:
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=path, check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.name", "t"], check=True)
    (path / "seed.txt").write_text("seed")
    subprocess.run(["git", "-C", str(path), "add", "seed.txt"], check=True)
    subprocess.run(["git", "-C", str(path), "commit", "-q", "-m", "init"], check=True)


def _write_plan(path: Path, n_tasks: int) -> Path:
    """A plan with N serial tasks (each its own wave)."""
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


# ── Task 1: budget / deadline honesty ──────────────────────────────────────────


def test_deadline_exhaustion_pauses_and_exits_nonzero(tmp_path, monkeypatch, capsys):
    """A zero-minute deadline trips the time gate on wave 1: the run must write
    a pause, mark ALL tasks skipped, and exit non-zero — not exit 0."""
    _init_repo(tmp_path)
    plan = _write_plan(tmp_path, 3)

    monkeypatch.setenv("RENMARK_MAX_MINUTES_PER_RUN", "0")
    # codex never runs (gate trips first), but be safe and force it "available".
    monkeypatch.setattr(_engine, "codex_available", lambda: True)

    rc = _engine.execute_plan(str(plan), repo=tmp_path)

    assert rc == 10, "budget exhaustion must use the failure exit code, not 0"
    out = capsys.readouterr().out
    assert "All tasks completed." not in out
    assert "PAUSED" in out
    # Pause file written, keyed to the first skipped task.
    from renmark import state

    pause = state.read_pause(tmp_path)
    assert pause is not None
    assert pause.reason == "deadline"
    assert pause.last_task_index == 1
    # All three tasks recorded as skipped (not just wave 1).
    assert "[1, 2, 3]" in out


# ── Task 2: parallel change-detection delta + sibling exclusion ─────────────────


def test_codex_delta_excludes_preexisting_sibling_changes(tmp_path, monkeypatch):
    """run_codex_task reports only files changed BY the task (post minus pre).
    A sibling's in-flight file present before the call is not attributed here."""
    _init_repo(tmp_path)

    from renmark.parser import Task

    task = Task(index=1, title="t", mode="A", target="out/a.txt", verifier="true", spec="x")

    calls = {"n": 0}

    def fake_status(repo):
        calls["n"] += 1
        if calls["n"] == 1:
            # pre: a sibling already touched sibling.txt
            return ["sibling.txt"]
        # post: sibling still there + this task's own file
        return ["sibling.txt", "out/a.txt"]

    monkeypatch.setattr(codex_provider, "_git_status_porcelain", fake_status)
    selected = "/opt/renmark/codex"
    monkeypatch.setattr(codex_provider, "_resolve_codex_executable", lambda _repo: selected)
    subprocess_calls = []

    class FakeProc:
        returncode = 0
        stdout = "done"
        stderr = ""

    def fake_run(*args, **kwargs):
        subprocess_calls.append((args, kwargs))
        return FakeProc()

    monkeypatch.setattr(codex_provider.subprocess, "run", fake_run)

    result = codex_provider.run_codex_task(task, tmp_path, timeout_s=5)
    assert result.changed_files == ["out/a.txt"], "sibling's pre-existing change must drop out"
    assert "sibling.txt" in result.pre_changed_files
    cmd = subprocess_calls[0][0][0]
    assert cmd == [
        selected,
        "exec",
        "--sandbox",
        "workspace-write",
        "--skip-git-repo-check",
        "-",
    ]
    assert subprocess_calls[0][1]["cwd"] == str(tmp_path)
    assert "--dangerously-bypass-approvals-and-sandbox" not in cmd


def test_codex_resolver_skips_unusable_first_path_candidate(tmp_path, monkeypatch):
    repo = tmp_path / "workspace"
    first_dir = tmp_path / "first-bin"
    second_dir = tmp_path / "second-bin"
    repo.mkdir()
    first_dir.mkdir()
    second_dir.mkdir()
    unusable = first_dir / "codex"
    usable = second_dir / "codex"
    unusable.write_text("#!/bin/sh\n")
    usable.write_text("#!/bin/sh\n")
    unusable.chmod(0o755)
    usable.chmod(0o755)
    monkeypatch.setenv("PATH", os.pathsep.join((str(first_dir), str(second_dir))))
    probed = []

    def fake_probe(executable, repo):
        probed.append((executable, repo))
        return executable == str(usable), "bubblewrap unavailable"

    monkeypatch.setattr(codex_provider, "_sandbox_probe", fake_probe)

    assert codex_provider._resolve_codex_executable(repo) == str(usable)
    assert probed == [(str(unusable), repo), (str(usable), repo)]


def test_codex_resolver_rejects_path_candidate_inside_target_repo(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    workspace_bin = workspace / "bin"
    external_bin = tmp_path / "external-bin"
    workspace_bin.mkdir(parents=True)
    external_bin.mkdir()
    workspace_codex = workspace_bin / "codex"
    external_codex = external_bin / "codex"
    workspace_codex.write_text("#!/bin/sh\n")
    external_codex.write_text("#!/bin/sh\n")
    workspace_codex.chmod(0o755)
    external_codex.chmod(0o755)
    monkeypatch.setenv("PATH", os.pathsep.join((str(workspace_bin), str(external_bin))))

    assert codex_provider._codex_candidates(workspace) == [str(external_codex)]


def test_codex_resolver_rejects_unusable_binary_before_model_call(tmp_path, monkeypatch):
    unusable = tmp_path / "codex"
    unusable.write_text("#!/bin/sh\n")
    unusable.chmod(0o755)
    monkeypatch.setattr(codex_provider, "_codex_candidates", lambda _repo: [str(unusable)])
    monkeypatch.setattr(
        codex_provider,
        "_sandbox_probe",
        lambda _executable, _repo: (False, "bubblewrap is unavailable"),
    )

    task = Task(index=1, title="t", mode="A", target="out/a.txt", verifier="true", spec="x")
    with pytest.raises(CodexError, match="No sandbox-capable Codex CLI") as exc:
        codex_provider.run_codex_task(task, tmp_path)

    assert "sudo apt install bubblewrap" in str(exc.value)
    assert "will not disable workspace-write" in str(exc.value)


def test_check_only_target_excludes_sibling_targets():
    """A sibling wave-target leaking into this task's delta must not trip the
    lane check (waves are disjoint, so this can't mask a real over-write)."""
    ok, reason = codex_provider.check_only_target_modified(
        ["out/a.txt", "out/b.txt"], "out/a.txt", sibling_targets=["out/b.txt"]
    )
    assert ok, reason
    # Without the sibling exclusion, the same input is out-of-lane.
    bad, _ = codex_provider.check_only_target_modified(["out/a.txt", "out/b.txt"], "out/a.txt")
    assert not bad


# ── porcelain -z: NUL parsing keeps unicode/space filenames un-mangled ──────────


def test_porcelain_z_unicode_space_filename_unmangled(tmp_path):
    """A real `git status --porcelain -z` on a unicode+space filename returns the
    path verbatim — NOT octal-escaped/quoted the way the non-`-z` form would
    (`"f\\303\\274nf \\303\\244.txt"`). The path must appear in the delta exactly."""
    _init_repo(tmp_path)
    fname = "fünf ä.txt"
    (tmp_path / fname).write_text("neu")

    pre: list[str] = []  # nothing pending right after the init commit
    post = codex_provider._git_status_porcelain(tmp_path)
    assert fname in post, f"unicode/space path mangled in snapshot: {post!r}"
    # No octal-escape artifacts and no wrapping quotes leaked in.
    assert not any("\\" in p or p.startswith('"') for p in post), post

    delta = codex_provider._delta(pre, post)
    assert fname in delta, f"unicode/space path missing from delta: {delta!r}"


def test_parse_porcelain_z_rename_returns_new_path_only():
    """A rename entry in `-z` output carries the NEW path in the record and the
    ORIGINAL path as a separate following NUL token. Parsing must yield the new
    path and SKIP the original — never emit both, never emit the original."""
    # Renamed old.txt -> new.txt, plus an ordinary modification, plus an add.
    raw = "R  new.txt\0old.txt\0 M kept.txt\0?? added.txt\0"
    paths = codex_provider._parse_porcelain_z(raw)
    assert "new.txt" in paths, paths
    assert "old.txt" not in paths, "original (pre-rename) path must be skipped"
    assert "kept.txt" in paths
    assert "added.txt" in paths
    # Exactly three real changes — the rename's original token is consumed, not counted.
    assert len(paths) == 3, paths


def test_parse_porcelain_z_copy_entry_skips_source():
    """Copy entries (status column 'C') behave like renames: new path kept,
    source path (the following NUL token) skipped."""
    raw = "C  copy.txt\0source.txt\0"
    paths = codex_provider._parse_porcelain_z(raw)
    assert paths == ["copy.txt"], paths


# ── Task 3 + 2: path-scoped rollback (untracked delete, tracked checkout) ───────


def test_rollback_deletes_untracked_target(tmp_path):
    """A newly-created (untracked) file is DELETED on rollback — checkout would
    be a no-op and leave the rejected artifact poisoning the next task."""
    _init_repo(tmp_path)
    new_file = tmp_path / "out" / "new.txt"
    new_file.parent.mkdir(parents=True)
    new_file.write_text("rejected artifact")

    untracked = _engine._untracked_paths(tmp_path, ["out/new.txt"])
    assert "out/new.txt" in untracked

    _engine._rollback_paths(tmp_path, ["out/new.txt"], untracked_before=untracked)
    assert not new_file.exists(), "untracked target must be deleted, not left on disk"


def test_rollback_restores_tracked_target(tmp_path):
    """A tracked file is restored to its committed content on rollback."""
    _init_repo(tmp_path)
    seed = tmp_path / "seed.txt"
    seed.write_text("CORRUPTED by a failed task")

    untracked = _engine._untracked_paths(tmp_path, ["seed.txt"])
    assert untracked == set()  # seed.txt is tracked

    _engine._rollback_paths(tmp_path, ["seed.txt"], untracked_before=untracked)
    assert seed.read_text() == "seed", "tracked target must be restored to committed content"


def test_rollback_leaves_sibling_untouched(tmp_path):
    """Rollback of one task's path must not touch a concurrent sibling's file."""
    _init_repo(tmp_path)
    sibling = tmp_path / "sibling.txt"
    sibling.write_text("sibling in-flight work")  # untracked sibling change
    mine = tmp_path / "out" / "mine.txt"
    mine.parent.mkdir(parents=True)
    mine.write_text("my rejected artifact")

    # Roll back ONLY my path.
    _engine._rollback_paths(tmp_path, ["out/mine.txt"], untracked_before={"out/mine.txt"})
    assert not mine.exists()
    assert sibling.exists(), "sibling's in-flight work must survive my rollback"
    assert sibling.read_text() == "sibling in-flight work"


# ── v0.9.1 review fixes: pin the atomic hot-path functions directly ───────────


def test_classify_and_rollback_atomic_deletes_untracked(tmp_path):
    """_classify_and_rollback (single-lock hot path) deletes an untracked
    rejected artifact — pins the TOCTOU-closing composition directly."""
    _init_repo(tmp_path)
    new_file = tmp_path / "out" / "new.txt"
    new_file.parent.mkdir(parents=True)
    new_file.write_text("rejected artifact")

    _engine._classify_and_rollback(tmp_path, ["out/new.txt"])
    assert not new_file.exists()


def test_classify_and_rollback_atomic_restores_tracked(tmp_path):
    _init_repo(tmp_path)
    seed = tmp_path / "seed.txt"
    seed.write_text("CORRUPTED")
    _engine._classify_and_rollback(tmp_path, ["seed.txt"])
    assert seed.read_text() == "seed"


def test_judge_lane_and_rollback_cleans_extras_leaves_target_and_siblings(tmp_path):
    """_judge_lane_and_rollback (single-lock snapshot→judge→rollback): an
    out-of-lane extra is rolled back; the task's own target and a declared
    sibling target survive."""
    _init_repo(tmp_path)
    target = tmp_path / "out" / "target.txt"
    target.parent.mkdir(parents=True)
    target.write_text("my work")
    rogue = tmp_path / "rogue.txt"
    rogue.write_text("out-of-lane write")
    sibling = tmp_path / "sib.txt"
    sibling.write_text("sibling in-flight work")

    ok, _reason = _engine._judge_lane_and_rollback(
        tmp_path,
        pre_changed_files=[],
        target="out/target.txt",
        sibling_targets=["sib.txt"],
    )
    assert ok is False
    assert not rogue.exists(), "out-of-lane extra must be rolled back"
    assert target.exists() and target.read_text() == "my work", "own target must survive lane rollback"
    assert sibling.exists() and sibling.read_text() == "sibling in-flight work"


def test_judge_lane_and_rollback_in_lane_is_noop(tmp_path):
    """A task that touched only its target judges in-lane; nothing rolled back."""
    _init_repo(tmp_path)
    target = tmp_path / "out" / "target.txt"
    target.parent.mkdir(parents=True)
    target.write_text("my work")
    ok, _reason = _engine._judge_lane_and_rollback(
        tmp_path,
        pre_changed_files=[],
        target="out/target.txt",
        sibling_targets=None,
    )
    assert ok is True
    assert target.exists()


def test_codex_runner_rejects_unchanged_target_before_verifier(tmp_path, monkeypatch):
    """A zero-delta executor exit cannot borrow a pre-existing green verifier."""
    _init_repo(tmp_path)
    task = Task(index=1, title="must edit", mode="B", target="seed.txt", verifier="true")
    cfg = SimpleNamespace(max_task_retries=0, default_verifier_timeout_s=5)

    monkeypatch.setattr(
        _codex_runner,
        "run_codex_task",
        lambda *_args, **_kwargs: CodexResult(
            exit_code=0,
            output_tail="completed without edits",
            changed_files=[],
            pre_changed_files=[],
        ),
    )
    monkeypatch.setattr(_codex_runner, "append_usage", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        _codex_runner,
        "_judge_lane_and_rollback",
        lambda *_args, **_kwargs: (True, "ok"),
    )
    monkeypatch.setattr(
        _codex_runner,
        "run_verifier",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("unchanged target must be rejected before verification")
        ),
    )
    monkeypatch.setattr(_codex_runner, "_record_escalation", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(_codex_runner, "_print", lambda *_args, **_kwargs: None)

    result = _codex_runner._execute_task_codex(
        task=task,
        repo=tmp_path,
        run_id="unchanged-target",
        cfg=cfg,
        total=1,
    )

    assert result[0] is False
    assert result[1] == "codex_no_target_change"


def test_codex_runner_rolls_back_dirty_target_before_retry(tmp_path, monkeypatch):
    """Executor and lane failures cannot poison the next attempt's target delta."""
    for failure_kind in ("nonzero", "lane"):
        repo = tmp_path / failure_kind
        repo.mkdir()
        _init_repo(repo)
        task = Task(index=1, title="retry cleanly", mode="B", target="seed.txt", verifier="true")
        cfg = SimpleNamespace(max_task_retries=1, default_verifier_timeout_s=5)
        calls = 0
        lane_calls = 0

        def run_codex(*_args, _repo=repo, _failure_kind=failure_kind, **_kwargs):
            nonlocal calls
            calls += 1
            if calls == 1:
                (_repo / "seed.txt").write_text("dirty first attempt")
                return CodexResult(
                    exit_code=1 if _failure_kind == "nonzero" else 0,
                    output_tail=f"{_failure_kind} failure",
                    changed_files=["seed.txt"],
                    pre_changed_files=[],
                )
            assert (_repo / "seed.txt").read_text() == "seed"
            (_repo / "seed.txt").write_text("fixed second attempt")
            return CodexResult(
                exit_code=0,
                output_tail="completed",
                changed_files=["seed.txt"],
                pre_changed_files=[],
            )

        def judge_lane(*_args, _failure_kind=failure_kind, **_kwargs):
            nonlocal lane_calls
            lane_calls += 1
            if _failure_kind == "lane" and lane_calls == 1:
                return False, "out-of-lane first attempt"
            return True, "ok"

        monkeypatch.setattr(_codex_runner, "run_codex_task", run_codex)
        monkeypatch.setattr(_codex_runner, "append_usage", lambda *_args, **_kwargs: None)
        monkeypatch.setattr(_codex_runner, "_judge_lane_and_rollback", judge_lane)
        monkeypatch.setattr(
            _codex_runner,
            "run_verifier",
            lambda *_args, **_kwargs: SimpleNamespace(ok=True),
        )
        monkeypatch.setattr(
            _codex_runner,
            "_git_commit",
            lambda *_args, **_kwargs: "abc123",
        )
        monkeypatch.setattr(_codex_runner, "_print", lambda *_args, **_kwargs: None)

        result = _codex_runner._execute_task_codex(
            task=task,
            repo=repo,
            run_id=f"retry-{failure_kind}",
            cfg=cfg,
            total=1,
        )

        assert result == (True, "", 0, "abc123")
        assert calls == 2
        assert (repo / "seed.txt").read_text() == "fixed second attempt"


def test_codex_verify_and_commit_rejects_empty_sha(tmp_path, monkeypatch):
    """A green verifier is not completion when Git produced no commit evidence."""
    _init_repo(tmp_path)
    task = Task(index=1, title="must commit", mode="B", target="seed.txt", verifier="true")
    cfg = SimpleNamespace(max_task_retries=0)

    monkeypatch.setattr(_codex_runner, "_git_commit", lambda *_args, **_kwargs: "")
    monkeypatch.setattr(_codex_runner, "_record_escalation", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(_codex_runner, "_print", lambda *_args, **_kwargs: None)

    result = _codex_runner._codex_verify_and_commit(
        SimpleNamespace(ok=True),
        task,
        1,
        tmp_path,
        "missing-commit",
        cfg,
        0,
        0.0,
        "",
    )

    assert result[0] is False
    assert result[1] == "codex_commit_missing"


def test_codex_verify_and_commit_accepts_sha_and_explicit_no_commit(tmp_path, monkeypatch):
    """Real commits and the intentional batching sentinel remain successful."""
    _init_repo(tmp_path)
    task = Task(index=1, title="valid completion", mode="B", target="seed.txt", verifier="true")
    cfg = SimpleNamespace(max_task_retries=0)
    monkeypatch.setattr(_codex_runner, "_print", lambda *_args, **_kwargs: None)

    for commit_result in ("abc123", "(no-commit)"):
        monkeypatch.setattr(
            _codex_runner,
            "_git_commit",
            lambda *_args, result=commit_result, **_kwargs: result,
        )
        result = _codex_runner._codex_verify_and_commit(
            SimpleNamespace(ok=True),
            task,
            1,
            tmp_path,
            "valid-commit",
            cfg,
            0,
            0.0,
            "",
        )
        assert result == (True, "", 0, commit_result)


# ── Dry-run cost estimate covers every executor tier ───────────────────────────


def test_dry_run_fable_task_without_est_cost_is_not_free(tmp_path, capsys):
    """A fable task with no est_cost_usd must get a non-zero inferred cost in the
    dry-run preview, not show as 'free' / drop out of the total."""
    plan = tmp_path / "plan.md"
    plan.write_text(
        "### Task 1: fable task\n"
        "- **mode:** A\n"
        "- **target:** out/file1.txt\n"
        "- **executor:** fable\n"
        "- **est_tokens:** 2000\n"
        "- **verifier:** true\n"
        "- **spec:**\n"
        "  make file 1\n"
    )

    rc = _engine.execute_plan(str(plan), repo=tmp_path, dry_run=True)

    assert rc == 0
    out = capsys.readouterr().out
    assert "free" not in out, "fable task must not be estimated as free"
    # Undeclared repos fall back fable->opus, so 2000 tok * $0.015/kT = $0.030.
    assert "fable→opus" in out
    assert "$0.030" in out
    assert "TOTAL estimate" in out
    assert "~$0.030" in out


def test_dry_run_fable_undeclared_renders_fallback(tmp_path, monkeypatch, capsys):
    """An undeclared repo previews fable tasks as fable->opus and prices them at
    the opus rate, never the full fable rate and never free."""
    monkeypatch.delenv("RENMARK_TOP_TIER", raising=False)
    plan = tmp_path / "plan.md"
    plan.write_text(
        "### Task 1: fable task\n"
        "- **mode:** A\n"
        "- **target:** out/file1.txt\n"
        "- **executor:** fable\n"
        "- **est_tokens:** 2000\n"
        "- **verifier:** true\n"
        "- **spec:**\n"
        "  make file 1\n"
    )

    rc = _engine.execute_plan(str(plan), repo=tmp_path, dry_run=True)

    assert rc == 0
    out = capsys.readouterr().out
    assert "free" not in out
    assert "fable→opus" in out
    assert "$0.030" in out
    assert "$0.060" not in out
    assert "TOTAL estimate" in out
    assert "~$0.030" in out


def test_dry_run_fable_declared_prices_full(tmp_path, monkeypatch, capsys):
    """A repo declaring top_tier: fable previews the executor unchanged and uses
    the full fable rate."""
    monkeypatch.delenv("RENMARK_TOP_TIER", raising=False)
    routing = tmp_path / ".renmark" / "memory" / "routing.md"
    routing.parent.mkdir(parents=True)
    routing.write_text("## Model tiers\n\ntop_tier: fable\n")
    plan = tmp_path / "plan.md"
    plan.write_text(
        "### Task 1: fable task\n"
        "- **mode:** A\n"
        "- **target:** out/file1.txt\n"
        "- **executor:** fable\n"
        "- **est_tokens:** 2000\n"
        "- **verifier:** true\n"
        "- **spec:**\n"
        "  make file 1\n"
    )

    rc = _engine.execute_plan(str(plan), repo=tmp_path, dry_run=True)

    assert rc == 0
    out = capsys.readouterr().out
    assert "free" not in out
    assert "fable→opus" not in out
    assert "fable" in out
    assert "$0.060" in out
    assert "TOTAL estimate" in out
    assert "~$0.060" in out


def test_dry_run_fable_downgrade_reprices_explicit_est_cost(tmp_path, monkeypatch, capsys):
    """A downgraded fable task with an explicit est_cost_usd must be repriced at
    the effective (opus) rate — the prefilled cost was estimated at the wrong
    tier and must not leak into the row or the total."""
    monkeypatch.delenv("RENMARK_TOP_TIER", raising=False)
    plan = tmp_path / "plan.md"
    plan.write_text(
        "### Task 1: fable task\n"
        "- **mode:** A\n"
        "- **target:** out/file1.txt\n"
        "- **executor:** fable\n"
        "- **est_tokens:** 1000\n"
        "- **est_cost_usd:** 0.030\n"
        "- **verifier:** true\n"
        "- **spec:**\n"
        "  make file 1\n"
    )

    rc = _engine.execute_plan(str(plan), repo=tmp_path, dry_run=True)

    assert rc == 0
    out = capsys.readouterr().out
    assert "free" not in out
    assert "fable→opus" in out
    # 1000 tok at the opus rate ($0.015/kT) = $0.015 — not the stale $0.030.
    assert "$0.015" in out
    assert "$0.030" not in out
    assert "TOTAL estimate" in out
    assert "~$0.015" in out

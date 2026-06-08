"""Unit tests for renmark.sizing — the proportional-pipeline tier classifier.

Hermetic: no network, no real git history dependence (we init throwaway repos
in tmp_path or monkeypatch the git subprocess). Thresholds are imported as
module constants so tuning them never silently breaks these tests.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from renmark import sizing
from renmark.parser import Task
from renmark.sizing import (
    DEFAULT_TIER,
    FULL_MIN_TASKS,
    LITE_MAX_TASKS,
    TIER_FULL,
    TIER_LITE,
    TIER_STANDARD,
    classify_diff,
    classify_plan,
)


def _task(
    index: int,
    target: str,
    *,
    complexity: str = "medium",
    est_tokens: int | None = None,
) -> Task:
    """Build a minimal valid Task for classification (parser not exercised)."""
    return Task(
        index=index,
        title=f"task {index}",
        mode="A",
        target=target,
        verifier="true",
        spec="do a thing",
        complexity=complexity,
        est_tokens=est_tokens,
    )


# ── classify_plan ────────────────────────────────────────────────────────────


def test_all_doc_small_set_is_lite() -> None:
    """<= LITE_MAX_TASKS doc/config targets, no hard, no core → lite."""
    tasks = [_task(i + 1, f"docs/page{i}.md") for i in range(LITE_MAX_TASKS)]
    assert len(tasks) <= LITE_MAX_TASKS
    assert classify_plan(tasks) == TIER_LITE


def test_any_hard_task_is_never_lite() -> None:
    """A single hard task forbids the lite lane (>= standard)."""
    tasks = [
        _task(1, "docs/a.md"),
        _task(2, "docs/b.md", complexity="hard"),
    ]
    result = classify_plan(tasks)
    assert result in {TIER_STANDARD, TIER_FULL}
    assert result != TIER_LITE


def test_core_module_target_is_at_least_standard() -> None:
    """A single simple edit to a core module (renmark/) must not be lite."""
    tasks = [_task(1, "renmark/parser.py", complexity="simple")]
    result = classify_plan(tasks)
    assert result in {TIER_STANDARD, TIER_FULL}
    assert result != TIER_LITE


def test_many_tasks_is_full() -> None:
    """Strictly more than FULL_MIN_TASKS tasks → full regardless of content."""
    n = FULL_MIN_TASKS + 1
    tasks = [_task(i + 1, f"docs/page{i}.md") for i in range(n)]
    assert classify_plan(tasks) == TIER_FULL


def test_empty_list_degrades_to_standard() -> None:
    assert classify_plan([]) == TIER_STANDARD
    assert DEFAULT_TIER == TIER_STANDARD


def test_classify_plan_never_raises_on_malformed_input() -> None:
    """None-ish / malformed task lists degrade safely, never raise."""
    assert classify_plan(None) == DEFAULT_TIER  # type: ignore[arg-type]
    # A list of objects missing the expected attributes must not raise.
    assert classify_plan([object(), object()]) in {  # type: ignore[list-item]
        TIER_LITE,
        TIER_STANDARD,
        TIER_FULL,
    }


# ── classify_diff ──────────────────────────────────────────────────────────


def _init_repo(path: Path) -> None:
    def run(*args: str) -> None:
        subprocess.run(
            ["git", "-C", str(path), *args],
            check=True,
            capture_output=True,
            text=True,
        )

    run("init", "-q")
    run("config", "user.email", "test@example.com")
    run("config", "user.name", "test")
    run("config", "commit.gpgsign", "false")


def _commit_all(path: Path, msg: str) -> None:
    subprocess.run(
        ["git", "-C", str(path), "add", "-A"], check=True, capture_output=True, text=True
    )
    subprocess.run(
        ["git", "-C", str(path), "commit", "-q", "-m", msg],
        check=True,
        capture_output=True,
        text=True,
    )


def test_classify_diff_tiny_doc_change_is_lite(tmp_path: Path) -> None:
    """A throwaway repo whose only diff vs base is a tiny doc edit → lite."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    (repo / "README.md").write_text("hello\n", encoding="utf-8")
    _commit_all(repo, "base")

    # Capture the initial branch name (master or main depending on git config)
    # BEFORE branching, so the base_ref is unambiguous.
    base = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "--abbrev-ref", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    # Branch HEAD ahead of base with a tiny doc-only change.
    subprocess.run(
        ["git", "-C", str(repo), "checkout", "-q", "-b", "work"],
        check=True,
        capture_output=True,
        text=True,
    )
    (repo / "README.md").write_text("hello\nworld\n", encoding="utf-8")
    _commit_all(repo, "tiny doc edit")

    assert classify_diff(repo, base_ref=base) == TIER_LITE


def test_classify_diff_no_git_degrades_to_standard(tmp_path: Path) -> None:
    """A non-repo directory must degrade to standard without raising."""
    not_a_repo = tmp_path / "plain"
    not_a_repo.mkdir()
    assert classify_diff(not_a_repo) == DEFAULT_TIER


def test_classify_diff_monkeypatched_large_diff_is_full(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Monkeypatch the git subprocess to return a large --stat → full."""

    class _Proc:
        returncode = 0
        stdout = (
            " a.py | 200 ++++++++++\n"
            " b.py | 250 ++++++++++\n"
            " 2 files changed, 400 insertions(+), 50 deletions(-)\n"
        )

    def fake_run(*args: object, **kwargs: object) -> _Proc:
        return _Proc()

    monkeypatch.setattr(sizing.subprocess, "run", fake_run)
    assert classify_diff("/whatever") == TIER_FULL


def test_classify_diff_monkeypatched_tiny_doc_is_lite(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Monkeypatch git to a tiny doc-only --stat → lite (no real repo)."""

    class _Proc:
        returncode = 0
        stdout = (
            " docs/readme.md | 4 ++--\n"
            " 1 file changed, 2 insertions(+), 2 deletions(-)\n"
        )

    def fake_run(*args: object, **kwargs: object) -> _Proc:
        return _Proc()

    monkeypatch.setattr(sizing.subprocess, "run", fake_run)
    assert classify_diff("/whatever") == TIER_LITE

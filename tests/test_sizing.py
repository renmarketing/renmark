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
    """None-ish / malformed task lists degrade to the SAFE default, never lite.

    Safety contract: a malformed task must NEVER reach the lite lane (lite skips
    the full review). The result must be exactly DEFAULT_TIER ('standard') — not
    merely "any tier".
    """
    assert classify_plan(None) == DEFAULT_TIER  # type: ignore[arg-type]
    # Bare objects miss target/complexity entirely → standard, never lite.
    assert classify_plan([object(), object()]) == DEFAULT_TIER  # type: ignore[list-item]


def test_malformed_target_degrades_to_standard() -> None:
    """A task with a missing / blank / non-str target → standard (never lite)."""

    class _Bad:
        target = ""  # blank target
        complexity = "simple"

    assert classify_plan([_Bad()]) == DEFAULT_TIER  # type: ignore[list-item]


def test_unrecognized_complexity_degrades_to_standard() -> None:
    """A task whose complexity is not simple/medium/hard → standard (never lite)."""

    class _Bad:
        target = "docs/a.md"
        complexity = "trivial"  # not a recognized complexity

    assert classify_plan([_Bad()]) == DEFAULT_TIER  # type: ignore[list-item]


def test_code_path_containing_template_is_not_lite() -> None:
    """A CODE file whose name contains 'template' is NOT doc/config → never lite.

    Regression for the substring bug: 'src/templates_engine.py' is real .py code
    and must not be classified lite *as doc/config* just because the path
    contains 'template'. With non-trivial est_tokens (so the very-small
    est_tokens lite path does NOT fire), a code file that was wrongly seen as
    doc/config would have gone lite via all_doc_config — it must be standard.
    """
    tasks = [
        _task(
            1,
            "src/templates_engine.py",
            complexity="simple",
            est_tokens=sizing.LITE_MAX_EST_TOKENS + 1,
        )
    ]
    result = classify_plan(tasks)
    assert result == TIER_STANDARD
    assert result != TIER_LITE
    # And the underlying predicate must agree.
    assert sizing._is_doc_or_config("src/templates_engine.py") is False
    assert sizing._is_doc_or_config("renmark/template_loader.py") is False
    # A genuine template file (suffix match) IS doc/config.
    assert sizing._is_doc_or_config("plugin/templates/CLAUDE.md.template") is True
    assert sizing._is_doc_or_config("ci/config.yaml.j2") is True


# ── resolve_override ─────────────────────────────────────────────────────────


def test_resolve_override_none_keeps_classified() -> None:
    assert sizing.resolve_override(TIER_STANDARD, None) == TIER_STANDARD
    assert sizing.resolve_override(TIER_FULL, None) == TIER_FULL
    assert sizing.resolve_override(TIER_LITE, None) == TIER_LITE


def test_resolve_override_full_always_escalates() -> None:
    """--full always wins (escalate is the safe direction)."""
    assert sizing.resolve_override(TIER_LITE, "full") == TIER_FULL
    assert sizing.resolve_override(TIER_STANDARD, "full") == TIER_FULL
    assert sizing.resolve_override(TIER_FULL, "full") == TIER_FULL


def test_resolve_override_lite_only_downgrades_standard() -> None:
    """--lite narrows ONLY a 'standard' classification; refused on 'full'."""
    # Allowed: standard → lite.
    assert sizing.resolve_override(TIER_STANDARD, "lite") == TIER_LITE
    # No-op: already lite stays lite.
    assert sizing.resolve_override(TIER_LITE, "lite") == TIER_LITE
    # REFUSED: classifier said full (hard/core/large) → keep full, never lite.
    assert sizing.resolve_override(TIER_FULL, "lite") == TIER_FULL
    assert sizing.resolve_override(TIER_FULL, "lite") != TIER_LITE


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


def test_classify_diff_invalid_base_ref_degrades_to_standard(tmp_path: Path) -> None:
    """A nonexistent base_ref in a real repo → standard (git returns nonzero)."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    (repo / "README.md").write_text("hi\n", encoding="utf-8")
    _commit_all(repo, "base")
    assert classify_diff(repo, base_ref="no-such-ref-xyz") == DEFAULT_TIER


def test_classify_diff_timeout_degrades_to_standard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A git subprocess timeout must degrade to standard, never raise."""

    def fake_run(*args: object, **kwargs: object) -> object:
        raise subprocess.TimeoutExpired(cmd="git", timeout=1)

    monkeypatch.setattr(sizing.subprocess, "run", fake_run)
    assert classify_diff("/whatever") == DEFAULT_TIER


def test_classify_diff_unparseable_range_degrades_to_standard() -> None:
    """An unsafe / unparseable diff_range degrades to standard (no git run)."""
    # Shell metacharacters and option-looking ranges are rejected before git.
    assert classify_diff("/whatever", diff_range="; rm -rf /") == DEFAULT_TIER
    assert classify_diff("/whatever", diff_range="--output=/etc/passwd") == DEFAULT_TIER
    assert classify_diff("/whatever", diff_range="") == DEFAULT_TIER


def test_classify_diff_explicit_range_passthrough(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A valid diff_range is passed to git and classified (here: lite doc)."""
    captured: dict[str, object] = {}

    class _Proc:
        returncode = 0
        stdout = (
            " docs/readme.md | 4 ++--\n"
            " 1 file changed, 2 insertions(+), 2 deletions(-)\n"
        )

    def fake_run(args: object, *rest: object, **kwargs: object) -> _Proc:
        captured["args"] = args
        return _Proc()

    monkeypatch.setattr(sizing.subprocess, "run", fake_run)
    assert classify_diff("/whatever", diff_range="HEAD~3..HEAD") == TIER_LITE
    # The explicit range reached the git argv, not the base_ref default.
    assert "HEAD~3..HEAD" in captured["args"]  # type: ignore[operator]


def test_safe_rev_arg_accepts_real_ranges() -> None:
    """The rev-arg validator accepts the ranges codereview actually uses."""
    for good in ("HEAD~3..HEAD", "main..feature", "HEAD", "abc123", "v1.0..v2.0"):
        assert sizing._is_safe_rev_arg(good) is True
    for bad in ("", "-x", "; rm -rf /", "a b", "main..feat;ls", "$(whoami)"):
        assert sizing._is_safe_rev_arg(bad) is False

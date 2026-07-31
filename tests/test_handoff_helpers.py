"""Tests for P4 file-handoff helpers: cmd_task_brief and cmd_review_package.

Load-bearing property: stdout is ONLY the written path — no brief/diff body
must ever leak through (REQ-5 / no-diffs-in-orchestrator rule).
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from renmark.cli import cmd_review_package, cmd_task_brief, main
from renmark.cli.commands import (
    ReviewFindingSummary,
    bounded_review_findings,
    build_review_fix_selector,
    write_scoped_fix_package,
)
from renmark.interaction import continue_selector

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

MINIMAL_PLAN = """\
### Task 1: Add greeting
- **mode:** A
- **target:** src/hello.py
- **executor:** codex
- **complexity:** simple
- **verifier:** echo ok
- **spec:**
  Write a hello() function that returns "hello".

### Task 2: Add farewell
- **mode:** A
- **target:** src/bye.py
- **executor:** sonnet
- **complexity:** medium
- **serves:** REQ-2
- **verifier:** pytest -q tests/
- **spec:**
  Write a bye() function that returns "bye".
"""


@pytest.fixture()
def plan_file(tmp_path: Path) -> Path:
    p = tmp_path / "2026-06-25-demo.plan.md"
    p.write_text(MINIMAL_PLAN, encoding="utf-8")
    return p


@pytest.fixture()
def review_findings() -> list[dict[str, object]]:
    """Structured review inputs, including more entries than the handoff cap."""
    return [
        {"id": "critical-auth", "severity": "Critical", "file": "auth.py", "summary": "leaks token"},
        {"id": "major-cache", "severity": "Major", "file": "cache.py", "summary": "uses stale state"},
        {"id": "minor-style", "severity": "Minor", "file": "style.py", "summary": "needs cleanup"},
        {"id": "nit-docs", "severity": "Nit", "file": "docs.py", "summary": "spelling"},
        {"id": "unknown", "severity": "Unranked", "file": "other.py", "summary": "needs triage"},
        {"id": "omitted", "severity": "Minor", "file": "later.py", "summary": "must be capped"},
    ]


@pytest.fixture()
def safe_review_findings() -> list[dict[str, object]]:
    return [
        {"id": "major-cache", "severity": "major", "file": "cache.py", "summary": "uses stale state"},
        {"id": "minor-style", "severity": "minor", "file": "style.py", "summary": "needs cleanup"},
    ]


# ---------------------------------------------------------------------------
# cmd_task_brief
# ---------------------------------------------------------------------------


def test_task_brief_writes_file_with_task_spec(tmp_path: Path, plan_file: Path, capsys) -> None:
    """Brief file must contain the task's spec text."""
    rc = cmd_task_brief(str(plan_file), 1, repo=tmp_path)
    assert rc == 0
    captured = capsys.readouterr()
    path = Path(captured.out.strip())
    assert path.exists(), f"brief file not created at {path}"
    body = path.read_text(encoding="utf-8")
    assert 'Write a hello() function' in body


def test_task_brief_contains_target_verifier_executor(tmp_path: Path, plan_file: Path, capsys) -> None:
    """Brief must include target, verifier, and executor so a subagent has everything it needs."""
    rc = cmd_task_brief(str(plan_file), 1, repo=tmp_path)
    assert rc == 0
    path = Path(capsys.readouterr().out.strip())
    body = path.read_text(encoding="utf-8")
    assert "src/hello.py" in body
    assert "echo ok" in body
    assert "codex" in body


def test_task_brief_stdout_is_only_path(tmp_path: Path, plan_file: Path, capsys) -> None:
    """The load-bearing property: stdout must be exactly one line — the path — no body."""
    rc = cmd_task_brief(str(plan_file), 1, repo=tmp_path)
    assert rc == 0
    out = capsys.readouterr().out
    # Exactly one non-empty line
    lines = [ln for ln in out.splitlines() if ln.strip()]
    assert len(lines) == 1, f"expected 1 path line, got {len(lines)}: {out!r}"
    # That line must be a real path, not brief prose
    assert Path(lines[0]).exists()
    # Must NOT contain spec prose
    assert "hello" not in lines[0]
    assert "Write" not in lines[0]


def test_task_brief_path_inside_renmark_state(tmp_path: Path, plan_file: Path, capsys) -> None:
    """REQ-6: output must be inside .renmark/state/handoffs/."""
    rc = cmd_task_brief(str(plan_file), 1, repo=tmp_path)
    assert rc == 0
    path = Path(capsys.readouterr().out.strip())
    assert ".renmark" in path.parts or ".renmark" in str(path)
    assert "handoffs" in str(path)


def test_task_brief_deterministic_filename(tmp_path: Path, plan_file: Path, capsys) -> None:
    """Same plan+index → same filename on repeated calls (idempotent overwrite)."""
    rc1 = cmd_task_brief(str(plan_file), 2, repo=tmp_path)
    out1 = capsys.readouterr().out.strip()
    rc2 = cmd_task_brief(str(plan_file), 2, repo=tmp_path)
    out2 = capsys.readouterr().out.strip()
    assert rc1 == 0 and rc2 == 0
    assert out1 == out2, "repeated calls must produce the same path"


def test_task_brief_task2_contains_serves(tmp_path: Path, plan_file: Path, capsys) -> None:
    """Optional fields (serves) must appear in the brief when present."""
    rc = cmd_task_brief(str(plan_file), 2, repo=tmp_path)
    assert rc == 0
    path = Path(capsys.readouterr().out.strip())
    body = path.read_text(encoding="utf-8")
    assert "REQ-2" in body


def test_task_brief_missing_task_index_returns_error(tmp_path: Path, plan_file: Path, capsys) -> None:
    """Non-existent task index → rc=2, nothing written to stdout."""
    rc = cmd_task_brief(str(plan_file), 99, repo=tmp_path)
    assert rc == 2
    out = capsys.readouterr().out
    assert out.strip() == "", f"stdout should be empty on error, got {out!r}"


def test_task_brief_missing_plan_returns_error(tmp_path: Path, capsys) -> None:
    """Missing plan file → rc=2."""
    rc = cmd_task_brief(str(tmp_path / "nonexistent.md"), 1, repo=tmp_path)
    assert rc == 2


def test_task_brief_accepts_string_index_from_cli(tmp_path: Path, plan_file: Path, capsys) -> None:
    """The CLI arg parser passes the index as a STRING; it must still match the
    int task.index (regression: a str compared to int silently 'not found')."""
    rc = cmd_task_brief(str(plan_file), "1", repo=tmp_path)  # type: ignore[arg-type]
    assert rc == 0
    out = capsys.readouterr().out.strip()
    assert out.endswith("-task-1.brief.md"), f"expected a brief path, got {out!r}"
    assert (tmp_path / out).read_text(encoding="utf-8").startswith("# Task 1:")


def test_task_brief_non_numeric_index_returns_error(tmp_path: Path, plan_file: Path, capsys) -> None:
    """A non-numeric index → rc=2 with a clear error, nothing on stdout."""
    rc = cmd_task_brief(str(plan_file), "abc", repo=tmp_path)  # type: ignore[arg-type]
    assert rc == 2
    assert capsys.readouterr().out.strip() == ""


# ---------------------------------------------------------------------------
# M4 review / fix / re-review handoff helpers
# ---------------------------------------------------------------------------


def test_bounded_review_findings_caps_and_normalizes(review_findings: list[dict[str, object]]) -> None:
    """Only bounded metadata crosses the review handoff boundary."""
    findings = bounded_review_findings(review_findings)
    assert len(findings) == 5
    assert [item.finding_id for item in findings] == [
        "critical-auth", "major-cache", "minor-style", "nit-docs", "unknown",
    ]
    assert findings[-1].severity == "unknown"
    assert all(len(item.summary) <= 240 for item in findings)


def test_critical_and_major_findings_block_signoff(review_findings: list[dict[str, object]]) -> None:
    """Critical and Major findings remain explicit signoff blockers."""
    by_id = {item.finding_id: item for item in bounded_review_findings(review_findings)}
    assert by_id["critical-auth"].blocks_signoff is True
    assert by_id["major-cache"].blocks_signoff is True
    assert by_id["minor-style"].blocks_signoff is False


def test_safe_scoped_fix_package_is_pointer_only(
    tmp_path: Path, safe_review_findings: list[dict[str, object]]
) -> None:
    """A non-dangerous finding set may create a scoped, non-executing artifact."""
    reference = ".renmark/state/handoffs/review-base-head.pkg.md"
    artifact = write_scoped_fix_package(reference, safe_review_findings, repo=tmp_path)
    assert artifact is not None and artifact.exists()
    payload = json.loads(artifact.read_text(encoding="utf-8"))
    assert payload["artifact_type"] == "scoped_fix_package"
    assert payload["review_package_ref"] == reference
    assert payload["auto_fix"] is False
    assert payload["requires_fresh_verification"] is True
    assert payload["requires_rereview"] is True
    assert payload["finding_count"] == 2


def test_dangerous_finding_recommends_cancel_and_refuses_fix(
    tmp_path: Path, review_findings: list[dict[str, object]]
) -> None:
    """Dangerous review work stops at an explicit refusal boundary."""
    dangerous = review_findings[:1]
    selector = build_review_fix_selector(dangerous, tool_available=False)
    semantic = selector["semantic"]
    assert semantic["decision_id"] == "review_fix_rereview"
    assert semantic["dangerous"] is True
    assert [choice["code"] for choice in semantic["choices"]] == ["cancel", "fix", "rereview"]
    assert semantic["choices"][0]["recommended"] is True
    assert continue_selector(selector, "cancel").kind == "cancel"
    assert write_scoped_fix_package("review.pkg.md", dangerous, repo=tmp_path) is None


def test_forged_critical_summary_is_refused_by_scoped_fix_writer(tmp_path: Path) -> None:
    """Critical severity cannot be bypassed by a forged dangerous=False flag."""
    forged = ReviewFindingSummary(
        finding_id="critical-auth",
        severity="critical",
        target="auth.py",
        summary="leaks token",
        blocks_signoff=True,
        dangerous=False,
    )
    assert write_scoped_fix_package("review.pkg.md", (forged,), repo=tmp_path) is None


def test_forged_critical_summary_recommends_safe_selector_path() -> None:
    """A forged safe flag must not make fixing a critical finding recommended."""
    forged = ReviewFindingSummary(
        finding_id="critical-auth",
        severity="critical",
        target="auth.py",
        summary="leaks token",
        blocks_signoff=True,
        dangerous=False,
    )
    semantic = build_review_fix_selector((forged,), tool_available=False)["semantic"]
    choices = {choice["code"]: choice for choice in semantic["choices"]}

    assert semantic["dangerous"] is True
    assert choices["cancel"]["recommended"] is True
    assert choices["fix"]["recommended"] is False


def test_bounded_review_findings_clamps_requested_limit(review_findings: list[dict[str, object]]) -> None:
    """Callers cannot expand the review handoff past its five-finding cap."""
    findings = bounded_review_findings(review_findings, limit=99)
    assert len(findings) == 5


def test_clean_review_is_ready_for_rereview_without_host_rendering() -> None:
    """A clean result exposes the host-neutral re-review semantic decision."""
    selector = build_review_fix_selector((), tool_available=False)
    semantic = selector["semantic"]
    assert semantic["decision_id"] == "review_fix_rereview"
    assert semantic["dangerous"] is False
    assert [choice["code"] for choice in semantic["choices"]] == ["rereview", "cancel"]
    assert semantic["choices"][0]["recommended"] is True


# ---------------------------------------------------------------------------
# cmd_review_package
# ---------------------------------------------------------------------------


def _init_git_repo(path: Path) -> None:
    """Create a minimal git repo with two commits so we have a real ref range."""
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=str(path), check=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=str(path), check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=str(path), check=True)
    (path / "a.py").write_text("x = 1\n")
    subprocess.run(["git", "add", "a.py"], cwd=str(path), check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=str(path), check=True)
    (path / "b.py").write_text("y = 2\n")
    subprocess.run(["git", "add", "b.py"], cwd=str(path), check=True)
    subprocess.run(["git", "commit", "-q", "-m", "add b"], cwd=str(path), check=True)


@pytest.fixture()
def git_repo(tmp_path: Path) -> Path:
    _init_git_repo(tmp_path)
    return tmp_path


def test_review_package_writes_file(git_repo: Path, capsys) -> None:
    """Package file must be created."""
    rc = cmd_review_package("HEAD~1", "HEAD", repo=git_repo)
    assert rc == 0
    path = Path(capsys.readouterr().out.strip())
    assert path.exists(), f"package file not created at {path}"


def test_review_package_stdout_is_only_path(git_repo: Path, capsys) -> None:
    """The load-bearing property: stdout must be exactly the path, no diff body."""
    rc = cmd_review_package("HEAD~1", "HEAD", repo=git_repo)
    assert rc == 0
    out = capsys.readouterr().out
    lines = [ln for ln in out.splitlines() if ln.strip()]
    assert len(lines) == 1, f"expected 1 path line, got {len(lines)}: {out!r}"
    path = Path(lines[0])
    assert path.exists()
    # Must not contain diff content inline in stdout
    assert "@@" not in lines[0]
    assert "diff" not in lines[0].lower() or lines[0].endswith(".pkg.md")


def test_review_package_contains_stat_and_diff(git_repo: Path, capsys) -> None:
    """Package body must contain a ## Stat and ## Diff section."""
    rc = cmd_review_package("HEAD~1", "HEAD", repo=git_repo)
    assert rc == 0
    path = Path(capsys.readouterr().out.strip())
    body = path.read_text(encoding="utf-8")
    assert "## Stat" in body
    assert "## Diff" in body
    # The new file b.py should appear in the diff
    assert "b.py" in body


def test_review_package_path_inside_renmark_state(git_repo: Path, capsys) -> None:
    """REQ-6: output must be inside .renmark/state/handoffs/."""
    rc = cmd_review_package("HEAD~1", "HEAD", repo=git_repo)
    assert rc == 0
    path = Path(capsys.readouterr().out.strip())
    assert "handoffs" in str(path)
    assert ".renmark" in str(path)


def test_review_package_deterministic_filename(git_repo: Path, capsys) -> None:
    """Same ref range → same filename on repeated calls."""
    rc1 = cmd_review_package("HEAD~1", "HEAD", repo=git_repo)
    out1 = capsys.readouterr().out.strip()
    rc2 = cmd_review_package("HEAD~1", "HEAD", repo=git_repo)
    out2 = capsys.readouterr().out.strip()
    assert rc1 == 0 and rc2 == 0
    assert out1 == out2, "repeated calls must produce the same path"


def test_review_package_bad_ref_returns_error(git_repo: Path, capsys) -> None:
    """Invalid git refs → rc=2, nothing on stdout."""
    rc = cmd_review_package("nonexistent-base", "nonexistent-head", repo=git_repo)
    assert rc == 2
    out = capsys.readouterr().out
    assert out.strip() == "", f"stdout should be empty on error, got {out!r}"


# ---------------------------------------------------------------------------
# CLI integration (main() dispatch)
# ---------------------------------------------------------------------------


def test_main_task_brief_flag(tmp_path: Path, plan_file: Path, capsys) -> None:
    """--task-brief PLAN N must dispatch to cmd_task_brief via main()."""
    rc = main(["--repo", str(tmp_path), "--task-brief", str(plan_file), "1"])
    assert rc == 0
    out = capsys.readouterr().out
    lines = [ln for ln in out.splitlines() if ln.strip()]
    assert len(lines) == 1
    assert Path(lines[0]).exists()


def test_main_review_package_flag(git_repo: Path, capsys) -> None:
    """--review-package BASE HEAD must dispatch to cmd_review_package via main()."""
    rc = main(["--repo", str(git_repo), "--review-package", "HEAD~1", "HEAD"])
    assert rc == 0
    out = capsys.readouterr().out
    lines = [ln for ln in out.splitlines() if ln.strip()]
    assert len(lines) == 1
    assert Path(lines[0]).exists()


def test_main_task_brief_bad_index_errors(tmp_path: Path, plan_file: Path) -> None:
    """--task-brief with non-integer index must exit with SystemExit (argparse error)."""
    with pytest.raises(SystemExit):
        main(["--repo", str(tmp_path), "--task-brief", str(plan_file), "notanint"])

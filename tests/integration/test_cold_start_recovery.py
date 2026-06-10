"""Cold-start recovery: simulate /clear by tearing down a Python process,
then verify lifecycle.json alone tells us where to resume. Zero-LLM
recovery is the framework's load-bearing innovation (principle #6)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from renmark import lifecycle


def test_cold_start_after_clear(fixture_project: Path, repo_root: Path):
    """Write lifecycle.json mid-flight, then in a fresh Python subprocess
    (simulating a Claude Code /clear), read it back and confirm the
    recommended next command is correct."""
    repo = fixture_project
    lifecycle.write_lifecycle(
        repo,
        stage="created",
        feature="auth",
        branch="feature/auth",
        artifact_update=("plan", ".renmark/plans/x.plan.md"),
    )

    # Fresh process — nothing in memory, just file IO + the renmark package.
    code = f"""
import sys
sys.path.insert(0, {str(repo_root)!r})
from renmark import lifecycle
state = lifecycle.read_lifecycle({str(repo)!r})
print(state.stage)
print(state.feature)
print(lifecycle.next_recommended({str(repo)!r}))
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        check=True,
    )
    lines = result.stdout.strip().splitlines()
    assert lines[0] == "created"
    assert lines[1] == "auth"
    assert "/renmark:verify" in lines[2]


def test_cold_start_with_pending_approval(fixture_project: Path, repo_root: Path):
    """If a human review gate is pending, cold start MUST direct to approve."""
    repo = fixture_project
    lifecycle.write_lifecycle(
        repo,
        stage="documented",
        feature="x",
        branch="x",
        human_review_required=True,
        human_review_for="release-v0.3.1",
    )
    code = f"""
import sys
sys.path.insert(0, {str(repo_root)!r})
from renmark import lifecycle
print(lifecycle.next_recommended({str(repo)!r}))
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "/renmark:approve" in result.stdout


def test_cold_start_with_no_lifecycle(fixture_project: Path, repo_root: Path):
    """No lifecycle.json = no in-flight feature. Cold start should say so."""
    repo = fixture_project
    # Don't write anything. Just read.
    code = f"""
import sys
sys.path.insert(0, {str(repo_root)!r})
from renmark import lifecycle
print(lifecycle.next_recommended({str(repo)!r}))
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "/renmark:start" in result.stdout or "no feature" in result.stdout


def test_cold_start_recovers_at_every_stage(fixture_project: Path, repo_root: Path):
    """Verify cold-start works no matter which stage the feature is in."""
    repo = fixture_project
    expected_routes = {
        "brainstorm-complete": "/renmark:plan",
        "plan-validated": "/renmark:orchestrate",
        "created": "/renmark:verify",
        "verified": "/renmark:codereview",
        # No /renmark:release skill ships — ready-to-release surfaces the
        # manual tag/zip hint, never a dead pointer.
        "ready-to-release": "manual",
    }
    for stage, expected in expected_routes.items():
        lifecycle.write_lifecycle(repo, stage=stage, feature="x", branch="x")
        rec = lifecycle.next_recommended(repo)
        assert expected in rec, f"stage={stage}: got {rec!r}, expected {expected}"

"""Integration test gating + fixtures.

Set ``RENMARK_SMOKE=1`` in the environment to enable. Default behavior is
to skip — unit tests stay fast (pytest tests/ -q completes in ~3s, smoke
suite takes ~30s and shells out to subprocess).
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest


def pytest_collection_modifyitems(config, items):
    """Skip integration tests unless RENMARK_SMOKE=1 is set."""
    if os.environ.get("RENMARK_SMOKE") == "1":
        return
    skip_marker = pytest.mark.skip(reason="set RENMARK_SMOKE=1 to enable integration tests")
    for item in items:
        if "tests/integration" in str(item.fspath):
            item.add_marker(skip_marker)


@pytest.fixture
def repo_root() -> Path:
    """Path to the renmark repo under test."""
    return Path(__file__).resolve().parent.parent.parent


@pytest.fixture
def fixture_project(tmp_path: Path) -> Path:
    """Build a throwaway .renmark/-shaped project for lifecycle smoke tests.

    Contains: an empty git repo, a baseline .renmark/ directory structure.
    """
    proj = tmp_path / "demo-project"
    proj.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=proj, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=proj, check=True)
    subprocess.run(["git", "config", "user.name", "smoke"], cwd=proj, check=True)

    # baseline .renmark/ layout (subset — only what smoke tests touch).
    for sub in ("memory", "plans", "specs", "reviews", "state"):
        (proj / ".renmark" / sub).mkdir(parents=True)
    (proj / ".renmark" / "memory" / "stack.md").write_text("# stack\n\n(empty)\n")
    (proj / "src").mkdir()
    (proj / "src" / "main.py").write_text("def main():\n    print('hi')\n")
    subprocess.run(["git", "add", "-A"], cwd=proj, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=proj, check=True)
    return proj


@pytest.fixture
def fixture_plan(fixture_project: Path) -> Path:
    """Write a plain plan into the fixture project and return its path."""
    plan = fixture_project / ".renmark" / "plans" / "2026-05-21-demo.plan.md"
    plan.write_text(
        "# Plan: demo feature\n\n"
        "## Tasks\n\n"
        "### Task 1: Add greeting constant\n"
        "- **mode:** A\n"
        "- **target:** src/greeting.py\n"
        "- **context_files:** []\n"
        "- **executor:** codex\n"
        "- **verifier:** python -c \"import src.greeting as g; assert g.GREETING == 'hi'\"\n"
        "- **verifier_timeout_s:** 5\n"
        "- **spec:**\n"
        "  Create src/greeting.py with `GREETING = 'hi'` and nothing else.\n"
    )
    return plan

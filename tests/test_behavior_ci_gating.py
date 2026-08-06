"""---
artifact_type: pytest-test-module
schema_version: 1
created_at: 2026-08-06T00:00:00-04:00
source_sha: "6c0d35d2b1c16eaf44b2b9419da81bc9ecaf56a9"
related_plan: "Task 14: CI-gating regression test"
generator: codex
stale_after: null
dependency_refs:
  - "renmark/cli/_dispatch_flags.py"
completion_state: complete
confidence: high
validation_status: unvalidated
retry_count: 0
parser_success: true
schema_compliance: true
---

Add a CI-gating regression test that shells out to `renmark-execute --behavior`
from the repo root and checks both the exit code and the printed behavior
summary line.

## Summary
- Added a subprocess-based regression test for `renmark-execute --behavior`.
- Asserts exit code `0` so the deterministic tier stays CI-safe.
- Uses a multiline regex to catch partial-pass summaries with nonzero failures.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_behavior_ci_gating_succeeds_and_reports_clean_summary() -> None:
    proc = subprocess.run(
        ["renmark-execute", "--behavior"],
        cwd=_repo_root(),
        check=False,
        capture_output=True,
        text=True,
    )

    assert proc.returncode == 0
    output = proc.stdout + proc.stderr
    assert re.search(r"^behavior: \d+/\d+ passed, 0 failed$", output, re.MULTILINE)

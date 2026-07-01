"""
---
artifact_type: task_output
schema_version: 1
created_at: 2026-07-01T00:00:00-04:00
source_sha: ecd28f1
related_plan: null
generator: codex
completion_state: complete
confidence: high
validation_status: unvalidated
retry_count: 0
parser_success: true
schema_compliance: true
dependency_refs:
  - renmark/mode.py
---
Pytest unit tests for ``renmark.mode`` using ``tmp_path`` as an isolated repo
root. The tests follow the existing style in ``tests/``: direct assertions,
small helpers only where needed, and no writes outside the temporary repo.

## Summary
- Covers set/read round-trips for both persisted operating modes.
- Verifies missing, corrupt, non-dict, and unknown-value reads degrade to ``None``.
- Asserts invalid ``set_mode`` raises ``ValueError`` without corrupting state.
- Checks ``clear_mode`` is idempotent and resets persisted state.
- Confirms per-skill default-mode mappings, including roadmap and unknown fallback.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from renmark import mode


def test_set_mode_round_trip_conductor(tmp_path: Path) -> None:
    mode.set_mode(tmp_path, "conductor")
    assert mode.read_mode(tmp_path) == "conductor"

    data = json.loads((tmp_path / ".renmark" / "state" / "mode.json").read_text())
    assert data == {"mode": "conductor"}


def test_set_mode_round_trip_orchestrator(tmp_path: Path) -> None:
    mode.set_mode(tmp_path, "orchestrator")
    assert mode.read_mode(tmp_path) == "orchestrator"

    data = json.loads((tmp_path / ".renmark" / "state" / "mode.json").read_text())
    assert data == {"mode": "orchestrator"}


def test_clear_mode_resets_persisted_state(tmp_path: Path) -> None:
    mode.set_mode(tmp_path, "conductor")
    assert mode.read_mode(tmp_path) == "conductor"

    mode.clear_mode(tmp_path)

    assert mode.read_mode(tmp_path) is None


def test_read_mode_missing_file_returns_none(tmp_path: Path) -> None:
    assert mode.read_mode(tmp_path) is None


def test_read_mode_corrupt_json_returns_none(tmp_path: Path) -> None:
    path = tmp_path / ".renmark" / "state" / "mode.json"
    path.parent.mkdir(parents=True)
    path.write_text("NOT JSON {{{", encoding="utf-8")

    assert mode.read_mode(tmp_path) is None


@pytest.mark.parametrize(
    ("payload", "label"),
    [
        ([1, 2, 3], "non-dict"),
        ({"mode": "bogus"}, "unknown mode"),
    ],
)
def test_read_mode_invalid_payloads_return_none(
    tmp_path: Path, payload: object, label: str
) -> None:
    path = tmp_path / ".renmark" / "state" / "mode.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(payload), encoding="utf-8")

    assert mode.read_mode(tmp_path) is None, label


def test_set_mode_bogus_raises_and_writes_no_file(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        mode.set_mode(tmp_path, "bogus")

    assert not (tmp_path / ".renmark" / "state" / "mode.json").exists()
    assert mode.read_mode(tmp_path) is None


def test_set_mode_bogus_preserves_prior_value(tmp_path: Path) -> None:
    mode.set_mode(tmp_path, "conductor")
    before = (tmp_path / ".renmark" / "state" / "mode.json").read_text(encoding="utf-8")

    with pytest.raises(ValueError):
        mode.set_mode(tmp_path, "bogus")

    after = (tmp_path / ".renmark" / "state" / "mode.json").read_text(encoding="utf-8")
    assert after == before
    assert mode.read_mode(tmp_path) == "conductor"


def test_clear_mode_when_absent_is_idempotent(tmp_path: Path) -> None:
    mode.clear_mode(tmp_path)
    assert mode.read_mode(tmp_path) is None


@pytest.mark.parametrize("skill", ["debug", "brainstorm"])
def test_default_mode_for_skill_conductor_cases(skill: str) -> None:
    assert mode.default_mode_for_skill(skill) == "conductor"


@pytest.mark.parametrize("skill", ["start", "feature", "orchestrate", "finish", "loop"])
def test_default_mode_for_skill_orchestrator_pipeline_cases(skill: str) -> None:
    assert mode.default_mode_for_skill(skill) == "orchestrator"


@pytest.mark.parametrize("skill", ["roadmap", "zzz"])
def test_default_mode_for_skill_falls_back_to_orchestrator(skill: str) -> None:
    assert mode.default_mode_for_skill(skill) == "orchestrator"

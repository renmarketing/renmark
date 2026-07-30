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
retry_count: 1
parser_success: true
schema_compliance: true
dependency_refs:
  - renmark/mode.py
---
Pytest unit tests for ``renmark.mode`` using ``tmp_path`` as an isolated repo
root. The tests assert the canonical delivery-state routing and legacy
compatibility guarantees without re-introducing a public persisted
``conductor`` value.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import unittest.mock as mock

import pytest

from renmark import mode


@pytest.fixture(autouse=True)
def clear_persisted_repos() -> None:
    mode._PERSISTED_REPOS.clear()


def test_mode_state_path_points_at_state_subdir(tmp_path: Path) -> None:
    path = mode.mode_state_path(tmp_path)
    assert path == tmp_path / ".renmark" / "state" / "mode.json"
    assert str(path).endswith(os.path.join(".renmark", "state", "mode.json"))
    assert mode.MODE_REL == ".renmark/state/mode.json"


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        (
            {"intent": "vague-new-product", "entry": "start"},
            mode.DeliveryState("agency", "guided"),
        ),
        (
            {"intent": "defined-feature", "entry": "feature"},
            mode.DeliveryState("orchestrator", "async"),
        ),
        (
            {"intent": "unknown", "entry": "feature"},
            mode.DeliveryState("orchestrator", "async"),
        ),
        (
            {"intent": "unknown", "entry": "fix"},
            mode.DeliveryState("orchestrator", "async"),
        ),
        (
            {"intent": "debug", "entry": "start"},
            mode.DeliveryState("orchestrator", "guided"),
        ),
        (
            {"intent": "unknown", "entry": "debug"},
            mode.DeliveryState("orchestrator", "guided"),
        ),
    ],
)
def test_resolve_delivery_state_routing_matrix(
    kwargs: dict[str, str], expected: mode.DeliveryState
) -> None:
    assert mode.resolve_delivery_state(**kwargs) == expected


@pytest.mark.parametrize(
    ("owner_choice", "kwargs", "expected"),
    [
        (
            "agency",
            {"intent": "debug", "entry": "debug"},
            mode.DeliveryState("agency", "guided"),
        ),
        (
            ("orchestrator", "direct"),
            {"intent": "vague-new-product", "entry": "start"},
            mode.DeliveryState("orchestrator", "direct"),
        ),
        (
            "conductor",
            {"intent": "defined-feature", "entry": "feature"},
            mode.DeliveryState("orchestrator", "guided"),
        ),
    ],
)
def test_explicit_owner_choice_takes_precedence(
    owner_choice: mode.OwnerChoice,
    kwargs: dict[str, str],
    expected: mode.DeliveryState,
) -> None:
    assert mode.resolve_delivery_state(owner_choice, **kwargs) == expected


def test_persist_delivery_state_once_keeps_first_choice_for_repo(tmp_path: Path) -> None:
    first = mode.persist_delivery_state_once(
        tmp_path, None, intent="vague-new-product", entry="start"
    )
    second = mode.persist_delivery_state_once(
        tmp_path, None, intent="debug", entry="debug"
    )

    assert first == mode.DeliveryState("agency", "guided")
    assert second == mode.DeliveryState("orchestrator", "guided")
    assert mode.read_delivery_state(tmp_path) == first


def test_resume_reads_back_canonical_delivery_choice(tmp_path: Path) -> None:
    state = mode.DeliveryState("agency", "guided")
    mode.write_delivery_state(tmp_path, state)

    assert mode.read_delivery_state(tmp_path) == state


def test_write_delivery_state_persists_canonical_payload(tmp_path: Path) -> None:
    state = mode.DeliveryState("orchestrator", "direct")
    mode.write_delivery_state(tmp_path, state)

    data = json.loads((tmp_path / ".renmark" / "state" / "mode.json").read_text())
    assert data == {
        "delivery_mode": "orchestrator",
        "interaction_mode": "direct",
        "mode": "orchestrator",
    }
    assert data["mode"] != "conductor"


def test_legacy_conductor_payload_reads_as_guided_orchestrator(tmp_path: Path) -> None:
    path = tmp_path / ".renmark" / "state" / "mode.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"mode": "conductor"}), encoding="utf-8")

    assert mode.read_delivery_state(tmp_path) == mode.DeliveryState(
        "orchestrator", "guided"
    )
    assert mode.read_mode(tmp_path) == "orchestrator"


def test_set_mode_conductor_writes_canonical_state_only(tmp_path: Path) -> None:
    mode.set_mode(tmp_path, "conductor")

    data = json.loads((tmp_path / ".renmark" / "state" / "mode.json").read_text())
    assert data == {
        "delivery_mode": "orchestrator",
        "interaction_mode": "guided",
        "mode": "orchestrator",
    }
    assert mode.read_delivery_state(tmp_path) == mode.DeliveryState(
        "orchestrator", "guided"
    )
    assert mode.read_mode(tmp_path) == "orchestrator"


def test_set_mode_orchestrator_writes_canonical_state_only(tmp_path: Path) -> None:
    mode.set_mode(tmp_path, "orchestrator")

    data = json.loads((tmp_path / ".renmark" / "state" / "mode.json").read_text())
    assert data == {
        "delivery_mode": "orchestrator",
        "interaction_mode": "async",
        "mode": "orchestrator",
    }
    assert mode.read_mode(tmp_path) == "orchestrator"


def test_clear_mode_resets_persisted_state(tmp_path: Path) -> None:
    mode.set_mode(tmp_path, "orchestrator")
    assert mode.read_delivery_state(tmp_path) == mode.DeliveryState(
        "orchestrator", "async"
    )

    mode.clear_mode(tmp_path)

    assert mode.read_delivery_state(tmp_path) is None
    assert mode.read_mode(tmp_path) is None


def test_read_mode_missing_file_returns_none(tmp_path: Path) -> None:
    assert mode.read_delivery_state(tmp_path) is None
    assert mode.read_mode(tmp_path) is None


def test_read_mode_corrupt_json_returns_none(tmp_path: Path) -> None:
    path = tmp_path / ".renmark" / "state" / "mode.json"
    path.parent.mkdir(parents=True)
    path.write_text("NOT JSON {{{", encoding="utf-8")

    assert mode.read_delivery_state(tmp_path) is None
    assert mode.read_mode(tmp_path) is None


@pytest.mark.parametrize(
    ("payload", "label"),
    [
        ([1, 2, 3], "non-dict"),
        ({"mode": "bogus"}, "unknown legacy mode"),
        ({"delivery_mode": "agency", "interaction_mode": "bogus"}, "unknown interaction"),
    ],
)
def test_read_mode_invalid_payloads_return_none(
    tmp_path: Path, payload: object, label: str
) -> None:
    path = tmp_path / ".renmark" / "state" / "mode.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(payload), encoding="utf-8")

    assert mode.read_delivery_state(tmp_path) is None, label
    assert mode.read_mode(tmp_path) is None, label


def test_set_mode_bogus_raises_and_writes_no_file(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        mode.set_mode(tmp_path, "bogus")

    assert not (tmp_path / ".renmark" / "state" / "mode.json").exists()
    assert mode.read_delivery_state(tmp_path) is None


def test_set_mode_bogus_preserves_prior_value(tmp_path: Path) -> None:
    mode.set_mode(tmp_path, "orchestrator")
    before = (tmp_path / ".renmark" / "state" / "mode.json").read_text(encoding="utf-8")

    with pytest.raises(ValueError):
        mode.set_mode(tmp_path, "bogus")

    after = (tmp_path / ".renmark" / "state" / "mode.json").read_text(encoding="utf-8")
    assert after == before
    assert mode.read_delivery_state(tmp_path) == mode.DeliveryState(
        "orchestrator", "async"
    )


def test_clear_mode_when_absent_is_idempotent(tmp_path: Path) -> None:
    mode.clear_mode(tmp_path)
    assert mode.read_delivery_state(tmp_path) is None


def test_write_delivery_state_failure_propagates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _boom(*_args: object, **_kwargs: object) -> None:
        raise OSError("read-only file system")

    monkeypatch.setattr(Path, "write_text", _boom)

    with pytest.raises(OSError):
        mode.write_delivery_state(tmp_path, mode.DeliveryState("agency", "guided"))

    state_dir = tmp_path / ".renmark" / "state"
    assert not (state_dir / "mode.json").exists()
    leftovers = list(state_dir.glob("mode.json.tmp.*")) if state_dir.exists() else []
    assert leftovers == []


def test_write_delivery_state_replace_failure_propagates_and_cleans_tmp(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _boom(*_args: object, **_kwargs: object) -> None:
        raise OSError("cannot replace")

    monkeypatch.setattr(os, "replace", _boom)

    with pytest.raises(OSError):
        mode.write_delivery_state(tmp_path, mode.DeliveryState("orchestrator", "async"))

    state_dir = tmp_path / ".renmark" / "state"
    assert not (state_dir / "mode.json").exists()
    leftovers = list(state_dir.glob("mode.json.tmp.*")) if state_dir.exists() else []
    assert leftovers == []


def test_write_delivery_state_is_atomic_no_partial_file(tmp_path: Path) -> None:
    replaced: list[tuple[str, str]] = []
    real_replace = os.replace

    def _record(src: os.PathLike[str] | str, dst: os.PathLike[str] | str) -> None:
        replaced.append((str(src), str(dst)))
        real_replace(src, dst)

    with mock.patch.object(os, "replace", _record):
        mode.write_delivery_state(tmp_path, mode.DeliveryState("agency", "guided"))

    assert len(replaced) == 1
    src, dst = replaced[0]
    assert Path(src).parent == Path(dst).parent
    assert ".tmp." in Path(src).name
    assert dst.endswith(os.path.join(".renmark", "state", "mode.json"))
    assert mode.read_delivery_state(tmp_path) == mode.DeliveryState("agency", "guided")


def test_clear_mode_delete_failure_propagates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    mode.write_delivery_state(tmp_path, mode.DeliveryState("agency", "guided"))

    def _boom(*_args: object, **_kwargs: object) -> None:
        raise PermissionError("cannot unlink")

    monkeypatch.setattr(Path, "unlink", _boom)

    with pytest.raises(OSError):
        mode.clear_mode(tmp_path)


@pytest.mark.parametrize(
    ("skill", "expected"),
    [
        ("start", mode.DeliveryState("agency", "guided")),
        ("brainstorm", mode.DeliveryState("agency", "guided")),
        ("feature", mode.DeliveryState("orchestrator", "async")),
        ("orchestrate", mode.DeliveryState("orchestrator", "async")),
        ("finish", mode.DeliveryState("orchestrator", "async")),
        ("debug", mode.DeliveryState("orchestrator", "guided")),
        ("roadmap", mode.DeliveryState("orchestrator", "async")),
        ("zzz", mode.DeliveryState("orchestrator", "async")),
    ],
)
def test_default_delivery_state_for_skill(skill: str, expected: mode.DeliveryState) -> None:
    assert mode.default_delivery_state_for_skill(skill) == expected


@pytest.mark.parametrize(
    "skill",
    ["start", "brainstorm", "feature", "orchestrate", "finish", "debug", "roadmap", "zzz"],
)
def test_default_mode_for_skill_never_returns_public_conductor(skill: str) -> None:
    assert mode.default_mode_for_skill(skill) == "orchestrator"

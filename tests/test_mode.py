"""Tests for the canonical Agency/Orchestrator delivery-mode bridge."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from renmark import delivery_state as aggregate
from renmark import mode


@pytest.fixture(autouse=True)
def clear_persisted_repos() -> None:
    mode._PERSISTED_REPOS.clear()


def test_paths_distinguish_canonical_and_legacy_state(tmp_path: Path) -> None:
    assert mode.delivery_state_path(tmp_path) == (
        tmp_path / ".renmark" / "state" / "delivery.json"
    )
    assert mode.mode_state_path(tmp_path) == (
        tmp_path / ".renmark" / "state" / "mode.json"
    )


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
            {"intent": "debug", "entry": "debug"},
            mode.DeliveryState("orchestrator", "guided"),
        ),
    ],
)
def test_resolve_delivery_state_routing_matrix(
    kwargs: dict[str, str], expected: mode.DeliveryState
) -> None:
    assert mode.resolve_delivery_state(**kwargs) == expected


def test_canonical_state_wins_and_write_preserves_package_state(
    tmp_path: Path,
) -> None:
    original = aggregate.DeliveryState(
        run_id="delivery-123",
        active_milestone_id="m2",
        work_packages=[
            aggregate.WorkPackageSummary(
                package_id="wp-a", milestone_id="m2", title="A"
            )
        ],
        provenance_events=[
            aggregate.DeliveryProvenanceEvent(kind="approved", detail="scope")
        ],
    )
    aggregate.write_delivery_state(tmp_path, original)
    normalized_original = aggregate.read_delivery_state(tmp_path)

    mode.set_mode(tmp_path, "agency")

    persisted = aggregate.read_delivery_state(tmp_path)
    assert persisted.delivery_mode == "agency"
    assert persisted.execution_policy == "guided"
    assert persisted.run_id == normalized_original.run_id
    assert persisted.active_milestone_id == "m2"
    assert len(persisted.work_packages) == 1
    assert len(persisted.provenance_events) == 1
    assert not mode.mode_state_path(tmp_path).exists()


def test_persist_once_returns_existing_canonical_choice(tmp_path: Path) -> None:
    mode.set_mode(tmp_path, "agency")

    resumed = mode.persist_delivery_state_once(
        tmp_path, intent="debug", entry="debug"
    )

    assert resumed == mode.DeliveryState("agency", "guided")


def test_legacy_conductor_payload_maps_forward_when_canonical_missing(
    tmp_path: Path,
) -> None:
    path = mode.mode_state_path(tmp_path)
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"mode": "conductor"}), encoding="utf-8")

    assert mode.read_delivery_state(tmp_path) == mode.DeliveryState(
        "orchestrator", "guided"
    )
    assert mode.read_mode(tmp_path) == "orchestrator"


def test_canonical_state_takes_precedence_over_legacy_payload(tmp_path: Path) -> None:
    path = mode.mode_state_path(tmp_path)
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"mode": "conductor"}), encoding="utf-8")
    mode.set_mode(tmp_path, "agency")

    assert mode.read_mode(tmp_path) == "agency"


@pytest.mark.parametrize("choice", ["agency", "orchestrator"])
def test_set_mode_accepts_only_public_modes(tmp_path: Path, choice: str) -> None:
    mode.set_mode(tmp_path, choice)
    assert mode.read_mode(tmp_path) == choice


def test_set_mode_rejects_conductor_and_bogus_values(tmp_path: Path) -> None:
    for choice in ("conductor", "bogus"):
        with pytest.raises(ValueError):
            mode.set_mode(tmp_path, choice)
    assert mode.read_delivery_state(tmp_path) is None


def test_clear_mode_removes_canonical_and_legacy_state(tmp_path: Path) -> None:
    mode.set_mode(tmp_path, "agency")
    legacy = mode.mode_state_path(tmp_path)
    legacy.write_text(json.dumps({"mode": "conductor"}), encoding="utf-8")

    mode.clear_mode(tmp_path)

    assert mode.read_delivery_state(tmp_path) is None
    assert not mode.delivery_state_path(tmp_path).exists()
    assert not legacy.exists()


def test_corrupt_canonical_falls_back_to_valid_legacy(tmp_path: Path) -> None:
    canonical = mode.delivery_state_path(tmp_path)
    canonical.parent.mkdir(parents=True)
    canonical.write_text("not-json", encoding="utf-8")
    mode.mode_state_path(tmp_path).write_text(
        json.dumps({"mode": "conductor"}), encoding="utf-8"
    )

    assert mode.read_delivery_state(tmp_path) == mode.DeliveryState(
        "orchestrator", "guided"
    )


@pytest.mark.parametrize(
    ("skill", "expected"),
    [
        ("start", "agency"),
        ("brainstorm", "agency"),
        ("feature", "orchestrator"),
        ("debug", "orchestrator"),
        ("unknown", "orchestrator"),
    ],
)
def test_default_mode_for_skill_uses_two_public_modes(
    skill: str, expected: str
) -> None:
    assert mode.default_mode_for_skill(skill) == expected

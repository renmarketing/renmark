"""Persisted delivery-mode state for renmark.

The canonical public state is a two-axis delivery choice:

- delivery mode: ``agency`` or ``orchestrator``
- interaction mode: ``guided``, ``direct``, or ``async``

Canonical state lives at ``.renmark/state/delivery.json``. The former
``.renmark/state/mode.json`` remains a read-only migration source for callers
that still know this module as ``renmark.mode``.

Compatibility rules:
- reads never raise and degrade to ``None`` on missing/corrupt/unreadable data
- legacy ``{"mode": "conductor"}`` reads as ``orchestrator/guided``
- new writes never persist public ``conductor`` state
- legacy wrapper APIs remain available for callers that still use
  ``read_mode`` / ``set_mode`` / ``clear_mode`` / ``default_mode_for_skill``
"""

from __future__ import annotations

import contextlib
import json
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Literal, cast

from . import delivery_state as _delivery

Mode = Literal["conductor", "orchestrator"]
DeliveryMode = Literal["agency", "orchestrator"]
InteractionMode = Literal["guided", "direct", "async"]
IntentClass = Literal[
    "vague-new-product",
    "defined-feature",
    "defined-fix",
    "debug",
    "unknown",
]
EntryClass = Literal[
    "start",
    "feature",
    "fix",
    "debug",
    "brainstorm",
    "orchestrate",
    "finish",
    "roadmap",
    "meta",
    "unknown",
]
OwnerChoice = (
    DeliveryMode
    | Mode
    | tuple[DeliveryMode, InteractionMode]
    | tuple[Mode, InteractionMode]
)

MODE_REL = ".renmark/state/mode.json"
_MODE_REL = MODE_REL

_VALID_DELIVERY_MODES: frozenset[str] = frozenset({"agency", "orchestrator"})
_VALID_INTERACTION_MODES: frozenset[str] = frozenset({"guided", "direct", "async"})
_VALID_MODES: frozenset[str] = frozenset({"agency", "orchestrator"})

_PERSISTED_REPOS: set[Path] = set()


@dataclass(frozen=True, slots=True)
class DeliveryState:
    """Canonical persisted delivery state."""

    delivery_mode: DeliveryMode
    interaction_mode: InteractionMode

    @property
    def mode(self) -> Mode:
        """Legacy single-axis mode view for older callers."""
        return "orchestrator"

    def to_payload(self) -> dict[str, str]:
        """Serialize with legacy compatibility fields."""
        return {
            "delivery_mode": self.delivery_mode,
            "interaction_mode": self.interaction_mode,
            # Preserve the legacy field name/path but never write "conductor".
            "mode": self.mode,
        }


_FALLBACK_STATE = DeliveryState("orchestrator", "async")
_DEBUG_STATE = DeliveryState("orchestrator", "guided")
_AGENCY_STATE = DeliveryState("agency", "guided")
_DEFINED_WORK_STATE = DeliveryState("orchestrator", "async")

_DEFAULT_STATE_BY_SKILL: dict[str, DeliveryState] = {
    "debug": _DEBUG_STATE,
    "brainstorm": _AGENCY_STATE,
    "start": _AGENCY_STATE,
    "feature": _DEFINED_WORK_STATE,
    "orchestrate": _DEFINED_WORK_STATE,
    "finish": _DEFINED_WORK_STATE,
}


def mode_state_path(repo: str | Path) -> Path:
    """Return the legacy compatibility path (read-only for new writes)."""
    return Path(repo) / MODE_REL


def delivery_state_path(repo: str | Path) -> Path:
    """Return the canonical persisted delivery-state path."""
    return _delivery.delivery_state_path(repo)


def _mode_path(repo: str | Path) -> Path:
    return mode_state_path(repo)


def _normalized_repo(repo: str | Path) -> Path:
    return Path(repo).resolve()


def _state_from_parts(
    delivery_mode: str | None, interaction_mode: str | None
) -> DeliveryState | None:
    if (
        delivery_mode in _VALID_DELIVERY_MODES
        and interaction_mode in _VALID_INTERACTION_MODES
    ):
        return DeliveryState(
            cast(DeliveryMode, delivery_mode),
            cast(InteractionMode, interaction_mode),
        )
    return None


def _parse_owner_choice(choice: OwnerChoice | None) -> DeliveryState | None:
    if choice is None:
        return None
    if isinstance(choice, tuple) and len(choice) == 2:
        delivery_mode, interaction_mode = choice
        if delivery_mode == "conductor":
            delivery_mode = "orchestrator"
            interaction_mode = "guided"
        state = _state_from_parts(delivery_mode, interaction_mode)
        if state is None:
            raise ValueError(
                "invalid owner choice: expected delivery mode "
                "'agency'|'orchestrator' and interaction mode "
                "'guided'|'direct'|'async'"
            )
        return state
    if choice == "conductor":
        return _DEBUG_STATE
    if choice == "orchestrator":
        return _DEFINED_WORK_STATE
    if choice == "agency":
        return _AGENCY_STATE
    raise ValueError(
        "invalid owner choice: expected 'agency', 'orchestrator', "
        "'conductor', or a canonical (delivery_mode, interaction_mode) pair"
    )


def _state_from_legacy_mode(mode: str | None) -> DeliveryState | None:
    if mode == "conductor":
        return _DEBUG_STATE
    if mode == "orchestrator":
        return _DEFINED_WORK_STATE
    return None


def read_delivery_state(repo: str | Path) -> DeliveryState | None:
    """Return the persisted canonical delivery state for *repo*.

    Canonical ``delivery.json`` wins. The legacy ``mode.json`` path remains a
    read-only migration fallback, including conductor → orchestrator/guided.
    """
    canonical, report = _delivery.read_delivery_state_with_report(repo)
    if report.state == "loaded":
        return _state_from_parts(
            canonical.delivery_mode,
            canonical.execution_policy,
        )
    try:
        text = _mode_path(repo).read_text(encoding="utf-8")
        data = json.loads(text)
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    state = _state_from_parts(
        data.get("delivery_mode"),
        data.get("interaction_mode"),
    )
    if state is not None:
        return state
    return _state_from_legacy_mode(data.get("mode"))


def write_delivery_state(repo: str | Path, state: DeliveryState) -> None:
    """Update the canonical aggregate without erasing milestone/run state."""
    current, report = _delivery.read_delivery_state_with_report(repo)
    if report.state != "loaded":
        current = _delivery.default_delivery_state()
    updated = replace(
        current,
        delivery_mode=state.delivery_mode,
        execution_policy=state.interaction_mode,
    )
    _delivery.write_delivery_state(repo, updated)


def clear_delivery_state(repo: str | Path) -> None:
    """Remove canonical and legacy delivery-state selections for *repo*."""
    for path in (delivery_state_path(repo), _mode_path(repo)):
        with contextlib.suppress(FileNotFoundError):
            path.unlink()
    _PERSISTED_REPOS.discard(_normalized_repo(repo))


def resolve_delivery_state(
    owner_choice: OwnerChoice | None = None,
    *,
    intent: IntentClass = "unknown",
    entry: EntryClass = "unknown",
) -> DeliveryState:
    """Resolve the canonical delivery state for the current run.

    Resolution order:
    - explicit owner choice wins
    - debug work resolves to ``orchestrator/guided``
    - vague new-product work recommends ``agency/guided``
    - defined feature/fix work recommends ``orchestrator/async``
    - otherwise fall back to the entry default, then the global fallback
    """
    explicit = _parse_owner_choice(owner_choice)
    if explicit is not None:
        return explicit
    if intent == "debug" or entry == "debug":
        return _DEBUG_STATE
    if intent == "vague-new-product" or entry in {"start", "brainstorm"}:
        return _AGENCY_STATE
    if intent in {"defined-feature", "defined-fix"} or entry in {
        "feature",
        "fix",
        "orchestrate",
        "finish",
    }:
        return _DEFINED_WORK_STATE
    return _DEFAULT_STATE_BY_SKILL.get(entry, _FALLBACK_STATE)


def persist_delivery_state_once(
    repo: str | Path,
    owner_choice: OwnerChoice | None = None,
    *,
    intent: IntentClass = "unknown",
    entry: EntryClass = "unknown",
) -> DeliveryState:
    """Resolve and persist the current run's delivery state once per repo."""
    repo_key = _normalized_repo(repo)
    existing = read_delivery_state(repo)
    if existing is not None:
        _PERSISTED_REPOS.add(repo_key)
        return existing
    state = resolve_delivery_state(owner_choice, intent=intent, entry=entry)
    if repo_key not in _PERSISTED_REPOS:
        write_delivery_state(repo, state)
        _PERSISTED_REPOS.add(repo_key)
    return state


def read_mode(repo: str | Path) -> DeliveryMode | None:
    """Return the public two-mode delivery choice for *repo*."""
    state = read_delivery_state(repo)
    if state is None:
        return None
    return state.delivery_mode


def set_mode(repo: str | Path, mode: str) -> None:
    """Persist the public Agency/Orchestrator delivery choice."""
    if mode not in _VALID_MODES:
        raise ValueError(
            f"invalid mode {mode!r}: expected 'agency' or 'orchestrator'"
        )
    write_delivery_state(
        repo,
        resolve_delivery_state(cast(DeliveryMode, mode)),
    )
    _PERSISTED_REPOS.add(_normalized_repo(repo))


def clear_mode(repo: str | Path) -> None:
    """Compatibility wrapper for clearing the persisted mode state."""
    clear_delivery_state(repo)


def default_delivery_state_for_skill(skill: str) -> DeliveryState:
    """Return the canonical default delivery state for *skill*."""
    return resolve_delivery_state(entry=cast(EntryClass, skill))


def default_mode_for_skill(skill: str) -> DeliveryMode:
    """Return the public delivery-mode default for *skill*."""
    return default_delivery_state_for_skill(skill).delivery_mode

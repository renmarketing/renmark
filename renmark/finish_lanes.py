"""Declarative finish-lane registry — deterministic, zero-LLM, never-raises.

This module defines the four named finish lanes used by the renmark ``finish``
pipeline.  It is the single source of truth for lane capabilities and is
reused by ``plugin/skills/finish/SKILL.md`` today and by a future Agency Mode.

Design contract:

- Pure functions of their inputs.  No network calls, no subprocess, no LLM.
- **Never raises into the caller.**  Every function catches all exceptions and
  returns a safe default (``"quick"`` for lane selectors, empty/placeholder
  strings for text helpers, ``False`` for predicates).
- Every lane constant and capability flag is a module-level name so callers can
  import symbols rather than magic strings.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

# ── Lane type ──────────────────────────────────────────────────────────────────

#: The four named finish lanes, in ascending cost/scope.
Lane = Literal["quick", "release", "self-update", "full"]

#: Lane name constants (import these rather than bare strings).
LANE_QUICK: Lane = "quick"
LANE_RELEASE: Lane = "release"
LANE_SELF_UPDATE: Lane = "self-update"
LANE_FULL: Lane = "full"

# Canonical menu order — the position a numbered finish-menu selection maps to
# (1=quick, 2=release, 3=self-update, 4=full). Cheapest → most expensive.
LANE_ORDER: tuple[Lane, ...] = (LANE_QUICK, LANE_RELEASE, LANE_SELF_UPDATE, LANE_FULL)

# ── LaneSpec dataclass ────────────────────────────────────────────────────────


@dataclass(frozen=True)
class LaneSpec:
    """Declarative capability record for a finish lane.

    All boolean fields are ``False`` for the cheapest lane and progressively
    enabled as lane cost rises.  ``actions`` is an ordered tuple of short
    imperative descriptions — the finish skill iterates these to build its
    work-list.
    """

    name: str
    merges: bool
    releases: bool
    packages: bool
    updates_wsl: bool
    cleans_worktrees: bool
    verification: str
    cost_level: str
    actions: tuple[str, ...]


# ── Lane registry ─────────────────────────────────────────────────────────────

#: All registered lanes keyed by :data:`Lane` name.
LANES: dict[Lane, LaneSpec] = {
    LANE_QUICK: LaneSpec(
        name=LANE_QUICK,
        merges=False,
        releases=False,
        packages=False,
        updates_wsl=False,
        cleans_worktrees=False,
        verification="artifact-confirm",
        cost_level="low",
        actions=(
            "summarize state",
            "confirm verify/review artifacts exist",
        ),
    ),
    LANE_RELEASE: LaneSpec(
        name=LANE_RELEASE,
        merges=True,
        releases=True,
        packages=False,
        updates_wsl=False,
        cleans_worktrees=False,
        verification="re-verify",
        cost_level="medium",
        actions=(
            "verify release readiness",
            "merge when approved",
            "version/changelog/release when relevant",
        ),
    ),
    LANE_SELF_UPDATE: LaneSpec(
        name=LANE_SELF_UPDATE,
        merges=True,
        releases=True,
        packages=True,
        updates_wsl=True,
        cleans_worktrees=True,
        verification="re-verify+release-qa",
        cost_level="high",
        actions=(
            "merge branches/worktrees",
            "release/version bump",
            "package/zip renmark",
            "update/install renmark on WSL",
            "verify installed CLI/plugin",
            "clean worktrees",
            "document release",
        ),
    ),
    LANE_FULL: LaneSpec(
        name=LANE_FULL,
        merges=True,
        releases=True,
        packages=True,
        updates_wsl=True,
        cleans_worktrees=True,
        verification="deepest",
        cost_level="high",
        actions=(
            "all finish behaviours",
            "deepest verification",
            "release + package + install + cleanup where applicable",
        ),
    ),
}

# ── Public API ─────────────────────────────────────────────────────────────────


def is_renmark_repo(repo: str | Path) -> bool:
    """Return ``True`` iff *repo* root contains BOTH ``renmark/`` and
    ``plugin/skills/finish/SKILL.md``.

    Pure predicate — no side effects, never raises.  Missing paths, bad types,
    or any I/O error all yield ``False``.
    """
    try:
        root = Path(repo)
        has_package = (root / "renmark").is_dir()
        has_skill = (root / "plugin" / "skills" / "finish" / "SKILL.md").is_file()
        return has_package and has_skill
    except Exception:
        return False


def recommend_lane(
    repo: str | Path,
    *,
    is_self: bool | None = None,
    lifecycle_stage: str | None = None,
) -> Lane:
    """Return the cheapest safe lane for *repo*.

    Decision rules (applied in order):

    1. If *is_self* is ``True`` (explicit), OR *is_self* is ``None`` and
       :func:`is_renmark_repo` returns ``True`` → ``"self-update"``.
    2. If *lifecycle_stage* is one of ``{"reviewed", "ready-to-release",
       "released"}`` → ``"release"``.
    3. Otherwise → ``"quick"``.

    ``"full"`` is never recommended automatically.  On any error → ``"quick"``.
    """
    try:
        if is_self is True or (is_self is None and is_renmark_repo(repo)):
            return LANE_SELF_UPDATE

        _release_stages = {"reviewed", "ready-to-release", "released"}
        if isinstance(lifecycle_stage, str) and lifecycle_stage in _release_stages:
            return LANE_RELEASE

        return LANE_QUICK
    except Exception:
        return LANE_QUICK


def resolve_lane(recommended: Lane, override: str | None) -> Lane:
    """Resolve a user override against the recommended lane.

    Accepts the forms the finish menu actually offers, so a numbered or
    lettered selection is honored instead of silently collapsing to the
    recommended lane:

    - exact lane name in :data:`LANES` (e.g. ``"self-update"``) → that lane;
    - the menu position ``"1".."4"`` in :data:`LANE_ORDER` order
      (quick / release / self-update / full) → the lane at that position;
    - a unique case-insensitive prefix of a lane name (e.g. ``"self"``,
      ``"rel"``, ``"q"``) → that lane;
    - ``None`` / empty / whitespace / unrecognized → *recommended* unchanged.

    Explicit override wins, including ``"full"``. Never raises.
    """
    try:
        if override is None:
            return recommended
        token = override.strip().lower()
        if not token:
            return recommended
        if token in LANES:
            return token  # type: ignore[return-value]
        if token.isdigit():
            idx = int(token) - 1
            if 0 <= idx < len(LANE_ORDER):
                return LANE_ORDER[idx]
            return recommended
        matches = [name for name in LANE_ORDER if name.startswith(token)]
        if len(matches) == 1:
            return matches[0]
        return recommended
    except Exception:
        return recommended


def lane_table() -> str:
    """Return a compact Markdown table of all lanes and their capabilities.

    Columns: ``Lane | Merges | Releases | Packages | WSL | Verification | Cost``.
    Booleans are rendered as ``✓`` / ``✗``.  Pure, never raises.
    """
    try:
        _yes = "✓"
        _no = "✗"

        header = "| Lane | Merges | Releases | Packages | WSL | Verification | Cost |"
        sep = "|------|--------|----------|----------|-----|--------------|------|"
        rows = [header, sep]
        for lane_name in (LANE_QUICK, LANE_RELEASE, LANE_SELF_UPDATE, LANE_FULL):
            spec = LANES[lane_name]
            rows.append(
                f"| {spec.name} "
                f"| {_yes if spec.merges else _no} "
                f"| {_yes if spec.releases else _no} "
                f"| {_yes if spec.packages else _no} "
                f"| {_yes if spec.updates_wsl else _no} "
                f"| {spec.verification} "
                f"| {spec.cost_level} |"
            )
        return "\n".join(rows)
    except Exception:
        return ""


def describe_lane(name: str) -> str:
    """Return a one-line summary for lane *name*.

    Format: ``"<name>: <action1>, <action2>, ..."``

    Returns a graceful ``"unknown lane: <name>"`` string for an unrecognized
    name.  Never raises.
    """
    try:
        spec = LANES.get(name)  # type: ignore[arg-type]
        if spec is None:
            return f"unknown lane: {name!r}"
        actions = ", ".join(spec.actions)
        return f"{spec.name}: {actions}"
    except Exception:
        return f"unknown lane: {name!r}"

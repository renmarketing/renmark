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

import subprocess
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
    - the menu position ``"1".."4"`` in :func:`ordered_lanes` order, with the
      recommendation at position 1;
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
            return token
        if token.isdigit():
            idx = int(token) - 1
            menu_order = ordered_lanes(recommended)
            if 0 <= idx < len(menu_order):
                return menu_order[idx]
            return recommended
        matches = [name for name in LANE_ORDER if name.startswith(token)]
        if len(matches) == 1:
            return matches[0]
        return recommended
    except Exception:
        return recommended


def ordered_lanes(recommended: Lane) -> tuple[Lane, ...]:
    """Return all lanes once, with *recommended* at index zero."""
    try:
        if recommended not in LANES:
            return LANE_ORDER
        return (recommended, *(lane for lane in LANE_ORDER if lane != recommended))
    except Exception:
        return LANE_ORDER


def lane_table() -> str:
    """Return a compact Markdown table of all lanes and their capabilities.

    Columns: ``Lane | Merges | Releases | Packages | WSL | Worktree | Verification | Cost``.
    Booleans are rendered as ``✓`` / ``✗``.  Pure, never raises.
    """
    try:
        _yes = "✓"
        _no = "✗"

        header = "| Lane | Merges | Releases | Packages | WSL | Worktree | Verification | Cost |"
        sep = "|------|--------|----------|----------|-----|----------|--------------|------|"
        rows = [header, sep]
        for lane_name in (LANE_QUICK, LANE_RELEASE, LANE_SELF_UPDATE, LANE_FULL):
            spec = LANES[lane_name]
            rows.append(
                f"| {spec.name} "
                f"| {_yes if spec.merges else _no} "
                f"| {_yes if spec.releases else _no} "
                f"| {_yes if spec.packages else _no} "
                f"| {_yes if spec.updates_wsl else _no} "
                f"| {_yes if spec.cleans_worktrees else _no} "
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
        spec = LANES.get(name)  # type: ignore[call-overload]
        if spec is None:
            return f"unknown lane: {name!r}"
        actions = ", ".join(spec.actions)
        return f"{spec.name}: {actions}"
    except Exception:
        return f"unknown lane: {name!r}"


# ── Deterministic release-readiness gate (REQ-21 AC3) ────────────────────────
#
# These functions run CODE only — no model calls, no network, no LLM inference.
# They are the deterministic tier that finish lanes call before any release/
# package/install action.  AI reasoning about release readiness is an owner-
# level explanation layer built on TOP of these pass/fail results; it never
# replaces them.


@dataclass(frozen=True)
class GateResult:
    """Result of a single deterministic readiness check.

    ``passed`` is the machine-readable verdict.  ``detail`` is a one-line
    human-readable explanation — always populated, even on pass (for tracing).
    """

    name: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class ReadinessReport:
    """Aggregated output of :func:`release_readiness`.

    ``ready`` is ``True`` only when every required gate passes.
    ``gates`` is the full ordered list of :class:`GateResult` objects so
    callers can surface per-check details without re-running checks.
    """

    ready: bool
    gates: tuple[GateResult, ...]


# Gates that are reported but do NOT gate the overall ``ready`` decision.
_INFORMATIONAL_GATES = frozenset({"tests_present", "artifact_budget", "stray_branches"})


def _gate_version_consistent(repo: Path) -> GateResult:
    """Check that all version files agree (no drift).

    Reuses ``renmark.release.drift_report`` — pure read of version files,
    no subprocess, no network.  Passes when the drift list is empty.
    """
    try:
        from renmark.release import drift_report

        issues = drift_report(repo)
        if not issues:
            return GateResult("version_consistent", True, "all version files agree")
        detail = "; ".join(issues[:3])
        if len(issues) > 3:
            detail += f" (+ {len(issues) - 3} more)"
        return GateResult("version_consistent", False, detail)
    except Exception as exc:
        return GateResult("version_consistent", False, f"check error: {exc}")


def _gate_tree_clean(repo: Path) -> GateResult:
    """Check that the working tree has no uncommitted changes.

    Preferred path: delegate to ``renmark.worktree.is_clean_tree(repo)`` —
    that module is being built in parallel.  If it is not yet available the
    import is caught and a minimal ``git status --porcelain`` call is made
    directly (same semantics, no external dependency beyond git).
    """
    # Preferred: use the worktree module when available.
    try:
        from renmark import worktree

        clean = worktree.is_clean_tree(repo)
        if clean:
            return GateResult("tree_clean", True, "working tree is clean")
        return GateResult("tree_clean", False, "working tree has uncommitted changes")
    except ImportError:
        pass  # module not yet present — fall through to inline git call
    except Exception as exc:
        return GateResult("tree_clean", False, f"worktree check error: {exc}")

    # Fallback: inline git status --porcelain.
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo), "status", "--porcelain"],
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            return GateResult("tree_clean", False, "git status failed (not a repo?)")
        if proc.stdout.strip():
            return GateResult("tree_clean", False, "working tree has uncommitted changes")
        return GateResult("tree_clean", True, "working tree is clean")
    except Exception as exc:
        return GateResult("tree_clean", False, f"git check error: {exc}")


def _gate_package_buildable(repo: Path) -> GateResult:
    """Check that the package name is derivable (manifest readable or dir name usable).

    Reuses ``renmark.release.package_basename`` — pure read, no subprocess.
    """
    try:
        from renmark.release import package_basename

        name = package_basename(repo)
        if name:
            return GateResult("package_buildable", True, f"package name: {name!r}")
        return GateResult("package_buildable", False, "package name is empty")
    except Exception as exc:
        return GateResult("package_buildable", False, f"check error: {exc}")


def _gate_tests_present(repo: Path) -> GateResult:
    """Optional check: verify that a tests/ directory exists."""
    try:
        tests_dir = repo / "tests"
        if tests_dir.is_dir():
            return GateResult("tests_present", True, f"tests/ directory found at {tests_dir}")
        return GateResult("tests_present", False, "tests/ directory not found")
    except Exception as exc:
        return GateResult("tests_present", False, f"check error: {exc}")


def _gate_artifact_budget(repo: Path) -> GateResult:
    """Optional check: run ``hygiene.validate_registry_compliance`` and
    summarize WARN/BLOCK counts. Never blocks ``ready`` — informational only.
    """
    try:
        from renmark import hygiene

        issues = hygiene.validate_registry_compliance(repo)
        block_count = sum(1 for issue in issues if issue.startswith("BLOCK"))
        warn_count = len(issues) - block_count
        passed = block_count == 0
        detail = "ok — 0 issues" if not issues else f"{warn_count} WARN, {block_count} BLOCK"
        return GateResult("artifact_budget", passed, detail)
    except Exception as exc:
        return GateResult("artifact_budget", False, f"check error: {exc}")


def _gate_stray_branches(repo: Path) -> GateResult:
    """Optional check: surface merged-but-undeleted local branches and stale
    worktrees at release time. Never blocks ``ready`` — informational only,
    same shape as ``artifact_budget``. Deleting them is a destructive git
    operation an Owner/agent must do explicitly (SKILL.md's branch/worktree
    cleanup steps); this gate exists so that step being skipped is VISIBLE at
    release time instead of silently accumulating across releases.
    """
    try:
        from renmark import worktree

        branches = worktree.stale_local_branches(repo)
        worktrees = worktree.stale_worktrees(repo)
        passed = not branches and not worktrees
        if passed:
            detail = "ok — no stray branches or worktrees"
        else:
            parts = []
            if branches:
                parts.append(f"{len(branches)} merged branch(es) not deleted: {', '.join(branches)}")
            if worktrees:
                names = [str(wt.get("path", "?")) for wt in worktrees]
                parts.append(f"{len(worktrees)} stale worktree(s): {', '.join(names)}")
            detail = "; ".join(parts)
        return GateResult("stray_branches", passed, detail)
    except Exception as exc:
        return GateResult("stray_branches", False, f"check error: {exc}")


def release_readiness(repo: str | Path = ".") -> ReadinessReport:
    """Aggregate deterministic release-readiness checks for *repo*.

    **Deterministic gate — runs code only, never a model (REQ-21 AC3).**
    Every check is a pure read of the filesystem or a bounded subprocess call
    (``git status``).  No network, no LLM, no side effects.

    Checks performed (in order):

    1. ``version_consistent`` — all version files agree; reuses
       ``renmark.release.drift_report``.
    2. ``tree_clean`` — working tree has no uncommitted changes; delegates to
       ``renmark.worktree.is_clean_tree`` when available, falls back to an
       inline ``git status --porcelain`` call.
    3. ``package_buildable`` — package name is derivable from the plugin
       manifest (or the repo dir name); reuses
       ``renmark.release.package_basename``.
    4. ``tests_present`` — optional structural check that ``tests/`` exists.
    5. ``artifact_budget`` — optional check of ``.renmark/`` artifact registry
       compliance; reuses ``renmark.hygiene.validate_registry_compliance``.
    6. ``stray_branches`` — optional check for merged-but-undeleted local
       branches and stale worktrees left over from a prior feature/release
       cycle; reuses ``renmark.worktree.stale_local_branches`` and
       ``renmark.worktree.stale_worktrees``.

    Returns a :class:`ReadinessReport` whose ``ready`` flag is ``True`` only
    when all **required** gates pass.  ``tests_present``, ``artifact_budget``,
    and ``stray_branches`` are *informational* gates — reported but do NOT
    gate ``ready`` (deleting a branch/worktree is a destructive git operation
    that must stay an explicit human/agent action, not an automatic release
    blocker). Never raises — any uncaught error degrades to a not-ready
    report rather than propagating.

    AI reasoning about *why* a release might not be ready is an owner-level
    explanation layer built on top of these results; it never replaces them.
    """
    try:
        root = Path(repo)
        gates: list[GateResult] = [
            _gate_version_consistent(root),
            _gate_tree_clean(root),
            _gate_package_buildable(root),
            _gate_tests_present(root),
            _gate_artifact_budget(root),
            _gate_stray_branches(root),
        ]
    except Exception as exc:  # honor the "never raises" contract
        return ReadinessReport(
            ready=False,
            gates=(GateResult("release_readiness", False, f"gate setup error: {exc}"),),
        )
    # tests_present is informational only — exclude it from the ready decision.
    ready = all(g.passed for g in gates if g.name not in _INFORMATIONAL_GATES)
    return ReadinessReport(ready=ready, gates=tuple(gates))

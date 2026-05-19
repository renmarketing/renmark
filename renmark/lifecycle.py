"""Lifecycle state for renmark features — enforces G12 (lifecycle persistence)
and the seven-stage workflow: Brainstorm → Plan → Create → Test → Review →
Document → Release.

Lifecycle state lives in ``.renmark/state/lifecycle.json``. It is the source
of truth for cold-start recovery: any session can read this file after
``/clear`` and know exactly where the in-flight feature is.

Strict separation from ``pipeline.json``:
- lifecycle.json carries WORKFLOW state (feature, stage, artifacts, approval).
- pipeline.json carries RUNTIME state (wave indices, retry counts, subprocess).

If lifecycle.json exceeds ~1KB it's a bug — runtime cruft has leaked in.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

# ── Stage taxonomy ────────────────────────────────────────────────────────────

# Canonical stages in order. Skills update lifecycle.json with one of these.
STAGES: list[str] = [
    "init",                 # lifecycle created, no work yet
    "brainstorm-complete",  # spec written
    "plan-drafted",         # plan written, not yet validated
    "plan-validated",       # check-plan PASS
    "created",              # orchestrate complete
    "verified",             # verify PASS
    "reviewed",             # codereview + (optional) secure complete
    "documented",           # document complete
    "ready-to-release",     # finish flipped the marker
    "released",             # release tagged + zip built
    "restored",             # a /renmark:restore happened
]

# Stage transitions — the router uses this to compute next_recommended.
NEXT_BY_STAGE: dict[str, str] = {
    "init":                  "/renmark:brainstorm",
    "brainstorm-complete":   "/renmark:plan",
    "plan-drafted":          "/renmark:check-plan",
    "plan-validated":        "/renmark:orchestrate",
    "created":               "/renmark:verify",
    "verified":              "/renmark:codereview",
    "reviewed":              "/renmark:document",
    "documented":            "/renmark:finish",
    "ready-to-release":      "/renmark:release",
    "released":              "(feature complete — start a new one with /renmark:start)",
    "restored":              "(working tree restored — start a new feature or continue manually)",
}

# Domain classification for context-contamination detection (G4).
DOMAIN_BY_SKILL: dict[str, str] = {
    "debug":       "debug",
    "codereview":  "debug",
    "start":       "build",
    "brainstorm":  "build",
    "plan":        "build",
    "check-plan":  "build",
    "orchestrate": "build",
    "verify":      "build",
    "finish":      "build",
    "feature":     "build",
    "secure":      "audit",
    "document":    "audit",
    "map":         "audit",
    "research":    "audit",
    "setup":       "meta",
    "roadmap":     "meta",
    "help":        "meta",
    "resume":      "meta",
    "release":     "meta",
    "restore":     "meta",
    "approve":     "meta",
    "issue":       "meta",
}

# ── Size guard ────────────────────────────────────────────────────────────────

LIFECYCLE_JSON_BYTE_BUDGET = 1024  # 1KB — exceeding this is a bug (G12 audit)


class LifecycleBloatError(RuntimeError):
    """Raised when lifecycle.json grows past its budget — runtime cruft has leaked."""


# ── Data ──────────────────────────────────────────────────────────────────────


@dataclass
class LifecycleState:
    """Workflow state for one in-flight feature. Persisted to disk as JSON."""

    feature: str = ""
    branch: str = ""
    github_issue: int | None = None
    stage: str = "init"
    stages_completed: list[str] = field(default_factory=list)
    artifacts: dict[str, str] = field(default_factory=dict)
    # Human approval gate (G7 / principle #7)
    human_review_required: bool = False
    human_review_completed: bool = False
    human_review_for: str | None = None
    next_recommended: str = ""
    last_updated: str = ""

    def __post_init__(self) -> None:
        if not self.last_updated:
            self.last_updated = _now()
        if not self.next_recommended:
            self.next_recommended = NEXT_BY_STAGE.get(self.stage, "")

    def to_json(self) -> str:
        # Round-trip through dict to guarantee JSON-safe values.
        return json.dumps(asdict(self), indent=2, sort_keys=False)


# ── Paths ────────────────────────────────────────────────────────────────────


def _state_dir(repo: Path | str) -> Path:
    return Path(repo) / ".renmark" / "state"


def _lifecycle_path(repo: Path | str) -> Path:
    return _state_dir(repo) / "lifecycle.json"


# ── Public API ────────────────────────────────────────────────────────────────


def read_lifecycle(repo: Path | str) -> LifecycleState | None:
    """Return the current LifecycleState, or None if no lifecycle exists."""
    path = _lifecycle_path(repo)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    # Tolerate unknown fields — drop them rather than crashing on schema drift.
    known = {f for f in LifecycleState.__dataclass_fields__}
    filtered = {k: v for k, v in data.items() if k in known}
    return LifecycleState(**filtered)


def write_lifecycle(
    repo: Path | str,
    *,
    stage: str | None = None,
    feature: str | None = None,
    branch: str | None = None,
    github_issue: int | None = None,
    artifact_update: tuple[str, str] | None = None,
    human_review_required: bool | None = None,
    human_review_completed: bool | None = None,
    human_review_for: str | None = None,
) -> LifecycleState:
    """Update lifecycle.json with the provided fields. Reads-modifies-writes
    so existing fields not overridden are preserved. Returns the new state.

    Raises LifecycleBloatError if the resulting file exceeds the budget.
    """
    current = read_lifecycle(repo) or LifecycleState()

    if stage is not None:
        if stage not in STAGES:
            raise ValueError(f"unknown stage {stage!r}; must be one of {STAGES}")
        if current.stage != stage and current.stage not in current.stages_completed:
            # Promote previous stage into stages_completed (idempotent).
            if current.stage != "init" and current.stage not in current.stages_completed:
                current.stages_completed.append(current.stage)
        current.stage = stage
        current.next_recommended = NEXT_BY_STAGE.get(stage, "")

    if feature is not None:
        current.feature = feature
    if branch is not None:
        current.branch = branch
    if github_issue is not None:
        current.github_issue = github_issue
    if artifact_update is not None:
        key, value = artifact_update
        current.artifacts[key] = value
    if human_review_required is not None:
        current.human_review_required = human_review_required
    if human_review_completed is not None:
        current.human_review_completed = human_review_completed
    if human_review_for is not None:
        current.human_review_for = human_review_for

    current.last_updated = _now()

    path = _lifecycle_path(repo)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = current.to_json()

    if len(payload.encode("utf-8")) > LIFECYCLE_JSON_BYTE_BUDGET:
        raise LifecycleBloatError(
            f"lifecycle.json would be {len(payload)} bytes; budget {LIFECYCLE_JSON_BYTE_BUDGET}. "
            "Runtime cruft has leaked in — move it to pipeline.json."
        )

    path.write_text(payload, encoding="utf-8")
    return current


def clear_lifecycle(repo: Path | str) -> None:
    """Delete lifecycle.json. Called when a feature finishes (released) or
    when the user wants a clean slate."""
    path = _lifecycle_path(repo)
    if path.exists():
        path.unlink()


def next_recommended(repo: Path | str) -> str:
    """Return the recommended next command for the current lifecycle, or a
    cold-start prompt if no lifecycle exists. Zero LLM calls."""
    state = read_lifecycle(repo)
    if state is None:
        return "/renmark:start (no feature in flight)"

    if state.human_review_required and not state.human_review_completed:
        target = state.human_review_for or "pending action"
        return f"/renmark:approve (awaiting human approval for: {target})"

    return state.next_recommended or NEXT_BY_STAGE.get(state.stage, "(unknown stage)")


def domain_of(skill: str) -> str:
    """Return the domain bucket for a skill name (G4 contamination detection)."""
    return DOMAIN_BY_SKILL.get(skill, "build")


def is_cross_domain_transition(prev_skill: str | None, new_skill: str) -> bool:
    """G4: True if moving from prev_skill to new_skill crosses domain boundaries.
    First invocation (prev_skill=None) is never cross-domain.
    """
    if prev_skill is None:
        return False
    return domain_of(prev_skill) != domain_of(new_skill)


# ── Internal ──────────────────────────────────────────────────────────────────


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

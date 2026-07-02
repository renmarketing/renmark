"""Behavioral tests for Agency Mode — proves CHANGES renmark behavior (AC11).

Tests pin the observable contracts:
- AC2: inactive agency leaves preamble byte-identical (no-op)
- Agency-aware vs non-aware routing (_AGENCY_AWARE_SKILLS)
- AC4/REQ-20: active preamble carries fragment POINTER not inlined body
- Fragment registration and on-demand loadability
- Mode selection stays independent of agency state
"""

from __future__ import annotations

from pathlib import Path

from renmark import agency, context, lifecycle, mode

# ── Repo root (the live project, not a tmp dir) ────────────────────────────────
# Used to resolve plugin_root for load_fragment — body check in T4 requires
# the real fragment, not a tmp synthetic copy.

_REPO_ROOT = Path(__file__).resolve().parent.parent
_PLUGIN_ROOT = _REPO_ROOT / "plugin"


# ── Helpers ───────────────────────────────────────────────────────────────────


def _init_state_dir(repo: Path) -> None:
    """Create .renmark/state/ so agency writes don't fail on missing parent."""
    (repo / ".renmark" / "state").mkdir(parents=True, exist_ok=True)


# ── 1. Inactive preamble has no agency hint ────────────────────────────────────


def test_inactive_preamble_has_no_agency_hint(tmp_path: Path) -> None:
    """With agency inactive (fresh tmp repo), skill_preamble('start') must NOT
    contain lifecycle._AGENCY_HINT_MARKER (AC2 — byte-identical when off)."""
    _init_state_dir(tmp_path)
    # Ensure agency is inactive (fresh repo — no agency.json → default inactive).
    assert not agency.is_active(tmp_path)

    result = lifecycle.skill_preamble(tmp_path, "start")
    # None is acceptable (no hints at all); a string must not carry the marker.
    if result is not None:
        assert lifecycle._AGENCY_HINT_MARKER not in result, (
            f"skill_preamble returned the agency hint for an inactive repo: {result!r}"
        )


def test_inactive_agency_note_is_byte_identical_passthrough(tmp_path: Path) -> None:
    """Invariant #1 at the unit level: when agency is inactive, _with_agency_note
    returns its input UNCHANGED (identity) — byte-identical, not merely
    marker-free. Proven for every spine skill against a sentinel that shares no
    text with the agency hint, so any appended/reordered content would fail."""
    _init_state_dir(tmp_path)
    assert not agency.is_active(tmp_path)
    sentinel = "SENTINEL-preamble-xyz"
    for skill in sorted(lifecycle._AGENCY_SPINE_SKILLS):
        assert lifecycle._with_agency_note(tmp_path, skill, sentinel) == sentinel
        # None must stay None too (no hint fabricated when there was none).
        assert lifecycle._with_agency_note(tmp_path, skill, None) is None


def test_agency_note_noop_for_nonaware_even_when_active(tmp_path: Path) -> None:
    """Skills NOT in the agency-aware set pass through unchanged even when active.

    (debug/audit are non-pipeline skills — they never get an agency hint.)"""
    _init_state_dir(tmp_path)
    agency.activate(tmp_path, current_phase="alpha", current_milestone="M1")
    sentinel = "SENTINEL-preamble-xyz"
    assert "debug" not in lifecycle._AGENCY_AWARE_SKILLS
    assert lifecycle._with_agency_note(tmp_path, "debug", sentinel) == sentinel
    assert lifecycle._with_agency_note(tmp_path, "audit", None) is None


def test_all_pipeline_skills_gain_hint_when_active(tmp_path: Path) -> None:
    """Fast-follow: EVERY agency-aware pipeline skill — the full set (spine
    start/prd/roadmap/finish/resume PLUS feature/plan/orchestrate/verify/
    codereview) — surfaces the agency hint + fragment pointer when active.
    Iterates the live set so it can never silently under-cover."""
    _init_state_dir(tmp_path)
    agency.activate(tmp_path, current_phase="alpha", current_milestone="M1")
    pointer = context.fragment_pointer("agency-delivery")
    covered = sorted(lifecycle._AGENCY_AWARE_SKILLS)
    assert len(covered) == 10, f"expected 10 agency-aware skills, got {covered}"
    for skill in covered:
        note = lifecycle._with_agency_note(tmp_path, skill, None)
        assert note is not None and lifecycle._AGENCY_HINT_MARKER in note, (
            f"{skill} did not gain the agency hint when active: {note!r}"
        )
        assert pointer in note, f"{skill} note missing fragment pointer: {note!r}"


# ── 2. Active spine preamble gains the hint ────────────────────────────────────


def test_active_spine_preamble_gains_hint(tmp_path: Path) -> None:
    """After activate(repo, current_phase='alpha', current_milestone='M1'),
    skill_preamble(repo, 'start') must contain the marker AND the fragment pointer."""
    _init_state_dir(tmp_path)
    agency.activate(tmp_path, current_phase="alpha", current_milestone="M1")

    result = lifecycle.skill_preamble(tmp_path, "start")
    assert result is not None, (
        "skill_preamble returned None for an active-agency spine skill; "
        "expected a hint string containing the agency marker."
    )
    assert lifecycle._AGENCY_HINT_MARKER in result, (
        f"Agency marker not found in active preamble for 'start': {result!r}"
    )
    pointer = context.fragment_pointer("agency-delivery")
    assert pointer in result, (
        f"Fragment pointer {pointer!r} not found in active preamble: {result!r}"
    )


# ── 3. Active non-spine preamble stays clean ──────────────────────────────────


def test_active_nonaware_preamble_stays_clean(tmp_path: Path) -> None:
    """With agency active, a NON-agency-aware skill ('debug') preamble must NOT
    contain the agency hint marker."""
    _init_state_dir(tmp_path)
    agency.activate(tmp_path, current_phase="beta", current_milestone="M2")

    # 'debug' is NOT in the agency-aware pipeline set
    assert "debug" not in lifecycle._AGENCY_AWARE_SKILLS

    result = lifecycle.skill_preamble(tmp_path, "debug")
    if result is not None:
        assert lifecycle._AGENCY_HINT_MARKER not in result, (
            f"Agency hint leaked into non-aware skill 'debug': {result!r}"
        )


# ── 4. Active preamble carries POINTER not inlined body (AC4 / REQ-20) ────────


def test_preamble_carries_pointer_not_body(tmp_path: Path) -> None:
    """Active preamble must contain the fragment pointer but NOT inline the
    fragment body (dynamic-loading guarantee: AC4 / REQ-20).

    Loads the real agency-delivery.md body from the live plugin dir to pick a
    distinctive substring, then asserts that substring is absent from the
    preamble string.
    """
    _init_state_dir(tmp_path)
    agency.activate(tmp_path, current_phase="alpha", current_milestone="M1")

    result = lifecycle.skill_preamble(tmp_path, "start")
    assert result is not None, (
        "skill_preamble returned None for an active-agency spine skill."
    )

    # The pointer must be present.
    pointer = context.fragment_pointer("agency-delivery")
    assert pointer in result, (
        f"Fragment pointer not found in preamble: {result!r}"
    )

    # Load the real body to find a distinctive phrase that should NOT be inlined.
    body = context.load_fragment(_PLUGIN_ROOT, "agency-delivery")
    # "milestone checkpoint" is a distinctive multi-word phrase in the fragment body
    # that would only appear if the body were inlined.
    distinctive = "milestone checkpoint"
    assert distinctive in body, (
        f"Sanity: expected {distinctive!r} in agency-delivery body — check fragment."
    )
    assert distinctive not in result, (
        f"Fragment body appears to be inlined in the preamble (found {distinctive!r}). "
        "Dynamic loading violated — preamble must carry the pointer only."
    )


# ── 5. Fragment registered and loadable ────────────────────────────────────────


def test_fragment_registered_and_loadable() -> None:
    """'agency-delivery' must be in context.fragment_names() AND load_fragment
    must return a non-empty string that contains 'milestone'."""
    names = context.fragment_names()
    assert "agency-delivery" in names, (
        f"'agency-delivery' not in fragment_names(): {names}"
    )

    body = context.load_fragment(_PLUGIN_ROOT, "agency-delivery")
    assert body, "load_fragment('agency-delivery') returned empty string"
    assert "milestone" in body, (
        "Expected 'milestone' in agency-delivery body — check the fragment."
    )


# ── 6. Mode selection is independent of agency active/inactive (AC2) ──────────


def test_mode_selection_independent_of_agency(tmp_path: Path) -> None:
    """Setting mode via renmark.mode must be unaffected by agency state, and
    toggling agency must not alter mode state."""
    _init_state_dir(tmp_path)

    # Start: both inactive/unset.
    assert mode.read_mode(tmp_path) is None
    assert not agency.is_active(tmp_path)

    # Set conductor mode, activate agency — mode must still be conductor.
    mode.set_mode(tmp_path, "conductor")
    agency.activate(tmp_path, current_phase="gamma", current_milestone="M3")
    assert mode.read_mode(tmp_path) == "conductor"
    assert agency.is_active(tmp_path)

    # Deactivate agency — mode must still be conductor.
    agency.deactivate(tmp_path)
    assert mode.read_mode(tmp_path) == "conductor"
    assert not agency.is_active(tmp_path)

    # Clear mode — agency state must be unaffected.
    mode.clear_mode(tmp_path)
    assert mode.read_mode(tmp_path) is None
    assert not agency.is_active(tmp_path)

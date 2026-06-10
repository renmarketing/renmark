"""Live shadow regression gate — runs the real tree's shadow cases against
shipped baselines and asserts no drift, missing baseline, or replay error.

This gates G3 / G11 / G12 anchors (dispatch, lifecycle, summary subsystems)
by running `shadow.run_all()` against the checked-in tests/shadow/ cases and
baselines.

All subsystems are hard gates — baselines were re-accepted after the v0.9.0
cleanup wave landed (dispatch error-format + lifecycle stage edits).
"""
from __future__ import annotations

from renmark import shadow


def _collect_failures(diffs: list[shadow.ShadowDiff]) -> list[tuple[str, str, str, str | None]]:
    """Return (subsystem, case, result, error) for any non-match."""
    return [
        (d.subsystem, d.case, d.result, d.error)
        for d in diffs
        if d.result != "match"
    ]


def test_shadow_live_dispatch() -> None:
    """Dispatch subsystem baselines must match current code (gates G11)."""
    diffs = shadow.run_subsystem("dispatch")
    failures = _collect_failures(diffs)
    assert not failures, f"dispatch shadow drift: {failures}"


def test_shadow_live_lifecycle() -> None:
    """Lifecycle subsystem baselines must match current code (gates G12)."""
    diffs = shadow.run_subsystem("lifecycle")
    failures = _collect_failures(diffs)
    assert not failures, f"lifecycle shadow drift: {failures}"


def test_shadow_live_summary() -> None:
    """Summary subsystem baselines must match current code (gates G3)."""
    diffs = shadow.run_subsystem("summary")
    failures = _collect_failures(diffs)
    assert not failures, f"summary shadow drift: {failures}"


def test_shadow_live_all_registered_subsystems_have_cases() -> None:
    """Every registered subsystem must have at least one case file."""
    for sub in shadow.registered_subsystems():
        cases = shadow.list_cases(sub)
        assert cases, f"subsystem {sub!r} has no case files — add at least one"


def test_shadow_live_no_missing_baselines() -> None:
    """No shipped case should be missing a baseline (run accept if you added a case)."""
    all_diffs = shadow.run_all()
    missing = [
        (sub, d.case)
        for sub, dlist in all_diffs.items()
        for d in dlist
        if d.result == "missing-baseline"
    ]
    assert not missing, (
        f"cases without a baseline (run python -m renmark.shadow accept --subsystem <sub> -m 'reason'): {missing}"
    )

"""Tests for the R-008 dispatch-reason/budget checklist added to
``renmark.subagent_gate`` per
``.renmark/plans/r-0.2/dispatch-reason-budget-design.md`` (R-0.2/WP-5).

Proves:
- (a) existing pre-R-0.2 justification-gate behavior (``justify_task``) is
  unchanged, and the new checklist is lenient by default (never raises, never
  blocks a dispatch missing fields unless ``strict=True`` is passed);
- (b) a fully-specified dispatch passes strict mode;
- (c) a dispatch missing any one required field is rejected in strict mode
  with a clear error naming which field is missing.
"""

from __future__ import annotations

import pytest

from renmark import subagent_gate as g


def _full_dispatch(**overrides: object) -> dict:
    spec: dict = {
        "work_order_id": "WO-12345",
        "contract": ".renmark/plans/2026-08-01-r-0.2-controlled-worker-execution-contract.md",
        "reason": "implement task 3",
        "scope": {"target_files": ["renmark/foo.py"], "prohibited_files": []},
        "expected_artifact": ".renmark/reviews/WO-12345-result.md",
        "budget_reservation": {"max_input_tokens": 60000, "max_output_tokens": 10000, "max_attempts": 2},
    }
    spec.update(overrides)
    return spec


# ── (a) existing behavior is unchanged ───────────────────────────────────────


def test_justify_task_medium_complexity_verdict_shape_unchanged() -> None:
    """Pins the pre-R-0.2 SubagentVerdict shape (mirrors the R-0.2 regression
    baseline) — the R-008 checklist must not mutate justify_task's output."""
    task = {
        "index": 1,
        "target": "src/a.py",
        "executor": "sonnet",
        "complexity": "medium",
    }
    verdict = g.justify_task(task)

    assert verdict.needs_subagent is True
    assert verdict.role == "code-implementer"
    assert verdict.tier == "sonnet"
    assert verdict.challenge is None
    assert verdict.challenge_code == ""
    assert not hasattr(verdict, "budget")
    assert not hasattr(verdict, "declared_scope")


def test_general_purpose_without_reason_still_challenged() -> None:
    task = {
        "executor": "sonnet",
        "complexity": "medium",
        "est_tokens": 1000,
        "target": "notes.txt",
    }
    verdict = g.justify_task(task)
    assert verdict.role == "general-purpose"
    assert verdict.challenge is not None
    assert "general-purpose" in verdict.challenge


# ── lenient (default) mode ───────────────────────────────────────────────────


def test_enforce_r008_lenient_default_never_raises_on_empty_spec() -> None:
    missing = g.enforce_r008_dispatch({})
    assert set(missing) == {
        "work_order_id",
        "contract",
        "reason",
        "scope",
        "expected_artifact",
        "budget_reservation",
    }


def test_enforce_r008_lenient_default_never_raises_on_legacy_task_dict() -> None:
    """A pre-R-0.2 task/dispatch dict (no R-008 fields at all) must not be
    rejected in default (lenient) mode — this is the backward-compat
    guarantee the design doc's migration plan requires."""
    legacy_task = {
        "index": 1,
        "target": "src/a.py",
        "executor": "sonnet",
        "complexity": "medium",
    }
    missing = g.enforce_r008_dispatch(legacy_task)
    assert "work_order_id" in missing
    # No exception raised — the call above completing is the proof.


def test_validate_r008_dispatch_pure_never_raises_on_bad_input() -> None:
    valid, missing = g.validate_r008_dispatch(None)
    assert valid is False
    assert len(missing) == 6


# ── (b) fully-specified dispatch passes strict mode ──────────────────────────


def test_enforce_r008_strict_passes_fully_specified_dispatch() -> None:
    spec = _full_dispatch()
    missing = g.enforce_r008_dispatch(spec, strict=True)
    assert missing == []

    valid, missing2 = g.validate_r008_dispatch(spec)
    assert valid is True
    assert missing2 == []


# ── (c) strict mode rejects a dispatch missing any one required field ───────


@pytest.mark.parametrize(
    "field_name",
    [
        "work_order_id",
        "contract",
        "reason",
        "scope",
        "expected_artifact",
        "budget_reservation",
    ],
)
def test_enforce_r008_strict_rejects_dispatch_missing_one_field(field_name: str) -> None:
    spec = _full_dispatch(**{field_name: None})

    with pytest.raises(g.R008DispatchRejected) as excinfo:
        g.enforce_r008_dispatch(spec, strict=True)

    assert field_name in excinfo.value.missing
    assert field_name in str(excinfo.value)


def test_enforce_r008_strict_rejects_and_names_all_missing_fields() -> None:
    spec = _full_dispatch(reason=None, budget_reservation=None)

    with pytest.raises(g.R008DispatchRejected) as excinfo:
        g.enforce_r008_dispatch(spec, strict=True)

    assert set(excinfo.value.missing) == {"reason", "budget_reservation"}
    assert "reason" in str(excinfo.value)
    assert "budget_reservation" in str(excinfo.value)


def test_r008_checklist_dataclass_all_present_and_missing_fields() -> None:
    spec = _full_dispatch()
    checklist = g._r008_checklist_from_spec(spec)
    assert checklist.all_present is True
    assert checklist.missing_fields() == []

    incomplete = g._r008_checklist_from_spec(_full_dispatch(scope=None))
    assert incomplete.all_present is False
    assert incomplete.missing_fields() == ["scope"]

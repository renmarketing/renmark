"""
---
artifact_type: pytest_test_artifact
schema_version: 1
created_at: 2026-08-05T00:00:00-04:00
source_sha: 213ce5d3d6aad04c2c8dfb3e2915fccd73b457b1
related_plan: Release 13 Task 5
generator: codex
stale_after: null
dependency_refs:
  - renmark.analytics
  - renmark.ledger
---

Pytest coverage for the additive ledger guardrail aggregation path.

The tests below verify the never-raise contract, the zero-state fallback, the
real-event reconciliation path, and the additive-only guarantee that the
existing analytics summary keys keep the same shape.

## Summary
- Covers empty-repo guardrails and preserves `features`/`tasks`/`loops` shape.
- Exercises real ledger writes for escalation and inspection reconciliation.
- Verifies malformed JSONL input degrades to zero guardrails without raising.
"""

from pathlib import Path

from renmark import analytics, ledger


NOW = "2026-08-05T00:00:00Z"


def _assert_core_summary_shape(summary: dict[str, object], baseline: dict[str, object]) -> None:
    for key in ("features", "tasks", "loops"):
        assert key in summary
        assert key in baseline
        assert isinstance(summary[key], dict)
        assert isinstance(baseline[key], dict)
        assert summary[key].keys() == baseline[key].keys()


def _assert_zero_guardrails(summary: dict[str, object]) -> None:
    assert summary["guardrails"] == {
        "escalations_total": 0,
        "escalations_blocking": 0,
        "inspection_verdicts": {},
        "inspection_total": 0,
    }


def _ledger_path(repo: Path) -> Path:
    return repo / ".renmark" / "ledger" / "events.jsonl"


def test_aggregate_without_ledger_file_includes_zero_guardrails(tmp_path: Path) -> None:
    baseline = analytics.aggregate(tmp_path, now=NOW)
    summary = analytics.aggregate(tmp_path, now=NOW)

    _assert_zero_guardrails(summary)
    _assert_core_summary_shape(summary, baseline)


def test_aggregate_reconciles_escalations_and_inspection_verdicts(tmp_path: Path) -> None:
    baseline = analytics.aggregate(tmp_path, now=NOW)

    ledger.append_ledger_event(
        tmp_path,
        ledger.Escalation(
            reason="first blocking escalation",
            originating_skill="renmark:debug",
            blocking=True,
            is_replannable=False,
        ),
        ts="2026-08-05T00:00:01Z",
    )
    ledger.append_ledger_event(
        tmp_path,
        ledger.Escalation(
            reason="non-blocking escalation",
            originating_skill="renmark:feature",
            blocking=False,
            is_replannable=True,
        ),
        ts="2026-08-05T00:00:02Z",
    )
    ledger.append_ledger_event(
        tmp_path,
        ledger.Escalation(
            reason="second blocking escalation",
            originating_skill="renmark:finish",
            blocking=True,
            is_replannable=False,
        ),
        ts="2026-08-05T00:00:03Z",
    )
    ledger.append_ledger_event(
        tmp_path,
        ledger.InspectionReport(
            subject_ref="build-1",
            verdict="pass",
            findings=[],
            generator="unit-test",
            dispatch_identity="dispatch-1",
        ),
        ts="2026-08-05T00:00:04Z",
    )
    ledger.append_ledger_event(
        tmp_path,
        ledger.InspectionReport(
            subject_ref="build-2",
            verdict="fail",
            findings=["missing guardrail"],
            generator="unit-test",
            dispatch_identity="dispatch-2",
        ),
        ts="2026-08-05T00:00:05Z",
    )
    ledger.append_ledger_event(
        tmp_path,
        ledger.InspectionReport(
            subject_ref="build-3",
            verdict="escalate",
            findings=["needs escalation"],
            generator="unit-test",
            dispatch_identity="dispatch-3",
        ),
        ts="2026-08-05T00:00:06Z",
    )

    summary = analytics.aggregate(tmp_path, now=NOW)
    guardrails = summary["guardrails"]

    assert guardrails == {
        "escalations_total": 3,
        "escalations_blocking": 2,
        "inspection_verdicts": {"pass": 1, "fail": 1, "escalate": 1},
        "inspection_total": 3,
    }
    _assert_core_summary_shape(summary, baseline)


def test_aggregate_with_malformed_ledger_degrades_to_zero_guardrails(tmp_path: Path) -> None:
    baseline = analytics.aggregate(tmp_path, now=NOW)

    ledger_file = _ledger_path(tmp_path)
    ledger_file.parent.mkdir(parents=True, exist_ok=True)
    ledger_file.write_text("not-json\n{]\n", encoding="utf-8")

    summary = analytics.aggregate(tmp_path, now=NOW)

    _assert_zero_guardrails(summary)
    _assert_core_summary_shape(summary, baseline)

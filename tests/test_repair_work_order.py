"""Tests for R-0.2/WP-5e: Inspector finding -> repair work order (ADR-046).

Covers .renmark/plans/r-0.2/inspector-repair-separation-design.md §4 and the
open-question-#1 schema decision recorded in renmark/dispatch.py.
"""

from renmark import dispatch, fast_path


def test_fail_finding_produces_repair_work_order_referencing_source() -> None:
    finding = dispatch.InspectorFinding(
        finding_id="F-001",
        source_file=".renmark/reviews/2026-08-01-example.review.md",
        verdict="FAIL",
        severity="minor",
        target="renmark/example.py",
        title="broken invariant",
    )
    order = dispatch.build_repair_work_order(finding, work_order_id="WO-1")

    assert order is not None
    assert isinstance(order, dispatch.RepairWorkOrder)
    assert order.order_id == "WO-1"
    # Pointer back to the source finding: file + id, not full content.
    assert order.source_inspection_id == ".renmark/reviews/2026-08-01-example.review.md#F-001"
    assert order.severity in ("major", "critical")
    assert order.acceptance_criteria


def test_major_severity_pass_verdict_still_produces_work_order() -> None:
    finding = dispatch.InspectorFinding(
        finding_id="F-002",
        source_file=".renmark/reviews/2026-08-01-example.review.md",
        verdict="PASS",
        severity="major",
        target="renmark/other.py",
    )
    order = dispatch.build_repair_work_order(finding, work_order_id="WO-2")

    assert order is not None
    assert order.severity == "major"


def test_critical_severity_preserved() -> None:
    finding = dispatch.InspectorFinding(
        finding_id="F-003",
        source_file=".renmark/reviews/2026-08-01-example.review.md",
        verdict="FAIL",
        severity="critical",
        target="renmark/critical.py",
    )
    order = dispatch.build_repair_work_order(finding, work_order_id="WO-3")

    assert order is not None
    assert order.severity == "critical"


def test_pass_low_severity_finding_does_not_produce_work_order() -> None:
    finding = dispatch.InspectorFinding(
        finding_id="F-004",
        source_file=".renmark/reviews/2026-08-01-example.review.md",
        verdict="PASS",
        severity="minor",
        target="renmark/fine.py",
    )
    order = dispatch.build_repair_work_order(finding, work_order_id="WO-4")

    assert order is None


def test_pass_info_severity_finding_does_not_produce_work_order() -> None:
    finding = dispatch.InspectorFinding(
        finding_id="F-005",
        source_file=".renmark/reviews/2026-08-01-example.review.md",
        verdict="PASS",
        severity="info",
        target="renmark/fine2.py",
    )
    order = dispatch.build_repair_work_order(finding, work_order_id="WO-5")

    assert order is None


def test_repair_work_order_scope_reuses_worker_scope_and_is_well_formed() -> None:
    finding = dispatch.InspectorFinding(
        finding_id="F-006",
        source_file=".renmark/reviews/2026-08-01-example.review.md",
        verdict="FAIL",
        severity="critical",
        target="renmark/scoped.py",
    )
    order = dispatch.build_repair_work_order(finding, work_order_id="WO-6")

    assert order is not None
    # Reuses WP-5a's fast_path.WorkerScope type unchanged (design doc §9).
    assert isinstance(order.scope, fast_path.WorkerScope)
    assert order.scope.allowed_paths == frozenset({"renmark/scoped.py"})
    assert order.scope.allowed_actions == frozenset({"A", "M"})


def test_repair_work_order_rejects_empty_acceptance_criteria() -> None:
    import pytest

    with pytest.raises(ValueError):
        dispatch.RepairWorkOrder(
            order_id="WO-7",
            source_inspection_id="src#F-007",
            severity="major",
            scope=fast_path.WorkerScope(allowed_paths=frozenset({"renmark/x.py"})),
            description="repair x",
            acceptance_criteria=[],
        )


def test_repair_work_order_rejects_non_major_critical_severity() -> None:
    import pytest

    with pytest.raises(ValueError):
        dispatch.RepairWorkOrder(
            order_id="WO-8",
            source_inspection_id="src#F-008",
            severity="minor",  # type: ignore[arg-type]
            scope=fast_path.WorkerScope(allowed_paths=frozenset({"renmark/x.py"})),
            description="repair x",
            acceptance_criteria=["re-run check"],
        )

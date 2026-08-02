"""R-0.3/WP-4: proves the four real ledger emission call sites actually
append well-formed events, not just that they exist in source.

- Work Order + Work Result: renmark.cli._engine.execute_plan's per-task
  dispatch/return, wired around the ``_execute_task`` call inside its
  ``_runner`` closure.
- Inspection Report: renmark.scan.write_report.
- Escalation: renmark.state.pause.write_pause (the single canonical writer
  behind every PAUSED-state call site).

All offline — no live Agent/LLM/codex call. ``_execute_task`` is monkeypatched
to a canned success so the dispatch loop runs without a real executor.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from renmark import ledger, scan
from renmark.cli import _engine
from renmark.state import pause as pause_state


def _init_repo(path: Path) -> None:
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=path, check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.name", "t"], check=True)
    (path / "seed.txt").write_text("seed")
    subprocess.run(["git", "-C", str(path), "add", "seed.txt"], check=True)
    subprocess.run(["git", "-C", str(path), "commit", "-q", "-m", "init"], check=True)


def _write_plan(path: Path) -> Path:
    p = path / "plan.md"
    p.write_text(
        "### Task 1: task 1\n"
        "- **mode:** A\n"
        "- **target:** out/file1.txt\n"
        "- **context_files:** []\n"
        "- **verifier:** true\n"
        "- **verifier_timeout_s:** 5\n"
        "- **spec:**\n"
        "  make file 1\n"
    )
    return p


def test_execute_plan_emits_work_order_and_work_result(tmp_path, monkeypatch):
    _init_repo(tmp_path)
    plan = _write_plan(tmp_path)

    monkeypatch.setattr(_engine, "codex_available", lambda: True)
    monkeypatch.setattr(
        _engine,
        "_execute_task",
        lambda **kwargs: (True, "", 100, "deadbeef"),
    )

    rc = _engine.execute_plan(str(plan), repo=tmp_path)
    assert rc == 0

    orders = ledger.read_ledger_events(tmp_path, kind=ledger.KIND_WORK_ORDER)
    results = ledger.read_ledger_events(tmp_path, kind=ledger.KIND_WORK_RESULT)

    assert len(orders) == 1
    assert orders[0]["task"] == "make file 1"
    assert orders[0]["order_id"]

    assert len(results) == 1
    assert results[0]["status"] == "complete"
    assert results[0]["order_id"] == orders[0]["order_id"]


def test_execute_plan_emits_failed_work_result(tmp_path, monkeypatch):
    _init_repo(tmp_path)
    plan = _write_plan(tmp_path)

    monkeypatch.setattr(_engine, "codex_available", lambda: True)
    monkeypatch.setattr(
        _engine,
        "_execute_task",
        lambda **kwargs: (False, "verifier failed", 50, ""),
    )

    rc = _engine.execute_plan(str(plan), repo=tmp_path)
    assert rc != 0

    results = ledger.read_ledger_events(tmp_path, kind=ledger.KIND_WORK_RESULT)
    assert len(results) == 1
    assert results[0]["status"] == "failed"
    assert results[0]["summary"] == "verifier failed"


def test_scan_write_report_emits_inspection_report(tmp_path):
    report = scan.ScanReport(
        completion_state="complete",
        confidence="high",
        validation_status="validated",
        checks_run=["pytest"],
        checks_failed_to_run=[],
        findings=[],
    )

    rel_path = scan.write_report(tmp_path, report)

    events = ledger.read_ledger_events(tmp_path, kind=ledger.KIND_INSPECTION_REPORT)
    assert len(events) == 1
    assert events[0]["subject_ref"] == rel_path
    assert events[0]["verdict"] == "pass"
    assert events[0]["generator"] == "scan"


def test_scan_write_report_with_findings_emits_changes_requested(tmp_path):
    finding = scan.make_finding(
        check="verifier",
        rule_id="pytest",
        target="tests",
        risk="high",
        title="pytest failed",
        summary_text="a test failed",
        action="Run pytest locally and fix the reported failures.",
    )
    report = scan.ScanReport(
        completion_state="complete",
        confidence="high",
        validation_status="validated",
        checks_run=["pytest"],
        checks_failed_to_run=[],
        findings=[finding],
    )

    scan.write_report(tmp_path, report)

    events = ledger.read_ledger_events(tmp_path, kind=ledger.KIND_INSPECTION_REPORT)
    assert len(events) == 1
    assert events[0]["verdict"] == "changes_requested"
    assert events[0]["findings"] == ["pytest failed"]


def test_execute_plan_emits_independent_inspection_verdict(tmp_path, monkeypatch):
    # R-0.4/WP-4: the _runner call site derives a real InspectionReport from
    # the task's own verifier pass/fail outcome, with a dispatch_identity
    # structurally distinct from the WorkResult's — proving the wiring, not
    # just the underlying ledger primitives, offline (no live executor).
    _init_repo(tmp_path)
    plan = _write_plan(tmp_path)

    monkeypatch.setattr(_engine, "codex_available", lambda: True)
    monkeypatch.setattr(
        _engine,
        "_execute_task",
        lambda **kwargs: (True, "", 100, "deadbeef"),
    )

    rc = _engine.execute_plan(str(plan), repo=tmp_path)
    assert rc == 0

    results = ledger.read_ledger_events(tmp_path, kind=ledger.KIND_WORK_RESULT)
    assert len(results) == 1
    work_result_dispatch_identity = results[0]["dispatch_identity"]
    assert work_result_dispatch_identity

    order_id = results[0]["order_id"]
    verdict = ledger.latest_verdict_for(tmp_path, order_id)
    assert verdict is not None
    assert verdict.dispatch_identity
    assert verdict.dispatch_identity != work_result_dispatch_identity
    assert verdict.verdict in ledger.VERDICTS
    assert verdict.verdict == "pass"


def test_write_pause_emits_escalation(tmp_path):
    state = pause_state.PauseState(
        run_id="run-1",
        plan_path="plan.md",
        last_task_index=1,
        reason="deadline",
        ts="2026-08-01T00:00:00+00:00",
    )

    pause_state.write_pause(tmp_path, state)

    events = ledger.read_ledger_events(tmp_path, kind=ledger.KIND_ESCALATION)
    assert len(events) == 1
    assert events[0]["reason"] == "deadline"
    assert events[0]["blocking"] is True

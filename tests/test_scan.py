"""---
artifact_type: task-output
schema_version: 1
created_at: 2026-06-16T00:00:00+00:00
source_sha: null
related_plan: null
generator: codex
stale_after: null
dependency_refs:
  - /home/renmark/projects/ai-system/renmark/scan.py
  - /home/renmark/projects/ai-system/renmark/backlog.py
  - /home/renmark/projects/ai-system/renmark/summary.py
completion_state: complete
confidence: high
validation_status: validated
retry_count: 0
parser_success: true
schema_compliance: true
---

# REQ-14 scan structural-pivot test refresh

## Perspectives

1. Contract perspective: assert the current `renmark.scan` interface as implemented after the structural read-only pivot, not the earlier single-line cron/hook assumptions.
2. Persistence perspective: drive the real `renmark.backlog` and `renmark.summary` paths so evidence-path, reservation, rollback, and dedup behavior are exercised through the supported seams.
3. Failure-path perspective: verify degraded locking and write rollback are surfaced and safe under contention-like failures rather than silently passing.
4. CLI perspective: keep direct `cmd_scan()` exit semantics separate from top-level `python3 -m renmark` flag gating and `--emit-cron` rendering.

## Assumptions

- Blocking: the artifact envelope must remain a module docstring so `tests/test_scan.py` stays importable by pytest while still satisfying the renmark artifact format.
- Blocking: the updated `renmark/scan.py` source is authoritative for the current contract; no separate review artifact was provided with stronger requirements.
- Deferrable: the degraded-lock regression can assert the stderr warning prefix instead of an internal `degraded` list because `_ledger_lock` does not expose that list to callers.
- Deferrable: direct `_rollback_reserved()` tests are sufficient for the marker-token contract; a separate `_propose_one()` race simulation is useful but not required to prove deletion safety.

## Edge Cases

### Findings

- Blocking: `emit_cron()` now makes the "NOT a sandbox" clause and backlog reservation inventory part of the public contract, while the Claude trigger remains optional and wrapped across lines.
- Blocking: `_report_rel_path()` now includes `checks_failed_to_run` and a nonce, and `write_report()` reserves with `O_EXCL`, so same-name collisions must re-roll instead of overwrite.
- Blocking: `_ledger_lock()` no longer silently serializes on lock failure; the warning prefix must be visible when flock acquisition fails.
- Blocking: `_rollback_reserved()` now deletes only when the exact reservation marker token is still present in `pending_decision`.

## Recommendations

- Keep cron assertions fragment-based for the optional Claude flags; line wrapping is now intentionally part of the emitted text.
- Exercise report collisions and rollback deletion through the real filesystem seams so the tests bind to production ownership checks, not a mocked helper.

## Evidence

- Files read: `/home/renmark/projects/ai-system/CHANGELOG.md`, `/home/renmark/projects/ai-system/renmark/scan.py`, `/home/renmark/projects/ai-system/renmark/backlog.py`, `/home/renmark/projects/ai-system/tests/test_scan.py`
- Verifier run: `python3 -m pytest -q tests/test_scan.py` → `26 passed in 0.50s`
- Missing context: no external review artifact was provided for the "3 Major fixes"; the updated source file is the only concrete contract.

## Summary

- Updated cron rendering assertions to the honest-claim contract: direct CLI, `NOT a sandbox`, reservation inventory, and the negated mutate quote.
- Kept the nonce-backed distinct-path regression and added an explicit `O_EXCL` no-overwrite collision test.
- Added surfaced-lock-degradation coverage that proves `propose_findings()` still completes and warns when flock acquisition fails.
- Rewrote rollback coverage around the exact reservation marker API while still exercising real backlog files.
"""

from __future__ import annotations

import ast
import fcntl
import json
import subprocess
import sys
from pathlib import Path

import pytest

from renmark import backlog, scan
from renmark.cli.commands import cmd_scan
from renmark.state import state_dir


def _finding(*, title: str = "pytest failed", summary_text: str = "pytest reported failures") -> scan.Finding:
    return scan.make_finding(
        check="verifier",
        rule_id="pytest",
        target="tests",
        risk="high",
        title=title,
        summary_text=summary_text,
        action="Run pytest locally and fix the reported failures.",
    )


def _report(*findings: scan.Finding, failed_checks: list[str] | None = None) -> scan.ScanReport:
    failed = list(failed_checks or [])
    return scan.ScanReport(
        findings=list(findings),
        checks_run=["pytest"],
        checks_failed_to_run=failed,
        completion_state="partial" if failed else "complete",
        confidence="low" if failed else "high",
        validation_status="unvalidated" if failed else "validated",
    )


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _run_hook(command: str) -> subprocess.CompletedProcess[str]:
    payload = json.dumps({"tool_input": {"command": command}})
    return subprocess.run(
        ["bash", "-lc", scan._READONLY_HOOK_COMMAND],
        input=payload,
        text=True,
        capture_output=True,
        cwd=str(_repo_root()),
    )
def test_finding_key_is_stable_and_formatted() -> None:
    finding = _finding()
    assert scan.finding_key(finding) == "verifier:pytest:tests"
    assert scan.finding_key(finding) == scan.finding_key(finding)


def test_propose_findings_deduplicates_unchanged_reports(tmp_path: Path) -> None:
    report = _report(_finding())
    report_path = scan.write_report(tmp_path, report)

    new_ids = scan.propose_findings(tmp_path, report)
    items = backlog.list_items(tmp_path)

    assert len(new_ids) == 1
    assert len(items) == 1
    assert items[0].id == new_ids[0]
    assert items[0].status == "needs review"
    assert items[0].source == "qa"
    assert items[0].evidence_path == report_path

    repeated_ids = scan.propose_findings(tmp_path, report)
    repeated_items = backlog.list_items(tmp_path)

    assert repeated_ids == []
    assert len(repeated_items) == 1
    assert repeated_items[0].id == new_ids[0]


def test_changed_fingerprint_resurfaces_existing_item_without_duplication(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    stamps = iter(
        [
            "2026-06-16T10:11:12+00:00",
            "2026-06-16T10:11:13+00:00",
            "2026-06-16T10:11:14+00:00",
            "2026-06-16T10:11:15+00:00",
        ]
    )
    monkeypatch.setattr(scan, "now_iso", lambda: next(stamps))

    first = _finding(title="pytest failed", summary_text="first failure summary")
    first_report = _report(first)
    first_report_path = scan.write_report(tmp_path, first_report)
    first_ids = scan.propose_findings(tmp_path, first_report)

    changed = _finding(title="pytest still failing", summary_text="updated failure summary")
    changed_report = _report(changed)
    changed_report_path = scan.write_report(tmp_path, changed_report)
    changed_ids = scan.propose_findings(tmp_path, changed_report)

    items = backlog.list_items(tmp_path)
    ledger = scan.load_ledger(tmp_path)
    key = scan.finding_key(changed)

    assert changed_ids == []
    assert len(first_ids) == 1
    assert len(items) == 1
    assert items[0].id == first_ids[0]
    assert items[0].title == "pytest still failing"
    assert items[0].summary == "updated failure summary"
    assert items[0].status == "needs review"
    assert items[0].evidence_path == changed_report_path
    assert first_report_path != changed_report_path
    assert changed_report.evidence_path == changed_report_path
    assert ledger[key]["backlog_id"] == first_ids[0]
    assert ledger[key]["fingerprint"] == changed.fingerprint
    assert ledger[key]["state"] == "re-surfaced"


def test_write_report_without_propose_leaves_backlog_empty(tmp_path: Path) -> None:
    scan.write_report(tmp_path, _report(_finding()))
    assert backlog.list_items(tmp_path) == []


def test_proposed_item_has_expected_shape(tmp_path: Path) -> None:
    report = _report(_finding())
    report_path = scan.write_report(tmp_path, report)
    new_ids = scan.propose_findings(tmp_path, report)

    assert len(new_ids) == 1
    item = backlog.read_item(tmp_path, new_ids[0])

    assert item is not None
    assert item.source == "qa"
    assert item.status == "needs review"
    assert item.evidence_path == report_path


def test_emit_cron_prefers_direct_python_trigger_and_labels_optional_hook(tmp_path: Path) -> None:
    cron = scan.emit_cron(tmp_path)

    assert "renmark-execute --scan" in cron
    assert "PRIMARY (recommended) — direct pure-Python CLI" in cron
    assert "NOT a sandbox" in cron
    assert "reservation" in cron
    assert "nothing it runs can mutate" not in cron
    assert "OPTIONAL — model-driven trigger" in cron
    assert "best-effort PreToolUse hook" in cron
    assert "--tools" in cron
    assert "--disallowedTools" in cron
    assert "--permission-mode dontAsk" in cron


@pytest.mark.parametrize(
    "command",
    [
        "git -C /tmp commit -m x",
        "git --git-dir=.git commit",
        "FOO=1 git commit",
        "git push",
    ],
)
def test_readonly_hook_blocks_mutating_git_commands(command: str) -> None:
    proc = _run_hook(command)

    assert proc.returncode != 0
    assert "block" in proc.stdout
    assert "read-only" in proc.stdout


@pytest.mark.parametrize("command", ["git status", "git diff", "pytest -q"])
def test_readonly_hook_allows_read_only_commands(command: str) -> None:
    proc = _run_hook(command)

    assert proc.returncode == 0
    assert "block" not in proc.stdout


def test_write_report_identical_partial_reports_get_distinct_nonce_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(scan, "now_iso", lambda: "2026-06-16T12:00:01+00:00")

    first_report = _report(_finding(), failed_checks=["mypy"])
    second_report = _report(_finding(), failed_checks=["mypy"])

    first_path = scan.write_report(tmp_path, first_report)
    second_path = scan.write_report(tmp_path, second_report)

    assert first_path != second_path
    assert first_report.evidence_path == first_path
    assert second_report.evidence_path == second_path


def test_write_report_rerolls_existing_name_without_overwriting(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(scan, "now_iso", lambda: "2026-06-16T12:34:56+00:00")
    uuids = iter(
        [
            "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
        ]
    )
    monkeypatch.setattr(scan.uuid, "uuid4", lambda: type("ReservedUuid", (), {"hex": next(uuids)})())

    first_report = _report(_finding(summary_text="first report body"))
    first_path = scan.write_report(tmp_path, first_report)
    first_file = tmp_path / first_path
    first_contents = first_file.read_text(encoding="utf-8")

    second_report = _report(_finding(summary_text="second report body"))
    second_path = scan.write_report(tmp_path, second_report)
    second_file = tmp_path / second_path

    assert first_path != second_path
    assert first_file.read_text(encoding="utf-8") == first_contents
    assert "first report body" in first_contents
    assert "second report body" in second_file.read_text(encoding="utf-8")


def test_stale_ledger_entry_with_changed_fingerprint_creates_new_item(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(scan, "now_iso", lambda: "2026-06-16T13:00:00+00:00")
    changed = _finding(title="pytest still failing", summary_text="new summary after drift")
    report = _report(changed)
    report_path = scan.write_report(tmp_path, report)
    scan.save_ledger(
        tmp_path,
        {
            scan.finding_key(changed): {
                "backlog_id": "B999",
                "fingerprint": "oldfinger1234",
                "first_seen": "2026-06-15T00:00:00+00:00",
                "last_seen": "2026-06-15T00:00:00+00:00",
                "state": "proposed",
            }
        },
    )

    new_ids = scan.propose_findings(tmp_path, report)
    items = backlog.list_items(tmp_path)
    ledger = scan.load_ledger(tmp_path)
    entry = ledger[scan.finding_key(changed)]

    assert len(new_ids) == 1
    assert len(items) == 1
    assert items[0].id == new_ids[0]
    assert items[0].evidence_path == report_path
    assert entry["backlog_id"] == new_ids[0]
    assert entry["fingerprint"] == changed.fingerprint
    assert entry["state"] == "proposed"


def test_propose_findings_warns_when_ledger_lock_acquisition_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    original_flock = fcntl.flock

    def raising_flock(fd: int, op: int) -> None:
        if op & fcntl.LOCK_EX:
            raise OSError("lock unavailable")
        return original_flock(fd, op)

    monkeypatch.setattr(fcntl, "flock", raising_flock)

    report = _report(_finding())
    report_path = scan.write_report(tmp_path, report)
    new_ids = scan.propose_findings(tmp_path, report)
    stderr = capsys.readouterr().err
    item = backlog.read_item(tmp_path, new_ids[0])

    assert len(new_ids) == 1
    assert item is not None
    assert item.evidence_path == report_path
    assert stderr.startswith("renmark:scan WARNING: ledger lock unavailable")


def test_rollback_reserved_unlinks_only_exact_marker_token(tmp_path: Path) -> None:
    item_id = backlog.next_id(tmp_path)
    marker_token = f"{scan._RESERVATION_MARKER_PREFIX}deadbeefdeadbeefdeadbeefdeadbeef"
    reserved_path = backlog.backlog_dir(tmp_path) / f"{item_id}.json"

    marker_item = backlog.BacklogItem(id=item_id, title="", pending_decision=marker_token)
    assert backlog.write_item(tmp_path, marker_item) is not None
    assert reserved_path.exists()

    scan._rollback_reserved(tmp_path, item_id, marker_token)

    assert backlog.read_item(tmp_path, item_id) is None
    assert not reserved_path.exists()


def test_rollback_reserved_preserves_item_without_exact_marker_token(tmp_path: Path) -> None:
    item_id = backlog.next_id(tmp_path)
    expected_marker = f"{scan._RESERVATION_MARKER_PREFIX}deadbeefdeadbeefdeadbeefdeadbeef"
    different_marker = f"{scan._RESERVATION_MARKER_PREFIX}feedfacefeedfacefeedfacefeedface"
    reserved_path = backlog.backlog_dir(tmp_path) / f"{item_id}.json"

    real_item = backlog.BacklogItem(
        id=item_id,
        title="preserve me",
        status="needs review",
        source="qa",
        risk="medium",
        summary="real item already populated",
        evidence_path=".renmark/reviews/existing.review.md",
        recommended_action="keep the file",
        pending_decision=different_marker,
        created_at="2026-06-16T14:00:00+00:00",
        updated_at="2026-06-16T14:00:00+00:00",
    )
    assert backlog.write_item(tmp_path, real_item) is not None
    before = reserved_path.read_text(encoding="utf-8")

    scan._rollback_reserved(tmp_path, item_id, expected_marker)

    preserved = backlog.read_item(tmp_path, item_id)
    assert preserved is not None
    assert preserved.title == "preserve me"
    assert reserved_path.read_text(encoding="utf-8") == before


def test_cmd_scan_returns_partial_exit_code_when_checks_failed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(scan, "run_scan", lambda repo: _report(_finding(), failed_checks=["mypy"]))
    monkeypatch.setattr(scan, "write_report", lambda repo, report: ".renmark/reviews/mock.review.md")
    monkeypatch.setattr(scan, "propose_findings", lambda repo, report: [])

    assert cmd_scan(tmp_path) == 2


def test_cmd_scan_returns_zero_for_clean_findings_only_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(scan, "run_scan", lambda repo: _report(_finding()))
    monkeypatch.setattr(scan, "write_report", lambda repo, report: ".renmark/reviews/mock.review.md")
    monkeypatch.setattr(scan, "propose_findings", lambda repo, report: [])

    assert cmd_scan(tmp_path) == 0


def test_cli_flag_gating_requires_scan_for_propose() -> None:
    proc = subprocess.run(
        [sys.executable, "-m", "renmark", "--propose"],
        cwd=str(_repo_root()),
        text=True,
        capture_output=True,
    )

    assert proc.returncode == 2
    assert "--propose/--emit-cron require --scan" in proc.stderr


def test_cli_scan_emit_cron_exits_zero() -> None:
    proc = subprocess.run(
        [sys.executable, "-m", "renmark", "--scan", "--emit-cron"],
        cwd=str(_repo_root()),
        text=True,
        capture_output=True,
    )

    assert proc.returncode == 0
    assert "renmark-execute --scan" in proc.stdout
    assert "--permission-mode dontAsk" in proc.stdout


def test_scan_module_does_not_reference_write_lifecycle() -> None:
    source = Path(scan.__file__).read_text(encoding="utf-8")
    module = ast.parse(source)

    imported_names = {
        alias.name
        for node in ast.walk(module)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imported_from_modules = {
        node.module
        for node in ast.walk(module)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    called_names = {
        node.func.id
        for node in ast.walk(module)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    called_attrs = {
        node.func.attr
        for node in ast.walk(module)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }

    assert "lifecycle" not in imported_names
    assert "renmark.lifecycle" not in imported_from_modules
    assert ".lifecycle" not in imported_from_modules
    assert "write_lifecycle" not in called_names
    assert "write_lifecycle" not in called_attrs


def test_load_ledger_tolerates_corrupt_json(tmp_path: Path) -> None:
    ledger_path = state_dir(tmp_path) / "proposals.json"
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    ledger_path.write_text("{not-valid-json", encoding="utf-8")

    assert scan.load_ledger(tmp_path) == {}


def test_run_scan_smoke_returns_report_without_raising(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / ".git").mkdir()
    monkeypatch.setattr(scan, "PROJECT_VERIFIERS", ())

    report = scan.run_scan(tmp_path)

    assert isinstance(report, scan.ScanReport)
    assert report.completion_state in {"complete", "partial", "failed"}

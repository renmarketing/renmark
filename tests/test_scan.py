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
  - /home/renmark/projects/ai-system/renmark/cli/commands.py
  - /home/renmark/projects/ai-system/renmark/cli/_engine.py
completion_state: complete
confidence: medium
validation_status: unvalidated
retry_count: 0
parser_success: true
schema_compliance: true
---

# REQ-14 scan test refresh

## Perspectives

1. Contract perspective: assert the current `renmark.scan` seams as implemented, not the pre-fix assumptions the stale tests encoded.
2. Persistence perspective: drive the real backlog and proposal ledger on disk so evidence-path, stale-ledger, and dedup behavior are exercised end to end.
3. Enforcement perspective: execute the read-only hook command as a subprocess with the same stdin JSON shape Claude Code uses instead of substring-matching obsolete regex text.
4. CLI perspective: split direct `cmd_scan()` exit-code coverage from top-level `python3 -m renmark` flag-gating coverage so failures point at the right layer.

## Assumptions

- Blocking: `write_report()` is the only supported way to set `ScanReport.evidence_path` before `propose_findings()`.
- Blocking: the current hook contract is behavioral: deny mutating git/rm commands, allow read-only commands, and emit a block JSON payload on denial.
- Deferrable: report-path uniqueness is asserted with controlled same-day timestamps rather than wall-clock sleeps.
- Deferrable: `python3 -m renmark --scan --emit-cron` is exercised against the repo root because that path is import-safe and write-free.

## Edge Cases

### Findings

- Blocking: a changed fingerprint with a stale `backlog_id` must create a fresh backlog item instead of suppressing the live finding.
- Blocking: the re-surface path must update the existing item's `evidence_path` to the second report artifact, not a recomputed stale path.
- Blocking: partial scan runs must return exit code `2` from `cmd_scan()` even if report writing succeeds.
- Deferrable: same-second uniqueness is not asserted because the current implementation derives uniqueness from the timestamp slice plus content hash.

## Recommendations

- Keep hook tests behavioral. The command body is intentionally base64-wrapped and implementation details can change again without changing the deny/allow contract.
- Keep evidence-path assertions anchored to the path actually returned by `write_report()`. Date-only path reconstruction is explicitly obsolete.

## Evidence

- Files read: `/home/renmark/projects/ai-system/CHANGELOG.md`, `/home/renmark/projects/ai-system/renmark/scan.py`, `/home/renmark/projects/ai-system/renmark/cli/commands.py`, `/home/renmark/projects/ai-system/renmark/cli/_engine.py`
- Planned verifier: `python3 -m pytest -q tests/test_scan.py`
- Missing context: no separate code-review artifact was provided; the updated source is the only authoritative contract.

## Summary

- Replaced the stale path-equality assertion with re-surface and evidence-path assertions that match the fixed scan contract.
- Swapped the old regex-literal hook check for real subprocess-driven deny and allow coverage.
- Added regressions for unique report paths, stale-ledger recreation, partial exit codes, and top-level flag gating.
- Kept the file as a valid renmark artifact envelope while remaining importable and executable by pytest.
"""

from __future__ import annotations

import ast
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


def test_emit_cron_includes_permission_guards_and_commit_block_semantics(tmp_path: Path) -> None:
    cron = scan.emit_cron(tmp_path)
    proc = _run_hook("git -C /tmp commit -m x")

    assert "--permission-mode dontAsk" in cron
    assert "--disallowedTools" in cron
    assert "--tools" in cron
    assert '"matcher": "Bash"' in cron
    assert proc.returncode != 0
    assert "block" in proc.stdout
    assert "decision" in proc.stdout


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


def test_write_report_same_day_calls_are_distinct_and_evidence_tracks_written_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    stamps = iter(
        [
            "2026-06-16T12:00:01+00:00",
            "2026-06-16T12:00:02+00:00",
            "2026-06-16T12:00:03+00:00",
        ]
    )
    monkeypatch.setattr(scan, "now_iso", lambda: next(stamps))

    report = _report(_finding())
    first_path = scan.write_report(tmp_path, report)
    second_path = scan.write_report(tmp_path, report)
    new_ids = scan.propose_findings(tmp_path, report)
    item = backlog.read_item(tmp_path, new_ids[0])

    assert first_path != second_path
    assert report.evidence_path == second_path
    assert item is not None
    assert item.evidence_path == second_path
    assert item.evidence_path != ".renmark/reviews/2026-06-16-scan.review.md"


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

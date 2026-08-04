"""
---
artifact_type: renmark_task_output
schema_version: 1
created_at: 2026-08-04T00:00:00Z
source_sha: unknown
related_plan: "Task 8: registry + validator tests"
generator: codex
stale_after: null
dependency_refs:
  - renmark/hygiene.py
  - tests/test_hygiene.py
completion_state: complete
confidence: medium
validation_status: unvalidated
retry_count: 0
parser_success: true
schema_compliance: true
---

Added hygiene registry, budget, validator, and safe-delete coverage.

## Summary
- Asserted the registry still has 14 entries and non-empty globs.
- Covered budget CLI behavior for empty, warn, and block cases.
- Checked registry compliance for stray files and audit inventory citations.
- Exercised the ephemeral safe-delete gate for eligible debug artifacts.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from renmark.hygiene import ARTIFACT_REGISTRY, prune_memory, scan_artifacts, validate_registry_compliance


def _write_artifact(
    path: Path,
    *,
    created_at: str,
    stale_after: str | None = None,
    source_sha: str | None = None,
    artifact_type: str = "plan",
    dependency_refs: list[str] | None = None,
    body: str = "content",
) -> None:
    """Write a .renmark artifact with frontmatter so hygiene can read it."""
    path.parent.mkdir(parents=True, exist_ok=True)
    refs = dependency_refs or []
    dependency_block = ["dependency_refs: []"] if not refs else ["dependency_refs:"] + [f"  - {ref}" for ref in refs]
    path.write_text(
        "\n".join(
            [
                "---",
                f"artifact_type: {artifact_type}",
                "schema_version: 1",
                f"created_at: {created_at}",
                f"source_sha: {source_sha or 'abc123'}",
                "related_plan: null",
                "generator: test",
                f"stale_after: {stale_after if stale_after is not None else 'null'}",
                *dependency_block,
                "completion_state: complete",
                "confidence: medium",
                "validation_status: unvalidated",
                "retry_count: 0",
                "parser_success: true",
                "schema_compliance: true",
                "---",
                "",
                body,
                "",
                "## Summary",
                "",
                "- one",
                "",
            ]
        )
    )


def _write_memory_file(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def _iso_days_ago(days: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).replace(microsecond=0).isoformat()


def _set_mtime(path: Path, days_ago: int) -> None:
    when = (datetime.now(timezone.utc) - timedelta(days=days_ago)).timestamp()
    os.utime(path, (when, when))


def test_artifact_registry_has_expected_size_and_globs() -> None:
    assert len(ARTIFACT_REGISTRY) == 14
    for spec in ARTIFACT_REGISTRY:
        assert isinstance(spec.path_glob, str)
        assert spec.path_glob.strip()


def test_budget_cli_reports_ok_for_empty_repo(tmp_path: Path) -> None:
    result = subprocess.run(
        [sys.executable, "-m", "renmark.hygiene", "budget", "--repo", str(tmp_path)],
        capture_output=True,
        text=True,
    )
    lines = [line for line in result.stdout.splitlines() if line.startswith("BUDGET  ")]

    assert result.returncode == 0
    assert len(lines) == len(ARTIFACT_REGISTRY)
    assert all("status=ok" in line for line in lines)


def test_budget_cli_reports_warn_at_warn_threshold(tmp_path: Path) -> None:
    spec = next(item for item in ARTIFACT_REGISTRY if item.name == "memory")
    count = int(spec.budget_count * spec.warn_pct) + 1
    for i in range(count):
        _write_artifact(
            tmp_path / ".renmark" / "memory" / f"warn-{i:02d}.md",
            created_at=_iso_days_ago(1),
            artifact_type="memory",
        )

    result = subprocess.run(
        [sys.executable, "-m", "renmark.hygiene", "budget", "--repo", str(tmp_path)],
        capture_output=True,
        text=True,
    )
    memory_line = next(line for line in result.stdout.splitlines() if line.startswith("BUDGET  memory "))

    assert result.returncode == 0
    assert f"count={count}/{spec.budget_count}" in memory_line
    assert "status=warn" in memory_line


def test_budget_cli_reports_block_at_capacity(tmp_path: Path) -> None:
    spec = next(item for item in ARTIFACT_REGISTRY if item.name == "memory")
    for i in range(spec.budget_count or 0):
        _write_artifact(
            tmp_path / ".renmark" / "memory" / f"block-{i:02d}.md",
            created_at=_iso_days_ago(1),
            artifact_type="memory",
        )

    result = subprocess.run(
        [sys.executable, "-m", "renmark.hygiene", "budget", "--repo", str(tmp_path)],
        capture_output=True,
        text=True,
    )
    memory_line = next(line for line in result.stdout.splitlines() if line.startswith("BUDGET  memory "))

    assert result.returncode == 0
    assert f"count={spec.budget_count}/{spec.budget_count}" in memory_line
    assert "status=block" in memory_line


def test_validate_registry_compliance_flags_unregistered_files(tmp_path: Path) -> None:
    rogue = tmp_path / ".renmark" / "unregistered" / "rogue.md"
    _write_artifact(rogue, created_at=_iso_days_ago(1))

    issues = validate_registry_compliance(tmp_path)

    assert f"no registry entry: unregistered/rogue.md" in issues


def test_validate_registry_compliance_requires_project_map_pointer_for_inventory_files(
    tmp_path: Path,
) -> None:
    _write_artifact(
        tmp_path / ".renmark" / "memory" / "project-map.md",
        created_at=_iso_days_ago(1),
        artifact_type="memory",
    )
    missing = tmp_path / ".renmark" / "audits" / "inventory-missing.md"
    ok = tmp_path / ".renmark" / "audits" / "inventory-ok.md"
    _write_artifact(
        missing,
        created_at=_iso_days_ago(1),
        artifact_type="audit",
        dependency_refs=[".renmark/memory/other.md"],
    )
    _write_artifact(
        ok,
        created_at=_iso_days_ago(1),
        artifact_type="audit",
        dependency_refs=[".renmark/memory/project-map.md"],
    )

    issues = validate_registry_compliance(tmp_path)

    assert f"no project-map.md pointer: .renmark/audits/inventory-missing.md" in issues
    assert f"no project-map.md pointer: .renmark/audits/inventory-ok.md" not in issues


def test_safe_delete_gate_requires_age_inbound_refs_and_not_newest(tmp_path: Path) -> None:
    referenced = tmp_path / ".renmark" / "debug" / "ref" / "referenced.md"
    newest = tmp_path / ".renmark" / "debug" / "new" / "newest.md"
    young = tmp_path / ".renmark" / "debug" / "young" / "young.md"
    delete_me = tmp_path / ".renmark" / "debug" / "old" / "delete-me.md"

    _write_artifact(referenced, created_at=_iso_days_ago(110), artifact_type="debug")
    _write_artifact(newest, created_at=_iso_days_ago(5), artifact_type="debug")
    _write_artifact(young, created_at=_iso_days_ago(30), artifact_type="debug")
    _write_artifact(delete_me, created_at=_iso_days_ago(120), artifact_type="debug")
    for path, days in ((referenced, 110), (newest, 5), (young, 30), (delete_me, 120)):
        _set_mtime(path, days)

    _write_artifact(
        tmp_path / ".renmark" / "plans" / "referrer.md",
        created_at=_iso_days_ago(1),
        dependency_refs=[".renmark/debug/ref/referenced.md"],
    )

    report = scan_artifacts(tmp_path, dry_run=False)

    assert report.archived == 1
    assert delete_me in report.archived_paths
    assert not delete_me.exists()
    assert referenced.exists()
    assert newest.exists()
    assert young.exists()


def test_scan_empty_repo(tmp_path: Path) -> None:
    report = scan_artifacts(tmp_path)

    assert report.scanned == 0
    assert report.archived == 0
    assert report.errors == []


def test_scan_fresh_artifact_kept(tmp_path: Path) -> None:
    artifact = tmp_path / ".renmark" / "plans" / "fresh.md"
    _write_artifact(artifact, created_at=_iso_days_ago(1))

    report = scan_artifacts(tmp_path)

    assert report.archived == 0
    assert report.kept == 1


def test_scan_expired_stale_after_archived(tmp_path: Path) -> None:
    artifact = tmp_path / ".renmark" / "plans" / "expired.md"
    _write_artifact(
        artifact,
        created_at="2026-01-01T00:00:00+00:00",
        stale_after="2026-01-02T00:00:00+00:00",
    )

    report = scan_artifacts(tmp_path, dry_run=False)
    archive_month = datetime.now(timezone.utc).strftime("%Y-%m")
    archived = tmp_path / ".renmark" / "archive" / archive_month / ".renmark" / "plans" / "expired.md"

    assert report.archived == 1
    assert archived in report.archived_paths
    assert archived.exists()
    assert not artifact.exists()


def test_scan_ttl_fallback(tmp_path: Path) -> None:
    artifact = tmp_path / ".renmark" / "plans" / "ttl.md"
    _write_artifact(artifact, created_at=_iso_days_ago(100))

    report = scan_artifacts(tmp_path, ttl_days=90, dry_run=False)

    assert report.archived == 1
    assert not artifact.exists()


def test_scan_referenced_never_archived(tmp_path: Path) -> None:
    artifact = tmp_path / ".renmark" / "plans" / "kept.md"
    _write_artifact(
        artifact,
        created_at="2026-01-01T00:00:00+00:00",
        stale_after="2026-01-02T00:00:00+00:00",
    )
    state_path = tmp_path / ".renmark" / "state" / "lifecycle.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps({"artifacts": {"plan": ".renmark/plans/kept.md"}}))

    report = scan_artifacts(tmp_path, dry_run=False)

    assert report.archived == 0
    assert report.kept == 1
    assert artifact.exists()


def test_scan_dry_run_no_writes(tmp_path: Path) -> None:
    artifact = tmp_path / ".renmark" / "plans" / "dry-run.md"
    _write_artifact(
        artifact,
        created_at="2026-01-01T00:00:00+00:00",
        stale_after="2026-01-02T00:00:00+00:00",
    )

    report = scan_artifacts(tmp_path, dry_run=True)

    assert report.archived == 0
    assert report.archived_paths == [artifact]
    assert artifact.exists()


def test_scan_ghost_ref_counted(tmp_path: Path) -> None:
    artifact = tmp_path / ".renmark" / "plans" / "stale.md"
    _write_artifact(
        artifact,
        created_at="2026-01-01T00:00:00+00:00",
        stale_after="2026-01-02T00:00:00+00:00",
    )
    state_path = tmp_path / ".renmark" / "state" / "lifecycle.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps({"artifacts": {"plan": ".renmark/plans/missing.md"}}))

    report = scan_artifacts(tmp_path, dry_run=False)

    assert report.ghost_refs == 1


def test_scan_refuses_archive_outside_renmark(tmp_path: Path) -> None:
    try:
        scan_artifacts(tmp_path, archive_root=tmp_path / "outside")
    except ValueError as exc:
        assert "archive_root must live under" in str(exc)
    else:
        raise AssertionError("expected ValueError for archive_root outside .renmark")


def test_prune_dedupes_learnings(tmp_path: Path) -> None:
    from renmark import memory

    memory.append_learning(tmp_path, signal="same-signal", observation="same observation", date="2026-05-01")
    memory.append_learning(tmp_path, signal="same-signal", observation="same observation", date="2026-05-01")

    report = prune_memory(tmp_path, dry_run=False)

    learnings = tmp_path / ".renmark" / "memory" / "learnings.md"
    assert report.deduped == 1
    # Only one of the two identical bullets should remain.
    assert learnings.read_text().count("**same-signal** — same observation") == 1


def test_prune_ages_out_old_bugs(tmp_path: Path) -> None:
    from renmark import memory

    old_date = _iso_days_ago(200)[:10]
    new_date = _iso_days_ago(0)[:10]
    memory.log_bug(tmp_path, title="Old bug", severity="major", symptom="x", date=old_date)
    memory.log_bug(tmp_path, title="New bug", severity="major", symptom="y", date=new_date)

    report = prune_memory(tmp_path, days=180, dry_run=False)

    bugs = tmp_path / ".renmark" / "memory" / "bugs.md"
    assert report.aged_out == 1
    text = bugs.read_text()
    assert "Old bug" not in text
    assert "New bug" in text


def test_prune_dry_run_no_writes(tmp_path: Path) -> None:
    from renmark import memory

    memory.append_learning(tmp_path, signal="dup", observation="dup observation", date="2026-05-01")
    memory.append_learning(tmp_path, signal="dup", observation="dup observation", date="2026-05-01")

    learnings = tmp_path / ".renmark" / "memory" / "learnings.md"
    before = learnings.read_text()

    report = prune_memory(tmp_path, dry_run=True)

    assert report.deduped == 1
    assert learnings.read_text() == before


def test_prune_refuses_curated_files(tmp_path: Path) -> None:
    decisions = tmp_path / ".renmark" / "memory" / "decisions.md"
    learnings = tmp_path / ".renmark" / "memory" / "learnings.md"
    _write_memory_file(decisions, "# Decisions\n\n## ADR-001\n\nKeep this curated note.\n")
    _write_memory_file(
        learnings,
        "# Learnings\n\n## 2026-05-01\n\nSame item\n\n## 2026-05-01\n\nSame item\n",
    )
    before = decisions.read_text()

    prune_memory(tmp_path, dry_run=False)

    assert decisions.read_text() == before


def test_cli_help_exits_zero(tmp_path: Path) -> None:
    result = subprocess.run(
        [sys.executable, "-m", "renmark.hygiene", "--help"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0


def test_cli_scan_outputs_bounded(tmp_path: Path) -> None:
    artifact = tmp_path / ".renmark" / "plans" / "cli.md"
    _write_artifact(
        artifact,
        created_at="2026-01-01T00:00:00+00:00",
        stale_after="2026-01-02T00:00:00+00:00",
    )

    result = subprocess.run(
        [sys.executable, "-m", "renmark.hygiene", "scan", "--apply", "--repo", str(tmp_path)],
        capture_output=True,
        text=True,
    )
    lines = result.stdout.splitlines()

    assert result.returncode == 0
    assert len(lines) <= 5
    assert lines[0].startswith("HYGIENE  mode=apply")

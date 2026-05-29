from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from renmark.hygiene import prune_memory, scan_artifacts


def _write_artifact(
    path: Path,
    *,
    created_at: str,
    stale_after: str | None = None,
    source_sha: str | None = None,
    body: str = "content",
) -> None:
    """Write a .renmark artifact with frontmatter so hygiene can read it."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "---",
                "artifact_type: plan",
                "schema_version: 1",
                f"created_at: {created_at}",
                f"source_sha: {source_sha or 'abc123'}",
                "related_plan: null",
                "generator: test",
                f"stale_after: {stale_after if stale_after is not None else 'null'}",
                "dependency_refs: []",
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
    learnings = tmp_path / ".renmark" / "memory" / "learnings.md"
    _write_memory_file(
        learnings,
        "# Learnings\n\n## 2026-05-01\n\nSame item\n\n## 2026-05-01\n\nSame item\n",
    )

    report = prune_memory(tmp_path, dry_run=False)

    assert report.deduped == 1
    assert learnings.read_text() == "# Learnings\n\n## 2026-05-01\n\nSame item\n\n"


def test_prune_ages_out_old_bugs(tmp_path: Path) -> None:
    bugs = tmp_path / ".renmark" / "memory" / "bugs.md"
    _write_memory_file(
        bugs,
        (f"# Bugs\n\n## {_iso_days_ago(200)[:10]}\n\nOld bug\n\n## {_iso_days_ago(0)[:10]}\n\nNew bug\n"),
    )

    report = prune_memory(tmp_path, days=180, dry_run=False)

    assert report.aged_out == 1
    assert "Old bug" not in bugs.read_text()
    assert "New bug" in bugs.read_text()


def test_prune_dry_run_no_writes(tmp_path: Path) -> None:
    learnings = tmp_path / ".renmark" / "memory" / "learnings.md"
    original = "# Learnings\n\n## 2026-05-01\n\nSame item\n\n## 2026-05-01\n\nSame item\n"
    _write_memory_file(learnings, original)

    report = prune_memory(tmp_path, dry_run=True)

    assert report.deduped == 1
    assert learnings.read_text() == original


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

"""
---
artifact_type: renmark_task_output
schema_version: 1
created_at: 2026-08-04T00:00:00Z
source_sha: unknown
related_plan: "Task 9: CLI dispatch flag tests"
generator: codex
stale_after: null
dependency_refs:
  - renmark/cli/_engine.py
  - tests/test_hygiene.py
completion_state: complete
confidence: high
validation_status: validated
retry_count: 0
parser_success: true
schema_compliance: true
---

CLI coverage for the artifact-hygiene dispatch flags.

## Summary
- Checks dry-run `--artifact-hygiene` output and filesystem stability.
- Verifies `--artifact-hygiene-apply` is rejected unless the parent flag is set.
- Confirms apply mode deletes a proven-safe ephemeral artifact through the CLI path.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from renmark.cli import _engine


def _write_artifact(
    path: Path,
    *,
    created_at: str,
    artifact_type: str = "debug",
    dependency_refs: list[str] | None = None,
) -> None:
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
                "source_sha: abc123",
                "related_plan: null",
                "generator: test",
                "stale_after: null",
                *dependency_block,
                "completion_state: complete",
                "confidence: medium",
                "validation_status: unvalidated",
                "retry_count: 0",
                "parser_success: true",
                "schema_compliance: true",
                "---",
                "",
                "content",
                "",
                "## Summary",
                "",
                "- one",
                "",
            ]
        ),
        encoding="utf-8",
    )


def _iso_days_ago(days: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).replace(microsecond=0).isoformat()


def _set_mtime(path: Path, days_ago: int) -> None:
    when = (datetime.now(timezone.utc) - timedelta(days=days_ago)).timestamp()
    os.utime(path, (when, when))


def _seed_delete_eligible_repo(tmp_path: Path) -> Path:
    referenced = tmp_path / ".renmark" / "debug" / "ref" / "referenced.md"
    newest = tmp_path / ".renmark" / "debug" / "new" / "newest.md"
    young = tmp_path / ".renmark" / "debug" / "young" / "young.md"
    delete_me = tmp_path / ".renmark" / "debug" / "old" / "delete-me.md"

    _write_artifact(referenced, created_at=_iso_days_ago(110))
    _write_artifact(newest, created_at=_iso_days_ago(5))
    _write_artifact(young, created_at=_iso_days_ago(30))
    _write_artifact(delete_me, created_at=_iso_days_ago(120))
    for path, days in ((referenced, 110), (newest, 5), (young, 30), (delete_me, 120)):
        _set_mtime(path, days)

    _write_artifact(
        tmp_path / ".renmark" / "plans" / "referrer.md",
        created_at=_iso_days_ago(1),
        artifact_type="plan",
        dependency_refs=[".renmark/debug/ref/referenced.md"],
    )

    return delete_me


def _snapshot_files(root: Path) -> set[str]:
    return {
        str(path.relative_to(root)).replace("\\", "/")
        for path in root.rglob("*")
        if path.is_file()
    }


def _snapshot_hygiene_targets(root: Path) -> set[str]:
    # The CLI writes startup state under .renmark/state and .renmark/memory;
    # the hygiene flag should only affect the artifact tree itself.
    return {
        rel
        for rel in _snapshot_files(root)
        if not rel.startswith(".renmark/memory/") and not rel.startswith(".renmark/state/")
    }


def _invoke_cli(argv: list[str]) -> int:
    try:
        result = _engine.main(argv)
    except SystemExit as exc:  # pragma: no cover - defensive parity with CLI semantics
        code = exc.code
        return code if isinstance(code, int) else 1
    return result if isinstance(result, int) else 0


def test_artifact_hygiene_dry_run_reports_without_writing(
    tmp_path: Path,
    capsys,
) -> None:
    delete_me = _seed_delete_eligible_repo(tmp_path)
    before = _snapshot_hygiene_targets(tmp_path)

    rc = _invoke_cli(["--repo", str(tmp_path), "--artifact-hygiene"])
    captured = capsys.readouterr()
    stdout_lines = [line for line in captured.out.splitlines() if line.strip()]

    after = _snapshot_hygiene_targets(tmp_path)
    assert rc == 0
    assert any(line.startswith("HYGIENE") for line in stdout_lines)
    assert any(line.startswith("BUDGET") for line in stdout_lines)
    assert any(line.startswith("VALIDATE") for line in stdout_lines)
    assert before == after
    assert delete_me.exists()
    assert captured.err == ""


def test_artifact_hygiene_apply_requires_parent_flag(
    tmp_path: Path,
    capsys,
) -> None:
    rc = _invoke_cli(["--repo", str(tmp_path), "--artifact-hygiene-apply"])
    captured = capsys.readouterr()

    assert rc == 2
    assert captured.out == ""
    assert "--artifact-hygiene-apply requires --artifact-hygiene" in captured.err


def test_artifact_hygiene_apply_deletes_safe_ephemeral_artifact(
    tmp_path: Path,
    capsys,
) -> None:
    delete_me = _seed_delete_eligible_repo(tmp_path)
    before = _snapshot_hygiene_targets(tmp_path)
    delete_me_rel = str(delete_me.relative_to(tmp_path)).replace("\\", "/")

    rc = _invoke_cli(
        [
            "--repo",
            str(tmp_path),
            "--artifact-hygiene",
            "--artifact-hygiene-apply",
        ]
    )
    captured = capsys.readouterr()
    stdout_lines = [line for line in captured.out.splitlines() if line.strip()]

    after = _snapshot_hygiene_targets(tmp_path)
    assert rc == 0
    assert any(line.startswith("HYGIENE") for line in stdout_lines)
    assert any(line.startswith("BUDGET") for line in stdout_lines)
    assert any(line.startswith("VALIDATE") for line in stdout_lines)
    assert before - after == {delete_me_rel}
    assert not delete_me.exists()
    assert (tmp_path / ".renmark" / "debug" / "ref" / "referenced.md").exists()
    assert (tmp_path / ".renmark" / "debug" / "new" / "newest.md").exists()
    assert (tmp_path / ".renmark" / "debug" / "young" / "young.md").exists()
    assert captured.err == ""

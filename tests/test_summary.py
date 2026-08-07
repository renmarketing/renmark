"""Unit tests for renmark.summary (G3, G6, G9 enforcement)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from renmark import summary
from renmark.summary import SummaryBoundaryError


def test_write_artifact_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "test.md"
    summary.write_artifact(
        path,
        artifact_type="research",
        body="full body content that orchestrator should never read",
        summary_lines=["finding 1", "finding 2", "finding 3"],
        generator="codex",
    )
    assert path.exists()
    text = path.read_text()
    assert text.startswith("---\n")
    assert "artifact_type: research" in text
    assert "## Summary" in text
    assert "- finding 1" in text


def test_write_artifact_enforces_5_line_cap(tmp_path: Path) -> None:
    path = tmp_path / "fail.md"
    with pytest.raises(SummaryBoundaryError):
        summary.write_artifact(
            path,
            artifact_type="test",
            body="x",
            summary_lines=["a", "b", "c", "d", "e", "f"],  # 6 lines = bug
        )
    assert not path.exists()


def test_write_artifact_enforces_per_line_token_cap(tmp_path: Path) -> None:
    path = tmp_path / "fail.md"
    too_long = "x" * (summary.MAX_CHARS_PER_LINE + 1)
    with pytest.raises(SummaryBoundaryError):
        summary.write_artifact(
            path,
            artifact_type="test",
            body="x",
            summary_lines=[too_long],
        )


def test_write_artifact_full_metadata(tmp_path: Path) -> None:
    path = tmp_path / "full.md"
    summary.write_artifact(
        path,
        artifact_type="security",
        body="body",
        summary_lines=["1 critical, 2 high"],
        generator="codex",
        related_plan=".renmark/plans/2026-05-19-x.plan.md",
        source_sha="abc123",
        completion_state="partial",
        confidence="high",
        validation_status="validated",
        retry_count=1,
        dependency_refs=["a.md", "b.md"],
    )
    meta = summary.read_metadata(path)
    assert meta["artifact_type"] == "security"
    assert meta["generator"] == "codex"
    assert meta["completion_state"] == "partial"
    assert meta["confidence"] == "high"
    assert meta["validation_status"] == "validated"
    assert meta["retry_count"] == 1
    assert meta["source_sha"] == "abc123"
    assert meta["dependency_refs"] == ["a.md", "b.md"]
    # schema_version round-trips through the tiny YAML parser as int — fine
    assert str(meta["schema_version"]) == "1"


def test_emit_pointer_returns_bounded_string(tmp_path: Path) -> None:
    path = tmp_path / "a.md"
    summary.write_artifact(
        path,
        artifact_type="research",
        body="x" * 100_000,  # big body, must not appear in pointer
        summary_lines=["line1", "line2"],
        generator="codex",
        confidence="high",
    )
    pointer = summary.emit_pointer(path, "Research")
    assert "x" * 1000 not in pointer  # body must not leak
    assert "research" in pointer
    assert "confidence=high" in pointer
    assert "line1" in pointer
    assert "line2" in pointer
    # Total length is bounded
    assert pointer.count("\n") <= summary.MAX_SUMMARY_LINES + 1  # header + bullets


def test_emit_pointer_caps_at_n_lines(tmp_path: Path) -> None:
    path = tmp_path / "a.md"
    # Bypass write_artifact's validation by writing manually with 10 summary
    # lines — emit_pointer must still cap.
    content = (
        "---\nartifact_type: x\nschema_version: 1\ncreated_at: 2026-01-01T00:00:00+00:00\n"
        "source_sha: null\nrelated_plan: null\ngenerator: test\nstale_after: null\n"
        "dependency_refs: []\ncompletion_state: complete\nconfidence: medium\n"
        "validation_status: unvalidated\nretry_count: 0\nparser_success: true\n"
        "schema_compliance: true\n---\n\nbody\n\n## Summary\n\n" + "\n".join(f"- line {i}" for i in range(10))
    )
    path.write_text(content)
    pointer = summary.emit_pointer(path, "X", n_lines=3)
    assert "line 0" in pointer
    assert "line 2" in pointer
    assert "line 5" not in pointer  # capped at n_lines=3


def test_emit_pointer_missing_artifact(tmp_path: Path) -> None:
    pointer = summary.emit_pointer(tmp_path / "missing.md", "Test")
    assert "missing" in pointer.lower()


def test_emit_pointer_missing_summary_section(tmp_path: Path) -> None:
    path = tmp_path / "bad.md"
    path.write_text("---\nartifact_type: x\n---\n\nbody without summary section\n")
    pointer = summary.emit_pointer(path, "Bad")
    assert "Summary" in pointer  # the error message mentions it


def test_read_metadata_handles_no_frontmatter(tmp_path: Path) -> None:
    path = tmp_path / "plain.md"
    path.write_text("# Just markdown\n\nNo frontmatter.\n")
    assert summary.read_metadata(path) == {}


def test_read_metadata_handles_missing_file(tmp_path: Path) -> None:
    assert summary.read_metadata(tmp_path / "ghost.md") == {}


def test_is_stale_missing_file(tmp_path: Path) -> None:
    assert summary.is_stale(tmp_path / "ghost.md") is True


def test_is_stale_fresh_artifact(tmp_path: Path) -> None:
    path = tmp_path / "fresh.md"
    summary.write_artifact(path, artifact_type="x", body="b", summary_lines=["s"], generator="t")
    assert summary.is_stale(path) is False


def test_is_stale_past_stale_after(tmp_path: Path) -> None:
    path = tmp_path / "old.md"
    past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(timespec="seconds")
    summary.write_artifact(
        path,
        artifact_type="x",
        body="b",
        summary_lines=["s"],
        generator="t",
        stale_after=past,
    )
    assert summary.is_stale(path) is True


def test_is_stale_naive_stale_after_does_not_raise(tmp_path: Path) -> None:
    path = tmp_path / "naive.md"
    summary.write_artifact(
        path,
        artifact_type="x",
        body="b",
        summary_lines=["s"],
        generator="t",
        stale_after="2020-01-01",  # date-only, no time/timezone component
    )
    assert summary.is_stale(path) is True


def test_is_stale_sha_drift(tmp_path: Path) -> None:
    path = tmp_path / "drifted.md"
    summary.write_artifact(
        path,
        artifact_type="x",
        body="b",
        summary_lines=["s"],
        generator="t",
        source_sha="abc",
    )
    assert summary.is_stale(path, against_sha="xyz") is True
    assert summary.is_stale(path, against_sha="abc") is False


def test_verifier_tail_success(tmp_path: Path) -> None:
    result = summary.verifier_tail("echo hello && echo world", cwd=tmp_path)
    assert result.startswith("exit 0 |")
    assert "hello" in result
    assert "world" in result


def test_verifier_tail_failure(tmp_path: Path) -> None:
    result = summary.verifier_tail("echo broken && exit 7", cwd=tmp_path)
    assert result.startswith("exit 7 |")
    assert "broken" in result


def test_verifier_tail_bounded_output(tmp_path: Path) -> None:
    # Output a long string — verifier_tail must still return a bounded line
    result = summary.verifier_tail("for i in $(seq 1 1000); do echo line-$i; done", cwd=tmp_path)
    assert len(result) < summary.MAX_CHARS_PER_LINE + 100  # bounded


def test_hash_artifact_deterministic(tmp_path: Path) -> None:
    path = tmp_path / "a.md"
    path.write_text("same content")
    h1 = summary.hash_artifact(path)
    h2 = summary.hash_artifact(path)
    assert h1 == h2
    assert len(h1) == 64


def test_artifact_metadata_default_created_at_is_recent() -> None:
    meta = summary.ArtifactMetadata(artifact_type="x")
    now = datetime.now(timezone.utc)
    parsed = datetime.fromisoformat(meta.created_at)
    assert abs((now - parsed).total_seconds()) < 5


def test_read_summary_lines_strips_bullets(tmp_path: Path) -> None:
    path = tmp_path / "v.md"
    summary.write_artifact(
        path,
        artifact_type="verification",
        body="body the orchestrator never reads",
        summary_lines=["passed: 3/5", "failed: search entries"],
    )
    assert summary.read_summary_lines(path) == ["passed: 3/5", "failed: search entries"]
    assert summary.read_summary_lines(tmp_path / "missing.md") == []


def test_summary_lines_feed_loop_decision(tmp_path: Path) -> None:
    """Integration: write_artifact -> read_metadata + read_summary_lines ->
    loop.build_decision must yield a non-blank next_action for a failed verify
    (frontmatter alone never carries summary_lines — the loop was stalling)."""
    from renmark import loop

    path = tmp_path / "v.md"
    summary.write_artifact(
        path,
        artifact_type="verification",
        body="b",
        summary_lines=[
            "failed: search entries",
            'run /renmark:debug with symptom: "search exits 1: no such table"',
        ],
        completion_state="partial",
    )
    meta = summary.read_metadata(path)
    meta["summary_lines"] = summary.read_summary_lines(path)
    decision = loop.build_decision(meta, 0)
    assert decision["next_action"]
    assert decision["goal_reached"] is False

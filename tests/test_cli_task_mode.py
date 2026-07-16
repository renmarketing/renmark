"""Unit tests for the ad-hoc Codex task mode in renmark-execute."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from renmark import __version__, cli


def test_version_flag_reports_package_version(capsys) -> None:
    with pytest.raises(SystemExit) as exc_info:
        cli.main(["--version"])

    assert exc_info.value.code == 0
    assert capsys.readouterr().out.strip() == f"renmark-execute {__version__}"


def test_task_mode_missing_output_arg_errors() -> None:
    """--task requires --output."""
    with pytest.raises(SystemExit):
        cli.main(["--task", "/tmp/x.md"])  # no --output


def test_task_mode_missing_spec_returns_fail_json(tmp_path: Path, capsys) -> None:
    """If the spec file is missing, emit a FAIL SubagentOutput JSON."""
    rc = cli.cmd_task(
        task_spec_path=str(tmp_path / "missing.md"),
        output_path=str(tmp_path / "out.md"),
        repo=tmp_path,
    )
    assert rc == 2
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert payload["status"] == "FAIL"
    assert "not found" in " ".join(payload["summary_lines"])
    assert payload["completion_state"] == "failed"


def test_task_mode_no_codex_returns_fail_json(tmp_path: Path, capsys, monkeypatch) -> None:
    """If codex isn't on PATH, the ad-hoc mode fails cleanly with bounded JSON."""
    spec = tmp_path / "spec.md"
    spec.write_text("do a thing")
    # Force codex to be 'not found'
    monkeypatch.setattr(shutil, "which", lambda name: None if name == "codex" else "/usr/bin/" + name)
    rc = cli.cmd_task(
        task_spec_path=str(spec),
        output_path=str(tmp_path / "out.md"),
        repo=tmp_path,
    )
    assert rc == 127
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "FAIL"
    assert any("codex" in line.lower() for line in payload["summary_lines"])


def test_task_mode_emits_pass_json_when_codex_succeeds(tmp_path: Path, capsys, monkeypatch) -> None:
    """Mock codex subprocess to write a valid artifact; ad-hoc mode should
    parse it into a SubagentOutput-shaped JSON."""
    spec = tmp_path / "spec.md"
    spec.write_text("summarize")
    out = tmp_path / "artifact.md"

    monkeypatch.setattr(shutil, "which", lambda name: "/fake/codex" if name == "codex" else None)

    def fake_run(cmd, **kwargs):
        # Write a valid renmark artifact to the output path.
        # (Codex would normally do this; we simulate it.)
        from renmark.summary import write_artifact

        write_artifact(
            out,
            artifact_type="research",
            body="big body content",
            summary_lines=["finding A", "finding B"],
            generator="codex",
        )

        class FakeProc:
            returncode = 0
            stdout = ""
            stderr = ""

        return FakeProc()

    monkeypatch.setattr(subprocess, "run", fake_run)

    rc = cli.cmd_task(
        task_spec_path=str(spec),
        output_path=str(out),
        repo=tmp_path,
    )
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "PASS"
    assert payload["artifact_path"] == str(out)
    assert payload["completion_state"] == "complete"
    assert len(payload["summary_lines"]) <= 5
    # G9: a valid artifact (frontmatter + ## Summary, as write_artifact emits)
    # must validate, and all six transparency fields must be present.
    assert payload["validation_status"] == "validated"
    assert payload["confidence"] == "medium"
    assert payload["parser_success"] is True
    assert payload["schema_compliance"] is True
    assert "retry_count" in payload
    # Crucial G3 check: orchestrator-visible payload has no "body" / "transcript" / "diff" leak
    forbidden = {"transcript", "body", "diff", "generated_code", "reasoning"}
    assert not (set(payload.keys()) & forbidden)


def test_task_mode_malformed_artifact_downgrades_g9(tmp_path: Path, capsys, monkeypatch) -> None:
    """G9 emitting side: codex exits 0 but writes a malformed artifact (no
    frontmatter / no ## Summary). cmd_task must still report the path but
    downgrade — partial / low / validation_status=failed — never silent PASS
    with optimistic confidence."""
    spec = tmp_path / "spec.md"
    spec.write_text("summarize")
    out = tmp_path / "artifact.md"

    monkeypatch.setattr(shutil, "which", lambda name: "/fake/codex" if name == "codex" else None)

    def fake_run(cmd, **kwargs):
        # Write a malformed artifact: plain text, no frontmatter, no ## Summary.
        out.write_text("just some prose codex emitted, not renmark format")

        class FakeProc:
            returncode = 0
            stdout = ""
            stderr = ""

        return FakeProc()

    monkeypatch.setattr(subprocess, "run", fake_run)

    rc = cli.cmd_task(task_spec_path=str(spec), output_path=str(out), repo=tmp_path)
    assert rc == 0  # artifact exists → status PASS, but downgraded
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "PASS"
    assert payload["artifact_path"] == str(out)
    assert payload["completion_state"] == "partial"
    assert payload["confidence"] == "low"
    assert payload["validation_status"] == "failed"
    assert payload["schema_compliance"] is False


def test_task_mode_emits_fail_when_codex_exits_nonzero(tmp_path: Path, capsys, monkeypatch) -> None:
    spec = tmp_path / "spec.md"
    spec.write_text("x")
    monkeypatch.setattr(shutil, "which", lambda name: "/fake/codex" if name == "codex" else None)

    def fake_run(cmd, **kwargs):
        class FakeProc:
            returncode = 3
            stdout = ""
            stderr = "codex error: rate limited\nretry later"

        return FakeProc()

    monkeypatch.setattr(subprocess, "run", fake_run)

    rc = cli.cmd_task(
        task_spec_path=str(spec),
        output_path=str(tmp_path / "out.md"),
        repo=tmp_path,
    )
    assert rc == 3
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "FAIL"
    assert any("rate" in line.lower() or "error" in line.lower() for line in payload["summary_lines"])


def test_task_mode_emits_fail_on_timeout(tmp_path: Path, capsys, monkeypatch) -> None:
    spec = tmp_path / "spec.md"
    spec.write_text("x")
    monkeypatch.setattr(shutil, "which", lambda name: "/fake/codex" if name == "codex" else None)

    def fake_run(cmd, **kwargs):
        raise subprocess.TimeoutExpired(cmd, 600)

    monkeypatch.setattr(subprocess, "run", fake_run)

    rc = cli.cmd_task(
        task_spec_path=str(spec),
        output_path=str(tmp_path / "out.md"),
        repo=tmp_path,
    )
    assert rc == 124  # canonical timeout exit
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "FAIL"
    assert any("timed out" in line.lower() for line in payload["summary_lines"])


def test_task_mode_pass_payload_round_trips_through_parser(tmp_path: Path, capsys, monkeypatch) -> None:
    """KEY INTEGRATION (G11): orchestrate pipes renmark-execute --task output
    through dispatch.parse_subagent_response. The PASS payload must be accepted
    — emitting any field outside SUBAGENT_OUTPUT_FIELDS would mark every
    successful codex task FAIL. (Release blocker found by v0.9.0 codereview.)"""
    from renmark.dispatch import parse_subagent_response

    spec = tmp_path / "spec.md"
    spec.write_text("summarize")
    out = tmp_path / "artifact.md"
    monkeypatch.setattr(shutil, "which", lambda name: "/fake/codex" if name == "codex" else None)

    def fake_run(cmd, **kwargs):
        from renmark.summary import write_artifact

        write_artifact(out, artifact_type="research", body="b", summary_lines=["a"], generator="codex")

        class FakeProc:
            returncode = 0
            stdout = ""
            stderr = ""

        return FakeProc()

    monkeypatch.setattr(subprocess, "run", fake_run)
    rc = cli.cmd_task(task_spec_path=str(spec), output_path=str(out), repo=tmp_path)
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    parsed = parse_subagent_response(payload)  # must NOT raise IsolationViolation
    assert parsed.status == "PASS"
    assert parsed.validation_status == "validated"


def test_task_mode_fail_payload_round_trips_through_parser(tmp_path: Path, capsys, monkeypatch) -> None:
    """The early-fail payloads must also stay parser-legal with all six G9 fields."""
    from renmark.dispatch import parse_subagent_response

    monkeypatch.setattr(shutil, "which", lambda name: None if name == "codex" else "/usr/bin/" + name)
    rc = cli.cmd_task(task_spec_path=str(tmp_path / "spec.md"), output_path=str(tmp_path / "o.md"), repo=tmp_path)
    assert rc != 0
    payload = json.loads(capsys.readouterr().out)
    for f in ("validation_status", "parser_success", "schema_compliance"):
        assert f in payload
    parsed = parse_subagent_response(payload)
    assert parsed.status == "FAIL"

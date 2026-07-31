"""CLI coverage for canonical Agency/Orchestrator delivery modes."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _delivery_path(repo: Path) -> Path:
    return repo / ".renmark" / "state" / "delivery.json"


def _run_cli(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "renmark", "--repo", str(repo), *args],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )


def test_set_and_get_agency_mode(tmp_path: Path) -> None:
    result = _run_cli(tmp_path, "--set-mode", "agency")
    assert result.returncode == 0
    assert "delivery mode set to agency" in result.stdout
    assert "execution policy: guided" in result.stdout
    assert ".renmark/state/delivery.json" in result.stdout.replace("\\", "/")

    get_result = _run_cli(tmp_path, "--get-mode")
    assert get_result.returncode == 0
    assert get_result.stdout.strip() == "agency (guided)"


def test_set_and_get_orchestrator_mode(tmp_path: Path) -> None:
    result = _run_cli(tmp_path, "--set-mode", "orchestrator")
    assert result.returncode == 0
    assert "execution policy: async" in result.stdout
    assert _delivery_path(tmp_path).exists()
    assert _run_cli(tmp_path, "--get-mode").stdout.strip() == (
        "orchestrator (async)"
    )


def test_clear_mode_is_idempotent_and_removes_legacy_state(tmp_path: Path) -> None:
    assert _run_cli(tmp_path, "--set-mode", "agency").returncode == 0
    legacy = tmp_path / ".renmark" / "state" / "mode.json"
    legacy.write_text(json.dumps({"mode": "conductor"}), encoding="utf-8")

    first = _run_cli(tmp_path, "--clear-mode")
    second = _run_cli(tmp_path, "--clear-mode")

    assert first.returncode == second.returncode == 0
    assert "delivery mode cleared" in first.stdout
    assert _run_cli(tmp_path, "--get-mode").stdout.strip() == "unset"
    assert not _delivery_path(tmp_path).exists()
    assert not legacy.exists()


def test_get_mode_reads_legacy_conductor_as_guided_orchestrator(
    tmp_path: Path,
) -> None:
    legacy = tmp_path / ".renmark" / "state" / "mode.json"
    legacy.parent.mkdir(parents=True)
    legacy.write_text(json.dumps({"mode": "conductor"}), encoding="utf-8")

    result = _run_cli(tmp_path, "--get-mode")

    assert result.returncode == 0
    assert result.stdout.strip() == "orchestrator (guided)"


def test_conductor_and_bogus_are_rejected_without_overwriting_state(
    tmp_path: Path,
) -> None:
    assert _run_cli(tmp_path, "--set-mode", "agency").returncode == 0
    before = _delivery_path(tmp_path).read_text(encoding="utf-8")

    for invalid in ("conductor", "bogus"):
        result = _run_cli(tmp_path, "--set-mode", invalid)
        assert result.returncode == 2
        assert "invalid choice" in result.stderr

    assert _delivery_path(tmp_path).read_text(encoding="utf-8") == before


def test_agency_activation_alias_converges_canonical_mode(tmp_path: Path) -> None:
    activated = _run_cli(tmp_path, "--activate-agency")
    assert activated.returncode == 0
    assert _run_cli(tmp_path, "--get-mode").stdout.strip() == "agency (guided)"

    deactivated = _run_cli(tmp_path, "--deactivate-agency")
    assert deactivated.returncode == 0
    assert _run_cli(tmp_path, "--get-mode").stdout.strip() == (
        "orchestrator (async)"
    )

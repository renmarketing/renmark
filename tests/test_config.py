"""Tests for renmark.config — persisted proactivity toggle (P11)."""

from __future__ import annotations

import json
from pathlib import Path

from renmark import config as cfg

# ── is_proactive: default behaviour ──────────────────────────────────────────


def test_default_is_true_when_no_config(tmp_path: Path) -> None:
    """Absence of .renmark/config.json must return True (backward-compat)."""
    assert cfg.is_proactive(tmp_path) is True


def test_default_is_true_when_file_missing_key(tmp_path: Path) -> None:
    """A config file with unrelated keys but no 'proactive' key → True."""
    p = tmp_path / ".renmark" / "config.json"
    p.parent.mkdir(parents=True)
    p.write_text(json.dumps({"other_key": "value"}), encoding="utf-8")
    assert cfg.is_proactive(tmp_path) is True


# ── set_proactive / round-trip ────────────────────────────────────────────────


def test_setter_writes_false_and_reads_back(tmp_path: Path) -> None:
    cfg.set_proactive(tmp_path, False)
    assert cfg.is_proactive(tmp_path) is False


def test_setter_writes_true_and_reads_back(tmp_path: Path) -> None:
    cfg.set_proactive(tmp_path, True)
    assert cfg.is_proactive(tmp_path) is True


def test_round_trip_false_then_true(tmp_path: Path) -> None:
    cfg.set_proactive(tmp_path, False)
    assert cfg.is_proactive(tmp_path) is False
    cfg.set_proactive(tmp_path, True)
    assert cfg.is_proactive(tmp_path) is True


def test_setter_preserves_other_keys(tmp_path: Path) -> None:
    """set_proactive must not clobber unrelated keys in config.json."""
    p = tmp_path / ".renmark" / "config.json"
    p.parent.mkdir(parents=True)
    p.write_text(json.dumps({"other_key": "kept"}), encoding="utf-8")
    cfg.set_proactive(tmp_path, False)
    data = json.loads(p.read_text(encoding="utf-8"))
    assert data["other_key"] == "kept"
    assert data["proactive"] is False


# ── REQ-6: config file stays under .renmark/ ─────────────────────────────────


def test_config_file_lives_under_renmark(tmp_path: Path) -> None:
    cfg.set_proactive(tmp_path, False)
    config_path = tmp_path / ".renmark" / "config.json"
    assert config_path.exists(), ".renmark/config.json must be created under .renmark/"


# ── Defensive degradation: corrupt / missing config never raises ──────────────


def test_corrupt_json_degrades_to_true(tmp_path: Path) -> None:
    p = tmp_path / ".renmark" / "config.json"
    p.parent.mkdir(parents=True)
    p.write_text("NOT VALID JSON {{{{", encoding="utf-8")
    # Must not raise; must return True (safe default)
    assert cfg.is_proactive(tmp_path) is True


def test_json_array_root_degrades_to_true(tmp_path: Path) -> None:
    """A JSON array at root is valid JSON but not a dict — degrade to True."""
    p = tmp_path / ".renmark" / "config.json"
    p.parent.mkdir(parents=True)
    p.write_text(json.dumps([1, 2, 3]), encoding="utf-8")
    assert cfg.is_proactive(tmp_path) is True


def test_set_proactive_on_unwritable_dir_does_not_raise(tmp_path: Path) -> None:
    """set_proactive swallows OS errors — never raises even if write fails."""
    import os

    renmark_dir = tmp_path / ".renmark"
    renmark_dir.mkdir(parents=True)
    # Make the directory read-only so write will fail.
    os.chmod(renmark_dir, 0o555)
    try:
        # Must not raise
        cfg.set_proactive(tmp_path, False)
    finally:
        os.chmod(renmark_dir, 0o755)  # restore for cleanup


def test_is_proactive_on_nonexistent_repo_does_not_raise(tmp_path: Path) -> None:
    """is_proactive on a path with no .renmark/ at all must return True silently."""
    nonexistent = tmp_path / "does" / "not" / "exist"
    assert cfg.is_proactive(nonexistent) is True

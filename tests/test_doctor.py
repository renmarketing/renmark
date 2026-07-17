"""Focused cross-host install checks for renmark.doctor."""

from __future__ import annotations

import json
from pathlib import Path

from renmark import doctor


def _write_manifest(path: Path, *, name: str = "renmark", version: str = "1.2.3") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"name": name, "version": version}))


def test_cross_host_manifest_check_requires_same_identity(tmp_path: Path, monkeypatch):
    plugin = tmp_path / "plugin"
    version_file = tmp_path / "VERSION"
    version_file.write_text("1.2.3\n")
    _write_manifest(plugin / ".claude-plugin" / "plugin.json")
    _write_manifest(plugin / ".codex-plugin" / "plugin.json")
    monkeypatch.setattr(doctor, "PLUGIN_SOURCE", plugin)
    monkeypatch.setattr(doctor, "VERSION_FILE", version_file)

    assert doctor.check_plugin_manifest().status == "pass"

    _write_manifest(plugin / ".codex-plugin" / "plugin.json", name="wrong")
    check = doctor.check_plugin_manifest()
    assert check.status == "fail"
    assert "manifest names" in check.detail


def test_codex_marketplace_and_source_fixes_are_idempotent(tmp_path: Path, monkeypatch):
    plugin = tmp_path / "checkout" / "plugin"
    _write_manifest(plugin / ".codex-plugin" / "plugin.json")
    marketplace = tmp_path / ".agents" / "plugins" / "marketplace.json"
    codex_source = tmp_path / "plugins" / "renmark"
    monkeypatch.setattr(doctor, "PLUGIN_SOURCE", plugin)
    monkeypatch.setattr(doctor, "CODEX_MARKETPLACE_JSON", marketplace)
    monkeypatch.setattr(doctor, "CODEX_PLUGIN_SOURCE", codex_source)

    assert doctor.check_codex_marketplace().status == "fail"
    assert doctor.check_codex_plugin_source().status == "fail"

    doctor._fix_codex_marketplace()
    doctor._fix_codex_source_link()
    doctor._fix_codex_marketplace()

    assert doctor.check_codex_marketplace().status == "pass"
    assert doctor.check_codex_plugin_source().status == "pass"
    assert not codex_source.is_symlink()
    entries = json.loads(marketplace.read_text())["plugins"]
    assert [entry["name"] for entry in entries].count("renmark") == 1


def test_codex_registry_check_requires_installed_and_enabled(monkeypatch):
    monkeypatch.setattr(doctor.shutil, "which", lambda command: "/fake/codex")

    def result(payload):
        return doctor.subprocess.CompletedProcess(
            args=["codex"],
            returncode=0,
            stdout=json.dumps(payload),
            stderr="",
        )

    monkeypatch.setattr(doctor.subprocess, "run", lambda *args, **kwargs: result({"installed": []}))
    assert doctor.check_codex_installed().status == "fail"

    monkeypatch.setattr(
        doctor.subprocess,
        "run",
        lambda *args, **kwargs: result(
            {
                "installed": [
                    {
                        "pluginId": "renmark@personal",
                        "installed": True,
                        "enabled": True,
                    }
                ]
            }
        ),
    )
    assert doctor.check_codex_installed().status == "pass"


def test_doctor_allows_unencodable_status_glyphs(monkeypatch):
    calls: list[dict[str, str]] = []

    class LegacyStdout:
        def reconfigure(self, **kwargs):
            calls.append(kwargs)

    monkeypatch.setattr(doctor.sys, "stdout", LegacyStdout())

    doctor._allow_unencodable_status_glyphs()

    assert calls == [{"errors": "replace"}]

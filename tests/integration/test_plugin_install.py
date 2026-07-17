"""End-to-end: bash install.sh in a fake $HOME and assert the plugin
symlinks land in the expected layout."""

from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
from pathlib import Path


def _install_fake_codex(fake_home: Path) -> Path:
    cli = fake_home / ".local" / "bin" / "codex"
    cli.parent.mkdir(parents=True, exist_ok=True)
    cli.write_text(
        """#!/usr/bin/env bash
set -eu
case "$*" in
  "--version") echo "codex-cli test" ;;
  "plugin add renmark@personal --json")
    touch "$HOME/.codex-renmark-installed"
    echo '{"pluginId":"renmark@personal"}'
    ;;
  "plugin remove renmark@personal")
    rm -f "$HOME/.codex-renmark-installed"
    ;;
  "plugin list --json")
    if [[ -f "$HOME/.codex-renmark-installed" ]]; then
      echo '{"installed":[{"pluginId":"renmark@personal","installed":true,"enabled":true}]}'
    else
      echo '{"installed":[]}'
    fi
    ;;
  *) exit 2 ;;
esac
"""
    )
    cli.chmod(0o755)
    return cli


def _install_failing_doctor_python(fake_home: Path) -> Path:
    """Proxy python3, but make the installer's doctor repair fail."""
    cli = fake_home / ".local" / "bin" / "python3"
    cli.write_text(
        f"""#!/usr/bin/env bash
if [[ "$*" == *"-m renmark.doctor"* ]]; then
  echo "simulated doctor failure" >&2
  exit 17
fi
exec {shlex.quote(sys.executable)} "$@"
"""
    )
    cli.chmod(0o755)
    return cli


def test_install_sh_creates_symlinks(repo_root: Path, tmp_path: Path):
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    fake_local_bin = fake_home / ".local" / "bin"
    fake_local_bin.mkdir(parents=True)
    _install_fake_codex(fake_home)

    env = os.environ.copy()
    env["HOME"] = str(fake_home)
    env["PATH"] = f"{fake_local_bin}:{env['PATH']}"

    result = subprocess.run(
        ["bash", str(repo_root / "install.sh")],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, f"install.sh failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"

    plugin_link = fake_home / ".claude" / "plugins" / "renmark"
    codex_plugin_link = fake_home / "plugins" / "renmark"
    cli_link = fake_local_bin / "renmark-execute"
    assert plugin_link.is_symlink(), f"missing plugin symlink at {plugin_link}"
    assert cli_link.is_symlink(), f"missing cli symlink at {cli_link}"
    assert plugin_link.resolve() == (repo_root / "plugin").resolve()
    assert codex_plugin_link.is_dir(), f"missing staged Codex plugin at {codex_plugin_link}"
    assert not codex_plugin_link.is_symlink()
    codex_manifest = json.loads((codex_plugin_link / ".codex-plugin" / "plugin.json").read_text())
    expected_version = (repo_root / "VERSION").read_text().strip()
    assert codex_manifest["version"].startswith(f"{expected_version}+codex.local.")
    assert cli_link.resolve() == (repo_root / "bin" / "renmark-execute").resolve()
    cache_path = (
        fake_home
        / ".claude"
        / "plugins"
        / "cache"
        / "renmark-local"
        / "renmark"
        / expected_version
    )
    assert cache_path.is_symlink(), f"missing Claude cache install at {cache_path}"
    assert cache_path.resolve() == (repo_root / "plugin").resolve()
    installed = json.loads(
        (fake_home / ".claude" / "plugins" / "installed_plugins.json").read_text()
    )
    install_path = Path(installed["plugins"]["renmark@renmark-local"][0]["installPath"])
    assert install_path.exists(), f"Claude registry points to missing path {install_path}"
    marketplace = json.loads((fake_home / ".agents" / "plugins" / "marketplace.json").read_text())
    renmark_entry = next(entry for entry in marketplace["plugins"] if entry["name"] == "renmark")
    assert renmark_entry["source"] == {"source": "local", "path": "./plugins/renmark"}
    assert (fake_home / ".codex-renmark-installed").exists()


def test_install_sh_fails_when_claude_registry_repair_fails(
    repo_root: Path, tmp_path: Path
):
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    fake_local_bin = fake_home / ".local" / "bin"
    fake_local_bin.mkdir(parents=True)
    _install_fake_codex(fake_home)
    _install_failing_doctor_python(fake_home)

    env = os.environ.copy()
    env["HOME"] = str(fake_home)
    env["PATH"] = f"{fake_local_bin}:{env['PATH']}"

    result = subprocess.run(
        ["bash", str(repo_root / "install.sh")],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode != 0
    assert "simulated doctor failure" in result.stderr


def test_install_sh_uninstall_cleans_up(repo_root: Path, tmp_path: Path):
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    fake_local_bin = fake_home / ".local" / "bin"
    fake_local_bin.mkdir(parents=True)
    _install_fake_codex(fake_home)

    env = os.environ.copy()
    env["HOME"] = str(fake_home)
    env["PATH"] = f"{fake_local_bin}:{env['PATH']}"

    subprocess.run(
        ["bash", str(repo_root / "install.sh")], env=env, capture_output=True, text=True, timeout=30, check=True
    )
    subprocess.run(
        ["bash", str(repo_root / "install.sh"), "--uninstall"],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    )

    assert not (fake_home / ".claude" / "plugins" / "renmark").exists()
    assert not (fake_home / "plugins" / "renmark").exists()
    assert not (fake_local_bin / "renmark-execute").exists()
    assert not (fake_home / ".codex-renmark-installed").exists()
    marketplace = json.loads((fake_home / ".agents" / "plugins" / "marketplace.json").read_text())
    assert all(entry.get("name") != "renmark" for entry in marketplace["plugins"])


def test_install_sh_idempotent(repo_root: Path, tmp_path: Path):
    """Running install.sh twice must not fail or create duplicate links."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    (fake_home / ".local" / "bin").mkdir(parents=True)
    _install_fake_codex(fake_home)
    env = os.environ.copy()
    env["HOME"] = str(fake_home)
    env["PATH"] = f"{fake_home / '.local' / 'bin'}:{env['PATH']}"

    for run in range(2):
        result = subprocess.run(
            ["bash", str(repo_root / "install.sh")],
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, f"install run #{run + 1} failed: {result.stderr}"


def test_plugin_has_required_skill_files(repo_root: Path):
    """A deployed plugin must ship every documented skill with a SKILL.md.

    The pinned roster below is the full command set shipped at this
    release; `.shared/` and `CONTRIBUTING.md` are reference files, not skills,
    and are excluded. Adding a skill means adding it here AND to the lifecycle
    registries — `tests/test_lifecycle.py` enforces exact registry⇄dir parity.
    """
    skills_dir = repo_root / "plugin" / "skills"
    required = {
        "start",
        "setup",
        "brainstorm",
        "plan",
        "check-plan",
        "orchestrate",
        "verify",
        "finish",
        "feature",
        "debug",
        "codereview",
        "roadmap",
        "help",
        "resume",
        "prd",
        "blueprint",
        "loop",
        "backlog",
        "doctor",
        "hygiene",
        "init",
        "analytics",
        "usage",
        "approve",
        "audit",
        "inventory",
        "eval",
        "guide",
        "scan",
        "heartbeat",
    }
    actual = {
        p.name
        for p in skills_dir.iterdir()
        if p.is_dir() and not p.name.startswith(("_", "."))
    }
    missing = required - actual
    assert not missing, f"missing skill directories: {missing}"
    extra = actual - required
    assert not extra, f"undocumented skill directories (add to pinned roster): {extra}"
    for name in required:
        assert (skills_dir / name / "SKILL.md").exists(), f"missing SKILL.md for {name}"


def test_shared_plugin_root_has_synchronized_host_manifests(repo_root: Path):
    plugin_root = repo_root / "plugin"
    claude = json.loads((plugin_root / ".claude-plugin" / "plugin.json").read_text())
    codex = json.loads((plugin_root / ".codex-plugin" / "plugin.json").read_text())

    assert claude["name"] == codex["name"] == "renmark"
    assert claude["version"] == codex["version"] == (repo_root / "VERSION").read_text().strip()
    assert not (repo_root / ".codex-plugin" / "plugin.json").exists()
    assert codex["skills"] == "./skills/"


def test_commands_directory_complete(repo_root: Path):
    """The commands/ shim layer must mirror skills/ exactly."""
    skills_dir = repo_root / "plugin" / "skills"
    commands_dir = repo_root / "plugin" / "commands"
    # Hidden/support dirs (e.g. .shared/) hold shared contract docs, not
    # skills — they have no command shim and are excluded from the parity check.
    skill_names = {
        p.name
        for p in skills_dir.iterdir()
        if p.is_dir() and not p.name.startswith(("_", "."))
    }
    command_names = {p.stem for p in commands_dir.glob("*.md")}
    assert skill_names == command_names, (
        f"skills/ vs commands/ mismatch:\n"
        f"  in skills not commands: {skill_names - command_names}\n"
        f"  in commands not skills: {command_names - skill_names}"
    )

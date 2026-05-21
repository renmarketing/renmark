"""End-to-end: bash install.sh in a fake $HOME and assert the plugin
symlinks land in the expected layout."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest


def test_install_sh_creates_symlinks(repo_root: Path, tmp_path: Path):
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    fake_local_bin = fake_home / ".local" / "bin"
    fake_local_bin.mkdir(parents=True)

    env = os.environ.copy()
    env["HOME"] = str(fake_home)
    env["PATH"] = f"{fake_local_bin}:{env['PATH']}"

    result = subprocess.run(
        ["bash", str(repo_root / "install.sh")],
        env=env, capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, (
        f"install.sh failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )

    plugin_link = fake_home / ".claude" / "plugins" / "renmark"
    cli_link = fake_local_bin / "renmark-execute"
    assert plugin_link.is_symlink(), f"missing plugin symlink at {plugin_link}"
    assert cli_link.is_symlink(), f"missing cli symlink at {cli_link}"
    assert plugin_link.resolve() == (repo_root / "plugin").resolve()
    assert cli_link.resolve() == (repo_root / "bin" / "renmark-execute").resolve()


def test_install_sh_uninstall_cleans_up(repo_root: Path, tmp_path: Path):
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    fake_local_bin = fake_home / ".local" / "bin"
    fake_local_bin.mkdir(parents=True)

    env = os.environ.copy()
    env["HOME"] = str(fake_home)
    env["PATH"] = f"{fake_local_bin}:{env['PATH']}"

    subprocess.run(["bash", str(repo_root / "install.sh")],
                   env=env, capture_output=True, text=True, timeout=30, check=True)
    subprocess.run(["bash", str(repo_root / "install.sh"), "--uninstall"],
                   env=env, capture_output=True, text=True, timeout=30, check=True)

    assert not (fake_home / ".claude" / "plugins" / "renmark").exists()
    assert not (fake_local_bin / "renmark-execute").exists()


def test_install_sh_idempotent(repo_root: Path, tmp_path: Path):
    """Running install.sh twice must not fail or create duplicate links."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    (fake_home / ".local" / "bin").mkdir(parents=True)
    env = os.environ.copy()
    env["HOME"] = str(fake_home)

    for run in range(2):
        result = subprocess.run(
            ["bash", str(repo_root / "install.sh")],
            env=env, capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 0, f"install run #{run+1} failed: {result.stderr}"


def test_plugin_has_required_skill_files(repo_root: Path):
    """A deployed plugin must have all 14 documented skills with SKILL.md."""
    skills_dir = repo_root / "plugin" / "skills"
    required = {
        "start", "setup", "brainstorm", "plan", "check-plan", "orchestrate",
        "verify", "finish", "feature", "debug", "codereview", "roadmap",
        "help", "resume",
    }
    actual = {p.name for p in skills_dir.iterdir() if p.is_dir()}
    missing = required - actual
    assert not missing, f"missing skill directories: {missing}"
    for name in required:
        assert (skills_dir / name / "SKILL.md").exists(), f"missing SKILL.md for {name}"


def test_commands_directory_complete(repo_root: Path):
    """The commands/ shim layer must mirror skills/ exactly."""
    skills_dir = repo_root / "plugin" / "skills"
    commands_dir = repo_root / "plugin" / "commands"
    skill_names = {p.name for p in skills_dir.iterdir() if p.is_dir()}
    command_names = {p.stem for p in commands_dir.glob("*.md")}
    assert skill_names == command_names, (
        f"skills/ vs commands/ mismatch:\n"
        f"  in skills not commands: {skill_names - command_names}\n"
        f"  in commands not skills: {command_names - skill_names}"
    )

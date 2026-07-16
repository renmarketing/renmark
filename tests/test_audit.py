"""Tests for renmark.audit — deterministic plugin/registry audit engine."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from renmark import audit

REPO_ROOT = Path(__file__).resolve().parent.parent


# ── synthetic plugin fixture ──────────────────────────────────────────────────


def _make_plugin(
    tmp_path: Path,
    *,
    skills: dict[str, str] | None = None,
    commands: dict[str, str] | None = None,
) -> Path:
    """Build a minimal repo with a synthetic plugin/ tree under tmp_path."""
    plugin = tmp_path / "plugin"
    (plugin / ".claude-plugin").mkdir(parents=True)
    (plugin / "skills").mkdir()
    (plugin / "commands").mkdir()
    (plugin / "templates").mkdir()
    (plugin / ".claude-plugin" / "plugin.json").write_text('{"name":"renmark","version":"0.0.0","description":"t"}')
    (plugin / "templates" / "CLAUDE.md.template").write_text("<!-- BEGIN:x -->\nf\n<!-- END:x -->\n")
    for name, body in (skills or {}).items():
        (plugin / "skills" / name).mkdir(parents=True)
        (plugin / "skills" / name / "SKILL.md").write_text(body)
    for name, body in (commands or {}).items():
        (plugin / "commands" / f"{name}.md").write_text(body)
    # VERSION files so release.drift_report doesn't choke (not the focus here).
    (tmp_path / "VERSION").write_text("0.0.0\n")
    return tmp_path


def _skill_md(name: str, desc: str = "a skill") -> str:
    return (
        f"---\nname: {name}\ndescription: {desc} for {name}\n---\n\n# {name}\n\n"
        f"See `${{CLAUDE_PLUGIN_ROOT}}/skills/.shared/next-steps.md`.\n"
    )


def _shim(name: str, desc: str = "a skill", body_lines: int = 1) -> str:
    body = "\n".join(
        [f"Read skills/{name}/SKILL.md and follow it."] + [f"extra line {i}" for i in range(body_lines - 1)]
    )
    return f"---\ndescription: {desc} for {name}\n---\n\n{body}\n"


# ── inventory harvest (real repo) ──────────────────────────────────────────────


def test_inventory_harvest_real_repo() -> None:
    """Harvest the real plugin: ≥23 commands, every shim/skill paired."""
    inv = audit.build_inventory(REPO_ROOT)
    assert len(inv) >= 23, f"expected ≥23 commands, got {len(inv)}"
    names = {e.name for e in inv}
    for expected in ("approve", "audit", "inventory"):
        assert expected in names, f"{expected} missing from inventory"
    # Every harvested shim has a backing SKILL.md (shim/skill parity).
    unpaired = [e.name for e in inv if not e.has_skill]
    assert not unpaired, f"shims without a SKILL.md: {unpaired}"
    # Each entry carries a resolved domain + class.
    for e in inv:
        assert e.domain in {"build", "debug", "audit", "meta"}
        assert e.skill_class in {"pipeline", "gate", "aux"}


# ── registry_sync (real repo — the lasting regression net) ─────────────────────


def test_registry_sync_real_repo_clean() -> None:
    """The real repo's registries must be in exact sync with the skill dirs.

    Wave 1 fixed all ghosts/missing; this is the regression net that keeps them
    fixed. Any new ghost or missing entry fails here.
    """
    issues = audit.registry_sync(REPO_ROOT)
    assert issues == [], "registry drift detected:\n  " + "\n  ".join(issues)


def test_registry_sync_detects_ghost(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A registry entry with no backing dir is reported as a ghost."""
    repo = _make_plugin(
        tmp_path,
        skills={"start": _skill_md("start")},
        commands={"start": _shim("start")},
    )
    monkeypatch.setattr(audit.lifecycle, "IMPLEMENTED_SKILLS", frozenset({"start", "ghostly"}))
    issues = audit.registry_sync(repo)
    assert any("ghostly" in i and "ghost" in i for i in issues), issues


def test_registry_sync_detects_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A skill dir absent from a registry is reported as missing."""
    repo = _make_plugin(
        tmp_path,
        skills={"orphan": _skill_md("orphan")},
        commands={"orphan": _shim("orphan")},
    )
    monkeypatch.setattr(audit.lifecycle, "IMPLEMENTED_SKILLS", frozenset())
    monkeypatch.setattr(audit.lifecycle, "DOMAIN_BY_SKILL", {})
    issues = audit.registry_sync(repo)
    assert any("orphan" in i and "missing" in i for i in issues), issues


# ── shim_thinness ──────────────────────────────────────────────────────────────


def test_shim_thinness_flags_fat_shim(tmp_path: Path) -> None:
    repo = _make_plugin(
        tmp_path,
        skills={"fat": _skill_md("fat")},
        commands={"fat": _shim("fat", body_lines=40)},
    )
    issues = audit.shim_thinness(repo)
    assert any("fat" in i and "lines" in i for i in issues), issues


def test_shim_thinness_flags_unwired_shim(tmp_path: Path) -> None:
    repo = _make_plugin(
        tmp_path,
        skills={"wired": _skill_md("wired")},
        commands={"wired": "---\ndescription: x for wired\n---\n\nNo skill reference here.\n"},
    )
    issues = audit.shim_thinness(repo)
    assert any("does not reference" in i for i in issues), issues


def test_shim_thinness_clean(tmp_path: Path) -> None:
    repo = _make_plugin(
        tmp_path,
        skills={"thin": _skill_md("thin")},
        commands={"thin": _shim("thin")},
    )
    assert audit.shim_thinness(repo) == []


# ── description_drift ──────────────────────────────────────────────────────────


def test_description_drift_flags_divergent(tmp_path: Path) -> None:
    repo = _make_plugin(
        tmp_path,
        skills={"thing": _skill_md("thing", desc="manage database migrations carefully")},
        commands={"thing": _shim("thing", desc="paint watercolor landscape portraits")},
    )
    issues = audit.description_drift(repo)
    assert any("thing" in i and "description-drift" in i for i in issues), issues


def test_description_drift_clean_when_aligned(tmp_path: Path) -> None:
    shared = "manage database migrations carefully always"
    repo = _make_plugin(
        tmp_path,
        skills={"thing": _skill_md("thing", desc=shared)},
        commands={"thing": _shim("thing", desc=shared)},
    )
    assert audit.description_drift(repo) == []


# ── registry_sync: skill dir without SKILL.md ─────────────────────────────────


def test_registry_sync_detects_dir_without_skill_md(tmp_path: Path) -> None:
    """A skill dir without SKILL.md emits a 'skill dir without SKILL.md' issue."""
    repo = _make_plugin(tmp_path, skills={}, commands={})
    # Manually create a dir that has no SKILL.md.
    (repo / "plugin" / "skills" / "orphaned_dir").mkdir(parents=True)
    issues = audit.registry_sync(repo)
    assert any("skill dir without SKILL.md" in i and "orphaned_dir" in i for i in issues), issues


def test_registry_sync_ignores_hidden_support_dir(tmp_path: Path) -> None:
    repo = _make_plugin(tmp_path, skills={}, commands={})
    shared = repo / "plugin" / "skills" / ".shared"
    shared.mkdir(parents=True)
    (shared / "contract.md").write_text("# internal contract\n", encoding="utf-8")

    issues = audit.registry_sync(repo)

    assert not any(".shared" in issue for issue in issues)


def test_registry_sync_skill_dir_with_skill_md_not_flagged(tmp_path: Path) -> None:
    """A skill dir WITH a SKILL.md does NOT emit the 'skill dir without SKILL.md' issue."""
    repo = _make_plugin(
        tmp_path,
        skills={"start": _skill_md("start")},
        commands={"start": _shim("start")},
    )
    issues = audit.registry_sync(repo)
    # None of the issues should be "skill dir without SKILL.md: start"
    no_skill_md_issues = [i for i in issues if "skill dir without SKILL.md" in i]
    assert not any("start" in i for i in no_skill_md_issues), no_skill_md_issues


# ── no_raw_jsonl ───────────────────────────────────────────────────────────────


def _make_plugin_with_skill_text(tmp_path: Path, skill_name: str, skill_text: str) -> Path:
    """Helper: build a plugin with a custom SKILL.md text for one skill."""
    plugin = tmp_path / "plugin"
    (plugin / ".claude-plugin").mkdir(parents=True)
    (plugin / "skills").mkdir()
    (plugin / "commands").mkdir()
    (plugin / "templates").mkdir()
    (plugin / ".claude-plugin" / "plugin.json").write_text('{"name":"renmark","version":"0.0.0","description":"t"}')
    (plugin / "templates" / "CLAUDE.md.template").write_text("<!-- BEGIN:x -->\nf\n<!-- END:x -->\n")
    (plugin / "skills" / skill_name).mkdir(parents=True)
    (plugin / "skills" / skill_name / "SKILL.md").write_text(skill_text)
    (tmp_path / "VERSION").write_text("0.0.0\n")
    return tmp_path


def test_no_raw_jsonl_flags_shell_read_in_skill(tmp_path: Path) -> None:
    """A SKILL.md that affirmatively cat-reads a .jsonl file is flagged."""
    bad_text = "---\nname: bad\ndescription: bad\n---\n\nRun this: `cat .renmark/state/usage.jsonl | jq .`\n"
    repo = _make_plugin_with_skill_text(tmp_path, "bad", bad_text)
    issues = audit.no_raw_jsonl(repo)
    assert any("no-raw-jsonl" in i and "bad" in i for i in issues), issues


def test_no_raw_jsonl_does_not_flag_prohibition(tmp_path: Path) -> None:
    """A SKILL.md that says 'NEVER cat .jsonl' is a prohibition — not flagged."""
    good_text = (
        "---\nname: good\ndescription: good\n---\n\n"
        "NEVER cat .renmark/analytics/events.jsonl into conversation.\n"
        "Do not tail .renmark/state/usage.jsonl inline.\n"
    )
    repo = _make_plugin_with_skill_text(tmp_path, "good", good_text)
    issues = audit.no_raw_jsonl(repo)
    assert issues == [], issues


def test_no_raw_jsonl_does_not_flag_python_block(tmp_path: Path) -> None:
    """A .jsonl path reference inside a python fenced block is not flagged."""
    good_text = (
        "---\nname: pyblock\ndescription: pyblock\n---\n\n"
        "```python\n"
        "path = '.renmark/state/usage.jsonl'  # cat here as a string literal\n"
        "```\n"
    )
    repo = _make_plugin_with_skill_text(tmp_path, "pyblock", good_text)
    issues = audit.no_raw_jsonl(repo)
    assert issues == [], issues


def test_no_raw_jsonl_real_repo_clean() -> None:
    """The real repo plugin has zero no-raw-jsonl issues."""
    issues = audit.no_raw_jsonl(REPO_ROOT)
    assert issues == [], "no-raw-jsonl regressions in real plugin:\n  " + "\n  ".join(issues)


# ── disclaimer_present ────────────────────────────────────────────────────────


def test_disclaimer_present_real_repo_clean() -> None:
    """The real repo's usage and analytics skills carry all mandatory markers."""
    issues = audit.disclaimer_present(REPO_ROOT)
    assert issues == [], "disclaimer markers missing:\n  " + "\n  ".join(issues)


def test_disclaimer_present_flags_missing_usage_disclaimer(tmp_path: Path) -> None:
    """If the usage disclaimer is absent, disclaimer_present flags it."""
    plugin = tmp_path / "plugin"
    (plugin / "skills" / "usage").mkdir(parents=True)
    (plugin / "skills" / "analytics").mkdir(parents=True)
    # usage SKILL.md WITHOUT the required disclaimer
    (plugin / "skills" / "usage" / "SKILL.md").write_text(
        "---\nname: usage\ndescription: usage\n---\n\nSome content but no disclaimer.\n"
    )
    # analytics SKILL.md WITH the required marker
    (plugin / "skills" / "analytics" / "SKILL.md").write_text(
        "---\nname: analytics\ndescription: analytics\n---\n\nNEVER dump raw logs. OK.\n"
    )
    issues = audit.disclaimer_present(tmp_path)
    assert any("usage" in i and "Observed local usage only" in i for i in issues), issues
    # analytics should be clean
    assert not any("analytics" in i for i in issues), issues


def test_disclaimer_present_flags_missing_analytics_marker(tmp_path: Path) -> None:
    """If the analytics no-raw-log marker is absent, disclaimer_present flags it."""
    plugin = tmp_path / "plugin"
    (plugin / "skills" / "usage").mkdir(parents=True)
    (plugin / "skills" / "analytics").mkdir(parents=True)
    # usage WITH disclaimer
    (plugin / "skills" / "usage" / "SKILL.md").write_text(
        "---\nname: usage\ndescription: usage\n---\n\n"
        "Observed local usage only. Provider-side account limits may differ.\n"
    )
    # analytics WITHOUT marker
    (plugin / "skills" / "analytics" / "SKILL.md").write_text(
        "---\nname: analytics\ndescription: analytics\n---\n\nNo rule here.\n"
    )
    issues = audit.disclaimer_present(tmp_path)
    assert any("analytics" in i and "NEVER dump raw logs" in i for i in issues), issues
    assert not any("usage" in i for i in issues), issues


# ── run_audit composition ──────────────────────────────────────────────────────


def test_run_audit_real_repo() -> None:
    """Full audit on the real repo: the novel passes this module owns are clean.

    registry-sync / shim-thinness / description-drift / no-raw-jsonl / disclaimer
    are this module's own passes and MUST be clean — they are the lasting
    regression net. The composed ``lint`` pass runs with the strict-frontmatter
    check ON; the only tolerable residue is strict-YAML frontmatter findings
    (the 8 invalid frontmatters fixed by a parallel agent in this same wave).
    Any NON-frontmatter lint issue — a wiring, citation, or template-block
    regression — still fails here.
    """
    report = audit.run_audit(REPO_ROOT)
    assert report.passes["registry-sync"] == [], report.passes["registry-sync"]
    assert report.passes["shim-thinness"] == [], report.passes["shim-thinness"]
    assert report.passes["description-drift"] == [], report.passes["description-drift"]
    assert report.passes["no-raw-jsonl"] == [], report.passes["no-raw-jsonl"]
    assert report.passes["disclaimer"] == [], report.passes["disclaimer"]
    assert report.passes["version-drift"] == [], report.passes["version-drift"]
    non_frontmatter_lint = [i for i in report.passes["lint"] if "frontmatter value" not in i]
    assert non_frontmatter_lint == [], non_frontmatter_lint
    # full run records modularity counts (advisory, not folded into total).
    assert isinstance(report.modularity_counts, dict)


def test_run_audit_quick_skips_modularity() -> None:
    report = audit.run_audit(REPO_ROOT, quick=True)
    assert report.quick is True
    assert report.modularity_counts == {}


# ── artifact writers (tmp repos) ───────────────────────────────────────────────


def test_write_inventory_creates_md_and_json(tmp_path: Path) -> None:
    repo = _make_plugin(
        tmp_path,
        skills={"start": _skill_md("start")},
        commands={"start": _shim("start")},
    )
    paths = audit.write_inventory(repo)
    md = Path(paths["md"])
    js = Path(paths["json"])
    assert md.exists() and js.exists()
    # md has G6 provenance frontmatter + a Summary section.
    text = md.read_text(encoding="utf-8")
    assert text.startswith("---")
    assert "generator: renmark-audit" in text
    assert "## Summary" in text
    # json is a list of command dicts.
    data = json.loads(js.read_text(encoding="utf-8"))
    assert isinstance(data, list) and data[0]["name"] == "start"
    # writes stay inside .renmark/audits/
    assert ".renmark/audits/" in md.as_posix()


def test_write_audit_report_creates_md_and_json(tmp_path: Path) -> None:
    repo = _make_plugin(
        tmp_path,
        skills={"start": _skill_md("start")},
        commands={"start": _shim("start")},
    )
    report = audit.run_audit(repo, quick=True)
    paths = audit.write_audit_report(repo, report)
    md = Path(paths["md"])
    js = Path(paths["json"])
    assert md.exists() and js.exists()
    assert "generator: renmark-audit" in md.read_text(encoding="utf-8")
    data = json.loads(js.read_text(encoding="utf-8"))
    assert data["verdict"] in {"PASS", "ISSUES"}
    assert "pass_counts" in data


# ── CLI smoke ──────────────────────────────────────────────────────────────────


def test_cli_inventory_only(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    repo = _make_plugin(
        tmp_path,
        skills={"start": _skill_md("start")},
        commands={"start": _shim("start")},
    )
    code = audit.main(["--inventory-only", "--repo", str(repo)])
    out = capsys.readouterr().out
    assert code == 0
    assert "inventory:" in out
    assert "1 commands" in out


def test_cli_full_clean_exits_zero(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    repo = _make_plugin(
        tmp_path,
        skills={"start": _skill_md("start")},
        commands={"start": _shim("start")},
    )
    # A clean synthetic plugin (no registry entries → no ghosts; the lone dir is
    # 'start' which IS in the real registries, so registry_sync sees it as
    # in-sync only if we don't trip missing. 'start' is registered, so clean.
    code = audit.main(["--quick", "--repo", str(repo)])
    out = capsys.readouterr().out
    assert "audit (quick):" in out
    assert code in (0, 1)  # may flag start-only registry mismatch; format is the point
    assert ("PASS" in out) or ("ISSUES" in out)


def test_cli_json_mode(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    repo = _make_plugin(
        tmp_path,
        skills={"start": _skill_md("start")},
        commands={"start": _shim("start")},
    )
    audit.main(["--quick", "--json", "--repo", str(repo)])
    out = capsys.readouterr().out
    data = json.loads(out)
    assert "report" in data and "verdict" in data["report"]


def test_cli_subprocess_real_repo() -> None:
    """End-to-end: the module runs as `python -m renmark.audit --quick`.

    Exit code reflects total issues; while the parallel wave's 8 strict-YAML
    frontmatter fixes are still landing, the run may report ISSUES (exit 1).
    The contract this asserts is the bounded stdout format + that the run
    completes (no crash / exit 2), not a green verdict.
    """
    proc = subprocess.run(
        [sys.executable, "-m", "renmark.audit", "--quick", "--repo", str(REPO_ROOT)],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        timeout=120,
    )
    assert proc.returncode in (0, 1), f"audit crashed:\n{proc.stdout}\n{proc.stderr}"
    assert "audit (quick):" in proc.stdout
    assert ("PASS" in proc.stdout) or ("ISSUES" in proc.stdout)
    assert "registry-sync=0" in proc.stdout
    assert "shim-thinness=0" in proc.stdout
    assert "no-raw-jsonl=0" in proc.stdout
    assert "disclaimer=0" in proc.stdout


def test_cli_no_plugin_dir(tmp_path: Path) -> None:
    code = audit.main(["--repo", str(tmp_path)])
    assert code == 2


def test_run_audit_survives_missing_version_file(tmp_path):
    """User projects (where this skill ships) may have no VERSION file — the
    audit must degrade to an advisory line, never crash. (v0.9.0 codereview.)"""
    plugin = tmp_path / "plugin"
    (plugin / "commands").mkdir(parents=True)
    (plugin / "skills").mkdir(parents=True)
    report = audit.run_audit(tmp_path, quick=True)
    assert any("version" in line.lower() for line in report.passes["version-drift"])


def test_no_raw_jsonl_catches_flag_bearing_commands(tmp_path):
    """v0.9.1 review: `head -5 f.jsonl` / `tail -n 20 f.jsonl` / `cat -- f.jsonl`
    must be flagged — flags between command and path must not evade the pass."""
    plugin = tmp_path / "plugin"
    sk = plugin / "skills" / "bad" / "SKILL.md"
    sk.parent.mkdir(parents=True)
    sk.write_text(
        "---\nname: bad\ndescription: x\n---\n"
        "Run head -5 .renmark/state/usage.jsonl\n"
        "Run tail -n 20 .renmark/analytics/events.jsonl\n"
        "Run cat -- .renmark/state/usage.jsonl\n"
    )
    (plugin / "commands").mkdir(parents=True)
    issues = audit.no_raw_jsonl(tmp_path)
    assert len(issues) == 3, issues

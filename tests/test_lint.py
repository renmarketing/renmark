"""Tests for renmark.lint — plugin contract linter."""
from __future__ import annotations

from pathlib import Path

import pytest

from renmark import lint

# ── frontmatter ──────────────────────────────────────────────────────────────


def test_parse_frontmatter_extracts_simple_kv():
    text = "---\nname: foo\ndescription: bar baz\n---\n\nbody"
    assert lint.parse_frontmatter(text) == {"name": "foo", "description": "bar baz"}


def test_parse_frontmatter_strips_quotes():
    text = "---\nname: 'foo'\nhint: \"bar\"\n---\n"
    fm = lint.parse_frontmatter(text)
    assert fm == {"name": "foo", "hint": "bar"}


def test_parse_frontmatter_returns_none_without_block():
    assert lint.parse_frontmatter("just a body") is None


def test_parse_frontmatter_ignores_comments_and_blanks():
    text = "---\n# a comment\nname: foo\n\ndescription: bar\n---\n"
    assert lint.parse_frontmatter(text) == {"name": "foo", "description": "bar"}


# ── plugin fixture builder ───────────────────────────────────────────────────


def _make_plugin(tmp_path: Path, *, skills: dict[str, str] | None = None,
                 commands: dict[str, str] | None = None,
                 plugin_json: str | None = None,
                 template: str | None = None) -> Path:
    """Build a synthetic plugin/ directory for testing."""
    plugin_dir = tmp_path / "plugin"
    (plugin_dir / ".claude-plugin").mkdir(parents=True)
    (plugin_dir / "skills").mkdir()
    (plugin_dir / "commands").mkdir()
    (plugin_dir / "templates").mkdir()

    (plugin_dir / ".claude-plugin" / "plugin.json").write_text(
        plugin_json if plugin_json is not None else
        '{"name":"renmark","version":"0.3.1","description":"test"}'
    )

    for name, body in (skills or {}).items():
        (plugin_dir / "skills" / name).mkdir(parents=True)
        (plugin_dir / "skills" / name / "SKILL.md").write_text(body)

    for name, body in (commands or {}).items():
        (plugin_dir / "commands" / f"{name}.md").write_text(body)

    (plugin_dir / "templates" / "CLAUDE.md.template").write_text(
        template if template is not None else
        "<!-- BEGIN:demo-rule -->\nfoo\n<!-- END:demo-rule -->\n"
    )
    return plugin_dir


def _valid_skill_md(name: str) -> str:
    # A fully-compliant skill cites the shared hand-off contract (lint_next_steps_citation).
    return (
        f"---\nname: {name}\ndescription: a skill for {name}\n---\n\n# {name}\n\n"
        f"## What's next\nSee `${{CLAUDE_PLUGIN_ROOT}}/skills/_shared/next-steps.md`.\n"
    )


def _valid_command_md(name: str) -> str:
    return (
        f"---\ndescription: a skill for {name}\nargument-hint: '[shape]'\n---\n\n"
        f"Read ${{CLAUDE_PLUGIN_ROOT}}/skills/{name}/SKILL.md and follow its instructions.\n"
    )


# ── skill linter ─────────────────────────────────────────────────────────────


def test_lint_skill_files_passes_valid(tmp_path: Path):
    plugin = _make_plugin(tmp_path, skills={"start": _valid_skill_md("start")})
    assert lint.lint_skill_files(plugin) == []


def test_lint_skill_files_catches_missing_skill_md(tmp_path: Path):
    plugin = _make_plugin(tmp_path)
    (plugin / "skills" / "broken").mkdir()
    issues = lint.lint_skill_files(plugin)
    assert any("missing SKILL.md" in i for i in issues)


def test_lint_skill_files_catches_missing_frontmatter(tmp_path: Path):
    plugin = _make_plugin(tmp_path, skills={"naked": "no frontmatter here"})
    issues = lint.lint_skill_files(plugin)
    assert any("missing YAML frontmatter" in i for i in issues)


def test_lint_skill_files_catches_name_mismatch(tmp_path: Path):
    plugin = _make_plugin(tmp_path, skills={"foo": _valid_skill_md("bar")})
    issues = lint.lint_skill_files(plugin)
    assert any("doesn't match directory" in i for i in issues)


def test_lint_skill_files_catches_missing_description(tmp_path: Path):
    body = "---\nname: foo\n---\n\n# foo\n"
    plugin = _make_plugin(tmp_path, skills={"foo": body})
    issues = lint.lint_skill_files(plugin)
    assert any("missing 'description'" in i for i in issues)


# ── command shim linter ──────────────────────────────────────────────────────


def test_lint_command_shims_passes_paired(tmp_path: Path):
    plugin = _make_plugin(
        tmp_path,
        skills={"start": _valid_skill_md("start")},
        commands={"start": _valid_command_md("start")},
    )
    assert lint.lint_command_shims(plugin) == []


def test_lint_command_shims_catches_command_without_skill(tmp_path: Path):
    plugin = _make_plugin(tmp_path, commands={"orphan": _valid_command_md("orphan")})
    issues = lint.lint_command_shims(plugin)
    assert any("no matching skills/orphan" in i for i in issues)


def test_lint_command_shims_catches_skill_without_command(tmp_path: Path):
    plugin = _make_plugin(tmp_path, skills={"unreachable": _valid_skill_md("unreachable")})
    issues = lint.lint_command_shims(plugin)
    assert any("unreachable" in i for i in issues)


def test_lint_ignores_underscore_shared_dirs(tmp_path: Path):
    """`_shared/` holds cross-skill reference files — not a skill, not orphaned.
    It must not trip 'missing SKILL.md' or 'unreachable' checks."""
    plugin = _make_plugin(tmp_path, skills={"start": _valid_skill_md("start")},
                          commands={"start": _valid_command_md("start")})
    shared = plugin / "skills" / "_shared"
    shared.mkdir()
    (shared / "scope-contract.md").write_text("# shared reference\n")
    assert lint.lint_skill_files(plugin) == []
    assert lint.lint_command_shims(plugin) == []


def test_lint_command_shims_catches_missing_skill_reference(tmp_path: Path):
    bad_command = (
        "---\ndescription: wrong\n---\n\n"
        "Read ${CLAUDE_PLUGIN_ROOT}/skills/elsewhere/SKILL.md — wrong target.\n"
    )
    plugin = _make_plugin(
        tmp_path,
        skills={"start": _valid_skill_md("start")},
        commands={"start": bad_command},
    )
    issues = lint.lint_command_shims(plugin)
    assert any("doesn't reference skills/start/SKILL.md" in i for i in issues)


# ── template rule-block linter ──────────────────────────────────────────────


def test_lint_template_passes_balanced(tmp_path: Path):
    template = (
        "<!-- BEGIN:foo -->\nbody\n<!-- END:foo -->\n\n"
        "<!-- BEGIN:bar -->\nx\n<!-- END:bar -->\n"
    )
    plugin = _make_plugin(tmp_path, template=template)
    issues = lint.lint_template_rule_blocks(plugin / "templates" / "CLAUDE.md.template")
    assert issues == []


def test_lint_template_catches_missing_end(tmp_path: Path):
    template = "<!-- BEGIN:foo -->\nbody\n"
    plugin = _make_plugin(tmp_path, template=template)
    issues = lint.lint_template_rule_blocks(plugin / "templates" / "CLAUDE.md.template")
    assert any("no matching END:foo" in i for i in issues)


def test_lint_template_catches_missing_begin(tmp_path: Path):
    template = "<!-- END:lonely -->\n"
    plugin = _make_plugin(tmp_path, template=template)
    issues = lint.lint_template_rule_blocks(plugin / "templates" / "CLAUDE.md.template")
    assert any("no matching BEGIN:lonely" in i for i in issues)


def test_lint_template_catches_duplicate_begin(tmp_path: Path):
    template = (
        "<!-- BEGIN:foo -->\na\n<!-- END:foo -->\n"
        "<!-- BEGIN:foo -->\nb\n<!-- END:foo -->\n"
    )
    plugin = _make_plugin(tmp_path, template=template)
    issues = lint.lint_template_rule_blocks(plugin / "templates" / "CLAUDE.md.template")
    assert any("appears" in i for i in issues)


def test_lint_template_catches_inverted_order(tmp_path: Path):
    template = "<!-- END:foo -->\n<!-- BEGIN:foo -->\n"
    plugin = _make_plugin(tmp_path, template=template)
    issues = lint.lint_template_rule_blocks(plugin / "templates" / "CLAUDE.md.template")
    assert any("precedes BEGIN" in i for i in issues)


def test_markers_ignore_bare_prose(tmp_path: Path):
    """Bare `BEGIN:name` / `END:name` in prose (not a full comment on its own
    line) is NOT a managed marker — the tightened regex only matches the
    `<!-- BEGIN:name -->` comment form."""
    template = (
        "Some prose mentioning BEGIN:example and END:example inline.\n"
        "<!-- BEGIN:real -->\nbody\n<!-- END:real -->\n"
    )
    plugin = _make_plugin(tmp_path, template=template)
    issues = lint.lint_template_rule_blocks(plugin / "templates" / "CLAUDE.md.template")
    # `example` must not be picked up as a marker → only the well-formed `real`
    # block exists, so no balance issues.
    assert issues == []
    blocks = {n for n, _ in lint.iter_rule_blocks(template)}
    assert blocks == {"real"}
    assert "example" not in blocks


# ── plugin.json linter ───────────────────────────────────────────────────────


def test_lint_plugin_json_catches_missing_fields(tmp_path: Path):
    plugin = _make_plugin(tmp_path, plugin_json='{"name":"renmark"}')
    issues = lint.lint_plugin_json(plugin)
    assert any("version" in i for i in issues)
    assert any("description" in i for i in issues)


def test_lint_plugin_json_catches_invalid_json(tmp_path: Path):
    plugin = _make_plugin(tmp_path, plugin_json="{not json")
    issues = lint.lint_plugin_json(plugin)
    assert any("invalid JSON" in i for i in issues)


# ── orchestration + CLI ──────────────────────────────────────────────────────


def test_lint_all_passes_clean_plugin(tmp_path: Path):
    plugin = _make_plugin(
        tmp_path,
        skills={"start": _valid_skill_md("start")},
        commands={"start": _valid_command_md("start")},
    )
    assert lint.lint_all(plugin) == []


def test_cli_passes_clean_plugin(tmp_path: Path, capsys):
    plugin = _make_plugin(
        tmp_path,
        skills={"start": _valid_skill_md("start")},
        commands={"start": _valid_command_md("start")},
    )
    exit_code = lint.main(["--plugin-dir", str(plugin)])
    assert exit_code == 0


def test_cli_fails_dirty_plugin(tmp_path: Path):
    plugin = _make_plugin(tmp_path, skills={"foo": "no frontmatter"})
    exit_code = lint.main(["--plugin-dir", str(plugin)])
    assert exit_code == 1


def test_cli_rejects_unknown_arg():
    exit_code = lint.main(["--bogus", "value"])
    assert exit_code == 2


def test_lints_real_renmark_plugin():
    """End-to-end: the actual renmark plugin must lint clean.

    If this fails, a real bug has crept into the plugin shipping config.
    """
    real_plugin = Path(__file__).resolve().parent.parent / "plugin"
    if not real_plugin.exists():
        pytest.skip("not running from repo root")
    issues = lint.lint_all(real_plugin)
    assert issues == [], "renmark plugin should lint clean:\n  " + "\n  ".join(issues)


# ── frontmatter-value strict pass ────────────────────────────────────────────


def _make_plugin_with_fm(tmp_path: Path, skill_fm_body: str, cmd_fm_body: str) -> Path:
    """Build a plugin with custom frontmatter for one skill and one command."""
    plugin = _make_plugin(
        tmp_path,
        skills={"myplugin": f"---\n{skill_fm_body}---\n\n# body\n\nSee next-steps.md.\n"},
        commands={"myplugin": f"---\n{cmd_fm_body}---\n\nRead skills/myplugin/SKILL.md.\n"},
    )
    return plugin


def test_lint_frontmatter_values_clean(tmp_path: Path) -> None:
    """Well-formed frontmatter passes the strict pass."""
    plugin = _make_plugin_with_fm(
        tmp_path,
        "name: myplugin\ndescription: A simple description\n",
        "description: A simple description\n",
    )
    issues = lint.lint_frontmatter_values(plugin)
    assert issues == []


def test_lint_frontmatter_values_flags_unquoted_colon_space(tmp_path: Path) -> None:
    """An unquoted value containing ': ' is flagged."""
    plugin = _make_plugin_with_fm(
        tmp_path,
        "name: myplugin\ndescription: foo: bar baz\n",
        "description: A simple description\n",
    )
    issues = lint.lint_frontmatter_values(plugin)
    assert any(": " in i and "unquoted" in i for i in issues), issues


def test_lint_frontmatter_values_quoted_value_ok(tmp_path: Path) -> None:
    """A value with ': ' that IS properly quoted passes."""
    plugin = _make_plugin_with_fm(
        tmp_path,
        'name: myplugin\ndescription: "foo: bar baz"\n',
        "description: A simple description\n",
    )
    issues = lint.lint_frontmatter_values(plugin)
    assert issues == []


def test_lint_all_strict_frontmatter_off_by_default(tmp_path: Path) -> None:
    """lint_all does NOT run the strict pass unless include_frontmatter_strict=True."""
    plugin = _make_plugin_with_fm(
        tmp_path,
        "name: myplugin\ndescription: foo: bar baz\n",
        "description: A simple description\n",
    )
    # Standard lint_all (strict off) should not report the colon-space issue
    issues_default = lint.lint_all(plugin)
    fm_issues = [i for i in issues_default if "unquoted" in i]
    assert fm_issues == [], "strict-frontmatter pass should be off by default"

    # With strict on, the issue appears
    issues_strict = lint.lint_all(plugin, include_frontmatter_strict=True)
    assert any("unquoted" in i for i in issues_strict)


def test_cli_strict_frontmatter_flag(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    """--strict-frontmatter CLI flag enables the strict pass."""
    plugin = _make_plugin(
        tmp_path,
        skills={"start": _valid_skill_md("start")},
        commands={"start": _valid_command_md("start")},
    )
    # Without flag: exit 0
    assert lint.main(["--plugin-dir", str(plugin)]) == 0
    # With flag and clean plugin: still exit 0
    assert lint.main(["--plugin-dir", str(plugin), "--strict-frontmatter"]) == 0


def test_lint_unreadable_skill_file(tmp_path: Path) -> None:
    """An unreadable SKILL.md is reported as an issue, not a crash."""
    import os
    plugin = _make_plugin(tmp_path, skills={"myskill": _valid_skill_md("myskill")},
                          commands={"myskill": _valid_command_md("myskill")})
    skill_md = plugin / "skills" / "myskill" / "SKILL.md"
    # Make the file unreadable
    os.chmod(str(skill_md), 0o000)
    try:
        issues = lint.lint_skill_files(plugin)
        # Should report something about unreadable, not crash
        assert any("unreadable" in i or "myskill" in i for i in issues)
    finally:
        os.chmod(str(skill_md), 0o644)

"""Plugin contract linter — checks that SKILL.md files, command shims, and
CLAUDE.md.template rule blocks are well-formed.

Catches the cheap mistakes early so they don't ship in a release:
    - SKILL.md without proper frontmatter (name, description)
    - commands/<name>.md without a matching skills/<name>/SKILL.md (and vice versa)
    - frontmatter description present but empty
    - CLAUDE.md.template with unbalanced BEGIN: / END: markers
    - SKILL.md frontmatter ``name:`` mismatching its directory

CLI:
    python -m renmark.lint [--plugin-dir DIR] [--template DIR]

Exit code 0 = clean, 1 = issues found, 2 = bad CLI usage.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

# ── Frontmatter parsing (zero-dep mini-YAML) ─────────────────────────────────

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?\n)---\s*\n", re.DOTALL)
_KV_RE = re.compile(r"^([a-zA-Z][a-zA-Z0-9_-]*):\s*(.*)$")


def parse_frontmatter(text: str) -> dict[str, Any] | None:
    """Extract a top-level YAML frontmatter block as a dict. Returns None if
    no frontmatter is present. Only handles the flat key:value form — that
    is the entire Claude Code SKILL.md / command convention.
    """
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return None
    body = match.group(1)
    out: dict[str, str] = {}
    for raw_line in body.splitlines():
        line = raw_line.rstrip()
        if not line or line.startswith("#"):
            continue
        m = _KV_RE.match(line)
        if m:
            key, value = m.group(1), m.group(2).strip()
            # Strip wrapping quotes if any.
            if (value.startswith("'") and value.endswith("'")) or (value.startswith('"') and value.endswith('"')):
                value = value[1:-1]
            out[key] = value
    return out


# ── Lint passes ──────────────────────────────────────────────────────────────


def lint_skill_files(plugin_dir: Path) -> list[str]:
    """Verify every skills/<name>/SKILL.md has valid frontmatter."""
    issues: list[str] = []
    skills_dir = plugin_dir / "skills"
    if not skills_dir.is_dir():
        return [f"plugin: missing skills/ directory at {skills_dir}"]

    for skill_path in sorted(skills_dir.iterdir()):
        if not skill_path.is_dir():
            continue
        # Underscore-prefixed dirs (e.g. _shared/) hold cross-skill reference
        # files, not skills — they have no SKILL.md and no paired command.
        if skill_path.name.startswith("_"):
            continue
        skill_md = skill_path / "SKILL.md"
        if not skill_md.exists():
            issues.append(f"skills/{skill_path.name}/: missing SKILL.md")
            continue
        text = skill_md.read_text(encoding="utf-8")
        fm = parse_frontmatter(text)
        if fm is None:
            issues.append(f"skills/{skill_path.name}/SKILL.md: missing YAML frontmatter")
            continue
        if "name" not in fm or not fm["name"]:
            issues.append(f"skills/{skill_path.name}/SKILL.md: frontmatter missing 'name'")
        elif fm["name"] != skill_path.name:
            issues.append(
                f"skills/{skill_path.name}/SKILL.md: name={fm['name']!r} doesn't match directory {skill_path.name!r}"
            )
        if "description" not in fm or not fm["description"]:
            issues.append(f"skills/{skill_path.name}/SKILL.md: frontmatter missing 'description'")
    return issues


def lint_next_steps_citation(plugin_dir: Path) -> list[str]:
    """Verify every skills/<name>/SKILL.md cites a hand-off contract — either
    ``next-steps.md`` or ``handoff-menu.md``. Skills that end without pointing
    the user to a next move are dead ends; gate skills satisfy this via
    handoff-menu.md, so either citation is accepted."""
    issues: list[str] = []
    skills_dir = plugin_dir / "skills"
    if not skills_dir.is_dir():
        return [f"plugin: missing skills/ directory at {skills_dir}"]

    for skill_path in sorted(skills_dir.iterdir()):
        if not skill_path.is_dir():
            continue
        # Underscore-prefixed dirs (e.g. _shared/) hold cross-skill reference
        # files, not skills — they have no SKILL.md and no paired command.
        if skill_path.name.startswith("_"):
            continue
        skill_md = skill_path / "SKILL.md"
        if not skill_md.exists():
            continue
        text = skill_md.read_text(encoding="utf-8")
        if "next-steps.md" not in text and "handoff-menu.md" not in text:
            issues.append(
                f"skills/{skill_path.name}/SKILL.md: missing next-steps.md citation "
                "(cite _shared/next-steps.md or handoff-menu.md)"
            )
    return issues


def lint_command_shims(plugin_dir: Path) -> list[str]:
    """Verify every commands/<name>.md has a matching skills/<name>/SKILL.md
    and vice versa. Slash commands without backing skills are dead links;
    skills without commands are unreachable from the UI."""
    issues: list[str] = []
    commands_dir = plugin_dir / "commands"
    skills_dir = plugin_dir / "skills"
    if not commands_dir.is_dir():
        return [f"plugin: missing commands/ directory at {commands_dir}"]
    if not skills_dir.is_dir():
        return [f"plugin: missing skills/ directory at {skills_dir}"]

    command_names = {p.stem for p in commands_dir.glob("*.md")}
    # Skip underscore-prefixed support dirs (e.g. _shared/) — not user-facing skills.
    skill_names = {p.name for p in skills_dir.iterdir() if p.is_dir() and not p.name.startswith("_")}

    for orphan in sorted(command_names - skill_names):
        issues.append(f"commands/{orphan}.md: no matching skills/{orphan}/SKILL.md")
    for orphan in sorted(skill_names - command_names):
        issues.append(f"skills/{orphan}/: no matching commands/{orphan}.md (unreachable)")

    # Each command shim must reference its skill path.
    for cmd_path in sorted(commands_dir.glob("*.md")):
        text = cmd_path.read_text(encoding="utf-8")
        expected = f"skills/{cmd_path.stem}/SKILL.md"
        if expected not in text:
            issues.append(f"commands/{cmd_path.name}: doesn't reference {expected}")
        fm = parse_frontmatter(text)
        if fm is None:
            issues.append(f"commands/{cmd_path.name}: missing frontmatter")
        elif not fm.get("description"):
            issues.append(f"commands/{cmd_path.name}: frontmatter missing 'description'")
    return issues


_BEGIN_RE = re.compile(r"BEGIN:([a-zA-Z][a-zA-Z0-9_-]*)")
_END_RE = re.compile(r"END:([a-zA-Z][a-zA-Z0-9_-]*)")


def lint_template_rule_blocks(template_path: Path) -> list[str]:
    """Verify every BEGIN:<name> has a matching END:<name>, and order is
    BEGIN then END for each block (no nesting)."""
    issues: list[str] = []
    if not template_path.exists():
        return [f"template: not found at {template_path}"]
    text = template_path.read_text(encoding="utf-8")

    begins = [(m.start(), m.group(1)) for m in _BEGIN_RE.finditer(text)]
    ends = [(m.start(), m.group(1)) for m in _END_RE.finditer(text)]

    begin_names = [name for _, name in begins]
    end_names = [name for _, name in ends]

    for name in begin_names:
        if begin_names.count(name) > 1:
            issues.append(f"template: BEGIN:{name} appears {begin_names.count(name)} times")

    missing_end = sorted(set(begin_names) - set(end_names))
    for name in missing_end:
        issues.append(f"template: BEGIN:{name} has no matching END:{name}")

    missing_begin = sorted(set(end_names) - set(begin_names))
    for name in missing_begin:
        issues.append(f"template: END:{name} has no matching BEGIN:{name}")

    # Order check: each BEGIN must precede its END.
    for name in set(begin_names) & set(end_names):
        b_pos = next(pos for pos, n in begins if n == name)
        e_pos = next(pos for pos, n in ends if n == name)
        if b_pos > e_pos:
            issues.append(f"template: END:{name} precedes BEGIN:{name}")

    # De-dup
    return sorted(set(issues))


def lint_plugin_json(plugin_dir: Path) -> list[str]:
    """Verify .claude-plugin/plugin.json exists and has required fields."""
    issues: list[str] = []
    p = plugin_dir / ".claude-plugin" / "plugin.json"
    if not p.exists():
        return [f"plugin: missing .claude-plugin/plugin.json at {p}"]
    import json as _json

    try:
        data = _json.loads(p.read_text(encoding="utf-8"))
    except _json.JSONDecodeError as exc:
        return [f"plugin.json: invalid JSON ({exc})"]
    for field in ("name", "version", "description"):
        if not data.get(field):
            issues.append(f"plugin.json: missing or empty {field!r}")
    return issues


# ── Orchestration ────────────────────────────────────────────────────────────


def lint_all(
    plugin_dir: Path,
    template_path: Path | None = None,
) -> list[str]:
    """Run every linter and return the combined issue list."""
    issues: list[str] = []
    issues.extend(lint_plugin_json(plugin_dir))
    issues.extend(lint_skill_files(plugin_dir))
    issues.extend(lint_next_steps_citation(plugin_dir))
    issues.extend(lint_command_shims(plugin_dir))
    if template_path is None:
        template_path = plugin_dir / "templates" / "CLAUDE.md.template"
    issues.extend(lint_template_rule_blocks(template_path))
    return issues


# ── CLI ──────────────────────────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    plugin_dir = Path("plugin")
    template_path: Path | None = None

    i = 0
    while i < len(argv):
        if argv[i] == "--plugin-dir" and i + 1 < len(argv):
            plugin_dir = Path(argv[i + 1])
            i += 2
        elif argv[i] == "--template" and i + 1 < len(argv):
            template_path = Path(argv[i + 1])
            i += 2
        elif argv[i] in ("-h", "--help"):
            sys.stdout.write("usage: python -m renmark.lint [--plugin-dir DIR] [--template PATH]\n")
            return 0
        else:
            sys.stderr.write(f"unknown arg: {argv[i]}\n")
            return 2

    if not plugin_dir.exists():
        sys.stderr.write(f"plugin dir not found: {plugin_dir}\n")
        return 2

    issues = lint_all(plugin_dir, template_path)
    if issues:
        for issue in issues:
            sys.stderr.write(f"  - {issue}\n")
        sys.stderr.write(f"FAIL ({len(issues)} issue{'s' if len(issues) != 1 else ''})\n")
        return 1
    sys.stdout.write(f"OK  plugin lint  {plugin_dir}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())

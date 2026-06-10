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
        try:
            text = skill_md.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            issues.append(f"skills/{skill_path.name}/SKILL.md: file unreadable")
            continue
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
    """Verify every skills/<name>/SKILL.md cites the hand-off contract.

    The umbrella contract is ``next-steps.md``; ``handoff-menu.md`` is its gate
    sub-menu. To keep the drift guard meaningful, the required citation depends
    on the skill's class (per ``lifecycle.skill_class``):

    - **pipeline / aux** skills MUST cite ``next-steps.md`` (citing only the gate
      menu would not give them their state-derived next step).
    - **gate** skills (verify, codereview) may cite EITHER ``next-steps.md`` or
      ``handoff-menu.md`` — the gate sub-menu is their correct hand-off.

    A skill that cites neither is a dead end.
    """
    from .lifecycle import skill_class

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
        try:
            text = skill_md.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            issues.append(f"skills/{skill_path.name}/SKILL.md: file unreadable")
            continue
        cites_umbrella = "next-steps.md" in text
        cites_gate = "handoff-menu.md" in text
        if skill_class(skill_path.name) == "gate":
            if not (cites_umbrella or cites_gate):
                issues.append(
                    f"skills/{skill_path.name}/SKILL.md: missing hand-off citation "
                    "(gate skill must cite _shared/next-steps.md or handoff-menu.md)"
                )
        elif not cites_umbrella:
            issues.append(
                f"skills/{skill_path.name}/SKILL.md: missing next-steps.md citation "
                "(pipeline/aux skill must cite _shared/next-steps.md)"
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
        try:
            text = cmd_path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            issues.append(f"commands/{cmd_path.name}: file unreadable")
            continue
        expected = f"skills/{cmd_path.stem}/SKILL.md"
        if expected not in text:
            issues.append(f"commands/{cmd_path.name}: doesn't reference {expected}")
        fm = parse_frontmatter(text)
        if fm is None:
            issues.append(f"commands/{cmd_path.name}: missing frontmatter")
        elif not fm.get("description"):
            issues.append(f"commands/{cmd_path.name}: frontmatter missing 'description'")
    return issues


# Managed markers are a full HTML comment on their OWN line:
#     <!-- BEGIN:name -->
#     <!-- END:name -->
# Anchored to line start/end (re.MULTILINE) with optional surrounding
# whitespace, so bare prose like "BEGIN:example" inside a sentence is NOT
# treated as a marker. This is the only marker form the real templates emit.
_BEGIN_RE = re.compile(r"^[ \t]*<!--[ \t]*BEGIN:([a-zA-Z][a-zA-Z0-9_-]*)[ \t]*-->[ \t]*$", re.MULTILINE)
_END_RE = re.compile(r"^[ \t]*<!--[ \t]*END:([a-zA-Z][a-zA-Z0-9_-]*)[ \t]*-->[ \t]*$", re.MULTILINE)


def validate_rule_markers(text: str) -> list[str]:
    """Return a list of marker-balance problems in ``text`` (empty = well-formed).

    Mirrors the strict rules of ``lint_template_rule_blocks`` but operates on an
    in-memory string (a target CLAUDE.md/AGENTS.md being merged), not a template
    path. A file is well-formed iff: every ``BEGIN:name`` appears exactly once,
    every ``END:name`` appears exactly once, the two sets of names match (no
    orphan BEGIN, no orphan END), and each BEGIN precedes its matching END.

    This is the pre-insert gate for ``init.merge_rule_blocks``: if this returns
    a non-empty list, the file must NOT be written to (it would risk corrupting
    already-unbalanced markers).
    """
    issues: list[str] = []
    begins = [(m.start(), m.group(1)) for m in _BEGIN_RE.finditer(text)]
    ends = [(m.start(), m.group(1)) for m in _END_RE.finditer(text)]
    begin_names = [name for _, name in begins]
    end_names = [name for _, name in ends]

    for name in set(begin_names):
        if begin_names.count(name) > 1:
            issues.append(f"BEGIN:{name} appears {begin_names.count(name)} times")
    for name in set(end_names):
        if end_names.count(name) > 1:
            issues.append(f"END:{name} appears {end_names.count(name)} times")

    for name in sorted(set(begin_names) - set(end_names)):
        issues.append(f"BEGIN:{name} has no matching END:{name}")
    for name in sorted(set(end_names) - set(begin_names)):
        issues.append(f"END:{name} has no matching BEGIN:{name}")

    for name in set(begin_names) & set(end_names):
        if begin_names.count(name) == 1 and end_names.count(name) == 1:
            b_pos = next(pos for pos, n in begins if n == name)
            e_pos = next(pos for pos, n in ends if n == name)
            if b_pos > e_pos:
                issues.append(f"END:{name} precedes BEGIN:{name}")
    return sorted(set(issues))


def iter_rule_blocks(text: str) -> list[tuple[str, str]]:
    """Extract well-formed ``BEGIN:<name>``…``END:<name>`` rule blocks from ``text``.

    Returns ``[(name, verbatim_block), …]`` in document order, where
    ``verbatim_block`` runs from the start of the BEGIN marker's line through
    the end of the END marker's line (trailing newline included if present).

    Reuses ``_BEGIN_RE`` / ``_END_RE`` so the linter and any consumer (e.g.
    ``init.merge_rule_blocks``) share one marker source of truth. Malformed
    blocks — duplicate, unbalanced, or out-of-order — are SKIPPED, never
    returned, so a caller can safely insert only what it gets back. This is
    intentionally non-strict (unlike ``lint_template_rule_blocks`` which
    reports those as issues); it's the merge-safe view of the same data.
    """
    begins = [(m.start(), m.group(1)) for m in _BEGIN_RE.finditer(text)]
    ends = [(m.start(), m.group(1)) for m in _END_RE.finditer(text)]

    begin_names = [name for _, name in begins]
    end_names = [name for _, name in ends]

    blocks: list[tuple[str, str]] = []
    for b_pos, name in begins:
        # Skip names that aren't a clean 1:1 balanced pair.
        if begin_names.count(name) != 1 or end_names.count(name) != 1:
            continue
        e_pos = next(pos for pos, n in ends if n == name)
        if e_pos < b_pos:
            continue  # out of order — skip
        # Expand to whole-line boundaries: line start of BEGIN, line end of END.
        line_start = text.rfind("\n", 0, b_pos) + 1
        end_marker = next(m for m in _END_RE.finditer(text) if m.group(1) == name)
        nl = text.find("\n", end_marker.end())
        line_end = len(text) if nl < 0 else nl + 1
        blocks.append((name, text[line_start:line_end]))
    return blocks


def lint_template_rule_blocks(template_path: Path) -> list[str]:
    """Verify every BEGIN:<name> has a matching END:<name>, and order is
    BEGIN then END for each block (no nesting)."""
    issues: list[str] = []
    if not template_path.exists():
        return [f"template: not found at {template_path}"]
    try:
        text = template_path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return [f"template: file unreadable at {template_path}"]

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


# ── Strict frontmatter-value pass ────────────────────────────────────────────

# Matches a frontmatter line whose plain-scalar value contains an unquoted
# ": " (colon-space).  Example: `description: foo: bar baz` where the value
# after the key is NOT wrapped in quotes.  We detect this by finding lines
# where (a) the value doesn't start with ' or ", and (b) ": " appears inside
# the value portion.
_FM_UNQUOTED_COLON_RE = re.compile(
    r"^([a-zA-Z][a-zA-Z0-9_-]*):\s+"  # key:
    r'(?![\'"])'  # value does NOT start with a quote
    r".*:\s",  # contains ": " somewhere
)

# Balanced quoted scalars per strict YAML: double-quoted values may contain
# backslash escapes (\" is legal); single-quoted values escape ' by doubling
# (''). A quoted value that doesn't fully match its balanced form (with only
# trailing whitespace after the closing quote) is flagged.
_FM_KEY_VALUE_RE = re.compile(r"^([a-zA-Z][a-zA-Z0-9_-]*):\s+(.*)$")
_FM_DQ_BALANCED_RE = re.compile(r'"(?:[^"\\]|\\.)*"\s*$')
_FM_SQ_BALANCED_RE = re.compile(r"'(?:[^']|'')*'\s*$")


def lint_frontmatter_values(plugin_dir: Path) -> list[str]:
    """Detect frontmatter lines with invalid strict-YAML scalar values.

    Flags:
    - An unquoted plain-scalar value that contains ``": "`` (colon-space) —
      strict YAML parsers reject these as mapping indicators.
    - A quoted scalar with unbalanced / extra quotes.

    This pass is gated behind ``include_frontmatter_strict=True`` in
    ``lint_all`` (default ``False``) because 8 current plugin .md files
    fail it and a wave-2 agent owns those fixes.  Run in CI after wave-2
    lands by passing ``--strict-frontmatter`` on the CLI.

    Returns a list of issue strings (empty = clean).
    """
    issues: list[str] = []
    md_files: list[Path] = []
    for sub in (plugin_dir / "commands", plugin_dir / "skills"):
        if sub.is_dir():
            md_files.extend(sub.rglob("*.md"))

    for md_path in sorted(md_files):
        try:
            text = md_path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        m = _FRONTMATTER_RE.match(text)
        if not m:
            continue
        try:
            rel = md_path.relative_to(plugin_dir)
        except ValueError:
            rel = md_path.name  # type: ignore[assignment]
        for raw_line in m.group(1).splitlines():
            line = raw_line.rstrip()
            if not line or line.startswith("#"):
                continue
            kv = _FM_KEY_VALUE_RE.match(line)
            if not kv:
                continue
            value = kv.group(2)
            if value.startswith('"'):
                if not _FM_DQ_BALANCED_RE.match(value):
                    issues.append(f"{rel}: frontmatter value has unbalanced quotes: {line!r}")
            elif value.startswith("'"):
                if not _FM_SQ_BALANCED_RE.match(value):
                    issues.append(f"{rel}: frontmatter value has unbalanced quotes: {line!r}")
            elif _FM_UNQUOTED_COLON_RE.match(line):
                issues.append(
                    f"{rel}: frontmatter value contains unquoted ': ' — quote the value to fix strict-YAML: {line!r}"
                )
    return issues


# ── Orchestration ────────────────────────────────────────────────────────────


def lint_all(
    plugin_dir: Path,
    template_path: Path | None = None,
    *,
    include_frontmatter_strict: bool = False,
) -> list[str]:
    """Run every linter and return the combined issue list.

    ``include_frontmatter_strict`` (default ``False``) enables the strict
    frontmatter-value pass (``lint_frontmatter_values``).  Gate it behind
    ``True`` / ``--strict-frontmatter`` only after the wave-2 agent fixes the
    8 plugin .md files that currently fail it.
    """
    issues: list[str] = []
    issues.extend(lint_plugin_json(plugin_dir))
    issues.extend(lint_skill_files(plugin_dir))
    issues.extend(lint_next_steps_citation(plugin_dir))
    issues.extend(lint_command_shims(plugin_dir))
    if template_path is None:
        template_path = plugin_dir / "templates" / "CLAUDE.md.template"
    issues.extend(lint_template_rule_blocks(template_path))
    if include_frontmatter_strict:
        issues.extend(lint_frontmatter_values(plugin_dir))
    return issues


# ── CLI ──────────────────────────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    plugin_dir = Path("plugin")
    template_path: Path | None = None
    strict_frontmatter = False

    i = 0
    while i < len(argv):
        if argv[i] == "--plugin-dir" and i + 1 < len(argv):
            plugin_dir = Path(argv[i + 1])
            i += 2
        elif argv[i] == "--template" and i + 1 < len(argv):
            template_path = Path(argv[i + 1])
            i += 2
        elif argv[i] == "--strict-frontmatter":
            strict_frontmatter = True
            i += 1
        elif argv[i] in ("-h", "--help"):
            sys.stdout.write(
                "usage: python -m renmark.lint [--plugin-dir DIR] [--template PATH] [--strict-frontmatter]\n"
            )
            return 0
        else:
            sys.stderr.write(f"unknown arg: {argv[i]}\n")
            return 2

    if not plugin_dir.exists():
        sys.stderr.write(f"plugin dir not found: {plugin_dir}\n")
        return 2

    issues = lint_all(plugin_dir, template_path, include_frontmatter_strict=strict_frontmatter)
    if issues:
        for issue in issues:
            sys.stderr.write(f"  - {issue}\n")
        sys.stderr.write(f"FAIL ({len(issues)} issue{'s' if len(issues) != 1 else ''})\n")
        return 1
    sys.stdout.write(f"OK  plugin lint  {plugin_dir}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())

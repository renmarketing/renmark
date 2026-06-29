"""Managed-block generator for SKILL.md files (P7 core).

Every renmark ``plugin/skills/<name>/SKILL.md`` carries the same small set of
boilerplate regions — a Step-0 context-check preamble, and citation blocks for
the ``_shared`` contracts (reasoning, next-steps, hand-off menu). Historically
each SKILL.md restated these by hand, so the wording drifted within a release
(the exact failure ``_shared/*`` files were created to stop). This module turns
those regions into **generated, marker-delimited managed blocks**: the canonical
text is read once from the ``_shared`` source files and rendered identically into
every skill, parameterized by :mod:`renmark.skillmeta`.

The contract mirrors :func:`renmark.init.merge_marked_block`:

- Each managed region lives between own-line ``<!-- BEGIN:gen-<block> -->`` and
  ``<!-- END:gen-<block> -->`` markers (a ``gen-`` namespace so they never collide
  with the project-stub / rule-block markers init.py owns). The hyphen — not a
  colon — is required because the shipped marker regex (``renmark.lint._BEGIN_RE``)
  forbids ``:`` in a marker name.
- ``render_block`` NEVER hardcodes the canonical blockquote — it extracts it from
  the matching ``_shared`` file, so an edit there propagates here next run.
- ``merge_skill`` replaces existing managed regions in place (byte-preserving
  everything outside them — frontmatter and prose are never touched) and INSERTS
  any absent block at a deterministic, documented location for first migration.

CLI (never raises uncaught — failures are caught and reported, returning nonzero):

    python -m renmark.skillgen            # dry-run: what --write would change
    python -m renmark.skillgen --check    # no writes; drift + frontmatter lint; exit 1 on any
    python -m renmark.skillgen --write     # apply managed-block merges to every skill

``--write`` reads frontmatter only for the lint report; it NEVER writes
frontmatter. This module does NOT run the migration on import — the markers are
inserted only when ``--write`` (or ``merge_skill(write=True)``) is invoked.

Stdlib-only; ``from __future__ import annotations``; matches the house CLI style
in :mod:`renmark.plan_lint` / :mod:`renmark.init`.
"""

from __future__ import annotations

import re
import sys
import traceback
from pathlib import Path

from . import skillmeta
from .init import MarkerCorruptionError, MarkerNotFoundError, merge_marked_block
from .lint import parse_frontmatter
from .skillmeta import SkillMeta

# ── Where the sources live ────────────────────────────────────────────────────

# /home/renmark/projects/ai-system/renmark/skillgen.py  →  /home/renmark/projects/ai-system
RENMARK_ROOT = Path(__file__).resolve().parent.parent
PLUGIN_SOURCE = RENMARK_ROOT / "plugin"
SHARED_DIR = PLUGIN_SOURCE / "skills" / "_shared"

# Blocks every skill carries, in the deterministic order new blocks are appended
# during first migration. ``preamble`` is ALWAYS rendered; the contract-citation
# blocks are rendered only when the skill's ``meta.cites`` lists them.
ALL_BLOCKS = ("preamble", "reasoning-contract", "next-steps", "handoff-menu")

# Marker namespace prefix for every generated region. The intent is a ``gen``
# namespace, but the shipped marker convention (``renmark.lint._BEGIN_RE``, which
# ``merge_marked_block`` enforces) restricts a marker NAME to
# ``[A-Za-z][A-Za-z0-9_-]*`` — colons are NOT allowed. So the on-disk marker is
# ``gen-<block>`` (a hyphen, not a colon): ``<!-- BEGIN:gen-preamble -->`` etc.
# This keeps the generator compatible with the existing primitive without
# touching the shared regex.
MARKER_PREFIX = "gen-"


def _marker(block: str) -> str:
    """The marker NAME for a block — ``gen-<block>`` (lint-regex compatible)."""
    return f"{MARKER_PREFIX}{block}"

# Map a citable ``_shared`` name to the block name it renders as. The preamble is
# not a citation — it is unconditional — so it is not in this map.
CITE_TO_BLOCK = {
    "reasoning-contract": "reasoning-contract",
    "next-steps": "next-steps",
    "handoff-menu": "handoff-menu",
}


class SkillGenError(RuntimeError):
    """A render/merge precondition failed (missing source file or section)."""


# ── Source extraction (NEVER hardcode the canonical text) ─────────────────────


def _read_shared(name: str) -> str:
    """Return the text of ``_shared/<name>.md``; raise SkillGenError if absent."""
    path = SHARED_DIR / f"{name}.md"
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise SkillGenError(f"cannot read shared source {path}: {exc}") from exc


def _extract_blockquote(text: str, anchor: str) -> str:
    """Extract the first contiguous ``>``-prefixed block after an anchor line.

    ``anchor`` is matched as a substring of any line (a ``#`` heading or a bold
    "When citing…" lead-in); the first blockquote (one or more consecutive lines
    starting with ``>``, blank ``>`` lines included) that follows it is returned
    with the leading ``> `` / ``>`` stripped from each line. Raises SkillGenError
    if not found.
    """
    lines = text.splitlines()
    start = None
    for i, ln in enumerate(lines):
        if anchor in ln:
            start = i + 1
            break
    if start is None:
        raise SkillGenError(f"anchor containing {anchor!r} not found in shared source")

    # Scan forward to the first '>' line, then collect the contiguous run.
    quote: list[str] = []
    in_quote = False
    for ln in lines[start:]:
        stripped = ln.rstrip()
        if stripped.startswith(">"):
            in_quote = True
            # Strip the leading '>' and one optional space.
            body = stripped[1:]
            if body.startswith(" "):
                body = body[1:]
            quote.append(body)
        elif in_quote:
            break  # blockquote ended
    if not quote:
        raise SkillGenError(f"no blockquote found after anchor {anchor!r}")
    return "\n".join(quote).strip()


# Heading anchors used to locate each canonical blockquote in its source file.
_REASONING_HEADING = "canonical reasoning instruction"
# Anchor on the "(class N):" lead-in of each citation block — unique to the
# "When citing this contract" section, so it can't collide with the earlier
# "Three skill classes" discussion headings.
_NEXTSTEPS_HEADING_BY_CLASS = {
    1: "(class 1):",
    2: "(class 2):",
    3: "(class 3):",
}


def _render_preamble(skill: str, meta: SkillMeta) -> str:
    """The Step-0 context-check instruction, parameterized by skill name.

    The preamble text is renmark's own convention (not a ``_shared`` blockquote),
    but it is rendered identically across skills so the wording can't drift. The
    skill name is the only parameter.
    """
    return (
        f"**Step 0 — Context check.** Call `lifecycle.skill_preamble(repo, '{skill}')`. "
        f"If it returns a non-None hint, surface it as a one-line note (a `/compact` or "
        f"`/clear` suggestion on a cross-domain transition). Do NOT block — the user "
        f"decides. This skill is the `{meta.domain}` domain."
    )


def _render_reasoning_contract(skill: str, meta: SkillMeta) -> str:
    """The pointer-citation for the reasoning/output-discipline contract.

    Pulls the canonical verbatim instruction from
    ``_shared/reasoning-contract.md`` so the rendered block matches the source.
    """
    instruction = _extract_blockquote(_read_shared("reasoning-contract"), _REASONING_HEADING)
    quoted = "\n".join(f"> {ln}" if ln else ">" for ln in instruction.splitlines())
    return (
        "When dispatching subagents, include the reasoning/output-discipline "
        "contract from `${CLAUDE_PLUGIN_ROOT}/skills/_shared/reasoning-contract.md` "
        "in every dispatched prompt (cite by pointer; do not paste). The canonical "
        "instruction it carries:\n\n"
        f"{quoted}"
    )


def _render_next_steps(skill: str, meta: SkillMeta) -> str:
    """The class-specific next-step citation from ``_shared/next-steps.md``.

    The skill's ``next_steps_class`` (1 = pipeline, 2 = quality gate, 3 = aux)
    selects which citation blockquote is rendered; ``<skill>`` is substituted
    with the skill name.
    """
    cls = meta.next_steps_class
    heading = _NEXTSTEPS_HEADING_BY_CLASS.get(cls)
    if heading is None:
        raise SkillGenError(f"{skill}: unknown next_steps_class {cls!r}")
    citation = _extract_blockquote(_read_shared("next-steps"), heading)
    citation = citation.replace("<skill>", skill)
    quoted = "\n".join(f"> {ln}" if ln else ">" for ln in citation.splitlines())
    return f"Next-step hand-off (class {cls}, see `${{CLAUDE_PLUGIN_ROOT}}/skills/_shared/next-steps.md`):\n\n{quoted}"


def _render_handoff_menu(skill: str, meta: SkillMeta) -> str:
    """The gate hand-off menu citation from ``_shared/handoff-menu.md``."""
    citation = _extract_blockquote(_read_shared("handoff-menu"), "citing this menu")
    quoted = "\n".join(f"> {ln}" if ln else ">" for ln in citation.splitlines())
    return f"Quality-gate hand-off menu (see `${{CLAUDE_PLUGIN_ROOT}}/skills/_shared/handoff-menu.md`):\n\n{quoted}"


_RENDERERS = {
    "preamble": _render_preamble,
    "reasoning-contract": _render_reasoning_contract,
    "next-steps": _render_next_steps,
    "handoff-menu": _render_handoff_menu,
}


def render_block(skill: str, block: str) -> str:
    """Render the managed-region body for ``block`` of ``skill``.

    ``block`` is one of :data:`ALL_BLOCKS`. The body is deterministic and carries
    NO BEGIN/END markers (``merge_skill`` adds those). Canonical contract text is
    extracted from the ``_shared`` sources, never hardcoded. Raises
    :class:`SkillGenError` if the skill is unknown or the block name is invalid.
    """
    meta = skillmeta.get(skill)
    if meta is None:
        raise SkillGenError(f"unknown skill {skill!r}")
    renderer = _RENDERERS.get(block)
    if renderer is None:
        raise SkillGenError(f"unknown block {block!r}")
    return renderer(skill, meta)


# ── Merge into a SKILL.md ─────────────────────────────────────────────────────


def _blocks_for(meta: SkillMeta) -> list[str]:
    """The ordered list of managed blocks this skill should carry.

    Always the preamble, plus one block per cited ``_shared`` contract, in the
    stable :data:`ALL_BLOCKS` order so insertion is deterministic.
    """
    wanted = {"preamble"}
    for cite in meta.cites:
        block = CITE_TO_BLOCK.get(cite)
        if block is not None:
            wanted.add(block)
    return [b for b in ALL_BLOCKS if b in wanted]


def _wrap(block: str, body: str) -> str:
    """The full own-line managed region for ``block`` (marker name ``gen-<block>``)."""
    name = _marker(block)
    return f"<!-- BEGIN:{name} -->\n{body}\n<!-- END:{name} -->"


def _frontmatter_end(text: str) -> int:
    """Return the char offset just past the closing ``---`` of frontmatter.

    Returns 0 when there is no frontmatter, so insertion below never lands
    inside a YAML block.
    """
    m = re.match(r"^---\s*\n.*?\n---\s*\n", text, re.DOTALL)
    return m.end() if m else 0


def merge_skill(path: Path, meta: SkillMeta, *, write: bool) -> tuple[str, bool]:
    """Merge every managed block this ``meta`` requires into the SKILL.md at ``path``.

    For each block in :func:`_blocks_for` (always the preamble + one per cited
    contract), the marker name is ``gen-<block>``. Existing managed regions are
    replaced in place via :func:`renmark.init.merge_marked_block` (everything
    outside the markers — frontmatter and prose — is byte-preserved). A block
    that is ABSENT is INSERTED, in :data:`ALL_BLOCKS` order, immediately after the
    frontmatter (or at the top of the file when there is no frontmatter) — a
    stable, documented home for the first migration.

    Returns ``(new_text, changed)``; ``changed`` is False on byte-equality (so a
    second merge is a no-op). Only writes to disk when ``write`` is True.
    Frontmatter is never modified.
    """
    skill = meta_skill_name(path)
    original = path.read_text(encoding="utf-8")
    text = original

    # Pass 1: replace every block that already exists, in place. Collect the
    # missing ones to insert together (single contiguous group → stable order,
    # idempotent whitespace, regardless of how many already existed).
    missing: list[str] = []
    for block in _blocks_for(meta):
        body = render_block(skill, block)
        try:
            text = merge_marked_block(text, _marker(block), f"\n{body}\n")
        except MarkerNotFoundError:
            missing.append(block)

    # Pass 2: insert the missing blocks as one block-group immediately after the
    # frontmatter (top of file when there is none), in ALL_BLOCKS order — a
    # stable, documented home for the first migration. One blank line separates
    # each region and pads the group from the surrounding text.
    if missing:
        regions = "\n\n".join(_wrap(block, render_block(skill, block)) for block in missing)
        ins = _frontmatter_end(text)
        prefix = text[:ins]
        suffix = text[ins:]
        # Normalize padding so re-running can't accumulate blank lines.
        prefix = prefix.rstrip("\n")
        suffix = suffix.lstrip("\n")
        head = (prefix + "\n\n") if prefix else ""
        tail = ("\n\n" + suffix) if suffix else "\n"
        text = f"{head}{regions}{tail}"

    changed = text != original
    if write and changed:
        path.write_text(text, encoding="utf-8")
    return text, changed


def meta_skill_name(path: Path) -> str:
    """The skill name for a SKILL.md path == its parent directory name."""
    return path.parent.name


# ── Frontmatter lint (read-only) ──────────────────────────────────────────────

# A description is "trigger-only-shaped" when it opens with the imperative "Use"
# and names at least one invocation trigger — a `/renmark:<skill>` mention or a
# quoted natural-language trigger phrase. This is the shape every shipped
# description already has (see plugin/skills/*/SKILL.md).
_TRIGGER_RE = re.compile(r"/renmark:|[\"']")


def _truthy(value: str | None) -> bool:
    """Parse a frontmatter scalar as a bool. Absent / 'false' / '' → False."""
    return (value or "").strip().lower() in {"true", "yes", "1"}


def lint_frontmatter(skill: str, text: str, meta: SkillMeta) -> list[str]:
    """Return frontmatter-discipline violations for one SKILL.md (read-only).

    Checks: a non-empty ``description`` that is trigger-only-shaped, and that the
    ``disable-model-invocation`` flag matches ``meta.disable_model_invocation``.
    """
    issues: list[str] = []
    fm = parse_frontmatter(text)
    if fm is None:
        return [f"{skill}: missing frontmatter"]

    desc = (fm.get("description") or "").strip()
    if not desc:
        issues.append(f"{skill}: frontmatter missing description")
    else:
        if not desc.startswith("Use"):
            issues.append(f"{skill}: description not trigger-shaped (should open with 'Use')")
        if not _TRIGGER_RE.search(desc):
            issues.append(f"{skill}: description names no trigger (/renmark: or quoted phrase)")

    declared = _truthy(fm.get("disable-model-invocation"))
    if declared != meta.disable_model_invocation:
        issues.append(
            f"{skill}: disable-model-invocation={declared} "
            f"but skillmeta expects {meta.disable_model_invocation}"
        )
    return issues


# ── CLI ───────────────────────────────────────────────────────────────────────


def _skill_path(skill: str) -> Path:
    return PLUGIN_SOURCE / "skills" / skill / "SKILL.md"


def _run_check() -> tuple[list[str], list[str]]:
    """Return (drifting, violations) over every registered skill.

    ``drifting`` = skills whose managed regions differ from the render output.
    ``violations`` = frontmatter-discipline violations. Both are bounded prose
    lines suitable for direct printing.
    """
    drifting: list[str] = []
    violations: list[str] = []
    for skill in sorted(skillmeta.SKILLS):
        meta = skillmeta.SKILLS[skill]
        path = _skill_path(skill)
        if not path.exists():
            violations.append(f"{skill}: SKILL.md not found at {path}")
            continue
        text = path.read_text(encoding="utf-8")
        violations.extend(lint_frontmatter(skill, text, meta))
        try:
            _, changed = merge_skill(path, meta, write=False)
        except (SkillGenError, MarkerCorruptionError) as exc:
            drifting.append(f"{skill}: {exc}")
            continue
        if changed:
            drifting.append(f"{skill}: managed blocks drift from generated output")
    return drifting, violations


def _run_apply(*, write: bool) -> list[str]:
    """Merge every skill (dry-run when ``write`` is False). Return changed-skill lines."""
    changed_lines: list[str] = []
    for skill in sorted(skillmeta.SKILLS):
        meta = skillmeta.SKILLS[skill]
        path = _skill_path(skill)
        if not path.exists():
            changed_lines.append(f"{skill}: SKILL.md not found — skipped")
            continue
        try:
            _, changed = merge_skill(path, meta, write=write)
        except (SkillGenError, MarkerCorruptionError) as exc:
            changed_lines.append(f"{skill}: ERROR {exc}")
            continue
        if changed:
            verb = "wrote" if write else "would change"
            changed_lines.append(f"{skill}: {verb} managed blocks")
    return changed_lines


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Never raises uncaught — faults are reported, nonzero returned.

    Exit codes: 0 = clean (or dry-run summary), 1 = drift/violations under
    ``--check`` (or an internal fault). Frontmatter is read for lint only and is
    never written.
    """
    argv = sys.argv[1:] if argv is None else list(argv)

    if any(a in ("-h", "--help") for a in argv):
        sys.stdout.write(
            "usage: python -m renmark.skillgen [--check | --write]\n"
            "  (default)  dry-run: print what --write would change, exit 0\n"
            "  --check    no writes; report drift + frontmatter violations; exit 1 on any\n"
            "  --write    apply managed-block merges to every skill; exit 0\n"
        )
        return 0

    mode = "dry"
    if "--check" in argv:
        mode = "check"
    elif "--write" in argv:
        mode = "write"

    try:
        if mode == "check":
            drifting, violations = _run_check()
            if not drifting and not violations:
                sys.stdout.write("skillgen --check: clean — all managed blocks current\n")
                return 0
            if drifting:
                sys.stdout.write(f"DRIFT ({len(drifting)}):\n")
                for line in drifting:
                    sys.stdout.write(f"- {line}\n")
            if violations:
                sys.stdout.write(f"FRONTMATTER ({len(violations)}):\n")
                for line in violations:
                    sys.stdout.write(f"- {line}\n")
            return 1

        changed = _run_apply(write=(mode == "write"))
        verb = "wrote" if mode == "write" else "dry-run — would change"
        if not changed:
            sys.stdout.write(f"skillgen {verb}: nothing to change\n")
            return 0
        sys.stdout.write(f"skillgen {verb} ({len(changed)}):\n")
        for line in changed:
            sys.stdout.write(f"- {line}\n")
        return 0
    except Exception as exc:  # never raise uncaught from the CLI
        sys.stdout.write(f"skillgen: internal error — {type(exc).__name__}: {exc}\n")
        sys.stdout.write(traceback.format_exc())
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

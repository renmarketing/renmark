"""Read-only consistency linter for SKILL.md files (P7 — pure lint, no generation).

Doc-slimming already single-sourced every shared boilerplate region into
``plugin/skills/_shared/*.md`` and had each SKILL.md cite it **by pointer**
(``${CLAUDE_PLUGIN_ROOT}/skills/_shared/<name>.md``). There is therefore no
duplicated verbatim block left to generate or migrate — so this module carries
NO generator. It is a pure, read-only consistency lint over the registered
SKILL.md files.

Two checks per skill:

1. **Frontmatter discipline.** A non-empty ``description`` that is
   trigger-only-shaped (opens with the imperative "Use" and names at least one
   invocation trigger — a ``/renmark:<skill>`` mention or a quoted phrase), and
   a ``disable-model-invocation`` frontmatter flag that is present-and-true IFF
   :mod:`renmark.skillmeta` records ``disable_model_invocation=True`` for the
   skill (any mismatch is a violation).

2. **Doc-slimming guard.** The skill body must NOT re-inline a ``_shared``
   canonical blockquote verbatim — it must cite the pointer instead. Detection
   uses distinctive signature substrings pulled from the ``_shared`` files at
   runtime (never hardcoded in full); if a signature appears verbatim in the
   skill body (whitespace-normalized, so markdown re-wrapping can't hide it),
   the skill is flagged to cite the pointer instead.

CLI (never raises uncaught — faults are caught and reported, returning nonzero):

    python -m renmark.skillgen            # --check (default)
    python -m renmark.skillgen --check    # per-skill violation report; exit 1 on any, else 0

There is no ``--write`` and no generation: this module only reads.

Stdlib-only; ``from __future__ import annotations``; matches the house CLI style
in :mod:`renmark.lint` / :mod:`renmark.init`.
"""

from __future__ import annotations

import re
import sys
import traceback
from pathlib import Path

from . import skillmeta
from .lint import parse_frontmatter
from .skillmeta import SkillMeta

# ── Where the sources live ────────────────────────────────────────────────────

# /home/renmark/projects/ai-system/renmark/skillgen.py  →  /home/renmark/projects/ai-system
RENMARK_ROOT = Path(__file__).resolve().parent.parent
PLUGIN_SOURCE = RENMARK_ROOT / "plugin"
SHARED_DIR = PLUGIN_SOURCE / "skills" / "_shared"

# Each _shared canonical region is single-sourced and cited by pointer. To catch
# a skill that re-inlines one verbatim, we derive the comparison signature FROM
# the live _shared file at runtime — never from a frozen copy. Per region we keep
# only a short, stable *anchor*: a needle used to LOCATE the canonical line in the
# current file. The signature actually compared against skill bodies is the live
# text of the line carrying that anchor (whitespace/quote-normalized), so any
# wording edit to that canonical line is tracked automatically instead of
# silently disabling the guard. If a file is missing, or the anchor no longer
# appears (the line was renamed away), the check degrades safely — it skips, with
# no false positive.
_SHARED_ANCHORS: dict[str, str] = {
    # The reasoning-contract stance clause — distinctive and stable.
    "reasoning-contract": "Push back by default",
    # The next-steps umbrella rule.
    "next-steps": "every skill MUST end by recommending",
    # The handoff-menu Pause Policy heading.
    "handoff-menu": "Pause Policy",
}


# ── Whitespace-normalized verbatim detection ──────────────────────────────────

_WS_RE = re.compile(r"\s+")


def _normalize(text: str) -> str:
    """Collapse all whitespace runs to single spaces and strip blockquote
    markers, so a re-inlined region wrapped differently than the source (or
    carrying ``> `` quote prefixes) still matches its signature."""
    # Drop leading '>' quote markers, then collapse whitespace.
    no_quotes = re.sub(r"(?m)^[ \t]*>[ \t]?", "", text)
    return _WS_RE.sub(" ", no_quotes).strip()


def _shared_signature(name: str) -> str | None:
    """Return a live-derived, whitespace-normalized signature for a ``_shared`` region.

    The signature is DERIVED FROM the current ``_shared/<name>.md`` file content,
    not from a frozen copy: we locate the canonical line by its short anchor in
    :data:`_SHARED_ANCHORS`, then return that line's live text (after the same
    whitespace/quote normalization applied to skill bodies). Because the compared
    span is read from the file every run, a wording edit to the canonical line is
    tracked automatically — the guard keeps matching the canonical text instead of
    a stale literal.

    Returns ``None`` (skip, not an error) when the source file is missing or the
    anchor no longer appears anywhere in it (the canonical line was renamed away);
    in either case there is nothing to compare against, so the check degrades
    safely with no false positive.
    """
    anchor = _SHARED_ANCHORS.get(name)
    if anchor is None:
        return None
    path = SHARED_DIR / f"{name}.md"
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    norm_anchor = _normalize(anchor)
    if not norm_anchor:
        return None
    # Derive the signature from the live line that carries the anchor. Each raw
    # line is normalized the same way skill bodies are (quote markers stripped,
    # whitespace collapsed) so the comparison is apples-to-apples.
    for raw_line in text.splitlines():
        norm_line = _normalize(raw_line)
        if norm_anchor in norm_line:
            return norm_line
    return None


# ── Frontmatter discipline ─────────────────────────────────────────────────────

# A description is "trigger-only-shaped" when it opens with the imperative "Use"
# and names at least one invocation trigger. A trigger is EITHER a
# `/renmark:<skill>` mention OR a *genuine* quoted invocation phrase — a balanced
# double-quote or backtick span that holds either a slash-command-like token
# (`/foo`) or at least two word tokens. A lone apostrophe inside a word (e.g.
# "repo's") is NOT a quoted phrase and must not satisfy the check — that was the
# bug in the earlier `["']`-matches-anything rule. This is the shape every shipped
# description already has (see plugin/skills/*/SKILL.md).
_TRIGGER_RE = re.compile(
    r"""(?sx)
      /renmark:                              # an explicit slash-command mention, or…
    | "\s*/[\w:\-]+\s*"                       # a slash-command token inside double quotes
    | `\s*/[\w:\-]+\s*`                       # …or inside backticks
    | "[^"]*?\w[\w'’\-]*\s+[^"]*?\w[\w'’\-]*[^"]*?"   # a double-quoted phrase of ≥2 word tokens
    | `[^`]*?\w[\w'’\-]*\s+[^`]*?\w[\w'’\-]*[^`]*?`   # …or a backtick phrase of ≥2 word tokens
    """
)


def _truthy(value: str | None) -> bool:
    """Parse a frontmatter scalar as a bool. Absent / 'false' / '' → False."""
    return (value or "").strip().lower() in {"true", "yes", "1"}


# ── Per-skill lint ──────────────────────────────────────────────────────────────


def lint_skill(skill: str, text: str, meta: SkillMeta) -> list[str]:
    """Return the consistency-lint violations for ONE SKILL.md (read-only).

    ``text`` is the full SKILL.md contents; ``meta`` its registry entry. Two
    families of checks are run:

    1. **Frontmatter discipline** — non-empty trigger-only-shaped ``description``;
       ``disable-model-invocation`` present-and-true IFF
       ``meta.disable_model_invocation``.
    2. **Doc-slimming guard** — the body must not re-inline a ``_shared``
       canonical blockquote verbatim (it must cite the pointer instead).

    Returns a list of human-readable violation strings (empty = clean).
    """
    issues: list[str] = []

    # 1. Frontmatter discipline.
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

    # 2. Doc-slimming guard — no re-inlined _shared canonical blockquote.
    normalized_body = _normalize(text)
    for name in _SHARED_ANCHORS:
        sig = _shared_signature(name)
        if sig and sig in normalized_body:
            issues.append(
                f"{skill}: re-inlines _shared/{name}.md blockquote verbatim — cite the pointer instead"
            )

    return issues


def _skill_md_path(skill: str) -> Path:
    return PLUGIN_SOURCE / "skills" / skill / "SKILL.md"


def lint_all(repo: str = ".") -> dict[str, list[str]]:
    """Lint every ``plugin/skills/*/SKILL.md`` and return ``{skill: [violations]}``.

    The skill name is the directory name; its metadata comes from
    :func:`skillmeta.get`. ``repo`` selects the project root whose ``plugin/``
    tree is linted (defaults to the in-package plugin source — the same source
    the rest of P7 reads). Underscore-prefixed support dirs (e.g. ``_shared/``)
    and any directory without a SKILL.md are skipped. Skills with no registry
    metadata are reported with a single "no skillmeta entry" violation rather
    than silently skipped (a registry/skill mismatch is itself drift).

    Every skill key is present in the result, including those with an empty
    (clean) violation list.
    """
    skills_dir = Path(repo) / "plugin" / "skills"
    # Fall back to the in-package plugin source when called with the default '.'
    # from outside the project root (mirrors how the rest of P7 resolves paths).
    if not skills_dir.is_dir():
        skills_dir = PLUGIN_SOURCE / "skills"

    results: dict[str, list[str]] = {}
    if not skills_dir.is_dir():
        return results

    for skill_path in sorted(skills_dir.iterdir()):
        if not skill_path.is_dir() or skill_path.name.startswith("_"):
            continue
        skill = skill_path.name
        skill_md = skill_path / "SKILL.md"
        if not skill_md.exists():
            results[skill] = [f"{skill}: missing SKILL.md at {skill_md}"]
            continue
        try:
            text = skill_md.read_text(encoding="utf-8")
        except OSError as exc:
            results[skill] = [f"{skill}: SKILL.md unreadable ({exc})"]
            continue
        meta = skillmeta.get(skill)
        if meta is None:
            results[skill] = [f"{skill}: no skillmeta entry (registry/skill mismatch)"]
            continue
        results[skill] = lint_skill(skill, text, meta)
    return results


# ── CLI ───────────────────────────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> int:
    """CLI entry point — ``--check`` (default). Never raises uncaught.

    Prints a bounded per-skill violation report and exits 1 if any skill has a
    violation, else 0. There is no ``--write`` and no generation: read-only lint.
    """
    argv = sys.argv[1:] if argv is None else list(argv)

    if any(a in ("-h", "--help") for a in argv):
        sys.stdout.write(
            "usage: python -m renmark.skillgen [--check]\n"
            "  --check (default)  read-only consistency lint over every SKILL.md;\n"
            "                     exit 1 if any violation, else 0\n"
        )
        return 0

    unknown = [a for a in argv if a not in ("--check",)]
    if unknown:
        sys.stdout.write(f"skillgen: unknown arg(s): {' '.join(unknown)} (only --check is supported)\n")
        return 1

    try:
        results = lint_all()
        flagged = {skill: issues for skill, issues in results.items() if issues}
        total = sum(len(v) for v in flagged.values())
        if not flagged:
            sys.stdout.write(f"skillgen --check: clean — {len(results)} skills, no violations\n")
            return 0
        sys.stdout.write(f"skillgen --check: {total} violation(s) across {len(flagged)} skill(s)\n")
        for skill in sorted(flagged):
            for line in flagged[skill]:
                sys.stdout.write(f"- {line}\n")
        return 1
    except Exception as exc:  # never raise uncaught from the CLI
        sys.stdout.write(f"skillgen: internal error — {type(exc).__name__}: {exc}\n")
        sys.stdout.write(traceback.format_exc())
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

"""Deterministic plugin/registry audit engine — the zero-LLM core of
``/renmark:audit`` and ``/renmark:inventory``.

This module **composes** the audit dimensions that already ship as standalone
deterministic checkers and adds only the passes none of them cover:

Already covered (composed here, never re-implemented):
    - :mod:`renmark.lint` — frontmatter presence/name-match, shim↔SKILL wiring,
      class-aware next-steps citation, template rule-block integrity, and the
      opt-in strict-YAML frontmatter pass.
    - :mod:`renmark.modularity` — engine code-health (5 AST metrics).
    - :func:`renmark.release.check_drift` — version-file parity.

Added here (the gaps the existing checkers lack):
    - :func:`registry_sync` — diff ``lifecycle.DOMAIN_BY_SKILL`` /
      ``IMPLEMENTED_SKILLS`` / class-set membership against the actual
      ``plugin/skills/`` directories. The worst-drifting subsystem had ZERO
      lint coverage before this.
    - :func:`shim_thinness` — flag command shims that are too fat or that don't
      reference their ``skills/<name>/SKILL.md``.
    - :func:`description_drift` — flag shim/SKILL description pairs that share too
      little vocabulary (a crude, deterministic token-overlap heuristic).

It also builds a flat per-command **inventory** (pure frontmatter parsing) used
by ``/renmark:inventory``.

CLI:
    python -m renmark.audit [--quick] [--inventory-only] [--json] [--repo PATH]

Bounded stdout (≤5 lines): per-pass counts + artifact paths + a PASS/ISSUES
verdict. Exit 0 = clean, 1 = issues found. Never writes outside
``.renmark/audits/``.
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

from . import lifecycle, lint, modularity, release, summary

# ── Tunables ──────────────────────────────────────────────────────────────────

#: A command shim is "thin" if its non-frontmatter body is at most this many
#: non-blank lines. Real shims are a one-line "read the SKILL.md" pointer plus a
#: fallback line; anything fatter has leaked logic that belongs in the SKILL.
SHIM_MAX_BODY_LINES: int = 25

#: description_drift heuristic: a shim/SKILL description pair whose shared-token
#: ratio (intersection / smaller-set size) falls below this is flagged. Crude by
#: design — it catches a shim that describes a *different* command than its
#: SKILL, not stylistic paraphrase. Calibrated against the real plugin: a punchy
#: shim paired with a longer, more detailed SKILL legitimately shares only ~35%
#: of the smaller token set (e.g. `loop`), so the floor sits below that — the
#: pass fires on genuinely divergent vocabulary (near-zero overlap), not on
#: shim-shorter/skill-longer phrasing. Tunable; documented as a heuristic.
DESCRIPTION_OVERLAP_MIN: float = 0.25

#: Stopwords excluded from the description-overlap token sets — generic plumbing
#: words carry no signal about whether two descriptions describe the same thing.
_STOPWORDS: frozenset[str] = frozenset(
    {
        "use",
        "to",
        "the",
        "a",
        "an",
        "and",
        "or",
        "of",
        "for",
        "in",
        "on",
        "it",
        "is",
        "its",
        "when",
        "user",
        "wants",
        "via",
        "with",
        "by",
        "then",
        "this",
        "that",
        "renmark",
    }
)

_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9-]*")

AUDITS_SUBDIR = ".renmark/audits"


# ── Inventory ───────────────────────────────────────────────────────────────


@dataclass
class CommandEntry:
    """One audited command — harvested from its shim + SKILL.md frontmatter."""

    name: str
    shim_path: str
    skill_path: str
    description: str
    argument_hint: str
    domain: str
    skill_class: str
    shim_body_lines: int
    skill_lines: int
    has_skill: bool

    def as_dict(self) -> dict[str, Any]:
        from dataclasses import asdict

        return asdict(self)


def _plugin_dir(repo: Path) -> Path:
    return repo / "plugin"


def _frontmatter_and_body(text: str) -> tuple[dict[str, Any], str]:
    """Return (frontmatter-dict, body-after-frontmatter). Empty dict if none."""
    fm = lint.parse_frontmatter(text)
    if fm is None:
        return {}, text
    m = lint._FRONTMATTER_RE.match(text)
    body = text[m.end() :] if m else text
    return fm, body


def _nonblank_lines(text: str) -> int:
    return sum(1 for line in text.splitlines() if line.strip())


def build_inventory(repo: Path | str) -> list[CommandEntry]:
    """Harvest a flat per-command inventory from the plugin tree.

    Pure parsing — no LLM. One entry per ``plugin/commands/*.md`` shim, joined
    to its ``plugin/skills/<name>/SKILL.md`` (when present). Domain and class are
    resolved via :func:`lifecycle.domain_of` / :func:`lifecycle.skill_class`.
    Entries are sorted by command name. Never raises — an unreadable file
    degrades to empty strings / zero counts for that entry's missing fields.
    """
    repo = Path(repo)
    plugin = _plugin_dir(repo)
    commands_dir = plugin / "commands"
    skills_dir = plugin / "skills"
    entries: list[CommandEntry] = []
    if not commands_dir.is_dir():
        return entries

    for shim in sorted(commands_dir.glob("*.md")):
        name = shim.stem
        try:
            shim_text = shim.read_text(encoding="utf-8")
        except OSError:
            shim_text = ""
        fm, body = _frontmatter_and_body(shim_text)

        skill_md = skills_dir / name / "SKILL.md"
        has_skill = skill_md.exists()
        skill_lines = 0
        if has_skill:
            try:
                skill_lines = len(skill_md.read_text(encoding="utf-8").splitlines())
            except OSError:
                skill_lines = 0

        entries.append(
            CommandEntry(
                name=name,
                shim_path=str(shim.relative_to(repo)).replace("\\", "/"),
                skill_path=str(skill_md.relative_to(repo)).replace("\\", "/") if has_skill else "",
                description=str(fm.get("description", "")).strip(),
                argument_hint=str(fm.get("argument-hint", "")).strip(),
                domain=lifecycle.domain_of(name),
                skill_class=lifecycle.skill_class(name),
                shim_body_lines=_nonblank_lines(body),
                skill_lines=skill_lines,
                has_skill=has_skill,
            )
        )
    return entries


# ── Novel deterministic passes ────────────────────────────────────────────────


def registry_sync(repo: Path | str) -> list[str]:
    """Diff the lifecycle registries against the actual ``plugin/skills/`` dirs.

    Reports drift in BOTH directions:
    - **ghost** — a name in ``DOMAIN_BY_SKILL`` / ``IMPLEMENTED_SKILLS`` /
      class-set (pipeline + gate + aux) that has no backing skill directory.
    - **missing** — a shipped skill directory absent from a registry.

    The class-set membership check is the union of ``PIPELINE_SKILLS``,
    ``GATE_SKILLS`` and ``AUX_SKILLS`` — every shipped skill must belong to
    exactly one class (``skill_class`` defaults unknown skills to ``aux``, so the
    only failure this surfaces is a *dir without any explicit class entry*,
    which would silently default rather than be classified on purpose).

    Returns a sorted issue list (empty = in sync). Never raises.
    """
    repo = Path(repo)
    skills_dir = _plugin_dir(repo) / "skills"
    dirs = (
        {
            d.name
            for d in skills_dir.iterdir()
            if d.is_dir() and not d.name.startswith("_") and (d / "SKILL.md").exists()
        }
        if skills_dir.is_dir()
        else set()
    )

    class_union = set(lifecycle.PIPELINE_SKILLS) | set(lifecycle.GATE_SKILLS) | set(lifecycle.AUX_SKILLS)

    registries: list[tuple[str, set[str]]] = [
        ("IMPLEMENTED_SKILLS", set(lifecycle.IMPLEMENTED_SKILLS)),
        ("DOMAIN_BY_SKILL", set(lifecycle.DOMAIN_BY_SKILL)),
        ("class-sets", class_union),
    ]

    issues: list[str] = []
    for label, reg in registries:
        for ghost in sorted(reg - dirs):
            issues.append(f"registry-sync: {label} lists '{ghost}' but no plugin/skills/{ghost}/ exists (ghost)")
        for missing in sorted(dirs - reg):
            issues.append(f"registry-sync: plugin/skills/{missing}/ has no entry in {label} (missing)")
    return sorted(set(issues))


def shim_thinness(repo: Path | str, *, inventory: list[CommandEntry] | None = None) -> list[str]:
    """Flag command shims that are too fat or don't reference their SKILL.md.

    A shim is a thin pointer: its non-frontmatter body should be ≤
    :data:`SHIM_MAX_BODY_LINES` non-blank lines AND must contain the literal
    ``skills/<name>/SKILL.md`` reference (so the slash command actually routes to
    its skill). Either failure is reported. Never raises.
    """
    repo = Path(repo)
    inv = inventory if inventory is not None else build_inventory(repo)
    issues: list[str] = []
    for e in inv:
        if e.shim_body_lines > SHIM_MAX_BODY_LINES:
            issues.append(
                f"shim-thinness: commands/{e.name}.md body is {e.shim_body_lines} lines "
                f"(max {SHIM_MAX_BODY_LINES}) — move logic into the SKILL.md"
            )
        shim_file = repo / e.shim_path
        try:
            text = shim_file.read_text(encoding="utf-8")
        except OSError:
            text = ""
        if f"skills/{e.name}/SKILL.md" not in text:
            issues.append(f"shim-thinness: commands/{e.name}.md does not reference skills/{e.name}/SKILL.md")
    return sorted(set(issues))


def _tokens(text: str) -> set[str]:
    return {t for t in _TOKEN_RE.findall(text.lower()) if t not in _STOPWORDS and len(t) > 1}


def description_drift(repo: Path | str, *, inventory: list[CommandEntry] | None = None) -> list[str]:
    """Flag shim↔SKILL description pairs that share too little vocabulary.

    Heuristic (crude but deterministic): tokenize both descriptions (lowercase,
    drop stopwords + 1-char tokens), then compute the overlap ratio
    ``|shim ∩ skill| / min(|shim|, |skill|)``. A pair below
    :data:`DESCRIPTION_OVERLAP_MIN` is flagged — the shim likely describes a
    different command than its SKILL. Pairs where either description is empty,
    or either token set is empty, are skipped (presence is the lint's job, not
    this pass's). Never raises.
    """
    repo = Path(repo)
    inv = inventory if inventory is not None else build_inventory(repo)
    issues: list[str] = []
    for e in inv:
        if not e.has_skill or not e.description:
            continue
        skill_md = repo / e.skill_path
        try:
            skill_fm = lint.parse_frontmatter(skill_md.read_text(encoding="utf-8")) or {}
        except OSError:
            continue
        skill_desc = str(skill_fm.get("description", "")).strip()
        if not skill_desc:
            continue
        shim_tokens = _tokens(e.description)
        skill_tokens = _tokens(skill_desc)
        if not shim_tokens or not skill_tokens:
            continue
        overlap = len(shim_tokens & skill_tokens) / min(len(shim_tokens), len(skill_tokens))
        if overlap < DESCRIPTION_OVERLAP_MIN:
            issues.append(
                f"description-drift: commands/{e.name}.md vs SKILL.md share only "
                f"{overlap:.0%} of tokens (min {DESCRIPTION_OVERLAP_MIN:.0%}) — "
                "descriptions may describe different commands"
            )
    return sorted(set(issues))


# ── Composition ───────────────────────────────────────────────────────────────


@dataclass
class AuditReport:
    """Structured result of :func:`run_audit`. JSON-trivial."""

    quick: bool
    passes: dict[str, list[str]] = field(default_factory=dict)
    modularity_counts: dict[str, int] = field(default_factory=dict)
    inventory_count: int = 0

    @property
    def total_issues(self) -> int:
        return sum(len(v) for v in self.passes.values())

    @property
    def ok(self) -> bool:
        return self.total_issues == 0

    def as_dict(self) -> dict[str, Any]:
        return {
            "quick": self.quick,
            "passes": self.passes,
            "pass_counts": {k: len(v) for k, v in self.passes.items()},
            "modularity_counts": self.modularity_counts,
            "inventory_count": self.inventory_count,
            "total_issues": self.total_issues,
            "verdict": "PASS" if self.ok else "ISSUES",
        }


def run_audit(repo: Path | str, *, quick: bool = False) -> AuditReport:
    """Run the full deterministic audit and return a structured report.

    Always runs: ``registry_sync`` + ``shim_thinness`` + ``description_drift`` +
    the composed ``lint.lint_all`` (with the strict-YAML frontmatter pass
    **enabled** — those frontmatters are fixed in this wave) + ``release.check_drift``.

    Non-quick additionally runs ``modularity.analyze`` and records its
    danger/warn/info counts (advisory — never folds into the issue total).
    Never raises into the caller.
    """
    repo = Path(repo)
    inv = build_inventory(repo)
    plugin = _plugin_dir(repo)

    passes: dict[str, list[str]] = {}
    passes["registry-sync"] = registry_sync(repo)
    passes["shim-thinness"] = shim_thinness(repo, inventory=inv)
    passes["description-drift"] = description_drift(repo, inventory=inv)
    passes["lint"] = lint.lint_all(plugin, include_frontmatter_strict=True)
    try:
        passes["version-drift"] = release.drift_report(repo)
    except (FileNotFoundError, OSError):
        # User projects (where this skill ships) may have no VERSION file —
        # degrade to an advisory line instead of crashing the whole audit.
        passes["version-drift"] = ["VERSION file not found — version parity skipped"]

    report = AuditReport(quick=quick, passes=passes, inventory_count=len(inv))

    if not quick:
        gaps = modularity.analyze(repo)
        counts: dict[str, int] = {}
        for g in gaps:
            counts[g.severity] = counts.get(g.severity, 0) + 1
        report.modularity_counts = counts

    return report


# ── Artifact writers ───────────────────────────────────────────────────────────


def _audits_dir(repo: Path) -> Path:
    d = repo / AUDITS_SUBDIR
    d.mkdir(parents=True, exist_ok=True)
    return d


def _today() -> str:
    return date.today().isoformat()


def write_inventory(repo: Path | str, *, inventory: list[CommandEntry] | None = None) -> dict[str, str]:
    """Write the command inventory to ``.renmark/audits/inventory-<date>.md`` (+ .json).

    The .md is written via :func:`summary.write_artifact` so G6 provenance
    metadata is automatic; the .json mirror is plain JSON. Returns
    ``{"md": <path>, "json": <path>}``.
    """
    repo = Path(repo)
    inv = inventory if inventory is not None else build_inventory(repo)
    out_dir = _audits_dir(repo)
    today = _today()

    # Markdown table body.
    rows = ["| command | domain | class | shim lines | skill lines | description |", "|---|---|---|---|---|---|"]
    for e in inv:
        desc = (e.description[:80] + "…") if len(e.description) > 80 else e.description
        desc = desc.replace("|", "\\|")
        skill_cell = str(e.skill_lines) if e.has_skill else "—"
        rows.append(f"| {e.name} | {e.domain} | {e.skill_class} | {e.shim_body_lines} | {skill_cell} | {desc} |")
    body = "# renmark command inventory\n\n" + "\n".join(rows)

    n_missing = sum(1 for e in inv if not e.has_skill)
    summary_lines = [
        f"{len(inv)} commands harvested from plugin/commands/*.md",
        f"{len(inv) - n_missing} have a backing SKILL.md, {n_missing} missing",
        f"domains: {_count_str(e.domain for e in inv)}",
        f"classes: {_count_str(e.skill_class for e in inv)}",
    ]

    md_path = out_dir / f"inventory-{today}.md"
    summary.write_artifact(
        md_path,
        artifact_type="audit",
        body=body,
        summary_lines=summary_lines,
        source_sha=summary.git_head_sha(repo),
        generator="renmark-audit",
        confidence="high",
        validation_status="validated",
    )

    json_path = out_dir / f"inventory-{today}.json"
    json_path.write_text(json.dumps([e.as_dict() for e in inv], indent=2) + "\n", encoding="utf-8")

    return {"md": str(md_path), "json": str(json_path)}


def write_audit_report(repo: Path | str, report: AuditReport) -> dict[str, str]:
    """Write the audit report to ``.renmark/audits/audit-report-<date>.md`` (+ .json).

    The .md is written via :func:`summary.write_artifact` (G6 provenance auto);
    the .json mirror is plain JSON. Returns ``{"md": <path>, "json": <path>}``.
    """
    repo = Path(repo)
    out_dir = _audits_dir(repo)
    today = _today()

    sections = ["# renmark audit report", ""]
    for pass_name, pass_issues in report.passes.items():
        sections.append(f"## {pass_name} ({len(pass_issues)} issue{'s' if len(pass_issues) != 1 else ''})")
        if pass_issues:
            sections.extend(f"- {i}" for i in pass_issues)
        else:
            sections.append("- (clean)")
        sections.append("")
    if not report.quick and report.modularity_counts:
        mc = report.modularity_counts
        sections.append("## modularity (advisory)")
        sections.append(f"- danger={mc.get('danger', 0)} warn={mc.get('warn', 0)} info={mc.get('info', 0)}")
        sections.append("")
    body = "\n".join(sections).rstrip()

    verdict = "PASS" if report.ok else "ISSUES"
    summary_lines = [f"verdict: {verdict} ({report.total_issues} issues across {len(report.passes)} passes)"]
    for pass_name, pass_issues in report.passes.items():
        if pass_issues:
            summary_lines.append(f"{pass_name}: {len(pass_issues)}")
        if len(summary_lines) >= summary.MAX_SUMMARY_LINES:
            break
    if len(summary_lines) == 1:
        summary_lines.append("all passes clean")

    md_path = out_dir / f"audit-report-{today}.md"
    summary.write_artifact(
        md_path,
        artifact_type="audit",
        body=body,
        summary_lines=summary_lines[: summary.MAX_SUMMARY_LINES],
        source_sha=summary.git_head_sha(repo),
        generator="renmark-audit",
        completion_state="complete",
        confidence="high",
        validation_status="validated" if report.ok else "failed",
    )

    json_path = out_dir / f"audit-report-{today}.json"
    json_path.write_text(json.dumps(report.as_dict(), indent=2) + "\n", encoding="utf-8")

    return {"md": str(md_path), "json": str(json_path)}


def _count_str(values: Any) -> str:
    counts: dict[str, int] = {}
    for v in values:
        counts[v] = counts.get(v, 0) + 1
    return ", ".join(f"{k}={n}" for k, n in sorted(counts.items()))


# ── CLI ──────────────────────────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    repo = Path(".")
    quick = False
    inventory_only = False
    as_json = False

    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--repo" and i + 1 < len(argv):
            repo = Path(argv[i + 1])
            i += 2
        elif arg == "--quick":
            quick = True
            i += 1
        elif arg == "--inventory-only":
            inventory_only = True
            i += 1
        elif arg == "--json":
            as_json = True
            i += 1
        elif arg in ("-h", "--help"):
            sys.stdout.write("usage: python -m renmark.audit [--quick] [--inventory-only] [--json] [--repo PATH]\n")
            return 0
        else:
            sys.stderr.write(f"unknown arg: {arg}\n")
            return 2

    if not (repo / "plugin").is_dir():
        sys.stderr.write(f"no plugin/ directory under {repo}\n")
        return 2

    if inventory_only:
        inv = build_inventory(repo)
        paths = write_inventory(repo, inventory=inv)
        if as_json:
            sys.stdout.write(json.dumps({"inventory_count": len(inv), "paths": paths}) + "\n")
        else:
            sys.stdout.write(f"inventory: {len(inv)} commands\n")
            sys.stdout.write(f"  md:   {paths['md']}\n")
            sys.stdout.write(f"  json: {paths['json']}\n")
        return 0

    report = run_audit(repo, quick=quick)
    inv_paths = write_inventory(repo)
    report_paths = write_audit_report(repo, report)

    if as_json:
        sys.stdout.write(
            json.dumps(
                {
                    "report": report.as_dict(),
                    "inventory": inv_paths,
                    "report_artifact": report_paths,
                }
            )
            + "\n"
        )
        return 0 if report.ok else 1

    # Bounded ≤5-line stdout: counts per pass + artifact path + verdict.
    counts = " ".join(f"{k}={len(v)}" for k, v in report.passes.items())
    sys.stdout.write(f"audit ({'quick' if quick else 'full'}): {counts}\n")
    if not quick and report.modularity_counts:
        mc = report.modularity_counts
        sys.stdout.write(f"  modularity (advisory): danger={mc.get('danger', 0)} warn={mc.get('warn', 0)}\n")
    sys.stdout.write(f"  report: {report_paths['md']}\n")
    sys.stdout.write(f"  inventory: {inv_paths['md']} ({report.inventory_count} commands)\n")
    sys.stdout.write(f"{'PASS' if report.ok else 'ISSUES'} ({report.total_issues} issues)\n")
    return 0 if report.ok else 1


if __name__ == "__main__":
    sys.exit(main())

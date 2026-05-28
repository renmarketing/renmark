"""Persistent project memory at `.renmark/memory/`.

Files act as living documentation — features shipped, bugs fixed, decisions
recorded, conventions documented, executor routing tuned. Skills read what
they need, append on relevant events, and never rewrite history.

Each memory file follows a documented format defined by its template under
`plugin/templates/memory/<name>.md.template`. Helpers below append into the
right section (most files are organized newest-first per CHANGELOG convention).
"""

from __future__ import annotations

import datetime as dt
import re
import shutil
from pathlib import Path

from .state import MEMORY_SUBDIR, RENMARK_DIR_NAME

MEMORY_FILES = (
    "INDEX.md",
    "project.md",
    "stack.md",
    "architecture.md",
    "features.md",
    "bugs.md",
    "decisions.md",
    "conventions.md",
    "routing.md",
    "learnings.md",
)


def memory_dir(repo: str | Path) -> Path:
    return Path(repo) / RENMARK_DIR_NAME / MEMORY_SUBDIR


def template_dir() -> Path | None:
    """Locate the plugin's memory templates.

    Honors `RENMARK_TEMPLATES` env var (mainly for tests). Otherwise walks
    up from this file looking for `plugin/templates/memory/`.
    """
    import os

    explicit = os.environ.get("RENMARK_TEMPLATES")
    if explicit:
        p = Path(explicit) / "memory"
        if p.is_dir():
            return p
    here = Path(__file__).resolve()
    for parent in here.parents:
        cand = parent / "plugin" / "templates" / "memory"
        if cand.is_dir():
            return cand
    return None


def ensure_memory(repo: str | Path) -> Path:
    """Create `.renmark/memory/` from templates if it doesn't exist yet.

    Returns the memory directory. Idempotent: existing files are not
    overwritten.
    """
    d = memory_dir(repo)
    d.mkdir(parents=True, exist_ok=True)
    tdir = template_dir()
    if tdir is None:
        # Templates missing — write minimal placeholders so callers don't NPE.
        for name in MEMORY_FILES:
            f = d / name
            if not f.exists():
                f.write_text(f"# {name[:-3]}\n\n(Auto-created. Templates not found.)\n", encoding="utf-8")
        return d
    for name in MEMORY_FILES:
        target = d / name
        if target.exists():
            continue
        src = tdir / f"{name}.template"
        if src.is_file():
            shutil.copy(src, target)
        else:
            target.write_text(f"# {name[:-3]}\n", encoding="utf-8")
    return d


def read_index(repo: str | Path) -> str:
    return (ensure_memory(repo) / "INDEX.md").read_text(encoding="utf-8")


def read_file(repo: str | Path, name: str) -> str:
    if name not in MEMORY_FILES:
        raise ValueError(f"unknown memory file: {name}")
    return (ensure_memory(repo) / name).read_text(encoding="utf-8")


def _today() -> str:
    return dt.date.today().isoformat()


def _insert_after_section(text: str, section_header: str, new_block: str) -> str:
    """Insert `new_block` immediately after the line matching `section_header`.

    `section_header` is matched as a markdown header line (e.g., "## Shipped").
    If the section is not found, the block is appended at the end of the file
    under a new H2 with that name.
    """
    lines = text.splitlines(keepends=True)
    pattern = re.compile(r"^" + re.escape(section_header) + r"\s*$")
    for i, line in enumerate(lines):
        if pattern.match(line.rstrip("\n")):
            # Skip any blank lines immediately following the header so the
            # new block starts cleanly.
            j = i + 1
            while j < len(lines) and lines[j].strip() == "":
                j += 1
            return "".join(lines[:j]) + "\n" + new_block.rstrip() + "\n\n" + "".join(lines[j:])
    return text.rstrip("\n") + f"\n\n{section_header}\n\n{new_block.rstrip()}\n"


def log_feature(
    repo: str | Path,
    *,
    title: str,
    files: list[str] | None = None,
    spec: str | None = None,
    plan: str | None = None,
    commits: str | None = None,
    description: str = "",
    section: str = "Shipped",
    date: str | None = None,
) -> None:
    """Append a feature entry to `features.md`.

    Section defaults to "Shipped". Pass "In progress" or "Planned" otherwise.
    """
    ensure_memory(repo)
    path = memory_dir(repo) / "features.md"
    block_lines = [f"### {date or _today()} — {title}", ""]
    if files:
        block_lines.append(f"**Files:** {', '.join(f'`{f}`' for f in files)}")
    if spec:
        block_lines.append(f"**Spec:** `{spec}`")
    if plan:
        block_lines.append(f"**Plan:** `{plan}`")
    if commits:
        block_lines.append(f"**Commits:** `{commits}`")
    if description:
        block_lines.extend(["", description.strip()])
    block_lines.extend(["", "---"])
    new = "\n".join(block_lines)
    text = path.read_text(encoding="utf-8")
    path.write_text(_insert_after_section(text, f"## {section}", new), encoding="utf-8")


def log_bug(
    repo: str | Path,
    *,
    title: str,
    severity: str,  # critical | major | minor
    symptom: str,
    root_cause: str | None = None,
    fix: str | None = None,
    lesson: str | None = None,
    section: str = "Fixed",  # or "Open"
    date: str | None = None,
) -> None:
    """Append a bug entry to `bugs.md`. If `lesson` is given, also appends to learnings.md."""
    ensure_memory(repo)
    path = memory_dir(repo) / "bugs.md"
    block = [
        f"### {date or _today()} — {title}",
        "",
        f"**Severity:** {severity}",
        f"**Symptom:** {symptom}",
    ]
    if root_cause:
        block.append(f"**Root cause:** {root_cause}")
    if fix:
        block.append(f"**Fix:** {fix}")
    if lesson:
        block.append(f"**Lesson:** {lesson}")
    block.extend(["", "---"])
    new = "\n".join(block)
    text = path.read_text(encoding="utf-8")
    path.write_text(_insert_after_section(text, f"## {section}", new), encoding="utf-8")

    if lesson:
        append_learning(repo, signal=title, observation=lesson, source="bug")


def log_decision(
    repo: str | Path,
    *,
    title: str,
    status: str = "Accepted",  # Accepted | Proposed | Deprecated | Superseded
    context: str = "",
    decision: str = "",
    alternatives: list[str] | None = None,
    consequences: list[str] | None = None,
    date: str | None = None,
) -> None:
    """Append an ADR to `decisions.md`. Auto-numbers based on existing ADRs."""
    ensure_memory(repo)
    path = memory_dir(repo) / "decisions.md"
    text = path.read_text(encoding="utf-8")
    n = len(re.findall(r"^## ADR-(\d+)", text, flags=re.MULTILINE))
    # If the template's example ADR-000 is still present and untouched,
    # don't count it; start real ADRs at 001.
    next_id = max(n, 1) if "ADR-000" in text else n
    block = [
        f"## ADR-{next_id:03d} — {title}",
        "",
        f"**Date:** {date or _today()}",
        f"**Status:** {status}",
        "",
    ]
    if context:
        block.extend([f"**Context.** {context}", ""])
    if decision:
        block.extend([f"**Decision.** {decision}", ""])
    if alternatives:
        block.append("**Alternatives considered.**")
        for a in alternatives:
            block.append(f"- {a}")
        block.append("")
    if consequences:
        block.append("**Consequences.**")
        for c in consequences:
            block.append(f"- {c}")
        block.append("")
    block.append("---")
    new = "\n".join(block)
    # Decisions appears newest-first under the document H1; insert after H1.
    path.write_text(_insert_after_section(text, "# Decisions (ADRs)", new), encoding="utf-8")


def append_routing(
    repo: str | Path,
    *,
    signature: str,  # e.g. "target=tests/**, complexity=medium"
    executor: str,
    outcome: str,  # "passed" | "failed" | "retried"
    run_id: str | None = None,
    date: str | None = None,
) -> None:
    """Append a routing observation to `routing.md` under 'Learned overrides'."""
    ensure_memory(repo)
    path = memory_dir(repo) / "routing.md"
    text = path.read_text(encoding="utf-8")
    line = f"- ({date or _today()}) `{signature}` → **{executor}** ({outcome}"
    if run_id:
        line += f", run={run_id}"
    line += ")"
    if "## Learned overrides" in text:
        path.write_text(_insert_after_section(text, "## Learned overrides", line), encoding="utf-8")
    else:
        path.write_text(text.rstrip() + "\n\n## Learned overrides\n\n" + line + "\n", encoding="utf-8")


def append_learning(
    repo: str | Path,
    *,
    signal: str,
    observation: str,
    source: str = "run",  # "run" | "bug" | "review"
    model: str | None = None,
    date: str | None = None,
) -> None:
    """Append a pattern observation to `learnings.md` under 'Learned this project'."""
    ensure_memory(repo)
    path = memory_dir(repo) / "learnings.md"
    text = path.read_text(encoding="utf-8")
    parts = [f"- ({date or _today()}, {source})"]
    if model:
        parts.append(f"model `{model}`:")
    parts.append(f"**{signal}** — {observation}")
    line = " ".join(parts)
    if "## Learned this project" in text:
        path.write_text(_insert_after_section(text, "## Learned this project", line), encoding="utf-8")
    else:
        path.write_text(text.rstrip() + "\n\n## Learned this project\n\n" + line + "\n", encoding="utf-8")

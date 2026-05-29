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
import hashlib
import re
import shutil
from dataclasses import dataclass
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
    """Append an ADR to `decisions.md`. Auto-numbers based on existing ADRs.

    Idempotent: if an ADR with the same `(title, date)` already exists, this
    is a no-op. Parsing errors are treated conservatively — if any block can't
    be parsed cleanly, the short-circuit is skipped and the write proceeds.
    """
    ensure_memory(repo)
    path = memory_dir(repo) / "decisions.md"
    text = path.read_text(encoding="utf-8")
    # Idempotency short-circuit: check for an existing ADR with same title+date.
    try:
        target_title = title.strip()
        target_date = (date or _today()).strip()
        # Find all ADR headers and their position in the text.
        adr_iter = list(re.finditer(r"^## ADR-\d+\s+—\s+(.+?)\s*$", text, flags=re.MULTILINE))
        for i, m in enumerate(adr_iter):
            existing_title = m.group(1).strip()
            if existing_title != target_title:
                continue
            # Look for **Date:** within this ADR block (up to next ADR header).
            block_start = m.end()
            block_end = adr_iter[i + 1].start() if i + 1 < len(adr_iter) else len(text)
            adr_body = text[block_start:block_end]
            date_m = re.search(r"^\*\*Date:\*\*\s*(\S+)", adr_body, flags=re.MULTILINE)
            if date_m and date_m.group(1).strip() == target_date:
                return  # Duplicate ADR — no-op.
    except Exception:
        # Conservative: parsing failed, let the write proceed.
        pass
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


# ---------------------------------------------------------------------------
# Memory log maintenance: dedupe + age-out
# ---------------------------------------------------------------------------

_DEDUPE_ALLOWED = ("learnings.md", "bugs.md", "features.md")
_CURATED_FILES = (
    "decisions.md",
    "INDEX.md",
    "project.md",
    "stack.md",
    "architecture.md",
    "conventions.md",
    "routing.md",
    "dev-standards.md",
    "MEMORY.md",
    "project-map.md",
)


@dataclass(frozen=True)
class _MemoryEntry:
    schema: str
    title: str
    date: str | None
    raw: str
    start: int
    end: int
    section_header: str


_SCHEMA_BY_NAME: dict[str, str] = {
    "features.md": "features",
    "bugs.md": "bugs",
    "learnings.md": "learnings",
}

_H3_HEADER_RE = re.compile(r"^###\s+(\d{4}-\d{2}-\d{2})\s+—\s+(.+?)\s*$")
_H2_SECTION_RE = re.compile(r"^##\s+(.+?)\s*$")
_LEARNING_BULLET_DATE_RE = re.compile(r"\((\d{4}-\d{2}-\d{2})")
_DATE_FIELD_RE = re.compile(r"^\*\*Date:\*\*\s*(\d{4}-\d{2}-\d{2})", flags=re.MULTILINE)


def _parse_h3_entries(text: str, schema: str) -> list[_MemoryEntry]:
    """Parse features.md / bugs.md — `### YYYY-MM-DD — Title` under `## Section`.

    Each entry's `raw` runs from the `###` line up to (but not including) the
    next `###` or `## Section` line, or EOF. A trailing `---` separator is
    included in `raw` if present.
    """
    lines = text.splitlines(keepends=True)
    # Pre-compute byte offsets for each line so we can return (start, end)
    # ranges in character positions over the original text.
    offsets: list[int] = []
    cur = 0
    for line in lines:
        offsets.append(cur)
        cur += len(line)
    offsets.append(cur)  # one past EOF

    entries: list[_MemoryEntry] = []
    current_section = ""
    n = len(lines)
    i = 0
    while i < n:
        line = lines[i]
        sec_m = _H2_SECTION_RE.match(line.rstrip("\n"))
        if sec_m:
            current_section = f"## {sec_m.group(1).strip()}"
            i += 1
            continue
        h3_m = _H3_HEADER_RE.match(line.rstrip("\n"))
        if h3_m and current_section:
            date = h3_m.group(1)
            title = h3_m.group(2).strip()
            start_line = i
            j = i + 1
            while j < n:
                ln = lines[j]
                if _H3_HEADER_RE.match(ln.rstrip("\n")):
                    break
                if _H2_SECTION_RE.match(ln.rstrip("\n")):
                    break
                j += 1
            end_line = j
            raw = "".join(lines[start_line:end_line])
            entries.append(
                _MemoryEntry(
                    schema=schema,
                    title=title,
                    date=date,
                    raw=raw,
                    start=offsets[start_line],
                    end=offsets[end_line],
                    section_header=current_section,
                ),
            )
            i = end_line
            continue
        i += 1
    return entries


def _parse_learning_entries(text: str) -> list[_MemoryEntry]:
    """Parse learnings.md — top-level `- ` bullets under `## Section`.

    A bullet runs from its `-` line to (but not including) the next top-level
    bullet, the next `## Section`, or EOF. Indented continuation lines belong
    to the preceding bullet.
    """
    allowed_sections = {"## Common patterns", "## Learned this project"}
    lines = text.splitlines(keepends=True)
    offsets: list[int] = []
    cur = 0
    for line in lines:
        offsets.append(cur)
        cur += len(line)
    offsets.append(cur)

    entries: list[_MemoryEntry] = []
    current_section = ""
    n = len(lines)
    i = 0
    while i < n:
        raw_line = lines[i]
        stripped_nl = raw_line.rstrip("\n")
        sec_m = _H2_SECTION_RE.match(stripped_nl)
        if sec_m:
            current_section = f"## {sec_m.group(1).strip()}"
            i += 1
            continue
        if current_section in allowed_sections and stripped_nl.startswith("- "):
            start_line = i
            j = i + 1
            saw_blank = False
            while j < n:
                ln = lines[j]
                ln_no_nl = ln.rstrip("\n")
                if ln_no_nl.startswith("- "):
                    break
                if _H2_SECTION_RE.match(ln_no_nl):
                    break
                # Blank line is provisional — extend through it; but if we
                # then see a non-indented, non-bullet, non-section line,
                # that's a paragraph break (e.g. template placeholders),
                # so end the bullet at the blank line.
                if ln_no_nl.strip() == "":
                    saw_blank = True
                    j += 1
                    continue
                if saw_blank and not (ln_no_nl.startswith(" ") or ln_no_nl.startswith("\t")):
                    # Non-indented paragraph after a blank — bullet ended at the blank.
                    break
                saw_blank = False
                j += 1
            # Trim trailing blank-only lines so the bullet's raw doesn't
            # absorb separator whitespace into its signature.
            while j > start_line + 1 and lines[j - 1].strip() == "":
                j -= 1
            end_line = j
            raw = "".join(lines[start_line:end_line])
            bullet_text = stripped_nl[2:].strip()
            title = bullet_text[:80] if bullet_text else ""
            date_m = _LEARNING_BULLET_DATE_RE.search(raw)
            date = date_m.group(1) if date_m else None
            entries.append(
                _MemoryEntry(
                    schema="learnings",
                    title=title,
                    date=date,
                    raw=raw,
                    start=offsets[start_line],
                    end=offsets[end_line],
                    section_header=current_section,
                ),
            )
            i = end_line
            continue
        i += 1
    return entries


def _parse_memory_entries(text: str, schema: str) -> list[_MemoryEntry]:
    """Dispatch parsing based on `schema` — one of features|bugs|learnings."""
    if schema in ("features", "bugs"):
        return _parse_h3_entries(text, schema)
    if schema == "learnings":
        return _parse_learning_entries(text)
    raise ValueError(f"unknown memory schema: {schema!r}")


def _remove_entries(text: str, entries: list[_MemoryEntry]) -> str:
    """Rebuild `text` with the given entries' `raw` spans excised.

    Spans are expected to be non-overlapping. They are sorted by `start` and
    removed in one pass — surrounding content (section headers, blank lines,
    preamble) is preserved unchanged.
    """
    if not entries:
        return text
    ordered = sorted(entries, key=lambda e: e.start)
    out_parts: list[str] = []
    cursor = 0
    for e in ordered:
        if e.start < cursor:
            # Overlap — defensive: skip to end of this entry.
            cursor = max(cursor, e.end)
            continue
        out_parts.append(text[cursor : e.start])
        cursor = e.end
    out_parts.append(text[cursor:])
    return "".join(out_parts)


def dedupe_memory_log(repo: str | Path, name: str, *, dry_run: bool = False) -> int:
    """Remove duplicate entries from a memory log, keeping the first occurrence.

    Only operates on the append-style logs: `learnings.md`, `bugs.md`,
    `features.md`. Curated files (decisions.md, project.md, etc.) raise
    ValueError.

    Schema-aware: features/bugs use `###` entries under `##` sections;
    learnings use top-level `-` bullets under `##` sections.

    Duplicate signature: `(title.strip(), sha256(raw.strip())[:12])`. Files
    are newest-first; keeping the first occurrence preserves the most recent
    copy of each repeated entry. Returns the number of duplicate entries
    removed; with `dry_run=True`, no write.
    """
    if name in _CURATED_FILES:
        raise ValueError(
            f"refusing to dedupe curated memory file '{name}'; "
            f"allowed: {list(_DEDUPE_ALLOWED)}; curated: {list(_CURATED_FILES)}"
        )
    if name not in _DEDUPE_ALLOWED:
        raise ValueError(f"unknown memory log '{name}'; allowed: {list(_DEDUPE_ALLOWED)}")
    schema = _SCHEMA_BY_NAME[name]
    ensure_memory(repo)
    path = memory_dir(repo) / name
    text = path.read_text(encoding="utf-8")
    entries = _parse_memory_entries(text, schema)
    seen: set[tuple[str, str]] = set()
    duplicates: list[_MemoryEntry] = []
    for entry in entries:
        digest = hashlib.sha256(entry.raw.strip().encode("utf-8")).hexdigest()[:12]
        sig = (entry.title.strip(), digest)
        if sig in seen:
            duplicates.append(entry)
            continue
        seen.add(sig)
    removed = len(duplicates)
    if removed == 0 or dry_run:
        return removed
    rebuilt = _remove_entries(text, duplicates)
    path.write_text(rebuilt, encoding="utf-8")
    return removed


def _entry_date_obj(entry: _MemoryEntry) -> dt.date | None:
    """Resolve an entry's date (H3 date, bullet date, or `**Date:**` field)."""
    if entry.date:
        try:
            return dt.date.fromisoformat(entry.date)
        except ValueError:
            pass
    dm = _DATE_FIELD_RE.search(entry.raw)
    if dm:
        try:
            return dt.date.fromisoformat(dm.group(1))
        except ValueError:
            return None
    return None


def age_out_memory_log(
    repo: str | Path,
    name: str,
    days: int,
    archive_root: Path,
    *,
    dry_run: bool = False,
) -> int:
    """Move entries older than `days` from a memory log into an archive file.

    Schema-aware (features/bugs `###` under `##`, learnings bullets under
    `##`). Entries without a parseable date are KEPT (safe default).

    Aged-out entries are appended to `archive_root/memory/<name>` grouped
    under their original `## Section` header so context is preserved. The
    archive write is idempotent across same-day re-runs: each section header
    is written at most once per call, but is reused if it already exists in
    the archive (the same set of moved entries can't be moved twice — they
    are excised from the source on the first call).

    Returns the count of entries moved. With `dry_run=True`, no files are
    written and no directories are created.
    """
    if name in _CURATED_FILES:
        raise ValueError(
            f"refusing to age out curated memory file '{name}'; "
            f"allowed: {list(_DEDUPE_ALLOWED)}; curated: {list(_CURATED_FILES)}"
        )
    if name not in _DEDUPE_ALLOWED:
        raise ValueError(f"unknown memory log '{name}'; allowed: {list(_DEDUPE_ALLOWED)}")
    schema = _SCHEMA_BY_NAME[name]
    ensure_memory(repo)
    path = memory_dir(repo) / name
    text = path.read_text(encoding="utf-8")
    entries = _parse_memory_entries(text, schema)
    today = dt.datetime.now(dt.timezone.utc).date()
    cutoff_delta = dt.timedelta(days=days)
    aged: list[_MemoryEntry] = []
    for entry in entries:
        entry_date = _entry_date_obj(entry)
        if entry_date is None:
            continue
        if (today - entry_date) > cutoff_delta:
            aged.append(entry)
    if not aged:
        return 0
    if dry_run:
        return len(aged)

    # Group aged entries by section header (preserve original order within
    # each section).
    grouped: dict[str, list[_MemoryEntry]] = {}
    section_order: list[str] = []
    for entry in aged:
        header = entry.section_header
        if header not in grouped:
            grouped[header] = []
            section_order.append(header)
        grouped[header].append(entry)

    archive_dir = Path(archive_root) / "memory"
    archive_dir.mkdir(parents=True, exist_ok=True)
    archive_file = archive_dir / name
    archive_existing = archive_file.read_text(encoding="utf-8") if archive_file.exists() else ""

    parts: list[str] = []
    if archive_existing:
        parts.append(archive_existing)
        if not archive_existing.endswith("\n"):
            parts.append("\n")
    for header in section_order:
        # Only emit the header if it isn't already present in the existing
        # archive content (idempotent append for repeat sections).
        if header not in archive_existing:
            parts.append(f"{header}\n\n")
        for entry in grouped[header]:
            parts.append(entry.raw)
            if not entry.raw.endswith("\n"):
                parts.append("\n")
    archive_file.write_text("".join(parts), encoding="utf-8")

    rebuilt = _remove_entries(text, aged)
    path.write_text(rebuilt, encoding="utf-8")
    return len(aged)


def log_escalation_decision(
    repo: str | Path,
    *,
    task_index: int,
    from_exec: str,
    to_exec: str,
    reason: str,
    plan_path: str | None = None,
) -> None:
    """Record an executor escalation as an ADR (best-effort, swallows errors).

    Title: `Escalated task {task_index} from {from_exec} to {to_exec}`.
    Passes today's date so the idempotency short-circuit in `log_decision`
    catches re-runs within the same day.
    """
    try:
        title = f"Escalated task {task_index} from {from_exec} to {to_exec}"
        context = (reason or "")[:200]
        if plan_path:
            context = f"{context} (plan: {plan_path})" if context else f"plan: {plan_path}"
        log_decision(
            repo,
            title=title,
            status="Accepted",
            context=context,
            decision=f"Re-route to {to_exec}",
            alternatives=[f"Retry {from_exec}", "Fail the task"],
            consequences=["Higher cost", "Higher capability"],
            date=_today(),
        )
    except Exception:
        # Best-effort: never raise.
        pass

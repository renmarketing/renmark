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


def _split_h2_entries(text: str) -> tuple[str, list[tuple[str, str]]]:
    """Split a markdown file into (preamble, [(h2_line, body), ...]).

    H2 boundary = a line starting with `## ` at column 0. Body includes
    everything from after the H2 line up to (but not including) the next H2
    or EOF. Preamble is everything before the first H2.
    """
    lines = text.splitlines(keepends=True)
    h2_re = re.compile(r"^## ")
    # Find H2 indices.
    h2_indices = [i for i, line in enumerate(lines) if h2_re.match(line)]
    if not h2_indices:
        return text, []
    preamble = "".join(lines[: h2_indices[0]])
    entries: list[tuple[str, str]] = []
    for idx, start in enumerate(h2_indices):
        end = h2_indices[idx + 1] if idx + 1 < len(h2_indices) else len(lines)
        h2_line = lines[start]
        body = "".join(lines[start + 1 : end])
        entries.append((h2_line, body))
    return preamble, entries


def _first_nonblank_line(body: str) -> str:
    for line in body.splitlines():
        s = line.strip()
        if s:
            return s
    return ""


def _h2_title(h2_line: str) -> str:
    # Strip leading "## " and trailing newline/whitespace.
    return h2_line.lstrip("#").strip()


def dedupe_memory_log(repo: str | Path, name: str, *, dry_run: bool = False) -> int:
    """Remove duplicate entries from a memory log, keeping the first occurrence.

    Only operates on the append-style logs: `learnings.md`, `bugs.md`,
    `features.md`. Curated files (decisions.md, project.md, etc.) raise
    ValueError.

    Duplicate signature: `(h2_title, sha256(first_nonblank_line_in_body)[:12])`.
    Files are newest-first, so keeping the first occurrence preserves the
    most recent copy of each repeated entry.

    Returns the number of duplicate entries removed. With `dry_run=True`,
    counts duplicates without writing.
    """
    if name in _CURATED_FILES:
        raise ValueError(
            f"refusing to dedupe curated memory file '{name}'; "
            f"allowed: {list(_DEDUPE_ALLOWED)}; curated: {list(_CURATED_FILES)}"
        )
    if name not in _DEDUPE_ALLOWED:
        raise ValueError(
            f"unknown memory log '{name}'; allowed: {list(_DEDUPE_ALLOWED)}"
        )
    ensure_memory(repo)
    path = memory_dir(repo) / name
    text = path.read_text(encoding="utf-8")
    preamble, entries = _split_h2_entries(text)
    seen: set[tuple[str, str]] = set()
    kept: list[tuple[str, str]] = []
    removed = 0
    for h2_line, body in entries:
        title = _h2_title(h2_line)
        first = _first_nonblank_line(body)
        digest = hashlib.sha256(first.encode("utf-8")).hexdigest()[:12]
        sig = (title, digest)
        if sig in seen:
            removed += 1
            continue
        seen.add(sig)
        kept.append((h2_line, body))
    if removed == 0 or dry_run:
        return removed
    rebuilt = preamble + "".join(h2 + body for h2, body in kept)
    path.write_text(rebuilt, encoding="utf-8")
    return removed


_DATE_RE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")
_DATE_FIELD_RE = re.compile(r"^\*\*Date:\*\*\s*(\d{4}-\d{2}-\d{2})", flags=re.MULTILINE)


def _entry_date(h2_line: str, body: str) -> dt.date | None:
    """Extract the first YYYY-MM-DD found in the H2 line or in a **Date:** body line."""
    m = _DATE_RE.search(h2_line)
    if not m:
        dm = _DATE_FIELD_RE.search(body)
        if dm:
            m = dm
    if not m:
        return None
    try:
        return dt.date.fromisoformat(m.group(1))
    except ValueError:
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

    Entries are parsed by H2 boundary. The first `YYYY-MM-DD` token found in
    the H2 line (or in a `**Date:**` line within the entry body) is the
    entry's age. Entries with no parseable date are KEPT (safe default).

    Aged-out entries are appended to `archive_root/memory/<name>` in their
    original (newest-first) order. The source file is rewritten without them.

    Returns the count of entries moved. With `dry_run=True`, no files are
    written and no directories are created.
    """
    if name in _CURATED_FILES:
        raise ValueError(
            f"refusing to age out curated memory file '{name}'; "
            f"allowed: {list(_DEDUPE_ALLOWED)}; curated: {list(_CURATED_FILES)}"
        )
    if name not in _DEDUPE_ALLOWED:
        raise ValueError(
            f"unknown memory log '{name}'; allowed: {list(_DEDUPE_ALLOWED)}"
        )
    ensure_memory(repo)
    path = memory_dir(repo) / name
    text = path.read_text(encoding="utf-8")
    preamble, entries = _split_h2_entries(text)
    today = dt.datetime.utcnow().date()
    cutoff_delta = dt.timedelta(days=days)
    kept: list[tuple[str, str]] = []
    aged: list[tuple[str, str]] = []
    for h2_line, body in entries:
        entry_date = _entry_date(h2_line, body)
        if entry_date is None:
            kept.append((h2_line, body))
            continue
        if (today - entry_date) > cutoff_delta:
            aged.append((h2_line, body))
        else:
            kept.append((h2_line, body))
    if not aged:
        return 0
    if dry_run:
        return len(aged)
    # Write archive: append aged entries to archive_root/memory/<name>.
    archive_dir = Path(archive_root) / "memory"
    archive_dir.mkdir(parents=True, exist_ok=True)
    archive_file = archive_dir / name
    archive_existing = archive_file.read_text(encoding="utf-8") if archive_file.exists() else ""
    archive_block = "".join(h2 + body for h2, body in aged)
    if archive_existing and not archive_existing.endswith("\n"):
        archive_existing += "\n"
    archive_file.write_text(archive_existing + archive_block, encoding="utf-8")
    # Rewrite source file without aged entries.
    rebuilt = preamble + "".join(h2 + body for h2, body in kept)
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

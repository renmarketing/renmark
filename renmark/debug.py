"""Debug session helpers — used by `/renmark:debug`.

A debug session is a structured loop:
  1. Reproduce — capture the symptom
  2. Hypothesize — list ranked guesses
  3. Investigate — run cheap inspections (greps, traces, reasoning)
  4. Root-cause — when a hypothesis is confirmed
  5. Fix — usually one file via /renmark:orchestrate, or Opus directly
  6. Verify — repro fails, regression test added

State lives in `.renmark/debug/<session-id>/session.md` so a debug run survives
`/clear`. This module exposes the file-format helpers; the skill drives the loop
conversationally with the user.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from . import memory as _memory
from . import state as _state


@dataclass
class DebugSession:
    session_id: str
    path: Path  # session.md inside .renmark/debug/<session_id>/

    @property
    def dir(self) -> Path:
        return self.path.parent


def new_session(repo: str | Path, symptom: str) -> DebugSession:
    """Create a fresh debug session directory + session.md skeleton."""
    sid = _state.new_run_id()
    repo_p = Path(repo)
    d = repo_p / _state.RENMARK_DIR_NAME / _state.DEBUG_SUBDIR / sid
    d.mkdir(parents=True, exist_ok=True)
    p = d / "session.md"
    p.write_text(
        f"# Debug session {sid}\n\n"
        f"**Started:** {_state.now_iso()}\n\n"
        f"## Symptom\n\n{symptom.strip()}\n\n"
        f"## Hypotheses\n\n(Ranked, newest at top.)\n\n"
        f"## Investigation log\n\n"
        f"## Root cause\n\n_(unknown)_\n\n"
        f"## Fix\n\n_(pending)_\n\n"
        f"## Verification\n\n_(pending)_\n",
        encoding="utf-8",
    )
    return DebugSession(session_id=sid, path=p)


def latest_session(repo: str | Path) -> DebugSession | None:
    """Return the most recently-modified debug session, or None."""
    base = Path(repo) / _state.RENMARK_DIR_NAME / _state.DEBUG_SUBDIR
    if not base.is_dir():
        return None
    candidates: list[tuple[float, Path]] = []
    for child in base.iterdir():
        if child.is_dir() and (child / "session.md").is_file():
            candidates.append((child.stat().st_mtime, child / "session.md"))
    if not candidates:
        return None
    candidates.sort(reverse=True)
    p = candidates[0][1]
    return DebugSession(session_id=p.parent.name, path=p)


def append_section(session: DebugSession, section: str, content: str) -> None:
    """Append `content` to a named section of session.md.

    Sections are H2 headings (`## Hypotheses`, etc.). If the section exists,
    append content right after the header. If not, create it at the end.
    """
    text = session.path.read_text(encoding="utf-8")
    block = content.rstrip() + "\n"
    header_pat = re.compile(rf"^## {re.escape(section)}\s*$", re.MULTILINE)
    m = header_pat.search(text)
    if m:
        insert_at = m.end()
        # Skip one trailing newline so we're on a fresh line.
        if insert_at < len(text) and text[insert_at] == "\n":
            insert_at += 1
        new_text = text[:insert_at] + "\n" + block + "\n" + text[insert_at:]
    else:
        new_text = text.rstrip() + f"\n\n## {section}\n\n{block}\n"
    session.path.write_text(new_text, encoding="utf-8")


def add_hypothesis(session: DebugSession, idx: int, title: str, likely: str) -> None:
    """Add a ranked hypothesis to the session."""
    append_section(session, "Hypotheses", f"{idx}. **{title}** — likely: {likely}")


def log_investigation(
    session: DebugSession,
    *,
    hypothesis: str,
    inspector: str,  # "haiku" | "codex" | "opus" | other executor string
    finding: str,
    rules_out: bool = False,
) -> None:
    """Append an investigation step to the log."""
    verdict = "RULES OUT" if rules_out else "noted"
    append_section(
        session,
        "Investigation log",
        f"- **{hypothesis}** (via {inspector}) → {verdict}: {finding}",
    )


def set_root_cause(session: DebugSession, root_cause: str) -> None:
    """Replace the Root cause section (single-value section)."""
    text = session.path.read_text(encoding="utf-8")
    new = re.sub(
        r"## Root cause\n\n.*?(?=\n## )",
        f"## Root cause\n\n{root_cause.strip()}\n\n",
        text,
        count=1,
        flags=re.DOTALL,
    )
    session.path.write_text(new, encoding="utf-8")


def close_session(
    session: DebugSession,
    repo: str | Path,
    *,
    title: str,
    severity: str,
    symptom: str,
    root_cause: str,
    fix: str,
    lesson: str | None = None,
) -> None:
    """Finalize a debug session and write a bug entry to .renmark/memory/bugs.md.

    Also optionally appends a generalizable lesson to learnings.md (via the
    log_bug helper, which auto-cross-posts).
    """
    _memory.log_bug(
        repo,
        title=title,
        severity=severity,
        symptom=symptom,
        root_cause=root_cause,
        fix=fix,
        lesson=lesson,
        section="Fixed",
    )
    # Mark the session as closed.
    append_section(session, "Verification", f"Closed {_state.now_iso()}. Logged to .renmark/memory/bugs.md.")


# Routing suggestions — used by /renmark:debug skill to pick a model per step.


def suggest_inspector(intent: str) -> str:
    """Return the cheapest model executor likely to be enough for `intent`.

    intent is a short tag from the skill: "grep", "file-read", "multi-file-trace",
    "api-check", "reasoning", "fix-emit".
    """
    cheap = {"grep", "file-read", "file-list", "line-count", "regex"}
    medium = {"multi-file-trace", "find-usages", "context-gather", "api-check"}
    heavy = {"reasoning", "design", "race-condition", "concurrency", "architecture"}
    intent = intent.lower()
    if intent in cheap:
        return "haiku"
    if intent in medium:
        return "codex"
    if intent in heavy:
        return "opus"
    # Default to codex for unknowns — it's the most capable agent-style.
    return "codex"

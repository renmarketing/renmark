"""renmark.blueprint — Deterministic core for blueprint feature.

Provides:
- Marker constants and builder for generated-region delimiters.
- splice_generated_block: idempotent region replacement.
- detect_ui: parse Frontend field from stack.md text.
"""
from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# Marker constants
# ---------------------------------------------------------------------------

MARKER_SCHEMATIC = "SCHEMATIC"
MARKER_PROTOTYPE = "PROTOTYPE"

_START_TPL = "<!-- RENMARK:GENERATED:{id}:START source-sha={sha} -->"
_END_TPL = "<!-- RENMARK:GENERATED:{id}:END -->"


def build_start_marker(marker_id: str, source_sha: str) -> str:
    """Return the START delimiter string for a generated region."""
    return _START_TPL.format(id=marker_id, sha=source_sha)


def build_end_marker(marker_id: str) -> str:
    """Return the END delimiter string for a generated region."""
    return _END_TPL.format(id=marker_id)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class MarkerNotFoundError(Exception):
    """Raised when a required START/END marker pair is absent or malformed."""


# ---------------------------------------------------------------------------
# splice_generated_block
# ---------------------------------------------------------------------------

# Pattern matches: <!-- RENMARK:GENERATED:<ID>:START source-sha=<sha> -->
_START_RE_TPL = r"<!-- RENMARK:GENERATED:{id}:START source-sha=\S+ -->"
_END_LITERAL_TPL = "<!-- RENMARK:GENERATED:{id}:END -->"


def splice_generated_block(
    text: str,
    marker_id: str,
    new_content: str,
    *,
    source_sha: str,
) -> str:
    """Replace the generated region for *marker_id* with *new_content*.

    Rebuilds the START marker with *source_sha*. Everything outside the
    markers is byte-preserved. Idempotent: splicing the same content twice
    yields identical output.

    Raises
    ------
    MarkerNotFoundError
        If the START marker is absent, or START is present without a matching
        END marker.
    """
    start_re = re.compile(_START_RE_TPL.format(id=re.escape(marker_id)))
    end_literal = _END_LITERAL_TPL.format(id=marker_id)

    start_match = start_re.search(text)
    if start_match is None:
        raise MarkerNotFoundError(
            f"START marker for '{marker_id}' not found in text."
        )

    end_pos = text.find(end_literal, start_match.end())
    if end_pos == -1:
        raise MarkerNotFoundError(
            f"END marker for '{marker_id}' not found after START marker."
        )

    new_start = build_start_marker(marker_id, source_sha)
    # Normalise new_content: strip outer newlines then wrap with exactly one
    # newline on each side so re-splicing is stable.
    inner = new_content.strip("\n")
    replacement = f"{new_start}\n{inner}\n{end_literal}"

    before = text[: start_match.start()]
    after = text[end_pos + len(end_literal) :]
    return before + replacement + after


# ---------------------------------------------------------------------------
# detect_ui
# ---------------------------------------------------------------------------

_NONE_RE = re.compile(r"^\*{0,2}none\*{0,2}$", re.IGNORECASE)


def detect_ui(stack_md_text: str | None) -> bool | None:
    """Parse the Frontend field from a stack.md body.

    Returns
    -------
    True
        Frontend is present and not none/empty.
    False
        Frontend is explicitly ``none`` (or ``**none**``).
    None
        *stack_md_text* is ``None``, or the text has no Frontend field.
    """
    if stack_md_text is None:
        return None

    # --- Try inline form first: "Frontend: <value>" ---
    inline_match = re.search(
        r"^[#\s]*Frontend\s*:\s*(.+)$", stack_md_text, re.IGNORECASE | re.MULTILINE
    )
    if inline_match:
        value = inline_match.group(1).strip()
        return not (not value or _NONE_RE.match(value))

    # --- Try section heading form: "## Frontend" ---
    section_match = re.search(
        r"^#{1,6}\s+Frontend\s*$", stack_md_text, re.IGNORECASE | re.MULTILINE
    )
    if section_match:
        # Collect non-empty lines after the heading until the next heading.
        rest = stack_md_text[section_match.end():]
        lines = rest.splitlines()
        value_lines: list[str] = []
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("#"):
                break
            if stripped:
                value_lines.append(stripped)
        if not value_lines:
            return None
        combined = " ".join(value_lines)
        return not _NONE_RE.match(combined.strip())

    return None

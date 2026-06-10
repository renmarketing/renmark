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


class MarkerInjectionError(ValueError):
    """Raised when new_content contains reserved marker strings for the target id."""


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
    end_literal = _END_LITERAL_TPL.format(id=marker_id)
    start_re = re.compile(_START_RE_TPL.format(id=re.escape(marker_id)))

    # FINDING 3: Guard against injection — new_content must not contain
    # the reserved marker strings for this marker_id.
    _any_start_fragment = f"RENMARK:GENERATED:{marker_id}:START"
    _any_end_fragment = f"RENMARK:GENERATED:{marker_id}:END"
    if _any_start_fragment in new_content or _any_end_fragment in new_content:
        raise MarkerInjectionError(
            f"new_content contains a reserved marker string for '{marker_id}'. "
            "Splicing this content would corrupt the artifact."
        )

    start_match = start_re.search(text)
    if start_match is None:
        raise MarkerNotFoundError(f"START marker for '{marker_id}' not found in text.")

    end_pos = text.find(end_literal, start_match.end())
    if end_pos == -1:
        raise MarkerNotFoundError(f"END marker for '{marker_id}' not found after START marker.")

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


def _normalize_md_value(raw: str) -> str:
    """Strip markdown decoration from a raw field value token.

    Removes: leading list markers (``-`` / ``+``), leading and trailing runs
    of ``*``, ``_``, and backtick characters independently (no symmetry
    required), and extra whitespace.  The result is a plain lower-case string
    suitable for comparison.

    Stripping each end independently handles asymmetric fragments such as
    ``** none`` (produced when ``**Frontend:** none`` is split on the first
    colon, leaving the closing ``**`` on the value side).
    """
    v = raw.strip()
    # Strip leading list marker (``- `` or ``+ `` or ``* ``)
    v = re.sub(r"^[-+*]\s+", "", v)
    # Strip leading decoration (* _ `) independently
    v = re.sub(r"^[*_`]+", "", v)
    # Strip trailing decoration (* _ `) independently
    v = re.sub(r"[*_`]+$", "", v)
    return v.strip()


def detect_ui(stack_md_text: str | None) -> bool | None:
    """Parse the Frontend field from a stack.md body.

    Supports two canonical formats (per scope-contract.md / stack.md):

    * **Inline bold form** — ``**Frontend:** React`` or ``Frontend: React``
    * **Section heading form** — ``## Frontend`` with the value on the next
      non-empty line (may be markdown-decorated, e.g. ``- **none**``).

    Parsing is line-oriented to avoid cross-line false matches (FINDING 2).
    Values are markdown-normalized before comparison (FINDINGS 1, 5).

    Returns
    -------
    True
        Frontend is present and not none/empty.
    False
        Frontend is explicitly ``none`` (case-insensitive, any decoration).
    None
        *stack_md_text* is ``None``, the text has no Frontend field, or the
        field is present but its value is blank.
    """
    if stack_md_text is None:
        return None

    lines = stack_md_text.splitlines()
    in_frontend_section = False

    for line in lines:
        # --- Section heading form: ## Frontend ---
        if re.match(r"^#{1,6}\s+Frontend\s*$", line, re.IGNORECASE):
            in_frontend_section = True
            continue

        if in_frontend_section:
            # Stop at the next heading.
            if re.match(r"^#{1,6}\s", line):
                break
            stripped = line.strip()
            if not stripped:
                continue
            # First non-empty line is the value.
            norm = _normalize_md_value(stripped)
            if not norm:
                return None
            return norm.lower() != "none"

        # --- Inline form: **Frontend:** value  OR  Frontend: value ---
        # FINDING 1: also match bolded ``**Frontend:**`` prefix.
        # FINDING 2: restrict value to the same line ([^\n]* / end of string).
        m = re.match(
            r"^\*{0,2}Frontend\*{0,2}\s*:\s*([^\n]*)",
            line,
            re.IGNORECASE,
        )
        if m:
            raw_value = m.group(1)
            norm = _normalize_md_value(raw_value)
            if not norm:
                # Blank value on this line — field present but unknown.
                return None
            return norm.lower() != "none"

    return None

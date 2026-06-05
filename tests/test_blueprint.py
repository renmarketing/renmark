"""Unit tests for renmark.blueprint — marker builders, splice, detect_ui."""
from __future__ import annotations

import pytest

from renmark import blueprint
from renmark.blueprint import (
    MARKER_PROTOTYPE,
    MARKER_SCHEMATIC,
    MarkerNotFoundError,
    build_end_marker,
    build_start_marker,
    detect_ui,
    splice_generated_block,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


def test_marker_constants() -> None:
    assert MARKER_SCHEMATIC == "SCHEMATIC"
    assert MARKER_PROTOTYPE == "PROTOTYPE"


# ---------------------------------------------------------------------------
# build_start_marker / build_end_marker
# ---------------------------------------------------------------------------


def test_build_start_marker_contains_sha() -> None:
    marker = build_start_marker("SCHEMATIC", "abc123")
    assert "abc123" in marker
    assert "source-sha=abc123" in marker
    assert "SCHEMATIC" in marker
    assert "START" in marker


def test_build_end_marker() -> None:
    marker = build_end_marker("SCHEMATIC")
    assert "SCHEMATIC" in marker
    assert "END" in marker


def test_build_markers_use_supplied_id() -> None:
    start = build_start_marker("PROTOTYPE", "deadbeef")
    end = build_end_marker("PROTOTYPE")
    assert "PROTOTYPE" in start
    assert "PROTOTYPE" in end
    assert "deadbeef" in start


# ---------------------------------------------------------------------------
# splice_generated_block — basic replacement
# ---------------------------------------------------------------------------


def _make_doc(marker_id: str, sha: str, inner: str, *, before: str = "", after: str = "") -> str:
    """Build a document with a generated region for testing."""
    start = build_start_marker(marker_id, sha)
    end = build_end_marker(marker_id)
    return f"{before}{start}\n{inner}\n{end}{after}"


def test_splice_replaces_only_inner_region() -> None:
    """splice_generated_block must byte-preserve surrounding human prose."""
    before = "# Human intro\nSome prose written by a human.\n"
    after = "\nMore human prose after the block.\n"
    doc = _make_doc("SCHEMATIC", "sha0", "old generated content", before=before, after=after)

    result = splice_generated_block(doc, "SCHEMATIC", "new generated content", source_sha="sha1")

    assert result.startswith(before)
    assert result.endswith(after)
    assert "new generated content" in result
    assert "old generated content" not in result


def test_splice_sha_recorded_in_output() -> None:
    """The START marker in the spliced output must contain the supplied source_sha."""
    doc = _make_doc("SCHEMATIC", "sha0", "initial")
    result = splice_generated_block(doc, "SCHEMATIC", "updated", source_sha="newsha99")
    assert "newsha99" in result
    assert "source-sha=newsha99" in result


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------


def test_splice_idempotent_same_content() -> None:
    """Splicing the same new_content twice yields identical output."""
    doc = _make_doc("SCHEMATIC", "sha0", "initial content")
    first = splice_generated_block(doc, "SCHEMATIC", "stable content", source_sha="sha1")
    second = splice_generated_block(first, "SCHEMATIC", "stable content", source_sha="sha1")
    assert first == second


# ---------------------------------------------------------------------------
# Human edit preservation on re-splice with different content
# ---------------------------------------------------------------------------


def test_splice_preserves_human_edit_outside_markers() -> None:
    """Re-splicing with different content preserves manual human edits outside markers."""
    original_doc = _make_doc(
        "PROTOTYPE",
        "sha0",
        "original generated",
        before="## Title\n",
        after="\n## Human section\nManual edit that must survive.\n",
    )

    # First splice — updates content, preserves surroundings
    after_first_splice = splice_generated_block(
        original_doc, "PROTOTYPE", "first generated", source_sha="sha1"
    )
    assert "Manual edit that must survive." in after_first_splice

    # Simulate a human edit to the surrounding prose
    doc_with_human_edit = after_first_splice.replace(
        "Manual edit that must survive.", "Manual edit CHANGED by human."
    )

    # Second splice with different generated content
    after_second_splice = splice_generated_block(
        doc_with_human_edit, "PROTOTYPE", "second generated", source_sha="sha2"
    )

    # Human edit is preserved
    assert "Manual edit CHANGED by human." in after_second_splice
    # Generated block is updated
    assert "second generated" in after_second_splice
    assert "first generated" not in after_second_splice


# ---------------------------------------------------------------------------
# MarkerNotFoundError
# ---------------------------------------------------------------------------


def test_splice_raises_when_markers_absent() -> None:
    """splice_generated_block raises MarkerNotFoundError when markers are absent."""
    with pytest.raises(MarkerNotFoundError):
        splice_generated_block("no markers here", "SCHEMATIC", "content", source_sha="sha")


def test_splice_raises_when_only_start_marker_present() -> None:
    """MarkerNotFoundError raised when START present but END absent."""
    start_only = build_start_marker("SCHEMATIC", "sha0") + "\nsome content\n"
    with pytest.raises(MarkerNotFoundError):
        splice_generated_block(start_only, "SCHEMATIC", "new", source_sha="sha1")


def test_marker_not_found_error_is_exception() -> None:
    assert issubclass(MarkerNotFoundError, Exception)


# ---------------------------------------------------------------------------
# detect_ui
# ---------------------------------------------------------------------------


def test_detect_ui_none_input_returns_none() -> None:
    assert detect_ui(None) is None


def test_detect_ui_no_frontend_field_returns_none() -> None:
    assert detect_ui("# Stack\n\nBackend: Python\n") is None


def test_detect_ui_empty_string_returns_none() -> None:
    assert detect_ui("") is None


def test_detect_ui_inline_react_returns_true() -> None:
    assert detect_ui("Frontend: React") is True


def test_detect_ui_inline_vue_returns_true() -> None:
    assert detect_ui("Frontend: Vue\nBackend: Node\n") is True


def test_detect_ui_inline_none_returns_false() -> None:
    assert detect_ui("Frontend: none") is False


def test_detect_ui_inline_none_bold_returns_false() -> None:
    assert detect_ui("Frontend: **none**") is False


def test_detect_ui_inline_none_case_insensitive() -> None:
    assert detect_ui("Frontend: NONE") is False


def test_detect_ui_section_heading_with_react_returns_true() -> None:
    text = "# Stack\n\n## Frontend\n\nReact 18\n\n## Backend\n\nNode\n"
    assert detect_ui(text) is True


def test_detect_ui_section_heading_with_none_returns_false() -> None:
    text = "# Stack\n\n## Frontend\n\nnone\n\n## Backend\n\nNode\n"
    assert detect_ui(text) is False


def test_detect_ui_section_heading_empty_body_returns_none() -> None:
    # No content lines after the ## Frontend heading before the next heading
    text = "## Frontend\n\n## Backend\n\nPython\n"
    assert detect_ui(text) is None

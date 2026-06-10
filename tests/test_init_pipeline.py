"""Tests for the /renmark:init scaffold-and-back-fill pipeline.

Covers the behavior added in this feature:

1. `run()` no longer dead-ends with exit 1 when CLAUDE.md is absent — it
   scaffolds CLAUDE.md/AGENTS.md/CHANGELOG.md/.renmark and returns exit 0.
2. Scaffold is non-destructive and idempotent — a pre-existing CLAUDE.md with
   custom content is never overwritten on re-run.
3. `merge_rule_blocks()` back-fills ONLY missing canonical rule blocks,
   byte-verbatim, leaving present (and hand-modified) blocks untouched, and is
   idempotent on a second call.
4. A malformed file (orphan END, unclosed BEGIN, etc.) is SKIPPED — never
   inserted into — and signaled via MarkerCorruptionError / run() exit 2, so a
   corrupt file is never made worse. Bare prose like "BEGIN:example" is not a
   managed marker. AGENTS.md rule-block back-fill is scoped out (#4).

Hermetic: every test runs against `tmp_path`. The real plugin template dir is
resolved via `renmark.memory.template_dir()`; no network, no mutation outside
the tmp repo.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from renmark import init, memory
from renmark.lint import iter_rule_blocks

# ── Helpers ──────────────────────────────────────────────────────────────────


def _template_dir() -> Path:
    """The directory holding CLAUDE.md.template / AGENTS.md.template."""
    mem_tdir = memory.template_dir()
    assert mem_tdir is not None, "renmark templates not found — install layout broken"
    return mem_tdir.parent


def _claude_template_text() -> str:
    return (_template_dir() / "CLAUDE.md.template").read_text(encoding="utf-8")


# ── 1. No more exit 1 when CLAUDE.md is absent ───────────────────────────────


def test_run_scaffolds_when_claude_md_absent(tmp_path: Path) -> None:
    """Empty repo → run() scaffolds and returns exit 0 (old behavior was exit 1)."""
    assert not (tmp_path / "CLAUDE.md").exists()

    code, summary = init.run(tmp_path)

    assert code == 0, f"expected exit 0 after scaffold, got {code}: {summary!r}"
    # The whole point of the fix: CLAUDE.md now exists.
    assert (tmp_path / "CLAUDE.md").is_file()
    # And the rest of the scaffold landed too.
    assert (tmp_path / "AGENTS.md").is_file()
    assert (tmp_path / "CHANGELOG.md").is_file()
    assert (tmp_path / ".renmark" / "memory" / "INDEX.md").is_file()
    # Summary is a success line, not a FAIL line.
    assert summary.startswith("OK")


# ── 2. Non-destructive / idempotent ──────────────────────────────────────────


def test_run_does_not_overwrite_existing_custom_claude_md(tmp_path: Path) -> None:
    """A pre-existing CLAUDE.md with custom content survives scaffold + run."""
    custom = "# My Project\n\nHand-written content the user cares about.\n"
    (tmp_path / "CLAUDE.md").write_text(custom, encoding="utf-8")

    code, _ = init.run(tmp_path)
    assert code == 0

    after = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
    # The original custom prose is preserved verbatim (the stub/blocks may be
    # appended after it, but nothing existing is removed or rewritten).
    assert custom.strip() in after


def test_run_is_idempotent(tmp_path: Path) -> None:
    """Two consecutive run() calls converge — the second changes nothing."""
    code1, _ = init.run(tmp_path)
    assert code1 == 0
    first = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")

    code2, _ = init.run(tmp_path)
    assert code2 == 0
    second = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")

    assert first == second, "second run() mutated CLAUDE.md — not idempotent"


def test_scaffold_missing_preserves_user_changelog(tmp_path: Path) -> None:
    """_scaffold_missing never clobbers an existing CHANGELOG.md."""
    (tmp_path / "CHANGELOG.md").write_text("USER CHANGELOG\n", encoding="utf-8")
    init._scaffold_missing(tmp_path)
    assert (tmp_path / "CHANGELOG.md").read_text(encoding="utf-8") == "USER CHANGELOG\n"


# ── 3. merge_rule_blocks back-fill ───────────────────────────────────────────


def test_merge_rule_blocks_backfills_only_missing_verbatim(tmp_path: Path) -> None:
    """Start from a CLAUDE.md missing two canonical blocks → exactly those two
    are re-inserted byte-verbatim; present (incl. hand-modified) blocks untouched;
    a second call adds nothing."""
    tdir = _template_dir()
    canonical = iter_rule_blocks(_claude_template_text())
    canon_by_name = dict(canonical)
    assert len(canonical) >= 4, "template should define several rule blocks"

    # Choose two interior blocks to delete (interior so insertion has anchors
    # on both sides) and one block to hand-modify (must stay untouched).
    drop_a_name, _ = canonical[2]
    drop_b_name, _ = canonical[4]
    keep_modified_name, keep_modified_block = canonical[1]

    # Build a CLAUDE.md from the template text, then surgically remove the two
    # blocks we want back-filled. We keep the rest of the template intact so the
    # remaining blocks act as positional anchors.
    text = _claude_template_text()
    for drop_name in (drop_a_name, drop_b_name):
        block = canon_by_name[drop_name]
        assert block in text, f"block {drop_name} not found verbatim in template"
        text = text.replace(block, "", 1)

    # Hand-modify the kept block's BODY (not its markers) so we can prove the
    # back-fill leaves existing blocks alone.
    assert keep_modified_block in text
    modified_block = keep_modified_block.replace(
        "## ", "## EDITED ", 1
    )
    assert modified_block != keep_modified_block, "expected the edit to change the block"
    text = text.replace(keep_modified_block, modified_block, 1)

    claude = tmp_path / "CLAUDE.md"
    claude.write_text(text, encoding="utf-8")

    # Sanity: the two dropped blocks really are absent before the merge.
    present_before = {n for n, _ in iter_rule_blocks(text)}
    assert drop_a_name not in present_before
    assert drop_b_name not in present_before

    # ── First merge: exactly the two missing blocks get added.
    result = init.merge_rule_blocks(tmp_path, template_dir=tdir)
    assert "CLAUDE.md" in result
    assert result["CLAUDE.md"] == 2, f"expected 2 blocks back-filled, got {result}"

    after_text = claude.read_text(encoding="utf-8")
    after_blocks = dict(iter_rule_blocks(after_text))

    # The two back-filled blocks are present and BYTE-VERBATIM equal to the
    # template's own blocks.
    for name in (drop_a_name, drop_b_name):
        assert name in after_blocks, f"{name} was not re-inserted"
        assert after_blocks[name] == canon_by_name[name], (
            f"{name} not byte-verbatim after back-fill"
        )

    # The hand-modified block is left exactly as the user wrote it.
    assert "EDITED" in after_text
    assert after_blocks[keep_modified_name] == modified_block

    # ── Second merge: idempotent — nothing left to add.
    result2 = init.merge_rule_blocks(tmp_path, template_dir=tdir)
    assert result2.get("CLAUDE.md", 0) == 0, "second merge should add 0 blocks"
    assert claude.read_text(encoding="utf-8") == after_text, "idempotent re-run mutated file"


def test_merge_rule_blocks_agents_always_zero(tmp_path: Path) -> None:
    """Scope-out (#4): AGENTS.md.template has NO managed rule-block markers, so
    AGENTS.md always reports 0 added — there is no CLAUDE.md↔AGENTS.md rule-block
    back-fill/mirroring. AGENTS.md is created from its own template by bootstrap.
    Never assert symmetry with CLAUDE.md."""
    tdir = _template_dir()
    # Both files present, derived from their own templates.
    (tmp_path / "CLAUDE.md").write_text(
        (tdir / "CLAUDE.md.template").read_text(encoding="utf-8"), encoding="utf-8"
    )
    (tmp_path / "AGENTS.md").write_text(
        (tdir / "AGENTS.md.template").read_text(encoding="utf-8"), encoding="utf-8"
    )

    result = init.merge_rule_blocks(tmp_path, template_dir=tdir)

    # AGENTS.md is reported (it exists) but always 0 by design.
    assert result.get("AGENTS.md") == 0
    # CLAUDE.md built straight from its template is already complete → 0 too.
    assert result.get("CLAUDE.md") == 0


def test_merge_rule_blocks_omits_absent_files(tmp_path: Path) -> None:
    """Files that don't exist are omitted from the result dict entirely."""
    tdir = _template_dir()
    # Only CLAUDE.md exists; AGENTS.md does not.
    (tmp_path / "CLAUDE.md").write_text(
        (tdir / "CLAUDE.md.template").read_text(encoding="utf-8"), encoding="utf-8"
    )
    result = init.merge_rule_blocks(tmp_path, template_dir=tdir)
    assert "CLAUDE.md" in result
    assert "AGENTS.md" not in result


def test_merge_rule_blocks_raises_without_templates(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """No template_dir and memory can't find one → RuntimeError."""
    (tmp_path / "CLAUDE.md").write_text("# x\n", encoding="utf-8")
    monkeypatch.setattr(memory, "template_dir", lambda: None)
    with pytest.raises(RuntimeError):
        init.merge_rule_blocks(tmp_path)


# ── 4. Malformed markers — unbalanced BEGIN ──────────────────────────────────


def test_merge_rule_blocks_skips_unclosed_begin(tmp_path: Path) -> None:
    """SAFETY: a CLAUDE.md with a BEGIN that has no matching END is MALFORMED.

    merge_rule_blocks must NOT insert anything into it (an insert could land
    inside the open block, corrupting the file further). Instead it skips the
    file and raises MarkerCorruptionError — the file content is left byte-for-
    byte unchanged, with no back-filled blocks and no new dangling markers.
    """
    tdir = _template_dir()
    canonical = iter_rule_blocks(_claude_template_text())
    target_name = canonical[0][0]  # name we'll leave dangling

    # File has a single unbalanced (unclosed) BEGIN marker and nothing else —
    # none of the other canonical blocks are present, but a later "missing
    # block" insert must NOT be attempted because the file is malformed.
    malformed = (
        "# Project\n\n"
        f"<!-- BEGIN:{target_name} -->\n"
        "Some half-written rule with no closing marker.\n\n"
        "More prose below.\n"
    )
    claude = tmp_path / "CLAUDE.md"
    claude.write_text(malformed, encoding="utf-8")

    with pytest.raises(init.MarkerCorruptionError):
        init.merge_rule_blocks(tmp_path, template_dir=tdir)

    after = claude.read_text(encoding="utf-8")
    # File is UNCHANGED — no insert inside the open block, nothing back-filled.
    assert after == malformed, "malformed file must be left byte-for-byte unchanged"
    # No new dangling markers were introduced and none of the missing canonical
    # blocks leaked in.
    assert after.count(f"BEGIN:{target_name}") == 1
    assert f"END:{target_name}" not in after
    other_missing = [n for n, _ in canonical if n != target_name]
    for n in other_missing:
        assert f"BEGIN:{n}" not in after, f"{n} must NOT be inserted into a malformed file"


def test_merge_rule_blocks_skips_orphan_end(tmp_path: Path) -> None:
    """SAFETY: a CLAUDE.md with an orphan END (no preceding BEGIN) is MALFORMED.

    The original bug: merge inserted a fresh block AND left the dangling END
    (1 BEGIN + 2 END = corrupt). Fix: the file is skipped, left unchanged, and
    MarkerCorruptionError is raised. No block is inserted, no marker imbalance
    is produced.
    """
    tdir = _template_dir()
    canonical = iter_rule_blocks(_claude_template_text())
    orphan_name = canonical[0][0]

    malformed = (
        "# Project\n\n"
        "Some prose.\n\n"
        f"<!-- END:{orphan_name} -->\n"
        "Trailing prose.\n"
    )
    claude = tmp_path / "CLAUDE.md"
    claude.write_text(malformed, encoding="utf-8")

    with pytest.raises(init.MarkerCorruptionError):
        init.merge_rule_blocks(tmp_path, template_dir=tdir)

    after = claude.read_text(encoding="utf-8")
    # Unchanged: no inserted block, no new BEGIN, exactly one (orphan) END left.
    assert after == malformed, "malformed file must be left byte-for-byte unchanged"
    assert after.count(f"END:{orphan_name}") == 1
    assert f"BEGIN:{orphan_name}" not in after


def test_run_returns_exit_2_on_corrupted_claude_md(tmp_path: Path) -> None:
    """run() maps marker corruption to exit code 2 (distinct from exit 1)."""
    canonical = iter_rule_blocks(_claude_template_text())
    orphan_name = canonical[0][0]
    # Orphan END with no matching BEGIN → corruption.
    (tmp_path / "CLAUDE.md").write_text(
        f"# Project\n\nprose\n\n<!-- END:{orphan_name} -->\n", encoding="utf-8"
    )

    code, summary = init.run(tmp_path)
    assert code == 2, f"expected exit 2 on corrupted markers, got {code}: {summary!r}"
    assert summary.startswith("FAIL")


def test_merge_rule_blocks_ignores_prose_marker(tmp_path: Path) -> None:
    """A CLAUDE.md whose PROSE contains bare 'BEGIN:example' text (not a real
    marker comment) is NOT treated as a managed marker. The file is well-formed,
    the prose is untouched, and the real missing canonical blocks back-fill."""
    tdir = _template_dir()
    canonical = iter_rule_blocks(_claude_template_text())

    # No real managed markers at all — just prose that mentions the token.
    prose = (
        "# Project\n\n"
        "This document explains the BEGIN:example convention in plain words.\n"
        "We also discuss END:example here, inline, as prose.\n"
    )
    claude = tmp_path / "CLAUDE.md"
    claude.write_text(prose, encoding="utf-8")

    result = init.merge_rule_blocks(tmp_path, template_dir=tdir)

    after = claude.read_text(encoding="utf-8")
    # Prose preserved verbatim.
    assert "This document explains the BEGIN:example convention" in after
    assert "We also discuss END:example here, inline, as prose." in after
    # 'example' was never a managed block → not inserted, not duplicated.
    after_blocks = {n for n, _ in iter_rule_blocks(after)}
    assert "example" not in after_blocks
    # ALL canonical blocks were missing → all back-filled correctly.
    assert result.get("CLAUDE.md", 0) == len(canonical)
    for n, _ in canonical:
        assert n in after_blocks, f"{n} should have been back-filled"


# ── _file_purpose multi-line docstring regression ────────────────────────────


def test_file_purpose_single_line_docstring() -> None:
    """A same-line triple-quoted docstring returns the full sentence."""
    text = '"""Single-line module purpose."""\n\nx = 1\n'
    assert init._file_purpose(text, "python") == "Single-line module purpose."


def test_file_purpose_multiline_joins_to_first_sentence() -> None:
    """A wrapped multi-line docstring is joined and the first sentence returned.

    Prior bug: the function returned only the *second* physical line
    (e.g. "tracking tuned.") rather than the complete first sentence that
    wraps across lines.
    """
    text = (
        '"""\n'
        "Persistent project memory at `.renmark/memory/`.\n"
        "\n"
        "Files act as living documentation.\n"
        '"""\n'
    )
    result = init._file_purpose(text, "python")
    # Must include the full first sentence, not a fragment from the second line
    assert result == "Persistent project memory at `.renmark/memory/`."


def test_file_purpose_multiline_no_period_returns_first_line() -> None:
    """When no sentence-end is found, the first non-empty body line is returned."""
    text = '"""\nModule with no period anywhere\nSome more description\n"""\n'
    result = init._file_purpose(text, "python")
    assert result == "Module with no period anywhere"


def test_file_purpose_multiline_wraps_across_lines() -> None:
    """A long first sentence that wraps across multiple lines is joined correctly."""
    # Use a short sentence that fits within the 80-char cap
    text = (
        '"""\n'
        "Drift detection that keeps pyproject,\n"
        "VERSION in sync.\n"
        '"""\n'
    )
    result = init._file_purpose(text, "python")
    # First sentence ends with the period after "sync."
    assert result.endswith("sync.")
    # Should contain the wrapped content joined
    assert "pyproject," in result and "VERSION in sync" in result

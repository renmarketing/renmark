"""Tests for the /renmark:init scaffold-and-back-fill pipeline.

Covers the behavior added in this feature:

1. `run()` no longer dead-ends with exit 1 when CLAUDE.md is absent — it
   scaffolds CLAUDE.md/AGENTS.md/CHANGELOG.md/.renmark and returns exit 0.
2. Scaffold is non-destructive and idempotent — a pre-existing CLAUDE.md with
   custom content is never overwritten on re-run.
3. `merge_rule_blocks()` back-fills ONLY missing canonical rule blocks,
   byte-verbatim, leaving present (and hand-modified) blocks untouched, and is
   idempotent on a second call.
4. A malformed (unbalanced BEGIN, no END) existing block is skipped, not
   duplicated or corrupted.

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
    """Design nuance: AGENTS.md.template has NO rule-block markers, so AGENTS.md
    always reports 0 added — never assert symmetry with CLAUDE.md."""
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


def test_merge_rule_blocks_skips_unbalanced_begin(tmp_path: Path) -> None:
    """A CLAUDE.md with a BEGIN that has no matching END is left uncorrupted:
    that block name is treated as 'present' (so it's never duplicated), no
    partial insert happens, and no exception is raised."""
    tdir = _template_dir()
    canonical = iter_rule_blocks(_claude_template_text())
    target_name = canonical[0][0]  # name we'll leave dangling

    # File has a single unbalanced BEGIN marker for `target_name` and nothing
    # else — none of the other canonical blocks are present.
    malformed = (
        "# Project\n\n"
        f"<!-- BEGIN:{target_name} -->\n"
        "Some half-written rule with no closing marker.\n\n"
        "More prose below.\n"
    )
    claude = tmp_path / "CLAUDE.md"
    claude.write_text(malformed, encoding="utf-8")

    # Must not raise.
    result = init.merge_rule_blocks(tmp_path, template_dir=tdir)

    after = claude.read_text(encoding="utf-8")

    # The dangling BEGIN is treated as present → not re-inserted, not duplicated.
    assert after.count(f"BEGIN:{target_name}") == 1, "dangling block was duplicated"
    # The unbalanced block (and its END) is NOT auto-closed/back-filled.
    assert f"END:{target_name}" not in after
    # Original prose is preserved — no corruption / partial insert over it.
    assert "Some half-written rule with no closing marker." in after
    assert "More prose below." in after

    # Other canonical blocks (which WERE missing) still get back-filled, proving
    # the merge proceeded past the malformed one rather than aborting.
    other_missing = [n for n, _ in canonical if n != target_name]
    assert result.get("CLAUDE.md", 0) == len(other_missing)
    after_blocks = {n for n, _ in iter_rule_blocks(after)}
    for n in other_missing:
        assert n in after_blocks, f"{n} should have been back-filled"

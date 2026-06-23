"""
---
artifact_type: task-output
schema_version: 1
created_at: 2026-06-23T00:00:00-04:00
generator: codex
source_sha: unknown
related_plan: null
stale_after: null
dependency_refs:
  - renmark.global_routing
  - renmark.lint.iter_rule_blocks
---
"""

from pathlib import Path

from renmark.global_routing import (
    ROUTING_BLOCK_NAME,
    detect_global_rule,
    global_claude_path,
    install_global_rule,
)
from renmark.lint import iter_rule_blocks


def _routing_block_count(text: str) -> int:
    return len([n for n, _ in iter_rule_blocks(text) if n == ROUTING_BLOCK_NAME])


def test_create_when_missing(tmp_path: Path) -> None:
    claude_dir = tmp_path / ".claude"

    assert global_claude_path(claude_dir=claude_dir) == claude_dir / "CLAUDE.md"
    assert detect_global_rule(claude_dir=claude_dir) == "missing"

    result = install_global_rule(claude_dir=claude_dir)

    assert result["action"] == "created"
    assert result["path"] == str(claude_dir / "CLAUDE.md")
    assert result["backup"] is None

    text = (claude_dir / "CLAUDE.md").read_text()
    assert _routing_block_count(text) == 1
    assert detect_global_rule(claude_dir=claude_dir) == "present-with-rule"


def test_append_when_present_without_rule(tmp_path: Path) -> None:
    claude_dir = tmp_path / ".claude"
    claude_md = claude_dir / "CLAUDE.md"
    claude_dir.mkdir()
    original = "# my rules\n\nkeep replies short\n"
    claude_md.write_text(original)

    assert detect_global_rule(claude_dir=claude_dir) == "present-without-rule"

    result = install_global_rule(claude_dir=claude_dir)

    assert result["action"] == "appended"
    assert result["path"] == str(claude_md)
    assert result["backup"] is not None

    backup = Path(result["backup"])
    assert backup.exists()
    assert backup.read_bytes() == original.encode()

    text = claude_md.read_text()
    assert original in text
    assert _routing_block_count(text) == 1


def test_already_present_is_noop(tmp_path: Path) -> None:
    claude_dir = tmp_path / ".claude"

    install_global_rule(claude_dir=claude_dir)
    claude_md = claude_dir / "CLAUDE.md"
    before = claude_md.read_bytes()

    result = install_global_rule(claude_dir=claude_dir)

    assert result["action"] == "already-present"
    assert result["path"] == str(claude_md)
    assert result["backup"] is None
    assert claude_md.read_bytes() == before
    assert _routing_block_count(claude_md.read_text()) == 1


def test_no_clobber_preserves_unrelated_content(tmp_path: Path) -> None:
    claude_dir = tmp_path / ".claude"
    claude_md = claude_dir / "CLAUDE.md"
    claude_dir.mkdir()
    sentinel = "preserve this exact line"
    claude_md.write_text(f"# custom rules\n\n{sentinel}\n")

    install_global_rule(claude_dir=claude_dir)

    text = claude_md.read_text()
    assert sentinel in text
    assert _routing_block_count(text) == 1


def test_idempotency_two_installs_keep_single_block(tmp_path: Path) -> None:
    claude_dir = tmp_path / ".claude"

    first = install_global_rule(claude_dir=claude_dir)
    second = install_global_rule(claude_dir=claude_dir)

    assert first["action"] == "created"
    assert second["action"] == "already-present"
    assert _routing_block_count((claude_dir / "CLAUDE.md").read_text()) == 1


def test_existing_backup_is_not_clobbered_unique_path(tmp_path: Path) -> None:
    """A pre-existing CLAUDE.md.bak must survive; the new backup gets a unique path."""
    claude_dir = tmp_path / ".claude"
    claude_md = claude_dir / "CLAUDE.md"
    claude_dir.mkdir()

    sentinel = "preserve this exact line"
    claude_md.write_text(f"# custom rules\n\n{sentinel}\n")

    # Pre-existing, unrelated .bak that must NOT be overwritten.
    existing_bak = claude_md.with_name(claude_md.name + ".bak")
    existing_bak_content = "pre-existing backup content — do not clobber\n"
    existing_bak.write_text(existing_bak_content)
    existing_bak_bytes = existing_bak.read_bytes()

    result = install_global_rule(claude_dir=claude_dir)

    assert result["action"] == "appended"

    # The original .bak is byte-unchanged.
    assert existing_bak.read_bytes() == existing_bak_bytes

    # The returned backup is a NEW, unique, existing path (e.g. ...bak.1).
    new_backup = Path(result["backup"])
    assert new_backup != existing_bak
    assert new_backup.exists()
    assert new_backup.name.endswith(".bak.1")

    text = claude_md.read_text()
    assert sentinel in text
    assert _routing_block_count(text) == 1


def test_malformed_markers_are_not_modified(tmp_path: Path) -> None:
    """Duplicated routing blocks => detect 'present-malformed', install writes nothing."""
    claude_dir = tmp_path / ".claude"
    claude_md = claude_dir / "CLAUDE.md"
    claude_dir.mkdir()

    # Two renmark-routing blocks — a clean append can never converge.
    malformed = (
        f"<!-- BEGIN:{ROUTING_BLOCK_NAME} -->\n"
        "first block body\n"
        f"<!-- END:{ROUTING_BLOCK_NAME} -->\n"
        "\n"
        f"<!-- BEGIN:{ROUTING_BLOCK_NAME} -->\n"
        "second block body\n"
        f"<!-- END:{ROUTING_BLOCK_NAME} -->\n"
    )
    claude_md.write_text(malformed)
    before = claude_md.read_bytes()

    assert detect_global_rule(claude_dir=claude_dir) == "present-malformed"

    result = install_global_rule(claude_dir=claude_dir)

    assert result["action"] == "needs-manual-repair"
    assert result["path"] == str(claude_md)
    assert result["backup"] is None

    # File is byte-UNCHANGED — nothing appended, no backup written.
    assert claude_md.read_bytes() == before

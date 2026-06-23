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
    home = tmp_path / ".claude"

    assert global_claude_path(home) == home / "CLAUDE.md"
    assert detect_global_rule(home) == "missing"

    result = install_global_rule(home)

    assert result["action"] == "created"
    assert result["path"] == str(home / "CLAUDE.md")
    assert result["backup"] is None

    text = (home / "CLAUDE.md").read_text()
    assert _routing_block_count(text) == 1
    assert detect_global_rule(home) == "present-with-rule"


def test_append_when_present_without_rule(tmp_path: Path) -> None:
    home = tmp_path / ".claude"
    claude_md = home / "CLAUDE.md"
    home.mkdir()
    original = "# my rules\n\nkeep replies short\n"
    claude_md.write_text(original)

    assert detect_global_rule(home) == "present-without-rule"

    result = install_global_rule(home)

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
    home = tmp_path / ".claude"

    install_global_rule(home)
    claude_md = home / "CLAUDE.md"
    before = claude_md.read_bytes()

    result = install_global_rule(home)

    assert result["action"] == "already-present"
    assert result["path"] == str(claude_md)
    assert result["backup"] is None
    assert claude_md.read_bytes() == before
    assert _routing_block_count(claude_md.read_text()) == 1


def test_no_clobber_preserves_unrelated_content(tmp_path: Path) -> None:
    home = tmp_path / ".claude"
    claude_md = home / "CLAUDE.md"
    home.mkdir()
    sentinel = "preserve this exact line"
    claude_md.write_text(f"# custom rules\n\n{sentinel}\n")

    install_global_rule(home)

    text = claude_md.read_text()
    assert sentinel in text
    assert _routing_block_count(text) == 1


def test_idempotency_two_installs_keep_single_block(tmp_path: Path) -> None:
    home = tmp_path / ".claude"

    first = install_global_rule(home)
    second = install_global_rule(home)

    assert first["action"] == "created"
    assert second["action"] == "already-present"
    assert _routing_block_count((home / "CLAUDE.md").read_text()) == 1

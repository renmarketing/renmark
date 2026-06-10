"""Unit tests for renmark.backlog (backlog item state machine).

Hermetic: every disk test runs under pytest's ``tmp_path``. No network, no git,
no datetime.now(). All field values are set to distinct strings so round-trip
tests prove every field is persisted and restored independently.
"""

from __future__ import annotations

import json
from pathlib import Path

from renmark.backlog import (
    DISPOSITIONS,
    BacklogItem,
    backlog_dir,
    completion_report,
    is_terminal_disposition,
    list_items,
    managed_branch_name,
    next_id,
    read_item,
    status_for_outcome,
    write_item,
)

# ── next_id ────────────────────────────────────────────────────────────────────


def test_next_id_empty_dir(tmp_path: Path) -> None:
    """Returns BL-0001 when the backlog directory is absent/empty."""
    assert next_id(tmp_path) == "BL-0001"


def test_next_id_increments_past_highest(tmp_path: Path) -> None:
    """Returns one past the highest existing numeric suffix."""
    bdir = backlog_dir(tmp_path)
    bdir.mkdir(parents=True, exist_ok=True)
    # Create three items: BL-0001, BL-0005, BL-0003
    for n in (1, 5, 3):
        item = BacklogItem(id=f"BL-{n:04d}", title=f"Item {n}", created_at="2026-01-01")
        write_item(tmp_path, item)
    assert next_id(tmp_path) == "BL-0006"


def test_next_id_skips_malformed_filename(tmp_path: Path) -> None:
    """A BL-*.json filename that isn't BL-<digits> is skipped without raising."""
    bdir = backlog_dir(tmp_path)
    bdir.mkdir(parents=True, exist_ok=True)
    # Write a valid item and a malformed filename
    item = BacklogItem(id="BL-0002", title="Item 2", created_at="2026-01-01")
    write_item(tmp_path, item)
    # Malformed: BL-abc.json — matches glob but not _ID_NUM_RE
    (bdir / "BL-abc.json").write_text("{}", encoding="utf-8")
    # Should still return BL-0003 (not raise)
    assert next_id(tmp_path) == "BL-0003"


def test_next_id_reserves_so_two_allocations_differ(tmp_path: Path) -> None:
    """FINDING 5: next_id atomically reserves — two consecutive allocations never
    collide, even with no write_item in between (the reservation file holds the
    id)."""
    first = next_id(tmp_path)
    second = next_id(tmp_path)
    assert first == "BL-0001"
    assert second == "BL-0002"
    assert first != second
    # The reservation created the placeholder file on disk.
    assert (backlog_dir(tmp_path) / f"{first}.json").exists()


# ── write_item / read_item round-trip ─────────────────────────────────────────


def test_write_then_read_round_trips_all_fields(tmp_path: Path) -> None:
    """All fields survive a write -> read cycle with distinct values."""
    original = BacklogItem(
        id="BL-0042",
        title="My distinct title",
        status="in progress",
        source="qa",
        risk="high",
        summary="A distinct summary",
        evidence_path="/path/to/evidence",
        recommended_action="Ship it",
        served_requirements="REQ-1 REQ-2",
        pending_decision="Approve design",
        branch="feature/backlog-bl-0042-my-feature",
        loop_id="loop-2026-06-09-my-feature",
        disposition="",
        created_at="2026-06-01T10:00:00",
        updated_at="2026-06-09T12:00:00",
    )
    written = write_item(tmp_path, original)
    assert written is not None
    assert written.exists()

    loaded = read_item(tmp_path, "BL-0042")
    assert loaded is not None
    assert loaded.id == "BL-0042"
    assert loaded.title == "My distinct title"
    assert loaded.status == "in progress"
    assert loaded.source == "qa"
    assert loaded.risk == "high"
    assert loaded.summary == "A distinct summary"
    assert loaded.evidence_path == "/path/to/evidence"
    assert loaded.recommended_action == "Ship it"
    assert loaded.served_requirements == "REQ-1 REQ-2"
    assert loaded.pending_decision == "Approve design"
    assert loaded.branch == "feature/backlog-bl-0042-my-feature"
    assert loaded.loop_id == "loop-2026-06-09-my-feature"
    assert loaded.disposition == ""
    assert loaded.created_at == "2026-06-01T10:00:00"
    assert loaded.updated_at == "2026-06-09T12:00:00"


# ── read_item edge cases ──────────────────────────────────────────────────────


def test_read_item_missing_id_returns_none(tmp_path: Path) -> None:
    """read_item returns None (not an exception) for an id that doesn't exist."""
    result = read_item(tmp_path, "BL-9998")
    assert result is None


def test_read_item_corrupt_file_returns_none(tmp_path: Path) -> None:
    """read_item returns None when the JSON file is corrupt/unreadable."""
    # Create the backlog directory by writing a valid item first
    item = BacklogItem(id="BL-0001", title="Seed", created_at="2026-01-01")
    write_item(tmp_path, item)
    # Now write garbage into BL-9999.json
    bdir = backlog_dir(tmp_path)
    (bdir / "BL-9999.json").write_text("not-json{{garbage", encoding="utf-8")
    result = read_item(tmp_path, "BL-9999")
    assert result is None


def test_read_item_unknown_status_coerces_to_needs_review(tmp_path: Path) -> None:
    """An unknown status on disk is coerced to 'needs review' on read."""
    bdir = backlog_dir(tmp_path)
    bdir.mkdir(parents=True, exist_ok=True)
    data = {"id": "BL-0010", "title": "Status test", "status": "totally-unknown-status"}
    (bdir / "BL-0010.json").write_text(json.dumps(data), encoding="utf-8")
    item = read_item(tmp_path, "BL-0010")
    assert item is not None
    assert item.status == "needs review"


def test_read_write_reject_traversal_id_without_touching_disk(tmp_path: Path) -> None:
    """FINDING 1: a '../traversal' id degrades to None and never writes a file
    outside backlog_dir."""
    # read_item with an unsafe id returns None, no disk access.
    assert read_item(tmp_path, "../../etc/passwd") is None
    assert read_item(tmp_path, "BL-1/../../escape") is None
    assert read_item(tmp_path, "not-an-id") is None

    # write_item with an unsafe id returns None and writes nothing anywhere.
    evil = BacklogItem(id="../escape", title="malicious")
    assert write_item(tmp_path, evil) is None
    # Nothing leaked above the backlog dir / repo root.
    assert not (tmp_path.parent / "escape.json").exists()
    assert not (tmp_path / "escape.json").exists()
    # The backlog dir holds no escape artifacts.
    bdir = backlog_dir(tmp_path)
    if bdir.exists():
        assert list(bdir.glob("*escape*")) == []


def test_write_item_non_serializable_field_returns_none(tmp_path: Path) -> None:
    """FINDING 2: a non-JSON-serializable field value makes write_item return None
    (not raise)."""
    item = BacklogItem(id="BL-0001", title="bad")
    # Sabotage a field with a value json.dumps can't serialize.
    item.summary = object()  # type: ignore[assignment]
    result = write_item(tmp_path, item)
    assert result is None
    # No target file was created.
    assert not (backlog_dir(tmp_path) / "BL-0001.json").exists()


def test_read_item_forces_requested_id_over_body(tmp_path: Path) -> None:
    """FINDING 3: the requested/filename id is authoritative — a body claiming a
    different id is overridden."""
    bdir = backlog_dir(tmp_path)
    bdir.mkdir(parents=True, exist_ok=True)
    # File BL-0001.json whose body lies and says id == BL-9999.
    data = {"id": "BL-9999", "title": "Liar"}
    (bdir / "BL-0001.json").write_text(json.dumps(data), encoding="utf-8")
    item = read_item(tmp_path, "BL-0001")
    assert item is not None
    assert item.id == "BL-0001"
    assert item.title == "Liar"


# ── list_items ────────────────────────────────────────────────────────────────


def test_list_items_newest_first(tmp_path: Path) -> None:
    """list_items returns items sorted newest-first by created_at then id."""
    items_to_write = [
        BacklogItem(id="BL-0001", title="First", created_at="2026-01-01T00:00:00"),
        BacklogItem(id="BL-0002", title="Second", created_at="2026-06-01T00:00:00"),
        BacklogItem(id="BL-0003", title="Third", created_at="2026-03-01T00:00:00"),
    ]
    for it in items_to_write:
        write_item(tmp_path, it)

    result = list_items(tmp_path)
    assert [it.id for it in result] == ["BL-0002", "BL-0003", "BL-0001"]


def test_list_items_skips_unreadable_file(tmp_path: Path) -> None:
    """list_items skips corrupt files without raising."""
    item = BacklogItem(id="BL-0001", title="Good item", created_at="2026-01-01")
    write_item(tmp_path, item)
    bdir = backlog_dir(tmp_path)
    # Write a corrupt JSON file
    (bdir / "BL-0002.json").write_text("{{not valid", encoding="utf-8")

    result = list_items(tmp_path)
    # Only the valid item is returned
    assert len(result) == 1
    assert result[0].id == "BL-0001"


# ── completion_report ─────────────────────────────────────────────────────────


def test_completion_report_goal_reached() -> None:
    assert completion_report(goal_reached=True, iteration=3, max_iterations=5) == ("Goal reached in 3/5 iterations.")


def test_completion_report_goal_not_reached() -> None:
    assert completion_report(goal_reached=False, iteration=5, max_iterations=5) == (
        "Stopped after 5/5 iterations. Goal not fully verified."
    )


# ── status_for_outcome ────────────────────────────────────────────────────────


def test_status_for_outcome_goal_reached() -> None:
    assert status_for_outcome(goal_reached=True) == "completed"


def test_status_for_outcome_goal_not_reached() -> None:
    assert status_for_outcome(goal_reached=False) == "blocked"


# ── managed_branch_name ───────────────────────────────────────────────────────


def test_managed_branch_name_deterministic_and_sanitised() -> None:
    """Branch name is deterministic, lowercased, and starts with the right prefix."""
    name = managed_branch_name("BL-0007", "Add Login Page!")
    assert name.startswith("feature/backlog-bl-0007-")
    assert name == name.lower()
    # Deterministic — same call returns same value
    assert managed_branch_name("BL-0007", "Add Login Page!") == name


def test_managed_branch_name_blank_slug_degrades_gracefully() -> None:
    """A blank slug produces a valid branch name (no crash, ends with -item)."""
    name = managed_branch_name("BL-0007", "")
    assert name.startswith("feature/backlog-bl-0007-")
    assert name.endswith("-item")


def test_managed_branch_name_malformed_id_is_ref_safe() -> None:
    """FINDING 4: a malformed id can't inject '/' or git-ref syntax — the id is
    sanitised the same way as the slug."""
    name = managed_branch_name("../../evil~id^{}", "My Feature")
    # The single intentional prefix slash is the only slash allowed.
    assert name.count("/") == 1
    assert name.startswith("feature/")
    # No git-ref-hostile characters survive in the suffix.
    suffix = name[len("feature/") :]
    for bad in ("/", "~", "^", "{", "}", "..", ":", "?", "*", "[", "\\"):
        assert bad not in suffix
    # Still deterministic and lowercase.
    assert name == name.lower()
    assert managed_branch_name("../../evil~id^{}", "My Feature") == name


# ── DISPOSITIONS / is_terminal_disposition ───────────────────────────────────


def test_dispositions_has_exactly_three_end_states() -> None:
    """DISPOSITIONS is exactly the three no-orphan-branch end-states."""
    assert set(DISPOSITIONS) == {"merged-deleted", "abandoned-deleted", "kept"}
    assert len(DISPOSITIONS) == 3


def test_is_terminal_disposition_true_for_all_dispositions() -> None:
    for d in DISPOSITIONS:
        assert is_terminal_disposition(d) is True


def test_is_terminal_disposition_false_for_empty_string() -> None:
    assert is_terminal_disposition("") is False


def test_is_terminal_disposition_false_for_unknown() -> None:
    assert is_terminal_disposition("deleted") is False

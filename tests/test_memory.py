"""Unit tests for renmark.memory."""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import pytest

from renmark import memory


def test_ensure_memory_creates_all_files(tmp_path: Path) -> None:
    d = memory.ensure_memory(tmp_path)
    assert d == tmp_path / ".renmark" / "memory"
    for name in memory.MEMORY_FILES:
        assert (d / name).is_file(), f"missing {name}"


def test_ensure_memory_idempotent(tmp_path: Path) -> None:
    memory.ensure_memory(tmp_path)
    # Touch a file with sentinel content; ensure second call doesn't overwrite.
    (tmp_path / ".renmark" / "memory" / "project.md").write_text("SENTINEL\n")
    memory.ensure_memory(tmp_path)
    assert (tmp_path / ".renmark" / "memory" / "project.md").read_text() == "SENTINEL\n"


def test_log_feature_appends_under_shipped(tmp_path: Path) -> None:
    memory.log_feature(
        tmp_path,
        title="Add /healthz endpoint",
        files=["src/server.py", "tests/test_healthz.py"],
        spec=".renmark/specs/foo.spec.md",
        plan=".renmark/plans/foo.plan.md",
        commits="abc123..def456",
        description="Returns server status.",
        date="2026-05-12",
    )
    text = (tmp_path / ".renmark" / "memory" / "features.md").read_text()
    assert "## Shipped" in text
    assert "Add /healthz endpoint" in text
    assert "`src/server.py`" in text
    assert "Returns server status." in text
    # Newest at top: our new entry should come BEFORE the template example.
    shipped_block = text.split("## Shipped", 1)[1].split("## In progress")[0]
    new_idx = shipped_block.index("Add /healthz endpoint")
    example_idx = shipped_block.find("(example)")
    if example_idx != -1:
        assert new_idx < example_idx


def test_log_bug_appends_under_fixed(tmp_path: Path) -> None:
    memory.log_bug(
        tmp_path,
        title="/metrics 500 under load",
        severity="major",
        symptom="intermittent 500s",
        root_cause="non-thread-safe buffer",
        fix="add threading.Lock; commit abc123",
        lesson="multi-threaded handlers must lock-guard shared state",
        date="2026-05-12",
    )
    bugs = (tmp_path / ".renmark" / "memory" / "bugs.md").read_text()
    assert "/metrics 500 under load" in bugs
    assert "**Severity:** major" in bugs
    # Lesson also goes to learnings.md.
    learnings = (tmp_path / ".renmark" / "memory" / "learnings.md").read_text()
    assert "multi-threaded handlers must lock-guard shared state" in learnings


def test_log_decision_numbers_adrs(tmp_path: Path) -> None:
    memory.log_decision(
        tmp_path,
        title="Use Python stdlib HTTP server",
        status="Accepted",
        context="Need a server with zero deps.",
        decision="Use http.server.",
        alternatives=["Flask — adds a dependency", "FastAPI — overkill"],
        consequences=["No async support", "Easy to vendor"],
    )
    text = (tmp_path / ".renmark" / "memory" / "decisions.md").read_text()
    # Template ships ADR-000 as example; ours should be ADR-001+.
    assert "Use Python stdlib HTTP server" in text
    assert "ADR-001" in text


def test_append_routing(tmp_path: Path) -> None:
    memory.append_routing(
        tmp_path,
        signature="target=tests/**, complexity=medium",
        executor="codex",
        outcome="passed",
        run_id="20260512-100000-abcd",
        date="2026-05-12",
    )
    text = (tmp_path / ".renmark" / "memory" / "routing.md").read_text()
    assert "## Learned overrides" in text
    assert "target=tests/**, complexity=medium" in text
    assert "**codex**" in text


def test_append_learning(tmp_path: Path) -> None:
    memory.append_learning(
        tmp_path,
        signal="NIM hung mid-stream on mistral-medium",
        observation="route mistral-medium tasks to llama-3.2-3b on free tier",
        source="run",
        model="mistralai/mistral-medium-3.5-128b",
        date="2026-05-12",
    )
    text = (tmp_path / ".renmark" / "memory" / "learnings.md").read_text()
    assert "## Learned this project" in text
    assert "NIM hung mid-stream on mistral-medium" in text
    assert "mistralai/mistral-medium-3.5-128b" in text


def test_template_dir_resolves(tmp_path: Path) -> None:
    """Templates should be discoverable from the renmark package layout."""
    td = memory.template_dir()
    assert td is not None
    assert td.is_dir()
    # At minimum, INDEX template should exist.
    assert (td / "INDEX.md.template").is_file()


def test_log_decision_idempotent_same_day(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(memory, "_today", lambda: "2026-05-29")

    memory.log_decision(tmp_path, title="X", decision="Y")
    memory.log_decision(tmp_path, title="X", decision="Y")

    text = (tmp_path / ".renmark" / "memory" / "decisions.md").read_text()
    assert text.count("## ADR-001 — X") == 1


def test_log_decision_distinct_titles_both_appear(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(memory, "_today", lambda: "2026-05-29")

    memory.log_decision(tmp_path, title="First", decision="A")
    memory.log_decision(tmp_path, title="Second", decision="B")

    text = (tmp_path / ".renmark" / "memory" / "decisions.md").read_text()
    assert "## ADR-001 — First" in text
    assert "## ADR-002 — Second" in text


def test_log_decision_same_title_different_date(tmp_path: Path) -> None:
    memory.log_decision(tmp_path, title="Same", decision="A", date="2026-05-28")
    memory.log_decision(tmp_path, title="Same", decision="B", date="2026-05-29")

    text = (tmp_path / ".renmark" / "memory" / "decisions.md").read_text()
    assert text.count("— Same") == 2
    assert "**Date:** 2026-05-28" in text
    assert "**Date:** 2026-05-29" in text


def test_log_escalation_decision_writes_adr(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(memory, "_today", lambda: "2026-05-29")

    memory.log_escalation_decision(
        tmp_path,
        task_index=7,
        from_exec="codex",
        to_exec="opus",
        reason="Need deeper reasoning",
    )

    text = (tmp_path / ".renmark" / "memory" / "decisions.md").read_text()
    assert "Escalated task 7 from codex to opus" in text
    assert "from codex to opus" in text
    assert "Re-route to opus" in text


def test_dedupe_memory_log_removes_dupes(tmp_path: Path) -> None:
    path = memory.ensure_memory(tmp_path) / "learnings.md"
    path.write_text(
        "# Learnings\n\n"
        "## Repeated entry\n\n"
        "same-first-line\n"
        "keep this copy\n\n"
        "## Repeated entry\n\n"
        "same-first-line\n"
        "remove this copy\n"
    )

    removed = memory.dedupe_memory_log(tmp_path, "learnings.md")
    text = path.read_text()

    assert removed == 1
    assert "keep this copy" in text
    assert "remove this copy" not in text


def test_dedupe_memory_log_keeps_distinct(tmp_path: Path) -> None:
    path = memory.ensure_memory(tmp_path) / "learnings.md"
    original = "# Learnings\n\n## Entry one\n\nfirst-line-a\nbody a\n\n## Entry one\n\nfirst-line-b\nbody b\n"
    path.write_text(original)

    removed = memory.dedupe_memory_log(tmp_path, "learnings.md")

    assert removed == 0
    assert path.read_text() == original


def test_dedupe_memory_log_rejects_curated_files(tmp_path: Path) -> None:
    memory.ensure_memory(tmp_path)

    with pytest.raises(ValueError):
        memory.dedupe_memory_log(tmp_path, "decisions.md")

    with pytest.raises(ValueError):
        memory.dedupe_memory_log(tmp_path, "project.md")


def test_age_out_memory_log_moves_old(tmp_path: Path) -> None:
    today = dt.datetime.utcnow().date()
    old = (today - dt.timedelta(days=200)).isoformat()
    recent = today.isoformat()
    path = memory.ensure_memory(tmp_path) / "features.md"
    path.write_text(f"# Features\n\n## {recent} — Recent\n\nrecent body\n\n## {old} — Old\n\nold body\n")

    archive_root = tmp_path / "archive"
    moved = memory.age_out_memory_log(tmp_path, "features.md", 180, archive_root)

    text = path.read_text()
    archived = (archive_root / "memory" / "features.md").read_text()
    assert moved == 1
    assert "Recent" in text
    assert "Old" not in text
    assert "Old" in archived
    assert "Recent" not in archived


def test_age_out_memory_log_keeps_undated(tmp_path: Path) -> None:
    path = memory.ensure_memory(tmp_path) / "bugs.md"
    original = "# Bugs\n\n## Undated entry\n\nNo parseable date here.\n"
    path.write_text(original)

    moved = memory.age_out_memory_log(tmp_path, "bugs.md", 180, tmp_path / "archive")

    assert moved == 0
    assert path.read_text() == original

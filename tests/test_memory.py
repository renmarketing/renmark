"""Unit tests for renmark.memory."""

from __future__ import annotations

import datetime as dt
from collections.abc import Callable
from pathlib import Path

import pytest

from renmark import memory


def _extract_titled_entry(text: str, title: str, date: str) -> str:
    heading = f"### {date} — {title}"
    entry_start = text.index(heading)
    entry_end = text.index("\n\n---", entry_start) + len("\n\n---")
    return text[entry_start:entry_end]


def _replace_with_duplicated_feature_entry(repo: Path, title: str, date: str) -> None:
    path = memory.ensure_memory(repo) / "features.md"
    entry = _extract_titled_entry(path.read_text(), title, date)
    path.write_text(f"# Features\n\n## Shipped\n\n{entry}\n\n{entry}\n")


def _replace_with_duplicated_bug_entry(repo: Path, title: str, date: str, section: str = "Fixed") -> None:
    path = memory.ensure_memory(repo) / "bugs.md"
    entry = _extract_titled_entry(path.read_text(), title, date)
    path.write_text(f"# Bugs\n\n## {section}\n\n{entry}\n\n{entry}\n")


def _replace_with_duplicated_learning_entry(repo: Path, signal: str) -> None:
    path = memory.ensure_memory(repo) / "learnings.md"
    text = path.read_text()
    entry = next(line for line in text.splitlines() if signal in line)
    path.write_text(f"# Learnings\n\n## Learned this project\n\n{entry}\n\n{entry}\n")


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
    feature_repo = tmp_path / "feature"
    memory.log_feature(
        feature_repo,
        title="Cache warmup on boot",
        files=["src/cache.py"],
        spec=".renmark/specs/cache.spec.md",
        plan=".renmark/plans/cache.plan.md",
        commits="abc123",
        description="Populate hot keys during startup.",
        date="2026-05-12",
    )
    memory.log_feature(
        feature_repo,
        title="Cache warmup on boot",
        files=["src/cache.py"],
        spec=".renmark/specs/cache.spec.md",
        plan=".renmark/plans/cache.plan.md",
        commits="abc123",
        description="Populate hot keys during startup.",
        date="2026-05-12",
    )
    _replace_with_duplicated_feature_entry(feature_repo, "Cache warmup on boot", "2026-05-12")
    feature_path = memory.ensure_memory(feature_repo) / "features.md"
    removed = memory.dedupe_memory_log(feature_repo, "features.md")
    feature_text = feature_path.read_text()
    assert removed == 1
    assert feature_text.count("### 2026-05-12 — Cache warmup on boot") == 1

    bug_repo = tmp_path / "bug"
    memory.log_bug(
        bug_repo,
        title="Worker leak under retry storm",
        severity="major",
        symptom="workers remain alive after retries",
        root_cause="cleanup path skipped after timeout",
        fix="always close workers in finally",
        lesson="retry cleanup must always run",
        date="2026-05-12",
    )
    memory.log_bug(
        bug_repo,
        title="Worker leak under retry storm",
        severity="major",
        symptom="workers remain alive after retries",
        root_cause="cleanup path skipped after timeout",
        fix="always close workers in finally",
        lesson="retry cleanup must always run",
        date="2026-05-12",
    )
    _replace_with_duplicated_bug_entry(bug_repo, "Worker leak under retry storm", "2026-05-12")
    bug_path = memory.ensure_memory(bug_repo) / "bugs.md"
    removed = memory.dedupe_memory_log(bug_repo, "bugs.md")
    bug_text = bug_path.read_text()
    assert removed == 1
    assert bug_text.count("### 2026-05-12 — Worker leak under retry storm") == 1

    learning_repo = tmp_path / "learning"
    memory.append_learning(
        learning_repo,
        signal="Queue workers leaked on retry",
        observation="always close leaked workers in cleanup",
        source="run",
        model="test-model",
        date="2026-05-12",
    )
    memory.append_learning(
        learning_repo,
        signal="Queue workers leaked on retry",
        observation="always close leaked workers in cleanup",
        source="run",
        model="test-model",
        date="2026-05-12",
    )
    _replace_with_duplicated_learning_entry(learning_repo, "Queue workers leaked on retry")
    learning_path = memory.ensure_memory(learning_repo) / "learnings.md"
    removed = memory.dedupe_memory_log(learning_repo, "learnings.md")
    learning_text = learning_path.read_text()
    assert removed == 1
    assert learning_text.count("Queue workers leaked on retry") == 1


def test_dedupe_memory_log_keeps_distinct(tmp_path: Path) -> None:
    feature_repo = tmp_path / "feature"
    memory.log_feature(
        feature_repo,
        title="Cache warmup on boot",
        files=["src/cache.py"],
        spec=".renmark/specs/cache.spec.md",
        plan=".renmark/plans/cache.plan.md",
        commits="abc123",
        description="Populate hot keys during startup.",
        date="2026-05-12",
    )
    memory.log_feature(
        feature_repo,
        title="Cache preload after deploy",
        files=["src/cache.py"],
        spec=".renmark/specs/cache.spec.md",
        plan=".renmark/plans/cache.plan.md",
        commits="def456",
        description="Preload hot keys after each deploy.",
        date="2026-05-12",
    )
    feature_path = memory.ensure_memory(feature_repo) / "features.md"
    original = feature_path.read_text()
    removed = memory.dedupe_memory_log(feature_repo, "features.md")
    assert removed == 0
    assert feature_path.read_text() == original

    bug_repo = tmp_path / "bug"
    memory.log_bug(
        bug_repo,
        title="Worker leak under retry storm",
        severity="major",
        symptom="workers remain alive after retries",
        root_cause="cleanup path skipped after timeout",
        fix="always close workers in finally",
        lesson="retry cleanup must always run",
        date="2026-05-12",
    )
    memory.log_bug(
        bug_repo,
        title="Retry budget miscounted",
        severity="minor",
        symptom="budget drops below zero",
        root_cause="counter decremented twice",
        fix="dedupe decrement path",
        lesson="budget counters need one write path",
        date="2026-05-12",
    )
    bug_path = memory.ensure_memory(bug_repo) / "bugs.md"
    original = bug_path.read_text()
    removed = memory.dedupe_memory_log(bug_repo, "bugs.md")
    assert removed == 0
    assert bug_path.read_text() == original

    learning_repo = tmp_path / "learning"
    memory.append_learning(
        learning_repo,
        signal="Queue workers leaked on retry",
        observation="always close leaked workers in cleanup",
        source="run",
        model="test-model",
        date="2026-05-12",
    )
    memory.append_learning(
        learning_repo,
        signal="Retry budget drifted negative",
        observation="route all budget writes through one function",
        source="run",
        model="test-model",
        date="2026-05-12",
    )
    learning_path = memory.ensure_memory(learning_repo) / "learnings.md"
    original = learning_path.read_text()
    removed = memory.dedupe_memory_log(learning_repo, "learnings.md")
    assert removed == 0
    assert learning_path.read_text() == original


def test_dedupe_memory_log_rejects_curated_files(tmp_path: Path) -> None:
    memory.ensure_memory(tmp_path)

    with pytest.raises(ValueError):
        memory.dedupe_memory_log(tmp_path, "decisions.md")

    with pytest.raises(ValueError):
        memory.dedupe_memory_log(tmp_path, "project.md")


def test_age_out_memory_log_moves_old(tmp_path: Path) -> None:
    today = dt.date.today()
    old = (today - dt.timedelta(days=200)).isoformat()
    recent = today.isoformat()
    memory.log_feature(
        tmp_path,
        title="Archive this shipped feature",
        files=["src/archive.py"],
        spec=".renmark/specs/archive.spec.md",
        plan=".renmark/plans/archive.plan.md",
        commits="abc123",
        description="This shipped long ago.",
        date=old,
    )
    memory.log_feature(
        tmp_path,
        title="Keep this shipped feature",
        files=["src/current.py"],
        spec=".renmark/specs/current.spec.md",
        plan=".renmark/plans/current.plan.md",
        commits="def456",
        description="This shipped recently.",
        date=recent,
    )
    path = memory.ensure_memory(tmp_path) / "features.md"

    archive_root = tmp_path / "archive"
    moved = memory.age_out_memory_log(tmp_path, "features.md", 180, archive_root)

    text = path.read_text()
    archived = (archive_root / "memory" / "features.md").read_text()
    assert moved == 1
    assert "Keep this shipped feature" in text
    assert "Archive this shipped feature" not in text
    assert "Archive this shipped feature" in archived
    assert "Keep this shipped feature" not in archived
    assert "## Shipped" in archived
    assert archived.index("## Shipped") < archived.index("Archive this shipped feature")


def test_age_out_memory_log_keeps_undated(tmp_path: Path) -> None:
    memory.append_learning(
        tmp_path,
        signal="Undated learning stays in place",
        observation="age-out ignores entries without parseable dates",
        source="run",
        model="test-model",
        date="not-a-date",
    )
    path = memory.ensure_memory(tmp_path) / "learnings.md"
    original = path.read_text()

    moved = memory.age_out_memory_log(tmp_path, "learnings.md", 180, tmp_path / "archive")

    assert moved == 0
    assert path.read_text() == original


@pytest.mark.parametrize(
    ("name", "writer", "kwargs", "entry_marker"),
    [
        (
            "features.md",
            memory.log_feature,
            {
                "title": "Schema feature duplicate",
                "files": ["src/feature.py"],
                "spec": ".renmark/specs/feature.spec.md",
                "plan": ".renmark/plans/feature.plan.md",
                "commits": "abc123",
                "description": "Exercise the shipped feature schema.",
                "date": "2026-05-12",
            },
            "### 2026-05-12 — Schema feature duplicate",
        ),
        (
            "bugs.md",
            memory.log_bug,
            {
                "title": "Schema bug duplicate",
                "severity": "major",
                "symptom": "schema bug symptom",
                "root_cause": "schema bug root cause",
                "fix": "schema bug fix",
                "lesson": "schema bug lesson",
                "date": "2026-05-12",
            },
            "### 2026-05-12 — Schema bug duplicate",
        ),
        (
            "learnings.md",
            memory.append_learning,
            {
                "signal": "Schema learning duplicate",
                "observation": "Exercise the learning schema.",
                "source": "run",
                "model": "test-model",
                "date": "2026-05-12",
            },
            "Schema learning duplicate",
        ),
    ],
)
def test_dedupe_handles_each_schema(
    tmp_path: Path,
    name: str,
    writer: Callable[..., None],
    kwargs: dict[str, object],
    entry_marker: str,
) -> None:
    repo = tmp_path / name.removesuffix(".md")
    writer(repo, **kwargs)
    if name == "features.md":
        _replace_with_duplicated_feature_entry(repo, "Schema feature duplicate", "2026-05-12")
    elif name == "bugs.md":
        _replace_with_duplicated_bug_entry(repo, "Schema bug duplicate", "2026-05-12")
    else:
        _replace_with_duplicated_learning_entry(repo, "Schema learning duplicate")

    removed = memory.dedupe_memory_log(repo, name)
    text = (memory.ensure_memory(repo) / name).read_text()

    assert removed == 1
    assert text.count(entry_marker) == 1


def test_age_out_preserves_section_header(tmp_path: Path) -> None:
    today = dt.date.today()
    old = (today - dt.timedelta(days=200)).isoformat()
    recent = today.isoformat()
    memory.log_bug(
        tmp_path,
        title="Archive this bug entry",
        severity="major",
        symptom="old bug symptom",
        root_cause="old bug root cause",
        fix="old bug fix",
        lesson="old bug lesson",
        section="Open",
        date=old,
    )
    memory.log_bug(
        tmp_path,
        title="Keep this bug entry",
        severity="minor",
        symptom="recent bug symptom",
        root_cause="recent bug root cause",
        fix="recent bug fix",
        lesson="recent bug lesson",
        section="Open",
        date=recent,
    )

    moved = memory.age_out_memory_log(tmp_path, "bugs.md", 180, tmp_path / "archive")
    archived = (tmp_path / "archive" / "memory" / "bugs.md").read_text()

    assert moved == 1
    assert "## Open" in archived
    assert archived.index("## Open") < archived.index("Archive this bug entry")


def test_append_routing_idempotent_on_exact_entry(tmp_path: Path) -> None:
    """routing.md is curated (hygiene refuses to dedupe) — a replayed append
    must not duplicate the signal."""
    for _ in range(2):
        memory.append_routing(
            tmp_path,
            signature="target=tests/**, complexity=medium",
            executor="codex",
            outcome="passed",
            run_id="r1",
            date="2026-06-09",
        )
    text = (memory.memory_dir(tmp_path) / "routing.md").read_text(encoding="utf-8")
    assert text.count("run=r1") == 1


# ── _insert_after_section blank-line leak regression ─────────────────────────


def test_insert_after_section_exactly_one_blank_on_first_insert() -> None:
    """A fresh section gets exactly one blank line between the header and the block."""
    text = "# Doc\n\n## Shipped\n\nold entry\n"
    result = memory._insert_after_section(text, "## Shipped", "new entry")
    after = result.split("## Shipped", 1)[1]
    # Exactly one blank line (i.e. "\n\n") before "new entry"
    assert after.startswith("\n\nnew entry"), repr(after[:40])


def test_insert_after_section_no_blank_leak_on_repeated_appends() -> None:
    """Two consecutive appends must leave exactly ONE blank line after the header.

    Regression for the blank-line LEAK: prior code preserved all existing
    blanks AND added one, so every append grew the gap by one line.
    After the fix, two appends still leave only one blank line after the header.
    """
    text = "# Doc\n\n## Shipped\n\n"

    result = memory._insert_after_section(text, "## Shipped", "entry-1")
    result = memory._insert_after_section(result, "## Shipped", "entry-2")

    after = result.split("## Shipped", 1)[1]
    # One blank line then the new entry — not two+ blanks.
    assert after.startswith("\n\nentry-2"), repr(after[:40])
    # And entry-1 is still present somewhere later in the file
    assert "entry-1" in result


def test_insert_after_section_body_blank_lines_preserved() -> None:
    """Blank lines WITHIN entries (below the first non-blank) are NOT collapsed."""
    text = "# Doc\n\n## Shipped\n\nentry-a\n\nbody-a\n"
    result = memory._insert_after_section(text, "## Shipped", "entry-b")
    assert "entry-a" in result
    assert "body-a" in result
    after = result.split("## Shipped", 1)[1]
    assert after.startswith("\n\nentry-b"), repr(after[:40])


# ── dead code absence guard ───────────────────────────────────────────────────


def test_read_index_and_read_file_are_removed() -> None:
    """read_index and read_file were dead-code; they must not be present."""
    assert not hasattr(memory, "read_index"), "read_index must be deleted (dead code)"
    assert not hasattr(memory, "read_file"), "read_file must be deleted (dead code)"

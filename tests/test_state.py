"""Unit tests for renmark.state."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from renmark import state


def test_usage_round_trip(tmp_path: Path) -> None:
    """Attempt-0 rows always append (a task may make many legitimate calls);
    only explicit retries (attempt > 0) are idempotent on
    (run_id, task_id, attempt, model)."""
    rec = state.UsageRecord(
        ts="2026-05-11T15:30:22+00:00",
        run_id="run-x",
        task_id=3,
        model="codestral-22b",
        prompt_tokens=120,
        completion_tokens=80,
    )
    state.append_usage(tmp_path, rec)
    state.append_usage(tmp_path, rec)  # attempt 0 → two legit calls, two rows
    rows = state.read_usage(tmp_path)
    assert len(rows) == 2
    assert rows[0]["task_id"] == 3
    assert rows[0]["prompt_tokens"] == 120

    # A retry row (attempt > 0) is idempotent: replaying the same attempt
    # appends exactly once.
    retry = state.UsageRecord(
        ts="2026-05-11T15:31:00+00:00",
        run_id="run-x",
        task_id=3,
        model="codestral-22b",
        prompt_tokens=120,
        completion_tokens=80,
        attempt=1,
    )
    state.append_usage(tmp_path, retry)
    state.append_usage(tmp_path, retry)  # replayed retry → deduped
    rows = state.read_usage(tmp_path)
    assert len(rows) == 3


def test_usage_no_run_id_always_appends(tmp_path: Path) -> None:
    """Rows with an empty run_id carry no stable identity → never deduped."""
    rec = state.UsageRecord(
        ts="2026-05-11T15:30:22+00:00",
        run_id="",
        task_id=1,
        model="codex",
        prompt_tokens=0,
        completion_tokens=0,
    )
    state.append_usage(tmp_path, rec)
    state.append_usage(tmp_path, rec)
    assert len(state.read_usage(tmp_path)) == 2


def test_usage_old_rows_without_attempt_still_parse(tmp_path: Path) -> None:
    """Read-side back-compat: pre-existing rows lacking the 'attempt' key still
    parse (treated as attempt=0) and retry-dedup works alongside them."""
    led = tmp_path / ".renmark" / "state"
    led.mkdir(parents=True)
    (led / "usage.jsonl").write_text(
        json.dumps(
            {
                "ts": "2026-05-11T15:30:22+00:00",
                "run_id": "run-old",
                "task_id": 2,
                "model": "codex",
                "prompt_tokens": 0,
                "completion_tokens": 0,
            }
        )
        + "\n"
    )
    # A new attempt-0 row always appends (legit additional call).
    state.append_usage(
        tmp_path,
        state.UsageRecord(
            ts="2026-05-11T15:31:00+00:00",
            run_id="run-old",
            task_id=2,
            model="codex",
            prompt_tokens=0,
            completion_tokens=0,
        ),
    )
    assert len(state.read_usage(tmp_path)) == 2
    # A retry row (attempt=1) replayed twice appends exactly once, even with
    # attempt-less legacy rows in the ledger.
    retry = state.UsageRecord(
        ts="2026-05-11T15:32:00+00:00",
        run_id="run-old",
        task_id=2,
        model="codex",
        prompt_tokens=0,
        completion_tokens=0,
        attempt=1,
    )
    state.append_usage(tmp_path, retry)
    state.append_usage(tmp_path, retry)
    assert len(state.read_usage(tmp_path)) == 3


def test_pause_round_trip(tmp_path: Path) -> None:
    assert state.read_pause(tmp_path) is None
    ps = state.PauseState(
        run_id="r1",
        plan_path="plans/foo.md",
        last_task_index=3,
        reason="429 backoff exhausted",
        ts=state.now_iso(),
    )
    state.write_pause(tmp_path, ps)
    got = state.read_pause(tmp_path)
    assert got is not None
    assert got.last_task_index == 3
    assert got.reason.startswith("429")
    state.clear_pause(tmp_path)
    assert state.read_pause(tmp_path) is None


def test_usage_today_filters_dates(tmp_path: Path) -> None:
    today_iso = state.now_iso()
    old_iso = "2020-01-01T00:00:00+00:00"
    state.append_usage(
        tmp_path,
        state.UsageRecord(today_iso, "r", 1, "m", 100, 50),
    )
    # Distinct task_id so it isn't deduped against the row above.
    state.append_usage(
        tmp_path,
        state.UsageRecord(old_iso, "r", 2, "m", 99999, 99999),
    )
    assert state.usage_today(tmp_path) == 150


def test_new_run_id_unique() -> None:
    a, b = state.new_run_id(), state.new_run_id()
    assert a != b
    assert len(a) > 10


def test_completed_task_indices_from_git(tmp_path: Path) -> None:
    """Build a tiny git repo, make commits, scan."""
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=tmp_path, check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.name", "t"], check=True)
    (tmp_path / "a.txt").write_text("a")
    subprocess.run(["git", "-C", str(tmp_path), "add", "a.txt"], check=True)
    subprocess.run(
        ["git", "-C", str(tmp_path), "commit", "-q", "-m", "[nim] task 1: first"],
        check=True,
    )
    (tmp_path / "b.txt").write_text("b")
    subprocess.run(["git", "-C", str(tmp_path), "add", "b.txt"], check=True)
    subprocess.run(
        ["git", "-C", str(tmp_path), "commit", "-q", "-m", "[manual] task 3: third"],
        check=True,
    )
    (tmp_path / "c.txt").write_text("c")
    subprocess.run(["git", "-C", str(tmp_path), "add", "c.txt"], check=True)
    subprocess.run(
        ["git", "-C", str(tmp_path), "commit", "-q", "-m", "unrelated commit"],
        check=True,
    )

    completed = state.completed_task_indices(tmp_path)
    assert completed == {1, 3}


def test_completed_task_indices_non_git_returns_empty(tmp_path: Path) -> None:
    assert state.completed_task_indices(tmp_path) == set()


def test_escalation_dir_created(tmp_path: Path) -> None:
    d = state.escalation_dir(tmp_path, 7)
    assert d.is_dir()
    assert d.name == "task-7"


def test_wave_summary_rotates_when_over_cap(tmp_path: Path, monkeypatch) -> None:
    """Wave-summaries dir must not grow unbounded — overflow goes to archive/."""
    monkeypatch.setattr(state._core, "WAVE_SUMMARIES_KEEP", 3)
    for i in range(5):
        state.write_wave_summary(tmp_path, i, [{"task_id": i}])
    waves_dir = tmp_path / ".renmark" / "state" / "wave-summaries"
    hot = list(waves_dir.glob("wave-*.json"))
    assert len(hot) == 3, f"expected 3 hot files, got {len(hot)}: {[p.name for p in hot]}"
    archive = tmp_path / ".renmark" / "state" / "archive" / "wave-summaries"
    assert archive.exists()
    archived = list(archive.rglob("wave-*.json"))
    assert len(archived) == 2


def test_open_log_rotates_when_over_cap(tmp_path: Path, monkeypatch) -> None:
    """logs/ dir lives at .renmark/logs/ (not under state/) — rotation must
    still find the repo root via the .renmark/ marker walk."""
    monkeypatch.setattr(state._core, "LOGS_KEEP", 2)
    for i in range(4):
        state.open_log(tmp_path, f"cmd-{i}", run_id=f"r{i}")
    logs = list((tmp_path / ".renmark" / "logs").glob("*.log"))
    assert len(logs) == 2
    archive = tmp_path / ".renmark" / "state" / "archive" / "logs"
    archived = list(archive.rglob("*.log"))
    assert len(archived) == 2


def test_escalation_dir_rotates(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(state._core, "ESCALATIONS_KEEP", 2)
    for i in range(4):
        state.escalation_dir(tmp_path, i)
    parent = tmp_path / ".renmark" / "state" / "escalations"
    hot = [p for p in parent.iterdir() if p.name.startswith("task-")]
    assert len(hot) == 2


def test_rotate_dir_skips_outside_renmark(tmp_path: Path) -> None:
    """If the target isn't inside a .renmark/ tree, rotate silently no-ops."""
    bogus = tmp_path / "not-a-renmark-tree"
    bogus.mkdir()
    for i in range(5):
        (bogus / f"{i}.txt").write_text(str(i))
    moved = state.rotate_dir(bogus, keep=2, subdir_in_archive="x")
    assert moved == 0
    assert len(list(bogus.iterdir())) == 5  # untouched


def test_commit_pattern_variants_all_recognized(tmp_path: Path) -> None:
    """v0.1.5 regression: orchestrator missed legitimate task-completion
    commits when the prefix wasn't bracketed, causing resume to re-run.
    """
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=tmp_path, check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.name", "t"], check=True)

    variants = [
        ("[nim] task 1: bracketed nim", 1),
        ("[manual] task 2: bracketed manual", 2),
        ("nim task 3: bare nim", 3),
        ("manual task 4: bare manual", 4),
        ("nim task 5 (manual): bare with paren", 5),
        ("manual task 6 (nim): bare with paren", 6),
        ("[renmark] task 7: bracketed renmark", 7),
        ("[codex] task 8: bracketed codex", 8),
        ("renmark task 9: bare renmark", 9),
    ]
    for i, (msg, _) in enumerate(variants):
        f = tmp_path / f"{i}.txt"
        f.write_text(str(i))
        subprocess.run(["git", "-C", str(tmp_path), "add", f.name], check=True)
        subprocess.run(["git", "-C", str(tmp_path), "commit", "-q", "-m", msg], check=True)

    # Add one that must NOT match (no nim/manual prefix at all).
    (tmp_path / "noise.txt").write_text("x")
    subprocess.run(["git", "-C", str(tmp_path), "add", "noise.txt"], check=True)
    subprocess.run(
        ["git", "-C", str(tmp_path), "commit", "-q", "-m", "task 99: should not match"],
        check=True,
    )

    completed = state.completed_task_indices(tmp_path)
    assert completed == {1, 2, 3, 4, 5, 6, 7, 8, 9}, completed


def test_usage_today_and_month_tolerate_malformed_rows(tmp_path: Path) -> None:
    """Type-malformed (valid-JSON) ledger rows must not crash the rolling sums."""
    import datetime as dt

    led = tmp_path / ".renmark" / "state"
    led.mkdir(parents=True)
    today = dt.datetime.now(dt.timezone.utc).date().isoformat()
    rows = [
        {"ts": today + "T01:00:00+00:00", "prompt_tokens": 100, "completion_tokens": 50},
        {"ts": 12345, "prompt_tokens": 100, "completion_tokens": 50},
        {"ts": today + "T02:00:00+00:00", "prompt_tokens": "oops", "completion_tokens": None},
    ]
    (led / "usage.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    assert state.usage_today(tmp_path) == 150
    assert state.usage_this_month(tmp_path) == 150

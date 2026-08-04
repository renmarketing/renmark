"""Unit tests for renmark.roadmap."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from renmark import roadmap, state


def _init_git(repo: Path) -> None:
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=str(repo), check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "t"], check=True)


def _commit(repo: Path, fname: str, msg: str) -> str:
    (repo / fname).write_text(f"// {fname}\n")
    subprocess.run(["git", "-C", str(repo), "add", fname], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", msg], check=True)
    sha = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "--short", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    return sha


def _log_usage(repo: Path, task_id: int, model: str, p: int, c: int, ts: str = "2026-05-12T10:00:00+00:00") -> None:
    state.append_usage(
        repo,
        state.UsageRecord(
            ts=ts,
            run_id="r1",
            task_id=task_id,
            model=model,
            prompt_tokens=p,
            completion_tokens=c,
        ),
    )


def test_empty_repo_returns_no_rows(tmp_path: Path) -> None:
    rows = roadmap.build_rows(tmp_path)
    assert rows == []


def test_shipped_tasks_from_git(tmp_path: Path) -> None:
    _init_git(tmp_path)
    sha1 = _commit(tmp_path, "a.py", "[nim] task 1: first")
    sha2 = _commit(tmp_path, "b.py", "[nim] task 2: second")
    _log_usage(tmp_path, 1, "meta/llama-3.2-3b-instruct", 100, 50)
    _log_usage(tmp_path, 2, "mistralai/mistral-large-3-675b-instruct-2512", 500, 300)

    rows = roadmap.build_rows(tmp_path)
    assert len(rows) == 2
    by_task = {r.task: r for r in rows}
    assert by_task["task 1"].status == "shipped"
    assert by_task["task 1"].llm == "llama-3.2-3b-instruct"
    assert by_task["task 1"].tokens == 150
    assert by_task["task 1"].commit == sha1
    assert by_task["task 2"].commit == sha2


def test_in_progress_task_no_commit(tmp_path: Path) -> None:
    _init_git(tmp_path)
    _log_usage(tmp_path, 5, "codex", 200, 100)
    rows = roadmap.build_rows(tmp_path)
    assert len(rows) == 1
    assert rows[0].status == "in-progress"
    assert rows[0].commit == ""


def test_retried_task_marked_when_multiple_calls(tmp_path: Path) -> None:
    _init_git(tmp_path)
    _log_usage(tmp_path, 9, "codex", 100, 50)
    _log_usage(tmp_path, 9, "codex", 100, 50)
    _log_usage(tmp_path, 9, "codex", 100, 50)
    rows = roadmap.build_rows(tmp_path)
    assert rows[0].status == "retried"


def test_render_table_has_totals(tmp_path: Path) -> None:
    _init_git(tmp_path)
    _commit(tmp_path, "a.py", "[nim] task 1: a")
    _log_usage(tmp_path, 1, "meta/llama-3.2-3b-instruct", 100, 50)
    table = roadmap.render_table(roadmap.build_rows(tmp_path))
    assert "Totals" in table
    assert "By status" in table
    assert "task 1" in table


def test_write_roadmap_md(tmp_path: Path) -> None:
    _init_git(tmp_path)
    _commit(tmp_path, "a.py", "[nim] task 1: a")
    _log_usage(tmp_path, 1, "codex", 1000, 500)
    out = roadmap.write_roadmap_md(tmp_path)
    assert out.is_file()
    text = out.read_text()
    assert "# Roadmap" in text
    # codex pricing is renmark.cost.PRICE_PER_KTOK["codex"] == 0.03/kT,
    # so 1500 tokens ≈ $0.045 (was incorrectly asserting $0.075 / 0.05-per-kT
    # before Release 6 fixed COST_PER_KT's drift from the canonical table).
    assert "$0.045" in text


def test_cost_estimate_zero_for_nim(tmp_path: Path) -> None:
    _init_git(tmp_path)
    _commit(tmp_path, "a.py", "[nim] task 1: a")
    _log_usage(tmp_path, 1, "meta/llama-3.2-3b-instruct", 1000, 500)
    rows = roadmap.build_rows(tmp_path)
    assert rows[0].cost_usd == 0.0


def test_cost_per_kt_has_fable_tier() -> None:
    assert roadmap.COST_PER_KT["fable"] == 0.030
    assert roadmap.COST_PER_KT["fable"] > roadmap.COST_PER_KT["opus"]


def test_estimate_cost_matches_fable_models(tmp_path: Path) -> None:
    """Fable model strings must bill at the fable rate, not fall through to 0.0."""
    # 1000 tokens at $0.030/kT = $0.030 — for both the bare tier name and the full model ID.
    assert roadmap._estimate_cost("fable", 1000) == 0.030
    assert roadmap._estimate_cost("claude-fable-5", 1000) == 0.030
    # End-to-end: a ledgered fable row carries the fable cost.
    _init_git(tmp_path)
    _commit(tmp_path, "a.py", "[nim] task 1: a")
    _log_usage(tmp_path, 1, "claude-fable-5", 1000, 500)
    rows = roadmap.build_rows(tmp_path)
    assert rows[0].cost_usd == 1500 / 1000.0 * roadmap.COST_PER_KT["fable"]
    assert rows[0].cost_usd > 0.0


def test_aggregate_usage_tolerates_malformed_rows(tmp_path: Path) -> None:
    """One type-malformed ledger row must not kill /renmark:roadmap."""
    led = tmp_path / ".renmark" / "state"
    led.mkdir(parents=True)
    rows = [
        {
            "task_id": 1,
            "prompt_tokens": 10,
            "completion_tokens": 5,
            "model": "codex",
            "ts": "2026-06-09T00:00:00+00:00",
        },
        {"task_id": "bogus", "prompt_tokens": 10},
        {"task_id": 1, "prompt_tokens": "oops", "completion_tokens": [1], "model": 7, "ts": 99},
    ]
    (led / "usage.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    agg = roadmap._aggregate_usage(tmp_path)
    assert agg[1]["tokens_in"] == 10
    assert agg[1]["tokens_out"] == 5
    assert agg[1]["calls"] == 2
    assert "bogus" not in agg

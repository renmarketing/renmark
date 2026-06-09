"""Unit tests for renmark.loop (Loop Mode state machine).

Hermetic: every test runs under pytest's ``tmp_path`` and seeds the usage
ledger through the real :func:`renmark.state.append_usage` API rather than
hardcoding the on-disk layout. All magic numbers reference module constants
from ``renmark.loop`` (DEFAULT_BUDGET_TOKENS / DEFAULT_MAX_ITERATIONS /
COST_PER_KTOKEN_USD) so the suite tracks the source of truth.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from renmark import loop
from renmark.loop import (
    COST_PER_KTOKEN_USD,
    DEFAULT_BUDGET_TOKENS,
    DEFAULT_MAX_ITERATIONS,
    LoopState,
    budget_remaining,
    build_decision,
    estimate_usd,
    loop_id,
    parse_budget,
    read_loop,
    refresh_spent,
    stop_reason,
    write_loop,
)
from renmark.state import UsageRecord, append_usage


# ── write_loop / read_loop round-trip ──────────────────────────────────────


def test_write_then_read_loop_round_trip(tmp_path: Path) -> None:
    """All fields survive a write -> read cycle under .renmark/loops/<id>/."""
    lid = loop_id("2026-06-09", "Add Auth!")
    state = LoopState(
        goal="ship auth",
        verify_cmd="pytest -q",
        budget_tokens=123_456,
        budget_usd_estimate="$1.23",
        spent_tokens=42,
        run_id="run-abc",
        max_iterations=7,
        iteration=3,
        status="running",
        pending_step="",
    )

    written = write_loop(tmp_path, lid, state)
    assert written is not None
    # Lands under the canonical .renmark/loops/<id>/loop.json location.
    assert written == loop.loop_dir(tmp_path, lid) / loop.LOOP_JSON
    assert written.exists()

    loaded = read_loop(tmp_path, lid)
    assert loaded is not None
    assert loaded.goal == "ship auth"
    assert loaded.verify_cmd == "pytest -q"
    assert loaded.budget_tokens == 123_456
    assert loaded.budget_usd_estimate == "$1.23"
    assert loaded.spent_tokens == 42
    assert loaded.run_id == "run-abc"
    assert loaded.max_iterations == 7
    assert loaded.iteration == 3
    assert loaded.status == "running"
    assert loaded.pending_step == ""


def test_loop_id_sanitises_slug() -> None:
    assert loop_id("2026-06-09", "Add Auth!") == "loop-2026-06-09-add-auth"
    assert loop_id("2026-06-09", "   ") == "loop-2026-06-09-loop"


def test_read_loop_missing_returns_none(tmp_path: Path) -> None:
    assert read_loop(tmp_path, "loop-does-not-exist") is None


def test_read_loop_corrupt_returns_none_no_raise(tmp_path: Path) -> None:
    lid = "loop-2026-06-09-corrupt"
    path = loop.loop_dir(tmp_path, lid) / loop.LOOP_JSON
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{ this is not json", encoding="utf-8")
    assert read_loop(tmp_path, lid) is None


def test_read_loop_non_dict_payload_returns_none(tmp_path: Path) -> None:
    lid = "loop-2026-06-09-list"
    path = loop.loop_dir(tmp_path, lid) / loop.LOOP_JSON
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("[1, 2, 3]", encoding="utf-8")
    assert read_loop(tmp_path, lid) is None


def test_read_loop_drops_unknown_fields(tmp_path: Path) -> None:
    """Schema drift (an extra key) must not crash the constructor."""
    lid = "loop-2026-06-09-extra"
    path = loop.loop_dir(tmp_path, lid) / loop.LOOP_JSON
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('{"goal": "g", "totally_new_field": 99}', encoding="utf-8")
    loaded = read_loop(tmp_path, lid)
    assert loaded is not None
    assert loaded.goal == "g"


# ── parse_budget / estimate_usd ─────────────────────────────────────────────


def test_parse_budget_token_int() -> None:
    tokens, usd = parse_budget(250_000)
    assert tokens == 250_000
    assert usd == estimate_usd(250_000)


def test_parse_budget_numeric_string() -> None:
    assert parse_budget("300000")[0] == 300_000
    assert parse_budget("300_000")[0] == 300_000
    assert parse_budget("300,000")[0] == 300_000


def test_parse_budget_dollar_string_matches_default() -> None:
    """At $0.01/1k tokens, a $3.00 budget resolves to the 300k default."""
    # Guard: this equivalence only holds if the constant is the assumed rate.
    assert COST_PER_KTOKEN_USD == pytest.approx(0.01)
    expected = round((3.00 / COST_PER_KTOKEN_USD) * 1000.0)
    tokens, usd = parse_budget("$3.00")
    assert tokens == expected
    assert tokens == DEFAULT_BUDGET_TOKENS
    assert usd == estimate_usd(tokens)
    # Bare "$3" parses identically.
    assert parse_budget("$3")[0] == expected


def test_parse_budget_blank_and_garbage_default() -> None:
    for bad in ("", "   ", "not-a-number", "$", "-5", 0, -100):
        tokens, usd = parse_budget(bad)  # type: ignore[arg-type]
        assert tokens == DEFAULT_BUDGET_TOKENS
        assert usd == estimate_usd(DEFAULT_BUDGET_TOKENS)


def test_parse_budget_rejects_bool() -> None:
    """bool is an int subclass but must not be read as a token count."""
    assert parse_budget(True)[0] == DEFAULT_BUDGET_TOKENS  # type: ignore[arg-type]


def test_estimate_usd_consistency_both_directions() -> None:
    # token -> $ derivation follows the documented blended rate.
    assert estimate_usd(DEFAULT_BUDGET_TOKENS) == "$3.00"
    assert estimate_usd(100_000) == "$1.00"
    assert estimate_usd(0) == "$0.00"
    assert estimate_usd(-50) == "$0.00"
    # $-string -> tokens -> $ round-trips to the same figure.
    tokens, usd = parse_budget("$3.00")
    assert estimate_usd(tokens) == usd == "$3.00"


# ── build_decision ──────────────────────────────────────────────────────────


def test_build_decision_goal_reached() -> None:
    meta = {
        "completion_state": "complete",
        "validation_status": "validated",
        "summary_lines": ["all 12 tests pass", "smoke ok"],
        "model_recommendation": "opus",
    }
    decision = build_decision(meta, spent_delta=50_000)
    assert decision["goal_reached"] is True
    assert decision["next_action"] == ""  # no further step when reached
    assert decision["evidence"] == ["all 12 tests pass", "smoke ok"]
    assert decision["model_recommendation"] == "opus"
    assert decision["estimated_next_cost"] == estimate_usd(50_000)


def test_build_decision_fail_partial_completion() -> None:
    meta = {
        "completion_state": "partial",
        "validation_status": "validated",
        "next_action": "fix the failing import",
        "summary": "3 of 5 tasks done",
    }
    decision = build_decision(meta, spent_delta=10_000)
    assert decision["goal_reached"] is False
    assert decision["next_action"] == "fix the failing import"
    assert decision["evidence"] == ["3 of 5 tasks done"]


def test_build_decision_fail_unvalidated() -> None:
    meta = {
        "completion_state": "complete",
        "validation_status": "failed",
        "next_action": "verifier reported 2 failures",
        "summary_lines": ["FAIL: test_auth"],
    }
    decision = build_decision(meta, spent_delta=0)
    assert decision["goal_reached"] is False
    assert decision["next_action"] == "verifier reported 2 failures"
    assert decision["evidence"] == ["FAIL: test_auth"]
    # Non-positive delta yields the $0.00 estimate.
    assert decision["estimated_next_cost"] == "$0.00"


def test_build_decision_reads_only_passed_dict() -> None:
    """No filesystem access: a bare dict in, a decision out. Defaults applied."""
    decision = build_decision({}, spent_delta=0)
    assert decision["goal_reached"] is False
    assert decision["evidence"] == []
    assert decision["model_recommendation"] == "sonnet"  # documented default


def test_build_decision_non_dict_meta_degrades() -> None:
    decision = build_decision("not a dict", spent_delta=0)  # type: ignore[arg-type]
    assert decision["goal_reached"] is False
    assert decision["evidence"] == []


# ── stop_reason ─────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "status",
    ["done", "budget-hit", "max-iter", "awaiting-approval", "stalled"],
)
def test_stop_reason_each_terminal_status_is_terminal(status: str) -> None:
    """Every terminal status (including SKILL-set 'stalled') stops the loop."""
    state = LoopState(status=status)
    assert stop_reason(state) == status


def test_stop_reason_running_with_room_continues() -> None:
    state = LoopState(
        status="running",
        spent_tokens=10,
        budget_tokens=DEFAULT_BUDGET_TOKENS,
        iteration=1,
        max_iterations=DEFAULT_MAX_ITERATIONS,
        pending_step="",
    )
    assert stop_reason(state) is None


def test_stop_reason_budget_hit_when_spent_reaches_budget() -> None:
    state = LoopState(
        status="running",
        spent_tokens=DEFAULT_BUDGET_TOKENS,
        budget_tokens=DEFAULT_BUDGET_TOKENS,
        iteration=0,
        max_iterations=DEFAULT_MAX_ITERATIONS,
    )
    assert stop_reason(state) == "budget-hit"


def test_stop_reason_max_iter_when_iteration_reaches_ceiling() -> None:
    state = LoopState(
        status="running",
        spent_tokens=0,
        budget_tokens=DEFAULT_BUDGET_TOKENS,
        iteration=DEFAULT_MAX_ITERATIONS,
        max_iterations=DEFAULT_MAX_ITERATIONS,
    )
    assert stop_reason(state) == "max-iter"


def test_stop_reason_budget_checked_before_max_iter() -> None:
    """Budget ceiling wins when both conditions trip — never exceed spend."""
    state = LoopState(
        status="running",
        spent_tokens=DEFAULT_BUDGET_TOKENS,
        budget_tokens=DEFAULT_BUDGET_TOKENS,
        iteration=DEFAULT_MAX_ITERATIONS,
        max_iterations=DEFAULT_MAX_ITERATIONS,
    )
    assert stop_reason(state) == "budget-hit"


def test_stop_reason_pending_step_awaits_approval() -> None:
    state = LoopState(
        status="running",
        spent_tokens=0,
        budget_tokens=DEFAULT_BUDGET_TOKENS,
        iteration=0,
        max_iterations=DEFAULT_MAX_ITERATIONS,
        pending_step="destructive migration",
    )
    assert stop_reason(state) == "awaiting-approval"


def test_stop_reason_does_not_derive_stalled_from_blank_next_action() -> None:
    """A running state with room is NOT stalled — stop_reason never inspects
    next_action; 'stalled' is set onto state.status by the driver, not derived
    here. This is the stalled-handling split."""
    state = LoopState(status="running", spent_tokens=0, budget_tokens=DEFAULT_BUDGET_TOKENS)
    assert stop_reason(state) is None


# ── refresh_spent / budget_remaining ────────────────────────────────────────


def _seed_usage(repo: Path, run_id: str, pairs: list[tuple[int, int]], *, task_id: int = 1) -> None:
    """Append usage records for ``run_id`` via the real ledger API (hermetic)."""
    for i, (pin, pout) in enumerate(pairs):
        append_usage(
            repo,
            UsageRecord(
                ts="2026-06-09T00:00:0%d+00:00" % (i % 10),
                run_id=run_id,
                task_id=task_id,
                model="codex",
                prompt_tokens=pin,
                completion_tokens=pout,
            ),
        )


def test_refresh_spent_aggregates_run_id(tmp_path: Path) -> None:
    state = LoopState(run_id="run-xyz", budget_tokens=DEFAULT_BUDGET_TOKENS, spent_tokens=0)
    _seed_usage(tmp_path, "run-xyz", [(1000, 500), (2000, 1500)])
    # A record under a DIFFERENT run_id must not be counted.
    _seed_usage(tmp_path, "run-other", [(9999, 9999)])

    refreshed = refresh_spent(tmp_path, state)
    assert refreshed is state  # mutates + returns the same object
    assert refreshed.spent_tokens == 1000 + 500 + 2000 + 1500
    assert budget_remaining(refreshed) == DEFAULT_BUDGET_TOKENS - 5000


def test_refresh_spent_blank_run_id_untouched(tmp_path: Path) -> None:
    state = LoopState(run_id="", spent_tokens=777)
    refreshed = refresh_spent(tmp_path, state)
    assert refreshed.spent_tokens == 777  # nothing to attribute yet


def test_refresh_spent_missing_ledger_no_raise(tmp_path: Path) -> None:
    """No usage.jsonl on disk → spend degrades to 0, never raises."""
    state = LoopState(run_id="run-none", spent_tokens=123)
    refreshed = refresh_spent(tmp_path, state)
    assert refreshed.spent_tokens == 0


def test_budget_remaining_never_negative() -> None:
    state = LoopState(budget_tokens=100, spent_tokens=250)
    assert budget_remaining(state) == 0


def test_budget_remaining_normal() -> None:
    state = LoopState(budget_tokens=DEFAULT_BUDGET_TOKENS, spent_tokens=100_000)
    assert budget_remaining(state) == DEFAULT_BUDGET_TOKENS - 100_000


# ── constant sanity (no hardcoded magic numbers leaked) ─────────────────────


def test_module_constants_have_expected_defaults() -> None:
    assert DEFAULT_MAX_ITERATIONS == 5
    assert DEFAULT_BUDGET_TOKENS == 300_000
    assert COST_PER_KTOKEN_USD == pytest.approx(0.01)

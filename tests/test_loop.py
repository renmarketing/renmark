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
    BUDGET_FLOOR_TOKENS,
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
    should_continue_budget,
    stop_reason,
    write_loop,
)
from renmark.state import UsageRecord, append_usage, usage_by_run_id

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
    assert pytest.approx(0.01) == COST_PER_KTOKEN_USD
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
                ts=f"2026-06-09T00:00:0{i % 10}+00:00",
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
    assert pytest.approx(0.01) == COST_PER_KTOKEN_USD


# ── Major #1: failed verify must DERIVE next_action and CONTINUE ─────────────


def test_build_decision_failed_verify_derives_next_action_from_symptom() -> None:
    """A FAILED verify with no explicit next_action but a debug-symptom line in
    summary_lines → build_decision derives an actionable next_action (loop
    CONTINUES instead of stalling on the first failure)."""
    meta = {
        "completion_state": "partial",
        "validation_status": "validated",
        # verify records the failure in summary_lines, NOT in next_action.
        "summary_lines": [
            "1/2 behaviors verified",
            "failed: search entries",
            'run /renmark:debug with symptom: "search exits 1: no such table: entries"',
        ],
    }
    decision = build_decision(meta, spent_delta=10_000)
    assert decision["goal_reached"] is False
    next_action = decision["next_action"]
    assert isinstance(next_action, str)
    assert next_action.strip() != ""  # derived → loop has an actionable step
    assert "search exits 1" in next_action  # carries the symptom

    # And the loop would CONTINUE: a running state with budget + iterations left
    # and a non-blank next_action is NOT terminal.
    state = LoopState(
        status="running",
        spent_tokens=10_000,
        budget_tokens=DEFAULT_BUDGET_TOKENS,
        iteration=1,
        max_iterations=DEFAULT_MAX_ITERATIONS,
        pending_step="",
    )
    assert stop_reason(state) is None


def test_build_decision_failed_verify_derives_from_failed_names_line() -> None:
    """No symptom line, but a 'failed: <names>' line → still derives an action."""
    meta = {
        "completion_state": "partial",
        "validation_status": "validated",
        "summary_lines": ["failed: search entries, list entries"],
    }
    decision = build_decision(meta, spent_delta=0)
    assert decision["goal_reached"] is False
    assert "search entries" in str(decision["next_action"])


def test_build_decision_failed_verify_no_actionable_step_stalls() -> None:
    """A failed verify reporting NO failed behaviors (failed: none) → blank
    next_action → the driver maps that to 'stalled' (a genuine no-op)."""
    meta = {
        "completion_state": "partial",
        "validation_status": "failed",
        "summary_lines": ["0/0 behaviors verified", "failed: none"],
    }
    decision = build_decision(meta, spent_delta=0)
    assert decision["goal_reached"] is False
    assert decision["next_action"] == ""  # nothing actionable → stalled signal


def test_build_decision_explicit_next_action_wins_over_derivation() -> None:
    """An explicit next_action in metadata is used verbatim (derivation is only
    the fallback for the failed-smoke case that records no next_action)."""
    meta = {
        "completion_state": "partial",
        "validation_status": "validated",
        "next_action": "fix the failing import",
        "summary_lines": ['run /renmark:debug with symptom: "other thing"'],
    }
    decision = build_decision(meta, spent_delta=0)
    assert decision["next_action"] == "fix the failing import"


# ── Major #2: budget PREFLIGHT stops BEFORE another dispatch ─────────────────


def test_should_continue_budget_true_with_room() -> None:
    state = LoopState(budget_tokens=DEFAULT_BUDGET_TOKENS, spent_tokens=100_000)
    assert should_continue_budget(state) is True


def test_should_continue_budget_false_at_budget() -> None:
    """At/over budget → preflight returns False BEFORE another dispatch."""
    state = LoopState(budget_tokens=DEFAULT_BUDGET_TOKENS, spent_tokens=DEFAULT_BUDGET_TOKENS)
    assert should_continue_budget(state) is False
    assert budget_remaining(state) < BUDGET_FLOOR_TOKENS


def test_should_continue_budget_false_over_budget() -> None:
    state = LoopState(budget_tokens=100, spent_tokens=500)
    assert should_continue_budget(state) is False


def test_budget_preflight_then_stop_reason_budget_hit() -> None:
    """Preflight scenario: a state at budget → should_continue_budget False AND
    stop_reason reports 'budget-hit' (the driver stops before spending more)."""
    state = LoopState(
        status="running",
        budget_tokens=DEFAULT_BUDGET_TOKENS,
        spent_tokens=DEFAULT_BUDGET_TOKENS,
        iteration=1,
        max_iterations=DEFAULT_MAX_ITERATIONS,
    )
    assert should_continue_budget(state) is False
    assert stop_reason(state) == "budget-hit"


def test_should_continue_budget_malformed_state_stops() -> None:
    """A malformed state degrades to False (stop), never raises / runs unbounded."""
    state = LoopState()
    state.budget_tokens = "garbage"  # type: ignore[assignment]
    assert should_continue_budget(state) is False


# ── Major #3: parse_budget never raises on nan/inf/overflow ──────────────────


@pytest.mark.parametrize(
    "bad",
    ["nan", "$nan", "inf", "$inf", "-inf", "1e309", "$1e309", "1e400", "NaN", "Infinity"],
)
def test_parse_budget_non_finite_degrades_to_default(bad: str) -> None:
    """nan / inf / 1e309 (→ inf) must NOT raise — degrade to the bounded default."""
    tokens, usd = parse_budget(bad)
    assert tokens == DEFAULT_BUDGET_TOKENS
    assert usd == estimate_usd(DEFAULT_BUDGET_TOKENS)


@pytest.mark.parametrize("bad", ["-5", "$-3", "0", "$0", "not-a-number", "", "   "])
def test_parse_budget_negative_zero_garbage_default(bad: str) -> None:
    tokens, _ = parse_budget(bad)
    assert tokens == DEFAULT_BUDGET_TOKENS


def test_parse_budget_never_raises_on_extreme_float() -> None:
    """A direct float overflow path stays bounded (no OverflowError escapes)."""
    tokens, _ = parse_budget("9" * 400)  # parses to inf as a float
    assert tokens == DEFAULT_BUDGET_TOKENS


# ── Major #4: read_loop degrades on malformed loop.json, never raises ────────


def test_read_loop_wrong_field_types_coerced(tmp_path: Path) -> None:
    """Wrong JSON types for fields are coerced, not crashed: int fields from
    strings, str fields from numbers — no raise."""
    lid = "loop-2026-06-09-types"
    path = loop.loop_dir(tmp_path, lid) / loop.LOOP_JSON
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        '{"goal": 123, "budget_tokens": "250000", "spent_tokens": "bad", '
        '"iteration": 2.0, "run_id": 456, "pending_step": 789, "status": "running"}',
        encoding="utf-8",
    )
    loaded = read_loop(tmp_path, lid)
    assert loaded is not None
    assert loaded.goal == "123"  # number coerced to str
    assert loaded.budget_tokens == 250_000  # numeric string coerced to int
    assert loaded.spent_tokens == 0  # garbage int → default 0
    assert loaded.iteration == 2  # float coerced to int
    assert loaded.run_id == "456"
    assert loaded.pending_step == "789"
    assert loaded.status == "running"


def test_read_loop_unknown_status_treated_as_terminal(tmp_path: Path) -> None:
    """An unknown status must NOT keep the loop running — it degrades to a
    terminal status so a malformed state stops rather than loops unbounded."""
    lid = "loop-2026-06-09-badstatus"
    path = loop.loop_dir(tmp_path, lid) / loop.LOOP_JSON
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('{"goal": "g", "status": "totally-bogus"}', encoding="utf-8")
    loaded = read_loop(tmp_path, lid)
    assert loaded is not None
    assert loaded.status in loop.TERMINAL_STATUSES  # terminal → stops
    assert stop_reason(loaded) is not None


def test_read_loop_non_str_pending_step_does_not_crash_stop_reason(tmp_path: Path) -> None:
    """The original bug: a non-str pending_step would raise on .strip() in
    stop_reason. After coercion (and the broadened guard) it must not raise."""
    lid = "loop-2026-06-09-pending"
    path = loop.loop_dir(tmp_path, lid) / loop.LOOP_JSON
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('{"goal": "g", "pending_step": 5, "status": "running"}', encoding="utf-8")
    loaded = read_loop(tmp_path, lid)
    assert loaded is not None
    # pending_step coerced to "5" (truthy) → awaiting-approval, but crucially no raise.
    assert stop_reason(loaded) is not None


def test_stop_reason_never_raises_on_raw_bad_state() -> None:
    """Even a directly-constructed bad state (bypassing read coercion) must
    degrade to a terminal stop, never raise."""
    state = LoopState()
    state.pending_step = 42  # type: ignore[assignment]
    state.spent_tokens = "x"  # type: ignore[assignment]
    assert stop_reason(state) is not None  # degrades to 'stalled', no raise


# ── Major #5: usage_by_run_id skips corrupt lines + clamps negatives ─────────


def test_usage_by_run_id_clamps_negative_tokens(tmp_path: Path) -> None:
    """Negative token fields are clamped to 0 — never under-count real spend
    (which would let the loop overshoot its budget)."""
    _seed_usage(tmp_path, "run-neg", [(-200, -200), (1000, 500)])
    total = usage_by_run_id(tmp_path, "run-neg")
    # The negative record contributes 0; only the valid 1500 counts.
    assert total == 1500
    assert total >= 0


def test_usage_by_run_id_skips_corrupt_line_no_raise(tmp_path: Path) -> None:
    """A corrupt / non-JSON line in usage.jsonl is skipped; valid lines still
    sum; the call never raises."""
    from renmark.state._core import USAGE_LEDGER, state_dir

    _seed_usage(tmp_path, "run-mix", [(1000, 500)])
    ledger = state_dir(tmp_path) / USAGE_LEDGER
    # Append a corrupt-byte line + a non-JSON line.
    with ledger.open("ab") as fh:
        fh.write(b"\xff\xfe not valid json bytes\n")
    with ledger.open("a", encoding="utf-8") as fh:
        fh.write("{ broken json\n")
    total = usage_by_run_id(tmp_path, "run-mix")
    assert total == 1500  # only the valid record counted, no crash


def test_usage_by_run_id_garbage_token_field_counts_zero(tmp_path: Path) -> None:
    from renmark.state._core import USAGE_LEDGER, state_dir

    ledger = state_dir(tmp_path) / USAGE_LEDGER
    ledger.parent.mkdir(parents=True, exist_ok=True)
    ledger.write_text(
        '{"run_id": "run-g", "prompt_tokens": "abc", "completion_tokens": null}\n',
        encoding="utf-8",
    )
    assert usage_by_run_id(tmp_path, "run-g") == 0


# ── M4: milestone execution loop state ─────────────────────────────────────


def test_loop_state_persists_stable_milestone_and_work_package_identity(tmp_path: Path) -> None:
    """A resumable loop keeps canonical package identity, not display labels."""
    lid = "loop-m4-identity"
    write_loop(
        tmp_path,
        lid,
        LoopState(
            goal="complete package",
            milestone_id="M4 Execution Review",
            work_package_id="Repair Loop State",
        ),
    )

    resumed = read_loop(tmp_path, lid)
    assert resumed is not None
    assert resumed.milestone_id == "m4-execution-review"
    assert resumed.work_package_id == "m4-execution-review--repair-loop-state"


def test_loop_state_resume_preserves_terminal_package_handoff(tmp_path: Path) -> None:
    """Only a verified completed loop permits scope advancement on resume."""
    lid = "loop-m4-done"
    write_loop(
        tmp_path,
        lid,
        LoopState(
            milestone_id="m4",
            work_package_id="m4--package-a",
            status="done",
            verified_success=True,
        ),
    )

    resumed = read_loop(tmp_path, lid)
    assert resumed is not None
    assert resumed.stop_reason == "done"
    assert resumed.scope_advance_allowed is True


def test_loop_state_done_without_verified_success_denies_scope_advancement() -> None:
    """A done status alone is insufficient to advance the work-package scope."""
    state = LoopState(
        milestone_id="m4",
        work_package_id="m4--package-a",
        status="done",
    )

    assert state.scope_advance_allowed is False


def test_build_decision_requires_fresh_verifier_evidence_before_repair() -> None:
    """No actionable verifier evidence is a no-progress signal, never a retry."""
    decision = build_decision(
        {"completion_state": "partial", "validation_status": "failed"},
        spent_delta=0,
    )

    assert decision["goal_reached"] is False
    assert decision["evidence"] == []
    assert decision["next_action"] == ""
    state = LoopState(status="stalled")
    assert stop_reason(state) == "stalled"
    assert state.stop_reason == "stalled"
    assert state.scope_advance_allowed is False


def test_loop_stops_after_at_most_two_repair_iterations() -> None:
    """A work package cannot enter a third repair dispatch."""
    state = LoopState(iteration=2, max_iterations=2)

    assert stop_reason(state) == "max-iter"
    assert state.stop_reason == "max-iter"
    assert state.scope_advance_allowed is False


def test_loop_approval_boundary_stops_without_scope_advancement() -> None:
    """REQ-12 approval work remains a terminal boundary for the package."""
    state = LoopState(
        milestone_id="m4",
        work_package_id="m4--release",
        pending_step="release package",
    )

    assert stop_reason(state) == "awaiting-approval"
    assert state.stop_reason == "awaiting-approval"
    assert state.scope_advance_allowed is False

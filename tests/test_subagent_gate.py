"""Tests for the enforced subagent-justification gate (renmark.subagent_gate).

Proves the deterministic-first gate CHALLENGES a spawn before dispatch:
- common checks resolve to no-subagent (deterministic path),
- a simple/tiny task is flagged as inline-able,
- a genuinely hard scoped task passes clean,
- general-purpose without a reason is challenged (and a reason clears it),
- a subagent-heavy / deterministic-eligible plan gets challenged,
- everything degrades safe and never raises.
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from renmark import recurrence
from renmark import subagent_gate as g

# ── per-task justification ────────────────────────────────────────────────────


def test_deterministic_task_needs_no_subagent() -> None:
    v = g.justify_task({"mode": "deterministic"})
    assert v.needs_subagent is False
    assert v.deterministic_eligible is True
    assert v.challenge is not None  # "resolve via a check, not a subagent"


def test_deterministic_executor_needs_no_subagent() -> None:
    # A deterministic executor (script/check/tool/code/none) is caught by
    # cost.is_deterministic_item.
    v = g.justify_task({"executor": "script"})
    assert v.deterministic_eligible is True
    assert v.needs_subagent is False


def test_simple_tiny_task_is_inline_flagged() -> None:
    v = g.justify_task(
        {"executor": "haiku", "complexity": "simple", "est_tokens": 200, "target": "a.md"}
    )
    assert v.needs_subagent is False
    assert v.challenge is not None
    assert "inline" in v.challenge or "haiku" in v.challenge


def test_hard_scoped_task_passes_clean() -> None:
    v = g.justify_task(
        {"executor": "opus", "complexity": "hard", "est_tokens": 2000,
         "target": "renmark/foo.py"}
    )
    assert v.needs_subagent is True
    assert v.role != "general-purpose"      # a scoped role was resolved
    assert v.challenge is None


def test_general_purpose_without_reason_is_challenged() -> None:
    v = g.justify_task(
        {"executor": "sonnet", "complexity": "medium", "est_tokens": 1000,
         "target": "notes.txt"}
    )
    assert v.role == "general-purpose"
    assert v.challenge is not None
    assert "general-purpose" in v.challenge


def test_general_purpose_with_reason_clears_challenge() -> None:
    v = g.justify_task(
        {"executor": "sonnet", "complexity": "medium", "est_tokens": 1000,
         "target": "notes.txt", "role_reason": "cross-cutting spike, no single role fits"}
    )
    assert v.role == "general-purpose"
    assert v.challenge is None
    assert v.needs_subagent is True


def test_deterministic_package_is_not_dispatched() -> None:
    v = g.justify_task({"cost_lane": "deterministic", "goal": "run checks"})
    assert v.deterministic_eligible is True
    assert v.needs_subagent is False
    assert v.challenge_code == "deterministic"


def test_general_purpose_package_without_reason_is_challenged() -> None:
    v = g.justify_task(
        {"cost_lane": "standard", "complexity": "medium", "target": "notes.txt"}
    )
    assert v.role == "general-purpose"
    assert v.challenge_code == "missing_role_reason"


# ── plan-level challenge ──────────────────────────────────────────────────────


def test_plan_with_deterministic_and_gp_is_challenged() -> None:
    plan = [
        {"mode": "deterministic"},
        {"executor": "haiku", "complexity": "simple", "est_tokens": 200, "target": "a.md"},
        {"executor": "opus", "complexity": "hard", "est_tokens": 2000, "target": "b.py"},
    ]
    pc = g.challenge_plan(plan)
    assert pc.challenged is True
    assert pc.deterministic_eligible == 1
    assert pc.unjustified <= pc.subagent_tasks      # invariant: never over-count
    assert pc.total == 3
    assert g.preview_line(pc).startswith("⚠")


def test_clean_scoped_plan_is_not_challenged() -> None:
    plan = [
        {"executor": "opus", "complexity": "hard", "est_tokens": 2000, "target": "renmark/x.py"},
        {"executor": "codex", "complexity": "medium", "est_tokens": 900, "target": "tests/test_x.py"},
    ]
    pc = g.challenge_plan(plan)
    assert pc.challenged is False
    assert pc.unjustified == 0
    assert g.preview_line(pc).startswith("✓")


def test_all_deterministic_plan_flags_every_task() -> None:
    plan = [{"mode": "deterministic"}, {"executor": "script"}]
    pc = g.challenge_plan(plan)
    assert pc.deterministic_eligible == 2
    assert pc.subagent_tasks == 0
    assert pc.challenged is True   # a cheaper (all-deterministic) path exists


# ── safety: never raises ──────────────────────────────────────────────────────


def test_gate_never_raises_on_garbage() -> None:
    for bad in (None, 123, "x", object()):
        v = g.justify_task(bad)
        assert isinstance(v, g.SubagentVerdict)
    for bad_plan in (None, 123, object()):
        pc = g.challenge_plan(bad_plan)
        assert isinstance(pc, g.PlanChallenge)
        assert pc.total == 0


def test_empty_plan_is_not_challenged() -> None:
    pc = g.challenge_plan([])
    assert pc.total == 0
    assert pc.challenged is False


# ── regression: codereview findings #3 + #4 ───────────────────────────────────


def test_simple_task_with_no_estimate_is_inline_not_false_spawn() -> None:
    """#4: a simple task with a MISSING est_tokens must be inline-able, not a
    mis-flagged unjustified subagent spawn."""
    v = g.justify_task(
        {"executor": "haiku", "complexity": "simple", "est_tokens": None, "target": "a.md"}
    )
    assert v.needs_subagent is False
    assert v.challenge_code == "inlineable"


def test_bool_est_tokens_not_treated_as_estimate() -> None:
    """#4: bool is not an int estimate (True==1 must not count)."""
    v = g.justify_task(
        {"executor": "haiku", "complexity": "simple", "est_tokens": True, "target": "a.md"}
    )
    assert v.needs_subagent is False  # simple + no real estimate → inline


def test_inlineable_gp_task_uses_inlineable_code_not_missing_reason() -> None:
    """#3: a general-purpose task challenged for being inline-able must carry
    challenge_code 'inlineable', NOT 'missing_role_reason'."""
    v = g.justify_task(
        {"executor": "sonnet", "complexity": "simple", "est_tokens": 100, "target": "notes.txt"}
    )
    assert v.role == "general-purpose"
    assert v.challenge_code == "inlineable"


# ── regression: codereview finding #2 (role_reason reachable from a real plan) ─


_PLAN_WITH_ROLE_REASON = """### Task 1: cross-cutting spike
- **mode:** B
- **target:** notes.txt
- **executor:** sonnet
- **complexity:** medium
- **est_tokens:** 1000
- **role_reason:** cross-cutting spike, no single role fits
- **verifier:** test -f notes.txt
- **spec:**
  Investigate the thing.
"""


def test_role_reason_parses_and_clears_gp_challenge(tmp_path) -> None:
    """#2: role_reason must be expressible in a real plan file (parser accepts it)
    and must clear the general-purpose challenge on the parsed Task."""
    from renmark import parser

    plan = tmp_path / "p.plan.md"
    plan.write_text(_PLAN_WITH_ROLE_REASON, encoding="utf-8")
    tasks = parser.parse_plan(plan)
    assert tasks[0].role_reason == "cross-cutting spike, no single role fits"
    v = g.justify_task(tasks[0])
    assert v.role == "general-purpose"
    assert v.challenge is None            # reason cleared the challenge
    assert v.needs_subagent is True


def test_active_failure_rule_blocks_matching_applicability(tmp_path: Path) -> None:
    rule = recurrence.propose_failure_rule(
        tmp_path,
        rule_id="R-ACTIVE-001",
        trigger="dispatch",
        applicability="aardvark token overlap",
        required_behavior="tighten the request",
        prohibited_failure="overbroad dispatch",
        source_evidence=["spec.md"],
    )
    recurrence.activate_failure_rule(tmp_path, rule.rule_id)

    verdict = g.check_failure_rule_constraints(tmp_path, "dispatch with aardvark token")

    assert verdict.passed is False
    assert verdict.matched_rule_ids == (rule.rule_id,)
    assert rule.rule_id in verdict.reason
    assert rule.rule_id in verdict.challenge


def test_proposed_failure_rule_is_never_matched(tmp_path: Path) -> None:
    rule = recurrence.propose_failure_rule(
        tmp_path,
        rule_id="R-PROPOSED-001",
        trigger="dispatch",
        applicability="aardvark token overlap",
        required_behavior="tighten the request",
        prohibited_failure="overbroad dispatch",
        source_evidence=["spec.md"],
    )

    verdict = g.check_failure_rule_constraints(tmp_path, "dispatch with aardvark token")

    assert verdict.passed is True
    assert verdict.matched_rule_ids == ()
    assert rule.rule_id not in verdict.reason


def test_deprecated_failure_rule_is_never_matched(tmp_path: Path) -> None:
    rule = recurrence.propose_failure_rule(
        tmp_path,
        rule_id="R-DEPRECATED-001",
        trigger="dispatch",
        applicability="aardvark token overlap",
        required_behavior="tighten the request",
        prohibited_failure="overbroad dispatch",
        source_evidence=["spec.md"],
    )
    recurrence.deprecate_failure_rule(tmp_path, rule.rule_id, reason="superseded")

    verdict = g.check_failure_rule_constraints(tmp_path, "dispatch with aardvark token")

    assert verdict.passed is True
    assert verdict.matched_rule_ids == ()
    assert rule.rule_id not in verdict.reason


def test_check_failure_rule_constraints_without_registry_is_safe(tmp_path: Path) -> None:
    verdict = g.check_failure_rule_constraints(tmp_path, "dispatch with aardvark token")
    assert verdict.passed is True
    assert verdict.matched_rule_ids == ()


def test_apply_failure_rule_constraints_merges_matched_rule_details(tmp_path: Path) -> None:
    rule = recurrence.propose_failure_rule(
        tmp_path,
        rule_id="R-MERGE-001",
        trigger="dispatch",
        applicability="aardvark token overlap",
        required_behavior="tighten the request",
        prohibited_failure="overbroad dispatch",
        source_evidence=["spec.md"],
    )
    recurrence.activate_failure_rule(tmp_path, rule.rule_id)
    verdict = g.check_failure_rule_constraints(tmp_path, "dispatch with aardvark token")

    existing_constraints = {"alpha": "keep", "nested": {"preserve": True}}
    original_constraints = deepcopy(existing_constraints)
    merged = g.apply_failure_rule_constraints(existing_constraints, verdict, [rule])

    assert existing_constraints == original_constraints
    assert merged is not existing_constraints
    assert merged["alpha"] == "keep"
    assert merged["nested"] == {"preserve": True}
    assert merged["failure_rules"] == [
        {
            "rule_id": rule.rule_id,
            "required_behavior": rule.required_behavior,
            "prohibited_failure": rule.prohibited_failure,
        }
    ]


def test_subagent_gate_source_does_not_reference_build_subagent_input() -> None:
    source = Path(g.__file__).read_text(encoding="utf-8")
    assert "build_subagent_input(" not in source


def test_validate_r008_dispatch_accepts_minimal_valid_spec() -> None:
    ok, missing = g.validate_r008_dispatch(
        {
            "work_order_id": "W-1",
            "contract": "C-1",
            "reason": "r",
            "scope": {"target": "notes.txt"},
            "expected_artifact": "out.txt",
            "budget_reservation": "B-1",
        }
    )
    assert ok is True
    assert missing == []


def test_check_capability_envelope_accepts_minimal_scope() -> None:
    verdicts = g.check_capability_envelope("sonnet", {"target": "notes.txt"})
    assert isinstance(verdicts, tuple)
    assert verdicts
    assert verdicts[0].passed is True

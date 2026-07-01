from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from renmark import behavior
from renmark.judge import Verdict


def _case(
    *,
    skill: str = "roadmap",
    prompt: str = "Summarize the next steps.",
    call: str = "lifecycle.next_steps",
    assertions: list[str] | None = None,
    contract: str = "Show the recommended next step and a finish fallback.",
    golden_ref: str = "roadmap-golden",
    source: Path | None = None,
) -> behavior.Case:
    return behavior.Case(
        skill=skill,
        prompt=prompt,
        deterministic=behavior.DeterministicSpec(
            call=call,
            assertions=tuple(assertions or []),
        ),
        eval=behavior.EvalSpec(
            contract=contract,
            golden_ref=golden_ref,
        ),
        source=source,
    )


def _write_case_file(
    tmp_path: Path,
    *,
    skill: str = "roadmap",
    prompt: str = "Summarize the next steps.",
    call: str = "lifecycle.next_steps",
    assertions: list[str] | None = None,
    contract: str = "Show the recommended next step and a finish fallback.",
    golden_ref: str = "roadmap-golden",
    filename: str = "roadmap.behavior.json",
) -> Path:
    payload = {
        "skill": skill,
        "prompt": prompt,
        "deterministic": {
            "call": call,
            "assertions": assertions or [],
        },
        "eval": {
            "contract": contract,
            "golden_ref": golden_ref,
        },
    }
    path = tmp_path / filename
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def _write_golden(case: behavior.Case, transcript: str) -> None:
    assert case.source is not None
    snapshots = case.source.parent / "snapshots"
    snapshots.mkdir(parents=True, exist_ok=True)
    snapshot = snapshots / f"{case.eval.golden_ref}.json"
    snapshot.write_text(
        json.dumps({"transcript": transcript}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def test_load_cases_parses_v2_case_schema(tmp_path: Path) -> None:
    case_path = _write_case_file(
        tmp_path,
        skill="roadmap",
        prompt="What should happen next?",
        call="plan_lint",
        assertions=["contains:dispatch policy", "not_contains:Agent("],
        contract="Keep dispatch policy output leak-free.",
        golden_ref="plan-lint-golden",
        filename="plan-lint.behavior.json",
    )

    loaded = behavior.load_cases(tmp_path)

    assert loaded == [
        behavior.Case(
            skill="roadmap",
            prompt="What should happen next?",
            deterministic=behavior.DeterministicSpec(
                call="plan_lint",
                assertions=("contains:dispatch policy", "not_contains:Agent("),
            ),
            eval=behavior.EvalSpec(
                contract="Keep dispatch policy output leak-free.",
                golden_ref="plan-lint-golden",
            ),
            source=case_path,
        )
    ]


def test_load_cases_rejects_unsafe_eval_golden_ref(tmp_path: Path) -> None:
    _write_case_file(tmp_path, golden_ref="../escape")

    with pytest.raises(behavior.BehaviorConfigError) as excinfo:
        behavior.load_cases(tmp_path)

    assert "snapshot ref '../escape'" in str(excinfo.value)


def test_run_passes_real_next_steps_output_without_invoking_runner() -> None:
    case = _case(
        assertions=[
            "contains:What's next:",
            "contains:(Recommended)",
            "line_ends:do nothing",
            "min_lines:4",
        ],
    )

    def would_raise_runner(_: str) -> str:
        raise AssertionError("default deterministic run must not invoke a live runner")

    results = behavior.run(cases=[case], judge=False, subagent_runner=would_raise_runner)

    assert len(results) == 1
    assert results[0].status == "PASS"
    assert results[0].message == "all deterministic assertions hold on the current output"
    assert results[0].judge_offered is False
    assert results[0].judge_verdict is None


def test_negative_deterministic_case_fails_on_real_output() -> None:
    case = _case(
        assertions=["contains:this token is not in the live next-steps output"],
    )

    results = behavior.run(cases=[case], judge=False, on_fail_offer=False)

    assert len(results) == 1
    assert results[0].status == "FAIL"
    assert results[0].message == "1 assertion(s) failed on the current output"
    assert results[0].failed_assertions == (
        "contains:this token is not in the live next-steps output",
    )


def test_unknown_deterministic_call_fails_clearly() -> None:
    case = _case(call="deterministic.call.that.does.not.exist")

    results = behavior.run(cases=[case], judge=False, on_fail_offer=False)

    assert len(results) == 1
    assert results[0].status == "FAIL"
    assert "unknown deterministic call" in results[0].message
    assert "deterministic.call.that.does.not.exist" in results[0].message
    assert "lifecycle.next_steps" in results[0].message


def test_judge_is_not_called_when_disabled_and_not_called_for_passes(tmp_path: Path) -> None:
    passing = _case(
        assertions=["contains:(Recommended)"],
        golden_ref="pass-golden",
        source=tmp_path / "pass.behavior.json",
    )
    failing = _case(
        assertions=["contains:missing from current output"],
        golden_ref="fail-golden",
        source=tmp_path / "fail.behavior.json",
    )

    with patch("renmark.judge.judge_behavior", autospec=True) as judge_behavior:
        results = behavior.run(cases=[passing, failing], judge=False, on_fail_offer=True)

    assert [result.status for result in results] == ["PASS", "FAIL"]
    assert results[0].judge_offered is False
    assert results[1].judge_offered is True
    assert results[0].judge_verdict is None
    assert results[1].judge_verdict is None
    judge_behavior.assert_not_called()


def test_judge_escalation_runs_only_for_deterministic_fail_when_enabled(tmp_path: Path) -> None:
    passing = _case(
        assertions=["contains:(Recommended)"],
        golden_ref="pass-golden",
        source=tmp_path / "pass.behavior.json",
    )
    failing = _case(
        assertions=["contains:missing from current output"],
        golden_ref="fail-golden",
        source=tmp_path / "fail.behavior.json",
    )
    _write_golden(failing, "Golden transcript with the required behavior.")

    verdict = Verdict(
        outcome="fail",
        confidence="medium",
        validation_status="validated",
        rationale="The current output still misses the required text.",
    )

    with patch("renmark.judge.judge_behavior", autospec=True, return_value=verdict) as judge_behavior:
        results = behavior.run(cases=[passing, failing], judge=True, repo=tmp_path)

    assert [result.status for result in results] == ["PASS", "FAIL"]
    assert results[0].judge_verdict is None
    assert results[1].judge_verdict == {
        "outcome": "fail",
        "confidence": "medium",
        "validation_status": "validated",
        "rationale": "The current output still misses the required text.",
    }
    judge_behavior.assert_called_once()


def test_judge_mode_errors_when_eval_golden_is_missing(tmp_path: Path) -> None:
    case = _case(
        assertions=["contains:missing from current output"],
        golden_ref="missing-golden",
        source=tmp_path / "missing.behavior.json",
    )

    with patch("renmark.judge.judge_behavior", autospec=True) as judge_behavior:
        results = behavior.run(cases=[case], judge=True, repo=tmp_path)

    assert len(results) == 1
    assert results[0].status == "ERROR"
    assert behavior.ACCEPT_FIRST_HINT in results[0].message
    judge_behavior.assert_not_called()


def test_assertion_miniformat_uses_real_plan_lint_output() -> None:
    case = _case(
        call="plan_lint",
        assertions=[
            "contains:dispatch policy for roadmap:",
            "not_contains:Agent(",
            r"matches:transcript-leak check: leak-free$",
            "min_lines:3",
        ],
    )

    results = behavior.run(cases=[case], judge=False, on_fail_offer=False)

    assert len(results) == 1
    assert results[0].status == "PASS"


def test_unknown_assertion_op_fails_deterministically() -> None:
    case = _case(
        call="plan_lint",
        assertions=["mystery:dispatch policy"],
    )

    results = behavior.run(cases=[case], judge=False, on_fail_offer=False)

    assert len(results) == 1
    assert results[0].status == "FAIL"
    assert results[0].failed_assertions == ("mystery:dispatch policy",)

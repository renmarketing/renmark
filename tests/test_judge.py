"""---
artifact_type: test_artifact
schema_version: 1
created_at: 2026-07-01T00:00:00Z
source_sha: null
related_plan: null
generator: codex
stale_after: null
dependency_refs:
  - /home/renmark/projects/ai-system/.claude/worktrees/p8-behavioral-brainstorm/renmark/judge.py
completion_state: complete
confidence: high
validation_status: validated
retry_count: 0
parser_success: true
schema_compliance: true
---

Unit tests for the behavioral judge's 3-state contract.

These tests cover validated pass/fail/uncertain verdicts, malformed and
exceptional responses becoming unvalidated uncertain results, prompt redaction
before composition, swap-order prompt generation, the evidence reference round
trip, the published cost constant, and a clean import path that does not
trigger any model call at import time.

## Summary

- Verifies valid mocked judge responses return validated pass, fail, and uncertain verdicts.
- Verifies malformed or unavailable judge paths become unvalidated uncertain results.
- Confirms prompt redaction strips Worker-authored values before string composition.
- Covers swap-order prompt generation and `JudgeEvidenceRef` round-tripping.
- Pins `JUDGE_EST_COST_USD` as a positive float and preserves the no-import-call guarantee.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from renmark import judge
from renmark.judge import JUDGE_EST_COST_USD, Verdict, judge_behavior


def _judge_kwargs() -> dict[str, object]:
    return {
        "repo": Path("."),
        "skill": "renmark:brainstorm",
        "prompt": "Design a release checklist.",
        "baseline": "Here is a generic answer.",
        "golden": "Here is a release checklist tailored to the contract.",
        "actual": "Here is a release checklist tailored to the contract.",
        "contract": "The skill should produce a concrete release checklist.",
    }


def test_judge_behavior_returns_validated_verdict_for_valid_mock_response() -> None:
    captured: list[str] = []

    def runner(prompt: str) -> str:
        captured.append(prompt)
        return """
Judge output:
```json
{"outcome": "pass", "confidence": "high", "rationale": "Actual behavior matches the contract."}
```
"""

    verdict = judge_behavior(subagent_runner=runner, **_judge_kwargs())

    assert verdict == Verdict(
        outcome="pass",
        confidence="high",
        validation_status="validated",
        rationale="Actual behavior matches the contract.",
    )
    assert len(captured) == 1
    assert "SKILL: renmark:brainstorm" in captured[0]
    assert "PROMPT (the shared input given to both):" in captured[0]
    assert "Respond with ONLY a JSON object" in captured[0]


def test_judge_behavior_marks_unparseable_response_unvalidated_and_uncertain() -> None:
    # 3-state Outcome: a response we could not read is "uncertain" (we don't
    # know), not "fail" (a decision the judge never rendered) — and never a pass.
    verdict = judge_behavior(
        subagent_runner=lambda prompt: "not json at all",
        **_judge_kwargs(),
    )

    assert verdict.validation_status == "unvalidated"
    assert verdict.outcome == "uncertain"
    assert verdict.confidence == "low"
    assert "could not parse a JSON object" in verdict.rationale


def test_judge_behavior_marks_malformed_payload_unvalidated_and_not_a_pass() -> None:
    verdict = judge_behavior(
        subagent_runner=lambda prompt: (
            '{"outcome": "maybe", "confidence": "high", "rationale": "unclear"}'
        ),
        **_judge_kwargs(),
    )

    assert verdict.validation_status == "unvalidated"
    assert verdict.outcome == "uncertain"
    assert verdict.confidence == "low"
    assert "unrecognized outcome" in verdict.rationale


def test_judge_behavior_rejects_pass_with_bogus_confidence() -> None:
    # Regression for codereview Major 3: a valid outcome with an unrecognized
    # confidence must NOT be a silent validated PASS (was coerced to "low").
    verdict = judge_behavior(
        subagent_runner=lambda prompt: (
            '{"outcome": "pass", "confidence": "bogus", "rationale": "looks ok"}'
        ),
        **_judge_kwargs(),
    )

    assert verdict.validation_status == "unvalidated"
    assert verdict.outcome == "uncertain"
    assert verdict.confidence == "low"
    assert "unrecognized confidence" in verdict.rationale


def test_judge_behavior_rejects_missing_rationale() -> None:
    # A present, recognized outcome/confidence but no rationale must not validate.
    verdict = judge_behavior(
        subagent_runner=lambda prompt: '{"outcome": "pass", "confidence": "high"}',
        **_judge_kwargs(),
    )

    assert verdict.validation_status == "unvalidated"
    assert verdict.outcome == "uncertain"
    assert verdict.confidence == "low"
    assert "missing or empty rationale" in verdict.rationale


def test_judge_behavior_returns_validated_fail_verdict_for_real_fail() -> None:
    verdict = judge_behavior(
        subagent_runner=lambda prompt: (
            '{"outcome": "fail", "confidence": "high", '
            '"rationale": "Actual behavior matches the contract."}'
        ),
        **_judge_kwargs(),
    )

    assert verdict == Verdict(
        outcome="fail",
        confidence="high",
        validation_status="validated",
        rationale="Actual behavior matches the contract.",
    )


def test_judge_behavior_returns_validated_uncertain_verdict_for_real_uncertain() -> None:
    verdict = judge_behavior(
        subagent_runner=lambda prompt: (
            '{"outcome": "uncertain", "confidence": "low", '
            '"rationale": "insufficient evidence"}'
        ),
        **_judge_kwargs(),
    )

    assert verdict == Verdict(
        outcome="uncertain",
        confidence="low",
        validation_status="validated",
        rationale="insufficient evidence",
    )


def test_judge_behavior_maps_unavailable_and_generic_exceptions_to_uncertain() -> None:
    cases = (
        (
            lambda prompt: (_ for _ in ()).throw(judge.JudgeUnavailable("runner down")),
            "judge runner unavailable",
        ),
        (
            lambda prompt: (_ for _ in ()).throw(RuntimeError("boom")),
            "judge runner error",
        ),
    )

    for runner, expected_rationale_prefix in cases:
        verdict = judge_behavior(subagent_runner=runner, **_judge_kwargs())

        assert verdict.outcome == "uncertain"
        assert verdict.validation_status == "unvalidated"
        assert verdict.confidence == "low"
        assert verdict.rationale.startswith(expected_rationale_prefix)


def test_compose_judge_prompt_redacts_worker_authored_values_before_string_composition() -> None:
    prompt = judge.compose_judge_prompt(
        skill="renmark:brainstorm",
        prompt="Design a release checklist.",
        baseline="Here is a generic answer.",
        golden={
            "self_assessment": "I should definitely win this comparison.",
            "text": "Here is a release checklist tailored to the contract.",
        },
        actual={
            "worker_confidence": "absolutely-certain-value",
            "preferred_verdict": "worker-only-preference",
            "text": "Here is a release checklist tailored to the contract.",
        },
        contract="The skill should produce a concrete release checklist.",
    )

    assert "I should definitely win this comparison." not in prompt
    assert "absolutely-certain-value" not in prompt
    assert "worker-only-preference" not in prompt
    assert "Here is a release checklist tailored to the contract." in prompt


def test_compose_judge_prompt_respects_swap_order_and_resolve_swap_order_exists() -> None:
    normal = judge.compose_judge_prompt(
        skill="skill-x",
        prompt="prompt-x",
        baseline="baseline-x",
        golden={"text": "golden-x"},
        actual={"text": "actual-x"},
        contract="contract-x",
        swap_order=False,
    )
    swapped = judge.compose_judge_prompt(
        skill="skill-x",
        prompt="prompt-x",
        baseline="baseline-x",
        golden={"text": "golden-x"},
        actual={"text": "actual-x"},
        contract="contract-x",
        swap_order=True,
    )

    assert callable(judge.resolve_swap_order)
    assert isinstance(judge.resolve_swap_order("seed"), bool)
    assert normal != swapped
    assert normal.index("BASELINE OUTPUT (skill disabled):") < normal.index(
        "ACTUAL WITH-SKILL OUTPUT:"
    )
    assert swapped.index("ACTUAL WITH-SKILL OUTPUT:") < swapped.index(
        "BASELINE OUTPUT (skill disabled):"
    )


def test_judge_evidence_ref_round_trips_from_verdict() -> None:
    verdict = Verdict(
        outcome="fail",
        confidence="high",
        validation_status="validated",
        rationale="Actual behavior matches the contract.",
    )

    ref = judge.JudgeEvidenceRef.from_verdict("subject-1", verdict)

    assert ref.subject_ref == "subject-1"
    assert ref.outcome == verdict.outcome
    assert ref.confidence == verdict.confidence
    assert ref.validation_status == verdict.validation_status
    assert ref.rationale == verdict.rationale
    assert ref.swapped is False


def test_judge_est_cost_usd_is_a_positive_float() -> None:
    assert isinstance(JUDGE_EST_COST_USD, float)
    assert JUDGE_EST_COST_USD > 0.0


def test_importing_judge_does_not_make_a_model_call() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import renmark.judge as judge; "
                "assert callable(judge._default_subagent_runner); "
                "assert judge.JUDGE_EST_COST_USD > 0; "
                "print('import-ok')"
            ),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == "import-ok"
    assert completed.stderr == ""

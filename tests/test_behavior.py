"""---
artifact_type: test_artifact
schema_version: 1
created_at: 2026-07-01T00:00:00-04:00
source_sha: null
related_plan: /home/renmark/projects/ai-system/.claude/worktrees/p8-behavioral-brainstorm/.renmark/plans/2026-07-01-p8-behavioral-skill-testing.plan.md
generator: codex
stale_after: null
dependency_refs:
  - /home/renmark/projects/ai-system/.claude/worktrees/p8-behavioral-brainstorm/renmark/behavior.py
  - /home/renmark/projects/ai-system/.claude/worktrees/p8-behavioral-brainstorm/renmark/judge.py
completion_state: complete
confidence: high
validation_status: pending
retry_count: 0
parser_success: true
schema_compliance: true
---

Behavior harness tests for the assertion-based replay redesign in
`renmark/behavior.py`. Fixtures are local and deterministic: each case writes a
`.behavior.json` file plus inline snapshot JSON in the new
`{"transcript": str, "inputs": dict}` format.

## Summary

- Covers `load_cases()` parsing, snapshot-ref traversal rejection, and assertions preservation.
- Covers replay `PASS`, assertion-driven `FAIL`, no-effect `FAIL`, and `ERROR` on missing or unusable snapshots.
- Covers `run(..., judge=False)` never invoking the judge while still offering escalation on deterministic failures.
- Covers `run(..., judge=True)` passing `actual=<current transcript>` to the judge and skipping escalation for `ERROR`.
- Covers deterministic assertion operators for `contains`, `not_contains`, `matches`, and `min_lines`.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from renmark import behavior
from renmark.judge import Verdict


def _write_case_file(
    tmp_path: Path,
    *,
    skill: str = "renmark:roadmap",
    prompt: str = "Summarize the next steps.",
    assertions: list[str] | None = None,
    baseline_ref: str = "case-baseline",
    golden_ref: str = "case-golden",
    filename: str = "sample.behavior.json",
) -> Path:
    payload = {
        "skill": skill,
        "prompt": prompt,
        "assertions": assertions if assertions is not None else ["contains:next step"],
        "baseline_ref": baseline_ref,
        "golden_ref": golden_ref,
    }
    case_path = tmp_path / filename
    case_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return case_path


def _write_snapshot(
    case_path: Path,
    ref: str,
    transcript: str,
    *,
    inputs: dict[str, object] | None = None,
) -> None:
    snapshots_dir = case_path.parent / "snapshots"
    snapshots_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "transcript": transcript,
        "inputs": (
            {
                "skill": "renmark:roadmap",
                "prompt": "reconstructed prompt",
                "skill_enabled": ref.endswith("golden"),
            }
            if inputs is None
            else inputs
        ),
    }
    (snapshots_dir / f"{ref}.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _make_case(
    tmp_path: Path,
    *,
    assertions: list[str] | None = None,
    baseline: str | None = None,
    golden: str | None = None,
    baseline_inputs: dict[str, object] | None = None,
    golden_inputs: dict[str, object] | None = None,
    baseline_ref: str = "case-baseline",
    golden_ref: str = "case-golden",
) -> behavior.Case:
    case_path = _write_case_file(
        tmp_path,
        assertions=assertions,
        baseline_ref=baseline_ref,
        golden_ref=golden_ref,
    )
    if baseline is not None:
        _write_snapshot(case_path, baseline_ref, baseline, inputs=baseline_inputs)
    if golden is not None:
        _write_snapshot(case_path, golden_ref, golden, inputs=golden_inputs)
    return behavior.load_cases(tmp_path)[0]


def test_load_cases_parses_behavior_json_into_case(tmp_path: Path) -> None:
    case_path = _write_case_file(
        tmp_path,
        skill="renmark:feature",
        prompt="Add a changelog entry.",
        assertions=["contains:Files changed", "line_ends:(Recommended)"],
        baseline_ref="feature-baseline",
        golden_ref="feature-golden",
        filename="feature.behavior.json",
    )

    loaded = behavior.load_cases(tmp_path)

    assert loaded == [
        behavior.Case(
            skill="renmark:feature",
            prompt="Add a changelog entry.",
            assertions=("contains:Files changed", "line_ends:(Recommended)"),
            baseline_ref="feature-baseline",
            golden_ref="feature-golden",
            source=case_path,
        )
    ]


def test_replay_passes_when_assertions_hold_on_current_transcript(tmp_path: Path) -> None:
    case = _make_case(
        tmp_path,
        assertions=["contains:next step", "not_contains:blocked", "line_ends:(Recommended)"],
        baseline="Plain answer with no menu.",
        golden="First next step\nChoose review (Recommended)",
    )

    result = behavior.replay(case)

    assert result.status == "PASS"
    assert result.message == "all assertions hold on the current transcript and it differs from baseline"
    assert result.failed_assertions == ()
    assert result.completion_state == "complete"
    assert result.validation_status == "validated"


def test_replay_fails_when_assertion_does_not_hold(tmp_path: Path) -> None:
    case = _make_case(
        tmp_path,
        assertions=["contains:next step", "contains:missing text"],
        baseline="Baseline without the contract text.",
        golden="Current transcript mentions the next step only.",
    )

    result = behavior.replay(case)

    assert result.status == "FAIL"
    assert result.message == "1 assertion(s) failed on the current transcript"
    assert result.failed_assertions == ("contains:missing text",)


def test_replay_fails_when_skill_had_no_effect_even_if_assertions_hold(tmp_path: Path) -> None:
    transcript = "same current transcript\nnext step"
    case = _make_case(
        tmp_path,
        assertions=["contains:next step"],
        baseline=transcript,
        golden=transcript,
    )

    result = behavior.replay(case)

    assert result.status == "FAIL"
    assert result.message == "with-skill transcript does not differ from baseline (skill had no effect)"
    assert result.failed_assertions == ()


def test_replay_errors_when_snapshot_is_missing(tmp_path: Path) -> None:
    case = _make_case(
        tmp_path,
        assertions=["contains:next step"],
        baseline="Recorded baseline exists.",
        golden=None,
    )

    result = behavior.replay(case)

    assert result.status == "ERROR"
    assert behavior.ACCEPT_FIRST_HINT in result.message
    assert "missing golden snapshot" in result.message


def test_replay_errors_when_golden_snapshot_has_empty_inputs(tmp_path: Path) -> None:
    case = _make_case(
        tmp_path,
        assertions=["contains:next step"],
        baseline="Recorded baseline exists.",
        golden="Recorded golden exists but cannot replay.",
        golden_inputs={},
    )

    result = behavior.replay(case)

    assert result.status == "ERROR"
    assert behavior.ACCEPT_FIRST_HINT in result.message
    assert "no recorded inputs" in result.message


def test_run_with_judge_disabled_never_invokes_judge(tmp_path: Path) -> None:
    case = _make_case(
        tmp_path,
        assertions=["contains:missing"],
        baseline="Baseline transcript.",
        golden="Current transcript without the required token.",
    )
    subagent_runner = Mock(name="subagent_runner")

    with patch("renmark.judge.judge_behavior", autospec=True) as judge_behavior:
        results = behavior.run(cases=[case], judge=False, subagent_runner=subagent_runner)

    assert len(results) == 1
    assert results[0].status == "FAIL"
    assert results[0].judge_offered is True
    assert results[0].judge_verdict is None
    judge_behavior.assert_not_called()
    subagent_runner.assert_not_called()


def test_run_with_judge_enabled_passes_current_transcript_as_actual(tmp_path: Path) -> None:
    current = "Current transcript mentions the next step only."
    case = _make_case(
        tmp_path,
        assertions=["contains:missing text"],
        baseline="Baseline transcript is different.",
        golden=current,
    )
    subagent_runner = Mock(name="subagent_runner")
    verdict = Verdict(
        outcome="fail",
        confidence="medium",
        validation_status="validated",
        rationale="The current transcript still misses the required text.",
    )

    with patch("renmark.judge.judge_behavior", autospec=True, return_value=verdict) as judge_behavior:
        results = behavior.run(
            cases=[case],
            judge=True,
            on_fail_offer=False,
            repo=tmp_path,
            subagent_runner=subagent_runner,
        )

    assert len(results) == 1
    assert results[0].status == "FAIL"
    assert results[0].judge_verdict == {
        "outcome": "fail",
        "confidence": "medium",
        "validation_status": "validated",
        "rationale": "The current transcript still misses the required text.",
    }
    _, kwargs = judge_behavior.call_args
    assert kwargs["actual"] == current
    assert kwargs["golden"] == current
    assert kwargs["baseline"] == "Baseline transcript is different."
    assert kwargs["contract"] == "- contains:missing text"


def test_run_with_judge_enabled_does_not_escalate_error_result(tmp_path: Path) -> None:
    case = _make_case(
        tmp_path,
        assertions=["contains:next step"],
        baseline="Recorded baseline exists.",
        golden="Golden transcript cannot replay.",
        golden_inputs={},
    )

    with patch("renmark.judge.judge_behavior", autospec=True) as judge_behavior:
        results = behavior.run(cases=[case], judge=True, repo=tmp_path)

    assert len(results) == 1
    assert results[0].status == "ERROR"
    assert results[0].judge_verdict is None
    judge_behavior.assert_not_called()


def test_load_cases_rejects_unsafe_snapshot_ref(tmp_path: Path) -> None:
    _write_case_file(tmp_path, golden_ref="../evil")

    with pytest.raises(behavior.BehaviorConfigError) as excinfo:
        behavior.load_cases(tmp_path)

    assert "snapshot ref '../evil'" in str(excinfo.value)


def test_assertion_miniformat_contains_not_contains_matches_and_min_lines(tmp_path: Path) -> None:
    case = _make_case(
        tmp_path,
        assertions=[
            "contains:next step",
            "not_contains:blocked",
            r"matches:^Alpha",
            "min_lines:2",
        ],
        baseline="No useful output.",
        golden="Alpha next step\nBeta follow-up",
    )

    result = behavior.replay(case)

    assert result.status == "PASS"


def test_unknown_op_shaped_assertion_fails_deterministically(tmp_path: Path) -> None:
    case = _make_case(
        tmp_path,
        assertions=["mystery:next step"],
        baseline="Baseline transcript.",
        golden="Current transcript includes next step.",
    )

    result = behavior.replay(case)

    assert result.status == "FAIL"
    assert result.failed_assertions == ("mystery:next step",)

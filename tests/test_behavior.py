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

Behavior harness unit tests covering declarative case loading, deterministic
replay outcomes, and judge escalation gating. Snapshots are written inline to a
temporary `snapshots/` directory; no live capture and no network access.

## Summary

- Verifies `load_cases()` parses `.behavior.json` files into strict `Case` objects.
- Covers replay PASS, FAIL-on-baseline-match, and ERROR-on-missing-snapshot outcomes.
- Asserts `run(..., judge=False)` offers escalation without invoking the judge.
- Asserts `run(..., judge=True)` lazily calls `renmark.judge.judge_behavior` on FAIL.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import Mock, patch

from renmark import behavior
from renmark.judge import Verdict


def _write_case_file(
    tmp_path: Path,
    *,
    skill: str = "renmark:brainstorm",
    prompt: str = "Help me plan a feature.",
    assertions: list[str] | None = None,
    baseline_ref: str = "case-baseline",
    golden_ref: str = "case-golden",
    filename: str = "sample.behavior.json",
) -> Path:
    case_path = tmp_path / filename
    payload = {
        "skill": skill,
        "prompt": prompt,
        "assertions": assertions or ["ask exactly one question"],
        "baseline_ref": baseline_ref,
        "golden_ref": golden_ref,
    }
    case_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return case_path


def _write_snapshot(case_path: Path, ref: str, transcript: str) -> None:
    snapshots_dir = case_path.parent / "snapshots"
    snapshots_dir.mkdir(parents=True, exist_ok=True)
    (snapshots_dir / f"{ref}.json").write_text(
        json.dumps({"transcript": transcript}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _make_case(tmp_path: Path, *, baseline: str | None, golden: str | None) -> behavior.Case:
    case_path = _write_case_file(tmp_path)
    if baseline is not None:
        _write_snapshot(case_path, "case-baseline", baseline)
    if golden is not None:
        _write_snapshot(case_path, "case-golden", golden)
    return behavior.load_cases(tmp_path)[0]


def test_load_cases_parses_behavior_json(tmp_path: Path) -> None:
    case_path = _write_case_file(
        tmp_path,
        skill="renmark:feature",
        prompt="Add a changelog entry.",
        assertions=["must mention files changed", "must state next step"],
        baseline_ref="feature-baseline",
        golden_ref="feature-golden",
        filename="feature.behavior.json",
    )

    loaded = behavior.load_cases(tmp_path)

    assert len(loaded) == 1
    case = loaded[0]
    assert case.skill == "renmark:feature"
    assert case.prompt == "Add a changelog entry."
    assert case.assertions == ("must mention files changed", "must state next step")
    assert case.baseline_ref == "feature-baseline"
    assert case.golden_ref == "feature-golden"
    assert case.source == case_path


def test_replay_passes_when_golden_matches_snapshot_and_differs_from_baseline(
    tmp_path: Path,
) -> None:
    case = _make_case(
        tmp_path,
        baseline="Plain assistant answer with no follow-up.",
        golden="Skill answer that asks exactly one follow-up question.",
    )

    result = behavior.replay(case)

    assert result.status == "PASS"
    assert result.message == "matches golden and differs from baseline"
    assert result.completion_state == "complete"
    assert result.validation_status == "validated"


def test_replay_fails_when_golden_matches_baseline(tmp_path: Path) -> None:
    transcript = "Identical output that proves the skill changed nothing."
    case = _make_case(tmp_path, baseline=transcript, golden=transcript)

    result = behavior.replay(case)

    assert result.status == "FAIL"
    assert result.message == "with-skill transcript does not differ from baseline (skill had no effect)"
    assert result.completion_state == "complete"
    assert result.validation_status == "validated"


def test_replay_returns_error_when_snapshot_file_is_missing(tmp_path: Path) -> None:
    case = _make_case(
        tmp_path,
        baseline="Recorded baseline exists.",
        golden=None,
    )

    result = behavior.replay(case)

    assert result.status == "ERROR"
    assert result.completion_state == "failed"
    assert result.validation_status == "unvalidated"
    assert behavior.ACCEPT_FIRST_HINT in result.message
    assert "missing golden snapshot" in result.message


def test_run_does_not_invoke_judge_when_disabled(tmp_path: Path) -> None:
    transcript = "No behavioral delta from baseline."
    case = _make_case(tmp_path, baseline=transcript, golden=transcript)
    subagent_runner = Mock(name="subagent_runner")

    with patch("renmark.judge.judge_behavior", autospec=True) as judge_behavior:
        results = behavior.run(cases=[case], judge=False, subagent_runner=subagent_runner)

    assert len(results) == 1
    result = results[0]
    assert result.status == "FAIL"
    assert result.judge_offered is True
    assert result.judge_verdict is None
    judge_behavior.assert_not_called()
    subagent_runner.assert_not_called()


def test_run_calls_judge_when_enabled_for_failing_case(tmp_path: Path) -> None:
    transcript = "No behavioral delta from baseline."
    case = _make_case(tmp_path, baseline=transcript, golden=transcript)
    subagent_runner = Mock(name="subagent_runner")
    verdict = Verdict(
        outcome="fail",
        confidence="medium",
        validation_status="validated",
        rationale="The with-skill output is identical to the baseline.",
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
    result = results[0]
    assert result.status == "FAIL"
    assert result.judge_offered is False
    assert result.judge_verdict == {
        "outcome": "fail",
        "confidence": "medium",
        "validation_status": "validated",
        "rationale": "The with-skill output is identical to the baseline.",
    }
    judge_behavior.assert_called_once_with(
        tmp_path,
        skill="renmark:brainstorm",
        prompt="Help me plan a feature.",
        baseline=transcript,
        golden=transcript,
        actual=transcript,
        contract="- ask exactly one question",
        subagent_runner=subagent_runner,
    )

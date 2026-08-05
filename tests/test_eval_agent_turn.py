"""
---
artifact_type: renmark_task_output
schema_version: "1.0"
created_at: "2026-07-02T00:00:00-04:00"
source_sha: "unknown"
related_plan: "Task 7: tests for the new behavior + judge entry points"
generator: "codex"
stale_after: null
dependency_refs:
  - "renmark/behavior.py"
  - "renmark/judge.py"
---

Hermetic unit tests for the public eval-agent-turn wrappers.

## Summary
- Added a reusable `Case` fixture rooted under `tmp_path`.
- Covered `compose_eval_prompt` with skill marker and original prompt assertions.
- Verified `capture_from_transcript` writes the expected snapshot payload.
- Proved `capture` is behavior-preserving against the transcript-based path with a stub runner.
- Covered judge prompt composition and defensive verdict parsing on valid and invalid input.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from renmark import behavior, judge


@pytest.fixture
def case(tmp_path: Path) -> behavior.Case:
    source = tmp_path / "agent-turn.behavior.json"
    source.write_text("{}", encoding="utf-8")
    return behavior.Case(
        skill="roadmap",
        prompt="Summarize the next steps.",
        deterministic=behavior.DeterministicSpec(
            call="lifecycle.next_steps",
            assertions=("contains:What's next:",),
        ),
        eval=behavior.EvalSpec(
            contract="Record the live transcript.",
            golden_ref="captured",
        ),
        source=source,
    )


def test_compose_eval_prompt_contains_enabled_skill_marker_and_case_prompt(
    case: behavior.Case,
) -> None:
    prompt = behavior.compose_eval_prompt(case)

    # Pin the FULL byte-exact prompt contract (this refactor must preserve it),
    # not just substrings.
    expected = (
        f"[skill ENABLED: {case.skill}] Respond to the following with the skill "
        f"active.\n\n{case.prompt}"
    )
    assert prompt == expected


def test_capture_from_transcript_writes_snapshot_and_returns_transcript(
    case: behavior.Case,
) -> None:
    transcript = behavior.capture_from_transcript(case, "TX")
    snapshot = case.source.parent / "snapshots" / f"{case.eval.golden_ref}.json"

    assert transcript == "TX"
    assert snapshot.exists()
    assert json.loads(snapshot.read_text(encoding="utf-8")) == {"transcript": "TX"}


def test_capture_produces_same_snapshot_as_capture_from_transcript(tmp_path: Path) -> None:
    direct_source = tmp_path / "direct.behavior.json"
    direct_source.write_text("{}", encoding="utf-8")
    direct_case = behavior.Case(
        skill="roadmap",
        prompt="Summarize the next steps.",
        deterministic=behavior.DeterministicSpec(
            call="lifecycle.next_steps",
            assertions=("contains:What's next:",),
        ),
        eval=behavior.EvalSpec(
            contract="Record the live transcript.",
            golden_ref="direct",
        ),
        source=direct_source,
    )

    runner_source = tmp_path / "runner.behavior.json"
    runner_source.write_text("{}", encoding="utf-8")
    runner_case = behavior.Case(
        skill="roadmap",
        prompt="Summarize the next steps.",
        deterministic=behavior.DeterministicSpec(
            call="lifecycle.next_steps",
            assertions=("contains:What's next:",),
        ),
        eval=behavior.EvalSpec(
            contract="Record the live transcript.",
            golden_ref="runner",
        ),
        source=runner_source,
    )

    seen_prompts: list[str] = []

    def stub_runner(prompt: str) -> str:
        seen_prompts.append(prompt)
        return "TX"

    direct_result = behavior.capture_from_transcript(direct_case, "TX")
    runner_result = behavior.capture(runner_case, stub_runner)

    direct_snapshot = json.loads(
        (direct_case.source.parent / "snapshots" / "direct.json").read_text(encoding="utf-8")
    )
    runner_snapshot = json.loads(
        (runner_case.source.parent / "snapshots" / "runner.json").read_text(encoding="utf-8")
    )

    assert direct_result == "TX"
    assert runner_result == "TX"
    assert seen_prompts == [behavior.compose_eval_prompt(runner_case)]
    assert direct_snapshot == runner_snapshot == {"transcript": "TX"}


def test_compose_judge_prompt_returns_non_empty_prompt_with_contract_text() -> None:
    prompt = judge.compose_judge_prompt(
        skill="roadmap",
        prompt="Summarize the next steps.",
        baseline="Baseline output",
        golden="Expected output",
        actual="Actual output",
        contract="Record the live transcript.",
    )

    assert prompt.strip()
    assert "SKILL CONTRACT" in prompt
    assert "Record the live transcript." in prompt
    assert "Respond with ONLY a JSON object" in prompt


def test_parse_judge_verdict_returns_validated_verdict_for_valid_json() -> None:
    verdict = judge.parse_judge_verdict(
        '{"outcome":"pass","confidence":"high","rationale":"The contract is met."}'
    )

    assert isinstance(verdict, judge.Verdict)
    assert verdict.outcome == "pass"
    assert verdict.confidence == "high"
    assert verdict.validation_status == "validated"
    assert verdict.rationale == "The contract is met."


def test_parse_judge_verdict_returns_unvalidated_uncertain_on_garbage() -> None:
    verdict = judge.parse_judge_verdict("not json at all")

    assert isinstance(verdict, judge.Verdict)
    assert verdict.outcome == "uncertain"
    assert verdict.confidence == "low"
    assert verdict.validation_status == "unvalidated"

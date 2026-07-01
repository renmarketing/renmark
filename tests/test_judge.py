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
validation_status: pending
retry_count: 0
parser_success: true
schema_compliance: true
---

Unit tests for the behavioral judge's deterministic contract.

These tests cover the mocked live-judge path, malformed/unparseable responses,
the published cost constant, and a clean import path that does not trigger any
model call at import time.

## Summary

- Verifies a valid mocked judge response returns a structured validated verdict.
- Verifies malformed responses become unvalidated failures, never silent passes.
- Pins `JUDGE_EST_COST_USD` as a positive float export.
- Confirms a fresh interpreter can import `renmark.judge` without making a call.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

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


def test_judge_behavior_marks_unparseable_response_unvalidated_and_failed() -> None:
    verdict = judge_behavior(
        subagent_runner=lambda prompt: "not json at all",
        **_judge_kwargs(),
    )

    assert verdict.validation_status == "unvalidated"
    assert verdict.outcome == "fail"
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
    assert verdict.outcome != "pass"
    assert verdict.outcome == "fail"
    assert verdict.confidence == "low"
    assert "unrecognized outcome" in verdict.rationale


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

from __future__ import annotations

import importlib
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from renmark import recurrence
from renmark.cli import _codex_runner as codex_runner
from renmark.parser import Task
from renmark.providers.codex import CodexResult
from renmark.scan import content_fingerprint, finding_key_from_parts
from renmark.verifier import VerifierResult


def _observation(
    *,
    rule_id: str = "verifier-failure",
    target: str = "tests/test_widget.py",
    signal: str = "stable failure",
    run_id: str = "run-1",
) -> recurrence.IssueObservation:
    return recurrence.IssueObservation(
        check="codex-retry",
        rule_id=rule_id,
        target=target,
        title=f"Codex {rule_id}",
        summary_text=signal,
        source="test",
        run_id=run_id,
    )


def _observe_twice(
    repo: Path,
    *,
    rule_id: str = "verifier-failure",
) -> recurrence.RecurrenceDecision:
    recurrence.observe_issue(repo, _observation(rule_id=rule_id))
    return recurrence.observe_issue(
        repo,
        _observation(rule_id=rule_id, run_id="run-2"),
    )


def test_identity_matches_scan_and_persisted_state_excludes_raw_signal(tmp_path: Path) -> None:
    secret = "raw transcript must never persist"
    observation = _observation(signal=secret)

    decision = recurrence.observe_issue(tmp_path, observation)

    assert decision.key == finding_key_from_parts(
        check=observation.check,
        rule_id=observation.rule_id,
        target=observation.target,
    )
    assert decision.fingerprint == content_fingerprint(
        title=observation.title,
        summary_text=observation.summary_text,
        target=observation.target,
    )[:16]
    state_text = (tmp_path / ".renmark/state/recurrences.json").read_text(encoding="utf-8")
    assert secret not in state_text
    assert observation.title not in state_text
    assert "summary_text" not in state_text
    assert "transcript" not in json.loads(state_text)["entries"][decision.key]


def test_equivalent_observations_block_across_runs_but_changed_signal_resets(
    tmp_path: Path,
) -> None:
    first = recurrence.observe_issue(tmp_path, _observation())
    second = recurrence.observe_issue(tmp_path, _observation(run_id="another-run"))
    changed = recurrence.observe_issue(
        tmp_path,
        _observation(signal="materially different failure", run_id="third-run"),
    )

    assert first.occurrence_count == 1
    assert first.retry_blocked is False
    assert second.occurrence_count == 2
    assert second.retry_blocked is True
    assert second.remediation_class == "patch"
    assert changed.occurrence_count == 1
    assert changed.retry_blocked is False
    assert changed.fingerprint != second.fingerprint


def test_remediation_acknowledgement_resolution_and_one_time_retry(tmp_path: Path) -> None:
    patch = _observe_twice(tmp_path)
    assert patch.remediation_class == "patch"

    acknowledged = recurrence.acknowledge_issue(
        tmp_path,
        key=patch.key,
        action="patch",
        fingerprint=patch.fingerprint,
        run_id="ack-patch",
    )
    assert acknowledged is not None
    assert acknowledged.acknowledged is True
    assert acknowledged.retry_blocked is False

    resolved = recurrence.resolve_issue(
        tmp_path,
        key=patch.key,
        action="patch",
        fingerprint=patch.fingerprint,
        run_id="resolved-patch",
    )
    assert resolved is not None
    assert resolved.resolved is True
    reopened = recurrence.observe_issue(tmp_path, _observation(run_id="after-resolution"))
    assert reopened.occurrence_count == 1

    guard = _observe_twice(tmp_path / "guard", rule_id="lane-violation")
    assert guard.remediation_class == "durable_guard"
    retry = recurrence.acknowledge_issue(
        tmp_path / "guard",
        key=guard.key,
        action="retry_once",
        fingerprint=guard.fingerprint,
        run_id="ack-retry",
    )
    assert retry is not None
    permitted = recurrence.pre_attempt(
        tmp_path / "guard",
        check="codex-retry",
        rule_id="lane-violation",
        target="tests/test_widget.py",
    )
    blocked_again = recurrence.pre_attempt(
        tmp_path / "guard",
        check="codex-retry",
        rule_id="lane-violation",
        target="tests/test_widget.py",
    )
    assert permitted is not None and permitted.retry_blocked is False
    assert blocked_again is not None and blocked_again.retry_blocked is True


def test_corrupt_state_recovers_and_pruning_is_bounded(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state_path = tmp_path / ".renmark/state/recurrences.json"
    state_path.parent.mkdir(parents=True)
    state_path.write_text("{not-json", encoding="utf-8")
    monkeypatch.setattr(recurrence, "MAX_ENTRIES", 3)

    for index in range(5):
        recurrence.observe_issue(
            tmp_path,
            _observation(target=f"tests/test_{index}.py", run_id=f"run-{index}"),
        )

    payload = json.loads(state_path.read_text(encoding="utf-8"))
    assert payload["version"] == recurrence.STATE_VERSION
    assert len(payload["entries"]) == 3


def test_atomic_write_failure_preserves_previous_ledger(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recurrence.observe_issue(tmp_path, _observation())
    state_path = tmp_path / ".renmark/state/recurrences.json"
    previous = state_path.read_bytes()

    def fail_replace(_source: object, _destination: object) -> None:
        raise OSError("simulated atomic replace failure")

    monkeypatch.setattr(os, "replace", fail_replace)
    with pytest.raises(recurrence.RecurrenceStateError, match="persist"):
        recurrence.observe_issue(
            tmp_path,
            _observation(target="tests/test_other.py"),
        )
    assert state_path.read_bytes() == previous


def test_missing_lock_backends_degrade_with_a_warning(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def missing_backend(_name: str) -> object:
        raise ModuleNotFoundError

    monkeypatch.setattr(importlib, "import_module", missing_backend)
    with pytest.warns(RuntimeWarning, match="lock"):
        decision = recurrence.observe_issue(tmp_path, _observation())
    assert decision.occurrence_count == 1


@pytest.mark.parametrize(
    ("failure_kind", "rule_id", "remediation"),
    [
        ("nonzero", "nonzero-executor-exit", "patch"),
        ("lane", "lane-violation", "durable_guard"),
        ("verifier", "verifier-failure", "patch"),
    ],
)
def test_codex_runner_stops_before_a_third_equivalent_attempt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure_kind: str,
    rule_id: str,
    remediation: recurrence.RemediationClass,
) -> None:
    calls = 0

    def run_codex(*_args: object, **_kwargs: object) -> CodexResult:
        nonlocal calls
        calls += 1
        return CodexResult(
            exit_code=1 if failure_kind == "nonzero" else 0,
            output_tail="stable executor failure",
            changed_files=["tests/test_widget.py"],
            pre_changed_files=[],
        )

    monkeypatch.setattr(codex_runner, "run_codex_task", run_codex)
    monkeypatch.setattr(codex_runner, "append_usage", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(codex_runner, "_print", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(codex_runner, "_record_escalation", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(codex_runner, "_classify_and_rollback", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        codex_runner,
        "_judge_lane_and_rollback",
        lambda *_args, **_kwargs: (
            (False, "stable lane failure") if failure_kind == "lane" else (True, "")
        ),
    )
    monkeypatch.setattr(
        codex_runner,
        "run_verifier",
        lambda *_args, **_kwargs: VerifierResult(
            exit_code=1 if failure_kind == "verifier" else 0,
            output="stable verifier failure",
            tail="stable verifier failure",
            timed_out=False,
        ),
    )
    task = Task(
        index=1,
        title="bounded retry",
        mode="A",
        target="tests/test_widget.py",
        verifier="pytest -q tests/test_widget.py",
    )
    cfg = SimpleNamespace(max_task_retries=1, default_verifier_timeout_s=5)

    result = codex_runner._execute_task_codex(
        task=task,
        repo=tmp_path,
        run_id="runner-test",
        cfg=cfg,
        total=1,
    )

    assert result[0] is False
    assert "repeated_issue_guard" in result
    assert calls == 2
    decision = recurrence.pre_attempt(
        tmp_path,
        check="codex-retry",
        rule_id=rule_id,
        target=task.target,
    )
    assert decision is not None
    assert decision.retry_blocked is True
    assert decision.remediation_class == remediation
    assert len(decision.summary_lines) <= recurrence.MAX_SUMMARY_LINES


def test_recurrence_guard_preserves_the_current_failure_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    decision = _observe_twice(tmp_path)
    recorded: dict[str, object] = {}

    def capture_escalation(*_args: object, **kwargs: object) -> None:
        recorded.update(kwargs)

    monkeypatch.setattr(codex_runner, "_record_escalation", capture_escalation)
    monkeypatch.setattr(codex_runner, "_print", lambda *_args, **_kwargs: None)
    task = Task(index=1, title="evidence", mode="A", target="tests/test_widget.py")
    cfg = SimpleNamespace(max_task_retries=1)

    codex_runner._codex_fail_recurrence_guard(
        task,
        1,
        tmp_path,
        "evidence-test",
        cfg,
        0,
        0.0,
        decision,
        verifier_log="actual verifier evidence",
    )

    assert recorded["verifier_log"] == "actual verifier evidence"


def test_orchestrate_contract_is_host_neutral_and_human_gated() -> None:
    text = (Path(__file__).parents[1] / "plugin/skills/orchestrate/SKILL.md").read_text(
        encoding="utf-8"
    )

    assert "prevents a third equivalent attempt" in text
    assert "on either Claude Code" in text
    assert "or Codex" in text
    assert "patching through `/renmark:debug`" in text
    assert "mirrored in both `CLAUDE.md` and `AGENTS.md`" in text
    assert "patch/debug" in text
    assert "propose a durable guard" in text
    assert "explicitly retry once" in text
    assert "still requires the normal human approval gate" in text
    assert "Do not observe Tier-1 or" in text
    assert "Tier-2 usage-limit pauses" in text

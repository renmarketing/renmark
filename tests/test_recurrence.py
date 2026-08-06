from __future__ import annotations

import importlib
import json
import os
from datetime import datetime, timedelta, timezone
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
    title: str | None = None,
    run_id: str = "run-1",
) -> recurrence.IssueObservation:
    return recurrence.IssueObservation(
        check="codex-retry",
        rule_id=rule_id,
        target=target,
        title=title or f"Codex {rule_id}",
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


def _recurrence_entry(repo: Path, key: str) -> dict[str, object]:
    payload = json.loads((repo / ".renmark/state/recurrences.json").read_text(encoding="utf-8"))
    return payload["entries"][key]


def _zulu(dt: datetime) -> str:
    return dt.isoformat().replace("+00:00", "Z")


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


def test_fresh_observe_issue_initializes_reopen_tracking_fields(tmp_path: Path) -> None:
    decision = recurrence.observe_issue(tmp_path, _observation())

    entry = _recurrence_entry(tmp_path, decision.key)
    assert entry["reopen_count"] == 0
    assert entry["reopen_timestamps"] == []
    assert entry["resolved_timestamps"] == []


def test_resolve_issue_appends_resolved_timestamp_and_equivalent_reobserve_marks_reopen(
    tmp_path: Path,
) -> None:
    observation = _observation()
    decision = recurrence.observe_issue(tmp_path, observation)
    resolved = recurrence.resolve_issue(
        tmp_path,
        key=decision.key,
        action="patch",
        fingerprint=decision.fingerprint,
        run_id="resolved-1",
    )

    assert resolved is not None
    entry = _recurrence_entry(tmp_path, decision.key)
    assert len(entry["resolved_timestamps"]) == 1
    assert entry["resolved_timestamps"][-1] == entry["resolved_at"]

    reopened = recurrence.observe_issue(tmp_path, _observation(run_id="run-2"))
    assert reopened.occurrence_count == 1

    entry = _recurrence_entry(tmp_path, decision.key)
    assert entry["reopen_count"] == 1
    assert entry["reopen_timestamps"] == [entry["last_observed_at"]]
    assert len(entry["resolved_timestamps"]) == 1


def test_observe_issue_with_different_fingerprint_starts_fresh_issue_after_resolve(
    tmp_path: Path,
) -> None:
    decision = recurrence.observe_issue(tmp_path, _observation())
    recurrence.resolve_issue(
        tmp_path,
        key=decision.key,
        action="patch",
        fingerprint=decision.fingerprint,
        run_id="resolved-1",
    )

    changed = recurrence.observe_issue(
        tmp_path,
        _observation(title="different title", signal="different summary", run_id="run-2"),
    )

    entry = _recurrence_entry(tmp_path, decision.key)
    assert changed.occurrence_count == 1
    assert entry["reopen_count"] == 0
    assert entry["reopen_timestamps"] == []
    assert entry["resolved_timestamps"] == []


def test_two_full_resolve_then_reobserve_cycles_accumulate_both_timestamp_lists(
    tmp_path: Path,
) -> None:
    observation = _observation()
    decision = recurrence.observe_issue(tmp_path, observation)

    recurrence.resolve_issue(
        tmp_path,
        key=decision.key,
        action="patch",
        fingerprint=decision.fingerprint,
        run_id="resolved-1",
    )
    recurrence.observe_issue(tmp_path, _observation(run_id="run-2"))
    recurrence.resolve_issue(
        tmp_path,
        key=decision.key,
        action="patch",
        fingerprint=decision.fingerprint,
        run_id="resolved-2",
    )
    recurrence.observe_issue(tmp_path, _observation(run_id="run-3"))

    entry = _recurrence_entry(tmp_path, decision.key)
    assert entry["reopen_count"] == 2
    assert len(entry["reopen_timestamps"]) == 2
    assert len(entry["resolved_timestamps"]) == 2


def test_reopen_rate_defaults_to_zero_without_state_file_and_counts_recent_reopen(
    tmp_path: Path,
) -> None:
    empty_rate = recurrence.reopen_rate(tmp_path)
    assert empty_rate["resolved_total"] == 0
    assert empty_rate["reopened_total"] == 0
    assert empty_rate["window_days"] == 30
    assert "window_start" in empty_rate
    assert "window_end" in empty_rate

    decision = recurrence.observe_issue(tmp_path, _observation())
    recurrence.resolve_issue(
        tmp_path,
        key=decision.key,
        action="patch",
        fingerprint=decision.fingerprint,
        run_id="resolved-1",
    )
    recurrence.observe_issue(tmp_path, _observation(run_id="run-2"))

    rate = recurrence.reopen_rate(tmp_path)
    assert rate["resolved_total"] == 1
    assert rate["reopened_total"] == 1
    assert rate["window_days"] == 30


def test_reopen_rate_windows_resolved_and_reopened_timestamps_independently(
    tmp_path: Path,
) -> None:
    now = datetime(2026, 8, 5, 12, 0, tzinfo=timezone.utc)
    decision = recurrence.observe_issue(tmp_path, _observation())
    recurrence.resolve_issue(
        tmp_path,
        key=decision.key,
        action="patch",
        fingerprint=decision.fingerprint,
        run_id="resolved-1",
    )

    state_path = tmp_path / ".renmark/state/recurrences.json"
    payload = json.loads(state_path.read_text(encoding="utf-8"))
    entry = payload["entries"][decision.key]
    resolved_at = _zulu(now - timedelta(days=60))
    reopened_at = _zulu(now - timedelta(days=5))
    entry["resolved_timestamps"] = [resolved_at]
    entry["reopen_timestamps"] = [reopened_at]
    entry["resolved_at"] = resolved_at
    entry["last_observed_at"] = _zulu(now)
    entry["reopen_count"] = 1
    state_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    rate = recurrence.reopen_rate(tmp_path, window_days=30, now=_zulu(now))
    assert rate["resolved_total"] == 0
    assert rate["reopened_total"] == 1
    assert rate["window_days"] == 30
    assert rate["window_start"] == _zulu(now - timedelta(days=30))
    assert rate["window_end"] == _zulu(now)


def test_failure_rule_lifecycle_persists_and_rejects_duplicate_ids(
    tmp_path: Path,
) -> None:
    registry_path = tmp_path / ".renmark" / "memory" / "failure_rules.jsonl"

    proposed = recurrence.propose_failure_rule(
        tmp_path,
        rule_id="policy-violation",
        trigger="stable failure signal",
        applicability="when codex retries the same failing task",
        required_behavior="stop and surface the failure",
        prohibited_failure="retrying without review",
        source_evidence=("tests/test_recurrence.py",),
        review_after="2030-01-01T00:00:00+00:00",
    )
    assert proposed.status == "proposed"
    assert registry_path == tmp_path / ".renmark" / "memory" / "failure_rules.jsonl"
    assert registry_path.exists()
    assert not (tmp_path / ".renmark" / "state" / "failure_rules.jsonl").exists()
    assert recurrence.load_failure_rules(tmp_path) == (proposed,)

    with pytest.raises(ValueError):
        recurrence.propose_failure_rule(
            tmp_path,
            rule_id="policy-violation",
            trigger="stable failure signal",
            applicability="when codex retries the same failing task",
            required_behavior="stop and surface the failure",
            prohibited_failure="retrying without review",
            source_evidence=("tests/test_recurrence.py",),
        )
    assert recurrence.load_failure_rules(tmp_path) == (proposed,)

    activated = recurrence.activate_failure_rule(tmp_path, "policy-violation")
    assert activated.status == "active"
    assert recurrence.load_failure_rules(tmp_path) == (activated,)

    with pytest.raises(ValueError, match="status 'active'"):
        recurrence.activate_failure_rule(tmp_path, "policy-violation")
    assert recurrence.load_failure_rules(tmp_path) == (activated,)

    deprecated = recurrence.deprecate_failure_rule(
        tmp_path,
        "policy-violation",
        reason="superseded by a broader guard",
    )
    assert deprecated.status == "deprecated"
    assert recurrence.load_failure_rules(tmp_path) == (deprecated,)


def test_failure_rule_conflicts_flag_contradictions_and_skip_deprecated_rules(
    tmp_path: Path,
) -> None:
    base = {
        "applicability": "when codex retries the same failing task",
        "source_evidence": ("tests/test_recurrence.py",),
    }

    contradiction_a = recurrence.propose_failure_rule(
        tmp_path,
        rule_id="contradiction-a",
        trigger="stable failure signal",
        required_behavior="retry once",
        prohibited_failure="abort immediately",
        **base,
    )
    contradiction_b = recurrence.propose_failure_rule(
        tmp_path,
        rule_id="contradiction-b",
        trigger="stable failure signal",
        required_behavior="escalate immediately",
        prohibited_failure="abort immediately",
        **base,
    )
    conflicts = recurrence.detect_failure_rule_conflicts(
        (contradiction_a, contradiction_b)
    )
    assert len(conflicts) == 1
    assert conflicts[0].kind == "contradiction"

    duplicate_a = recurrence.propose_failure_rule(
        tmp_path,
        rule_id="duplicate-a",
        trigger="stable failure signal",
        required_behavior="retry once",
        prohibited_failure="abort immediately",
        **base,
    )
    duplicate_b = recurrence.propose_failure_rule(
        tmp_path,
        rule_id="duplicate-b",
        trigger="stable failure signal",
        required_behavior="retry once",
        prohibited_failure="abort immediately",
        **base,
    )
    duplicate_conflicts = recurrence.detect_failure_rule_conflicts(
        (duplicate_a, duplicate_b)
    )
    assert len(duplicate_conflicts) == 1
    assert duplicate_conflicts[0].kind == "duplicate_trigger"

    deprecated_duplicate = recurrence.deprecate_failure_rule(tmp_path, "duplicate-b")
    assert deprecated_duplicate.status == "deprecated"
    assert recurrence.detect_failure_rule_conflicts(
        (duplicate_a, deprecated_duplicate)
    ) == ()


def test_failure_rules_due_for_review_is_read_only_and_only_returns_due_rules(
    tmp_path: Path,
) -> None:
    now = datetime.now(timezone.utc)
    past = (now - timedelta(days=1)).isoformat()
    future = (now + timedelta(days=1)).isoformat()

    due = recurrence.activate_failure_rule(
        tmp_path,
        recurrence.propose_failure_rule(
            tmp_path,
            rule_id="review-due",
            trigger="stable failure signal",
            applicability="when codex retries the same failing task",
            required_behavior="stop and surface the failure",
            prohibited_failure="retrying without review",
            source_evidence=("tests/test_recurrence.py",),
            review_after=past,
        ).rule_id,
    )
    future_rule = recurrence.activate_failure_rule(
        tmp_path,
        recurrence.propose_failure_rule(
            tmp_path,
            rule_id="review-future",
            trigger="stable failure signal",
            applicability="when codex retries the same failing task",
            required_behavior="stop and surface the failure",
            prohibited_failure="retrying without review",
            source_evidence=("tests/test_recurrence.py",),
            review_after=future,
        ).rule_id,
    )
    no_review = recurrence.activate_failure_rule(
        tmp_path,
        recurrence.propose_failure_rule(
            tmp_path,
            rule_id="review-none",
            trigger="stable failure signal",
            applicability="when codex retries the same failing task",
            required_behavior="stop and surface the failure",
            prohibited_failure="retrying without review",
            source_evidence=("tests/test_recurrence.py",),
        ).rule_id,
    )
    proposed = recurrence.propose_failure_rule(
        tmp_path,
        rule_id="review-proposed",
        trigger="stable failure signal",
        applicability="when codex retries the same failing task",
        required_behavior="stop and surface the failure",
        prohibited_failure="retrying without review",
        source_evidence=("tests/test_recurrence.py",),
        review_after=past,
    )

    due_rules = recurrence.failure_rules_due_for_review(tmp_path, as_of=now)
    assert tuple(rule.rule_id for rule in due_rules) == (due.rule_id,)
    assert due_rules[0].status == "active"
    assert recurrence.load_failure_rules(tmp_path) == (
        due,
        future_rule,
        no_review,
        proposed,
    )


def test_durable_guard_seed_candidates_are_read_only_and_return_seeded_keys(
    tmp_path: Path,
) -> None:
    state_path = tmp_path / ".renmark" / "state" / "recurrences.json"
    registry_path = tmp_path / ".renmark" / "memory" / "failure_rules.jsonl"

    recurrence.observe_issue(
        tmp_path,
        _observation(rule_id="policy-violation", run_id="seed-1"),
    )
    recurrence.observe_issue(
        tmp_path,
        _observation(rule_id="policy-violation", run_id="seed-2"),
    )
    third = recurrence.observe_issue(
        tmp_path,
        _observation(rule_id="policy-violation", run_id="seed-3"),
    )

    state_before = state_path.read_bytes()
    registry_before = registry_path.read_bytes() if registry_path.exists() else None

    candidates = recurrence.durable_guard_seed_candidates(tmp_path)

    assert len(candidates) == 1
    assert candidates[0]["key"] == third.key
    assert candidates[0]["occurrence_count"] == 3
    assert candidates[0]["target"] == "tests/test_widget.py"
    assert third.occurrence_count == 3
    assert third.remediation_class == "durable_guard"
    assert state_path.read_bytes() == state_before
    if registry_before is None:
        assert not registry_path.exists()
    else:
        assert registry_path.read_bytes() == registry_before


def test_req24_recurrence_decisions_remain_stable_across_pre_attempt_ack_and_resolve(
    tmp_path: Path,
) -> None:
    observed = _observe_twice(tmp_path)
    pre_attempt_decision = recurrence.pre_attempt(
        tmp_path,
        check="codex-retry",
        rule_id="verifier-failure",
        target="tests/test_widget.py",
    )
    acknowledged = recurrence.acknowledge_issue(
        tmp_path,
        key=observed.key,
        action="patch",
        fingerprint=observed.fingerprint,
        run_id="ack-patch",
    )
    resolved = recurrence.resolve_issue(
        tmp_path,
        key=observed.key,
        action="patch",
        fingerprint=observed.fingerprint,
        run_id="resolved-patch",
    )

    assert observed.occurrence_count == 2
    assert observed.retry_blocked is True
    assert observed.remediation_class == "patch"
    assert observed.summary_lines == ("Codex verifier-failure", "stable failure")

    assert pre_attempt_decision.occurrence_count == 2
    assert pre_attempt_decision.retry_blocked is True
    assert pre_attempt_decision.remediation_class == "patch"
    assert pre_attempt_decision.summary_lines == (
        "test: tests/test_widget.py",
        "occurrences=2; remediation=patch; status=open",
        "next attempt blocked",
    )

    assert acknowledged is not None
    assert acknowledged.occurrence_count == 2
    assert acknowledged.retry_blocked is False
    assert acknowledged.remediation_class == "patch"
    assert acknowledged.summary_lines == (
        "test: tests/test_widget.py",
        "occurrences=2; remediation=patch; status=acknowledged",
        "next attempt permitted",
    )

    assert resolved is not None
    assert resolved.occurrence_count == 2
    assert resolved.retry_blocked is False
    assert resolved.remediation_class == "patch"
    assert resolved.summary_lines == (
        "test: tests/test_widget.py",
        "occurrences=2; remediation=patch; status=resolved",
        "next attempt permitted",
    )


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

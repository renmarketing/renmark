"""Tests for renmark.shadow — record-and-replay framework. Uses an
isolated tmpdir to avoid touching real tests/shadow/ baselines."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from renmark import shadow


@pytest.fixture
def shadow_root(tmp_path: Path, monkeypatch) -> Path:
    """Redirect shadow.* helpers at an isolated tmpdir."""
    monkeypatch.setattr(shadow, "_shadow_root", lambda: tmp_path)
    return tmp_path


def _write_case(root: Path, subsystem: str, name: str, payload: dict) -> None:
    cases = root / "cases" / subsystem
    cases.mkdir(parents=True, exist_ok=True)
    (cases / f"{name}.json").write_text(json.dumps(payload), encoding="utf-8")


def _write_baseline(root: Path, subsystem: str, name: str, payload: dict) -> None:
    base = root / "baselines" / subsystem
    base.mkdir(parents=True, exist_ok=True)
    (base / f"{name}.json").write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")


# ── registry ──────────────────────────────────────────────────────────────────


def test_register_adds_subsystem():
    assert "dispatch" in shadow.registered_subsystems()
    assert "lifecycle" in shadow.registered_subsystems()
    assert "summary" in shadow.registered_subsystems()


# ── run / diff ────────────────────────────────────────────────────────────────


def test_run_match_when_baseline_agrees(shadow_root: Path):
    _write_case(
        shadow_root,
        "dispatch",
        "case-x",
        {"response": {"status": "PASS", "artifact_path": "x", "summary_lines": ["ok"]}},
    )
    diffs = shadow.run_subsystem("dispatch")
    # No baseline yet → missing.
    assert all(d.result == "missing-baseline" for d in diffs)

    # Now record baseline by hand.
    actual = shadow._REGISTRY["dispatch"](
        {"response": {"status": "PASS", "artifact_path": "x", "summary_lines": ["ok"]}}
    )
    _write_baseline(shadow_root, "dispatch", "case-x", actual)

    diffs = shadow.run_subsystem("dispatch")
    assert all(d.result == "match" for d in diffs)


def test_run_drift_when_baseline_differs(shadow_root: Path):
    _write_case(
        shadow_root,
        "dispatch",
        "case-y",
        {"response": {"status": "PASS", "artifact_path": "x", "summary_lines": ["new"]}},
    )
    _write_baseline(
        shadow_root, "dispatch", "case-y", {"status": "PASS", "artifact_path": "x", "summary_lines": ["old"]}
    )
    diffs = shadow.run_subsystem("dispatch")
    assert any(d.result == "drift" for d in diffs)


def test_run_missing_baseline_flagged(shadow_root: Path):
    _write_case(
        shadow_root,
        "dispatch",
        "case-fresh",
        {"response": {"status": "PASS", "artifact_path": "x", "summary_lines": []}},
    )
    diffs = shadow.run_subsystem("dispatch")
    assert any(d.result == "missing-baseline" for d in diffs)


def test_run_handles_corrupt_case(shadow_root: Path):
    bad_path = shadow_root / "cases" / "dispatch"
    bad_path.mkdir(parents=True)
    (bad_path / "case-broken.json").write_text("{not valid json")
    diffs = shadow.run_subsystem("dispatch")
    assert any(d.result == "error" for d in diffs)


def test_run_unknown_subsystem_raises(shadow_root: Path):
    with pytest.raises(KeyError):
        shadow.run_subsystem("bogus-subsystem-xyz")


def test_run_isolation_violation_is_baselineable(shadow_root: Path):
    """A SubagentOutput containing leaked fields should baseline as the
    IsolationViolation error message — not crash the runner."""
    _write_case(
        shadow_root,
        "dispatch",
        "case-leak",
        {
            "response": {
                "status": "PASS",
                "artifact_path": "x",
                "summary_lines": ["ok"],
                "transcript": "leak",
            }
        },
    )
    diffs = shadow.run_subsystem("dispatch")
    # missing-baseline — but the replay didn't crash.
    assert len(diffs) >= 1
    d = next(d for d in diffs if d.case == "case-leak")
    assert d.result == "missing-baseline"
    assert d.actual is not None
    assert d.actual.get("error") == "IsolationViolation"


# ── accept ────────────────────────────────────────────────────────────────────


def test_accept_writes_baselines_and_changelog(shadow_root: Path):
    _write_case(
        shadow_root,
        "dispatch",
        "case-a",
        {"response": {"status": "PASS", "artifact_path": "x", "summary_lines": ["ok"]}},
    )
    count = shadow.accept_subsystem("dispatch", "first baseline")
    assert count == 1
    assert (shadow_root / "baselines" / "dispatch" / "case-a.json").exists()
    assert (shadow_root / "CHANGES.md").exists()
    log = (shadow_root / "CHANGES.md").read_text()
    assert "dispatch" in log
    assert "first baseline" in log


def test_accept_requires_message(shadow_root: Path):
    with pytest.raises(ValueError):
        shadow.accept_subsystem("dispatch", "")
    with pytest.raises(ValueError):
        shadow.accept_subsystem("dispatch", "   ")


def test_accept_rejects_unknown_subsystem(shadow_root: Path):
    with pytest.raises(KeyError):
        shadow.accept_subsystem("nope", "msg")


def test_accept_makes_subsequent_run_clean(shadow_root: Path):
    _write_case(shadow_root, "lifecycle", "case-z", {"calls": [{"stage": "init", "feature": "x", "branch": "x"}]})
    shadow.accept_subsystem("lifecycle", "test baseline")
    diffs = shadow.run_subsystem("lifecycle")
    assert all(d.result == "match" for d in diffs)


def test_accept_prepends_to_existing_changelog(shadow_root: Path):
    _write_case(shadow_root, "lifecycle", "case-1", {"calls": [{"stage": "init", "feature": "x", "branch": "x"}]})
    shadow.accept_subsystem("lifecycle", "first")
    shadow.accept_subsystem("lifecycle", "second")
    log = (shadow_root / "CHANGES.md").read_text()
    # Header still at top, second message above first.
    assert log.startswith("# Shadow baseline changes")
    pos_second = log.index("second")
    pos_first = log.index("first")
    assert pos_second < pos_first


# ── replay functions are deterministic ───────────────────────────────────────


def test_dispatch_replay_strips_isolation_violation():
    out = shadow._replay_dispatch(
        {
            "response": {
                "status": "PASS",
                "artifact_path": "x",
                "summary_lines": ["ok"],
                "transcript": "leak",
            }
        }
    )
    assert out["error"] == "IsolationViolation"


def test_dispatch_replay_pristine_path():
    out = shadow._replay_dispatch(
        {
            "response": {
                "status": "PASS",
                "artifact_path": "x.md",
                "summary_lines": ["one"],
            }
        }
    )
    assert out["status"] == "PASS"
    assert "transcript" not in out


def test_lifecycle_replay_strips_last_updated():
    """last_updated is a timestamp — must be stripped for deterministic baselines."""
    out = shadow._replay_lifecycle({"calls": [{"stage": "init", "feature": "x", "branch": "x"}]})
    assert "last_updated" not in out
    assert out["feature"] == "x"


def test_summary_replay_deterministic():
    out1 = shadow._replay_summary({"metadata": {"artifact_type": "verification", "generator": "test"}})
    out2 = shadow._replay_summary({"metadata": {"artifact_type": "verification", "generator": "test"}})
    # Same input → same output (we inject a fixed created_at).
    assert out1 == out2


# ── CLI ──────────────────────────────────────────────────────────────────────


def test_cli_list_subcommand(capsys):
    exit_code = shadow.main(["list"])
    assert exit_code == 0
    out = capsys.readouterr().out
    assert "dispatch" in out
    assert "lifecycle" in out


def test_cli_accept_requires_message_arg(capsys):
    exit_code = shadow.main(["accept", "--subsystem", "dispatch"])
    assert exit_code == 2


def test_cli_accept_requires_subsystem(capsys):
    exit_code = shadow.main(["accept", "-m", "msg"])
    assert exit_code == 2


def test_cli_run_against_real_baselines():
    """The shipped baselines must agree with the current code. Drift here
    means the source changed without the dev running ``accept``."""
    diffs = shadow.run_all()
    bad = []
    for sub, dlist in diffs.items():
        for d in dlist:
            if d.result not in ("match",):
                bad.append((sub, d.case, d.result, d.error))
    assert not bad, f"shipped shadow baselines drift from current code: {bad}"


def test_cli_unknown_command():
    assert shadow.main(["bogus"]) == 2


def test_cli_empty():
    assert shadow.main([]) == 2

"""---
artifact_type: renmark_task_output
schema_version: "1.0"
created_at: "2026-07-02T00:00:00-04:00"
source_sha: "unknown"
related_plan: "Task 4: tests for the runner seam + delegation"
generator: "codex"
stale_after: null
dependency_refs:
  - "Task 3"
---

This artifact implements the eval-runner seam coverage requested by the task:
config/env precedence, subprocess execution, resolver behavior, and the
behavior-layer delegation path that uses the runner to capture a snapshot.

## Summary
- Added precedence coverage for env, config, and default `None`.
- Added a real subprocess round-trip test using `cat`.
- Added failure-mode coverage for blank, missing, and non-zero runner commands.
- Added resolver coverage for unconfigured and configured paths.
- Added behavior-layer delegation coverage for `build_subagent_runner` and `capture`.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from renmark import behavior, config
from renmark.providers.eval_runner import (
    EvalRunnerError,
    build_subprocess_runner,
    resolve_eval_runner,
)


@pytest.fixture(autouse=True)
def _clear_eval_runner_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("RENMARK_EVAL_RUNNER_CMD", raising=False)


def _case_file(tmp_path: Path, *, golden_ref: str = "captured") -> behavior.Case:
    source = tmp_path / "roadmap.behavior.json"
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
            golden_ref=golden_ref,
        ),
        source=source,
    )


def test_eval_runner_cmd_precedence_env_then_config_then_default(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path

    assert config.eval_runner_cmd(repo) is None

    config.set_eval_runner_cmd(repo, "cat")
    assert config.eval_runner_cmd(repo) == "cat"

    monkeypatch.setenv("RENMARK_EVAL_RUNNER_CMD", "  env-cat  ")
    assert config.eval_runner_cmd(repo) == "env-cat"

    monkeypatch.setenv("RENMARK_EVAL_RUNNER_CMD", "   ")
    assert config.eval_runner_cmd(repo) == "cat"


def test_build_subprocess_runner_round_trips_stdin_to_stdout() -> None:
    runner = build_subprocess_runner("cat")

    assert runner("hello") == "hello"


@pytest.mark.parametrize(
    ("cmd", "prompt", "message"),
    [
        ('sh -c "exit 3"', "hello", "exited 3"),
        ("command-that-definitely-does-not-exist-renmark", "hello", "not found on PATH"),
        ("   ", None, "empty after shlex.split"),
    ],
)
def test_build_subprocess_runner_failure_modes_raise_eval_runner_error(
    cmd: str,
    prompt: str | None,
    message: str,
) -> None:
    if prompt is None:
        with pytest.raises(EvalRunnerError, match=message):
            build_subprocess_runner(cmd)
        return

    runner = build_subprocess_runner(cmd)
    with pytest.raises(EvalRunnerError, match=message):
        runner(prompt)


def test_resolve_eval_runner_returns_none_when_unconfigured(tmp_path: Path) -> None:
    assert resolve_eval_runner(tmp_path) is None


def test_resolve_eval_runner_returns_callable_when_env_configured(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("RENMARK_EVAL_RUNNER_CMD", "cat")

    runner = resolve_eval_runner(tmp_path)

    assert runner is not None
    assert runner("hello") == "hello"


def test_behavior_build_subagent_runner_raises_when_unconfigured(tmp_path: Path) -> None:
    with pytest.raises(behavior.LiveRunnerUnavailable):
        behavior.build_subagent_runner(tmp_path)


def test_behavior_build_subagent_runner_delegates_to_configured_live_runner_and_capture(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("RENMARK_EVAL_RUNNER_CMD", "cat")
    case = _case_file(tmp_path)

    runner = behavior.build_subagent_runner(tmp_path)
    recorded = behavior.capture(case, runner)

    assert "[skill ENABLED: roadmap]" in recorded
    assert case.prompt in recorded

    snapshot = tmp_path / "snapshots" / "captured.json"
    assert snapshot.exists()
    payload = json.loads(snapshot.read_text(encoding="utf-8"))
    assert payload["transcript"] == recorded

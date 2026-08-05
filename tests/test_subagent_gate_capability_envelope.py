"""
---
artifact_type: test
schema_version: 1
created_at: "2026-08-05T00:00:00-04:00"
source_sha: "task-spec"
related_plan: "Task 5: envelope tests"
generator: "codex"
dependency_refs:
  - "renmark.subagent_gate"
  - "renmark.cost"
---

Capability-envelope regression tests for `renmark.subagent_gate`.

This file intentionally carries a renmark artifact header while remaining a
normal pytest module so the verifier can execute it directly.

## Summary
- Locks the control-status table to the claimed 6-control x 2-host matrix.
- Verifies path, command, spend, advisory, and unsupported envelope behavior.
- Confirms codex path checks are post-action-only, not pre-dispatch blocks.
- Checks malformed or unknown controls degrade safely to `unsupported`.
"""

from __future__ import annotations

from collections.abc import Iterable

import pytest

from renmark import cost, subagent_gate, subagent_profiles
from renmark.subagent_gate import ENVELOPE_CONTROL_STATUS, check_capability_envelope, control_status


def verdict_by_control(verdicts: Iterable[subagent_gate.EnvelopeVerdict], control: str) -> subagent_gate.EnvelopeVerdict:
    for verdict in verdicts:
        if verdict.control == control:
            return verdict
    raise AssertionError(f"missing verdict for control={control!r}")


def test_control_status_table_matches_claimed_matrix() -> None:
    expected = {
        "path": {"claude": "enforced", "codex": "verified_after"},
        "command": {"claude": "enforced", "codex": "enforced"},
        "spend_timeout": {"claude": "enforced", "codex": "enforced"},
        "network_domain": {"claude": "advisory", "codex": "advisory"},
        "git_action": {"claude": "advisory", "codex": "advisory"},
        "external_action": {"claude": "unsupported", "codex": "unsupported"},
    }

    assert ENVELOPE_CONTROL_STATUS == expected


@pytest.mark.parametrize(
    ("control", "host", "expected"),
    [
        ("path", "claude", "enforced"),
        ("path", "codex", "verified_after"),
        ("command", "codex", "enforced"),
        ("network_domain", "claude", "advisory"),
        ("external_action", "codex", "unsupported"),
        ("nonsense", "claude", "unsupported"),
    ],
)
def test_control_status_degrades_safely(control: str, host: str, expected: str) -> None:
    assert control_status(control, host) == expected


@pytest.mark.parametrize("host", ["claude", "codex"])
def test_path_and_command_envelope_for_code_implementer(host: str) -> None:
    in_envelope = check_capability_envelope(
        "code-implementer",
        {"paths": ["renmark/subagent_gate.py"]},
        host=host,
    )
    path_verdict = verdict_by_control(in_envelope, "path")

    if host == "claude":
        assert path_verdict.passed is True
    else:
        assert path_verdict.passed is True
        assert "post-action" in path_verdict.reason
        assert "not pre-dispatch" in path_verdict.reason

    out_of_envelope = check_capability_envelope(
        "code-implementer",
        {"paths": ["secrets/keys.pem"]},
        host=host,
    )
    path_verdict = verdict_by_control(out_of_envelope, "path")

    if host == "claude":
        assert path_verdict.passed is False
        assert path_verdict.violations
    else:
        assert path_verdict.passed is True
        assert "post-action" in path_verdict.reason
        assert "not pre-dispatch" in path_verdict.reason


def test_command_envelope_and_general_purpose_passthrough() -> None:
    allowed = check_capability_envelope(
        "test-writer",
        {"commands": ["pytest"]},
        host="claude",
    )
    allowed_command = verdict_by_control(allowed, "command")
    assert allowed_command.passed is True
    assert allowed_command.violations == ()

    blocked = check_capability_envelope(
        "test-writer",
        {"commands": ["rm"]},
        host="claude",
    )
    blocked_command = verdict_by_control(blocked, "command")
    assert blocked_command.passed is False
    assert blocked_command.violations

    unrestricted = check_capability_envelope(
        "general-purpose",
        {"commands": ["rm"]},
        host="claude",
    )
    unrestricted_command = verdict_by_control(unrestricted, "command")
    assert unrestricted_command.passed is True
    assert unrestricted_command.violations == ()


def test_spend_timeout_envelope_uses_role_tier_ceiling() -> None:
    role = "code-implementer"
    tier = subagent_profiles.profile_tier(role)
    max_tokens = cost.DEFAULT_MAX_TOKENS_PER_DISPATCH[tier]

    within = check_capability_envelope(role, {"budget": {"max_tokens": max_tokens}}, host="claude")
    within_spend = verdict_by_control(within, "spend_timeout")
    assert within_spend.passed is True
    assert within_spend.violations == ()

    malformed = check_capability_envelope(
        role,
        {"budget": {"max_tokens": -1}},
        host="claude",
    )
    malformed_spend = verdict_by_control(malformed, "spend_timeout")
    assert malformed_spend.passed is False
    assert malformed_spend.violations


@pytest.mark.parametrize("host", ["claude", "codex"])
@pytest.mark.parametrize(
    ("control", "expected_status"),
    [
        ("network_domain", "advisory"),
        ("git_action", "advisory"),
        ("external_action", "unsupported"),
    ],
)
def test_advisory_and_unsupported_dimensions_always_pass(
    host: str,
    control: str,
    expected_status: str,
) -> None:
    verdicts = check_capability_envelope(
        "code-implementer",
        {
            "paths": ["secrets/keys.pem"],
            "commands": ["rm"],
            "budget": {"max_tokens": 1},
            "network_domains": ["example.com"],
            "git_actions": ["push"],
            "external_actions": ["callout"],
        },
        host=host,
    )
    verdict = verdict_by_control(verdicts, control)
    assert verdict.passed is True
    assert verdict.status == expected_status
    assert verdict.violations == ()

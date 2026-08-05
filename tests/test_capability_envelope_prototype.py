import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
HOOK_PATH = REPO_ROOT / ".claude" / "hooks" / "capability_envelope_prototype.py"


def run_hook(payload: dict[str, object]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(HOOK_PATH)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
    )


def test_allowed_target_passes() -> None:
    payload = {
        "tool_name": "Write",
        "tool_input": {"file_path": "renmark/scratch_prototype.py"},
        "cwd": str(REPO_ROOT),
    }

    result = run_hook(payload)

    assert result.returncode == 0
    parsed = json.loads(result.stdout)
    assert parsed["hookSpecificOutput"]["permissionDecision"] == "allow"


def test_disallowed_target_blocks() -> None:
    payload = {
        "tool_name": "Write",
        "tool_input": {"file_path": "secrets/.env"},
        "cwd": str(REPO_ROOT),
    }

    result = run_hook(payload)

    assert result.returncode == 0
    parsed = json.loads(result.stdout)
    assert parsed["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_non_write_tool_defers() -> None:
    payload = {
        "tool_name": "Grep",
        "tool_input": {"pattern": "ls"},
        "cwd": str(REPO_ROOT),
    }

    result = run_hook(payload)

    assert result.returncode == 0
    assert result.stdout == ""


def test_bash_allowed_command_passes() -> None:
    payload = {
        "tool_name": "Bash",
        "tool_input": {"command": "pytest tests/"},
        "renmark_role": "code-implementer",
        "cwd": str(REPO_ROOT),
    }

    result = run_hook(payload)

    assert result.returncode == 0
    parsed = json.loads(result.stdout)
    assert parsed["hookSpecificOutput"]["permissionDecision"] == "allow"


def test_bash_disallowed_command_blocks() -> None:
    payload = {
        "tool_name": "Bash",
        "tool_input": {"command": "rm -rf /"},
        "renmark_role": "code-implementer",
        "cwd": str(REPO_ROOT),
    }

    result = run_hook(payload)

    assert result.returncode == 0
    parsed = json.loads(result.stdout)
    assert parsed["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "allowed_commands" in parsed["hookSpecificOutput"]["permissionDecisionReason"]


def test_bash_role_with_no_restrictions_always_allows() -> None:
    payload = {
        "tool_name": "Bash",
        "tool_input": {"command": "rm -rf /"},
        "renmark_role": "general-purpose",
        "cwd": str(REPO_ROOT),
    }

    result = run_hook(payload)

    assert result.returncode == 0
    assert result.stdout == ""


def test_bash_missing_command_defers() -> None:
    payload = {
        "tool_name": "Bash",
        "tool_input": {},
        "renmark_role": "code-implementer",
        "cwd": str(REPO_ROOT),
    }

    result = run_hook(payload)

    assert result.returncode == 0
    assert result.stdout == ""

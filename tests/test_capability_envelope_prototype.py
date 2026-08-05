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
        "tool_name": "Bash",
        "tool_input": {"command": "ls"},
        "cwd": str(REPO_ROOT),
    }

    result = run_hook(payload)

    assert result.returncode == 0
    assert result.stdout == ""

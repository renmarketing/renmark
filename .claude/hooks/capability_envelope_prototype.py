"""Still PROTOTYPE / SPIKE evidence for Release 6 of
`governed-orchestration-assurance` — hardened per Release 6, but NOT
registered in `.claude/settings.json`. Going live requires a SEPARATE,
explicit Owner-approved step outside this program's task dispatch.

Not wired into `.claude/settings.json`, not used by any renmark dispatch
path.

Implements Claude Code's `PreToolUse` hook contract. Reads a single JSON
payload from stdin describing a proposed tool call, resolves the acting
agent profile from `renmark/subagent_profiles.py` (via the hypothetical
`renmark_role` payload field, falling back to `code-implementer` when
absent), and prints an `allow` / `deny` decision for:

- `Write` / `Edit` calls whose `file_path` does, or does not, match that
  profile's `allowed_targets` globs.
- `Bash` calls whose extracted command name does, or does not, appear in
  that profile's `allowed_commands` tuple (empty tuple = no restriction).

Any other tool call, or malformed input, is passed through silently (no
decision) so normal permission flow applies.
"""

from __future__ import annotations

import fnmatch
import json
import sys
from pathlib import Path

# Insert the repo root at the front of sys.path so this script can import
# renmark.subagent_profiles when run standalone (e.g. by the Claude Code
# hook runner), independent of the invoking process's cwd or PYTHONPATH.
_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))

from renmark.subagent_profiles import PROFILES  # noqa: E402


def _make_relative(file_path: str, cwd: str | None) -> str:
    """Return `file_path` relative to `cwd` (forward slashes) when possible.

    Purely lexical (no filesystem access) — this only strips a matching
    `cwd` prefix from `file_path`, since neither value is guaranteed to
    exist on disk in this prototype. Falls back to `file_path` unchanged
    if `cwd` is absent or is not a prefix of `file_path`.
    """
    normalized_path = file_path.replace("\\", "/")
    if not cwd:
        return normalized_path

    normalized_cwd = cwd.replace("\\", "/").rstrip("/")
    if normalized_path == normalized_cwd:
        return ""
    prefix = normalized_cwd + "/"
    if normalized_path.startswith(prefix):
        return normalized_path[len(prefix) :]
    return normalized_path


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        # Malformed input — defer to normal permission flow.
        sys.exit(0)

    if not isinstance(payload, dict):
        sys.exit(0)

    tool_name = payload.get("tool_name")
    tool_input = payload.get("tool_input")

    role = payload.get("renmark_role") or "code-implementer"
    profile = PROFILES.get(role, PROFILES["code-implementer"])

    if tool_name not in ("Write", "Edit", "Bash"):
        sys.exit(0)

    if not isinstance(tool_input, dict):
        sys.exit(0)

    if tool_name == "Bash":
        command = tool_input.get("command")
        if not isinstance(command, str) or not command.strip():
            sys.exit(0)

        allowed_commands = profile.allowed_commands
        if not allowed_commands:
            sys.exit(0)

        first_token = command.strip().split()[0]
        command_name = Path(first_token).name

        if command_name in allowed_commands:
            output = {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "allow",
                    "permissionDecisionReason": (
                        f"command '{command_name}' matches {role} "
                        "allowed_commands"
                    ),
                }
            }
        else:
            output = {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": (
                        f"command '{command_name}' not in {role} "
                        f"allowed_commands: {allowed_commands}"
                    ),
                }
            }

        print(json.dumps(output))
        sys.exit(0)

    file_path = tool_input.get("file_path")
    if not file_path:
        sys.exit(0)

    cwd = tool_input.get("cwd") or payload.get("cwd")
    relative_path = _make_relative(file_path, cwd)

    allowed_targets = profile.allowed_targets
    globs = [g.strip() for g in allowed_targets.split(",") if g.strip()]

    matched = any(fnmatch.fnmatch(relative_path, glob) for glob in globs)

    if matched:
        output = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow",
                "permissionDecisionReason": (
                    f"path matches {role} allowed_targets"
                ),
            }
        }
    else:
        output = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": (
                    f"path does not match {role} allowed_targets: "
                    f"{allowed_targets}"
                ),
            }
        }

    print(json.dumps(output))
    sys.exit(0)


if __name__ == "__main__":
    main()

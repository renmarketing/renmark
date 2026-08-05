"""PROTOTYPE / SPIKE ONLY — not wired into `.claude/settings.json`, not used
by any renmark dispatch path; evidence artifact for Release 5 of the
`governed-orchestration-assurance` roadmap.

Implements Claude Code's `PreToolUse` hook contract, scoped to ONE agent
profile (`code-implementer`) from `renmark/subagent_profiles.py`. Reads a
single JSON payload from stdin describing a proposed tool call and prints
an `allow` / `deny` decision for `Write` / `Edit` calls whose `file_path`
does, or does not, match that profile's `allowed_targets` globs. Any other
tool call is passed through silently (no decision) so normal permission
flow applies.
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

    if tool_name not in ("Write", "Edit"):
        sys.exit(0)

    if not isinstance(tool_input, dict):
        sys.exit(0)

    file_path = tool_input.get("file_path")
    if not file_path:
        sys.exit(0)

    cwd = tool_input.get("cwd") or payload.get("cwd")
    relative_path = _make_relative(file_path, cwd)

    allowed_targets = PROFILES["code-implementer"].allowed_targets
    globs = [g.strip() for g in allowed_targets.split(",") if g.strip()]

    matched = any(fnmatch.fnmatch(relative_path, glob) for glob in globs)

    if matched:
        output = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow",
                "permissionDecisionReason": (
                    "path matches code-implementer allowed_targets"
                ),
            }
        }
    else:
        output = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": (
                    "path does not match code-implementer allowed_targets: "
                    f"{allowed_targets}"
                ),
            }
        }

    print(json.dumps(output))
    sys.exit(0)


if __name__ == "__main__":
    main()

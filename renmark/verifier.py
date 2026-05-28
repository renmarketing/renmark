"""Subprocess runner for verifier commands.

Each task in the plan specifies a verifier shell command. We run it via
`bash -c` from the repo root with a configurable timeout, capture combined
stdout+stderr, and return the exit code plus the tail of output (for use in
NIM retry prompts).
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class VerifierResult:
    exit_code: int
    output: str  # combined stdout+stderr
    tail: str  # last 50 lines of output, for retry prompts
    timed_out: bool

    @property
    def ok(self) -> bool:
        return self.exit_code == 0 and not self.timed_out


def run_verifier(
    command: str,
    *,
    cwd: str | Path,
    timeout_s: int = 60,
    tail_lines: int = 50,
) -> VerifierResult:
    if not command.strip():
        return VerifierResult(
            exit_code=2,
            output="empty verifier command",
            tail="empty verifier command",
            timed_out=False,
        )
    try:
        proc = subprocess.run(
            ["bash", "-c", command],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
    except subprocess.TimeoutExpired as e:
        partial = ""
        if e.stdout:
            partial += e.stdout if isinstance(e.stdout, str) else e.stdout.decode(errors="replace")
        if e.stderr:
            partial += e.stderr if isinstance(e.stderr, str) else e.stderr.decode(errors="replace")
        msg = f"[verifier timed out after {timeout_s}s]\n{partial}"
        return VerifierResult(
            exit_code=124,
            output=msg,
            tail=_tail(msg, tail_lines),
            timed_out=True,
        )

    combined = (proc.stdout or "") + (proc.stderr or "")
    return VerifierResult(
        exit_code=proc.returncode,
        output=combined,
        tail=_tail(combined, tail_lines),
        timed_out=False,
    )


def _tail(text: str, n: int) -> str:
    lines = text.splitlines()
    if len(lines) <= n:
        return text
    return "\n".join(lines[-n:])

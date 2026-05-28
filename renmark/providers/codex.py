"""Codex CLI executor — delegates a task to `codex exec` instead of NIM.

Codex is an agent: given a prompt, it plans and edits files itself. So
unlike the NIM executor (which just emits text we apply), the codex
executor invokes the CLI and verifies what it produced.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from ..parser import Task


class CodexError(RuntimeError):
    """Codex CLI not available, or exited non-zero."""


@dataclass
class CodexResult:
    exit_code: int
    output_tail: str  # last lines of codex stdout/stderr — for retry feedback
    changed_files: list[str]  # files in workspace that codex modified


def codex_available() -> bool:
    return shutil.which("codex") is not None


def _git_status_porcelain(repo: Path) -> list[str]:
    """Return list of paths with any change vs. HEAD (staged or unstaged)."""
    proc = subprocess.run(
        ["git", "-C", str(repo), "status", "--porcelain"],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        return []
    paths: list[str] = []
    for line in proc.stdout.splitlines():
        # Porcelain v1: 2-char status + space + path. Untracked starts with "??".
        if len(line) < 4:
            continue
        path = line[3:].strip()
        # Handle rename/copy: "R  oldpath -> newpath" — take new path.
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        paths.append(path.strip('"'))
    return paths


def build_codex_prompt(task: Task, repo: Path) -> str:
    """Compose an agent-style prompt for codex.

    Codex isn't a "emit only the file" model — it's an agent. So the
    prompt tells it the goal, the constraints, and the verifier it must
    satisfy.
    """
    mode_verb = "Create the file" if task.mode == "A" else "Modify the existing file"
    ctx_lines = []
    if task.context_files:
        ctx_lines.append("Read-only context files (you MAY read but MUST NOT modify):")
        for c in task.context_files:
            ctx_lines.append(f"  - {c}")
    ctx_block = "\n".join(ctx_lines) + "\n\n" if ctx_lines else ""

    return (
        f"You are an autonomous agent completing one task in a larger plan.\n\n"
        f"Goal: {mode_verb} `{task.target}`.\n\n"
        f"Specification:\n{task.spec}\n\n"
        f"Constraints — these are HARD requirements:\n"
        f"- Modify exactly one file: `{task.target}`. Do not create or edit any other file.\n"
        f"- Do not commit. Do not run git. Just edit the file.\n"
        f"- Do not install dependencies.\n"
        f"- Your work is considered complete when this command exits 0:\n"
        f"    {task.verifier}\n"
        f"- Run the verifier yourself if you want to check; "
        f"the orchestrator will run it after you finish.\n\n"
        f"{ctx_block}"
        f"Output: when done, just stop. The orchestrator reads the file from disk, "
        f"runs the verifier, and decides PASS/FAIL.\n"
    )


def run_codex_task(
    task: Task,
    repo: Path,
    *,
    timeout_s: int = 600,
    sandbox: str = "workspace-write",
    extra_args: list[str] | None = None,
) -> CodexResult:
    """Invoke `codex exec` for one task.

    Returns CodexResult with exit code, output tail, and changed-files
    detected via git status before/after.
    """
    if not codex_available():
        raise CodexError(
            "codex CLI not on PATH. Install it (npm i -g @openai/codex) or switch the task back to executor: nim."
        )

    prompt = build_codex_prompt(task, repo)

    cmd = [
        "codex",
        "exec",
        "--sandbox",
        sandbox,
        "--skip-git-repo-check",  # we already verified git ourselves
    ]
    if extra_args:
        cmd.extend(extra_args)
    # Pass prompt via stdin so very long specs don't hit shell-arg limits.
    cmd.append("-")

    try:
        proc = subprocess.run(
            cmd,
            input=prompt,
            cwd=str(repo),
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
    except subprocess.TimeoutExpired as e:
        partial = ""
        if e.stdout:
            partial += e.stdout if isinstance(e.stdout, str) else e.stdout.decode(errors="replace")  # type: ignore[unreachable]
        if e.stderr:
            partial += e.stderr if isinstance(e.stderr, str) else e.stderr.decode(errors="replace")  # type: ignore[unreachable]
        return CodexResult(
            exit_code=124,
            output_tail=f"[codex timed out after {timeout_s}s]\n{partial[-2000:]}",
            changed_files=_git_status_porcelain(repo),
        )

    combined = (proc.stdout or "") + (proc.stderr or "")
    tail = "\n".join(combined.splitlines()[-50:])
    return CodexResult(
        exit_code=proc.returncode,
        output_tail=tail,
        changed_files=_git_status_porcelain(repo),
    )


def check_only_target_modified(changed: list[str], target: str) -> tuple[bool, str]:
    """Codex sometimes modifies files outside the target. Reject those tasks.

    Returns (ok, reason). Both target and target-relative variants are accepted.
    """
    target_variants = {target, "./" + target}
    extras = [p for p in changed if p not in target_variants]
    if extras:
        return False, f"codex modified files beyond target: {extras}"
    return True, "ok"

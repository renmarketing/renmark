"""Codex CLI executor — delegates a task to `codex exec` instead of NIM.

Codex is an agent: given a prompt, it plans and edits files itself. So
unlike the NIM executor (which just emits text we apply), the codex
executor invokes the CLI and verifies what it produced.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from ..parser import Task


class CodexError(RuntimeError):
    """Codex CLI not available, or exited non-zero."""


@dataclass
class CodexResult:
    exit_code: int
    output_tail: str  # last lines of codex stdout/stderr — for retry feedback
    changed_files: list[str]  # files THIS task changed (post-minus-pre delta)
    # Pre-call porcelain snapshot, so the engine can tell which of this task's
    # changed_files were UNTRACKED before the task (delete-on-rollback) vs
    # tracked (checkout-on-rollback). Paths only — same normalization as
    # changed_files.
    pre_changed_files: list[str] = field(default_factory=list)


def codex_available() -> bool:
    return shutil.which("codex") is not None


def _git_status_porcelain(repo: Path) -> list[str]:
    """Return list of paths with any change vs. HEAD (staged or unstaged).

    Uses ``--porcelain -z`` (NUL-separated, machine format): paths are emitted
    verbatim — no surrounding quotes, no octal-escaping of unicode/space/control
    bytes. That keeps filenames like ``fünf ä.txt`` un-mangled, which the
    non-``-z`` form would render as ``"f\303\274nf \303\244.txt"`` and break the
    delta/lane/rollback path-matching downstream.

    ``--untracked-files=all`` lists untracked files INDIVIDUALLY instead of
    collapsing a new directory to ``dir/`` — without it, a task whose target
    lives in a brand-new directory reports ``out/`` instead of
    ``out/target.txt`` and judges out-of-lane against its own work.
    """
    proc = subprocess.run(
        ["git", "-C", str(repo), "status", "--porcelain", "-z", "--untracked-files=all"],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        return []
    return _parse_porcelain_z(proc.stdout)


def _parse_porcelain_z(raw: str) -> list[str]:
    """Parse ``git status --porcelain -z`` output into a list of paths.

    Records are NUL-separated (no trailing newline per entry). Each record is
    ``XY<space>path``; the leading status field is exactly 3 bytes (2 status
    chars + 1 space) so the path is ``record[3:]``.

    Rename/copy entries (status ``R`` or ``C`` in either column) are special:
    git emits the *new* path in the current record and the *original* path as a
    SEPARATE following NUL-terminated token. We take the new path and SKIP the
    original (it is not a change to attribute on its own).
    """
    tokens = raw.split("\0")
    # ``-z`` ends the stream with a trailing NUL → a final empty token; drop
    # any empties so they aren't mistaken for a record.
    tokens = [t for t in tokens if t != ""]
    paths: list[str] = []
    i = 0
    while i < len(tokens):
        rec = tokens[i]
        if len(rec) < 4:
            i += 1
            continue
        status = rec[:2]
        path = rec[3:]
        # Rename/copy: the ORIGINAL path follows as the next NUL-separated
        # token. Take the new path (already in `path`), skip the original.
        if "R" in status or "C" in status:
            i += 2  # consume this record AND the trailing original-path token
        else:
            i += 1
        paths.append(path)
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

    # Snapshot the working tree BEFORE the codex call. In a parallel wave,
    # sibling tasks have in-flight changes; without a pre-snapshot, repo-global
    # porcelain would attribute those to THIS task. The task's changed set is
    # the post-minus-pre delta, so siblings' files never look out-of-lane here.
    pre = _git_status_porcelain(repo)

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
        post = _git_status_porcelain(repo)
        return CodexResult(
            exit_code=124,
            output_tail=f"[codex timed out after {timeout_s}s]\n{partial[-2000:]}",
            changed_files=_delta(pre, post),
            pre_changed_files=pre,
        )

    combined = (proc.stdout or "") + (proc.stderr or "")
    tail = "\n".join(combined.splitlines()[-50:])
    post = _git_status_porcelain(repo)
    return CodexResult(
        exit_code=proc.returncode,
        output_tail=tail,
        changed_files=_delta(pre, post),
        pre_changed_files=pre,
    )


def _delta(pre: list[str], post: list[str]) -> list[str]:
    """Files changed by this task = those dirty AFTER but not BEFORE the call.

    A sibling task's in-flight file is in both pre and post, so it drops out of
    the delta and is never mistaken for this task's out-of-lane work.
    """
    before = set(pre)
    return [p for p in post if p not in before]


def check_only_target_modified(
    changed: list[str],
    target: str,
    *,
    sibling_targets: list[str] | None = None,
) -> tuple[bool, str]:
    """Codex sometimes modifies files outside the target. Reject those tasks.

    Returns (ok, reason). Both target and target-relative variants are accepted.

    ``sibling_targets`` are the OTHER tasks' targets in the same parallel wave.
    Even with the pre/post delta, a sibling's file can leak into this task's
    delta if the sibling created it during this task's call window; excluding
    the wave's declared targets keeps such races from tripping the lane check.
    Wave targets are guaranteed disjoint (dispatch.validate_wave), so excluding
    them can never mask a real over-write of this task's own target.
    """
    allowed = {target, "./" + target}
    for sib in sibling_targets or []:
        allowed.add(sib)
        allowed.add("./" + sib)
    extras = [p for p in changed if p not in allowed]
    if extras:
        return False, f"codex modified files beyond target: {extras}"
    return True, "ok"

"""Pluggable eval-runner seam + the shipped subprocess-command implementation.

The eval tier needs *some* way to turn a prompt into a model trajectory. That
capability is a SEAM: a single ``EvalRunner = Callable[[str], str]`` — given a
prompt string, return the model's output string.

Today the only shipped runner shells out to a user-configured command
(``RENMARK_EVAL_RUNNER_CMD`` / config; see ``renmark.config.eval_runner_cmd``),
e.g. ``claude -p``. That is ``build_subprocess_runner`` below.

THE SEAM (why this module exists): a *different* kind of runner — e.g. an
in-process agent-turn runner that drives a subagent directly — can be added
later by writing ANOTHER builder function here (say ``build_agent_turn_runner``)
that returns the same ``EvalRunner`` shape. Callers
(``renmark.behavior.build_subagent_runner`` and the CLI) depend only on the
``Callable[[str], str]`` contract and on ``resolve_eval_runner`` returning
``None`` when nothing is configured — so a new runner slots in with zero caller
changes. This module deliberately does NOT import ``renmark.behavior`` (that
would create an import cycle: behavior consumes this seam); it imports
``renmark.config`` normally.
"""

from __future__ import annotations

import shlex
import subprocess
from collections.abc import Callable
from pathlib import Path

from .. import config

# The seam. A runner takes a prompt and returns the model's output text.
EvalRunner = Callable[[str], str]

# stderr is truncated to this many chars in error messages — enough to see the
# failure, small enough to keep the orchestrator's context bounded.
_STDERR_CAP = 500


class EvalRunnerError(RuntimeError):
    """Eval runner mis-configured, or the runner command failed.

    Raised at build time for an empty command, and at call time for a command
    that is not on PATH, exits non-zero, or times out.
    """


def build_subprocess_runner(cmd: str, *, timeout: float = 120.0) -> EvalRunner:
    """Return an ``EvalRunner`` that runs ``cmd`` and feeds the prompt on stdin.

    ``cmd`` is split with ``shlex.split`` and executed with ``shell=False`` — no
    shell interpretation. This is the safer default for a command-execution
    surface: a plain command like ``claude -p`` still works, and anything that
    genuinely needs shell features (pipes, ``$VAR``, redirection) must be wrapped
    in a script that IS the command. The prompt is passed on stdin (``input``),
    and the runner returns the command's stdout.

    Raises ``EvalRunnerError`` (never returns silently) on:
      * a blank/empty ``cmd`` (nothing after ``shlex.split``) — at build time;
      * a malformed ``cmd`` that ``shlex.split`` cannot parse (e.g. an unbalanced
        quote) — at build time;
      * the command not being on PATH (``FileNotFoundError``);
      * any other launch failure (``OSError`` — e.g. ``PermissionError`` /
        ``IsADirectoryError`` when the command resolves to a non-executable
        path like ``/`` or ``.``);
      * a non-zero exit (message includes truncated stderr);
      * a timeout (``subprocess.TimeoutExpired``).
    """
    try:
        argv = shlex.split(cmd)
    except ValueError as e:
        raise EvalRunnerError(
            f"eval runner command is not parseable ({e}): {cmd!r}"
        ) from e
    if not argv:
        raise EvalRunnerError("eval runner command is empty after shlex.split")

    def _run(prompt: str) -> str:
        try:
            proc = subprocess.run(
                argv,
                input=prompt,
                text=True,
                capture_output=True,
                timeout=timeout,
                shell=False,
            )
        except FileNotFoundError as e:
            raise EvalRunnerError(
                f"eval runner command not found on PATH: {argv[0]!r}"
            ) from e
        except subprocess.TimeoutExpired as e:
            raise EvalRunnerError(
                f"eval runner command timed out after {timeout}s: {argv[0]!r}"
            ) from e
        except OSError as e:
            # Any other launch failure — e.g. PermissionError / IsADirectoryError
            # when the command resolves to a non-executable path like "/" or ".".
            # Wrap it so the module contract is uniformly EvalRunnerError.
            raise EvalRunnerError(
                f"eval runner command could not be launched ({e}): {argv[0]!r}"
            ) from e

        if proc.returncode != 0:
            stderr = (proc.stderr or "").strip()[:_STDERR_CAP]
            raise EvalRunnerError(
                f"eval runner command exited {proc.returncode}: {argv[0]!r}\n{stderr}"
            )
        return proc.stdout

    return _run


def resolve_eval_runner(repo: Path, model: str = "sonnet") -> EvalRunner | None:
    """Resolve the configured eval runner for ``repo``, or ``None``.

    Reads ``renmark.config.eval_runner_cmd(repo)``: when a command is configured
    (env ``RENMARK_EVAL_RUNNER_CMD`` or project config), return a subprocess
    runner for it; when unconfigured (``None``), return ``None`` so the caller
    can degrade gracefully (skip the eval tier).

    ``model`` is accepted but currently unused: it is part of the eventual
    host-injection signature (a future in-process agent-turn runner will pick a
    subagent model from it). Keeping it now means callers won't have to change
    signature when that runner lands — see the SEAM note in the module docstring.
    """
    cmd = config.eval_runner_cmd(repo)
    if cmd is None:
        return None
    return build_subprocess_runner(cmd)

"""Codex execution helpers: git rollback, lane-checking, and codex task dispatch.

Extracted from _engine.py to keep that module below the 1000-line threshold.
All logic is unchanged — this is a pure structural move.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from .. import memory as _memory
from ..parser import Task
from ..providers.codex import (
    CodexError,
    check_only_target_modified,
    codex_available,
    run_codex_task,
)
from ..recurrence import IssueObservation, RecurrenceDecision, observe_issue, pre_attempt
from ..state import (
    UsageRecord,
    append_usage,
    escalation_dir,
    now_iso,
)
from ..verifier import run_verifier


def _get_engine() -> Any:
    """Lazy accessor for _engine symbols (avoids circular import at module level)."""
    from . import _engine
    return _engine


def _GIT_LOCK() -> Any:
    return _get_engine()._GIT_LOCK


# ---------------------------------------------------------------------------
# Import shims — resolved lazily through _get_engine() to avoid the circular
# import that would arise from a module-level ``from ._engine import ...``
# (since _engine.py imports _execute_task_codex from this module).
# ---------------------------------------------------------------------------

def _git(*args: str, cwd: Path) -> Any:
    return _get_engine()._git(*args, cwd=cwd)


def _git_commit(cwd: Path, target: str, message: str, trailer: str) -> str:
    return _get_engine()._git_commit(cwd, target, message, trailer)  # type: ignore[no-any-return]


def _print(msg: str = "") -> None:
    _get_engine()._print(msg)


def _format_status_line(
    n: int, total: int, title: str, status: str, elapsed_s: float, tokens: int, sha_or_note: str
) -> str:
    return _get_engine()._format_status_line(  # type: ignore[no-any-return]
        n, total, title, status, elapsed_s, tokens, sha_or_note
    )


# ---------------------------------------------------------------------------
# Git rollback helpers
# ---------------------------------------------------------------------------

def _git_restore_target(cwd: Path, target: str) -> None:
    import threading as _threading  # noqa: F401 — used via _GIT_LOCK reference
    with _get_engine()._GIT_LOCK:
        _get_engine()._git("checkout", "--", target, cwd=cwd)


def _untracked_paths_locked(cwd: Path, paths: list[str]) -> set[str]:
    """Subset of ``paths`` that git does NOT track (no committed version).

    LOCK CONTRACT: the caller MUST already hold ``_GIT_LOCK``. Classification
    and the rollback that consumes it must run under a SINGLE lock acquisition
    (``_classify_and_rollback`` is the only intended caller) so a sibling thread
    cannot create/delete a file in the gap and flip a path between the
    tracked→checkout and untracked→delete arms. ``_GIT_LOCK`` is a plain
    ``threading.Lock`` (non-reentrant), so this helper must NEVER re-acquire it.

    A path git doesn't track is a newly-created file: ``git checkout -- <path>``
    is a no-op (returncode 0, nothing restored), so rollback must DELETE it
    instead. We ask git directly (``ls-files --error-unmatch``) rather than
    parsing porcelain status codes, which the changed-files list has stripped.
    """
    _engine = _get_engine()
    untracked: set[str] = set()
    for p in paths:
        norm = p[2:] if p.startswith("./") else p
        r = _engine._git("ls-files", "--error-unmatch", "--", norm, cwd=cwd)
        if r.returncode != 0:
            untracked.add(norm)
    return untracked


def _rollback_paths_locked(cwd: Path, paths: list[str], *, untracked_before: set[str]) -> None:
    """Restore ONLY the given paths — never ``git checkout -- .`` (whole tree),
    which would revert a sibling wave-task's in-flight work.

    LOCK CONTRACT: the caller MUST already hold ``_GIT_LOCK`` (see
    ``_classify_and_rollback``). Does NOT acquire the lock itself — ``_GIT_LOCK``
    is non-reentrant, and the classify→rollback sequence must be one atomic
    critical section.

    Mode-aware per path: a path that was UNTRACKED before the task can't be
    restored by checkout (git has no committed version), so it's deleted;
    tracked paths are checked-out.
    """
    _engine = _get_engine()
    if not paths:
        return
    for p in paths:
        norm = p[2:] if p.startswith("./") else p
        if norm in untracked_before or p in untracked_before:
            # Untracked → delete the file/dir codex created.
            cleaned = _engine._git("clean", "-fd", "--", norm, cwd=cwd)
            if cleaned.returncode != 0:
                # Fall back to a direct unlink if clean refused.
                fp = cwd / norm
                try:
                    if fp.is_file():
                        fp.unlink()
                except OSError:
                    pass
        else:
            co = _engine._git("checkout", "--", norm, cwd=cwd)
            if co.returncode != 0:
                _print(f"warning: rollback checkout failed for {norm}: {co.stderr.strip()[:120]}")


def _classify_and_rollback(cwd: Path, paths: list[str]) -> None:
    """Classify untracked-vs-tracked AND roll back, under ONE ``_GIT_LOCK``.

    Replaces the old two-acquisition pattern (``_untracked_paths`` then
    ``_rollback_paths``) which left a TOCTOU gap: a sibling thread could
    create or delete a file between the classification and the rollback,
    flipping a path's tracked/untracked status so rollback chose the wrong
    arm (checkout-ing a now-untracked file as a no-op, or cleaning a tracked
    one). Holding the lock across both makes the decision and the action
    atomic with respect to sibling git operations.
    """
    if not paths:
        return
    with _get_engine()._GIT_LOCK:
        untracked = _untracked_paths_locked(cwd, paths)
        _rollback_paths_locked(cwd, paths, untracked_before=untracked)


# Backwards-compatible standalone wrappers (each takes the lock itself). These
# are NOT used on the hot rollback path — that goes through _classify_and_rollback
# for a single atomic acquisition. They remain for callers/tests that exercise
# classification or rollback in isolation. Never chain them on the hot path: two
# acquisitions reintroduce the TOCTOU gap these helpers' _locked variants close.
def _untracked_paths(cwd: Path, paths: list[str]) -> set[str]:
    with _get_engine()._GIT_LOCK:
        return _untracked_paths_locked(cwd, paths)


def _rollback_paths(cwd: Path, paths: list[str], *, untracked_before: set[str]) -> None:
    with _get_engine()._GIT_LOCK:
        _rollback_paths_locked(cwd, paths, untracked_before=untracked_before)


def _judge_lane_and_rollback(
    cwd: Path,
    *,
    pre_changed_files: list[str],
    target: str,
    sibling_targets: list[str] | None,
) -> tuple[bool, str]:
    """Atomically snapshot → judge out-of-lane → roll back, under ONE ``_GIT_LOCK``.

    The codex subprocess has already finished (the lock is NOT held during it —
    that would serialize the parallel wave). Here we re-take the porcelain
    post-snapshot, recompute the post-minus-pre delta, run the lane check, and —
    if out of lane — classify + roll back this task's OWN extra paths, all in a
    single critical section. That closes the window where a sibling could
    interleave a git write between the lane judgment and the rollback (e.g.
    creating a file that the rollback then misclassifies, or committing one the
    judgment just saw).

    RESIDUAL WINDOW (inherent, not fixable here): a sibling writing DURING this
    task's codex subprocess cannot be attributed — porcelain-based detection
    only diffs the pre/post snapshots and the lock is necessarily released
    across the subprocess. The pre/post delta + sibling-target exclusion masks
    those siblings from THIS task's lane check; what it cannot do is detect a
    sibling's concurrent in-flight edit. Judgment+rollback themselves are now
    atomic.

    Returns ``(ok, reason)`` from the lane check. On ``ok`` nothing is rolled
    back. ``_GIT_LOCK`` is non-reentrant, so every git call inside MUST use the
    ``*_locked`` helpers (no nested acquisition).
    """
    from ..providers.codex import _delta, _git_status_porcelain

    sib = set(sibling_targets or [])
    with _get_engine()._GIT_LOCK:
        post = _git_status_porcelain(cwd)
        changed = _delta(pre_changed_files, post)
        ok, reason = check_only_target_modified(changed, target, sibling_targets=sibling_targets)
        if not ok:
            # Roll back EXTRAS only — never the task's own target (its fate is
            # the caller's decision: the FAIL/retry path rolls the target back
            # separately via _classify_and_rollback) and never sibling targets.
            skip = sib | {target}
            own_extras = [p for p in changed if (p[2:] if p.startswith("./") else p) not in skip]
            untracked = _untracked_paths_locked(cwd, own_extras)
            _rollback_paths_locked(cwd, own_extras, untracked_before=untracked)
    return ok, reason


# ---------------------------------------------------------------------------
# Codex execution helpers
# ---------------------------------------------------------------------------

_CODEX_RECURRENCE_CHECK = "codex-retry"
_CODEX_RECURRENCE_RULES = (
    "nonzero-executor-exit",
    "lane-violation",
    "verifier-failure",
)
_RECURRENCE_SIGNAL_LIMIT = 1_200


def _bounded_recurrence_signal(task: Task, signal: str) -> str:
    """Build bounded, in-memory-only input for recurrence fingerprinting."""
    verifier = str(task.verifier)
    if len(verifier) > 240:
        verifier = verifier[:240]
    if len(signal) > _RECURRENCE_SIGNAL_LIMIT:
        signal = signal[-_RECURRENCE_SIGNAL_LIMIT:]
    return f"verifier={verifier}\nsignal={signal}"


def _observe_codex_failure(
    repo: Path,
    task: Task,
    run_id: str,
    *,
    rule_id: str,
    signal: str,
) -> RecurrenceDecision:
    """Record one retry-eligible failure without persisting its raw signal."""
    return observe_issue(
        repo,
        IssueObservation(
            check=_CODEX_RECURRENCE_CHECK,
            rule_id=rule_id,
            target=task.target,
            title=f"Codex {rule_id}: {task.title}",
            summary_text=_bounded_recurrence_signal(task, signal),
            source="renmark.cli._codex_runner",
            run_id=run_id,
        ),
    )


def _pre_attempt_recurrence_guard(repo: Path, task: Task) -> RecurrenceDecision | None:
    """Return the first persisted recurrence guard blocking a Codex call."""
    for rule_id in _CODEX_RECURRENCE_RULES:
        decision = pre_attempt(
            repo,
            check=_CODEX_RECURRENCE_CHECK,
            rule_id=rule_id,
            target=task.target,
        )
        if decision is not None and decision.retry_blocked:
            return decision
    return None


def _recurrence_status_note(decision: RecurrenceDecision) -> str:
    """Render bounded evidence plus the required proactive remediation hint."""
    evidence = (
        f"repeated issue x{decision.occurrence_count} "
        f"key={decision.key[:12]} fingerprint={decision.fingerprint[:12]}"
    )
    detail = " | ".join(line.strip()[:100] for line in decision.summary_lines[:2] if line.strip())
    note = f"{evidence}; recommend patch or durable_guard"
    if detail:
        note = f"{note}; {detail}"
    return note[:320]

def _codex_fail_after_retries(
    task: Task,
    total: int,
    repo: Path,
    run_id: str,
    cfg: Any,
    retries_left: int,
    start: float,
    status_note: str,
    verifier_log: str,
    fail_code: str,
) -> tuple[bool, str, int, str]:
    """Print FAIL status and record escalation for a terminal codex failure.

    Called when retries are exhausted for exit-code failures, out-of-lane
    violations, or verifier failures. Returns the standard failure tuple.
    """
    _print(_format_status_line(task.index, total, task.title, "FAIL", time.monotonic() - start, 0, status_note))
    _record_escalation(
        repo, task, run_id, "codex",
        base_prompt="(see codex_output.log)",
        response="",
        verifier_log=verifier_log,
        retry_count=cfg.max_task_retries - retries_left,
        prompt_tokens=0,
        completion_tokens=0,
    )
    return False, fail_code, 0, ""


def _codex_fail_recurrence_guard(
    task: Task,
    total: int,
    repo: Path,
    run_id: str,
    cfg: Any,
    retries_left: int,
    start: float,
    decision: RecurrenceDecision,
    *,
    verifier_log: str | None = None,
) -> tuple[bool, str, int, str]:
    """Stop a repeated issue with bounded evidence before another Codex call."""
    note = _recurrence_status_note(decision)
    return _codex_fail_after_retries(
        task,
        total,
        repo,
        run_id,
        cfg,
        retries_left,
        start,
        note,
        verifier_log or note,
        "repeated_issue_guard",
    )


def _codex_verify_and_commit(
    vres: Any,
    task: Task,
    total: int,
    repo: Path,
    run_id: str,
    cfg: Any,
    retries_left: int,
    start: float,
    last_output_tail: str,
) -> tuple[bool | None, str, int, str]:
    """Handle the verifier result for a single codex attempt.

    If the verifier passes: commit, print PASS, return ``(True, "", 0, sha)``.

    If the verifier fails: roll back the target (mode-aware — deletes untracked
    targets, checks out tracked ones under one _GIT_LOCK), then:
    - Return ``(None, "", 0, "")`` sentinel when retries remain; caller
      decrements ``retries_left`` and continues the loop.
    - Return the failure tuple when retries are exhausted.
    """
    if vres.ok:
        sha = _git_commit(
            repo,
            task.target,
            message=f"[renmark] task {task.index}: {task.title}",
            trailer="Co-Authored-By: Codex-CLI <noreply@openai.com>",
        )
        _print(
            _format_status_line(
                task.index, total, task.title, "PASS", time.monotonic() - start, 0,
                f"→ {sha or '(no-commit)'} (codex)",
            )
        )
        return True, "", 0, sha

    # Verifier failed. Roll back before deciding to retry or fail.
    # _classify_and_rollback deletes untracked targets and checks out tracked
    # ones — classification + rollback under ONE lock (no TOCTOU gap).
    last_verifier_tail = vres.tail
    _classify_and_rollback(repo, [task.target])
    recurrence = _observe_codex_failure(
        repo,
        task,
        run_id,
        rule_id="verifier-failure",
        signal=f"exit_code={vres.exit_code}\n{last_verifier_tail}",
    )
    if recurrence.retry_blocked:
        return _codex_fail_recurrence_guard(
            task,
            total,
            repo,
            run_id,
            cfg,
            retries_left,
            start,
            recurrence,
            verifier_log=(
                f"verifier:\n{last_verifier_tail}\n\n"
                f"codex tail:\n{last_output_tail}"
            ),
        )
    if retries_left > 0:
        return None, "", 0, ""  # sentinel: retry

    return _codex_fail_after_retries(
        task, total, repo, run_id, cfg, retries_left, start,
        f"codex verifier exit {vres.exit_code} after retries",
        f"verifier:\n{last_verifier_tail}\n\ncodex tail:\n{last_output_tail}",
        "codex_verifier_failed",
    )


def _execute_task_codex(
    *,
    task: Task,
    repo: Path,
    run_id: str,
    cfg: Any,
    total: int,
    sibling_targets: list[str] | None = None,
) -> tuple[bool, str, int, str]:
    """Run a task via the Codex CLI instead of NIM.

    Codex is an agent: it writes files directly. The orchestrator only
    builds the prompt, invokes `codex exec`, post-checks that codex stayed
    in its lane (modified only `target`), runs the verifier, and commits.

    Token tracking: codex usage rolls up to OpenAI's billing dashboard, not
    here. We record a usage row with 0 tokens so `--usage` reflects that
    the task ran without polluting NIM token totals.
    """
    start = time.monotonic()
    if not codex_available():
        _print(_format_status_line(task.index, total, task.title, "FAIL", 0.0, 0, "codex CLI not on PATH"))
        _record_escalation(
            repo, task, run_id, "codex",
            base_prompt="(codex not available)",
            response="",
            verifier_log="codex CLI is not installed (npm i -g @openai/codex)",
            retry_count=0,
            prompt_tokens=0,
            completion_tokens=0,
        )
        return False, "codex_unavailable", 0, ""

    retries_left = cfg.max_task_retries
    last_output_tail = ""

    while True:
        recurrence_guard = _pre_attempt_recurrence_guard(repo, task)
        if recurrence_guard is not None:
            return _codex_fail_recurrence_guard(
                task, total, repo, run_id, cfg, retries_left, start, recurrence_guard
            )

        try:
            result = run_codex_task(task, repo, timeout_s=cfg.default_verifier_timeout_s * 10)
        except CodexError as e:
            _print(
                _format_status_line(task.index, total, task.title, "FAIL", time.monotonic() - start, 0, f"codex: {e}")
            )
            _record_escalation(
                repo, task, run_id, "codex",
                base_prompt="(codex error)",
                response="",
                verifier_log=str(e),
                retry_count=cfg.max_task_retries - retries_left,
                prompt_tokens=0,
                completion_tokens=0,
            )
            return False, "codex_error", 0, ""

        # Log a usage row so --usage shows the call. The attempt counter makes
        # the row idempotent on replay while still appending one row per genuine
        # retry (each retry decrements retries_left → higher attempt index).
        append_usage(
            repo,
            UsageRecord(
                ts=now_iso(), run_id=run_id, task_id=task.index, model="codex",
                prompt_tokens=0, completion_tokens=0,
                attempt=cfg.max_task_retries - retries_left,
            ),
        )
        last_output_tail = result.output_tail

        if result.exit_code != 0:
            recurrence = _observe_codex_failure(
                repo,
                task,
                run_id,
                rule_id="nonzero-executor-exit",
                signal=f"exit_code={result.exit_code}\n{result.output_tail}",
            )
            if recurrence.retry_blocked:
                return _codex_fail_recurrence_guard(
                    task,
                    total,
                    repo,
                    run_id,
                    cfg,
                    retries_left,
                    start,
                    recurrence,
                    verifier_log=result.output_tail,
                )
            if retries_left > 0:
                retries_left -= 1
                continue
            return _codex_fail_after_retries(
                task, total, repo, run_id, cfg, retries_left, start,
                f"codex exit {result.exit_code} after retries",
                result.output_tail,
                "codex_failed",
            )

        # Constrain codex: must have modified only the target file (sibling
        # wave-targets are excluded — they're another task's lane, not ours).
        # Re-snapshot → judge → roll back atomically under one _GIT_LOCK so a
        # sibling cannot interleave a git write between the judgment and the
        # rollback. The lock is NOT held during the codex subprocess above —
        # that would serialize the whole parallel wave. Rolls back ONLY this
        # task's own extra paths (never the whole tree, which would clobber
        # concurrent sibling work); the wave's siblings are left untouched.
        ok, reason = _judge_lane_and_rollback(
            repo,
            pre_changed_files=result.pre_changed_files,
            target=task.target,
            sibling_targets=sibling_targets,
        )
        if not ok:
            recurrence = _observe_codex_failure(
                repo,
                task,
                run_id,
                rule_id="lane-violation",
                signal=f"reason={reason}\n{result.output_tail}",
            )
            if recurrence.retry_blocked:
                return _codex_fail_recurrence_guard(
                    task,
                    total,
                    repo,
                    run_id,
                    cfg,
                    retries_left,
                    start,
                    recurrence,
                    verifier_log=f"{reason}\n\n{result.output_tail}",
                )
            if retries_left > 0:
                retries_left -= 1
                continue
            return _codex_fail_after_retries(
                task, total, repo, run_id, cfg, retries_left, start,
                f"codex out of lane: {reason[:40]}",
                f"{reason}\n\n{result.output_tail}",
                "codex_out_of_lane",
            )

        # Run verifier.
        vres = run_verifier(task.verifier, cwd=repo, timeout_s=task.verifier_timeout_s)
        outcome = _codex_verify_and_commit(
            vres, task, total, repo, run_id, cfg, retries_left, start, last_output_tail
        )
        if outcome[0] is None:
            retries_left -= 1
            continue
        return outcome  # type: ignore[return-value]


def _record_escalation(
    repo: Path,
    task: Task,
    run_id: str,
    model: str,
    *,
    base_prompt: str,
    response: str,
    verifier_log: str,
    retry_count: int,
    prompt_tokens: int,
    completion_tokens: int,
    escalated_to: str | None = None,
) -> None:
    d = escalation_dir(repo, task.index)
    (d / "prompt.txt").write_text(base_prompt, encoding="utf-8")
    (d / "response.txt").write_text(response, encoding="utf-8")
    (d / "verifier.log").write_text(verifier_log, encoding="utf-8")
    if task.mode == "B" and response.lstrip().startswith("--- "):
        (d / "diff.patch").write_text(response, encoding="utf-8")
    (d / "metadata.json").write_text(
        json.dumps(
            {
                "task_index": task.index,
                "title": task.title,
                "mode": task.mode,
                "target": task.target,
                "model": model,
                "run_id": run_id,
                "retry_count": retry_count,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "ts": now_iso(),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    if escalated_to is not None:
        _memory.log_escalation_decision(
            repo,
            task_index=task.index,
            from_exec=task.executor,
            to_exec=escalated_to,
            reason=verifier_log,
        )

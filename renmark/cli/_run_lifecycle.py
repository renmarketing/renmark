"""Run-bookkeeping cluster: resume setup, run-state anchors, exit handling.

Extracted from ``_engine.py`` as a pure structural move (target-blueprint.md
§1.1) — every function below is byte-identical in behavior to its previous
definition in ``_engine.py``, which re-exports them for backward compatibility.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from ..parser import Task
from ..state import (
    PauseState,
    clear_pause,
    clear_pipeline_state,
    completed_task_titles,
    now_iso,
    read_pause,
    usage_this_month,
    usage_today,
    write_pause,
    write_pipeline_state,
)

if TYPE_CHECKING:  # pragma: no cover - typing only
    from ._engine import Config


def _get_engine() -> Any:
    """Lazy accessor for _engine symbols (avoids circular import at module level)."""
    from . import _engine

    return _engine


def _print(msg: str = "") -> None:
    _get_engine()._print(msg)


def _setup_resume_state(repo: Path, tasks: list[Task]) -> set[int]:
    """Compute the set of already-committed task indices for --resume.

    Reads pause state and git log, cross-checks the raw done-set against the
    current live plan, prints warnings for orphaned indices, and returns only
    the safe-to-skip subset.
    """
    pause = read_pause(repo)
    if pause is None:
        _print("note: no PAUSED state found; running from start")
    else:
        _print(f"resuming run {pause.run_id}; last attempted task: {pause.last_task_index}")
    # Capture index AND commit title: the git-log scan is unbounded over the
    # whole repo history, so a bare index match proves nothing — any prior plan
    # that ever numbered a task N makes index N look "done" forever.
    done_titles = completed_task_titles(repo)
    raw_done = set(done_titles)
    # Cross-check: a git-log scan may include indices from a DIFFERENT plan
    # (reused task numbers, ``(task N)``-suffix side commits, etc.).
    # Silently skipping tasks that don't exist in the current plan is the
    # single most expensive observed failure — the ledger and git log must
    # be trusted, but ONLY for indices whose index AND title unambiguously
    # belong to THIS plan.
    done, ambiguous = _get_engine()._cross_check_skip_list(raw_done, tasks, done_titles)
    if ambiguous:
        _print(
            f"warning: skip-list cross-check found {len(ambiguous)} orphaned "
            f"index(es) {sorted(ambiguous)} not matching current plan "
            f"({len(tasks)} tasks).  These will NOT be silently skipped — "
            f"re-running to avoid false completions.  "
            f"(Likely cause: reused task numbers or commits from a different plan.)"
        )
    if done:
        _print(f"skipping already-committed tasks: {sorted(done)}")
    return done


def _print_run_summary(
    passed: list[int],
    failed_task: Task | None,
    budget_kind: str | None,
    needs_agent: list[int],
    tasks: list[Task],
    tokens_used: int,
    cfg: Config,
    repo: Path,
    skipped: list[int],
    waves: list[list[Task]],
) -> None:
    """Print the end-of-run summary table (pass/fail/skip counts, token usage, waves)."""
    _print("")
    parts = [
        f"{len(passed)}/{len(tasks)} passed",
        f"{1 if (failed_task or budget_kind) else 0} failed",
        f"{len(skipped)} skipped",
    ]
    if needs_agent:
        parts.append(f"{len(needs_agent)} needs-agent ({sorted(needs_agent)})")
    _print(", ".join(parts))
    today = usage_today(repo)
    # Token-gate honesty: codex usage rolls up to OpenAI's dashboard, recorded
    # here as 0 tokens — so for a codex-only run tokens_used stays 0 and the
    # RENMARK_MAX_TOKENS_PER_RUN gate is INERT (the time/task budgets are the
    # real gates). Printing "0 / 50000 (0.0%)" would falsely imply the token
    # gate is live. When nothing was metered locally, say so plainly instead.
    if tokens_used == 0:
        _print(
            f"Tokens this run: n/a (codex usage reported upstream) | Today: {today} | Month: {usage_this_month(repo)}"
        )
    else:
        _print(
            f"Tokens this run: {tokens_used} / {cfg.max_tokens_per_run} "
            f"({100 * tokens_used / max(cfg.max_tokens_per_run, 1):.1f}%) | "
            f"Today: {today} | Month: {usage_this_month(repo)}"
        )
    waves_count = len(waves)
    _print(f"Waves: {waves_count} (parallel-grouped from {len(tasks)} tasks)")


def _handle_run_exit(
    failed_task: Task | None,
    budget_kind: str | None,
    failure_kind: str | None,
    needs_agent: list[int],
    skipped: list[int],
    run_id: str,
    plan_path: str,
    repo: Path,
    tasks: list[Task],
) -> int:
    """Resolve the final exit code and write pause state if needed.

    Returns 0 on success (all tasks passed or needs-agent handoff),
    10 on pause (budget exhaustion or task failure).
    """
    # Budget/deadline exhaustion: NOT a success. Write an honest pause keyed to
    # the first skipped task and exit non-zero — never the "All tasks completed"
    # branch. Checked before the success branch so a tripped gate can't fall
    # through to exit 0.
    if budget_kind is not None and failed_task is None:
        first_skipped = min(skipped) if skipped else 0
        reason = "budget" if budget_kind == "token_budget" else "deadline"
        write_pause(
            repo,
            PauseState(
                run_id=run_id,
                plan_path=str(plan_path),
                last_task_index=first_skipped,
                reason=reason,
                ts=now_iso(),
            ),
        )
        write_pipeline_state(repo, current_phase="paused")
        _print(
            f"PAUSED ({reason}): {budget_kind} gate tripped with "
            f"{len(skipped)} task(s) unrun {sorted(skipped)}.\n"
            f"Resume with: renmark-execute --resume {plan_path}"
        )
        return 10

    if failed_task is None and not needs_agent:
        _get_engine()._git_tag(repo, f"renmark-run-{run_id}-end")
        _complete_clean_run(repo, run_id, plan_path, tasks)
        clear_pipeline_state(repo)
        clear_pause(repo)
        _print("All tasks completed.")
        return 0
    if failed_task is None and needs_agent:
        # A host-agent task has not run in this process, so this is a handoff
        # rather than a clean completion.  Keep both durable resume pointers
        # for the orchestrate skill that will dispatch it.
        first_needed = min(needs_agent)
        write_pause(
            repo,
            PauseState(
                run_id=run_id,
                plan_path=str(plan_path),
                last_task_index=first_needed,
                reason="needs_agent",
                ts=now_iso(),
            ),
        )
        write_pipeline_state(repo, current_phase="paused")
        _print(
            f"Note: tasks {sorted(needs_agent)} need Claude (opus/sonnet) dispatch "
            f"via the /renmark:orchestrate skill's Agent-tool path. "
            f"renmark-execute (CLI) doesn't dispatch Claude executors."
        )
        # We did not fail — orchestrate skill is expected to follow up.
        # Don't tag run-end yet; that's the skill's job after Agent tasks land.
        return 0

    # Failure path: write pause state and exit non-zero.
    # Both early-return branches above guarantee failed_task is non-None here.
    assert failed_task is not None
    write_pause(
        repo,
        PauseState(
            run_id=run_id,
            plan_path=str(plan_path),
            last_task_index=failed_task.index,
            reason=failure_kind or "unknown",
            ts=now_iso(),
        ),
    )
    write_pipeline_state(repo, current_phase="paused", add_failed_task=failed_task.index)
    _print(
        f"PAUSED at task {failed_task.index} ({failure_kind}). "
        f"Artifacts: .renmark/state/escalations/task-{failed_task.index}/\n"
        f"Resume with: renmark-execute --resume {plan_path}"
    )
    return 10


def _begin_run_state(
    repo: Path,
    plan_path: str,
    waves: list[list[Task]],
    run_id: str,
) -> None:
    """Persist a fresh, resumable runtime anchor before any task dispatch."""
    from .. import delivery_state as _delivery

    write_pipeline_state(
        repo,
        current_phase="orchestrate",
        current_plan=str(plan_path),
        wave_index=0,
        wave_total=len(waves),
        clear_tasks=True,
    )
    delivery = _delivery.read_delivery_state(repo)
    delivery.run_id = run_id
    delivery.loop_status = "in_progress"
    # A new execution invalidates any independent review attached to an older
    # run, even when that review had a clean/passed result.
    delivery.review_status = "pending"
    _delivery.write_delivery_state(repo, delivery)


def _complete_clean_run(repo: Path, run_id: str, plan_path: str, tasks: list[Task]) -> None:
    """Record the terminal workflow and delivery transitions for a clean run."""
    from .. import delivery_state as _delivery
    from .. import lifecycle as _lifecycle

    delivery = _delivery.read_delivery_state(repo)
    milestone_id = delivery.active_milestone_id or Path(plan_path).stem
    delivery.run_id = run_id
    # A clean executor run has completed its declared task verifiers, but has
    # not performed an independent review of this run.
    delivery.verification_status = "passed"
    delivery.review_status = "pending"
    delivery.loop_status = "passed"
    for task in tasks:
        delivery = _delivery.upsert_work_package(
            delivery,
            _delivery.WorkPackageSummary(
                package_id=f"task-{task.index}",
                milestone_id=milestone_id,
                title=task.title,
                status="passed",
                summary="completed by renmark-execute",
                owner="orchestrator",
                updated_at=now_iso(),
                artifact_ref=str(plan_path),
            ),
        )
    # Archive (not plain-write): every package upserted above is status="passed",
    # so this immediately compacts them into .renmark/state/delivery-archive.json
    # instead of leaving delivery.json's work_packages to accumulate run over
    # run — the same byte-budget class of bug fixed for provenance_events above,
    # now closed for work_packages too. archive_completed_work_packages already
    # calls write_delivery_state itself.
    _delivery.archive_completed_work_packages(repo, delivery)
    _lifecycle.write_lifecycle(repo, stage="created")

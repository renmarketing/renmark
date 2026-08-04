"""Wave-execution loop: per-task dispatch, ledger emission, and wave iteration.

Extracted from ``_engine.py`` as a pure structural move (target-blueprint.md
§1.1) — every function below is byte-identical in behavior to its previous
definition in ``_engine.py``, which re-exports them for backward compatibility.

Module-level names that live in ``_engine.py`` (and that tests monkeypatch
there, e.g. ``_execute_task`` / ``_r008_precheck``) are resolved at call time
through :func:`_get_engine` so the existing patch points keep working.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .. import task_tracking as _task_tracking
from ..ledger import DispatchIndependenceError as _DispatchIndependenceError
from ..ledger import WorkOrder as _LedgerWorkOrder
from ..ledger import WorkResult as _LedgerWorkResult
from ..ledger import append_ledger_event as _append_ledger_event
from ..ledger import check_dispatch_independence as _check_dispatch_independence
from ..ledger import emit_inspection_verdict as _emit_inspection_verdict
from ..parser import Task
from ..state import now_iso, write_pipeline_state
from ..verifier import run_verifier as _run_verifier

if TYPE_CHECKING:  # pragma: no cover - typing only
    from ._engine import Config

# R-0.4/WP-4: fixed dispatch identity for the deterministic verifier-derived
# inspector wired below. It is a constant precisely because it names a
# subsystem (this module's own verifier pass/fail check), not a per-task
# executor invocation — every real WorkResult's `dispatch_identity` varies
# by executor+order_id (see `_runner`), so the two can never coincidentally
# collide and `check_dispatch_independence` has a real structural distinction
# to enforce, not a coincidental one.
_INSPECTOR_DISPATCH_IDENTITY = "renmark-verifier"


def _get_engine() -> Any:
    """Lazy accessor for _engine symbols (avoids circular import at module level)."""
    from . import _engine

    return _engine


def _print(msg: str = "") -> None:
    _get_engine()._print(msg)


def _format_status_line(
    n: int,
    total: int,
    title: str,
    status: str,
    elapsed_s: float,
    tokens: int,
    sha_or_note: str,
) -> str:
    return _get_engine()._format_status_line(  # type: ignore[no-any-return]
        n, total, title, status, elapsed_s, tokens, sha_or_note
    )


@dataclass
class _WaveRunOutcome:
    """Aggregate result of running every wave of a plan."""

    tokens_used: int
    passed: list[int]
    skipped: list[int]
    needs_agent: list[int]
    failed_task: Task | None
    failure_kind: str | None
    budget_kind: str | None


def _prepare_waves(tasks: list[Task]) -> tuple[list[list[Task]] | None, str]:
    """Group tasks into waves for parallel execution and validate each wave.

    Tasks sharing a `parallel_group` run concurrently; defaults to one wave per
    task. Returns ``(waves, "")`` on success or ``(None, message)`` on an
    invalid wave.
    """
    from .. import dispatch as _dispatch

    try:
        waves = _dispatch.group_tasks_by_wave(tasks)
        for w in waves:
            _dispatch.validate_wave(w)
    except ValueError as e:
        return None, str(e)
    return waves, ""


def _create_parent_task(repo: Path, run_id: str, plan_path: str) -> str:
    """REQ-31: one native parent task per milestone (this plan run).

    Reused unchanged on resume — create_or_reuse_task is idempotent by task_id.
    Best-effort: a tracking-layer failure must never block a real dispatch.
    """
    parent_task_id = f"run-{run_id}"
    try:
        _task_tracking.create_or_reuse_task(
            repo,
            parent_task_id,
            title=f"Execute plan {plan_path}",
            role="orchestrator",
            scope=plan_path,
            verification_expectation="every dispatched task independently verified",
        )
        _task_tracking.mark_in_progress(repo, parent_task_id)
    except Exception:
        pass
    return parent_task_id


def _emit_work_order(repo: Path, task: Task, order_id: str) -> None:
    """R-0.3/WP-4: real WorkOrder emission point.

    This is the actual moment a task is handed to a live executor (via
    ``_execute_task`` → codex); order_id is ``{run_id}-{task_index}`` since
    tasks have no pre-existing dispatch uuid. A ledger write failure must never
    block the real dispatch, so it's best-effort/never-raising, same as the
    R-0.0 baseline-trace convention this module already follows.
    """
    try:
        _append_ledger_event(
            repo,
            _LedgerWorkOrder(
                order_id=order_id,
                task=task.spec or task.title,
                role=task.role or task.executor,
                file_scope=[task.target, *task.context_files],
                verifier=task.verifier,
            ),
            ts=now_iso(),
        )
    except Exception:
        pass


def _track_worker_dispatch(
    repo: Path,
    task: Task,
    *,
    worker_task_id: str,
    parent_task_id: str,
    dispatch_identity: str,
) -> None:
    """REQ-31: one native task per dispatch, reused unchanged on resume.

    ``mark_in_progress`` fires immediately before the real dispatch call —
    never after. Best-effort: tracking must never block dispatch.
    """
    try:
        _task_tracking.create_or_reuse_task(
            repo,
            worker_task_id,
            title=task.title or task.spec or f"task {task.index}",
            role=task.role or task.executor or "unknown",
            scope=task.target,
            verification_expectation=task.verifier,
            parent_id=parent_task_id,
            dispatch_identity=dispatch_identity,
        )
        _task_tracking.mark_in_progress(repo, worker_task_id)
    except Exception:
        pass


def _emit_work_result(
    repo: Path,
    task: Task,
    *,
    order_id: str,
    ok: bool,
    reason: str,
    dispatch_identity: str,
) -> None:
    """R-0.3/WP-4: real WorkResult emission point.

    The return from the live executor call, matched to the WorkOrder by
    order_id. R-0.4/WP-2: ``dispatch_identity`` records which real dispatch
    produced this result (executor + order_id, unique per task/run) so a later
    inspector can prove independence rather than assume it.
    """
    try:
        _append_ledger_event(
            repo,
            _LedgerWorkResult(
                order_id=order_id,
                status="complete" if ok else "failed",
                summary=reason,
                touched_files=[task.target] if ok else [],
                dispatch_identity=dispatch_identity,
            ),
            ts=now_iso(),
        )
    except Exception:
        pass


def _inspect_and_track(
    repo: Path,
    task: Task,
    *,
    run_id: str,
    order_id: str,
    worker_task_id: str,
    verify_task_id: str,
    parent_task_id: str,
    work_result_dispatch_identity: str,
    sha: str,
    reason: str,
) -> None:
    """R-0.4/WP-4b (bounded repair): real InspectionReport emission point.

    The verdict is derived from a FRESH, independently-rerun ``task.verifier``
    execution (a genuinely separate subprocess call, decoupled from the
    Worker's own verifier run inside ``_execute_task``/``_execute_task_codex``)
    rather than from the Worker's own already-known ``ok``/``reason`` variables
    — see 2026-08-01-r-0.4-wp6-independent-review.md Finding 3. This is a
    deterministic, read-only-by-convention re-check (this codebase's verifier
    commands are check/test commands, e.g. pytest/py_compile, not mutating
    ones), dispatched under a fixed deterministic-verifier identity that is
    structurally distinct from ``work_result_dispatch_identity`` (which always
    carries the task's own executor + order_id). The independence check runs
    UNWRAPPED so a genuine ``DispatchIndependenceError`` is a real, visible
    rejection — never silently swallowed. Only the ledger *write* is
    best-effort / never-raising, matching the WorkOrder/WorkResult convention
    above (a disk/IO failure must never block the pipeline).
    """
    try:
        _check_dispatch_independence(
            repo,
            work_result_dispatch_identity,
            _INSPECTOR_DISPATCH_IDENTITY,
        )
    except _DispatchIndependenceError as exc:
        _print(
            f"WARNING: inspection verdict rejected for {order_id} "
            f"(dispatch independence check failed): {exc}"
        )
        try:
            _task_tracking.record_blocker(
                repo, worker_task_id, f"dispatch independence check failed: {exc}"
            )
        except Exception:
            pass
    else:
        fresh_result = _run_verifier(
            task.verifier,
            cwd=repo,
            timeout_s=task.verifier_timeout_s,
        )
        try:
            _emit_inspection_verdict(
                repo,
                work_result_id=order_id,
                work_order_id=order_id,
                verdict="pass" if fresh_result.ok else "fail",
                evidence=[fresh_result.tail] if fresh_result.tail else [],
                inspector_dispatch_identity=_INSPECTOR_DISPATCH_IDENTITY,
                work_result_dispatch_identity=work_result_dispatch_identity,
                ts=now_iso(),
            )
        except Exception:
            pass

        # REQ-31: the native verification task is completed from the
        # SAME fresh, independently-rerun verifier result the ledger's
        # InspectionReport above uses — never from the worker's own
        # `ok`. Only once that verification task is `completed` does
        # `complete_worker_task` allow the worker task to complete; this
        # is the mechanical no-self-approval enforcement (REQ-31 rule 5),
        # reusing the same dispatch-identity independence check the
        # ledger's InspectionReport already relies on.
        try:
            _task_tracking.create_or_reuse_task(
                repo,
                verify_task_id,
                title=f"Verify task {task.index}",
                role="inspector",
                scope=task.target,
                verification_expectation=task.verifier,
                parent_id=parent_task_id,
                depends_on=(worker_task_id,),
                dispatch_identity=_INSPECTOR_DISPATCH_IDENTITY,
            )
            _task_tracking.mark_in_progress(repo, verify_task_id)
            _task_tracking.complete_task(
                repo,
                verify_task_id,
                artifact_path=f".renmark/state/wave-summaries/{run_id}",
                result_summary="pass" if fresh_result.ok else "fail",
            )
            if fresh_result.ok:
                _task_tracking.complete_worker_task(
                    repo,
                    worker_task_id,
                    verification_task_id=verify_task_id,
                    artifact_path=sha or task.target,
                    result_summary=reason,
                )
            else:
                _task_tracking.record_failure(
                    repo, worker_task_id, "independent verifier rerun failed"
                )
        except Exception:
            pass


def _run_waves(
    *,
    waves: list[list[Task]],
    tasks: list[Task],
    done: set[int],
    repo: Path,
    run_id: str,
    cfg: Config,
    deadline: float,
    parent_task_id: str,
) -> _WaveRunOutcome:
    """Run every wave of the plan, dispatching each wave's runnable tasks.

    Owns the per-run mutable bookkeeping (tokens, passed/skipped/needs-agent
    indices, failure and budget kinds) that the wave loop and its per-task
    runner share.
    """
    from .. import dispatch as _dispatch

    tokens_used = 0
    passed: list[int] = []
    failed_task: Task | None = None
    failure_kind: str | None = None
    skipped: list[int] = []
    needs_agent: list[int] = []  # tasks executor=opus/sonnet, skill must dispatch
    r008_warned: list[int] = []  # tasks that dispatched with missing R-008 fields

    # Holder for the current wave's task list, set per-wave below so the
    # runner can compute each task's sibling targets (for rollback isolation).
    current_wave: list[Task] = []

    def _runner(task: Task, _repo: Path) -> _dispatch.TaskResult:
        """Adapter: existing _execute_task tuple → dispatch.TaskResult."""
        # R-008 pre-dispatch checklist (lenient — warn, never block). This is
        # the real per-task dispatch call site: every task reaching _runner is
        # about to be handed to a live executor (_execute_task → codex).
        if _get_engine()._r008_precheck(task):
            r008_warned.append(task.index)
        sibling_targets = [t.target for t in current_wave if t.index != task.index]

        order_id = f"{run_id}-{task.index}"
        # `work_result_dispatch_identity` only depends on already-known
        # values (executor + order_id), so it's safe to compute here, before
        # dispatch, for the native worker task's `dispatch_identity` field —
        # the same identity the WorkResult ledger event below records.
        work_result_dispatch_identity = f"{task.executor or 'unknown'}:{order_id}"
        worker_task_id = f"task-{order_id}"
        verify_task_id = f"task-{order_id}-verify"

        _emit_work_order(_repo, task, order_id)
        _track_worker_dispatch(
            _repo,
            task,
            worker_task_id=worker_task_id,
            parent_task_id=parent_task_id,
            dispatch_identity=work_result_dispatch_identity,
        )

        ok, reason, used, sha = _get_engine()._execute_task(
            task=task,
            repo=_repo,
            run_id=run_id,
            cfg=cfg,
            remaining_token_budget=max(0, cfg.max_tokens_per_run - tokens_used),
            total=len(tasks),
            sibling_targets=sibling_targets,
        )

        _emit_work_result(
            _repo,
            task,
            order_id=order_id,
            ok=ok,
            reason=reason,
            dispatch_identity=work_result_dispatch_identity,
        )
        _inspect_and_track(
            _repo,
            task,
            run_id=run_id,
            order_id=order_id,
            worker_task_id=worker_task_id,
            verify_task_id=verify_task_id,
            parent_task_id=parent_task_id,
            work_result_dispatch_identity=work_result_dispatch_identity,
            sha=sha,
            reason=reason,
        )

        return _dispatch.TaskResult(
            task_index=task.index,
            executor=task.executor,
            status="passed" if ok else "failed",
            sha=sha,
            tokens_out=used,
            note=reason,
        )

    # Set when a wave-level budget/deadline gate trips. Unlike a per-task
    # failure, this is not tied to one task — it means "stop, out of budget".
    budget_kind: str | None = None

    def _skip_all_remaining(from_wave_idx: int) -> None:
        """Mark every not-done, not-yet-run task from this wave onward skipped.

        Without this the run only recorded the CURRENT wave's tasks as skipped,
        silently dropping later waves from the count and the pause state.
        """
        for later in waves[from_wave_idx:]:
            for t in later:
                if t.index in done or t.index in passed or t.index in skipped:
                    continue
                skipped.append(t.index)

    for wave_idx, wave in enumerate(waves):
        # Already-committed tasks (from --resume) just emit DONE lines.
        for t in wave:
            if t.index in done:
                _print(
                    _format_status_line(
                        t.index,
                        len(tasks),
                        t.title,
                        "DONE",
                        0.0,
                        0,
                        "(prev run)",
                    )
                )
                if t.index not in passed:
                    passed.append(t.index)

        runnable = [t for t in wave if t.index not in done]
        if not runnable or failed_task is not None:
            continue

        # Wave-level budget gates. Trip → record EVERY remaining task (this wave
        # and all later waves) as skipped, then break to the budget-pause path.
        if tokens_used >= cfg.max_tokens_per_run:
            budget_kind = "token_budget"
            _skip_all_remaining(wave_idx)
            break
        if time.monotonic() > deadline:
            budget_kind = "time_budget"
            _skip_all_remaining(wave_idx)
            break

        # Dispatch the wave. codex/haiku run in parallel; opus/sonnet are
        # marked `needs_agent` for the skill to handle via Agent tool.
        # Publish the wave so _runner can derive each task's sibling targets.
        current_wave = runnable
        try:
            wave_result = _dispatch.dispatch_wave(
                runnable,
                repo=repo,
                run_task=_runner,
            )
        except Exception as exc:  # pragma: no cover — defense in depth
            import traceback as _tb

            tb = _tb.format_exc()
            _print(f"ERROR dispatching wave: {type(exc).__name__}: {str(exc)[:100]}")
            for t in runnable:
                _get_engine()._record_escalation(
                    repo,
                    t,
                    run_id,
                    _get_engine()._choose_model(t, cfg),
                    base_prompt="(wave dispatch failed)",
                    response="",
                    verifier_log=tb,
                    retry_count=0,
                    prompt_tokens=0,
                    completion_tokens=0,
                )
            failed_task = runnable[0]
            failure_kind = "wave_dispatch_failed"
            break

        # Process results in task-index order so the log reads naturally.
        tokens_delta, failed_task, failure_kind = _process_wave_results(
            wave_result, runnable, tasks, repo, run_id, passed, needs_agent
        )
        tokens_used += tokens_delta
        for task_index in passed:
            write_pipeline_state(repo, add_completed_task=task_index)
        if failed_task is not None:
            write_pipeline_state(repo, add_failed_task=failed_task.index)
        elif needs_agent:
            # Do not advance past a host-agent handoff: pipeline_is_resumable
            # requires this wave to remain pending, including when it is the
            # final wave of the plan.
            write_pipeline_state(repo, current_phase="paused", wave_index=wave_idx)
            break
        else:
            write_pipeline_state(repo, wave_index=wave_idx + 1)

    return _WaveRunOutcome(
        tokens_used=tokens_used,
        passed=passed,
        skipped=skipped,
        needs_agent=needs_agent,
        failed_task=failed_task,
        failure_kind=failure_kind,
        budget_kind=budget_kind,
    )


def _process_wave_results(
    wave_result: Any,  # _dispatch.WaveResult — imported lazily inside execute_plan
    runnable: list[Task],
    tasks: list[Task],
    repo: Path,
    run_id: str,
    passed: list[int],
    needs_agent: list[int],
) -> tuple[int, Task | None, str | None]:
    """Process task results from a dispatched wave.

    Mutates ``passed`` and ``needs_agent`` in-place.
    Returns ``(tokens_delta, failed_task, failure_kind)``.
    """
    tokens_delta = 0
    failed_task: Task | None = None
    failure_kind: str | None = None

    for r in sorted(wave_result.tasks, key=lambda x: x.task_index):
        task_obj = next(t for t in runnable if t.index == r.task_index)
        if r.status == "passed":
            passed.append(r.task_index)
            tokens_delta += r.tokens_out
            _get_engine()._memory_log_outcome(repo, task_obj, "passed", run_id)
        elif r.status == "needs_agent":
            needs_agent.append(r.task_index)
            _print(
                _format_status_line(
                    r.task_index,
                    len(tasks),
                    task_obj.title,
                    "NEEDS-AGENT",
                    0.0,
                    0,
                    f"executor={r.executor} — orchestrate skill must dispatch via Agent tool",
                )
            )
        else:  # failed
            failed_task = task_obj
            failure_kind = r.note or "task_failed"
            tokens_delta += r.tokens_out
            _get_engine()._memory_log_outcome(repo, task_obj, "failed", run_id, note=r.note)
            break  # stop wave processing; outer loop also breaks via failed_task check

    return tokens_delta, failed_task, failure_kind

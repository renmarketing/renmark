"""renmark-execute CLI: orchestrates plan execution via Codex and Claude agents."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from .. import memory as _memory
from ..parser import PlanError, Task, parse_plan
from ..providers.codex import (
    CodexError,
    check_only_target_modified,
    codex_available,
    run_codex_task,
)
from ..state import (
    PauseState,
    UsageRecord,
    append_usage,
    clear_pause,
    completed_task_indices,
    escalation_dir,
    new_run_id,
    now_iso,
    read_pause,
    state_dir,
    usage_this_month,
    usage_today,
    write_pause,
)
from ..verifier import run_verifier
from .commands import (
    cmd_analytics,
    cmd_logs,
    cmd_review_package,
    cmd_roadmap,
    cmd_scan,
    cmd_task,
    cmd_task_brief,
    cmd_usage,
)


@dataclass
class Config:
    prefer_small_model: str
    big_model: str
    top_tier: str
    max_tokens_per_run: int
    max_minutes_per_run: int
    max_tasks_per_run: int
    max_task_retries: int
    default_verifier_timeout_s: int
    temperature: float
    max_output_tokens: int

    @classmethod
    def from_env(cls) -> Config:
        top_tier = os.environ.get("RENMARK_TOP_TIER", "").strip()
        if top_tier not in ("fable", "opus"):
            top_tier = ""  # defer to capabilities file resolution
        return cls(
            prefer_small_model=os.environ.get("RENMARK_PREFER_SMALL_MODEL", ""),
            big_model=os.environ.get("RENMARK_BIG_MODEL", ""),
            top_tier=top_tier,
            max_tokens_per_run=int(os.environ.get("RENMARK_MAX_TOKENS_PER_RUN", "50000")),
            max_minutes_per_run=int(os.environ.get("RENMARK_MAX_MINUTES_PER_RUN", "30")),
            max_tasks_per_run=int(os.environ.get("RENMARK_MAX_TASKS_PER_RUN", "15")),
            max_task_retries=int(os.environ.get("RENMARK_MAX_TASK_RETRIES", "2")),
            default_verifier_timeout_s=int(os.environ.get("RENMARK_DEFAULT_VERIFIER_TIMEOUT_S", "60")),
            temperature=float(os.environ.get("RENMARK_TEMPERATURE", "0.2")),
            max_output_tokens=int(os.environ.get("RENMARK_MAX_OUTPUT_TOKENS", "4096")),
        )


def _print(msg: str = "") -> None:
    print(msg, flush=True)


def _git(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True)


def _is_git_repo(cwd: Path) -> bool:
    return _git("rev-parse", "--is-inside-work-tree", cwd=cwd).returncode == 0


def _ensure_git_repo(cwd: Path) -> None:
    """Initialize a git repo (with identity + empty initial commit) if missing.

    Commits are required per-task, so the orchestrator can't run without one.
    Doing this silently is safer than asking the user to set up git manually.
    """
    _print(f"note: initializing git repo at {cwd} (commits required per task)")
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=str(cwd), check=True)
    name = _git("config", "user.name", cwd=cwd)
    if name.returncode != 0 or not name.stdout.strip():
        _git("config", "user.name", "renmark", cwd=cwd)
    email = _git("config", "user.email", cwd=cwd)
    if email.returncode != 0 or not email.stdout.strip():
        _git("config", "user.email", "renmark@local", cwd=cwd)
    subprocess.run(
        ["git", "commit", "-q", "--allow-empty", "-m", "init (renmark)"],
        cwd=str(cwd),
        check=True,
    )


# Serialize git operations across parallel task threads. Wave members write to
# disjoint files (validated by dispatch) so the apply/verify steps are safe to
# parallelize, but the git index is not — index lock contention would
# manifest as "Another git process seems to be running" errors.
import threading as _threading

_GIT_LOCK = _threading.Lock()


def _git_tag(cwd: Path, name: str) -> None:
    with _GIT_LOCK:
        _git("tag", "-f", name, cwd=cwd)


# When --no-commit is on, _git_commit becomes a no-op that returns a sentinel
# string. The skill (`/renmark:orchestrate`) is then responsible for batching
# commits per wave, in task-index order, after the wave finishes.
_NO_COMMIT_MODE = False


def _git_commit(cwd: Path, target: str, message: str, trailer: str) -> str:
    if _NO_COMMIT_MODE:
        return "(no-commit)"
    with _GIT_LOCK:
        add = _git("add", "--", target, cwd=cwd)
        if add.returncode != 0:
            return ""
        full = message + "\n\n" + trailer + "\n"
        commit = subprocess.run(
            ["git", "commit", "-q", "-F", "-"],
            cwd=str(cwd),
            input=full,
            capture_output=True,
            text=True,
        )
        if commit.returncode != 0:
            return ""
        sha = _git("rev-parse", "--short", "HEAD", cwd=cwd).stdout.strip()
        return sha


def _git_restore_target(cwd: Path, target: str) -> None:
    with _GIT_LOCK:
        _git("checkout", "--", target, cwd=cwd)


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
    untracked: set[str] = set()
    for p in paths:
        norm = p[2:] if p.startswith("./") else p
        r = _git("ls-files", "--error-unmatch", "--", norm, cwd=cwd)
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
    if not paths:
        return
    for p in paths:
        norm = p[2:] if p.startswith("./") else p
        if norm in untracked_before or p in untracked_before:
            # Untracked → delete the file/dir codex created.
            cleaned = _git("clean", "-fd", "--", norm, cwd=cwd)
            if cleaned.returncode != 0:
                # Fall back to a direct unlink if clean refused.
                fp = cwd / norm
                try:
                    if fp.is_file():
                        fp.unlink()
                except OSError:
                    pass
        else:
            co = _git("checkout", "--", norm, cwd=cwd)
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
    with _GIT_LOCK:
        untracked = _untracked_paths_locked(cwd, paths)
        _rollback_paths_locked(cwd, paths, untracked_before=untracked)


# Backwards-compatible standalone wrappers (each takes the lock itself). These
# are NOT used on the hot rollback path — that goes through _classify_and_rollback
# for a single atomic acquisition. They remain for callers/tests that exercise
# classification or rollback in isolation. Never chain them on the hot path: two
# acquisitions reintroduce the TOCTOU gap these helpers' _locked variants close.
def _untracked_paths(cwd: Path, paths: list[str]) -> set[str]:
    with _GIT_LOCK:
        return _untracked_paths_locked(cwd, paths)


def _rollback_paths(cwd: Path, paths: list[str], *, untracked_before: set[str]) -> None:
    with _GIT_LOCK:
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
    with _GIT_LOCK:
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


def _choose_model(task: Task, cfg: Config) -> str:
    return task.model or cfg.prefer_small_model


def _default_tokens_for_complexity(complexity: str) -> int:
    """Rough output-token estimate when the plan doesn't specify est_tokens."""
    return {"simple": 200, "medium": 1000, "hard": 4000}.get(complexity, 1000)


def _task_signature(task: Task) -> str:
    """Compact signature used in routing memory entries."""
    import fnmatch  # noqa: F401

    # Reduce target to a coarse glob: filename for short paths, directory prefix otherwise.
    parts = task.target.split("/")
    if len(parts) >= 2 and parts[0] in ("tests", "test"):
        glob = f"{parts[0]}/**"
    elif "." in parts[-1]:
        glob = f"*.{parts[-1].rsplit('.', 1)[1]}"
    else:
        glob = task.target
    return f"target={glob}, complexity={task.complexity}, mode={task.mode}"


def _cross_check_skip_list(
    done: set[int],
    tasks: list[Task],
) -> tuple[set[int], set[int]]:
    """Validate the resume skip-list against the CURRENT plan's task set.

    Background: completed_task_indices() scans git log with a loose regex that
    accepts ``(task N)``-suffix commits and any bracketed prefix.  When task
    numbers are reused across different plans, or when a previous run's commits
    bleed into the skip-list, a task that was never run in THIS plan can be
    silently marked "done" — the single most expensive observed failure mode.

    This function makes the check deterministic:
    - An index in ``done`` that corresponds to a valid task in the current plan
      is safe to skip (the task ran and committed in this plan or an equivalent
      one with the same numbering).
    - An index in ``done`` that does NOT appear in the current plan is ORPHANED:
      it came from a different plan (different task count, reused number, or a
      ``(task N)``-suffix side-commit).  Return it in the ``ambiguous`` set so
      the caller can warn and NOT silently skip real tasks.

    Args:
        done:  Indices the git-log scan reported as completed.
        tasks: Tasks from the current live plan (parse_plan result).

    Returns:
        (safe_to_skip, ambiguous) — two disjoint subsets of ``done``.
    """
    plan_indices = {t.index for t in tasks}
    safe_to_skip: set[int] = set()
    ambiguous: set[int] = set()
    for idx in done:
        if idx in plan_indices:
            safe_to_skip.add(idx)
        else:
            # This index has no counterpart in the current plan; treating it as
            # "done" would silently drop a real task.  Flag it rather than skip.
            ambiguous.add(idx)
    return safe_to_skip, ambiguous


def _memory_log_outcome(repo: Path, task: Task, outcome: str, run_id: str, note: str = "") -> None:
    """Append a routing.md entry after each task completes. Best-effort."""
    try:
        from .. import memory as _mem

        _mem.append_routing(
            repo,
            signature=_task_signature(task),
            executor=task.executor,
            outcome=outcome,
            run_id=run_id,
        )
        if outcome == "failed" and note:
            _mem.append_learning(
                repo,
                signal=f"task {task.index} failed on {task.executor}",
                observation=note[:200],
                source="run",
            )
    except Exception:
        pass  # memory updates are non-critical


def _format_status_line(
    n: int,
    total: int,
    title: str,
    status: str,
    elapsed_s: float,
    tokens: int,
    sha_or_note: str,
) -> str:
    return f"[{n}/{total}] {title[:46]:<46} {status:<6} {elapsed_s:>5.1f}s  {tokens:>5} tok  {sha_or_note}"


def execute_plan(
    plan_path: str,
    *,
    repo: Path,
    resume: bool = False,
    dry_run: bool = False,
    no_commit: bool = False,
) -> int:
    global _NO_COMMIT_MODE
    _NO_COMMIT_MODE = no_commit

    cfg = Config.from_env()
    try:
        tasks = parse_plan(plan_path)
    except PlanError as e:
        _print(f"ERROR parsing plan: {e}")
        return 2

    if len(tasks) > cfg.max_tasks_per_run:
        _print(
            f"ERROR: plan has {len(tasks)} tasks; max per run is "
            f"{cfg.max_tasks_per_run}. Split the plan into multiple files."
        )
        return 2

    if not dry_run and not _is_git_repo(repo):
        _ensure_git_repo(repo)

    # Determine which tasks are already done (resume support).
    done: set[int] = set()
    if resume:
        pause = read_pause(repo)
        if pause is None:
            _print("note: no PAUSED state found; running from start")
        else:
            _print(f"resuming run {pause.run_id}; last attempted task: {pause.last_task_index}")
        raw_done = completed_task_indices(repo)
        # Cross-check: a git-log scan may include indices from a DIFFERENT plan
        # (reused task numbers, ``(task N)``-suffix side commits, etc.).
        # Silently skipping tasks that don't exist in the current plan is the
        # single most expensive observed failure — the ledger and git log must
        # be trusted, but ONLY for indices that unambiguously belong to THIS plan.
        done, ambiguous = _cross_check_skip_list(raw_done, tasks)
        if ambiguous:
            _print(
                f"warning: skip-list cross-check found {len(ambiguous)} orphaned "
                f"index(es) {sorted(ambiguous)} not in current plan "
                f"({len(tasks)} tasks).  These will NOT be silently skipped — "
                f"re-running to avoid false completions.  "
                f"(Likely cause: reused task numbers or commits from a different plan.)"
            )
        if done:
            _print(f"skipping already-committed tasks: {sorted(done)}")

    run_id = new_run_id()
    state_dir(repo)  # ensure exists
    _print(
        f"renmark  plan: {plan_path}  run: {run_id}\n"
        f"model_default: {cfg.prefer_small_model}   "
        f"budget: {cfg.max_tokens_per_run} tok / {cfg.max_minutes_per_run} min"
    )

    if dry_run:
        from .. import capabilities as _caps
        from .. import dispatch as _d

        waves = _d.group_tasks_by_wave(tasks)
        _print(f"\n[DRY RUN] {len(tasks)} tasks in {len(waves)} wave(s):\n")
        # Cost estimates per executor — approximate $/kT (output tokens).
        cost_per_kt = {"haiku": 0.0001, "codex": 0.05, "sonnet": 0.003, "opus": 0.015, "fable": 0.030}
        total_tokens = 0
        total_cost = 0.0
        for w_idx, w in enumerate(waves, 1):
            wave_tag = "(parallel)" if len(w) > 1 else ""
            _print(f"  Wave {w_idx}: {len(w)} task(s) {wave_tag}")
            for t in w:
                mark = "DONE" if t.index in done else "TODO"
                tok = t.est_tokens or _default_tokens_for_complexity(t.complexity)
                # Resolve declared-tier fallback (fable→opus when undeclared) so
                # the preview prices and labels what will actually run.
                ex = _caps.effective_executor(t.executor, repo)
                ex_display = f"{t.executor}→{ex}" if ex != t.executor else ex
                # A downgraded executor (e.g. fable→opus) invalidates any prefilled
                # est_cost_usd — it was estimated at the wrong tier. Reprice from
                # the effective executor's rate so display matches what's charged.
                cost = t.est_cost_usd if ex == t.executor else None
                if cost is None:
                    # Infer from executor.
                    rate = cost_per_kt.get(ex, 0.0)
                    if "/" in ex:  # provider/model — assume openai-compatible mid-tier
                        rate = cost_per_kt.get("sonnet", 0.003)
                    cost = (tok / 1000.0) * rate
                cost_str = f"${cost:.3f}" if cost > 0 else "free"
                _print(
                    f"    [{mark}] task {t.index} {ex_display:<8} {t.complexity:<6} "
                    f"~{tok:>5} tok  {cost_str:>8}  → {t.target}  ({t.title})"
                )
                total_tokens += tok
                total_cost += cost
        _print(f"\n  TOTAL estimate: ~{total_tokens:,} tokens · ~${total_cost:.3f}")
        _print(
            "  (codex metered separately; haiku/sonnet/opus/fable bill to your Claude Code quota, ~10k overhead/task)"
        )
        return 0

    # Start anchor tag.
    _git_tag(repo, f"renmark-run-{run_id}-start")
    clear_pause(repo)

    deadline = time.monotonic() + (cfg.max_minutes_per_run * 60)
    tokens_used = 0
    passed: list[int] = []
    failed_task: Task | None = None
    failure_kind: str | None = None
    skipped: list[int] = []

    # Group tasks into waves for parallel execution. Tasks sharing a
    # `parallel_group` run concurrently; defaults to one wave per task.
    from .. import dispatch as _dispatch

    try:
        waves = _dispatch.group_tasks_by_wave(tasks)
        for w in waves:
            _dispatch.validate_wave(w)
    except ValueError as e:
        _print(f"ERROR: plan has invalid wave: {e}")
        return 2

    needs_agent: list[int] = []  # tasks executor=opus/sonnet, skill must dispatch

    # Holder for the current wave's task list, set per-wave below so the
    # runner can compute each task's sibling targets (for rollback isolation).
    current_wave: list[Task] = []

    def _runner(task: Task, _repo: Path) -> _dispatch.TaskResult:
        """Adapter: existing _execute_task tuple → dispatch.TaskResult."""
        sibling_targets = [t.target for t in current_wave if t.index != task.index]
        ok, reason, used, sha = _execute_task(
            task=task,
            repo=_repo,
            run_id=run_id,
            cfg=cfg,
            remaining_token_budget=max(0, cfg.max_tokens_per_run - tokens_used),
            total=len(tasks),
            sibling_targets=sibling_targets,
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
                _record_escalation(
                    repo,
                    t,
                    run_id,
                    _choose_model(t, cfg),
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
        for r in sorted(wave_result.tasks, key=lambda x: x.task_index):
            task_obj = next(t for t in runnable if t.index == r.task_index)
            if r.status == "passed":
                passed.append(r.task_index)
                tokens_used += r.tokens_out
                _memory_log_outcome(repo, task_obj, "passed", run_id)
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
                tokens_used += r.tokens_out
                _memory_log_outcome(repo, task_obj, "failed", run_id, note=r.note)
                break  # stop wave processing; outer loop also breaks via failed_task check

    # End-of-run summary.
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
        _print(
            f"PAUSED ({reason}): {budget_kind} gate tripped with "
            f"{len(skipped)} task(s) unrun {sorted(skipped)}.\n"
            f"Resume with: renmark-execute --resume {plan_path}"
        )
        return 10

    if failed_task is None and not needs_agent:
        _git_tag(repo, f"renmark-run-{run_id}-end")
        clear_pause(repo)
        _print("All tasks completed.")
        return 0
    if failed_task is None and needs_agent:
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
    _print(
        f"PAUSED at task {failed_task.index} ({failure_kind}). "
        f"Artifacts: .renmark/state/escalations/task-{failed_task.index}/\n"
        f"Resume with: renmark-execute --resume {plan_path}"
    )
    return 10


def _execute_task(
    *,
    task: Task,
    repo: Path,
    run_id: str,
    cfg: Config,
    remaining_token_budget: int,
    total: int,
    sibling_targets: list[str] | None = None,
) -> tuple[bool, str, int, str]:
    """Execute one task. Returns (ok, failure_reason_or_blank, tokens_used, sha_or_blank)."""
    # nim executor removed in v0.2.0; only codex reaches this function now.
    return _execute_task_codex(
        task=task, repo=repo, run_id=run_id, cfg=cfg, total=total, sibling_targets=sibling_targets
    )


def _execute_task_codex(
    *,
    task: Task,
    repo: Path,
    run_id: str,
    cfg: Config,
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
        _print(
            _format_status_line(
                task.index,
                total,
                task.title,
                "FAIL",
                0.0,
                0,
                "codex CLI not on PATH",
            )
        )
        _record_escalation(
            repo,
            task,
            run_id,
            "codex",
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
        try:
            result = run_codex_task(task, repo, timeout_s=cfg.default_verifier_timeout_s * 10)
        except CodexError as e:
            _print(
                _format_status_line(
                    task.index,
                    total,
                    task.title,
                    "FAIL",
                    time.monotonic() - start,
                    0,
                    f"codex: {e}",
                )
            )
            _record_escalation(
                repo,
                task,
                run_id,
                "codex",
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
                ts=now_iso(),
                run_id=run_id,
                task_id=task.index,
                model="codex",
                prompt_tokens=0,
                completion_tokens=0,
                attempt=cfg.max_task_retries - retries_left,
            ),
        )

        last_output_tail = result.output_tail

        if result.exit_code != 0:
            if retries_left > 0:
                retries_left -= 1
                continue
            _print(
                _format_status_line(
                    task.index,
                    total,
                    task.title,
                    "FAIL",
                    time.monotonic() - start,
                    0,
                    f"codex exit {result.exit_code} after retries",
                )
            )
            _record_escalation(
                repo,
                task,
                run_id,
                "codex",
                base_prompt="(see codex_output.log)",
                response="",
                verifier_log=result.output_tail,
                retry_count=cfg.max_task_retries - retries_left,
                prompt_tokens=0,
                completion_tokens=0,
            )
            return False, "codex_failed", 0, ""

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
            if retries_left > 0:
                retries_left -= 1
                continue
            _print(
                _format_status_line(
                    task.index,
                    total,
                    task.title,
                    "FAIL",
                    time.monotonic() - start,
                    0,
                    f"codex out of lane: {reason[:40]}",
                )
            )
            _record_escalation(
                repo,
                task,
                run_id,
                "codex",
                base_prompt="(see codex_output.log)",
                response="",
                verifier_log=f"{reason}\n\n{result.output_tail}",
                retry_count=cfg.max_task_retries - retries_left,
                prompt_tokens=0,
                completion_tokens=0,
            )
            return False, "codex_out_of_lane", 0, ""

        # Run verifier.
        vres = run_verifier(task.verifier, cwd=repo, timeout_s=task.verifier_timeout_s)
        if vres.ok:
            sha = _git_commit(
                repo,
                task.target,
                message=f"[renmark] task {task.index}: {task.title}",
                trailer="Co-Authored-By: Codex-CLI <noreply@openai.com>",
            )
            _print(
                _format_status_line(
                    task.index,
                    total,
                    task.title,
                    "PASS",
                    time.monotonic() - start,
                    0,
                    f"→ {sha or '(no-commit)'} (codex)",
                )
            )
            return True, "", 0, sha

        # Verifier failed. Roll back the target and retry. Mode-aware: a mode-A
        # task that just CREATED the target leaves it untracked, so a plain
        # `git checkout` is a no-op (returncode ignored) and the rejected
        # artifact would persist and poison the NEXT task's change detection.
        # _classify_and_rollback deletes untracked targets and checks out tracked
        # ones — classification + rollback under ONE lock (no TOCTOU gap).
        last_verifier_tail = vres.tail
        _classify_and_rollback(repo, [task.target])
        if retries_left > 0:
            retries_left -= 1
            continue

        _print(
            _format_status_line(
                task.index,
                total,
                task.title,
                "FAIL",
                time.monotonic() - start,
                0,
                f"codex verifier exit {vres.exit_code} after retries",
            )
        )
        _record_escalation(
            repo,
            task,
            run_id,
            "codex",
            base_prompt="(see codex_output.log)",
            response="",
            verifier_log=f"verifier:\n{last_verifier_tail}\n\ncodex tail:\n{last_output_tail}",
            retry_count=cfg.max_task_retries - retries_left,
            prompt_tokens=0,
            completion_tokens=0,
        )
        return False, "codex_verifier_failed", 0, ""


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
    import json

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


def _cmd_behavior(repo: Path, *, accept: bool, judge: bool) -> int:
    """Behavioral-suite lane: run the deterministic tier, record eval goldens, or judge FAILs.

    Bounded output (a few lines): one status line per case plus a totals line.

    Two honestly-labelled tiers (P8-v2):

    - Default ``--behavior``: the DETERMINISTIC tier ONLY. Calls ``behavior.run``
      without constructing or passing any live subagent runner, guaranteeing zero
      token spend and no network in CI. Exit non-zero on any FAIL/ERROR.
    - ``--behavior --accept``: the eval tier's live capture path. Constructs a live
      runner via ``behavior.build_subagent_runner`` and calls ``behavior.capture``
      per case to record its golden transcript (a deliberate live step).
    - ``--behavior --judge``: escalate deterministic FAILs to the LLM judge by
      passing ``judge=True`` AND the live runner into ``behavior.run``. Without it a
      deterministic FAIL prints a cost-noted OFFER (never auto-spends) unless headless.
    """
    from .. import behavior as _behavior
    from .. import config as _config

    behavioral_dir = str(repo / "tests" / "behavioral")

    if accept:
        return _behavior_accept(repo, behavioral_dir)

    headless = _config.is_headless(repo)

    # Default / --judge: deterministic tier. On the default path we pass NO live
    # runner, so run() spends zero tokens and touches no network. Only --judge
    # constructs the live runner and forwards it so a FAIL can escalate.
    runner = _behavior.build_subagent_runner(repo) if judge else None
    try:
        results = _behavior.run(
            behavioral_dir, judge=judge, repo=repo, subagent_runner=runner
        )
    except _behavior.BehaviorConfigError as exc:
        _print(f"ERROR loading behavioral cases: {exc}")
        return 2

    failed = 0
    offered = False
    for r in results:
        if r.status != "PASS":
            failed += 1
        msg = r.message[:60] if r.message else ""
        _print(f"  {r.status:<5} {r.skill}/{r.case:<24} {msg}")
        if r.judge_offered and not (judge or headless):
            offered = True

    _print(f"behavior: {len(results) - failed}/{len(results)} passed, {failed} failed")
    if offered:
        _print(
            f"  {failed} FAIL(s) eligible for LLM-judge review (~${_judge_est_cost():.2f}); "
            f"re-run with --behavior --judge to escalate. Not auto-invoked."
        )
    return 0 if failed == 0 else 10


def _behavior_accept(repo: Path, behavioral_dir: str) -> int:
    """Record eval-tier golden transcripts (the ``--behavior --accept`` path).

    A deliberate live step: constructs a live subagent runner via
    ``behavior.build_subagent_runner`` and calls ``behavior.capture`` for each
    case to write its ``snapshots/<golden_ref>.json`` golden. Bounded output.
    """
    from .. import behavior as _behavior

    try:
        cases = _behavior.load_cases(behavioral_dir)
    except _behavior.BehaviorConfigError as exc:
        _print(f"ERROR loading behavioral cases: {exc}")
        return 2

    runner = _behavior.build_subagent_runner(repo)
    recorded = 0
    failed = 0
    for case in cases:
        try:
            _behavior.capture(case, runner)
        except Exception as exc:  # a bad case shouldn't abort the whole capture
            failed += 1
            _print(f"  ERROR {case.skill}/{case.eval.golden_ref:<24} {type(exc).__name__}: {exc}")
            continue
        recorded += 1
        _print(f"  RECORD {case.skill}/{case.eval.golden_ref}")

    _print(f"behavior --accept: {recorded}/{len(cases)} golden transcripts recorded, {failed} failed")
    return 0 if failed == 0 else 10


def _judge_est_cost() -> float:
    """Lazy accessor for the judge's estimated per-call cost (avoids eager import)."""
    from ..judge import JUDGE_EST_COST_USD

    return JUDGE_EST_COST_USD


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    ap = argparse.ArgumentParser(prog="renmark-execute")
    ap.add_argument("plan", nargs="?", help="path to plan file")
    ap.add_argument("--resume", action="store_true", help="resume a paused run")
    ap.add_argument("--dry-run", action="store_true", help="parse plan, list tasks, exit")
    ap.add_argument("--usage", action="store_true", help="show usage and exit")
    ap.add_argument("--analytics", action="store_true", help="show build-health analytics and exit")
    ap.add_argument(
        "--roadmap",
        action="store_true",
        help="print task | llm | status | tokens | $ | commit table; also writes .renmark/memory/roadmap.md",
    )
    ap.add_argument("--logs", action="store_true", help="list recent .renmark/logs/ files for troubleshooting")
    ap.add_argument("--logs-n", type=int, default=10, help="how many logs to list (with --logs; default 10)")
    ap.add_argument("--scan", action="store_true", help="scan repo and print cron/schedule proposals; exit 0")
    ap.add_argument("--propose", action="store_true", help="(with --scan) include proposed cron entries")
    ap.add_argument("--emit-cron", action="store_true", help="(with --scan) emit cron block to stdout (read-only)")
    ap.add_argument(
        "--behavior",
        action="store_true",
        help=(
            "replay behavioral cases in tests/behavioral/ and print a bounded PASS/FAIL "
            "summary; deterministic (no spend). Exit non-zero on any FAIL/ERROR."
        ),
    )
    ap.add_argument(
        "--accept",
        action="store_true",
        help="(with --behavior) record eval-tier golden transcripts via the live capture path (deliberate spend)",
    )
    ap.add_argument(
        "--judge",
        action="store_true",
        help=(
            "(with --behavior) escalate deterministic FAILs to the LLM judge "
            "(opt-in spend); without it a FAIL prints a judge OFFER instead"
        ),
    )
    ap.add_argument(
        "--no-commit",
        action="store_true",
        help="apply tasks and run verifier but do not git-commit (skill batches commits per wave)",
    )
    ap.add_argument("--repo", default=".", help="repo root (default: current dir)")
    # v0.3.0: ad-hoc Codex task mode (G5/G11)
    ap.add_argument(
        "--task",
        metavar="SPEC_PATH",
        help=(
            "ad-hoc mode: read a task-spec markdown file, dispatch to Codex, "
            "write artifact to --output. Emits SubagentOutput JSON to stdout."
        ),
    )
    ap.add_argument("--output", metavar="ARTIFACT_PATH", help="(with --task) where Codex writes its artifact")
    # P11 — persisted proactivity toggle
    ap.add_argument(
        "--set-proactive",
        metavar="true|false",
        help=(
            "persist the auto-routing proactivity flag to .renmark/config.json "
            "('true' = route plain-English build/dev tasks through renmark automatically; "
            "'false' = skip auto-routing until re-enabled). Default: true."
        ),
    )
    # P10 — persisted headless toggle
    ap.add_argument(
        "--set-headless",
        metavar="true|false",
        help=(
            "persist the headless-mode flag to .renmark/config.json "
            "('true' = run non-interactively, suppressing interactive gates/menus; "
            "'false' = restore interactive behavior). Default: false."
        ),
    )
    # P4 file-handoff helpers — print ONLY the written path; diff/spec bytes stay out of orchestrator context
    ap.add_argument(
        "--task-brief",
        nargs=2,
        metavar=("PLAN_PATH", "TASK_INDEX"),
        help=(
            "extract task N's spec/brief from PLAN_PATH, write to "
            ".renmark/state/handoffs/<stem>-task-N.brief.md, print ONLY the path"
        ),
    )
    ap.add_argument(
        "--review-package",
        nargs=2,
        metavar=("BASE_REF", "HEAD_REF"),
        help=(
            "write git diff --stat + per-file diffs for BASE..HEAD to "
            ".renmark/state/handoffs/review-<base>-<head>.pkg.md, print ONLY the path"
        ),
    )
    args = ap.parse_args(argv)

    if (args.propose or args.emit_cron) and not args.scan:
        print("--propose/--emit-cron require --scan", file=sys.stderr)
        return 2
    if (args.accept or args.judge) and not args.behavior:
        print("--accept/--judge require --behavior", file=sys.stderr)
        return 2

    repo = Path(args.repo).resolve()

    if args.usage:
        return cmd_usage(repo)
    if args.analytics:
        return cmd_analytics(repo)
    if args.roadmap:
        return cmd_roadmap(repo)
    if args.logs:
        return cmd_logs(repo, n=args.logs_n)
    if args.scan:
        return cmd_scan(repo, propose=args.propose, emit_cron=args.emit_cron)
    if args.behavior:
        return _cmd_behavior(repo, accept=args.accept, judge=args.judge)
    if args.task:
        if not args.output:
            ap.error("--task requires --output ARTIFACT_PATH")
        return cmd_task(args.task, args.output, repo=repo)
    if args.set_proactive is not None:
        raw = args.set_proactive.strip().lower()
        if raw not in ("true", "false"):
            ap.error("--set-proactive expects 'true' or 'false'")
        from .. import config as _config
        value = raw == "true"
        _config.set_proactive(repo, value)
        state_str = "on" if value else "off"
        print(f"renmark: proactive auto-routing {state_str} ({repo}/.renmark/config.json)")
        return 0
    if args.set_headless is not None:
        raw = args.set_headless.strip().lower()
        if raw not in ("true", "false"):
            ap.error("--set-headless expects 'true' or 'false'")
        from .. import config as _config
        value = raw == "true"
        _config.set_headless(repo, value)
        state_str = "on" if value else "off"
        print(f"renmark: headless mode {state_str} ({repo}/.renmark/config.json)")
        return 0
    if args.task_brief:
        plan_path, task_index_str = args.task_brief
        try:
            task_index = int(task_index_str)
        except ValueError:
            ap.error(f"--task-brief TASK_INDEX must be an integer, got {task_index_str!r}")
        return cmd_task_brief(plan_path, task_index, repo=repo)
    if args.review_package:
        base_ref, head_ref = args.review_package
        return cmd_review_package(base_ref, head_ref, repo=repo)

    if not args.plan:
        ap.error(
            "plan path is required unless --usage / --analytics / --roadmap / --logs / "
            "--scan / --behavior / --task / --task-brief / --review-package / "
            "--set-proactive / --set-headless"
        )
    return execute_plan(
        args.plan,
        repo=repo,
        resume=args.resume,
        dry_run=args.dry_run,
        no_commit=args.no_commit,
    )


if __name__ == "__main__":
    sys.exit(main())

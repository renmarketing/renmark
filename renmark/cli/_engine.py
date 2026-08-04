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

from .. import __version__
from .. import task_tracking as _task_tracking  # noqa: F401  (re-export)
from ..ledger import DispatchIndependenceError as _DispatchIndependenceError  # noqa: F401
from ..ledger import WorkOrder as _LedgerWorkOrder  # noqa: F401
from ..ledger import WorkResult as _LedgerWorkResult  # noqa: F401
from ..ledger import append_ledger_event as _append_ledger_event  # noqa: F401
from ..ledger import check_dispatch_independence as _check_dispatch_independence  # noqa: F401
from ..ledger import emit_inspection_verdict as _emit_inspection_verdict  # noqa: F401
from ..parser import PlanError, Task, parse_plan
from ..providers.codex import codex_available as codex_available

# Re-exported `..state` names whose only callers moved to `_run_lifecycle.py`.
# Kept importable from `renmark.cli._engine` for backward compatibility;
# `as`-aliased to themselves so linters recognize the re-export as intentional.
from ..state import (
    PauseState as PauseState,
)
from ..state import (
    clear_pause,
    new_run_id,
    state_dir,
)
from ..state import (
    clear_pipeline_state as clear_pipeline_state,
)
from ..state import (
    completed_task_indices as completed_task_indices,
)
from ..state import (
    now_iso as now_iso,
)
from ..state import (
    read_pause as read_pause,
)
from ..state import (
    usage_this_month as usage_this_month,
)
from ..state import (
    usage_today as usage_today,
)
from ..state import (
    write_pause as write_pause,
)
from ..state import (
    write_pipeline_state as write_pipeline_state,
)
from ..verifier import run_verifier as _run_verifier  # noqa: F401
from ._codex_runner import (
    _classify_and_rollback as _classify_and_rollback,
)
from ._codex_runner import (
    _execute_task_codex,
)
from ._codex_runner import (
    _judge_lane_and_rollback as _judge_lane_and_rollback,
)
from ._codex_runner import (
    _rollback_paths as _rollback_paths,
)
from ._codex_runner import (
    _untracked_paths as _untracked_paths,
)

# Pure re-exports (no internal callers in this module) — kept for backward
# compatibility with external importers (e.g. tests importing
# `_delivery_state_line` directly from `renmark.cli._engine`). `as`-aliased
# to themselves so linters recognize the re-export as intentional.
from ._dispatch_flags import (
    _behavior_accept as _behavior_accept,
)
from ._dispatch_flags import (
    _bounded_delivery_state_display as _bounded_delivery_state_display,
)
from ._dispatch_flags import (
    _cmd_behavior as _cmd_behavior,
)
from ._dispatch_flags import (
    _delivery_state_line as _delivery_state_line,
)
from ._dispatch_flags import (
    _dispatch_agency_flags,
    _dispatch_compact_flags,
    _dispatch_handoff_flags,
    _dispatch_mode_read_flags,
    _dispatch_proactive_mode_flags,
    _dispatch_query_flags,
)
from ._dispatch_flags import (
    _judge_est_cost as _judge_est_cost,
)
from ._run_lifecycle import (
    _begin_run_state,
    _handle_run_exit,
    _print_run_summary,
    _setup_resume_state,
)
from ._run_lifecycle import (
    _complete_clean_run as _complete_clean_run,
)
from ._wave_loop import (
    _INSPECTOR_DISPATCH_IDENTITY as _INSPECTOR_DISPATCH_IDENTITY,
)
from ._wave_loop import (
    _create_parent_task,
    _prepare_waves,
    _run_waves,
)
from ._wave_loop import (
    _emit_work_order as _emit_work_order,
)
from ._wave_loop import (
    _emit_work_result as _emit_work_result,
)
from ._wave_loop import (
    _inspect_and_track as _inspect_and_track,
)
from ._wave_loop import (
    _process_wave_results as _process_wave_results,
)
from ._wave_loop import (
    _track_worker_dispatch as _track_worker_dispatch,
)
from ._wave_loop import (
    _WaveRunOutcome as _WaveRunOutcome,
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
        from .. import plan_lint as _plan_lint

        _mem.append_routing(
            repo,
            signature=_task_signature(task),
            executor=task.executor,
            outcome=outcome,
            run_id=run_id,
            escalation_reason=_plan_lint.escalation_reason_for(task),
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


def _handle_dry_run(tasks: list[Task], done: set[int], repo: Path) -> int:
    """Print the dry-run plan preview and return 0.

    Shows wave structure, per-task executor/cost estimates, and the
    deterministic subagent-justification gate (REQ-21) summary. Makes no
    model call and writes nothing to disk.
    """
    from .. import capabilities as _caps
    from .. import cost as _cost
    from .. import dispatch as _d
    from .. import subagent_gate as _sg

    waves = _d.group_tasks_by_wave(tasks)
    _print(f"\n[DRY RUN] {len(tasks)} tasks in {len(waves)} wave(s):\n")
    # Cost estimates per executor — approximate $/kT (output tokens).
    # Single source of truth: renmark.cost.PRICE_PER_KTOK (was a hand-duplicated
    # local dict that had drifted from it — codex was 0.05 here vs 0.03 there).
    cost_per_kt = _cost.PRICE_PER_KTOK
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
    # Deterministic subagent-justification gate (REQ-21) — enforced here in
    # the cost-preview code path, not just documented. Flags deterministic-
    # eligible / inline-able / unexplained-general-purpose spawns before dispatch.
    _print("  " + _sg.preview_line(_sg.challenge_plan(tasks)))
    return 0


def _r008_precheck(task: Task) -> list[str]:
    """R-008 pre-dispatch checklist gate — called immediately BEFORE a task is
    handed to a real dispatch runner (``_runner`` below), the actual per-task
    dispatch-orchestration call site in the CLI layer.

    Lenient mode only (Phase 1 of the migration path in
    ``.renmark/plans/r-0.2/dispatch-reason-budget-design.md`` §5/§8): missing
    fields NEVER block dispatch here — this wiring only makes the checklist
    live-but-non-blocking. Pre-R-0.2 ``Task`` objects carry none of the six
    R-008 fields yet, so today every dispatch is expected to warn; that is the
    intended, unchanged behavior for existing callers. Returns the list of
    missing field names (empty when fully satisfied) and prints one bounded
    warning line so the gap is surfaced, not silently discarded.
    """
    from .. import subagent_gate as _sg

    missing = _sg.enforce_r008_dispatch(task, strict=False)
    if missing:
        title = getattr(task, "title", "") or ""
        index = getattr(task, "index", "?")
        _print(
            f"R-008 WARN: task {index} ({title}) dispatched with missing "
            f"field(s): {', '.join(missing)} (lenient mode — not blocking)"
        )
    return missing


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
        done = _setup_resume_state(repo, tasks)

    run_id = new_run_id()
    state_dir(repo)  # ensure exists
    _print(
        f"renmark  plan: {plan_path}  run: {run_id}\n"
        f"model_default: {cfg.prefer_small_model}   "
        f"budget: {cfg.max_tokens_per_run} tok / {cfg.max_minutes_per_run} min"
    )

    if dry_run:
        return _handle_dry_run(tasks, done, repo)

    deadline = time.monotonic() + (cfg.max_minutes_per_run * 60)

    waves, wave_error = _prepare_waves(tasks)
    if waves is None:
        _print(f"ERROR: plan has invalid wave: {wave_error}")
        return 2

    # Persist the execution anchor only after the plan is fully validated, but
    # before any tag, pause clearing, or task dispatch can make the run live.
    _begin_run_state(repo, plan_path, waves, run_id)

    # Start anchor tag.
    _git_tag(repo, f"renmark-run-{run_id}-start")
    clear_pause(repo)

    parent_task_id = _create_parent_task(repo, run_id, plan_path)

    outcome = _run_waves(
        waves=waves,
        tasks=tasks,
        done=done,
        repo=repo,
        run_id=run_id,
        cfg=cfg,
        deadline=deadline,
        parent_task_id=parent_task_id,
    )

    # End-of-run summary.
    _print_run_summary(
        outcome.passed,
        outcome.failed_task,
        outcome.budget_kind,
        outcome.needs_agent,
        tasks,
        outcome.tokens_used,
        cfg,
        repo,
        outcome.skipped,
        waves,
    )

    return _handle_run_exit(
        outcome.failed_task,
        outcome.budget_kind,
        outcome.failure_kind,
        outcome.needs_agent,
        outcome.skipped,
        run_id,
        plan_path,
        repo,
        tasks,
    )


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




def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    ap = argparse.ArgumentParser(prog="renmark-execute")
    ap.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    ap.add_argument("plan", nargs="?", help="path to plan file")
    ap.add_argument("--resume", action="store_true", help="resume a paused run")
    ap.add_argument("--dry-run", action="store_true", help="parse plan, list tasks, exit")
    ap.add_argument("--usage", action="store_true", help="show usage and exit")
    ap.add_argument(
        "--delivery-state",
        action="store_true",
        help=(
            "print a bounded read-only delivery-state summary "
            "(delivery_mode, execution_policy, active milestone, contract/freshness, drift count)"
        ),
    )
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
        "--heartbeat",
        action="store_true",
        help="check pipeline heartbeat and emit any overdue notification; exit 0",
    )
    ap.add_argument(
        "--heartbeat-emit-cron",
        action="store_true",
        help="(with --heartbeat) emit cron install block to stdout",
    )
    ap.add_argument(
        "--heartbeat-auto-resume",
        action="store_true",
        help="(with --heartbeat) auto-resume the pipeline if overdue",
    )
    ap.add_argument(
        "--heartbeat-interval",
        type=int,
        default=30,
        metavar="MINUTES",
        help="(with --heartbeat) cron interval in minutes (default: 30)",
    )
    ap.add_argument(
        "--heartbeat-check-cron",
        action="store_true",
        help=(
            "check if the renmark-heartbeat cron entry is installed; "
            "prints 'installed' or 'not-installed'; exit 0"
        ),
    )
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
    # Persisted public delivery mode (agency|orchestrator).
    ap.add_argument(
        "--set-mode",
        choices=("agency", "orchestrator"),
        metavar="agency|orchestrator",
        help=(
            "persist the delivery mode to .renmark/state/delivery.json "
            "('agency' = owner-facing milestone delivery; "
            "'orchestrator' = bounded work-package execution)."
        ),
    )
    ap.add_argument(
        "--get-mode",
        action="store_true",
        help="print the persisted delivery mode and execution policy, then exit",
    )
    ap.add_argument(
        "--clear-mode",
        action="store_true",
        help="clear canonical and legacy delivery-mode state, then exit",
    )
    # Context hygiene gates
    ap.add_argument(
        "--compact-checkpoint",
        action="store_true",
        help=(
            "persist resume state to .renmark/state/compact_checkpoint.json "
            "and print the commands to run before /compact. "
            "Use when context is at 60%%+ to preserve state before compacting."
        ),
    )
    ap.add_argument(
        "--set-compact-gate-tokens",
        metavar="TOKENS",
        type=int,
        help=(
            "persist the compact-gate token threshold to .renmark/config.json. "
            "Default: 120000 (proxy for 60%% of the 200k window). "
            "0 = disable the compact gate. Negative values are rejected."
        ),
    )
    ap.add_argument(
        "--get-compact-gate-tokens",
        action="store_true",
        help="print the current compact-gate token threshold (0 = disabled)",
    )
    # Agency Mode state management
    ap.add_argument(
        "--agency-status",
        action="store_true",
        help="print current agency state (active/inactive, phase, milestone)",
    )
    ap.add_argument(
        "--activate-agency",
        action="store_true",
        help="activate Agency Mode in the current repo",
    )
    ap.add_argument(
        "--deactivate-agency",
        action="store_true",
        help="deactivate Agency Mode in the current repo",
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
    if (args.heartbeat_emit_cron or args.heartbeat_auto_resume or args.heartbeat_interval != 30) and not args.heartbeat:
        print("--heartbeat-emit-cron/--heartbeat-auto-resume/--heartbeat-interval require --heartbeat", file=sys.stderr)
        return 2
    if (args.accept or args.judge) and not args.behavior:
        print("--accept/--judge require --behavior", file=sys.stderr)
        return 2

    repo = Path(args.repo).resolve()

    for _handler in (
        lambda: _dispatch_query_flags(args, ap, repo),
        lambda: _dispatch_proactive_mode_flags(args, ap, repo),
        lambda: _dispatch_agency_flags(args, repo),
        lambda: _dispatch_mode_read_flags(args, ap, repo),
        lambda: _dispatch_compact_flags(args, repo),
        lambda: _dispatch_handoff_flags(args, ap, repo),
    ):
        _result = _handler()  # type: ignore[no-untyped-call]
        if _result is not None:
            return _result

    if not args.plan:
        ap.error(
            "plan path is required unless --usage / --delivery-state / --analytics / --roadmap / --logs / "
            "--scan / --heartbeat / --heartbeat-check-cron / --behavior / --task / --task-brief / --review-package / "
            "--set-proactive / --set-headless / --set-mode / --get-mode / --clear-mode"
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

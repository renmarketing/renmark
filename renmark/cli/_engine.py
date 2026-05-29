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
from ..apply import ApplyError, apply_mode_a, apply_mode_b
from ..parser import PlanError, Task, parse_plan
from ..prompts import mode_a_prompt, mode_b_prompt
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
from .commands import cmd_logs, cmd_roadmap, cmd_task, cmd_usage


@dataclass
class Config:
    prefer_small_model: str
    big_model: str
    max_tokens_per_run: int
    max_minutes_per_run: int
    max_tasks_per_run: int
    max_task_retries: int
    default_verifier_timeout_s: int
    temperature: float
    max_output_tokens: int

    @classmethod
    def from_env(cls) -> Config:
        return cls(
            prefer_small_model=os.environ.get("RENMARK_PREFER_SMALL_MODEL", ""),
            big_model=os.environ.get("RENMARK_BIG_MODEL", ""),
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


def _build_prompt(task: Task, repo: Path) -> str:
    if task.mode == "A":
        return mode_a_prompt(task)
    # Mode B: read current contents + context files.
    current = (repo / task.target).read_text(encoding="utf-8")
    context: dict[str, str] = {}
    for ctx in task.context_files:
        if ctx == task.target:
            continue
        p = repo / ctx
        if not p.is_file():
            raise ApplyError(f"context_file missing: {ctx}")
        context[ctx] = p.read_text(encoding="utf-8")
    return mode_b_prompt(task, current, context)


def _apply(task: Task, repo: Path, response: str) -> None:
    if task.mode == "A":
        apply_mode_a(repo, task.target, response)
    else:
        apply_mode_b(repo, task.target, response)


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
        done = completed_task_indices(repo)
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
        from .. import dispatch as _d

        waves = _d.group_tasks_by_wave(tasks)
        _print(f"\n[DRY RUN] {len(tasks)} tasks in {len(waves)} wave(s):\n")
        # Cost estimates per executor — approximate $/kT (output tokens).
        cost_per_kt = {"haiku": 0.0001, "codex": 0.05, "sonnet": 0.003, "opus": 0.015}
        total_tokens = 0
        total_cost = 0.0
        for w_idx, w in enumerate(waves, 1):
            wave_tag = "(parallel)" if len(w) > 1 else ""
            _print(f"  Wave {w_idx}: {len(w)} task(s) {wave_tag}")
            for t in w:
                mark = "DONE" if t.index in done else "TODO"
                tok = t.est_tokens or _default_tokens_for_complexity(t.complexity)
                ex = t.executor
                cost = t.est_cost_usd
                if cost is None:
                    # Infer from executor.
                    rate = cost_per_kt.get(ex, 0.0)
                    if "/" in ex:  # provider/model — assume openai-compatible mid-tier
                        rate = cost_per_kt.get("sonnet", 0.003)
                    cost = (tok / 1000.0) * rate
                cost_str = f"${cost:.3f}" if cost > 0 else "free"
                _print(
                    f"    [{mark}] task {t.index} {ex:<8} {t.complexity:<6} "
                    f"~{tok:>5} tok  {cost_str:>8}  → {t.target}  ({t.title})"
                )
                total_tokens += tok
                total_cost += cost
        _print(f"\n  TOTAL estimate: ~{total_tokens:,} tokens · ~${total_cost:.3f}")
        _print("  (codex metered separately; haiku/sonnet/opus bill to your Claude Code quota, ~10k overhead/task)")
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

    def _runner(task: Task, _repo: Path) -> _dispatch.TaskResult:
        """Adapter: existing _execute_task tuple → dispatch.TaskResult."""
        ok, reason, used, sha = _execute_task(
            task=task,
            repo=_repo,
            run_id=run_id,
            cfg=cfg,
            remaining_token_budget=max(0, cfg.max_tokens_per_run - tokens_used),
            total=len(tasks),
        )
        return _dispatch.TaskResult(
            task_index=task.index,
            executor=task.executor,
            status="passed" if ok else "failed",
            sha=sha,
            tokens_out=used,
            note=reason,
        )

    for wave in waves:
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

        # Wave-level budget gates.
        if tokens_used >= cfg.max_tokens_per_run:
            failure_kind = "token_budget"
            for t in runnable:
                skipped.append(t.index)
            break
        if time.monotonic() > deadline:
            failure_kind = "time_budget"
            for t in runnable:
                skipped.append(t.index)
            break

        # Dispatch the wave. codex/haiku run in parallel; opus/sonnet are
        # marked `needs_agent` for the skill to handle via Agent tool.
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
        f"{1 if failed_task else 0} failed",
        f"{len(skipped)} skipped",
    ]
    if needs_agent:
        parts.append(f"{len(needs_agent)} needs-agent ({sorted(needs_agent)})")
    _print(", ".join(parts))
    today = usage_today(repo)
    _print(
        f"Tokens this run: {tokens_used} / {cfg.max_tokens_per_run} "
        f"({100 * tokens_used / max(cfg.max_tokens_per_run, 1):.1f}%) | "
        f"Today: {today} | Month: {usage_this_month(repo)}"
    )
    waves_count = len(waves)
    _print(f"Waves: {waves_count} (parallel-grouped from {len(tasks)} tasks)")

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
) -> tuple[bool, str, int, str]:
    """Execute one task. Returns (ok, failure_reason_or_blank, tokens_used, sha_or_blank)."""
    # nim executor removed in v0.2.0; only codex reaches this function now.
    return _execute_task_codex(task=task, repo=repo, run_id=run_id, cfg=cfg, total=total)


def _execute_task_codex(
    *,
    task: Task,
    repo: Path,
    run_id: str,
    cfg: Config,
    total: int,
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

        # Log a usage row so --usage shows the call.
        append_usage(
            repo,
            UsageRecord(
                ts=now_iso(),
                run_id=run_id,
                task_id=task.index,
                model="codex",
                prompt_tokens=0,
                completion_tokens=0,
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

        # Constrain codex: must have modified only the target file.
        ok, reason = check_only_target_modified(result.changed_files, task.target)
        if not ok:
            # Roll back everything codex did and either retry or escalate.
            subprocess.run(["git", "-C", str(repo), "checkout", "--", "."], capture_output=True)
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(repo),
                    "clean",
                    "-fd",
                    "--",
                    *(p for p in result.changed_files if p != task.target),
                ],
                capture_output=True,
            )
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

        # Verifier failed. Roll back target and retry.
        last_verifier_tail = vres.tail
        subprocess.run(["git", "-C", str(repo), "checkout", "--", task.target], capture_output=True)
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


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    ap = argparse.ArgumentParser(prog="renmark-execute")
    ap.add_argument("plan", nargs="?", help="path to plan file")
    ap.add_argument("--resume", action="store_true", help="resume a paused run")
    ap.add_argument("--dry-run", action="store_true", help="parse plan, list tasks, exit")
    ap.add_argument("--usage", action="store_true", help="show usage and exit")
    ap.add_argument(
        "--roadmap",
        action="store_true",
        help="print task | llm | status | tokens | $ | commit table; also writes .renmark/memory/roadmap.md",
    )
    ap.add_argument("--logs", action="store_true", help="list recent .renmark/logs/ files for troubleshooting")
    ap.add_argument("--logs-n", type=int, default=10, help="how many logs to list (with --logs; default 10)")
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
    args = ap.parse_args(argv)

    repo = Path(args.repo).resolve()

    if args.usage:
        return cmd_usage(repo)
    if args.roadmap:
        return cmd_roadmap(repo)
    if args.logs:
        return cmd_logs(repo, n=args.logs_n)
    if args.task:
        if not args.output:
            ap.error("--task requires --output ARTIFACT_PATH")
        return cmd_task(args.task, args.output, repo=repo)

    if not args.plan:
        ap.error("plan path is required unless --usage / --roadmap / --logs / --task")
    return execute_plan(
        args.plan,
        repo=repo,
        resume=args.resume,
        dry_run=args.dry_run,
        no_commit=args.no_commit,
    )


if __name__ == "__main__":
    sys.exit(main())

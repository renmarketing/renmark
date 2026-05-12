"""nim-execute CLI: orchestrates plan execution against NVIDIA NIM."""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from .apply import ApplyError, apply_mode_a, apply_mode_b
from .providers.codex import (
    CodexError,
    check_only_target_modified,
    codex_available,
    run_codex_task,
)
from .providers.nim import (
    NIMAuthError,
    NIMClient,
    NIMError,
    NIMQuotaError,
    NIMRateLimitError,
    NIMResponse,
)
from .parser import PlanError, Task, parse_plan
from .prompts import format_reminder_prompt, mode_a_prompt, mode_b_prompt, retry_prompt
from .state import (
    PauseState,
    UsageRecord,
    append_usage,
    clear_pause,
    completed_task_indices,
    escalation_dir,
    new_run_id,
    now_iso,
    read_pause,
    read_usage,
    state_dir,
    usage_this_month,
    usage_today,
    write_pause,
)
from .verifier import run_verifier


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
    def from_env(cls) -> "Config":
        return cls(
            prefer_small_model=os.environ.get(
                "NIM_PREFER_SMALL_MODEL", "mistralai/codestral-22b-instruct-v0.1"
            ),
            big_model=os.environ.get(
                "NIM_BIG_MODEL", "mistralai/mistral-large-3-675b-instruct-2512"
            ),
            max_tokens_per_run=int(os.environ.get("NIM_MAX_TOKENS_PER_RUN", "50000")),
            max_minutes_per_run=int(os.environ.get("NIM_MAX_MINUTES_PER_RUN", "30")),
            max_tasks_per_run=int(os.environ.get("NIM_MAX_TASKS_PER_RUN", "15")),
            max_task_retries=int(os.environ.get("NIM_MAX_TASK_RETRIES", "2")),
            default_verifier_timeout_s=int(
                os.environ.get("NIM_DEFAULT_VERIFIER_TIMEOUT_S", "60")
            ),
            temperature=float(os.environ.get("NIM_TEMPERATURE", "0.2")),
            max_output_tokens=int(os.environ.get("NIM_MAX_OUTPUT_TOKENS", "4096")),
        )


def _print(msg: str = "") -> None:
    print(msg, flush=True)


def _git(*args: str, cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args], cwd=str(cwd), capture_output=True, text=True
    )


def _is_git_repo(cwd: Path) -> bool:
    return _git("rev-parse", "--is-inside-work-tree", cwd=cwd).returncode == 0


def _ensure_git_repo(cwd: Path) -> None:
    """Initialize a git repo (with identity + empty initial commit) if missing.

    Commits are required per-task, so the orchestrator can't run without one.
    Doing this silently is safer than asking the user to set up git manually.
    """
    _print(f"note: initializing git repo at {cwd} (commits required per task)")
    subprocess.run(
        ["git", "init", "-q", "-b", "main"], cwd=str(cwd), check=True
    )
    name = _git("config", "user.name", cwd=cwd)
    if name.returncode != 0 or not name.stdout.strip():
        _git("config", "user.name", "nim-execute", cwd=cwd)
    email = _git("config", "user.email", cwd=cwd)
    if email.returncode != 0 or not email.stdout.strip():
        _git("config", "user.email", "nim-execute@local", cwd=cwd)
    subprocess.run(
        ["git", "commit", "-q", "--allow-empty", "-m", "init (nim-execute)"],
        cwd=str(cwd), check=True,
    )


def _git_tag(cwd: Path, name: str) -> None:
    _git("tag", "-f", name, cwd=cwd)


def _git_commit(cwd: Path, target: str, message: str, trailer: str) -> str:
    add = _git("add", "--", target, cwd=cwd)
    if add.returncode != 0:
        return ""
    full = message + "\n\n" + trailer + "\n"
    commit = subprocess.run(
        ["git", "commit", "-q", "-F", "-"],
        cwd=str(cwd), input=full, capture_output=True, text=True,
    )
    if commit.returncode != 0:
        return ""
    sha = _git("rev-parse", "--short", "HEAD", cwd=cwd).stdout.strip()
    return sha


def _git_restore_target(cwd: Path, target: str) -> None:
    _git("checkout", "--", target, cwd=cwd)


def _choose_model(task: Task, cfg: Config) -> str:
    return task.model or cfg.prefer_small_model


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
    n: int, total: int, title: str, status: str, elapsed_s: float,
    tokens: int, sha_or_note: str,
) -> str:
    return (
        f"[{n}/{total}] {title[:46]:<46} {status:<6} "
        f"{elapsed_s:>5.1f}s  {tokens:>5} tok  {sha_or_note}"
    )


def execute_plan(
    plan_path: str, *, repo: Path, resume: bool = False, dry_run: bool = False,
) -> int:
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

    if not dry_run:
        if not os.environ.get("NVIDIA_NIM_API_KEY"):
            _print(
                "ERROR: NVIDIA_NIM_API_KEY not set.\n"
                "Either export it in your shell, or create a .env file in "
                f"{repo} with:\n  NVIDIA_NIM_API_KEY=nvapi-..."
            )
            return 3
        if not _is_git_repo(repo):
            _ensure_git_repo(repo)

    # Determine which tasks are already done (resume support).
    done: set[int] = set()
    if resume:
        pause = read_pause(repo)
        if pause is None:
            _print("note: no PAUSED state found; running from start")
        else:
            _print(f"resuming run {pause.run_id}; last attempted task: "
                   f"{pause.last_task_index}")
        done = completed_task_indices(repo)
        if done:
            _print(f"skipping already-committed tasks: {sorted(done)}")

    run_id = new_run_id()
    state_dir(repo)  # ensure exists
    _print(
        f"nim-execute  plan: {plan_path}  run: {run_id}\n"
        f"model_default: {cfg.prefer_small_model}   "
        f"budget: {cfg.max_tokens_per_run} tok / {cfg.max_minutes_per_run} min"
    )

    if dry_run:
        _print("\n[DRY RUN] would execute the following tasks:")
        for t in tasks:
            mark = "DONE" if t.index in done else "TODO"
            _print(f"  [{mark}] task {t.index} mode={t.mode} → {t.target}  ({t.title})")
        return 0

    # Pre-flight quota probe (cheap).
    client = NIMClient.from_env()
    try:
        client.preflight_probe(cfg.prefer_small_model)
    except NIMAuthError as e:
        _print(f"ERROR: auth failed during pre-flight ({e}). Check NVIDIA_NIM_API_KEY.")
        return 3
    except NIMQuotaError as e:
        _print(f"ERROR: quota exhausted during pre-flight ({e}). Try later.")
        return 4
    except NIMError as e:
        _print(f"ERROR: NIM unavailable during pre-flight ({e}).")
        return 5

    # Start anchor tag.
    _git_tag(repo, f"nim-run-{run_id}-start")
    clear_pause(repo)

    deadline = time.monotonic() + (cfg.max_minutes_per_run * 60)
    tokens_used = 0
    passed: list[int] = []
    failed_task: Task | None = None
    failure_kind: str | None = None
    skipped: list[int] = []

    for task in tasks:
        if task.index in done:
            _print(_format_status_line(
                task.index, len(tasks), task.title, "DONE", 0.0, 0, "(prev run)",
            ))
            passed.append(task.index)
            continue
        if failed_task is not None:
            skipped.append(task.index)
            _print(_format_status_line(
                task.index, len(tasks), task.title, "SKIP", 0.0, 0, "(after fail)",
            ))
            continue
        if tokens_used >= cfg.max_tokens_per_run:
            failure_kind = "token_budget"
            skipped.append(task.index)
            continue
        if time.monotonic() > deadline:
            failure_kind = "time_budget"
            skipped.append(task.index)
            continue

        try:
            ok, reason, used_tokens, sha = _execute_task(
                task=task, repo=repo, run_id=run_id, cfg=cfg, client=client,
                remaining_token_budget=cfg.max_tokens_per_run - tokens_used,
                total=len(tasks),
            )
        except Exception as exc:  # pragma: no cover — defense in depth
            # Any uncaught exception inside the task pipeline (e.g., a
            # response shape we didn't anticipate, a verifier shell quirk).
            # Escalate cleanly instead of crashing the whole run.
            import traceback as _tb
            tb = _tb.format_exc()
            _record_escalation(
                repo, task, run_id, _choose_model(task, cfg),
                base_prompt="(unexpected exception — see traceback)",
                response="", verifier_log=tb,
                retry_count=cfg.max_task_retries,
                prompt_tokens=0, completion_tokens=0,
            )
            _print(_format_status_line(
                task.index, len(tasks), task.title, "FAIL", 0.0, 0,
                f"unexpected: {type(exc).__name__}: {str(exc)[:60]}",
            ))
            failed_task = task
            failure_kind = "unexpected_exception"
            continue
        tokens_used += used_tokens
        if ok:
            passed.append(task.index)
        else:
            failed_task = task
            failure_kind = reason

    # End-of-run summary.
    _print("")
    _print(
        f"{len(passed)}/{len(tasks)} passed, "
        f"{1 if failed_task else 0} failed, "
        f"{len(skipped)} skipped"
    )
    today = usage_today(repo)
    _print(
        f"Tokens this run: {tokens_used} / {cfg.max_tokens_per_run} "
        f"({100 * tokens_used / max(cfg.max_tokens_per_run, 1):.1f}%) | "
        f"Today: {today} | Month: {usage_this_month(repo)}"
    )

    if failed_task is None:
        _git_tag(repo, f"nim-run-{run_id}-end")
        clear_pause(repo)
        _print("All tasks completed.")
        return 0

    # Failure path: write pause state and exit non-zero.
    write_pause(repo, PauseState(
        run_id=run_id, plan_path=str(plan_path),
        last_task_index=failed_task.index,
        reason=failure_kind or "unknown", ts=now_iso(),
    ))
    _print(
        f"PAUSED at task {failed_task.index} ({failure_kind}). "
        f"Artifacts: .renmark/state/escalations/task-{failed_task.index}/\n"
        f"Resume with: renmark-execute --resume {plan_path}"
    )
    return 10


def _execute_task(
    *, task: Task, repo: Path, run_id: str, cfg: Config, client: NIMClient,
    remaining_token_budget: int, total: int,
) -> tuple[bool, str, int, str]:
    """Execute one task. Returns (ok, failure_reason_or_blank, tokens_used, sha_or_blank)."""
    if task.executor == "codex":
        return _execute_task_codex(task=task, repo=repo, run_id=run_id, cfg=cfg, total=total)
    model = _choose_model(task, cfg)
    start = time.monotonic()
    try:
        base_prompt = _build_prompt(task, repo)
    except ApplyError as e:
        _record_escalation(repo, task, run_id, model, base_prompt="(prompt build failed)",
                           response="", verifier_log=str(e), retry_count=0,
                           prompt_tokens=0, completion_tokens=0)
        _print(_format_status_line(
            task.index, total, task.title, "FAIL", 0.0, 0,
            f"prompt build: {e}",
        ))
        return False, "prompt_build", 0, ""

    prompt = base_prompt
    tokens_total = 0
    last_response = ""
    last_verifier_tail = ""
    retries_left = cfg.max_task_retries

    while True:
        try:
            resp = client.complete(
                model=model, prompt=prompt,
                temperature=cfg.temperature,
                max_tokens=min(cfg.max_output_tokens, remaining_token_budget),
            )
        except NIMQuotaError as e:
            _print(_format_status_line(
                task.index, total, task.title, "PAUSE", time.monotonic() - start,
                tokens_total, f"quota: {e}",
            ))
            return False, "quota_exhausted", tokens_total, ""
        except NIMRateLimitError as e:
            _print(_format_status_line(
                task.index, total, task.title, "PAUSE", time.monotonic() - start,
                tokens_total, f"rate-limit: {e}",
            ))
            return False, "rate_limited", tokens_total, ""
        except NIMError as e:
            _print(_format_status_line(
                task.index, total, task.title, "FAIL", time.monotonic() - start,
                tokens_total, f"nim error: {e}",
            ))
            _record_escalation(repo, task, run_id, model, base_prompt=prompt,
                               response="", verifier_log=str(e),
                               retry_count=cfg.max_task_retries - retries_left,
                               prompt_tokens=0, completion_tokens=0)
            return False, "nim_error", tokens_total, ""

        last_response = resp.text
        tokens_total += resp.prompt_tokens + resp.completion_tokens
        append_usage(repo, UsageRecord(
            ts=now_iso(), run_id=run_id, task_id=task.index, model=resp.model,
            prompt_tokens=resp.prompt_tokens, completion_tokens=resp.completion_tokens,
        ))

        # Attempt to apply.
        apply_err: str | None = None
        try:
            _apply(task, repo, resp.text)
        except ApplyError as e:
            apply_err = str(e)

        if apply_err:
            if retries_left > 0:
                retries_left -= 1
                prompt = format_reminder_prompt(base_prompt, apply_err)
                continue
            _print(_format_status_line(
                task.index, total, task.title, "FAIL", time.monotonic() - start,
                tokens_total, f"apply: {apply_err[:40]}",
            ))
            _record_escalation(
                repo, task, run_id, model, base_prompt=prompt, response=resp.text,
                verifier_log=apply_err, retry_count=cfg.max_task_retries - retries_left,
                prompt_tokens=resp.prompt_tokens, completion_tokens=resp.completion_tokens,
            )
            return False, "apply_failed", tokens_total, ""

        # Run verifier.
        vres = run_verifier(
            task.verifier, cwd=repo, timeout_s=task.verifier_timeout_s,
        )
        if vres.ok:
            sha = _git_commit(
                repo, task.target,
                message=f"[nim] task {task.index}: {task.title}",
                trailer=f"Co-Authored-By: NIM-{model.split('/')[-1]} <noreply@nvidia.com>",
            )
            _print(_format_status_line(
                task.index, total, task.title, "PASS", time.monotonic() - start,
                tokens_total, f"→ {sha or '(no-commit)'}",
            ))
            return True, "", tokens_total, sha

        # Verifier failed.
        last_verifier_tail = vres.tail
        # Roll back target so retries start from a clean state.
        _git_restore_target(repo, task.target)
        if retries_left > 0:
            retries_left -= 1
            prompt = retry_prompt(base_prompt, vres.tail)
            continue

        _print(_format_status_line(
            task.index, total, task.title, "FAIL", time.monotonic() - start,
            tokens_total, f"verifier exit {vres.exit_code} after retries",
        ))
        _record_escalation(
            repo, task, run_id, model, base_prompt=prompt, response=last_response,
            verifier_log=last_verifier_tail,
            retry_count=cfg.max_task_retries - retries_left,
            prompt_tokens=resp.prompt_tokens, completion_tokens=resp.completion_tokens,
        )
        return False, "verifier_failed", tokens_total, ""


def _execute_task_codex(
    *, task: Task, repo: Path, run_id: str, cfg: Config, total: int,
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
        _print(_format_status_line(
            task.index, total, task.title, "FAIL", 0.0, 0,
            "codex CLI not on PATH",
        ))
        _record_escalation(
            repo, task, run_id, "codex",
            base_prompt="(codex not available)", response="",
            verifier_log="codex CLI is not installed (npm i -g @openai/codex)",
            retry_count=0, prompt_tokens=0, completion_tokens=0,
        )
        return False, "codex_unavailable", 0, ""

    retries_left = cfg.max_task_retries
    last_output_tail = ""

    while True:
        try:
            result = run_codex_task(task, repo, timeout_s=cfg.default_verifier_timeout_s * 10)
        except CodexError as e:
            _print(_format_status_line(
                task.index, total, task.title, "FAIL", time.monotonic() - start, 0,
                f"codex: {e}",
            ))
            _record_escalation(repo, task, run_id, "codex",
                               base_prompt="(codex error)", response="",
                               verifier_log=str(e),
                               retry_count=cfg.max_task_retries - retries_left,
                               prompt_tokens=0, completion_tokens=0)
            return False, "codex_error", 0, ""

        # Log a usage row so --usage shows the call.
        append_usage(repo, UsageRecord(
            ts=now_iso(), run_id=run_id, task_id=task.index, model="codex",
            prompt_tokens=0, completion_tokens=0,
        ))

        last_output_tail = result.output_tail

        if result.exit_code != 0:
            if retries_left > 0:
                retries_left -= 1
                continue
            _print(_format_status_line(
                task.index, total, task.title, "FAIL", time.monotonic() - start, 0,
                f"codex exit {result.exit_code} after retries",
            ))
            _record_escalation(repo, task, run_id, "codex",
                               base_prompt="(see codex_output.log)", response="",
                               verifier_log=result.output_tail,
                               retry_count=cfg.max_task_retries - retries_left,
                               prompt_tokens=0, completion_tokens=0)
            return False, "codex_failed", 0, ""

        # Constrain codex: must have modified only the target file.
        ok, reason = check_only_target_modified(result.changed_files, task.target)
        if not ok:
            # Roll back everything codex did and either retry or escalate.
            subprocess.run(["git", "-C", str(repo), "checkout", "--", "."],
                           capture_output=True)
            subprocess.run(["git", "-C", str(repo), "clean", "-fd",
                            "--", *(p for p in result.changed_files if p != task.target)],
                           capture_output=True)
            if retries_left > 0:
                retries_left -= 1
                continue
            _print(_format_status_line(
                task.index, total, task.title, "FAIL", time.monotonic() - start, 0,
                f"codex out of lane: {reason[:40]}",
            ))
            _record_escalation(repo, task, run_id, "codex",
                               base_prompt="(see codex_output.log)", response="",
                               verifier_log=f"{reason}\n\n{result.output_tail}",
                               retry_count=cfg.max_task_retries - retries_left,
                               prompt_tokens=0, completion_tokens=0)
            return False, "codex_out_of_lane", 0, ""

        # Run verifier.
        vres = run_verifier(task.verifier, cwd=repo, timeout_s=task.verifier_timeout_s)
        if vres.ok:
            sha = _git_commit(
                repo, task.target,
                message=f"[nim] task {task.index}: {task.title}",
                trailer="Co-Authored-By: Codex-CLI <noreply@openai.com>",
            )
            _print(_format_status_line(
                task.index, total, task.title, "PASS",
                time.monotonic() - start, 0, f"→ {sha or '(no-commit)'} (codex)",
            ))
            return True, "", 0, sha

        # Verifier failed. Roll back target and retry.
        last_verifier_tail = vres.tail
        subprocess.run(["git", "-C", str(repo), "checkout", "--", task.target],
                       capture_output=True)
        if retries_left > 0:
            retries_left -= 1
            continue

        _print(_format_status_line(
            task.index, total, task.title, "FAIL", time.monotonic() - start, 0,
            f"codex verifier exit {vres.exit_code} after retries",
        ))
        _record_escalation(repo, task, run_id, "codex",
                           base_prompt="(see codex_output.log)", response="",
                           verifier_log=f"verifier:\n{last_verifier_tail}\n\ncodex tail:\n{last_output_tail}",
                           retry_count=cfg.max_task_retries - retries_left,
                           prompt_tokens=0, completion_tokens=0)
        return False, "codex_verifier_failed", 0, ""


def _record_escalation(
    repo: Path, task: Task, run_id: str, model: str, *, base_prompt: str,
    response: str, verifier_log: str, retry_count: int,
    prompt_tokens: int, completion_tokens: int,
) -> None:
    import json
    d = escalation_dir(repo, task.index)
    (d / "prompt.txt").write_text(base_prompt, encoding="utf-8")
    (d / "response.txt").write_text(response, encoding="utf-8")
    (d / "verifier.log").write_text(verifier_log, encoding="utf-8")
    if task.mode == "B" and response.lstrip().startswith("--- "):
        (d / "diff.patch").write_text(response, encoding="utf-8")
    (d / "metadata.json").write_text(
        json.dumps({
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
        }, indent=2),
        encoding="utf-8",
    )


def cmd_usage(repo: Path) -> int:
    rows = read_usage(repo)
    if not rows:
        print(f"No usage recorded yet at {repo}/.renmark/state/usage.jsonl")
        return 0

    def tok(r: dict) -> int:
        return int(r.get("prompt_tokens", 0)) + int(r.get("completion_tokens", 0))

    today_prefix = now_iso()[:10]
    month_prefix = now_iso()[:7]
    today_rows = [r for r in rows if r.get("ts", "").startswith(today_prefix)]
    month_rows = [r for r in rows if r.get("ts", "").startswith(month_prefix)]

    print(f"Today ({today_prefix}):  {sum(tok(r) for r in today_rows):>7} tokens "
          f"over {len(today_rows)} calls")
    print(f"This month:          {sum(tok(r) for r in month_rows):>7} tokens "
          f"over {len(month_rows)} calls")
    print(f"All time:            {sum(tok(r) for r in rows):>7} tokens "
          f"over {len(rows)} calls")

    # Per-model breakdown this month.
    by_model: dict[str, dict[str, int]] = {}
    for r in month_rows:
        m = r.get("model", "?").split("/")[-1]
        d = by_model.setdefault(m, {"calls": 0, "prompt": 0, "completion": 0})
        d["calls"] += 1
        d["prompt"] += int(r.get("prompt_tokens", 0))
        d["completion"] += int(r.get("completion_tokens", 0))
    if by_model:
        print("\nBy model (this month):")
        print(f"  {'model':<40} {'calls':>6} {'prompt':>8} {'compl':>8} {'total':>8}")
        for m, d in sorted(by_model.items(), key=lambda kv: -(kv[1]["prompt"] + kv[1]["completion"])):
            total = d["prompt"] + d["completion"]
            print(f"  {m:<40} {d['calls']:>6} {d['prompt']:>8} {d['completion']:>8} {total:>8}")

    # Per-run breakdown (today only, to keep it readable).
    by_run: dict[str, dict] = {}
    for r in today_rows:
        rid = r.get("run_id", "?")
        d = by_run.setdefault(rid, {"calls": 0, "tokens": 0, "first": r.get("ts", "")})
        d["calls"] += 1
        d["tokens"] += tok(r)
    if by_run:
        print("\nRuns today:")
        print(f"  {'run_id':<28} {'calls':>6} {'tokens':>8}  started")
        for rid, d in sorted(by_run.items(), key=lambda kv: kv[1]["first"]):
            print(f"  {rid:<28} {d['calls']:>6} {d['tokens']:>8}  {d['first']}")

    # Top tasks this month (catch tasks that ate tokens via retries).
    by_task: dict[tuple, dict] = {}
    for r in month_rows:
        key = (r.get("task_id"), r.get("model", "?").split("/")[-1])
        d = by_task.setdefault(key, {"calls": 0, "tokens": 0})
        d["calls"] += 1
        d["tokens"] += tok(r)
    retries = [(k, v) for k, v in by_task.items() if v["calls"] > 1]
    if retries:
        print("\nTasks that retried this month (eating tokens):")
        for (tid, m), d in sorted(retries, key=lambda kv: -kv[1]["calls"]):
            print(f"  task {tid} ({m}): {d['calls']} calls, {d['tokens']} tokens")

    return 0


def cmd_roadmap(repo: Path) -> int:
    from . import roadmap as _roadmap
    rows = _roadmap.build_rows(repo)
    print(_roadmap.render_table(rows))
    _roadmap.write_roadmap_md(repo)
    print(f"\n(Snapshot written to {repo}/.renmark/memory/roadmap.md)")
    return 0


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    ap = argparse.ArgumentParser(prog="renmark-execute")
    ap.add_argument("plan", nargs="?", help="path to plan file")
    ap.add_argument("--resume", action="store_true", help="resume a paused run")
    ap.add_argument("--dry-run", action="store_true", help="parse plan, list tasks, exit")
    ap.add_argument("--usage", action="store_true", help="show usage and exit")
    ap.add_argument("--roadmap", action="store_true",
                    help="print task | llm | status | tokens | $ | commit table; also writes .renmark/memory/roadmap.md")
    ap.add_argument("--no-commit", action="store_true",
                    help="apply tasks and run verifier but do not git-commit (skill batches commits per wave)")
    ap.add_argument("--repo", default=".", help="repo root (default: current dir)")
    args = ap.parse_args(argv)

    repo = Path(args.repo).resolve()

    if args.usage:
        return cmd_usage(repo)
    if args.roadmap:
        return cmd_roadmap(repo)

    if not args.plan:
        ap.error("plan path is required unless --usage")
    return execute_plan(args.plan, repo=repo, resume=args.resume, dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())

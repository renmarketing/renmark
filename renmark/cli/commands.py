"""renmark-execute subcommand handlers (--usage / --roadmap / --logs / --task).

Self-contained CLI reporting + ad-hoc Codex task mode. These do not touch the
orchestrator's shared git globals, so they live apart from the execution engine.
"""
from __future__ import annotations

from pathlib import Path

from ..state import now_iso, read_usage


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
    from .. import roadmap as _roadmap
    rows = _roadmap.build_rows(repo)
    print(_roadmap.render_table(rows))
    _roadmap.write_roadmap_md(repo)
    print(f"\n(Snapshot written to {repo}/.renmark/memory/roadmap.md)")
    return 0


def cmd_logs(repo: Path, n: int = 10) -> int:
    from .. import state as _state
    items = _state.recent_logs(repo, n=n)
    if not items:
        print(f"No logs yet at {repo}/.renmark/logs/")
        return 0
    print(f"{'when':<26} {'size':>8}  file")
    print("-" * 60)
    for it in items:
        kb = it["size"] / 1024
        print(f"{it['mtime']:<26} {kb:>6.1f}K  {it['name']}")
    print(f"\nFull paths in {repo}/.renmark/logs/")
    return 0


def cmd_task(task_spec_path: str, output_path: str, *, repo: Path) -> int:
    """Ad-hoc Codex task mode (v0.3.0+).

    Reads a task-spec markdown file (prompt + context paths, no inline code),
    dispatches to Codex, writes the artifact to <output_path>. Emits a
    SubagentOutput-shaped JSON dict to stdout for the orchestrator to consume.
    Honors G5 (executor isolation) and G11 (task isolation).
    """
    import json as _json
    from ..summary import emit_pointer, git_head_sha

    spec_path = Path(task_spec_path)
    out_path = Path(output_path)
    if not spec_path.exists():
        print(_json.dumps({
            "status": "FAIL",
            "artifact_path": str(out_path),
            "summary_lines": [f"task spec not found at {spec_path}"],
            "completion_state": "failed",
            "confidence": "high",
            "retry_count": 0,
        }))
        return 2

    task_prompt = spec_path.read_text(encoding="utf-8")

    # Resolve the codex CLI. If not present, return FAIL early — the framework
    # falls back to Sonnet via Agent calls, but ad-hoc mode is codex-only by design
    # (the whole point is to push bulk work outside the orchestrator's window).
    import shutil
    if shutil.which("codex") is None:
        print(_json.dumps({
            "status": "FAIL",
            "artifact_path": str(out_path),
            "summary_lines": [
                "codex CLI not found on PATH",
                "Install codex (https://github.com/openai/codex) or call this task via Agent."
            ],
            "completion_state": "failed",
            "confidence": "high",
            "retry_count": 0,
        }))
        return 127

    # Run codex with the task spec as input. We tell it to write the artifact
    # to <output_path> with the standard ## Summary section. Codex's stdout
    # is NOT what we surface — we only consume the artifact body it writes.
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Build the wrapper prompt that instructs Codex on artifact format.
    wrapper = (
        f"You are a renmark task executor. Read the task spec below and write your "
        f"complete output to {out_path}. The output file MUST be valid renmark artifact "
        f"format: YAML frontmatter metadata + body + a '## Summary' section with at most "
        f"5 bullet lines. Do NOT print the body to stdout. Only the artifact file matters.\n\n"
        f"--- TASK SPEC ---\n{task_prompt}\n--- END TASK SPEC ---\n"
    )

    import subprocess
    try:
        proc = subprocess.run(
            ["codex", "exec", "-"],
            input=wrapper,
            text=True,
            capture_output=True,
            timeout=600,
            cwd=str(repo),
        )
    except subprocess.TimeoutExpired:
        print(_json.dumps({
            "status": "FAIL",
            "artifact_path": str(out_path),
            "summary_lines": ["codex timed out after 600s"],
            "completion_state": "failed",
            "confidence": "high",
            "retry_count": 0,
        }))
        return 124

    if proc.returncode != 0 or not out_path.exists():
        # codex either errored or didn't write the artifact. Surface a bounded summary.
        stderr_tail = (proc.stderr or "").splitlines()[-3:]
        print(_json.dumps({
            "status": "FAIL",
            "artifact_path": str(out_path),
            "summary_lines": [
                f"codex exit {proc.returncode}",
                *[line[:200] for line in stderr_tail],
            ][:5],
            "completion_state": "failed",
            "confidence": "high",
            "retry_count": 0,
        }))
        return proc.returncode or 1

    # Artifact exists. Parse its Summary section into our SubagentOutput shape.
    # Note: codex may not have written valid renmark format — be defensive.
    pointer = emit_pointer(out_path, "task")
    sha = git_head_sha(repo)
    output = {
        "status": "PASS",
        "artifact_path": str(out_path),
        "touched_files": [str(out_path)],
        "sha": sha,
        "summary_lines": pointer.splitlines()[1:6],  # skip header line, take ≤5
        "dependency_notes": "",
        "token_count": 0,  # codex CLI doesn't surface this; orchestrator may estimate
        "completion_state": "complete",
        "confidence": "medium",
        "retry_count": 0,
    }
    print(_json.dumps(output))
    return 0

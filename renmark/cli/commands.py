"""renmark-execute subcommand handlers (--usage / --roadmap / --logs / --task /
--task-brief / --review-package).

Self-contained CLI reporting + ad-hoc Codex task mode. These do not touch the
orchestrator's shared git globals, so they live apart from the execution engine.
"""

from __future__ import annotations

import json
from pathlib import Path

from ..state import handoffs_dir, now_iso, read_usage


def cmd_usage(repo: Path) -> int:
    from .. import usage as _usage

    # Always render the bounded view — even with no recorded usage. The renderer
    # shows zero windows AND the mandatory disclaimer; an early return on an empty
    # ledger would drop the disclaimer (and hide paused-run / local-limit state).
    if not read_usage(repo):
        print(f"No usage recorded yet at {repo}/.renmark/state/usage.jsonl\n")

    view = _usage.build_usage_view(repo, now=now_iso())
    print(_usage.render_usage_md(view))
    return 0


def cmd_analytics(repo: Path) -> int:
    from .. import analytics as _analytics

    try:
        _analytics.aggregate(repo, now=now_iso())
        report = _analytics.build_health_report(repo, now=now_iso())
        md = _analytics.render_health_md(report)
    except Exception:
        print("No analytics yet — run some features or tasks to populate the ledgers.")
        return 0

    print(md)

    # Write committed memory snapshot (mirrors how cmd_roadmap writes roadmap.md).
    memory_dir = Path(repo) / ".renmark" / "memory"
    memory_dir.mkdir(parents=True, exist_ok=True)
    analytics_path = memory_dir / "analytics.md"
    analytics_path.write_text(md, encoding="utf-8")
    print(f"\n(Snapshot written to {repo}/.renmark/memory/analytics.md)")
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


def cmd_scan(repo: Path, *, propose: bool = False, emit_cron: bool = False) -> int:
    from .. import scan as _scan

    if emit_cron:
        print(_scan.emit_cron(repo))
        return 0

    report = _scan.run_scan(repo)
    path = _scan.write_report(repo, report)
    ids = _scan.propose_findings(repo, report) if propose else []

    newly_proposed = len(ids)
    deduped_str = str(report.finding_count - newly_proposed) if propose else "—"
    failed_checks = len(report.checks_failed_to_run)

    partial_note = f"  |  partial: {failed_checks} checks failed to run" if failed_checks else ""
    print(
        f"Findings: {report.finding_count}  |  Proposed: {newly_proposed}"
        f"  |  Deduped/skipped: {deduped_str}  |  Checks failed to run: {failed_checks}"
        f"{partial_note}"
    )
    print(f"Report: {path}")
    if not propose:
        print("(run with --propose to file backlog items)")
    return 2 if failed_checks else 0


def cmd_heartbeat(repo: Path, *, emit_cron: bool = False, auto_resume: bool = False, interval_minutes: int = 30) -> int:
    import datetime

    from .. import heartbeat as _heartbeat

    if emit_cron:
        print(_heartbeat.emit_cron(repo, interval_minutes=interval_minutes))
        return 0

    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    result = _heartbeat.check(repo, now=now)

    if auto_resume and result.should_notify:
        print(result.message)
        return _heartbeat.auto_resume(repo)

    if result.should_notify:
        print(result.message)

    return 0


def cmd_heartbeat_check_cron() -> int:
    """Print 'installed' or 'not-installed' based on cron entry presence. Exit 0 always."""
    from .. import heartbeat as _heartbeat
    status = "installed" if _heartbeat.is_cron_installed() else "not-installed"
    print(status)
    return 0


def _fail_response(out_path: Path | str, summary_lines: list[str]) -> str:
    """Return the standard FAIL JSON string for cmd_task early exits."""
    return json.dumps(
        {
            "status": "FAIL",
            "artifact_path": str(out_path),
            "summary_lines": summary_lines,
            "completion_state": "failed",
            "confidence": "high",
            "retry_count": 0,
            "validation_status": "failed",
            "parser_success": False,
            "schema_compliance": False,
        }
    )


def cmd_task(task_spec_path: str, output_path: str, *, repo: Path) -> int:
    """Ad-hoc Codex task mode (v0.3.0+).

    Reads a task-spec markdown file (prompt + context paths, no inline code),
    dispatches to Codex, writes the artifact to <output_path>. Emits a
    SubagentOutput-shaped JSON dict[str, Any] to stdout for the orchestrator to consume.
    Honors G5 (executor isolation) and G11 (task isolation).
    """
    from ..summary import emit_pointer, git_head_sha

    spec_path = Path(task_spec_path)
    out_path = Path(output_path)
    if not spec_path.exists():
        print(_fail_response(out_path, [f"task spec not found at {spec_path}"]))
        return 2

    task_prompt = spec_path.read_text(encoding="utf-8")

    # Resolve the codex CLI. If not present, return FAIL early — the framework
    # falls back to Sonnet via Agent calls, but ad-hoc mode is codex-only by design
    # (the whole point is to push bulk work outside the orchestrator's window).
    import shutil

    if shutil.which("codex") is None:
        print(_fail_response(out_path, [
            "codex CLI not found on PATH",
            "Install codex (https://github.com/openai/codex) or call this task via Agent.",
        ]))
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
        # Explicit sandbox: never ride the codex CLI default — this is the G5
        # heavy-work path and must match providers/codex.py's constraint.
        proc = subprocess.run(
            ["codex", "exec", "--sandbox", "workspace-write", "--skip-git-repo-check", "-"],
            input=wrapper,
            text=True,
            capture_output=True,
            timeout=600,
            cwd=str(repo),
        )
    except subprocess.TimeoutExpired:
        print(_fail_response(out_path, ["codex timed out after 600s"]))
        return 124

    if proc.returncode != 0 or not out_path.exists():
        # codex either errored or didn't write the artifact. Surface a bounded summary.
        stderr_tail = (proc.stderr or "").splitlines()[-3:]
        print(_fail_response(out_path, (
            [f"codex exit {proc.returncode}", *[line[:200] for line in stderr_tail]][:5]
        )))
        return proc.returncode or 1

    # Artifact exists, but existence != correctness (G9). Validate it before
    # declaring PASS: it must carry YAML frontmatter (read_metadata) AND a
    # parseable '## Summary' section (read_summary_lines). A bare returncode-0
    # is NOT sufficient evidence the artifact is well-formed.
    from ..summary import read_metadata, read_summary_lines

    pointer = emit_pointer(out_path, "task")
    sha = git_head_sha(repo)
    metadata = read_metadata(out_path)
    summary_lines = read_summary_lines(out_path)
    has_metadata = bool(metadata)
    has_summary = bool(summary_lines)
    validated = has_metadata and has_summary

    output = {
        "status": "PASS",
        "artifact_path": str(out_path),
        "touched_files": [str(out_path)],
        "sha": sha,
        "summary_lines": pointer.splitlines()[1:6],  # skip header line, take ≤5
        "dependency_notes": "",
        "token_count": 0,  # codex CLI doesn't surface this; orchestrator may estimate
        # G9 transparency — all six fields, always emitted:
        "completion_state": "complete" if validated else "partial",
        "confidence": "medium" if validated else "low",
        "validation_status": "validated" if validated else "failed",
        "retry_count": 0,
        "parser_success": True,  # we parsed the artifact without raising
        "schema_compliance": validated,  # frontmatter + ## Summary both present
    }
    print(json.dumps(output))
    return 0


def cmd_task_brief(plan_path: str, task_index: int, *, repo: Path) -> int:
    """File-handoff helper: extract one task's brief from a plan and write it to
    `.renmark/state/handoffs/<plan-stem>-task-<N>.brief.md`.

    Prints ONLY the written path to stdout — the brief body never passes through
    the orchestrator's context (REQ-5 / no-diffs rule).

    Filename is deterministic (plan-stem + task-index) so repeated calls for the
    same task are idempotent and overwrite rather than accumulate.

    Returns 0 on success, 2 on any error (printed to stderr).
    """
    import sys

    from ..parser import PlanError, parse_plan

    # Coerce defensively: the `_engine.py` arg parser already passes an int, but
    # direct/programmatic callers (tests, embeds) may hand a string. Without this,
    # a str would never match an int `t.index`, producing the "not found;
    # available: [1, 2]" paradox. int(int) is a harmless no-op for the CLI path.
    try:
        task_index = int(task_index)
    except (TypeError, ValueError):
        print(f"ERROR: task index must be an integer, got {task_index!r}", file=sys.stderr)
        return 2

    try:
        tasks = parse_plan(plan_path)
    except PlanError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    matching = [t for t in tasks if t.index == task_index]
    if not matching:
        indices = sorted(t.index for t in tasks)
        print(
            f"ERROR: task index {task_index} not found in plan; available: {indices}",
            file=sys.stderr,
        )
        return 2

    task = matching[0]

    # Build the brief: everything a subagent needs, nothing more.
    lines: list[str] = [
        f"# Task {task.index}: {task.title}",
        "",
        f"**mode:** {task.mode}",
        f"**target:** {task.target}",
        f"**executor:** {task.executor}",
        f"**complexity:** {task.complexity}",
    ]
    if task.serves:
        lines.append(f"**serves:** {task.serves}")
    if task.context_files:
        lines.append(f"**context_files:** {task.context_files}")
    if task.parallel_group is not None:
        lines.append(f"**parallel_group:** {task.parallel_group}")
    lines += [
        "",
        "## Spec",
        "",
        task.spec,
        "",
        "## Verifier",
        "",
        "```",
        task.verifier,
        "```",
        f"verifier_timeout_s: {task.verifier_timeout_s}",
    ]
    brief_body = "\n".join(lines) + "\n"

    # Deterministic filename: <plan-stem>-task-<N>.brief.md
    plan_stem = Path(plan_path).stem
    # Strip common suffixes like ".plan" so "2026-06-25-foo.plan" → "2026-06-25-foo"
    if plan_stem.endswith(".plan"):
        plan_stem = plan_stem[: -len(".plan")]
    filename = f"{plan_stem}-task-{task_index}.brief.md"

    out_dir = handoffs_dir(repo)
    out_path = out_dir / filename
    out_path.write_text(brief_body, encoding="utf-8")

    # Print ONLY the path — the load-bearing property.
    print(str(out_path))
    return 0


def cmd_review_package(base_ref: str, head_ref: str, *, repo: Path) -> int:
    """File-handoff helper: write a bounded review package (git diff --stat +
    per-file diffs) for the range ``base_ref..head_ref`` to
    `.renmark/state/handoffs/review-<base-short>-<head-short>.pkg.md`.

    Prints ONLY the written path to stdout — the diff bytes never pass through
    the orchestrator's context (REQ-5 / no-diffs rule).

    Filename is deterministic: derived from the short-SHA (or sanitised ref name)
    of each endpoint, so repeated calls for the same range overwrite rather than
    accumulate.

    Returns 0 on success, 2 on any error (printed to stderr).
    """
    import subprocess
    import sys

    def _git(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", *args],
            cwd=str(repo),
            capture_output=True,
            text=True,
        )

    # Resolve each ref to a short SHA for a stable, content-based filename.
    def _short_sha(ref: str) -> str:
        r = _git("rev-parse", "--short", ref)
        if r.returncode == 0:
            return r.stdout.strip()
        # Fallback: sanitise the ref string so it's filename-safe.
        import re
        return re.sub(r"[^a-zA-Z0-9._-]", "-", ref)[:20]

    base_short = _short_sha(base_ref)
    head_short = _short_sha(head_ref)

    # --stat summary (always bounded).
    stat_result = _git("diff", "--stat", f"{base_ref}..{head_ref}")
    if stat_result.returncode != 0:
        print(
            f"ERROR: git diff --stat {base_ref}..{head_ref} failed: "
            f"{stat_result.stderr.strip()[:200]}",
            file=sys.stderr,
        )
        return 2

    # Per-file diffs, bounded: cap total output at ~200 KB to prevent runaway
    # packages on large branches. The reviewer subagent reads the file in one
    # call; unbounded diffs defeat the purpose of the helper.
    _MAX_DIFF_BYTES = 200_000
    diff_result = _git("diff", f"{base_ref}..{head_ref}")
    if diff_result.returncode != 0:
        # Symmetric with the --stat guard above: a stat-success + diff-failure
        # must NOT write an empty-diff package and return success (silent
        # false-success). Surface the error and bail.
        print(
            f"ERROR: git diff {base_ref}..{head_ref} failed: "
            f"{diff_result.stderr.strip()[:200]}",
            file=sys.stderr,
        )
        return 2
    diff_body = diff_result.stdout
    truncated = False
    if len(diff_body.encode()) > _MAX_DIFF_BYTES:
        # Truncate at a line boundary near the limit.
        encoded = diff_body.encode()[:_MAX_DIFF_BYTES]
        diff_body = encoded.decode(errors="replace").rsplit("\n", 1)[0]
        truncated = True

    lines: list[str] = [
        f"# Review package: {base_ref}..{head_ref}",
        "",
        f"base: `{base_ref}` ({base_short})",
        f"head: `{head_ref}` ({head_short})",
        "",
        "## Stat",
        "",
        "```",
        stat_result.stdout.rstrip(),
        "```",
        "",
        "## Diff",
        "",
        "```diff",
        diff_body.rstrip(),
        "```",
    ]
    if truncated:
        lines += [
            "",
            f"_(diff truncated at {_MAX_DIFF_BYTES // 1000}KB — run "
            f"`git diff {base_ref}..{head_ref}` locally for the full output)_",
        ]

    pkg_body = "\n".join(lines) + "\n"

    filename = f"review-{base_short}-{head_short}.pkg.md"
    out_dir = handoffs_dir(repo)
    out_path = out_dir / filename
    out_path.write_text(pkg_body, encoding="utf-8")

    # Print ONLY the path — the load-bearing property.
    print(str(out_path))
    return 0

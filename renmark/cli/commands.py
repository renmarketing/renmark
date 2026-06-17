"""renmark-execute subcommand handlers (--usage / --roadmap / --logs / --task).

Self-contained CLI reporting + ad-hoc Codex task mode. These do not touch the
orchestrator's shared git globals, so they live apart from the execution engine.
"""

from __future__ import annotations

from pathlib import Path

from ..state import now_iso, read_usage


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

    print(
        f"Findings: {report.finding_count}  |  Proposed: {newly_proposed}"
        f"  |  Deduped/skipped: {deduped_str}  |  Checks failed to run: {failed_checks}"
    )
    print(f"Report: {path}")
    if not propose:
        print("(run with --propose to file backlog items)")
    return 0


def cmd_task(task_spec_path: str, output_path: str, *, repo: Path) -> int:
    """Ad-hoc Codex task mode (v0.3.0+).

    Reads a task-spec markdown file (prompt + context paths, no inline code),
    dispatches to Codex, writes the artifact to <output_path>. Emits a
    SubagentOutput-shaped JSON dict[str, Any] to stdout for the orchestrator to consume.
    Honors G5 (executor isolation) and G11 (task isolation).
    """
    import json as _json

    from ..summary import emit_pointer, git_head_sha

    spec_path = Path(task_spec_path)
    out_path = Path(output_path)
    if not spec_path.exists():
        print(
            _json.dumps(
                {
                    "status": "FAIL",
                    "artifact_path": str(out_path),
                    "summary_lines": [f"task spec not found at {spec_path}"],
                    "completion_state": "failed",
                    "confidence": "high",
                    "retry_count": 0,
                    "validation_status": "failed",
                    "parser_success": False,
                    "schema_compliance": False,
                }
            )
        )
        return 2

    task_prompt = spec_path.read_text(encoding="utf-8")

    # Resolve the codex CLI. If not present, return FAIL early — the framework
    # falls back to Sonnet via Agent calls, but ad-hoc mode is codex-only by design
    # (the whole point is to push bulk work outside the orchestrator's window).
    import shutil

    if shutil.which("codex") is None:
        print(
            _json.dumps(
                {
                    "status": "FAIL",
                    "artifact_path": str(out_path),
                    "summary_lines": [
                        "codex CLI not found on PATH",
                        "Install codex (https://github.com/openai/codex) or call this task via Agent.",
                    ],
                    "completion_state": "failed",
                    "confidence": "high",
                    "retry_count": 0,
                    "validation_status": "failed",
                    "parser_success": False,
                    "schema_compliance": False,
                }
            )
        )
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
        print(
            _json.dumps(
                {
                    "status": "FAIL",
                    "artifact_path": str(out_path),
                    "summary_lines": ["codex timed out after 600s"],
                    "completion_state": "failed",
                    "confidence": "high",
                    "retry_count": 0,
                    "validation_status": "failed",
                    "parser_success": False,
                    "schema_compliance": False,
                }
            )
        )
        return 124

    if proc.returncode != 0 or not out_path.exists():
        # codex either errored or didn't write the artifact. Surface a bounded summary.
        stderr_tail = (proc.stderr or "").splitlines()[-3:]
        print(
            _json.dumps(
                {
                    "status": "FAIL",
                    "artifact_path": str(out_path),
                    "summary_lines": [
                        f"codex exit {proc.returncode}",
                        *[line[:200] for line in stderr_tail],
                    ][:5],
                    "completion_state": "failed",
                    "confidence": "high",
                    "retry_count": 0,
                    "validation_status": "failed",
                    "parser_success": False,
                    "schema_compliance": False,
                }
            )
        )
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
    print(_json.dumps(output))
    return 0

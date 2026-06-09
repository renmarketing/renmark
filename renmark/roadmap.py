"""Roadmap reporter.

Synthesizes a status report from three sources:
- `.renmark/memory/features.md` — declared features (planned/in-progress/shipped)
- `.renmark/state/usage.jsonl` — token spend per LLM call (run_id, task_id, model, tokens)
- git log — commit shas for `[renmark|codex|nim|manual] task N:` entries

Output: a per-task table with columns:
  task | llm | status | tokens | $ | commit

Plus a totals row (per-LLM token aggregate and project total $).
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .state import RENMARK_DIR_NAME, read_usage

# Approximate per-token costs (USD per 1k tokens) for cost estimates.
# Opus Agent calls DO consume Anthropic billing (not "in-context free") — they
# go through the user's Claude Code quota. Same for haiku/sonnet. Update as
# pricing shifts.
COST_PER_KT = {
    "haiku": 0.0001,
    "codex": 0.05,
    "sonnet": 0.003,
    "opus": 0.015,  # Anthropic output pricing, rough rule-of-thumb
    "nim": 0.0,  # legacy: NIM removed in v0.2.0
}

# Per-Agent-call overhead: every haiku/sonnet/opus task receives ~10k tokens of
# system prompt + task spec on TOP of its output. Sized to match the plan
# cost-preview footnote so roadmap and plan agree.
AGENT_OVERHEAD_TOKENS = 10_000


@dataclass
class RoadmapRow:
    task: str  # task index + title
    llm: str  # model name or executor
    status: str  # passed | failed | retried | shipped | planned | in-progress
    tokens: int
    cost_usd: float
    commit: str  # short sha or empty
    when: str = ""  # ISO timestamp or date


def _git_commits_for_tasks(repo: str | Path) -> dict[int, str]:
    """Map task_index → short sha by scanning git log for `[renmark|codex|nim|manual] task N:` commits."""
    try:
        out = subprocess.run(
            ["git", "-C", str(repo), "log", "--pretty=%h %s"],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        ).stdout
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        return {}
    pattern = re.compile(
        r"^([0-9a-f]+)\s+\[?(?:renmark|codex|nim|manual)\]?\s+task\s+(\d+)\s*(?:\([^)]*\))?\s*:",
        re.IGNORECASE,
    )
    out_map: dict[int, str] = {}
    for line in out.splitlines():
        m = pattern.match(line.strip())
        if m:
            sha, idx = m.group(1), int(m.group(2))
            out_map.setdefault(idx, sha)
    return out_map


def _aggregate_usage(repo: str | Path) -> dict[int, dict[str, Any]]:
    """Per-task aggregate from usage.jsonl: total tokens, primary model, call count."""
    rows = read_usage(repo)
    by_task: dict[int, dict[str, Any]] = {}
    for r in rows:
        # Tolerate type-malformed ledger rows: one bad row must not kill the
        # whole roadmap (same contract as state.usage's defensive readers).
        try:
            tid = int(r.get("task_id", 0))
        except (TypeError, ValueError):
            continue
        d = by_task.setdefault(
            tid,
            {
                "tokens_in": 0,
                "tokens_out": 0,
                "models": [],
                "calls": 0,
                "last_ts": "",
            },
        )
        d["tokens_in"] += _safe_int(r.get("prompt_tokens", 0))
        d["tokens_out"] += _safe_int(r.get("completion_tokens", 0))
        d["calls"] += 1
        m = r.get("model", "")
        if isinstance(m, str) and m and m not in d["models"]:
            d["models"].append(m)
        ts = r.get("ts", "")
        if isinstance(ts, str):
            d["last_ts"] = max(d["last_ts"], ts)
    return by_task


def _safe_int(value: Any) -> int:
    """Coerce a ledger field to ``int``; bad input → 0."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def build_rows(repo: str | Path) -> list[RoadmapRow]:
    """Build per-task rows from features.md + usage.jsonl + git log."""
    repo_p = Path(repo)
    commits = _git_commits_for_tasks(repo_p)
    usage = _aggregate_usage(repo_p)

    rows: list[RoadmapRow] = []

    # Shipped tasks come from git commit history (the source of truth that something landed).
    for tid in sorted(commits.keys()):
        u = usage.get(tid, {})
        models = ", ".join(u.get("models", [])) or "?"
        tokens = u.get("tokens_in", 0) + u.get("tokens_out", 0)
        cost = _estimate_cost(models, tokens)
        rows.append(
            RoadmapRow(
                task=f"task {tid}",
                llm=_short_model(models),
                status="shipped",
                tokens=tokens,
                cost_usd=cost,
                commit=commits[tid],
                when=u.get("last_ts", ""),
            )
        )

    # Tasks with usage but no commit = attempted, not landed (in-progress or failed).
    for tid, u in usage.items():
        if tid in commits:
            continue
        models = ", ".join(u.get("models", [])) or "?"
        tokens = u.get("tokens_in", 0) + u.get("tokens_out", 0)
        cost = _estimate_cost(models, tokens)
        # If retries > 1 and no commit, likely failed/escalated.
        status = "retried" if u.get("calls", 1) > 1 else "in-progress"
        rows.append(
            RoadmapRow(
                task=f"task {tid}",
                llm=_short_model(models),
                status=status,
                tokens=tokens,
                cost_usd=cost,
                commit="",
                when=u.get("last_ts", ""),
            )
        )

    return rows


def _short_model(name: str) -> str:
    # Trim org/model to just model for compactness.
    if "/" in name:
        return name.split("/", 1)[1]
    return name


def _estimate_cost(model_str: str, tokens: int) -> float:
    """Approximate cost based on which executor strings are in the model field.

    Honest accounting: haiku/sonnet/opus Agent calls cost real Anthropic
    quota (not "in-context free" as the v0.2.x ledger assumed)."""
    m = model_str.lower()
    if "codex" in m:
        return (tokens / 1000.0) * COST_PER_KT["codex"]
    if "opus" in m:
        return (tokens / 1000.0) * COST_PER_KT["opus"]
    if "sonnet" in m:
        return (tokens / 1000.0) * COST_PER_KT["sonnet"]
    if "haiku" in m:
        return (tokens / 1000.0) * COST_PER_KT["haiku"]
    return 0.0  # NIM and unknown = free


def render_table(rows: list[RoadmapRow]) -> str:
    """Render rows as a Markdown table with totals."""
    if not rows:
        return "(no roadmap data yet — run /renmark:plan and /renmark:orchestrate to populate)"

    header = "| task | llm | status | tokens | $ | commit |\n|------|-----|--------|-------:|--:|--------|\n"
    lines = []
    total_tokens = 0
    total_cost = 0.0
    by_status: dict[str, int] = {}
    for r in rows:
        cost_str = f"${r.cost_usd:.3f}" if r.cost_usd > 0 else "free"
        sha = r.commit or "—"
        lines.append(f"| {r.task} | {r.llm} | {r.status} | {r.tokens:,} | {cost_str} | `{sha}` |")
        total_tokens += r.tokens
        total_cost += r.cost_usd
        by_status[r.status] = by_status.get(r.status, 0) + 1

    summary = (
        f"\n\n**Totals:** {len(rows)} tasks · {total_tokens:,} tokens · ${total_cost:.3f}\n"
        + "**By status:** "
        + ", ".join(f"{k}={v}" for k, v in sorted(by_status.items()))
    )

    return header + "\n".join(lines) + summary


def write_roadmap_md(repo: str | Path) -> Path:
    """Render the current roadmap and write it to .renmark/memory/roadmap.md."""
    rows = build_rows(repo)
    table = render_table(rows)
    out = Path(repo) / RENMARK_DIR_NAME / "memory" / "roadmap.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        "# Roadmap\n\nAuto-generated by /renmark:roadmap from features.md + usage.jsonl + git log.\n\n" + table + "\n",
        encoding="utf-8",
    )
    return out

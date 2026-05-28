"""Token-usage ledger (.renmark/state/usage.jsonl).

Codex tasks are ledgered by renmark-execute; Claude-model Agent calls via
`log_agent_call`. /renmark:roadmap reads this file for spend reporting.
"""

from __future__ import annotations

import datetime as dt
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from ._core import USAGE_LEDGER, new_run_id, now_iso, state_dir


@dataclass
class UsageRecord:
    ts: str
    run_id: str
    task_id: int
    model: str
    prompt_tokens: int
    completion_tokens: int

    def as_jsonl(self) -> str:
        return json.dumps(asdict(self), separators=(",", ":"))


def append_usage(repo_root: str | Path, rec: UsageRecord) -> None:
    path = state_dir(repo_root) / USAGE_LEDGER
    with path.open("a", encoding="utf-8") as fh:
        fh.write(rec.as_jsonl() + "\n")


def log_agent_call(
    repo_root: str | Path,
    *,
    task_id: int,
    model: str,
    tokens_in: int = 0,
    tokens_out: int = 0,
    run_id: str | None = None,
) -> UsageRecord:
    """Record one Agent-tool call (haiku/sonnet/opus) in usage.jsonl.

    The orchestrate skill calls this after every Agent return so
    /renmark:roadmap reports honest spend. Codex tasks are ledgered by
    renmark-execute directly; this helper is for the Claude-model path.

    If `tokens_in` is 0 but `tokens_out` is set, the caller likely only has
    SubagentOutput.token_count (total) — pass it as tokens_out and treat
    tokens_in as the Agent-overhead constant in render code.
    """
    rec = UsageRecord(
        ts=now_iso(),
        run_id=run_id or new_run_id(),
        task_id=int(task_id),
        model=model,
        prompt_tokens=int(tokens_in),
        completion_tokens=int(tokens_out),
    )
    append_usage(repo_root, rec)
    return rec


def read_usage(repo_root: str | Path) -> list[dict[str, Any]]:
    path = state_dir(repo_root) / USAGE_LEDGER
    if not path.exists():
        return []
    out: list[dict[str, Any]] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        raw = raw.strip()
        if not raw:
            continue
        try:
            out.append(json.loads(raw))
        except json.JSONDecodeError:
            continue
    return out


def usage_today(repo_root: str | Path) -> int:
    today = dt.datetime.now(dt.timezone.utc).date().isoformat()
    total = 0
    for r in read_usage(repo_root):
        if r.get("ts", "").startswith(today):
            total += int(r.get("prompt_tokens", 0)) + int(r.get("completion_tokens", 0))
    return total


def usage_this_month(repo_root: str | Path) -> int:
    prefix = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m")
    total = 0
    for r in read_usage(repo_root):
        if r.get("ts", "").startswith(prefix):
            total += int(r.get("prompt_tokens", 0)) + int(r.get("completion_tokens", 0))
    return total

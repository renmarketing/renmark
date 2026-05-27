"""Persistent state for renmark-execute.

Split into cohesive submodules (v0.3.2). This package re-exports the full
public surface so `from renmark import state; state.X` and
`from renmark.state import X` both keep working exactly as before the split.

Submodules:
- _core     paths, time helpers, dir-rotation primitive
- usage     token-usage ledger
- pause     PAUSED file + escalation buckets
- pipeline  pipeline.json runtime state + wave summaries
- logs      per-invocation troubleshooting logs
- commits   completed-task detection via git log
- skills    skill-invocation tracking + context-budget check
"""
from __future__ import annotations

from ._core import (
    ARCHIVE_SUBDIR,
    DEBUG_SUBDIR,
    ESCALATIONS_DIR,
    ESCALATIONS_KEEP,
    LAST_SKILL_FILE,
    LOGS_KEEP,
    LOGS_SUBDIR,
    MEMORY_SUBDIR,
    PAUSED_FILE,
    PIPELINE_JSON,
    RENMARK_DIR_NAME,
    STATE_DIR_NAME,
    STATE_SUBDIR,
    USAGE_LEDGER,
    WAVE_SUMMARIES_KEEP,
    WAVE_SUMMARIES_SUBDIR,
    new_run_id,
    now_iso,
    rotate_dir,
    state_dir,
)
from .usage import (
    UsageRecord,
    append_usage,
    log_agent_call,
    read_usage,
    usage_this_month,
    usage_today,
)
from .pause import (
    PauseState,
    clear_pause,
    escalation_dir,
    read_pause,
    write_pause,
)
from .pipeline import (
    PipelineState,
    clear_pipeline_state,
    list_wave_summaries,
    pipeline_is_resumable,
    read_pipeline_state,
    read_wave_summary,
    write_pipeline_state,
    write_wave_summary,
)
from .logs import (
    append_log,
    logs_dir,
    open_log,
    recent_logs,
)
from .commits import completed_task_indices
from .skills import (
    context_budget_check,
    last_skill_invocation,
    record_skill_invocation,
)

__all__ = [
    # _core
    "RENMARK_DIR_NAME", "STATE_SUBDIR", "MEMORY_SUBDIR", "DEBUG_SUBDIR",
    "LOGS_SUBDIR", "USAGE_LEDGER", "PAUSED_FILE", "ESCALATIONS_DIR",
    "ARCHIVE_SUBDIR", "PIPELINE_JSON", "WAVE_SUMMARIES_SUBDIR", "LAST_SKILL_FILE",
    "WAVE_SUMMARIES_KEEP", "LOGS_KEEP", "ESCALATIONS_KEEP", "STATE_DIR_NAME",
    "new_run_id", "now_iso", "state_dir", "rotate_dir",
    # usage
    "UsageRecord", "append_usage", "log_agent_call", "read_usage",
    "usage_today", "usage_this_month",
    # pause
    "PauseState", "write_pause", "read_pause", "clear_pause", "escalation_dir",
    # pipeline
    "PipelineState", "read_pipeline_state", "write_pipeline_state",
    "clear_pipeline_state", "pipeline_is_resumable", "write_wave_summary",
    "read_wave_summary", "list_wave_summaries",
    # logs
    "logs_dir", "open_log", "append_log", "recent_logs",
    # commits
    "completed_task_indices",
    # skills
    "record_skill_invocation", "last_skill_invocation", "context_budget_check",
]

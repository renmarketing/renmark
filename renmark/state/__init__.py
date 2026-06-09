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
from .commits import completed_task_indices
from .logs import (
    append_log,
    logs_dir,
    open_log,
    recent_logs,
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
from .skills import (
    context_budget_check,
    last_skill_invocation,
    record_skill_invocation,
)
from .usage import (
    UsageRecord,
    append_usage,
    log_agent_call,
    read_usage,
    usage_by_run_id,
    usage_this_month,
    usage_today,
)

__all__ = [
    "ARCHIVE_SUBDIR",
    "DEBUG_SUBDIR",
    "ESCALATIONS_DIR",
    "ESCALATIONS_KEEP",
    "LAST_SKILL_FILE",
    "LOGS_KEEP",
    "LOGS_SUBDIR",
    "MEMORY_SUBDIR",
    "PAUSED_FILE",
    "PIPELINE_JSON",
    # _core
    "RENMARK_DIR_NAME",
    "STATE_DIR_NAME",
    "STATE_SUBDIR",
    "USAGE_LEDGER",
    "WAVE_SUMMARIES_KEEP",
    "WAVE_SUMMARIES_SUBDIR",
    # pause
    "PauseState",
    # pipeline
    "PipelineState",
    # usage
    "UsageRecord",
    "append_log",
    "append_usage",
    "clear_pause",
    "clear_pipeline_state",
    # commits
    "completed_task_indices",
    "context_budget_check",
    "escalation_dir",
    "last_skill_invocation",
    "list_wave_summaries",
    "log_agent_call",
    # logs
    "logs_dir",
    "new_run_id",
    "now_iso",
    "open_log",
    "pipeline_is_resumable",
    "read_pause",
    "read_pipeline_state",
    "read_usage",
    "read_wave_summary",
    "recent_logs",
    # skills
    "record_skill_invocation",
    "rotate_dir",
    "state_dir",
    "usage_by_run_id",
    "usage_this_month",
    "usage_today",
    "write_pause",
    "write_pipeline_state",
    "write_wave_summary",
]

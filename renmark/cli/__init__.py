"""renmark-execute CLI package.

Split from a single 982-line module into an execution engine (`_engine`) plus
self-contained subcommand handlers (`commands`). This package re-exports the
prior public surface so `from renmark import cli; cli.main(...)` /
`cli.cmd_task(...)` and `from renmark.cli import main` keep working unchanged.
"""

from __future__ import annotations

from ._engine import Config, execute_plan, main
from .commands import cmd_analytics, cmd_logs, cmd_roadmap, cmd_scan, cmd_task, cmd_usage

__all__ = [
    "Config",
    "cmd_analytics",
    "cmd_logs",
    "cmd_roadmap",
    "cmd_scan",
    "cmd_task",
    "cmd_usage",
    "execute_plan",
    "main",
]

"""Host identity and capability resolution for Claude Code and Codex.

The explicit ``host`` argument wins over ``RENMARK_HOST``.  With neither set,
Claude Code remains the default so existing callers keep their historical
behavior.  Unknown explicit hosts are conservative: they advertise no native
selector or manual context-reset commands.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum


class HostKind(str, Enum):
    """Supported agent hosts."""

    CLAUDE_CODE = "claude"
    CODEX = "codex"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class HostCapabilities:
    """Behavioral capabilities exposed by an agent host.

    ``selector_tool`` names the preferred native selector when that tool is
    exposed by the current surface.  Callers must still fall back to a numbered
    selector when the named tool is unavailable (for example Codex Default
    mode does not currently expose ``request_user_input``).
    """

    render_surface: str
    selector_tool: str | None
    selector_available: bool
    selector_min_options: int
    selector_max_options: int
    supports_numbered_selector: bool
    supports_clear: bool
    supports_resume: bool
    supports_compact: bool = False
    # Additive (cross-host-native-tool-leverage Release 3). Declares whether this
    # host exposes the ExitWorktree tool at all — it is NOT wired into any skill
    # yet. finish/SKILL.md §3.6's worktree-cleanup target is a different, dead
    # code path (no renmark skill creates a worktree via EnterWorktree), so this
    # field currently has no consumer. See .renmark/rethink/
    # cross-host-native-tool-leverage/roadmap.md Release 3.
    supports_exit_worktree: bool = False


_CAPABILITIES: dict[HostKind, HostCapabilities] = {
    HostKind.CLAUDE_CODE: HostCapabilities(
        render_surface="claude-native",
        selector_tool="AskUserQuestion",
        selector_available=True,
        selector_min_options=1,
        selector_max_options=4,
        supports_numbered_selector=True,
        supports_clear=True,
        supports_resume=True,
        supports_compact=True,
        supports_exit_worktree=True,
    ),
    HostKind.CODEX: HostCapabilities(
        render_surface="codex-default",
        selector_tool="request_user_input",
        selector_available=False,
        selector_min_options=2,
        selector_max_options=3,
        supports_numbered_selector=True,
        supports_clear=False,
        supports_resume=False,
        supports_compact=False,
    ),
    HostKind.UNKNOWN: HostCapabilities(
        render_surface="unknown",
        selector_tool=None,
        selector_available=False,
        selector_min_options=0,
        selector_max_options=0,
        supports_numbered_selector=True,
        supports_clear=False,
        supports_resume=False,
        supports_compact=False,
    ),
}

_HOST_ALIASES: dict[str, HostKind] = {
    "claude": HostKind.CLAUDE_CODE,
    "claude-code": HostKind.CLAUDE_CODE,
    "claude_code": HostKind.CLAUDE_CODE,
    "codex": HostKind.CODEX,
    "openai-codex": HostKind.CODEX,
    "unknown": HostKind.UNKNOWN,
}


def resolve_host(host: str | HostKind | None = None) -> HostKind:
    """Resolve host identity from an explicit value, then ``RENMARK_HOST``.

    No value preserves the pre-parity Claude Code default.  An unrecognised
    explicit value or environment value resolves to ``UNKNOWN`` rather than
    assuming support for host commands that may not exist.
    """

    if isinstance(host, HostKind):
        return host
    raw = host if host is not None else os.getenv("RENMARK_HOST")
    if raw is None or not raw.strip():
        # Codex surfaces expose these process markers even when a user has not
        # configured RENMARK_HOST. Keep this below the explicit/env contract so
        # tests and wrappers can always override it deterministically.
        if os.getenv("CODEX_THREAD_ID") or os.getenv(
            "CODEX_INTERNAL_ORIGINATOR_OVERRIDE"
        ):
            return HostKind.CODEX
        return HostKind.CLAUDE_CODE
    return _HOST_ALIASES.get(raw.strip().lower(), HostKind.UNKNOWN)


def capabilities_for(
    host: str | HostKind | None = None,
    *,
    render_surface: str | None = None,
    selector_available: bool | None = None,
) -> HostCapabilities:
    """Return immutable capabilities for the resolved host.

    ``render_surface`` and ``selector_available`` are explicit runtime
    overrides.  They let the caller describe the current UI surface without
    persisting or inferring that state from the environment.
    """

    capabilities = _CAPABILITIES[resolve_host(host)]

    if render_surface is None and selector_available is None:
        return capabilities

    resolved_surface = capabilities.render_surface if render_surface is None else render_surface
    resolved_selector_available = (
        capabilities.selector_available
        if selector_available is None
        else selector_available
    )

    selector_tool = capabilities.selector_tool if resolved_selector_available else None
    selector_min_options = (
        capabilities.selector_min_options if resolved_selector_available else 0
    )
    selector_max_options = (
        capabilities.selector_max_options if resolved_selector_available else 0
    )

    if resolved_surface == "codex-plan" and capabilities.selector_tool:
        resolved_selector_available = True
        selector_tool = capabilities.selector_tool
        selector_min_options = capabilities.selector_min_options
        selector_max_options = capabilities.selector_max_options

    return HostCapabilities(
        render_surface=resolved_surface,
        selector_tool=selector_tool,
        selector_available=resolved_selector_available,
        selector_min_options=selector_min_options,
        selector_max_options=selector_max_options,
        supports_numbered_selector=capabilities.supports_numbered_selector,
        supports_clear=capabilities.supports_clear,
        supports_resume=capabilities.supports_resume,
        supports_compact=capabilities.supports_compact,
    )

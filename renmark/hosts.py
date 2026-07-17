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

    selector_tool: str | None
    selector_max_options: int
    supports_clear: bool
    supports_resume: bool
    supports_compact: bool = False


_CAPABILITIES: dict[HostKind, HostCapabilities] = {
    HostKind.CLAUDE_CODE: HostCapabilities(
        selector_tool="AskUserQuestion",
        selector_max_options=4,
        supports_clear=True,
        supports_resume=True,
        supports_compact=True,
    ),
    HostKind.CODEX: HostCapabilities(
        selector_tool="request_user_input",
        selector_max_options=3,
        supports_clear=False,
        supports_resume=False,
        supports_compact=False,
    ),
    HostKind.UNKNOWN: HostCapabilities(
        selector_tool=None,
        selector_max_options=0,
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


def capabilities_for(host: str | HostKind | None = None) -> HostCapabilities:
    """Return immutable capabilities for the resolved host."""

    return _CAPABILITIES[resolve_host(host)]

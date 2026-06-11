"""---
artifact_type: code_module
schema_version: 1
created_at: 2026-06-11T00:00:00Z
source_sha: null
related_plan: null
generator: codex
stale_after: null
dependency_refs:
  - .renmark/memory/routing.md
completion_state: complete
confidence: high
validation_status: validated
retry_count: 0
parser_success: true
schema_compliance: true
---

Capability routing helpers for declared model tiers.

This module reads the canonical ``## Model tiers`` block from
``.renmark/memory/routing.md`` and exposes bounded, pure helpers for executor
resolution. Public functions are defensive: missing files, missing blocks, and
malformed lines resolve to safe defaults instead of raising.

## Summary

- Parses only the ``## Model tiers`` block and skips malformed entries.
- Resolves the top tier from ``RENMARK_TOP_TIER`` first, then file state, then ``opus``.
- Treats only ``fable`` and ``opus`` as valid top-tier values.
- Preserves non-``fable`` executors unchanged in ``effective_executor``.
"""

from __future__ import annotations

import os
from pathlib import Path

_ROUTING_PATH = Path(".renmark/memory/routing.md")
_MODEL_TIERS_HEADING = "## Model tiers"
_SECTION_PREFIX = "## "
_VALID_TOP_TIERS = {"fable", "opus"}


def read_tiers(repo: Path) -> dict[str, str]:
    """Return key/value pairs from the ``## Model tiers`` block.

    Missing files, missing blocks, and malformed lines all resolve to ``{}``.
    """
    try:
        text = (repo / _ROUTING_PATH).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return {}

    lines = text.splitlines()
    start_index = _find_heading(lines, _MODEL_TIERS_HEADING)
    if start_index is None:
        return {}

    tiers: dict[str, str] = {}
    for raw_line in lines[start_index + 1 :]:
        if raw_line.startswith(_SECTION_PREFIX):
            break
        line = raw_line.strip()
        if not line or ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if not key or not value:
            continue
        tiers[key] = value
    return tiers


def top_tier(repo: Path) -> str:
    """Return the effective top-tier model, defaulting to ``opus``."""
    env_value = os.environ.get("RENMARK_TOP_TIER", "").strip()
    if env_value in _VALID_TOP_TIERS:
        return env_value

    declared = read_tiers(repo).get("top_tier", "").strip()
    if declared in _VALID_TOP_TIERS:
        return declared
    return "opus"


def is_top_tier_declared(repo: Path) -> bool:
    """Return ``True`` when the effective top tier resolves to ``fable``."""
    try:
        return top_tier(repo) == "fable"
    except Exception:
        return False


def effective_executor(executor: str, repo: Path) -> str:
    """Resolve ``fable`` to ``opus`` unless the repo declares that top tier."""
    try:
        if executor != "fable":
            return executor
        if is_top_tier_declared(repo):
            return "fable"
        return "opus"
    except Exception:
        return executor


def _find_heading(lines: list[str], heading: str) -> int | None:
    """Return the first matching heading index, or ``None`` when absent."""
    for index, line in enumerate(lines):
        if line.strip() == heading:
            return index
    return None

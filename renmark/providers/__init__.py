"""Provider registry — one module per LLM backend.

Phase 1: nim, codex, claude_agent.
Phase 4: ollama, openrouter, openai_compat.
Phase 5: litellm_plugin (opt-in).

Each provider exposes a module-level `complete(...)` function returning a
ProviderResponse (text + token counts). The dispatcher (renmark.dispatch)
picks the provider based on the task's `executor` field.
"""
from __future__ import annotations

# Phase 1 imports happen lazily inside dispatch.py to avoid circular deps and
# to skip codex import overhead when not used.
PROVIDERS = {"nim", "codex", "opus", "sonnet"}

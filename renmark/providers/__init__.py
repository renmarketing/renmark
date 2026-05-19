"""Provider registry — one module per LLM backend.

Native providers: codex, claude_agent (haiku/sonnet/opus),
ollama, openrouter, openai_compat.

nim was removed in v0.2.0 — use haiku for simple tasks instead.

Each provider exposes a module-level `complete(...)` function returning a
ProviderResponse (text + token counts). The dispatcher (renmark.dispatch) picks
the provider based on the task's `executor` field.

Executor → provider mapping:
  haiku                → providers.claude_agent (skill must call Agent tool)
  codex                → providers.codex
  sonnet, opus         → providers.claude_agent (skill must call Agent tool)
  ollama_chat/<model>  → providers.ollama
  openrouter/<rest>    → providers.openrouter
  openai_compat/<m>    → providers.openai_compat (needs OPENAI_COMPAT_BASE_URL)
  <other>/<model>      → providers.openai_compat with model as-is
"""
from __future__ import annotations

# Native executor identifiers handled directly.
NATIVE_EXECUTORS = {"haiku", "codex", "sonnet", "opus"}

# Prefix → provider-module-name mapping for "/" -shaped executor strings.
PROVIDER_PREFIXES = {
    "ollama_chat": "ollama",
    "openrouter": "openrouter",
    "openai_compat": "openai_compat",
}


def resolve_provider(executor: str) -> tuple[str, str]:
    """Map an executor string to (provider_module_name, model_arg).

    Examples:
        "haiku"                            -> ("claude_agent", "haiku")
        "codex"                            -> ("codex", "")
        "sonnet"                           -> ("claude_agent", "sonnet")
        "opus"                             -> ("claude_agent", "opus")
        "ollama_chat/qwen2.5-coder:7b"     -> ("ollama", "qwen2.5-coder:7b")
        "openrouter/anthropic/claude-3-h"  -> ("openrouter", "anthropic/claude-3-h")
        "openai_compat/llama-3-70b"        -> ("openai_compat", "llama-3-70b")
        "together/llama-3-70b"             -> ("openai_compat", "llama-3-70b")  (any unknown prefix)
    """
    if executor in NATIVE_EXECUTORS:
        if executor in ("haiku", "sonnet", "opus"):
            return ("claude_agent", executor)
        return (executor, "")  # codex
    if "/" not in executor:
        raise ValueError(f"unknown executor: {executor}")
    prefix, rest = executor.split("/", 1)
    mod = PROVIDER_PREFIXES.get(prefix)
    if mod is None:
        # Fall through to openai_compat — many providers expose OpenAI-shaped
        # APIs and just need the right base URL + key set via env.
        return ("openai_compat", rest)
    return (mod, rest)

"""Provider registry — one module per LLM backend.

Native providers (Phase 1 + Phase 4): nim, codex, claude_agent (opus/sonnet),
ollama, openrouter, openai_compat.

LiteLLM was considered as a multi-provider wrapper and dropped — adding a new
provider is ~50 lines copying the openai_compat pattern.

Each provider exposes a module-level `complete(...)` function returning a
ProviderResponse (text + token counts). The dispatcher (renmark.dispatch) picks
the provider based on the task's `executor` field.

Executor → provider mapping:
  nim                  → providers.nim
  codex                → providers.codex
  opus, sonnet         → providers.claude_agent (skill must call Agent tool)
  ollama_chat/<model>  → providers.ollama
  openrouter/<rest>    → providers.openrouter
  openai_compat/<m>    → providers.openai_compat (needs OPENAI_COMPAT_BASE_URL)
  <other>/<model>      → providers.openai_compat with model as-is
"""
from __future__ import annotations

# Native executor identifiers handled directly.
NATIVE_EXECUTORS = {"nim", "codex", "opus", "sonnet"}

# Prefix → provider-module-name mapping for "/" -shaped executor strings.
PROVIDER_PREFIXES = {
    "ollama_chat": "ollama",
    "openrouter": "openrouter",
    "openai_compat": "openai_compat",
}


def resolve_provider(executor: str) -> tuple[str, str]:
    """Map an executor string to (provider_module_name, model_arg).

    Examples:
        "nim"                              -> ("nim", "")
        "codex"                            -> ("codex", "")
        "opus"                             -> ("claude_agent", "opus")
        "sonnet"                           -> ("claude_agent", "sonnet")
        "ollama_chat/qwen2.5-coder:7b"     -> ("ollama", "qwen2.5-coder:7b")
        "openrouter/anthropic/claude-3-h"  -> ("openrouter", "anthropic/claude-3-h")
        "openai_compat/llama-3-70b"        -> ("openai_compat", "llama-3-70b")
        "together/llama-3-70b"             -> ("openai_compat", "llama-3-70b")  (any unknown prefix)
    """
    if executor in NATIVE_EXECUTORS:
        if executor in ("opus", "sonnet"):
            return ("claude_agent", executor)
        return (executor, "")
    if "/" not in executor:
        raise ValueError(f"unknown executor: {executor}")
    prefix, rest = executor.split("/", 1)
    mod = PROVIDER_PREFIXES.get(prefix)
    if mod is None:
        # Fall through to openai_compat — many providers expose OpenAI-shaped
        # APIs and just need the right base URL + key set via env.
        return ("openai_compat", rest)
    return (mod, rest)

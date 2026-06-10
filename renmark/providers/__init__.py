"""Provider registry — one module per LLM backend.

Active providers: codex, claude_agent (haiku/sonnet/opus).

nim, ollama, openrouter, and openai_compat were removed in v0.2.0.
The only production executor is codex; claude_agent handles
haiku/sonnet/opus via the host's Agent tool call.
"""

from __future__ import annotations

# Native executor identifiers handled directly.
NATIVE_EXECUTORS = {"haiku", "codex", "sonnet", "opus"}

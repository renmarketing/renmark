"""Local Ollama provider (http://localhost:11434).

Ollama exposes an OpenAI-compatible API at /v1/chat/completions. We reuse
the openai_compat client and just default the base URL + skip auth.

Executor string format: `ollama_chat/<model>` (e.g. `ollama_chat/qwen2.5-coder:7b`).
"""
from __future__ import annotations

import os

from . import openai_compat


DEFAULT_OLLAMA_URL = "http://localhost:11434/v1"


def complete(
    *,
    model: str,                 # e.g. "qwen2.5-coder:7b"
    prompt: str,
    base_url: str | None = None,
    temperature: float = 0.2,
    max_tokens: int = 4096,
    timeout_s: int = 600,       # local can be slow on first load
    max_retries: int = 1,       # local; retries rarely help
) -> openai_compat.ProviderResponse:
    base = base_url or os.environ.get("OLLAMA_BASE_URL") or DEFAULT_OLLAMA_URL
    return openai_compat.complete(
        model=model,
        prompt=prompt,
        base_url=base,
        api_key="ollama",  # ignored by ollama but required by openai_compat shape
        temperature=temperature,
        max_tokens=max_tokens,
        timeout_s=timeout_s,
        max_retries=max_retries,
    )

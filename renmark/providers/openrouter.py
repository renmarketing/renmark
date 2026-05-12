"""OpenRouter provider — gateway to ~150 models through one OpenAI-compatible API.

Executor string format: `openrouter/<provider>/<model>`
  e.g. `openrouter/anthropic/claude-3-haiku`, `openrouter/meta-llama/llama-3.1-70b-instruct`.

The first `openrouter/` segment is stripped by the dispatcher; the rest is passed
as the OpenRouter `model` field.

Env: OPENROUTER_API_KEY
"""
from __future__ import annotations

import os

from . import openai_compat


OPENROUTER_URL = "https://openrouter.ai/api/v1"


def complete(
    *,
    model: str,                 # already stripped of leading "openrouter/" by dispatcher
    prompt: str,
    api_key: str | None = None,
    temperature: float = 0.2,
    max_tokens: int = 4096,
    timeout_s: int = 300,
    max_retries: int = 5,
) -> openai_compat.ProviderResponse:
    key = api_key or os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise openai_compat.ProviderError(
            "OPENROUTER_API_KEY not set. Get one at https://openrouter.ai/keys"
        )
    return openai_compat.complete(
        model=model,
        prompt=prompt,
        base_url=OPENROUTER_URL,
        api_key=key,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout_s=timeout_s,
        max_retries=max_retries,
    )

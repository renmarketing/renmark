"""Generic OpenAI-compatible provider.

Many services expose an OpenAI-compatible chat-completions endpoint:
Together, Anyscale, Groq, DeepInfra, Fireworks, Mistral cloud, vLLM, etc.
This provider speaks that protocol against a configurable base URL + key.

Executor string format: `openai_compat/<model>` (when base URL is set via env),
or just pass model directly when the dispatcher knows the provider context.

Env vars consumed (caller can override per call):
- OPENAI_COMPAT_BASE_URL  (e.g. https://api.together.xyz/v1)
- OPENAI_COMPAT_API_KEY
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass

import requests


@dataclass
class ProviderResponse:
    text: str
    prompt_tokens: int
    completion_tokens: int
    model: str


class ProviderError(RuntimeError):
    pass


def complete(
    *,
    model: str,
    prompt: str,
    base_url: str | None = None,
    api_key: str | None = None,
    temperature: float = 0.2,
    max_tokens: int = 4096,
    timeout_s: int = 300,
    max_retries: int = 3,
) -> ProviderResponse:
    """Run a non-streaming chat completion against an OpenAI-compatible API.

    Non-streaming for simplicity — most use cases here are short emit tasks
    where buffering is fine. Add streaming later if needed.
    """
    base = base_url or os.environ.get("OPENAI_COMPAT_BASE_URL")
    key = api_key or os.environ.get("OPENAI_COMPAT_API_KEY")
    if not base:
        raise ProviderError("OPENAI_COMPAT_BASE_URL not set")
    if not key:
        raise ProviderError("OPENAI_COMPAT_API_KEY not set")
    url = f"{base.rstrip('/')}/chat/completions"

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }

    delay = 2.0
    last_err: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=timeout_s)
        except requests.RequestException as e:
            last_err = e
            if attempt >= max_retries:
                raise ProviderError(f"network failure after {max_retries} retries: {e}") from e
            time.sleep(delay)
            delay = min(delay * 2, 60.0)
            continue

        if resp.status_code in (429, 503):
            if attempt >= max_retries:
                raise ProviderError(f"HTTP {resp.status_code} after {max_retries} retries")
            time.sleep(delay)
            delay = min(delay * 2, 60.0)
            continue
        if resp.status_code == 401:
            raise ProviderError(f"401 Unauthorized — check API key")
        if resp.status_code >= 400:
            raise ProviderError(f"HTTP {resp.status_code}: {resp.text[:500]}")

        try:
            data = resp.json()
        except ValueError as e:
            raise ProviderError(f"non-JSON response: {resp.text[:500]}") from e
        try:
            text = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as e:
            raise ProviderError(f"unexpected response shape: {data}") from e
        usage = data.get("usage") or {}
        return ProviderResponse(
            text=text,
            prompt_tokens=int(usage.get("prompt_tokens", 0)),
            completion_tokens=int(usage.get("completion_tokens", 0)),
            model=data.get("model", model),
        )

    raise ProviderError(f"exhausted retries: {last_err}")  # pragma: no cover

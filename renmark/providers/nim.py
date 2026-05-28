"""NIM (NVIDIA Inference Microservice) HTTP client with pacing and 429 backoff.

The orchestrator uses this exclusively. Streaming is always on so big-model
generations don't timeout the HTTP connection.
"""

from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import dataclass

import requests


class NIMError(RuntimeError):
    """Generic NIM API failure."""


class NIMRateLimitError(NIMError):
    """429/503 after exhausting retries — caller should pause."""


class NIMAuthError(NIMError):
    """401 — bad API key."""


class NIMQuotaError(NIMError):
    """Used when the pre-flight probe indicates quota is gone."""


@dataclass
class NIMResponse:
    text: str
    prompt_tokens: int
    completion_tokens: int
    model: str


class RateLimiter:
    def __init__(self, min_interval_s: float) -> None:
        self.min_interval_s = max(0.0, float(min_interval_s))
        self._last_call: float = 0.0
        self._lock = threading.Lock()

    def wait(self) -> None:
        with self._lock:
            now = time.monotonic()
            wait_for = (self._last_call + self.min_interval_s) - now
            if wait_for > 0:
                time.sleep(wait_for)
            self._last_call = time.monotonic()


class NIMClient:
    def __init__(
        self,
        api_key: str,
        base_url: str,
        rate_limiter: RateLimiter | None = None,
        max_retries_429: int = 5,
        timeout_s: int = 300,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.rate_limiter = rate_limiter or RateLimiter(0.0)
        self.max_retries_429 = max_retries_429
        self.timeout_s = timeout_s

    @classmethod
    def from_env(cls, *, min_interval_s: float | None = None) -> NIMClient:
        api_key = os.environ.get("NVIDIA_NIM_API_KEY")
        if not api_key:
            raise NIMAuthError("NVIDIA_NIM_API_KEY not set in environment")
        base = os.environ.get("NVIDIA_NIM_BASE_URL", "https://integrate.api.nvidia.com/v1")
        interval = min_interval_s if min_interval_s is not None else float(os.environ.get("NIM_MIN_INTERVAL_S", "6.0"))
        retries = int(os.environ.get("NIM_MAX_RETRIES_429", "5"))
        timeout = int(os.environ.get("NIM_TIMEOUT_S", "300"))
        return cls(
            api_key=api_key,
            base_url=base,
            rate_limiter=RateLimiter(interval),
            max_retries_429=retries,
            timeout_s=timeout,
        )

    def preflight_probe(self, model: str) -> None:
        """Send a 1-token request to check the API is reachable and quota is not exhausted.

        Raises NIMAuthError on 401, NIMQuotaError on 429, NIMError on other failures.
        """
        try:
            self.complete(
                model=model,
                prompt="ok",
                temperature=0.0,
                max_tokens=1,
                _is_probe=True,
            )
        except NIMRateLimitError as e:
            raise NIMQuotaError(
                "Pre-flight probe rate-limited — quota likely exhausted. Retry later or upgrade NVIDIA NIM tier."
            ) from e

    def complete(
        self,
        *,
        model: str,
        prompt: str,
        temperature: float = 0.2,
        max_tokens: int = 4096,
        _is_probe: bool = False,
    ) -> NIMResponse:
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "text/event-stream",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
            # OpenAI-compatible: makes the server include a final chunk with
            # usage={prompt_tokens, completion_tokens, total_tokens} after
            # the content chunks. Without this, NIM streams don't carry
            # token counts and our ledger records zeros.
            "stream_options": {"include_usage": True},
        }

        attempt = 0
        delay = 2.0
        while True:
            self.rate_limiter.wait()
            try:
                with requests.post(
                    url,
                    headers=headers,
                    json=payload,
                    stream=True,
                    timeout=self.timeout_s,
                ) as resp:
                    if resp.status_code == 401:
                        raise NIMAuthError(f"401 Unauthorized: {resp.text[:200]}")
                    if resp.status_code in (429, 503):
                        if attempt >= self.max_retries_429:
                            raise NIMRateLimitError(f"HTTP {resp.status_code} after {self.max_retries_429} retries")
                        attempt += 1
                        time.sleep(delay)
                        delay = min(delay * 2, 60.0)
                        continue
                    if resp.status_code >= 400:
                        raise NIMError(f"HTTP {resp.status_code}: {resp.text[:500]}")

                    text_chunks: list[str] = []
                    prompt_tokens = 0
                    completion_tokens = 0
                    seen_model = model
                    for raw in resp.iter_lines(decode_unicode=False):
                        if not raw:
                            continue
                        try:
                            line = raw.decode("utf-8")
                        except UnicodeDecodeError:
                            continue
                        if not line.startswith("data: "):
                            continue
                        data = line[len("data: ") :]
                        if data == "[DONE]":
                            break
                        try:
                            obj = json.loads(data)
                        except json.JSONDecodeError:
                            continue
                        seen_model = obj.get("model", seen_model)
                        for choice in obj.get("choices", []) or []:
                            delta = choice.get("delta") or {}
                            content = delta.get("content")
                            if content:
                                text_chunks.append(content)
                        usage = obj.get("usage") or {}
                        if usage:
                            prompt_tokens = int(usage.get("prompt_tokens", prompt_tokens))
                            completion_tokens = int(usage.get("completion_tokens", completion_tokens))
                    return NIMResponse(
                        text="".join(text_chunks),
                        prompt_tokens=prompt_tokens,
                        completion_tokens=completion_tokens,
                        model=seen_model,
                    )
            except requests.RequestException as e:
                # Catches Timeout, ConnectionError, ChunkedEncodingError
                # (truncated SSE streams), ContentDecodingError, etc. —
                # anything inheriting from the `requests` exception base.
                if attempt >= self.max_retries_429:
                    raise NIMError(f"network failure after retries: {type(e).__name__}: {e}") from e
                attempt += 1
                time.sleep(delay)
                delay = min(delay * 2, 60.0)

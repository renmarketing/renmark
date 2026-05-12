"""Unit tests for NIMClient (mocked HTTP)."""
from __future__ import annotations

import time
from unittest.mock import patch

import pytest

from renmark.providers import nim as nim_client  # alias preserves test code
from renmark.providers.nim import (
    NIMAuthError,
    NIMClient,
    NIMError,
    NIMRateLimitError,
    RateLimiter,
)


class _FakeStreamResp:
    def __init__(self, status_code: int, lines: list[bytes] | None = None,
                 text: str = "") -> None:
        self.status_code = status_code
        self._lines = lines or []
        self.text = text

    def __enter__(self) -> "_FakeStreamResp":
        return self

    def __exit__(self, *a) -> None:
        return None

    def iter_lines(self, decode_unicode: bool = False):
        yield from self._lines


def _sse(payload: dict) -> bytes:
    import json
    return b"data: " + json.dumps(payload).encode()


def test_rate_limiter_enforces_interval() -> None:
    rl = RateLimiter(0.1)
    rl.wait()
    t0 = time.monotonic()
    rl.wait()
    assert time.monotonic() - t0 >= 0.09


def test_client_parses_sse_and_usage() -> None:
    sse_lines = [
        _sse({"choices": [{"delta": {"content": "hello "}}]}),
        b"",
        _sse({"choices": [{"delta": {"content": "world"}}]}),
        _sse({"usage": {"prompt_tokens": 11, "completion_tokens": 2},
              "choices": [{"delta": {}}]}),
        b"data: [DONE]",
    ]
    fake = _FakeStreamResp(200, sse_lines)
    client = NIMClient(
        api_key="x", base_url="https://example.invalid/v1",
        rate_limiter=RateLimiter(0.0), max_retries_429=2, timeout_s=5,
    )
    with patch.object(nim_client.requests, "post", return_value=fake):
        resp = client.complete(model="m", prompt="hi", max_tokens=10)
    assert resp.text == "hello world"
    assert resp.prompt_tokens == 11
    assert resp.completion_tokens == 2


def test_client_raises_auth_on_401() -> None:
    fake = _FakeStreamResp(401, [], text="bad key")
    client = NIMClient(
        api_key="x", base_url="https://example.invalid/v1",
        rate_limiter=RateLimiter(0.0), max_retries_429=2, timeout_s=5,
    )
    with patch.object(nim_client.requests, "post", return_value=fake):
        with pytest.raises(NIMAuthError):
            client.complete(model="m", prompt="hi", max_tokens=10)


def test_client_retries_429_then_succeeds() -> None:
    good_lines = [
        _sse({"choices": [{"delta": {"content": "ok"}}],
              "usage": {"prompt_tokens": 1, "completion_tokens": 1}}),
        b"data: [DONE]",
    ]
    responses = [
        _FakeStreamResp(429, [], text="slow down"),
        _FakeStreamResp(429, [], text="slow down"),
        _FakeStreamResp(200, good_lines),
    ]
    client = NIMClient(
        api_key="x", base_url="https://example.invalid/v1",
        rate_limiter=RateLimiter(0.0), max_retries_429=5, timeout_s=5,
    )
    with patch.object(nim_client.requests, "post", side_effect=responses):
        with patch.object(nim_client.time, "sleep"):
            resp = client.complete(model="m", prompt="hi", max_tokens=10)
    assert resp.text == "ok"


def test_client_gives_up_after_max_retries_429() -> None:
    responses = [_FakeStreamResp(429, [], text="x") for _ in range(4)]
    client = NIMClient(
        api_key="x", base_url="https://example.invalid/v1",
        rate_limiter=RateLimiter(0.0), max_retries_429=3, timeout_s=5,
    )
    with patch.object(nim_client.requests, "post", side_effect=responses):
        with patch.object(nim_client.time, "sleep"):
            with pytest.raises(NIMRateLimitError):
                client.complete(model="m", prompt="hi", max_tokens=10)


def test_client_retries_on_chunked_encoding_error() -> None:
    """Regression: truncated SSE stream used to crash the orchestrator (v0.1.2-).

    requests.exceptions.ChunkedEncodingError is NOT a subclass of Timeout
    or ConnectionError, so the narrow except-tuple let it escape. v0.1.3
    broadens the catch to requests.RequestException.
    """
    good_lines = [
        _sse({"choices": [{"delta": {"content": "ok"}}],
              "usage": {"prompt_tokens": 1, "completion_tokens": 1}}),
        b"data: [DONE]",
    ]
    # First call: raises ChunkedEncodingError mid-stream. Second: succeeds.
    call_count = {"n": 0}

    def fake_post(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise nim_client.requests.exceptions.ChunkedEncodingError(
                "stream truncated"
            )
        return _FakeStreamResp(200, good_lines)

    client = NIMClient(
        api_key="x", base_url="https://example.invalid/v1",
        rate_limiter=RateLimiter(0.0), max_retries_429=3, timeout_s=5,
    )
    with patch.object(nim_client.requests, "post", side_effect=fake_post):
        with patch.object(nim_client.time, "sleep"):
            resp = client.complete(model="m", prompt="hi", max_tokens=10)
    assert resp.text == "ok"
    assert call_count["n"] == 2  # retried once


def test_client_raises_generic_on_500() -> None:
    fake = _FakeStreamResp(500, [], text="server boom")
    client = NIMClient(
        api_key="x", base_url="https://example.invalid/v1",
        rate_limiter=RateLimiter(0.0), max_retries_429=2, timeout_s=5,
    )
    with patch.object(nim_client.requests, "post", return_value=fake):
        with pytest.raises(NIMError):
            client.complete(model="m", prompt="hi", max_tokens=10)

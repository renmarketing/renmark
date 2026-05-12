"""Unit tests for renmark.providers (Phase 4 native providers, mocked HTTP)."""
from __future__ import annotations

from unittest.mock import patch, MagicMock

import pytest

from renmark.providers import (
    NATIVE_EXECUTORS,
    resolve_provider,
    openai_compat,
    ollama,
    openrouter,
)


# --- resolver -----------------------------------------------------------

def test_resolver_native_executors() -> None:
    assert resolve_provider("nim") == ("nim", "")
    assert resolve_provider("codex") == ("codex", "")
    assert resolve_provider("opus") == ("claude_agent", "opus")
    assert resolve_provider("sonnet") == ("claude_agent", "sonnet")


def test_resolver_ollama_strips_prefix() -> None:
    assert resolve_provider("ollama_chat/qwen2.5-coder:7b") == ("ollama", "qwen2.5-coder:7b")


def test_resolver_openrouter_passes_through_rest() -> None:
    assert resolve_provider("openrouter/anthropic/claude-3-haiku") == (
        "openrouter", "anthropic/claude-3-haiku",
    )


def test_resolver_openai_compat_explicit() -> None:
    assert resolve_provider("openai_compat/llama-3-70b") == ("openai_compat", "llama-3-70b")


def test_resolver_unknown_prefix_falls_through_to_openai_compat() -> None:
    # Any unknown <prefix>/<model> hits openai_compat with the model as-is.
    assert resolve_provider("together/llama-3-70b-instruct") == (
        "openai_compat", "llama-3-70b-instruct",
    )


def test_resolver_rejects_bare_unknown() -> None:
    with pytest.raises(ValueError, match="unknown executor"):
        resolve_provider("gpt5")


# --- openai_compat (mocked) ---------------------------------------------

def _mock_response(status: int, body: dict | str):
    m = MagicMock()
    m.status_code = status
    if isinstance(body, dict):
        m.json.return_value = body
        m.text = str(body)
    else:
        m.json.side_effect = ValueError("no json")
        m.text = body
    return m


def test_openai_compat_happy_path() -> None:
    body = {
        "model": "test-model",
        "choices": [{"message": {"content": "hello world"}}],
        "usage": {"prompt_tokens": 12, "completion_tokens": 3},
    }
    with patch.object(openai_compat.requests, "post", return_value=_mock_response(200, body)):
        r = openai_compat.complete(
            model="test-model", prompt="hi",
            base_url="https://example.invalid/v1", api_key="key",
        )
    assert r.text == "hello world"
    assert r.prompt_tokens == 12
    assert r.completion_tokens == 3
    assert r.model == "test-model"


def test_openai_compat_missing_base_url_raises() -> None:
    with patch.dict("os.environ", {}, clear=True):
        with pytest.raises(openai_compat.ProviderError, match="OPENAI_COMPAT_BASE_URL"):
            openai_compat.complete(model="m", prompt="x")


def test_openai_compat_401() -> None:
    with patch.object(openai_compat.requests, "post", return_value=_mock_response(401, "nope")):
        with pytest.raises(openai_compat.ProviderError, match="401"):
            openai_compat.complete(
                model="m", prompt="x",
                base_url="https://example.invalid/v1", api_key="bad",
            )


def test_openai_compat_retries_429_then_succeeds() -> None:
    good = _mock_response(200, {
        "choices": [{"message": {"content": "ok"}}],
        "usage": {"prompt_tokens": 1, "completion_tokens": 1},
    })
    responses = [_mock_response(429, "slow"), _mock_response(429, "slow"), good]
    with patch.object(openai_compat.requests, "post", side_effect=responses):
        with patch.object(openai_compat.time, "sleep"):
            r = openai_compat.complete(
                model="m", prompt="x",
                base_url="https://example.invalid/v1", api_key="k",
                max_retries=3,
            )
    assert r.text == "ok"


# --- ollama (delegates to openai_compat) --------------------------------

def test_ollama_uses_default_local_url() -> None:
    body = {
        "choices": [{"message": {"content": "ollama-ok"}}],
        "usage": {"prompt_tokens": 5, "completion_tokens": 2},
    }
    with patch.object(openai_compat.requests, "post", return_value=_mock_response(200, body)) as p:
        ollama.complete(model="qwen2.5-coder:7b", prompt="hi")
    assert p.called
    called_url = p.call_args.args[0]
    assert "localhost:11434" in called_url


# --- openrouter ----------------------------------------------------------

def test_openrouter_requires_api_key() -> None:
    with patch.dict("os.environ", {}, clear=True):
        with pytest.raises(openai_compat.ProviderError, match="OPENROUTER_API_KEY"):
            openrouter.complete(model="anthropic/claude-3-haiku", prompt="x")


def test_openrouter_passes_full_model_string() -> None:
    body = {
        "choices": [{"message": {"content": "or-ok"}}],
        "usage": {"prompt_tokens": 3, "completion_tokens": 1},
    }
    with patch.object(openai_compat.requests, "post", return_value=_mock_response(200, body)) as p:
        openrouter.complete(model="anthropic/claude-3-haiku", prompt="x", api_key="sk-or-123")
    payload = p.call_args.kwargs["json"]
    assert payload["model"] == "anthropic/claude-3-haiku"
    assert "openrouter.ai" in p.call_args.args[0]

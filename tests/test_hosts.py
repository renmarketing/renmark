"""Host identity and capability resolution."""

from __future__ import annotations

import pytest

from renmark.hosts import HostKind, capabilities_for, resolve_host


def test_resolve_host_defaults_to_claude(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("RENMARK_HOST", raising=False)
    monkeypatch.delenv("CODEX_THREAD_ID", raising=False)
    monkeypatch.delenv("CODEX_INTERNAL_ORIGINATOR_OVERRIDE", raising=False)

    assert resolve_host() is HostKind.CLAUDE_CODE


def test_codex_process_marker_is_detected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("RENMARK_HOST", raising=False)
    monkeypatch.setenv("CODEX_THREAD_ID", "thread-123")

    assert resolve_host() is HostKind.CODEX


def test_explicit_host_wins_over_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RENMARK_HOST", "codex")

    assert resolve_host("claude-code") is HostKind.CLAUDE_CODE


def test_codex_capabilities_do_not_claim_clear_or_resume() -> None:
    capabilities = capabilities_for(HostKind.CODEX)

    assert capabilities.selector_tool == "request_user_input"
    assert capabilities.selector_max_options == 3
    assert capabilities.supports_clear is False
    assert capabilities.supports_resume is False
    assert capabilities.supports_compact is False


def test_claude_capabilities_preserve_existing_context_commands() -> None:
    capabilities = capabilities_for("claude")

    assert capabilities.selector_tool == "AskUserQuestion"
    assert capabilities.selector_max_options == 4
    assert capabilities.supports_clear is True
    assert capabilities.supports_resume is True
    assert capabilities.supports_compact is True


def test_unknown_host_is_conservative(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RENMARK_HOST", "future-host")

    assert resolve_host() is HostKind.UNKNOWN
    assert capabilities_for().selector_tool is None
    assert capabilities_for().supports_clear is False

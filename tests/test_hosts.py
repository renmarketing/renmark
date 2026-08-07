"""Host identity and capability resolution."""

from __future__ import annotations

import pytest

from renmark.hosts import HostCapabilities, HostKind, capabilities_for, resolve_host


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


@pytest.mark.parametrize(
    ("label", "kwargs", "expected"),
    [
        (
            "claude",
            {"host": HostKind.CLAUDE_CODE},
            HostCapabilities(
                render_surface="claude-native",
                selector_tool="AskUserQuestion",
                selector_available=True,
                selector_min_options=1,
                selector_max_options=4,
                supports_numbered_selector=True,
                supports_clear=True,
                supports_resume=True,
                supports_compact=True,
                supports_exit_worktree=True,
            ),
        ),
        (
            "codex_plan",
            {"host": HostKind.CODEX, "render_surface": "codex-plan"},
            HostCapabilities(
                render_surface="codex-plan",
                selector_tool="request_user_input",
                selector_available=True,
                selector_min_options=2,
                selector_max_options=3,
                supports_numbered_selector=True,
                supports_clear=False,
                supports_resume=False,
                supports_compact=False,
            ),
        ),
        (
            "codex_default",
            {"host": HostKind.CODEX},
            HostCapabilities(
                render_surface="codex-default",
                selector_tool="request_user_input",
                selector_available=False,
                selector_min_options=2,
                selector_max_options=3,
                supports_numbered_selector=True,
                supports_clear=False,
                supports_resume=False,
                supports_compact=False,
            ),
        ),
        (
            "explicit_availability_override_on",
            {"host": HostKind.CODEX, "selector_available": True},
            HostCapabilities(
                render_surface="codex-default",
                selector_tool="request_user_input",
                selector_available=True,
                selector_min_options=2,
                selector_max_options=3,
                supports_numbered_selector=True,
                supports_clear=False,
                supports_resume=False,
                supports_compact=False,
            ),
        ),
        (
            "explicit_availability_override_off",
            {
                "host": HostKind.CLAUDE_CODE,
                "render_surface": "claude-native",
                "selector_available": False,
            },
            HostCapabilities(
                render_surface="claude-native",
                selector_tool=None,
                selector_available=False,
                selector_min_options=0,
                selector_max_options=0,
                supports_numbered_selector=True,
                supports_clear=True,
                supports_resume=True,
                supports_compact=True,
            ),
        ),
        (
            "unknown",
            {"host": HostKind.UNKNOWN},
            HostCapabilities(
                render_surface="unknown",
                selector_tool=None,
                selector_available=False,
                selector_min_options=0,
                selector_max_options=0,
                supports_numbered_selector=True,
                supports_clear=False,
                supports_resume=False,
                supports_compact=False,
            ),
        ),
    ],
    ids=lambda label, *_: label,
)
def test_host_capability_matrix(
    label: str, kwargs: dict[str, object], expected: HostCapabilities
) -> None:
    del label
    assert capabilities_for(**kwargs) == expected


def test_codex_capabilities_do_not_claim_clear_or_resume() -> None:
    capabilities = capabilities_for(HostKind.CODEX)

    assert capabilities.selector_tool == "request_user_input"
    assert capabilities.selector_available is False
    assert capabilities.selector_min_options == 2
    assert capabilities.selector_max_options == 3
    assert capabilities.supports_numbered_selector is True
    assert capabilities.supports_clear is False
    assert capabilities.supports_resume is False
    assert capabilities.supports_compact is False
    assert capabilities.supports_exit_worktree is False


def test_claude_capabilities_preserve_existing_context_commands() -> None:
    capabilities = capabilities_for("claude")

    assert capabilities.selector_tool == "AskUserQuestion"
    assert capabilities.selector_min_options == 1
    assert capabilities.selector_max_options == 4
    assert capabilities.supports_numbered_selector is True
    assert capabilities.supports_clear is True
    assert capabilities.supports_resume is True
    assert capabilities.supports_compact is True
    assert capabilities.supports_exit_worktree is True


def test_unknown_host_is_conservative(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RENMARK_HOST", "future-host")

    assert resolve_host() is HostKind.UNKNOWN
    capabilities = capabilities_for()
    assert capabilities.selector_tool is None
    assert capabilities.selector_available is False
    assert capabilities.selector_min_options == 0
    assert capabilities.selector_max_options == 0
    assert capabilities.supports_numbered_selector is True
    assert capabilities.supports_clear is False


def test_host_only_capabilities_call_matches_native_contract() -> None:
    assert capabilities_for(HostKind.CLAUDE_CODE) == capabilities_for("claude")
    assert capabilities_for(HostKind.CODEX) == capabilities_for("codex")

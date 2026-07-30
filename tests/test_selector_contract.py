"""Cross-host selector semantic contract tests."""

from __future__ import annotations

from dataclasses import asdict

import pytest

from renmark.delivery_state import DeliveryState
from renmark.hosts import HostKind, capabilities_for
from renmark.interaction import Choice, build_selector, continue_selector


def _dangerous_choices() -> tuple[Choice, ...]:
    return (
        Choice("a", "Approve", "continue with the dangerous action", recommended=True),
        Choice("r", "Review", "inspect the proposal first"),
        Choice("e", "Edit", "change the proposal"),
        Choice("w", "Wait", "pause without approving"),
        Choice("reject", "Reject", "refuse the dangerous action"),
    )


def _selector_cases() -> tuple[dict[str, object], ...]:
    return (
        {
            "id": "claude_native",
            "kwargs": {"host": HostKind.CLAUDE_CODE},
            "mode": "selector",
            "tool": "AskUserQuestion",
            "page_count": 2,
            "visible_labels": (
                "Approve (Recommended)",
                "Review",
                "Edit",
                "More",
            ),
        },
        {
            "id": "codex_plan_native",
            "kwargs": {"host": HostKind.CODEX, "render_surface": "codex-plan"},
            "mode": "selector",
            "tool": "request_user_input",
            "page_count": 3,
            "visible_labels": (
                "Approve (Recommended)",
                "Review",
                "More",
            ),
        },
        {
            "id": "codex_default_fallback",
            "kwargs": {"host": HostKind.CODEX, "tool_available": False},
            "mode": "fallback",
            "tool": None,
            "page_count": 1,
            "visible_labels": (
                "Approve (Recommended)",
                "Review",
                "Edit",
                "Wait",
                "Reject",
            ),
        },
    )


def _rendered_case(case: dict[str, object], *, page: int = 0) -> dict[str, object]:
    kwargs = dict(case["kwargs"])  # type: ignore[arg-type]
    kwargs["page"] = page
    return build_selector(
        "Proceed with release?",
        _dangerous_choices(),
        decision_id="release_gate",
        header="Approve",
        dangerous=True,
        **kwargs,
    )


def _semantic_ids(rendered: dict[str, object]) -> tuple[str, ...]:
    semantic = rendered["semantic"]  # type: ignore[index]
    return tuple(choice["choice_id"] for choice in semantic["choices"])  # type: ignore[index]


def test_table_driven_render_paths_preserve_identical_semantic_choices() -> None:
    rendered = [_rendered_case(case) for case in _selector_cases()]

    first_semantic = rendered[0]["semantic"]
    assert sum(choice["recommended"] for choice in first_semantic["choices"]) == 1
    assert first_semantic["choices"][0]["choice_id"] == "a"
    assert first_semantic["choices"][0]["label"] == "Approve"

    for case, payload in zip(_selector_cases(), rendered, strict=True):
        assert payload["mode"] == case["mode"]
        assert payload.get("tool") == case["tool"]
        assert payload["semantic"] == first_semantic
        assert _semantic_ids(payload) == ("a", "r", "e", "w", "reject")
        assert payload["semantic"]["dangerous"] is True
        assert payload["semantic"]["decision_id"] == "release_gate"
        visible = payload["page"]["bindings"]
        assert tuple(entry["label"] for entry in visible) == case["visible_labels"]
        if payload["mode"] == "selector":
            options = payload["arguments"]["questions"][0]["options"]
            assert options[0]["label"] == "Approve (Recommended)"
            assert payload["overflow"] is True
        else:
            assert payload["reason"] == "selector_unavailable"
            assert "headless" not in payload


@pytest.mark.parametrize("case", _selector_cases(), ids=lambda case: str(case["id"]))
def test_reachable_semantic_choices_match_across_render_paths(case: dict[str, object]) -> None:
    rendered = _rendered_case(case)

    first_choice = continue_selector(rendered, "1")
    assert first_choice.kind == "selected"
    assert first_choice.choice is not None
    assert first_choice.choice.choice_id == "a"

    refusal = continue_selector(rendered, "reject" if rendered["mode"] == "fallback" else "cancel")
    assert refusal.kind == "cancel"
    assert refusal.choice is not None
    assert refusal.choice.choice_id == "reject"

    review = continue_selector(rendered, "review")
    assert review.kind == "selected"
    assert review.choice is not None
    assert review.choice.choice_id == "r"


def test_claude_overflow_pages_keep_back_and_refusal_reachable() -> None:
    first_page = _rendered_case(_selector_cases()[0])
    assert continue_selector(first_page, "more").kind == "more"

    second_page = _rendered_case(_selector_cases()[0], page=1)
    assert second_page["page"]["count"] == 2
    assert tuple(entry["label"] for entry in second_page["page"]["bindings"]) == (
        "Wait",
        "Reject",
        "Back",
    )

    rejection = continue_selector(second_page, "2")
    assert rejection.kind == "cancel"
    assert rejection.choice is not None
    assert rejection.choice.choice_id == "reject"

    back = continue_selector(second_page, "back")
    assert back.kind == "back"


def test_codex_plan_overflow_pages_cover_more_back_and_reject() -> None:
    first_page = _rendered_case(_selector_cases()[1])
    assert continue_selector(first_page, "more").kind == "more"

    second_page = _rendered_case(_selector_cases()[1], page=1)
    assert tuple(entry["label"] for entry in second_page["page"]["bindings"]) == (
        "Edit",
        "More",
        "Back",
    )
    assert continue_selector(second_page, "more").kind == "more"
    assert continue_selector(second_page, "back").kind == "back"

    third_page = _rendered_case(_selector_cases()[1], page=2)
    assert tuple(entry["label"] for entry in third_page["page"]["bindings"]) == (
        "Wait",
        "Reject",
        "Back",
    )
    rejection = continue_selector(third_page, "reject")
    assert rejection.kind == "cancel"
    assert rejection.choice is not None
    assert rejection.choice.choice_id == "reject"


def test_one_choice_always_falls_back_with_complete_numbered_menu() -> None:
    choice = (Choice("only", "Only choice", "the sole semantic action", recommended=True),)

    for host in (HostKind.CLAUDE_CODE, HostKind.CODEX):
        rendered = build_selector("Only one?", choice, host=host)
        assert rendered["mode"] == "fallback"
        assert rendered["reason"] == "single_choice_requires_fallback"
        assert rendered["options"] == (
            "1. [only] Only choice (Recommended) — the sole semantic action",
        )
        result = continue_selector(rendered, "1")
        assert result.kind == "selected"
        assert result.choice is not None
        assert result.choice.choice_id == "only"


def test_invalid_and_free_text_continuation_are_host_neutral() -> None:
    selector = build_selector(
        "What next?",
        (
            Choice("d", "Dispatch", "run it", recommended=True),
            Choice("n", "No", "stop"),
        ),
        host=HostKind.CODEX,
        render_surface="codex-plan",
        allow_free_text=True,
    )
    assert continue_selector(selector, "not listed").kind == "free_text"
    assert continue_selector(selector, "not listed").text == "not listed"

    fallback = build_selector(
        "What next?",
        (
            Choice("d", "Dispatch", "run it", recommended=True),
            Choice("n", "No", "stop"),
        ),
        host=HostKind.CODEX,
    )
    assert continue_selector(fallback, "not listed").kind == "invalid"


def test_render_time_presentation_never_enters_delivery_state() -> None:
    rendered = _rendered_case(_selector_cases()[1], page=2)
    payload = asdict(DeliveryState())
    forbidden = {
        "tool",
        "arguments",
        "fallback",
        "overflow",
        "instructions",
        "semantic",
        "page",
        "render_surface",
        "selector_available",
    }

    assert forbidden.isdisjoint(payload)
    assert forbidden.isdisjoint(rendered["semantic"])
    assert "render_surface" not in rendered["semantic"]
    assert "selector_available" not in rendered["semantic"]


def test_selector_helpers_do_not_switch_codex_collaboration_mode() -> None:
    default_before = capabilities_for(HostKind.CODEX)
    assert default_before.render_surface == "codex-default"
    assert default_before.selector_available is False

    rendered = _rendered_case(_selector_cases()[1], page=1)
    default_after = capabilities_for(HostKind.CODEX)

    assert rendered["host"] == "codex"
    assert rendered["tool"] == "request_user_input"
    assert rendered["semantic"]["header"] == "Approve"
    assert "collaboration" not in rendered
    assert "mode_switch" not in rendered
    assert default_after == default_before

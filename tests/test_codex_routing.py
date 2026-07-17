from renmark.codex_routing import build_native_dispatch, route_for_task


def test_simple_task_routes_to_mini() -> None:
    route = route_for_task({"complexity": "simple", "role": "docs-editor"})

    assert route.model == "gpt-5.4-mini"
    assert route.reasoning_effort == "low"
    assert route.tier == "codex-mini"


def test_medium_task_routes_to_gpt55_medium() -> None:
    route = route_for_task({"complexity": "medium", "role": "code-implementer"})

    assert route.model == "gpt-5.5"
    assert route.reasoning_effort == "medium"
    assert route.tier == "codex-standard"


def test_hard_task_routes_to_gpt55_high() -> None:
    route = route_for_task({"complexity": "hard", "role": "reviewer"})

    assert route.model == "gpt-5.5"
    assert route.reasoning_effort == "high"
    assert route.tier == "codex-deep"


def test_native_dispatch_uses_isolated_codex_transport() -> None:
    native = build_native_dispatch(
        {"index": 7, "title": "Edit docs!", "complexity": "simple"},
        role="docs-editor",
        prompt="bounded packet",
    )

    assert native.spawn_tool == "spawn_agent"
    assert native.wait_tool == "wait_agent"
    assert native.followup_tool == "followup_task"
    assert native.task_name == "renmark_7_docs_editor_edit_docs"
    assert native.spawn_args == {
        "task_name": native.task_name,
        "fork_turns": "none",
        "message": "bounded packet",
    }
    assert native.route.tier == "codex-mini"
    assert "model" not in native.spawn_args

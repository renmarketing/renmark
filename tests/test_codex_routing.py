from renmark.codex_routing import route_for_task


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

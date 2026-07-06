"""Deterministic tests for subagent role profiles and role propagation."""

from __future__ import annotations

from pathlib import Path

from renmark import memory, subagent_profiles
from renmark.cost import estimate_cost
from renmark.dispatch import build_subagent_input
from renmark.parser import Task


def _make_task(**overrides: object) -> Task:
    defaults = dict(
        index=10,
        title="task",
        mode="B",
        target="renmark/example.py",
        context_files=[],
        executor="codex",
        complexity="medium",
        parallel_group=4,
        verifier="pytest -q",
        spec="do the thing",
        est_tokens=None,
        est_cost_usd=None,
    )
    defaults.update(overrides)
    return Task(**defaults)


def test_profiles_have_complete_fields_and_specialized_tiers() -> None:
    assert "general-purpose" in subagent_profiles.PROFILES

    for role, spec in subagent_profiles.PROFILES.items():
        assert spec.role == role
        assert spec.model_tier in {"haiku", "codex", "sonnet", "opus"}
        assert spec.allowed_targets
        assert spec.output_format
        assert spec.stop_condition
        assert spec.verification
        assert spec.context_scope in {"narrow", "broad"}

    assert subagent_profiles.PROFILES["general-purpose"].model_tier == "sonnet"
    assert subagent_profiles.PROFILES["docs-editor"].model_tier == "haiku"
    assert subagent_profiles.PROFILES["test-writer"].model_tier == "codex"
    assert subagent_profiles.PROFILES["audit-reader"].model_tier == "haiku"


def test_resolve_profile_maps_targets_and_fallback() -> None:
    test_task = _make_task(target="tests/test_cost.py")
    docs_task = _make_task(target="plugin/skills/feature/SKILL.md")
    code_task = _make_task(target="renmark/dispatch.py")
    fallback_task = _make_task(target="assets/logo.svg")

    assert subagent_profiles.resolve_profile(test_task) == "test-writer"
    assert subagent_profiles.resolve_profile(docs_task) == "docs-editor"
    assert subagent_profiles.resolve_profile(code_task) == "code-implementer"
    assert subagent_profiles.resolve_profile(fallback_task) == "general-purpose"


def test_build_subagent_input_populates_role_from_profile_resolution() -> None:
    task = _make_task(target="tests/test_subagent_profiles.py", spec="add tests")

    packet = build_subagent_input(task)

    assert packet.role == "test-writer"


def test_append_routing_persists_role(tmp_path: Path) -> None:
    memory.append_routing(
        tmp_path,
        signature="target=tests/test_subagent_profiles.py, complexity=medium",
        executor="codex",
        outcome="passed",
        role="test-writer",
        date="2026-07-02",
    )

    routing = (tmp_path / ".renmark" / "memory" / "routing.md").read_text(encoding="utf-8")
    assert "role=test-writer" in routing


def test_has_native_agent_file_checks_static_roles_without_repo() -> None:
    specialized_roles = (
        "docs-editor",
        "code-implementer",
        "test-writer",
        "reviewer",
        "release-manager",
        "researcher",
        "audit-reader",
        "finish-lane-specialist",
    )

    for role in specialized_roles:
        assert subagent_profiles.has_native_agent_file(role) is True

    assert subagent_profiles.has_native_agent_file("general-purpose") is False
    assert subagent_profiles.has_native_agent_file("garbage-role-name") is False


def test_has_native_agent_file_checks_repo_native_agent_files(tmp_path: Path) -> None:
    role = "reviewer"
    agent_file = tmp_path / ".claude" / "agents" / f"{role}.md"
    agent_file.parent.mkdir(parents=True)
    agent_file.write_text("# reviewer\n", encoding="utf-8")

    assert subagent_profiles.has_native_agent_file(role, repo=tmp_path) is True
    assert subagent_profiles.has_native_agent_file("release-manager", repo=tmp_path) is False


def test_estimate_cost_exposes_sorted_unique_roles() -> None:
    preview = estimate_cost(
        [
            {"executor": "codex", "est_tokens": 500, "role": "test-writer"},
            {"executor": "haiku", "est_tokens": 100, "role": "docs-editor"},
            {"executor": "codex", "est_tokens": 250, "role": "test-writer"},
        ]
    )

    assert preview.roles == ("docs-editor", "test-writer")


def test_subagent_input_to_dict_serializes_role() -> None:
    # AC2: the *serialized* dispatch packet must carry the role, not just the dataclass field.
    task = Task(
        index=1, title="write tests", mode="B", target="tests/test_x.py",
        context_files=[], model=None, verifier="pytest -q", spec="...",
        executor="codex", complexity="medium", parallel_group=1,
    )
    packet = build_subagent_input(task)
    payload = packet.to_dict()
    assert "role" in payload
    assert payload["role"] == packet.role == "test-writer"

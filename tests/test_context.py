"""
---
artifact_type: test
schema_version: 1
created_at: 2026-07-01T00:00:00Z
source_sha: unknown
related_plan: REQ-20
generator: codex
stale_after: null
dependency_refs:
  - renmark/context.py
  - renmark/dispatch.py
  - renmark/parser.py
---
Pytest coverage for `renmark.context` and the metadata-only skill-loading
integration in `renmark.dispatch`.

## Summary
- Verifies the full context taxonomy and path classification contract.
- Covers skill metadata, pointer rendering, and body-on-demand file loading.
- Proves upfront context excludes dynamic bodies for pipeline, meta, and unknown skills.
- Guards `assert_metadata_only` against fenced, multiline, and oversized payloads.
- Confirms dispatch packets carry plan metadata + pointer, not the plan SKILL.md body.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from renmark import context, dispatch, skillmeta
from renmark.parser import Task, parse_plan


def _make_task(tmp_path: Path) -> Task:
    plan_path = tmp_path / "task.plan.md"
    plan_path.write_text(
        "\n".join(
            [
                "### Task 1: sample task",
                "- **mode:** A",
                "- **target:** src/foo.py",
                "- **context_files:** [docs/spec.md]",
                "- **executor:** codex",
                "- **verifier:** python3 -m pytest tests/test_context.py -q",
                "- **spec:** Build the target file.",
            ]
        ),
        encoding="utf-8",
    )
    return parse_plan(plan_path)[0]


def test_context_kind_members_and_taxonomy_match() -> None:
    expected = {
        context.ContextKind.STATIC,
        context.ContextKind.DYNAMIC,
        context.ContextKind.MEMORY,
        context.ContextKind.TASK_LOCAL,
    }
    assert set(context.ContextKind) == expected
    assert set(context.TAXONOMY) == expected
    for kind, source in context.TAXONOMY.items():
        assert source.kind is kind


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("CLAUDE.md", context.ContextKind.STATIC),
        ("AGENTS.md", context.ContextKind.STATIC),
        ("plugin/skills/plan/SKILL.md", context.ContextKind.DYNAMIC),
        ("plugin/skills/.shared/reuse-check.md", context.ContextKind.DYNAMIC),
        (".renmark/memory/INDEX.md", context.ContextKind.MEMORY),
        ("src/foo.py", context.ContextKind.TASK_LOCAL),
        ("", context.ContextKind.TASK_LOCAL),
    ],
)
def test_classify_path_matches_contract(path: str, expected: context.ContextKind) -> None:
    assert context.classify_path(path) is expected


def test_skill_metadata_and_pointer_contract() -> None:
    metadata = context.skill_metadata("plan")
    assert metadata is not None
    assert set(metadata) == {
        "name",
        "domain",
        "next_steps_class",
        "cites",
        "has_handoff",
        "disable_model_invocation",
    }
    assert metadata["name"] == "plan"
    assert metadata["domain"] == skillmeta.SKILLS["plan"].domain
    assert metadata["next_steps_class"] == skillmeta.SKILLS["plan"].next_steps_class
    assert metadata["cites"] == skillmeta.SKILLS["plan"].cites
    assert metadata["has_handoff"] == skillmeta.SKILLS["plan"].has_handoff
    assert (
        metadata["disable_model_invocation"]
        == skillmeta.SKILLS["plan"].disable_model_invocation
    )
    assert context.skill_metadata("does-not-exist") is None
    plan_body = Path("plugin/skills/plan/SKILL.md").read_text(encoding="utf-8")
    assert "Reads a spec" in plan_body
    assert "Reads a spec" not in json.dumps(metadata, sort_keys=True)
    assert set(context.all_skill_metadata()) == set(skillmeta.SKILLS)
    assert (
        context.skill_pointer("plan")
        == "${CLAUDE_PLUGIN_ROOT}/skills/plan/SKILL.md"
    )


def test_body_loaders_are_on_demand(tmp_path: Path) -> None:
    plugin_root = tmp_path / "plugin"
    skill_dir = plugin_root / "skills" / "foo"
    shared_dir = plugin_root / "skills" / ".shared"
    skill_dir.mkdir(parents=True)
    shared_dir.mkdir(parents=True)

    skill_text = "# foo\nskill body\n"
    fragment_text = "shared fragment\n"
    (skill_dir / "SKILL.md").write_text(skill_text, encoding="utf-8")
    (shared_dir / "bar.md").write_text(fragment_text, encoding="utf-8")

    assert context.load_skill_body(plugin_root, "foo") == skill_text
    assert context.load_fragment(plugin_root, "bar") == fragment_text
    with pytest.raises(FileNotFoundError):
        context.load_skill_body(plugin_root, "missing")
    with pytest.raises(FileNotFoundError):
        context.load_fragment(plugin_root, "missing")


@pytest.mark.parametrize("skill_name", ["plan", "help", "unknown-skill"])
def test_upfront_kinds_exclude_dynamic_bodies(skill_name: str) -> None:
    kinds = context.upfront_kinds_for_skill(skill_name)
    assert isinstance(kinds, frozenset)
    assert context.ContextKind.STATIC in kinds
    assert context.ContextKind.MEMORY in kinds
    assert context.ContextKind.DYNAMIC not in kinds
    assert context.ContextKind.TASK_LOCAL not in kinds


def test_assert_metadata_only_accepts_bare_names() -> None:
    context.assert_metadata_only(["plan", "verify"])


@pytest.mark.parametrize(
    "bad_entry",
    [
        "plan\nwith body",
        "```inlined body```",
        "x" * 81,
    ],
)
def test_assert_metadata_only_rejects_body_like_entries(bad_entry: str) -> None:
    with pytest.raises(ValueError):
        context.assert_metadata_only(["plan", bad_entry])


def test_build_subagent_input_uses_skill_metadata_not_body(tmp_path: Path) -> None:
    task = _make_task(tmp_path)

    packet = dispatch.build_subagent_input(task, required_skills=["plan"])
    payload = packet.to_dict()
    skill_refs = payload["required_skills"]

    assert len(skill_refs) == 1
    assert skill_refs[0]["name"] == "plan"
    assert skill_refs[0]["pointer"] == "${CLAUDE_PLUGIN_ROOT}/skills/plan/SKILL.md"
    assert skill_refs[0]["metadata"] == context.skill_metadata("plan")

    packet_json = packet.to_json()
    distinctive_phrase = (
        "Before decomposing a directly provided feature description"
    )
    plan_body = Path("plugin/skills/plan/SKILL.md").read_text(encoding="utf-8")
    assert distinctive_phrase in plan_body
    assert distinctive_phrase not in packet_json


def test_build_subagent_input_rejects_inlined_skill_body(tmp_path: Path) -> None:
    task = _make_task(tmp_path)

    with pytest.raises(ValueError):
        dispatch.build_subagent_input(
            task,
            required_skills=["```inlined body```"],
        )


def test_build_subagent_input_defaults_required_skills_to_empty(tmp_path: Path) -> None:
    task = _make_task(tmp_path)

    packet = dispatch.build_subagent_input(task)

    assert packet.required_skills == []
    assert packet.to_dict()["required_skills"] == []

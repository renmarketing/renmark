"""Unit tests for staged-program helpers in renmark.roadmap."""

from __future__ import annotations

from pathlib import Path

from renmark import program, roadmap


def _program_fixture() -> program.Program:
    return program.Program(
        feature="Setup reconciliation",
        mode="staged",
        current_stage_id="stage-2",
        stages=[
            program.StageNode(
                id="stage-1",
                title="Plan foundation",
                serves="REQ-1",
                status="done",
                tasks=[
                    program.TaskNode(id="task-1", title="Draft spec", status="done"),
                ],
            ),
            program.StageNode(
                id="stage-2",
                title="Build workflow",
                serves="REQ-2",
                status="partial",
                tasks=[
                    program.TaskNode(id="task-2", title="Implement flow", status="needed"),
                    program.TaskNode(id="task-3", title="Verify flow", status="needed"),
                ],
            ),
            program.StageNode(
                id="stage-3",
                title="Release support",
                serves="REQ-3",
                status="needed",
                tasks=[
                    program.TaskNode(id="task-4", title="Ship docs", status="needed"),
                ],
            ),
        ],
    )


def test_render_program_table_returns_no_program_string_when_absent(tmp_path: Path) -> None:
    rendered = roadmap.render_program_table(tmp_path)

    assert rendered == (
        "(no in-flight program — run /renmark:plan to stage one, "
        "then /renmark:orchestrate to drive it)"
    )


def test_render_program_table_renders_stages_tasks_statuses_and_attention_section(
    tmp_path: Path,
) -> None:
    program.write_program(tmp_path, _program_fixture())

    rendered = roadmap.render_program_table(tmp_path)

    assert "# Program — Setup reconciliation" in rendered
    assert "_mode: staged · Stage 2/3 · task 0/2 done · current: Build workflow_" in rendered
    assert "## ● Plan foundation — serves REQ-1 [done]" in rendered
    assert "## ◑ Build workflow — serves REQ-2 [partial] (current)" in rendered
    assert "## ! Release support — serves REQ-3 [needed]" in rendered
    assert "- [done] Draft spec" in rendered
    assert "- [needed] Implement flow" in rendered
    assert "- [needed] Verify flow" in rendered
    assert "- [needed] Ship docs" in rendered
    assert "## Where work is needed" in rendered
    assert "- Build workflow (serves REQ-2) — partial" in rendered
    assert "- Release support (serves REQ-3) — needed" in rendered


def test_reconcile_setup_maps_req_matches_and_persists(tmp_path: Path) -> None:
    state = program.Program(
        feature="Brownfield import",
        mode="setup",
        stages=[
            program.StageNode(
                id="stage-1",
                title="Plan foundation",
                serves="REQ-1",
                status="pending",
                tasks=[
                    program.TaskNode(id="task-1", title="Draft spec", status="pending"),
                ],
            ),
            program.StageNode(
                id="stage-2",
                title="Build workflow",
                serves="REQ-2",
                status="pending",
                tasks=[
                    program.TaskNode(id="task-2", title="Implement flow", status="pending"),
                ],
            ),
            program.StageNode(
                id="stage-3",
                title="Release support",
                serves="REQ-3",
                status="pending",
                tasks=[
                    program.TaskNode(id="task-3", title="Ship docs", status="pending"),
                ],
            ),
        ],
    )
    program.write_program(tmp_path, state)

    updated = roadmap.reconcile_setup(
        tmp_path,
        {
            "built_reqs": ["REQ-1"],
            "partial_reqs": ["REQ-2"],
            "built_components": [],
        },
    )

    assert [stage.status for stage in updated.stages] == ["done", "partial", "needed"]
    assert [task.status for task in updated.stages[0].tasks] == ["done"]
    assert [task.status for task in updated.stages[1].tasks] == ["needed"]
    assert [task.status for task in updated.stages[2].tasks] == ["needed"]

    persisted = program.read_program(tmp_path)
    assert persisted is not None
    assert [stage.status for stage in persisted.stages] == ["done", "partial", "needed"]
    assert [task.status for task in persisted.stages[0].tasks] == ["done"]
    assert [task.status for task in persisted.stages[1].tasks] == ["needed"]
    assert [task.status for task in persisted.stages[2].tasks] == ["needed"]


def test_program_map_is_stale_for_missing_old_and_fresh_maps(
    tmp_path: Path, monkeypatch
) -> None:
    assert roadmap.program_map_is_stale(tmp_path) is True

    map_path = tmp_path / ".renmark" / "memory" / "project-map.md"
    map_path.parent.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(roadmap, "_git_short_sha", lambda repo: "abc123")

    map_path.write_text(
        "<!-- Last refreshed: 2026-06-14 @ deadbeef -->\n# Project Map\n",
        encoding="utf-8",
    )
    assert roadmap.program_map_is_stale(tmp_path) is True

    map_path.write_text(
        "<!-- Last refreshed: 2026-06-14 @ abc123 -->\n# Project Map\n",
        encoding="utf-8",
    )
    assert roadmap.program_map_is_stale(tmp_path) is False


def test_legacy_render_table_path_still_runs() -> None:
    rows = [
        roadmap.RoadmapRow(
            task="task 1",
            llm="codex",
            status="shipped",
            tokens=1200,
            cost_usd=0.06,
            commit="abc123",
        )
    ]

    rendered = roadmap.render_table(rows)

    assert "| task 1 | codex | shipped | 1,200 | $0.060 | `abc123` |" in rendered

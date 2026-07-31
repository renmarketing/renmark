from __future__ import annotations

from renmark import reports
from renmark.cli._engine import _delivery_state_line
from renmark.delivery_state import DeliveryState, write_delivery_state

NOW = "2026-07-30T12:00:00Z"


def test_report_carries_delivery_ids_through_metrics_and_resume_facing_markdown(tmp_path):
    report = reports.build_feature_report(
        tmp_path,
        feature="migration-readiness",
        delivery_milestone_id="m6-migration",
        delivery_work_package_id="m6-migration--reporting",
        task_id="4",
        now=NOW,
    )

    assert report["delivery_milestone_id"] == "m6-migration"
    assert report["delivery_work_package_id"] == "m6-migration--reporting"
    assert report["task_id"] == "4"

    markdown = reports.render_report_md(report)
    assert "- delivery_milestone_id: m6-migration" in markdown
    assert "- delivery_work_package_id: m6-migration--reporting" in markdown
    assert "- task_id: 4" in markdown


def test_legacy_report_reader_surface_accepts_task_only_identity_without_inference():
    legacy_report = {
        "feature": "legacy-feature",
        "task_id": "17",
        "branch": "main",
    }

    markdown = reports.render_report_md(legacy_report)

    assert "- delivery_milestone_id: (none)" in markdown
    assert "- delivery_work_package_id: (none)" in markdown
    assert "- task_id: 17" in markdown


def test_task_index_never_becomes_a_delivery_identity(tmp_path):
    report = reports.build_feature_report(
        tmp_path,
        feature="index-is-not-identity",
        task_id="4",
        now=NOW,
    )

    assert report["delivery_milestone_id"] == ""
    assert report["delivery_work_package_id"] == ""


def test_resume_summary_and_report_output_remain_bounded(tmp_path, monkeypatch):
    import renmark.lifecycle as lifecycle

    monkeypatch.setattr(
        lifecycle,
        "read_legacy_delivery_summary",
        lambda repo: type("Summary", (), {
            "canonical_delivery": DeliveryState(),
            "drift_repair_notes": [],
        })(),
    )
    write_delivery_state(
        tmp_path,
        DeliveryState(active_milestone_id=("Milestone " * 40).strip()),
    )
    report = reports.build_feature_report(
        tmp_path,
        feature="bounded",
        delivery_milestone_id="m6",
        delivery_work_package_id="m6--reporting",
        now=NOW,
    )

    line = _delivery_state_line(tmp_path)
    markdown = reports.render_report_md({**report, "untrusted_transcript": "x" * 100_000})

    assert "\n" not in line
    assert len(line) <= 240
    assert "untrusted_transcript" not in markdown
    assert "x" * 100 not in markdown


def test_resume_summary_bounds_legacy_unbounded_milestone_display(tmp_path, monkeypatch):
    import renmark.delivery_state as delivery_state
    import renmark.lifecycle as lifecycle

    milestone = "legacy-milestone-" + "x" * 100
    state = DeliveryState()
    state.active_milestone_id = milestone
    monkeypatch.setattr(
        delivery_state,
        "read_delivery_state_with_report",
        lambda repo: (state, type("Report", (), {"state": "loaded"})()),
    )
    monkeypatch.setattr(
        lifecycle,
        "read_legacy_delivery_summary",
        lambda repo: type("Summary", (), {
            "canonical_delivery": DeliveryState(),
            "drift_repair_notes": [],
        })(),
    )

    line = _delivery_state_line(tmp_path)
    fields = dict(part.split("=", 1) for part in line.split()[1:])

    assert state.active_milestone_id == milestone
    assert fields["active_milestone"] == f"{milestone[:45]}..."
    assert len(fields["active_milestone"]) == 48

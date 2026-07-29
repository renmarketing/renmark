import json
from pathlib import Path

from renmark import agency as agency_mod
from renmark import lifecycle as lifecycle_mod
from renmark.delivery_state import CONTRACT_VERSION
from renmark.delivery_state import DeliveryState as CanonicalDeliveryState
from renmark.delivery_state import DeliveryProvenanceEvent
from renmark.delivery_state import WorkPackageSummary
from renmark.lifecycle import read_legacy_delivery_summary
from renmark.mode import mode_state_path
from renmark.program import program_json_path


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def test_legacy_delivery_summary_projects_one_canonical_run(
    tmp_path: Path, monkeypatch
) -> None:
    state_dir = tmp_path / ".renmark" / "state"

    def compat_clean_text(value: str, limit: int = 48) -> str:
        return " ".join(value.split())[:limit]

    def compat_delivery_state(**kwargs: object) -> CanonicalDeliveryState:
        raw_packages = kwargs.get("work_packages", [])
        raw_events = kwargs.get("provenance_events", [])
        kwargs["work_packages"] = [
            item
            if isinstance(item, WorkPackageSummary)
            else WorkPackageSummary(**{**item, "package_id": ""})
            for item in raw_packages
        ]
        kwargs["provenance_events"] = [
            item if isinstance(item, DeliveryProvenanceEvent) else DeliveryProvenanceEvent(**item)
            for item in raw_events
        ]
        return CanonicalDeliveryState(**kwargs)

    def compat_append_provenance_event(
        state: CanonicalDeliveryState, *, ts: str, kind: str, detail: str = "", source: str = "", ref: str = ""
    ) -> CanonicalDeliveryState:
        state.provenance_events = [
            *state.provenance_events,
            DeliveryProvenanceEvent(
                ts=ts,
                kind=kind,
                detail=detail,
                source=source,
                ref=ref,
            ).normalized(),
        ][-24:]
        return state

    monkeypatch.setattr(agency_mod, "_clean_text", compat_clean_text)
    monkeypatch.setattr(agency_mod, "append_provenance_event", compat_append_provenance_event)
    monkeypatch.setattr(lifecycle_mod, "DeliveryState", compat_delivery_state)
    monkeypatch.setattr(lifecycle_mod, "append_provenance_event", compat_append_provenance_event)

    _write_json(
        state_dir / "agency.json",
        {
            "active": True,
            "current_phase": "   ",
            "current_milestone": "Go Live / Wave 1",
            "next_checkpoint": "Checklist / Final QA",
            "signoff_status": "approved",
            "cost_lane": "lean",
            "roadmap_ref": "docs/roadmap.md",
        },
    )
    _write_json(
        program_json_path(tmp_path),
        {
            "feature": "Delivery projection",
            "mode": "staged",
            "created_at": "2026-07-29T00:00:00+00:00",
            "current_stage_id": "verify",
            "stages": [
                {
                    "id": "verify",
                    "title": "Verify",
                    "serves": "REQ-25",
                    "status": "in_progress",
                    "pipeline_phases": ["verify"],
                    "tasks": [
                        {
                            "id": "smoke-pass",
                            "title": "Smoke Pass",
                            "status": "pending",
                            "retry_count": 0,
                            "pipeline_phases": ["verify"],
                            "summary": "  confirm  release blockers  ",
                        }
                    ],
                }
            ],
        },
    )
    _write_json(
        state_dir / "lifecycle.json",
        {
            "feature": "Delivery projection",
            "stage": "plan-drafted",
            "stages_completed": ["brainstorm-complete"],
            "artifacts": {},
            "next_recommended": "/renmark:check-plan",
            "last_updated": "2026-07-29T00:00:00+00:00",
        },
    )
    _write_json(
        state_dir / "pipeline.json",
        {
            "current_phase": "paused",
            "current_plan": ".renmark/plans/delivery.plan.md",
            "wave_index": 1,
            "wave_total": 3,
            "completed_tasks": [1],
            "failed_tasks": [],
            "last_updated": "2026-07-29T00:00:00+00:00",
        },
    )
    _write_json(mode_state_path(tmp_path), {"mode": "conductor"})

    summary = read_legacy_delivery_summary(tmp_path)
    delivery = summary.canonical_delivery
    payload = summary.as_dict()

    assert delivery.delivery_mode == "agency"
    assert delivery.delivery_mode != "conductor"
    assert delivery.execution_policy == "guided"
    assert delivery.active_milestone_id == "go-live-wave-1"
    assert delivery.work_packages[0].milestone_id == "go-live-wave-1"
    assert delivery.work_packages[0].package_id == "go-live-wave-1--checklist-final-qa"
    assert delivery.work_packages[0].summary == "Go Live / Wave 1"
    assert delivery.approval_status == "approved"
    assert delivery.review_status == "approved"
    assert delivery.contract_version == CONTRACT_VERSION
    assert payload["delivery"]["contract_version"] == CONTRACT_VERSION
    assert "freshness" not in payload
    assert "freshness" not in payload["delivery"]

    assert 1 <= len(summary.notes) <= 5
    assert any("empty current_phase" in note for note in summary.notes)
    assert any("contradictory active states" in note for note in summary.notes)
    assert any("lifecycle/program drift" in note for note in summary.notes)
    assert any("runtime/workflow drift" in note for note in summary.notes)
    assert len(delivery.provenance_events) == 1 + min(3, len(summary.notes))

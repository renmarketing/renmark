from __future__ import annotations

from types import SimpleNamespace
from pathlib import Path

from renmark import cli
from renmark.cli._engine import _delivery_state_line
from renmark.delivery_state import DeliveryState, write_delivery_state


def _stub_legacy_summary(
    monkeypatch,
    *,
    canonical_delivery: DeliveryState | None = None,
    drift_repair_notes: tuple[str, ...] = (),
) -> None:
    import renmark.lifecycle as lifecycle

    monkeypatch.setattr(
        lifecycle,
        "read_legacy_delivery_summary",
        lambda repo: SimpleNamespace(
            canonical_delivery=canonical_delivery or DeliveryState(),
            drift_repair_notes=list(drift_repair_notes),
        ),
    )


def _run_delivery_state_cli(repo: Path, capsys) -> str:
    rc = cli.main(["--repo", str(repo), "--delivery-state"])
    assert rc == 0
    captured = capsys.readouterr()
    assert captured.err == ""
    return captured.out.strip()


def test_delivery_state_cli_reports_missing_state_without_creating_it(
    tmp_path: Path, capsys, monkeypatch
) -> None:
    _stub_legacy_summary(monkeypatch)

    line = _run_delivery_state_cli(tmp_path, capsys)

    assert line == (
        "delivery_state "
        "delivery_mode=orchestrator "
        "execution_policy=guided "
        "active_milestone=(none) "
        "contract_version=delivery-state/v1 "
        "freshness=missing "
        "drift_count=0"
    )
    assert not (tmp_path / ".renmark" / "state" / "delivery.json").exists()


def test_delivery_state_cli_reports_loaded_clean_state(
    tmp_path: Path, capsys, monkeypatch
) -> None:
    _stub_legacy_summary(monkeypatch)
    write_delivery_state(
        tmp_path,
        DeliveryState(
            delivery_mode="agency",
            execution_policy="async",
            active_milestone_id="Milestone Alpha",
            contract_version="delivery-state/v9",
        ),
    )

    line = _run_delivery_state_cli(tmp_path, capsys)

    assert line == (
        "delivery_state "
        "delivery_mode=agency "
        "execution_policy=async "
        "active_milestone=milestone-alpha "
        "contract_version=delivery-state/v9 "
        "freshness=loaded "
        "drift_count=0"
    )


def test_delivery_state_summary_maps_legacy_conductor_tokens(
    tmp_path: Path, monkeypatch
) -> None:
    _stub_legacy_summary(monkeypatch)
    write_delivery_state(
        tmp_path,
        DeliveryState(delivery_mode="conductor", execution_policy="conductor"),
    )

    line = _delivery_state_line(tmp_path)

    assert "delivery_mode=orchestrator" in line
    assert "execution_policy=guided" in line


def test_delivery_state_summary_includes_drift_count(tmp_path: Path, monkeypatch) -> None:
    _stub_legacy_summary(monkeypatch, drift_repair_notes=("one", "two", "three"))
    write_delivery_state(tmp_path, DeliveryState())

    line = _delivery_state_line(tmp_path)

    assert "freshness=loaded" in line
    assert line.endswith("drift_count=3")


def test_delivery_state_summary_is_bounded(tmp_path: Path, monkeypatch) -> None:
    _stub_legacy_summary(monkeypatch)
    write_delivery_state(
        tmp_path,
        DeliveryState(
            active_milestone_id=("Milestone " * 40).strip(),
            contract_version="c" * 200,
        ),
    )

    line = _delivery_state_line(tmp_path)
    fields = dict(part.split("=", 1) for part in line.split()[1:])

    assert "\n" not in line
    assert len(line) <= 240
    assert len(fields["active_milestone"]) <= 48
    assert len(fields["contract_version"]) <= 40


def test_delivery_state_inspection_does_not_mutate_state_file(
    tmp_path: Path, monkeypatch
) -> None:
    _stub_legacy_summary(monkeypatch)
    path = write_delivery_state(
        tmp_path,
        DeliveryState(
            delivery_mode="agency",
            execution_policy="direct",
            active_milestone_id="Launch Review",
        ),
    )
    before = path.read_text(encoding="utf-8")

    line = _delivery_state_line(tmp_path)

    assert "freshness=loaded" in line
    assert path.read_text(encoding="utf-8") == before

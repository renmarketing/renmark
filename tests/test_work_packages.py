"""Direct compatibility tests for milestone work-package compilation."""

from __future__ import annotations

from pathlib import Path

import pytest

from renmark.parser import Milestone, PackagePlan, WorkPackage
from renmark.work_packages import (
    PackageCompilationError,
    compile_or_fallback,
    compile_package_plan,
    compile_work_package,
    legacy_tasks,
)


def _package(*, dependencies: list[str] | None = None, status: str = "pending") -> WorkPackage:
    return WorkPackage(
        id="m3--compiler", goal="Compile package", expected_outcome="legacy packets",
        acceptance_evidence=["pytest -q"], dependencies=dependencies or ["none"],
        risks=["compatibility"], allowed_surfaces=["implementation", "tests"],
        cost_lane="standard", demo_point="tests pass", signoff_policy="owner", status=status,
    )


def test_compiler_emits_unchanged_legacy_tasks_with_sidecar_metadata() -> None:
    packets = compile_work_package(
        _package(dependencies=[".renmark/reviews/upstream.md"]), milestone_id="m3",
        surface_targets={"implementation": "renmark/work_packages.py", "tests": "tests/test_work_packages.py"},
        verifier="pytest -q tests/test_work_packages.py",
    )
    tasks = legacy_tasks(packets)
    assert [task.index for task in tasks] == [1, 2]
    assert [task.target for task in tasks] == ["renmark/work_packages.py", "tests/test_work_packages.py"]
    assert packets[0].metadata.package_id == "m3--compiler"
    assert packets[0].metadata.dependency_artifacts == (".renmark/reviews/upstream.md",)
    assert not hasattr(tasks[0], "metadata")


def test_compiler_keeps_multifile_scope_to_allowed_targets() -> None:
    packets = compile_work_package(
        _package(), milestone_id="m3",
        surface_targets={"implementation": "renmark/work_packages.py", "tests": "tests/test_work_packages.py"},
    )
    assert packets[0].task.context_files == ["tests/test_work_packages.py"]
    assert packets[1].task.context_files == ["renmark/work_packages.py"]


def test_compiler_rejects_non_artifact_dependencies() -> None:
    with pytest.raises(PackageCompilationError, match="artifact pointers"):
        compile_work_package(
            _package(dependencies=["paste the transcript here"]), milestone_id="m3",
            surface_targets={"implementation": "renmark/work_packages.py", "tests": "tests/test_work_packages.py"},
        )


def test_disabled_package_compiler_skips_package_backend() -> None:
    plan = PackagePlan("agency", [Milestone("m3", "goal", "outcome", [_package()])])
    assert compile_package_plan(plan, surface_targets={}, enabled=False) == []


def test_disabled_compiler_falls_back_to_legacy_plan(tmp_path: Path) -> None:
    legacy = tmp_path / "legacy.plan.md"
    legacy.write_text(
        "### Task 1: legacy\n- **mode:** A\n- **target:** a.py\n- **verifier:** true\n- **spec:** x\n",
        encoding="utf-8",
    )
    tasks = compile_or_fallback(str(legacy), enabled=False)
    assert len(tasks) == 1
    assert tasks[0].title == "legacy"

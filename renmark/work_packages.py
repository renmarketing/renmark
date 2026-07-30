"""Compile bounded milestone work packages to the legacy :class:`Task` backend.

The legacy executor deliberately continues to receive ordinary ``Task``
objects.  Package provenance is held beside each task in ``CompiledTask`` so
adding this adapter cannot change the ``Task`` wire shape used by existing
dispatch and plan-lint callers.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import PurePosixPath

from renmark.parser import PackagePlan, Task, WorkPackage, parse_plan


class PackageCompilationError(ValueError):
    """Raised when a package cannot safely be represented by legacy tasks."""


@dataclass(frozen=True)
class TaskPacketMetadata:
    """Bounded package provenance kept outside the legacy ``Task`` contract."""

    milestone_id: str
    package_id: str
    dependency_artifacts: tuple[str, ...]
    allowed_surfaces: tuple[str, ...]


@dataclass(frozen=True)
class CompiledTask:
    """A legacy task together with non-wire package metadata."""

    task: Task
    metadata: TaskPacketMetadata


def compile_work_package(
    package: WorkPackage,
    *,
    milestone_id: str,
    surface_targets: Mapping[str, str],
    start_index: int = 1,
    mode: str = "B",
    executor: str = "codex",
    verifier: str = "true",
) -> list[CompiledTask]:
    """Compile one package to one legacy task per allowed surface.

    ``surface_targets`` is deliberately supplied by the caller: package plans
    name bounded *kinds* of permitted work, while legacy tasks need a concrete
    repository-relative target.  This keeps package schemas portable and makes
    multi-file implementation-plus-test packages explicit at the adapter edge.
    """
    if start_index < 1:
        raise PackageCompilationError("start_index must be >= 1")
    if mode not in {"A", "B"}:
        raise PackageCompilationError("legacy task mode must be A or B")
    if not verifier.strip():
        raise PackageCompilationError("verifier must be non-empty")

    dependencies = _artifact_dependencies(package.dependencies)
    surfaces = tuple(package.allowed_surfaces)
    targets: list[tuple[str, str]] = []
    for surface in surfaces:
        target = surface_targets.get(surface)
        if not target:
            raise PackageCompilationError(f"missing target for allowed surface {surface!r}")
        _validate_target(target)
        targets.append((surface, target))
    if len({target for _, target in targets}) != len(targets):
        raise PackageCompilationError("allowed surfaces must map to distinct targets")

    metadata = TaskPacketMetadata(
        milestone_id=milestone_id,
        package_id=package.id,
        dependency_artifacts=dependencies,
        allowed_surfaces=surfaces,
    )
    compiled: list[CompiledTask] = []
    all_targets = [target for _, target in targets]
    for offset, (surface, target) in enumerate(targets):
        peers = [candidate for candidate in all_targets if candidate != target]
        task = Task(
            index=start_index + offset,
            title=f"{package.goal} ({surface})",
            mode=mode,
            target=target,
            context_files=peers,
            verifier=verifier,
            spec=_bounded_spec(package, surface, dependencies),
            executor=executor,
        )
        compiled.append(CompiledTask(task=task, metadata=metadata))
    return compiled


def compile_package_plan(
    plan: PackagePlan,
    *,
    surface_targets: Mapping[str, Mapping[str, str]],
    enabled: bool = True,
    mode: str = "B",
    executor: str = "codex",
    verifier: str = "true",
) -> list[CompiledTask]:
    """Compile pending packages in a plan, or return no package packets when disabled."""
    if not enabled:
        return []
    compiled: list[CompiledTask] = []
    next_index = 1
    for milestone in plan.milestones:
        for package in milestone.work_packages:
            if package.status not in {"pending", "in_progress"}:
                continue
            packets = compile_work_package(
                package,
                milestone_id=milestone.id,
                surface_targets=surface_targets.get(package.id, {}),
                start_index=next_index,
                mode=mode,
                executor=executor,
                verifier=verifier,
            )
            compiled.extend(packets)
            next_index += len(packets)
    return compiled


def compile_or_fallback(
    plan: PackagePlan | str,
    *,
    surface_targets: Mapping[str, Mapping[str, str]] | None = None,
    enabled: bool = True,
    mode: str = "B",
    executor: str = "codex",
    verifier: str = "true",
) -> list[CompiledTask] | list[Task]:
    """Use packages when enabled; otherwise preserve the legacy plan backend.

    The fallback accepts a legacy markdown plan path and returns exactly the
    existing ``parse_plan`` result, avoiding a partial feature flag migration.
    """
    if not enabled:
        if not isinstance(plan, str):
            return []
        return parse_plan(plan)
    if not isinstance(plan, PackagePlan):
        raise PackageCompilationError("enabled package compilation requires a PackagePlan")
    return compile_package_plan(
        plan,
        surface_targets=surface_targets or {},
        mode=mode,
        executor=executor,
        verifier=verifier,
    )


def legacy_tasks(packets: Sequence[CompiledTask]) -> list[Task]:
    """Extract unchanged legacy tasks for existing executor call sites."""
    return [packet.task for packet in packets]


def _artifact_dependencies(dependencies: Sequence[str]) -> tuple[str, ...]:
    result: list[str] = []
    for dependency in dependencies:
        if dependency == "none":
            continue
        if not dependency.startswith(".renmark/") or any(
            marker in dependency.lower() for marker in ("transcript", "diff", "patch", "generated_code")
        ):
            raise PackageCompilationError(
                "dependencies must be bounded .renmark artifact pointers (or 'none')"
            )
        _validate_target(dependency)
        result.append(dependency)
    return tuple(result)


def _validate_target(target: str) -> None:
    path = PurePosixPath(target)
    if not target or path.is_absolute() or ".." in path.parts:
        raise PackageCompilationError(f"target must be a repository-relative path: {target!r}")


def _bounded_spec(package: WorkPackage, surface: str, dependencies: tuple[str, ...]) -> str:
    dependency_note = ", ".join(dependencies) if dependencies else "none"
    return (
        f"Package {package.id}; milestone-scoped outcome: {package.expected_outcome}. "
        f"Implement only the {surface} allowed surface. "
        f"Acceptance evidence: {'; '.join(package.acceptance_evidence)}. "
        f"Dependency artifacts: {dependency_note}."
    )

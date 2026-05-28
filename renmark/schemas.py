"""JSON-shape validators for renmark's canonical state files and artifact
payloads. Zero external dependencies — validation is structural, not full
JSON Schema. Returns lists of human-readable issues; empty list = valid.

Validators cover:
    - lifecycle.json       (workflow state, G12)
    - pipeline.json        (runtime state)
    - SubagentOutput JSON  (G11 task isolation)
    - ArtifactMetadata     (YAML frontmatter, G6)

CLI:
    python -m renmark.schemas lifecycle  <path>
    python -m renmark.schemas pipeline   <path>
    python -m renmark.schemas subagent   <path>
    python -m renmark.schemas artifact   <path>

Exit code 0 = valid, 1 = invalid, 2 = bad CLI usage.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

from renmark.dispatch import (
    SUBAGENT_OUTPUT_COMPLETION_STATES,
    SUBAGENT_OUTPUT_CONFIDENCE_VALUES,
    SUBAGENT_OUTPUT_FIELDS,
    SUBAGENT_OUTPUT_STATUS_VALUES,
)
from renmark.lifecycle import STAGES

# ── Lifecycle ────────────────────────────────────────────────────────────────

LIFECYCLE_FIELDS = {
    "feature": (str, True),
    "branch": (str, True),
    "github_issue": ((int, type(None)), True),
    "stage": (str, True),
    "stages_completed": (list, True),
    "artifacts": (dict, True),
    "human_review_required": (bool, True),
    "human_review_completed": (bool, True),
    "human_review_for": ((str, type(None)), True),
    "next_recommended": (str, True),
    "last_updated": (str, True),
}


def validate_lifecycle(data: Any) -> list[str]:
    """Return list of issues in a lifecycle.json payload. Empty = valid."""
    issues: list[str] = []
    if not isinstance(data, dict):
        return [f"lifecycle: expected object, got {type(data).__name__}"]

    issues.extend(_check_fields(data, LIFECYCLE_FIELDS, "lifecycle"))

    stage = data.get("stage")
    if isinstance(stage, str) and stage not in STAGES:
        issues.append(f"lifecycle.stage={stage!r} not in canonical STAGES")

    completed = data.get("stages_completed")
    if isinstance(completed, list):
        for s in completed:
            if not isinstance(s, str):
                issues.append(f"lifecycle.stages_completed has non-string: {s!r}")
            elif s not in STAGES:
                issues.append(f"lifecycle.stages_completed has unknown stage: {s!r}")

    artifacts = data.get("artifacts")
    if isinstance(artifacts, dict):
        for k, v in artifacts.items():
            if not isinstance(v, str):
                issues.append(f"lifecycle.artifacts[{k!r}] expected str, got {type(v).__name__}")

    # Size budget — runtime cruft check.
    payload = json.dumps(data).encode("utf-8")
    if len(payload) > 1024:
        issues.append(f"lifecycle.json is {len(payload)} bytes (budget 1024) — runtime cruft has leaked")

    return issues


# ── Pipeline ─────────────────────────────────────────────────────────────────

PIPELINE_FIELDS = {
    "current_phase": (str, True),
    "current_plan": (str, True),
    "wave_index": (int, True),
    "wave_total": (int, True),
    "completed_tasks": (list, True),
    "failed_tasks": (list, True),
    "last_updated": (str, True),
}

PIPELINE_PHASES = {"idle", "orchestrate", "paused"}


def validate_pipeline(data: Any) -> list[str]:
    issues: list[str] = []
    if not isinstance(data, dict):
        return [f"pipeline: expected object, got {type(data).__name__}"]

    issues.extend(_check_fields(data, PIPELINE_FIELDS, "pipeline"))

    phase = data.get("current_phase")
    if isinstance(phase, str) and phase not in PIPELINE_PHASES:
        issues.append(f"pipeline.current_phase={phase!r} not in {sorted(PIPELINE_PHASES)}")

    for key in ("completed_tasks", "failed_tasks"):
        seq = data.get(key)
        if isinstance(seq, list):
            for i, v in enumerate(seq):
                if not isinstance(v, int):
                    issues.append(f"pipeline.{key}[{i}] expected int, got {type(v).__name__}")

    return issues


# ── SubagentOutput ───────────────────────────────────────────────────────────

SUBAGENT_OUTPUT_TYPES = {
    "status": str,
    "artifact_path": str,
    "touched_files": list,
    "sha": (str, type(None)),
    "summary_lines": list,
    "dependency_notes": str,
    "token_count": int,
    "completion_state": str,
    "confidence": str,
    "retry_count": int,
}


def validate_subagent_output(data: Any) -> list[str]:
    """Validate a SubagentOutput-shaped JSON dict. G11 isolation: rejects
    ANY field outside SUBAGENT_OUTPUT_FIELDS (transcript, diff, reasoning,
    generated_code, etc.).
    """
    issues: list[str] = []
    if not isinstance(data, dict):
        return [f"subagent: expected object, got {type(data).__name__}"]

    # G11 leakage check — extra fields are isolation violations.
    extra = set(data.keys()) - SUBAGENT_OUTPUT_FIELDS
    if extra:
        issues.append(
            f"subagent: G11 isolation violation — extra fields {sorted(extra)} not in {sorted(SUBAGENT_OUTPUT_FIELDS)}"
        )

    for field, expected_type in SUBAGENT_OUTPUT_TYPES.items():
        if field not in data:
            # status + artifact_path are required; others have defaults.
            if field in ("status", "artifact_path"):
                issues.append(f"subagent: required field {field!r} missing")
            continue
        if not _isinstance(data[field], expected_type):
            issues.append(f"subagent.{field} expected {_typename(expected_type)}, got {type(data[field]).__name__}")

    status = data.get("status")
    if isinstance(status, str) and status not in SUBAGENT_OUTPUT_STATUS_VALUES:
        issues.append(f"subagent.status={status!r} not in {sorted(SUBAGENT_OUTPUT_STATUS_VALUES)}")

    cs = data.get("completion_state")
    if isinstance(cs, str) and cs not in SUBAGENT_OUTPUT_COMPLETION_STATES:
        issues.append(f"subagent.completion_state={cs!r} not in {sorted(SUBAGENT_OUTPUT_COMPLETION_STATES)}")

    conf = data.get("confidence")
    if isinstance(conf, str) and conf not in SUBAGENT_OUTPUT_CONFIDENCE_VALUES:
        issues.append(f"subagent.confidence={conf!r} not in {sorted(SUBAGENT_OUTPUT_CONFIDENCE_VALUES)}")

    summary = data.get("summary_lines")
    if isinstance(summary, list):
        if len(summary) > 5:
            issues.append(f"subagent.summary_lines has {len(summary)} entries — G3 cap is 5")
        for i, line in enumerate(summary):
            if not isinstance(line, str):
                issues.append(f"subagent.summary_lines[{i}] expected str, got {type(line).__name__}")
            elif len(line) > 1200:
                issues.append(f"subagent.summary_lines[{i}] is {len(line)} chars — G3 cap is 1200")

    return issues


# ── ArtifactMetadata (G6) ────────────────────────────────────────────────────

ARTIFACT_METADATA_FIELDS = {
    "artifact_type": (str, True),
    "schema_version": ((str, int), True),
    "created_at": (str, True),
    "source_sha": ((str, type(None)), False),
    "related_plan": ((str, type(None)), False),
    "generator": (str, True),
    "stale_after": ((str, type(None)), False),
    "dependency_refs": (list, False),
    "completion_state": (str, False),
    "confidence": (str, False),
    "validation_status": (str, False),
    "retry_count": (int, False),
    "parser_success": (bool, False),
    "schema_compliance": (bool, False),
}

ARTIFACT_COMPLETION_STATES = {"complete", "partial", "failed"}
ARTIFACT_CONFIDENCES = {"low", "medium", "high"}
ARTIFACT_VALIDATION_STATES = {"validated", "unvalidated", "failed"}


def validate_artifact_metadata(data: Any) -> list[str]:
    issues: list[str] = []
    if not isinstance(data, dict):
        return [f"artifact: expected object, got {type(data).__name__}"]

    issues.extend(_check_fields(data, ARTIFACT_METADATA_FIELDS, "artifact"))

    cs = data.get("completion_state")
    if isinstance(cs, str) and cs not in ARTIFACT_COMPLETION_STATES:
        issues.append(f"artifact.completion_state={cs!r} not in {sorted(ARTIFACT_COMPLETION_STATES)}")
    conf = data.get("confidence")
    if isinstance(conf, str) and conf not in ARTIFACT_CONFIDENCES:
        issues.append(f"artifact.confidence={conf!r} not in {sorted(ARTIFACT_CONFIDENCES)}")
    vs = data.get("validation_status")
    if isinstance(vs, str) and vs not in ARTIFACT_VALIDATION_STATES:
        issues.append(f"artifact.validation_status={vs!r} not in {sorted(ARTIFACT_VALIDATION_STATES)}")

    return issues


# ── Helpers ──────────────────────────────────────────────────────────────────


def _check_fields(data: dict[str, Any], spec: dict[str, tuple[Any, ...]], scope: str) -> list[str]:
    issues: list[str] = []
    for field, (expected_type, required) in spec.items():
        if field not in data:
            if required:
                issues.append(f"{scope}: required field {field!r} missing")
            continue
        if not _isinstance(data[field], expected_type):
            issues.append(f"{scope}.{field} expected {_typename(expected_type)}, got {type(data[field]).__name__}")
    return issues


def _isinstance(value: Any, expected: Any) -> bool:
    # bool is a subclass of int — exclude it when expecting int.
    if expected is int and isinstance(value, bool):
        return False
    if isinstance(expected, tuple):
        if int in expected and bool not in expected and isinstance(value, bool):
            return False
        return isinstance(value, expected)
    return isinstance(value, expected)


def _typename(expected: Any) -> str:
    if isinstance(expected, tuple):
        return " | ".join(getattr(t, "__name__", str(t)) for t in expected)
    return getattr(expected, "__name__", str(expected))


# ── CLI ──────────────────────────────────────────────────────────────────────


VALIDATORS: dict[str, Callable[[Any], list[str]]] = {
    "lifecycle": validate_lifecycle,
    "pipeline": validate_pipeline,
    "subagent": validate_subagent_output,
    "artifact": validate_artifact_metadata,
}


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 2 or argv[0] not in VALIDATORS:
        sys.stderr.write("usage: python -m renmark.schemas {lifecycle|pipeline|subagent|artifact} <path>\n")
        return 2

    kind, path = argv
    p = Path(path)
    if not p.exists():
        sys.stderr.write(f"file not found: {p}\n")
        return 2

    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        sys.stderr.write(f"failed to parse {p}: {exc}\n")
        return 1

    issues = VALIDATORS[kind](data)
    if issues:
        for issue in issues:
            sys.stderr.write(f"  - {issue}\n")
        sys.stderr.write(f"FAIL ({len(issues)} issue{'s' if len(issues) != 1 else ''})\n")
        return 1

    sys.stdout.write(f"OK  {kind}  {p}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())

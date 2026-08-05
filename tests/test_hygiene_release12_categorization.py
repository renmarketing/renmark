"""
---
artifact_type: test
schema_version: 1
created_at: 2026-08-05T00:00:00Z
source_sha: b44f95b5c8964f99c46867fad93c58868ec61078
related_plan: .renmark/plans/release-12.plan.md
generator: codex
stale_after: null
dependency_refs:
  - renmark.hygiene
  - renmark.recurrence
  - renmark.context
completion_state: complete
confidence: high
validation_status: unvalidated
retry_count: 0
parser_success: true
schema_compliance: true
---

## Body

Release 12 Task 4 regression tests for hygiene categorization, review-sweep surfacing, and the context snapshot guard.

## Summary
- Covers the 7-way registry partition and confirms every registered artifact lands in exactly one bucket.
- Verifies `scan` reports a due-for-review failure rule without mutating the stored rule status.
- Guards the current `renmark/context.py` source hash and `ContextKind` member order.
"""

from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

import pytest

from renmark.context import ContextKind
from renmark.hygiene import ARTIFACT_REGISTRY, categorize_seven_way, compute_seven_way_report
from renmark.recurrence import activate_failure_rule, load_failure_rules, propose_failure_rule

EXPECTED_CONTEXT_SHA256 = "ad1a1c3e209fb1c1901688058b580eadfee16ad3d7b5f6da86962be72030931a"
EXPECTED_CONTEXT_KIND_NAMES = ("STATIC", "DYNAMIC", "MEMORY", "TASK_LOCAL")
EXPECTED_SEVEN_WAY_CATEGORIES = {
    "receipts",
    "canonical_artifacts",
    "lifecycle_state",
    "bounded_task_context",
    "failure_rule_registry",
    "stable_preferences",
    "ephemeral_conversation",
}


def _write_file(repo: Path, relative_path: str) -> None:
    path = repo / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"seeded for {relative_path}\n", encoding="utf-8")


def _seed_seven_way_repo(repo: Path) -> dict[str, str]:
    seeded_paths = {
        "audits": "audits/sample.md",
        "plans": "plans/sample.md",
        "reviews": "reviews/sample.md",
        "state-live": "state/lifecycle.json",
        "state-scratch": "state/escalations/sample.md",
        "memory": "memory/sample.md",
        "ledger": "ledger/events.jsonl",
        "reports": "reports/features/alpha/sample.md",
        "rethink": "rethink/release/sample.md",
        "roadmap": "roadmap/sample.md",
        "specs": "specs/sample.md",
        "debug": "debug/session/sample.md",
        "version-unpacked": "version/v1/sample.md",
        "version-zip": "version/release.zip",
    }
    for relative_path in seeded_paths.values():
        _write_file(repo, relative_path)
    return seeded_paths


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    return tmp_path


def test_seven_way_report_partitions_every_registry_entry_once(repo: Path) -> None:
    _seed_seven_way_repo(repo)

    report = compute_seven_way_report(repo)

    assert set(report) == EXPECTED_SEVEN_WAY_CATEGORIES

    all_report_names = [name for bucket in report.values() for name in bucket]
    assert len(all_report_names) == len(ARTIFACT_REGISTRY)
    assert len(all_report_names) == len(set(all_report_names))
    assert set(all_report_names) == {spec.name for spec in ARTIFACT_REGISTRY}

    categorized_names: list[str] = []
    seen_names: set[str] = set()
    for spec in ARTIFACT_REGISTRY:
        category = categorize_seven_way(spec)
        assert category in report
        categorized_names.append(spec.name)

        assert spec.name in report[category]
        assert spec.name not in seen_names
        seen_names.add(spec.name)

    assert len(categorized_names) == len(ARTIFACT_REGISTRY)
    assert len(categorized_names) == len(set(categorized_names))


def test_scan_reports_due_for_review_without_mutating_rule_status(repo: Path) -> None:
    rule = propose_failure_rule(
        repo,
        rule_id="review-sweep-rule",
        trigger="stale review follow-up",
        applicability="scan",
        required_behavior="report due-for-review failure rules",
        prohibited_failure="mutate failure rule status",
        source_evidence=("release-12-task-4",),
        review_after="2024-01-01T00:00:00Z",
        created_at="2026-08-05T00:00:00Z",
    )
    activate_failure_rule(repo, rule.rule_id)

    before_status = load_failure_rules(repo)[0].status
    assert before_status == "active"

    proc = subprocess.run(
        [sys.executable, "-m", "renmark.hygiene", "scan"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )

    stdout_lines = proc.stdout.splitlines()
    assert any(line.startswith("FAILURE-RULES") and "due_for_review=1" in line for line in stdout_lines)

    after_rules = load_failure_rules(repo)
    assert len(after_rules) == 1
    assert after_rules[0].status == "active"


def test_context_snapshot_and_enum_members_are_unchanged() -> None:
    context_path = Path(__file__).resolve().parents[1] / "renmark" / "context.py"
    context_text = context_path.read_text(encoding="utf-8")

    assert hashlib.sha256(context_text.encode("utf-8")).hexdigest() == EXPECTED_CONTEXT_SHA256
    assert tuple(ContextKind.__members__) == EXPECTED_CONTEXT_KIND_NAMES

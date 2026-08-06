"""
---
artifact_type: renmark_task_output
schema_version: 1
created_at: 2026-08-06T00:00:00Z
source_sha: unknown
related_plan: "task-3 governance-wiring regression test"
generator: codex
stale_after: null
dependency_refs:
  - plugin/skills/rethink/SKILL.md
completion_state: complete
confidence: medium
validation_status: unvalidated
retry_count: 0
parser_success: true
schema_compliance: true
---

Pure file-content regression coverage for the `/renmark:rethink` governance
wiring in `plugin/skills/rethink/SKILL.md`.

## Summary
- Checks the Inspector challenge heading is present and ordered between stage 8 and stage 9.
- Confirms the skill still references `ledger.emit_inspection_verdict`, `work_order_for_task`, and `resolve_lens_for`.
- Verifies the Inspector remains read-only via the roadmap-revision restriction text.
- Guards the existing three-gate / three Owner-gates language so the Inspector step is not treated as a fourth approval gate.
"""

from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_PATH = REPO_ROOT / "plugin" / "skills" / "rethink" / "SKILL.md"


def test_rethink_skill_governance_wiring() -> None:
    text = SKILL_PATH.read_text(encoding="utf-8")
    normalized = " ".join(text.split())

    stage_8 = text.index("### 8. Incremental transformation roadmap")
    inspector = text.index("### 8a. Independent Inspector challenge")
    stage_9 = text.index("### 9. Execution Gate, then hand off to milestone execution")

    assert stage_8 < inspector < stage_9
    assert "ledger.emit_inspection_verdict" in normalized
    assert "work_order_for_task" in normalized
    assert "resolve_lens_for" in normalized
    assert "may not revise the roadmap itself, only report findings" in normalized
    assert "three named Owner decision gates" in normalized

    inspector_heading_end = text.index("\n", inspector)
    inspector_heading = text[inspector:inspector_heading_end]
    assert "Gate" not in inspector_heading

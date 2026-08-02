"""Contract tests for REQ-30 — orchestration efficiency and UX stability is
a protected capability.

Static content checks over PRD.md, the named baseline artifact, CLAUDE.md/
AGENTS.md, and every pipeline SKILL.md that must cite REQ-30. Proves the
requirement exists, names a concrete pinned baseline (not a vague "current
behavior"), defines a quantified regression-block condition with an
explicit-exception escape hatch, and is actually referenced from every
pipeline it claims to bind — not just declared once and forgotten.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PRD_PATH = REPO_ROOT / "PRD.md"
CLAUDE_PATH = REPO_ROOT / "CLAUDE.md"
AGENTS_PATH = REPO_ROOT / "AGENTS.md"
BASELINE_PATH = REPO_ROOT / ".renmark" / "memory" / "orchestration-baseline.md"
MEMORY_INDEX_PATH = REPO_ROOT / ".renmark" / "memory" / "INDEX.md"

PIPELINE_SKILL_PATHS = {
    name: REPO_ROOT / "plugin" / "skills" / name / "SKILL.md"
    for name in (
        "init",
        "start",
        "feature",
        "debug",
        "roadmap",
        "finish",
        "rethink",
        "orchestrate",
    )
}


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _normalized(path: Path) -> str:
    return " ".join(_read(path).split())


# ── REQ-30 exists with the required substance ────────────────────────────────


def test_prd_declares_req30():
    text = _read(PRD_PATH)
    assert (
        "`REQ-30` **Orchestration efficiency and UX stability is a protected\n"
        "    capability.**" in text
        or "REQ-30` **Orchestration efficiency and UX stability is a protected"
        in text
    )


def test_req30_cites_existing_requirements_rather_than_restating_them():
    norm = _normalized(PRD_PATH)
    for cite in (
        "extends REQ-5, REQ-20",
        "extends REQ-3, REQ-24",
        "extends REQ-2, REQ-21",
        "extends REQ-21, REQ-24",
        "extends REQ-22, REQ-28, REQ-29",
    ):
        assert cite in norm


def test_req30_names_a_pinned_baseline_not_a_vague_reference():
    norm = _normalized(PRD_PATH)
    assert "ORCHESTRATION-BASELINE-2026-08" in norm
    assert "`v0.39.7`" in norm
    assert "commit `d9cccc5`" in norm
    assert ".renmark/memory/orchestration-baseline.md" in norm


def test_req30_defines_quantified_regression_block_with_exception_path():
    norm = _normalized(PRD_PATH)
    assert "increases median token use or execution time by more than 15%" in norm
    assert (
        "An exception requires\n      quantified evidence, explicit Owner approval, a documented benefit, and\n      a rollback path"
        in _read(PRD_PATH)
        or "An exception requires quantified evidence, explicit Owner approval, a documented benefit, and a rollback path"
        in norm
    )
    assert "new functionality alone never justifies an\n      efficiency regression" in _read(
        PRD_PATH
    ) or "new functionality alone never justifies an efficiency regression" in norm


def test_req30_requires_explicit_prd_change_for_orchestration_edits():
    norm = _normalized(PRD_PATH)
    assert (
        "requires\n      an explicit PRD change and Owner approval through `/renmark:prd`'s\n      UPDATE gate"
        in _read(PRD_PATH)
        or "requires an explicit PRD change and Owner approval through `/renmark:prd`'s UPDATE gate"
        in norm
    )
    assert "never a side effect of an unrelated feature" in norm


def test_req30_acceptance_lists_all_eight_pipelines():
    norm = _normalized(PRD_PATH)
    assert (
        "`init`, `start`, `feature`, `debug`,\n      `roadmap`, `finish`, `rethink`, and `orchestrate` each cite this"
        in _read(PRD_PATH)
        or "`init`, `start`, `feature`, `debug`, `roadmap`, `finish`, `rethink`, and `orchestrate` each cite this"
        in norm
    )


def test_goals_section_has_matching_req30_bullet():
    norm = _normalized(PRD_PATH)
    assert (
        "measured against\n  a named baseline, not a subjective impression that can silently regress as\n  new features land (REQ-30)"
        in _read(PRD_PATH)
        or "measured against a named baseline, not a subjective impression that can silently regress as new features land (REQ-30)"
        in norm
    )


def test_revision_note_documents_req30_as_protection_not_new_mechanics():
    norm = _normalized(PRD_PATH)
    assert "Added REQ-30" in norm
    assert "does not restate REQ-2/5/20/21/22/24/27's" in norm


# ── named baseline artifact exists and is registered ─────────────────────────


def test_baseline_artifact_exists_and_is_pinned():
    assert BASELINE_PATH.exists()
    text = _read(BASELINE_PATH)
    assert "ORCHESTRATION-BASELINE-2026-08" in text
    assert "v0.39.7" in text
    assert "d9cccc5" in text


def test_baseline_artifact_is_honest_about_missing_quantitative_numbers():
    norm = _normalized(BASELINE_PATH)
    assert "does **not** yet contain measured token/wall-clock/dispatch-count" in norm
    assert "not something to fabricate into a memory file" in norm


def test_baseline_artifact_names_the_four_representative_scenarios():
    text = _read(BASELINE_PATH)
    for scenario in ("Start", "Feature / Fix", "Orchestrate", "Rethink"):
        assert scenario in text


def test_memory_index_registers_the_baseline_file():
    text = _read(MEMORY_INDEX_PATH)
    assert "orchestration-baseline.md" in text
    assert "REQ-30" in text


# ── CLAUDE.md / AGENTS.md carry the operational rule, mirrored ──────────────


def test_claude_md_has_orchestration_efficiency_rule_block():
    text = _read(CLAUDE_PATH)
    assert "<!-- BEGIN:orchestration-efficiency-rule -->" in text
    assert "<!-- END:orchestration-efficiency-rule -->" in text
    assert "## Orchestration efficiency is a protected capability (REQ-30)" in text
    assert "ORCHESTRATION-BASELINE-2026-08" in text


def test_claude_md_markers_stay_balanced():
    text = _read(CLAUDE_PATH)
    assert text.count("<!-- BEGIN:") == text.count("<!-- END:")


def test_agents_md_mirrors_the_rule():
    text = _read(AGENTS_PATH)
    assert "**Orchestration efficiency is a protected capability (REQ-30).**" in text
    assert "ORCHESTRATION-BASELINE-2026-08" in text
    assert "§ `orchestration-efficiency-rule`" in text


# ── every named pipeline actually cites REQ-30 ───────────────────────────────


def test_every_pipeline_skill_cites_req30():
    for name, path in PIPELINE_SKILL_PATHS.items():
        text = _read(path)
        assert "REQ-30" in text, f"{name}/SKILL.md does not cite REQ-30"


def test_rethink_req30_citation_ties_to_dispatch_and_artifact_discipline():
    norm = _normalized(PIPELINE_SKILL_PATHS["rethink"])
    assert (
        "bound by REQ-30 (orchestration efficiency is a protected\ncapability)"
        in _read(PIPELINE_SKILL_PATHS["rethink"])
        or "bound by REQ-30" in norm
    )


def test_start_req30_citation_ties_to_fast_path_and_gate_discipline():
    norm = _normalized(PIPELINE_SKILL_PATHS["start"])
    assert "Bound by REQ-30" in norm
    assert "no routine status prompts between them" in norm


def test_orchestrate_req30_citation_names_the_skip_list_mechanism():
    norm = _normalized(PIPELINE_SKILL_PATHS["orchestrate"])
    assert "REQ-30" in norm
    assert "_cross_check_skip_list" in norm

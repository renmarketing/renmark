"""Contract tests for the expanded /renmark:rethink modernization pipeline.

These are static content checks over the shipped SKILL.md / PRD.md / help
surfaces — rethink's stages are markdown-authored governance, not a Python
state machine, so the pipeline's honest-completion, evidence, and gate rules
are proven by asserting the required contract language ships in each
surface and stays consistent across them.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILL_PATH = REPO_ROOT / "plugin" / "skills" / "rethink" / "SKILL.md"
COMMAND_PATH = REPO_ROOT / "plugin" / "commands" / "rethink.md"
PRD_PATH = REPO_ROOT / "PRD.md"
HELP_PATH = REPO_ROOT / "plugin" / "skills" / "help" / "SKILL.md"
CLAUDE_PATH = REPO_ROOT / "CLAUDE.md"
AGENTS_PATH = REPO_ROOT / "AGENTS.md"

NEW_ARTIFACTS = (
    "survey.md",
    "baseline.md",
    "prd-acceptance-map.md",
    "external-benchmark.md",
    "modularity-assessment.md",
    "classification.md",
    "target-blueprint.md",
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _normalized(path: Path) -> str:
    """Read and collapse all whitespace runs to single spaces.

    SKILL.md wraps prose at ~80 columns, so a multi-word contract phrase can
    straddle a line break; normalizing lets assertions match the phrase
    regardless of where the author wrapped it.
    """
    return " ".join(_read(path).split())


# ── stage / artifact presence ────────────────────────────────────────────────


def test_skill_declares_nine_stages():
    text = _read(SKILL_PATH)
    assert "nine bounded stages" in text
    for heading in (
        "### 0a. Transformation Intake",
        "### 1. Internal system survey",
        "### 2. Behavioral baseline",
        "### 3. PRD acceptance contract",
        "### 4. External discovery and benchmarking",
        "### 5. Modularity, scalability, and maintainability assessment",
        "### 5a. Discovery Direction Gate",
        "### 6. Evidence-based classification",
        "### 7. Target modular blueprint",
        "### 7a. Solution Gate",
        "### 8. Incremental transformation roadmap",
        "### 9. Execution Gate, then hand off to milestone execution",
    ):
        assert heading in text, f"missing stage heading: {heading}"


def test_stage_headings_appear_in_order():
    text = _read(SKILL_PATH)
    headings = [
        "### 0a. Transformation Intake",
        "### 1. Internal system survey",
        "### 2. Behavioral baseline",
        "### 3. PRD acceptance contract",
        "### 4. External discovery and benchmarking",
        "### 5. Modularity, scalability, and maintainability assessment",
        "### 5a. Discovery Direction Gate",
        "### 6. Evidence-based classification",
        "### 7. Target modular blueprint",
        "### 7a. Solution Gate",
        "### 8. Incremental transformation roadmap",
        "### 9. Execution Gate, then hand off to milestone execution",
    ]
    positions = [text.index(h) for h in headings]
    assert positions == sorted(positions), "stage headings are out of order"


def test_skill_declares_all_new_artifacts():
    text = _read(SKILL_PATH)
    for artifact in NEW_ARTIFACTS:
        assert f".renmark/rethink/<slug>/{artifact}" in text, f"missing artifact: {artifact}"


# ── internal survey vs external benchmark are distinct and both mandatory ───


def test_internal_survey_is_never_presented_as_external_research():
    text = _read(SKILL_PATH)
    assert "internal, repository-grounded research only" in text
    assert "never stands in for stage 4's external benchmarking" in text


def test_external_benchmark_stage_is_mandatory_and_evidence_aware():
    text = _read(SKILL_PATH)
    assert "### 4. External discovery and benchmarking" in text
    norm = _normalized(SKILL_PATH)
    for term in (
        "source, access date, evidence strength",
        "Verified external facts",
        "Inferences",
        "Recommendations",
        "Unknowns",
    ):
        assert term in norm


def test_blocked_external_research_cannot_be_reported_complete():
    norm = _normalized(SKILL_PATH)
    assert "the subagent reports this stage **blocked** or **incomplete**" in norm
    assert "it must never silently fall back to model memory" in norm
    # the "Do not" section must repeat the honesty rule explicitly
    assert "never substitute model memory and call it research" in norm


# ── PRD acceptance contract is distinct from the behavioral baseline ────────


def test_prd_acceptance_contract_stage_exists_and_is_distinct_from_baseline():
    text = _read(SKILL_PATH)
    assert "### 3. PRD acceptance contract" in text
    assert "the baseline says what the app *currently does*" in text
    assert "the PRD contract says what the app *is required to do*" in text
    assert "Existing behavior is\nnot correct merely because it exists" in text


def test_completion_is_blocked_on_unresolved_prd_criteria():
    norm = _normalized(SKILL_PATH)
    assert (
        "a transformation cannot be reported complete while an applicable PRD"
        " acceptance criterion remains failed, omitted, unverified, or changed"
        " without explicit Owner approval" in norm
    )


# ── modularity assessment is mandatory and reaches Improve items ────────────


def test_modularity_assessment_stage_is_mandatory():
    text = _read(SKILL_PATH)
    assert "### 5. Modularity, scalability, and maintainability assessment" in text
    assert "Avoid speculative microservices" in text


def test_improve_items_may_receive_architectural_boundary_changes():
    text = _read(SKILL_PATH)
    assert "Architectural redesign is not limited to `Replace`" in text
    assert "An `Improve` item may" in text
    assert "**Do not skip the modularity assessment**" in text
    assert "do not restrict architectural\n  redesign to `Replace` items only" in text


# ── classification cites all four evidence sources ───────────────────────────


def test_classification_requires_cited_multi_source_evidence():
    text = _read(SKILL_PATH)
    assert "Every classification decision must cite its evidence" in text
    assert "internal\nsurvey/baseline finding" in text
    assert "PRD-acceptance impact" in text
    assert "external evidence where relevant" in text
    assert "modularity\nimpact" in text


# ── owner gate / no self-approval / no production mutation before approval ──


def test_owner_gate_and_no_self_approval():
    norm = _normalized(SKILL_PATH)
    assert "No agent in this pipeline may self-approve a structural recommendation" in norm
    assert "Do not let any agent self-approve a structural recommendation" in norm


def test_no_production_code_before_owner_approval():
    norm = _normalized(SKILL_PATH)
    assert (
        "Stages 1–8 (plus the Transformation Intake, the Discovery Direction"
        " Gate, and the Solution Gate) produce artifacts and decisions only."
        in norm
    )
    assert "Structural change begins after the stage-9 Execution Gate's Owner approval" in norm
    assert "read-only regarding the target application's production code" in norm


def test_roadmap_reuses_program_contract_and_first_release_default():
    text = _read(SKILL_PATH)
    assert "renmark.program.write_program(repo, program)" in text
    assert '"baseline and compatibility coverage"' in text


# ── cross-surface consistency: command, PRD, help ────────────────────────────


def test_command_file_points_at_skill_and_matches_pipeline_name():
    text = _read(COMMAND_PATH)
    assert "rethink/SKILL.md" in text
    assert "Brownfield Modernization pipeline" in text


def test_prd_req28_reflects_nine_stage_pipeline():
    text = _read(PRD_PATH)
    assert "`REQ-28` **Brownfield modernization entry point.**" in text
    assert "PRD acceptance contract" in text
    assert "external discovery and benchmarking" in text
    assert "modularity, scalability, and maintainability assessment" in text
    assert "blocked/incomplete" in text
    assert "not limited to `Replace`" in text


def test_prd_has_revision_note_for_the_expansion():
    text = _read(PRD_PATH)
    assert "Amended REQ-28 to expand" in text
    assert "does not invalidate rethink's prior\napproved behavior" in text


def test_help_skill_mentions_expanded_stages():
    norm = _normalized(HELP_PATH)
    assert "PRD acceptance contract" in norm
    assert "external benchmarking" in norm
    assert "modularity/scalability assessment" in norm
    assert "Discovery Direction Gate" in norm
    assert "Solution Gate" in norm
    assert "Execution Gate" in norm


def test_claude_and_agents_md_mirror_rethink_summary():
    claude_text = _read(CLAUDE_PATH)
    agents_text = _read(AGENTS_PATH)
    needle = (
        "internal survey + external benchmarking + a binding PRD acceptance "
        "contract + a mandatory modularity/scalability assessment"
    )
    assert needle in claude_text
    assert needle in agents_text
    gate_needle = "gated by a Discovery Direction Gate, a Solution Gate, and an Execution Gate"
    assert gate_needle in claude_text
    assert gate_needle in agents_text


# ── Transformation Intake ────────────────────────────────────────────────────


def test_transformation_intake_asks_only_blocking_questions():
    norm = _normalized(SKILL_PATH)
    assert "### 0a. Transformation Intake" in norm
    for term in (
        "the **desired outcome**",
        "**protected behavior**",
        "**constraints**",
        "**non-goals**",
        "**areas open to change**",
    ):
        assert term in norm
    assert "asking only **blocking** questions" in norm
    assert ".renmark/rethink/<slug>/intake.md" in norm


# ── Discovery Direction Gate blocks progression ──────────────────────────────


def test_discovery_direction_gate_presents_required_elements_and_blocks():
    norm = _normalized(SKILL_PATH)
    assert (
        "After stages 1–5 (survey, baseline, PRD acceptance contract,"
        " external benchmark, modularity assessment) and before stage 6"
        " classification or stage 7 blueprint work begins" in norm
    )
    for term in (
        "**Material findings and implications**",
        "**Gaps**",
        "**Recommended transformation direction**",
        "**Up to two viable alternatives**",
        "**Assumptions, risks, and the exact Owner decisions required**",
    ):
        assert term in norm
    assert (
        "Require one explicit choice — never auto-proceed on the"
        " recommendation, and\nnever infer it from an earlier unrelated"
        " approval." in _read(SKILL_PATH)
        or "never infer it from an earlier unrelated approval" in norm
    )


def test_discovery_direction_gate_rejection_returns_to_correct_stage():
    norm = _normalized(SKILL_PATH)
    assert (
        "route back to the specific stage (1–5) that needs more evidence;"
        " do not restart the pipeline" in norm
    )


# ── Solution Gate blocks progression ─────────────────────────────────────────


def test_solution_gate_presents_required_elements_and_blocks():
    norm = _normalized(SKILL_PATH)
    for term in (
        "**Behavioral and PRD changes**",
        "**Protected behavior**",
        "**Module/data/integration boundaries**",
        "**Removals, incompatibilities, and migration risks**",
        "**Material tradeoffs, exclusions, and unresolved decisions**",
    ):
        assert term in norm
    assert (
        "Require one explicit `AskUserQuestion` approval — never inferred"
        " from the Discovery Direction Gate's earlier, unrelated approval"
        in norm
    )


def test_solution_gate_rejection_returns_to_classification_and_blueprint():
    norm = _normalized(SKILL_PATH)
    assert (
        "return to stage 6/7 (classification/blueprint) for revision,"
        " reusing stages 1–5's artifacts unchanged — do not re-run research"
        " or re-ask the Transformation Intake" in norm
    )


# ── Execution Gate blocks progression; no code before it ────────────────────


def test_execution_gate_presents_roadmap_fields_and_blocks():
    norm = _normalized(SKILL_PATH)
    assert "### 9. Execution Gate, then hand off to milestone execution" in norm
    assert (
        "require **one explicit `AskUserQuestion` approval** before any"
        " target production code changes or Agency execution begins" in norm
    )


def test_execution_gate_rejection_returns_to_roadmap_stage():
    norm = _normalized(SKILL_PATH)
    assert (
        "return to stage 8 (roadmap) for revision, reusing stages 1–7's"
        " approved artifacts and decisions unchanged — do not re-run"
        " research, re-dispatch classification, or re-ask either earlier"
        " gate" in norm
    )


# ── exception check-in triggers on the five named conditions ────────────────


def test_exception_checkin_triggers_on_all_five_conditions():
    norm = _normalized(SKILL_PATH)
    for trigger in (
        "a **material PRD/Owner-intent conflict**",
        "**unreliable or blocked research**",
        "a **major cost/scope/security impact**",
        "a **proposed behavior removal or incompatibility**",
        "a **high-impact unknown that cannot be safely bounded**",
    ):
        assert trigger in norm


def test_exception_checkin_pauses_only_affected_decision():
    norm = _normalized(SKILL_PATH)
    assert (
        "pause only the affected decision — do not discard completed"
        " work, and do not stop stages that don't depend on the exception"
        in norm
    )


def test_exception_checkin_never_shows_raw_research():
    norm = _normalized(SKILL_PATH)
    assert (
        "never raw research, logs, or a technical questionnaire" in norm
    )
    assert "findings → implications → recommendation → alternatives → exact" in norm


# ── gate rules: no silent/self approval, no raw research, resume reuse ──────


def test_gate_rules_section_forbids_silent_and_self_approval():
    text = _read(SKILL_PATH)
    assert "## Gate rules" in text
    norm = _normalized(SKILL_PATH)
    assert (
        "Never infer approval from silence or an earlier unrelated approval."
        in norm
    )
    assert (
        "No agent in this pipeline may approve its own recommendation."
        in norm
    )
    assert "Never show raw research, logs, or a technical questionnaire." in norm


def test_gate_rules_require_resume_reuse_of_completed_artifacts():
    norm = _normalized(SKILL_PATH)
    assert "Resume from the last approved checkpoint." in norm
    assert (
        "a stage whose artifact already exists and whose gate (if any)"
        " already cleared is reused, never re-run and never re-asked" in norm
    )


def test_gate_rules_forbid_routine_status_interruptions():
    norm = _normalized(SKILL_PATH)
    assert (
        "Gates must not add routine status interruptions between mandatory"
        " decisions." in norm
    )


def test_do_not_section_repeats_no_silent_no_self_approval_rules():
    norm = _normalized(SKILL_PATH)
    assert "Do not infer any gate's approval from silence" in norm
    assert (
        "never the subagent that\n  proposed the thing being approved"
        in _read(SKILL_PATH)
        or "never the subagent that proposed the thing being approved" in norm
    )
    assert "Do not add a routine status prompt between the three named gates" in norm


# ── regression: existing dispatch/context-hygiene/Agency behavior intact ────


def test_bounded_subagent_dispatch_pattern_unchanged():
    norm = _normalized(SKILL_PATH)
    assert "role: researcher" in norm
    assert "bounded ≤5-line" in norm or "bounded\n≤5-line" in _read(SKILL_PATH)


def test_agency_handoff_machinery_unchanged():
    norm = _normalized(SKILL_PATH)
    assert "renmark.agency.activate(repo, ...)" in norm
    assert "rather than building a rethink-only executor" in norm
    assert "Do not invent a parallel execution system." in norm


def test_program_contract_reuse_unchanged():
    norm = _normalized(SKILL_PATH)
    assert "renmark.program.write_program(repo, program)" in norm
    assert '"baseline and compatibility coverage"' in norm

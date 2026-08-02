"""Contract tests for /renmark:start's three-gate evidence/traceability/
modularity pipeline (Discovery Direction Gate, Solution Gate, Execution
Gate) plus its cross-cutting exception check-in.

Like the rethink pipeline, start's stages are markdown-authored governance
rather than a Python state machine, so the contract's gate, honesty, and
traceability rules are proven by asserting the required language ships in
the skill (and stays consistent with the PRD/help/docs surfaces), not by
executing the skill.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILL_PATH = REPO_ROOT / "plugin" / "skills" / "start" / "SKILL.md"
COMMAND_PATH = REPO_ROOT / "plugin" / "commands" / "start.md"
PRD_PATH = REPO_ROOT / "PRD.md"
HELP_PATH = REPO_ROOT / "plugin" / "skills" / "help" / "SKILL.md"
CLAUDE_PATH = REPO_ROOT / "CLAUDE.md"
AGENTS_PATH = REPO_ROOT / "AGENTS.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _normalized(path: Path) -> str:
    return " ".join(_read(path).split())


# ── all stage headings exist, in order ───────────────────────────────────────


def test_skill_declares_all_stage_headings_in_order():
    text = _read(SKILL_PATH)
    headings = [
        "### 4.5. External discovery — or an approved fast-path waiver",
        "### 4.6. Discovery Direction Gate",
        "### 5. Confirm in plain language",
        "### 5a. Establish the PRD before building",
        "### 5a-ii. PRD acceptance / traceability contract",
        "### 5b. Prospective modular blueprint",
        "### 5c. Solution Gate",
        "### 6. Inject best practices into plan context",
        "### 7. Route to pipeline",
        "### 7a. Execution Gate",
        "### 8. Handoff to execution",
    ]
    positions = [text.index(h) for h in headings]
    assert positions == sorted(positions), "stage headings are out of order"


def test_exception_checkin_section_exists():
    text = _read(SKILL_PATH)
    assert "## Exception check-in (cross-cutting — Complex scope)" in text


# ── Discovery Direction Gate blocks progression ──────────────────────────────


def test_discovery_direction_gate_presents_required_elements_and_blocks():
    norm = _normalized(SKILL_PATH)
    assert "This gate governs *direction*" in norm
    for term in (
        "**Findings**",
        "**Implications**",
        "**Recommended direction**",
        "**Viable alternatives**",
        "**Assumptions**",
        "**Risks**",
        "**Exact decisions required**",
    ):
        assert term in norm
    assert "Require one explicit choice — never auto-proceed on the recommendation" in norm


def test_discovery_direction_gate_replaces_step5_for_complex_scope():
    norm = _normalized(SKILL_PATH)
    assert (
        "For Complex scope, this gate replaces Step 5's plain-language" in norm
    )
    assert "do not ask both" in norm


# ── Solution Gate blocks progression ─────────────────────────────────────────


def test_solution_gate_presents_required_elements_and_blocks():
    norm = _normalized(SKILL_PATH)
    for term in (
        "**Scope**",
        "**Workflows**",
        "**Requirements**",
        "**Module boundaries**",
        "**Exclusions**",
        "**Unresolved decisions**",
        "**Material tradeoffs**",
    ):
        assert term in norm
    assert (
        "require **one explicit `AskUserQuestion` approval** before continuing"
        in norm
    )
    assert "No agent in this pipeline may self-approve a structural or scope decision" in norm


def test_solution_gate_precedes_roadmap_not_execution():
    norm = _normalized(SKILL_PATH)
    assert (
        "This gate approves the *solution* — scope and design — not yet the"
        " roadmap (Step 7) or execution (Step 7a)" in norm
    )


# ── Execution Gate blocks progression; no code before it ────────────────────


def test_execution_gate_presents_roadmap_and_blocks():
    norm = _normalized(SKILL_PATH)
    assert "present that roadmap/plan and require **one explicit Owner approval**" in norm
    assert (
        "No target application code changes before this gate clears." in norm
    )
    assert (
        "the first target code is written only after `/renmark:orchestrate`"
        " (or the staged driver) starts, which happens only after this gate's"
        " explicit approval" in norm
    )


def test_execution_gate_is_realized_through_existing_handoff_not_a_new_menu():
    norm = _normalized(SKILL_PATH)
    assert "This is not a second, separate menu" in norm


# ── exception check-in triggers on the four named conditions ────────────────


def test_exception_checkin_triggers_on_all_four_conditions():
    norm = _normalized(SKILL_PATH)
    for trigger in (
        "a **material PRD conflict**",
        "**unreliable research**",
        "a **major cost/scope/security implication**",
        "a **high-impact unknown**",
    ):
        assert trigger in norm


def test_exception_checkin_is_an_interrupt_not_a_deferred_gate():
    norm = _normalized(SKILL_PATH)
    assert (
        "stop the current stage immediately and run an **exception check-in**"
        " rather than folding the issue silently into the next scheduled gate"
        in norm
    )
    assert (
        "present the specific finding, why it's material, and the concrete"
        " options (never raw research or a wall of caveats)" in norm
    )
    assert "Get one explicit Owner decision" in norm


def test_unresolved_high_impact_unknown_becomes_bounded_spike():
    norm = _normalized(SKILL_PATH)
    assert (
        "becomes a bounded spike (question, scope, evidence requirement,"
        " budget, stop condition) recorded on the roadmap — never a silent"
        " assumption" in norm
    )


# ── research cannot be falsely reported complete ─────────────────────────────


def test_blocked_external_access_is_reported_honestly():
    norm = _normalized(SKILL_PATH)
    assert (
        "the subagent reports this stage `blocked` or `incomplete` in its"
        " returned status" in norm
    )
    assert "it must never silently fall back to model memory" in norm
    assert "triggers the exception check-in" in norm


# ── PRD acceptance contract traces criteria to releases and verification ────


def test_prd_acceptance_contract_traces_to_release_and_verification():
    norm = _normalized(SKILL_PATH)
    assert "the roadmap release that will deliver it, its verification method" in norm
    assert (
        "no release may be reported complete while an applicable PRD acceptance"
        " criterion is failed, omitted, unverified, or changed without explicit"
        " Owner approval" in norm
    )


def test_prd_acceptance_contract_applies_even_to_simple_scope():
    norm = _normalized(SKILL_PATH)
    assert (
        "The minimal PRD's goal/success criteria (Step 5a) already double as"
        " the acceptance contract" in norm
    )


# ── modular design precedes execution ────────────────────────────────────────


def test_blueprint_is_mandatory_for_complex_and_precedes_solution_gate():
    norm = _normalized(SKILL_PATH)
    assert "mandatory before execution, not merely offered" in norm
    assert "Before any build task is dispatched, establish deliberate module boundaries" in norm
    assert "avoid speculative microservices and premature abstraction" in norm
    # blueprint (5b) heading must precede the Solution Gate (5c) heading
    text = _read(SKILL_PATH)
    assert text.index("### 5b. Prospective modular blueprint") < text.index(
        "### 5c. Solution Gate"
    )


def test_blueprint_reuses_existing_blueprint_skill():
    text = _read(SKILL_PATH)
    assert "/renmark:blueprint" in text


# ── the fast path survives ───────────────────────────────────────────────────


def test_simple_scope_waiver_is_explicit_and_owner_approved():
    norm = _normalized(SKILL_PATH)
    assert "documented waiver instead" in norm
    for field in ("**reason**", "**risk**", "**scope**"):
        assert field in norm
    assert (
        'The user\'s existing "Ready? [Y/n]" answer IS the explicit Owner approval'
        " of that waiver" in norm
    )
    assert "do not add any of the three gates" in norm


def test_waiver_does_not_survive_scope_creep():
    norm = _normalized(SKILL_PATH)
    assert "the waiver does not travel with scope creep" in norm


def test_fast_path_question_budget_is_unchanged():
    norm = _normalized(SKILL_PATH)
    assert "the two-follow-up-question promise is unchanged" in norm
    assert "Cap at 2" in norm


def test_no_second_interrogation_for_simple_builds():
    norm = _normalized(SKILL_PATH)
    assert (
        "Fold a one-line documented waiver into the existing Step-5"
        " confirmation instead — no new gate" in norm
    )


# ── release-level fields / Program reuse ─────────────────────────────────────


def test_program_stages_carry_release_level_fields():
    norm = _normalized(SKILL_PATH)
    for term in (
        "the user-observable value it delivers",
        "PRD criteria (`AC-<n>`) it satisfies",
        "its verification method",
        "its observability hook",
        "an Owner acceptance scenario",
    ):
        assert term in norm
    assert "reusing the same `Program`/`StageNode` shape" in norm


# ── cross-surface consistency ────────────────────────────────────────────────


def test_command_file_still_points_at_skill():
    text = _read(COMMAND_PATH)
    assert "start/SKILL.md" in text


def test_prd_req29_names_all_three_gates_and_checkin():
    text = _read(PRD_PATH)
    assert "`REQ-29` **Evidence-based greenfield entry point.**" in text
    assert "**Discovery Direction Gate**" in text
    assert "**Solution Gate**" in text
    assert "**Execution Gate**" in text
    assert "exception check-in" in text
    assert "PRD acceptance/" in text and "traceability contract" in text


def test_prd_req29_excludes_brownfield_concerns():
    norm = " ".join(_read(PRD_PATH).split())
    assert "excludes brownfield-only concerns" in norm
    assert "Keep/Improve/Replace/Remove classification" in norm


def test_prd_has_revision_note_for_three_gate_elaboration():
    text = _read(PRD_PATH)
    assert "split\nits single" in text or "split its single" in " ".join(text.split())
    assert "Discovery Direction Gate" in text and "not a new requirement or a reversal" in text


def test_help_skill_mentions_all_three_gates():
    text = _read(HELP_PATH)
    assert "Discovery Direction Gate" in text
    assert "Solution Gate" in text
    assert "Execution Gate" in text


def test_claude_and_agents_md_mirror_start_summary_with_gates():
    claude_text = _read(CLAUDE_PATH)
    agents_text = _read(AGENTS_PATH)
    needle = (
        "nontrivial builds run external research, a Discovery Direction Gate, "
        "a PRD acceptance contract, a modular blueprint, a Solution Gate, and "
        "an Execution Gate"
    )
    assert needle in claude_text
    assert needle in agents_text

"""Contract tests for REQ-31 — native task tracking for dispatched work.

Static content checks over the shared `task-tracking.md` fragment, its
wiring into `subagent-budget.md` (the single dispatch-packet contract every
dispatching pipeline already cites), `PRD.md`'s REQ-31, and the mirrored
CLAUDE.md/AGENTS.md pointers. Proves the lifecycle, the no-self-approval
rule, resume-reuse, the no-new-gate/no-regression constraint, and honest
degradation are all specified — and that every dispatching pipeline inherits
the contract through the shared fragment rather than needing its own copy.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FRAGMENT_PATH = REPO_ROOT / "plugin" / "skills" / ".shared" / "task-tracking.md"
BUDGET_PATH = REPO_ROOT / "plugin" / "skills" / ".shared" / "subagent-budget.md"
PRD_PATH = REPO_ROOT / "PRD.md"
CLAUDE_PATH = REPO_ROOT / "CLAUDE.md"
AGENTS_PATH = REPO_ROOT / "AGENTS.md"
ORCHESTRATE_PATH = REPO_ROOT / "plugin" / "skills" / "orchestrate" / "SKILL.md"

# Pipelines REQ-31 explicitly names as dispatching and therefore covered.
DISPATCHING_PIPELINES = ("start", "feature", "debug", "rethink", "orchestrate", "finish")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _normalized(path: Path) -> str:
    return " ".join(_read(path).split())


# ── the shared fragment exists with the full lifecycle contract ─────────────


def test_fragment_exists_and_names_lifecycle_states():
    text = _read(FRAGMENT_PATH)
    for state in ("`pending`", "`in_progress`", "`completed`"):
        assert state in text


def test_fragment_requires_one_parent_per_milestone_one_bounded_per_dispatch():
    norm = _normalized(FRAGMENT_PATH)
    assert "one parent task per milestone" in norm.lower() or (
        "**One parent task per milestone**" in _read(FRAGMENT_PATH)
    )
    assert "one bounded task per dispatch" in norm.lower() or (
        "**One bounded task per dispatch**" in _read(FRAGMENT_PATH)
    )
    assert "Do not** create a native task for trivial internal reasoning" in norm


def test_fragment_requires_dispatch_content_fields():
    text = _read(FRAGMENT_PATH)
    for field in (
        "Title",
        "Role/agent",
        "Scope and expected result",
        "Dependencies/blockers",
        "Acceptance/verification requirement",
    ):
        assert field in text


def test_fragment_forbids_self_approval():
    norm = _normalized(FRAGMENT_PATH)
    assert (
        "A worker task's own completion never completes its parent milestone"
        " task" in norm
    )
    assert "create an" in norm and "explicit verification/review task" in norm


def test_fragment_requires_resume_reuse_not_recreation():
    norm = _normalized(FRAGMENT_PATH)
    assert (
        "reload existing tasks (`TaskList`/`TaskGet`) before creating anything"
        in norm
    )
    assert (
        "never recreated" in norm or "never recreate a completed one" in norm
    )
    assert "Never redispatch a completed or accepted task" in norm


def test_fragment_requires_scope_change_to_close_before_replace():
    norm = _normalized(FRAGMENT_PATH)
    assert (
        "set it `deleted` with a one-line reason recorded first" in norm
    )
    assert "never silently abandon a task with no trace" in norm


def test_fragment_forbids_new_gates_and_retained_context():
    norm = _normalized(FRAGMENT_PATH)
    assert "**No new Owner gate.**" in norm
    assert "**No retained orchestrator context.**" in norm
    assert "**No raw research, transcripts, diffs, or logs.**" in norm


def test_fragment_requires_honest_degradation():
    norm = _normalized(FRAGMENT_PATH)
    assert "say so plainly" in norm
    assert (
        "Never claim a native task was created or updated when the live"
        " host tool was not actually called" in norm
    )
    assert "a fabricated" in norm and "is worse than an honest" in norm


def test_fragment_distinguishes_live_host_tools_from_python_mirror():
    norm = _normalized(FRAGMENT_PATH)
    assert "Two enforcement layers, not one" in norm
    assert "There\n   is no way to satisfy requirement 1 from Python" in _read(
        FRAGMENT_PATH
    ) or "There is no way to satisfy requirement 1 from Python" in norm
    assert "This does not satisfy requirement 1 for a live agent session" in norm


def test_fragment_ties_to_req31_and_is_bound_by_req30():
    norm = _normalized(FRAGMENT_PATH)
    assert "Implements `PRD.md` REQ-31" in norm
    assert "bound by REQ-30" in norm
    assert "never a second execution path, a new Owner gate, or retained" in norm


# ── wired through the existing dispatch-packet contract, not duplicated ─────


def test_subagent_budget_cites_task_tracking_fragment():
    norm = _normalized(BUDGET_PATH)
    assert "_shared/task-tracking.md" in norm
    assert "**Native task tracking.**" in norm


def test_subagent_budget_citation_quote_mentions_task_tracking():
    norm = _normalized(BUDGET_PATH)
    assert "Track each dispatch as a native task per `_shared/task-tracking.md`" in norm


def test_task_tracking_is_informational_not_a_second_schema():
    norm = _normalized(BUDGET_PATH)
    assert (
        "This is informational scaffolding around the packet above — it"
        " does not change what gets dispatched" in norm
    )


# ── PRD REQ-31 ────────────────────────────────────────────────────────────────


def test_prd_declares_req31_with_full_lifecycle():
    text = _read(PRD_PATH)
    assert "`REQ-31` **Native task tracking for dispatched work.**" in text
    norm = _normalized(PRD_PATH)
    assert (
        "pending` on creation →\n    `in_progress` immediately before dispatch"
        in text
        or "`pending` on creation → `in_progress` immediately before dispatch"
        in norm
    )


def test_req31_names_every_dispatching_pipeline():
    norm = _normalized(PRD_PATH)
    for pipeline in (*DISPATCHING_PIPELINES, "codereview"):
        assert f"`{pipeline}`" in norm


def test_req31_forbids_self_approval_and_cites_existing_gate_precedent():
    norm = _normalized(PRD_PATH)
    assert (
        "A worker's own task completion never completes its parent milestone"
        in norm
    )
    assert "extends REQ-4, REQ-12, REQ-28, REQ-29" in norm


def test_req31_requires_resume_reuse_and_honest_degradation():
    norm = _normalized(PRD_PATH)
    assert (
        "a completed or\n    accepted task is never recreated or redispatched"
        in _read(PRD_PATH)
        or "a completed or accepted task is never recreated or redispatched"
        in norm
    )
    assert "it never claims a native" in norm
    assert "when the live host tool was not actually" in norm


def test_req31_splits_live_host_tools_from_python_mirror_mechanism():
    norm = _normalized(PRD_PATH)
    assert "two distinct, non-substitutable" in norm
    assert "no Python module can invoke a host's tools on" in norm
    # Widened 2026-08-06 (cross-host-native-tool-leverage rethink, exception
    # check-in): mechanism (ii) now covers any dispatch path lacking a native
    # task-visibility primitive, not just the headless subprocess path.
    assert "is the acceptable substitute wherever (i) has nothing to call" in norm
    assert "never substitutes for (i) on a host that actually has native task tools" in norm


def test_req31_bound_by_req30_no_regression():
    norm = _normalized(PRD_PATH)
    assert "extends REQ-5, REQ-30" in norm
    assert (
        "no measured token/time regression beyond REQ-30's 15%" in norm
        or "no\n      measured token/time regression beyond REQ-30's 15% threshold" in _read(PRD_PATH)
    )


def test_goals_section_has_matching_req31_bullet():
    norm = _normalized(PRD_PATH)
    assert (
        "never self-approved,\n  never silently recreated on resume (REQ-31)"
        in _read(PRD_PATH)
        or "never self-approved, never silently recreated on resume (REQ-31)"
        in norm
    )


def test_revision_note_documents_req31_as_shared_implementation():
    norm = _normalized(PRD_PATH)
    assert "Added REQ-31" in norm
    assert "implemented once" in norm.lower()
    assert "rather than rewriting each pipeline's SKILL.md" in norm


# ── CLAUDE.md / AGENTS.md carry the mirrored operational rule ───────────────


def test_claude_md_has_task_tracking_rule_block():
    text = _read(CLAUDE_PATH)
    assert "<!-- BEGIN:task-tracking-rule -->" in text
    assert "<!-- END:task-tracking-rule -->" in text
    assert "## Native task tracking (REQ-31)" in text


def test_claude_md_markers_stay_balanced():
    text = _read(CLAUDE_PATH)
    assert text.count("<!-- BEGIN:") == text.count("<!-- END:")


def test_agents_md_mirrors_task_tracking_rule():
    text = _read(AGENTS_PATH)
    assert "**Native task tracking (REQ-31).**" in text
    assert "§ `task-tracking-rule`" in text
    assert "plugin/skills/.shared/task-tracking.md" in text


# ── orchestrate (the primary dispatch engine) cites it concretely ───────────


def test_orchestrate_cites_task_tracking_and_ties_to_skip_list_resume():
    norm = _normalized(ORCHESTRATE_PATH)
    assert "task-tracking.md" in norm
    assert "REQ-31" in norm
    assert "reuses the tasks the skip-list already accounts for rather than" in norm

---
artifact_type: milestone_execution_plan
schema_version: 1
created_at: 2026-07-30T14:55:00+00:00
source_sha: 6973a8d
related_plan: .renmark/plans/2026-07-29-two-mode-milestone-delivery.plan.md
generator: renmark:orchestrate
stale_after: null
dependency_refs:
  - .renmark/plans/2026-07-29-two-mode-milestone-delivery-m2-part1-runtime.plan.md
  - .renmark/plans/2026-07-29-two-mode-milestone-delivery-m2-part2-entry-contract.plan.md
  - .renmark/debug/20260730-144120-0b43/session.md
completion_state: complete
confidence: high
validation_status: validated
retry_count: 0
parser_success: true
schema_compliance: true
---

# M2 continuation — milestone-sized work packages

This continuation preserves the approved M2 scope, the original `101,700`-token /
`$1.0955` cap, and the Part 1 → Part 2 dependency. Completed work through task 8
is retained. The remaining approved envelope is at most `72,100` estimated tokens /
`$0.5365`; packaging may reduce overhead but never authorizes spending beyond it.

Each package owns implementation plus directly related tests and runs a bounded
`build → verify → review → fix` loop with at most three iterations. A package stops
immediately on an unresolved verifier/review finding, security or destructive gate,
or any scope/budget expansion. Recovery uses stable package IDs and boundary
artifacts—never task-index-only resume.

## WP-M2-A — canonical runtime, lifecycle, CLI, and handoff

Combines Part 1 tasks 9–13 with direct compatibility repairs exposed by the fresh
repository gates.

- Production: `renmark/mode.py`, `renmark/lifecycle.py`, `renmark/cli/_engine.py`
- Tests: `tests/test_mode.py`, `tests/test_agency_behavior.py`,
  `tests/test_lifecycle.py`, `tests/test_mode_cli.py`
- Contract: `plugin/skills/.shared/handoff-menu.md`
- Outcome: Agency/Orchestrator is the only public delivery vocabulary; legacy
  Conductor remains readable as Orchestrator/guided; lifecycle, CLI, and handoffs
  converge without re-asking or persisting selector presentation.
- Gate: focused suites + Ruff + mypy + full pytest + bounded independent review.

## WP-M2-B — entry-skill routing contract

Combines Part 2 tasks 1–5.

- Skills: `plugin/skills/start/SKILL.md`, `plugin/skills/feature/SKILL.md`,
  `plugin/skills/debug/SKILL.md`, `plugin/skills/resume/SKILL.md`
- Tests: `tests/test_skill_trigger_phrases.py`
- Outcome: new ideas can choose Agency, defined work routes directly to
  Orchestrator, debug is guided Orchestrator, and resume reuses canonical state.
- Gate: all four deterministic skill verifiers + trigger suite + contract review.

## WP-M2-C — cross-host behavioral proof

Combines Part 2 tasks 6–9.

- Fixtures: `tests/behavioral/mode.behavior.json`,
  `tests/behavioral/selector_claude.behavior.json`,
  `tests/behavioral/selector_codex.behavior.json`
- Tests: `tests/test_behavior.py`
- Outcome: deterministic behavior fixtures prove canonical delivery routing,
  Claude native selection, Codex Plan pagination, and Codex Default fallback
  without model spend.
- Gate: JSON parsing + behavior tests + `renmark-execute --behavior` + full M2
  verification and review.

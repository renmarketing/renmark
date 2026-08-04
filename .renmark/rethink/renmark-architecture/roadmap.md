---
artifact_type: rethink-roadmap
schema_version: 1
created_at: 2026-08-03T00:00:00Z
source_sha: c6741856f7603aac3e01f324fbaa4b7e6478155e
related_plan: null
generator: renmark:code-implementer
stale_after: null
dependency_refs: ["classification.md","target-blueprint.md","baseline.md","prd-acceptance-map.md","intake.md"]
---

# Incremental transformation roadmap — Stage 8 of `/renmark:rethink` (renmark-architecture)

Seven small, independently usable, user-testable releases — never a big-bang
rewrite. Built as a `renmark.program` (`renmark.program.write_program`), the
same `Program`/`StageNode`/`TaskNode` shapes `/renmark:roadmap`'s forward-plan
mode already uses. No parallel roadmap format was invented.

**Program artifact**: `.renmark/state/program.json` (canonical, runtime)
**Rendered checklist**: `.renmark/roadmap/program.md` (committed, re-derived)
**Prior program archived to**: `.renmark/rethink/renmark-architecture/archive/pre-roadmap-program-2026-08-03.{json,md}`
(the repo's completed `renmark-prd-program` — all 19 stages `done` — was
snapshotted before this roadmap became the active program, so no historical
state was silently lost.)

Release 1 is fixed as "baseline and compatibility coverage" per the pipeline's
hard rule — not overridden by the Owner in this run.

---

## Release sequence

| # | Stage id | Title | Serves | Compat guarantee |
|---|---|---|---|---|
| 1 | `release-1-baseline-compat-coverage` | Baseline and compatibility coverage | REQ-30 | Full `pytest -q` ≥ 1931 passed/31 skipped (baseline.md's last recorded figure) |
| 2 | `release-2-remove-context-budget-hint` | Remove `context_budget_hint` dead code | REQ-5 | Full suite green; zero remaining call sites (grep) |
| 3 | `release-3-schemas-dependency-reversal` | Reverse `schemas.py`'s inverted dependency | new (PRD flag 6) | Full suite green; constant values unchanged, only import direction changes |
| 4 | `release-4-cli-engine-split` | Split `renmark/cli/_engine.py` into a sub-package | REQ-30 (exempt) | Full suite green incl. `test_engine_resume_crosscheck.py`/`test_engine_budget_and_rollback.py`; same public API |
| 5 | `release-5-lifecycle-split` | Split `renmark/lifecycle.py` into a sub-package | REQ-30 (exempt) | Full suite green incl. `test_lifecycle.py`; `STAGES` order + 1KB byte-budget unchanged |
| 6 | `release-6-cost-resolve-executor` | Centralize routing behind `cost.resolve_executor` | REQ-2 | Full suite green; new golden before/after routing-decision test proves identical outcomes |
| 7 | `release-7-skillmeta-lint-gate` | Skillmeta-completeness lint gate (optional/stretch) | new | Full suite green; `domain_of`'s never-raises contract preserved |

---

### Release 1 — Baseline and compatibility coverage (hard-default first release)

- **User-observable value**: Stage 2's baseline stops being a point-in-time
  doc and becomes a runnable regression guard (lifecycle `STAGES` order, 1KB
  byte-budget guard, host-capability table, artifact-home convention). Also
  the natural place to measure REQ-30's still-unmeasured numeric baseline
  (tokens/wall-clock/dispatch count for Start/Feature-Fix/Orchestrate/Rethink)
  — a measurement task with no code change, resolving classification.md item
  10's blocking prerequisite before it can block anything downstream.
- **PRD IDs advanced**: REQ-30 (+ AC-3), REQ-3, REQ-6, REQ-20, REQ-23, plus
  unblocks the 9 currently-`unverified` rows (REQ-2/7/9-14/16/18/24/31) that
  only need a fresh live `pytest -q` to confirm.
- **Compatibility guarantee**: full `pytest -q` stays at or above 1931
  passed/31 skipped, zero new skips/xfails. Verification: fresh `pytest -q` +
  `renmark-execute --behavior`, re-run (not reused from a prior wave).
- **Migration steps**: add tests only — no production code moves.
- **Observability hook**: `.renmark/memory/orchestration-baseline.md` gets
  real numbers in place of "not yet measured."
- **Rollback path**: revert the test-only commit; zero production blast
  radius.
- **Owner acceptance scenario**: Owner runs `pytest -q`, sees a documented
  passing compatibility suite, and sees orchestration-baseline.md carrying
  real figures instead of an open item.

### Release 2 — Remove `context_budget_hint` dead code

- **Value**: removes dead scaffolding masquerading as enforcement
  (classification.md item 7, re-verified 2026-08-03, zero production
  callers).
- **PRD IDs**: REQ-5 (partial → met).
- **Compatibility guarantee**: full suite green; release 1's grep-based
  compat test shows zero remaining `context_budget_hint` references anywhere
  in `renmark/`/`plugin/` post-removal.
- **Migration steps**: delete the function + its `tests/test_state_skills.py`
  case; update `CLAUDE.md`/`AGENTS.md`/`CHANGELOG.md` mentions.
- **Observability hook**: CHANGELOG entry + the grep assertion added in
  release 1.
- **Rollback path**: single-commit `git revert` — no caller exists to break.
- **Owner acceptance scenario**: Owner re-runs the Stage-3 PRD-acceptance
  grep and sees REQ-5's row flip from partial to met.

### Release 3 — Reverse `schemas.py`'s inverted dependency — **DONE (2026-08-04, scope revised — see below)**

- **Value**: `schemas.py` becomes a true leaf again, so
  `dispatch.py`/`lifecycle.py` can be tested and modified independently of
  it. Foundational — releases 4 and 5's splits depend on getting this import
  direction right first (target-blueprint.md §1.3). *(Revised: releases 4-5
  only ever needed the `STAGES`/`SUBAGENT_OUTPUT_*` half of this — see
  Scope revision below.)*
- **PRD IDs**: resolves PRD-acceptance-map flag 6 (deferrable spec debt, not
  a compliance failure but material Stage-5 input).
- **Compatibility guarantee**: constant VALUES unchanged, only import
  direction changes; full suite green.
- **Migration steps (as executed)**: moved `STAGES` (from `lifecycle.py`)
  and the four `SUBAGENT_OUTPUT_*` constants (from `dispatch.py`) into
  `schemas.py`; both modules import them back at module level, breaking the
  two circular-import workarounds their own code had documented.
- **Observability hook**: an import-graph check confirming zero
  schemas↔lifecycle / schemas↔dispatch cycles (both fixed and re-verified).
- **Rollback path**: revert the single commit; imports revert with it.
- **Owner acceptance scenario (as delivered)**: Owner confirmed the
  scope-revised acceptance below.

**Scope revision (Owner decision, 2026-08-04):** the original migration
steps also called for moving `delivery_state.py`'s constants
(`CONTRACT_VERSION`/`SCHEMA_VERSION`/`PROVENANCE_EVENT_CAP`/
`WORK_PACKAGE_CAP`/`LEGACY_REF_CAP`/`SUMMARY_TEXT_LIMIT`/
`stable_milestone_id`/`stable_work_package_id`) into `schemas.py` too. During
implementation this was found to conflict with `delivery_state.py`'s own
module docstring, which declares it **"stdlib-only and intentionally
self-contained"** — a documented architectural invariant that predates this
rethink. Owner decision: **keep `delivery_state.py` stdlib-only**; the
"zero `renmark.*` imports" acceptance criterion for `schemas.py` is revised
to accept the one documented, permanent exception (`schemas.py` importing
`delivery_state.py`'s constants — the existing, unchanged direction).
Release 3 is **complete** under this revised scope, not partial — the
constant-consolidation goal was to eliminate the *forced* function-local
workaround imports (schemas↔lifecycle, schemas↔dispatch), both of which are
fixed. `delivery_state.py`'s stdlib-only boundary is a permanent design
constraint, not deferred work.

### Release 4 — Split `renmark/cli/_engine.py` into a sub-package

- **Value**: the 1698-line integration root becomes a thin orchestrating
  shell (`main()`/`execute_plan()`) plus three cohesive modules
  (`cli/_dispatch_flags.py`, `cli/_run_lifecycle.py`, `cli/_wave_loop.py`),
  mirroring the `renmark/state/` precedent. No user-facing change.
- **PRD IDs**: exempt from REQ-30's UPDATE gate per `intake.md`'s exception
  check-in (behavior-preserving structural extraction only); protects
  REQ-1/3/4.
- **Compatibility guarantee**: full suite green including
  `test_engine_resume_crosscheck.py`/`test_engine_budget_and_rollback.py`;
  same public functions/imports/call sites, before/after parity.
- **Migration steps**: per-function coverage inventory first
  (target-blueprint.md §3.6 — only 2 scenario-named test files map ~40
  functions), then extract; `cli/__init__.py` re-exports the full surface.
- **Observability hook**: none new — `pipeline.json`/wave-summaries unchanged
  shape.
- **Rollback path**: revert the package-split commit(s).
- **Owner acceptance scenario**: Owner runs `/renmark:orchestrate`
  end-to-end and sees identical behavior; `from renmark.cli import
  execute_plan` still works.

### Release 5 — Split `renmark/lifecycle.py` into a sub-package

- **Value**: isolates the reconciliation staleness hotspot (3+ CHANGELOG
  bugs, R-0.1/R-0.2/R-0.3) into one focused file, reducing blast radius of
  the next fix.
- **PRD IDs**: same REQ-30 exemption as release 4; protects REQ-1/3/4 "met/
  protect" rows (no gate/stage/UX wording change).
- **Compatibility guarantee**: full suite green including
  `test_lifecycle.py`; `STAGES` order and `LIFECYCLE_JSON_BYTE_BUDGET` (1KB)
  byte-for-byte unchanged; host-parity fixtures (Claude Code/Codex) unchanged.
- **Migration steps**: per-function coverage inventory first (only 1 test
  file maps ~50 defs across 6+ concerns); `lifecycle/__init__.py` re-exports
  the full surface.
- **Observability hook**: byte-budget enforcement (`LifecycleBloatError`)
  stays a live, tested guard.
- **Rollback path**: revert the commit.
- **Owner acceptance scenario**: Owner exercises `skill_preamble`/resume on
  both Claude Code and Codex and sees identical gate behavior post-split.

### Release 6 — Centralize routing behind `cost.resolve_executor`

- **Value**: adding a new executor tier drops from 4+ uncoordinated touch
  points to one `providers/<tier>.py` adapter + one branch in
  `cost.resolve_executor`.
- **PRD IDs**: touches REQ-2 (target "unchanged — protect") and REQ-30's
  tripwire; in-scope only because routing *outcomes* stay byte-identical
  (target-blueprint.md §1.4 — call-graph consolidation, not a policy change).
- **Compatibility guarantee**: routing outcomes unchanged; a new golden
  before/after routing-decision test is required in addition to full suite
  parity.
- **Migration steps**: `_choose_model()` (relocated in release 4)/
  `codex_routing.py`/`subagent_profiles.py`'s role-to-tier mapping call
  `cost.resolve_executor()` instead of deciding independently.
- **Observability hook**: `.renmark/memory/routing.md` continues logging
  identically.
- **Rollback path**: revert the commit.
- **Owner acceptance scenario**: Owner runs a sample dispatch and confirms
  the identical tier is chosen before and after, satisfying REQ-30's
  regression rule.

### Release 7 — Skillmeta-completeness lint gate (optional/stretch)

- **Value**: catches a missing `skillmeta.SKILLS[...]` entry loudly instead
  of silently letting `domain_of` default an unregistered skill to `"build"`.
- **PRD IDs**: no direct REQ row — a structural-hardening opportunity
  (classification.md item 5, target-blueprint.md §1.5), explicitly flagged
  as optional/stretch and recommended for deferral to the end of the roadmap.
- **Compatibility guarantee**: `domain_of`'s "never raises" contract is
  preserved; lint-only, zero runtime-behavior change; full suite green.
- **Migration steps**: one new check inside the existing `plan_lint.py`/
  `skillgen.py` family — no new module.
- **Observability hook**: lint failure surfaces immediately in CI/local
  `plan_lint` runs.
- **Rollback path**: revert the lint addition; no runtime impact either way.
- **Owner acceptance scenario**: Owner adds an intentionally unregistered
  `plugin/skills/<name>/` directory and sees `plan_lint` fail loud instead of
  silently defaulting.

---

## Explicitly excluded from this roadmap

**Git-worktree-per-agent isolation** (classification.md item 11) does not
appear above — it is an Owner-deferred, out-of-scope spike per the Discovery
Direction Gate decision, and its spike contract stays recorded only in
`classification.md` for institutional memory.

## Next step

Stage 9 (Execution Gate) presents this sequence for one explicit
`AskUserQuestion` approval before any target production code changes begin —
approving *execution*, not re-litigating the Discovery Direction Gate or
Solution Gate decisions already made.

---

## Execution Gate — decision (2026-08-03)

**Approved.** Owner approved execution via AskUserQuestion. Direction
(Discovery Direction Gate) and classification/blueprint (Solution Gate) were
already approved separately — this gate approved starting real production
changes. Rethink's responsibility ends here; execution proceeds through
renmark's existing Agency/milestone machinery (`renmark.agency.activate` +
this stage's `Program`), starting with Release 1 (baseline and compatibility
coverage) via `/renmark:orchestrate` or `/renmark:feature`.

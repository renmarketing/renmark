---
artifact_type: program
schema_version: 1
created_at: 2026-08-03T11:28:22+00:00
source_sha: c6741856f7603aac3e01f324fbaa4b7e6478155e
---

# Program — renmark-architecture-rethink-roadmap

_mode: staged · Stage 1/7 · task 1/2 done · current: Release 1: Baseline and compatibility coverage_

## ○ Release 1: Baseline and compatibility coverage — serves REQ-30 **(current)**
_phases: plan → build → verify → review → release_

- [x] Turn Stage-2 baseline into runnable compatibility tests — Value: durable, runnable proof of current behavior (lifecycle STAGES order, 1KB byte-budget guard, host-capability table, artifact-home convention) instead of a point-in-time doc. PRD: advances REQ-3/REQ-6/REQ-20/REQ-23 verification; unblocks REQ-2/7/9-14/16/18/24/31 (currently unverified — needs live pytest). Compat guarantee: full `pytest -q` stays >= 1931 passed/31 skipped (baseline.md's last recorded figure), zero new skips/xfails. Migration: add tests only, no production code moves; verify via fresh `pytest -q` + `renmark-execute --behavior`. Rollback: revert the test-only commit; zero runtime blast radius.
- [ ] Measure REQ-30's unmeasured numeric baseline (tokens/wall-clock/dispatch count) — Value: replaces orchestration-baseline.md's 'not yet measured' gap with real numbers for Start/Feature-Fix/Orchestrate/Rethink. PRD: satisfies REQ-30 row + AC-3 (untestable-as-written today); resolves classification.md item 10's blocking prerequisite. Compat: measurement-only, no dispatch/routing behavior change. Observability: updates .renmark/memory/orchestration-baseline.md with real figures; unblocks the 15%-regression check for releases 4-6 below. Owner acceptance: Owner sees real numbers replace 'not yet measured' in orchestration-baseline.md and a green compat suite.

## ○ Release 2: Remove context_budget_hint dead code — serves REQ-5
_phases: plan → build → verify → review → release_

- [x] Delete unreferenced context_budget_hint + its test and doc mentions — Value: removes dead scaffolding masquerading as enforcement (classification.md item 7, re-verified 2026-08-03). PRD: flips REQ-5 from partial toward met (zero production callers confirmed by repeated grep). Compat: full pytest -q stays green; release-1's grep-based compat test must show zero remaining call sites post-removal. Migration: delete function + tests/test_state_skills.py case; update CLAUDE.md/AGENTS.md/CHANGELOG references. Rollback: single-commit git revert; no downstream caller exists to break. Owner acceptance: grep shows zero hits repo-wide.

## ● Release 3: Reverse schemas.py's inverted dependency — serves new
_phases: plan → build → verify → review → release_

- [x] Make schemas.py/contracts.py the sole owner of shared contract constants — STAGES + SUBAGENT_OUTPUT_* moved into schemas.py (lifecycle.py/dispatch.py import back), breaking both circular-import workarounds. delivery_state.py stays stdlib-only permanently (Owner decision 2026-08-04) — roadmap scope revised accordingly, not deferred work.

## ● Release 4: Split renmark/cli/_engine.py into a sub-package — serves REQ-30
_phases: plan → build → verify → review → release_

- [x] Extract cli/_dispatch_flags.py, cli/_run_lifecycle.py, cli/_wave_loop.py — All 3 extractions done: _dispatch_flags.py (437L), _run_lifecycle.py (271L), _wave_loop.py (569L). _engine.py: 1698 -> 788 lines. Full suite green throughout (1936/31), each step independently re-verified, live renmark-execute --dry-run smoke test passed. No protected areas touched.

## ● Release 5: Split renmark/lifecycle.py into a sub-package — serves REQ-30
_phases: plan → build → verify → review → release_

- [x] Extract lifecycle/stage.py, next_steps.py, preamble.py, reconciliation.py — All 5 steps done: lifecycle.py (1747L) -> lifecycle/ package (stage.py 1057L, next_steps.py 175L, preamble.py 324L, reconciliation.py 297L, __init__.py 129L). Full suite green throughout (1936/31). STAGES + LIFECYCLE_JSON_BYTE_BUDGET byte-for-byte unchanged. Host-parity (claude/codex) confirmed identical for skill_preamble. No protected areas touched.

## ● Release 6: Centralize routing behind cost.resolve_executor — serves REQ-2
_phases: plan → build → verify → review → release_

- [x] Add cost.resolve_executor and migrate the 12-file scattered call sites — Scoped down per Owner decision: only the genuinely duplicated executor pricing table was centralized (3 copies -> 1, on renmark.cost.PRICE_PER_KTOK), fixing a live drift bug (codex priced 0.03 vs 0.05). The full 3-way resolve_executor() merge (model tier / role / codex dispatch) was NOT done -- kept as separate functions per Owner decision. Full suite green (1936/31).

## ● Release 7: Skillmeta-completeness lint gate — serves new
_phases: plan → build → verify → review → release_

- [x] Extend plan_lint.py to fail on an unregistered plugin/skills/<name>/ dir — Check 13 added to plan_lint.py: BLOCKs on an unregistered plugin/skills/<name>/ dir. 3 fixture tests + live acceptance-scenario demo confirmed. Zero drift found in current repo (30/30 match). Full suite green (1939/31, +3 new tests). Roadmap complete.

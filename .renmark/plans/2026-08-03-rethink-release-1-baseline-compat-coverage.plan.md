# Release 1: Baseline and compatibility coverage

Source: `.renmark/rethink/renmark-architecture/roadmap.md`, Stage 9 Execution
Gate (approved 2026-08-03). Program: `.renmark/state/program.json`, stage
`release-1-baseline-compat-coverage` (serves REQ-30). Turns `baseline.md`'s
point-in-time claims (lifecycle STAGES order, 1KB `lifecycle.json` byte
budget, host-capability table, artifact-home convention) into runnable
`pytest` compatibility tests, test-only — no production code moves.

**Owner-mandated protections (do not touch, do not weaken, do not rename):**
- `renmark/agency.py` role/milestone machinery and
  `.bootstrap-renmark/decisions/ADR-001-role-based-orchestration.md`'s
  Owner/General-Contractor/Architect/Worker/Inspector role model.
- `plugin/skills/.shared/interaction-contract.md` and any
  `renmark.interaction.build_selector` call site (`AskUserQuestion`,
  1–4 options, recommended option first).
- `plugin/skills/.shared/task-tracking.md` and `renmark/task_tracking.py`
  (native host task creation/update around dispatch).

If a task would need to modify any of the three items above, it must NOT be
executed — stop and report back to the Owner instead of proceeding.

`r1-req30-baseline-measurement` (the roadmap's second Release-1 item — live
numeric measurement of tokens/wall-clock/dispatch-count across the Start/
Feature-Fix/Orchestrate/Rethink pipelines) is intentionally **excluded** from
this plan: it requires actually running four full pipelines end-to-end, which
is a separate, materially more expensive measurement exercise, not a single
bounded file-write task. It stays `pending` in `.renmark/state/program.json`
until the Owner explicitly schedules that measurement run.

### Task 1: baseline compatibility test suite
- **mode:** A
- **target:** tests/test_artifact_home_and_baseline_compat.py
- **complexity:** medium
- **executor:** codex
- **role:** test-writer
- **parallel_group:** 1
- **est_tokens:** 1400
- **est_cost_usd:** 0.04
- **verifier:** pytest -q tests/test_artifact_home_and_baseline_compat.py
- **serves:** REQ-3, REQ-6, REQ-20, REQ-23
- **spec:**
  Add a new pytest test file, `tests/test_artifact_home_and_baseline_compat.py`,
  covering the parts of `baseline.md` NOT already covered by
  `tests/test_lifecycle.py` (STAGES order, byte-budget) or
  `tests/test_hosts.py` (capabilities_for table) — do not duplicate those,
  only reference them in a module docstring as "covered elsewhere."

  Assert the **artifact-home convention** from the project's `CLAUDE.md`
  ("All renmark output stays inside the project" — specs→`.renmark/specs/`,
  plans→`.renmark/plans/`, reviews→`.renmark/reviews/`, research→
  `.renmark/research/`, runtime→`.renmark/state/`, memory→`.renmark/memory/`,
  logs→`.renmark/logs/`, debug→`.renmark/debug/<session-id>/`, audits→
  `.renmark/audits/`):

  1. `renmark.bootstrap` (or wherever `init`/`bootstrap` creates project
     scaffolding today — read `renmark/bootstrap.py` first) creates `specs/`,
     `plans/`, `reviews/` under `.renmark/`, not at repo root.
  2. `renmark.state._core.find_repo_root` (read the real signature first)
     walks up from a nested `tmp_path` directory and correctly finds the
     `.renmark/` marker directory — add a case for a repo root 3+ levels
     below `tmp_path` and a case where no `.renmark/` exists (returns
     `None`).
  3. At least one real writer per canonical home resolves under `.renmark/`
     relative to repo root, using `tmp_path` fixtures — pick concrete,
     already-existing functions (do not invent new ones): a `state.*` writer
     for `.renmark/state/`, a `memory.*` writer (e.g. `log_feature`) for
     `.renmark/memory/`, and `lifecycle.write_lifecycle` for
     `.renmark/state/lifecycle.json`. Read each function's actual current
     signature and behavior first — do not guess argument names.

  Do not modify any non-test file. Do not touch `renmark/agency.py`,
  `plugin/skills/.shared/interaction-contract.md`,
  `plugin/skills/.shared/task-tracking.md`, or `renmark/task_tracking.py` —
  those are Owner-protected for this run; if achieving full coverage would
  require touching them, write the test against their current public
  behavior only, never edit them.

  Full `pytest -q` must stay at or above baseline.md's last recorded figure
  (>= 1931 passed / 31 skipped), with zero new skips or xfails.

---

## Cost preview

| Task | Executor | Est. tokens (incl. overhead) | Est. cost |
|---|---|---|---|
| 1. baseline compatibility test suite | codex | ~1400 | ~$0.04 |

**Total: ~$0.04, 1 task, 1 parallel group, no Opus/Fable escalation.**

Subagent gate: single well-scoped `codex` test-authoring task with a defined
verifier — deterministic-eligible check passes (test scaffolding is codex's
designated lane per `plugin/skills/.shared/model-routing.md`).

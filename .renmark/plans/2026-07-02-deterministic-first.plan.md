---
artifact_type: plan
schema_version: 1
created_at: 2026-07-02T18:55:26Z
source_sha: fba6875
related_plan: null
generator: feature
stale_after: null
dependency_refs:
  - .renmark/specs/2026-07-02-deterministic-first.request.md
  - renmark/cost.py
  - renmark/finish_lanes.py
  - renmark/release.py
tier: standard
feature: deterministic-first
branch: worktree-deterministic-first
---

# Deterministic-first execution — plan

Implements REQ-21 (Deterministic-first routing). Renmark prefers deterministic
code/tools before AI/subagents; worktree lifecycle + release/package/install
checks become deterministic git/parser calls; cost preview labels each item
deterministic vs model-driven; finish lanes expose worktree cleanup.

## Scope Contract
- **In:** the 7 tasks below. Deterministic helpers, cost tagging, lane column,
  shared fragment + mirrored rule block, tests, gate wiring, changelog.
- **Out:** removing worktree isolation (explicitly forbidden); Agency Mode build
  (only a cross-ref note); changing model-routing tier semantics.
- **Reuse:** codex.py `_git_status_porcelain`/`_parse_porcelain_z`;
  release.py `check_drift`/`current_version`/`build_package`; existing
  `LaneSpec.cleans_worktrees` flag; cost.py `_get` item accessor.

## Tasks

| # | Task | Files | Executor | Depends |
|---|---|---|---|---|
| T1 | `deterministic-first.md` fragment + mirrored `CLAUDE.md`/`AGENTS.md` rule block (`<!-- BEGIN:deterministic-first-routing -->`) | plugin/skills/_shared/deterministic-first.md, CLAUDE.md, AGENTS.md | haiku | — |
| T2 | `renmark/worktree.py` — pure git-backed fns: current_branch, list_worktrees, stale detection, divergence (merge-base/rev-list), diff_size (--stat), is_clean_tree (--porcelain), is_merged (--merged/rev-list). Reuse codex porcelain helpers | renmark/worktree.py | codex | — |
| T3 | Release-readiness deterministic gate: pure fns for release/package/install verification, called by finish lanes; reuse release.check_drift/current_version | renmark/finish_lanes.py, renmark/release.py | sonnet | — |
| T4 | Cost preview deterministic-vs-model-driven tagging: per-item `mode` + preview split counts | renmark/cost.py | sonnet | — |
| T5 | Worktree column in `lane_table()` rendering `cleans_worktrees` | renmark/finish_lanes.py | haiku | T3 |
| T6 | Tests: worktree helpers deterministic, gate runs code not model, cost split reported, lane column present | tests/test_worktree.py, tests/test_cost.py, tests/test_finish_lanes.py | codex | T2,T3,T4,T5 |
| T7 | Wire gates (cite deterministic-first from model-routing/subagent-budget/finish), Agency-Mode cross-ref note, CHANGELOG | plugin/skills/_shared/model-routing.md, .renmark/specs/2026-07-02-agency-mode.request.md, CHANGELOG.md | haiku | T1 |

## Waves
- **Wave 1 (parallel):** T1, T2, T3, T4 — independent file scopes.
- **Wave 2 (parallel):** T5 (after T3), T7 (after T1).
- **Wave 3:** T6 tests (after T2–T5) → run `pytest -q`, `ruff check`, `mypy .`.

## Verifier
`pytest -q && ruff check && mypy .` — goal-backward: new tests assert gates run
code (no model call), cost preview reports a deterministic/model split, and
lane_table renders the Worktree column.

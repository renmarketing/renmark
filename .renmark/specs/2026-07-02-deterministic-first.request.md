---
artifact_type: feature-request
schema_version: 1
created_at: 2026-07-02T00:00:00Z
source_sha: 0a126ad
generator: feature
status: queued
depends_on: cost-control-finish-lanes
stale_after: null
dependency_refs:
  - renmark/cost.py
  - plugin/skills/_shared/model-routing.md
  - plugin/skills/_shared/subagent-budget.md
---

# Deterministic-first execution — queued feature request

**Status:** QUEUED (2026-07-02). Builds directly on `cost-control-finish-lanes`
(v0.28.0): extends the model-routing / subagent-budget / cost-preview discipline
with an explicit "prefer deterministic code/tools before AI or subagents" gate.
**Recommended:** build fresh after `/clear` (same `build` domain; queued so the
full request isn't lost).

## Goal

Renmark should prefer deterministic code/tools before using AI or subagents.
Before spawning a model call, check, in order:
1. Can this be answered by existing state, files, git, grep, or a parser?
2. Can a deterministic script/check perform this reliably?
3. Is this repeated enough to deserve a reusable check?
4. Is AI actually needed for judgment, synthesis, or ambiguity?

## Default routing

- deterministic check for exact validation
- Haiku/Sonnet for small interpretation
- specialized subagent for scoped ambiguous work
- Opus/Fable only for high-risk judgment

## Deterministic-first task examples

git/worktree status; version/release checks; package/zip creation; install/update
verification; PRD frontmatter validation; plan lint; mirror checks (CLAUDE.md ==
AGENTS.md); skill registry sync; test/lint/typecheck execution; artifact existence
checks; release readiness checklist.

## Acceptance criteria

1. Renmark documents deterministic-first routing.
2. Repeated pipeline gates use scripts/checks before AI.
3. Finish lanes use deterministic checks for release/package/install verification.
4. Subagents are not spawned for checks that code can perform.
5. Cost preview identifies which parts are deterministic vs model-driven.
6. Agency Mode can reuse deterministic gates for milestone verification.

## Likely shape (to refine at build time — MVP-first)

- New `_shared/deterministic-first.md` fragment (the routing rule + the 4-question
  gate + the task-example catalog) + mirrored CLAUDE.md/AGENTS.md rule block.
- A small deterministic "release-readiness / gate" helper module (or extend
  `renmark/finish_lanes.py` + `renmark/release.py::check_drift`) exposing the
  release/package/install verification checks as pure functions the finish lanes
  call — so AC3 is real code, not just docs.
- Extend `renmark/cost.py::CostPreview` (or `estimate_cost`) to tag each item /
  the preview as `deterministic` vs `model-driven` (AC5).
- Tests proving the gates run code (not a model) and the cost preview reports the
  deterministic/model split.
- Agency Mode spec cross-ref (AC6): note deterministic gates back milestone verification.

---

## Sub-scope (2026-07-02) — Worktree cost control (deterministic-first lifecycle)

Worktrees stay REQUIRED for safe isolated development (esp. renmark-on-renmark).
**Do not remove worktree isolation.** But worktree lifecycle management must be
deterministic-first:

- create worktree via git commands
- check current branch via git
- detect stale worktrees via `git worktree list`
- check divergence via `merge-base` / `rev-list`
- check diff size via `git diff --stat`
- verify clean tree via `git status --porcelain`
- cleanup via deterministic commands

Use AI ONLY when: branch history is ambiguous; merge risk needs interpretation;
conflicts require judgment; release readiness needs owner-level explanation.

### Worktree acceptance criteria
1. Worktree safety remains intact (isolation not removed).
2. Routine worktree checks are deterministic (git, not a model).
3. AI is not used for simple branch/status/diff checks.
4. Finish lanes SHOW whether worktree cleanup is included — NOTE: `LaneSpec.cleans_worktrees`
   already exists but `finish_lanes.lane_table()` does not render it; add a "Worktree"
   column (deterministic, tiny).
5. Renmark-on-renmark self-update finish keeps worktree cleanup but avoids unnecessary
   model calls (the merged-vs-branch check that gated ExitWorktree is exactly a
   `git branch --merged` / `rev-list` check — deterministic).

### Note from the v0.28.0 finish (evidence this is needed)
During the v0.28.0 self-update finish, the merged-branch safety check before worktree
removal was done with `git branch --merged` + comparing the merge's 2nd parent to the
branch tip — purely deterministic, no model call. That pattern should be codified as a
reusable `finish_lanes`/worktree helper so every self-update finish reuses it.

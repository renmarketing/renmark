# R-0.0 Release-Candidate and Tagging Policy

Per Owner Decision 3 (`governing-methodology-addendum-03.md`): keep the existing release channel, no new distribution system.

## Flow

```text
1. Development/integration happens on an isolated branch/worktree
   (e.g. release/R-0.0-baseline-and-prd-reconciliation, branched from main).
2. WP-1..WP-5 land on that branch. Each work package is a normal commit,
   following the existing repo convention (see recent CHANGELOG.md entries
   for the established message/changelog-entry format).
3. A complete release candidate is produced on that branch: PRD addendum +
   ADR-001 + 3 benchmark definitions + baseline-report.md + 3 scenario JSONs
   + instrumentation behavior-neutral proof.
4. Required engineering verification (contract, runtime, reproducibility
   inspections per contract.yaml) run against that candidate.
5. Tag the candidate: vX.Y.Z-rc.1 (X.Y.Z = next version per existing
   convention - see "Versioning" below).
6. Owner (or an explicitly delegated evaluator, per Decision 2) performs the
   internal-acceptance-scenario.md checklist against the RC.
7. On ACCEPTED / ACCEPTED WITH FOLLOW-UP: merge the branch into main,
   tag vX.Y.Z (final), per the existing release process (VERSION,
   pyproject.toml, renmark/__init__.py, plugin/.claude-plugin/plugin.json,
   plugin/.codex-plugin/plugin.json, .claude-plugin/marketplace.json,
   README.md all updated together — the same 7-8 file set used in every
   prior release commit, e.g. this session's own v0.39.2 fix).
8. On REJECTED / BLOCKED: branch stays open, no tag promotion, findings
   feed back into a revised WP-3/WP-4/WP-5 cycle.
```

## Versioning

Per Owner instruction: "Use the repository's existing versioning convention if it differs. Do not change the versioning scheme as part of R-0.0 unless an incompatibility is found."

Current convention observed directly in this repo (confirmed via `renmark.release check` and recent commit history): a flat `X.Y.Z` bumped in lockstep across 8 locations (`VERSION`, `pyproject.toml`, `renmark/__init__.py`, `plugin/.claude-plugin/plugin.json`, `plugin/.codex-plugin/plugin.json`, `.claude-plugin/marketplace.json` ×2, `README.md`) for every discrete change, tracked via `renmark/release.py`'s `check_drift`/`drift_report`. Current version: **0.39.2**.

No semver-major/minor distinction is currently enforced by tooling (patch-level bumps have been used for both bug fixes and doc/contract changes alike, per CHANGELOG.md history). R-0.0's own version bump (if any) follows this same existing convention — **no new versioning scheme introduced**. Whether R-0.0 itself warrants a version bump at all (since it's internal-enablement, not a functional change) is a WP-1-time decision, not decided here.

## Rollback

R-0.0's `prohibited_paths` (see `contract.yaml`) blocks all `renmark/**` and `plugin/**` production-code changes this release. Rollback is therefore simple: `git revert` the release branch's merge commit, or reset `main` to the pre-merge tag if the merge hasn't been pushed/shared yet — no production behavior to untangle, no user-facing regression possible from this release by construction.

## What this policy does NOT do

- Does not introduce CI/CD automation, a package registry, or any deployment target beyond this GitHub repo — consistent with Owner Decision 3.
- Does not pre-commit to whether R-0.0 gets a real version bump — that's confirmed at WP-1 time once the actual diff size is known.
- Does not resolve the instrumentation-path question (see `benchmark-budget-and-circuit-breakers.md`) — that's a prerequisite for WP-4/WP-5, tracked separately.

---
artifact_type: rethink-intake
schema_version: 1
created_at: 2026-08-03T00:00:00Z
source_sha: c674185
related_plan: null
generator: sonnet
stale_after: null
dependency_refs: []
---

# Transformation Intake — renmark-architecture

**Target:** renmark itself (this repo)

**Desired outcome:** Modernize architecture — existing pipelines/behavior stay,
but the internal structure needs to change to support growth/maintainability.

**Protected behavior:** Nothing pinned yet. Owner deferred to stage 1/2
evidence to determine what's actually load-bearing before committing to a
protected list. (Note for exception check-in: since nothing is pre-pinned,
stage 2's baseline output itself becomes the protected-behavior reference
going forward.)

**Constraints:** None known yet — no hard timeline/budget/platform/team
constraint stated. Record as open; let evidence drive scope.

**Non-goals:** No explicit non-goals yet. (Corrected 2026-08-03: the original
"Both of the above" recording was ambiguous and could be misread as a firm
double constraint; the Owner clarified no non-goal is locked in yet. Treat
"structural/architecture-only, no skill-prose/UX rewrite, no new
pipelines/features" as the working assumption from the desired-outcome
answer, not a hard non-goal, until confirmed at a later gate.)

**Areas open to change:** Everything is open — no area pre-declared settled.
Stages 1–5 evidence (survey, PRD acceptance map, external benchmark,
modularity assessment) drives what actually changes.

**Decision log:**
- 2026-08-03: Intake captured via AskUserQuestion, three rounds (target repo,
  outcome; protected/constraints/non-goals; open areas). Owner chose renmark
  itself as target, "Modernize architecture" as outcome.
- 2026-08-03: Exception check-in (triggered by Stage 3's PRD acceptance
  mapping, flag 3) resolved. Decision: a behavior-preserving structural split
  of `renmark/cli/_engine.py` and `renmark/lifecycle.py` (same public
  functions/imports/call sites, verified via before/after test-suite parity)
  is EXEMPT from REQ-30's UPDATE gate. Any change touching actual
  routing/dispatch decisions, context limits, or gate frequency still
  requires the REQ-30 baseline (currently unmeasured, per
  `.renmark/memory/orchestration-baseline.md`) plus the UPDATE gate. This
  decision governs Stage 6 classification and Stage 7 blueprint scope for
  these two modules.

# Governing Methodology Addendum 03: Consolidated Doctrine + R-0.0 Owner Decisions

**Status:** Governing — binding decisions in Part 2 resolve the open questions from addendum-02.
**Authority:** Direct instruction from Roberto (Owner), authority order rank 1.
**Date:** 2026-08-01.

## Part 1 — Consolidated operating model (as supplied)

This restates and consolidates addendum-01 (4 runtime roles + deterministic subsystems, Phase sequencing) and addendum-02 (release-oriented milestones, acceptance ladder, lifecycle) into one coherent statement. No new concepts beyond those two documents; stored here verbatim for a single canonical reference point going forward, per the Owner's framing: "the internal governance exists to reduce wasted inference, context bloat, rework, and supervision — not to expose more process to the user."

Core operating model: Owner (Roberto) → General Contractor (main session) → Planner (Architecture mode for major system decisions / Milestone mode for executable release work — modes, not separate mandatory agents) → bounded Workers → independent Inspectors. Governor/Integrator/Ledger are primarily deterministic software, not conversational agents.

Release-oriented milestones: a milestone is a distinct, usable, testable product advancement, not completed internal modules. Each delivers a user-visible capability, a working release candidate, automated verification, independent inspection, a user-level acceptance scenario, a rollback procedure, and observation/feedback after release. Work Orders complete technical tasks; milestones complete user outcomes.

Three (four, counting research spike) execution paths: Patch (targeted tests + inspection), Feature release (integration + verification + user acceptance + release), Architectural release (architecture planning + approval + migration testing + controlled release), Research spike (bounded experiment → evidence, not production implementation). Small tasks use a fast path, bypassing the full planning/multi-agent process.

Authority boundaries: Planner plans, does not implement. Workers implement only their assigned scope, cannot redesign/replan/dispatch agents. Inspectors verify, do not repair — repairs become separate Work Orders. Integrator applies/validates changes. Only the General Contractor controls dispatch and workflow progression. Roles define authority boundaries; they do not automatically require separate model calls.

Context/artifact discipline: project truth lives in structured artifacts (release contracts, Work Orders, Work Results, Inspection Reports, Escalation Requests, release closeouts), not long conversation history. Each role gets minimum necessary context. Resumable from artifacts without reloading prior conversations.

Budget/orchestration controls: every dispatch needs a reason, bounded scope, defined output, call budget, retry limit, stopping condition. Nested dispatch, speculative agents, unlimited repair loops, and automatic replanning are prohibited. Replanning requires evidence (Owner requirement change, impossible contract, genuine architectural conflict).

Verification and user acceptance: component tests → integration/system tests → independent inspection → real user-level acceptance scenario → short observation period post-release. For Renmark itself: an actual natural-language feature request, judged on usefulness, efficiency, reliability, and ease of supervision.

Dogfooding: Renmark uses this same methodology on itself. Valid Renmark releases: Controlled Worker Execution, Budgeted Orchestration, Independent Verification, Remote WritingMate Worker Support. Internal components are implementation details supporting these — not sufficient milestone definitions alone.

Continuous feature advancement: small vertical releases producing complete user capabilities (Release 1: create+save → Release 2: edit+validate → Release 3: publish+share), not horizontal layers (all-DB → all-services → all-API → all-UI) unusable until the end.

WritingMate: added only after bounded Work Orders, structured Worker responses, scope validation, secret redaction, safe patch integration, local test execution, independent inspection, and provider budgets/failure controls exist. Initially small implementation/testing/analysis/review tasks; proposes code/patches which Renmark applies, tests, and verifies locally.

Overall objective (user-facing simplicity, restated verbatim): describe the desired capability → review only important assumptions → receive a working release candidate → test it as a user → accept it or provide feedback → advance to the next release.

## Part 2 — Binding Owner decisions (resolves addendum-02's 3 open questions + adds Phase/Release relationship rules)

### Decision 1: R-0.0 gates R-0.1

R-0.1 ("Bounded Small-Task Fast Path") is the first user-testable product release, but **R-0.0 must close first** — it establishes the PRD invariants, baseline measurements, and comparison criteria needed to determine whether R-0.1 is actually an improvement.

**Do not manufacture an end-user story for R-0.0.** Classify it as an **internal-enablement release** with an internal acceptance scenario:
- The PRD addendum is reviewed and approved.
- The three benchmark definitions are reproducible.
- Current Renmark behavior is measured.
- Baseline results include: inference calls, dispatches, replans, retries, context estimates, duration, completion status, result quality.
- The instrumentation is shown to be behavior-neutral when disabled.
- The evidence is sufficient to evaluate R-0.1 later.

R-0.0 still passes the full release lifecycle, but its acceptance authority evaluates **operational readiness and evidence**, not a user-facing feature.

### Decision 2: Roberto remains the default final acceptance authority

For: user-visible feature releases; architectural releases; changes to Renmark governance/orchestration behavior; releases materially affecting cost, context, routing, or reliability — **final ACCEPTED / ACCEPTED WITH FOLLOW-UP / REJECTED / BLOCKED is Roberto's**, even if execution of the acceptance scenario is delegated to Claude, Codex, automated tests, or another evaluator.

To avoid Roberto becoming a bottleneck, a release contract **may** define preapproved delegated acceptance for: internal-enablement releases; documentation-only releases; low-risk maintenance releases; patches with no user-visible or governance behavior change. **Delegated acceptance must be explicit in the release contract — never assumed.** Even when execution is delegated, evidence and decision must be recorded.

### Decision 3: Keep the current release channel — no new distribution system

Flow: development/integration in an isolated milestone branch or worktree → complete release candidate before merge → required engineering verification and acceptance performed against that candidate → accepted release merged into `main` → final release identified with the existing version-tag mechanism.

Use a pre-release tag `vX.Y.Z-rc.1` for an acceptance candidate, then `vX.Y.Z` after final acceptance, if useful. **Do not change the versioning scheme as part of R-0.0 unless an incompatibility is found.**

### Additional decisions (Phase/Release relationship)

- Keep the complete 10-state release lifecycle — READY and INTEGRATED are valid and remain.
- **Phases remain sequencing and dependency containers. Releases remain the units of demonstrable advancement. Work Orders remain the units of implementation.**
- A Phase may contain one or more releases when that produces cleaner, independently testable user value.
- A release may draw from parts of multiple Phases when dependencies require it, **but the contract must state that explicitly**.
- Do not force every internal implementation activity to become a separate release.
- **A Phase may not close merely because its internal tasks are complete — its associated release outcomes must meet their acceptance and observation requirements.**

## This pass's deliverable (per Owner instruction)

> Draft the R-0.0 release contract and its supporting Phase 0 specifications using these decisions. Do not instrument production code or execute benchmark runs yet.

Produced: `milestones/R-0.0/contract.yaml`, `milestones/R-0.0/internal-acceptance-scenario.md`, `milestones/R-0.0/benchmark-budget-and-circuit-breakers.md`, `milestones/R-0.0/release-candidate-and-tagging-policy.md`. `milestones/INDEX.md` updated. No production code touched. No benchmark executed. Stopped for Owner approval — see the accompanying Done/Found/Next report.

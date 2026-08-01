# Governing Methodology Addendum 02: Release-Oriented Milestones

**Status:** Governing — supersedes/extends `governing-methodology-addendum-01.md`'s Phase framing
**Authority:** Direct instruction from Roberto (Owner), authority order rank 1
**Date:** 2026-08-01 (session continuation)
**Scope:** Applies to (1) Renmark's own development, and (2) every project Renmark plans, implements, verifies, and releases going forward. This is doctrine, not a one-off rule for the current refactor — it sits alongside context hygiene and deterministic execution as a core Renmark principle.

**Relationship to addendum-01:** addendum-01 collapsed the runtime role zoo (10 roles → 4 + deterministic subsystems) and replaced the original 10-milestone sequence with a Phase 0–8 sequence. That correction is still valid and unchanged. This addendum corrects a *different* axis: what it means for a phase/milestone to be "done." Under addendum-01 alone, a phase completes when its listed tasks are implemented and tests pass. Under this addendum, a **release** (the renamed unit, see below) completes only when a user-testable capability has been demonstrated and accepted — engineering completion is a *step toward* that, not the finish line.

---

## Full text as supplied by the Owner

> Claude's revised roadmap currently treats phases mostly as implementation steps. Your proposal changes the governing unit from "technical milestone completed" to "usable capability released and validated." That also addresses the earlier concern that user experience could remain unprotected until late in the build.

### The key distinction

| Level | Meaning |
|---|---|
| Roadmap phase | Internal evolution of the project or platform |
| Milestone release | A distinct, usable, testable product capability |
| Work order | An implementation task contributing to that release |

A Worker completing ten tasks does not complete a milestone. A milestone completes when a user can use, evaluate, and accept a meaningful new capability.

### Example for Renmark itself

Instead of "Milestone 2: Implement authority classes and schemas," use:

> **Release 0.4: Controlled Worker Execution** — A user can ask Renmark to complete a bounded feature, and Workers cannot replan, expand scope, or dispatch nested agents.

That release contains the same internal authority controls, but frames a user-testable outcome: Roberto starts a real feature → Renmark selects fast/normal path → Worker stays in scope → a budget limit prevents runaway dispatch → Renmark returns a usable result → Roberto compares against the previous version. Stronger than "the authority module's tests passed."

### The acceptance ladder

Every milestone release passes four levels: **1. Component verification** (unit/schema tests, static analysis, permission/policy tests) → **2. System verification** (integration, e2e, repo-mutation checks, retry/failure/recovery paths) → **3. User acceptance** (a human performs the intended workflow, inspects the result, confirms simpler/faster/more reliable, records feedback) → **4. Release observation** (defects, usage/runtime behavior, feedback, regression check, stable-or-repair decision).

### Release lifecycle

```text
PLANNED → READY → IN DEVELOPMENT → INTEGRATED → ENGINEERING VERIFIED →
RELEASE CANDIDATE → USER ACCEPTANCE → RELEASED → OBSERVED → CLOSED
```

(Owner's first draft omitted READY/INTEGRATED from the state list but included them in the requirements section — the 10-state form above is the reconciled canonical list used throughout this addendum.)

USER ACCEPTANCE results in: ACCEPTED / ACCEPTED WITH FOLLOW-UP / REJECTED / BLOCKED.

### Work classification and required path

- **Patch** (bounded correction, no material new user journey): `Work Order → integration → tests → applicable inspection → patch release`
- **Feature Release** (distinct new user capability): `Milestone contract → implementation → integration → engineering verification → user acceptance → feature release`
- **Architectural Release** (subsystem/boundary/data-model/compatibility change): `Architecture planning → Owner gate → milestone planning → implementation → migration+integration testing → user acceptance → controlled release`
- **Research Spike** (uncertainty reduction, no production release): `Question → bounded experiment → evidence → recommendation or decision gate`. A spike cannot silently become implementation.

### Planning hierarchy (4 units, not 3)

**Product Roadmap** (sequence of user outcomes/capabilities) → **Milestone Release** (one independently testable, potentially releasable increment of user value) → **Work Package** (groups related implementation work for a release) → **Work Order** (one bounded implementation/repair task). Work Orders complete implementation activity; Milestone Releases complete user outcomes.

### Milestone release requirements (every release must define)

Release identifier/version; user-visible capability; intended user/actor; user journey enabled; problem/need addressed; included scope; explicit exclusions; technical dependencies; applicable architectural constraints; work packages and work orders; automated acceptance criteria; required Inspectors; demonstration procedure; user-acceptance scenario; release artifact; migration requirements; rollback procedure; observation period; feedback/defect handling; conditions for release closure.

A release with no identifiable user-testable outcome must be classified as one of: Internal enablement release / Research spike / Migration release / Maintenance release — and must still define observable evidence of value.

### User-level acceptance (required, automated verification is necessary but insufficient)

Every user-facing milestone needs ≥1 acceptance scenario from the user's perspective, identifying: starting state, user action, expected visible behavior, expected result, failure behavior, evidence captured, acceptance decision. GUI apps → browser/device interaction where practical. APIs → consumer-level request/response. CLI tools → the real command and expected output. Agentic systems (Renmark itself) → a complete natural-language task from initiation to demonstrated result.

### Renmark self-development (dogfooding)

Each Renmark release must provide a demonstrable capability. Examples given: **Controlled Execution Release** (bounded feature run, no unauthorized scope expansion/nested delegation), **Budgeted Orchestration Release** (configurable execution budget, safe stop on exhaustion), **Independent Verification Release** (evidence-based independent inspection before acceptance), **Remote Worker Release** (WritingMate Worker proposes bounded code, Renmark applies/tests/inspects/presents as a candidate). Internal modules are implementation details supporting these outcomes — not independently sufficient milestone definitions.

### Universal project behavior (applies to every project Renmark builds, not just itself)

Prefer vertical increments delivering end-to-end value over horizontal layers unusable until late:

**Preferred:** Release 1 (create+save a basic project) → Release 2 (edit+validate) → Release 3 (publish+share).
**Avoid:** Milestone 1 (all DB models) → Milestone 2 (all service classes) → Milestone 3 (all API routes) → Milestone 4 (the interface).

Horizontal technical work may occur inside each release; the milestone *boundary* must represent a usable vertical capability.

### Continuous feature advancement

Each release should be independently testable, preserve previously accepted behavior unless explicitly changed, contain a rollback path, avoid depending on unfinished future milestones, produce a usable/observable advancement, and capture user feedback before the next major release finalizes. The roadmap may evolve from evidence/feedback, but **accepted milestone history must not be rewritten** — new understanding creates a follow-up release, change request, defect release, or architectural revision, never a retroactive redefinition of an already-accepted release.

### Release contract shape (canonical, reconciles with addendum-01's Phase/role vocabulary)

```yaml
release_id: R-0.4
title: Controlled Worker Execution
release_type: feature   # patch | feature | architectural | research-spike | internal-enablement | migration | maintenance

user_value:
  actor: Renmark user
  capability: Run a bounded feature without uncontrolled replanning or nested agent dispatch
  problem_addressed: Excessive orchestration consumes quota before useful work is completed

user_journey:
  starting_state: Existing Renmark project
  action: User submits a bounded feature request
  expected_result: Feature is implemented within declared scope and budget

scope: { included: [], excluded: [] }
work_packages: []
engineering_acceptance: []
required_inspections: []

user_acceptance:
  scenario: []
  evidence_required: []
  decision_authority: Owner

release:
  channel: preview   # preview | internal | production, etc.
  artifact: []
  rollback: []

observation:
  period: one representative follow-up task
  metrics: [total model calls, replans, context consumed, completion quality, owner intervention required]

status: planned   # PLANNED | READY | IN DEVELOPMENT | INTEGRATED | ENGINEERING VERIFIED | RELEASE CANDIDATE | USER ACCEPTANCE | RELEASED | OBSERVED | CLOSED
```

### Release closure rule

A milestone may **not** be marked complete merely because code was written, unit tests passed, Workers reported completion, the branch merged, or the General Contractor believes the outcome is correct. Closure requires: (1) engineering acceptance, (2) required Inspector approval, (3) a complete release candidate, (4) user-level acceptance when applicable, (5) release or approved internal deployment, (6) observation evidence, (7) closeout documentation.

### UX protection (unchanged from addendum-01, restated here as doctrine)

Internal governance complexity stays invisible by default. Normal user experience: describe the desired capability → review material assumptions when necessary → receive a release candidate → test/demonstrate → accept or give feedback → continue to the next release. Users never manage Workers, Inspectors, artifact schemas, or internal role transitions during ordinary use.

### Success principle

> Renmark does not succeed because it generated and tested code. Renmark succeeds when it repeatedly advances a product through small, coherent, usable, tested, accepted, and observable releases.

---

## Reconciliation with `governing-methodology-addendum-01.md`

Addendum-01's Phase 0–8 sequence is **not replaced**, it is **reframed**. Each blocking Phase becomes the engineering-side work inside one or more Releases; the Phase itself no longer "completes" on task-done — it completes when the Release built from it reaches CLOSED on the ladder above.

| Addendum-01 unit | Under this addendum |
|---|---|
| "Phase" (0–8) | Renamed conceptually to a **Release track** — a phase's work still happens, but its exit criterion is now the acceptance ladder (Component → System → User → Observation), not "tasks done." |
| Phase completion = tasks implemented + tests pass | **Insufficient.** Now requires: engineering acceptance + required Inspector approval + release candidate + user acceptance (when user-facing) + release + observation evidence + closeout. |
| No explicit user-acceptance step existed in addendum-01's phases | Added — every user-facing Phase/Release now requires §5's user-level acceptance scenario (for Renmark: a complete natural-language task from initiation to demonstrated result). |
| Milestone numbering scheme (Phase 0, 1, 2...) | Retained as the *sequencing* mechanism, but each Phase should now be re-expressed as one or more named **Releases** (e.g. "Release 0.4: Controlled Worker Execution" rather than "Phase 2: Authority boundaries and budget controls") so the unit of completion is visible capability, not internal category. |
| `milestones/M-0/contract.yaml` schema (superseded) and its would-be P-0 replacement (not yet drafted) | Both are superseded again — any future release contract should use the `release_id`/`user_value`/`user_journey`/lifecycle-`status` shape from this addendum, not the original Work-Order-only milestone contract shape. |

## What still needs Owner input before any release contract can move past PLANNED

This addendum defines *how* releases are structured and closed — it does not itself answer:

1. What is Release 1 for Renmark's own governed-orchestration work? (Candidate, per addendum-01's Phase 1+2 merge: "Release 0.1 — Bounded Small-Task Fast Path," since Phase 1 (UX/compatibility harness) and the blocking subset of Phase 2 (authority boundaries) together would make the first user-testable claim: *a small task runs through General Contractor → Worker → deterministic tests → Inspector-only-if-risk-requires, and the existing single-command UX is unchanged.* This is proposed, not decided.)
2. Who performs USER ACCEPTANCE for Renmark's own releases — Roberto directly each time, or a defined acceptance scenario Roberto can delegate?
3. What "channel" does a Renmark release ship through (`release.channel` in the contract) — this repo's `main` branch + version tag, as it already does today, or something new?

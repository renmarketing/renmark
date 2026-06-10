# Decisions (ADRs)

Architecture Decision Records. Newest at top. Each ADR captures: context (why we needed to decide), the decision, alternatives considered, and consequences. Updated by `/renmark:brainstorm` and `/renmark:plan` when they make non-trivial calls; hand-editable.














## ADR-022 — Finished feature reporting-and-usage-analytics

**Date:** 2026-06-09
**Status:** Accepted

**Context.** Completed stages: plan-drafted, plan-validated, created, verified, reviewed [corrected 2026-06-09 — stage tracking dropped verified/reviewed; see audit-delta]

**Decision.** Branch feature/reporting-and-usage-analytics reached stage ready-to-release

---

## ADR-021 — Released renmark v0.7.8

**Date:** 2026-06-09
**Status:** Accepted

**Context.** release-version-snapshot feature; merged to main, branch deleted

**Decision.** Tagged v0.7.8; snapshot .renmark/version/v0.7.8 (dogfood) + ~/projects/ai-system-renmark-v0.7.8-2026-06-09.zip

---

## ADR-020 — Finished feature release-version-snapshot

**Date:** 2026-06-09
**Status:** Accepted

**Context.** Completed stages: plan-drafted, plan-validated, created, verified, reviewed

**Decision.** Branch feature/release-version-snapshot reached stage ready-to-release

---

## ADR-019 — Released renmark v0.7.7

**Date:** 2026-06-09
**Status:** Accepted

**Context.** Backlog-driven loop execution (REQ-13/14); merged feature/backlog-driven-loop-execution into main

**Decision.** Tagged v0.7.7 + packaged ~/projects/ai-system-renmark-v0.7.7-2026-06-09.zip (local; no remote)

---

## ADR-018 — Finished feature backlog-driven-loop-execution

**Date:** 2026-06-09
**Status:** Accepted

**Context.** Completed stages: plan-drafted, plan-validated, created, verified, reviewed

**Decision.** Branch feature/backlog-driven-loop-execution reached stage ready-to-release

---

## ADR-017 — Escalated task 2 from codex to sonnet

**Date:** 2026-06-09
**Status:** Accepted

**Context.** codex CLI sandbox read-only this session; could not write tests/test_backlog.py — reassigned to writable sonnet Agent (plan: .renmark/plans/2026-06-09-backlog-driven-loop-execution.plan.md)

**Decision.** Re-route to sonnet

**Alternatives considered.**
- Retry codex
- Fail the task

**Consequences.**
- Higher cost
- Higher capability

---

## ADR-016 — Finished feature loop-mode

**Date:** 2026-06-09
**Status:** Accepted

**Context.** Completed stages: brainstorm-complete, plan-drafted, plan-validated, created, verified; new core renmark/loop.py + state/usage.py + /renmark:loop; codereview full codex 5 Major + 2 Minor + 1 Nit (stall-on-failure, budget overshoot, never-raise) all fixed+re-verified

**Decision.** Branch feature/loop-mode reached stage ready-to-release

---

## ADR-015 — Finished feature modularity-health-lens

**Date:** 2026-06-08
**Status:** Accepted

**Context.** Completed stages: brainstorm-complete, plan-drafted, plan-validated, created, verified; new core renmark/modularity.py; codereview full codex 3 Major + 2 Minor (metric accuracy/suppression) all fixed+re-verified

**Decision.** Branch feature/modularity-health-lens reached stage ready-to-release

---

## ADR-014 — Finished feature proportional-pipeline

**Date:** 2026-06-08
**Status:** Accepted

**Context.** Completed stages: brainstorm-complete, plan-drafted, plan-validated, created, verified; touches core sizing.py; codereview full codex 2 Critical + 2 Major + 1 Minor (false-lite holes) all fixed+re-verified+11 regression tests

**Decision.** Branch feature/proportional-pipeline reached stage ready-to-release

---

## ADR-013 — Pipeline cost efficiency: build C+A (proportional+tiered) first, defer B (batch)

**Date:** 2026-06-08
**Status:** Accepted

**Context.** Evidence: a 2-task feature cost ~340k tokens, ~40% of it a 120-130k codex codereview paid once per feature regardless of size. Basis for choosing C+A over higher-raw-reduction B/all: proportionality (cost tracks risk/size), automatic per-feature savings (no behavior change), lowest build cost+risk, preserves per-feature isolation that caught real bugs this session. B is situational (needs batching, reduces isolation, adds latency) — better sequenced second for backlog burndown.

**Decision.** Build proportional codereview (auto-skip/downgrade codex on tiny/doc diffs; opt-in always) + size-tier lite-lane (tiny features bypass heavy stages) FIRST. Defer roadmap-batch execution (B) and modularity health lens to backlog.

---

## ADR-012 — Finished feature acceptance-criteria

**Date:** 2026-06-08
**Status:** Accepted

**Context.** Completed stages: plan-drafted, plan-validated, created, verified; doc/skill-only; codereview 0 critical, 1 Major + 1 Minor (cross-file format) fixed

**Decision.** Branch feature/acceptance-criteria reached stage ready-to-release

---

## ADR-011 — Finished feature init-pipeline

**Date:** 2026-06-08
**Status:** Accepted

**Context.** Completed stages: brainstorm-complete, plan-drafted, plan-validated, created, verified; codereview 0 critical, 4 Major + 1 Minor all fixed+re-verified+tested

**Decision.** Branch feature/init-pipeline reached stage ready-to-release

---

## ADR-010 — Finished feature next-step-engine

**Date:** 2026-06-08
**Status:** Accepted

**Context.** Completed stages: brainstorm-complete, plan-drafted, plan-validated, created, verified; codereview 0 critical, 3 major + 1 minor all fixed+tested

**Decision.** Branch feature/next-step-engine reached stage ready-to-release

---

## ADR-009 — Gap discovery extends /renmark:roadmap (supersedes ADR-005 deferral)

**Date:** 2026-06-08
**Status:** Accepted (design — formalized at plan/execution time)

**Context.** The `next-step-engine` feature makes every interaction guided and
adds a "what to build next" gap-discovery engine. A codebase survey found only
3/19 skills cite the shared hand-off contract; 16 lack a consistent next-step,
5 have none. ADR-005 had *deferred* a "roadmap PRD progress view" as bloat-now.

**Decision.**
- Gap discovery **extends `/renmark:roadmap`** rather than adding a standalone
  `/renmark:next` skill — deliberately reactivating ADR-005's deferred item,
  scoped tightly: **read-only, advisory, human-gated**, reuses the ALIGN subagent
  pattern (roadmap never reads the PRD body inline), never a second PRD writer.
- Next-step guidance **generalizes existing machinery**: `NEXT_BY_STAGE` +
  `next_recommended()` (Tier 0) and `_shared/handoff-menu.md` (verify gates,
  Tier 1) — a new `_shared/next-steps.md` umbrella references them; no rebuild.
- State source is **lifecycle.json + pipeline.json** (durable, survives `/clear`).
- Tier-2 live web research is **opt-in, default off**.
- `/renmark:finish` (post-release) and **`/renmark:init`** (after mapping) both
  route into roadmap's gap mode — init gains a guided hand-off (user tweak).

**Alternatives considered.**
- Standalone `/renmark:next` skill — rejected to avoid a new skill surface
  overlapping roadmap (ADR-005 anti-bloat).
- Merge `handoff-menu.md` into one file — rejected; keep the working gate
  contract, add an umbrella that references it.
- Web research on by default — rejected (cost/context hygiene).

**Consequences.**
- Pro: one shared contract + lint guard prevents per-skill menu drift.
- Pro: reuses proven, unimplemented-skill-safe routing.
- Con: reverses an ADR-005 deferral — mitigated by the read-only/advisory scoping
  above. This ADR documents the supersession.

**Spec:** `.renmark/specs/2026-06-08-next-step-engine.spec.md`

---

## ADR-008 — Finished feature blueprint

**Date:** 2026-06-05
**Status:** Accepted

**Context.** Completed stages: brainstorm-complete, plan-drafted, plan-validated, created, verified, ready-to-release

**Decision.** Branch feature/blueprint reached stage ready-to-release

---

## ADR-007 — Escalated task 6 from codex to sonnet

**Date:** 2026-06-05
**Status:** Accepted

**Context.** codex --task ran in a read-only sandbox and could not write tests/test_blueprint.py; sonnet Agent wrote 22 passing tests. (plan: .renmark/plans/2026-06-05-blueprint.plan.md)

**Decision.** Re-route to sonnet

**Alternatives considered.**
- Retry codex
- Fail the task

**Consequences.**
- Higher cost
- Higher capability

---

## ADR-006 — Finished feature prd-source-of-truth

**Date:** 2026-06-05
**Status:** Accepted

**Context.** Completed stages: brainstorm-complete, plan-drafted, plan-validated, created; codereview 0 critical

**Decision.** Branch feature/prd-source-of-truth merged to main; reached stage ready-to-release

---

## ADR-005 — PRD touchpoint policy: one writer, one align contract, nothing else

**Date:** 2026-06-05
**Status:** Accepted

**Context.** With `PRD.md` shipped as the source of truth, there was pressure to
"bake the PRD into" more skills (brainstorm-as-writer, `verify --coverage`,
roadmap progress view, init/document PRD pointers). Each addition risks the two
failure modes the PRD feature was designed to avoid: **duplication** (the same
who/why/non-goals living in PRD *and* spec *and* scope contract) and **context
bloat** (more skills reading the PRD body, eroding the orchestrator-never-reads
hygiene pillar). The PRD and the brainstorm spec are at different altitudes —
PRD is *product-level* (one per project, durable); a spec is *feature-level*
(many per project). Collapsing them is the duplication trap.

**Decision.** Every renmark skill maps to exactly ONE of three PRD interactions:

1. **WRITE** (create/update) — *only* `/renmark:prd`. Every other skill that
   wants a PRD change **routes** to it (proposes); none write `PRD.md` directly.
   This keeps one writer and one human gate, and dissolves the "multiple entry
   points mutating one file" risk: start/brainstorm/feature all *route*, never
   *write*.
2. **ALIGN** (read-only ≤5-line verdict) — *only* via the
   `_shared/prd-alignment.md` subagent. No skill invents its own PRD-reading
   logic; the PRD body never enters orchestrator/router context. Users today:
   `feature` (drift gate). Added by this ADR: `brainstorm` (keep specs consistent
   with product direction) + a non-blocking nudge when no PRD exists yet.
3. **NOTHING** — the default, and correct for most skills.

`plan` is the one borderline case: it does a *light* read of `REQ-n` IDs for the
optional `serves:` traceability field (not a full ALIGN). This is load-bearing —
requirement coverage flows plan → tasks → verify transitively, which is *why*
`verify --coverage` is unnecessary.

**Alternatives considered (rejected as duplication or speculation).**
- **brainstorm writes the PRD** — rejected. Brainstorm already writes a spec;
  making it a second PRD writer duplicates who/why/non-goals across two docs and
  adds a second writer to a single-writer artifact.
- **`verify --coverage` (REQ coverage lens)** — rejected. Traceability already
  flows plan → tasks → verify; a coverage mode re-reads the PRD to recompute what
  the plan already encodes. Also already a spec non-goal.
- **roadmap "PRD progress view"** — deferred. Genuine altitude overlap (both
  describe "direction"), but roadmap is sequence-ordered and PRD is
  requirement-ordered; a read-only view is plausible later, bloat now.
- **init / document PRD pointer** — rejected. `/renmark:prd` already maintains
  the plain-text PRD pointer in CLAUDE.md/AGENTS.md; a second writer of that
  pointer is duplication. `document-release` doesn't exist in this repo and would
  just re-run feature's drift check.
- **orchestrate/finish touch the PRD** — rejected. orchestrate reading the PRD
  violates the hygiene pillar; finish only *routes* to `/renmark:prd` on release.

**Consequences.**
- Pro: one writer, one align contract — the duplication and bloat failure modes
  are structurally prevented, not just discouraged.
- Pro: future skill authors have a decision rule (WRITE / ALIGN / NOTHING) and a
  bloat list to check proposals against.
- Con: requirement coverage stays implicit (via plan traceability), not a
  first-class verify report — accepted trade-off.
- Non-goals split by altitude: **product-level non-goals → PRD**; **this-build's
  MVP cut → scope contract**. Cross-reference, never copy.

---


## ADR-004 — Finished feature qa-flow-memory

**Date:** 2026-06-04
**Status:** Accepted

**Context.** Completed stages: plan-drafted, plan-validated, created, verified

**Decision.** Branch feature/qa-flow-memory reached stage ready-to-release

---

## ADR-003 — Finished feature verify-browser-qa

**Date:** 2026-06-04
**Status:** Accepted

**Context.** Completed stages: plan-drafted, plan-validated, created, verified, ready-to-release

**Decision.** Branch feature/verify-browser-qa reached stage ready-to-release

---

## ADR-002 — Finished feature codereview-focus

**Date:** 2026-05-29
**Status:** Accepted

**Context.** Small 3-task feature; per CLAUDE.md 'small changes stay on main'; folded into v0.5.6 release alongside lifecycle-hygiene

**Decision.** Landed --focus optimize/standards directly on main

---

## ADR-001 — Finished feature lifecycle-hygiene

**Date:** 2026-05-29
**Status:** Accepted

**Context.** Completed stages: plan-drafted, plan-validated, created, verified

**Decision.** Branch feature/lifecycle-hygiene reached stage ready-to-release

---

## ADR-000 — (example) Choose JSON over MessagePack for /api responses

**Date:** YYYY-MM-DD
**Status:** Accepted

**Context.** We need a serialization format for the public API. Latency-sensitive clients are mixed (browser + mobile + backend).

**Decision.** Use JSON.

**Alternatives considered.**
- MessagePack — 30% smaller payloads, but browser support is poor and tooling friction outweighs the gain.
- Protobuf — strong typing but requires schema sharing; our consumers are unknown.

**Consequences.**
- Pro: every consumer can speak JSON natively.
- Con: payloads are larger and parsing is slower at scale.
- Revisit if p99 serialization time > 50ms.

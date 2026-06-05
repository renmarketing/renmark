# Decisions (ADRs)


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

Architecture Decision Records. Newest at top. Each ADR captures: context (why we needed to decide), the decision, alternatives considered, and consequences. Updated by `/renmark:brainstorm` and `/renmark:plan` when they make non-trivial calls; hand-editable.

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

# Decisions (ADRs)





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

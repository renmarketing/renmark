# Decisions (ADRs)

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

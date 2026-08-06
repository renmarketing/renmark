---
artifact_type: rethink-intake
schema_version: 1
created_at: 2026-08-06T05:30:00Z
source_sha: 286d016
related_plan: null
generator: sonnet
---

# Transformation Intake — cross-host-native-tool-leverage

**Desired outcome:** Inventory the native tools available on each host renmark
runs on (Claude Code CLI, Codex CLI — Hermes deferred, see below), identify
where renmark has hand-rolled/re-engineered functionality a native tool now
provides, and adopt what's safe to adopt — without breaking renmark's
existing multi-host routing (Claude gets Claude-native calls, Codex gets
Codex-native calls, never a mismatched call surfacing on the wrong host).

**Protected behavior:**
- REQ-30 (orchestration efficiency is a protected capability) — any adopted
  native tool must not increase median token use or execution time by more
  than 15% over the `ORCHESTRATION-BASELINE-2026-08` pin, must not add a
  routine Owner gate, and must not weaken verification/completion/recovery
  behavior.
- G11 task isolation contract — bounded `SubagentOutput` only crosses back
  into orchestrator context; no adopted tool may leak a transcript, diff, or
  generated code into orchestrator context.
- Existing host-detection correctness — `renmark.hosts.capabilities_for` and
  every skill's `host="claude"|"codex"` branching must continue to route each
  host to ITS OWN native surface, never the other's.

**Constraints:** None stated beyond the above. Investigation-first —
`/renmark:rethink`'s own rule that stages 1-8 change no production code
applies as normal.

**Non-goals (this pass):**
- **Hermes is explicitly deferred.** No reference to "Hermes" exists
  anywhere in this repo, PRD.md, or renmark's docs. Owner chose to scope
  this transformation to Claude Code + Codex only; Hermes becomes a future
  transformation once its actual identity/docs/tool surface is known.
- **Not** a broader reassessment of renmark's whole multi-host abstraction
  shape (`renmark/hosts.py`, `capabilities_for`) — Owner confirmed the
  narrower "inventory + adopt" scope over the broader "reconsider the whole
  model" option.

**Areas open to change:** skill-prose routing instructions, dispatch-layer
host-detection/transport-selection code, any hand-rolled mechanism (cron
emission, worktree shell-outs, pause/resume bookkeeping) that duplicates
what a native tool on that host now provides.

**Areas explicitly NOT open to change (settled):** `WorkOrder` schema
(Release 3), the capability-envelope enforcement mechanism (Release 6), the
G11 isolation contract itself, the risk-tier/lens classifier (Release 8) —
these are renmark's own domain logic, not candidates for replacement by a
generic host primitive (confirmed in the prior same-session native-tool
inventory pass — see `.renmark/reports/` conversation context — as
genuinely renmark-only value).

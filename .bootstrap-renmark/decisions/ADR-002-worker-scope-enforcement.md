# ADR-002 — Worker Scope Enforcement (Detective, Deterministic, Host-Independent)

**Numbering note:** same isolated `.bootstrap-renmark/decisions/` namespace as
ADR-001 — distinct from `.renmark/memory/decisions.md`'s own ADR-001..ADR-045
sequence, per `governing-bootstrap-directive.md` §4. Not renumbered; migrates
together with ADR-001 if/when the bootstrap namespace merges into the
canonical one (next available there: ADR-046 onward).

**Date:** 2026-08-01
**Status:** Proposed — part of release R-0.1 ("Bounded Small-Task Fast
Path"), work package WP-2. Not yet ACCEPTED in the release-lifecycle sense —
evaluated at R-0.1's own acceptance step alongside the rest of its evidence.
**Supersedes:** nothing. Extends ADR-001's authority-boundary principle
("Workers implement only assigned scope, cannot redesign/replan/dispatch
agents") from a stated intent into an actual enforcement design.

## Context

R-0.0's Scenario C benchmark run produced a concrete, not hypothetical,
authority-boundary failure: a dispatched Worker attempted to force-delete 4
pre-existing files it did not create and had no authorization to touch. The
platform's own permission classifier blocked it. Reading the current
dispatch code (`renmark/providers/claude_agent.py::build_agent_dispatch`)
confirms why nothing in `renmark/**` itself would have: today's "scope" is
one sentence of prose in the dispatch prompt ("Modify exactly one file...
Do not create or edit any other file"), and the Worker's own self-reported
`SubagentOutput.touched_files` is never cross-checked against what actually
happened in the repository. R-0.0's closeout (`.bootstrap-renmark/
milestones/R-0.0/closeout.md`) recorded this as follow-up item F2: R-0.1's
contract must treat this finding as founding evidence for its scope, not
background color.

## Decision

Adopt a two-layer model for Worker scope, and build only the layer that is
actually Renmark's to build:

1. **Layer A (host-level, preventive, pre-existing, out of scope to
   change):** the live tool-permission prompt a host (Claude Code, Codex)
   shows before a destructive action executes. This already works — it's
   what stopped Scenario C. Renmark does not attempt to duplicate or
   replace it; no `renmark/**` code can intercept it.

2. **Layer B (Renmark-owned, detective and gating, deterministic, new for
   R-0.1):** a pure function, `verify_worker_scope(scope, repo, base_sha) ->
   ScopeVerdict`, that runs in the orchestrator after a Worker reports
   completion and before its output is accepted. It compares the Worker's
   **declared** scope (`WorkerScope.allowed_paths` + `allowed_actions`,
   populated from R-0.1/WP-1's classifier — not renegotiated mid-task)
   against the Worker's **actual** `git diff --name-status` output — never
   against the Worker's own self-reported `touched_files`. A delete or
   rename action is always a violation on the fast path, regardless of
   whether the path is in `allowed_paths`; any path outside
   `allowed_paths` is a violation regardless of action type.

A FAIL verdict blocks merge/commit/advancement (mirrors the existing
`IsolationViolation` refuse-don't-silently-accept posture for
`SubagentOutput`), does NOT trigger an automatic revert (itself a
destructive action outside a bare scope-check's authority), and produces an
auditable ledger record plus an escalation to Inspector/Owner — the exact
"Inspector only if risk requires it" trigger the routing model already
describes.

No-nested-dispatch enforcement is explicitly left partially unresolved:
Renmark's Python layer has no deterministic, host-independent signal today
for "did the Worker invoke another agent." This ADR does not claim otherwise
— WP-4 chooses between a contractual-only guarantee and a partial
transcript-based check, depending on what the active host actually exposes.

## Consequences

- The literal Scenario C reproduction (a scope excluding the 4
  `.renmark/audits/*` files, a diff that deletes them) becomes a required,
  concrete regression test for `verify_worker_scope`, not a paper claim.
- `verify_worker_scope` and `WorkerScope` are new, additive constructs —
  they do not modify `SubagentInput`/`SubagentOutput`'s existing field
  contracts, only add a scope-check step alongside them.
- Layer B only covers fast-path dispatches for R-0.1 (per its contract's
  explicit exclusion of Normal/Architectural Feature paths). Extending it
  further is a future release's decision, not implied here.
- This ADR does NOT claim Renmark can prevent a live destructive tool call
  — only that it can deterministically detect and block acceptance of one
  that the host didn't stop, independent of host, prompt-approval mode, or
  Worker honesty.

## Migration and rollback

Design-only as of this ADR — no `renmark/**` file is touched by WP-1 or
WP-2. `verify_worker_scope`/`WorkerScope` land in WP-4, gated behind an
explicit `allowed_paths` amendment naming the exact modules, same discipline
R-0.0 used for its own instrumentation. Rollback at every stage before WP-4
lands is a plain git revert of docs/design artifacts only.

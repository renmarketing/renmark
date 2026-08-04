---
artifact_type: rethink-intake
schema_version: 1
created_at: 2026-08-04T05:46:22Z
source_sha: 9bd233548a7f7b34695124596c3faa6398ec044b
related_plan: null
generator: sonnet
stale_after: null
dependency_refs: []
---

# Transformation Intake — artifact-lifecycle

**Target:** Renmark's `.renmark/` artifact and persistent-context subsystem
(not the whole repo — narrower scope than the prior `renmark-architecture`
rethink, which covered `renmark/` source structure and has already released
through its roadmap).

**Desired outcome:** Make `.renmark/` lean, bounded, and purposeful — reduce
what grows unbounded on disk and what gets pulled into agent/orchestrator
context — while making the directory Hermes-ready (i.e., safe for a future
lighter-weight context-loading mode to enumerate without recursively
ingesting everything under it).

**Protected behavior (non-negotiable, per Owner's explicit phrasing):**
- canonical decisions (PRD, plans, ADR-equivalents)
- acceptance evidence (verification/review artifacts tied to releases)
- recovery state (`.renmark/state/`, lifecycle/pipeline resumability)
- release history

**Constraints:**
- Phase 1 (this run) is strictly read-only: no delete, move, rewrite,
  archive, commit, or install of any existing artifact.
- Must extend Renmark's existing artifact-lifecycle / REQ-30 / REQ-31
  machinery — no parallel governance system.

**Non-goals:**
- Not a rewrite of `renmark/` source structure (that's the separate,
  already-released `renmark-architecture` transformation).
- Not, in this run, an implementation — Phase 1 is inventory-only.

**Areas open to change:** Everything under `.renmark/` is nominally open to
reclassification (active context / canonical evidence / archived history /
ephemeral output) — Phase 1's inventory is what will tell us which.

**Owner-directed scope for this run:** Owner explicitly asked to stop at a
gate after the read-only inventory (Phase 1) and *before* any lifecycle
contract (Phase 2) or implementation proposal (Phase 3) work proceeds. This
run therefore executes rethink's Transformation Intake + Stage 1 (internal
survey, scoped to `.renmark/`) only, then presents findings at a gate instead
of continuing through stages 2–9 unprompted.

**Decision log:**
- 2026-08-04: Intake captured directly from the Owner's `/renmark:rethink`
  invocation args (no additional blocking questions needed — outcome,
  protected behavior, constraints, and stop-point were all stated
  explicitly). Recorded verbatim scope above.
- 2026-08-04: Post-Phase-1 gate. Presented via `AskUserQuestion`: headline
  survey findings (version/ duplicate trees; three-way structural-map
  overlap; no retention policy on plans/reviews; startup exposure already
  narrow) plus four options for how to proceed. Owner chose "Continue to
  Phase 2 now" (full 13-type classification, not the narrowed two-overlap
  option) — reasoning given: "prevents a narrow cleanup from leaving other
  unbounded growth paths unresolved." Proceeding to Phase 2 (lifecycle
  contract) for all 13 artifact types found in survey.md. Still no artifact
  moved, deleted, or rewritten — Phase 2 is contract design only.
- 2026-08-04: Post-Phase-2 gate. Presented via `AskUserQuestion`: 13-type
  classification (6 canonical evidence / 1 active-context / 5 ephemeral /
  1 mixed), the three-way overlap resolution (canonical home =
  `.renmark/memory/project-map.md`), and the RETIRE-UNPACKED-VERSION-TREES
  recommendation. Owner chose "Continue to Phase 3 now." Proceeding to Phase
  3 (implementation proposal) — still a proposal only, no code written or
  artifact touched.
- 2026-08-04: Phase 3 complete — `.renmark/rethink/artifact-lifecycle/implementation-proposal.md`.
  Smallest-extension proposal: extends `renmark/hygiene.py` (registry +
  `budget`/`validate` subcommands + safe-deletion logic), reuses
  `renmark/schemas.py` unchanged, adds one gate to
  `renmark/finish_lanes.py::release_readiness`, adds an allowlist constant +
  test to `renmark/lifecycle/preamble.py`, and a thin `--artifact-hygiene`
  dispatch in `renmark/cli/_engine.py`. No parallel module, no new Owner
  gate. Migration first step: RETIRE-UNPACKED-VERSION-TREES (delete
  `version/v0.39.7/`, `v0.40.0/`; keep `v0.41.0/` + all zips; rollback via
  unzip). Estimated ~2,168 → ~410-420 files, ~10-22MB → ~1-3MB; injected
  context tokens unchanged (already narrow, now allowlist-enforced).
- 2026-08-04: Final gate. Owner chose "Route to /renmark:feature for
  implementation" — build the full proposal (registry, hygiene subcommands,
  finish-time gate, Hermes allowlist + test) on a branch, starting with the
  reversible version/-tree cleanup as the first change. Rethink's
  responsibility ends here: handing off `implementation-proposal.md` to
  `/renmark:feature`, which owns branching, the actual code changes, and its
  own verify/review/finish flow.

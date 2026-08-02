# Decisions (ADRs)

## ADR-047 — Approved R-0.4 contract as drafted

**Date:** 2026-08-01
**Status:** Accepted

**Context.** Contract: .renmark/plans/2026-08-01-r-0.4-minimal-independent-inspector-contract.md. R-0.2 follow-ups and roadmap Phase 3 items remain tracked debt, out of scope for R-0.4.

**Decision.** Owner approved R-0.4 (Minimal Independent Inspector) as drafted; PRD wording gap on mechanical Inspector independence tracked as debt, not a blocker. Execution proceeds WP-1..WP-6 under Continue-by-Default Policy.

---

## ADR-046 — Inspector/repair separation enforcement (R-006)

**Date:** 2026-08-01
**Status:** Accepted — design; implementation pending WP-5

**Context.** Constitution rule R-006 ("Inspectors cannot repair — findings and evidence only; a separate repair work order performs changes") requires that Inspector-role dispatches (codereview, verify, QA) are structurally prevented from mutating files. Today, the `reviewer.md` agent role declares `tools: Read, Grep, Glob, Bash, Write` — permitting Write access despite the contractual intent (subagent-profiles.md declares reviewer as "read-only"). This creates a gap: an Inspector COULD self-repair during its own dispatch, undermining the authority separation between Inspection and Repair.

**Decision.** Two-layer enforcement:

1. **Tool restriction on Inspector roles:** Remove `Write` and `Edit` from `plugin/agents/reviewer.md` and any future Inspector-class roles (e.g., QA Inspector, Architecture Inspector). Keep read and query tools (Read, Grep, Glob, Bash) to permit test execution and evidence gathering, but structurally prevent file mutation via the host platform's tool allowlist.

2. **Repair work-order pattern:** Any Inspector finding with severity ≥ Major or a FAIL verdict must produce a separate, logged repair work order (with work-order ID, source inspection reference, scope, and acceptance criteria) routed through the Governor to an appropriate Worker role—not an in-context fix by the Inspector itself.

**Consequences:**
- Pro: Separation is now structural (tool restriction) + policy (work-order pattern), not just advice.
- Pro: Audit trail records every inspection→repair flow with forward/backward pointers.
- Pro: Authority boundaries are enforced by the host platform, not dependent on prompt discipline.
- Con: Inspector findings are slightly delayed (one dispatch for finding, one for repair) vs. hypothetical in-line fix.
- Con: Requires skill updates (codereview, verify, etc.) to emit repair work orders instead of assuming fixes.

**Spec:** `.renmark/plans/r-0.2/inspector-repair-separation-design.md`.

---

## ADR-045 — Public Agency and Orchestrator paths; internal Conductor policy

**Date:** 2026-07-30
**Status:** Accepted — supersedes ADR-039

**Context.** ADR-039 recorded a completed harness-operating-modes feature but
does not express the product boundary needed for the managed delivery model.
The product needs two stable public paths: **Agency** for owner-facing
engagement, discovery, agreement, milestones, and signoff; and
**Orchestrator** for executing a defined, approved milestone through scoped
packages. Internal routing and guided behavior must not become a third public
workflow or invalidate existing operating-mode integrations.

**Decision.** Expose Agency and Orchestrator as the only public paths. Agency
governs owner decisions and hands an approved milestone to Orchestrator;
Orchestrator performs the bounded delivery work, verification, review, and
returns evidence for the applicable owner gate. **Conductor** is an internal
guided-policy layer only: it may select, sequence, and explain the appropriate
public path, but has no independent public contract, lifecycle, or approval
authority.

**Migration and rollback.** Existing operating-mode names, commands, persisted
state, and integrations remain compatibility projections during migration;
they must map deterministically to Agency or Orchestrator without changing
approval, review, merge, or release gates. Migration is additive and
reversible: retain readable legacy state and adapters until consumers have
migrated, avoid destructive renames or state rewrites, and permit rollback by
disabling the new routing/projection while preserving canonical lifecycle and
delivery evidence. A rollback must never reinterpret approval or silently
advance a milestone.

**Consequences.** Public documentation and entrypoints describe two paths;
Conductor remains implementation detail. Compatibility code may be removed
only after consumers and persisted artifacts are safely migrated and a
documented rollback is no longer required.

---

## ADR-044 — Finished feature context-hygiene-gates

**Date:** 2026-07-06
**Status:** Accepted

**Context.** Completed stages: plan-validated, reviewed

**Decision.** Branch feature/context-hygiene-gates reached stage released

---

## ADR-043 — Finished feature agent-team-migration

**Date:** 2026-07-06
**Status:** Accepted

**Context.** Completed stages: plan-drafted,plan-validated,created,verified,reviewed

**Decision.** Branch feature/agent-team-migration reached stage ready-to-release

---

## ADR-042 — Finished feature deterministic-first

**Date:** 2026-07-02
**Status:** Accepted

**Context.** REQ-21 deterministic-first routing; stages init→released

**Decision.** Branch worktree-deterministic-first merged to main, released v0.29.0

---

## ADR-041 — Finished feature agent-turn-runner

**Date:** 2026-07-02
**Status:** Accepted

**Context.** Completed stages: plan-drafted, plan-validated, created, verified

**Decision.** Branch feature/agent-turn-runner reached ready-to-release (v0.27.0 pending)

---

## ADR-040 — Finished feature dynamic-skill-loading

**Date:** 2026-07-01
**Status:** Accepted

**Context.** Completed stages: plan-drafted, plan-validated, created, verified, reviewed

**Decision.** Branch worktree-feature+dynamic-skill-loading reached stage ready-to-release

---

## ADR-039 — Finished feature harness-operating-modes

**Date:** 2026-07-01
**Status:** Accepted

**Context.** Completed stages: brainstorm-complete, plan-drafted, plan-validated, created, verified

**Decision.** Branch  reached stage ready-to-release

---

## ADR-038 — P7 pivot: generator → consistency lint (doc-slimming already DRY'd skills)

**Date:** 2026-06-29
**Status:** Accepted (owner-approved mid-build)

**Context.** P7 (ADR-037) planned a managed-block generator to DRY cross-cutting SKILL.md boilerplate. Implementation surfaced two facts: (1) the generated generic preamble would flatten skills' customized Step-0 logic; (2) more fundamentally, doc-slimming (ADR-027/028) had ALREADY single-sourced all shared boilerplate into `_shared/*` via pointer citations — `grep` for the canonical reasoning blockquote returns 0 hits across the 28 skills (it lives only in `_shared/reasoning-contract.md`); the 8 "reasoning-contract citers" carry distinct one-line pointers, not a duplicated block. There is no byte-identical duplication to generate.

**Decision.** Drop block generation + the 28-file migration entirely. Repurpose `renmark/skillgen.py` as a READ-ONLY consistency lint (`--check`): frontmatter discipline (trigger-only description + `disable-model-invocation` == registry) + doc-slimming guard (flag any skill re-inlining a `_shared` blockquote verbatim). Retain `renmark/skillmeta.py` (the registry, now feeding lifecycle) and the extracted init marker primitive. Wire `--check` into precommit.

**Consequence.** P7's real value is the registry + a guard that PREVENTS regressing doc-slimming — not generation. `skillgen` must stay read-only; re-introducing generation would reverse doc-slimming. Verified 1148 pass, --check clean on 28 skills. (Orchestrator note: I initially recommended managed-blocks without verifying duplication existed; the build correctly corrected the design.)

---

## ADR-037 — P7 template-generated SKILL.md (spec)

**Date:** 2026-06-29
**Status:** Accepted (spec); implementation pending plan

**Context.** 28 SKILL.md files share cross-cutting boilerplate (Step-0 preamble + reasoning-contract/next-steps/handoff-menu citations); a doctrine change means editing up to 26 files by hand — the path by which v0.20.0's frontmatter discipline drifts.

**Decision.** Three owner-confirmed choices:
1. **Managed blocks** — marker-delimited generator-owned regions inside hand-authored SKILL.md, reusing init.py's marker-merge (`<!-- BEGIN:gen:<block> -->`). Rejected full-file generation (huge migration) and lint-only (no auto-propagation).
2. **Scope** — generate Step-0 preamble + the 3 shared citations (pulled from `_shared`); frontmatter stays hand-authored, enforced by `--check` lint. Rejected generating frontmatter (touches v0.20.0).
3. **Central registry** `renmark/skillmeta.py` (extends `lifecycle.DOMAIN_BY_SKILL`) read by generator + preamble + next_steps. Rejected 28 per-skill manifests and inference-from-file.

**Consequence.** PRD-alignment = drift-but-benign (internal maintainability tooling, not product). Hard guard: generator NEVER writes frontmatter; lint validates only. Spec: `.renmark/specs/2026-06-29-p7-skill-templates.spec.md`. Targets ≥v0.23.0 with P8.

---

## ADR-036 — Finished feature p10-headless-contract

**Date:** 2026-06-26
**Status:** Accepted

**Context.** Completed stages: brainstorm-complete, plan-drafted, plan-validated, created, verified, reviewed

**Decision.** Branch  reached stage ready-to-release

---

## ADR-035 — resolve_gate uncertainty: None = assume interactive

**Date:** 2026-06-26
**Status:** Accepted (owner-confirmed)

**Context.** Codex re-review flagged that `renmark.headless.resolve_gate` returns
`{"mode":"interactive"}` for a dangerous gate when `is_headless` is False and
`tool_available is None`, arguing the owner's "uncertainty → halt dangerous gates"
rule should make it halt.

**Decision.** Current behavior is correct and intentional. `tool_available=None`
means "assume a human is present" → return interactive so the skill renders the
`AskUserQuestion` menu and the human approves the merge/release **live**. Halting
there would break normal interactive dangerous-gate approval. The fail-safe halt
fires only when positively headless: `RENMARK_HEADLESS=1`, `config.headless`, or
an explicit `tool_available=False` (AskUserQuestion provably absent → spawned
subagent). "Uncertainty" in the owner rule means provably-headless-but-undetected,
which true-headless callers signal via those explicit channels — not the
default-interactive path.

**Consequence.** The codex re-review finding (headless.py:73) is declined
by-design. The two genuinely-fixed re-review items (halt mkdir guard, descriptive
success prose) were applied (commit 80598eb).

---

## ADR-034 — P10 headless / spawned-session contract (spec)

**Date:** 2026-06-26
**Status:** Accepted (spec); implementation pending plan

**Context.** Renmark runs in background jobs / under outer orchestrators but every pipeline skill ends in an interactive `AskUserQuestion` menu and pauses at Pause-Policy gates — which stalls a headless run. Brainstormed via interactive Q&A; contract finalized by owner.

**Decision.** Three owner-specified rules pin the contract:
1. **Gates** — safe gates auto-pick the `(Recommended)` option in headless mode; dangerous gates (`merge`, `release`, destructive ops, PRD approval, cost/token over budget) halt, write a decision artifact, set `human_review_required=true`, and return `needs_input` (never `failed`).
2. **Detection** — precedence `RENMARK_HEADLESS=1` (force on) > `=0` (force off) > `.renmark/config.json` `headless` > tool-availability fallback adapter (AskUserQuestion absent → headless); never inferred from `CLAUDE_JOB_DIR`/`CLAUDECODE`. **Uncertain → dangerous gates fail safe (halt + emit).**
3. **Return** — structured JSON (`status`/`mode`/`gate`/`decision`/`human_review_required`/`artifacts`/`reason`) + one classifier-friendly prose line (`result:`/`needs input:`/`failed:`).

**Alternatives rejected.** Auto-pick everything (unsupervised shipping); auto-detect from `CLAUDE_JOB_DIR` (false positive — this very session is a bg job with a live human); gstack 3-word verbatim vocabulary (second status vocab vs the repo's classifier lines); prose-only (owner chose structured JSON for programmatic outer drivers).

**Consequences.** Tool-availability is a fallback adapter, not trusted truth — the stable renmark contract (env+config) is primary. Inherited via the 3 shared menu files, so the 28 SKILL.md files and v0.20.0 trigger-only frontmatter are untouched. Spec: `.renmark/specs/2026-06-26-p10-headless-contract.spec.md`.

---

## ADR-033 — Finished feature graduated-preamble-tier

**Date:** 2026-06-25
**Status:** Accepted

**Context.** Completed stages: plan-drafted, plan-validated, created, verified, reviewed

**Decision.** Branch worktree-feature+graduated-preamble-tier reached stage ready-to-release

---

## ADR-032 — Finished feature finish-branch-disposition

**Date:** 2026-06-17
**Status:** Accepted

**Context.** Completed stages: plan-drafted, plan-validated, created, verified, reviewed

**Decision.** Branch feature/finish-branch-disposition reached stage ready-to-release

---

## ADR-031 — Finished feature req14-scan-proposer

**Date:** 2026-06-16
**Status:** Accepted

**Context.** Completed stages: brainstorm-complete, plan-drafted, plan-validated, created, verified, reviewed

**Decision.** Branch  reached stage ready-to-release

---

## ADR-030 — Finished feature roadmap-staged-planner

**Date:** 2026-06-14
**Status:** Accepted

**Context.** Completed stages: brainstorm-complete, plan-drafted, plan-validated, created, verified

**Decision.** Branch feature/roadmap-staged-planner reached stage ready-to-release

---

## ADR-029 — Finished feature playwright-browser-control

**Date:** 2026-06-13
**Status:** Accepted

**Context.** Completed stages: brainstorm-complete, plan-drafted, plan-validated, created, verified, reviewed

**Decision.** Branch feature/playwright-browser-control reached stage ready-to-release

---

## ADR-028 — Finished feature doc-slimming-fixes

**Date:** 2026-06-12
**Status:** Accepted

**Context.** Completed stages: plan-drafted, plan-validated, created, verified

**Decision.** Branch feature/doc-slimming-fixes reached ready-to-release

---

## ADR-027 — Finished feature claude-doc-slimming

**Date:** 2026-06-12
**Status:** Accepted

**Context.** Completed stages: plan-validated, created, verified

**Decision.** Branch feature/claude-doc-slimming reached ready-to-release

---

## ADR-026 — Finished feature cowork-alignment

**Date:** 2026-06-12
**Status:** Accepted

**Context.** Completed stages: plan-drafted, plan-validated, created, verified

**Decision.** Branch feature/cowork-alignment reached stage ready-to-release

---

## ADR-025 — Finished feature agent-routing-policy

**Date:** 2026-06-12
**Status:** Accepted

**Context.** Completed stages: plan-drafted, plan-validated, created, verified

**Decision.** Branch feature/agent-routing-policy reached stage ready-to-release

---

## ADR-024 — Finished feature fable-routing

**Date:** 2026-06-12
**Status:** Accepted

**Context.** Completed stages: plan-drafted, plan-validated, created, verified

**Decision.** Branch feature/fable-routing reached stage ready-to-release

---

## ADR-023 — Finished feature fable-integration

**Date:** 2026-06-11
**Status:** Accepted

**Context.** Completed stages: plan-drafted, plan-validated, created, verified, reviewed

**Decision.** Branch feature/fable-integration reached stage ready-to-release

---

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

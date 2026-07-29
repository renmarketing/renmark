---
artifact_type: renmark_master_plan
schema_version: 1
created_at: 2026-07-29T00:00:00-04:00
source_sha: 527bdf5
related_plan: null
generator: codex
stale_after: null
dependency_refs:
  - PRD.md#REQ-22
  - PRD.md#REQ-25
  - .renmark/audits/2026-07-29-renmark-architecture-audit-and-proposal.md
  - .renmark/audits/2026-07-29-mode-simplification.md
  - .renmark/audits/2026-07-29-routing-granularity-review-loop.md
  - .renmark/audits/2026-07-29-workflow-milestone-architecture.md
completion_state: complete
confidence: high
validation_status: validated
retry_count: 0
parser_success: not_applicable_master_plan
schema_compliance: validated
---

# Two-mode milestone delivery master program

## Contract summary

Renmark exposes exactly two owner-selectable paths:

- Agency path: starts from an idea or product-level outcome. Agency owns discovery, PRD agreement, stack recommendation, milestone roadmap approval, demos, feedback, owner signoff, and release. Agency delegates every approved milestone to Orchestrator and does not duplicate execution state, cost, verification, loop, or review code.
- Orchestrator path: starts from a defined goal, feature, bug, spec, or approved milestone. Orchestrator owns scope validation, work-package planning, model routing, dispatch, verification, independent review, bounded repair, and finish.

Conductor is not a public or persisted mode. Its useful behavior becomes an internal `execution_policy: guided|direct|async` selected by Orchestrator based on task size, risk, and interaction needs.

Public command taxonomy after the redesign:

- Public front doors: `/renmark:init`, `/renmark:start`, `/renmark:feature`, `/renmark:debug`, `/renmark:roadmap`, `/renmark:finish`, `/renmark:resume`, `/renmark:status` or `/renmark:usage` where available.
- Advanced aliases: `/renmark:prd`, `/renmark:plan`, `/renmark:check-plan`, `/renmark:orchestrate`, `/renmark:verify`, `/renmark:codereview`, `/renmark:loop`, `/renmark:approve`, `/renmark:blueprint`, `/renmark:backlog`, `/renmark:scan`, `/renmark:analytics`, `/renmark:hygiene`, `/renmark:doctor`, `/renmark:eval`.
- Internal phases behind public paths: PRD alignment, contract refresh, milestone compile, work-package planning, dispatch waves, verify, independent review, repair loop, demo, signoff, finish-lane selection.
- Deprecated public concept: Conductor Mode as a durable owner choice. Backward-compatible reads may accept legacy `conductor` and map it to Orchestrator with `execution_policy: guided`.

Preserved decisions:

- ADR-005 remains in force: `/renmark:prd` is the only PRD writer.
- ADR-038 remains in force: do not reintroduce full skill-body generation; contract propagation uses concise managed blocks and pointer citations.
- ADR-039 must be explicitly superseded by a future ADR after runtime compatibility exists; this plan does not silently erase it.

## Future work-package format

Current Renmark execution still accepts one-target task packets. This master program dogfoods the future format each milestone should compile to after Milestone 3:

```yaml
work_package:
  id: WP-Mx-N
  milestone_id: Mx
  goal: owner-visible behavior or bounded implementation outcome
  allowed_surface:
    files: []
    modules: []
  forbidden_scope: []
  acceptance_evidence: []
  verifier: []
  rollback: []
  planner_route: deterministic|standard|deep
  executor_route: deterministic|mini|codex|standard
  reviewer_route: deterministic|reviewer|codex
  loop_budget:
    build_iterations: 2
    review_cycles: 3
    max_tokens: 0
    max_cost_usd: 0.00
  stop_conditions: []
```

The Milestone 1 bootstrap plan intentionally stays with current one-file task packets until the work-package compiler lands.

## Milestone M1 — Canonical Delivery State

- Stable ID: `M1-canonical-delivery-state`
- Goal: create one authoritative per-run aggregate that links or replaces Agency, Program, Lifecycle, Pipeline, mode, milestone, work-package, approval, review, loop, verifier, provenance, and contract freshness state without deleting legacy state files.
- Expected owner-visible outcome: `/renmark:resume`, `/renmark:start`, and `/renmark:feature` can identify the active delivery run from one canonical read path instead of guessing from whichever legacy file is populated.
- Product acceptance evidence:
  - `tests/test_delivery_state.py`, `tests/test_schemas.py`, `tests/test_agency.py`, `tests/test_program.py`, `tests/test_lifecycle.py`, and `tests/test_state_pipeline.py` cover schema versioning, migration adapters, drift repair, stable IDs, provenance events, and backward compatibility.
  - Corrupt or contradictory current state reports bounded repair evidence instead of silently masking active work.
  - Legacy `agency.json`, `program.json`, `lifecycle.json`, `pipeline.json`, and `mode.json` readers remain compatible.
- Dependencies: accepted REQ-22 and REQ-25; current state modules; no full skill-body generation.
- Allowed component surface: `renmark/delivery_state.py`, `renmark/schemas.py`, `renmark/agency.py`, `renmark/program.py`, `renmark/lifecycle.py`, `renmark/state/pipeline.py`, focused tests, and one CLI/state seam if needed.
- Forbidden scope and invariants:
  - Do not remove legacy state files.
  - Do not change PRD writer policy.
  - Do not alter dispatch execution semantics yet.
  - Do not change public command docs yet except tests that prove state behavior.
- Work packages:
  - `WP-M1-1`: define delivery-run schema, stable ID rules, milestone/work-package status vocabulary, provenance events, bloat caps, atomic read/write, and bounded summary accessors.
  - `WP-M1-2`: add migration adapters from Agency, Program, Lifecycle, Pipeline, and Mode into the aggregate.
  - `WP-M1-3`: add drift repair for active-but-empty Agency, contradictory lifecycle/program stages, stale mode values, and orphaned pipeline plans.
  - `WP-M1-4`: add schema and compatibility tests.
- Routing:
  - Planner: standard.
  - Executor: Codex for code/test packets; haiku only for tiny docs if needed.
  - Reviewer: reviewer or Codex read-only once the milestone passes tests.
- Deterministic gates:
  - Parse M1 bootstrap plan.
  - `python -m renmark.plan_lint .renmark/plans/2026-07-29-two-mode-milestone-delivery-m1.plan.md`
  - `python -m renmark.subagent_gate .renmark/plans/2026-07-29-two-mode-milestone-delivery-m1.plan.md`
  - Focused pytest targets listed in the bootstrap plan.
- Build-loop placement and budget: Orchestrator-local `build → verify → repair → verify`; max 2 implementation repair iterations per packet; before a third equivalent failure, recurrence guard escalates.
- Review-loop placement and budget: after all M1 tests pass, run independent review; Critical/Major findings become scoped M1 fix packets; max 2 review-fix-review cycles or $0.40 of review/repair spend beyond the implementation preview, whichever hits first.
- Demo and signoff: show `delivery_state` status output and a before/after drift-repair example; owner signs off before M2.
- Compatibility strategy: additive aggregate first; legacy files remain readable and writable; canonical aggregate consumes legacy state without forcing a migration on first read.
- Rollback: disable aggregate readers and fall back to existing Agency/Program/Lifecycle/Pipeline readers; remove only the new module/test seams from the milestone branch if required.
- Estimated tokens/cost band: current executable M1 preview is 28,900 tokens and $0.867 (medium) at the canonical Codex rate; no Opus/Fable expected.
- Stop conditions: schema ambiguity that changes REQ-22, state corruption without deterministic repair path, test baseline regression outside allowed surface, implementation re-estimate above $1.00 or 15% above an approved preview, exhausted review/repair budget, or owner approval gate.

## Milestone M2 — Entry Routing and Two-Mode Public Contract

- Stable ID: `M2-entry-routing-two-mode`
- Goal: make `init`, `start`, `feature`, `debug`, `resume`, and mode CLI route through the canonical delivery run with Agency and Orchestrator as the only public modes.
- Expected owner-visible outcome: users see one clear choice when needed: Agency for product delivery, Orchestrator for defined execution. Explicit owner choice persists per run. Legacy Conductor state is read as internal guided policy and cannot be selected as a new public mode.
- Product acceptance evidence:
  - Golden tests show vague new builds route to Agency recommendation, defined feature/fix routes to Orchestrator, explicit choice wins, and resume never asks again.
  - Legacy `renmark-execute --get-mode` remains compatible but reports deprecation guidance for `conductor`.
  - `debug` uses Orchestrator with `execution_policy: guided`, not a third mode.
- Dependencies: M1 canonical state.
- Allowed component surface: `renmark/mode.py`, `renmark/lifecycle.py`, `renmark/cli/_engine.py`, `plugin/skills/start/SKILL.md`, `plugin/skills/feature/SKILL.md`, `plugin/skills/debug/SKILL.md`, `plugin/skills/resume/SKILL.md`, relevant tests.
- Forbidden scope and invariants:
  - Do not delete compatibility readers.
  - Do not add a per-entry mode gate that breaks auto-routing.
  - Do not ask Codex users for unsupported `/clear` or `/compact`.
- Work packages:
  - `WP-M2-1`: introduce delivery-mode API with `agency|orchestrator` and internal execution-policy mapping.
  - `WP-M2-2`: update entry skill preambles and routing text.
  - `WP-M2-3`: update CLI mode commands with compatibility warnings.
  - `WP-M2-4`: add cross-host and behavior tests.
- Routing:
  - Planner: standard.
  - Executor: Codex for code/tests; docs-editor/haiku for concise skill docs.
  - Reviewer: reviewer after tests.
- Deterministic gates: mode unit tests, lifecycle behavior tests, trigger matrix tests, `python -m renmark.audit --inventory-only` if available, plan lint for implementation plan.
- Build-loop placement and budget: max 2 repair iterations per failing focused test packet.
- Review-loop placement and budget: one milestone review; max 3 fix/re-review cycles.
- Demo and signoff: run sample routing matrix for Agency, direct Orchestrator, debug-guided, and legacy conductor read; owner signs off on wording.
- Compatibility strategy: legacy mode file values remain readable; new writes use delivery-run mode; old conductor maps to Orchestrator guided.
- Rollback: revert routing layer to legacy mode reads while keeping M1 state inert.
- Estimated tokens/cost band: 30k-50k tokens; dollar cost is recomputed from routed work packages through `renmark.cost` before M2 dispatch; no Opus/Fable expected.
- Stop conditions: any behavior requiring three public modes, selector parity break, context-budget rule conflict, or owner wording rejection.

## Milestone M3 — Milestone Planner and Work-Package Compiler

- Stable ID: `M3-milestone-planner-work-packages`
- Goal: replace file-first planning as the product altitude with milestone-first planning that compiles into bounded work packages and then into current or upgraded executor packets.
- Expected owner-visible outcome: Agency produces a milestone roadmap with goals, expected outcomes, acceptance evidence, dependencies, risks, cost lane, demo point, and signoff policy; Orchestrator can run a defined milestone directly.
- Product acceptance evidence:
  - Plans store milestone IDs and work-package IDs that remain stable across resume.
  - Work packages support multi-file allowed surfaces while preserving bounded context and rollback.
  - Current single-file task format remains available as a compiler backend until execution upgrades are complete.
- Dependencies: M1, M2.
- Allowed component surface: planner, parser, plan_lint, subagent_gate, cost, dispatch packet builders, roadmap/program renderers, tests.
- Forbidden scope and invariants:
  - Do not let work packages request full diffs, generated bodies, or transcript content.
  - Do not bypass deterministic-first routing.
  - Do not let milestone planning write PRD; route PRD changes to `/renmark:prd`.
- Work packages:
  - `WP-M3-1`: define typed milestone and work-package schemas.
  - `WP-M3-2`: add compiler from milestone package to current task packets.
  - `WP-M3-3`: update plan lint and subagent gate for goal-bounded packages.
  - `WP-M3-4`: add cost preview by milestone/work-package.
- Routing:
  - Planner: standard; deep only for unresolved architecture forks.
  - Executor: Codex/standard for code; deterministic for schema checks.
  - Reviewer: reviewer with parser/lint focus.
- Deterministic gates: schema validation, parser round-trip tests, plan lint fixtures, subagent gate fixtures, cost preview tests.
- Build-loop placement and budget: compiler failures get max 2 repair iterations per fixture class.
- Review-loop placement and budget: max 3 review-fix-review cycles, prioritizing parser and context hygiene findings.
- Demo and signoff: show one Agency roadmap compiled into work packages and one direct Orchestrator feature compiled from a defined goal.
- Compatibility strategy: keep current `### Task N` parser as backend and add package parser beside it.
- Rollback: disable package parser and keep generated current-format plans.
- Estimated tokens/cost band: 45k-70k tokens; dollar cost is recomputed from routed work packages through `renmark.cost` before M3 dispatch; possible deep review only if schema forks remain unresolved.
- Stop conditions: work-package format breaks existing plan execution, cost preview cannot price packages, or package scope weakens REQ-5/G11.

## Milestone M4 — Milestone Execution, Verification, Review, and Loops

- Stable ID: `M4-milestone-execution-review-loops`
- Goal: make Orchestrator execute each milestone through dispatch waves, fresh verification, independent review, scoped fix packages, re-verification, and re-review before demo/signoff.
- Expected owner-visible outcome: every milestone reports verified/reviewed status with bounded evidence and either clean signoff readiness or explicit blocker/fix-loop status.
- Product acceptance evidence:
  - Build loop: `build → verify → repair → verify` is milestone-local, budgeted, and recurrence-guarded.
  - Review loop: `review → scoped fix → verify → re-review` is mandatory before Agency milestone signoff and optional/proportional for direct Orchestrator work.
  - Loop state nests under active milestone/work-package and cannot change product scope or advance a milestone.
- Dependencies: M1, M2, M3.
- Allowed component surface: `renmark/loop.py`, dispatch engine, verifier, codereview integration, program_driver, recurrence integration, pipeline state, tests.
- Forbidden scope and invariants:
  - Do not auto-fix security overrides, merges, releases, or PRD changes.
  - Do not store raw review bodies or large verifier output in delivery state.
  - Do not retry a third equivalent attempt.
- Work packages:
  - `WP-M4-1`: attach loop state to milestone/work-package IDs.
  - `WP-M4-2`: add review finding export to scoped fix-package generation.
  - `WP-M4-3`: wire recurrence guard into milestone loop decisions.
  - `WP-M4-4`: update finish/readiness to require clean review for milestone signoff.
- Routing:
  - Planner: standard.
  - Executor: Codex for fix packets; deterministic for verifiers.
  - Reviewer: independent reviewer/Codex read-only; security-sensitive findings may escalate only with declared reason.
- Deterministic gates: loop unit tests, recurrence tests, codereview finding fixtures, verifier freshness tests, pipeline resume tests.
- Build-loop placement and budget: default 2 repair iterations per work package; budget configurable per milestone.
- Review-loop placement and budget: default 3 review-fix-review cycles per milestone or configured dollar cap; Critical/Major block signoff, Minor/Nit may defer by policy.
- Demo and signoff: run a synthetic milestone with one verifier failure and one review finding through bounded repair to clean signoff readiness.
- Compatibility strategy: standalone `/renmark:loop` and `/renmark:codereview` continue to work; mandatory loops activate only inside milestone execution.
- Rollback: disable milestone-loop adapter and fall back to existing manual codereview next steps.
- Estimated tokens/cost band: 60k-90k tokens; dollar cost is recomputed from routed work packages through `renmark.cost` before M4 dispatch; deep reviewer only for high-risk findings.
- Stop conditions: loop can mutate scope, recurrence evidence is lost, review artifacts exceed bounded output, or signoff can be reached without clean verification/review.

## Milestone M5 — Project Contract Propagation

- Stable ID: `M5-project-contract-propagation`
- Goal: implement REQ-25 by deriving concise managed `CLAUDE.md` and `AGENTS.md` contract blocks from one canonical source and refreshing them through `init`, `start`, and `feature` without overwriting project-specific instructions.
- Expected owner-visible outcome: adopted and newly built projects receive the same current two-mode contract regardless of entry point, and custom instructions outside managed markers remain byte-for-byte unchanged.
- Product acceptance evidence:
  - `init` on new/existing repo, `start` on stale repo, and `feature` on stale repo converge on the same managed contract.
  - Running refresh twice produces no second diff.
  - Root docs, templates, installed blocks, and host variants pass deterministic parity checks.
  - Blocks cite skills/shared contracts by pointer and do not inline full skill bodies.
- Dependencies: M1, M2; ADR-038 preserved.
- Allowed component surface: `renmark/init.py`, templates for `CLAUDE.md` and `AGENTS.md`, contract source fragment, start/feature freshness check seam, deterministic parity tests.
- Forbidden scope and invariants:
  - Do not add a second contract writer.
  - Do not overwrite unmarked project instructions.
  - Do not generate full skill bodies or duplicate large shared fragments.
  - Do not write PRD from init/start/feature.
- Work packages:
  - `WP-M5-1`: introduce canonical concise contract source.
  - `WP-M5-2`: route `start` and `feature` through the init merge primitive.
  - `WP-M5-3`: add idempotency, preservation, and parity checks.
  - `WP-M5-4`: update root `CLAUDE.md`/`AGENTS.md` and templates in one commit.
- Routing:
  - Planner: standard.
  - Executor: Codex/docs-editor for templates and tests.
  - Reviewer: reviewer for preservation and ADR-038 compliance.
- Deterministic gates: idempotency fixtures, marker preservation tests, semantic parity test, audit/lint, focused init/start/feature tests.
- Build-loop placement and budget: max 2 repair iterations per failing contract fixture.
- Review-loop placement and budget: max 3 review-fix-review cycles; any accidental overwrite is blocking.
- Demo and signoff: show before/after for a project with custom CLAUDE/AGENTS content and prove no second diff.
- Compatibility strategy: marker names remain stable; old managed blocks refresh in place; unmarked instructions are never claimed.
- Rollback: disable freshness check in start/feature and leave init merge primitive intact.
- Estimated tokens/cost band: 35k-55k tokens; dollar cost is recomputed from routed work packages through `renmark.cost` before M5 dispatch; no Opus/Fable expected.
- Stop conditions: parity drift, non-idempotent refresh, unmarked content overwrite, or full skill-body duplication.

## Milestone M6 — Migration, Golden Trajectories, ADR, and Release

- Stable ID: `M6-migration-golden-release`
- Goal: complete cross-host migration proof, golden trajectories, docs cleanup, ADR supersession, analytics alignment, and release readiness.
- Expected owner-visible outcome: Renmark behaves as a cohesive two-mode vibe-coding solution on Claude Code and Codex with resumable milestone delivery and verified contract propagation.
- Product acceptance evidence:
  - Agency golden trajectory: idea → PRD approval → roadmap approval → Orchestrator milestone → verify → review → demo/signoff → release.
  - Orchestrator golden trajectory: defined goal → work packages → dispatch → verify → review → fix loop if needed → finish.
  - `init`, `start`, and `feature` contract propagation success criteria pass.
  - Analytics and status report milestone/work-package IDs, not reusable `task 1` labels.
  - ADR task explicitly supersedes ADR-039 and records Conductor demotion after runtime support exists.
- Dependencies: M1-M5.
- Allowed component surface: tests/behavioral, integration tests, analytics/status, docs/help, CHANGELOG, ADR/memory, release metadata.
- Forbidden scope and invariants:
  - Do not remove legacy compatibility before migration tests pass.
  - Do not merge or release without `/renmark:approve`.
  - Do not weaken Codex host-managed context handling.
- Work packages:
  - `WP-M6-1`: add Agency and Orchestrator golden trajectories across hosts.
  - `WP-M6-2`: update analytics/status/reporting by milestone/work-package ID.
  - `WP-M6-3`: write ADR superseding ADR-039 and update user-facing docs/help.
  - `WP-M6-4`: run full verification, independent review, and finish lane.
- Routing:
  - Planner: standard.
  - Executor: deterministic/Codex for tests/docs.
  - Reviewer: reviewer; release-manager for version/changelog/tag readiness.
- Deterministic gates: full pytest, behavior tier, audit/inventory, release drift checks, package validation if release lane approved.
- Build-loop placement and budget: max 2 repair iterations per failing golden trajectory class.
- Review-loop placement and budget: max 3 review-fix-review cycles; release findings block until resolved or explicitly deferred.
- Demo and signoff: show both mode trajectories and request release approval.
- Compatibility strategy: legacy state readers remain at least one release; deprecation warning explains migration path.
- Rollback: keep feature branch unreleased; revert docs/help/analytics while leaving stable runtime pieces if independently safe.
- Estimated tokens/cost band: 50k-80k tokens; dollar cost is recomputed from routed work packages through `renmark.cost` before M6 dispatch; release actions require owner gate.
- Stop conditions: cross-host divergence, golden trajectory failure, ADR conflict unresolved, release gate absent, or package verification failure.

## Cross-milestone assumptions and edge cases

Assumptions:

- The accepted PRD at source SHA `527bdf5` is authoritative for REQ-22 and REQ-25.
- "Two modes" means two owner-selectable delivery modes, not removal of human approval gates or local guided execution.
- Existing one-file task packets are a bootstrap limitation, not a product requirement.
- M1 may add compatibility adapters without changing public routing yet.

Potential edge cases:

- Blocking: active Agency state with empty milestone fields can conflict with stale lifecycle/program state; M1 must repair or surface it deterministically.
- Blocking: legacy `conductor` mode files must not break resume; M2 must map them without preserving Conductor as public mode.
- Blocking: review-fix loops can increase cost; M4 must budget and stop on recurrence or no fresh evidence.
- Deferrable: analytics label cleanup can wait until M6 because it depends on stable milestone/work-package IDs.
- Deferrable: ADR-039 supersession should wait until runtime support exists, then be recorded explicitly in M6.

Recommended robust path:

1. Land M1 canonical state before changing routing or docs.
2. Change public routing in M2 only after the aggregate can preserve legacy workflows.
3. Add future work-package planning in M3, then enforce milestone-local loops in M4.
4. Propagate the concise project contract in M5 after the runtime semantics exist.
5. Prove both host trajectories and supersede ADR-039 in M6.

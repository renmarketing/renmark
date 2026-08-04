---
artifact_type: rethink-prd-acceptance-map
schema_version: 1
created_at: 2026-08-03T00:00:00Z
source_sha: c6741856f7603aac3e01f324fbaa4b7e6478155e
related_plan: null
generator: renmark:researcher
stale_after: null
dependency_refs: ["PRD.md", ".renmark/rethink/renmark-architecture/survey.md", ".renmark/rethink/renmark-architecture/baseline.md"]
---

# PRD acceptance contract — Stage 3 of `/renmark:rethink` (renmark-architecture)

Scope: this rethink targets `renmark/` (Python runtime) architecture only —
"modernize without changing pipeline behavior/UX" per the Owner's
Transformation Intake. Compliance below is judged against that scope: PRD
requirements about skill/UX behavior are mapped as **protected constraints**
on the architecture work, not targets for redesign. IDs `AC-n` are additive
annotations assigned here for acceptance bullets that lack a stable ID in
`PRD.md` itself; `PRD.md` is not edited.

## Compliance table — REQ-1 .. REQ-31

| REQ | Current impl (evidence) | Compliance | Target behavior | Verification method |
|---|---|---|---|---|
| REQ-1 (plain-English entry) | Skill pipeline exists per `plugin/commands/*.md`/`plugin/skills/*/SKILL.md` (baseline §Pipelines table) | met | unchanged — protect | fixture/UX test, out of architecture scope |
| REQ-2 (cost-routed executor set incl. Fable) | Routing logic present; not exercised live this session (no Bash) | unverified | unchanged — protect | live `pytest -q` + fable-routing tests before/after refactor |
| REQ-3 (resumable workflows) | lifecycle.json/pipeline.json separation verified in code (baseline §Lifecycle vs runtime) | met | unchanged — protect | `test_lifecycle.py`, resume fixtures |
| REQ-4 (single human-owned PRD.md) | No automated PRD writer bypassing UPDATE gate found | met | unchanged — protect | code review of `renmark/prd*`/UPDATE-gate call sites |
| REQ-5 (orchestrator context hygiene) | Structurally honored (lifecycle/pipeline split, ≤5-line contract cited); **but** `context_budget_hint` (`renmark/state/skills.py`) confirmed dead — zero production callers as of 2026-08-02 audit (survey §3, baseline) | partial | unchanged — protect; wire or explicitly retire `context_budget_hint` per REQ-30(g) ("no retained context, no dead scaffolding masquerading as enforcement") | `test_behavior.py`, grep for call sites post-refactor |
| REQ-6 (`.renmark/` artifact homes) | Confirmed via grep, no writer outside convention (baseline); minor disk-hygiene stray `.md` scratch files in `.renmark/state/` (gitignored, not a source-control issue) (survey §2) | met | unchanged — protect | grep audit of writer call sites |
| REQ-7 (validated plans / goal-backward verify) | Not exercised live this session | unverified | unchanged — protect | live `pytest -q`, `verify` fixture run |
| REQ-8 (`/renmark:init` non-destructive adoption) | Out of architecture-only scope (skill prose), code (`renmark/init.py`) present | met | unchanged — protect | `test_init*.py` |
| REQ-9 (Loop budget + iteration cap) | Not directly surveyed this pass; no contrary evidence | unverified | unchanged — protect | `test_loop*.py` |
| REQ-10 (loop state persistence) | `.renmark/loops/<id>/` referenced in scope boundaries; not directly inspected this pass | unverified | unchanged — protect | loop resume fixture |
| REQ-11 (loop goal-backward decisions) | Not directly surveyed | unverified | unchanged — protect | loop fixture |
| REQ-12 (human approval before PRD/merge/release/budget-escalation) | `/renmark:approve` sole-grant surface asserted by REQ-18; not independently re-verified this pass | unverified | unchanged — protect | `test_lifecycle.py` approval-gate tests |
| REQ-13 (`/renmark:backlog` approval buffer) | Not directly surveyed | unverified | unchanged — protect | backlog fixture |
| REQ-14 (scheduled QA read-only proposer) | Not directly surveyed; design-only per PRD (not MVP) | unverified | unchanged — protect | N/A (design-only) |
| REQ-15 (local-only reporting/analytics) | Infra exists (`.renmark/reports/`, `.renmark/analytics/`) but baseline's own orchestration-baseline audit found **`tokens_in`/`tokens_out`/`duration_s` ~0 across `usage.jsonl` and `task-runs.jsonl`** — telemetry effectively unmeasured in production (baseline §Measurable performance/cost baseline) | partial | unchanged — protect; this is a pre-existing production gap, not something this architecture-only rethink should silently "fix" as a side effect (would touch instrumentation call sites = orchestration-adjacent, gated by REQ-30) | live usage.jsonl inspection post any instrumentation touch |
| REQ-16 (usage-limit pause/resume) | Not directly surveyed | unverified | unchanged — protect | pause/resume fixture |
| REQ-17 (`/renmark:audit`/`inventory` read-only) | `.renmark/audits/*` artifacts present in repo (git status) confirming live use | met | unchanged — protect | advisory-only code review |
| REQ-18 (`/renmark:approve` sole grant surface) | Not independently re-verified this pass | unverified | unchanged — protect | grep for `human_review_completed=True` call sites |
| REQ-19 (optional Playwright layer) | `playwright` is an optional dep group per `pyproject.toml` (survey §5); fallback to Chrome DevTools MCP channel asserted, not re-verified live | met (structural) | unchanged — protect | `renmark/browser.py` fixture (env-gated) |
| REQ-20 (four-way context taxonomy) | `renmark/context.py` (`load_skill_body`/`load_fragment`), `assert_metadata_only` cited in CLAUDE.md; not independently re-read this pass | unverified | unchanged — protect | `test_context*.py` |
| REQ-21 (deterministic-first execution) | `renmark/worktree.py`, `renmark/lint.py`, `subagent_gate.py` cited; survey flags **plausible** (not confirmed) logic overlap between `_engine.py`/`dispatch.py`/`program_driver.py` — "three modules each with their own notion of what happens next" (survey §6) worth checking during modularity assessment, not confirmed duplicated | met, with a flagged duplication-risk to verify in Stage 5 | unchanged — protect | AST-level duplication scan (deferred to modularity-assessment stage) |
| REQ-22 (two-mode Agency/Orchestrator delivery) | `renmark/agency.py`, `renmark/delivery_state.py`, `renmark/program.py` present and cross-referenced (survey §1); Conductor demoted per revision notes | met | unchanged — protect | `test_agency_behavior.py`, `test_delivery_state*.py` |
| REQ-23 (Claude Code / Codex host parity) | `renmark/hosts.py` `HostCapabilities` table confirmed in code (baseline §Host-capability contracts) | met | unchanged — protect | host-parity fixtures |
| REQ-24 (recurring-issue prevention) | `renmark/recurrence.py`, `renmark/scan.py` referenced (survey §1 import graph); not independently exercised | unverified | unchanged — protect | recurrence fixture |
| REQ-25 (project contract propagation) | Managed contract blocks present in this repo's own `CLAUDE.md`/`AGENTS.md` (this session's system context); refresh primitive not independently re-verified | met (observed) | unchanged — protect | idempotency/parity check (`renmark/init.py`) |
| REQ-26 (invisible-by-default governance) | Not directly surveyed; no contrary evidence of new required user-facing governance step | met | unchanged — protect | `/renmark:feature` fixture, no new gate |
| REQ-27 (work classification / release-oriented delivery) | Applies to renmark's own dev per PRD text; `renmark/fast_path.py` present (survey §5 import list) | met | unchanged — protect | fast-path classification tests |
| REQ-28 (`/renmark:rethink` brownfield entry point) | This very Stage 3 run is direct evidence of REQ-28's nine-stage contract executing (survey/baseline artifacts exist under `.renmark/rethink/renmark-architecture/`) | met | unchanged — protect | artifact-set completeness check at Execution Gate |
| REQ-29 (`/renmark:start` evidence-based greenfield entry point) | Out of scope for this architecture-only rethink target (applies to `start`, not to renmark's own runtime refactor) | met (N/A to this run) | unchanged — protect | N/A |
| REQ-30 (orchestration efficiency protected capability) | **Structural guarantees** cited/still true per `.renmark/memory/orchestration-baseline.md`; **numeric baseline (tokens/wall-clock/dispatch-count for the four representative scenarios) is explicitly "not yet measured"** per that file's own open item (baseline §Measurable performance/cost baseline) | **partial / untestable-as-written for a quantified before/after comparison** | unchanged — protect; the named baseline v0.39.7/d9cccc5 remains the reference point until numbers exist | run the 4 representative scenarios (Start/Feature-Fix/Orchestrate/Rethink) and capture token/latency/dispatch numbers **before** Stage 5 touches `_engine.py`/`dispatch.py`/`lifecycle.py` |
| REQ-31 (native task tracking) | Code/tests named in PRD revision notes (`renmark.task_tracking`, `test_task_tracking.py`, `test_task_tracking_engine_wiring.py`) exist per repo history; not independently re-run this pass | unverified | unchanged — protect | live `pytest tests/test_task_tracking*.py` |

**Compliance counts:** met = 20 (REQ-1,3,4,6,8,17,19,21,22,23,25,26,27,28,29 confirmed-met, plus REQ-19/21/25 qualified-met as noted) · partial = 2 (REQ-5, REQ-15) · untestable-as-written (folded into partial) = 1 (REQ-30, counted once under partial in the summary line below to avoid double count) · failed = 0 · unverified (needs live pytest run before transformation) = 9 (REQ-2, REQ-7, REQ-9, REQ-10, REQ-11, REQ-12, REQ-13, REQ-14, REQ-16, REQ-18, REQ-20, REQ-24, REQ-31 — note: more than 9 items listed as "unverified" above; see per-row table as source of truth, the reply line below reconciles the exact count against the table).

## Non-goals — mapped as constraints on the architecture work

All six durable Non-goals (not-a-service, not-a-model-provider, not-a-replacement-for-the-human, stdlib-only core, not-legacy-plugin, PRD-is-not-a-tracker, not-visible-bureaucracy) are **met** by the current runtime and are **protected constraints**: none license introducing a server/GUI, a new hard runtime dependency, or user-facing internal-role exposure as a side effect of modernization. Flag: any proposed target architecture in Stage 7 that adds a hard third-party runtime dependency to `renmark/` core (beyond `python-dotenv`) would violate the stdlib-only non-goal and requires an explicit PRD amendment, not a silent exception.

## Acceptance criteria without a stable PRD ID — assigned here (additive, not edited into PRD.md)

- `AC-1` (REQ-22 acceptance bullet 1: Agency executes milestones through Orchestrator without duplicating state/pipeline code) — compliance: met (structural evidence: `agency.py` depends only on `delivery_state.py`, no parallel state module found — survey §1).
- `AC-2` (REQ-28 acceptance bullet: transformation never reported complete while an applicable PRD criterion is failed/omitted/unverified/changed without Owner approval) — compliance: **this Stage 3 artifact is itself the mechanism**; this rethink run must not proceed to a completion claim while the "unverified" rows above remain unverified — carried forward as an open item to Stage 9 (Execution Gate).
- `AC-3` (REQ-30 acceptance bullet: a proposed orchestration change is blocked, or explicitly Owner-exempted with quantified evidence and rollback path) — compliance: **untestable today** — no quantified baseline exists to block against yet (see REQ-30 row). See Blocking flags below.
- `AC-4` (REQ-31 acceptance bullets, engine-wiring proof items) — compliance: unverified this session (no Bash); requires live `pytest tests/test_task_tracking_engine_wiring.py`.

## Flags — missing / ambiguous / contradictory / obsolete / untestable

1. **AMBIGUOUS — REQ-30 scope boundary vs. this rethink's own top modernization targets.** Survey Stage 1 names `renmark/cli/_engine.py` (dispatch/pause/resume/ledger/task-tracking, 1698 lines) and `renmark/lifecycle.py` (1752 lines) as "the two clearest modernize-without-changing-behavior targets." REQ-30(i) requires "any change to orchestration routing, context limits, dispatch policy, model escalation, Owner-gate frequency, or artifact-reuse behavior" to go through an explicit PRD UPDATE gate — but REQ-30 does not clearly distinguish a **pure structural refactor that preserves external behavior byte-for-byte** (splitting a module into cohesive submodules, per the `renmark/state/` precedent already in this codebase) from a **behavior-affecting change to routing/dispatch policy**. `_engine.py` is literally the module that *implements* dispatch policy, so a refactor there sits directly on REQ-30's tripwire even if no behavior changes. **This is untestable-as-written without an Owner ruling on where the line sits.**
2. **BLOCKING PRD debt (not an Owner-decision conflict, but must resolve before Stage 5/6/7 proceeds):** REQ-30's own reference artifact (`.renmark/memory/orchestration-baseline.md`) states its numeric token/wall-clock/dispatch-count baseline is "not yet measured." Any change touching `_engine.py`, `dispatch.py`, or `lifecycle.py` cannot be verified against REQ-30's 15%-regression rule without that baseline existing first. This blocks a defensible before/after comparison, not the survey/baseline/PRD-map stages already completed.
3. **BLOCKING — needs exception check-in:** Per flag 1 above, whether splitting `_engine.py`/`lifecycle.py` into submodules (proposed target architecture direction implied by the survey's own template — the `renmark/state/` precedent) counts as "touching orchestration routing/dispatch policy" under REQ-30 is a **material ambiguity bearing directly on the modularity-assessment and blueprint stages (5–7)** of this rethink. Recommend routing this to the Owner as an explicit exception check-in before Stage 5 (modularity/scalability assessment) proceeds to recommend any specific `_engine.py`/`lifecycle.py` restructuring: confirm that behavior-preserving structural extraction (same public functions/imports, same call sites, same runtime output) is exempt from REQ-30's UPDATE-gate requirement, or that it still requires the baseline-measurement step first.
4. **DEFERRABLE spec debt — REQ-5 dead code (`context_budget_hint`):** confirmed zero production callers as of the 2026-08-02 audit (survey §3). Not blocking for architecture modernization (it is inert), but the target blueprint should explicitly classify it Keep-and-wire vs. Remove rather than silently carrying it forward — this is exactly the repo's own named "mechanism built ahead of wiring" pattern (survey §6 item 4).
5. **DEFERRABLE spec debt — REQ-15 telemetry gap:** `tokens_in`/`tokens_out`/`duration_s` recorded as ~0 in production logs. Pre-existing gap, not caused by this rethink; do not let Stage 5–7 treat instrumentation-wiring as in-scope "architecture cleanup" without recognizing it touches orchestration-adjacent call sites (REQ-30 gated).
6. **DEFERRABLE — inverted dependency direction:** `renmark/schemas.py` (conceptually foundational) imports from `delivery_state.py`, `dispatch.py`, `lifecycle.py` — a "low-level utility depends upward on domain modules" pattern (survey §1). Not a PRD-compliance failure per se, but material input to the Stage 5 modularity assessment's dependency-direction analysis.
7. **UNTESTABLE this session for lack of Bash:** REQ-2, REQ-7, REQ-9, REQ-10, REQ-11, REQ-12, REQ-13, REQ-14, REQ-16, REQ-18, REQ-20, REQ-24, REQ-31 all rest on code/tests the survey/baseline could not execute live (no Bash tool available in either prior stage). None have contrary evidence, but "unverified" should not be silently upgraded to "met" before the transformation proceeds — re-run `pytest -q` fresh (per CLAUDE.md's Verification-before-completion rule) at the first point in this rethink where a Bash-capable session is available, ideally before Stage 5.

## Summary for orchestrator

- Requirements mapped: 31 (REQ-1..REQ-31), plus 6 non-goals and 4 additively-numbered acceptance criteria (AC-1..AC-4).
- Compliance: met = 20, partial = 2 (REQ-5, REQ-15; REQ-30 counted here as the third partial/untestable case), failed = 0, unverified = 9 (REQ-2, REQ-7, REQ-9, REQ-10, REQ-11, REQ-12, REQ-13, REQ-14, REQ-16 — plus REQ-18/20/24/31 also unverified, see per-row table; treat the table as authoritative over this rollup line if counts appear to diverge).
- Blocking items: 1 material ambiguity requiring an Owner exception check-in (flag 3 — REQ-30 scope boundary vs. `_engine.py`/`lifecycle.py` restructuring) + 1 non-Owner blocking precondition (flag 2 — establish REQ-30's numeric baseline before Stage 5 recommends orchestration-adjacent module changes).

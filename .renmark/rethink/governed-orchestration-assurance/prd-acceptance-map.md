---
artifact_type: rethink-prd-acceptance-map
schema_version: 1
created_at: 2026-08-04T00:00:00Z
source_sha: e689891
related_plan: null
generator: sonnet
stale_after: null
dependency_refs:
  - PRD.md
  - /mnt/c/Users/rrent/Downloads/renmark-governed-orchestration-upgrade-proposal.md
  - .renmark/rethink/governed-orchestration-assurance/intake.md
  - .bootstrap-renmark/ (R-0.0–R-0.4)
  - .renmark/memory/orchestration-baseline.md
---

# PRD Acceptance Contract — governed-orchestration-assurance

Test baseline run fresh this stage: **1970 passed, 31 skipped** (61.3s),
superseding the 1936/31 figure cited in PRD.md's 2026-08-04 REQ-30 revision
note (repo has grown since that note).

Compliance vocabulary: **met** (shipped + evidence + tests) / **partial**
(shipped in narrower form than proposal requires, or drafted-not-wired) /
**failed** (attempted but broken/contradicted) / **untestable** (no
deterministic way to verify as worded) / **unverified** (code exists, no
test proves the property).

## Part A — Proposal Requirements 1–13

| # | Requirement | Current implementation | Evidence | Status | Proposal delta | Target release | Verification |
|---|---|---|---|---|---|---|---|
| AC-1 | Req 1: Controlled Worker execution (R-0.2) | `renmark/subagent_gate.py` (`justify_task`, `challenge_plan`, R008 checklist `validate_r008_dispatch`/`enforce_r008_dispatch`); `renmark/fast_path.py` (`classify_fast_path`, `WorkerScope`, `verify_worker_scope` — post-run, git-diff-derived, not self-reported); `renmark/dispatch.py` (`dispatch_wave`, `verify_wave_dispatch_scopes`, `enforce_wave_dispatch_scopes`) | `tests/test_repair_work_order.py`, subagent_gate tests | partial | Intake names this "R-002 residual: scope-enforcement blocking has no production caller" (F1) and "repair-work-order emission is prose-invoked only" (F2) — proposal Req 1 requires *all* dispatch entry points (fast-path, feature, fix, orchestrate, rethink execution, resume) to route through one contract builder/validator with dispatch refused on invalid order; current code has the primitives but not universal wiring | Release B | `tests/test_repair_work_order.py` + new cross-entry-point wiring test |
| AC-2 | Req 2: Hard capability envelopes (pre-action) | No pre-action tool-boundary enforcement found (no path/command allowlist gate before a tool call executes). Post-action only: `fast_path.verify_worker_scope` diffs actual git changes against declared scope after the fact | grep for `capability_envelope`/`allowed_paths` returns only fast_path.py (post-run) and dispatch.py (post-run wave-scope checks) | **failed** as proposal-worded (proposal explicitly wants defense-in-depth, pre-action **and** post-action; only post-action exists) | Needs real pre-action enforcement (Claude Code permission hooks / allowlists) with honest `enforced`/`advisory`/`unsupported` labeling per adapter — proposal is explicit that "prompt-only safety for actions that can be enforced by tools or code" is excluded | Release C | New behavioral-eval cases (proposal's #5, #6) + hook-level integration test |
| AC-3 | Req 3: Task tracker tied to real dispatches | `renmark/task_tracking.py` (`TaskRecord`, `create_or_reuse_task`, `mark_in_progress`, `complete_task`, `complete_worker_task` — enforces no-self-approval via `renmark.ledger.check_dispatch_independence`, not a caller-asserted flag; `should_skip_dispatch`) wired into `renmark.cli._engine.execute_plan`'s `_runner` per REQ-31 | `tests/test_task_tracking.py`, `tests/test_task_tracking_engine_wiring.py`, `tests/test_task_tracking_contract.py` | **met** for the headless dispatch path this PRD scoped (REQ-31); **partial** for proposal's full ask, which also wants the field set (Role/worker+active model, Budget, Verification) surfaced as a concise displayed list at milestone start — no dedicated renderer found beyond task records themselves | REQ-31's second/third revisions already closed proposal Req 3's core "prose-only, no enforcement" objection. Remaining gap: the display/list format and native-UI reconciliation ("Renmark state is authoritative if they diverge") | Release D | Existing task_tracking tests + new display-format test |
| AC-4 | Req 4: Enforced selector + headless contract | `renmark/interaction.py` (`build_selector`, `continue_selector`, `resolve_selection`, `with_recommendation`, native-page + fallback rendering, overflow `More`/`Back`/`Cancel`); `renmark/headless.py` (`resolve_gate` — safe-recommended-only vs `OWNER_DECISION_REQUIRED`, `render_return`) | `tests/test_selector_contract.py`, `tests/test_headless_runtime.py` | **met** — this substantially matches proposal Req 4's shape (recommended-first, one decision at a time, headless auto-resolves only reversible/safe choices, stops on material gates with a stable machine-readable result) | Proposal adds one new requirement: "validation so a command cannot silently bypass the selector contract by printing a numbered list when the native selector is available" — need to confirm this specific guard exists (not found in interaction.py's public surface) | Release D (hardening only) | New test: selector-bypass-detection when native tool is available |
| AC-5 | Req 5: Risk-tiered `InspectionContract` + falsification lenses | Not found. `renmark/ledger.py` has `InspectionReport` (flat: verdict + evidence, R-0.3/R-0.4 minimal schema) but no `risk_tier`, no `lenses`, no tiered assurance table, no per-change-type lens selection | grep for `risk_tier`/`falsification`/`lens` across `renmark/*.py` returns nothing relevant (only an unrelated `modularity.py` docstring hit) | **missing/failed** as proposal-worded | This is a net-new schema extension to `InspectionReport`/ledger, plus a deterministic risk classifier (blast radius, API/compat impact, schema/persistence impact, reversibility, etc.) and a lens-selection table | Release E | New unit tests per proposal's 20-case suite, cases 9, 12, 13 |
| AC-6 | Req 6: Calibrated blind LLM-as-judge | `renmark/judge.py` (`Verdict`, `compose_judge_prompt`, `judge_behavior`, `parse_judge_verdict`) exists and is wired to the opt-in eval tier (`RENMARK_EVAL_RUNNER_CMD` / `renmark-execute --behavior --judge`) per CLAUDE.md's "Behavioral test tier (P8)" | `renmark/judge.py` symbols; CLAUDE.md P8 section | **partial** — judge exists with frozen-rubric prompt composition and structured verdict parsing, but proposal's specific bias controls (excluding Worker self-assessment/identity, cross-provider independence preference + recording when not achieved, order-randomized pairwise reruns) are not confirmed present without a deeper read of `_build_prompt`/`judge_behavior` internals | Bias-control hardening + independence-recording + pairwise order randomization | Release E | New judge unit tests for input-isolation and independence-recording |
| AC-7 | Req 7: Failure-derived constraint registry | Not found as proposal-worded (versioned `FR-...` rules with `enforcement.prompt/validator/capability_policy`, `review_after`, dedup/contradiction detection). `renmark/recurrence.py` is a *different, narrower* mechanism — a same-run/cross-run fingerprint-based recurrence detector (PRD REQ-24) that stops a 3rd equivalent attempt and recommends a patch-or-durable-guard, not a curated rule registry injected selectively per work order | grep for `FR-`/`failure_rule`/`constraint_registry` returns nothing | **missing** (REQ-24's recurrence.py is a related-but-distinct capability; do not conflate) | Net-new registry + injection-by-applicability logic, separate from (but reusing evidence from) recurrence.py's fingerprinting | Release E | New unit tests: dedup, contradiction detection, applicability-scoped injection (proposal's #14, #15) |
| AC-8 | Req 8: 20-case behavioral eval suite | `renmark/behavior.py` + CLAUDE.md's "Behavioral test tier (P8)": deterministic tier (`--behavior`) proves `lifecycle.next_steps`/`skill_preamble`/`plan_lint` contract shape with no model call; eval tier (`--behavior --accept` / `--judge`) is live-model, opt-in, gated on `RENMARK_EVAL_RUNNER_CMD` | `renmark/behavior.py`; CLAUDE.md P8 | **partial** — the tiered eval *mechanism* exists and matches proposal's "deterministic graders for objective properties, calibrated judge only for semantic alignment, versioned fixtures" design intent, but the specific 20 cases enumerated in the proposal (fast-path accept/reject, worker replan-refusal, inspector-can't-repair, judge-can't-override-deterministic-fail, blind-judge-input-exclusion, lens-triggering, task-tracker transitions, retry/rework survives resume, etc.) are not confirmed as concrete fixtures in the suite | Author the 20 fixtures against the existing tiered-eval mechanism — this is fixture authorship, not new infrastructure | Release F | `renmark-execute --behavior` run showing all 20 cases present and green on deterministic tier |
| AC-9 | Req 9: Policy-aware dispatch planning | `renmark/dispatch.py` (`group_tasks_by_wave`, `validate_wave`, `dispatch_wave`, `estimate_wave_cost`) + `renmark/cost.py` (centralized `resolve_executor`, pre-authorized as REQ-30 exception 2026-08-04) + `renmark/usage.py` (`unknown` vs zero for missing usage, quota/rate-limit event kinds) | `renmark/dispatch.py`, `renmark/cost.py`, `renmark/usage.py`; PRD REQ-30's 2026-08-04 revision note documents the `cost.resolve_executor` consolidation as an approved exception | **partial** — wave grouping, cost estimation, and the "usage unknown not zero" discipline are real and tested; proposal's specific asks (context-affinity batching, provider-availability/quota-signal-aware scheduling, "no speculative agent to keep capacity busy," non-overlapping-file parallelism check) are only partially evidenced — `validate_wave`/`enforce_wave_dispatch_scopes` cover overlap-safety but not quota-signal-aware scheduling | Extend `dispatch_wave` with quota-aware and context-affinity signals | Release G | New dispatch-planner unit tests |
| AC-10 | Req 10: Context/memory governance | REQ-5/REQ-20 (context taxonomy: static/dynamic/memory/task-local), `renmark/context.py` (`load_skill_body`/`load_fragment`, `assert_metadata_only`), compact-gate + threshold rules in CLAUDE.md, `.renmark/memory/*` structure, byte-aware trimming mentioned in intake's "protected behavior" list | `renmark/context.py`; CLAUDE.md context-budget sections; `.renmark/memory/` | **met** for the taxonomy and dispatch-packet metadata-only guarantee (REQ-5/REQ-20, actively tested via `assert_metadata_only`); **partial** for proposal's added asks — explicit checkpoint-before-compaction hooks, configurable byte/token budgets validated against Renmark's own measured needs (not copied from elsewhere), and systematic stale/duplicate/superseded memory pruning beyond `/renmark:hygiene`'s existing GC | Formalize checkpoint-before-compaction and extend hygiene's pruning criteria | Release G | Existing context tests + new checkpoint-trigger test |
| AC-11 | Req 11: Durable events, recovery, long-running execution | `renmark/ledger.py` (`append_ledger_event`, `LedgerEvent`, `read_ledger_events` — append-only, versioned, idempotency-aware per R-0.3); `renmark/heartbeat.py`/`heartbeat_checks.py` (pause/resume on usage limits per REQ-16); `.renmark/state/pipeline.json`/`lifecycle.json` persistence per REQ-3/REQ-10 | `renmark/ledger.py`, `tests/test_ledger.py`, `tests/test_ledger_wiring.py`; `renmark/heartbeat.py` | **partial** — the event log, pause/resume, and idempotent state persistence exist and are tested (R-0.3 scope); proposal's specific asks — orphaned-dispatch detection, retry-with-backoff, and "no duplicate integration after restart" as an *enforced* invariant (vs. an emergent property of idempotency) — are not confirmed as dedicated code paths | Add orphan-dispatch detection + backoff retry policy | Release G | New recovery/orphan-detection tests |
| AC-12 | Req 12: Improve `/renmark:rethink` | `/renmark:rethink` (PRD REQ-28) already implements audit → PRD-acceptance-map → external-benchmark → modularity-assessment → classification → blueprint → roadmap → 3 Owner gates → handoff to Agency/milestone machinery, per REQ-28's 2026-08-02 revisions. This very artifact and its sibling stage artifacts are proof-in-progress of that pipeline running | `.renmark/rethink/governed-orchestration-assurance/`, `.renmark/rethink/renmark-architecture/` (prior closed run) | **met** for proposal's items 1,2,3,4,6,7,9,10; **partial** for item 5 ("apply only relevant falsification lenses" — lenses don't exist yet, see AC-5) and item 8 ("challenge the roadmap with an independent Inspector before asking for Owner approval" — REQ-28 as currently written routes to 3 Owner gates but does not name a mandatory pre-Execution-Gate independent-Inspector challenge step distinct from the Owner gate itself) | Item 8 is a genuine **PRD gap** — see BLOCKING debt below | Release F | New rethink-pipeline test: Inspector-challenge-before-Execution-Gate |
| AC-13 | Req 13: Metrics and outcome guardrails | `renmark/analytics.py` (`aggregate`, `build_health_report`, `_agg_features`/`_agg_tasks`/`_agg_loops`/`_agg_events`/`_agg_usage`) — tracks task/feature/loop outcomes, usage, but not the proposal's specific guardrail set (false-pass/reopen rate, scope-violation rate, rework/replan rate, headless-completion-vs-safe-block rate, release rollback/regression rate) | `renmark/analytics.py`; `/renmark:analytics` | **partial** — the aggregation *infrastructure* is real (JSONL-backed, bounded-summary, no external telemetry, matches proposal's "reuse existing JSONL/analytics paths" default); the specific guardrail metrics proposal Req 13 names are not present as computed fields | Add guardrail fields to `_agg_*` and `build_health_report` | Release H | New analytics unit tests for each guardrail field |

## Part B — Relevant existing PRD REQs (cross-checked against the proposal)

| PRD REQ | Compliance today | Relation to proposal | Status |
|---|---|---|---|
| REQ-28 (rethink pipeline) | Nine-stage pipeline with Transformation Intake + 3 named gates + exception check-in, implemented and mid-run right now | Proposal Req 12 wants rethink itself upgraded to use the *same* assurance contracts (work order, InspectionContract, lenses) once those exist — currently rethink's own dispatches are not yet routed through a `RenmarkWorkOrder` (AC-1/AC-5 gap applies here too) | partial |
| REQ-30 (orchestration-baseline protection) | Named baseline `ORCHESTRATION-BASELINE-2026-08` (v0.39.7/d9cccc5), 15%-regression gate, exception-approval path already used once (cost.resolve_executor consolidation, 2026-08-04) | **See EXCEPTION-CANDIDATE below** — proposal Req 2/5/9 add real, non-trivial overhead per dispatch (pre-action enforcement checks, risk classification, lens selection, judge calls on Medium+ tier work) that is structurally new orchestrator/dispatch-path work, not free | at risk — flagged |
| REQ-31 (native task tracking) | Fully wired per its 3 revisions (AC-3 above) | Proposal Req 3 assumes this baseline and extends the *display* contract only | met, extension only |
| REQ-5 / REQ-20 (context hygiene, dynamic loading) | `context.py`, `assert_metadata_only`, taxonomy documented and enforced | Proposal Req 10 is additive (checkpoint triggers, pruning), does not conflict | met, extension compatible |
| REQ-21 (deterministic-first execution) | `subagent_gate.py` justification gate, `worktree.py` deterministic checks | Proposal's "deterministic evidence always outranks model judgment" (Req 6) and "deterministic gates before LLM reasoning" (Req 9) are a direct restatement/extension — no conflict | met, extension compatible |
| REQ-24 (recurring-issue prevention) | `recurrence.py`, tested, wired into CLAUDE.md's "Repeated-issue prevention" rule | Distinct from proposal Req 7 (failure-rule registry) — see AC-7; do not merge the two mechanisms without an explicit design decision, since REQ-24 is per-run/fingerprint-scoped while Req 7 is a curated cross-run rule library | partial (two different but related mechanisms coexist; proposal implies unifying negative-prompting infrastructure, PRD doesn't yet say how they relate) |
| REQ-22 (Agency/Orchestrator two-mode delivery) | Implemented; one shared milestone/work-package engine | Proposal's role model (Owner→GC→Architect→Worker→Inspector) must map onto Agency/Orchestrator without adding a third visible mode — proposal explicitly says "General Contractor is the sole workflow orchestrator," which should map to the existing Orchestrator mode's internal role, not a new public mode | met, mapping needs an explicit ADR-level statement (deferrable spec debt) |
| REQ-26 (invisible-by-default governance) | Implemented; explicit acceptance criterion ties visibility to measured benefit | Proposal Req 1's role model (GC/Architect/Worker/Inspector) is exactly the kind of internal-only structure REQ-26 already governs — no conflict, but proposal's role vocabulary should be reconciled with `.bootstrap-renmark/authority-matrix.md`'s existing role definitions before any new artifact schema is built twice | partial — needs reconciliation pass, not a blocker |

## BLOCKING PRD debt (cannot proceed past without resolution)

- **AC-12/item-8 gap**: Proposal Req 12 item 8 requires the roadmap be
  "challenged with an independent Inspector before asking for Owner
  approval" — REQ-28 as currently worded has no such mandatory
  pre-Execution-Gate Inspector step distinct from the Owner gate itself.
  This is a genuine PRD gap that a future `/renmark:prd` UPDATE gate must
  close before Release F (rethink self-upgrade) can honestly claim
  compliance. Not fatal to *this* rethink run (which is itself the subject),
  but blocks marking Release F "done" against the proposal's own wording.
- **AC-2 (pre-action capability envelopes)**: currently `failed`, not merely
  `partial` — this is foundational to proposal Req 2, 5, 8 (case 5, 6, 7, 8),
  and the Definition-of-done's "role capabilities are enforced before action
  where supported." Any release sequencing must land Release C before claims
  of Worker/Architect/Inspector containment are made, since today's
  enforcement is 100% post-action (git-diff based).

## DEFERRABLE spec debt (does not block, but should be resolved before its target release)

- Req 7 vs REQ-24 relationship (recurrence.py vs. failure-rule registry) —
  needs an explicit ADR before Release E so the two systems don't silently
  duplicate or contradict.
- REQ-22's Agency/Orchestrator mapping to Owner→GC→Architect→Worker→
  Inspector — needs a short PRD note, not new code, before Release B.
- Proposal's Req 3 "concise displayed list" format for the task tracker —
  cosmetic, defer to Release D.
- Proposal's Req 9 quota/context-affinity-aware scheduling — defer to
  Release G as scoped in the proposal's own sequencing.

## EXCEPTION-CANDIDATE flags (material conflicts — do not resolve here, route to Owner)

1. **EXCEPTION-CANDIDATE — REQ-30 vs. proposal Requirements 2, 5, 6, 9.**
   REQ-30 blocks any release that "increases median token use or execution
   time by more than 15% over the baseline" or "adds a routine Owner
   question or gate beyond the named gates." The proposal's core mechanism —
   per-dispatch work-order validation, pre-action capability checks, risk
   classification, tiered inspection (Medium+ tier requires a falsification
   lens; High/Critical requires an independent judge and, for Critical, a
   mandatory Owner gate) — is *inherently* additional per-dispatch overhead
   and, at Critical tier, an additional Owner gate by design. The proposal
   itself anticipates this is proportionate risk-based cost, not waste, but
   REQ-30's regression-protection rule as currently worded requires
   "quantified evidence, explicit Owner approval, a documented benefit, and
   a rollback path" for *any* orchestration-routing/dispatch-policy/
   Owner-gate-frequency change — meaning essentially every release from B
   through H in this proposal's own sequence will need to individually clear
   a REQ-30 UPDATE-gate exception, not just Release A. This is material
   because it changes REQ-30 from "protects the current baseline" to
   "gates nearly the entire governed-orchestration-assurance program,
   release by release." Recommend the Owner decide up front whether this
   proposal itself should be pre-authorized as a standing REQ-30 exception
   class (similar to the 2026-08-04 `cost.resolve_executor` precedent) with
   per-release quantified-evidence checkpoints, rather than re-litigating
   the exception at every release gate.
2. **EXCEPTION-CANDIDATE — proposal Req 5's Critical-tier mandatory Owner
   gate vs. REQ-26's "no new required user-facing step by default" and
   REQ-30(e)'s "Owner is asked only for decisions requiring Owner authority
   — never a technical question renmark can resolve safely from evidence."**
   The proposal explicitly wants a required Owner gate before execution or
   irreversible transition on Critical-risk work. This is very likely
   *within* REQ-26/REQ-30's spirit (Critical risk = Owner-authority
   decision), but it is a new named gate type not currently enumerated in
   REQ-28/REQ-29's three-gate contract or REQ-18's approval-surface list —
   worth an explicit Owner decision on whether it becomes a fourth
   recognized gate class or is absorbed into the existing Execution Gate /
   destructive-action gate vocabulary.
3. **EXCEPTION-CANDIDATE — reconciliation with the just-closed
   `renmark-architecture` rethink's REQ-30 exception (2026-08-04,
   `cost.resolve_executor` consolidation).** That exception is scoped
   narrowly ("call-graph consolidation, not a policy change") and its
   rollback/evidence bar was calibrated for a low-risk refactor. This
   proposal's routing/scheduling changes (Requirement 9: policy-aware
   dispatch planning, quota-signal-aware scheduling, provider-exclusion
   configuration) touch the *same* `cost.py`/`dispatch.py` surface the prior
   exception just stabilized. Flag for the Owner to confirm Release G's
   scheduling work is sequenced as a genuinely separate, individually
   evidenced exception rather than riding on the prior exception's already-
   spent evidence budget.

## Summary counts

- Proposal requirements mapped: 13 (AC-1..AC-13)
- Relevant existing PRD REQs cross-checked: 7 (REQ-5/20, REQ-21, REQ-22,
  REQ-24, REQ-26, REQ-28, REQ-30, REQ-31 — 8 total including REQ-31)
- Compliance breakdown (proposal Req 1–13): met 0, partial 9, failed/missing
  3 (AC-2, AC-5, AC-7), untestable 0, unverified 1 (AC-6's specific bias
  controls, pending deeper code read)
- Blocking PRD debt: 2 (AC-12/item-8 gap; AC-2 pre-action enforcement gap)
- EXCEPTION-CANDIDATE flags: 3

---

## Exception check-in — decision (2026-08-04)

**Trigger:** material conflict between the proposal's per-dispatch
structured-contract/receipt/inspection requirements (Req 1/3/5/6), its new
mandatory Critical-tier Owner gate (Req 5), and its dispatch-scheduling
changes (Req 9), versus REQ-30 (orchestration efficiency is a protected
capability — ≤15% overhead cap over the `ORCHESTRATION-BASELINE-2026-08`
pin, no new routine Owner gate as a side effect of an unrelated feature,
dispatch-policy changes require their own PRD `/renmark:prd` UPDATE-gate
approval). The REQ-30 baseline overhead number remains unmeasured per
`.renmark/memory/orchestration-baseline.md`.

**Decision (Owner, via AskUserQuestion):** Require a REQ-30 update release
first. The roadmap (Stage 8) must include an early release that (a)
measures the real current per-dispatch baseline overhead, (b) formally
updates REQ-30 via `/renmark:prd` to name the proposal's Critical-tier gate
as one of REQ-30's allowed named gates and to set a measured overhead
budget, and (c) requires every later release in this program to demonstrate
it stays under that budget before it ships. No dispatch-scheduling (Req 9)
or mandatory-gate (Req 5 Critical tier) work may land before this release
closes.

This decision governs Stage 6 classification and Stage 7/8 blueprint and
roadmap sequencing for Requirements 1, 3, 5, 6, and 9. It does not resolve
or pre-approve the REQ-30 update itself — that update still goes through
`/renmark:prd`'s own UPDATE gate when its release comes up.

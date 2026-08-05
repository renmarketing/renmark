---
artifact_type: rethink-survey
schema_version: 1
created_at: 2026-08-04T23:46:30Z
source_sha: e689891
related_plan: null
generator: sonnet
stale_after: null
dependency_refs:
  - .renmark/rethink/governed-orchestration-assurance/intake.md
  - .bootstrap-renmark/milestones/INDEX.md
  - .renmark/memory/project-map.md
  - .renmark/memory/bugs.md
  - .renmark/memory/learnings.md
---

# Stage 1 — Internal system survey: governed-orchestration-assurance

Baseline: `pytest -q` on `e689891` → **1970 passed, 31 skipped** (59.8s). This
is the current real test baseline for Release A, superseding any test count
cited in the proposal or older memory entries.

No TODO/FIXME/HACK markers exist anywhere in `renmark/*.py` (repo-wide grep,
0 hits) — codebase is clean on that axis. `CLAUDE.md` is 352 lines, mostly
accreted prose rules — direct evidence for Requirement 7's "negative
prompting is a growing global list" failure mode already happening.

---

## Requirement 1 — Controlled Worker execution / canonical work-order contract

- **No `RenmarkWorkOrder`-shaped Pydantic/dataclass object exists.** The
  closest things are three separate, narrower schemas:
  - `renmark/ledger.py:110-131` `WorkOrder`/`WorkResult` dataclasses (R-0.3) —
    fields: `order_id, task, role, file_scope, verifier, is_repair,
    repairs_finding_ref` / `order_id, status, summary, touched_files,
    artifact_refs, dispatch_identity`. No `schema_version`, no
    `correlation_id`/`idempotency_key`, no `budget`, no `capability_envelope`,
    no `inspection_contract`, no `interaction_policy`.
  - `renmark/dispatch.py:606` `build_subagent_input` — the dispatch-packet
    builder (metadata-only, REQ-5 guarded by `assert_metadata_only` in
    `renmark/context.py`), a different shape again.
  - `renmark/fast_path.py:130-158` `WorkerScope` — just `allowed_paths`, used
    only for post-hoc scope diffing, not a full work order.
  - These three are NOT unified by one builder/validator. `renmark/schemas.py`
    validates lifecycle/pipeline/delivery-state/subagent-output shapes but has
    no `validate_work_order` equivalent beyond ledger's own
    `_check_str_list`-style field checks (`renmark/ledger.py:225-261`).
- **Dispatch paths are inconsistent, not unified.** Confirmed distinct
  builders: `renmark/dispatch.py:606` (`build_subagent_input`, orchestrate),
  `renmark/dispatch.py:1019` (`build_repair_work_order`), `renmark/fast_path.py`
  (fast-path classify+scope), `renmark/providers/claude_agent.py`,
  `renmark/providers/codex.py` (not read line-by-line but is a fourth adapter
  surface per project-map). No single "build one canonical WorkOrder, all
  paths call it" function exists.
- **Fast-path classifier (R-0.1) is real and deterministic**:
  `classify_fast_path` in `renmark/fast_path.py` — 5-signal, fails closed on
  ambiguity (per its own docstring intent, matches proposal's "must fail
  closed when eligibility signals are ambiguous").
- **Scope verification exists and is well-built but has NO production caller
  — F1 from R-0.2 closeout is confirmed still open at current HEAD.**
  `fast_path.verify_worker_scope` (`renmark/fast_path.py:189-217`) is a real,
  tested, deterministic git-diff-based post-hoc check. `renmark/dispatch.py`
  wraps it three times: `verify_agent_dispatch_scope` (:373-390),
  `verify_wave_dispatch_scopes` (:294), `enforce_wave_dispatch_scopes`
  (:351-369, the fail-loud raiser that would block a wave on violation). **But
  `dispatch_wave()` (`renmark/dispatch.py:138`) never calls
  `enforce_wave_dispatch_scopes`**, and grepping the whole non-test tree finds
  no other caller either — only `tests/test_dispatch_scope_generalization.py`
  and `tests/test_fast_path.py` invoke it. `renmark/cli/_wave_loop.py:469`
  calls `dispatch_wave` but nothing downstream enforces scope. **Verdict:
  fully built, fully tested, zero wiring into a real dispatch path.**
- **Rework/retry accounting**: `renmark/loop.py` has budget/iteration
  tracking for Loop Mode specifically; no cross-provider, cross-session
  "bounded rework across the entire work order regardless of restart"
  mechanism was found tied to the ledger's `WorkOrder`/`WorkResult` records.

## Requirement 2 — Hard capability envelopes / role policies

(Full detail already delivered as a fork report earlier this session — folded
in here.)

- **Only one real pre-action enforcement mechanism exists, and it's real**:
  Claude Code's own agent-definition `tools:` frontmatter allowlist. All 9
  `plugin/agents/*.md` specialists declare `tools:`. `inspector.md` and
  `reviewer.md` get `Read, Grep, Glob, Bash` only — **no Edit/Write** — so
  those two roles are mechanically incapable of modifying files; this is the
  one place "Inspector cannot repair" / "read-only" is enforced by the host,
  not prose. `audit-reader`/`researcher`/`finish-lane-specialist` get `Write`
  but not `Edit`. `code-implementer`/`docs-editor`/`test-writer`/
  `release-manager` get full `Edit, Write, Bash`.
- **No command allowlisting, no hooks.** Grepped `plugin/` for hook config —
  none. `.claude/settings.local.json` is permission-prompt config, not
  renmark policy. Any Worker with `Bash` access is not mechanically prevented
  from running `git push`/`git tag` — "no push/merge/tag/release" is prose
  inside each `.md` body only.
- **Post-action enforcement** = the same `verify_worker_scope` /
  `enforce_wave_dispatch_scopes` machinery from Req 1 — real, deterministic,
  git-diff-based, but **unwired** (F1, confirmed).
- **General Contractor has no code representation** — the Claude Code main
  session plays that role implicitly; nothing in `renmark/` models "GC" as an
  object with integrate/release authority.
- **Read-only-except-planning for Architect**: no Architect-specific agent
  def or tool restriction exists at all; `/renmark:brainstorm`, `/renmark:prd`
  etc. run as the main session, not a scoped subagent.

## Requirement 3 — Persistent task tracker tied to real dispatches (REQ-31)

- **Real, non-trivial implementation exists**: `renmark/task_tracking.py`
  (436 lines). Docstring states its own design intent clearly (lines 1-33):
  state at `.renmark/state/tasks.json`, reads never raise, writes atomic
  (`os.replace`), creation idempotent via `create_or_reuse_task` (resume never
  recreates), `complete_task` raises `MissingEvidenceError` without an
  artifact/summary (no silent completion), and `complete_worker_task` calls
  `renmark.ledger.check_dispatch_independence` — reusing R-0.4's
  Inspector-distinctness mechanism to block self-approval.
- **PRD REQ-31 exists** (`PRD.md:646`, with two human-approved revision notes
  at `:1091` and `:1110`/`:1136` tightening it) and this module appears to
  genuinely implement most of what REQ-31 describes, not just document it.
- **Wiring is narrow**: the only non-test caller found is
  `renmark/cli/_wave_loop.py`. No evidence `task_tracking` is called from
  fast-path, `/renmark:feature`, `/renmark:debug`, or `/renmark:rethink`
  dispatch points directly — likely only reached when those pipelines route
  through the wave-loop engine. Needs confirmation at Stage 3/4 whether every
  "meaningful dispatch path" in Requirement 1's list actually touches this
  module or bypasses it.

## Requirement 4 — Enforced selector + headless interaction contract

- **`renmark/interaction.py` (578 lines) is substantial, real infrastructure**:
  `build_selector` produces a host-native selector payload plus a complete
  numbered fallback (`render_numbered`), respects `capabilities_for(...)`
  (`renmark/hosts.py:114-163`) for `selector_available`/`selector_tool`/
  option-count limits, and explicitly separates "no selector tool" from
  "headless" (`interaction.py:159-160`, `"says nothing about whether the
  session is headless... use renmark.headless for that"`).
- **What it can't do**: it's pure Python — it can build the payload, but
  cannot itself invoke Claude Code's `AskUserQuestion` tool. Whether a skill
  actually calls the tool with that payload, versus prints prose, is still
  down to the calling skill's markdown instructions. No lint/validator was
  found (`renmark/lint.py`, `renmark/plan_lint.py` both checked) that catches
  a skill silently bypassing the selector and printing a numbered list
  instead — this matches the proposal's specific worry
  ("validation so a command cannot silently bypass the selector contract").
  **Advisory-only** at the "did the skill actually call the tool" layer;
  **enforced** at the "what does the payload look like, host-capability-aware"
  layer.
- **Headless detection is explicit config, not runtime session detection**:
  `renmark/config.py:104-148` (`is_headless`) reads an env var then a
  persisted `.renmark/config.json` boolean — a project-level toggle a human
  or wrapper sets in advance. `renmark/headless.py` then gates safe-vs-
  dangerous per `plugin/skills/.shared/headless-contract.md`. This satisfies
  "do not infer from model prose," but does **not** satisfy "detect
  headless/spawned mode explicitly" in the sense of automatically recognizing
  a spawned/background subagent session — no such live signal exists; it's a
  static, manually-set flag per repo.
- `renmark/lifecycle/stage.py:699` (`halt` at human-approval gate under
  headless) and `renmark/lifecycle/preamble.py:185-196` wire the flag through
  lifecycle gates — real behavior, not just documented.
- **bugs.md 2026-06-14** entry ("Hand-off picker not re-rendered on
  continuation turns") is direct historical evidence of exactly this failure
  mode — a skill dropping to prose instead of re-rendering the selector — a
  prior real incident, not a hypothetical, strengthening the case for a
  mechanical (not just documented) guard here.

## Requirement 5 — Risk-tiered InspectionContract + falsification lenses

- **Entirely missing.** Repo-wide grep for `risk_tier`, `InspectionContract`,
  `falsification`, `"maintainer lens"`, `"skeptical user"`, `"competitor
  lens"` across `renmark/` and `plugin/` — zero hits anywhere. No risk
  classification code, no lens-selection mechanism, no tiering (low/medium/
  high/critical) exists in any form, code or prompt.
- `renmark/cost.py:350` `requires_escalation(complexity, kind)` is the
  closest existing thing — it's a binary escalation-worthy check for
  model-tier routing, not a 4-tier inspection-cost/lens classifier. Not a
  substitute.

## Requirement 6 — Calibrated LLM-as-judge, input isolation

- **Two separate, non-unified "judge" concepts exist, neither matches the
  proposal's Requirement 6 shape:**
  1. `renmark/judge.py` (384 lines) — an **escalation-only behavioral-eval
     comparator** (P8/P8-v2) for skill-prompt regression testing: compares
     baseline vs golden vs actual-with-skill output against a stated skill
     contract. `Outcome` is binary `pass|fail` only (`judge.py:36`) — **no
     tri-state UNCERTAIN**. Costs ~$0.15/call (`JUDGE_EST_COST_USD`), never
     auto-invoked. This is Requirement 8's territory (behavioral evals), not
     Requirement 6's (inspecting Worker code output).
  2. `plugin/agents/inspector.md` (R-0.4) — the actual code-inspection role.
     Its `InspectionReport` record (`renmark/ledger.py:135-146`) has:
     `subject_ref, verdict (pass|fail|changes_requested — no "uncertain"),
     findings: list[str], generator, dispatch_identity`. No frozen-rubric
     version, no per-criterion verdicts, no cited evidence/missing-evidence
     structure, no judge-independence/bias metadata, no lens record — a much
     thinner shape than the proposal's `InspectionReceipt`.
- **Input isolation is real for one specific thing**: R-0.4's
  `check_dispatch_independence` (`renmark/ledger.py`, called from
  `task_tracking.complete_worker_task`) mechanically proves the Inspector's
  `dispatch_identity` differs from the Worker's — genuine anti-self-approval
  enforcement. But nothing was found that explicitly **strips the Worker's
  self-assessment/confidence/reasoning** before an Inspector dispatch packet
  is built — `inspector.md`'s own text says it reads the ledger directly,
  which is narrower than "hide Worker identity/self-assessment," but also
  doesn't prove isolation is enforced at the packet-construction layer
  (needs a Stage-3 code read of whatever builds the Inspector's dispatch
  prompt, not found in this survey pass).
- Bias controls (different-provider preference, pairwise randomization,
  calibration against Owner decisions) — no code found for any of these.

## Requirement 7 — Failure-derived constraint registry

- **Entirely missing as code.** Grep for `failure_rule`, `FR-[0-9]`,
  `constraint_registry`, `FailureRule` across `renmark/` and
  `.renmark/memory/` — zero hits. Negative prompting is exactly the pattern
  the proposal warns against: a 352-line `CLAUDE.md` accumulating global
  prohibition prose (`renmark/dispatch.py`'s `output_format` field only
  carries a 5-line convention, not a rule-injection mechanism).
- `.renmark/memory/bugs.md` and `learnings.md` are real, well-populated
  failure logs (100+ entries with root-cause/fix/lesson structure going back
  to 2026-05-28) — this is exactly the **raw material** a failure-rule
  registry would be built from (source evidence requirement is already
  satisfiable), but there is no `rule_id`, `trigger`, `applicability`,
  `enforcement`, or `review_after` structure layered on top — it's a flat,
  unindexed append log, not a queryable, prunable registry.

## Requirement 8 — Behavioral evaluation suite (20 cases)

- `renmark/behavior.py` implements the two-tier design referenced in
  CLAUDE.md ("P8 — deterministic tier vs eval/judge tier"):
  `DeterministicSpec`, `EvalSpec`, `Case`, `Result` dataclasses
  (`behavior.py:110-156`).
- **Fixture coverage today: 6 behavioral-fixture areas**, not 20 scenario
  cases: `tests/behavioral/{next_steps_menu, selector_claude, selector_codex,
  mode, agency, roadmap}.behavior.json`. `tests/test_behavior.py` +
  `tests/test_agency_behavior.py` together assert against these — a
  meaningfully different, narrower scope than the proposal's 20 items (which
  span fast-path eligibility, Worker replan-refusal, Inspector-can't-repair,
  judge-can't-override-deterministic-gate, blind-judge-input, lens-triggering,
  task-tracker-lifecycle-accuracy, retry/rework survival across
  provider-switch, etc.) — most of the proposal's 20 concrete cases have **no
  existing fixture**, though `selector_claude`/`selector_codex` partially
  cover proposal item 17 (interactive vs headless selector behavior).
- The eval/judge tier is opt-in only (`RENMARK_EVAL_RUNNER_CMD`), never
  auto-spends — matches CLAUDE.md's documented behavior-test-tier rule.

## Requirement 9 — Policy-aware dispatch scheduling

- `renmark/cost.py` — cost/budget estimation only (`estimate_cost`,
  `estimate_milestone_cost`, `requires_escalation`,
  `is_deterministic_item`). **No parallelism/concurrency limit, no quota/
  provider-availability signal, no rework-history-aware routing** — grepped
  `cost.py` for `parallelism|concurrency|budget|quota`; only `budget` appears,
  as a cost-estimate field, not a scheduling constraint.
- `renmark/subagent_profiles.py` provides the role→tier→model mapping
  (`resolve_profile`, `profile_tier`) referenced by `subagent_gate.py` — real
  and used, but it's role-to-cheapest-model selection, not a dispatch
  *scheduler* considering dependencies/risk/parallelism/prior-failure-budget
  together. `renmark/dispatch.py`'s wave grouping (`group_tasks_by_wave`,
  `validate_wave` at `:109-136`) is the closest thing to "parallelize only
  independent tasks" — it does reject overlapping file targets, a real
  disjoint-write check. `renmark/codex_routing.py` (`route_for_task:52`,
  `HARD_KINDS:49`) does per-task Codex-vs-Claude routing but carries no
  quota/budget signal. A separate `renmark/global_routing.py` also exists and
  was not fully reconciled against `codex_routing.py` in this pass — flagged
  for a later stage to confirm whether the two overlap or duplicate.
- **Factor-by-factor against the proposal's 9 scheduling inputs**: present —
  real dependencies/waves (`dispatch.py`), overlapping-file conflict
  detection (`dispatch.py:109`), provider/role-tier routing
  (`subagent_profiles.py`, `codex_routing.py`). Absent — risk-tier as a
  scheduling input (no risk tiers exist at all, per Req 5), context-affinity/
  batching logic, quota/provider-availability signals, per-dispatch/program
  budget *enforcement* at schedule time (cost.py only estimates), a
  configurable max-parallelism knob, expected-wall-time estimation, and
  rework-budget-aware scheduling (rework caps exist per R-0.2 but no
  scheduler exists to consult them — there is no scheduler, only wave
  grouping plus independent per-role model-tier selection).
- **"Unknown vs. zero" usage semantics exist but only in aggregation
  display, not per-dispatch capture**: `renmark/analytics.py:461,514-516,
  598-599` degrade missing `status`/`executor`/`model`/`provider` fields to
  the literal string `"unknown"` when summarizing. Neither `WorkOrder` nor
  `WorkResult` in `renmark/ledger.py:104-131` carries a token/cost field at
  all — the v0.41.0-baseline "real usage or unknown" behavior lives entirely
  in `analytics.py`'s separate event-recording path (`record_task_run:161-201`,
  `est_cost_usd` field), unlinked to the ledger.

## Requirement 10 — Context and memory governance

- **Partial infrastructure exists, but not the proposal's full 7-way split**
  (stable preferences / canonical artifacts / lifecycle state / bounded task
  context / failure-rule registry / receipts / ephemeral conversation).
  `renmark/context.py` implements a `ContextKind` enum (`:95`) plus
  `load_skill_body` (`:284`), `load_fragment` (`:297`), and
  `assert_metadata_only` (`:333`) — real, working static/dynamic separation
  for skill bodies specifically (dispatch packets carry metadata pointers,
  never full skill text — matches CLAUDE.md's own citation). It does not
  implement a failure-rule-registry category (Req 7 is entirely missing, see
  above) or a distinct receipts category (ledger.py's 4 kinds are the closest
  analog, unlinked to this module).
- `renmark/memory.py` implements the append-only memory logs
  (`log_feature`, `log_bug`, `log_decision`, `append_routing`,
  `append_learning`, `log_escalation_decision`) plus `dedupe_memory_log`
  (`:547`) and `age_out_memory_log` (`:612`) — covers "receipts/historical
  evidence" and "stable preferences" loosely, but with no schema separating
  the proposal's named categories.
- `renmark/hygiene.py` provides GC/pruning (`prune_memory:587`,
  `scan_artifacts:488`) and `validate_registry_compliance` (`:420`), which
  checks artifact-metadata *presence* (matching the "one canonical artifact
  per purpose" rule) but not content correctness.
- **Checkpoint-before-compaction is real, not just documented**:
  `renmark/lifecycle/preamble.py:205` emits the literal `CONTEXT_GATE_CLEAR:`
  prefix on an interactive cross-domain transition when
  `host_capabilities.supports_clear` (from `capabilities_for(...)`,
  `preamble.py:159`); headless sessions bypass via `preamble.py:183-199`
  (checks `config.is_headless`, records the invocation, skips the gate);
  unsupported hosts (Codex) bypass via `preamble.py:176-180`
  (`if not host_capabilities.supports_clear: verdict = None`). The
  compact-gate branch (advisory-only, bypasses `finish`/`approve`/`resume`)
  begins `preamble.py:223`. `renmark/config.py:216,233`
  (`compact_gate_tokens`/`set_compact_gate_tokens`) and
  `renmark/cli/_dispatch_flags.py:389-391` wire `--compact-checkpoint` →
  `_lifecycle.persist_compact_checkpoint` → `.renmark/state/compact_checkpoint.json`
  (file confirmed present in live state dir). This is a solid, already-shipped
  implementation of the proposal's "checkpoint before compaction" requirement.
- Live `.renmark/state/` contents observed: `program.json`, `delivery.json`,
  `delivery-archive.json`, `agency.json`, `mode.json`, `tasks.json`,
  `usage.jsonl`, `recurrences.json`, `compact_checkpoint.json`,
  `last-skill.json` — note there is **no single `pipeline.json`** at HEAD
  despite CLAUDE.md referencing that name; live state has fragmented into
  `program.json`/`delivery.json` instead. Worth flagging as a doc/reality
  drift item for a later stage, independent of this proposal.

## Requirement 11 — Durable events, receipts, recovery

- `renmark/ledger.py` supports exactly **4 event kinds**: `KIND_WORK_ORDER`,
  `KIND_WORK_RESULT`, `KIND_INSPECTION_REPORT`, `KIND_ESCALATION`
  (`ledger.py:74-83`), append-only, schema-validated
  (`_KIND_BY_TYPE`/`_VALIDATORS_BY_KIND` maps at `:168-274`). This is R-0.3's
  intentionally-narrow scope (per closeout: "blueprint/milestone-contract/
  closeout schemas, hashing, snapshot/restore, migration adapters deferred").
  **No finer-grained lifecycle events** (dispatch queued/started/
  checkpointed/timed-out/cancelled, Owner-decision-recorded,
  integration-completed) exist as ledger kinds today — those live only as
  prose-level lifecycle-stage transitions in `renmark/lifecycle/stage.py`.
- **Ledger event fields vs. proposal requirements (field-by-field)**: `ts`
  (timestamp) is present and required on every kind (`ledger.py:304-305`);
  `kind` stands in for event-type but there is no `schema_version` field on
  any dataclass; `WorkOrder`/`WorkResult` carry `order_id` only — no
  `attempt_id`, no `correlation_id` anywhere in the file; no
  prior/resulting-state fields on any kind; `WorkOrder.role` is the only
  actor/role field (`WorkResult`/`InspectionReport`/`Escalation` carry only
  `dispatch_identity`, i.e. who dispatched, not a role); evidence references
  are partial (`WorkResult.artifact_refs`, `InspectionReport.findings`) with
  none on `Escalation`; **idempotency info is absent entirely**.
- **`renmark/state/pause.py`** (`usage_limit_pause:42`, `write_pause:84`,
  `read_pause:124`, `clear_pause:148`) is real and exercised (see
  `.renmark/memory/learnings.md` 2026-06-26 P10 headless-contract entry), but
  is scoped to **usage-limit rate-limit pause only**, not a general
  work-order pause/cancel/resume. `renmark/heartbeat.py` +
  `renmark/heartbeat_checks.py:29` (`check_usage_limit_pause`) poll for when
  that specific pause clears (`auto_resume` at `heartbeat.py:78`) — same
  narrow scope.
- **No orphaned-dispatch detection exists.** All `orphan`-matching hits in
  the repo concern orphaned git branches (`backlog.py`) or orphaned markdown
  markers (`init.py`, `lint.py`) — unrelated to dispatch recovery. **No
  retry-with-backoff for dispatch attempts exists** (only the usage-pause
  backoff above). The closest thing to "no duplicate integration after
  restart" is `renmark/cli/_run_lifecycle.py:42` (`_setup_resume_state`) plus
  the plan-task skip-list cross-check (`_cross_check_skip_list`, referenced
  in CLAUDE.md) — prevents re-dispatching already-completed *plan tasks* by
  stable index, which is not a general correlation/idempotency mechanism.
- `renmark/analytics.py` (`record_event`, `record_task_run`,
  `record_feature_run`, `record_loop_run`, `close_feature_disposition`) is a
  separate, JSONL-based event/aggregation layer from the ledger — two
  parallel "durable record" systems (ledger.py for R-0.3 receipts, analytics
  for REQ-15 metrics) that don't appear unified.

## Requirement 13 — Metrics and outcome guardrails

- `renmark/analytics.py` aggregators (`_agg_features`, `_agg_tasks`,
  `_agg_loops`, `_agg_events`, `_agg_usage`) cover feature/task/loop
  success-rate and usage — a genuine existing baseline surface
  (`/renmark:analytics` command). **None of the proposal's specific guardrail
  metrics exist today**: no false-pass/reopen rate, no scope-violation rate
  (unsurprising, since scope enforcement itself is unwired per Req 1/2), no
  Owner-interruptions-per-milestone, no percentage-of-dispatches-with-
  unknown-usage, no duplicate-artifact rate. These would need new aggregation
  logic, though the JSONL substrate to build it on already exists and is
  reusable (matches the proposal's "reuse existing JSONL/analytics paths"
  recommended default).

## Requirement 12 — `/renmark:rethink` itself

Out of scope for this survey pass (self-referential — this very pipeline run
is exercising it). Note for Stage 2+: this rethink run is itself evidence of
current `/renmark:rethink` capability — it already does audit → (this
survey) → external benchmark → PRD-acceptance-map → modularity-assessment →
blueprint → roadmap staging per the sibling `renmark-architecture` rethink's
completed artifact set (see `.renmark/rethink/renmark-architecture/` for the
existing stage shape this pipeline already produces). Whether it currently
does independent-Inspector challenge of its OWN roadmap before the Owner gate
(proposal requirement 12.8) needs a direct read of the rethink pipeline's
skill body at Stage 2/4, not done here.

## Cross-cutting notes

- **`.renmark/memory/bugs.md`/`learnings.md` recurring themes relevant to
  this proposal** (384 + 225 lines, distilled not pasted): (1) pipeline-entry
  skills that establish a new work unit have previously failed to persist
  *identity*, not just stage, at entry — downstream stages then silently
  inherited stale state (direct relevance to Req 1/Req 3 — work-order
  identity, task-tracker accuracy); (2) a cluster of 3 related P8 judge/eval
  incidents — "judge silent-pass on bad confidence," "`--accept` cannot
  record from CLI," "replay does not test current behavior" — exactly the
  kind of prior-incident evidence the proposal's failure-rule registry (Req
  7) says should seed real rules instead of CLAUDE.md prose (direct
  relevance to Req 6 and Req 8); (3) a persisted config flag that was
  documented but not runtime-enforced (P11) — the same "prompt-only vs.
  enforced" gap class the proposal flags for capability envelopes (Req 2);
  (4) UI/state-sync bugs (hand-off picker not re-rendered on continuation,
  roadmap staleness guard unclearable after non-structural commits) —
  relevant to Req 3's "reconcile native UI state with Renmark state, Renmark
  authoritative" requirement, which currently has no reconciliation code
  (one-way writes only, confirmed in Req 3 above); (5) Loop-driver
  budget/retry gaps (stalled on first failed verify, could overshoot
  budget) — relevant to Req 9/Req 11's bounded-retry requirements; (6)
  deterministic-classifier false negatives (modularity analyzer, sizing
  classifier, plan parser) — relevant to Req 5's reliance on deterministic
  signals for risk tiering. No theme in either file duplicates the R-0.2
  F1–F5 residuals beyond what `.bootstrap-renmark`'s milestone INDEX already
  tracks.
- **Two "judge" systems, two "receipt" systems, two "event" systems** already
  coexist (Req 6, Req 11) without a stated reconciliation — a real
  consolidation risk the roadmap stage should flag explicitly, per the
  proposal's own instruction to consolidate rather than duplicate.
- **F1 (scope enforcement has no production caller) is the single most
  load-bearing finding in this survey** — it blocks a real claim of
  Requirement 1 and Requirement 2 "pre-action enforcement" both, and touches
  Requirement 8 test cases 1/2/5 (fast-path/scope tests) directly. It should
  be Release B's first task per the proposal's own Release B ("route every
  dispatch path through common validation... preserve fast-path behavior").
- No destabilizing surprises: no TODO/FIXME debt, test suite is green
  (1970 passed / 31 skipped), matching the "healthy repo, governance-shaped
  gap" picture the proposal's own baseline section predicts.

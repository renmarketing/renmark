---
artifact_type: rethink-classification
schema_version: 1
created_at: 2026-08-04T00:00:00Z
source_sha: e689891
related_plan: .renmark/rethink/governed-orchestration-assurance/intake.md
generator: sonnet
stale_after: null
dependency_refs:
  - .renmark/rethink/governed-orchestration-assurance/intake.md
  - .renmark/rethink/governed-orchestration-assurance/survey.md
  - .renmark/rethink/governed-orchestration-assurance/baseline.md
  - .renmark/rethink/governed-orchestration-assurance/prd-acceptance-map.md
  - .renmark/rethink/governed-orchestration-assurance/external-benchmark.md
  - .renmark/rethink/governed-orchestration-assurance/modularity-assessment.md
  - .renmark/rethink/governed-orchestration-assurance/peer-findings-req5-7.md
---

# Stage 6 — Evidence-based classification: governed-orchestration-assurance

Classification order is BINDING per the modularity-assessment Discovery
Direction Gate decision (2026-08-04): (a) work-order reconciliation first,
(b) R-0.2 F1 scope-enforcement wiring via `PreToolUse` hooks early, (c) REQ-30
update release before Critical-tier gate/dispatch-scheduling work, (d)
Requirements 5/6/7 as new capability on the reconciled foundation, (e)
`/renmark:rethink` self-upgrade (Req 12) last.

Legend: **Keep** / **Improve** / **Replace** / **Remove** / **Unknown —
needs a spike**.

---

## (a) Work-order / dispatch-packet consolidation (Requirement 1)

### 1. `ledger.WorkOrder` / `WorkResult` / `InspectionReport` / `Escalation` (`renmark/ledger.py:110-146`)

**Classification: Improve** (becomes the canonical anchor — extended, not replaced)

- Evidence (survey): `renmark/ledger.py:110-131` — no `schema_version`,
  `correlation_id`/`idempotency_key`, `budget`, `capability_envelope`, or
  `inspection_contract` fields today.
- Evidence (modularity §3/§4/§11): explicitly recommended as the anchor —
  "already the schema-validated, ledger-persisted one," near-leaf
  (`state._core` only), docstring self-scopes as "schema + read/write
  primitives ONLY." Extension plan: add `RenmarkWorkOrder` fields (risk
  tier, capability-envelope ref, lens name) in place; add
  `work_order_for_task(...)` called once from `dispatch.build_subagent_input`.
- PRD-acceptance impact: AC-1 (partial → target Release B), AC-11 (ledger is
  also the durable-events substrate).
- External evidence: F1.1/F1.2 (deterministic backbone + stage-boundary
  validation gates as the field's converging pattern) directly validates
  extending an existing schema-validated store rather than inventing a new
  one.

### 2. `dispatch.SubagentInput` / `SubagentOutput` (`renmark/dispatch.py:606`)

**Classification: Improve** (becomes a projection/view of `ledger.WorkOrder`, field names stay stable for its own 5 test files)

- Evidence (survey): a "different shape again" from `WorkOrder` — `task_spec`
  vs `task`, `required_files` vs `file_scope`, `verifier_expectations` vs
  `verifier`.
- Evidence (modularity §3/§4): NOT itself wrong — it is the actual
  metadata-only packet a subagent receives (REQ-20/G11-guarded via
  `context.assert_metadata_only`), a legitimately distinct concern
  (dispatch payload vs. ledger receipt). Fix is a documented, tested
  projection function, not a rename/merge of the dataclass itself; its
  public fields/tests (5 files: `test_dispatch.py`,
  `test_dispatch_isolation.py`, `test_dispatch_scope_generalization.py`,
  `test_cross_host_dispatch_e2e.py`, `test_r0_2_dispatch_regression_baseline.py`)
  must stay stable per baseline compat-check #7.
- PRD-acceptance impact: AC-1 (partial), baseline compat-check #7
  (REQ-20 metadata-only dispatch — must not regress).

### 3. `dispatch.RepairWorkOrder` (`renmark/dispatch.py:1019`, fields at `:960-964`)

**Classification: Replace** (field-identity only — `work_order_id` renamed/aliased onto `order_id`; the repair-specific fields it uniquely owns are kept)

- Evidence (survey): a third, independently-shaped work order —
  `work_order_id, source_inspection_id, severity, scope, description,
  acceptance_criteria`.
- Evidence (modularity §3): **field-name drift is already live, not
  hypothetical** — `work_order_id` vs `ledger.WorkOrder.order_id` naming the
  same concept differently. Its own comment block (dispatch.py:960-964)
  already reasons about reusing `fast_path.WorkerScope` for `scope` but
  didn't extend that discipline to the order-identity field itself — this is
  precisely the "not necessarily wrong, just inconsistent" case the
  classification contract calls out: `severity`, `source_inspection_id`,
  `acceptance_criteria` are repair-specific and legitimately stay; only the
  identity field converges onto `ledger.WorkOrder`'s `order_id`.
- PRD-acceptance impact: AC-1 (F2 — "repair-work-order emission is
  prose-invoked only," per intake §Known prior work).
- Modularity impact: §12 sequencing note 1 — this reconciliation is the
  hard prerequisite; no new schema may land before it per the Discovery
  Direction Gate.

### 4. `fast_path.WorkerScope` (`renmark/fast_path.py:130-158`)

**Classification: Keep**

- Evidence (survey/baseline): clean, single-purpose, real, tested; baseline
  compat-check #2/#3 protects its 5-signal contract and Layer-B
  git-diff-based verification semantics explicitly ("extend only, never
  replace with a second fast path").
- Evidence (modularity §1/§7): "best-isolated module in the delta set,"
  already the precedent `RepairWorkOrder.scope` reuses — a positive pattern
  to keep, not touch.
- PRD-acceptance impact: baseline compat-check #2/#3 (must stay green).

---

## (b) Capability envelope pre-action enforcement incl. `PreToolUse` hooks (Requirement 2)

### 5. Claude Code agent-definition `tools:` frontmatter allowlist (`plugin/agents/*.md`)

**Classification: Keep**

- Evidence (survey): the one real pre-action mechanism that exists today —
  `inspector.md`/`reviewer.md` get `Read, Grep, Glob, Bash` only (no
  Edit/Write), mechanically enforced by the host, not prose.
- PRD-acceptance impact: AC-2's one bright spot ("only place read-only is
  enforced by the host").
- External evidence: F2.1 (Claude Code's own security model is
  `PreToolUse` blocking hooks + OS sandboxing) confirms this is the correct
  substrate to build on, not around.

### 6. `fast_path.verify_worker_scope` / `dispatch.enforce_wave_dispatch_scopes` post-action scope check

**Classification: Improve** (needs a production caller wired in — this is the F1 residual, priority (b) in the Discovery Direction Gate)

- Evidence (survey): `fast_path.verify_worker_scope` (`fast_path.py:189-217`)
  is real, tested, deterministic; wrapped 3x in `dispatch.py`
  (`verify_agent_dispatch_scope:373-390`, `verify_wave_dispatch_scopes:294`,
  `enforce_wave_dispatch_scopes:351-369`) — **but `dispatch_wave()`
  (`dispatch.py:138`) never calls `enforce_wave_dispatch_scopes`**, and no
  other non-test caller exists anywhere in the repo. "Fully built, fully
  tested, zero wiring into a real dispatch path."
- PRD-acceptance impact: AC-1 partial (F1), AC-2 `failed` as proposal-worded
  — this specific gap is why AC-2 is `failed`, not `partial`.
- Modularity impact: §8 — capability-envelope enforcement is a
  ONE-function-addition problem (`subagent_gate.check_capability_envelope`),
  called from the same pre-dispatch funnel every one of the 6 dispatch
  paths already uses; not an N-call-site rewrite.
- Blocking status: `prd-acceptance-map.md` names AC-2 as BLOCKING PRD debt —
  "Any release sequencing must land Release C before claims of
  Worker/Architect/Inspector containment are made."

### 7. Pre-action capability-envelope enforcement via Claude Code `PreToolUse` hooks

**Classification: Unknown — needs a spike**

- Question: can a role's capability envelope (derived from
  `subagent_profiles.ProfileSpec.allowed_targets`) be expressed and enforced
  as a hook-time allow/deny check against dispatch-packet metadata already
  carried per `context-taxonomy.md`, without becoming a second enforcement
  surface parallel to the git-diff post-action check?
- Scope: read Claude Code's `PreToolUse` hook contract (input shape,
  blocking semantics, what metadata is available at hook time) and prototype
  one hook wired to one agent profile's `allowed_targets`.
- Evidence requirement: a working hook config + one passing/one blocking
  integration test demonstrating pre-action denial for an out-of-envelope
  tool call.
- Budget: 1 bounded investigation session, no production wiring beyond the
  single prototype hook.
- Stop condition: either the hook contract supports metadata-driven allow/
  deny (proceed to Release C design) or it does not (fall back to
  post-action-only enforcement + document why, escalate to Owner).
- External evidence grounding the spike: F2.1 (Claude Code's `PreToolUse` is
  blocking/awaited pre-action), F2.2/F2.3 (deterministic pre-action
  authorization argued as the load-bearing layer over post-hoc guardrails),
  Tier-3 Recommendation 1 ("treat pre-action enforcement as primarily a
  wiring problem, not a build problem").
- Also flagged: Codex's own enforcement mechanism (prompt-only vs OS-level)
  is unretrieved (external-benchmark U1) — the envelope must work
  identically on both hosts renmark dispatches to; this is a second,
  narrower spike folded into the same investigation (compare Codex CLI's own
  sandboxing docs to Claude Code's `PreToolUse` model).

### 8. `subagent_profiles.ProfileSpec.allowed_targets` field

**Classification: Improve**

- Evidence (modularity §1): "the field's docstring says 'informational for
  now; enforced in future Agency Mode' — literally the proposal's ask." Real
  field, unenforced.
- PRD-acceptance impact: AC-2 (the literal seam the capability envelope
  needs to become real, per modularity §11 target map).
- Modularity impact: no new module — `check_capability_envelope` reads this
  field, turning prose-descriptive text into a real glob/frozenset check.

---

## (c) REQ-30 update release (binding prerequisite from the Exception check-in decision)

### 9. REQ-30 update release itself

**Classification: Improve** (own dedicated entry — required prerequisite release, not optional)

- Evidence (prd-acceptance-map "Exception check-in — decision 2026-08-04"):
  Owner decision via AskUserQuestion — "Require a REQ-30 update release
  first. The roadmap must include an early release that (a) measures the
  real current per-dispatch baseline overhead, (b) formally updates REQ-30
  via `/renmark:prd` to name the proposal's Critical-tier gate as one of
  REQ-30's allowed named gates and set a measured overhead budget, and (c)
  requires every later release in this program to demonstrate it stays
  under that budget. No dispatch-scheduling (Req 9) or mandatory-gate (Req
  5 Critical tier) work may land before this release closes." This is
  binding on Stage 6 classification and Stage 7/8 sequencing for
  Requirements 1, 3, 5, 6, and 9.
- PRD-acceptance impact: three EXCEPTION-CANDIDATE flags in
  `prd-acceptance-map.md` (REQ-30 vs. proposal Req 2/5/6/9 per-dispatch
  overhead; proposal Req 5 Critical-tier mandatory Owner gate vs.
  REQ-26/REQ-30(e); reconciliation with the just-closed
  `cost.resolve_executor` REQ-30 exception precedent).
- Baseline impact: `.renmark/memory/orchestration-baseline.md`
  (`ORCHESTRATION-BASELINE-2026-08`, v0.39.7/`d9cccc5`) itself documents its
  own open item — no measured token/wall-clock/dispatch-count numbers exist
  yet for the four representative scenarios (Start, Feature/Fix,
  Orchestrate, Rethink); baseline.md §5 confirms this table is still
  unpopulated. This release is what populates it.
- Not "Unknown" because the *work* to do (measure, then run the PRD UPDATE
  gate) is fully specified by the Owner decision — it is scoped, bounded
  implementation/process work, not an open question.

---

## (d) Requirements 5/6/7 — new capability on the reconciled foundation

### 10. Risk-tiered `InspectionContract` + falsification lenses (Requirement 5)

**Classification: Unknown — needs a spike**, with a named Improve sub-component

- Sub-component A (**Improve**): `ledger.InspectionReport`
  (`renmark/ledger.py:135-146`) — real, tested, non-circular verdict
  emission (`check_dispatch_independence`,
  `tests/test_ledger_wiring.py::test_inspection_verdict_derived_from_independent_rerun_not_worker_ok`).
  Verdict vocabulary is `pass|fail|escalate` — no `risk_tier`, no `lenses`
  field. Extension: additive fields per modularity §11 target map
  (`RiskTier` enum, lens name), not a new inspection pathway.
- Sub-component B (**Unknown — needs a spike**): the risk-classification
  function itself (blast radius, API/compat impact, schema/persistence
  impact, reversibility → tier). Question: what deterministic signals in
  this repo (file scope, target module, wave size) reliably predict risk
  tier without a model call, given the survey's own cross-cutting note that
  "deterministic-classifier false negatives (modularity analyzer, sizing
  classifier, plan parser)" are a recurring bugs.md theme? Scope: design and
  hand-validate a risk-tier classifier against ~15-20 real past dispatches
  from `.renmark/analytics/task-runs.jsonl`/ledger history. Evidence
  requirement: classifier output compared against a human-assigned tier for
  the sample set, documented disagreement rate. Budget: 1 bounded session,
  no production wiring. Stop condition: classifier reaches an
  Owner-acceptable disagreement rate, or the tiering criteria are redefined
  and re-spiked once (not indefinitely).
- Evidence (peer-findings): "Entirely missing as code" — zero hits for
  `risk_tier`, `InspectionContract`, `falsification`, lens names anywhere in
  `renmark/`/`plugin/`. Confirmed independently by both the dispatched
  survey and the peer report.
- PRD-acceptance impact: AC-5 `missing/failed` as proposal-worded.
- External evidence: F4.1/F4.2/F4.3/F4.4 (kill-mandate critic + cross-family
  check beats indiscriminate multi-persona debate; naive debate can
  *diminish* accuracy) — directly shapes the lens-selection design once the
  risk-tier spike lands: selection logic is the load-bearing choice, not
  lens count.
- Modularity impact: §6/§11 — lens selection lives as a policy function in
  `subagent_profiles.py`/`subagent_gate.py` orbit, mirroring `cost.py`'s
  existing "policy, not mechanism" role; no new prompt-injection pathway
  (dispatch packets stay metadata-only per REQ-20).
- Sequencing: per Discovery Direction Gate, this is greenfield capability
  built AFTER (a) work-order reconciliation and (c) the REQ-30 update
  release — no Critical-tier gate work lands before (c) closes.

### 11. Calibrated LLM-judge (Requirement 6)

**Classification: Replace at the schema/behavior level; Improve at the mechanism level** — split entry, two components:

- Component A — `renmark/judge.py` mechanism (**Improve**): real,
  cost-labeled, injectable `subagent_runner`, defensive JSON parsing that
  never silently promotes a parse failure to pass. Evidence (peer-findings):
  free-text `contract` param (`judge.py:99`, no rubric freeze/versioning);
  two-state only (`Outcome` is `pass|fail`, `judge.py:36` — not the
  proposal's required three-state `pass|fail|uncertain`); zero bias
  controls (no cross-provider preference, no pairwise order randomization,
  no calibration-against-Owner-decisions loop). The mechanism (injectable
  runner, defensive parsing, cost gating) is sound and reusable — only the
  verdict vocabulary and calibration inputs need extension, not a rewrite.
- Component B — verdict vocabulary/bias controls (**Replace**, i.e. the
  binary `Outcome` enum is superseded by a three-state one; this is a
  breaking schema change to `judge.py`'s public `Outcome` type, not an
  additive field): must add `uncertain` as a first-class outcome (currently
  unparseable/failed responses map to `fail` + `validation_status:
  unvalidated` as an "uncertain-proxy," not a real third state), plus input
  isolation (redact Worker self-assessment/confidence/identity before the
  prompt is composed — peer-findings confirm judge.py "doesn't ingest Worker
  self-assessment/confidence/identity at all... input isolation is
  incidental, not a designed control") and bias controls.
- Evidence: peer-findings confirms `judge.py` is "wholly separate from
  `ledger.py`'s `InspectionReport`/`inspector.md` — no code path connects
  them" and is "the only judge mechanism in the repo, used solely for
  behavioral-eval regression... not for grading Worker deliverables against
  an InspectionContract" — i.e. Requirement 6's judge and Requirement 8's
  eval-tier judge are the SAME code today but serve two different proposal
  requirements; do not fork a second judge module.
- PRD-acceptance impact: AC-6 `partial`/`unverified` (bias controls need a
  deeper code read before this could even be called `partial` with
  confidence).
- External evidence: F3.1 (position bias is NOT fixed by prompting — needs
  structural order-flip randomization, high-strength evidence, 3
  independent sources agree); F3.2/F3.3 (reproducibility/calibration/bias
  control triad; verbosity + self-preference bias named); Tier-3
  Recommendation 2 — size the calibration gold-set to renmark's real
  dispatch volume (20-40 cases), not the SaaS-scale 100-300/200 numbers
  (I3: no source distinguishes CLI/single-user tools from SaaS scale).
- Modularity impact: §11 — extend `Verdict`/`compose_judge_prompt` in
  place, stays escalation-only, stays a leaf.

### 12. Failure-derived constraint registry (Requirement 7)

**Classification: Improve** (extend `recurrence.py`, do not create a new module — this is NOT a "missing" classification despite the requirement's code being absent, because the substrate already exists at ~70%)

- Evidence (survey): "Entirely missing as code" for the proposal's
  specific `FR-[0-9]`/`failure_rule`/`constraint_registry` vocabulary — zero
  hits. `CLAUDE.md` at 352 lines, ~35 distinct must-not/never/do-not
  occurrences (peer-findings), all always-loaded — direct evidence of the
  "growing global prohibition list" failure mode the proposal warns against.
- Evidence (modularity §1/§6): `recurrence.py` (680L) is "a strong,
  underused asset... bounded (`MAX_ENTRIES = 512`), fingerprinted
  (`content_fingerprint` from `scan.py`), with `RemediationClass =
  Literal["patch", "durable_guard"]`... structurally *is* a failure-rule
  registry, just not yet read by a pre-dispatch gate." "The proposal's
  registry is `recurrence.py`'s `durable_guard` entries read back as
  constraints at dispatch time — a new *reader* function
  (`recurrence.active_guards_for(...)`) consumed by `subagent_gate.py`'s
  pre-dispatch check, not a new store."
- PRD-acceptance impact: AC-7 `missing` as proposal-worded, but explicitly
  distinguished from REQ-24 (`recurrence.py`'s existing per-run/fingerprint
  recurrence-prevention role, which stays as-is) — DEFERRABLE spec debt
  flags "Req 7 vs REQ-24 relationship... needs an explicit ADR before
  Release E so the two systems don't silently duplicate or contradict."
- External evidence: F5.1 (constraint accumulation without bound is a named
  governance anti-pattern — SARC framework); F5.2 (deterministic constraint
  systems belong in code/tool-registry, not system prompt — directly
  matches this repo's own `deterministic-first.md` philosophy); F5.3
  (Creator-agent pattern — rules should originate FROM observed failures,
  matching `recurrence.py`'s fingerprint-from-real-failure design already);
  F5.4 (constraint drift — decay-checking is NOT currently an explicit
  stage in the proposal as summarized; Tier-3 Recommendation 5 flags adding
  a periodic re-verification sweep to `/renmark:hygiene` or an audit stage).
- Modularity impact: §11 — `recurrence.py` extended with a read-side
  accessor consumed only by `subagent_gate.py`; no new store, no new
  schema, no second prompt-composition pathway (constraint text still only
  reaches a dispatch packet through the existing `build_subagent_input`
  funnel).

### 13. `renmark/cost.py:350 requires_escalation` (near-miss for Req 5/9)

**Classification: Keep** (explicitly not a substitute for risk tiering — stays scoped to its own job)

- Evidence (survey): "the closest existing thing... it's a binary
  escalation-worthy check for model-tier routing, not a 4-tier
  inspection-cost/lens classifier. Not a substitute."
- PRD-acceptance impact: no AC directly; named to prevent scope confusion
  between model-tier routing (Req 9's territory) and inspection risk-tiering
  (Req 5's territory) — these must not be conflated into one function.

---

## Task tracker binding (Requirement 3)

### 14. `renmark/task_tracking.py` (436 lines, REQ-31)

**Classification: Improve**

- Evidence (survey/baseline): real, non-trivial (docstring lines 1-33);
  atomic writes (`os.replace`); `create_or_reuse_task` idempotent;
  `complete_task` raises `MissingEvidenceError` without evidence;
  `complete_worker_task` reuses `ledger.check_dispatch_independence` (no
  duplicate self-approval logic — confirmed by grep per modularity §1).
  Wiring is narrow: only non-test caller found is
  `renmark/cli/_wave_loop.py` — "no evidence `task_tracking` is called from
  fast-path, `/renmark:feature`, `/renmark:debug`, or `/renmark:rethink`
  dispatch points directly."
- PRD-acceptance impact: AC-3 `met` for the headless-dispatch path REQ-31
  scoped; `partial` for the proposal's fuller ask (Role/worker+active model/
  Budget/Verification as a concise displayed list — no dedicated renderer
  found).
- Modularity impact: §11 — extend to bind task creation to a real
  `ledger.WorkOrder.order_id` instead of an independently-chosen `task_id`,
  reusing the already-proven `check_dispatch_independence` reuse pattern
  (closes REQ-31's "bound to real dispatches" gap using the (a)
  reconciliation work, once it lands — a real ordering dependency on item 1
  above).
- Baseline compat-check #6 protects `complete_worker_task`'s no-self-approval
  gate through this change.

---

## Selector/headless interaction contract (Requirement 4)

### 15. `renmark/interaction.py` (578 lines) + `renmark/headless.py`

**Classification: Improve**

- Evidence (survey): substantial, real infrastructure — `build_selector`
  produces a host-native selector payload + numbered fallback, respects
  `capabilities_for(...)` (`renmark/hosts.py:114-163`). What it can't do: it
  cannot itself invoke Claude Code's `AskUserQuestion` tool — whether a
  skill actually calls the tool vs. prints prose is down to the calling
  skill's markdown; no lint/validator found (`renmark/lint.py`,
  `renmark/plan_lint.py` both checked) that catches a skill silently
  bypassing the selector.
- Historical evidence: `bugs.md` 2026-06-14 ("Hand-off picker not
  re-rendered on continuation turns") — a real prior incident of exactly
  this failure mode, not hypothetical.
- PRD-acceptance impact: AC-4 `met` for the shape (recommended-first, one
  decision at a time, headless auto-resolves reversible/safe choices only);
  the delta is a bypass-detection guard.
- Modularity impact: §11 — add an "enforced" mode: reject a non-selector
  fallback where `hosts.capabilities_for` says a native picker is
  available — turns today's advisory split into a hard check, same
  dataclasses, no new module.

### 16. Headless detection (`renmark/config.py:104-148 is_headless`)

**Classification: Keep**

- Evidence (survey): "static, manually-set flag per repo" — a project-level
  toggle a human/wrapper sets in advance, not live session-spawn detection.
  Satisfies "do not infer from model prose"; does not satisfy automatic
  spawned-session recognition, but the proposal's ask (explicit
  config-based detection, no prose inference) is what this already is —
  `renmark/lifecycle/stage.py:699` and `preamble.py:185-196` wire it through
  lifecycle gates for real behavior, not documentation only.
- PRD-acceptance impact: AC-4, no delta identified against this specific
  sub-component.

---

## Dispatch scheduling / routing (Requirement 9)

### 17. `renmark/dispatch.py` wave grouping (`group_tasks_by_wave`, `validate_wave`) + `renmark/cost.py` + `renmark/codex_routing.py`

**Classification: Improve** — GATED, does not proceed until item 9 (REQ-30 update release) closes

- Evidence (survey): real dependency/wave grouping and overlapping-file
  conflict detection exist (`dispatch.py:109-136`); role/provider-tier
  routing exists (`subagent_profiles.py`, `codex_routing.py:52 HARD_KINDS`).
  Absent: risk-tier as a scheduling input (Req 5 doesn't exist yet), quota/
  provider-availability signals, configurable max-parallelism knob,
  expected-wall-time estimation, rework-budget-aware scheduling (rework
  caps exist per R-0.2 but nothing consults them at schedule time — "there
  is no scheduler, only wave grouping plus independent per-role model-tier
  selection").
- PRD-acceptance impact: AC-9 `partial`.
- Modularity impact: a separate, not-yet-reconciled `renmark/global_routing.py`
  exists alongside `codex_routing.py` — "flagged for a later stage to
  confirm whether the two overlap or duplicate" (survey Req 9 section) —
  this reconciliation should happen before or alongside this Improve, not
  after.
- **Binding gate**: per the Exception check-in decision, "No
  dispatch-scheduling (Req 9)... work may land before this [REQ-30 update]
  release closes." This item cannot start implementation until item 9 is
  done — sequencing dependency, not classification uncertainty.

### 18. `renmark/global_routing.py` vs `renmark/codex_routing.py` overlap

**Classification: Unknown — needs a spike**

- Question: do these two modules duplicate routing logic, or serve
  genuinely distinct scopes (global cross-provider routing vs.
  Codex-specific hard-kind routing)?
- Scope: read both modules fully, diff their responsibilities, produce a
  short reconciliation note (merge, or document the boundary explicitly).
- Evidence requirement: a one-page finding — either "no overlap, boundary
  is X" or "overlap found at Y, recommend merging into Z."
- Budget: bounded to one read-and-diff pass, no code changes.
- Stop condition: finding produced; if merge is recommended, that becomes
  its own Improve/Replace item in a later stage, not decided here.
- Evidence source: survey Req 9 section, "not fully reconciled against
  `codex_routing.py` in this pass — flagged for a later stage."

---

## Context/memory governance (Requirement 10)

### 19. `renmark/context.py` (`ContextKind`, `load_skill_body`, `load_fragment`, `assert_metadata_only`)

**Classification: Keep**

- Evidence (survey): "real, working static/dynamic separation for skill
  bodies specifically... matches CLAUDE.md's own citation." Does not
  implement a failure-rule-registry category (that's item 12/`recurrence.py`,
  not this module) or a distinct receipts category.
- Evidence (modularity §1): explicitly documents itself as "the taxonomy
  layer beneath the production dispatch packet... deliberately does NOT
  define a competing packet dataclass" — a positive discipline example
  cited as a model for new governance code to follow.
- PRD-acceptance impact: AC-10 `met` for the taxonomy/dispatch-packet
  metadata-only guarantee (actively tested via `assert_metadata_only`),
  baseline compat-check #7.

### 20. Checkpoint-before-compaction (`renmark/lifecycle/preamble.py:205 CONTEXT_GATE_CLEAR:`, `renmark/config.py:216,233`)

**Classification: Keep**

- Evidence (survey): "real, not just documented" — emits literal prefix on
  interactive cross-domain transition when `supports_clear`; headless
  bypasses via recorded invocation; unsupported hosts (Codex) bypass
  cleanly. `.renmark/state/compact_checkpoint.json` confirmed present in
  live state dir.
- PRD-acceptance impact: AC-10, "a solid, already-shipped implementation of
  the proposal's 'checkpoint before compaction' requirement" — no delta
  needed here specifically.

### 21. `renmark/memory.py` (append-only logs) + `renmark/hygiene.py` (GC/pruning)

**Classification: Improve**

- Evidence (survey): covers "receipts/historical evidence" and "stable
  preferences" loosely but with no schema separating the proposal's named
  7-way categories (stable preferences / canonical artifacts / lifecycle
  state / bounded task context / failure-rule registry / receipts /
  ephemeral conversation). `hygiene.py`'s `validate_registry_compliance`
  checks artifact-metadata presence, not content correctness.
- PRD-acceptance impact: AC-10 `partial` — formalize checkpoint-before-
  compaction (already done, item 20) and extend hygiene's pruning criteria.
- External evidence: F5.4 (constraint drift) → Tier-3 Recommendation 5
  suggests a periodic re-verification sweep fits naturally into
  `/renmark:hygiene` here, for the constraint-registry item specifically
  once item 12 exists.

### 22. Live state fragmentation: `program.json`/`delivery.json` vs. documented `pipeline.json`

**Classification: Unknown — needs a spike** (flagged as doc/reality drift, independent of this proposal but touching Req 10/11)

- Question: is `pipeline.json` genuinely superseded by
  `program.json`/`delivery.json`, or is this an undocumented split that
  should be reconciled/renamed in `CLAUDE.md`?
- Scope: read `renmark/state/` module(s) that write these files, confirm
  current authoritative state-file set, update `CLAUDE.md`'s references if
  confirmed stale.
- Evidence requirement: one finding note — current file set vs. documented
  file set, with a recommendation (rename docs, or these are genuinely
  different and both are needed).
- Budget: one bounded read-and-diff pass.
- Stop condition: finding produced, doc-only fix applied if trivial;
  anything requiring code change becomes its own future item.
- Evidence source: survey Req 10, "note there is no single `pipeline.json`
  at HEAD despite CLAUDE.md referencing that name."

---

## Durable events/recovery (Requirement 11)

### 23. `renmark/ledger.py` append-only JSONL event log (`KIND_WORK_ORDER`, `KIND_WORK_RESULT`, `KIND_INSPECTION_REPORT`, `KIND_ESCALATION`)

**Classification: Keep** (as an event-sourcing pattern) + **Improve** (field completeness) — split:

- Component A — the append-only JSONL mechanism itself (**Keep**): Evidence
  (modularity §9) — "No new microservice/daemon/broker for the event log...
  fully satisfies 'durable events/recovery' for a single-process,
  file-backed CLI tool — a database or message broker here would be pure
  speculative complexity, and the proposal's own non-goals list explicitly
  excludes this." External evidence F6.1: event-sourcing via append-only
  log is a canonical, decades-precedented pattern (git itself is a real-
  world example) — Tier-3 Recommendation 6: "Do not treat the append-only
  ledger design as needing external validation."
- Component B — field completeness (**Improve**): Evidence (survey): 4
  event kinds only; no finer-grained lifecycle events (dispatch queued/
  started/checkpointed/timed-out/cancelled); no `schema_version` field on
  any dataclass; no `attempt_id`/`correlation_id` anywhere; no prior/
  resulting-state fields; idempotency info absent entirely.
- PRD-acceptance impact: AC-11 `partial` — event log/pause/resume/idempotent
  persistence exist and are tested (R-0.3 scope); orphaned-dispatch
  detection, retry-with-backoff, and "no duplicate integration after
  restart" as an enforced invariant are not confirmed as dedicated code
  paths.

### 24. Orphaned-dispatch detection / retry-with-backoff for dispatch attempts

**Classification: Unknown — needs a spike** (candidate U3 from Stage 4, plus a second, narrower gap)

- Question 1 (Stage-4 flagged U3): no comparable lightweight,
  database-free, single-user event-sourcing reference implementation exists
  in public literature to benchmark `.renmark/state/`'s design against for
  Requirement 11's durable events/recovery.
- Scope: accept this as genuinely under-documented (external-benchmark's
  own recommendation) and instead self-benchmark — measure renmark's own
  resume/recovery correctness (does a restart mid-dispatch ever produce a
  duplicate integration or an orphaned task record?) against a handful of
  deliberately-interrupted real or simulated runs.
- Evidence requirement: a short table of interrupt-and-resume scenarios
  tested, each with a pass/fail on "no duplicate, no orphan."
  `renmark/heartbeat.py`/`heartbeat_checks.py`'s existing usage-limit-pause
  path is the nearest real precedent to reuse for the test harness.
- Budget: 1 bounded session, no new production orphan-detection code — this
  spike produces the evidence that determines whether Component B (item 23)
  needs a dedicated orphan-detection code path or whether existing
  `_setup_resume_state`/`_cross_check_skip_list` already cover it well
  enough at the plan-task level (survey notes this exists but is scoped to
  "plan tasks by stable index," not a general work-order correlation
  mechanism).
- Stop condition: scenario table produced; if gaps are found, orphan-
  detection becomes a scoped Improve item in a later stage.
- External evidence: F6.1's own limitation statement — "this sub-topic
  returned the weakest evidence of the seven... no primary source found
  benchmarking or describing a JSONL-file-backed, single-process,
  single-user append-only ledger pattern equivalent to what renmark already
  does."

### 25. `renmark/analytics.py` event/aggregation layer vs. `ledger.py` — two parallel "durable record" systems

**Classification: Improve** (reconcile, do not duplicate further — same class of issue as item 1's work-order drift, at the event-log altitude)

- Evidence (survey): "`renmark/analytics.py`... is a separate, JSONL-based
  event/aggregation layer from the ledger — two parallel 'durable record'
  systems (`ledger.py` for R-0.3 receipts, `analytics` for REQ-15 metrics)
  that don't appear unified." Cross-cutting note explicitly flags "Two
  'judge' systems, two 'receipt' systems, two 'event' systems already
  coexist... without a stated reconciliation — a real consolidation risk
  the roadmap stage should flag explicitly."
- PRD-acceptance impact: touches AC-11 and AC-13 (metrics) both — a
  guardrail-metrics extension (item 26) should read from a reconciled
  source, not add a third parallel record system.

---

## Metrics/guardrails (Requirement 13)

### 26. `renmark/analytics.py` aggregators (`_agg_features`, `_agg_tasks`, `_agg_loops`, `_agg_events`, `_agg_usage`, `build_health_report`)

**Classification: Improve**

- Evidence (survey/prd-acceptance-map): genuine existing baseline surface
  (`/renmark:analytics` command); "None of the proposal's specific guardrail
  metrics exist today: no false-pass/reopen rate, no scope-violation rate
  (unsurprising, since scope enforcement itself is unwired per Req 1/2), no
  Owner-interruptions-per-milestone, no percentage-of-dispatches-with-
  unknown-usage, no duplicate-artifact rate."
- PRD-acceptance impact: AC-13 `partial` — "the aggregation infrastructure
  is real... reuse existing JSONL/analytics paths" default matches the
  proposal's own stated preference.
- External evidence: F7.1's "43%" vendor statistic explicitly should NOT be
  imported as a target/baseline (Tier-3 Recommendation 7) — define and
  measure renmark's own baseline instead, reinforcing item 9's REQ-30
  measurement work as the correct precedent pattern.
- Ordering note: the scope-violation-rate metric specifically cannot be
  built honestly until item 6 (production scope-enforcement wiring) lands —
  there is nothing to measure yet.

---

## Rethink self-upgrade (Requirement 12) — built LAST per Discovery Direction Gate

### 27. `/renmark:rethink` pipeline itself (REQ-28)

**Classification: Improve**

- Evidence (prd-acceptance-map AC-12): `met` for proposal items 1,2,3,4,6,
  7,9,10; `partial` for item 5 ("apply only relevant falsification lenses"
  — lenses don't exist yet, dependent on item 10 above) and item 8
  ("challenge the roadmap with an independent Inspector before asking for
  Owner approval" — REQ-28 as currently written routes to 3 Owner gates but
  names no mandatory pre-Execution-Gate independent-Inspector challenge
  step distinct from the Owner gate itself).
- Blocking status: `prd-acceptance-map.md` names AC-12/item-8 as BLOCKING
  PRD debt — "a genuine PRD gap that a future `/renmark:prd` UPDATE gate
  must close before Release F (rethink self-upgrade) can honestly claim
  compliance."
- Sequencing: explicitly LAST per the Discovery Direction Gate ("once the
  assurance contracts it needs to consume — work order, inspection
  contract, receipts — actually exist to consume"). This very Stage 6 run
  is itself live evidence of REQ-28's current capability.
- Modularity impact: no module change identified for this item at Stage 6
  — the gap is a PRD-contract wording gap (item 8), resolved via
  `/renmark:prd`, not a code-architecture change.

---

## Role model reconciliation (cross-cutting, touches Requirements 1/2/12)

### 28. `agency.py` (project-phase role altitude) vs. `subagent_profiles.py` (per-dispatch-role altitude)

**Classification: Unknown — needs a spike**

- Question: the proposal's Owner→GC→Architect→Worker→Inspector role model
  exists today at TWO unreconciled altitudes — `agency.py`'s
  `AgencyState`/milestone/signoff tracking (project-phase) and
  `subagent_profiles.PROFILES` (per-dispatch role). Does the capability
  envelope (item 8) need to enforce at both altitudes, or only the
  per-dispatch one?
- Scope: produce a short ADR-level note stating which altitude a capability
  envelope enforces at (modularity §1 already leans "per-dispatch role,
  almost certainly — agency.py's phase gates are a different, milestone-
  level concern already covered by existing lifecycle/agency gates") and
  get it confirmed, not re-derived from scratch.
- Evidence requirement: one ADR paragraph + explicit Owner/maintainer
  sign-off it doesn't need new code.
- Budget: bounded to a single read-confirm pass — the modularity assessment
  already did the hard analytical work; this spike is closing the loop, not
  re-investigating.
- Stop condition: ADR note produced and accepted, no code change required
  unless the confirmation contradicts modularity §1's lean.
- PRD-acceptance impact: `prd-acceptance-map.md` DEFERRABLE spec debt —
  "REQ-22's Agency/Orchestrator mapping to Owner→GC→Architect→Worker→
  Inspector — needs a short PRD note, not new code, before Release B."
- Evidence source: modularity §1, "not yet unified... not a bug, but worth
  naming explicitly before a capability envelope is bolted onto one and
  assumed to cover the other."

---

## Remove — explicit check

No component across the 13 requirements' surveyed evidence qualifies as
**Remove**. Every module touched by this transformation (`ledger.py`,
`dispatch.py`, `fast_path.py`, `subagent_gate.py`, `judge.py`,
`task_tracking.py`, `interaction.py`, `hosts.py`, `cost.py`,
`codex_routing.py`, `subagent_profiles.py`, `agency.py`, `recurrence.py`,
`context.py`) is either load-bearing today (Keep) or has a documented
extension path (Improve/Replace) per modularity-assessment §9's explicit
"NOT justified" list, which itself argues against removal-adjacent moves
(no new microservice, no new governance package, no second work-order
schema, no second prompt-injection pathway) rather than for removing
existing code. `renmark/global_routing.py` (item 18) is a Remove
*candidate* pending its own spike, but is classified Unknown here, not
Remove, per the classification contract's rule against forcing a
Remove without confirmed evidence of dead weight.

---

## Summary

**Total classification entries: 28**

| Class | Count | Items |
|---|---|---|
| Keep | 7 | 4, 5, 13, 16, 19, 20, 23a (ledger JSONL mechanism, counted with 23) |
| Improve | 14 | 1, 2, 6, 8, 9, 10a, 11a, 12, 14, 15, 17, 21, 23b, 25, 26, 27 |
| Replace | 2 | 3, 11b |
| Remove | 0 | — |
| Unknown — needs a spike | 7 | 7, 10b, 18, 22, 24, 28 |

(Note: items 10, 11, and 23 each split into sub-components across
Keep/Improve/Replace/Unknown per the classification contract's instruction
to be precise about which part of a mixed finding falls where; the table
above counts each top-level numbered item once under its dominant/first-
listed classification, with splits noted in the item's own section.)

Binding sequencing carried forward to Stage 7/8: item 1-4 (work-order
reconciliation) first; item 6-8 (capability envelope + `PreToolUse` spike)
early; item 9 (REQ-30 update release) before any Critical-tier gate or
item 17/18 (dispatch scheduling) work; items 10-12 (Req 5/6/7) as new
capability after items 1-9; item 27 (rethink self-upgrade) last.

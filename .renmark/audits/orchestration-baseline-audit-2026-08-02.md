---
artifact_type: audit
schema_version: 1
created_at: 2026-08-02T00:00:00Z
source_sha: 98ca9798e0f24c512fbf727eb290c673d087c3c5
related_plan: PRD.md#REQ-30
generator: sonnet
stale_after: null
dependency_refs:
  - .renmark/memory/orchestration-baseline.md
  - PRD.md#REQ-30
  - PRD.md#REQ-31
completion_state: complete
confidence: high
validation_status: validated
retry_count: 0
parser_success: true
schema_compliance: true
---

# ORCHESTRATION-BASELINE-2026-08 — audit and measurement report

**Scope: measurement and audit only. No runtime behavior, routing, pipeline, or target-application
code was changed to produce this report.** Pinned reference point: `v0.39.7`, commit `d9cccc5`,
2026-08-02 (per `.renmark/memory/orchestration-baseline.md`). This report is evaluated against
current `HEAD` (`98ca979`, `v0.40.0`), one release after the pin — the pinned commit is unchanged
in the areas audited below, so findings apply to both.

## 1. Does Renmark have a real SDK/launcher that can issue `/compact`/`/clear` and continue?

**No.** Searched for subprocess/`Popen` calls shelling out to a `claude`/`codex` CLI with
compact/clear flags, and for any headless Claude Code SDK usage. `renmark/headless.py` +
`renmark/config.py:104-148` implement a **gate-resolution helper** (auto-picks a safe option or
halts when no live session can answer a question) — this is not the same capability. It does not
drive a live session's context state. `renmark/dispatch.py:934` and `renmark/cost.py:53` contain
only comments noting the Agent-tool/codex-subprocess boundary, not code. The `/compact`/`/clear`
gates documented in CLAUDE.md are **advisory prose presented to a human via `AskUserQuestion`** —
the user runs the host command manually. Confirms the CLAUDE.md framing ("Neither gate claims to
invoke `/compact` or `/clear`") is accurate to the code, not aspirational.

## 2. Is the model-routing table enforced at runtime, or only documented?

**Documented only; not runtime-enforced.**
- `renmark/cost.py:350` `requires_escalation()` is a pure classifier. Its only callers found are
  `tests/test_cost.py:5,57-60` — zero production call sites in `renmark/dispatch.py` or
  `renmark/cli/_engine.py`.
- Dispatch (`renmark/dispatch.py:923` `dispatch_task_isolated`, `:844` `_build_claude_host_calls`)
  reads the `model`/`executor` field already set on the `Task` object (e.g. `:879`
  `arguments["model"]="fable"`, `:913` `native.route.model`) — it never calls `requires_escalation`
  to validate or veto that choice. Whatever set `executor` at plan-authoring time (a human or an
  LLM reading `model-routing.md`) is the actual enforcement mechanism; dispatch just executes it.
- `renmark/subagent_gate.py:396` (`python -m renmark.subagent_gate <plan>`) is a real classifier,
  but its only call sites are `renmark/cli/_engine.py:327,581` (inside `_handle_dry_run`, i.e.
  `renmark-execute --dry-run` preview output) and `plugin/skills/orchestrate/SKILL.md:92,102`
  (documented as a manual cost-preview step). **No hits in `dispatch_task_isolated` or
  `dispatch_wave`** — it does not block or veto a real wave dispatch in code; it only annotates the
  preview surface.
- **Conclusion:** the routing table is convention + LLM/human judgment at plan-authoring time,
  checked by nothing downstream. A plan author who ignores the table produces a plan Renmark will
  execute without complaint.

## 3. When are reviewers/additional workers actually dispatched?

**Manual/per-plan, not automatic per task.** No occurrence of an automatic model-reviewer Agent
dispatch inside `dispatch_wave`/`_run_one`. There *is* deterministic scope verification
(`verify_wave_dispatch_scopes` at `dispatch.py:288`, `verify_agent_dispatch_scope` at `:367`,
delegating to `fast_path.verify_worker_scope`) — but that checks touched-file scope, not code
quality/logic; it is not a "reviewer." The `reviewer` subagent role
(`plugin/skills/.shared/subagent-profiles.md:14`) is invoked by `/renmark:codereview`
(user- or pipeline-triggered) or scheduled as an explicit work package by a plan author per
`.shared/subagent-budget.md`/`project-delivery-contract.md`. It fires when a plan/pipeline stage
schedules it — never unconditionally on every dispatched task, and not strictly gated to
failure-only either; it's a planning decision, not a runtime rule.

## 4. Resume/skip-list claim — verified accurate

`renmark/cli/_engine.py:210-248` `_cross_check_skip_list` cross-checks git-derived "done" indices
against the live plan's task-index set; an index absent from the current plan comes back
`ambiguous` and is re-run, never silently dropped — matches the CLAUDE.md claim. `resume`'s
SKILL.md states "one file read, zero LLM calls"; step 1 is `lifecycle.read_lifecycle(Path('.'))`
(`renmark/lifecycle.py:455`, comment confirms "Zero LLM calls"). This claim holds under code
inspection, unlike claims 1-3 above.

## 5. Which artifacts are canonical, duplicated, obsolete, or stale?

**Canonical (committed, source of truth per CLAUDE.md):** `.renmark/memory/*.md` — `routing.md`,
`analytics.md`, `orchestration-baseline.md`, `project-map.md`, `roadmap.md`, etc.

**Stale relative to today (2026-08-02):**
- `.renmark/memory/analytics.md:2` — `_generated 2026-07-06T19:07:34+00:00_`, **~27 days stale**.
  Meanwhile `.renmark/analytics/task-runs.jsonl` (124 lines) and `.renmark/state/usage.jsonl`
  (231 lines) keep accumulating through today. It was written once, not refreshed on a cadence —
  there is no code that regenerates it automatically.
- `.renmark/memory/routing.md` is genuinely append-only with real dated entries (newest found:
  2026-07-30) — closer to "live" than `analytics.md`, but it's a **manually/skill-appended prose
  ledger**, not derived programmatically from the jsonl telemetry. The two ledgers are independent
  and not cross-validated against each other.

**Duplicated/uncommitted accumulation (from `git status` at session start — 32 untracked files
under `.renmark/{reviews,audits,reports,roadmap}/`):**
- `.renmark/reviews/` has 146 JSON files total, mostly untracked — one-off per-run outputs never
  pruned or committed.
- `.renmark/audits/` has ~35 dated `audit-report-*`/`inventory-*` pairs back to 2026-06-09, with
  near-daily reruns; `audit-report-2026-08-01.json` vs `-08-02.json` differ by essentially one
  field (`inventory_count: 30→31`) — near-duplicate content kept as separate files.
- `.renmark/roadmap/agency-optimization-roadmap.md` (untracked) overlaps in purpose with the
  **committed** `.renmark/memory/roadmap.md` — two roadmap artifacts with unclear precedence.
- These are exactly what `/renmark:hygiene` is built to prune (dry-run by default). This report
  does not run it — recommended as a follow-up action, not executed here.

## 6. Which metrics are unavailable (and why)

| Metric (requested by REQ-30) | Status | Evidence |
|---|---|---|
| Per-run input/output/cache tokens | **Unavailable** | `.renmark/state/usage.jsonl` (231 lines) and `.renmark/analytics/task-runs.jsonl` (124 lines): `tokens_in`/`tokens_out`/`prompt_tokens`/`completion_tokens` are ~0 across nearly all records. `renmark/cli/commands.py:452` has an explicit comment: `"token_count": 0,  # codex CLI doesn't surface this; orchestrator may estimate`. `SubagentOutput.token_count` (`renmark/dispatch.py:514/556`) is a schema slot nothing populates from a real Agent-tool or Codex response. |
| Wall/API time per run | **Unavailable** | `duration_s: 0.0` on every sampled `task-runs.jsonl` record. No code found capturing elapsed time around a dispatch call. |
| Context size (actual conversation tokens) | **Unavailable** | `renmark/state/skills.py:23` `context_budget_hint(tokens)` is a pure lookup over an already-known `tokens: int` — **zero production callers found** anywhere in `renmark/` or `plugin/`. The 100k/120k/150k thresholds in CLAUDE.md are policy constants; nothing feeds them a measured value. Self-reporting by the orchestrating LLM is the only mechanism, and it is inherently approximate. |
| Dispatch count by role/model | **Available** | `task-runs.jsonl` records `executor`/`model` per task (structural, real); `.renmark/analytics/summary.json` aggregates counts. Usable now. |
| Duplicate dispatches / repeated file reads | **Unavailable as a metric** | Dedup *logic* exists (recurrence ledger, `_cross_check_skip_list`) but no instrumentation counts or logs repeated reads/dispatches per run. |
| Owner question/gate count, time-to-first-checkpoint | **Unavailable as a metric** | `events.jsonl` logs `resume`/`release`/`quota` events with timestamps (could derive *some* elapsed time between specific event kinds for a `run_id`), but no field counts `AskUserQuestion` gates or marks "first useful checkpoint." Gates are enforced via `lifecycle.json` state and live `AskUserQuestion` calls, not logged as a countable metric. |
| Verification/completion outcome | **Available** | `task-runs.jsonl` (`verifier_result`, `status`), `summary.json` (pass/fail totals), `.renmark/state/delivery.json` (`approval_status`/`review_status`/`verification_status`). Real and usable today. |
| `summary.json` token totals | **Present but not trustworthy as usage** | `renmark/analytics.py:508` computes `tokens = total_tokens or (tokens_in + tokens_out)` — a faithful sum, not an estimate function. But since the underlying per-task fields are ~0, any nonzero total in `summary.json` reflects only the sparse subset of records that happen to carry a real value (e.g. `record_loop_run`, `analytics.py:349-381`, which takes a caller-supplied `total_tokens` int of **unverified** provenance — itself not confirmed measured vs. guessed at its call site). `est_cost_usd` is a separate field, never cross-derived into the token math. |

## 7. Interaction of "subagent-heavy," ">150k context," and "Renmark plugin"

**Cannot be determined from current evidence — explicitly marked unknown, not estimated.** No
per-run context-size measurement exists (§6: `context_budget_hint` has no real caller), and no
per-run wall-clock/token capture exists (§6) to correlate against subagent-dispatch count. Without
at least one of those two measured series, there is no basis to say whether these three attributes
are additive, overlapping, or causally linked — asserting a percentage or ranking here would be
exactly the "estimate from memory" the goal prohibits. This is the single largest evidence gap
blocking REQ-30's regression-protection rule (15% threshold) from being checkable today.

## 8. Representative scenario capture — mined from recent real runs

No *new* scenarios were run (see reasons at the end of this section). Instead, this section mines
concrete numbers from real, already-completed runs in this repo's own history — real dispatch
counts, real gate timestamps, real wall-clock between checkpoints, real verification outcomes.
Every field is either a measured real value with its evidence path, or explicitly `unknown` — none
are estimated from memory.

### Feature/Fix — `add-rethink-pipeline-skill` (2026-08-02)

Evidence: `.renmark/plans/2026-08-02-add-rethink-pipeline-skill.plan.md`,
`.renmark/analytics/feature-runs.jsonl:13`.

| Field | Value | Source |
|---|---|---|
| Dispatch count by role/model | 10 tasks planned: 1× `opus`/`general-purpose` (Task 1), 9× `haiku` (7× `docs-editor`, 2× `general-purpose`) | plan file lines 45-395, per-task `executor:`/`role:` fields |
| Tokens | Plan's own cost-preview estimate: ~105,040 tokens, ~$0.21 (opus 13,500 + haiku 91,540) — **this is a pre-dispatch estimate, not a measured actual**; no post-run actual-usage figure exists to compare it against (§6) | plan file lines 418-425 |
| Wall/API time | **Unknown** — only a single completion timestamp (`2026-08-02T16:10:51Z`) is recorded; the plan file carries no start timestamp, so elapsed time is not derivable | `feature-runs.jsonl:13` |
| Verification/completion outcome | Completed; full suite `pytest -q` → 1782 passed, 31 skipped, 0 failed; 39 files changed; branch merged-deleted | `feature-runs.jsonl:13` |
| Owner gates | **0 found** in this run's window — no `AskUserQuestion`/gate event logged around 2026-08-02 in `events.jsonl` (only two unrelated `release` events that day) — consistent with `feedback_wp_progression_no_gate` (continue-by-default once scope is set) | `.renmark/analytics/events.jsonl` (2026-08-02 rows) |
| Duplicate dispatch / repeated reads | **Unknown** — not instrumented (§6) | — |

### Orchestrate — M2 milestone work packages (2026-07-30) + R-0.2/R-0.3 milestone cycles (2026-08-01)

Evidence: `.renmark/state/wave-summaries/wave-{0..4}.json`, `.renmark/analytics/task-runs.jsonl`
(2026-07-30 rows), `.renmark/state/delivery.json` `provenance_events`.

| Field | Value | Source |
|---|---|---|
| Dispatch count by role/model | 12 task-run records on 2026-07-30: **11× `codex`, 1× `haiku`** | `task-runs.jsonl`, filtered `ts` startswith `2026-07-30` |
| Verification/completion outcome | 7 PASS / 5 FAIL rows — but the FAILs are **2 tasks (id 2, 4) each retried twice** before passing (06:10 FAIL → 13:01 FAIL → 14:23 PASS), i.e. **2 real duplicate re-dispatches** of the same task, directly visible in the log — a concrete instance of the "duplicate dispatch" metric REQ-30 asks about, this one legitimately caused by prior failures, not redundant work | same rows, `task_id`/`status`/`ts` |
| Wall/API time (checkpoint-to-checkpoint, real timestamps) | `milestone-packaging` 14:50 → `WP-M2-A passed` 16:10 = **80 min**; A→B = **25 min**; B→`milestone-passed` = **20 min** (2026-07-30). Separately, R-0.3: `contract-approved` 2026-08-01 15:45 → `RELEASED` 16:30 = **45 min total**, described in the log itself as "first Renmark milestone to close clean on first pass." R-0.2: `contract-approved` 13:00 → `RELEASED` 15:35 = **2h35m**, with 4 items of tracked follow-up debt (F1/F2/F4/F5) | `delivery.json` `provenance_events` timestamps |
| Per-task token/duration | `total_tokens: 0`, `duration_s: 0.0` on every one of the 12 rows — confirms §6's finding at the per-run level, not just in aggregate | `task-runs.jsonl` 2026-07-30 rows |
| Owner gates | Exactly **2** explicit `(Owner, AskUserQuestion)` milestone-contract-approval events in this stretch of history (R-0.2 2026-08-01T13:00, R-0.3 2026-08-01T15:45) — both logged with that annotation in the provenance event `detail` field itself | `delivery.json` `provenance_events` |
| Path note | `wave-*.json` artifact paths read `/home/uvi/projects/ai-system/...`, not this machine's `/home/renmark/projects/renmark/...` — same project under a different clone/host path at capture time; flagged, not corrected, since it doesn't change the measured values | `.renmark/state/wave-summaries/wave-0.json` |

### Start — no qualifying real run exists

Renmark's own genesis commit (`65a965b`/`2fff288`, **2026-05-12**) predates the earliest telemetry
record in `.renmark/state/usage.jsonl` (**2026-05-28**) by 16 days — the project was scaffolded
before any run-tracking existed. No other `/renmark:start` execution against a fresh project is
recorded anywhere in `.renmark/analytics/`, `.renmark/state/`, or `.renmark/plans/` (all plan files
are Feature/Orchestrate-shaped work on the existing renmark codebase). **Status: unknown, not
estimated** — there is no real Start-scenario run to mine.

### Rethink — no real executions yet (pipeline shipped today)

`grep -rl "rethink" .renmark/analytics/*.jsonl .renmark/state/delivery*.json` returns only
`feature-runs.jsonl:13` — the Feature/Fix run above that **built** the `/renmark:rethink` pipeline
itself. The pipeline merged into `main` at `2026-08-02T16:10:51Z` (same run) and has not yet been
invoked against any project. **Status: unknown, not estimated** — there is no real Rethink-scenario
run to mine; it did not exist as an executable pipeline until this session's own recent history.

### Why no *new* scenarios were run

1. Running a fresh Start or Rethink scenario now spends real tokens and is the kind of "expensive
   multi-model operation" `.shared/cost-preview.md` gates on an explicit go-ahead — which
   `orchestration-baseline.md`'s own "still needs to be captured" note already flags, and this
   audit's directive stops short of authorizing spend.
2. §6 shows the current telemetry path would record `tokens_in/out≈0`, `duration_s=0.0` regardless
   — confirmed again at the per-row level in the Orchestrate table above. Spending tokens on a new
   run today would not produce better numbers than what's mined here; **instrumentation (§9) should
   land before further scenario capture**, new or historical.

## 9. Minimal instrumentation proposal (proposal only — not implemented)

1. **Capture real dispatch usage where it already exists.** Claude Code's own `Agent` tool
   completion already returns a real, measured usage block per subagent dispatch — this session's
   own background-agent notifications included
   `<usage><subagent_tokens>52329</subagent_tokens><tool_uses>12</tool_uses><duration_ms>44206</duration_ms></usage>`
   twice. Wiring whatever writes `task-runs.jsonl`/`usage.jsonl` entries to capture that block
   (instead of leaving `tokens_in`/`tokens_out`/`duration_s` at 0) is a small, already-available
   fix — not new instrumentation, just plumbing an existing signal through.
2. **Codex subprocess:** parse whatever the codex CLI actually emits for token/usage in its
   verbose/JSON output mode if it exists; otherwise record `null`/`"unknown"` instead of `0` —
   `0` currently reads as "zero tokens used," which is misleading vs. "not captured."
3. **Context-size measurement:** no host-exposed API for true context size was found in this repo.
   Smallest viable step: have the orchestrating skill self-report an estimate at defined
   checkpoints and pass it into `context_budget_hint`, explicitly flagged as approximate — this
   does not close the gap, only makes the existing hint function reachable instead of dead code.
4. **Gate/checkpoint counting:** add a `gate` event kind to `events.jsonl` (parallel to the
   existing `resume`/`release`/`quota` kinds) emitted alongside each `AskUserQuestion` call and
   each `lifecycle.json` stage transition, so gate frequency and time-to-first-checkpoint become
   derivable per `run_id` without new files.
5. **Artifact hygiene:** run `/renmark:hygiene` (dry-run first) against the 32 untracked
   `.renmark/{reviews,audits,reports,roadmap}/` files identified in §5, and reconcile
   `.renmark/roadmap/agency-optimization-roadmap.md` against the committed
   `.renmark/memory/roadmap.md`. Proposal only — not run here.

None of the above were implemented; this is a change proposal for Owner review.

## Owner gate

This audit found:
- REQ-30's regression-protection rule (15% token/time threshold) is **currently unmeasurable** —
  the telemetry it depends on doesn't exist yet, confirmed both in aggregate (§6) and at the
  per-row level in real historical runs (§8: every 2026-07-30 Orchestrate task-run row shows
  `total_tokens: 0`, `duration_s: 0.0`).
- The model-routing table and `subagent_gate.py` are **not runtime-enforced** — they inform a
  cost-preview surface and plan-authoring convention only (§2).
- Real mined data (§8) *does* exist for dispatch-count-by-role, verification outcome, and
  checkpoint wall-clock/gate-count — e.g. the Orchestrate M2/R-0.3 runs show real 20-80 minute
  checkpoint-to-checkpoint intervals and exactly 2 Owner `AskUserQuestion` gates across the
  R-0.2/R-0.3 milestone cycle — but Start and Rethink scenarios have **zero qualifying real runs**
  in this repo's history to mine (Start predates telemetry by 16 days; Rethink shipped in this same
  session and has never been invoked).
- `.renmark/memory/analytics.md` is **stale by ~27 days** and not auto-regenerated (§5).
- 32+ uncommitted duplicate/stale artifacts have accumulated under `.renmark/` (§5).

**Recommendation:** accept this as the qualitative-plus-gap-map baseline, and separately approve
(a) the minimal instrumentation in §9 items 1-2 (cheapest, plumbs an already-available signal) as
a prerequisite before spending tokens on representative scenario capture, and (b) a
`/renmark:hygiene --apply` pass on the stale artifacts in §5. Per REQ-30/REQ-31, none of this
proceeds without explicit Owner approval — no orchestration or instrumentation code has been
written.

**No further action is taken until the Owner responds to this gate.**

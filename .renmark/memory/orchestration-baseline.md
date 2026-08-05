---
artifact_type: memory
schema_version: 1
created_at: 2026-08-02
source_sha: d9cccc5
related_plan: PRD.md#REQ-30
generator: prd
---

# Orchestration baseline — `ORCHESTRATION-BASELINE-2026-08`

Canonical reference point for `PRD.md`'s REQ-30 ("Orchestration efficiency
and UX stability is a protected capability"). Named so that "preserve current
behavior" points here, not to a subjective later impression.

**Pinned to:** `v0.39.7`, commit `d9cccc5`, 2026-08-02.

## What this baseline protects (structural guarantees, already enforced)

These are already load-bearing rules in `CLAUDE.md`/`AGENTS.md` and specified
by `PRD.md`'s REQ-2, REQ-5, REQ-20, REQ-21, REQ-22, REQ-24, REQ-27. REQ-30
does not restate them — it makes loosening any of them, silently, a release
blocker:

- Orchestrator-visible output per task capped at **≤5 lines / ≤300 tokens**
  (REQ-5); subagent dispatch packets carry task-local context + required-
  skill *metadata only*, never full skill bodies (REQ-20).
- **Deterministic-first execution**: the 4-question gate (existing state? a
  script? repeated enough to codify? does it actually need AI judgment?)
  runs before any model call or subagent dispatch (REQ-21).
- **One bounded worker per task by default**; parallel/extra dispatch
  requires independent work and a clear time/quality benefit (REQ-21,
  REQ-24); duplicate investigation of an already-answered question is
  prohibited (REQ-24's recurrence ledger).
- **Cheapest-capable-model routing** — Haiku for mechanical work, Codex for
  bounded code/test generation, Sonnet for normal planning/implementation,
  Opus/Fable escalation-only — with a cost preview before spend (REQ-2).
- **Fast path for bounded corrections** — a small fix skips full milestone
  planning and multi-agent orchestration ceremony (REQ-27).
- **Two delivery modes, not more** — Agency and Orchestrator — with routine
  work packages continuing without a stop-and-ask between each one once a
  milestone contract is approved (REQ-22, `feedback_wp_progression_no_gate`
  memory entry).
- **Resumability without replay** — `/renmark:resume` is a single `≤1KB`
  file read, zero LLM calls, and never re-dispatches an already-completed
  task (REQ-3; `_cross_check_skip_list` in `renmark/cli/_engine.py`).

## Audit — 2026-08-02

Full evidence-based gap audit: `.renmark/audits/orchestration-baseline-audit-2026-08-02.md`.
Headline findings: per-run token/wall-clock telemetry is effectively unmeasured (`tokens_in`/
`tokens_out`/`duration_s` are ~0 across `.renmark/state/usage.jsonl` and
`.renmark/analytics/task-runs.jsonl`); `context_budget_hint` has zero production callers; the
model-routing table and `subagent_gate.py` are enforced only at plan-authoring/cost-preview time,
not inside `dispatch_task_isolated`/`dispatch_wave`; `.renmark/memory/analytics.md` is ~27 days
stale. The audit mines real historical runs instead of spending new tokens on fresh scenarios:
Feature/Fix (`add-rethink-pipeline-skill`, 2026-08-02) and Orchestrate (M2 milestone + R-0.2/R-0.3,
2026-07-30/08-01) both have real dispatch-count/verification/gate-timestamp data (audit §8); Start
predates telemetry by 16 days and Rethink has never been invoked, so both are honestly `unknown`,
not estimated. Minimal instrumentation (audit §9) is proposed as a prerequisite to closing the
token/wall-clock gap, pending Owner approval.

**Update on `milestone_context_checkpoint`:** originally flagged by codex codereview as spec
"under-built" — wired at the Agency milestone boundary (`renmark/agency.py`'s
`approve_milestone_for_orchestrator`) but with no way to supply a real signal, making it a dormant
hook. Closed: `approve_milestone_for_orchestrator` and `agency.activate` now both accept an
`estimated_tokens: int | None = None` keyword, threaded straight through to
`milestone_context_checkpoint`. No host-exposed context-size API exists (confirmed by the audit,
still true), so this is the **self-reported-estimate path** the audit named as the other viable
signal source: the live agent driving Agency Mode passes its own self-monitored context estimate —
the same number it already tracks for CLAUDE.md's 60%/80% compact-gate rule — as `estimated_tokens`
when it calls `activate(..., signoff_status="approved", estimated_tokens=<self-reported count>)` at
a genuine milestone approval. Cited in `plugin/skills/.shared/agency-delivery.md`. Proven end-to-end
(not just unit-mocked) in `tests/test_agency.py`: a real `estimated_tokens` crossing the configured
threshold produces a real `context-checkpoint-hint` provenance event and a real
`.renmark/state/compact_checkpoint.json` write; omitting it stays exactly as dormant as before —
never fabricates a trigger. The one remaining gap is genuinely unclosable without new host
capability: nothing here *measures* real context size automatically, it only wires the pipe for a
self-report to travel through.

## What still needs to be captured (this artifact's open item)

This entry pins the *qualitative* baseline and the *mechanism* REQ-30
requires. It does **not** yet contain measured token/wall-clock/dispatch-count
numbers for the four representative scenarios REQ-30 names — capturing those
requires actually running them, which spends real tokens and is exactly the
kind of "expensive multi-model operation" that needs a cost preview and an
explicit go-ahead before it runs (see `.shared/cost-preview.md`), not
something to fabricate into a memory file.

To populate this baseline with real numbers, run each representative scenario
once against this pinned commit and record its metrics here (a dated
`## Scenario capture — <date>` section per run):

| Scenario | Command | What to capture |
|---|---|---|
| Start | `/renmark:start` on a small-to-medium fresh idea | tokens, wall-clock, dispatch count, Owner-gate count, time to first checkpoint |
| Feature / Fix | `/renmark:feature` or `/renmark:debug` on a bounded change | same, plus fast-path vs. full-ceremony routing decision |
| Orchestrate | `/renmark:orchestrate` on a multi-task plan | tokens, dispatch count, repeated-read count, wave-summary sizes |
| Rethink | `/renmark:rethink` on an existing project | tokens, dispatch count per stage, gate count (3 named + any exception check-ins) |

`/renmark:analytics` already aggregates token totals, dispatch counts, and
loop success rate from `.renmark/analytics/*.jsonl` and `.renmark/state/usage.jsonl`
— prefer running it over hand-computing these numbers.

## Scenario capture — 2026-08-04

Populates the four blank rows above with real numbers mined from data already
on disk. **No fresh pipeline was invoked to produce this section** — per this
file's own rule, that remains a distinct future action requiring its own
cost-preview + Owner go-ahead. Two things changed since the 2026-08-02 audit
that this update reflects: (1) `.renmark/analytics/task-runs.jsonl` now
carries real `measured:true` rows (the audit's §9 item-1 instrumentation
proposal appears to have landed via the `orchestration-baseline-controls`
feature, 2026-08-02/03) that the audit itself could not have seen; (2)
`/renmark:rethink` has now genuinely been invoked — this very
`governed-orchestration-assurance` build is a live Rethink execution, so
Rethink is no longer "never invoked," though it is **still incomplete**
(`lifecycle.json` stage: `plan-validated`, `pipeline.json`:
`current_phase: "orchestrate"`, `wave_index: 0/wave_total: 1` as of this
writing) — its numbers below are partial, not a closed-run total.

| Scenario | Tokens | Wall-clock | Dispatch count | Owner-gate count | Notes |
|---|---|---|---|---|---|
| Start | unknown | unknown | unknown | unknown | No qualifying run exists. Genesis commit (`65a965b`/`2fff288`, 2026-05-12) predates the earliest telemetry row in `.renmark/state/usage.jsonl` (2026-05-28) by 16 days. Still true as of 2026-08-04 — no `/renmark:start` run against a fresh project appears anywhere in `.renmark/analytics/` or `.renmark/plans/`. |
| Feature / Fix | Two data points, both real, neither estimated. **(a)** `add-rethink-pipeline-skill` (2026-08-02): plan's own pre-dispatch cost-preview estimate only — ~105,040 tokens (opus 13,500 + haiku 91,540) — no measured actual exists to compare it against. **(b)** `orchestration-baseline-controls` (2026-08-02, merged 2026-08-03): **502,107 measured tokens** summed from 12 `measured:true` rows in `task-runs.jsonl` (haiku 173,631 across 5 dispatches; sonnet 278,389 across 6; opus 50,087 across 1) — this is the first real (not estimated) token figure this baseline file has ever recorded. Plus an unknown number of additional `codex`-executor dispatches logged in `.renmark/ledger/events.jsonl` for the same build (codex doesn't surface tokens — consistent with audit §6, not a new gap). | (a) unknown — no start timestamp recorded, only completion (`2026-08-02T16:10:51Z`). (b) unknown — `duration_s: 0.0` on every row (per-row confirmation of audit §6). | (a) 10 tasks planned: 1 opus + 9 haiku (plan file). (b) 12 measured task-run rows (5 haiku, 6 sonnet, 1 opus) plus ≥6 additional `codex` work-orders visible in `.renmark/ledger/events.jsonl` for the same feature window (2026-08-02T20:34–21:55) — exact combined total not derivable since the two logs aren't cross-linked by a shared run id. | (a) 0 found in `events.jsonl` around 2026-08-02 — consistent with `feedback_wp_progression_no_gate`. (b) not separately checked; same continue-by-default policy applies, no evidence of an added gate. | Both are real historical Feature-pipeline runs on this repo, not fresh spend for this task. |
| Orchestrate | `total_tokens: 0`, `duration_s: 0.0` on all 12 sampled 2026-07-30 rows — unmeasured, not zero-usage (audit §6/§8). | Checkpoint-to-checkpoint, real timestamps: M2 `milestone-packaging`→`WP-M2-A passed` = 80 min; A→B = 25 min; B→`milestone-passed` = 20 min (2026-07-30). R-0.3: `contract-approved`→`RELEASED` = 45 min (2026-08-01, "first Renmark milestone to close clean on first pass"). R-0.2: `contract-approved`→`RELEASED` = 2h35m, 4 items of tracked follow-up debt. | 12 task-run records on 2026-07-30: 11× `codex`, 1× `haiku`. 2 of those (task ids 2, 4) were real duplicate re-dispatches after prior FAILs, not fresh redundant work. | Exactly 2 `(Owner, AskUserQuestion)` milestone-contract-approval events across R-0.2/R-0.3 (2026-08-01T13:00, T15:45), both logged with that annotation in `delivery.json`'s `provenance_events`. | Unchanged from the 2026-08-02 audit — no newer Orchestrate-scenario data found on disk as of 2026-08-04. |
| Rethink | unknown — codex executor doesn't surface tokens (audit §6), and this run is not yet complete. | Partial, real: ledger `work_order`/`work_result`/`inspection_report` triples for this build's orchestrate phase span `2026-08-02T20:34:54Z` → `2026-08-05T01:00:04Z` in `.renmark/ledger/events.jsonl` — not a closed total, the run is still executing. | **Partial, in progress**: 7 `work_order` events, 6 completed `work_result` events (all `status: complete`), 6 `inspection_report` verdicts (all `pass`), 1 `escalation` event (`reason: needs_agent`), all dispatched to `codex`. `pipeline.json` shows `wave_index: 0` of `wave_total: 1` for the current plan — more dispatches are pending. | Not separately counted in the ledger sample reviewed; the rethink pipeline's own Discovery/Solution/Execution gates are tracked in `.renmark/rethink/governed-orchestration-assurance/*.md`, not re-derived here. | **First-ever real Rethink execution** (`/renmark:rethink` had never been invoked as of the 2026-08-02 audit) — but genuinely incomplete. Do not treat this row as a closed-run baseline number; re-check after this build finishes. |

**Provenance.** Sources read: `.renmark/analytics/task-runs.jsonl` (140 rows,
12 with `measured:true`), `.renmark/analytics/events.jsonl` (36 rows),
`.renmark/analytics/summary.json` (generated 2026-07-06, stale — token
totals there are aggregate/untrustworthy per audit §6, not used here in
place of the per-row `measured:true` figures), `.renmark/analytics/feature-runs.jsonl`
(15 rows), `.renmark/ledger/events.jsonl` (20 rows), `.renmark/state/lifecycle.json`,
`.renmark/state/pipeline.json`, and
`.renmark/audits/orchestration-baseline-audit-2026-08-02.md` (source of the
Feature/Fix-(a) and Orchestrate rows, carried forward unchanged). Captured
2026-08-04, no fresh pipeline invocation. **Fresh scenario capture for Start
(still unknown) and a completed Rethink total (currently partial) remains a
distinct future action requiring its own cost-preview + explicit Owner
go-ahead**, per this file's existing rule above — this update does not
authorize or perform that spend.

## Regression rule (REQ-30)

Once populated, any change to orchestration routing, context limits, dispatch
policy, model escalation, Owner-gate frequency, or artifact-reuse behavior
must re-run the same four scenarios and compare against the numbers recorded
here. A release is blocked if it increases median token use or execution
time by more than 15%, adds a routine Owner question/gate beyond each
pipeline's named gates, introduces a duplicate dispatch or repeated completed
work, sends detailed worker context into the orchestrator, or weakens
verification/completion/recovery behavior — unless the Owner grants an
explicit, evidence-backed exception with a documented benefit and a rollback
path.

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

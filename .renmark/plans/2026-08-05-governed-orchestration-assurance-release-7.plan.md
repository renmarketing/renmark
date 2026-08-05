# Plan: governed-orchestration-assurance Release 7 — REQ-30 overhead measurement

**Scope note (binding):** Release 7 has two conceptual parts per
`.renmark/rethink/governed-orchestration-assurance/roadmap.md`'s Release 7
section: (1) measuring real per-dispatch baseline overhead, and (2) formally
amending REQ-30 in `PRD.md` via `/renmark:prd`'s own UPDATE gate. **This plan
covers ONLY part (1).** No task in this plan touches `PRD.md`. The PRD
amendment is a separate, already-existing renmark pipeline
(`/renmark:prd`) with its own human-gated approval flow, invoked by the
orchestrator after this plan's task verifies green, using the numbers this
plan produces as its evidence.

Context: `.renmark/memory/orchestration-baseline.md` already carries a
`## Scenario capture — 2026-08-04` section from Release 1 with real
Feature/Fix numbers (502,107 measured tokens, from the `orchestration-
baseline-controls` feature, a different feature than this transformation)
and a Rethink row recorded as partial/in-progress (7 work_order events,
wave_index 0/1). Since that capture, this very `governed-orchestration-
assurance` transformation has run Releases 2-6 to completion (git log:
`4b29358`..`1d6787b`, 2026-08-05), so the Rethink scenario's real numbers are
now far more complete than Release 1's snapshot. `ORCHESTRATION-BASELINE-
2026-08` is pinned to `v0.39.7`/`d9cccc5` (2026-08-02) — this whole
transformation postdates that pin, so a like-for-like comparison must be
computed explicitly, not assumed. `AGENT_OVERHEAD_TOKENS = 10_000` in both
`renmark/cost.py` and `renmark/roadmap.py` is unchanged since the pin
(confirmed via `git log -p --since=2026-08-02` on both files — no hits), so
the assumed-overhead constant has not drifted; the task below must state
that explicitly rather than re-deriving it from scratch.

### Task 1: Mine and record REQ-30 overhead measurement
- **mode:** B
- **target:** .renmark/memory/orchestration-baseline.md
- **complexity:** hard
- **executor:** sonnet
- **role:** researcher
- **role_reason:** bounded real-data mining (JSONL logs, git log, plan files) plus honest statistical/comparative write-up — reasoning-heavy synthesis over disk-resident evidence, not mechanical file editing and not a good codex/haiku fit.
- **parallel_group:** 1
- **est_tokens:** 3200
- **est_cost_usd:** 0.0396
- **verifier:** grep -q "^## REQ-30 overhead measurement" .renmark/memory/orchestration-baseline.md
- **serves:** REQ-30
- **spec:**
  Append a dated `## REQ-30 overhead measurement — 2026-08-05` section to
  the END of `.renmark/memory/orchestration-baseline.md` (keep all existing
  sections, including `## Scenario capture — 2026-08-04`, unchanged). Do
  not touch `PRD.md` — out of scope for this task. Real disk data only, no
  fabricated/estimated numbers; mark anything not derivable `unknown` with
  the specific reason.

  See `.renmark/plans/refs/2026-08-05-release-7-measurement-notes.md` for
  the exact mining steps and known-real numbers to cross-check against
  (dispatch counts per release plan file, `task-runs.jsonl`/
  `ledger/events.jsonl` queries, `delivery.json` provenance-event check,
  the `AGENT_OVERHEAD_TOKENS` drift check). Cover, per scenario: (1)
  **Rethink** — re-measure this transformation's Releases 1-6 dispatch
  count + executor mix (from plan files), token spend (from
  `task-runs.jsonl`, split measured/unmeasured, noting codex's known
  token-blind gap), ledger-coverage cross-check, and Owner-gate count
  (Stage 9 Execution Gate + zero routine gates since, per
  `delivery.json`); mark as a Releases 1-6 partial total, not closed. (2)
  **Feature/Fix** — check for anything fresher than the existing
  502,107-token `orchestration-baseline-controls` figure; if none, carry
  it forward unchanged with its existing "different feature" caveat. (3)
  **Orchestrate** — check for anything newer than the 2026-08-02 audit; if
  none, carry forward unchanged. (4) **Start** — reconfirm `unknown`.

  Then write an honest overhead-vs-pin paragraph: confirm
  `AGENT_OVERHEAD_TOKENS = 10_000` is unchanged in `cost.py`/`roadmap.py`
  since the `d9cccc5` pin (no drift); state plainly that a full
  like-for-like measured comparison isn't computable (pin predates any
  numeric baseline, codex stays token-blind) — name the gap, don't
  fabricate a percentage; report what partial comparison IS computable;
  end with one recommended overhead-budget line for the REQ-30 PRD
  amendment to cite, grounded only in what the mined data supports.

  Format: match the existing table style. Add a `**Provenance.**` line
  listing files/commands consulted and the capture date. Mine only —
  invoke no pipeline, spend no fresh tokens on a live scenario run.

---

## Cost preview

| Task | Executor | Tokens (incl. overhead) | Cost |
|---|---|---|---|
| 1: Mine and record REQ-30 overhead measurement | sonnet | 3,200 + 10,000 = 13,200 | $0.0396 |

**Total tasks:** 1 (1 parallel group)
**Total tokens (incl. ~10k Agent overhead):** ~13,200
**Total cost:** **$0.0396**
**Executors:** sonnet×1
**PRD.md:** not touched by any task in this plan — the REQ-30 PRD amendment happens via a separate `/renmark:prd` invocation after this task verifies green.

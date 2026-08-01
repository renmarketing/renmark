# R-0.0 Benchmark Budget and Circuit-Breaker Policy

Per `governing-architecture-roadmap.md` §14.2 (3 baseline scenarios) and §9.4 (circuit breakers), Owner Decision 1's evidence requirements, and the Owner's 2026-08-01 budget correction (this document supersedes the original proposed numbers — see "Revision history" at the bottom).

**No benchmark has been executed. This document is a policy for a future WP-5 pass, still gated behind WP-1 through WP-4.**

**Objective, per explicit Owner correction:** these limits measure **subscription quota consumption and orchestration behavior** — not API dollar billing. No USD estimates appear in this document. Token measurements may be estimates when the host doesn't expose exact usage; **call count and elapsed-time limits are authoritative**, not token counts.

## Scenario definitions (working titles — full definitions are WP-3, not yet written)

| Scenario | Shape | Rationale |
|---|---|---|
| A — Small local change | 1–2 file change (e.g. a targeted bug fix) | Cheapest, fastest — validates the harness itself before spending on B/C |
| B — Normal feature | Medium vertical feature (impl + tests, single module) | Represents typical `/renmark:feature` usage |
| C — Architectural feature | Long-horizon multi-module milestone (impl + tests + docs, several files) | Stress case — where orchestration overhead is expected to be worst, per `current-system-audit.md` §Cross-cutting observation 5 |

## Approved budget (per-scenario, ONE execution pass each — not a rerun)

| Scenario | Max model/agent invocations | Max wall-clock | Target context+output total |
|---|---:|---:|---:|
| A — Small local change | 2 | 10 min | 40,000 est. tokens |
| B — Normal feature | 6 | 25 min | 120,000 est. tokens |
| C — Architectural feature | 12 | 45 min | 300,000 est. tokens |

**Hard aggregate limit across all three scenarios, one pass each:**
- **Maximum 20 model/agent invocations total.**
- **Maximum 460,000 estimated tokens total.**
- **No WritingMate or separately-billed API usage.**
- Maximum 80 minutes wall-clock total (per Owner's stated aggregate).

These numbers are the Owner-approved ceiling as of 2026-08-01 — not an estimate to be re-derived.

## Circuit breakers (apply during WP-5 execution)

- **Any per-scenario invocation, wall-clock, or aggregate ceiling breach** → abort the current scenario run immediately, mark it `BLOCKED` in `baseline-report.md` with the partial data captured. **No automatic retry.**
- **Any scenario run exceeds twice its expected call count** → stop immediately, even if the aggregate ceiling has not yet been reached.
- **Any scenario run modifies a file outside its declared benchmark target** → abort immediately; this is itself evidence worth capturing, not just discarding (it's exactly the scope-violation class of problem R-0.1/R-0.2 aim to fix).
- **More than 2 replans in a single benchmark run** → abort-and-log. Do not attempt to complete the benchmark by working around the limit.
- **Record partial evidence from every aborted run** — an aborted run is still a data point, not a discarded attempt.

## Reproducibility (revised)

The original draft required rerunning each scenario a second time to empirically check variance. Per the Owner's corrected budget — **one pass per scenario, 20 invocations total** — that empirical rerun is out of scope for this pass. Reproducibility is instead established **by construction** at WP-3: each benchmark task definition must fix its starting commit, exact task text, and scoring rubric precisely enough that re-running it (in a future, separately-budgeted pass, if ever needed) would be expected to land within a stated tolerance — but that rerun itself is not part of R-0.0's current scope or budget. `contract.yaml`'s `engineering_acceptance` has been updated to reflect this.

## Instrumentation path — resolved (staged hybrid, per Owner correction)

**Stage 1 (WP-4, this contract, no gate needed):** read-only. Read existing `.renmark/analytics/*.jsonl` output (`events.jsonl`, `task-runs.jsonl`, `feature-runs.jsonl`) and produce a coverage table against every required metric: model/agent invocations, dispatch type, context-size estimates, output-size estimates, replans, retries, worker dispatches, test executions, verification executions, duration, completion status, failure classification. Zero `renmark/**` changes. Do not assume coverage merely because a ledger file exists — verify each metric against an actual recorded field.

**Stage 2 (only if stage 1 finds a genuine gap):** design (not implement) opt-in instrumentation:
- Gated behind `RENMARK_BASELINE_TRACE=1` — behavior-neutral (byte-identical output on a fixed test input) when unset.
- No routing, planning, retry, test, or verification decision may change.
- Reuse the existing append-only analytics path where practical.
- Touch only the exact modules identified in the design — this contract's `allowed_paths` must be explicitly amended with those exact paths **before** implementation, never a blanket `renmark/**` exception.
- Include a test proving behavior neutrality.
- Not a general telemetry platform — scoped narrowly to R-0.0's stated missing metrics only.

Implementation of stage 2 (if triggered) does not start until the stage-1 coverage table + stage-2 design are produced and inspected under this contract.

---

## Revision history

- **2026-08-01 (original draft, superseded):** proposed 3/10/25 invocation caps (38 total), USD estimates, and a doubled reproducibility-rerun budget. Superseded in full by the Owner's correction: "That permits 38 calls and conflicts with the previously established maximum of 20 invocations across the complete baseline... Do not convert this into a dollar-spend estimate."
- **2026-08-01 (this revision):** 2/6/12 invocation caps (20 total), no USD, one pass per scenario, reproducibility established by construction rather than empirical rerun.

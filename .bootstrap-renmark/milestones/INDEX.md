# Milestones / Releases Index

**Reading order:** `governing-methodology-addendum-03.md` (2026-08-01) is governing for Phase/Release relationship rules and R-0.0's binding decisions. `governing-methodology-addendum-02.md` (2026-08-01) is governing for release lifecycle/acceptance-ladder mechanics. `governing-methodology-addendum-01.md` (2026-07-31) is governing for the 4-role runtime model and Phase 0–8 sequencing. Neither original document's milestone table (`governing-architecture-roadmap.md` §15) should be implemented as originally written.

## Superseded — original 10-milestone sequence

Historical reference only.

| ID | Title | Status |
|---|---|---|
| M-0 | Baseline and Architectural Freeze | superseded → see R-0.0 below |
| M-1..M-10 | (see governing-methodology-addendum-01.md reconciliation table) | superseded |

## Phase 0 — sequencing container (not a unit of completion)

Per addendum-03: "Phases remain sequencing and dependency containers... A Phase may not close merely because its internal tasks are complete — its associated release outcomes must meet their acceptance and observation requirements." Phase 0 currently contains one release:

| Release | Title | Type | Gates | Lifecycle status |
|---|---|---|---|---|
| **R-0.0** | Baseline and PRD Reconciliation | internal-enablement | gates R-0.0 → R-0.1 (R-0.1 cannot start until R-0.0 reaches RELEASED+) | **RELEASED** (2026-08-01, v0.39.3, tag `v0.39.3`). All 5 work packages complete. Acceptance review executed against `internal-acceptance-scenario.md`: **ACCEPTED WITH FOLLOW-UP** (F1: Scenario B/C baseline numbers not representative, re-run corrected versions before citing; F2: R-0.1's contract must cite the Scenario C unauthorized-delete finding as founding evidence). See `R-0.0/closeout.md`. `gates_release: R-0.1` is now unlocked. |

## Phase 1 + Phase 2 (blocking subset)

| Release | Title | Type | Built from | Lifecycle status |
|---|---|---|---|---|
| **R-0.1** | Bounded Small-Task Fast Path | feature | Phase 1 + blocking subset of Phase 2 | **RELEASED** (2026-08-01, v0.39.4, tag `v0.39.4`). All 5 work packages complete. `renmark/fast_path.py` (classification + scope enforcement) + `claude_agent.build_fast_path_agent_dispatch()` (live wiring, additive — existing `build_agent_dispatch` untouched). Acceptance: **ACCEPTED WITH FOLLOW-UP** (F1: no-nested-dispatch is prompt-level only, not mechanically enforced — no host-independent signal exists today; F2: the R-0.0-vs-R-0.1 benchmark comparison is n=1, not a controlled A/B). See `R-0.1/closeout.md`. `gates_release: R-0.2` is now unlocked. |
| **R-0.2** | Controlled Worker Execution | feature | remainder of Phase 2 | **RELEASED** (2026-08-01, v0.39.5, tag `v0.39.5`). Contract at `.renmark/plans/2026-08-01-r-0.2-controlled-worker-execution-contract.md` (moved out of this `milestones/` tree per Owner instruction — canonical renmark artifacts live under `.renmark/`, not `.bootstrap-renmark/`). WP-1–WP-6 designed; WP-5a-e implemented (scope-verification generalization, R-008 dispatch gate, Inspector tool-restriction + repair-work-order pattern, evidence-required replan gate, rework-cap wiring); WP-7 independent review found every mechanism built-and-tested but under-wired; WP-8 (bounded repair pass) and WP-9 (final narrow pass on scope enforcement) measurably narrowed but did not fully close that gap. Acceptance: **ACCEPTED WITH FOLLOW-UP** — materially more follow-ups than R-0.0/R-0.1 (F1 residual: scope-enforcement blocking still has no production caller; F2: repair-work-order emission is prose-invoked only; F3 residual: R-008 gate is live but lenient-only; F4: rework-cap uniformity gaps remain at fast-path/debug; F5: replan-gate coverage is debug-only; F6 carried from R-0.1; F7: `ruff`/`mypy` unavailable in this environment). See `.renmark/reviews/2026-08-01-r-0.2-closeout.md`. `gates_release: R-0.3` is now unlocked, with F1/F2/F4/F5 recorded as real pre-existing debt for R-0.3's planning. |

Phases 3–8 (minimal ledger, minimal Inspector, Planner altitude split, deterministic integration, WritingMate, advanced optimizations): no releases drafted yet. Per addendum-01 §9 / addendum-03: only one blocking release is actively worked at a time, and no future release is broken down until the preceding blocking release closes (reaches CLOSED on the 10-state lifecycle, not merely ENGINEERING VERIFIED).

## Release contract template

`release-contract-template.yaml` — canonical shape. `R-0.0/contract.yaml` is the first filled-in instance.

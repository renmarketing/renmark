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

## Phase 1 + Phase 2 (blocking subset) — contract drafted, pending Owner approval

| Release | Title | Type | Built from | Lifecycle status |
|---|---|---|---|---|
| R-0.1 | Bounded Small-Task Fast Path | feature | Phase 1 + blocking subset of Phase 2 | **READY** (Owner-approved as drafted, 2026-08-01). **Only WP-1 (small-task classification design) is authorized to start.** WP-2 (Worker scope-enforcement design), WP-3 (UX regression suite), WP-4 (implementation), WP-5 (benchmark comparison vs. R-0.0) each remain individually gated — see `R-0.1/contract.yaml` work_packages[].status. `allowed_paths` stays empty until an explicit amendment. |
| R-0.2 | Controlled Worker Execution | feature | remainder of Phase 2 | PLANNED (working title only, contract not yet drafted) |

Phases 3–8 (minimal ledger, minimal Inspector, Planner altitude split, deterministic integration, WritingMate, advanced optimizations): no releases drafted yet. Per addendum-01 §9 / addendum-03: only one blocking release is actively worked at a time, and no future release is broken down until the preceding blocking release closes (reaches CLOSED on the 10-state lifecycle, not merely ENGINEERING VERIFIED).

## Release contract template

`release-contract-template.yaml` — canonical shape. `R-0.0/contract.yaml` is the first filled-in instance.

# .bootstrap-renmark/

Temporary implementation-control workspace for the Renmark role-based orchestration refactor.

This directory is the **temporary operating system for the implementation**, per the Owner-supplied governing directive. It is deliberately kept outside `.renmark/` so the existing Renmark runtime cannot load, mutate, or treat these draft artifacts as approved project truth while the new system is being built.

## Governing documents (canonical reference, do not edit)

- `governing-bootstrap-directive.md` — the methodology document itself (roles, authority order, prohibited behavior, required sequence, First Claude Code Instruction). Still governing.
- `governing-architecture-roadmap.md` — the original target architecture and 10-milestone implementation roadmap. Role/artifact/constitution definitions still valid as reference; the milestone *sequence* is superseded, see addendum-01.
- `governing-methodology-addendum-01.md` — (2026-07-31) collapses the 10-role hierarchy to 4 runtime roles + deterministic subsystems; replaces the 10-milestone sequence with a Phase 0–8 sequence; moves UX/compatibility protection to the front. Still governing.
- `governing-methodology-addendum-02.md` — (2026-08-01) **release-oriented milestones**: the unit of completion changes from "Phase's tasks implemented" to "user-testable capability demonstrated and accepted" via a 10-state release lifecycle (PLANNED→...→CLOSED) and a 4-level acceptance ladder. Applies to Renmark's own development AND every project Renmark builds — core doctrine, not a one-off refactor rule. Currently governing; supersedes addendum-01's completion criteria while keeping its sequencing.

All were supplied verbatim by the Owner (Roberto), 2026-07-31 through 2026-08-01.

See `milestones/INDEX.md` for how these reconcile into the current release-candidate list (R-0.0, R-0.1, R-0.2 — all working titles, none approved yet) and `release-contract-template.yaml` for the canonical contract shape.

## Status

**Phase A (bootstrap) in progress.** Per the governing directive's authority order and its Section 13 "First Claude Code Instruction," this pass produces only:

1. This directory structure.
2. `authority-matrix.md`.
3. `current-system-audit.md` (Phase B — descriptive only, no redesign).
4. `milestones/M-0/contract.yaml` (proposed, not yet Owner-approved).
5. A `Done / Found / Next` report to the Owner.

**No production code has been modified. No implementation Workers have been dispatched. No `/renmark:*` orchestration commands have been invoked for anything beyond logged baseline inspection (none were invoked this pass — see current-system-audit.md for how baseline inspection was actually performed).**

Execution stops after this pass pending Owner approval, per governing-bootstrap-directive.md Section 5 (Phase A, item 8) and Section 13.

## Directory map

```text
.bootstrap-renmark/
├── README.md                          (this file)
├── governing-bootstrap-directive.md   (canonical methodology reference)
├── governing-architecture-roadmap.md  (canonical architecture reference)
├── authority-matrix.md
├── current-system-audit.md
├── decisions/
│   └── INDEX.md
├── milestones/
│   ├── INDEX.md
│   └── M-0/
│       ├── contract.yaml
│       ├── work-orders/       (empty — no workers dispatched)
│       ├── worker-returns/    (empty)
│       ├── inspections/       (empty)
│       └── integration/       (empty)
├── ledger/
│   └── events.jsonl
├── metrics/                   (empty — baseline scenarios not yet run; requires Owner go-ahead per M-0 contract)
└── migration/                 (empty — not yet applicable)
```

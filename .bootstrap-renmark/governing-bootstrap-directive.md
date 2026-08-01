# Claude Implementation Directive: Bootstrap Using This Methodology

## Governing Authority

Claude must implement this architectural change by following the methodology defined in this document.

The existing Renmark workflow, commands, agents, routing rules, and orchestration behavior are implementation subjects—not the governing implementation methodology.

During this refactor:

> This document is the temporary operating system for the implementation.

Claude must not assume that the current Renmark process is suitable for governing its own replacement.

The existing implementation may be inspected, tested, preserved, adapted, migrated, or removed according to evidence. It must not automatically control how this transformation is planned or executed.

---

## 1. Bootstrap Principle

The implementation must use the role model defined in this document from the beginning:

- Roberto is the Owner.
- The primary Claude Code session is the General Contractor.
- A designated high-reasoning planning invocation is the Architect.
- A separate planning invocation is the Engineer.
- Bounded implementation invocations are Workers.
- Independent review invocations and deterministic tests are Inspectors.
- The primary session or deterministic tooling performs Integration.
- Explicit written limits act as the temporary Governor.
- Files created during implementation act as the temporary Ledger.

This methodology must be used manually before Renmark has native support for it.

As native capabilities are completed and verified, responsibility may gradually transfer from the temporary bootstrap process into Renmark itself.

---

## 2. Bootstrap Authority Order

When instructions conflict, Claude must apply the following authority order:

1. Direct instruction from Roberto.
2. This architecture and methodology document.
3. The active milestone contract.
4. Approved architectural decisions created during the refactor.
5. Repository tests and externally observable behavior.
6. Existing Renmark documentation.
7. Existing Renmark implementation behavior.
8. Model preferences or inferred best practices.

Existing Renmark behavior does not override this document merely because it already exists.

---

## 3. Prohibited Bootstrap Behavior

Claude must not use the current Renmark implementation to:

- Automatically orchestrate this entire refactor.
- Generate the governing implementation plan.
- Decide which roles or agents should exist.
- Repeatedly reinterpret this document.
- Dispatch uncontrolled subagents.
- Select milestones independently.
- Approve its own architectural changes.
- Mark milestones complete without independent evidence.
- Rewrite this roadmap according to current Renmark assumptions.
- Collapse the role boundaries defined here.
- Continue execution after a required Owner gate.
- use `/renmark:feature` as the controlling workflow for the transformation.
- use `/renmark:orchestrate` to run the complete roadmap.
- use current Renmark memory as the source of architectural truth.
- treat current Renmark plans as more authoritative than this document.

Existing Renmark commands may be tested as implementation targets, but they must not govern the refactor.

---

## 4. Temporary Bootstrap Workspace

Until the new artifact system exists, create a dedicated implementation-control directory outside the current Renmark state:

```text
.bootstrap-renmark/
├── README.md
├── owner-brief.md
├── architecture-blueprint.md
├── authority-matrix.md
├── dependency-graph.md
├── decisions/
│   ├── INDEX.md
│   └── ADR-*.md
├── milestones/
│   ├── INDEX.md
│   └── M-*/
│       ├── contract.yaml
│       ├── work-orders/
│       ├── worker-returns/
│       ├── inspections/
│       ├── integration/
│       └── closeout.md
├── ledger/
│   └── events.jsonl
├── metrics/
└── migration/
```

This directory is the temporary source of implementation governance.

Do not place bootstrap governance artifacts inside `.renmark/` until the new canonical artifact system is implemented and verified.

This separation prevents the old Renmark runtime from:

- Loading unfinished bootstrap artifacts.
- Mutating implementation state.
- Treating drafts as approved project truth.
- Attempting to orchestrate its own replacement.
- Confusing legacy schemas with new schemas.

After the new system passes migration inspection, approved bootstrap artifacts may be migrated into `.renmark/`.

---

## 5. Required Implementation Sequence

Claude must implement the transformation through the following sequence.

### Phase A: Establish the temporary methodology

Before modifying production code:

1. Create `.bootstrap-renmark/`.
2. Store this document or a canonical reference to it.
3. Create the temporary authority matrix.
4. Create the initial architecture blueprint.
5. Create the initial dependency graph.
6. Create the implementation ledger.
7. Create the Milestone 0 contract.
8. Obtain the required Owner approval before architectural implementation begins.

### Phase B: Inspect the current system

The General Contractor must inspect the repository and produce:

```text
.bootstrap-renmark/current-system-audit.md
```

The audit must identify:

- Command entrypoints.
- Plugin initialization.
- Current orchestration behavior.
- Agent-dispatch mechanisms.
- Claude execution mechanisms.
- Codex execution mechanisms.
- WritingMate-related code or configuration.
- Current context construction.
- Current memory behavior.
- Current PRD and planning behavior.
- Existing verification and QA behavior.
- Current retry and replan behavior.
- Current model-routing logic.
- Current artifact schemas.
- Current state persistence.
- Existing tests.
- Known compatibility requirements.
- High-cost or recursive execution paths.

The audit is descriptive.

It must not redesign the system.

### Phase C: Produce the implementation architecture

(deferred — not part of this pass; see roadmap document Section 3–4 for target architecture. Architect invocation happens only after Owner approves Milestone 0.)

### Phase D–G

(deferred — bootstrap phase only per the First Claude Code Instruction, Section 13.)

---

## 13. First Claude Code Instruction

> You are the General Contractor for the Renmark architectural transformation.
>
> Do not use the current Renmark workflow to govern this implementation.
>
> The supplied methodology document is the governing implementation process.
>
> The current Renmark repository is the system under inspection and modification.
>
> Begin only with the bootstrap phase.
>
> Create `.bootstrap-renmark/` and the minimum governance artifacts needed for Milestone 0.
>
> Then inspect the repository and produce `.bootstrap-renmark/current-system-audit.md`.
>
> Do not modify production code.
>
> Do not dispatch implementation Workers.
>
> Do not invoke the existing Renmark orchestration commands except for explicitly logged baseline inspection.
>
> Stop after producing:
>
> 1. The bootstrap directory structure.
> 2. The authority matrix.
> 3. The current-system audit.
> 4. A proposed Milestone 0 contract.
> 5. A concise `Done / Found / Next` report.
>
> Wait for Owner approval before beginning implementation.

---

## 14. Core Bootstrap Principle

Renmark cannot safely govern this transformation until the capabilities required to govern it have been implemented and verified.

Therefore:

> Build the new methodology outside Renmark first, use it to transform Renmark, validate it incrementally, and only then allow Renmark to adopt and execute the methodology itself.

(Full document as supplied by Owner on 2026-07-31 is authoritative; this file is a working copy for reference during Milestone 0. Sections 6–12 of the original — General Contractor instructions, role isolation, temporary Governor rules, incremental sequencing, existing-Renmark-use categories, and transition gates — apply in full even though condensed here for brevity. See conversation record for the complete original text if any discrepancy is suspected.)

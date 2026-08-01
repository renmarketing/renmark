# Governing Methodology Addendum 01: Governor Assessment and Roadmap Revision

**Status:** Governing — supersedes conflicting portions of `governing-architecture-roadmap.md`
**Authority:** Direct instruction from Roberto (Owner), authority order rank 1 (governing-bootstrap-directive.md §2), also functions as an amendment to the methodology document itself (rank 2)
**Date:** 2026-07-31 (session continuation)
**Effect:** The original 10-milestone roadmap (`governing-architecture-roadmap.md` §15) is **not** to be implemented as originally sequenced. This addendum's Phase 0–8 sequence replaces it. `governing-architecture-roadmap.md` remains valid as an architecture *reference* (role definitions, artifact contract shapes, constitution R-001–R-015) — only the milestone *sequence and scope* is revised.

The original `milestones/M-0/contract.yaml` (proposed, never approved) is **superseded** by this addendum's Phase 0, which has broader scope (adds PRD reconciliation, which the original M-0 lacked).

---

## Full text as supplied by the Owner

> Claude's answer is strong. I agree with roughly 80–85% of it, but I would correct one important conclusion.

### 1. Difficulty: Claude is probably right

Not a rewrite — Renmark already has many primitives (structured subagent inputs/outputs, externalized state, deterministic lifecycle checks, artifact-size controls, execution isolation, verification/routing mechanisms). Parts of the proposed architecture are formalization and consolidation. The genuinely difficult parts: separating architectural decisions from implementation planning; making inspection genuinely independent; applying remote/API-generated code safely; determining minimum impact of a change; migrating without breaking current workflows. A weeks-to-months project, not a weekend refactor.

### 2. PRD alignment: a real risk, but overstated as stated

The current PRD and the proposal don't necessarily disagree about the **product experience** — only if the contractor–architect–worker structure becomes visible to the user. Renmark can still serve the vibe coder who types `/renmark:start`; internally it may use several authority roles without exposing them.

> Renmark remains a simple vibe-coding interface externally, with a governed execution control plane internally.

Primarily an architectural upgrade — becomes a PRD pivot only if: users must understand the roles; users must manually approve every handoff; every feature produces large governance artifacts; the workflow becomes slower/more ceremonious; Renmark prioritizes compliance machinery over shipping working software.

The PRD should gain a constraint:

> Internal orchestration complexity must remain invisible by default. Governance must reduce user effort, inference cost, or failure rate; otherwise it must not execute.

### 3. Upgrade versus overkill: both, depending on literalness of implementation

The role-zoo warning is valid. The analogy defines authority — it should not automatically mean nine persistent model agents. Reduce the **runtime** architecture to four visible execution roles:

| Runtime concept | Responsibility |
|---|---|
| General Contractor | Controls workflow and communicates with the user |
| Planner | Performs architecture or milestone planning at the required altitude |
| Worker | Implements bounded work |
| Inspector | Independently verifies work |

Everything else is mostly a **deterministic subsystem**, not a persistent agent:

- **Governor:** policy code, budgets, circuit breakers.
- **Integrator:** patch application, Git operations, conflict detection, tests.
- **Ledger:** storage.
- **Engineer:** a planning *mode* / contract-generation stage, not necessarily an ongoing agent.
- **Architect:** an elevated Planner *mode*, invoked only for material architecture work.

This preserves the authority model without paying for an artificial organization on every task.

### 4. The roadmap sequence was wrong

Protecting current UX cannot wait until Milestone 8 — that was the biggest flaw in the original roadmap. Compatibility and UX invariants must be established at the beginning.

## Recommended revised sequence

### Phase 0 — PRD and measurable baseline (Blocking)
- Reconcile the PRD with the internal governance architecture.
- Define what must remain unchanged for the user.
- Measure current call counts, context usage, replans, and completion quality.
- Select three representative benchmark tasks.

### Phase 1 — UX and compatibility harness (Blocking)
- Preserve the single-command entrypoint.
- Add regression tests for current commands.
- Define maximum acceptable ceremony.
- Define current expected outputs and approval gates.
- Guarantee a rollback path.

(Moves the essential parts of the old Milestone 8 to the front.)

### Phase 2 — Authority boundaries and budget controls (Blocking, likely highest immediate return)
- Workers cannot replan.
- Inspectors cannot repair.
- Nested dispatch is prohibited.
- Every call needs a reason and budget.
- Replanning requires evidence.
- Retry loops are capped.
- Small changes use a fast path.

### Phase 3 — Minimal canonical ledger (Blocking)
Do not begin by creating six new artifact types and a large directory hierarchy. First consolidate: current lifecycle state, dispatch history, work results, inspection results, resource usage. Introduce only the minimum contracts: Work Order, Work Result, Inspection Report, Escalation.

### Phase 4 — Minimal independent Inspector (Blocking)
Start with one combined Inspector checking: acceptance criteria, tests, scope compliance, architecture constraints when applicable. Split into specialized Inspectors only when data proves separation improves outcomes.

### Phase 5 — Planner altitude separation (Conditional, not universally blocking)
Two planning modes: **Architecture mode** (system boundaries, major decisions) and **Milestone mode** (executable work contracts). Do not automatically invoke both. Architecture mode runs only when the task materially affects system design.

### Phase 6 — Deterministic integration layer (Blocking for WritingMate, not for improving native Claude/Codex execution)
Patch validation; allowed-file enforcement; local application of API-generated changes; test execution; Git/worktree management; conflict classification. Required before remote LLM Workers are safe.

### Phase 7 — WritingMate provider (Deferrable until the control plane works)
Only after bounded work orders, scope validation, local integration, inspection, and budgets exist. Use for small implementation slices, test generation, code analysis, independent review — not initially for architecture or repo-wide refactors.

### Phase 8 — Advanced optimizations (Deferrable)
Only after measurement demonstrates the need: full dependency graph, model performance registry, specialized Inspectors, confidence thresholds, dynamic capability routing, detailed impact analysis.

## Methodology document correction

The original document describes the **maximum mature architecture**, which could be misread as the *minimum required implementation*. Add near the top:

> The role model defines authority boundaries, not a requirement that every role be implemented as a separate model invocation. Prefer deterministic code, combined roles, and fast paths. Introduce a separate agent only when independent context or independent judgment produces measurable value.

Also add:

> Small tasks must bypass architectural planning, milestone decomposition, and multi-agent orchestration unless a policy trigger requires them.

Practical routing model:

```text
Small local task
→ General Contractor
→ Worker
→ deterministic tests
→ Inspector only if risk requires it

Normal feature
→ Milestone Planner
→ Workers
→ Integrator
→ Inspector

Architectural feature
→ Architecture Planner
→ Owner gate
→ Milestone Planner
→ Workers
→ Integrator
→ Inspector
```

## Governor assessment

The destination is sound. The original 10-milestone roadmap is not yet ready for full implementation as written.

**Blocking gaps:** PRD reconciliation; UX invariants moved to the beginning; clear fast path for small tasks; clarification that roles are authority boundaries, not mandatory separate agents; baseline metrics; minimum viable artifact set; explicit criteria for when Architect and Engineer modes are invoked.

**Deferrable complexity:** full model capability registry; multiple specialized Inspector classes; comprehensive dependency graph engine; confidence mathematics; large artifact hierarchy; full self-hosting transition machinery.

## Best next move (as instructed)

> Do not ask Claude to begin Milestone 0 from the ten-milestone roadmap yet. First revise the methodology into a minimum viable governed orchestration roadmap with three explicit paths — small task, normal feature, and architectural feature — and place UX compatibility and budget controls before expanding the agent architecture.

---

## Reconciliation with `governing-architecture-roadmap.md`

| Original concept | Status under this addendum |
|---|---|
| §3.1 Role hierarchy (10 rows incl. Foreman, Ledger as separate rows) | Collapsed to 4 runtime roles (GC, Planner, Worker, Inspector) + deterministic subsystems (Governor, Integrator, Ledger). Foreman/Dispatcher folds into deterministic Governor/Integrator code, not a role. |
| §3.4 Architect / §3.5 Engineer as distinct invocation types | Both become **modes of one Planner** role (Architecture mode, Milestone mode) — not separate persistent agents. Architecture mode is conditional, invoked only on material design impact. |
| §5 Canonical Artifact Model (full `.renmark/` hierarchy incl. `config/`, `specs/interfaces/`, `decisions/ADR-*`, per-milestone 5-subdir structure) | Deferred. Phase 3 introduces only 4 minimal contracts (Work Order, Work Result, Inspection Report, Escalation) consolidating *existing* siloed logs — not the full target hierarchy. |
| §6 Artifact Contracts (6 YAML schemas) | Contract *shapes* remain valid reference for Phase 3, scoped down to the 4 above. |
| §9 Budget Governor, §12 Confidence-Based Escalation | Confidence math and full budget-dimension tracking → Phase 8 (deferrable). Phase 2 ships the *blocking* subset: reason+budget per call, capped retries, evidence-required replanning. |
| §15 Milestone 0–10 sequence | **Replaced** by this addendum's Phase 0–8. Milestone numbering (M-0 etc.) should not be reused for the new phases to avoid confusion — see `milestones/INDEX.md` update. |
| §16 "First repository analysis output" (`current-system-audit.md`) | **Still valid and already satisfied** — the audit already produced covers exactly this requirement; no rework needed. |
| Constitution R-001–R-015 (`governing-architecture-roadmap.md` §4) | Still governing, unchanged. |
| Milestone 10 (WritingMate) sequencing rule | Still governing, unchanged — now expressed as Phase 7, still gated behind Phase 6 (deterministic integration layer), consistent with the original intent. |

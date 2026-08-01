# Renmark Role-Based Orchestration Architecture and Implementation Roadmap

**Status:** Proposed architectural evolution
**Target:** Renmark plugin for Claude Code and Codex CLI
**Primary objective:** Make long-horizon vibe coding sustainable by separating planning, implementation, inspection, integration, and governance while minimizing context and subscription-credit consumption.
**Prepared for:** Claude Code implementation
**Date:** July 31, 2026

> Full text as supplied by the Owner (Roberto) on 2026-07-31, stored verbatim for canonical reference during Milestone 0 and all subsequent Architect/Engineer invocations. Reproduced in full below (Sections 1–19 plus the closing Final Architectural Principle) — see the conversation record if any transcription discrepancy is suspected.

---

# 1. Executive Summary

Renmark began as a context-hygiene and deterministic workflow system for long-horizon software development.

Its existing strengths include:

- Persistent project state stored outside the model context.
- PRDs, plans, milestones, ADRs, reviews, approvals, and changelogs.
- Isolated task execution.
- Multi-model routing.
- Claude Code and Codex execution.
- Parallel work groups with controlled integration.
- Verification and human approval gates.
- Commands such as `/renmark:feature`, `/renmark:plan`, `/renmark:orchestrate`, `/renmark:verify`, `/renmark:debug`, `/renmark:codereview`, `/renmark:finish`, `/renmark:roadmap`, `/renmark:doctor`.

The current problem is not that Renmark lacks process. The problem is that orchestration has gradually become too expensive. Claude Code or Codex may repeatedly reinterpret the project, replan settled decisions, load too much history, dispatch unnecessary agents, perform redundant reviews, revisit unrelated files, run excessive tests, overengineer small changes, and spend more inference managing the workflow than implementing the feature.

The proposed solution is to turn Renmark into a governed AI software organization, using a construction-industry analogy: Owner (Roberto), General Contractor (Claude Code/Codex session), Architect (high-capability planning model), Engineer (technical planning model), Workers (small/specialized models), Inspectors (independent models and deterministic tools), Integrator (applies/reconciles changes), Governor (enforces budgets/authority/routing), and the Renmark artifact store/ledger as permanent records.

The most important change is not adding more agents — it is preventing agents from crossing authority boundaries. The Governor should be deterministic code whenever possible, not another conversational agent.

---

# 2. Session Conclusions

**2.1 Renmark remains a plugin** — not a standalone platform replacing Claude Code or Codex. It operates through Claude Code, Codex CLI, potentially both, and external LLM providers for bounded inference. Renmark provides workflow governance, role separation, persistent state, context selection, artifact contracts, routing, inspection gates, budget enforcement, and cross-session resumption.

**2.2 The host is the General Contractor** — receives the Owner's request, starts/resumes lifecycle, loads canonical state, decides next approved role, dispatches work orders, collects structured results, invokes inspectors, coordinates integration, reports to Owner. Must not personally redo every role's work.

**2.3 The Architect is expensive and infrequent** — expands the Owner's idea into a coherent blueprint (system boundaries, components, data flow, integration boundaries, quality attributes, modularity, risks, non-functional constraints, ADR candidates). Must not create per-file instructions. Calling the Architect per task reproduces the cost problem.

**2.4 The Engineer translates architecture into executable contracts** — milestones, dependencies, interfaces, acceptance criteria, test expectations, work packages, risk classification, file-scope recommendations. Cannot revise architecture without escalation.

**2.5 Workers implement bounded slices** — receive one work order, relevant requirements, explicit target files, required interfaces, constraints, relevant tests, expected response format. Do NOT receive the complete conversation, complete repo, every historical plan/ADR body, every prior worker transcript, or authority to redesign/spawn agents.

**2.6 Inspectors are mandatory and independent** — review evidence, produce structured findings, return PASS/FAIL/BLOCKED, cite violated contract clause, provide reproducible evidence, classify severity, avoid implementing repairs. Often use a stronger model than the Worker.

**2.7 API workers do not directly work on the repository** — two worker modes: Native worker (filesystem/tool access, isolated worktree) vs Remote inference worker (text in, text out; cannot be trusted to claim it edited files, ran tests, verified builds, or inspected runtime behavior — Renmark must apply remote output in an isolated environment and generate local evidence).

---

# 3. Target Renmark Operating Model

**3.1 Role hierarchy** (authority-based, not prestige-based):

| Role | Primary responsibility | May modify repository | May change architecture | May dispatch agents |
|---|---|---:|---:|---:|
| Owner | Define intent and approve outcomes | No | Through change request | No |
| General Contractor | Orchestrate lifecycle and report progress | Limited integration actions | No | Yes, through Renmark |
| Architect | Produce or revise blueprint | No | Yes | No |
| Engineer | Convert blueprint into milestone contracts | No | No | No |
| Foreman/Dispatcher | Package and route work orders | No | No | No |
| Worker | Implement one bounded work order | In isolated scope | No | No |
| Integrator | Apply and merge approved changes | Yes | No | No |
| Inspector | Verify implementation and evidence | No | No | No |
| Governor | Enforce policy, limits, and routing | No | No | No |
| Ledger | Preserve canonical project state | N/A | N/A | N/A |

**3.2 Owner** — Roberto or another human operator. Provides intent, priorities, constraints, milestone feedback, architecture/release approval. Should not have to supervise every agent call.

**3.3 General Contractor** — normally the main Claude Code/Codex session; owns the lifecycle state machine; loads minimum canonical state, identifies phase, verifies prerequisites, selects next allowed action, dispatches only approved roles, tracks budgets, prevents unauthorized replanning, collects evidence, stops at human gates, produces `Done/Found/Next` reporting. Must not silently rewrite the Architect's blueprint, let Workers expand scope, load all history by default, spawn speculative agents, repeat inspection without new evidence, or rerun the whole workflow for a local failure.

**3.4 Architect** — highest-reasoning planning role; invoked only for initial blueprint, major new subsystem design, approved material change requests, confirmed architectural contradictions, or Engineer-unresolvable failures. Output: system intent, component map, domain concepts, interfaces, data ownership, control flow, quality attributes, security boundaries, extension strategy, constraints, non-goals, ADR candidates, architectural acceptance criteria. Must NOT include full implementation, large code blocks, per-file instructions, speculative components, or unbounded feature lists. Blueprint freezes after approval.

**3.5 Engineer** — translates frozen blueprint into buildable milestones: dependency graph, milestone contracts, interface contracts, risk classification, work-order candidates, test strategy, integration strategy, impact-analysis rules. If blueprint is incomplete, escalates rather than silently modifying architecture.

**3.6 Foreman/Context Dispatcher** — primarily deterministic Renmark code: reads current milestone contract, selects dependency-ready work, determines target scope, assembles smallest sufficient context, redacts secrets, selects model via routing policy, issues work order, validates returned schema, records ledger event. Does not reason about product direction.

**3.7 Workers** — implement exactly one work order; stay within target scope; follow repo conventions; preserve interfaces; return structured output; report assumptions/blockers/confidence; avoid unrelated cleanup, opportunistic refactors, architectural reinterpretation, or dispatching other agents. Specializations: implementation, test-generation, refactor, documentation, migration, UI, database, debugging — evidence-driven, not just model-size-driven.

**3.8 Integrator** — handles repository mutation and combination of work: applies remote patches, validates target scope, detects conflicts, combines independent Worker outputs, runs formatting/static checks, preserves repo consistency, records file hashes, prepares inspection candidate, commits only after gates pass. May resolve mechanical conflicts; may NOT resolve requirement/architectural conflicts without escalation.

**3.9 Inspectors** — initial classes: Contract Inspector (milestone/work-order acceptance criteria), Architecture Inspector (boundaries/coupling/modularity/ADR compliance), Code Inspector (correctness/maintainability/error handling/conventions), Test Inspector (coverage/relevance/execution evidence), Runtime Inspector (builds/tests/smoke/integration), UI Inspector (Playwright — happy paths, error states, loading states, boundary conditions, core interaction flow, regressions), Risk Inspectors (security, privacy, performance, accessibility, data migration, backward compatibility — invoked only when the milestone risk profile requires them; the Engineer determines required Inspector classes per milestone contract).

**3.10 Governor** — deterministic whenever possible: enforces authority, call limits, context limits, retry limits, replan rules; prevents nested dispatch; tracks model-category allowance; selects permitted routing; triggers circuit breakers; requires evidence before escalation; stops execution when budget is exhausted. Must not itself become another expensive reasoning loop.

---

# 4. Renmark Constitution

- **R-001 State lives in artifacts** — project truth lives in `.renmark/` artifacts, not the active model conversation.
- **R-002 Load indexes before bodies** — load memory indexes/summaries/hashes/metadata before full documents.
- **R-003 Use the smallest sufficient context** — every role receives only what its contract requires.
- **R-004 Plan once, revise through evidence** — a frozen blueprint may only be revised via an explicit architectural change request.
- **R-005 Workers cannot redesign** — may report a design problem but cannot solve it by expanding their own authority.
- **R-006 Inspectors cannot repair** — findings and evidence only; a separate repair work order performs changes.
- **R-007 No nested delegation** — a dispatched Worker/Inspector/Engineer/Architect cannot spawn additional Renmark agents; only the General Contractor may dispatch, through the Governor.
- **R-008 No speculative agents** — every dispatch requires a work-order ID, contract, reason, scope, expected artifact, budget reservation.
- **R-009 No unsupported success claims** — a remote model cannot claim tests passed unless Renmark has local execution evidence.
- **R-010 No unrelated cleanup** — Workers/Integrators cannot modify files outside the approved impact set without escalation.
- **R-011 Inspection is evidence-based** — no milestone passes because an agent says the code "looks good"; PASS requires attached evidence.
- **R-012 Rework is bounded** — repair cycles are limited; repeated failure escalates instead of looping indefinitely.
- **R-013 Orchestration must justify its cost** — Renmark must record whether agent calls produced implementation, evidence, planning, or overhead.
- **R-014 Human gates remain authoritative** — Owner approves initial blueprint, material scope changes, architectural changes, milestone acceptance (when configured), release/destructive operations.
- **R-015 Existing executor constraints remain valid** — e.g. Codex execution through the approved `renmark-execute` subprocess path, native Claude-family agents through the approved Agent dispatch mechanism, no unauthorized agent commits, verifier execution before completion, parallel execution within approved groups, serialized integration/commits per wave, ledgered rerouting when an executor changes — unless explicitly migrated.

---

# 5. Canonical Artifact Model

Renmark already uses `.renmark/` as canonical project state; the new architecture extends rather than replaces it:

```text
.renmark/
├── constitution.md
├── config/{roles.yaml, routing.yaml, budgets.yaml, inspectors.yaml, providers.yaml}
├── state/{pipeline.json, current-run.json, quota-state.json, snapshots/}
├── specs/{project-brief.md, architecture-blueprint.md, interfaces/, non-functional-requirements.md}
├── decisions/{INDEX.md, ADR-*.md}
├── milestones/{INDEX.md, M-*/{contract.yaml, context-manifest.json, work-orders/, worker-returns/, integration/, inspections/, closeout.md}}
├── plans/
├── reviews/
├── memory/{INDEX.md, ...}
├── debug/
├── audits/
├── analytics/{calls.jsonl, context.jsonl, costs.jsonl, milestones.jsonl}
└── ledger/{events.jsonl, snapshots/}
```

All paths should be adapted to actual repository conventions rather than blindly duplicated.

---

# 6. Artifact Contracts

## 6.1 Architecture blueprint (YAML)
`schema_version`, `project{id,title,intent,owner}`, `scope{included,excluded,assumptions}`, `architecture{components,domain_boundaries,external_integrations,data_ownership,control_flows,extension_points}`, `quality_attributes{maintainability,security,reliability,performance,usability,testability}`, `constraints`, `non_goals`, `risks`, `adr_candidates`, `acceptance{architecture_conditions}`, `status: draft`, `revision`, `approved_by`, `approved_at`.

## 6.2 Milestone contract (YAML)
`milestone_id`, `title`, `blueprint_revision`, `objective{outcome,rationale}`, `dependencies{requires,unlocks}`, `scope{included,excluded,allowed_paths,prohibited_paths}`, `interfaces{consumes,produces,must_preserve}`, `acceptance_criteria[{id,requirement,evidence_type}]`, `required_inspections[contract,code,test,runtime]`, `risk{level,factors}`, `budgets{worker_calls,inspector_calls,repair_cycles,architect_calls,engineer_revisions}`, `status: ready`.

## 6.3 Work order (YAML)
`work_order_id`, `milestone_id`, `role: implementation-worker`, `objective`, `authority{allowed_operations,prohibited_operations}`, `scope{target_files,related_files_read_only,prohibited_files}`, `requirements`, `interfaces`, `acceptance_criteria`, `tests_expected`, `context_manifest{artifacts,file_hashes,estimated_input_tokens}`, `response_contract: worker-return-v1`, `budget{max_output_tokens,max_attempts}`.

## 6.4 Worker return (YAML)
`work_order_id`, `status: completed`, `summary`, `changes[{path,operation,patch}]`, `tests_proposed`, `tests_claimed_run` (should normally be empty for remote API Workers), `assumptions`, `risks`, `blockers`, `confidence{value,basis}`, `scope_compliance{modified_only_allowed_paths,architecture_change_requested}`.

## 6.5 Inspection report (YAML)
`inspection_id`, `milestone_id`, `inspection_type`, `candidate_hash`, `result: PASS`, `severity`, `criteria[{acceptance_id,result,evidence[{type,path}]}]`, `findings`, `required_repairs`, `advisories`, `scope_violation`, `architecture_escalation_required`.

## 6.6 Escalation request (YAML)
`escalation_id`, `source_role`, `milestone_id`, `work_order_id`, `classification`, `problem`, `evidence`, `attempts_completed`, `requested_authority{target_role,requested_decision}`, `scope_expansion_requested`, `architecture_change_requested`.

---

# 7. Lifecycle State Machine

Existing high-level flow (`Plan → Create → Test → Review → Document → Release`) and operational flow (`PRD → plan → build → verify → QA → review → ship`) map to:

```text
OWNER_INTAKE → PROJECT_BRIEF → ARCHITECTURE_DRAFT → OWNER_ARCHITECTURE_GATE →
BLUEPRINT_FROZEN → ENGINEERING_PLAN → MILESTONE_READY → WORK_ORDER_DISPATCH →
WORKER_RETURN → INTEGRATION_CANDIDATE → INSPECTION →
  ├── PASS → MILESTONE_CLOSEOUT
  ├── LOCAL_FAIL → REPAIR_WORK_ORDER
  ├── CONTRACT_FAIL → ENGINEER_ESCALATION
  ├── ARCHITECTURE_FAIL → ARCHITECT_ESCALATION
  └── BUDGET_FAIL → OWNER_GATE
→ OWNER_MILESTONE_GATE → NEXT_MILESTONE or RELEASE
```

**7.1 Failure classification:**
- **Local implementation failure** (incorrect condition, missing validation, broken test, type error, local integration issue) → Repair Worker, same scope, no replan.
- **Work-order failure** (ambiguous requirement, missing target interface, incorrect file scope, contradictory acceptance criteria) → Engineer, revise work order/milestone contract, do not auto-invoke Architect.
- **Architecture failure** (blueprint can't satisfy a required use case, contradictory component responsibility, undefined data ownership, new requirement changes boundaries, ADR no longer viable) → Architect, require evidence, require Owner approval when material.
- **Governance failure** (retry limit reached, context cap exceeded, quota exhausted, too many agents requested, repeated inconclusive inspection) → General Contractor, stop execution, produce budget/evidence report, request Owner decision only when necessary.

---

# 8. Context Hygiene Becomes Context Minimization

**8.1 Role-specific context:**
- **General Contractor**: current pipeline state, current milestone summary, open blockers, current budgets, artifact indexes, last closeout, Owner's active instruction. NOT all worker transcripts/full diffs/full history/every prior milestone body.
- **Architect**: Owner project brief, existing blueprint (if revising), relevant constraints, ADR index + selected ADRs, repository map, explicit escalation evidence. NOT unrelated implementation details, every source file, full execution logs.
- **Engineer**: frozen blueprint, repository map, dependency graph, applicable ADRs, existing interfaces, current milestone requirements.
- **Worker**: one work order, target files, read-only related files, required interface snippets, relevant tests, applicable conventions.
- **Inspector**: applicable contract, candidate diff or file hashes, test evidence, relevant changed files, applicable ADR excerpts.

**8.2 Context manifests** — every dispatch records artifact paths, file paths, file hashes, estimated tokens, inclusion reason, redactions applied, receiving role. Makes context selection auditable.

**8.3 No full-history continuation** — a new role invocation must not inherit the full parent conversation; continuity comes from artifacts. Preserves the existing principle behind `SubagentInput`/`SubagentOutput`/`dispatch_task_isolated`/isolated orchestration/per-wave summaries/canonical `.renmark/` state — evolve, don't discard.

---

# 9. Budget Governor

**9.1 Budget dimensions:** project, feature, milestone, work order, role, provider, model, model category, context tokens, output tokens, agent calls, repair cycles, replans, test executions, wall-clock duration.

**9.2 Initial provisional limits (configurable):**
```yaml
defaults:
  project: { architect_initial_calls: 1 }
  milestone:
    engineer_calls: 1
    engineer_revisions: 1
    worker_calls: 6
    inspector_calls: 6
    repair_cycles: 2
    architecture_escalations: 0
  work_order: { worker_attempts: 2, nested_dispatches: 0 }
  orchestration: { max_parallel_workers: 3, max_parallel_inspectors: 3, speculative_dispatches: 0 }
```

**9.3 Replan policy** — permitted only when: Owner changes a requirement; an Inspector provides architecture-level failure evidence; the Engineer proves the milestone contract is impossible; a dependency materially changed; the repository differs materially from the approved code map. NOT permitted because a Worker is uncertain, a test failed locally, a model prefers a different design, context feels confusing, or another model proposes a "more elegant" architecture.

**9.4 Circuit breakers** — stop when: retry limit exceeded; scope violations repeat; context cap exceeded; the same inspection finding repeats without new evidence; provider quota insufficient; the work order requires architecture authority; the candidate modifies prohibited paths; test evidence cannot be generated; the repository is in an unexpected state.

---

# 10. Artifact-First Communication

Roles communicate through versioned artifacts, not freeform conversational history. The General Contractor receives only artifact path, hash, status, summary, dependencies, budget consumed, required next action — in `Done / Found / Next` form. Avoid long reasoning explanations, repeated history recaps, raw transcripts, complete diffs in GC context, unstructured "thoughts" about future changes.

---

# 11. Dependency Graph and Change Impact

The Engineer produces a machine-readable dependency graph (nodes: component, module, interface, data store, external integration, test suite, UI flow, milestone; edges: imports, calls, produces, consumes, persists, renders, tests, depends-on, implements). When a file/interface changes, Renmark computes the minimum impacted set — only impacted work orders/tests/inspectors/docs/milestones reopen. A UI validation-rule change must not reopen the entire architecture and every milestone.

---

# 12. Confidence-Based Escalation

Every non-deterministic role reports confidence (a routing signal, not objective truth) with a short basis.

```yaml
confidence_policy:
  worker: { accept_for_integration: 0.75, inspect_with_extra_review: 0.55, escalate_below: 0.55 }
  inspector: { accept_pass: 0.80, require_second_inspector_below: 0.65 }
```

Low confidence triggers escalation, not repeated self-reasoning.

---

# 13. Model Specialization

Routing must consider capability, not only model size. Model registry records observed performance per role (`capabilities{code_generation,refactoring,testing,architecture,debugging,inspection}`, `supports{structured_output,tool_use,filesystem}`, `limits`, `allowed_roles`). Routing inputs: role, task type, risk, scope size, required tool access, provider availability, remaining allowance, historical pass rate, average repair rate, average context cost, latency.

Initial role guidance: Architect = highest-reasoning model, used rarely. Engineer = strong reasoning + repo understanding. General Contractor = reliable medium-to-strong host model. Worker = smallest proven-capable model. Inspector = independent model, stronger than the Worker when risk warrants. Integrator = deterministic tools first, model only for conflicts. Governor = deterministic code.

---

# 14. Observability and Metrics

**14.1 Required per-milestone metrics:** total calls, calls by role/provider/model, Architect calls, replans, worker attempts, repair cycles, inspector calls, context tokens, output tokens, WritingMate counted messages (when available), native subscription usage approximation, files changed/loaded, tests executed/repeated, wall-clock duration, agent-generated-implementation %, orchestration-overhead %, first-pass inspection rate, rework rate, scope-violation rate.

**14.2 Baseline scenarios (before refactoring):** Scenario A (small one/two-file change), Scenario B (medium vertical feature with impl + tests), Scenario C (long-horizon multi-module milestone with UI/tests/docs). Re-run after each major milestone.

**14.3 Provisional success targets (adjust after baseline measurement):** reduce orchestration calls ≥40%; reduce unnecessary replans ≥80%; reduce average context loaded per Worker ≥60%; ≥70% first-pass Worker acceptance on bounded tasks; normal repair loops limited to one; nested Worker dispatch fully prevented; maintain/improve test and inspection pass rates; a new Claude Code/Codex session can resume from artifacts without loading prior transcripts.

---

# 15. Milestone Implementation Roadmap

### Milestone 0: Baseline and Architectural Freeze
**Goal:** measure current behavior before changing it.
**Tasks:** ADR describing the role-based orchestration evolution; document current lifecycle and executor paths; add temporary instrumentation around agent dispatch, Codex subprocess execution, model routing, test execution, review calls, context assembly; run three baseline scenarios; record calls/context size/replans/tests/agent count/duration; identify highest-overhead paths; freeze unrelated workflow expansion during this refactor.
**Acceptance:** existing behavior documented; baseline reports exist; current tests pass; no functional behavior intentionally changed; rollback point tagged.
**Deliverables:** ADR, baseline report, trace schema, rollback tag, current architecture map.

### Milestone 1: Role and Authority System
Add role identifiers (owner, general-contractor, architect, engineer, dispatcher, worker, integrator, inspector, governor); role definitions + authority policies; authority validator rejecting Worker architecture changes, Inspector repository mutations, nested dispatch, Integrator requirement invention; map existing Claude/Codex/Fable routing to roles while preserving existing executor-specific restrictions; add role info to logs/ledger.
**Acceptance:** every dispatch has an assigned role; every role has explicit permissions; authority violations fail before inference/mutation; existing `/renmark:feature` and manual phase commands remain functional.

### Milestone 2: Artifact Contracts and Canonical Ledger
Schemas for blueprint/milestone contract/work order/worker return/inspection report/escalation request/milestone closeout; schema validation; append-only ledger events; artifact hashes; snapshot/restore; extend current pipeline state; preserve existing `.renmark/` conventions; migrate existing plan/review/memory outputs via adapters; ensure `INDEX.md` files are read before artifact bodies.
**Acceptance:** a run can resume from disk artifacts without full role transcripts; invalid outputs rejected; every result traceable requirement→milestone→work order→worker→candidate→inspection→closeout.

### Milestone 3: Architect and Engineer Pipeline
Architect invocation contract + approval gate + frozen blueprints; Engineer invocation contract; dependency graph generation; milestone contract generation; architecture escalation workflow; prevent routine milestones from invoking the Architect; blueprint revision tracking; map `/renmark:prd` and `/renmark:blueprint` into this pipeline; update `/renmark:plan` to operate as the Engineer role; keep Architect output above file-level implementation detail.
**Acceptance:** a seed request can become an approved blueprint → milestone contracts; a Worker cannot revise the blueprint; a local failure does not trigger Architect invocation; blueprint changes require a revision artifact + approval gate.

### Milestone 4: Bounded Worker Dispatch
Extend/wrap `SubagentInput`→`WorkOrder`, `SubagentOutput`→`WorkerReturn`; update `dispatch_task_isolated`; target-path enforcement; context manifests; token estimation; prohibit nested dispatch; Worker specialization; support native Claude workers, Codex executor workers, future remote API workers; preserve parallel execution groups and serialized per-wave integration; Workers return concise structured summaries only.
**Acceptance:** Workers receive only bounded context; cannot modify unapproved files; cannot spawn agents; output validated before integration; GC context receives no full Worker transcript.

### Milestone 5: Inspector Framework
Inspector registry; implement Contract/Architecture/Code/Test/Runtime/UI Inspectors; risk-based optional Inspectors; structured inspection reports; evidence required for PASS; independent model routing; Inspectors cannot modify files; repair-request generation; Playwright execution for applicable UI features; happy-path + selected edge-case verification; map existing `/renmark:verify`, QA, deep-QA, and code-review into this layer.
**Acceptance:** no milestone closes without required Inspector reports; Inspectors cannot repair code; PASS requires reproducible evidence; failed inspections create bounded repair work orders; UI milestones include browser evidence when configured.

### Milestone 6: Integrator and Impact Analysis
Integrator role; isolated candidate workspace/worktree handling; apply remote/native patches through the Integrator; verify patch scope; record before/after file hashes; deterministic merge support; conflict classification; dependency graph traversal; calculate impacted files/tests; restrict reinspection to impacted set where safe; preserve human merge gates and branch workflow rules.
**Acceptance:** remote output applied safely without direct API filesystem access; scope violations rejected; local evidence generated post-application; unrelated tests/agents not invoked by default; mechanical vs architectural conflicts treated differently.

### Milestone 7: Governor, Budgets, and Routing
Budget configuration; budget reservations before dispatch; track calls/context/retries/tests; retry and repair limits; replan policy; circuit breakers; confidence-based escalation; evidence-required escalation; model capability registry; historical routing metrics; quota-awareness; "no speculative dispatch" enforcement; explicit reason required for every Agent/executor call; milestone cost/overhead reports.
**Acceptance:** Renmark refuses unauthorized additional agents; replans require a recognized trigger; repair loops terminate; model selection explainable from policy; every milestone produces a resource report; baseline scenarios show measurable overhead reduction.

### Milestone 8: Owner-Facing Vibe Coding Experience
Keep `/renmark:feature` as primary entrypoint; accept natural-language intent; show Owner blueprint summary/assumptions/milestone sequence/key decisions; hide low-value orchestration chatter; present milestone closeout (what was built, demo instructions, test evidence, inspection status, known limitations, decisions needing input); support targeted feedback routed as local correction / milestone-contract revision / architectural change request; preserve manual commands for advanced control.
**Acceptance:** Owner can initiate a substantial feature with one request without supervising each Worker; feedback changes only necessary artifacts; completed milestones demonstrable/inspectable; internal complexity doesn't leak into routine usage.

### Milestone 9: Migration and Compatibility
Detect existing Renmark state versions; migration adapters; preserve existing PRDs/plans/memory/reviews/changelog/debug sessions; map old tasks→work orders; map verification outputs→inspection reports; compatibility mode; update `/renmark:doctor`; validate Claude Code plugin install + Codex CLI integration; test Windows/WSL/macOS/Linux paths where currently supported; update help/command docs.
**Acceptance:** existing projects can be opened and workflows resumed; migration is reversible; doctor reports missing/incompatible artifacts; Claude/Codex execution paths remain operational.

### Milestone 10: WritingMate LLM API Provider
**Architectural decision:** implement WritingMate first as a Renmark provider adapter via its OpenAI-compatible API (not MCP as the mandatory routing layer — MCP optional later for interactive/model-discovery use). Configure via `WRITINGMATE_DEVELOPER_KEY` env var; provider config block (`type: openai-compatible`, `base_url`, `api_key_env`, `workspace_id_env`, `model_discovery: true`, `model_cache_ttl_seconds`, `timeout_seconds`, `max_retries`); discover models at runtime rather than hard-coding the catalog.

Provider interface: `LLMProvider{list_models, get_model, generate, health_check, normalize_usage, classify_error, redact_for_logs}`; implement `WritingMateProvider implements LLMProvider`.

Remote Workers receive a bounded system contract + work order + file excerpts + interfaces + acceptance criteria + existing tests + output schema, and must not claim to have edited files/run tests/dispatched agents. Prefer strict JSON responses matching the Worker Return schema (§6.4). Flow: Work Order → Context Packager → WritingMate Provider → Remote Worker Response → Schema Validation → Scope Validation → Integrator applies patch in isolated workspace → local formatter/static checks → local tests → Inspectors → accept/repair/escalate.

**Usage controls:** WritingMate API and chat share account allowances — track calls by model category; avoid large prompts / full repo history; keep each request within one counted-message unit where practical; reserve output headroom; prefer Basic-category models for high-volume bounded tasks; Pro for complex Workers/Inspectors; Ultimate only for rare high-value decisions; never hard-code AppSumo Tier 4 limits — let the user configure actual pacing; stop dispatching before the configured allowance is exhausted; fall back to an approved native executor rather than looping on API failures. Recommended context target: `max_effective_tokens_per_request: 14000`, `preferred_input_token_ceiling: 10000`, `preferred_output_token_ceiling: 4000`.

**Model mapping** — assignment must use the live model list, not hardcoded assumptions about which model is "best."

**Security rules:** Developer Key only in env vars/approved secret storage; never in git, `.renmark/` artifacts, prompts, debug logs, or screenshots; redact secrets before sending context; file-level remote-provider policies; projects may prohibit external API context entirely; record which files/snippets were sent; no unrelated proprietary code sent; provide a provider kill switch.

**Acceptance:** live model catalog discovered; a bounded test work order succeeds end-to-end through the API; out-of-scope files rejected; Integrator applies valid output in isolation; local tests generate real evidence; Inspectors can verify the result; usage recorded; provider limits stop excessive dispatch; API failure doesn't corrupt pipeline state; no Developer Key written to disk artifacts or logs.

---

# 16. Claude Code Implementation Instructions

**Mission:** refactor Renmark from context-hygiene-with-increasingly-expensive-orchestration into governed role-based orchestration, preserving existing functionality, one milestone at a time — never all milestones in one context/branch.

**Required operating rules:** inspect repo before proposing changes; map existing modules to target concepts; reuse existing abstractions; preserve current command compatibility and `.renmark/` canonical state; preserve Claude/Codex executor restrictions; don't rename/remove public commands without migration; implement one roadmap milestone at a time; create an ADR before architectural code changes; add tests for each policy; produce full milestone closeout artifacts; stop after each milestone acceptance gate; don't dispatch agents unless the milestone explicitly authorizes them; don't use the Architect role to implement this refactor repeatedly; treat the roadmap as target architecture, not permission to overengineer unrelated systems.

**First repository analysis output** (before modifying code): `.renmark/audits/role-orchestration-repository-map.md` (note: bootstrap-phase equivalent is `.bootstrap-renmark/current-system-audit.md` per the governing bootstrap directive) identifying current command entrypoints, pipeline state implementation, Agent dispatch implementation, Codex subprocess implementation, model-routing implementation, context-selection implementation, plan/task schemas, verification/QA implementation, ledger/logging implementation, worktree/branch behavior, existing tests, gaps vs Milestone 0, and a Milestone-0-only file-level mapping proposal — NOT a complete file-by-file plan for all ten milestones in the first pass.

**Implementation cadence per milestone:** read roadmap + current milestone contract + relevant repo map sections + applicable ADRs → create/update milestone contract → identify smallest implementation scope → implement → test → run relevant Inspectors → produce closeout → stop for the configured gate.

**Required milestone closeout sections:** Outcome; Files changed; Tests executed; Inspection results; Metrics; Deviations from contract; New risks; Migration impact; Rollback procedure; Recommended next milestone.

**Prohibited:** rebuilding Renmark from scratch; replacing stable systems without evidence; implementing WritingMate before role contracts/integration controls exist; adding new agent roles without authority definitions; letting Workers/Inspectors spawn agents; loading full project history into every dispatch; treating remote API output as locally verified; silently revising the architecture; continuing through failed milestone acceptance criteria; optimizing for elegance at the expense of migration safety; combining several roadmap milestones into one unreviewable change.

---

# 17. Blocking and Deferrable Work

**Blocking before this architecture is viable:** role authority definitions; artifact schemas; canonical state and ledger; frozen blueprint behavior; Engineer-to-Worker contracts; independent Inspectors; safe Integrator; budget Governor; bounded repair loops; scope enforcement; resume-from-artifact support.

**Deferrable:** graphical orchestration dashboard; automatic dynamic model benchmarking; full MCP integration; multi-user orchestration; cloud-hosted Renmark service; marketplace model routing; advanced visual architecture diagrams; fully autonomous release; cross-project organizational memory; customer-facing WritingMate-backed services. Must not block the core refactor.

---

# 18. Recommended Immediate Action Points

1. Create the architecture ADR ("ADR: Role-Based Governed Orchestration for Renmark").
2. Instrument the current workflow before modifying it — the existing inefficiency must be measurable.
3. Run baseline scenarios and identify where calls multiply.
4. Implement Milestone 1 role boundaries before adding new agents.
5. Implement artifact contracts and the ledger.
6. Separate Architect and Engineer.
7. Convert existing isolated tasks into strict Work Orders.
8. Make Inspectors independent and evidence-based.
9. Add Integrator and Governor controls.
10. Only after those controls are proven, integrate WritingMate as a remote Worker provider.

---

# 19. Definition of Done

Complete when: Roberto can start `/renmark:feature` with a high-level product request; the GC obtains a bounded architectural blueprint; the blueprint is approved and frozen; the Engineer produces milestone contracts; Workers receive small role-specific work orders and cannot redesign/expand scope; remote API Workers return patches rather than pretending to operate the repository; the Integrator applies candidate changes safely; Inspectors independently verify contracts and runtime evidence; failures route to the correct authority level; replanning occurs only through explicit evidence and policy; retry/repair loops are bounded; context is selected from canonical artifacts rather than inherited conversations; Claude Code and Codex can resume the project from `.renmark/`; WritingMate can supply bounded inference without controlling the repository; the Owner sees milestone outcomes rather than orchestration noise; the new baseline demonstrates materially lower context/credit consumption; quality and verification remain equal to or better than the existing workflow; Renmark's orchestration costs less than the implementation value it enables.

---

# Final Architectural Principle

Renmark should not attempt to make every model understand the complete project. Renmark should make it unnecessary for every model to understand the complete project.

The blueprint preserves intent. The Engineer preserves technical coherence. The Work Order preserves scope. The Worker produces implementation. The Integrator preserves repository integrity. The Inspector preserves quality. The Governor preserves resources and authority. The Ledger preserves memory. The General Contractor preserves the workflow. The Owner preserves direction.

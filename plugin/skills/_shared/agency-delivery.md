# Agency Delivery Contract — Reference (single source of truth)

**Shared by `/renmark:start` (agency mode opt-in) and any skill that participates in an active agency workflow.** This is the one place the agency delivery loop, owner-questioning discipline, milestone/signoff gates, and agent-split rules live. Agency Mode is a **higher-level workflow above Conductor/Orchestrator** — it does not replace either mode; those still govern how individual tasks execute within each phase. Explicit opt-in only; invoked via `/renmark:start` when the user signals a full-project engagement.

---

## The delivery loop

Agency Mode walks through seven ordered phases. Each phase ends with a **milestone checkpoint** that pauses for owner feedback before the next phase begins.

| Phase | Main-agent action | Owner gate |
|---|---|---|
| 1. Discovery | Gather goal, users, constraints, success criteria via owner questions | Confirm understanding |
| 2. PRD agreement | Draft PRD artifact; surface risks and open questions | Explicit PRD approval |
| 3. Tech-stack recommendation | Propose stack; state trade-offs; ask owner to confirm or redirect | Stack signoff |
| 4. Roadmap / milestones | Decompose into milestones with acceptance criteria | Milestone plan approval |
| 5. Build | Dispatch scoped background agents per milestone; main agent coordinates | Milestone checkpoint after each milestone |
| 6. Demo / feedback | Surface working artifact or demo; gather feedback | Feedback round |
| 7. Verification + signoff | Run verifier; confirm acceptance criteria met; request owner signoff | Final signoff |

After signoff, route to `/renmark:finish` for release lane selection.

---

## Owner-questioning discipline

Agency Mode asks owner-level questions — one at a time, at the start of discovery and at each gate. It does NOT ask unnecessary technical questions that background agents can resolve themselves.

**Ask these:**
- What is the goal and why now?
- Who are the users?
- What are the constraints (time, budget, platform, integrations)?
- What are the risks the owner is already aware of?
- What does success look like, and who has final signoff?

**Do NOT ask:**
- Which library or framework to use (propose → owner confirms or redirects).
- How to implement a specific task (resolve in background agents).
- Whether to run tests (always run).
- Any question a deterministic check or file read can answer.

One question per turn. Never batch five questions into one message.

---

## Milestone and signoff gates

Agency gates are **distinct from technical gates** (lint, test, verifier). They exist to preserve owner alignment across phases.

| Gate | What triggers it | What resumes it |
|---|---|---|
| PRD agreement | End of discovery | Owner confirms PRD in writing |
| Stack signoff | After tech-stack proposal | Owner confirms or selects alternative |
| Milestone plan approval | After roadmap decomposition | Owner approves milestone list |
| Milestone checkpoint | After each milestone completes | Owner reviews deliverable, types continue |
| Final signoff | After verification passes | Owner types signoff or explicit approval |

A milestone checkpoint does not pass automatically when tests pass — it pauses for owner review. The distinction: **technical gates are automated; owner gates are not**.

Lifecycle transitions (`lifecycle.json`) mirror these gates: each phase writes its stage before returning. Gate state lives in `pipeline.json` (not in the conversation). Recovery after `/clear`: run `/renmark:resume`.

---

## Main-agent / background-agent split

| Responsibility | Who does it |
|---|---|
| Owner questioning, gate management, phase transitions | Main agent (Conductor or Orchestrator mode) |
| Artifact drafting (PRD, tech-stack doc, roadmap) | Main agent (short, single-purpose) |
| Milestone implementation | Scoped background agents, dispatched per task |
| Verification runs, deterministic checks | Background agents or `renmark-execute` |
| Milestone checkpoint summary, feedback synthesis | Main agent (reads summaries only, never full diffs) |
| Release preparation | `/renmark:finish` via handoff |

The main agent coordinates and communicates — it does not accumulate implementation context. Background agents write artifacts; the main agent reads bounded summaries (≤5 lines per task). This is the same orchestrator hygiene rule: **the orchestrator advances on summary fields alone**.

---

## Cost-control infra reuse

Agency Mode does not duplicate cost infrastructure — it delegates to existing modules:

- **Finish lane selection:** `renmark.finish_lanes.recommend_lane` / `resolve_lane` (see `finish-lanes.md`).
- **Cost preview:** `renmark.cost.estimate_cost` / `requires_escalation` — labels each phase task deterministic or model-driven before the owner approves the milestone plan.
- **Context budget:** `renmark.state.skills.context_budget_hint` (100k summarize / 120k compact / 150k checkpoint).
- **Subagent profiles:** role field in every dispatch packet; ledger tracks by role (see `subagent-profiles.md`).
- **Model routing:** cheapest capable executor per task type (see `model-routing.md`).
- **Task dispatch budget:** one local read/grep before any subagent (see `subagent-budget.md`).
- **Deterministic-first:** milestone-readiness checks (are acceptance criteria met? did tests pass? does the artifact exist?) run deterministically — **no model calls for infra validation** (see `deterministic-first.md`).

Do not inline these rules — cite the shared fragments.

---

## Examples

**Example 1: Owner asks a technical question during discovery.**  
"Should we use PostgreSQL or SQLite?" — Do NOT defer back to the owner. Propose PostgreSQL for production scale, SQLite for local dev; ask the owner to confirm or redirect. One turn. Move on.

**Example 2: Milestone build completes, tests pass.**  
Tests passing is not a milestone checkpoint. The main agent still pauses: surfaces a one-paragraph summary of what was built, what works, what is deferred — and waits for the owner to type "continue" or give feedback. The checkpoint is owner-driven, not automated.

**Example 3: PRD drafted, owner wants to change scope.**  
Honor it. Update the PRD artifact, re-run cost preview against revised milestones, present the delta ("this adds one milestone, estimated +$X"). Ask owner to re-approve before dispatching build agents.

---

## Why a shared file

Owner gates were earlier scattered across individual skill prompts: `/renmark:start` had its own gate list, `/renmark:feature` had a different one, `/renmark:finish` had a third. They drifted — one gated on stack signoff, another skipped it. Centralizing here means:

- One delivery loop definition shared by all agency-aware skills.
- Owner-questioning discipline defined once; no skill adds unnecessary technical questions independently.
- Milestone and signoff semantics are stable and auditable.
- Cost-control infra is referenced, not restated — no drift.

When citing this contract in a SKILL.md or subagent dispatch, write:

> *Honor the agency delivery contract in `${CLAUDE_PLUGIN_ROOT}/skills/_shared/agency-delivery.md`: discovery → PRD → stack signoff → roadmap/milestones → build → demo/feedback → verification → final signoff → finish. Ask owner-level questions only (goal, users, constraints, risks, success, signoff). Milestone checkpoints pause for owner review — they do not pass automatically when tests pass. Background agents handle implementation; main agent coordinates and reads bounded summaries. Delegate cost infra to finish_lanes / cost.py / context_budget_hint / subagent-profiles — do not inline those rules.*

Do not paste the delivery loop or gate table into the calling SKILL.md — cite this file.

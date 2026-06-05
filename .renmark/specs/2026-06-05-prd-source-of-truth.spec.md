---
artifact_type: spec
schema_version: 1
created_at: 2026-06-05
implemented_at: null
generator: brainstorm
related_plan: null
related_release: null
status: draft
dependency_refs:
  - .renmark/research/2026-06-05-prd-taskmaster.research.md
---

# Spec — `PRD.md`: a per-project source of truth + `/renmark:prd` skill

## Context

renmark today has two kinds of durable, committed project documentation:
`CLAUDE.md` / `AGENTS.md` (which describe **how to work** in the repo) and
per-feature specs under `.renmark/specs/` (which describe **one feature** at a
time). What it lacks is a single, durable answer to **what** the project is and
**why** — a Product Requirements Document that survives across features and acts
as the source of truth that plans, specs, and pipeline stages align to.

The user surfaced this gap directly: *"besides the initial instruction
[CLAUDE.md] I don't think we have anything like a PRD … a source of truth to
align plans."* This spec adds that artifact and the skill that authors it,
informed by a study of how TaskMaster (`eyaltoledano/claude-task-master`)
handles PRDs and task management.

**Driving goal (user's words):** a centralized source of truth for the project,
authored once and kept as **static living documentation** — updated only on
reviewed, approved change, not churned every feature.

## Prior art & references

Full research lives at
`.renmark/research/2026-06-05-prd-taskmaster.research.md` (TaskMaster README,
`task-structure.md`, `command-reference.md`, plus lean-PRD best-practice
sources). Key findings:

- TaskMaster mandates a single PRD (`.taskmaster/docs/prd.txt`) as the pipeline
  entry point, one-shot-parsed into `tasks.json`. **It does no PRD↔task sync** —
  the PRD is a seed, not a maintained source of truth.
- Lean-PRD best practice: problem, target users, goals & non-goals,
  requirements (as behaviors/outcomes), success metrics, scope boundaries, open
  questions — kept lightweight and updated as decisions resolve.
- renmark already exceeds TaskMaster on execution (parallel waves, per-task
  model routing, lifecycle+pipeline resume, formal approval gates, and a strict
  orchestrator-never-reads-code context-hygiene doctrine). The one thing it
  lacks is the **named, templated PRD**.

### renmark vs TaskMaster — comparison

| Dimension | TaskMaster | renmark (today) | Learning for renmark |
|---|---|---|---|
| **PRD artifact** | `.taskmaster/docs/prd.txt`, freeform `.txt`; mandated entry point | **None** — only CLAUDE.md + per-feature specs | **Adopt a named, templated PRD** (this feature) |
| **PRD → tasks** | `parse-prd` LLM-generates `tasks.json` in one pass | spec → `/renmark:plan` decomposes into atomic tasks | Equivalent; renmark's spec layer ≈ per-feature PRD |
| **Task model** | `tasks.json`: id/title/desc/status/deps/priority/details/testStrategy/subtasks | plan = markdown atomic tasks + executor tag + verifier; runtime status in `pipeline.json` | Could borrow status taxonomy (review/deferred/cancelled) + priority *(out of scope here)* |
| **Complexity** | 1–10 → recommends **subtask count** | complexity → **per-task model routing** (haiku/codex/sonnet/opus) | renmark's use is more cost-aware |
| **Dependencies** | DAG → serial `next` picker; `validate`/`fix-dependencies` integrity tools | DAG → **parallel wave execution** | renmark leads on concurrency; could borrow dep-integrity tooling *(out of scope)* |
| **State / resume** | `tasks.json` (status in-file, tagged per branch) | `lifecycle.json` + `pipeline.json`, `/renmark:resume` zero-LLM cold start | renmark leads |
| **Approval gates** | None formal | Machine-checked `human_review_*` gates; `/renmark:approve` | renmark leads |
| **Context hygiene** | MCP tool-mode tiers (7/15/36 tools) | Orchestrator **never reads generated code**; ≤5-line summaries | renmark leads — and this shapes the PRD design (below) |
| **PRD ↔ work sync** | **None** | N/A (no PRD yet) | **Opportunity to leapfrog: a lightweight drift check** (this feature) |

**Net:** renmark out-engineers TaskMaster on execution; the gap is the PRD
artifact itself. The differentiator this feature adds beyond TaskMaster is a
**lightweight PRD↔work drift check** — something TaskMaster does not have.

## Goals

1. **`PRD.md` artifact** — a single, committed, project-root document that is the
   durable source of truth. Markdown, with a provenance-metadata header and a
   fixed set of lean sections (below). Numbered `REQ-n` requirements to leave a
   hook for future traceability without enforcing it now.
2. **`/renmark:prd` skill** — standalone, with two modes:
   - **Create** (no `PRD.md`): interview the user (fresh project) or synthesize a
     draft from existing `CLAUDE.md` + specs + `CHANGELOG.md`; present for
     approval before writing.
   - **Update** (PRD exists): reconcile against current state, present a proposed
     diff, **write only after explicit human approval** (living doc, gated).
3. **Pipeline wiring:**
   - `/renmark:start` (new project): if no `PRD.md`, invoke `/renmark:prd` create
     mode as part of onboarding.
   - `/renmark:feature`: dispatch an **alignment subagent** that reads `PRD.md` +
     relevant docs *in isolation* and returns a bounded verdict; on drift, propose
     a permission-gated PRD update.
4. **Lightweight drift check** — a bounded check (not full requirements
   management): "does this feature have a home in the PRD? does it contradict a
   non-goal?" → ≤5-line flag + optional proposed PRD addition. Human approves or
   skips. Leapfrogs TaskMaster, which has no such check.
5. **Traceability note** — `/renmark:plan` adds a one-line `serves: REQ-n / new`
   note per task. Cheap, optional, no hard gating.
6. **Pointers** — one **plain-text** pointer line in `CLAUDE.md` and `AGENTS.md`
   (added in the same commit) directing readers to `PRD.md` and to the subagent
   alignment pattern. **Never an `@import`** (see Context Hygiene).

## Non-goals (this feature)

- The **prototype/schematic pipeline step** — explicitly the next, separate
  feature (recorded in memory). The PRD section layout should leave a natural
  home for it but this feature does not build it.
- Full `REQ-ID` enforcement in `/renmark:verify` (coverage gating).
- Hard PRD↔plan gating / blocking. Drift is a *flag*, not a *block*.
- Borrowing TaskMaster's task status taxonomy / dependency-integrity tooling —
  noted as future learnings, not built here.
- Migrating existing projects' specs into a PRD automatically (create mode can
  synthesize a draft on request, but no bulk migration).

## Architecture

### The artifact: `PRD.md` (project root, committed)

Location is the **project root**, a peer to `CLAUDE.md` / `CHANGELOG.md`.
Rationale (and a key context-hygiene finding): file location does **not** affect
context — only `CLAUDE.md`/`AGENTS.md` are auto-loaded by Claude Code. A
root-level `PRD.md` is never loaded until something explicitly reads it, so root
costs nothing over `.renmark/` and is the most discoverable home. Renmark's
"writes stay in the project" doctrine explicitly permits project-root docs.

Provenance header (consistent with renmark artifact doctrine):

```yaml
artifact_type: prd
schema_version: 1
created_at: ISO8601
last_reviewed: ISO8601
status: draft | approved
```

Lean sections (best-practice set from research):

1. **Vision / Problem** — what we're building and why (the WHY)
2. **Target users**
3. **Goals & Non-goals** — non-goals prevent scope creep
4. **Requirements** — numbered `REQ-1, REQ-2, …`, written as behaviors/outcomes
5. **Success metrics**
6. **Scope boundaries** — in / out / deferred
7. **Open questions**

### The skill: `/renmark:prd`

A new skill under `plugin/skills/prd/SKILL.md` plus a command wrapper at
`plugin/commands/prd.md`. Behavior:

- **Mode detection:** PRD present → update; absent → create.
- **Create:** if the project is fresh, interview one-question-at-a-time (reuse
  brainstorm's questioning style); if mature, synthesize a draft from
  `CLAUDE.md` + specs + `CHANGELOG.md`. Present the full draft for approval, then
  write `PRD.md` + a `## [date] — PRD created` CHANGELOG entry.
- **Update:** read current `PRD.md`, reconcile against the requested change,
  present a **diff**, and write only on explicit approval. Bump `last_reviewed`.
  Append a `## [date] — PRD updated` CHANGELOG entry.
- **Lifecycle:** updates are rare and human-gated — set/check the existing
  `human_review_*` gate fields where a PRD write is proposed by an automated
  stage.

### Pipeline wiring

- **`start`:** add a step — if no `PRD.md`, offer/invoke `/renmark:prd` create.
- **`feature` (router):** before/around planning, dispatch an **alignment
  subagent** (Agent tool, isolated context). The router passes the feature
  description + file scope; the subagent reads `PRD.md` + docs and returns:
  - `verdict`: `aligned` | `drift`
  - if drift: a ≤5-line reason + an optional proposed PRD addition (markdown)
  The router surfaces the verdict and, on drift, routes the proposed addition
  into `/renmark:prd` update mode (human-gated). The router/orchestrator
  **never reads the PRD body itself**.

## Context hygiene (renmark pillar — central to this design)

- **The orchestrator/router never loads the full PRD into context.** All PRD
  reading for alignment happens inside an **isolated subagent** that returns a
  bounded ≤5-line summary (G11 *orchestrate runs each task in isolation*; *the
  orchestrator coordinates, it does not accumulate*).
- **`PRD.md` is never `@import`-ed** into `CLAUDE.md`/`AGENTS.md`. The pointer is
  plain prose, so the PRD is not auto-loaded every session. Proposed pointer
  text:
  > *"Source of truth: `PRD.md`. For new features/changes, dispatch a subagent
  > to read `PRD.md` + docs and return a bounded alignment/drift summary — never
  > load the full PRD into the orchestrator."*
- The standalone `/renmark:prd` skill is the only place the full PRD is read, and
  that runs as its own dedicated invocation (not orchestrator accumulation).

## Components

| Component | Path | Change |
|---|---|---|
| PRD template | `plugin/templates/PRD.md.template` | new |
| prd skill | `plugin/skills/prd/SKILL.md` | new |
| prd command | `plugin/commands/prd.md` | new |
| Alignment subagent contract | `plugin/skills/_shared/` (e.g. `prd-alignment.md`) | new — the subagent brief + bounded return schema |
| start skill | `plugin/skills/start/SKILL.md` | edit — create-PRD step |
| feature skill | `plugin/skills/feature/SKILL.md` | edit — dispatch alignment subagent |
| plan skill | `plugin/skills/plan/SKILL.md` | edit — `serves: REQ-n` note per task |
| lifecycle / DOMAIN_BY_SKILL | `renmark/lifecycle.py` | edit — register `prd` (meta or build domain) |
| help / docs | `plugin/skills/help/SKILL.md`, README/CLAUDE.md tables | edit — list `/renmark:prd` |
| CLAUDE.md / AGENTS.md pointer | project root (renmark's own + template) | edit — plain-text pointer line |

## Success criteria

1. `/renmark:prd` in an existing project produces a valid `PRD.md` (all lean
   sections, valid metadata header) from existing docs, after approval.
2. `/renmark:prd` in a fresh project produces a `PRD.md` via interview.
3. Re-running `/renmark:prd` proposes a sensible diff and **never writes without
   explicit approval**.
4. `/renmark:feature` surfaces a `drift` verdict when a feature has no home in
   the PRD, and an `aligned` verdict when it does — via a subagent, with the PRD
   body never entering orchestrator context.
5. The CLAUDE.md/AGENTS.md pointer is plain text (no `@import`); `PRD.md` is not
   auto-loaded into a session.
6. All renmark dev gates pass: `pytest -q`, `ruff check`, `mypy .`.

## Open questions (for plan stage)

- Should `start`'s PRD step be mandatory or offered (skippable)?
- Where exactly does the alignment-subagent dispatch sit in the `feature` router
  ordering — before plan, or alongside it?
- Does the alignment subagent get its own tiny shared contract file, or inline
  brief in the feature skill?

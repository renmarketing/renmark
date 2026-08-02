---
name: rethink
description: "Use for the Brownfield Transformation pipeline (/renmark:rethink) when reassessing or migrating an EXISTING application — plain requests like \"rethink this app\", \"this codebase needs a rebuild plan\", \"help me modernize X\". Surveys before it structurally changes anything; for a brand-new project use /renmark:start, for a bounded addition within the existing direction use /renmark:feature."
---

# rethink

## Overview

The **Brownfield Transformation pipeline** — the counterpart to
`/renmark:start`'s greenfield lane. `start` assumes a blank slate; `rethink`
assumes a running system with users, data, integrations, and history that must
survive the transformation.

The working analogy (REQ-28): **renovating an occupied building.** You inspect
what exists before you swing a hammer, decide deliberately what stays and what
goes, and then renovate in usable sections — the building stays livable
throughout. There is no floor on which everything is demolished at once.

Concretely, rethink runs six bounded stages — survey → baseline →
classification → target blueprint → transformation roadmap → Owner gate — and
then hands the approved roadmap to renmark's **existing** milestone/Agency
execution machinery. It implements REQ-28 and extends REQ-5 (context hygiene),
REQ-22/REQ-27 (milestone execution), and REQ-4/REQ-12 (human gates).

**Nothing in this pipeline modifies production code.** Stages 1–5 produce
artifacts only. Structural change begins after the stage-6 Owner approval, and
then only through `orchestrate`/`feature`/`finish`.

## When to Use

- "This codebase needs a rebuild plan" / "help me modernize X"
- A legacy or inherited application whose architecture no longer fits its job
- A migration (framework, platform, data store, deployment target) where the
  current behavior must keep working throughout
- Accumulated drift: the system works, but nobody can say what should stay

**Use something else instead for:**

- A brand-new project with no existing system → `/renmark:start`
- A bounded addition or change that keeps the current direction → `/renmark:feature`
- Something specifically broken → `/renmark:debug`
- "What's next" within the existing plan → `/renmark:roadmap`

## Steps

**Step 0 — Context check.** Call `lifecycle.skill_preamble(repo, 'rethink')`.
If it returns a non-None hint, surface it as a one-line note.

**Slug.** Derive `<slug>` once from the transformation's name (lowercase,
non-alphanumerics to `-`) and use the same `.renmark/rethink/<slug>/` directory
for every stage artifact below.

### 1. Survey the current system

Dispatch **one bounded subagent** (Agent tool, `role: researcher`; fall back to
`general-purpose` only if no researcher profile is available) to read the target
project and report what actually exists:

- architecture and module boundaries; data flows and stores
- features **actually in use**, not merely declared (entry points, routes,
  call sites — a documented feature with no live caller is a finding)
- tests, integrations, deployment and ops dependencies
- pain and cost signals: `TODO`/`FIXME`/`HACK` density, test-coverage gaps,
  duplication, stale or unmaintained dependencies, known failure hotspots

**Reuse before re-deriving.** If the target already has
`.renmark/memory/project-map.md` (from `/renmark:init`), pass it to the subagent
as a starting input rather than re-deriving the map from scratch. If it is
missing or stale, route to `/renmark:init` first.

The subagent writes `.renmark/rethink/<slug>/survey.md` and returns **only** a
bounded ≤5-line summary (counts, top findings, artifact path). The survey body
never enters orchestrator context (REQ-5).

### 2. Establish a behavioral baseline

A second bounded subagent (same artifact directory) captures what must keep
working:

- current outputs and acceptance examples — the observable behavior users rely on
- any measurable performance / quality / cost baseline worth holding
- the concrete compatibility tests and checks that must stay green through the
  entire transformation

Written to `.renmark/rethink/<slug>/baseline.md`; bounded ≤5-line return only.

**This baseline is the contract for every later migration release.** No
structural change may regress it without an explicit, Owner-approved exception
recorded against the roadmap.

### 3. Classify the existing system

Using the survey + baseline (by pointer, never by body), classify every
identified component/capability as exactly one of:

| Class | Meaning |
|---|---|
| **Keep** | Works; stays as-is. No migration work. |
| **Improve** | Works; needs bounded rework, not replacement. |
| **Replace** | The target architecture supersedes it. |
| **Remove** | Dead weight; no longer earns its keep. |
| **Unknown — needs a spike** | Insufficient evidence to classify. Names a bounded, time- and scope-boxed investigation — never open-ended research. |

Written to `.renmark/rethink/<slug>/classification.md`. Every `Unknown` entry
must carry its spike's scope and stop condition; an unbounded `Unknown` is a
defect in the classification, not a valid outcome.

### 4. Create the target blueprint

Written to `.renmark/rethink/<slug>/target-blueprint.md`, covering:

- desired capabilities and system boundaries
- new architecture **only where the classification justifies it** — i.e. for
  `Replace` items. `Keep` and `Improve` components do not get redesigned here.
- explicit migration constraints: what must not break (from stage 2), plus any
  budget/timeline limits
- an explicit **non-goals** list — what this transformation is deliberately
  not attempting

**Diagrams reuse `/renmark:blueprint`.** Use its existing
Mermaid-from-`.renmark/memory/project-map.md` convention for the **current**
state diagram, paired with a **target** state diagram in the same form. Do not
invent a separate diagramming approach.

### 5. Produce a transformation roadmap

A sequence of **small, independently usable releases** — never a big-bang
rewrite. Each release states:

- the user-observable capability it delivers
- its own compatibility guarantee (which baseline checks it must keep green)
- its rollback path

Old and new components may coexist temporarily; that coexistence is a normal,
planned state, not a defect.

**Format reuse (mandatory).** The roadmap is built as a `renmark.program` —
`renmark.program.write_program(repo, program)` with the existing
`Program`/`StageNode` shapes already used by `/renmark:roadmap`'s forward-plan
mode. Do **not** invent a parallel roadmap format.

**First-release default (hard).** The first release in the roadmap is
**"baseline and compatibility coverage"** — turning stage 2's baseline into
real, runnable compatibility tests — not any architecture replacement. Only an
explicit Owner override may reorder it, and the override is recorded on the
program.

### 6. Owner gate, then hand off to milestone execution

Before any stage transitions from planning to execution, present the
classification + target blueprint + roadmap as a **bounded summary** and require
**one explicit `AskUserQuestion` approval**. This is the REQ-4/REQ-12 human
gate; it follows the milestone-approval pattern in
`${CLAUDE_PLUGIN_ROOT}/skills/.shared/agency-delivery.md` (read by pointer — do
not restate its mechanics here).

On approval, activate renmark's **existing** Agency/milestone execution
machinery — `renmark.agency.activate(repo, ...)` plus the `Program` written in
stage 5 — rather than building a rethink-only executor:

- **Architect** — the target structure, already produced in stage 4
- **Engineer** — the migration milestones, i.e. the `Program` stages from stage 5
- **Workers** — bounded per-milestone changes, via the existing
  `orchestrate` / `feature` dispatch path
- **Inspectors** — verify both that old behavior is preserved (stage-2
  baseline/compatibility tests) **and** that the new capability is delivered
- **Owner** — accepts each usable release, through `/renmark:finish`'s existing
  accept/release gate (do not duplicate it)

**Rethink's responsibility ends at handing off an Owner-approved `Program`.**
It does not re-implement orchestrate or finish.

### Context hygiene throughout

Every stage's heavy artifact — survey, baseline, classification, blueprint,
roadmap body — is written to `.renmark/rethink/<slug>/` on disk. Between stages
the orchestrator sees only bounded **≤5-line** summaries plus artifact paths
(REQ-5). No stage may read a prior stage's full artifact body back into the
primary conversation; a later stage that needs detail dispatches a subagent
pointed at the path.

## Do not

- **Do not implement or restructure anything** before the Owner approves the
  baseline, the Keep/Improve/Replace/Remove classification, and the first
  migration milestone. This is REQ-28's acceptance criterion — stages 1–5 change
  no production code.
- **Do not invent a parallel execution system.** Reuse `renmark/agency.py`,
  `renmark/program.py`, `/renmark:orchestrate`, and `/renmark:finish`. A
  rethink-only executor, roadmap format, or release gate is a defect.
- **Do not default the first release to architecture replacement.** The first
  release is baseline/compatibility coverage unless the Owner explicitly
  overrides it on the record.
- **Do not skip the survey or baseline stages** — not even for a project the
  user says they already know well, and not even for one you just built.
  Evidence before claim (the project's "Verification before completion" rule).
- **Do not pull artifact bodies into orchestrator context.** Bounded summaries
  and paths only (REQ-5).
- **Do not propose a big-bang rewrite**, or a release with no compatibility
  guarantee and no rollback path.

## What's next

*End by calling `renmark.lifecycle.next_steps(repo, "rethink")` and render the
result per `${CLAUDE_PLUGIN_ROOT}/skills/.shared/next-steps.md` (class 1 —
Tier-0 stage routing). Present via `AskUserQuestion` (handoff-menu.md rules
6–9); the state-derived next command is the `(Recommended)` option. Require an
explicit choice — never auto-proceed.*

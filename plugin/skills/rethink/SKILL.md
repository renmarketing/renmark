---
name: rethink
description: "Use for the Brownfield Modernization pipeline (/renmark:rethink) when reassessing or migrating an EXISTING application — plain requests like \"rethink this app\", \"this codebase needs a rebuild plan\", \"help me modernize X\". Surveys internally, benchmarks externally, binds to PRD acceptance criteria, and assesses modularity before it structurally changes anything; for a brand-new project use /renmark:start, for a bounded addition within the existing direction use /renmark:feature."
---

# rethink

## Overview

The **Brownfield Modernization pipeline** — the counterpart to `/renmark:start`'s
greenfield lane. `start` assumes a blank slate; `rethink` assumes a running
system with users, data, integrations, PRD commitments, and history that must
survive the transformation.

The working analogy (REQ-28): **renovating an occupied building.** You inspect
what exists, check it against the contract (the PRD), compare it to how the
trade has moved on outside your walls, assess whether the building's internal
structure can actually support what you want to build next, decide
deliberately what stays and what goes, and then renovate in usable sections —
the building stays livable throughout. There is no floor on which everything
is demolished at once.

Concretely, rethink runs its existing **nine bounded stages** — internal
survey → behavioral baseline → PRD acceptance contract → external
benchmarking → modularity/scalability assessment → evidence-based
classification → target modular blueprint → incremental transformation
roadmap → Owner gate — unchanged, plus a **Transformation Intake** ahead of
stage 1 and three named Owner decision gates threaded through the same
sequence at the points where a real decision is made: the **Discovery
Direction Gate** (after stage 5, before stage 6), the **Solution Gate**
(after stage 7, before stage 8), and the **Execution Gate** (stage 9,
elaborated). A cross-cutting **exception check-in** can interrupt any stage
on a material issue rather than waiting for its scheduled gate. None of this
adds a new stage, a parallel roadmap format, or a rethink-only executor —
see "Exception check-in" and "Gate rules," below, and each gate's own
section. It implements REQ-28 and extends REQ-5 (context hygiene),
REQ-22/REQ-27 (milestone execution), and REQ-4/REQ-12 (human gates). Every
bounded subagent dispatch, artifact-pointer pattern, and gate in this
pipeline is also bound by REQ-30 (orchestration efficiency is a protected
capability) — a stage may add a durable artifact, never retained
orchestrator context or a duplicate dispatch.

**Nothing in this pipeline modifies production code.** Stages 1–8 (plus the
Transformation Intake, the Discovery Direction Gate, and the Solution Gate)
produce artifacts and decisions only. Structural change begins after the
stage-9 Execution Gate's Owner approval, and then only through
`orchestrate`/`feature`/`finish`.

## When to Use

- "This codebase needs a rebuild plan" / "help me modernize X"
- A legacy or inherited application whose architecture no longer fits its job
- A migration (framework, platform, data store, deployment target) where the
  current behavior must keep working throughout
- Accumulated drift: the system works, but nobody can say what should stay,
  whether it still meets the PRD, or how it compares to where the market moved

**Use something else instead for:**

- A brand-new project with no existing system → `/renmark:start`
- A bounded addition or change that keeps the current direction → `/renmark:feature`
- Something specifically broken → `/renmark:debug`
- "What's next" within the existing plan → `/renmark:roadmap`

## Exception check-in (cross-cutting)

Any stage from Transformation Intake onward can hit something that cannot
wait for its stage's scheduled gate. When it does, stop the current stage
immediately and run an **exception check-in** rather than folding the issue
silently into the next scheduled gate. Trigger a check-in on:

- a **material PRD/Owner-intent conflict** — stage 3's PRD acceptance
  contract surfaces a requirement that contradicts the Transformation
  Intake's stated outcome or protected behavior
- **unreliable or blocked research** — stage 1 or stage 4 comes back
  `blocked`/`incomplete`, or a finding's evidence strength is too low to act
  on, on a point that matters for the decision at hand
- a **major cost/scope/security impact** — anything that would materially
  change the transformation's size, its attack surface, or its ongoing cost,
  discovered mid-stage
- a **proposed behavior removal or incompatibility** — a classification or
  blueprint decision that would break something the Transformation Intake
  named as protected behavior
- a **high-impact unknown that cannot be safely bounded** — a spike
  candidate whose scope, evidence requirement, or budget can't be pinned down
  well enough to record as a normal `Unknown` entry

**Behavior:** pause only the affected decision — do not discard completed
work, and do not stop stages that don't depend on the exception. Present the
specific finding, why it's material, and the concrete options (never raw
research, logs, or a technical questionnaire) via one `AskUserQuestion` call,
in the order findings → implications → recommendation → alternatives → exact
decision, recommending one option clearly. Get one explicit Owner decision.
Record it in the stage's artifact (a dated note, not a silent rewrite) before
resuming. A stage that triggers a check-in still reaches its own scheduled
gate afterward, carrying the decision forward as one of its inputs.

## Gate rules

These apply to the Discovery Direction Gate, the Solution Gate, the
Execution Gate, and every exception check-in:

- **Never infer approval from silence or an earlier unrelated approval.**
  Each gate requires its own explicit decision; approving the direction does
  not approve the blueprint, and approving the blueprint does not approve
  the roadmap.
- **No agent in this pipeline may approve its own recommendation.** The
  subagent that proposes a direction, a classification, or a roadmap is not
  the approver of it — the Owner is, every time.
- **Never show raw research, logs, or a technical questionnaire.** Every
  gate presents findings → implications → recommendation → alternatives →
  the exact decision required — never the artifact body.
- **Recommend one option clearly** and ask only Owner-level questions —
  never a technical detail resolvable from evidence already gathered.
- **Persist every approval, rejection, exception, and resulting direction**
  in the stage's artifact — durable, dated, never conversation-only.
- **On rejection, return to the stage that owns the rejected decision** —
  not to the start of the pipeline. A rejected direction (Discovery Direction
  Gate) returns to stage 6 (classification) with the Owner's alternative
  chosen instead, not to stage 1. A rejected solution (Solution Gate) returns
  to stage 6/7 (classification/blueprint) for revision, not to research. A
  rejected roadmap (Execution Gate) returns to stage 8 (roadmap), reusing
  every already-approved upstream artifact.
- **Resume from the last approved checkpoint.** A resumed rethink run reads
  `lifecycle.skill_preamble`/existing stage artifacts under
  `.renmark/rethink/<slug>/` before re-dispatching anything — a stage whose
  artifact already exists and whose gate (if any) already cleared is reused,
  never re-run and never re-asked. Only the first unresumed stage dispatches
  a subagent or presents a gate.
- **Gates must not add routine status interruptions between mandatory
  decisions.** Three named gates plus the exception check-in are the entire
  interaction surface — no additional "here's what I'm doing now" prompts
  between them.

## Steps

**Step 0 — Context check.** Call `lifecycle.skill_preamble(repo, 'rethink')`.
If it returns a non-None hint, surface it as a one-line note.

**Slug.** Derive `<slug>` once from the transformation's name (lowercase,
non-alphanumerics to `-`) and use the same `.renmark/rethink/<slug>/` directory
for every stage artifact below.

### 0a. Transformation Intake

Before dispatching stage 1, confirm — directly with the Owner, asking only
**blocking** questions (resolve anything resolvable from stage 1's own
evidence instead of asking):

- the **desired outcome** — what this transformation is for
- **protected behavior** — what must keep working no matter what changes
  (feeds stage 2's baseline as a named input, not a replacement for it)
- **constraints** — timeline, budget, platform, or team limits already known
- **non-goals** — what this transformation is deliberately not attempting
- **areas open to change** — what the Owner already expects to be
  restructured, vs. what should be treated as settled

Record the answers in `.renmark/rethink/<slug>/intake.md`; bounded ≤5-line
return only. This does not replace stage 2's baseline or stage 3's PRD
contract — it is the Owner-stated intent those stages verify evidence
against, and it is the reference point the exception check-in uses to detect
a material PRD/Owner-intent conflict or a proposed removal of protected
behavior.

### 1. Internal system survey

Dispatch **one bounded subagent** (Agent tool, `role: researcher`; fall back to
`general-purpose` only if no researcher profile is available) to read the
**target repository** and report what actually exists:

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

This is **internal, repository-grounded research only** — it never leaves the
codebase and never stands in for stage 4's external benchmarking. The
subagent writes `.renmark/rethink/<slug>/survey.md` and returns **only** a
bounded ≤5-line summary (counts, top findings, artifact path). The survey body
never enters orchestrator context (REQ-5).

### 2. Behavioral baseline

A second bounded subagent (same artifact directory) captures what must keep
working:

- current outputs and acceptance examples — the observable behavior users rely on
- any measurable performance / quality / cost baseline worth holding
- the concrete compatibility tests and checks that must stay green through the
  entire transformation

Written to `.renmark/rethink/<slug>/baseline.md`; bounded ≤5-line return only.

**This baseline is the contract for every later migration release regarding
what must not break.** It is deliberately **not** the same thing as stage 3's
PRD acceptance contract — the baseline says what the app *currently does*;
the PRD contract says what the app *is required to do*. Existing behavior is
not correct merely because it exists — see stage 3.

### 3. PRD acceptance contract

A bounded subagent extracts the product's binding requirements and maps the
current system against them — this stage is mandatory and precedes
classification.

- Extract every applicable PRD goal, requirement, non-goal, constraint, and
  acceptance criterion. Assign a stable identifier to any criterion that lacks
  one (e.g. `AC-<n>`) **without silently rewriting the PRD** — new identifiers
  are additive annotations, not edits to PRD prose.
- For each requirement, map: current implementation → current behavioral
  evidence → compliance status (`met` / `partial` / `failed` / `untestable` /
  `unverified`) → proposed target behavior → planned roadmap release →
  verification method.
- Flag requirements that are missing, ambiguous, contradictory, obsolete, or
  untestable as-written.
- Separate **blocking PRD debt** (a requirement the transformation cannot
  proceed past without resolution) from **deferrable specification debt** (a
  gap worth recording but not gating this transformation).
- Any material conflict between current behavior and the PRD, or any proposed
  PRD change, is **not** resolvable by the subagent or by rethink itself — it
  triggers the exception check-in (above) immediately rather than waiting
  for a later gate (or, for a standalone PRD edit, routes to `/renmark:prd`'s
  own UPDATE gate).

Written to `.renmark/rethink/<slug>/prd-acceptance-map.md`; bounded ≤5-line
return only (requirement count, compliance breakdown, count of blocking
conflicts, artifact path).

**Binding rule:** a transformation cannot be reported complete while an
applicable PRD acceptance criterion remains failed, omitted, unverified, or
changed without explicit Owner approval. Every roadmap release produced in
stage 8 must carry PRD-traceable acceptance scenarios and a deterministic
verification method wherever one is possible.

### 4. External discovery and benchmarking

A separate bounded subagent (Agent tool, `role: researcher`) performs
**external** research — distinct from stage 1's internal survey and never a
substitute for it. Scope the research to what actually matters for this
product's domain and goals, not a generic best-practices dump:

- comparable software and direct/adjacent competitors
- current industry-standard workflows and capabilities in this domain
- proven patterns for architecture, modularity, integration, security,
  observability, testing, deployment, UX, and maintainability relevant to the
  application
- common limitations, failure modes, and migration lessons from comparable
  transformations
- opportunities for parity, differentiation, simplification, or leapfrogging

**Evidence discipline.** Every finding records its source, access date,
evidence strength, applicability to this product, and limitations. The
artifact separates three tiers explicitly:
- **Verified external facts** (sourced, checkable)
- **Inferences** (reasoned from facts, not directly sourced)
- **Recommendations** (what to do about it) — plus an explicit **Unknowns**
  list for anything that needs a bounded spike, not open-ended research.

**Honesty about access.** If external access (`WebSearch`/`WebFetch`) is
unavailable or fails, the subagent reports this stage **blocked** or
**incomplete** in its returned status — it must never silently fall back to
model memory and present that as completed research. A blocked/incomplete
external-benchmark stage is a valid, honest outcome that still requires
Owner visibility before the pipeline proceeds past stage 9; it is never
quietly upgraded to "done."

Written to `.renmark/rethink/<slug>/external-benchmark.md`; bounded ≤5-line
return only (stage status — `complete`/`blocked`/`incomplete` — finding count,
top parity gap or differentiator, artifact path).

### 5. Modularity, scalability, and maintainability assessment

A bounded subagent evaluates the current system's internal structure —
distinct from stage 1's feature-level survey, focused specifically on
architectural health:

- domain and service boundaries; module responsibilities and cohesion
- coupling and dependency direction; circular dependencies
- oversized modules/classes/functions; duplicated logic and fragmented ownership
- data ownership and transaction boundaries
- public APIs, internal contracts, and versioning
- provider/adaptor replaceability; plugin and extension points
- configuration and environment boundaries
- test isolation and testability; observability and failure containment
- deployment/runtime boundaries where justified; scaling bottlenecks
- security and permission boundaries
- how easily a feature can be added, replaced, or removed today

Produces a **current-state module/dependency map** and a **target modular
architecture** showing module ownership, responsibilities, public
interfaces/contracts, allowed dependency directions, data boundaries,
integration/adaptor boundaries, extension points, and migration seams.

**Avoid speculative microservices.** Prefer the smallest architecture that
creates clear ownership, replaceable boundaries, testability, scaling
capacity, and maintainability — a justified boundary, not a fashionable one.

Written to `.renmark/rethink/<slug>/modularity-assessment.md`; bounded ≤5-line
return only (module count, top coupling/scaling risk, artifact path).

### 5a. Discovery Direction Gate

After stages 1–5 (survey, baseline, PRD acceptance contract, external
benchmark, modularity assessment) and before stage 6 classification or stage
7 blueprint work begins, present one bounded summary and require an
explicit Owner direction. This gate governs *direction* — which of the
several plausible transformation strategies the evidence supports — not the
classification or blueprint detail, which come after it.

Present, via `AskUserQuestion`:

- **Material findings and implications** — the handful of facts from stages
  1–5 that actually change the direction, and what each means for this
  transformation (pointers to the stage artifacts, never their bodies)
- **Gaps** — where the PRD, the architecture, a needed capability, or the
  research is materially incomplete or in tension with the Transformation
  Intake
- **Recommended transformation direction** — one concrete direction, marked
  `(Recommended)`
- **Up to two viable alternatives** — real alternative directions, not token
  options
- **Assumptions, risks, and the exact Owner decisions required** — what's
  being taken as given, what could go wrong, and the specific choice this
  gate is asking the Owner to make

If any of stages 1–5 returned `blocked`/`incomplete` on a point material to
this decision, or if a finding contradicts the Transformation Intake's
protected behavior, that is an exception check-in (above), not a normal
gate — resolve it first.

Require one explicit choice — never auto-proceed on the recommendation, and
never infer it from an earlier unrelated approval. Record the chosen
direction as a dated append to the relevant stage artifact (never a silent
rewrite). **On rejection:** re-present the alternatives, or — only if the
Owner's feedback surfaces a genuine evidence gap — route back to the
specific stage (1–5) that needs more evidence; do not restart the pipeline.

### 6. Evidence-based classification

Using stages 1–5 (by pointer, never by body), classify every identified
component/capability as exactly one of:

| Class | Meaning |
|---|---|
| **Keep** | Works; stays as-is. No migration work. |
| **Improve** | Works; needs bounded rework, not replacement. |
| **Replace** | The target architecture supersedes it. |
| **Remove** | Dead weight; no longer earns its keep. |
| **Unknown — needs a spike** | Insufficient evidence to classify. Names a bounded, time- and scope-boxed investigation — never open-ended research. |

**Every classification decision must cite its evidence**: the internal
survey/baseline finding that grounds it, its PRD-acceptance impact (from
stage 3), external evidence where relevant (stage 4), and its modularity
impact (stage 5). A classification with no cited evidence is a defect, not a
valid entry.

**Architectural redesign is not limited to `Replace`.** An `Improve` item may
require decomposition, boundary extraction, dependency inversion, or
interface stabilization identified in stage 5 — without replacing its
behavior. Modularity findings must be able to move an item's classification
or its treatment within a classification; do not silo modularity work behind
`Replace` only.

Written to `.renmark/rethink/<slug>/classification.md`. Every `Unknown` entry
must carry its spike's question, scope, evidence requirement, budget, and stop
condition — an unbounded `Unknown` is a defect in the classification, not a
valid outcome.

### 7. Target modular blueprint

Written to `.renmark/rethink/<slug>/target-blueprint.md`, covering:

- desired capabilities and system boundaries, traced to the PRD requirements
  they satisfy (stage 3) and to the classification decisions that justify them
  (stage 6)
- new or restructured architecture for `Replace` items (new design) **and**
  `Improve` items whose stage-5/6 evidence calls for boundary extraction,
  decomposition, dependency inversion, or interface stabilization — `Keep`
  items are not redesigned here
- module contracts, dependency directions, data ownership, and integration
  boundaries from stage 5, carried into the target state
- explicit migration constraints: what must not break (stage 2), plus any
  budget/timeline limits
- an explicit **non-goals** list — what this transformation is deliberately
  not attempting

**Diagrams reuse `/renmark:blueprint`.** Use its existing
Mermaid-from-`.renmark/memory/project-map.md` convention for the **current**
state diagram, paired with a **target** state diagram in the same form. Do not
invent a separate diagramming approach.

### 7a. Solution Gate

After stage 6's classification and stage 7's blueprint, before stage 8's
roadmap is finalized, present one bounded summary and require an explicit
Owner approval. This gate approves the *solution* — what changes and what's
protected — not yet the roadmap sequencing, which gets its own gate (stage 9).

Present:

- **Behavioral and PRD changes** — what the classification/blueprint would
  change relative to today's behavior and relative to the PRD acceptance
  contract (stage 3)
- **Protected behavior** — confirmation that the Transformation Intake's
  protected behavior is honored, or an explicit flag where it is not
- **Module/data/integration boundaries** — the stage 7 blueprint's key
  ownership and dependency-direction decisions
- **Removals, incompatibilities, and migration risks** — every `Remove`
  classification, every planned incompatibility, and the risk each carries
- **Material tradeoffs, exclusions, and unresolved decisions** — where the
  simplest-maintainable-design preference (stage 5) traded off against a
  more elaborate option, the blueprint's non-goals, and anything left as a
  bounded spike rather than a resolved choice

**No agent in this pipeline may self-approve a structural recommendation.**
A blocking research gap, an unresolved PRD conflict, a proposed removal of
protected behavior, or an unresolved architectural spike stops this gate
from clearing — it does not get silently waved through into stage 8. Any of
those is grounds for the exception check-in (above) if it surfaced *before*
this gate was reached.

Require one explicit `AskUserQuestion` approval — never inferred from the
Discovery Direction Gate's earlier, unrelated approval. **On rejection:**
return to stage 6/7 (classification/blueprint) for revision, reusing stages
1–5's artifacts unchanged — do not re-run research or re-ask the
Transformation Intake.

### 8. Incremental transformation roadmap

A sequence of **small, independently usable, user-testable releases** — never
a big-bang rewrite. Each release states:

- the user-observable capability/value it delivers
- the PRD acceptance criteria (stage 3) it satisfies or advances
- its own compatibility guarantee (which stage-2 baseline checks it must keep
  green) and its verification method
- its migration steps, its observability/monitoring hook, and its rollback path
- an Owner-facing acceptance scenario for demoing the release

Old and new components may coexist temporarily; that coexistence is a normal,
planned state, not a defect.

**Format reuse (mandatory).** The roadmap is built as a `renmark.program` —
`renmark.program.write_program(repo, program)` with the existing
`Program`/`StageNode` shapes already used by `/renmark:roadmap`'s forward-plan
mode. Do **not** invent a parallel roadmap format.

**First-release default (hard).** The first release in the roadmap is
**"baseline and compatibility coverage"** — turning stage 2's baseline into
real, runnable compatibility tests — not any architecture replacement. Only an
explicit Owner override, backed by stage 3/4/5 evidence, may reorder it, and
the override plus its justification is recorded on the program.

### 9. Execution Gate, then hand off to milestone execution

Before any stage transitions from planning to execution, present the
**incremental transformation roadmap** (stage 8) — its release outcomes, the
PRD criteria (stage 3) each satisfies, each release's compatibility
guarantee, dependencies, migration steps, verification method, observability
hook, rollback path, and Owner acceptance scenario — and require **one
explicit `AskUserQuestion` approval** before any target production code
changes or Agency execution begins. This is the REQ-4/REQ-12 human gate; it
follows the milestone-approval pattern in
`${CLAUDE_PLUGIN_ROOT}/skills/.shared/agency-delivery.md` (read by pointer — do
not restate its mechanics here).

This gate approves *execution* specifically — the Discovery Direction Gate
already approved direction, and the Solution Gate already approved the
classification and blueprint; do not re-litigate either here, and do not
infer this gate's approval from either of theirs. **No agent in this
pipeline may self-approve a structural recommendation.** Every
classification, blueprint, and roadmap decision remains a proposal until
this gate clears it.

**On rejection:** return to stage 8 (roadmap) for revision, reusing stages
1–7's approved artifacts and decisions unchanged — do not re-run research,
re-dispatch classification, or re-ask either earlier gate.

On approval, activate renmark's **existing** Agency/milestone execution
machinery — `renmark.agency.activate(repo, ...)` plus the `Program` written in
stage 8 — rather than building a rethink-only executor:

- **Architect** — the target structure, already produced in stage 7
- **Engineer** — the migration milestones, i.e. the `Program` stages from stage 8
- **Workers** — bounded per-milestone changes, via the existing
  `orchestrate` / `feature` dispatch path
- **Inspectors** — verify both that old behavior is preserved (stage-2
  baseline/compatibility tests) **and** that the PRD acceptance criteria
  (stage 3) and the new capability are delivered
- **Owner** — accepts each usable release, through `/renmark:finish`'s existing
  accept/release gate (do not duplicate it)

**Rethink's responsibility ends at handing off an Owner-approved `Program`.**
It does not re-implement orchestrate or finish.

### Context hygiene throughout

Every stage's heavy artifact — survey, baseline, PRD-acceptance map, external
benchmark, modularity assessment, classification, blueprint, roadmap body — is
written to `.renmark/rethink/<slug>/` on disk. Between stages the orchestrator
sees only bounded **≤5-line** summaries plus artifact paths (REQ-5). No stage
may read a prior stage's full artifact body back into the primary
conversation; a later stage that needs detail dispatches a subagent pointed at
the path. Stages 1–8 are **read-only regarding the target application's
production code** — they write only under `.renmark/rethink/<slug>/` and
renmark's own governance/state paths.

## Do not

- **Do not implement or restructure anything** before the Owner approves the
  PRD acceptance contract, the external-benchmark findings, the modularity
  assessment, the Keep/Improve/Replace/Remove classification, and the first
  migration milestone. This is REQ-28's acceptance criterion — stages 1–8
  change no production code.
- **Do not treat the internal survey as external research**, and do not treat
  the external-benchmark stage as optional. They are separate mandatory stages
  with separate artifacts; conflating or skipping either is a defect.
- **Do not report the external-benchmark stage complete** when external access
  was unavailable or failed. Report `blocked`/`incomplete` honestly — never
  substitute model memory and call it research.
- **Do not treat current behavior as correct because it exists.** The
  behavioral baseline (stage 2) and the PRD acceptance contract (stage 3) are
  different concepts; passing the baseline never substitutes for satisfying
  the PRD.
- **Do not report the transformation complete** while an applicable PRD
  acceptance criterion is failed, omitted, unverified, or changed without
  explicit Owner approval.
- **Do not skip the modularity assessment**, and do not restrict architectural
  redesign to `Replace` items only — an `Improve` item may need boundary
  extraction, decomposition, dependency inversion, or interface stabilization
  without a full replacement.
- **Do not propose speculative microservices** or any boundary not justified
  by stage 5's evidence.
- **Do not invent a parallel execution system.** Reuse `renmark/agency.py`,
  `renmark/program.py`, `/renmark:orchestrate`, and `/renmark:finish`. A
  rethink-only executor, roadmap format, or release gate is a defect.
- **Do not default the first release to architecture replacement.** The first
  release is baseline/compatibility coverage unless the Owner explicitly
  overrides it on the record, backed by evidence.
- **Do not skip the survey, baseline, PRD-acceptance, or external-benchmark
  stages** — not even for a project the user says they already know well, and
  not even for one you just built. Evidence before claim (the project's
  "Verification before completion" rule).
- **Do not pull artifact bodies into orchestrator context.** Bounded summaries
  and paths only (REQ-5).
- **Do not propose a big-bang rewrite**, or a release with no PRD-traceable
  acceptance scenario, no compatibility guarantee, or no rollback path.
- **Do not let any agent self-approve a structural recommendation.** The
  Discovery Direction Gate, the Solution Gate, and the Execution Gate are the
  sole approval surfaces for this pipeline — never the subagent that
  proposed the thing being approved.
- **Do not infer any gate's approval from silence or from a different gate's
  approval.** The Discovery Direction Gate, the Solution Gate, and the
  Execution Gate are three distinct decisions; approving one is not
  approving another.
- **Do not show raw research, logs, or a technical questionnaire at any
  gate.** Every gate presents findings → implications → recommendation →
  alternatives → the exact decision required — never the artifact body.
- **Do not add a routine status prompt between the three named gates.** The
  Discovery Direction Gate, the Solution Gate, the Execution Gate, and the
  exception check-in are the entire interaction surface — no extra
  "here's what I'm about to do" interruptions.
- **Do not fold a material PRD/Owner-intent conflict, unreliable/blocked
  research, a major cost/scope/security impact, a proposed removal of
  protected behavior, or an unbounded high-impact unknown into the next
  scheduled gate.** Run the exception check-in immediately.
- **Do not re-run a completed stage or re-ask a cleared gate on resume.** A
  resumed rethink run reads existing stage artifacts and gate decisions
  under `.renmark/rethink/<slug>/` before dispatching anything new.

## What's next

*End by calling `renmark.lifecycle.next_steps(repo, "rethink")` and render the
result per `${CLAUDE_PLUGIN_ROOT}/skills/.shared/next-steps.md` (class 1 —
Tier-0 stage routing). Present via `AskUserQuestion` (handoff-menu.md rules
6–9); the state-derived next command is the `(Recommended)` option. Require an
explicit choice — never auto-proceed.*

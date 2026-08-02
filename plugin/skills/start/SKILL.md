---
name: start
description: "Use for the New Build pipeline (/renmark:start) when starting something new from scratch — plain requests like \"build X\", \"create X\", \"develop X\", \"use Agency\", or \"use Orchestrator\". The vibe-coder entry point when you don't know where to begin; for changes to an existing build use /renmark:feature instead."
---

# start

## Overview

The **New Build pipeline** — the vibe-coder entry point for building something new. Ask what you want to build, and renmark handles the rest — stack selection, scope, external evidence, best practices, a binding PRD, deliberate module boundaries, and routing — without requiring any knowledge of specs, plans, or executors.

**Pipeline (Complex scope):** intent intake → external research **or an approved fast-path waiver** → **Discovery Direction Gate** → solution design (PRD + PRD acceptance/traceability contract + prospective modular blueprint) → **Solution Gate** → incremental release roadmap → **Execution Gate** → handoff to existing Agency/milestone execution → verify → review. **Simple scope** collapses everything from external research through the Execution Gate into one documented waiver inside the existing Step-5 confirmation — intent intake → waiver+confirm → PRD → build → verify → review, unchanged from before this contract existed.

renmark continues automatically and pauses only at the real gates in the Pause Policy (`${CLAUDE_PLUGIN_ROOT}/skills/.shared/handoff-menu.md`) plus this pipeline's three named Owner gates — the Discovery Direction Gate, the Solution Gate, and the Execution Gate — and an **exception check-in** that can interrupt any stage on a material conflict, unreliable research, a major cost/scope/security implication, or a high-impact unknown (see "Exception check-in," below). Each of the three gates and the exception check-in requires one explicit Owner decision; none auto-proceeds.

**Proportional to scope, not brownfield.** This is greenfield discovery, not `/renmark:rethink`'s brownfield survey — there is no existing system to survey, no compatibility baseline to hold, and no Keep/Improve/Replace/Remove classification. What `start` borrows from `rethink` is the *discipline*: cite evidence, bind to the PRD, design module boundaries deliberately, and gate execution on explicit Owner approval — applied to a system that doesn't exist yet.

**Bound by REQ-30** (orchestration efficiency is a protected capability): the Simple-scope fast path stays a single confirmation, the three Complex-scope gates stay the entire interaction surface (no routine status prompts between them), and every subagent dispatch in this pipeline (research, PRD-acceptance mapping, blueprint) returns a bounded ≤5-line summary plus an artifact pointer — never a full body into orchestrator context.

**Adaptive routing (Step 7) stays intact:** a clear single-purpose build → straight to `/renmark:plan`; a fuzzy or multi-part idea → `/renmark:brainstorm` first; a whole greenfield product → the staged program. A `PRD.md` is established before the first feature is built (Step 5a); for a **Complex** scope, external research (Step 4.5), the Discovery Direction Gate (Step 4.6), a PRD acceptance contract (Step 5a-ii), a modular blueprint (Step 5b), the Solution Gate (Step 5c), and the Execution Gate (Step 7a) are now **mandatory**, not offered. For a **Simple** scope they collapse into one documented waiver inside the existing Step-5 confirmation — the two-follow-up-question promise is unchanged, and no additional gate is added.

## Delivery mode

Resolve the once-per-run `delivery_mode` through canonical DeliveryState. Reuse
an existing choice without another gate; otherwise present the shared
interaction-contract decision with **Agency (Recommended)** for a vague product
idea and **Orchestrator (Recommended)** for a defined build. An explicit owner
choice always wins. Agency owns discovery, PRD/roadmap governance, milestones,
and owner checkpoints, then delegates every approved milestone's execution to
Orchestrator. Orchestrator takes a defined outcome directly through its bounded
build → verify → review → fix loop. Persist the choice in
`.renmark/state/delivery.json`; selector/page state is presentation-only.

The legacy `agency.json` may retain phase-detail compatibility, but it is not a
third mode and never overrides canonical DeliveryState. Use
`${CLAUDE_PLUGIN_ROOT}/skills/.shared/interaction-contract.md` for the decision
surface and `${CLAUDE_PLUGIN_ROOT}/skills/.shared/agency-delivery.md` for the
Agency governance contract. Status remains ordinary prose.

## Exception check-in (cross-cutting — Complex scope)

Any stage from Step 4.5 onward can hit something that cannot wait for its
stage's normal gate. When it does, stop the current stage immediately and
run an **exception check-in** rather than folding the issue silently into the
next scheduled gate. Trigger a check-in on:

- a **material PRD conflict** — the PRD acceptance contract (Step 5a-ii)
  surfaces a requirement that contradicts a decision already made, or a
  change to `PRD.md` that isn't a routine addition
- **unreliable research** — Step 4.5 comes back `blocked`/`incomplete`, or a
  finding's evidence strength is too low to act on, on a point that matters
  for the decision at hand
- a **major cost/scope/security implication** — anything that would
  materially change the build's size, its attack surface, or its ongoing
  cost, discovered mid-stage
- a **high-impact unknown** — a spike candidate whose answer would change the
  direction, not just a detail, of the solution

**Behavior:** present the specific finding, why it's material, and the
concrete options (never raw research or a wall of caveats) via one
`AskUserQuestion` call. Get one explicit Owner decision. Record it in the
stage's artifact (a dated note, not a silent edit) before resuming that
stage. An exception check-in is a targeted interrupt, not a replacement for
the Discovery Direction Gate, the Solution Gate, or the Execution Gate — a
stage that triggers one still reaches its own scheduled gate afterward,
carrying the decision forward as one of its inputs. A high-impact unknown
that survives a check-in without resolution becomes a bounded spike (question,
scope, evidence requirement, budget, stop condition) recorded on the roadmap
— never a silent assumption.

## Steps

**Step 0 — Context and contract freshness check.** Before any planning, deterministically inspect `CLAUDE.md` and `AGENTS.md` with `renmark.init.contract_is_fresh(text, repo)`. If either guidance file or its managed project-delivery contract is missing, or either contract is stale, immediately call `renmark.init.merge_project_delivery_contract(repo)`. This is an automatic maintenance step: do not show a user gate, copy contract prose, or write either guidance file directly. `merge_project_delivery_contract` is init's sole safe merge primitive; if it reports malformed managed markers, stop and surface that concrete blocker.

Then call `lifecycle.skill_preamble(repo, 'start')`. If it returns a non-None hint, surface as a one-line note (do not block — user decides). Also check `lifecycle.read_lifecycle(repo)` — if a feature is in flight (`stage != 'released'` and not None), redirect: *"There's an in-flight feature `<feature>` at stage `<stage>`. Run `/renmark:resume` to continue it, or `/renmark:start` will override."*

Optionally, only when the global auto-routing rule is missing (`global_routing.detect_global_rule()` returns `missing` or `present-without-rule`), append one unobtrusive line to the context note — never a prompt, never a menu, and never repeated mid-build: *"tip: `/renmark:doctor --install-routing` makes renmark the default everywhere."* If the rule is already present, say nothing.

### 1. Open with one question

Ask exactly this, nothing else:

> "What do you want to build or create? Describe it however feels natural — one sentence or ten, your call."

Do not mention specs, plans, executors, or any renmark terminology. Do not ask about tech stack yet.

---

### 2. Assess the response

> *The canonical scope questions (Q1–Q3) and their menus live in `.shared/scope-contract.md`; the tables in Steps 2–4 below are their rendering for vibe coders — do not improvise alternatives.*

From the description, determine silently:

**Complexity:**
- *Simple* — single purpose, clear inputs/outputs, likely < 5 tasks (e.g., "a script that...", "a page that shows...", "a tool to convert...")
- *Complex* — multiple features, system design needed, unclear boundaries (e.g., "a platform for...", "an app where users can...", "something that manages...")

**Stack signal:**
- Script, automation, data → Python
- CLI tool, developer utility → Python or Node.js
- Web app, dashboard, CRUD → Node.js + Express or Python + FastAPI
- Interactive UI, visual → browser frontend + Vite or React
- Mobile → React Native

**Deployment signal:**
- No mention of others, public, server, users → assume local
- "others will use it", "public", "my team", "online" → deployable

---

### 3. Adaptive follow-up (at most 2 questions, only when needed)

Ask only when the answer would meaningfully change what gets built AND cannot be
reasonably inferred. Ask one at a time through
`renmark.interaction.build_selector`. Infer the safest likely answer and mark it
as the sole recommendation at index 0; when no answer can be inferred, put `Not
sure yet (Recommended)` first. The numbered lists below are the full fallback.

**Q1 — Reach** (ask if deployment signal is ambiguous):
> "Is this just for you, or will other people use it?"
> 1. [a] Just me — local machine is fine
> 2. [b] Others / my team — needs to be accessible to more people
> 3. [c] Not sure yet

**Q2 — Lifespan** (ask if complexity is ambiguous):
> "Is this a one-time run or something you'll use regularly?"
> 1. [a] One-time / occasional — keep it simple, I'll run it manually
> 2. [b] Regular use — worth making it maintainable and easy to update
> 3. [c] Not sure yet

Skip both questions for clearly scoped requests. Never ask about tech stack, architecture, or framework preferences — infer them.

---

### 4. Auto-select stack and scope

Apply silently using these defaults:

| Signal | Default stack |
|---|---|
| "script", "automate", "batch", "process" | Python |
| "CLI", "command line", "developer tool" | Python or Node.js CLI |
| "web app", "dashboard", "CRUD", "admin" | Node.js + Express + SQLite |
| "data", "CSV", "analysis", "ML" | Python |
| "page", "site", "landing" | Static HTML/JS + Vite |
| "real-time", "chat", "live" | Node.js + Socket.io |
| "mobile", "iOS", "Android" | React Native |

**Deployment default:**
- Local unless "others", "public", "team", "online", or "server" was mentioned
- If local: no auth, no deployment config, no cloud setup
- If deployable: include basic deployment notes and .env config

**MVP scope default:**
- First version = simplest thing that does the described job
- Exclude: admin panels, analytics, payment integrations, user roles, mobile apps — unless explicitly requested

---

### 4.5. External discovery — or an approved fast-path waiver

**Slug.** Derive `<slug>` once from the confirmed description (lowercase,
non-alphanumerics to `-`) and use `.renmark/start/<slug>/` for every artifact
this step and Steps 5a-ii/5b produce.

**Complex scope:** before the PRD is finalized, dispatch **one bounded
subagent** (Agent tool, `role: researcher`; fall back to `general-purpose`
only if no researcher profile is available) to research, scoped to this
product's actual domain and goals — not a generic best-practices dump:

- comparable products and direct/adjacent competitors
- domain-standard workflows and the capabilities users of this kind of product
  already expect
- architecture, UX, integrations, security, observability, deployment, and
  scaling patterns relevant to the confirmed stack/scope
- common failure modes in comparable builds

**Evidence discipline** — same as `/renmark:rethink`'s external-benchmark
stage: every finding records its source, access date, evidence strength,
applicability, and limitations; the artifact separates **verified external
facts**, **inferences**, **recommendations**, and an explicit **unknowns**
list (each unknown a bounded spike: question, scope, evidence requirement,
budget, stop condition — never open-ended research). Note parity expectations
(what users will assume exists) and differentiation opportunities.

**Research informs; it never overrides.** The Owner's Step-1 intent is
authoritative. Findings, implications, and any recommended direction they
suggest are carried forward into Step 4.6's Discovery Direction Gate — never
silently substituted for the user's stated goal ahead of that gate.

**Honesty about access.** If `WebSearch`/`WebFetch` is unavailable or fails,
the subagent reports this stage `blocked` or `incomplete` in its returned
status — it must never silently fall back to model memory and present that as
completed research. A `blocked`/`incomplete` status on a point that matters
for the direction decision triggers the exception check-in (above) rather
than silently proceeding to Step 4.6 as if research were complete.

Written to `.renmark/start/<slug>/external-research.md`; bounded ≤5-line
return only (status — `complete`/`blocked`/`incomplete` — top parity gap or
differentiator, artifact path).

**Simple scope — documented waiver instead.** A single-purpose, clearly
scoped build (script, small tool, < 5 tasks) skips this stage through an
explicit, recorded waiver rather than a silent skip. Fold the waiver into the
Step-5 confirmation as one extra line naming: **reason** (why the fast path
applies — e.g. "single-purpose script, no competitive surface"), **risk**
(what's foregone — e.g. "no check against comparable-tool patterns or known
failure modes"), and **scope** (what's skipped — external research, the
Discovery Direction Gate, the Solution Gate, the Execution Gate, and the
Step 5b modular blueprint). The user's existing "Ready? [Y/n]" answer IS the
explicit Owner approval of that waiver — do not add any of the three gates.
Record the waiver line in the same CHANGELOG scope entry Step 4.5/5 writes
(see `.shared/scope-contract.md`).

If a build initially assessed as Simple grows in scope mid-build (new
requirements push it past "< 5 tasks"), re-run this step as Complex before
continuing — the waiver does not travel with scope creep.

---

### 4.6. Discovery Direction Gate

**Complex scope only.** Before the PRD is drafted, present one bounded
summary of Step 4.5's research and require an explicit Owner decision on
direction. This gate governs *direction*, not architecture (Step 5c) or
execution (Step 7a) — it exists so the PRD gets written toward a direction
the Owner actually chose, not one the research subagent picked by default.

Present, via `AskUserQuestion`:

- **Findings** — the top few facts/inferences from `external-research.md`
  (pointer + ≤5-line digest, never the artifact body)
- **Implications** — what those findings mean for this build specifically
- **Recommended direction** — one concrete direction, marked `(Recommended)`
- **Viable alternatives** — at least one real alternative direction, not a
  token option
- **Assumptions** — what's being taken as given if the recommendation is chosen
- **Risks** — what could go wrong with the recommended direction
- **Exact decisions required** — the specific choices this gate is asking the
  Owner to make (e.g. "match the category-standard onboarding flow, or
  differentiate on X")

If Step 4.5 returned `blocked`/`incomplete` on a point material to this
decision, that is an exception check-in (above), not a normal gate — resolve
it before presenting this gate's menu.

Require one explicit choice — never auto-proceed on the recommendation.
**For Complex scope, this gate replaces Step 5's plain-language "Ready?"
confirmation** — do not ask both; the chosen direction carries forward as
Step 5's summary is built from it. Record the chosen direction in
`external-research.md`'s artifact (a short dated append, not a rewrite).

---

### 5. Confirm in plain language

**Simple scope only** — for Complex scope, Step 4.6 already obtained the
equivalent explicit confirmation; skip this step and continue directly to
Step 5a.

Present a summary before building:

> "Here's what I'll build:
>
> **[1–2 sentence plain-English description of the output]**
>
> Stack: [inferred stack, briefly]
> Scope: [what's included, what's not for this version]
> Fast path — skipping external research, the Discovery Direction/Solution/Execution gates, and a modular blueprint (single-purpose, small scope); risk: no check against comparable-tool patterns.
>
> I'll also include error handling, a README with setup instructions, and basic tests so it works out of the box.
>
> Ready? [Y/n — or tell me if anything looks off]"

Wait for explicit confirmation before continuing. If the user redirects, adjust the summary and confirm again. Do not proceed on silence. This confirmation is also the Owner's explicit approval of the Step-4.5 waiver — no separate waiver gate.

**Implementation note (internal — never shown to the user):** the vibe-coder
build path MAY run as a bounded **Loop Mode** under the hood — the
iterate-until-verified engine that keeps refining until the smoke test passes or
a budget is hit. This is an implementation detail of how `start` drives the
build; it does NOT add a third question. Fold the loop's two knobs into the
single Step-5 confirmation already shown above:

- **Budget** — a sensible default effort ceiling for the iterate cycle.
- **Max iterations** — a sensible default cap on refinement passes.

Pick sensible defaults silently and state them plainly inside the existing
summary (e.g. *"I'll keep refining until the tests pass, within a sensible
effort budget"*). Confirm goal + budget + max-iterations in that ONE plain-English
confirmation — do NOT add a fourth bullet that reads like a new interrogation,
and do NOT surface the word "loop", "iteration budget", or any engine jargon to
the user. Once confirmed, drive the bounded loop and route normally (Step 7).
The word "loop" stays inside these internal notes only.

**Repeated-issue pre-attempt gate for loop iterations (deterministic).** If the
bounded loop detects a repair is needed before attempting the next iteration (e.g.
build output indicates a fixable error), call `recurrence.pre_attempt()` before
retry:

```python
from renmark import recurrence

decision = recurrence.pre_attempt(
    repo, check="start-build-loop", rule_id="build-iteration-failure",
    target="initial-build"
)
if decision is not None and decision.retry_blocked:
    # STOP the iteration; render bounded handoff per handoff-menu.md
```

Surface at most five lines: `occurrence_count`, fingerprint evidence, `summary_lines`,
and recommended action. Offer the three choices (patch/debug, durable guard, retry once)
per `${CLAUDE_PLUGIN_ROOT}/skills/.shared/handoff-menu.md`, then call
`recurrence.acknowledge_issue()` to record the selected action. A `retry_once`
selection must re-enter this pre_attempt gate before the next loop iteration; never
bypass it.

---

### 5a. Establish the PRD before building

The New Build pipeline produces a `PRD.md` before the first feature is built — it's the source of truth the roadmap and features align to. This is a Pause-Policy gate (#2 PRD approval): the human owns the PRD, so confirm before writing it. If `PRD.md` is missing, scale the effort to the scope:

- **Simple scope** (a single-purpose script or tool): draft a minimal PRD — goal, users, success criteria — from the confirmed Step-5 summary, show it in ~5 lines, and continue once the user okays it. Don't run a full interview.
- **Complex / multi-feature scope**: invoke `/renmark:prd` (create mode) for a proper pass — hand it the Step-4.5 `external-research.md` artifact **pointer** (never its body) as optional supporting input, not as a requirement source. Then return here and continue to Step 5a-ii.

If `PRD.md` already exists, skip silently. Don't turn this into a heavy interrogation for small builds — but don't skip it either; the PRD is what keeps the build from drifting.

---

### 5a-ii. PRD acceptance / traceability contract

**Complex scope, after PRD approval:** dispatch a bounded subagent to extract
the PRD's applicable goals, requirements, constraints, non-goals, and
acceptance criteria and map each to: planned behavior, the target
module/contract that will implement it (cross-reference Step 5b once it
exists, or note "pending Step 5b" if this runs first), the roadmap release
that will deliver it, its verification method, and its current
evidence/status (`planned` — nothing is built yet, so status here is about
whether the criterion is even testable, not whether it currently passes).
Assign a stable identifier (`AC-<n>`) to any criterion that lacks one, as an
additive annotation — never a silent PRD rewrite.

Flag requirements that are missing, ambiguous, contradictory, or untestable
as-written. Any material PRD or scope change this surfaces is **not**
resolvable by the subagent — route it to `/renmark:prd`'s own UPDATE gate for
Owner approval before continuing.

Written to `.renmark/start/<slug>/prd-acceptance-map.md`; bounded ≤5-line
return only (criterion count, flagged-criterion count, artifact path).

**Binding rule:** no release may be reported complete while an applicable PRD
acceptance criterion is failed, omitted, unverified, or changed without
explicit Owner approval — this is enforced at `/renmark:verify` /
`/renmark:finish` time, same as any other acceptance evidence; this step's
job is only to make the mapping explicit before code exists.

**Simple scope:** no separate artifact. The minimal PRD's goal/success
criteria (Step 5a) already double as the acceptance contract — record one
line naming the required smoke test (Step 6) as their verification method,
inside the same PRD note. No new gate.

---

### 5b. Prospective modular blueprint

**Complex scope: mandatory before execution, not merely offered.** Before any
build task is dispatched, establish deliberate module boundaries — this is
architecture applied to a system that doesn't exist yet, not a redesign of
one that does. Cover:

- domain/module boundaries and responsibilities
- dependency direction (which modules may depend on which — and which
  direction is disallowed)
- data ownership per module; public APIs / internal contracts
- provider/adaptor boundaries (what's swappable — LLM provider, storage,
  auth) and extension points
- test seams, observability hooks, and failure containment
- security/permission boundaries
- realistic scaling pressures for this product, if any are foreseeable now

Produce a **target dependency map**: module ownership, responsibilities,
public interfaces, allowed dependency directions, data boundaries, and
replaceable integration seams. **Prefer the simplest maintainable design** —
avoid speculative microservices and premature abstraction; a boundary earns
its place by a concrete responsibility or replaceability need, not by
convention.

**Reuse `/renmark:blueprint`** for the diagram — its Mermaid convention, not a
new one. Invoke it and continue to Step 5a-ii/5c once it completes; do not
route around it with a bespoke diagram format. Written alongside
`SCHEMATIC.md` (blueprint's own artifact) plus a short
`.renmark/start/<slug>/modularity-notes.md` capturing the dependency-direction
rules above that don't fit `SCHEMATIC.md`'s diagram format.

**Simple scope:** stays offered/skippable under the Step-4.5 waiver — a
diagram of one file is still noise. If offered and declined, or the scope is
simple, skip silently:

> "This has enough moving parts to be worth a quick blueprint via `/renmark:blueprint` — a living `SCHEMATIC.md` (architecture overview, module map, data flow), plus a `PROTOTYPE.html` mock-up if there's a UI. Want me to generate it before we build?
>
> 1. [a] Yes — run `/renmark:blueprint` now before we continue
> 2. [b] Skip — continue with the normal next step"

---

### 5c. Solution Gate

**Complex scope only** (Simple scope's Step-5 confirmation already serves as
its sole gate — do not add this step for Simple builds). Before Step 6 or the
roadmap is finalized, present one bounded summary of the solution just
designed (Steps 5a/5a-ii/5b) and require **one explicit `AskUserQuestion`
approval** before continuing. This gate approves the *solution* — scope and
design — not yet the roadmap (Step 7) or execution (Step 7a); those get their
own gates once they exist.

Present:

- **Scope** — what's in and out for this build (from Step 5a's PRD)
- **Workflows** — the user-observable workflows the PRD commits to
- **Requirements** — the Step 5a-ii traceability contract's criterion count
  and any flagged/ambiguous/untestable items
- **Module boundaries** — the Step 5b blueprint's key ownership and
  dependency-direction decisions
- **Exclusions** — the PRD's non-goals and the blueprint's explicit
  "not doing this now" calls
- **Unresolved decisions** — anything Step 5a-ii or 5b left as a bounded
  spike rather than a resolved choice
- **Material tradeoffs** — where the simplest-maintainable-design preference
  (Step 5b) traded off against a more elaborate option, and why

**No agent in this pipeline may self-approve a structural or scope
decision.** A blocking research gap, an unresolved PRD conflict, or an
unresolved architectural spike stops this gate from clearing — it does not
get silently waved through into Step 6. Any of those is also grounds for the
exception check-in (above) if it surfaced *before* this gate was reached;
this gate is where anything not already resolved gets its explicit decision.

Every material decision surfaced here — a stack deviation from Step 4's
inference, an architecture choice in Step 5b, a scope cut — must cite: the
Owner's Step-1 goal, its PRD impact, relevant external evidence (Step 4.5,
where applicable), its modularity/scaling impact (Step 5b), the alternatives
considered, and any unresolved assumption. An `Unknown` that can't be
resolved here becomes a bounded spike (question, scope, evidence requirement,
budget, stop condition) recorded on the roadmap, never an open-ended one.

On approval: continue to Step 6, then Step 7's routing to build the roadmap.
Steps 4.5 through 5c write only under `.renmark/start/<slug>/`, `PRD.md` (via
`/renmark:prd`'s own gate), and `SCHEMATIC.md`/`PROTOTYPE.html` (via
`/renmark:blueprint`) — still no target application code, which waits for
Step 7a's Execution Gate.

---

### 6. Inject best practices into plan context

Before routing to the next step, establish these as non-negotiable task requirements. Do NOT add them as separate tasks — weave them into the task specs for the relevant implementation tasks:

**Always:**
- Error handling with plain-language user messages (no raw stack traces)
- Input validation at every system boundary (user input, file reads, API calls)
- Secrets and config in `.env` (never hardcoded) — always include `.env.example`
- `README.md` — what it does, how to install, how to run, one example
- `.gitignore` — env files, caches, `node_modules`, `__pycache__`, build output
- At least one smoke test that exits 0 when the core feature works

**Web app additions:**
- No credentials or tokens in API responses
- Basic input sanitization (prevent obvious injection)

**CLI additions:**
- `--help` flag with usage description
- Clean exit codes (0 = success, non-zero = error)

**Data tool additions:**
- Graceful handling of empty or malformed input
- Clear output format documented in README

---

### 7. Route to pipeline

**Simple, clear scope** (single purpose, < 5 tasks, stack obvious):
→ Invoke `/renmark:plan` with the confirmed description + injected best practices as context.
Tell the user: *"Let me put together the build plan now..."*

**Complex, multi-feature, or design decisions needed** (multiple systems, unclear architecture, UX questions):
→ Invoke `/renmark:brainstorm` with the confirmed description as starting context, skipping the empty-folder bootstrap question (already handled by start).
Tell the user: *"This has a few moving parts — let me ask a couple of design questions before we start building so we get the structure right..."*

**Greenfield whole-product / program — offered branch (feature-planner mode):**
When the user's description signals a full product or multi-stage program from scratch ("build a platform", "build an entire app", "I want to create a full system", or any scope that implies ordered stages rather than a single deliverable), offer a third routing option before proceeding:

> "This sounds like a full product — multiple stages, each building on the last.
> I can plan this as a **staged program**: brainstorm the stages first, then drive
> each stage through the normal pipeline in order, tracking progress automatically.
>
> 1. [a] **Staged program** — plan the whole product as an ordered program (recommended for greenfield builds)
> 2. [b] **Single feature** — treat it as one feature and plan it now
> 3. [c] Not sure yet — walk me through it"

- If the user chooses **[a]**: invoke `/renmark:brainstorm` with the description as context, then route the brainstorm output through `/renmark:roadmap` **forward plan mode** (`plugin/skills/roadmap/SKILL.md` — forward plan mode section) to derive an ordered stage→task program and emit a `renmark.program` (persisted to `.renmark/state/program.json`). The staged driver (`renmark.program_driver`) then sequences stages; each stage runs the normal brainstorm→plan→orchestrate→verify pipeline. Each program stage carries the release-level fields Step 5c's Solution Gate already gathered: the user-observable value it delivers, the Step 5a-ii PRD criteria (`AC-<n>`) it satisfies, the Step 5b module/contract it touches, its dependencies, its verification method, its observability hook, and an Owner acceptance scenario — reusing the same `Program`/`StageNode` shape `/renmark:rethink`'s roadmap stage writes, never a parallel format.
- If the user chooses **[b]** or **[c]**, or if the scope is clearly a single deliverable: fall through to the default routing above. For Complex scope, the single feature IS the one release — `/renmark:verify`/`/renmark:finish` still check it against the Step 5a-ii criteria before it's reported done. Do NOT offer this branch again.

This branch is additive: the default adaptive one-question routing above remains the default for all single-feature work. Do NOT surface "staged program", "program.json", "feature-planner", or driver terminology to the user — use plain-English equivalents only ("staged plan", "step-by-step program").

Do NOT mention plan files, spec files, or executor types to the user.

---

### 7a. Execution Gate

**Complex scope only.** By the time Step 7's routing produces a concrete
roadmap — `/renmark:plan`'s plan for a single-feature build, or the
`renmark.program` for a staged program — no target application code exists
yet. Before `/renmark:orchestrate` (or the staged driver's first build stage)
runs, present that roadmap/plan and require **one explicit Owner approval**.
For a single-feature build this release-level summary is exactly the
program-stage field list above, applied to the one release; for a staged
program it is the program's ordered stage list.

This gate is realized through the same `next_steps` handoff `AskUserQuestion`
menu Step 7 already ends on (below) — for Complex scope, that menu's content
IS this gate: it must show the roadmap/plan summary, not just a bare
"run `/renmark:orchestrate` next" recommendation, and the user's explicit
selection of that recommended option IS the Execution Gate's approval. This
is not a second, separate menu — it is the existing handoff upgraded to
carry load-bearing content for Complex builds.

**No target application code changes before this gate clears.** Steps 4.5
through 7a write only under `.renmark/start/<slug>/`, `PRD.md`, `program.json`
/ the plan artifact, and `SCHEMATIC.md`/`PROTOTYPE.html` — the first target
code is written only after `/renmark:orchestrate` (or the staged driver)
starts, which happens only after this gate's explicit approval.

---

### 8. Handoff to execution

Once the Execution Gate clears (Complex scope) or the Step-5 confirmation
clears (Simple scope), hand off to renmark's **existing** milestone/Agency
execution machinery — the "Delivery mode" section above, `/renmark:orchestrate`,
and the staged `program_driver` — exactly as `start` already does today.
This step names that handoff explicitly; it does not add a new executor,
mirroring `/renmark:rethink`'s own stage 9 handoff.

The routing above IS the next step — defer its presentation to the shared
next-step contract (class 1 — Tier-0 stage routing):

> *End by calling `renmark.lifecycle.next_steps(repo, "start")` and render the
> result per `${CLAUDE_PLUGIN_ROOT}/skills/.shared/next-steps.md` (class 1 —
> Tier-0 stage routing). Present via `AskUserQuestion` (handoff-menu.md rules
> 6–9); the state-derived next command is the `(Recommended)` option. Require an
> explicit choice — never auto-proceed.*

### Heartbeat cron hint (optional, non-blocking)

Before presenting the handoff menu, run:

```bash
renmark-execute --heartbeat-check-cron
```

If output is `not-installed`, add one optional menu item to the `AskUserQuestion` handoff:

> **Set up heartbeat monitor** (optional) — run every 30 min to auto-resume if a usage limit is hit:
> `(crontab -l 2>/dev/null; echo "*/30 * * * * cd <repo> && renmark-execute --heartbeat --auto-resume") | crontab -`
> Replace `<repo>` with the actual repo path from `lifecycle.json`.

This is purely informational. The user can skip it. It never gates the handoff or blocks the recommended action.

---

## Common Mistakes

| Mistake | Fix |
|---|---|
| Asking about tech stack | Never ask — infer and state in the summary |
| Mentioning "spec", "plan", "executor", "orchestrate" | Use plain English: "build plan", "next step", "run the tasks" |
| Asking more than 2 follow-up questions | Cap at 2 — infer everything else |
| Proceeding without confirmation | Always wait for explicit yes before routing |
| Adding best practices as separate tasks | Weave them into implementation task specs |
| Running full external research + blueprint + all three gates on a Simple build | Fold a one-line documented waiver into the existing Step-5 confirmation instead — no new gate |
| Reporting a Complex build's PRD acceptance criteria "unverified" as if that were fine at ship time | It's fine at Step 5a-ii (nothing is built yet); it is a blocker at `/renmark:verify`/`/renmark:finish` |
| Treating Step 4.5's research as a second source of requirements | Research informs; only the Owner's stated intent + the approved PRD set requirements |
| Skipping the Step 5b blueprint for a Complex build because "it's obvious" | Mandatory for Complex scope — skip only under the Simple-scope waiver |
| Asking Step 5's plain-language confirmation AND Step 4.6's Discovery Direction Gate for a Complex build | Step 4.6 replaces Step 5 for Complex scope — never both |
| Folding a material PRD conflict, a `blocked` research finding, or a high-impact unknown into the next scheduled gate instead of stopping | Run the exception check-in immediately — it's a targeted interrupt, not deferred to the Discovery Direction/Solution/Execution gate |
| Writing any build code before the Step 7a Execution Gate clears (Complex) or Step 5 confirms (Simple) | Steps 4.5–7a are artifacts + gates only — no target code until `/renmark:orchestrate` runs |

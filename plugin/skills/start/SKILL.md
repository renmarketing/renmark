---
name: start
description: "Use for the New Build pipeline (/renmark:start) when starting something new from scratch — plain requests like \"build X\", \"create X\", \"develop X\". The vibe-coder entry point when you don't know where to begin; for changes to an existing build use /renmark:feature instead."
---

# start

## Overview

The **New Build pipeline** — the vibe-coder entry point for building something new. Ask what you want to build, and renmark handles the rest — stack selection, scope, best practices, PRD, and routing — without requiring any knowledge of specs, plans, or executors.

**Pipeline:** intent → (brainstorm if fuzzy) → PRD → roadmap → first feature → plan → build → verify → review. renmark continues automatically and pauses only at the real gates in the Pause Policy (`${CLAUDE_PLUGIN_ROOT}/skills/_shared/handoff-menu.md`) — chiefly unclear intent, PRD approval, and cost.

**Adaptive routing (Step 7) stays intact:** a clear single-purpose build → straight to `/renmark:plan`; a fuzzy or multi-part idea → `/renmark:brainstorm` first; a whole greenfield product → the staged program. A `PRD.md` is established before the first feature is built (Step 5a); a blueprint is offered only when the architecture is non-trivial (Step 5b).

## Operating mode

`start` defaults to **Orchestrator** mode for goal-level build-out — it drives the whole pipeline to a working deliverable, not one edit at a time. The first meaningful workflow is where the mode is chosen: ask once, persist the choice, and don't re-ask. Either mode (Orchestrator or **Conductor**) is overridable at any time via `renmark-execute --set-mode`.

## When Agency Mode is active

`/renmark:start` is the **explicit opt-in entry** for Agency Mode — no auto-detect. When chosen, offer an Agency lane that frames the session as a discovery call: owner intent, users, problem, outcome, owner-level questions, and project classification (new app / feature / migration / automation / research-build). Agency Mode sits **above** Conductor/Orchestrator and does not replace them; existing `/renmark:start` behavior is unchanged when the Agency lane is not chosen. For the full contract, see `${CLAUDE_PLUGIN_ROOT}/skills/_shared/agency-delivery.md`.

**Seed the state on opt-in (required — this is what makes the loop enterable/resumable).** Once the owner opts in and you've established the first phase, activate agency state so `/renmark:resume` and every spine skill's preamble pick it up. Run exactly:

```bash
python3 -c "from renmark import agency; agency.activate('.', current_phase='discovery', current_milestone='<first milestone>', signoff_status='pending')"
```

This writes `.renmark/state/agency.json` (verify: `python3 -c "from renmark import agency; print(agency.is_active('.'))"` → `True`). Update `current_phase`/`current_milestone` as the delivery loop advances; call `renmark.agency.deactivate('.')` only at final signoff/release. Do NOT seed agency state unless the owner explicitly chose the Agency lane.

## Steps

**Step 0 — Context check.** Call `lifecycle.skill_preamble(repo, 'start')`. If it returns a non-None hint, surface as a one-line note (do not block — user decides). Also check `lifecycle.read_lifecycle(repo)` — if a feature is in flight (`stage != 'released'` and not None), redirect: *"There's an in-flight feature `<feature>` at stage `<stage>`. Run `/renmark:resume` to continue it, or `/renmark:start` will override."*

Optionally, only when the global auto-routing rule is missing (`global_routing.detect_global_rule()` returns `missing` or `present-without-rule`), append one unobtrusive line to the context note — never a prompt, never a menu, and never repeated mid-build: *"tip: `/renmark:doctor --install-routing` makes renmark the default everywhere."* If the rule is already present, say nothing.

### 1. Open with one question

Ask exactly this, nothing else:

> "What do you want to build or create? Describe it however feels natural — one sentence or ten, your call."

Do not mention specs, plans, executors, or any renmark terminology. Do not ask about tech stack yet.

---

### 2. Assess the response

> *The canonical scope questions (Q1–Q3) and their menus live in `_shared/scope-contract.md`; the tables in Steps 2–4 below are their rendering for vibe coders — do not improvise alternatives.*

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

Ask only when the answer would meaningfully change what gets built AND cannot be reasonably inferred. Ask one at a time. **Ask each via the `AskUserQuestion` tool (arrow-selectable choices) when available**; the numbered lists below are the text fallback for non-interactive sessions (accept a number or bracket letter).

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

### 5. Confirm in plain language

Present a summary before building:

> "Here's what I'll build:
>
> **[1–2 sentence plain-English description of the output]**
>
> Stack: [inferred stack, briefly]
> Scope: [what's included, what's not for this version]
>
> I'll also include error handling, a README with setup instructions, and basic tests so it works out of the box.
>
> Ready? [Y/n — or tell me if anything looks off]"

Wait for explicit confirmation before continuing. If the user redirects, adjust the summary and confirm again. Do not proceed on silence.

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

---

### 5a. Establish the PRD before building

The New Build pipeline produces a `PRD.md` before the first feature is built — it's the source of truth the roadmap and features align to. This is a Pause-Policy gate (#2 PRD approval): the human owns the PRD, so confirm before writing it. If `PRD.md` is missing, scale the effort to the scope:

- **Simple scope** (a single-purpose script or tool): draft a minimal PRD — goal, users, success criteria — from the confirmed Step-5 summary, show it in ~5 lines, and continue once the user okays it. Don't run a full interview.
- **Complex / multi-feature scope**: invoke `/renmark:prd` (create mode) for a proper pass, then return here and continue to Step 6.

If `PRD.md` already exists, skip silently. Don't turn this into a heavy interrogation for small builds — but don't skip it either; the PRD is what keeps the build from drifting.

---

### 5b. Offer a blueprint when the architecture is non-trivial

Only relevant when the build has real structure to draw — a complex/multi-feature scope, or any browser UI. For a simple single-purpose script, skip silently (a diagram of one file is noise). When it does apply and `SCHEMATIC.md` does **not** exist, offer once — do not block, never auto-run:

> "This has enough moving parts to be worth a quick blueprint via `/renmark:blueprint` — a living `SCHEMATIC.md` (architecture overview, module map, data flow), plus a `PROTOTYPE.html` mock-up if there's a UI. Want me to generate it before we build?
>
> 1. [a] Yes — run `/renmark:blueprint` now before we continue
> 2. [b] Skip — continue with the normal next step"

- If the user chooses **[a]**: invoke `/renmark:blueprint`, then return here and continue to Step 6 once it completes.
- If the user chooses **[b]**, if the scope is simple, or if `SCHEMATIC.md` already exists: skip silently and continue.

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

- If the user chooses **[a]**: invoke `/renmark:brainstorm` with the description as context, then route the brainstorm output through `/renmark:roadmap` **forward plan mode** (`plugin/skills/roadmap/SKILL.md` — forward plan mode section) to derive an ordered stage→task program and emit a `renmark.program` (persisted to `.renmark/state/program.json`). The staged driver (`renmark.program_driver`) then sequences stages; each stage runs the normal brainstorm→plan→orchestrate→verify pipeline.
- If the user chooses **[b]** or **[c]**, or if the scope is clearly a single deliverable: fall through to the default routing above — do NOT offer this branch again.

This branch is additive: the default adaptive one-question routing above remains the default for all single-feature work. Do NOT surface "staged program", "program.json", "feature-planner", or driver terminology to the user — use plain-English equivalents only ("staged plan", "step-by-step program").

Do NOT mention plan files, spec files, or executor types to the user.

The routing above IS the next step — defer its presentation to the shared
next-step contract (class 1 — Tier-0 stage routing):

> *End by calling `renmark.lifecycle.next_steps(repo, "start")` and render the
> result per `${CLAUDE_PLUGIN_ROOT}/skills/_shared/next-steps.md` (class 1 —
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

---
name: start
description: Use when a vibe coder wants to build something and doesn't know where to begin — the plain-English entry point for the full renmark pipeline. Adaptive: one open question, at most 2 follow-ups, then routes to plan or brainstorm automatically.
---

# start

## Overview

The vibe coder entry point. Ask what you want to build, and renmark handles the rest — stack selection, scope, best practices, and pipeline routing — without requiring any knowledge of specs, plans, or executors.

## Steps

**Step 0 — Context check.** Call `lifecycle.skill_preamble(repo, 'start')`. If it returns a non-None hint, surface as a one-line note (do not block — user decides). Also check `lifecycle.read_lifecycle(repo)` — if a feature is in flight (`stage != 'released'` and not None), redirect: *"There's an in-flight feature `<feature>` at stage `<stage>`. Run `/renmark:resume` to continue it, or `/renmark:start` will override."*

### 1. Open with one question

Ask exactly this, nothing else:

> "What do you want to build or create? Describe it however feels natural — one sentence or ten, your call."

Do not mention specs, plans, executors, or any renmark terminology. Do not ask about tech stack yet.

---

### 2. Assess the response

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

### 5a. Offer PRD creation (new projects only)

Check whether `PRD.md` exists at the project root. If it does **not** exist, offer once — do not block:

> "Would you like me to create a `PRD.md` for this project? It captures the goal, users, and success criteria as a living source of truth — useful when the project grows or when handing off context.
>
> 1. [a] Yes — run `/renmark:prd` now before we continue
> 2. [b] Skip — continue with the normal next step"

- If the user chooses **[a]**: invoke `/renmark:prd` (create mode), then return here and continue to Step 6 once it completes.
- If the user chooses **[b]**, or if `PRD.md` already exists: skip silently and continue.

Do not mention this step if `PRD.md` already exists. Do not block or repeat the offer.

---

### 5b. Offer blueprint generation (new projects only)

Check whether `SCHEMATIC.md` exists at the project root. If it does **not** exist, offer once — do not block:

> "Would you like me to generate a project blueprint via `/renmark:blueprint`? It produces a living `SCHEMATIC.md` (architecture overview, module map, data flow) — and a `PROTOTYPE.html` interactive mock-up if the build has a UI.
>
> 1. [a] Yes — run `/renmark:blueprint` now before we continue
> 2. [b] Skip — continue with the normal next step"

- If the user chooses **[a]**: invoke `/renmark:blueprint`, then return here and continue to Step 6 once it completes.
- If the user chooses **[b]**, or if `SCHEMATIC.md` already exists: skip silently and continue.

Do not mention this step if `SCHEMATIC.md` already exists. Do not block or repeat the offer.

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

Do NOT mention plan files, spec files, or executor types to the user.

The routing above IS the next step — defer its presentation to the shared
next-step contract (class 1 — Tier-0 stage routing):

> *End by calling `renmark.lifecycle.next_steps(repo, "start")` and render the
> result per `${CLAUDE_PLUGIN_ROOT}/skills/_shared/next-steps.md` (class 1 —
> Tier-0 stage routing). Present via `AskUserQuestion` (handoff-menu.md rules
> 6–9); the state-derived next command is the `(Recommended)` option. Require an
> explicit choice — never auto-proceed.*

---

## Common Mistakes

| Mistake | Fix |
|---|---|
| Asking about tech stack | Never ask — infer and state in the summary |
| Mentioning "spec", "plan", "executor", "orchestrate" | Use plain English: "build plan", "next step", "run the tasks" |
| Asking more than 2 follow-up questions | Cap at 2 — infer everything else |
| Proceeding without confirmation | Always wait for explicit yes before routing |
| Adding best practices as separate tasks | Weave them into implementation task specs |

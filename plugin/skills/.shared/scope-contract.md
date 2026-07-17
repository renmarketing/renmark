# Scope Contract — Discovery Reference (single source of truth)

**Shared by `/renmark:brainstorm` and `/renmark:plan`.** This is the one place
the stack / deployment / MVP-boundary questions live, so the two skills can't
drift apart. Whichever skill runs first establishes the contract (Q1–Q3 below)
and writes the records (CHANGELOG scope entry + `stack.md`); the other detects
those records and skips re-asking.

- `brainstorm` runs this during design discovery (its Step 3), then researches
  around the chosen stack.
- `plan` runs this in its Step 0 **only if** no spec/stack.md/CHANGELOG scope
  entry already covers the work — i.e. only when brainstorm was skipped.

**Altitude vs the PRD (anti-duplication):** this contract owns a *build's* MVP
boundary / out-of-scope (Q3) — ephemeral, per-feature. **Product-level**
non-goals (what the product will never be) belong in `PRD.md`. Cross-reference,
don't copy: the MVP cut here is "not in *this* version"; a PRD non-goal is "not
*ever*." See the PRD touchpoint policy in `_shared/prd-alignment.md`.

---

## Presentation

**Ask each question below via the `AskUserQuestion` tool (arrow-selectable choices) when available** — `AskUserQuestion` is the canonical fit for these stack/deployment/scope decisions. Map each option to a choice (`label` = the option, e.g. `Yes, use that [a]`; `description` = its gloss). The tool caps at **4 options per question**: for the questions below with 5 options (Q1, Q2), surface the 4 highest-value choices and rely on the always-accepted free-text answer for the rest (the "I'll specify" / "Skip" options are naturally free-text anyway), and print the full numbered list as the fallback. In a non-interactive session (or if the tool is unavailable/errors), print the numbered list and accept a number or bracket letter. A choice is always required — never auto-proceed.

**Headless mode (safe gate).** The Q1–Q3 scope questions are a SAFE gate per the headless contract: when renmark runs headless (no human at a TTY, `AskUserQuestion` absent), they are **not** asked interactively. The skill auto-picks the recommended/default option for each question (suggested stack confirmed, deployment per the inference rules / "undecided", MVP boundary per "plan everything"), records the choice in the scope records (CHANGELOG entry + `stack.md`) plus `decision: auto_picked_recommended` in the return JSON, and continues — never stalling on a picker that cannot be answered. Detection and the full contract live in `${CLAUDE_PLUGIN_ROOT}/skills/.shared/headless-contract.md`.

---

## Q1 — Tech stack

Always ask for new projects unless the stack is already documented. Infer a suggested stack and present as a confirmable choice:

> For this [feature type], I'd suggest: [recommended stack]. Does that work?
> 1. [a] Yes, use that
> 2. [b] Different backend — I'll specify
> 3. [c] Different frontend/UI approach — I'll specify
> 4. [d] Show me 2–3 reasonable options
> 5. [e] Skip — I'll add stack notes to the plan manually

**Stack inference rules:**

| Signal | Default stack |
|---|---|
| `3d`, `game`, `canvas`, `animation`, `interactive visual` | browser frontend + Three.js or Canvas |
| `web app`, `server`, `api`, `login`, `accounts`, `dashboard` | Node.js + Express or Python + FastAPI |
| `data`, `ml`, `analysis`, `csv`, `automation` | Python |
| `mobile`, `ios`, `android` | React Native unless native platform specified |
| `cli`, `command line`, `developer tool` | Python or Node.js CLI |
| `static site`, `landing page`, `portfolio` | static frontend + Vite |
| `auth`, `payments`, `multi-user`, `roles` | backend + database required |
| `realtime`, `chat`, `multiplayer`, `collaboration` | backend + realtime transport required |

If multiple stacks are plausible, offer options rather than choosing silently:

> This could reasonably be built two ways:
> 1. [a] Python + FastAPI + SQLite — backend-first
> 2. [b] Node.js + Express + SQLite — JavaScript full-stack
> 3. [c] Next.js — frontend and backend routes together
>
> Which direction should I use? (arrow-select via `AskUserQuestion` when available; else type the number/letter — a choice is required)

---

## Q2 — Deployment target

Ask when the feature includes: server, accounts, auth, database, multiplayer, realtime, API, payments, or public access. Skip for clearly local, static, or frontend-only work.

> Where will this run?
> 1. [a] Local only — localhost, no public server
> 2. [b] Self-hosted server / VPS
> 3. [c] Cloud platform (Vercel, Railway, Fly.io, AWS, etc.)
> 4. [d] Internal/private network
> 5. [e] Doesn't matter yet

If user chooses "doesn't matter yet," record: *Deployment target: undecided; plan should avoid provider-specific assumptions.*

---

## Q3 — MVP boundary

Always ask for new projects and major features.

> What should be out of scope for this version?
> 1. [a] Nothing obvious — plan everything I described
> 2. [b] MVP only — keep it to the simplest usable version
> 3. [c] Skip advanced features for now
> 4. [d] I'll specify exactly what to exclude

If user chooses MVP only, infer sensible exclusions and record them explicitly.

---

## CHANGELOG scope entry format

```markdown
## [YYYY-MM-DD] — project scope: [feature name]

**Request:** [1–2 sentence summary]
**Tech stack:** [confirmed stack]
**Deployment:** [confirmed target]
**MVP boundary:** [confirmed MVP level]
**Out of scope:** [explicit exclusions, or "nothing excluded"]

**Locked decisions:**
- Tech stack and deployment target above are locked for this plan
- Changing them requires a new project scope entry
- Implementation details may be refined during planning if they don't conflict with these decisions
```

---

## stack.md format

```markdown
# Stack

**Runtime:** [e.g., Node.js 20, Python 3.12, browser-only]
**Backend framework:** [e.g., Express, FastAPI, none]
**Frontend:** [e.g., React, Vite, Three.js, vanilla JS, none]
**Database:** [e.g., SQLite, PostgreSQL, none, undecided]
**Realtime:** [e.g., Socket.io, WebSocket, none]
**Auth:** [e.g., local dev only, session auth, external provider, none, undecided]
**Deployment target:** [local, VPS, cloud, internal, undecided]
**Notes:** [important constraints or user preferences]
```

When updating an existing `stack.md`, preserve prior decisions unless the user explicitly changes them. If the new scope changes the stack, add a dated note rather than silently replacing.

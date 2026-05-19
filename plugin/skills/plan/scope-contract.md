# Scope Contract — Discovery Reference

Referenced by `/renmark:plan` Step 0. Full question text, option menus, and record formats.

---

## Q1 — Tech stack

Always ask for new projects unless the stack is already documented. Infer a suggested stack and present as a confirmable choice:

> For this [feature type], I'd suggest: [recommended stack]. Does that work?
> - [a] Yes, use that
> - [b] Different backend — I'll specify
> - [c] Different frontend/UI approach — I'll specify
> - [d] Show me 2–3 reasonable options
> - [e] Skip — I'll add stack notes to the plan manually

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
> - [a] Python + FastAPI + SQLite — backend-first
> - [b] Node.js + Express + SQLite — JavaScript full-stack
> - [c] Next.js — frontend and backend routes together
>
> Which direction should I use?

---

## Q2 — Deployment target

Ask when the feature includes: server, accounts, auth, database, multiplayer, realtime, API, payments, or public access. Skip for clearly local, static, or frontend-only work.

> Where will this run?
> - [a] Local only — localhost, no public server
> - [b] Self-hosted server / VPS
> - [c] Cloud platform (Vercel, Railway, Fly.io, AWS, etc.)
> - [d] Internal/private network
> - [e] Doesn't matter yet

If user chooses "doesn't matter yet," record: *Deployment target: undecided; plan should avoid provider-specific assumptions.*

---

## Q3 — MVP boundary

Always ask for new projects and major features.

> What should be out of scope for this version?
> - [a] Nothing obvious — plan everything I described
> - [b] MVP only — keep it to the simplest usable version
> - [c] Skip advanced features for now
> - [d] I'll specify exactly what to exclude

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

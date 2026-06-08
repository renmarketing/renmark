---
name: prd
description: Use when the user wants to author or maintain the project's Product Requirements Document — typed as /renmark:prd or phrases like "write the PRD", "what's the PRD say", "update the product spec", "keep the PRD current". Authors and maintains a single per-project `PRD.md` at the repo root as the human-owned source of truth for what the product is and is not. Two modes: CREATE (no PRD yet) interviews one-question-at-a-time on a fresh project or synthesizes a draft from existing docs on a mature one; UPDATE (PRD exists) reconciles a requested change and presents a diff. Every write is human-gated — the PRD is a living doc the human owns, never silently rewritten by an automated stage.
---

# prd

## Overview

`/renmark:prd` owns the project's `PRD.md` — the single, committed, human-authored source of truth for *what this product is, who it's for, what it does, and what it explicitly is not*. It is the durable answer to "are we still building the right thing?" that specs, plans, and features are checked against. The skill never writes the PRD without explicit human approval: in CREATE mode it presents a full draft for sign-off; in UPDATE mode it presents a diff. The full PRD body is read **only inside this skill's own invocation** — orchestrator and router callers never load it into their context.

## When to Use

- "Write the PRD for this project" / "we don't have a PRD yet"
- "Update the PRD — we just decided to drop the export feature"
- "What does the PRD say about X?" — answered inside UPDATE mode's read step (it reads the PRD, then proposes any edit); there is no separate read-only mode
- A fresh project that needs its product definition pinned down before any feature work
- A mature project whose product definition lives implicitly in CLAUDE.md / specs / changelog and should be made explicit
- An automated stage (e.g. `/renmark:feature`'s drift check) detected the request diverges from the PRD and wants the PRD reconsidered — routed here for a human-gated edit

**Do NOT use:**
- To decompose work into tasks — that's `/renmark:plan`. The PRD says *what* and *why*, never the task breakdown.
- To flesh out a single feature's design — that's `/renmark:brainstorm` (writes a spec under `.renmark/specs/`). The PRD is product-level, not feature-level.
- To check whether a change aligns with the PRD from inside another skill — do NOT read the PRD body there. Dispatch the alignment subagent at `${CLAUDE_PLUGIN_ROOT}/skills/_shared/prd-alignment.md` and consume only its bounded summary.
- To execute or verify work — use `/renmark:orchestrate` / `/renmark:verify`.

## Steps

**Step 0 — Context check.** Call `lifecycle.skill_preamble(repo, 'prd')`. If it returns a non-None hint, surface it as a one-line note. Do NOT block — the user decides whether to `/compact` or `/clear`.

**Mode detection.** Check for `PRD.md` at the project root:

```bash
test -f PRD.md && echo UPDATE || echo CREATE
```

- `PRD.md` present → **UPDATE mode**.
- `PRD.md` absent → **CREATE mode**.

### CREATE mode

No `PRD.md` exists yet. Pick a sub-path by project maturity (read `.renmark/memory/project.md` and check whether `CLAUDE.md` is still the unfilled scaffold template):

**Fresh project (no real product definition yet) → interview.** Ask the user questions **one at a time**, brainstorm-style, using `AskUserQuestion` with **at most 4 options** (the picker rejects arrays with >4 items — bundle related choices if you need more). One question, one answer, then the next. Cover, in order:
1. **What is this product** — the one-sentence pitch (the WHAT).
2. **Who is it for** — the primary user / audience.
3. **The problem it solves** — the WHY, and the status quo it replaces.
4. **What it does** — the 3–5 core capabilities (MVP boundary).
5. **What it explicitly is NOT** — non-goals and out-of-scope, stated up front.
6. **How we'll know it works** — success criteria.

Stop asking once you can state the product in 2–3 paragraphs with a confirmed non-goals list.

**Optional acceptance criteria (interview path).** *After* the requirements above are gathered, you MAY — one requirement at a time — offer to attach **1–3 acceptance criteria** to each `REQ-n`. This step is **entirely optional and fully skippable**: tell the user up front they can skip any one requirement or skip the whole pass. For each requirement they opt into, capture 1–3 outcome statements in the template's exact format — `*Acceptance:* done when (outcome); done when (outcome).` — phrased as observable product outcomes, not implementation steps. Leave the line off for any requirement the user skips. Never block the PRD write on this; a PRD with zero acceptance criteria is valid.

**Mature project (product already exists implicitly) → synthesize.** Instead of interviewing, synthesize a draft from what's already on disk: `CLAUDE.md` (the "What this project is" section + project-at-a-glance), the specs under `.renmark/specs/`, and `CHANGELOG.md`. Heavy reading of these files is fine — it happens **inside this dedicated invocation**, not in an orchestrator. Distill them into the same product-level fields the interview would gather (what / who / why / capabilities / non-goals / success criteria). For acceptance criteria, infer obvious `*Acceptance:* done when …` outcomes for a requirement **only where the existing docs make them clear**; otherwise leave the acceptance line blank rather than guessing.

**Then, in both sub-paths:**

1. **Present the full draft for EXPLICIT approval.** Show the complete proposed PRD content in the conversation and ask the user to approve, edit, or reject section by section. Do NOT write the file until the user explicitly approves. (This skill's own invocation is the one place the full PRD body legitimately lives in context.)
2. **On approval, write `PRD.md`** at the project root from the template at `${CLAUDE_PLUGIN_ROOT}/templates/PRD.md.template`, substituting `{{PROJECT_NAME}}` and `{{DATE}}` (today). Keep the provenance metadata header the template carries (so downstream alignment checks can read freshness without reading the body). Set `last_reviewed` to today.
3. **Append a CHANGELOG entry:**
   ```
   ## [YYYY-MM-DD] — PRD created
   **Request:** <user's ask in 1–2 plain sentences>
   **Built:** Created PRD.md as the project's product source of truth (<fresh-interview | synthesized-from-docs>).
   **Files changed:**
   - `PRD.md` — new product definition (what/who/why/capabilities/non-goals/success criteria)
   **Do not change:**
   - PRD.md is human-owned. Automated stages may PROPOSE edits but never write it without approval.
   ```
4. **Pointer, not import.** Ensure `CLAUDE.md` / `AGENTS.md` reference the PRD as **plain text** (e.g. "Product source of truth: see `PRD.md`"), NEVER as an `@import` — an import would auto-load the full PRD into every session's context and defeat the whole hygiene contract. If you add or touch that pointer, keep it plain text and mirror it across both files.

### UPDATE mode

`PRD.md` exists. The PRD is a **living doc** the human owns — never silently rewritten.

1. **Read the current `PRD.md`** (full read — again, legitimate only inside this skill).
2. **Reconcile against the requested change.** Determine which sections the request touches and what the minimal, faithful edit is. If the request conflicts with an existing non-goal or core capability, call that out explicitly rather than silently overwriting it. A requirement's acceptance criteria (`*Acceptance:* done when …`) are an editable part of that requirement — adding, changing, or removing them flows through this same reconcile → DIFF → explicit-approval path; they are never silently written or dropped.
3. **Present a DIFF** of the proposed change in the conversation — old vs. new for each touched section — and ask for explicit approval. Do NOT write until the user approves.
4. **On approval, write `PRD.md`** with the reconciled content. **Bump `last_reviewed`** in the metadata header to today.
5. **Append a CHANGELOG entry:**
   ```
   ## [YYYY-MM-DD] — PRD updated
   **Request:** <user's ask in 1–2 plain sentences>
   **Built:** Reconciled <section(s)> of PRD.md; bumped last_reviewed.
   **Files changed:**
   - `PRD.md` — <what changed and why>
   **Do not change:**
   - <any non-goal/invariant the edit reaffirmed or newly pinned>
   ```

### Altitude — what acceptance criteria are (and are NOT)

Acceptance criteria on a requirement are **product-level outcome criteria** — "done when (observable outcome)" — that say *what success looks like for the user*, pitched at the same altitude as the PRD itself. They are deliberately NOT:

- **plan task verifiers** — the shell/`pytest` checks a `/renmark:plan` task carries live at the task level, not here;
- **the deferred `verify --coverage` capability** (ADR-005) — writing `*Acceptance:* done when …` lines does NOT build coverage reporting and must not be read as committing to it.

`/renmark:verify`'s goal-backward smoke test MAY lean on a requirement's acceptance criteria as hints for what to probe, but that is opportunistic reuse — it does not turn acceptance criteria into a coverage matrix. Keep them at product altitude: outcome statements, never test commands.

### Human gate (automated-stage proposals)

When a PRD write is **proposed by an automated stage** rather than typed by the user directly (e.g. `/renmark:feature`'s drift check decides the requested feature diverges from the PRD and routes here), treat it as a gated mutation per renmark's approval-gate doctrine:

- On entry from an automated stage, set the lifecycle approval fields before proposing the write:
  ```python
  from renmark import lifecycle
  lifecycle.write_lifecycle(
      repo,
      human_review_required=True,
      human_review_for="prd-edit: <one-line description of the proposed change>",
  )
  ```
- **Never write `PRD.md` while `human_review_required and not human_review_completed`.** Present the draft/diff and stop until the human approves. (`/renmark:approve` is the *planned* skill to flip `human_review_completed`; until it ships, `lifecycle.next_recommended()` surfaces a manual gate message and the human clears it by approving the draft/diff here.)
- After the human approves and the write lands, clear the gate (`human_review_required=False, human_review_completed=False, human_review_for=None`) so it doesn't leak into the next stage.
- A user typing `/renmark:prd` directly **is** the human in the loop — the explicit draft/diff approval above satisfies the gate; you don't additionally block on the lifecycle bit unless an automated stage set it.

### Context hygiene (load-bearing)

The full PRD body is read **only inside this dedicated `/renmark:prd` invocation**. Orchestrator and router callers — `/renmark:orchestrate`, `/renmark:feature`, and any skill checking "does this change still match the product?" — **MUST NOT read the PRD body into their context.** They dispatch the alignment subagent defined at `${CLAUDE_PLUGIN_ROOT}/skills/_shared/prd-alignment.md`, which reads the PRD in isolation and returns only a bounded **≤5-line** summary (aligned / drift + which non-goal or capability is at issue). The PRD's plain-text pointer in CLAUDE.md/AGENTS.md (never an `@import`) keeps it off the always-loaded path; this skill is the only place the body legitimately enters a conversation.

## What's next

`prd` is a **pipeline skill** (class 1) in the next-step contract. After a PRD
create or update lands and the human gate (above) is satisfied, hand off — never
dead-end on a written file.

> *End by calling `renmark.lifecycle.next_steps(repo, "prd")` and render the
> result per `${CLAUDE_PLUGIN_ROOT}/skills/_shared/next-steps.md` (class 1 —
> Tier-0 stage routing). Present via `AskUserQuestion` (handoff-menu.md rules
> 6–9); the state-derived next command is the `(Recommended)` option. Require an
> explicit choice — never auto-proceed.*

The state-derived recommendation follows the in-flight feature's lifecycle stage:
if a feature is in flight, `next_steps` returns its current `next_recommended()`
stage (resume the pipeline where it left off). If **no feature is in flight**,
the recommended next step is `/renmark:roadmap` (gap mode) — surface unbuilt
PRD promises against `CHANGELOG.md` + `features.md` now that the product
definition is pinned. Do not paste the rendering rules — cite the file.

## Governance compliance

| # | Rule | How this skill complies |
|---|---|---|
| G2 | Canonical state | The PRD lives on disk at `PRD.md` (committed) and every change is logged to `CHANGELOG.md`; approval gates persist in `.renmark/state/lifecycle.json`. Nothing relies on "what was said earlier" — the product definition is a file, not conversation memory. |
| G3 | Summary boundary | Callers consume only the alignment subagent's ≤5-line summary; the PRD body never crosses into orchestrator/router context. CHANGELOG entries are compact and structured. |
| G5 | Executor isolation | Heavy PRD reading (synthesis from CLAUDE.md/specs/changelog in CREATE, full read in UPDATE) happens inside this dedicated invocation; for any *other* skill the heavy read is delegated to the `_shared/prd-alignment.md` alignment subagent — the orchestrator never reads the PRD body itself. |
| G6 | Artifact governance | `PRD.md` is a **human-owned source-of-truth doc, not a generated artifact**, so it carries a deliberately lean header (`artifact_type`, `schema_version`, `created_at`, `last_reviewed`, `status`) and is explicitly exempt from the generated-artifact provenance fields (`source_sha`, `generator`, `dependency_refs`). UPDATE mode bumps `last_reviewed` so freshness is checkable without reading the body. |
| G7 | Compact semantics | The PRD and its approval state are on disk (`PRD.md`, `lifecycle.json`); after `/compact` mid-skill the proposed change can be re-derived from the file and the pending `human_review_for` field — no transcript dependency. |
| G8 | Compounding verification | Every create/update appends a structured `CHANGELOG.md` entry (request + built + files + invariants), so product decisions and pinned non-goals accrue as durable project memory rather than vanishing. |
| G9 | Failure transparency | Writes happen only on explicit approval; a declined/edited draft stays unwritten and is reported honestly as not-yet-applied rather than claimed complete. The metadata header reflects actual `last_reviewed`, never a fabricated date. |
| G10 | Workflow recovery | Re-running `/renmark:prd` is idempotent and self-locating: mode is re-detected from whether `PRD.md` exists, and a pending automated-stage edit is recoverable from `human_review_required`/`human_review_for` — the user never starts over. |
| G11 | Task isolation | When invoked by another skill the PRD read is delegated to the `_shared/prd-alignment.md` subagent in an isolated context; the caller consumes only its `SubagentOutput`-style bounded summary — never the PRD body, never a transcript. This skill itself dispatches no sub-tasks (its own reads are first-person, in-invocation). |

*Mirror any rule-affecting change to this skill in `AGENTS.md`/CLAUDE.md guidance per the workspace sync convention.*

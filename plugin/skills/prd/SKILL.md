---
name: prd
description: "Use when the user wants to author or maintain the project's Product Requirements Document — typed as /renmark:prd or phrases like \"write the PRD\", \"update requirements\", \"update the product spec\". Creates the PRD when none exists or reconciles a requested change as a human-gated diff."
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

## When Agency Mode is active

In Agency Mode, the PRD is the owner-agreed source-of-truth LOCK. Owner approval gates all PRD changes; change control applies when milestone feedback shifts scope. See `${CLAUDE_PLUGIN_ROOT}/skills/_shared/agency-delivery.md` for the full contract. The human-gated create/update flow above remains unchanged — this rule is a reinforcement, not a new pathway.

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

**Optional acceptance criteria (interview path).** *After* the requirements above are gathered, you MAY — one requirement at a time — offer to attach **1–3 acceptance criteria** to each `REQ-n`. This step is **entirely optional and fully skippable**: tell the user up front they can skip any one requirement or skip the whole pass. For each requirement they opt into, capture the criteria as a single indented bullet in the template's exact format — `- *Acceptance:* done when (outcome); done when (outcome).` (one `- *Acceptance:*` bullet holding 1–3 semicolon-separated `done when…` clauses) — phrased as observable product outcomes, not implementation steps. Leave the line off for any requirement the user skips. Never block the PRD write on this; a PRD with zero acceptance criteria is valid.

**Mature project (product already exists implicitly) → synthesize.** Instead of interviewing, synthesize a draft from what's already on disk: `CLAUDE.md` (the "What this project is" section + project-at-a-glance), the specs under `.renmark/specs/`, and `CHANGELOG.md`. Heavy reading of these files is fine — it happens **inside this dedicated invocation**, not in an orchestrator. Distill them into the same product-level fields the interview would gather (what / who / why / capabilities / non-goals / success criteria). For acceptance criteria, infer an obvious `- *Acceptance:* done when …` bullet for a requirement **only where the existing docs make them clear**; otherwise leave the acceptance line off rather than guessing.

**Then, in both sub-paths:**

1. **Run the reuse check before drafting a new product capability.** Before presenting a draft that proposes a new capability, dispatch the reuse-check subagent so a "we already have this" finding surfaces *before* the PRD enshrines a redundant capability as a product requirement.

   > *Before proposing any custom build, dispatch the reuse-check subagent from `${CLAUDE_PLUGIN_ROOT}/skills/_shared/reuse-check.md`: Agent tool call (`model: haiku`; `sonnet` for a large search surface), passing ONLY `request_description`. The subagent searches loaded skills/commands, session MCP tools, `.renmark/specs/` + `.renmark/plans/`, and `.renmark/memory/features.md` in its own context, and returns ONLY the ≤5-line `reuse: found | none` verdict (+ a one-line pointer when found). Surface the verdict and default to reuse; do NOT read the searched bodies in the orchestrator context (REQ-5).*

   > *Include the reasoning/output-discipline contract from `${CLAUDE_PLUGIN_ROOT}/skills/_shared/reasoning-contract.md` in the dispatched subagent prompt: multi-perspective decomposition → explicit assumptions/edge cases → synthesis; blocking vs deferrable; findings vs recommendations; evidence preserved; missing context stated, never guessed; stance of pushing back by default (no sycophancy).*

   On `reuse: found`, surface the pointer and ask whether the new capability should instead point at the existing one rather than be drafted as a fresh product requirement.

2. **Surface contradictions before presenting the draft.** If the draft conflicts with an existing non-goal, a recorded decision (`.renmark/memory/decisions.md`, the Decision log, or a prior CHANGELOG "Do not change" guard), or a previously stated scope boundary, **name the contradiction explicitly and reconcile it** rather than silently overwriting. State the conflicting pair (what the draft says vs. what is on file), then ask the human which one wins — never resolve it by quietly dropping the older decision.

3. **Lead the draft with a context-recovery preamble.** Open the presented draft with a short (≤5-line) preamble that states: what was recovered from disk (which files synthesized, or that this is a fresh interview), the reuse verdict, any contradiction surfaced above, and — critically — **what is still missing or unconfirmed.** State the gaps explicitly instead of guessing past them (reasoning-contract discipline: missing context is named, not papered over). This preamble is orientation, not the PRD body.

4. **Present the full draft for EXPLICIT approval.** Show the complete proposed PRD content in the conversation and ask the user to approve, edit, or reject section by section. Do NOT write the file until the user explicitly approves. (This skill's own invocation is the one place the full PRD body legitimately lives in context.)

   **Headless gate.** Before rendering the approval picker, consult `renmark.headless.resolve_gate(repo, "prd-create", kind="dangerous", originating_skill="prd", what=<one-line description of the PRD draft>)`. If it returns anything other than `{"mode": "interactive"}` (headless), emit the returned `needs_input` JSON envelope + `headless.render_return(envelope)` prose line and **STOP** — the human owns the product source of truth, so PRD approval can never be auto-granted headless (PRD approval is a dangerous gate, per `${CLAUDE_PLUGIN_ROOT}/skills/_shared/headless-contract.md`). Interactive → render the approval picker unchanged.
5. **End with a Final Recommendation verdict.** Alongside the approval gate, surface a one-line **Final Recommendation** — exactly one of `build-now | revise-scope | discovery-first | do-not-build-yet` — followed by one sentence of why (this is the value the template's `## Recommendation` section captures). The verdict is **ADVISORY**: it informs the human's decision but does not grant it. The human still owns the write (REQ-4) — do NOT treat any verdict, including `build-now`, as approval to write the file.
6. **On approval, write `PRD.md`** at the project root from the template at `${CLAUDE_PLUGIN_ROOT}/templates/PRD.md.template`, substituting `{{PROJECT_NAME}}` and `{{DATE}}` (today). Keep the provenance metadata header the template carries (so downstream alignment checks can read freshness without reading the body). Set `last_reviewed` to today.
7. **Append a CHANGELOG entry:**
   ```
   ## [YYYY-MM-DD] — PRD created
   **Request:** <user's ask in 1–2 plain sentences>
   **Built:** Created PRD.md as the project's product source of truth (<fresh-interview | synthesized-from-docs>).
   **Files changed:**
   - `PRD.md` — new product definition (what/who/why/capabilities/non-goals/success criteria)
   **Do not change:**
   - PRD.md is human-owned. Automated stages may PROPOSE edits but never write it without approval.
   ```
8. **Pointer, not import.** Ensure `CLAUDE.md` / `AGENTS.md` reference the PRD as **plain text** (e.g. "Product source of truth: see `PRD.md`"), NEVER as an `@import` — an import would auto-load the full PRD into every session's context and defeat the whole hygiene contract. If you add or touch that pointer, keep it plain text and mirror it across both files.

### UPDATE mode

`PRD.md` exists. The PRD is a **living doc** the human owns — never silently rewritten.

1. **Read the current `PRD.md`** (full read — again, legitimate only inside this skill).
2. **Reconcile against the requested change.** Determine which sections the request touches and what the minimal, faithful edit is. If the request conflicts with an existing non-goal or core capability, call that out explicitly rather than silently overwriting it. A requirement's acceptance criteria (`*Acceptance:* done when …`) are an editable part of that requirement — adding, changing, or removing them flows through this same reconcile → DIFF → explicit-approval path; they are never silently written or dropped.

   **Fable lane (declared projects only).** In projects whose capability declaration says `capabilities.top_tier == "fable"`, this reconcile-and-diff analysis — ambiguity detection, dependency mapping, conflict checks against existing non-goals/capabilities — MAY be dispatched as **one non-interactive fable subagent**: a single bounded call carrying the full PRD body plus the requested change, returning the proposed diff and a ≤5-line rationale, which this skill then presents at step 3 exactly as it would its own analysis. The DIFF presentation, the human approval gate, and the write flow are completely unchanged — fable proposes, the human still approves, this skill still writes. This lane is for the analysis step only: interactive CREATE interviews stay on the session brain — never per-checkpoint fable calls. *Include the reasoning/output-discipline contract from `${CLAUDE_PLUGIN_ROOT}/skills/_shared/reasoning-contract.md` in the dispatched fable prompt: multi-perspective decomposition → explicit assumptions/edge cases → synthesis; blocking vs deferrable; findings vs recommendations; evidence preserved; missing context stated, never guessed.*
3. **Present a DIFF** of the proposed change in the conversation — old vs. new for each touched section — and ask for explicit approval. Do NOT write until the user approves.

   **Headless gate.** Before rendering the approval picker, consult `renmark.headless.resolve_gate(repo, "prd-update", kind="dangerous", originating_skill="prd", what=<one-line description of the PRD change>)`. If it returns anything other than `{"mode": "interactive"}` (headless), emit the returned `needs_input` JSON envelope + `headless.render_return(envelope)` prose line and **STOP** — the human owns the product source of truth, so PRD approval can never be auto-granted headless (PRD approval is a dangerous gate, per `${CLAUDE_PLUGIN_ROOT}/skills/_shared/headless-contract.md`). Interactive → render the approval picker unchanged.
4. **End with a Final Recommendation verdict.** Alongside the DIFF and the approval gate, surface a one-line **Final Recommendation** — exactly one of `build-now | revise-scope | discovery-first | do-not-build-yet` — plus one sentence of why (the value the template's `## Recommendation` section captures; update it if the edit changes the verdict). The verdict is **ADVISORY** and does not grant approval: the human still owns the write (REQ-4) — never treat any verdict as license to write the file.
5. **On approval, write `PRD.md`** with the reconciled content. **Bump `last_reviewed`** in the metadata header to today.
6. **Append a CHANGELOG entry:**
   ```
   ## [YYYY-MM-DD] — PRD updated
   **Request:** <user's ask in 1–2 plain sentences>
   **Built:** Reconciled <section(s)> of PRD.md; bumped last_reviewed.
   **Files changed:**
   - `PRD.md` — <what changed and why>
   **Do not change:**
   - <any non-goal/invariant the edit reaffirmed or newly pinned>
   ```

### Optional template sections (populate when relevant)

The template at `${CLAUDE_PLUGIN_ROOT}/templates/PRD.md.template` carries several structures the skill populates **only when the project benefits** — every one is OPTIONAL, and a lean PRD that omits all of them is fully valid. Never add an empty section to satisfy a checklist; absence is a legitimate signal that the project doesn't need it.

- **Requirement sub-categories** — the flat `REQ-n` list MAY be clustered under optional headings: *Functional* (what it does), *Non-functional* (quality / security / performance / portability), *Data & Schema* (entities, contracts, persistence, migration shape), *UI-UX* (surfaces, flows, accessibility), and *AI-Agent* (for agentic builds: role, allowed + forbidden tools, output contract, when-to-stop conditions). Use them when grouping aids clarity; a flat, ungrouped list stays valid.
- **`[blocking | deferrable]` tags on Open questions** — each open question MAY be tagged: `[blocking]` must be resolved before build starts, `[deferrable]` can be answered later without stalling work. Tag only where the distinction matters.
- **`## Constraints & dependencies`** — optional section for external/internal constraints (platforms, APIs, libraries, deadlines, budgets, upstream teams, regulatory limits), each tagged `[blocking | deferrable | unknown]`. Omit entirely for a PRD with no notable constraints.
- **`## Decision log`** — optional PRD-*authoring* history (scope cuts, requirement framing, target-user calls) captured as decision · why · alternatives · tradeoff. This is product-authoring memory, DISTINCT from the architectural ADRs in `.renmark/memory/decisions.md` — cross-reference an ADR by path, never duplicate it here.
- **`## Recommendation`** — the one-line advisory verdict (`build-now | revise-scope | discovery-first | do-not-build-yet` + one sentence) produced at the approval gate above. Persist the surfaced verdict here so the written PRD records it.

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
- **Never write `PRD.md` while `human_review_required and not human_review_completed`.** Present the draft/diff and stop until the human approves. (Invoke `/renmark:approve` to flip `human_review_completed`; `lifecycle.next_recommended()` surfaces it as the recommended next command when a gate is pending.)
- After the human approves and the write lands, clear the gate (`human_review_required=False, human_review_completed=False, human_review_for=""`) so it doesn't leak into the next stage. (Pass `""`, not `None` — `write_lifecycle` treats `None` as "leave unchanged", so `None` would strand the stale gate text in lifecycle.json.) `/renmark:approve` is the flip surface for the `human_review_required` bit when the gate was set by an automated stage.
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
| G11 | Task isolation | When invoked by another skill the PRD read is delegated to the `_shared/prd-alignment.md` subagent in an isolated context; the caller consumes only its `SubagentOutput`-style bounded summary — never the PRD body, never a transcript. This skill's only own dispatch is the optional UPDATE-mode fable reconcile lane: one non-interactive, isolated subagent call that absorbs the full PRD body in *its* context (never the caller's) and returns only a bounded proposed diff plus a ≤5-line rationale. All other reads are first-person, in-invocation. |

*Mirror any rule-affecting change to this skill in `AGENTS.md`/CLAUDE.md guidance per the workspace sync convention.*

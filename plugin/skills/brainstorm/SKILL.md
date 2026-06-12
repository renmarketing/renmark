---
name: brainstorm
description: Use when the user wants to flesh out an idea into a concrete spec — typed as /renmark:brainstorm or phrases like "let's brainstorm this", "I have an idea", "help me think through X". Asks one question at a time using the session's top reasoning tier (Fable 5 when available, Opus otherwise), researches best practices and prior art (similar software, live GitHub repos) before proposing approaches, establishes the shared scope contract, and writes a design doc at the end. Bootstraps fresh projects by creating CLAUDE.md, AGENTS.md, and .renmark/ when invoked in an empty folder.
---

# brainstorm

## Overview

One-question-at-a-time spec discovery, driven by the session's top reasoning tier (Fable 5 when available, Opus otherwise), **research-backed**. Output: a design doc at `.renmark/specs/YYYY-MM-DD-<topic>.spec.md` that `/renmark:plan` consumes next.

Brainstorm does two things `plan` does not: it **researches prior art** (best practices, software that solves the same problem, reference implementations on GitHub) so the design is informed rather than invented, and it **establishes the scope contract** (stack / deployment / MVP boundary) using the shared source of truth at `${CLAUDE_PLUGIN_ROOT}/skills/_shared/scope-contract.md`. Because brainstorm writes the scope records, `/renmark:plan` detects them and skips re-asking — the two skills never double-question you.

If the current directory has no `CLAUDE.md`, no `AGENTS.md`, and no `.renmark/`, ask the user whether to scaffold a fresh project before starting the brainstorm.

## When to Use

- "Let's brainstorm a /healthz endpoint"
- "I have an idea for a CLI tool"
- "Help me design X"
- Empty/near-empty directory + user wants to start a new project
- Any time you want the design informed by prior art / best practices, not invented from scratch

**Do NOT use:**
- For executing existing plans — use `/renmark:orchestrate`
- For debugging — use `/renmark:debug`
- For a small change inside an already-scoped project — go straight to `/renmark:plan` (its scope contract is the lightweight fallback when brainstorm is skipped)

## Steps

**Step 0 — Context check.** Call `lifecycle.skill_preamble(repo, 'brainstorm')`. If it returns a non-None hint, surface as a one-line note. (Domain is resolved from `DOMAIN_BY_SKILL` — do not pass it manually.) For synthesis skills like brainstorm, `skill_preamble` now also surfaces a declared-tier hint (e.g. *"declared top tier: fable — … `/model fable`"*) — surface it verbatim, exactly like any other preamble hint.

**Final step — Lifecycle update.** After the spec is written to `.renmark/specs/YYYY-MM-DD-<topic>.spec.md`, call `lifecycle.write_lifecycle(repo, stage='brainstorm-complete', feature=<topic>, artifact_update=('spec', <spec-path>))`. This is what makes `/renmark:resume` work after `/clear`.

### 1. Empty-folder bootstrap (only if needed)

Check the cwd:
```bash
test -e CLAUDE.md || test -e AGENTS.md || test -d .renmark
```

If none exist, ask the user: *"This looks like a fresh project. Scaffold `CLAUDE.md`, `AGENTS.md`, and `.renmark/` to organize work? [Y/n]"*

On yes:
- Read templates from `${CLAUDE_PLUGIN_ROOT}/templates/` (CLAUDE.md.template, AGENTS.md.template, memory/INDEX.md, etc.).
- Substitute placeholders for project name and date.
- Write `CLAUDE.md`, `AGENTS.md`, `CHANGELOG.md`, `.gitignore` (with `.renmark/state/`, `.renmark/debug/`, and `.renmark/logs/` entries — transient runtime), and the `.renmark/` directory tree.
- `CHANGELOG.md` starts with a single bootstrap entry (date, "project bootstrap", files created, standard "Do not change" guards for `.renmark/memory/` and CLAUDE.md↔AGENTS.md sync).
- Run `git init -b main && git add -A`. Then attempt the scaffold commit:
  ```bash
  git -c user.name="renmark-scaffold" -c user.email="scaffold@renmark.local" commit -q -m "chore: renmark scaffold"
  ```
  If the commit is blocked (impersonation guard, no global config), skip it and tell the user: *"Scaffold files created. Run `git commit -m 'chore: renmark scaffold'` once you've set your git user config."*

### 1b. PRD check (read-only — keep the spec aligned to product direction)

A brainstorm spec is **feature-level**; the PRD is **product-level**. Before
questioning, reconcile the two — without ever loading the PRD body into context.

```bash
test -f PRD.md && echo HAS_PRD || echo NO_PRD
```

- **`NO_PRD`** → surface a **one-line, non-blocking** nudge and continue:
  *"No PRD yet — `/renmark:prd` pins the product direction this spec should serve.
  Optional; brainstorm continues either way."* Do **not** create the PRD here and
  do **not** block. (Brainstorm is not a PRD writer — see the PRD touchpoint
  policy in `${CLAUDE_PLUGIN_ROOT}/skills/_shared/prd-alignment.md`.)
- **`HAS_PRD`** → dispatch the PRD alignment subagent from
  `${CLAUDE_PLUGIN_ROOT}/skills/_shared/prd-alignment.md`: an **Agent tool call**
  passing ONLY a one-line description of what's being brainstormed + the likely
  file scope. Receive ONLY the ≤5-line `verdict`. **Do NOT read `PRD.md` in this
  skill's context.**
  - `verdict: aligned` → note it in one line and proceed; let the PRD's stated
    goals shape your questioning and approaches.
  - `verdict: drift` → surface the bounded reason. The brainstorm continues, but
    the spec now has a product-direction question to resolve: either narrow the
    idea back into PRD scope, or — if the product genuinely should grow — route
    the subagent's `proposed_prd_addition` into `/renmark:prd` update mode
    (human-gated). Never write `PRD.md` from here.

### 2. Brainstorm + establish the scope contract

Ask the user questions ONE at a time. Prefer multiple-choice when possible. **Cap multiselect options at 4** — `AskUserQuestion` rejects arrays with >4 items. Bundle related options if more are needed. Cover:
- Goal / problem being solved (the WHY)
- Constraints (deadlines, environment, dependencies)
- Success criteria (how do you know it worked?)
- Out-of-scope explicitly

**Run the scope contract here.** As part of discovery, ask the Q1–Q3 stack / deployment / MVP-boundary questions from the shared source of truth at `${CLAUDE_PLUGIN_ROOT}/skills/_shared/scope-contract.md` (same questions `/renmark:plan` would ask — do NOT improvise your own). You will record these in Step 6 so `plan` skips re-asking.

Stop asking once you can describe what's being built in 2-3 paragraphs AND you have a confirmed stack / deployment / MVP boundary.

### 3. Research prior art (context-bounded, parallel sonnet subagents)

Before proposing approaches, research the problem space so the design is informed, not invented. Scale effort to novelty: skip for trivial/throwaway work; research thoroughly for anything novel, public-facing, or where you're unsure of the idiomatic approach.

**What to look for:**
- **Best practices** for this class of solution (idiomatic patterns, common pitfalls, security/perf gotchas) for the confirmed stack.
- **Prior art** — existing software/libraries that already solve this problem (build-vs-reuse signal).
- **Reference implementations** — live GitHub repos doing something similar, to learn structure and avoid reinventing.

**Dispatch — parallel `model: sonnet` subagents, never inline queries.** Do NOT run the research queries in this session's context: brainstorm runs on the session's top reasoning tier, so inline web busywork burns top-tier tokens at session price for zero reasoning gain. Instead, split the research angles (best practices / prior art / reference repos) across 2–4 subagents and dispatch them as **single-message multiple `Agent` tool calls with `model: sonnet`** (per the parallelism rule — sequential dispatch is the slow path). Brief each subagent with: a one-line problem statement + the confirmed stack, its single research angle, the focused queries to run (`WebSearch` for best-practices and prior-art discovery; `WebFetch` to read a specific doc/README/repo page; `Context7` if available for authoritative library/framework docs — 2–4 focused queries total across the dispatch, not a broad sweep), and the artifact path it must write.

**Context hygiene (G3/G6 — this is critical):** the session brain never sees raw search results or fetched pages. Each subagent writes its full findings into the `.renmark/research/` artifact and returns ONLY a ≤5-line summary. Give each parallel subagent its own angle-suffixed file (e.g. `.renmark/research/YYYY-MM-DD-<topic>-<angle>.research.md`) — two parallel agents must never share a write scope. Each subagent persists via:

```python
from renmark import summary
summary.write_artifact(
    ".renmark/research/YYYY-MM-DD-<topic>-<angle>.research.md",
    artifact_type="research",
    body=full_findings,                # sources, quotes, repo links, notes
    summary_lines=[                    # ≤5 lines — the ONLY thing returned to the session
        "best practice: <one-liner>",
        "prior art: <tool/lib> — reuse vs build: <call>",
        "reference repo: <owner/name> — <what to borrow>",
        "key risk surfaced: <one-liner>",
        "stack confirmed idiomatic: <yes/adjust>",
    ],
    generator="brainstorm-research",
    confidence="medium",
    validation_status="unvalidated",
)
```

Cite the artifact paths to the user. The session brain reads ONLY the returned ≤5-line summaries and synthesizes them in Step 4 — gathering ran on sonnet; synthesis stays on the top tier. Let the findings shape the approaches — call out explicitly when research changed your recommendation (e.g. "an existing library covers 80% of this, so the plan should wrap it, not rebuild it").

### 4. Propose 2-3 approaches

With trade-offs, **informed by the research**. Lead with your recommendation and name the prior art / best practice that backs it.

**Optional fable synthesis lane (declared projects only).** In projects where `capabilities.top_tier == "fable"` AND the session is NOT already running on Fable (the user didn't run `/model fable`), this step's approach synthesis — architecture options, alternative implementation paths, risk/opportunity discovery — MAY be dispatched as **one** non-interactive fable subagent: a single `Agent` tool call with `model: "fable"`. Inputs: the Step 2 answers summary + the Step 3 research summaries (the ≤5-line summaries, never the artifact bodies). Output: 2-3 approaches with trade-offs + risks, bounded to ≤10 lines. The session brain then presents and discusses the approaches with the user — the fable subagent never talks to the user directly. When the session IS Fable, synthesize inline as today — no dispatch. The one-question-at-a-time discovery loop (Step 2) is NEVER dispatched — no per-checkpoint fable calls; this lane fires at most once per brainstorm, here.

> *Include the reasoning/output-discipline contract from
> `${CLAUDE_PLUGIN_ROOT}/skills/_shared/reasoning-contract.md` in every
> dispatched subagent prompt: multi-perspective decomposition → explicit
> assumptions/edge cases → synthesis; blocking vs deferrable; findings vs
> recommendations; evidence preserved; missing context stated, never guessed.*

### 5. Present the design

In sections, scaled to complexity. Get approval per section. Cover: architecture, components, data flow, error handling, testing.

### 6. Write the spec + scope records

Save the spec to `.renmark/specs/YYYY-MM-DD-<topic>.spec.md`. Include: context, goals, non-goals, architecture, components, success criteria, and a **Prior art & references** section pointing at the research artifact.

**Altitude (anti-duplication):** the spec's non-goals are **feature-scoped** (what *this* build excludes). **Product-level** non-goals belong in `PRD.md`, not here — if a non-goal is durable product direction, reference the PRD rather than copying it, and (on drift) route it to `/renmark:prd`. The build's MVP cut lives in the scope contract (Step 6 records), not duplicated into the spec's non-goals.

**Write the scope contract records** so `/renmark:plan` skips re-discovery (this is the shared-source-of-truth payoff). Using the formats in `${CLAUDE_PLUGIN_ROOT}/skills/_shared/scope-contract.md`:
- Append a `## [date] — project scope: <feature>` entry to `CHANGELOG.md` with the confirmed stack / deployment / MVP boundary / out-of-scope.
- Write/update `.renmark/memory/stack.md` with the confirmed stack.

Also update `.renmark/memory/project.md` with any new project facts learned.

### 7. Hand off (wizard step)

Renmark is a wizard pipeline: `brainstorm → plan (auto-validates) → orchestrate (auto-verifies) → finish`. After writing the spec, render the 3 options per `${CLAUDE_PLUGIN_ROOT}/skills/_shared/handoff-menu.md` rules (Plan [p], Wait [w], No [n]). The rendering rules, picker vs. numbered-list fallback, and required-choice contract all live there — do not duplicate them here.

- **1 / p** → immediately invoke `/renmark:plan <path>`. Don't make the user retype the command.
- **2 / w** → stop. Tell the user how to resume: `/renmark:plan <path>` when ready.
- **3 / n** → stop, and log a note in `.renmark/memory/decisions.md` that planning was deferred and why.

This hand-off follows the shared next-step contract (brainstorm is a class-1 pipeline skill):

> *End by calling `renmark.lifecycle.next_steps(repo, "brainstorm")` and render the
> result per `${CLAUDE_PLUGIN_ROOT}/skills/_shared/next-steps.md` (class 1 —
> Tier-0 stage routing). Present via `AskUserQuestion` (handoff-menu.md rules
> 6–9); the state-derived next command is the `(Recommended)` option. Require an
> explicit choice — never auto-proceed.*

## Common Mistakes

| Mistake | Fix |
|---|---|
| Asking multiple questions at once | One at a time — easier to answer, less context churn |
| Implementing during brainstorm | Brainstorm ends with a spec, not code. Implementation is `/renmark:orchestrate`'s job |
| Skipping the bootstrap question | Empty projects benefit from CLAUDE.md + AGENTS.md before any work starts |
| Writing the spec without user approval | Present the design, get section-by-section approval, then write |

## Reference

- Plan format spec: `PLAN.md` in the renmark install
- Template files: `${CLAUDE_PLUGIN_ROOT}/templates/`

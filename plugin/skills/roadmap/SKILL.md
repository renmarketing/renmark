---
name: roadmap
description: "Use for the Maintenance / Gap pipeline — what's stale, missing, or next. Typed as /renmark:roadmap, \"show the roadmap\", \"what's been built\", \"what's next\". Default prints a zero-cost status table (task | llm | status | tokens | $ | commit) from usage.jsonl + git log; --gaps dispatches bounded subagents to compare PRD vs shipped work and propose backlog items; --research adds web research. Also handles forward planning (PRD → staged/whole-product program) and --setup brownfield reconciliation."
---

# roadmap

## Overview

The **Maintenance / Gap pipeline** — keeps the product moving toward the PRD. Default mode is a zero-cost status reporter; `--gaps` compares PRD vs shipped work, surfaces gaps, and proposes backlog items; `--research` adds web research. Pulls from two sources to build a per-task table with totals:

- `.renmark/state/usage.jsonl` — token spend per LLM call
- `git log` — task-N commits that have landed

Output columns: **task | llm | status | tokens | $ | commit** + totals.

## Steps

**Step 0 — Context check.** Call `lifecycle.skill_preamble(repo, 'roadmap')`. If it returns a non-None hint, surface as a one-line note.

## When invoked

```bash
renmark-execute --roadmap
```

(or call `renmark.roadmap.build_rows(repo)` + `render_table(rows)` from inside this skill).

Show the rendered table to the user. Also write the current snapshot to `.renmark/memory/roadmap.md` so it's committed alongside the rest of the docs.

## Statuses

`build_rows` derives status from git log and usage.jsonl only — there is no "planned" status.

| Status | Meaning |
|---|---|
| `shipped` | a `[renmark] task N:` (or `[codex] task N:` or `[manual] task N:`) commit exists in git |
| `in-progress` | usage.jsonl has an entry for the task but no matching commit |
| `retried` | multiple usage entries for the same task without a commit (likely escalated) |

## When to use

- "Show me the roadmap"
- "How much have we spent?"
- "What's the status?"
- After completing a plan run, to summarize what landed

## Sample output

```
| task   | llm    | status      | tokens | $       | commit    |
|--------|--------|-------------|-------:|--------:|-----------|
| task 1 | haiku  | shipped     |    191 | $0.002  | `e373204` |
| task 2 | haiku  | shipped     |    981 | $0.010  | `45227a1` |
| task 3 | codex  | shipped     |    304 | $0.015  | `611391f` |
| task 4 | codex  | retried     | 148321 | $7.416  | `—`       |
| task 5 | sonnet | shipped     |    362 | $0.011  | `bda857a` |
| task 6 | haiku  | shipped     |   1320 | $0.013  | `f7720b2` |

Totals: 6 tasks · 151,479 tokens · $7.467
By status: retried=1, shipped=5
```

## Do not (status mode)

- Make any LLM calls. The status table is pure aggregation.
- Modify `features.md`, `usage.jsonl`, or git history. Read-only synthesis.

---

## FORWARD PLAN mode (PRD present)

When `PRD.md` exists and no `program.json` is on disk, `/renmark:roadmap` can
derive and persist a staged execution program. This is the entry point for
`staged` and `whole-product` builds.

**Orchestrator-visible output is bounded (G3).** The PRD body NEVER enters the
orchestrator context. A **bounded subagent** (G11) reads `PRD.md` in its own
isolated context and returns only:

- an ordered `stage → task` sequence (machine-readable list, ≤5 lines of prose)
- the resolved program mode (`staged` | `whole-product`)

The orchestrator passes this sequence to `renmark.program.write_program(repo,
program)`, which persists `.renmark/state/program.json` (runtime, gitignored)
and `.renmark/roadmap/program.md` (committed checklist). No PRD content is
retained in orchestrator context after this step (REQ-5 / G11).

**One human approval gate (REQ-18)** fires before any execution: set
`human_review_required` in `lifecycle.json` with `human_review_for` naming the
derived program, surface a summary table to the user, and halt. Resume only
after `/renmark:approve` clears the gate. This gate is non-negotiable — the
orchestrator MUST NOT proceed to execution with an unapproved program.

Shared contracts to apply (read by path, never pasted inline):

- `${CLAUDE_PLUGIN_ROOT}/skills/_shared/reuse-check.md` — before deriving a
  custom stage sequence, confirm no existing plan covers it.
- `${CLAUDE_PLUGIN_ROOT}/skills/_shared/reasoning-contract.md` — governs the
  subagent's output discipline.

### Do not (forward plan mode)

- Read `PRD.md` inline in the orchestrator — always dispatch the bounded subagent.
- Write `PRD.md` or any plan file — forward plan mode is read + derive + persist only.
- Skip the REQ-18 approval gate before execution.

---

## `--setup` BROWNFIELD RECONCILIATION

`/renmark:roadmap --setup` is for projects where work is already partly done.
It combines forward planning with a "what is already built" signal to produce an
accurate current-position view.

### Flow

```
/renmark:roadmap --setup
  1. Forward-plan subagent: derive stage/task sequence from PRD.md (as above,
     bounded G11 — PRD body stays in subagent context only).
  2. Built-signal subagent: reads .renmark/memory/project-map.md + git history
     + existing --gaps ALIGN logic in its own context; returns a structured
     built_signal dict: {"built_reqs":[REQ-n…],"partial_reqs":[…],"built_components":[…]}.
     The subagent's raw output (source scan, git log) stays in its context; only
     the structured dict crosses the boundary (REQ-5 / G11).
  3. Orchestrator calls renmark.roadmap.reconcile_setup(repo, built_signal)
     which maps stage/task statuses and persists program.json.
  4. Staleness check: if renmark.roadmap.program_map_is_stale(repo) returns
     True, HALT and direct the user to run /renmark:init before proceeding
     (stale project-map.md makes the built-signal unreliable).
  5. Render: print renmark.roadmap.render_program_table(repo) — the bounded
     position line (stage X/Y · task done/total) plus the per-stage status grid,
     highlighting stages/tasks still needing work.
```

### Do not (`--setup`)

- Load project-map.md, git log, or source-scan output into orchestrator context
  — route to the bounded built-signal subagent (REQ-5 / G11).
- Proceed past the staleness check — a stale project-map.md produces an
  unreliable built signal; `/renmark:init` must run first.
- Skip the REQ-18 approval gate that applies after program derivation (same rule
  as forward plan mode above).

---

## IN-FLIGHT RENDER (program.json present)

When `program.json` already exists on disk, `/renmark:roadmap` (with no flags)
shows the current program position **in addition to** the retrospective usage
table. Call `renmark.roadmap.render_program_table(repo)` and surface its output
as a bounded position block (G3): the mode line (`staged` | `whole-product`),
the position string from `renmark.program.position(program)`, and the per-stage
status grid. This is zero-LLM, zero-network — purely deterministic read from
`program.json`.

If `program.json` is absent, skip this block silently (the function returns a
friendly string; surface it only if the user explicitly asked for program
status). If `program.json` is corrupt, `render_program_table` propagates
`program.ProgramStateError` — surface the error message and direct the user to
`/renmark:debug`.

---

## GAP-DISCOVERY mode (`--gaps`)

Status mode answers *"what has renmark built?"*. Gap-discovery mode answers the
adjacent question *"what should it build next?"* — by comparing **PRD-intent vs
shipped** (CHANGELOG + `.renmark/memory/features.md`) to surface uncovered
requirements, drift, and a suggested next feature.

Implements **ADR-009** (gap discovery extends `/renmark:roadmap` rather than
adding a standalone `/renmark:next`; reactivates the deferred ADR-005 roadmap
view under a tight scope). Reached via `/renmark:roadmap --gaps`, and routed into
automatically by `/renmark:finish` (post-release hand-off) and `/renmark:init`
(after mapping) so a finished or freshly-mapped project is guided to its
uncovered work instead of dead-ending.

### Hard scope — read-only, advisory, human-gated

This mode is strictly **read-only, advisory, and human-gated**:

- **One-writer rule (ADR-005).** `/renmark:prd` is the *only* writer of `PRD.md`.
  Roadmap NEVER writes `PRD.md`, never writes any roadmap/gap file beyond its own
  status snapshot, and never edits git history. Every proposal it produces is
  *routed* to `/renmark:prd` update mode (human-gated) — AI proposes, the human
  owns the PRD.
- **No inline PRD body.** Roadmap MUST NOT read the `PRD.md` body into its own
  context. It dispatches the **ALIGN subagent** (the `_shared/prd-alignment.md`
  pattern) so the PRD body stays isolated; roadmap sees only the bounded
  ≤5-line verdict.
- **Heavy work runs in subagents.** Gap analysis (T1) and any web research (T2)
  run in **isolated subagents** that return bounded **≤5-line** summaries. The
  orchestrator/roadmap context never absorbs PRD bodies, CHANGELOG dumps, or
  research transcripts.

### Tiered cost gating (per `_shared/next-steps.md`)

Cost escalates deliberately — never jump to an expensive tier silently:

- **T0 — deterministic next (free, always).** The stage-derived
  `next_recommended()` from `lifecycle.json`. Always computed; the floor that
  even `--gaps` returns first. Zero LLM, zero network.
- **T1 — local LLM gap analysis (DEFAULT).** Offline reasoning over `PRD.md`
  (via the ALIGN subagent — never inline) + `CHANGELOG.md` +
  `.renmark/memory/features.md` to surface uncovered requirements / unbuilt
  promises / drift, and propose the next feature. Local only — **no network**.
  If T1 hits an unfamiliar domain it cannot reason about offline, it raises an
  **unknown-domain flag** (the only condition besides explicit opt-in that
  permits T2).
- **T2 — live web research (OPT-IN, default OFF).** Web search for prior-art /
  competitive best-practice next-step ideas. Runs **only** on explicit user
  opt-in (`--gaps --research`) **or** when T1 raises its unknown-domain flag.
  Never the default; never silent. Runs in a subagent via Claude Code's own web
  tools (no Python dep), returning a bounded ≤5-line idea list.

### Flow

```
/renmark:roadmap --gaps
  → T0  next_recommended()                      # free, always — durable state
  → T1  ALIGN subagent (prd-alignment.md):      # DEFAULT, offline
          inputs: feature_description + file_scope ONLY (never PRD body)
          subagent reads PRD.md in its own context
          + CHANGELOG.md + features.md
        → bounded ≤5-line gap verdict / uncovered-requirement list
  → T2  [opt-in OR T1 unknown-domain flag] web-research subagent
        → bounded ≤5-line best-practice ideas
  → advisory next-feature suggestion
  → PRD changes route to /renmark:prd (human-gated). Roadmap writes nothing.
```

### Output

A short advisory list: uncovered requirements / drift, plus a suggested next
feature. Surface it to the user; do not write it to `PRD.md` or any roadmap file.
Any concrete PRD addition is handed to `/renmark:prd` for the human to approve.

## Do not (gap mode)

- Read the `PRD.md` body inline — always dispatch the ALIGN subagent.
- Write `PRD.md`, any roadmap/gap file, or git history — route proposals to
  `/renmark:prd` (human-gated).
- Run T2 web research by default — it is opt-in / unknown-domain only.
- Pull subagent transcripts, PRD bodies, or research dumps into context — bounded
  ≤5-line summaries only.

---

## What's next

*End by calling `renmark.lifecycle.next_steps(repo, "roadmap")` and render per
`${CLAUDE_PLUGIN_ROOT}/skills/_shared/next-steps.md` (class 3 — resume-pipeline
+ 1–2 local actions). The in-flight feature's next command is `(Recommended)`;
add the skill's local follow-ups (e.g. open the top-ranked gap item, or re-run
`--gaps --research`). Render via `AskUserQuestion` (handoff-menu.md rules 6–9);
require an explicit choice.*

---

*Rule-affecting note for maintainers: this mode's scope (read-only / advisory /
human-gated; one-writer rule for `PRD.md`; ALIGN-subagent-only PRD reads) mirrors
the contracts in `CLAUDE.md` and `AGENTS.md` — mirror any change to that scope in
both root files in the same commit.*

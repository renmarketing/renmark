---
name: roadmap
description: Use when the user wants a status report on what renmark has built in this project — typed as /renmark:roadmap, "show the roadmap", "what's been built", "token usage report". Prints a table of task | llm | status | tokens | $ | commit, synthesized from features.md, usage.jsonl, and git log. Zero LLM calls.
---

# roadmap

## Overview

Project-level status reporter. Pulls from three sources to build a per-task table with totals:

- `.renmark/memory/features.md` — declared features
- `.renmark/state/usage.jsonl` — token spend per LLM call
- `git log` — task-N commits that have landed

Output columns: **task | llm | status | tokens | $ | commit** + totals.

## When invoked

```bash
renmark-execute --roadmap
```

(or call `renmark.roadmap.build_rows(repo)` + `render_table(rows)` from inside this skill).

Show the rendered table to the user. Also write the current snapshot to `.renmark/memory/roadmap.md` so it's committed alongside the rest of the docs.

## Statuses

| Status | Meaning |
|---|---|
| `shipped` | a `[renmark] task N:` (or `[codex] task N:` or `[manual] task N:`) commit exists in git |
| `in-progress` | usage.jsonl has an entry for the task but no matching commit |
| `retried` | multiple usage entries for the same task without a commit (likely escalated) |
| `planned` | listed in features.md "Planned" but no usage yet |

## When to use

- "Show me the roadmap"
- "How much have we spent?"
- "What's the status?"
- After completing a plan run, to summarize what landed

## Sample output

```
| task   | llm                            | status      | tokens | $       | commit  |
|--------|--------------------------------|-------------|-------:|--------:|---------|
| task 1 | llama-3.2-3b-instruct          | shipped     |    191 | free    | `e373204` |
| task 2 | mistral-large-3-675b-instruct  | shipped     |    981 | free    | `45227a1` |
| task 3 | llama-3.2-3b-instruct          | shipped     |    304 | free    | `611391f` |
| task 4 | codex                          | retried     | 148321 | $7.416  | `—`     |
| task 5 | llama-3.2-3b-instruct          | shipped     |    362 | free    | `bda857a` |
| task 6 | llama-3.2-3b-instruct          | shipped     |   1320 | free    | `f7720b2` |

Totals: 6 tasks · 151,479 tokens · $7.416
By status: retried=1, shipped=5
```

## Do not (status mode)

- Make any LLM calls. The status table is pure aggregation.
- Modify `features.md`, `usage.jsonl`, or git history. Read-only synthesis.

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

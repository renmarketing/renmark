---
name: backlog
description: "Use when the user wants to review or act on tracked work items — typed as `/renmark:backlog` or phrases like \"show the backlog\", \"what's pending review\", \"approve and build X\". Opens an interactive list and per-item detail view; 'Approve and build' builds the item on a managed branch."
---

# backlog

## Overview

`/renmark:backlog` is renmark's **human approval buffer** (PRD REQ-13): the queue where
proposed/tracked work waits for a human to triage it before any tokens flow. It is the
front door between *"something should be built"* and *"build it now."* The skill lists the
backlog, opens a per-item detail view, and routes each item to one of five dispositions —
**Approve and build**, **Research more**, **Split**, **Reject**, **Back**.

The deterministic ledger lives in `renmark/backlog.py` (`BacklogItem`, `STATUSES`,
`DISPOSITIONS`, `read_item` / `write_item` / `list_items`, `next_id`,
`managed_branch_name`, `completion_report`, `status_for_outcome`,
`is_terminal_disposition`). **This skill DRIVES the queue; the module OWNS the state.**
The driver triages items and dispatches builds; the module persists each item, coerces
malformed status back to `needs review`, and never raises into the caller.

**Context hygiene (REQ-5/11):** the skill reads ONLY item metadata (title, status, source,
risk, summary, evidence path, recommended action, served requirements) and verify metadata
(`.verification.md`). It NEVER reads generated code, diffs, evidence bodies, or artifact
contents into conversation — only summaries, paths, status, and verification verdicts.

> Vibe coders rarely type `/renmark:backlog` — `/renmark:start` and the gate menus surface
> approval choices for them. This is the expert triage surface.

## When to Use

- A queue of proposals (bugs, ideas, QA gaps, research findings, user requests) needs a
  human decision before building.
- "Show me what's pending review", "approve and build the rate-limit item", "reject that".

**Do NOT use:**
- To build something already approved and scoped → `/renmark:loop` or `/renmark:orchestrate`.
- To brainstorm a raw idea into a spec → `/renmark:brainstorm`.
- To merge / release / PR → that's `/renmark:finish` (Approve-and-build stops *before* those).

## Steps

**Step 0 — Context check.** Call `lifecycle.skill_preamble(repo, 'backlog')`. If it returns
a non-None hint, surface it as a one-line note. Then detect in-flight work and offer to
resume rather than starting fresh:

- Scan backlog items for `status == "in progress"` via `backlog.list_items(repo)`. For each
  such item, read its stored `loop_id` and call `renmark.loop.read_loop(repo, item.loop_id)`
  to fetch current loop state — backlog items are the index into loops, there is no separate
  loop-enumeration API. A `running` / `awaiting-approval` loop state → an Approve-and-build
  is mid-flight. Surface the resume command + iteration / budget-remaining.
- If any backlog item has `status == "in progress"` (even if its loop has already reached a
  terminal state awaiting human merge approval), surface "resume <id>" instead of opening
  the list cold.

If either is in flight, **offer resume first** — do not start a second build (see Human
gates & hygiene: only one code-writing loop per working tree).

### 1. List view

Read the queue as **bounded metadata only** (context hygiene — never read evidence bodies
or code):

```python
from renmark import backlog
items = backlog.list_items(repo)
```

Present the items through `renmark.interaction.build_selector` (handoff-menu.md rules 6–9),
one option per item, each showing `title · status · source · risk · pending decision`.
Mark the highest-priority item as the sole recommendation so it is index 0. Use
the active host's option cap; if more items exist, surface the highest-priority (lowest
status in the machine first: `needs review` / `needs approval` outrank `blocked` /
`completed`) and print the full numbered fallback beneath so the rest stay reachable.
Always include a `Back / Nothing` exit. On selection, open the **Detail view** (Step 2).

### 2. Detail view (selected item)

`backlog.read_item(repo, item_id)` → show the bounded item card (metadata only):

```
<title>   [<id>]
  Status:              <status>
  Source:              <source>          Risk: <risk>
  Summary:             <summary>
  Evidence:            <evidence_path>    (path only — never read its body)
  Recommended action:  <recommended_action>
  Served requirements: <served_requirements, if known>
  Pending decision:    <pending_decision>
```

Then offer the action set through `build_selector` (rules 6–9). Recommend the
item's `recommended_action` when it maps to an option; otherwise recommend
`Back`. Require an explicit choice:

| Option | Effect |
|---|---|
| **Approve and build** | Step 3 — sets `in progress`, branches, runs bounded Loop Mode. |
| **Research more** | Step 4 — route to research/brainstorm; status stays `needs review`. |
| **Split into smaller items** | Step 4 — create child items at `needs approval`. |
| **Reject** | Step 4 — status `rejected`; no branch. |
| **Back** | Return to the List view (Step 1). |

### 3. Approve and build (the load-bearing wiring)

This is the only path that spends tokens. It is gated by the human's explicit selection of
**Approve and build** — that selection *is* the approval (REQ-13 buffer → REQ-12 dispatch).

1. **Promote status.** Set the item `approved`, then `in progress`, and persist:
   ```python
   item.status = "in progress"
   backlog.write_item(repo, item)        # status is validated on read: off-vocabulary values coerce to needs review on the next read
   ```
2. **Derive the loop goal** from the item — `title` + `summary` + `recommended_action`
   composed into one goal sentence. No new flags, no extra prompts.
3. **Create the managed branch** (NO orphan branches start here — the disposition is
   recorded at the end, Step 3b):
   ```bash
   git checkout -b <branch>      # <branch> from backlog.managed_branch_name(item.id, slug)
   ```
   Record `item.branch = <branch>` and `backlog.write_item`.
4. **Run bounded Loop Mode** per the `/renmark:loop` driving procedure (single upfront
   approval already satisfied by the Approve-and-build selection — do NOT re-prompt
   per iteration). The bounds are **HARDCODED — no user-facing flags**:
   - `max_iterations = 5` (HARDCODED — `renmark.loop.DEFAULT_MAX_ITERATIONS`).
   - budget = the **default** (`DEFAULT_BUDGET_TOKENS`). No `--budget`, no
     `--max-iterations`, no backlog-ID flag is ever exposed to the user.
   - The loop cycles `orchestrate → verify → decide`, **commits each passing iteration to
     the managed branch**, and stops at a terminal status (`done` / `budget-hit` /
     `max-iter` / `awaiting-approval` / `stalled`). Reads ONLY verify metadata + the ledger.
5. **Bounded completion line.** On terminal status, print the single
   `backlog.completion_report(goal_reached=…, iteration=N, max_iterations=5)` line
   ("Goal reached in N/5…" / "Stopped after 5/5…"). No diffs, no transcript.

### 3b. Branch lifecycle — NO ORPHAN BRANCHES

Every managed branch MUST end in **exactly one** recorded `DISPOSITIONS` value before this
skill returns. Route on the loop's terminal verify result:

**Final verify PASS** (loop reached `done`):
- **STOP for human merge approval (REQ-12 — never auto-merge).** Surface the gate; invoke
  `/renmark:approve` to flip the lifecycle `human_review_required` bit.
- **INTERIM state — awaiting-merge (NOT a disposition, NOT an orphan):** while the human
  has not yet approved the merge, the item remains `status = "in progress"` with its
  `branch` and `loop_id` recorded on the item. The branch is intentionally retained and
  the item is resumable. This is NOT an orphan branch — the branch is tracked on the item,
  and re-entering `/renmark:backlog` (Step 0) detects it and resumes to the merge gate.
  A disposition is **terminal** and is set **only at a terminal outcome** — the
  awaiting-merge interim is a tracked, resumable state, not a disposition.
- On approval: merge the branch into `main` → **RE-RUN `/renmark:verify` on `main`** (the
  goal must still hold post-merge) → delete the branch → set
  `item.status = "completed"`, `item.disposition = "merged-deleted"`, `backlog.write_item`.
  This is the terminal outcome; `merged-deleted` is recorded only after merge + delete
  complete. Then emit the completion event:
  ```python
  from renmark import analytics, state as rstate
  analytics.record_event(repo, ts=rstate.now_iso(), kind="backlog_completed", item_id=item.id)
  ```

**Final verify FAIL, or loop hit `5/5` without success** (`max-iter` / `stalled` / failing
`done`):
- Do **NOT** merge. Set `item.status = "blocked"`, `backlog.write_item`. Emit the blocked event:
  ```python
  analytics.record_event(repo, ts=rstate.now_iso(), kind="backlog_blocked", item_id=item.id)
  ```
- OFFER keep-or-delete through `build_selector`, with **Keep the branch
  (Recommended)** first:
  | Choice | Disposition | Branch |
  |---|---|---|
  | **Keep the branch** (resume / inspect later) | `kept` | left in place |
  | **Abandon** (discard the attempt) | `abandoned-deleted` | `git branch -D <branch>` |
- Persist the chosen `item.disposition` (`backlog.write_item`). Validate with
  `backlog.is_terminal_disposition(item.disposition)` before returning.

The skill MUST NOT return while a managed branch exists without a recorded disposition.

### 4. Non-build dispositions

| Option | Action |
|---|---|
| **Research more** | Route to `/renmark:brainstorm` (its research step covers prior-art/best-practice digging; a dedicated `/renmark:research` skill does not exist). Leave `item.status = "needs review"` — it stays in the queue for re-triage after research lands. |
| **Split into smaller items** | Guidance: create child items (one per sub-scope) at `status = "needs approval"` via `backlog.next_id` + `backlog.write_item`, each pointing back at the parent in its `summary`. MVP MAY stub the decomposition mechanics, but MUST persist the split intent (at minimum the parent re-tagged + a note of the requested children) so the decision survives a `/clear`. |
| **Reject** | Set `item.status = "rejected"`, `backlog.write_item`. No branch is created. Emit: `analytics.record_event(repo, ts=rstate.now_iso(), kind="backlog_rejected", item_id=item.id)`. |
| **Back** | Return to the List view (Step 1) — no state change. |

## Human gates & hygiene

- **Human approval gates (REQ-12).** Merge, release, PRD edits, destructive ops, and any
  budget escalation REQUIRE explicit human approval. AI generates and commits code on the
  managed branch; the human owns merges and releases. Invoke `/renmark:approve` to flip the
  lifecycle `human_review_required` bit. Approve-and-build's bounded loop never crosses
  these edges — it stops at `awaiting-approval` and hands off.
- **One code-writing loop per working tree.** REFUSE to start a second concurrent build
  while a `running` loop or an `in progress` backlog item exists in this tree (Step 0
  detects it). Offer resume, not a parallel build.
- **Context hygiene.** The orchestrator/skill reads ONLY summaries, paths, metadata,
  status, and verification evidence — **never code, diffs, evidence bodies, or transcripts.**

## Scheduled QA proposer (design-only)

The read-only proposer lane that auto-files QA-gap items into this backlog (REQ-14) is
**design-only** — see `plugin/skills/backlog/SCHEDULED-QA.md`. It is NOT executed by this
skill; `/renmark:backlog` only triages items that already exist in the ledger.

## Next step

*End by calling `renmark.lifecycle.next_steps(repo, "backlog")` and render the
result per `${CLAUDE_PLUGIN_ROOT}/skills/.shared/next-steps.md` (class 3 —
resume-pipeline + 1–2 local actions). The generic aux router for `backlog`
produces `/renmark:backlog (refresh the list)` and `/renmark:finish` — those
are the non-blocked fallbacks. The skill drives its own hand-off menu directly
and MUST diverge from the generic aux for the blocked path:*

- *PASS-and-approved build exit → `/renmark:finish` `(Recommended)`, then
  `/renmark:backlog (refresh the list)`.*
- *Blocked build exit (loop hit max-iter / stalled / failing done) → the skill
  MUST explicitly offer `/renmark:debug` `(Recommended)` in this hand-off menu,
  followed by `/renmark:backlog (refresh the list)`. The generic aux router does
  not surface debug; the skill owns this routing decision and must present it
  directly.*
- *All other exits (Research more, Split, Reject, Back) → `/renmark:backlog
  (refresh the list)` `(Recommended)`, then `/renmark:finish` as secondary.*

*Add the backlog's local follow-ups (re-open the list, triage the next item).
Present via `AskUserQuestion` (handoff-menu.md rules 6–9); require an explicit
choice — never auto-proceed.*

Do not paste the rendering rules — cite the file.

*Mirror any rule changes in `AGENTS.md` in the same commit.*

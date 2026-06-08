---
name: setup
description: Thin alias — `/renmark:setup` refreshes/back-fills renmark rule blocks in an existing project by delegating to `/renmark:init`'s deterministic rule-block merge. The front-door "initialize renmark into an existing project" pipeline is now `/renmark:init`.
---

# setup

## Overview

`/renmark:setup` is now a **thin alias**. Per PRD REQ-8, the single front-door
for "initialize renmark into an existing project" is **`/renmark:init`** — it
scans the repo, seeds `.renmark/`, and back-fills the managed renmark rule blocks
into `CLAUDE.md` / `AGENTS.md`.

`/renmark:setup` exists only as a **rule-block-refresh alias**: instead of
duplicating any scaffold logic, it delegates to `/renmark:init`'s deterministic
rule-block back-fill (`merge_rule_blocks`). Running it re-merges any missing
managed `<!-- BEGIN:x -->` blocks without touching hand-written content — exactly
what `init` does, scoped to the rule-block step.

## When to Use

- You typed `/renmark:setup` out of habit → forward to `/renmark:init`.
- You only want to refresh/back-fill renmark rule blocks in `CLAUDE.md` /
  `AGENTS.md` → this alias runs `merge_rule_blocks` (the `init` rule-block step).

For full project initialization (repo scan, `.renmark/` seeding, project map),
use **`/renmark:init`** directly — it is the canonical pipeline.

## Steps

**Step 0 — Context check.** Call `lifecycle.skill_preamble(repo, 'setup')`. If it
returns a non-None hint, surface it as a one-line note.

**Delegate.** Invoke `/renmark:init`'s deterministic rule-block back-fill
(`merge_rule_blocks`) — do NOT reimplement scaffold logic here. Back-fill targets
**CLAUDE.md's** managed rule blocks; `AGENTS.md.template` carries no managed
markers, so there is **no CLAUDE.md→AGENTS.md rule-block mirroring** — AGENTS.md is
created from its own template by scaffold, and rule-block parity is the
human/`sync-note` discipline. If a target file's markers are malformed,
`merge_rule_blocks` **skips it (never writes)** and raises `MarkerCorruptionError`
(init exits 2). Report which blocks were back-filled, that all were present, or
that the file was skipped for corruption.

## What's next

setup is an **aux / terminal skill** (class 3 in
`${CLAUDE_PLUGIN_ROOT}/skills/_shared/next-steps.md`). It sits off the main
pipeline line.

> *End by calling `renmark.lifecycle.next_steps(repo, "setup")` and render per
> `${CLAUDE_PLUGIN_ROOT}/skills/_shared/next-steps.md` (class 3 — resume-pipeline
> + 1–2 local actions). The in-flight feature's next command is `(Recommended)`;
> add the skill's local follow-ups. Render via `AskUserQuestion` (handoff-menu.md
> rules 6–9); require an explicit choice.*

Since this is a thin alias, the natural local follow-up is **`/renmark:init`**
(the canonical front-door). Do not paste the rendering rules or the gate menu —
cite `next-steps.md`.

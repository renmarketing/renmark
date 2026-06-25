---
name: guide
description: "Use when the user types /renmark:guide or says \"I don't know which command to use\", \"help me pick a pipeline\", \"where do I start\", \"what renmark command should I use\", \"guide me\"."
disable-model-invocation: false
---

# guide

## Overview

`/renmark:guide` is the **interactive decision-tree on-ramp** for renmark. Instead of reading a flat command list, the user answers one question and lands on the right pipeline. Zero configuration; no knowledge of renmark internals required.

This is distinct from `/renmark:help` (which is a static reference listing all commands). `guide` is the wizard that routes you to the right command; `help` is the dictionary you consult once you know the command.

## When to use

- First time in a repo that uses renmark
- You know roughly what you want to do but can't remember the command
- You want a recommendation rather than a reference

## Steps

### 1. Ask the one routing question

Using `AskUserQuestion`, ask exactly this — no preamble, no renmark jargon:

> **What are you trying to do right now?**
>
> 1. Build something new — start a new app, tool, or feature from scratch
> 2. Change or add to an existing build
> 3. Something is broken and I need to fix it
> 4. See what's been built / find gaps / decide what's next
> 5. We're done — I want to verify, review, and ship
> 6. Adopt renmark into an existing repo that doesn't use it yet
> 7. I was mid-something and lost my place after a `/clear`
> 8. I'm not sure — show me the options

Label option 1 `(Recommended start)` if no lifecycle state exists; otherwise label the option that matches the current lifecycle stage `(Recommended)`.

### 2. Route based on answer

| Answer | Recommended command | When to offer the alternative |
|--------|--------------------|-----------------------------|
| 1 — new build | `/renmark:start` | Offer `/renmark:brainstorm` if the idea sounds fuzzy ("I have an idea but…") |
| 2 — change / add | `/renmark:feature` | — |
| 3 — broken / bug | `/renmark:debug` | — |
| 4 — what's next | `/renmark:roadmap` | — |
| 5 — ship it | `/renmark:finish` | Mention `/renmark:verify` if there is doubt whether the last build passed |
| 6 — adopt renmark | `/renmark:init` | — |
| 7 — lost place | `/renmark:resume` | — |
| 8 — not sure | Print the quick "Which one?" map (copied from `/renmark:help`) and re-ask |

### 3. Confirm and hand off

After routing, say exactly one sentence:

> "Running `/renmark:<command>` now — it will ask you what it needs."

Then invoke the chosen command (dispatch via the skill's own invocation path — do NOT inline its steps here). The user is now in the pipeline; `guide` is done.

**Exception — option 8 (not sure):** Print the quick map and loop back to the question once. If the user is still unsure after the second pass, invoke `/renmark:help` and let them browse.

## Do not

- Describe the internals of the target pipeline here. That lives in each skill's own SKILL.md.
- Show more than one question at a time. The whole point is to reduce cognitive load, not add to it.
- Make any HTTP calls, run subprocesses, or read project files during the routing question. The routing choice is intent-only.
- Advertise a pipeline stage or modifier flag that doesn't exist.

## What's next

`guide` is a class-3 aux/terminal skill under
`${CLAUDE_PLUGIN_ROOT}/skills/_shared/next-steps.md`. After it routes the user
into a pipeline, `guide` itself is done — the target pipeline owns all subsequent
hand-offs. No `AskUserQuestion` picker needed after the dispatch.

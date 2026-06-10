# Contributing a renmark skill

This document is the **governance acceptance bar** for any new renmark skill (or substantive change to an existing one). It exists because renmark's primary design constraint is context hygiene under Sonnet 200k: the orchestrator's reasoning quality degrades long before the window is full, and any new skill that violates the rules below makes every other skill less reliable.

A new skill that cannot tick all 9 boxes below does not merge.

## The 9-rule compliance checklist

For each new **pipeline-class or quality-gate-class** SKILL.md, confirm and document in a `## Governance compliance` section at the bottom of the skill file. Aux/meta skills (class 3 per `_shared/next-steps.md`) MAY use a shorter form — a single-sentence compliance note per applicable rule — but MUST still call out any rule the skill actively relies on:

| # | Rule | Check |
|---|---|---|
| G2 | Canonical state | Skill writes its state to `.renmark/state/`, `.renmark/memory/`, or an artifact under `.renmark/specs|reviews/` before exiting. Never relies on "what was said earlier" in conversation. |
| G3 | Summary boundary | Every orchestrator-visible output line is ≤ 5 lines OR ≤ 300 tokens. Long content goes into an artifact; only a structured summary is returned. |
| G5 | Executor isolation | Heavy cognition (file reads, diff analysis, synthesis, bulk generation) runs in a Codex subprocess via `renmark-execute --task` or in a sandboxed Agent. The orchestrator never does the heavy reading itself. |
| G6 | Artifact governance | Output artifacts are written via `renmark.summary.write_artifact` with full metadata (`artifact_type`, `schema_version`, `created_at`, `source_sha`, `related_plan`, `generator`, optional `stale_after`, `dependency_refs`). |
| G7 | Compact semantics | After `/compact` is run mid-skill, the skill can still resume by reading `.renmark/state/pipeline.json`. The skill does not depend on transcript reasoning for continuity. |
| G8 | Compounding verification | If the skill fails, it appends a learning to `.renmark/memory/learnings.md` and/or a bug to `.renmark/memory/bugs.md`. Failures expand future regression coverage, not vanish silently. |
| G9 | Failure transparency | Artifact metadata sets `completion_state`, `confidence`, `validation_status`, `retry_count`, `parser_success`, `schema_compliance` honestly. Skills that succeed half-way return `partial`, not `complete`. |
| G10 | Workflow recovery | The skill can be re-run after interruption and pick up from the state file. It does not require the user to "start over." |
| G11 | Task isolation | If the skill dispatches sub-tasks (orchestrate, loop, backlog, debug, feature): each sub-dispatch uses `dispatch_task_isolated` (or the documented equivalent for Codex subprocesses), and the orchestrator consumes only `SubagentOutput` fields — never inline transcripts, generated code, or diffs. |

## What this means in practice

When you draft a new SKILL.md, before merging, run yourself through these questions:

1. **Where does my state live?** If the answer involves "the conversation will remember it," redesign. State lives on disk.
2. **What's the worst-case orchestrator-visible output line if my skill misbehaves?** If the answer is "a 200-line diff," redesign. Cap the output.
3. **What model reads the bulky thing?** If the answer is "Sonnet/Opus reads it inline," redesign. Codex or a sandboxed Agent reads it.
4. **What does my artifact look like on disk?** Show the metadata block. If it's missing fields, redesign.
5. **What happens if the user runs `/compact` halfway through my skill?** If the answer is "the user loses their place," redesign.
6. **If my skill fails, does anyone learn from it?** If the answer is no, redesign — add the learnings.md write.
7. **Does my output say `validation_status: validated` when nothing actually validated it?** If yes, redesign — be honest about uncertainty.
8. **If the process crashes mid-skill, can I resume?** If the answer is "you re-run from scratch," redesign — write resume points.
9. **If I dispatch sub-tasks, do they each get an isolated context?** If the answer is "they share the orchestrator's chat history," redesign — use `dispatch_task_isolated`. (Dispatching skills: `orchestrate`, `loop`, `backlog`, `debug`, `feature`.)

## Skill structure template

Every SKILL.md follows the canonical structure (see `plugin/skills/check-plan/SKILL.md` and `plugin/skills/verify/SKILL.md` as references):

```markdown
---
name: <skill-name>
description: <one paragraph — when to use, what it does, what's unique>
---

# <skill-name>

## Overview

(2–4 sentences. What it does. What contract it honors.)

## When to Use

- (concrete triggers)

**Do NOT use:**
- (concrete anti-triggers)

## Steps

### 0. Context check

Call `lifecycle.skill_preamble(repo, '<skill>')`. If it returns a non-None hint,
surface as a one-line note. Do NOT block — user decides.

### 1. ...

## Hand off (wizard step)

(How to chain into the next skill.)

## Governance compliance

| # | Rule | How this skill complies |
|---|---|---|
| G2 | Canonical state | ... |
| G3 | Summary boundary | ... |
| G5 | Executor isolation | ... |
| G6 | Artifact governance | ... |
| G7 | Compact semantics | ... |
| G8 | Compounding verification | ... |
| G9 | Failure transparency | ... |
| G10 | Workflow recovery | ... |
| G11 | Task isolation | N/A (skill does not dispatch sub-tasks) — or — describe how `dispatch_task_isolated` is used |
```

## Long-form rules

If a skill's full rule set runs more than ~50 lines, extract the long-form rules into a sibling file (pattern: `_shared/scope-contract.md` referenced from both `plan/SKILL.md` and `brainstorm/SKILL.md`). Skill files stay scannable; depth lives next to them. Rules shared by 2+ skills go in `skills/_shared/` so they have a single source of truth.

## Adding a new rule block

If you're proposing a new governance rule (G12+):

1. Add it to the governance sections in the repo's root `CLAUDE.md` (the canonical in-repo governance source).
2. Add a `BEGIN:<name>-rule` block to `plugin/templates/CLAUDE.md.template`.
3. Add a one-liner mirror to `plugin/templates/AGENTS.md.template`.
4. Register the block name in `renmark/init.py`'s rule-block registry and add a reference in `plugin/skills/init/SKILL.md`.
5. Add a row to the compliance checklist in this file.

All five edits land in the same commit. Rules without a checklist row don't bind; checklist rows without a CLAUDE.md block aren't merged into existing projects on `/renmark:setup`.

## Why this bar is rigid

Renmark is opinionated about one thing: the orchestrator is a coordinator, not a memory container. Every skill that respects that makes every other skill more reliable. Every skill that doesn't makes the whole pipeline less reliable. There is no in-between — context rot compounds.

If a proposed skill cannot meet the bar, the right move is usually to split it: push the heavy work into Codex (which doesn't care about Sonnet's window) and keep the orchestrator portion tiny.

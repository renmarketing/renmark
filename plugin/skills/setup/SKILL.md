---
name: setup
description: Use when adding renmark to an existing project — creates missing CLAUDE.md, AGENTS.md, CHANGELOG.md, and .renmark/ structure, or merges missing renmark rule blocks into existing files. Safe to run in any project; never overwrites existing content.
---

# setup

## Overview

Prepares an existing project for the renmark workflow. Reads the current project state, creates missing files, and adds missing renmark rule sections to existing ones. Merge-only — never replaces or removes existing content.

## When to Use

- Starting renmark in a project that already has code or config
- CLAUDE.md exists but is missing renmark rules
- CHANGELOG.md doesn't exist yet
- `.renmark/` directory is missing

**Use `/renmark:brainstorm` for empty/new projects** — it bootstraps and brainstorms in one flow.

## Steps

**Step 0 — Context check.** Call `lifecycle.skill_preamble(repo, 'setup')`. If it returns a non-None hint, surface as a one-line note.

**Lifecycle initialization.** As part of setup, if no `.renmark/state/lifecycle.json` exists, leave it that way — `/renmark:start` or `/renmark:feature` will create it when work actually begins. Setup itself does NOT seed a lifecycle (there's no in-flight feature yet).

### 1. Discover project state

```bash
test -f CLAUDE.md     && echo "CLAUDE.md present"
test -f AGENTS.md     && echo "AGENTS.md present"
test -f CHANGELOG.md  && echo "CHANGELOG.md present"
test -d .renmark      && echo ".renmark/ present"
git rev-parse --git-dir 2>/dev/null && echo "git repo" || echo "no git repo"
```

**Detect tech stack** from files present:
- `package.json` → Node.js; scan `dependencies` for express, react, next, vite, etc.
- `requirements.txt` / `pyproject.toml` → Python; scan for flask, django, fastapi
- `go.mod` → Go; `Cargo.toml` → Rust
- `*.db` files or env references → SQLite / Postgres hint
- `Dockerfile` → deployment target hint

### 2. Optimize CLAUDE.md

**If missing:** create from the renmark CLAUDE.md template with the detected stack filled in.

**If exists:** check for each `<!-- BEGIN:x -->` marker. Add any missing blocks from the template at the end of the file. Blocks to check in order:

| Block | What it adds |
|---|---|
| `changelog-rule` | Read CHANGELOG before tasks, append after |
| `refactor-safety-rule` | Checkpoint + baseline before >3-file changes |
| `context-hygiene-rule` | Never read generated files into conversation |
| `executor-dispatch-rule` | codex → renmark-execute, haiku/sonnet/opus → Agent |
| `root-cause-rule` | Root cause sentence required before any fix |
| `verify-before-done-rule` | Re-run verifiers fresh before claiming done |
| `orchestrator-role-rule` | Orchestrator coordinates; does not accumulate context |
| `canonical-state-rule` | Truth lives in `.renmark/` and CHANGELOG, not conversation |
| `summary-boundary-rule` | Orchestrator-visible output ≤ 5 lines or ≤ 300 tokens |
| `context-contamination-rule` | Cross-domain skill changes recommend `/clear` |
| `artifact-governance-rule` | Every artifact carries provenance + freshness metadata |
| `compact-semantics-rule` | `/compact` preserves goals + state, discards stale reasoning |
| `failure-transparency-rule` | Outputs carry completion_state / confidence / validation_status |
| `workflow-recovery-rule` | Multi-step workflows resumable via `.renmark/state/pipeline.json` |
| `task-isolation-rule` | Orchestrate tasks run in isolated subagent contexts |
| `context-budget-rule` | `/compact` at 60%, `/clear` on cross-domain skill changes |
| `lifecycle-rule` | Every stage transition writes `.renmark/state/lifecycle.json` (G12) |

If no renmark tooling table is present, append the full `## Tooling — renmark workflow` section.

### 3. Optimize AGENTS.md

Same logic: create if missing, or append missing rule summaries. Mirror every rule added to CLAUDE.md. AGENTS.md stays shorter — one-liner per rule, not the full block.

### 4. Create or update CHANGELOG.md

**If missing:** create with a single setup entry:

```markdown
# Changelog

## [YYYY-MM-DD] — renmark setup

**Request:** Add renmark workflow to existing project.
**Built:** CLAUDE.md rules, AGENTS.md rules, .renmark/ structure
**Do not change:**
- Changelog format — renmark reads and appends to this file automatically
- The `## [date] — [title]` heading format is parsed by renmark tooling
```

**If exists:** leave as-is. The existing changelog is already the project history — don't touch it.

### 5. Set up .renmark/ structure

```bash
mkdir -p .renmark/{memory,plans,specs,state,debug,logs,reviews}
```

Create any missing memory seed files from templates:
- `stack.md` — fill with detected stack from step 1
- `INDEX.md` — auto-generated index of memory files
- `features.md`, `bugs.md`, `decisions.md`, `routing.md`, `learnings.md` — empty templates

**Git setup:**
- If no `.gitignore` exists, create one with `.renmark/state/` and `.renmark/debug/` entries
- If `.gitignore` exists, check for those entries and add if missing
- If not a git repo, ask: *"Initialize git repo? [Y/n]"* — on Y run `git init -b main && git add -A`

### 5.5 Seed the project map (first-time only)

If `.renmark/memory/project-map.md` does not yet exist, seed it now:

```bash
python -m renmark.init
```

This populates the `<!-- BEGIN:project-stub -->` block in CLAUDE.md (and AGENTS.md if it exists) and writes `.renmark/memory/project-map.md`. The script is deterministic Python — no LLM tokens spent.

**Skip silently if `project-map.md` already exists** — setup is bootstrap-only. Subsequent refreshes happen automatically at the end of `/renmark:finish`, or manually via `/renmark:init`.

If the script exits 1 (CLAUDE.md missing — shouldn't happen since step 2 just created it), note in the report and continue. If it exits 2 (corrupted markers), surface the message and stop; the user has to resolve manually.

Capture the script's stdout line and roll it into step 6's report as `project-map — <stdout>`.

### 6. Report and hand off

```
renmark setup: <project-name>

CLAUDE.md   — [created | 3 rules added: context-hygiene, executor-dispatch, verify-before-done]
AGENTS.md   — [created | synced with CLAUDE.md changes]
CHANGELOG.md — [created | already exists — left as-is]
.renmark/   — [created | already exists]
stack.md    — Node.js + Express + SQLite (detected — verify in .renmark/memory/stack.md)
project-map — [seeded (.renmark/memory/project-map.md) | already existed — skipped]
```

Then prompt:

> *"Project is ready for renmark.*
> *  [b] Brainstorm — design a new feature into a spec via /renmark:brainstorm*
> *  [p] Plan — I already have a description; go straight to /renmark:plan*
> *  [n] Nothing — setup only, stop here"*

On **b** → invoke `/renmark:brainstorm`. On **p** → invoke `/renmark:plan`. On **n** → stop.

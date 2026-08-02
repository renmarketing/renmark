---
name: init
description: "Use for the Project Setup pipeline (/renmark:init) to adopt renmark into a repo — plain requests like \"adopt renmark\", \"set renmark up here\", \"initialize renmark in this project\". The non-destructive, idempotent front door that scaffolds and maps any repo (new, in-progress, or production). Renmark's analog to Claude Code's native /init."
---

# init

## Overview

`/renmark:init` is renmark's **non-destructive front door** — the named adoption
pipeline for bringing renmark into any project, with or without an existing
`CLAUDE.md`. It both *initializes* (scaffolds what's missing) and *documents*
(maps the code), then routes the now-mapped project at its uncovered gaps.

Bound by REQ-30 (orchestration efficiency is a protected capability): the
deterministic scan/scaffold/merge path below is exactly the kind of
zero-LLM, zero-dispatch work REQ-30 requires by default — do not add a
subagent dispatch where the deterministic module already answers the
question.

All scanning, scaffolding, rule-block merging, regex, rendering, and file I/O is
done by the **deterministic, zero-LLM** Python module `renmark.init`. **No LLM
calls are made for the work itself.** The agent's only jobs are: invoke the
script, relay its bounded summary line, and hand off. The agent does **not** read
or merge file bodies, templates, or rule blocks itself — `init.py` does all of
that deterministically (byte-verbatim, unit-tested, idempotent), which is what
keeps the orchestrator's context clean.

Outputs are split across three locations for context-window hygiene:

- **CLAUDE.md / AGENTS.md** get a tiny **stub** (~10-15 lines, ~250 tokens) inside a managed `<!-- BEGIN:project-stub -->` block. Always-loaded context. Includes a `Dev gates:` line listing the project's test/lint/typecheck commands when detected.
- **`.renmark/memory/project-map.md`** — full directory tree, module tables with symbols, command catalog. Not auto-loaded.
- **`.renmark/memory/dev-standards.md`** — detected dev standards (test, lint, formatter, type checker, CI, pre-commit, env schema, DB tooling, local-dev commands, code style, dep policy) **plus** a *Standards health* section that flags gaps and proposes tighten-this recommendations (e.g. "no linter configured", "TypeScript not in strict mode", "secrets risk: `.env` is committed"). Not auto-loaded.

## When to Use

- Onboarding renmark to a project — **even an empty or unscaffolded one** (init scaffolds; you no longer need to run `/renmark:setup` first)
- First-time onboarding to a project that already has substantial code
- After a major restructure (new top-level dirs, renamed modules, new entry points)
- The user says "document the project", "renmark init", "initialize this project", "refresh the project map"
- Called as a sub-step from `/renmark:finish` (post-feature refresh)

**Not for**: spec design (`/renmark:brainstorm`), task decomposition (`/renmark:plan`).
Note: `/renmark:setup` is now a **thin rule-block-refresh alias of init** (see below) — it is no longer a separate bootstrapper.

## The 6-step front-door pipeline

The SKILL orchestrates; `renmark/init.py` (the CLI) does the deterministic work.
A single `python -m renmark.init` invocation performs steps 1–5; the SKILL adds
the step-6 hand-off.

1. **Detect** — project state: `CLAUDE.md` / `AGENTS.md` / `CHANGELOG.md` / `.renmark/` presence, git status, stack (`pyproject.toml` / `package.json` / `go.mod` / `Cargo.toml` / Claude Code plugin manifest). The CLI detects stack; the SKILL surfaces the state from the summary line.
2. **Scaffold-if-missing** — done by `python -m renmark.init`. At the top of `init.run()` it calls `bootstrap(repo, init_git=False)` and creates `CHANGELOG.md` if absent, scaffolding `CLAUDE.md` / `AGENTS.md` / `.gitignore` / `.renmark/` from templates. **Existence-skip = non-destructive.** Because of this, init **no longer errors when `CLAUDE.md` is absent** — it creates it.
3. **Rule-block back-fill (deterministic, zero-LLM)** — `merge_rule_blocks()` in `init.py`. For an existing `CLAUDE.md` missing canonical `<!-- BEGIN:<name> -->`…`<!-- END:<name> -->` rule blocks, it inserts the template's blocks **byte-verbatim** at the right markers, reusing the marker primitives proven in lint. Idempotent (skips blocks already present), non-destructive (never edits existing block content, never overwrites hand-modified blocks). `CLAUDE.md.template` is the only template carrying managed markers, so this step is effectively CLAUDE.md-only — **there is no CLAUDE.md↔AGENTS.md rule-block back-fill/mirroring** (AGENTS.md is created from its own template by scaffold; rule-block parity is the human/`sync-note` discipline). **Safety:** before inserting into any file, its existing markers are validated for balance — a file with orphan/unclosed/duplicate/out-of-order markers is **skipped, never written**, and init exits **2** (user-fixable document corruption). On malformed input merge SKIPS; it never inserts and never produces unbalanced markers. **The agent does NOT read or merge rule blocks — init.py does it deterministically.**
4. **Scan & map** — walks the repo, extracts public symbols, writes the full map to `.renmark/memory/project-map.md`, and merges the `BEGIN:project-stub` block into CLAUDE.md/AGENTS.md. Byte-equality skip avoids prompt-cache busting.
5. **Standards + health gaps** — writes `.renmark/memory/dev-standards.md` plus the *Standards health* gap report. The health report now ALSO surfaces **advisory modularity / scalability gaps** (oversized files, long/complex functions, high import coupling / cognitive complexity) the same way as standards-health gaps — purely informational, **NEVER blocking** (init still exits 0).
6. **Roadmap `--gaps` hand-off at the end** — SKILL-level (per ADR-009). A freshly initialized or re-mapped project is exactly when "what are the uncovered gaps / next moves?" matters most, so init ends by routing into roadmap's **gap-discovery mode** rather than dead-ending. If the project has no `PRD.md`, nudge `/renmark:prd` first.

## Steps

**Step 0 — Context check.** Call `lifecycle.skill_preamble(repo, 'init')`. If it returns a non-None hint, surface as a one-line note.

### 1. Run the pipeline

```bash
python -m renmark.init
```

That single command runs steps 1–5 above (detect → scaffold → back-fill → scan/map → standards). The script:

1. Scaffolds any missing `CLAUDE.md` / `AGENTS.md` / `.gitignore` / `.renmark/` / `CHANGELOG.md` (existence-skip, non-destructive).
2. Back-fills any missing canonical rule blocks byte-verbatim (idempotent, never edits existing blocks).
3. Walks the repo (excludes `.git`, `node_modules`, `.venv`, `dist`, `build`, `.renmark/state`, `.renmark/debug`, etc.).
4. Detects stack from `pyproject.toml` / `package.json` / `go.mod` / `Cargo.toml` / Claude Code plugin manifest.
5. Extracts public symbols from the top-20 largest source files (Python, JS/TS, Go, Rust, Ruby).
6. Renders a stub and the full map; merges the `project-stub` block.
7. **Byte-equality-skip:** if the rendered stub body matches what's already in CLAUDE.md, the file isn't rewritten — no prompt-cache bust. Same for `project-map.md`.
8. Writes whatever changed; prints a one-line summary to stdout.

**Stdout format:**
```
OK  stub=<created|refreshed|unchanged> agents=<…|skipped> map=<…> standards=<…> blocks=<N|unchanged> modules=<N> commands=<N> langs=<py,ts,…> ref=YYYY-MM-DD@<git-sha>
HEALTH: <N> standards gaps (<X danger>, <Y warn>, <Z info>)[, <M> modularity (<major> major/<warn> warn)] — see `.renmark/memory/dev-standards.md`
```

The `HEALTH:` line appears with two optional parts: standards gaps (if any) and modularity gaps (if any), joined by `, `. Both halves are omitted when their count is zero. A clean, fully-initialized project produces just the `OK` line with everything `unchanged`.

**Exit codes:**
- `0` — success (whether or not anything changed; this is the normal path even when CLAUDE.md was absent and had to be scaffolded)
- `2` — corrupted markers (multiple `BEGIN:project-stub`, unbalanced rule-block markers) or bad CLI usage

There is **no longer an exit 1 for "CLAUDE.md missing"** — init scaffolds it. (A post-scaffold guard remains as a should-never-happen safety net.)

### 2. Flags

- `python -m renmark.init scan` — scan only, print diagnostic summary, no writes
- `python -m renmark.init --full` — include private symbols (leading `_`, lowercase Go funcs, non-`pub` Rust)
- `python -m renmark.init --deep` — add expensive standards checks (samples last 20 commits for conventional-commits style; future: `gh api` branch-protection lookups, test-naming inference). Always safe to combine with refresh or scan.
- `python -m renmark.init <path>` — operate on a different repo path (default `.`)

**The baseline scaffold + back-fill + dev-standards scan runs every time, no flag needed.** The `--deep` flag adds the slow / opinionated checks on top.

### 3. Relay the result

Pass the stdout line through to the user as-is, optionally with a one-sentence interpretation. If exit code is non-zero, surface the FAIL line and stop — do not attempt manual fallback steps. Never read the scaffolded files, templates, or merged rule blocks into the conversation; the bounded stdout line is the only thing the orchestrator consumes.

### 4. Declared model tier (one-time)

After the pipeline has run — `.renmark/memory/routing.md` now exists, whether it
was just scaffolded or was already there — check it for a `## Model tiers` block:

```bash
grep -q '^## Model tiers' .renmark/memory/routing.md
```

- **Block present** → **never overwrite it.** Report the current declaration in
  one line (e.g. `Model tiers: top_tier=fable (declared 2026-06-12)`) and move on.
  This keeps the step idempotent — re-running init never re-asks or rewrites.
- **Block absent** → ask **once** via `renmark.interaction.build_selector`:
  *"Do you have Claude Fable 5 access for this project?"* with exactly two
  options: `No (Recommended)` → `top_tier: opus`, `Yes` → `top_tier: fable`.
  Then insert the
  block into `routing.md` **above the `## Learned overrides` section**, using
  exactly this grammar:

  ```
  ## Model tiers
  top_tier: <fable|opus>
  declared_at: <YYYY-MM-DD>
  ```

- **Non-interactive runs** (called as a sub-step from `/renmark:finish`, or any
  context where `AskUserQuestion` is unavailable) write the default
  `top_tier: opus` — the safe value; re-run init interactively to upgrade it.

Note: `/renmark:setup` inherits this step via its delegation to init's rule-block
merge, and `/renmark:doctor` reports the current declaration.

### 4b. Global auto-routing offer (one-time, non-blocking)

Like the model-tier declaration above, this is a **one-time, idempotent offer** —
never a gate. It asks whether renmark should become the default for build/dev work
in **every** project on this machine by adding a `renmark-routing` rule block to the
global, every-session `~/.claude/CLAUDE.md`.

Resolve the current state first via the committed helper:

```bash
python -c "from renmark.global_routing import detect_global_rule; print(detect_global_rule())"
```

- `present-with-rule` → the rule is already installed. **Skip silently** — do not
  re-ask, do not report. This keeps the step idempotent across re-runs.
- `missing` or `present-without-rule` → offer **once** via
  `renmark.interaction.build_selector` (text
  fallback below for non-interactive runs):

  > "Want renmark to be the default for build/dev work in every project on this
  > machine? I can add a routing rule to `~/.claude/CLAUDE.md` — it's backed up
  > first and never overwrites your other rules.
  >
  > 1. [y] Yes (Recommended) — make renmark the default everywhere
  > 2. [n] Skip"

  - **Yes** → run `/renmark:doctor --install-routing` (the dedicated opt-in flag
    that calls `global_routing.install_global_rule()`), or call
    `global_routing.install_global_rule()` directly. Relay the one-line result
    (`{action, path, backup}`) and note it takes effect next session. (Plain
    `/renmark:doctor --fix` no longer writes the global rule — it only detects
    and reports it.)
  - **Skip** → continue. Do not re-offer on this run.

**Non-blocking, always:** this offer NEVER halts init — whatever the answer (or on a
non-interactive run where `AskUserQuestion` is unavailable, in which case skip the
write and continue silently), init proceeds straight to the roadmap hand-off.
**Honest scope:** auto-routing is a model-followed instruction, not a hard interlock;
an explicit `/renmark:` command always wins; it is per-machine (the global write
targets THIS machine's `~/.claude/CLAUDE.md`). The global write is always
user-approved (offer → on yes → `--install-routing` write), backed up, and never
silently performed — see `/renmark:doctor` for the advisory detect/report (plain
`--fix`) and the explicit opt-in write (`--install-routing`).

### 5. What's next — roadmap hand-off (step 6)

A freshly initialized or re-mapped project is exactly when "what are the uncovered
gaps / next moves?" matters most. So init ends by routing into roadmap's
**gap-discovery mode** (per ADR-009), giving the user a guided hand-off instead of
an informational dead-end. If the project has no `PRD.md`, nudge `/renmark:prd`
first so gap discovery has a source of truth to compare against.

> *End by calling `renmark.lifecycle.next_steps(repo, "init")` and render per
> `${CLAUDE_PLUGIN_ROOT}/skills/.shared/next-steps.md` (class 3 — resume-pipeline
> + 1–2 local actions). The in-flight feature's next command is `(Recommended)`;
> add the skill's local follow-ups. Render via `AskUserQuestion` (handoff-menu.md
> rules 6–9); require an explicit choice.*

For init specifically, the **PRIMARY recommended action is
`/renmark:roadmap` (gap mode)** — point the now-mapped project at its uncovered
gaps and next moves (nudge `/renmark:prd` first if no PRD exists). Surface the
in-flight feature's resume step (or `/renmark:start` if none) as an alternate,
plus `Nothing`. Init never auto-proceeds — it hands off through an explicit choice.

### Heartbeat cron hint (optional, non-blocking)

Before presenting the handoff menu, run:

```bash
renmark-execute --heartbeat-check-cron
```

If output is `not-installed`, add one optional menu item to the `AskUserQuestion` handoff:

> **Set up heartbeat monitor** (optional) — run every 30 min to auto-resume if a usage limit is hit:
> `(crontab -l 2>/dev/null; echo "*/30 * * * * cd <repo> && renmark-execute --heartbeat --auto-resume") | crontab -`
> Replace `<repo>` with the actual repo path from `lifecycle.json`.

This is purely informational. The user can skip it. It never gates the handoff or blocks the recommended action.

## `/renmark:setup` is now a thin alias of init

Per PRD REQ-8, `/renmark:setup` is no longer a separate bootstrapper — it is a
**thin rule-block-refresh alias of init**. Its SKILL/command pair stays (lint
pairing green, `name: setup`, cites `next-steps.md` as an aux-class skill), but
its body delegates to init's **rule-block back-fill** (step 3) rather than
duplicating scaffold logic. Use `/renmark:init` for full onboarding; `/renmark:setup`
when you specifically want to refresh/back-fill canonical rule blocks into existing
CLAUDE.md/AGENTS.md.

## When called as a sub-step (not standalone)

`/renmark:finish` invokes `python -m renmark.init` directly. It:

- Doesn't repeat init's lifecycle preamble (the caller already did one).
- Captures the stdout line and folds it into its own summary report.
- For `/renmark:finish`: if the script wrote anything, `git add` the changed files and commit as `docs: refresh project map`.

## Fallback (if `renmark.init` is unavailable)

If `python -m renmark.init` returns "module not found" — older or broken renmark install — tell the user to re-run `bash install.sh` from the renmark checkout (or reinstall the plugin). Do not implement the scan, scaffold, or rule-block merge manually in the agent context; that wastes tokens and re-introduces the very problem the script exists to solve.

## Boundaries

- **`init.py` is strictly ZERO-LLM.** Pure Python; near-zero token cost per invocation. All scaffolding, rule-block merging, scanning, and rendering is deterministic. The roadmap gap-discovery hand-off (step 6) is the only LLM-touching part, and it lives at the **SKILL level**, never inside `init.py`.
- **Non-destructive + idempotent.** Existence-skip on create; byte-equality skip on managed blocks; rule-block back-fill only inserts *missing* canonical blocks and never edits existing or hand-modified content. Re-running on a fully-initialized project byte/existence-skips everything → "unchanged".
- **AGENTS.md is created from its own template — NOT rule-block-mirrored.** Scaffold creates `AGENTS.md` from `AGENTS.md.template` when absent. That template carries **no managed rule-block markers**, so `merge_rule_blocks` always reports `AGENTS.md: 0` and performs **no CLAUDE.md→AGENTS.md back-fill**. Rule-block parity between the two files is the human/`sync-note` discipline, not an automated merge — do not claim mirroring.
- **Bounded source edits.** The script never edits, renames, or deletes anything under the project tree except: scaffolded onboarding files (when absent), the managed `project-stub` and canonical rule blocks in CLAUDE.md, and the generated `.renmark/memory/` files.
- **No `.renmark/state/` writes** beyond optional lifecycle tick.
- **Respect freeze.** If `/freeze` is active and a target file is outside the allowed path, abort with a message.
- **Malformed markers never corrupt a file.** Before inserting, `merge_rule_blocks` validates each target's markers for balance. A file with orphan `END`, unclosed `BEGIN`, duplicate, or out-of-order markers is **skipped — never written** (no partial insert, no block placed inside an open block) — and raises `MarkerCorruptionError`. On malformed input the merge SKIPS the file; it never inserts.
- **Exit codes.** `0` = success (whether or not anything was written). `1` = scaffold/template-availability failure (CLAUDE.md still absent, or the renmark templates directory could not be located). `2` = user-fixable document corruption (a CLAUDE.md/AGENTS.md has unbalanced managed markers) or bad CLI usage — the file is left untouched; fix the markers and re-run.
- **Cache discipline.** Byte-equality skip is the script's responsibility — agents don't need to check separately.

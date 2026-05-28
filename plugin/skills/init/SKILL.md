---
name: init
description: Use when the user wants renmark to document the project itself — scans the repo for file structure, modules, and public functions/exports. Writes a tiny stub into CLAUDE.md/AGENTS.md (always loaded) and the full detailed map into .renmark/memory/project-map.md (read on demand). Renmark's analog to Claude Code's native /init, designed for context-window hygiene. Idempotent — re-run anytime to refresh.
---

# init

## Overview

Generates a *codebase map* and *dev-standards report*, split across three locations for context-window hygiene:

- **CLAUDE.md / AGENTS.md** get a tiny **stub** (~10-15 lines, ~250 tokens) inside a managed `<!-- BEGIN:project-stub -->` block. Always-loaded context. Includes a `Dev gates:` line listing the project's test/lint/typecheck commands when detected.
- **`.renmark/memory/project-map.md`** — full directory tree, module tables with symbols, command catalog. Not auto-loaded.
- **`.renmark/memory/dev-standards.md`** — detected dev standards (test, lint, formatter, type checker, CI, pre-commit, env schema, DB tooling, local-dev commands, code style, dep policy) **plus** a *Standards health* section that flags gaps and proposes tighten-this recommendations (e.g. "no linter configured", "TypeScript not in strict mode", "secrets risk: `.env` is committed"). Not auto-loaded.

All scanning, regex, rendering, and file I/O is done by the deterministic Python module `renmark.init`. **No LLM calls are made for the work itself.** The agent's only job is to invoke the script and relay its summary lines.

## When to Use

- First time onboarding renmark to a project that already has substantial code
- After a major restructure (new top-level dirs, renamed modules, new entry points)
- The user says "document the project", "renmark init", "refresh the project map"
- Called as a sub-step from `/renmark:setup` (first-time bootstrap) and `/renmark:finish` (post-feature refresh)

**Not for**: rule scaffolding (`/renmark:setup`), spec design (`/renmark:brainstorm`), task decomposition (`/renmark:plan`).

## Steps

**Step 0 — Context check.** Call `lifecycle.skill_preamble(repo, 'init')`. If it returns a non-None hint, surface as a one-line note.

### 1. Run the scanner

```bash
python -m renmark.init
```

That's the whole operation. The script:

1. Walks the repo (excludes `.git`, `node_modules`, `.venv`, `dist`, `build`, `.renmark/state`, `.renmark/debug`, etc.).
2. Detects stack from `pyproject.toml` / `package.json` / `go.mod` / `Cargo.toml` / Claude Code plugin manifest.
3. Extracts public symbols from the top-20 largest source files (Python, JS/TS, Go, Rust, Ruby).
4. Renders a stub and the full map.
5. **Byte-equality-skip:** if the rendered stub body matches what's already in CLAUDE.md, the file isn't rewritten — no prompt-cache bust. Same for `project-map.md`.
6. Writes whatever changed; prints a one-line summary to stdout.

**Stdout format:**
```
OK  stub=<created|refreshed|unchanged> agents=<…|skipped> map=<…> standards=<…> modules=<N> commands=<N> langs=<py,ts,…> ref=YYYY-MM-DD@<git-sha>
HEALTH: <N> gaps (<X danger>, <Y warn>, <Z info>) — see `.renmark/memory/dev-standards.md`
```

The `HEALTH:` line only appears when there's at least one gap. A clean project produces just the `OK` line.

**Exit codes:**
- `0` — success (whether or not anything changed)
- `1` — CLAUDE.md missing (tell user to run `/renmark:setup` first)
- `2` — corrupted markers (multiple `BEGIN:project-stub`) or bad CLI usage

### 2. Flags

- `python -m renmark.init scan` — scan only, print diagnostic summary, no writes
- `python -m renmark.init --full` — include private symbols (leading `_`, lowercase Go funcs, non-`pub` Rust)
- `python -m renmark.init --deep` — add expensive standards checks (samples last 20 commits for conventional-commits style; future: `gh api` branch-protection lookups, test-naming inference). Always safe to combine with refresh or scan.
- `python -m renmark.init <path>` — operate on a different repo path (default `.`)

**The baseline dev-standards scan runs every time, no flag needed.** The `--deep` flag adds the slow / opinionated checks on top.

### 3. Relay the result

Pass the stdout line through to the user as-is, optionally with a one-sentence interpretation. If exit code is non-zero, surface the FAIL line and stop — do not attempt manual fallback steps.

### 4. Done

No automatic handoff. Init is informational.

## When called as a sub-step (not standalone)

`/renmark:setup` and `/renmark:finish` invoke `python -m renmark.init` directly. They:

- Don't repeat init's lifecycle preamble (the caller already did one).
- Capture the stdout line and fold it into their own summary report.
- For `/renmark:finish`: if the script wrote anything, `git add` the changed files and commit as `docs: refresh project map`.

## Fallback (if `renmark.init` is unavailable)

If `python -m renmark.init` returns "module not found" — older renmark install — tell the user to run `bin/renmark-install` or update renmark. Do not implement the scan manually in the agent context; that wastes tokens and re-introduces the very problem the script exists to solve.

## Boundaries

- **Read-only on source.** The script never edits, renames, or deletes anything under the project tree except the stub block in CLAUDE.md/AGENTS.md and the generated `.renmark/memory/project-map.md`.
- **No LLM calls.** Pure Python; near-zero token cost per invocation.
- **No `.renmark/state/` writes** beyond optional lifecycle tick.
- **Respect freeze.** If `/freeze` is active and CLAUDE.md is outside the allowed path, abort with a message.
- **Cache discipline.** Byte-equality skip is the script's responsibility — agents don't need to check separately.

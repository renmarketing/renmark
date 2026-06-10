---
name: doctor
description: Use when `/renmark:*` commands aren't appearing, the plugin seems broken, or the user just wants a sanity check on the install. Diagnoses Claude Code plugin registration health and proposes (or applies) fixes.
---

# doctor

## Overview

Verifies that renmark is correctly installed and registered with Claude Code. Catches the three places a directory-marketplace plugin install can silently fail: `installed_plugins.json` registration, `settings.json` `enabledPlugins`, and `settings.json` `extraKnownMarketplaces`. Also checks version parity, cache symlink, Python package importability, and CLI on PATH.

All checks are deterministic Python — **zero LLM cost per run**. The agent's only job is to invoke the script and relay its output.

## When to Use

- The user types `/renmark:` and nothing comes up
- `/reload-plugins` says "1 error during load" or the count seems low
- After a version bump where renmark suddenly stops surfacing
- The user installed renmark via `install.sh` but slash commands aren't appearing
- Sanity check before reporting a bug ("is my install even right?")

## Steps

**Step 1 — Run the diagnostic.**

```bash
python -m renmark.doctor
```

The script returns:
- Exit 0 if healthy (warnings alone still exit 0)
- Exit 1 only when a check FAILED

It prints a checklist with ✓ / ✗ / ! glyphs and a `fix:` line for any failure that has a known remediation.

**Step 2 — Offer auto-fix if any failures are flagged `auto_fixable`.**

The output's final line will say something like:
> `2 can be auto-fixed: python -m renmark.doctor --fix`

If the user agrees (or didn't pass anything that implies they wanted just a report), run:

```bash
python -m renmark.doctor --fix
```

This applies the safe automatic fixes (settings.json edits, cache symlink, registry registration) — each writing a backup file first. The script re-runs the checks after fixing and prints the final state.

**Step 3 — Tell the user to `/reload-plugins`.**

Settings changes don't take effect until Claude Code reloads its plugin registry. After a fix run, end with:

> *"Run `/reload-plugins` in Claude Code to pick up the changes."*

## Flags

- `python -m renmark.doctor` — diagnose only, no writes
- `python -m renmark.doctor --fix` — apply safe auto-fixes (settings.json + registry + cache symlink). Each modified file gets a `.doctor.bak.<timestamp>` backup.
- `python -m renmark.doctor --json` — machine-readable output, same checks

## What it does NOT do

- **Doesn't `pip install` anything.** If the Python package isn't importable, the script flags it but won't reinstall — that's a system-level change the user should do explicitly.
- **Doesn't restart Claude Code.** No mechanism to do so; the user must run `/reload-plugins` themselves.
- **Doesn't touch the source repo.** Only writes to `~/.claude/` config files and `~/.claude/plugins/cache/renmark-local/`.

## Boundaries

- Read-only by default. `--fix` writes only to `~/.claude/settings.json`, `~/.claude/plugins/installed_plugins.json`, and `~/.claude/plugins/cache/renmark-local/`. Always with a timestamped backup of any pre-existing file.
- No LLM calls. No network. No code in the project tree is touched.
- Designed to be re-runnable. `--fix` is idempotent — applying it twice is a no-op on the second run.

## What's next

doctor is an **aux / terminal skill** (class 3 in
`${CLAUDE_PLUGIN_ROOT}/skills/_shared/next-steps.md`). After diagnosis (and any
`--fix`), don't dead-end — return the user to the pipeline.

> *End by calling `renmark.lifecycle.next_steps(repo, "doctor")` and render per
> `${CLAUDE_PLUGIN_ROOT}/skills/_shared/next-steps.md` (class 3 — resume-pipeline
> + 1–2 local actions). The in-flight feature's next command is `(Recommended)`;
> add the skill's local follow-ups. Render via `AskUserQuestion` (handoff-menu.md
> rules 6–9); require an explicit choice.*

The two doctor-local actions to surface alongside the resume-pipeline option:

- **Re-run the skill that was failing** — the whole reason doctor was invoked was
  a `/renmark:*` command that wouldn't surface or behave; once the install is
  healthy (and after `/reload-plugins`), re-run that command.
- **Resume the in-flight feature** — `next_recommended()` from `lifecycle.json`,
  so the user lands back on the pipeline rather than stranded at a health report.

If no feature is in flight, the resume option becomes `/renmark:start`. Do not
paste the rendering rules — cite the file.

---
name: hygiene
description: "Use to garbage-collect stale renmark artifacts and prune append-only memory logs — typed as /renmark:hygiene. Default dry-run; --apply to make changes."
disable-model-invocation: true
---

# hygiene

## Overview

Hygiene closes the loop on renmark's existing `stale_after` / `created_at` / `source_sha` artifact metadata. The schema was designed in earlier releases (see `renmark/summary.py`); this module is the sweeper that finally consumes it. Built on top of `summary.is_stale()` plus the memory helpers — stdlib only, no LLM calls.

Two operations, one CLI:

- **scan** — walk `.renmark/specs|plans|reviews|research|state/wave-summaries`, identify artifacts past their `stale_after` (or older than `--ttl-days` when metadata is missing), archive them to `.renmark/archive/YYYY-MM/` preserving the original repo-relative path. Artifacts referenced by `lifecycle.json` are never archived.
- **prune** — age out and dedupe entries in `learnings.md`, `bugs.md`, `features.md`. Curated memory files are never touched.

## When to Use

- Monthly cleanup of a bloated `.renmark/` directory.
- After a long-running feature branch leaves stale plans/reviews behind.
- Before archiving a finished project — compact the artifact tree first.
- When memory logs (`learnings.md`, `bugs.md`, `features.md`) accumulate duplicates from repeated debug sessions.

## Steps

**Step 0 — Context check.** Call `lifecycle.skill_preamble(repo, 'hygiene')`. Hygiene is `meta` domain; cross-domain prompts only fire on transitions FROM `build` / `debug` / `audit`. Surface the returned hint if non-None.

### 1. Run the scanner

```bash
python -m renmark.hygiene scan                   # dry-run, default 90d TTL
python -m renmark.hygiene scan --apply           # actually archive
python -m renmark.hygiene all --apply --ttl-days 60 --memory-days 120
```

Subcommands: `scan` (artifacts), `prune` (memory logs), `all` (both).

### 2. Relay the result

Pass the bounded stdout through to the user unchanged. The script emits one or two status lines — `HYGIENE …` always, and `MEMORY …` only when pruning ran — plus an `ERRORS …` line only on `--apply` failures. Do not paraphrase or expand — the format is the contract.

## Flags

- `--apply` — make changes on disk. Default is dry-run (report only).
- `--ttl-days N` — artifact TTL fallback when `stale_after` is missing (default `90`).
- `--memory-days N` — age-out threshold for memory log entries (default `180`).
- `--include-memory` — when subcommand is `scan`, also runs `prune` after.
- `--repo PATH` — project root (default `.`).

## Boundaries

- **NEVER advances `lifecycle.json` stage.** Hygiene is diagnostic, not a workflow transition.
- **All writes inside `.renmark/`.** Refuses with `ValueError` if `archive_root` resolves outside that subtree.
- **Archive layout preserved.** `.renmark/plans/foo.plan.md` → `.renmark/archive/YYYY-MM/plans/foo.plan.md`.
- **Lifecycle-referenced artifacts never archived** — even if past their TTL.
- **Curated memory files are off-limits.** Only `learnings.md`, `bugs.md`, `features.md` are pruned. Never touches `decisions.md`, `INDEX.md`, `project.md`, `stack.md`, `architecture.md`, `conventions.md`, `routing.md`, `dev-standards.md`, `MEMORY.md`, `project-map.md`.
- **No LLM calls.** Deterministic Python only.

## What's next

Hygiene is an aux / terminal skill (class 3) — it sits off the main pipeline and
never advances `lifecycle.json`. After a hygiene pass, return the user to the
in-flight feature rather than leaving them on a terminal cliff:

> *End by calling `renmark.lifecycle.next_steps(repo, "hygiene")` and render per
> `${CLAUDE_PLUGIN_ROOT}/skills/_shared/next-steps.md` (class 3 — resume-pipeline
> + 1–2 local actions). The in-flight feature's next command is `(Recommended)`;
> add the skill's local follow-ups. Render via `AskUserQuestion` (handoff-menu.md
> rules 6–9); require an explicit choice.*

The recommended next step is **resume-pipeline**: the in-flight feature's
`next_recommended()` (from `lifecycle.json`), so the user picks the cleaned-up
`.renmark/` tree back up at its next stage. If no feature is in flight, the
resume option becomes `/renmark:start`. Local follow-ups to offer: re-run with
`--apply` (if the prior run was a dry-run), or `prune`/`scan` the other target.

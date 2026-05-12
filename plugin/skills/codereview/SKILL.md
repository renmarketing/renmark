---
name: codereview
description: Use when the user wants a diff or PR reviewed — typed as /renmark:codereview or phrases like "review this", "review my changes", "check this PR", "code review HEAD~3..HEAD". Runs multi-pass review: codex adversarial (find bugs) → sonnet quality (style/naming/readability) → opus architecture/security on hot files. Produces structured markdown at .renmark/reviews/YYYY-MM-DD-<sha>.review.md with severity-ranked findings.
---

# codereview

## Overview

Reviews a diff in three passes, each routed to the model best suited for that lens. Output is a structured review file with findings ranked by severity. NEVER auto-applies fixes — the human or `/renmark:orchestrate` does that.

## When to Use

- "Review my changes" / "review this PR"
- After completing a feature, before merging
- After `/renmark:orchestrate` finishes — sanity check what NIM/Codex wrote

**Do NOT use:**
- For debugging a runtime failure — use `/renmark:debug`
- For implementing fixes — review only; fixes go through orchestrate or direct edit

## Status note (v0.0.1)

Phase 3 work. The skill ships as a documented workflow; routing through Sonnet/Opus subagents requires the Phase 1 dispatch layer. For v0.0.1, the adversarial pass (codex) is available today via `codex review`; quality and architecture passes can be invoked manually with the Agent tool.

## The three passes

### Pass 1 — Adversarial (find bugs)

**Model:** Codex CLI, read-only sandbox.

Run:
```bash
codex exec --sandbox read-only "Review the diff <ref>..HEAD. Find runtime bugs, logic errors, off-by-ones, race conditions, and bad assumptions. List each finding with: file:line, severity, why it's wrong, suggested fix. Do not modify any files."
```

Capture output to `.renmark/reviews/<sha>/adversarial.md`.

### Pass 2 — Quality (style, naming, readability)

**Model:** Sonnet via Agent tool with model override.

Prompt the subagent with the diff and ask for:
- Naming clarity
- Function size / single responsibility
- Comments where the WHY isn't obvious
- Redundancy / repetition
- Test coverage gaps

Capture to `.renmark/reviews/<sha>/quality.md`.

### Pass 3 — Architecture / Security (hot files only)

**Model:** Opus via Agent tool.

Apply only to "hot" files:
- Files >150 lines in the diff
- Files touching auth, crypto, SQL, user input
- Files implementing public APIs

Ask Opus for:
- Architectural concerns (coupling, layering, premature abstractions)
- Security issues (injection vectors, auth bypass, data leaks)
- Edge cases the diff doesn't handle

Capture to `.renmark/reviews/<sha>/architecture.md`.

## Steps

### 1. Determine scope

If user gave a ref range (`HEAD~3..HEAD`, `main..feature`), use that. Otherwise default to `git diff --name-only HEAD` (working tree).

### 2. Show diff summary

```bash
git diff --stat <range>
```

Confirm with the user. Ask: *"Run all three passes, or just one? [all/adversarial/quality/architecture]"*

### 3. Run passes

In order: adversarial → quality → architecture. Each writes its own file under `.renmark/reviews/<short-sha>/`.

### 4. Consolidate

Merge the three pass files into `.renmark/reviews/YYYY-MM-DD-<sha>.review.md`:
- Findings grouped by severity (Critical / Major / Minor / Nit)
- Each finding cites pass (which model found it) + file:line
- Top of doc summarizes counts per severity

### 5. Hand off

Tell the user: *"Review written to `<path>`. <N critical, M major, K minor> findings."*

Don't auto-fix. The human reads and decides.

## Focus modes

`/renmark:codereview HEAD~3..HEAD --focus security` runs only Opus pass with security framing.
`--focus perf` runs only architecture pass with performance framing.
`--focus all` (default) runs all three.

## Reference

- Codex review syntax: `codex review --help`
- Existing `review` slash command for inspiration

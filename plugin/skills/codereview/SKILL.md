---
name: codereview
description: Use when the user wants a diff or PR reviewed — typed as /renmark:codereview or phrases like "review this", "review my changes", "check this PR", "code review HEAD~3..HEAD". Runs a single codex-based review pass in a read-only sandbox; codex emits a structured markdown report at .renmark/reviews/YYYY-MM-DD-<sha>.review.md. Opus only reads the severity summary — never the diff itself, to keep context lean.
---

# codereview

## Overview

**Single-pass codex review.** Codex runs in `--sandbox read-only` mode, reads the diff, and emits a structured findings report. Opus orchestrates but never ingests the diff body — that's the whole point of routing this to codex.

No Sonnet or Opus passes. Earlier designs included them; experience showed that putting code into the conversation defeats the context-hygiene goal renmark is built for. Codex is purpose-built for adversarial bug-finding and that's the most valuable single lens.

Output: structured markdown at `.renmark/reviews/YYYY-MM-DD-<sha>.review.md` with findings grouped by severity (Critical / Major / Minor / Nit).

Recommended cadence: **after a full plan completes**, not after every task. `/renmark:orchestrate` offers a hand-off prompt at the end of a successful run.

## When to Use

- "Review my changes" / "review this PR"
- After completing a feature, before merging
- After `/renmark:orchestrate` finishes — sanity check what agents wrote

**Do NOT use:**
- For debugging a runtime failure — use `/renmark:debug`
- For implementing fixes — review only; fixes go through orchestrate or direct edit

## How it runs (one pass, codex)

```bash
codex exec --sandbox read-only -
```

The skill pipes a prompt like:

```
Review the diff <range>. Find: runtime bugs, logic errors, off-by-ones,
race conditions, security issues (injection, auth, data leaks), bad
assumptions, edge cases the code doesn't handle.

For each finding:
  - file:line
  - severity: Critical | Major | Minor | Nit
  - one-sentence description
  - one-sentence fix suggestion

Top of report: summary counts per severity.
Do not modify any files. Do not exit until the review is complete.
```

Codex writes its review to `.renmark/reviews/YYYY-MM-DD-<sha>.review.md` directly (or the skill captures stdout and writes it).

## Steps

**Step 0 — Context check.** Call `lifecycle.skill_preamble(repo, 'codereview')`. If it returns a non-None hint, surface as a one-line note.

**Lifecycle note:** Codereview is orthogonal to stage progression but commonly runs as part of the Review stage. Skill should NOT bump `lifecycle.json.stage` directly — the wrapper `/renmark:feature` handles that after both codereview AND any secure audit complete.

### 1. Determine scope

If the user gave a ref range (`HEAD~3..HEAD`, `main..feature`), use that. Otherwise default to `git diff --name-only HEAD` (working tree). Show a `git diff --stat <range>` summary and confirm with the user.

### 2. Run codex

Shell out via the renmark CLI (or directly) with the prompt above. Streaming output goes to `.renmark/logs/codereview-<run_id>.log` for troubleshooting if codex misbehaves.

### 3. Capture the review

Codex output is parsed (or written through verbatim) and saved to `.renmark/reviews/YYYY-MM-DD-<sha>.review.md`.

### 4. Hand off

Tell the user — using ONLY the summary, never the diff body:

> *"Review at `<path>`. <N critical, M major, K minor> findings.*
> *What's next?*
> *  [o] Open — open the review file to read the full findings*
> *  [f] Fix — kick off a new /renmark:plan built from the critical findings*
> *  [n] Done — stop here; the review stays on disk"*

Don't auto-fix. The human reads and decides.

## When to invoke

Recommended cadence (for context hygiene):

- **Auto-suggested by `/renmark:orchestrate`** after a successful plan run completes — one review for the whole feature, not one per task.
- **Before merge** when you're about to land work to main.
- **Ad-hoc** when you want a sanity check on a specific range.

Avoid: running codereview after every single task. That creates one review per file and floods the reviews directory.

## Reference

- Codex review syntax: `codex review --help`
- Existing `review` slash command for inspiration

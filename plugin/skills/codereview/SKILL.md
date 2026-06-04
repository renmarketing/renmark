---
name: codereview
description: Use when the user wants a diff or PR reviewed — typed as /renmark:codereview or phrases like "review this", "review my changes", "check this PR", "code review HEAD~3..HEAD". Runs a single codex-based review pass in a read-only sandbox; codex emits a structured markdown report at .renmark/reviews/YYYY-MM-DD-<sha>.review.md. Opus only reads the severity summary — never the diff itself, to keep context lean. Supports `--focus optimize` and `--focus standards` to swap the prompt template; default is correctness + quality.
---

# codereview

## Overview

**Single-pass codex review.** Codex runs in `--sandbox read-only` mode, reads the diff, and emits a structured findings report. Opus orchestrates but never ingests the diff body — that's the whole point of routing this to codex.

No Sonnet or Opus passes. Earlier designs included them; experience showed that putting code into the conversation defeats the context-hygiene goal renmark is built for. Codex is purpose-built for adversarial bug-finding and that's the most valuable single lens.

Output: structured markdown at `.renmark/reviews/YYYY-MM-DD-<sha>.review.md` with findings grouped by severity (Critical / Major / Minor / Nit).

Recommended cadence: **after a full plan completes**, not after every task. `/renmark:orchestrate` offers a hand-off prompt at the end of a successful run.

## Argument parsing

- `$ARGUMENTS` may contain a git ref range AND/OR `--focus <mode>`.
- Recognized modes: `optimize`, `standards`. Anything else (or absent) = default.
- Parse rule: strip the `--focus <mode>` pair from `$ARGUMENTS`; remaining text is the ref range (passed unchanged to Step 1).
- Unknown mode → print a one-line note (`unknown --focus <mode> — falling back to default`) and use the default prompt. Do not abort.

## When to Use

- "Review my changes" / "review this PR"
- After completing a feature, before merging
- After `/renmark:orchestrate` finishes — sanity check what agents wrote

**Do NOT use:**
- For debugging a runtime failure — use `/renmark:debug`
- For implementing fixes — review only; fixes go through orchestrate or direct edit

## How it runs (one pass, codex)

The agent selects one of three prompt blocks below based on the parsed focus, then pipes it to `codex exec --sandbox read-only -`.

```bash
codex exec --sandbox read-only -
```

### Prompt: default (correctness + quality)

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

### Prompt: optimize

```
Review the diff <range> for PERFORMANCE and IDIOM issues. Focus on:
  - unnecessary allocations, copies, or work inside hot loops
  - asymptotic complexity surprises (accidental O(n²) over reasonable inputs)
  - repeated computation that could be cached or hoisted
  - blocking calls where async / batching would scale better
  - non-idiomatic constructs that have a clearer, faster language-native form
  - resource lifecycle issues (locks held too long, file handles, sockets)

Out of scope for this pass: correctness bugs, security, edge cases.
  If you spot a correctness bug while looking at perf, list it as ASIDE
  (severity: Major), but DO NOT exhaustively hunt for them — that's the
  default focus's job.

For each finding:
  - file:line
  - severity: Critical | Major | Minor | Nit
  - one-sentence description (what's slow / non-idiomatic, and roughly why)
  - one-sentence fix suggestion

Top of report: summary counts per severity, plus a single bold line
"Focus: optimize" so the reader knows which lens this pass used.
Do not modify any files. Do not exit until the review is complete.
```

### Prompt: standards

```
Review the diff <range> for adherence to the project's UNWRITTEN code
standards. Skip what tools/precommit.sh already checks (ruff lint, ruff
format, mypy strict, plugin lint, pytest) — those are the WRITTEN
standards and the gate already enforces them. Look only at the
conventions that exist in the codebase but are not enforced by tooling.

Sources of truth:
  - Spot-check 3–5 other files in the same module/package for
    conventions: imports (relative vs absolute), error-handling shape
    (raise vs return None vs Result), logging style, naming, type
    annotation density, docstring presence and shape, where helpers go.
  - If .renmark/memory/conventions.md exists, treat it as a hard rubric.
  - If .renmark/memory/dev-standards.md flags any "gap" the diff touches,
    call those out.

Specifically look for:
  - pathlib.Path vs os.path mixing
  - dict[str, Any] in new code where a TypedDict / dataclass would fit
    the existing pattern
  - new public function without a type annotation when siblings have them
  - error suppression (bare except, except Exception: pass) inconsistent
    with sibling files
  - reinventing a helper that already exists elsewhere in the package
  - naming drift (camelCase function in a snake_case file, etc.)
  - missing or stale CHANGELOG entry when sibling features have them

For each finding:
  - file:line
  - severity: Critical | Major | Minor | Nit  (most standards findings
    will be Minor or Nit; Major only if it would block merge in a
    maintainer review)
  - one-sentence description (what convention is broken, and what the
    majority pattern looks like)
  - one-sentence fix suggestion

Top of report: summary counts per severity, plus a single bold line
"Focus: standards" so the reader knows which lens this pass used.
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

Tell the user — using ONLY the summary, never the diff body. Lead with the codereview-specific actions, then render the shared quality-gate menu so re-testing from a different angle stays one keystroke away:

> *"Review at `<path>` (focus: <mode>). <N critical, M major, K minor> findings.*
> *What's next?*
> *  1. [o] Open — open the review file to read the full findings*
> *  2. [fix] Fix — kick off a new /renmark:plan built from the critical findings"*

Omit the `(focus: <mode>)` parenthetical entirely when mode is default — preserves the existing terse output for the common case.

Then append the hand-off menu from `${CLAUDE_PLUGIN_ROOT}/skills/_shared/handoff-menu.md`, applying the rendering rules:

- **Omit `[c] Code review`** — we just ran it.
- **Show `[s] Smoke`** and `[qa] QA` (a finding worth re-verifying live often lives in the just-reviewed diff).
- **Show `[dq] Deep QA`** only if a passing `.qa.md` exists for the current sha.
- **Show `[d] Debug`** only if any Critical findings exist (Major+ alone is informational, not a debug trigger).
- **Show `[f] Finish`** unconditionally and `[n] Nothing` always.

Continue the numbering from the `[o]`/`[fix]` actions above so the user sees one
single numbered list (e.g. `1. [o]`, `2. [fix]`, then `3. [s]`, `4. [qa]`, …) —
and require an explicit choice before doing anything.

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
- Focus modes: see Argument parsing above. Adding a new focus = adding a new `### Prompt: <name>` block; nothing else to change.

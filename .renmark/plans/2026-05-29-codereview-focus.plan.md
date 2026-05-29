---
artifact_type: plan
schema_version: 1
created_at: 2026-05-29T00:00:00Z
source_sha: f5e480c
generator: opus
related_spec: null
stale_after: 2026-08-29T00:00:00Z
dependency_refs: []
---

# /renmark:codereview --focus

**Branch:** any (single-skill edit, fits on `main` or any feature branch)
**Base sha:** `f5e480c`
**Goal:** Extend `/renmark:codereview` with a `--focus <mode>` flag selecting one of three prompt templates. Same skill, same artifact path, same ≤5-line summary contract — just a different prompt fed to Codex. Zero new module, zero new context cost.

## Focus modes

| Mode | Lens | Prompt focus |
|------|------|--------------|
| (default) | correctness + quality | runtime bugs, logic errors, off-by-ones, races, security, edge cases — **current behavior, unchanged** |
| `optimize` | performance + idiom | allocations, asymptotic complexity, repeated work, language-idiom violations, unnecessary copies/locks/awaits |
| `standards` | **unwritten** project standards | uses `pathlib` not `os.path` when the rest of the codebase does; consistent error-handling shape; logging style; naming; dead code. Skips what `tools/precommit.sh` already checks (ruff, mypy strict, etc.) — those are the *written* standards. |

## Out of scope

- **`--focus prior-art`** — explicitly dropped. "Is there a stdlib / well-known lib that does this better?" is *research*, not *review*. It would require codex to reach outside the diff and consult external knowledge / web. That belongs on `/renmark:brainstorm` (as a prior-art lookup mode) or a standalone `/renmark:prior-art` skill — not on codereview's read-only sandbox. Documented here so future contributors don't re-add it without revisiting the trade-off.
- No new Python module. The prompt selection lives in `SKILL.md` as three labeled blocks; the agent picks one based on the parsed `$ARGUMENTS`.
- No change to the artifact path (`.renmark/reviews/YYYY-MM-DD-<sha>.review.md`), the summary contract, or the hand-off menu.

## Tasks

### Task 1: codereview SKILL.md — add --focus parsing + three prompt blocks
- **mode:** B
- **target:** plugin/skills/codereview/SKILL.md
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 1
- **est_tokens:** 2500
- **est_cost_usd:** 0.038
- **verifier:** grep -q "focus optimize" plugin/skills/codereview/SKILL.md && grep -q "focus standards" plugin/skills/codereview/SKILL.md && grep -c "^### Prompt:" plugin/skills/codereview/SKILL.md | awk '{exit ($1 < 3)}'
- **spec:**
  Update `plugin/skills/codereview/SKILL.md` to accept `--focus <mode>` and select a corresponding prompt template. Keep the file readable and under ~220 lines.

  **Changes:**

  1. **Frontmatter `description`** — append one short clause: "Supports `--focus optimize` and `--focus standards` to swap the prompt template; default is correctness + quality."

  2. **New section `## Argument parsing`** (insert after `## Overview`, before `## When to Use`). Concise. Describe:
     - `$ARGUMENTS` may contain a git ref range AND/OR `--focus <mode>`.
     - Recognized modes: `optimize`, `standards`. Anything else (or absent) = default.
     - Parse rule: strip the `--focus <mode>` pair from `$ARGUMENTS`; remaining text is the ref range (passed to Step 1 unchanged).
     - Unknown mode → print a one-line note and fall back to default; do not abort.

  3. **Section `## How it runs (one pass, codex)`** — replace the single prompt block with a short paragraph that says "the agent selects one of three prompt blocks below based on the parsed focus, then pipes it to `codex exec --sandbox read-only -`." Move the existing prompt under a new heading `### Prompt: default (correctness + quality)` and keep its body unchanged.

  4. **Add `### Prompt: optimize`** immediately after the default prompt. Body — single fenced block containing:
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

  5. **Add `### Prompt: standards`** immediately after the optimize prompt. Body:
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

  6. **Step 4 (Hand off)** — minimal update: the summary line should include the focus mode when non-default. Change the existing:
     > *"Review at `<path>`. <N critical, M major, K minor> findings.*

     to:
     > *"Review at `<path>` (focus: <mode>). <N critical, M major, K minor> findings.*

     Omit the parenthetical entirely when mode is default, to preserve existing terse output.

  7. **Section `## Reference`** — add one bullet at the end: "Focus modes: see Argument parsing above. Adding a new focus = adding a new `### Prompt: <name>` block; nothing else to change."

  **Do NOT change** the artifact path, the codex invocation flags (`--sandbox read-only -`), the lifecycle note, or the Hand-off menu's lower-half (the shared handoff-menu.md include). The whole point of this feature is "same skill, different prompt."

  **Do NOT split prompts into a separate `prompts/` directory.** Three labeled blocks inside SKILL.md is the chosen structure for now; revisit only if a 5th focus mode is added.

### Task 2: codereview slash command — update argument-hint
- **mode:** B
- **target:** plugin/commands/codereview.md
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 1
- **est_tokens:** 200
- **est_cost_usd:** 0.001
- **verifier:** grep -q "focus" plugin/commands/codereview.md
- **spec:**
  Update `plugin/commands/codereview.md`. The current `argument-hint` says `'[ref range like HEAD~3..HEAD or empty for working tree]'`. Change it to:

  `'[ref range like HEAD~3..HEAD] [--focus optimize|standards]'`

  Do not modify any other content (frontmatter `description`, body text, the `$ARGUMENTS` dispatch line). The skill body handles parsing — the command's only job is to surface the new flag in tab-completion / `--help` style listings.

### Task 3: CHANGELOG — v0.5.7 entry
- **mode:** B
- **target:** CHANGELOG.md
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 1
- **est_tokens:** 1500
- **est_cost_usd:** 0.035
- **verifier:** head -3 CHANGELOG.md | grep -q "v0.5.7"
- **spec:**
  Prepend a new `## v0.5.7 — 2026-05-29 (codereview --focus: optimize / standards prompt templates)` entry to `CHANGELOG.md`. Match the voice and structure of recent entries (v0.5.5 and v0.5.4 are good shape — driving idea, what shipped, "Do not change" guards).

  **Required sections:**

  - **Driving idea (1 paragraph)** — codereview's default lens is correctness; sometimes you want a different lens (perf, project-standards) WITHOUT paying for a second skill, a second module, or a second artifact path. `--focus` swaps the prompt template only. Zero new context cost.

  - **What shipped** — bullets:
    - `--focus optimize` — perf / idiom lens: allocations, complexity, hot-loop work, blocking calls, resource lifecycle.
    - `--focus standards` — unwritten-standards lens: looks at the diff against sibling files in the same package for conventions that aren't enforced by `tools/precommit.sh`. Skips what ruff/mypy/format already check — those are the *written* standards and the pre-commit gate is the enforcer.
    - Default (no flag) — unchanged. Same prompt, same output, same artifact path.
    - Summary line now surfaces the focus mode when non-default: `Review at <path> (focus: optimize). N findings.`
    - Hand-off menu, artifact path, codex invocation, lifecycle behavior — all unchanged.

  - **What did NOT ship (and why)** — one paragraph naming `--focus prior-art`. Quote the reasoning: prior-art lookup ("is there a stdlib / well-known lib that does this better?") is research, not review. It would require codex to reach beyond the diff. That belongs on `/renmark:brainstorm` as a prior-art mode, or a separate `/renmark:prior-art` skill if usage justifies the slot. Future contributors should not re-add it without revisiting the trade-off.

  - **Do not change** guards:
    - The three-prompts-in-one-SKILL.md structure. Splitting into a `prompts/` subdirectory is premature until there's a 5th mode.
    - The unchanged default prompt. Editing the default prompt = silently changing behavior of every existing codereview invocation; that's a separate feature ticket.
    - Codex sandbox flags (`--sandbox read-only -`). The standards focus is tempting to give web access for "look up the idiom" — don't. Read-only sandbox is what keeps codereview cheap and reproducible. If web access is wanted, route through brainstorm/prior-art, not codereview.
    - The omission of the `(focus: default)` parenthetical when no flag was used. Default output stays terse; the parenthetical only appears for non-default modes.

  Keep entry length comparable to recent patch releases (~60–100 lines). No emojis.

---

## Cost preview (honest accounting — includes ~10k Agent overhead per Claude task)

| Task | Executor | Output | Total tokens (w/ overhead) | Cost |
|------|----------|--------|----------------------------|------|
| 1 codereview SKILL.md | sonnet | 2,500 | 12,500 | $0.038 |
| 2 codereview command | haiku | 200 | 10,200 | $0.001 |
| 3 CHANGELOG.md | sonnet | 1,500 | 11,500 | $0.035 |

**Total: ~$0.07 across 3 tasks in 1 wave.**

Executors: haiku×1, sonnet×2. No codex, no opus — this is a small surgical edit.

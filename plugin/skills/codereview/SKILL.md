---
name: codereview
description: "Use when the user wants a diff or PR reviewed — typed as /renmark:codereview or phrases like \"review this\", \"review my changes\", \"check this PR\", \"code review HEAD~3..HEAD\". Depth scales to the diff: a small/doc diff gets a quick in-context review, a larger one gets the full sandboxed review pass."
---

# codereview

## Overview

**Review depth is proportional to the diff.** Before choosing a review engine, the
skill classifies the range with `renmark.sizing.classify_diff(repo, base_ref)` →
`Tier ∈ {lite, standard, full}` (deterministic, zero-LLM; runs `git diff --stat`;
degrades to `standard` on any no-git / error). The classified tier picks the lane:

- **`lite` (doc/config-dominant or a very small code diff) → built-in cheap `/review`
  by DEFAULT.** This runs in-context (~10–25k tokens) and catches the obvious bugs
  plus cross-file / consistency issues. It is **never silently skipped** — the skill
  always states which review ran and always **offers a one-keystroke escalate to the
  full codex pass**.
- **`standard` / `full` → full codex review** (the heavy lane, below). Codex runs in
  `--sandbox read-only` mode, reads the diff, and emits a structured findings report.
  Opus orchestrates but never ingests the diff body — that's the whole point of
  routing this to codex.

No Sonnet or Opus passes for the heavy lane. Earlier designs included them; experience
showed that putting code into the conversation defeats the context-hygiene goal renmark
is built for. Codex is purpose-built for adversarial bug-finding and that's the most
valuable single lens — but it's overkill for a one-line doc tweak, hence the
proportional default.

The heavy lane's output: structured markdown at `.renmark/reviews/YYYY-MM-DD-<sha>.review.md`
with findings grouped by severity (Critical / Major / Minor / Nit). The cheap `/review`
lane reports its findings in-context (it does not write a `.review.md` artifact).

Recommended cadence: **after a full plan completes**, not after every task. `/renmark:orchestrate` offers a hand-off prompt at the end of a successful run.

## Argument parsing

- `$ARGUMENTS` may contain a git ref range AND/OR `--focus <mode>` AND/OR a
  tier-override flag (`--full` / `--skip`).
- Recognized focus modes: `optimize`, `standards`. Anything else (or absent) = default.
- Recognized tier-override flags (mutually exclusive; explicit > inferred):
  - `--full` → force the **full codex** review regardless of the classified tier
    (escalate a lite diff up to codex).
  - `--skip` → **explicitly skip** the review entirely. This is the only sanctioned
    way to run no review — the skill NEVER skips silently on its own. State that the
    review was skipped by explicit `--skip` and stop.
- Parse rule: strip the `--focus <mode>` pair AND any `--full` / `--skip` flag from
  `$ARGUMENTS`; the remaining text is the ref range (passed unchanged to Step 1).
- Unknown focus mode → print a one-line note (`unknown --focus <mode> — falling back
  to default`) and use the default prompt. Do not abort.
- If both `--full` and `--skip` are present → print a one-line note and treat as
  `--skip` (refusing to review is the safer of two contradictory explicit asks);
  the user can re-run with `--full` alone.

## When to Use

- "Review my changes" / "review this PR"
- After completing a feature, before merging
- After `/renmark:orchestrate` finishes — sanity check what agents wrote

**Do NOT use:**
- For debugging a runtime failure — use `/renmark:debug`
- For implementing fixes — review only; fixes go through orchestrate or direct edit

## How it runs (proportional: cheap `/review` or full codex)

The lane is chosen by the classified tier (see Steps → Determine scope) and any
tier-override flag:

- **`--skip`** → no review runs (explicit only). State it and stop.
- **`lite` tier and no `--full`** → run the built-in cheap **`/review`** skill
  in-context over the same range. Report findings inline, then offer the one-keystroke
  escalate to the full codex pass (see Hand off).
- **`standard` / `full` tier, OR `--full` on any tier** → run the full codex pass
  below.

**When Agency Mode is active:** codereview runs a full review before each milestone signoff, reports both merge-readiness and risk findings, and gates the owner signoff on review verdict. The review blocks premature "done" declarations until findings are addressed. See the Agency Mode contract at `${CLAUDE_PLUGIN_ROOT}/skills/_shared/agency-delivery.md` for gating rules and escalation conditions. When Agency Mode is off, existing codereview behavior is unchanged.

**Adversarial escalation (REQ-2 — highest-stakes diffs only).** For release-gating,
security-sensitive, or engine/state code, adversarial verification subagents MAY be
dispatched on `fable` (Agent tool, `model: "fable"`) to attempt to refute the review's
findings before they ship. Fable dispatch applies in projects with a declared
`top_tier: fable` (renmark.capabilities); undeclared projects run the same refutation
passes on opus. This is an escalation tier, never the default review path —
the codex read-only sandbox pass and the bounded severity-summary contract (Opus reads
only the summary, never the diff body) are unchanged.

> *Include the reasoning/output-discipline contract from
> `${CLAUDE_PLUGIN_ROOT}/skills/_shared/reasoning-contract.md` in every
> dispatched subagent prompt: multi-perspective decomposition → explicit
> assumptions/edge cases → synthesis; blocking vs deferrable; findings vs
> recommendations; evidence preserved; missing context stated, never guessed.*

For the full codex pass, the agent selects one of three prompt blocks below based on
the parsed focus, then pipes it to `codex exec --sandbox read-only -`.

```bash
codex exec --sandbox read-only -
```

### Prompt: default (spec-compliance + correctness + quality)

The skill pipes a prompt like:

```
You are reviewing the diff <range>. Emit TWO independently-scored verdicts.

━━ VERDICT 1 — Spec-compliance ━━
Goal: <one-paragraph task/plan intent from <plan_path> or provided inline>

Did the diff build the RIGHT thing?
  - compliant   — diff satisfies the goal; nothing missing, nothing extra
  - under-built — one or more requirements from the goal are absent or incomplete
  - over-built  — diff includes material scope beyond the stated goal

Emit exactly one of:
  Spec: compliant
  Spec: under-built — <one line: what is missing>
  Spec: over-built  — <one line: what is extra>

━━ VERDICT 2 — Code-quality ━━
Find: runtime bugs, logic errors, off-by-ones, race conditions, security issues
(injection, auth, data leaks), bad assumptions, edge cases the code doesn't handle.

For each finding:
  - file:line
  - severity: Critical | Major | Minor | Nit
  - one-sentence description
  - one-sentence fix suggestion

Top of quality section: summary counts per severity.

Present the two verdicts at the TOP of your report, clearly labelled, before
any per-finding details. Do not modify any files. Do not exit until the review
is complete.
```

**Passing spec intent to codex:** the orchestrator supplies the plan goal by
one of two methods (preference order):
1. `--plan <path>` flag → codex reads the goal paragraph from that plan file
   inside the sandbox (read-only; it only reads, does not modify).
2. Inline in the prompt as a `Goal:` paragraph when no plan file is available.

Codex reads the plan path in-sandbox; the Opus orchestrator sees only the
two verdict lines + counts in the bounded summary — never the plan body or
the diff body. Context hygiene is preserved.

### Prompt: optimize

```
You are reviewing the diff <range> with focus OPTIMIZE.

━━ VERDICT 1 — Spec-compliance (lite) ━━
Goal: <one-paragraph task/plan intent from <plan_path> or provided inline>

Quick scope check — did the diff build the RIGHT thing?
  Spec: compliant | under-built — <what's missing> | over-built — <what's extra>

━━ VERDICT 2 — Performance & idiom ━━
Focus on:
  - unnecessary allocations, copies, or work inside hot loops
  - asymptotic complexity surprises (accidental O(n²) over reasonable inputs)
  - repeated computation that could be cached or hoisted
  - blocking calls where async / batching would scale better
  - non-idiomatic constructs that have a clearer, faster language-native form
  - resource lifecycle issues (locks held too long, file handles, sockets)

Out of scope: correctness bugs, security, edge cases.
  If you spot a correctness bug while looking at perf, list it as ASIDE
  (severity: Major), but DO NOT exhaustively hunt for them.

For each finding:
  - file:line
  - severity: Critical | Major | Minor | Nit
  - one-sentence description (what's slow / non-idiomatic, and roughly why)
  - one-sentence fix suggestion

Present the two verdicts at the TOP of your report. Then: summary counts per
severity, plus a single bold line "Focus: optimize".
Do not modify any files. Do not exit until the review is complete.
```

### Prompt: standards

```
You are reviewing the diff <range> with focus STANDARDS.

━━ VERDICT 1 — Spec-compliance (lite) ━━
Goal: <one-paragraph task/plan intent from <plan_path> or provided inline>

Quick scope check — did the diff build the RIGHT thing?
  Spec: compliant | under-built — <what's missing> | over-built — <what's extra>

━━ VERDICT 2 — Code standards ━━
Skip whatever the project's own pre-commit/CI gates already enforce (check
for .pre-commit-config.yaml and CI config files — in renmark's own repo that
is tools/precommit.sh: ruff lint, ruff format, mypy strict, plugin lint,
pytest). Look only at conventions that exist in the codebase but are not
enforced by tooling.

Sources of truth:
  - Spot-check 3–5 other files in the same module/package for conventions:
    imports (relative vs absolute), error-handling shape (raise vs return
    None vs Result), logging style, naming, type annotation density,
    docstring presence and shape, where helpers go.
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

Present the two verdicts at the TOP of your report. Then: summary counts
per severity, plus a single bold line "Focus: standards".
Do not modify any files. Do not exit until the review is complete.
```

Codex writes its review to `.renmark/reviews/YYYY-MM-DD-<sha>.review.md` directly (or the skill captures stdout and writes it).

## Steps

**Step 0 — Context check.** Call `lifecycle.skill_preamble(repo, 'codereview')`. If it returns a non-None hint, surface as a one-line note.

**Lifecycle note:** Codereview advances the lifecycle stage when it runs against a verified feature. After the full codex pass writes its report, check whether the project has a lifecycle and the stage is `"verified"`:

```python
from renmark import lifecycle
from pathlib import Path
s = lifecycle.read_lifecycle(Path('.'))
if s and s.stage == "verified":
    lifecycle.write_lifecycle(Path('.'), stage="reviewed",
                              artifact_update=("review", report_path))
```

Ad-hoc reviews on arbitrary diffs (stage is not `"verified"`, or no lifecycle exists) skip this write — stage ownership stays with the pipeline, not with incidental reviews.

### 1. Determine scope & classify the tier

If the user gave a ref range (`HEAD~3..HEAD`, `main..feature`), use that. Otherwise default to `git diff --name-only HEAD` (working tree). Show a `git diff --stat <range>` summary and confirm with the user.

Then classify the diff to make the review **proportional** to its size/risk:

```python
from renmark.sizing import classify_diff
# Pass the ACTUAL review range. When the user gave a range (HEAD~3..HEAD,
# main..feature), hand it through as diff_range so the tier reflects what is
# actually being reviewed — not a base_ref..HEAD guess. With no range, the
# base_ref default applies.
tier = classify_diff(repo, base_ref, diff_range=review_range)  # 'lite' | 'standard' | 'full'
```

`classify_diff` is deterministic and zero-LLM: it runs `git diff --stat` under the
hood and degrades to `'standard'` (the safe middle) on no-git / error / an
**unparseable or unsafe range** — which escalates to the full review, the safe
direction. Resolve the final lane:

- `--skip` present → skipped (explicit). State it and stop — no engine runs.
- `--full` present → **full codex**, regardless of `tier`.
- else `tier == 'lite'` → cheap **`/review`** (in-context).
- else (`tier ∈ {standard, full}`) → **full codex**.

**State the diff tier and the chosen review BEFORE running anything**, e.g.
`Diff tier: lite — running cheap /review (escalate to codex with --full).` or
`Diff tier: standard — running full codex review.` Never start a review without
surfacing this line.

### 2. Run the chosen review

**Cheap lane (`lite`, no `--full`):** invoke the built-in **`/review`** skill over
the same range, in-context. Report its findings inline. Do not write a `.review.md`
artifact — proceed to Hand off, which always offers the escalate.

**Full lane (`standard`/`full`, or `--full`):** pipe the focus prompt to
`codex exec --sandbox read-only -`. If you want a log for troubleshooting, tee
codex's output to `.renmark/logs/codereview-<run_id>.log` yourself — there is no
implicit logging machinery; the log only exists if you explicitly write it.

### 3. Capture the review

**Full lane only:** codex output is parsed (or written through verbatim) and saved to
`.renmark/reviews/YYYY-MM-DD-<sha>.review.md`. The cheap `/review` lane reports
in-context and writes no artifact — there is no `<path>` to report for it.

### 4. Hand off

Tell the user — using ONLY the summary, never the diff body.

**Cheap-lane hand-off (ran `/review`):** state which review ran, emit a brief
spec-compliance note, and ALWAYS offer the escalate. Lead with:

> *"Diff tier: lite — ran cheap `/review` in-context.*
> *Spec: <compliant | under-built — … | over-built — …>*
> *Quality: <N critical, M major, K minor> findings.*
> *What's next?*
> *  1. [full] Escalate — re-run as the full codex pass (`/renmark:codereview --full <range>`)*
> *  2. [fix] Fix — kick off a new /renmark:plan built from the findings"*

The `[full]` escalate is mandatory on the cheap lane — never present the cheap result
as final without it.

**Full-lane hand-off (ran codex):** surface BOTH verdicts first, then the action menu:

> *"Review at `<path>` (focus: <mode>).*
> *Spec: <compliant | under-built — … | over-built — …>*
> *Quality: <N critical, M major, K minor> findings.*
> *What's next?*
> *  1. [o] Open — open the review file to read the full findings*
> *  2. [fix] Fix — kick off a new /renmark:plan built from the critical/spec findings"*

Omit the `(focus: <mode>)` parenthetical entirely when mode is default — preserves the existing terse output for the common case.

Then append the hand-off menu from `${CLAUDE_PLUGIN_ROOT}/skills/_shared/handoff-menu.md`, applying the rendering rules:

- **Omit `[c] Code review`** — we just ran it.
- **Show `[s] Smoke`** and `[qa] QA` (a finding worth re-verifying live often lives in the just-reviewed diff).
- **Show `[dq] Deep QA`** only if a passing `.qa.md` exists for the current sha.
- **Show `[d] Debug`** if ANY of these are true: (a) Critical quality findings exist, OR (b) the spec verdict is `under-built`, OR (c) the spec verdict is `over-built`. Major-only quality findings with a compliant spec are informational, not a debug trigger.
- **Show `[f] Finish`** unconditionally and `[n] Nothing` always.

Treat the `[o]`/`[fix]` actions plus the filtered gate options as ONE combined
menu. **Present it as an interactive `AskUserQuestion` choice when available**
(PRIMARY) — one selectable choice per option (`label` = action + code, e.g.
`Fix [fix]`, `Open [o]`, `Code review`… ). This combined menu usually exceeds
the picker's 4-option cap, so apply handoff-menu.md rule 6's overflow path:
surface the **4 highest-priority** as selectable choices (priority: `[fix]` on
critical findings → `[qa]` → `[f]` → `[o]`/`[s]`, always keep `[n] Nothing`) AND
print the **full combined numbered list** beneath as reference, so the overflow
options stay reachable by typed number/letter. **Fall back** to the numbered list
entirely when `AskUserQuestion` is unavailable / non-interactive / errors. Require
an explicit choice before doing anything.

Don't auto-fix. The human reads and decides.

## When to invoke

Recommended cadence (for context hygiene):

- **Auto-suggested by `/renmark:orchestrate`** after a successful plan run completes — one review for the whole feature, not one per task.
- **Before merge** when you're about to land work to main.
- **Ad-hoc** when you want a sanity check on a specific range.

Avoid: running codereview after every single task. That creates one review per file and floods the reviews directory.

## Reference

- Proportional classifier:
  `renmark.sizing.classify_diff(repo, base_ref='main', diff_range=None) -> Tier`
  where `Tier ∈ {lite, standard, full}` — deterministic, zero-LLM. Pass the
  explicit review range as `diff_range` (e.g. `HEAD~3..HEAD`, `main..feature`)
  so the tier matches what's reviewed; with no range the `base_ref..HEAD`
  default applies. Degrades to `standard` on no-git / error / unsafe-or-
  unparseable range (which escalates to the full review — the safe direction).
  Single source of truth for which lane runs.
- Codex review syntax: `codex review --help`
- Built-in cheap **`/review`** slash command — the lite lane's in-context engine
  (also good for inspiration on prompt shape).
- Tier-override flags: `--full` (force codex), `--skip` (explicit skip) — see
  Argument parsing. These always win over the inferred tier.
- Focus modes: see Argument parsing above. Adding a new focus = adding a new `### Prompt: <name>` block; nothing else to change.

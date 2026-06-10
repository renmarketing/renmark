---
name: usage
description: Use when the user wants observed local usage status — typed as /renmark:usage, "show usage", "rolling 5h", "weekly limits", "paused runs". Reports current pause state, local limits, and rolling 5-hour window from Claude Code runtime. Zero LLM calls.
---

# usage

## Overview

Zero-LLM status skill. Displays the bounded local usage view — current pause
state, rolling 5-hour window, and any locally-observable limits — by delegating
all aggregation to the Python layer (`renmark.usage.render_usage_md`). The skill
itself never reads raw event logs.

## Step 0 — context check

```python
hint = renmark.lifecycle.skill_preamble(repo, 'usage')
```

If `hint` is non-empty, surface it as a one-line note before proceeding.
(Example hint: domain-transition warning or context-budget advisory.)

## Main — display bounded usage output

Run the usage reporter:

```bash
renmark-execute --usage
```

Show the output verbatim to the user. Do not summarise, trim, or interpret it —
the Python layer already bounds the view.

### Hard rule — never read raw event logs into context

**NEVER** read `.renmark/analytics/*.jsonl` or `.renmark/state/usage.jsonl`
into the conversation context. The Python layer (`renmark.usage.render_usage_md`)
aggregates those files; the skill only displays the bounded output it produces.
Violating this rule defeats the entire purpose of the bounded-view design and can
exhaust context on large event logs.

### Disclaimer string

The output ALWAYS carries the exact string:

> Observed local usage only. Provider-side account limits may differ.

Provider-reported limits appear in the output **only** when a reliable
provider-side source exposed them (e.g. a rate-limit header returned by the
API). Do not infer, estimate, or synthesise provider limits from local data.

### Paused runs

If the output indicates one or more paused runs, surface the suggested resume
time shown in the output and direct the user to `/renmark:resume` to pick up
where orchestration left off.

## Do not

- Make any LLM calls. This skill is pure display — zero inference.
- Read `.renmark/analytics/*.jsonl` or `.renmark/state/usage.jsonl` inline.
- Infer, estimate, or synthesise provider account limits beyond what the Python
  layer explicitly reports.
- Modify any usage, analytics, or state files. Read-only operation.

## See also

- `/renmark:analytics` — per-feature build-health summary (shipped/blocked counts, loop success rate, token/cost by feature)
- `/renmark:roadmap` — per-task status table (shipped/retried/in-progress) synthesized from git log + usage.jsonl

## What's next

*End by calling `renmark.lifecycle.next_steps(repo, "usage")` and render per
`${CLAUDE_PLUGIN_ROOT}/skills/_shared/next-steps.md` (class 3 — resume-pipeline
+ 1–2 local actions). The in-flight feature's next command is `(Recommended)`;
add the skill's local follow-ups (e.g. re-run `/renmark:usage` to refresh the
view, or run `/renmark:resume` if paused runs were reported). Render via
`AskUserQuestion` (handoff-menu.md rules 6–9); require an explicit choice.*

---

*Rule-affecting note for maintainers: the hard rule against reading raw event
logs inline and the bounded-output contract are governance requirements — mirror
any change to those rules in `CLAUDE.md` and `AGENTS.md` in the same commit.*

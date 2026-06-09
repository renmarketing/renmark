---
name: analytics
description: Use when you need a bounded project build-health summary — typed as /renmark:analytics. Prints shipped/blocked features, loop success rate, token/cost by feature. Zero LLM calls.
---

# analytics

## Overview

Project build-health reporter. Aggregates cross-feature metrics into a bounded
summary — no LLM calls, no raw log ingestion. Sources:

- `.renmark/state/pipeline.json` — wave/task status per feature
- `.renmark/state/usage.jsonl` — token spend per LLM call
- `.renmark/memory/features.md` — declared features
- `.renmark/analytics/*.jsonl` — loop telemetry (Python aggregates; never loaded into context)

Output: shipped vs. blocked feature counts, loop success rate, token/cost breakdown
by feature. Also writes `.renmark/memory/analytics.md` as a committed snapshot.

## Step 0 — context check

```python
hint = renmark.lifecycle.skill_preamble(repo, 'analytics')
```

Surface `hint` to the user if non-empty (e.g. cross-domain transition warning,
context-budget alert). Then proceed.

## Main — run and display

```bash
renmark-execute --analytics
```

`renmark-execute --analytics` aggregates all telemetry sources in Python and
prints a bounded build-health summary. Display that summary to the user.

The Python aggregator also writes the snapshot to `.renmark/memory/analytics.md`
so it can be committed alongside the rest of the project memory.

## Hard rules

- **NEVER dump raw logs.** Do NOT read `.renmark/analytics/*.jsonl` files into
  the conversation. Python aggregates; this skill displays only the bounded summary
  returned by `renmark-execute --analytics`.
- **Zero LLM calls.** This skill is purely deterministic aggregation and
  display. No inference, no subagents, no web calls.
- **Read-only.** Do not modify `features.md`, `usage.jsonl`, pipeline state, or
  git history. Only `.renmark/memory/analytics.md` is written (by the Python
  aggregator, not by this skill directly).

## What's next

*End by calling `renmark.lifecycle.next_steps(repo, "analytics")` and render per
`${CLAUDE_PLUGIN_ROOT}/skills/_shared/next-steps.md` (class 3 — resume-pipeline
+ 1–2 local actions). The in-flight feature's next command is `(Recommended)`;
add the skill's local follow-ups (e.g. re-run analytics after the next orchestrate,
or open `.renmark/memory/analytics.md` to review the snapshot). Render via
`AskUserQuestion` (handoff-menu.md rules 6–9); require an explicit choice.*

---

*Rule-affecting note for maintainers: the hard rules above (no raw-log ingestion,
zero LLM calls, read-only) are invariants — mirror any change to them in
`CLAUDE.md` and `AGENTS.md` in the same commit.*

---
name: analytics
description: "Use when the user wants a project build-health summary — typed as /renmark:analytics or \"build health\", \"feature metrics\", \"loop success rate\", \"token cost by feature\"."
disable-model-invocation: false
---

# analytics

## Overview

Project build-health reporter. Aggregates cross-feature metrics into a bounded
summary — no LLM calls, no raw log ingestion. Sources:

- `.renmark/analytics/*.jsonl` — the 4 analytics ledgers: feature runs, loop
  iterations, verify results, and cost events (Python aggregates; never loaded
  into context)
- `.renmark/state/usage.jsonl` — token spend per LLM call

Output: shipped vs. blocked feature counts, loop success rate, token/cost breakdown
by feature. The Python aggregator (`aggregate()`) WRITES `.renmark/analytics/summary.json`
as a machine-readable snapshot, and also writes `.renmark/memory/analytics.md` as a
committed human-readable snapshot.

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
- **Read-only (except managed snapshots).** Do not modify `usage.jsonl`, pipeline
  state, or git history. Only `.renmark/analytics/summary.json` and
  `.renmark/memory/analytics.md` are written (by the Python aggregator, not by
  this skill directly).

## See also

- `/renmark:usage` — rolling 5-hour window, pause state, and local limits
- `/renmark:roadmap` — per-task status table (shipped/retried/in-progress) synthesized from git log + usage.jsonl

## What's next

*End by calling `renmark.lifecycle.next_steps(repo, "analytics")` and render per
`${CLAUDE_PLUGIN_ROOT}/skills/.shared/next-steps.md` (class 3 — resume-pipeline
+ 1–2 local actions). The in-flight feature's next command is `(Recommended)`;
add the skill's local follow-ups (e.g. re-run analytics after the next orchestrate,
or open `.renmark/memory/analytics.md` to review the snapshot). Render via
`AskUserQuestion` (handoff-menu.md rules 6–9); require an explicit choice.*

---

*Rule-affecting note for maintainers: the hard rules above (no raw-log ingestion,
zero LLM calls, read-only) are invariants — mirror any change to them in
`CLAUDE.md` and `AGENTS.md` in the same commit.*

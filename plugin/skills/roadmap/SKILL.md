---
name: roadmap
description: Use when the user wants a status report on what renmark has built in this project — typed as /renmark:roadmap, "show the roadmap", "what's been built", "token usage report". Prints a table of task | llm | status | tokens | $ | commit, synthesized from features.md, usage.jsonl, and git log. Zero LLM calls.
---

# roadmap

## Overview

Project-level status reporter. Pulls from three sources to build a per-task table with totals:

- `.renmark/memory/features.md` — declared features
- `.renmark/state/usage.jsonl` — token spend per LLM call
- `git log` — task-N commits that have landed

Output columns: **task | llm | status | tokens | $ | commit** + totals.

## When invoked

```bash
renmark-execute --roadmap
```

(or call `renmark.roadmap.build_rows(repo)` + `render_table(rows)` from inside this skill).

Show the rendered table to the user. Also write the current snapshot to `.renmark/memory/roadmap.md` so it's committed alongside the rest of the docs.

## Statuses

| Status | Meaning |
|---|---|
| `shipped` | a `[nim] task N:` (or `[manual] task N:`) commit exists in git |
| `in-progress` | usage.jsonl has an entry for the task but no matching commit |
| `retried` | multiple usage entries for the same task without a commit (likely escalated) |
| `planned` | listed in features.md "Planned" but no usage yet |

## When to use

- "Show me the roadmap"
- "How much have we spent?"
- "What's the status?"
- After completing a plan run, to summarize what landed

## Sample output

```
| task   | llm                            | status      | tokens | $       | commit  |
|--------|--------------------------------|-------------|-------:|--------:|---------|
| task 1 | llama-3.2-3b-instruct          | shipped     |    191 | free    | `e373204` |
| task 2 | mistral-large-3-675b-instruct  | shipped     |    981 | free    | `45227a1` |
| task 3 | llama-3.2-3b-instruct          | shipped     |    304 | free    | `611391f` |
| task 4 | codex                          | retried     | 148321 | $7.416  | `—`     |
| task 5 | llama-3.2-3b-instruct          | shipped     |    362 | free    | `bda857a` |
| task 6 | llama-3.2-3b-instruct          | shipped     |   1320 | free    | `f7720b2` |

Totals: 6 tasks · 151,479 tokens · $7.416
By status: retried=1, shipped=5
```

## Do not

- Make any LLM calls. This is pure aggregation.
- Modify `features.md`, `usage.jsonl`, or git history. Read-only synthesis.

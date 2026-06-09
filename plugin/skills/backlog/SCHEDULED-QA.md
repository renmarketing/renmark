# Scheduled QA / Deep-QA Lane — Design Note (NOT IMPLEMENTED)

> **Status: DESIGN-ONLY.** This is a forward-looking reference for the future
> scheduled QA lane per **REQ-14**. It is intentionally *not* a `SKILL.md` and
> ships **no runtime** in this MVP. Nothing here runs today — the document
> exists so the integration seam is obvious when the lane is built.

## Purpose

renmark separates work into **four lanes**:

1. Foreground feature — human-driven `/renmark:feature` pipeline.
2. Backlog intake — the approval buffer where items wait for human review.
3. **Scheduled QA** — the **read-only proposer** lane (this doc, REQ-14).
4. Execution — bounded, human-gated Loop Mode.

Scheduled QA is the third lane and the **upstream** of the backlog intake lane:
a periodically-triggered, **read-only** agent that inspects the project and
*proposes* work. It never does the work. Everything it surfaces lands in the
backlog as an item with `status="needs review"`, so a human still owns the
decision to act. It feeds the approval buffer; it is not the buffer, and it is
not an executor.

## MAY (the proposer's full authority)

- Inspect the project (read source, configs, git history, prior artifacts).
- Run **read-only** checks: tests, linters, type checks, `/renmark:verify`
  smoke / `--qa` / `--deep-qa` flows.
- Research issues, regressions, flaky tests, dependency drift.
- Write QA reports into `.renmark/reviews/` or `.renmark/research/`.
- **Propose** backlog items — created with `status="needs review"` only.

## MUST NOT (hard boundaries, per REQ-14)

- Edit product code.
- Commit, merge, or release.
- Edit `PRD.md`.
- Escalate the iteration / token budget.
- Auto-execute backlog items, or trigger Loop Mode.

Autonomous scheduled **execution** is explicitly **out of scope** and remains
*Deferred* in the PRD. This lane proposes; it never runs the fix.

## Clean integration seam

A future scheduler enqueues a proposal through the existing backlog API —
**without touching product code**. After writing its report, it calls:

```python
from renmark.backlog import write_item, BacklogItem

write_item(repo, BacklogItem(
    id=next_id(repo),
    title="Flaky test: tests/test_loop.py::test_resume",
    status="needs review",                      # ALWAYS — the approval buffer
    source="qa",                                # marks the proposer lane
    evidence_path=".renmark/reviews/2026-06-09-qa.review.md",
    risk="medium",
    summary="...",
    recommended_action="...",
))
```

The seam is deliberately narrow: the scheduler's *only* mutation is a single
`write_item` call landing a `needs review` / `source="qa"` item with an
`evidence_path` pointing at its report. No other state is written, no branch is
created, no code is changed. The MVP `backlog.py` surface already supports this
exactly — the lane is "just add a scheduler that calls it."

## Parallelism

Scheduled QA is **read-only**, so any number of QA passes MAY run concurrently
and alongside other work. The only hard constraint is the execution lane: at
most **one code-writing loop may run per working tree** at a time. QA never
writes code, so it is exempt from that lock.

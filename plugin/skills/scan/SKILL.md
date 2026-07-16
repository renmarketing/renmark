---
name: scan
description: "Use to run the read-only QA proposer lane — typed as /renmark:scan (--propose to land backlog items, --emit-cron for the schedule command). Never edits code, commits, or merges."
disable-model-invocation: false
---

# scan

## Overview

`/renmark:scan` is the **read-only scheduled QA proposer lane** (REQ-14). It is
the **third of renmark's four lanes** and the direct upstream of the backlog
intake buffer:

1. Foreground feature — human-driven `/renmark:feature` pipeline.
2. Backlog intake — the approval buffer where items wait for human review.
3. **Scheduled QA (this lane)** — read-only proposer, surfaces findings only.
4. Execution — bounded, human-gated Loop Mode.

Scan inspects the project, runs read-only checks, writes a bounded report, and
optionally proposes backlog items. It **never acts on findings** — all proposed
items land with `status="needs review"` so a human owns every decision to act.
Design notes and the clean integration seam live in
`plugin/skills/backlog/SCHEDULED-QA.md`.

## When to Use

- On a cron or external trigger, to surface regressions between human-driven
  sessions without touching product code.
- Manually, before a release, to get a QA snapshot without running the full
  audit pipeline.
- When you want `source=qa` backlog items created automatically from verifier
  findings, deduplicated against prior proposals.

## Steps

**Step 0 — Context check.** Call `lifecycle.skill_preamble(repo, 'scan')`. Scan
is `audit` domain; surface the returned hint if non-None (a cross-domain
transition into auditing is worth a `/clear` note).

### Mode 1 — Scan only (default)

```bash
renmark-execute --scan
```

Runs read-only checks (audit passes + shell verifiers). Writes a bounded report
to `.renmark/reviews/<date>-scan.review.md`. Prints a ≤5-line summary verbatim —
do not paraphrase or expand (**the format is the contract**). Writes **zero**
backlog items. Exit 0 = clean, 1 = findings.

### Mode 2 — Scan + propose (`--propose`)

```bash
renmark-execute --scan --propose
```

Runs the same read-only checks as Mode 1, then deduplicates findings against
`.renmark/state/proposals.json` (key: `{check}:{rule_id}:{target}`). For each
**new** finding only, calls:

```python
write_item(repo, BacklogItem(
    source="qa",
    status="needs review",   # always — human reviews before action
    evidence_path=".renmark/reviews/<date>-scan.review.md",
    ...
))
```

Existing proposals are silently skipped. The ≤5-line summary reports the counts
(found / new / skipped). The session reads only the summary line; **never** the
findings body.

### Mode 3 — Emit cron command (`--emit-cron`)

```bash
renmark-execute --scan --emit-cron
```

Prints the **direct** external trigger command for scheduling:

```bash
renmark-execute --scan --propose
```

This command runs **entirely inside the Python binary** — no `claude -p`, no
LLM call, no Bash tool invocation, no token spend. It is safe to drop directly
into `cron`, Windows Task Scheduler, a CI step, or any external scheduler.

**Why this is the right trigger:** The scan engine is pure Python. Its write
paths are: the review report (`.renmark/reviews/`), the dedup ledger
(`.renmark/state/proposals.json`), the backlog reservation file under
`.renmark/state/` (next_id allocation and rollback on failure), and `write_item`
for backlog proposals. It has no code path that commits, merges, pushes, or
edits product files — that structural absence is real and permanent.

**Important: scan is NOT a sandbox.** The verifiers it runs (pytest, ruff,
mypy) execute the **project's own code**. Side effects from the project's test
suite — temporary files, network calls in tests, database fixtures — apply here
too. Schedule and trust scan at the same level as running your test suite
directly, not as an isolated read-only probe.

**Scheduling is EXTERNAL to renmark (Option 1).** Renmark never daemonizes,
registers a cron, or owns the schedule — the printed command is the handoff.
Pass it to `cron`, a CI step, or any scheduler the project already uses.

#### Optional: PreToolUse Bash-denylist hook (defense-in-depth)

`--emit-cron` also prints a sample PreToolUse Bash-denylist hook that blocks
write/commit shell verbs. This hook is **optional and best-effort**. It is
relevant **only** when a user chooses to trigger scan via
`claude -p "/renmark:scan --propose"` rather than via the direct binary. When
using the direct binary (the recommended path above), the hook has no effect
and need not be installed. The hook is defense-in-depth; it is NOT the
read-only guarantee.

## Hard Read-Only Contract (REQ-14)

**MAY:**

- Inspect source, configs, git history, prior artifacts.
- Run read-only checks: tests, linters, type checks, verifier smoke / `--qa` /
  `--deep-qa` flows.
- Write reports to `.renmark/reviews/` and proposals to `.renmark/state/`.
- Propose backlog items with `source="qa"`, `status="needs review"`.

**MUST NOT:**

- Edit product code.
- Commit, merge, or release.
- Edit `PRD.md`.
- Escalate the iteration / token budget.
- Auto-execute backlog items or trigger Loop Mode.

Autonomous scheduled execution is explicitly out of scope and remains *Deferred*
in the PRD. This lane proposes; it never runs the fix.

## Bounded Output (G11)

The orchestrator / calling session reads **only** the ≤5-line summary. The full
findings body stays inside the artifact. Passing the body into the session is a
context hygiene violation — route diagnostics to `/renmark:debug` instead.

## What's Next

After a `--propose` run, triage the proposed items with `/renmark:backlog`. That
skill surfaces the `needs review` queue and lets you approve, reject, or defer
each item before any execution occurs.

scan is an **aux / terminal skill** (class 3 in
`${CLAUDE_PLUGIN_ROOT}/skills/.shared/next-steps.md`). It reports and proposes;
it never advances the pipeline.

> *End by calling `renmark.lifecycle.next_steps(repo, "scan")` and render per
> `${CLAUDE_PLUGIN_ROOT}/skills/.shared/next-steps.md` (class 3 — resume-pipeline
> + 1–2 local actions). The in-flight feature's next command is `(Recommended)`;
> add the skill's local follow-ups (e.g. `/renmark:backlog` to triage proposed
> items). Render via `AskUserQuestion`
> (`${CLAUDE_PLUGIN_ROOT}/skills/.shared/handoff-menu.md` rules 6–9); require an
> explicit choice.*

## Maintainer Note

**Read-only** and **external-scheduling** are invariants for this lane, not
implementation choices. Any change that grants scan write-code, commit, or
schedule-registration capability violates REQ-14. Mirror all contract changes in
`CLAUDE.md` and `AGENTS.md` in the same commit.

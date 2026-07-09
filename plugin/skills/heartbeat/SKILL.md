---
name: heartbeat
description: "Use to monitor for usage-limit recovery — typed as /renmark:heartbeat or run renmark-execute --heartbeat. Checks when a paused run can resume; notifies when the limit clears. Zero LLM calls. Use --emit-cron to set up automated polling."
disable-model-invocation: true
---

# heartbeat

## Overview

`/renmark:heartbeat` is the **proactive workflow scheduler**. It monitors for
stalls and blockers across 5 categories: usage-limit pauses, stuck feature
lifecycle stages (>4h), stalled pipeline waves (>2h), blocked backlog items
(>48h), and loops awaiting approval. Zero LLM calls; operates entirely in Python
on local state.

## When to Use

- After a run pauses due to a usage limit
- Periodically (via `--emit-cron`), to catch stuck workflows before they block
  progress
- To check backlog/pipeline health without entering Claude Code

## Steps

### Mode 1 — Check status (default)

```bash
renmark-execute --heartbeat
```

Reads all `.renmark/state/` sources. If everything is moving normally, outputs:
`HEARTBEAT_OK`. If anything is stuck or needs attention, outputs a summary with
the suggested next command for each item (e.g., resume paused feature, advance
stuck lifecycle stage, unblock backlog item, approve awaiting loop).

Exit 0 always (this is a status check, not a failure condition).

### Mode 2 — Emit cron command (`--emit-cron`)

```bash
renmark-execute --heartbeat --emit-cron
```

Prints the direct external trigger for scheduling:

```bash
renmark-execute --heartbeat --notify
```

This command runs entirely inside the Python binary — no LLM, no tokens. Safe to
drop into `cron`, Windows Task Scheduler, or any external scheduler.

### Mode 3 — Auto-resume (`--auto-resume`)

```bash
renmark-execute --heartbeat --auto-resume
```

Polls until the usage limit clears, then automatically re-invokes the paused
command (e.g. `/renmark:loop --resume` or the original feature command). Useful
when you want to walk away and let the build finish unattended. Exit 0 on
success, non-zero if the paused state is lost or corrupted.

## Use Cases

- **Set-and-forget:** After hitting a usage limit, run
  `renmark-execute --heartbeat --emit-cron`, add the output to `cron` or Task
  Scheduler, and receive a notification when the limit clears.
- **Manual polling:** While waiting for a limit to expire, run
  `renmark-execute --heartbeat` in a separate terminal to check time remaining.
- **Unattended completion:** When you have a long-running loop, schedule
  `renmark-execute --heartbeat --auto-resume` and it will pick up where you left
  off once the limit window passes.

## Governance

Heartbeat is **read-only and non-destructive**. It reads `.renmark/state/` only,
never modifies workflow state, never commits, never advances stages. When
`--auto-resume` is used, it delegates back to the paused command's own recovery
logic (the actual re-invocation is external to heartbeat).

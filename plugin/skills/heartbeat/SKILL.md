---
name: heartbeat
description: "Use to monitor for usage-limit recovery — typed as /renmark:heartbeat or run renmark-execute --heartbeat. Checks when a paused run can resume; notifies when the limit clears. Zero LLM calls. Use --emit-cron to set up automated polling."
disable-model-invocation: true
---

# heartbeat

## Overview

`/renmark:heartbeat` is the **usage-limit recovery monitor**. When a
`/renmark:feature`, `/renmark:loop`, or other long-running workflow pauses
because of a local usage limit, heartbeat watches for the limit to clear and
notifies you when it's safe to resume. Zero LLM calls; operates entirely in
Python on local state.

## When to Use

- After a run pauses due to a usage limit (heartbeat detects this via
  `.renmark/state/PAUSED`)
- As a periodic scheduled check (via `--emit-cron`), to auto-notify when the
  limit window closes
- To manually poll recovery status without entering Claude Code

## Steps

### Mode 1 — Check status (default)

```bash
renmark-execute --heartbeat
```

Reads `.renmark/state/PAUSED`. If no usage-limit pause is active, outputs:
`HEARTBEAT_OK`. If a pause IS active, outputs:

```
⏸  Paused: <feature> (limit clears at <resume_after>)
   Iteration: <N>/<max>  |  Time until resume: <human-readable duration>
   Ready to resume: /renmark:loop --resume  (or re-invoke the paused command)
```

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

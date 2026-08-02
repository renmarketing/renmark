# Usage Instrumentation — Reference (single source of truth)

Companion to `task-tracking.md` — same two-layer split, applied to recording
**measured token/duration usage** instead of task status. Read
`task-tracking.md` first for the full live-tool-vs-Python-mirror reasoning;
this file does not restate it.

## Why

Claude Code's own `Agent` tool completion already returns a real, measured
usage block per subagent dispatch (`subagent_tokens`, `tool_uses`,
`duration_ms` — visible in every `<task-notification>` a live session
receives). No Python module can intercept that block on the agent's behalf —
only the live agent that just made the `Agent` tool call can see it. This is
the exact same reasoning `task-tracking.md` already documents for why native
`TaskCreate`/`TaskUpdate` must be a live in-transcript tool call, not a Python
side effect — the same two-layer split applies here.

## Layer 1 — primary, live host

Whenever an interactive session dispatches an `Agent` tool call as part of
running a renmark pipeline (`orchestrate`, `feature`, `debug`, `rethink`,
etc.), it MUST, immediately after receiving the result, call

```
renmark.analytics.record_task_run(
    repo, ts=..., task_id=..., executor=..., model=..., status=...,
    duration_s=<duration_ms/1000>, tokens_in=<subagent_tokens>,
    total_tokens=<subagent_tokens>, measured=True, ...
)
```

using the REAL numbers from the `<usage>` block it just received — not an
estimate, not the plan's `est_tokens`. This is a skill instruction to the
live agent, satisfied only by a real Python call using real numbers seen in
the transcript.

## Layer 2 — headless fallback

The `renmark-execute` CLI's Codex/subprocess dispatch path (`execute_plan` in
`renmark/cli/_engine.py`) has no live Agent-tool result to read usage from,
and the Codex CLI itself does not currently surface token usage (see the
`token_count` comment at `renmark/cli/commands.py:452` — "codex CLI doesn't
surface this; orchestrator may estimate"). That path continues to record
`measured=False` — this is honest, not a bug, and is explicitly out of scope
for this contract (mirrors R-0.3's documented "explicitly out of scope, not
an oversight" precedent for partial dispatch-path coverage).

## What NOT to do

Never estimate a token figure and record it with `measured=True`. Never read
the `.output` transcript file to extract usage — only the `<usage>` block
already surfaced inline in the task-notification/tool-result is a real
measured number.

## Dispatch reference (for skill authors)

When citing this contract in a SKILL.md, write:

> *Immediately after an `Agent` dispatch returns, call
> `renmark.analytics.record_task_run(..., measured=True)` with the real
> `subagent_tokens`/`duration_ms` from the usage block you just received —
> never an estimate. Full contract:
> `${CLAUDE_PLUGIN_ROOT}/skills/.shared/usage-instrumentation.md`. The
> headless `renmark-execute` Codex path records `measured=False` — out of
> scope here, not a bug.*

Do not paste the layer explanation into the calling SKILL.md — cite this
file, the same way skills cite `task-tracking.md` rather than restating it.

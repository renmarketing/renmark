---
name: orchestrate
description: Use when the user wants to execute an existing renmark plan — typed as /renmark:orchestrate or phrases like "deploy this plan", "execute the plan", "run the orchestrator", "build it". Reads the plan, dispatches each task to its assigned executor (nim, codex, opus, sonnet), runs verifiers, commits per task, and writes summary state to .renmark/state/. Skill loads only summary lines into Opus context — generated code bodies stay in subprocesses or subagents.
---

# orchestrate

## Overview

Dispatches plan tasks in waves. Within a `parallel_group`, tasks run concurrently — nim/codex tasks via one batched Bash call to `renmark-execute`; opus/sonnet tasks via parallel Agent tool calls in a single Claude turn. After each wave, the skill commits passing tasks serially in task-index order.

**Token-isolation contract:** the skill NEVER reads generated code into the conversation. Only per-task summaries (PASS/FAIL/skip + sha + token count). On escalation, the skill reads `.renmark/state/escalations/task-N/` artifacts.

## When to Use

- User has a `.renmark/plans/*.plan.md` file ready and wants it executed
- After `/renmark:plan` completes
- To `--resume` a paused run

**Do NOT use:**
- Without a plan file → `/renmark:plan` first
- For brainstorming or design — that's `/renmark:brainstorm`

## Status note (v0.0.1)

Phase 1 dispatch (parallel waves, claude_agent provider, memory updates) is being implemented. v0.0.1 ships the baseline CLI (`renmark-execute`) that handles single-task plans through nim and codex executors. The opus/sonnet routes and parallel waves land in v0.0.2.

If your plan has `executor: opus` or `executor: sonnet` tasks today, do them manually after running orchestrate on the nim/codex tasks. The skill will note which tasks are pending Claude executors.

## Steps

### 1. Discover plan

If the user gave a path, use it. Otherwise:

```bash
ls -1t .renmark/plans/*.plan.md 2>/dev/null | head -1
```

Confirm the path with the user before continuing.

### 2. Pre-flight (free)

```bash
renmark-execute --dry-run <plan>
```

Show the task list and cost preview. Ask: *"Proceed? [y/N]"*

### 3. Run

```bash
renmark-execute <plan>
```

Stream summary lines as they arrive. Do NOT cat generated files.

### 4. Interpret outcome

| Exit | Meaning | Action |
|---|---|---|
| 0 | All tasks passed | Report totals; tag end |
| 2 | Plan parse error | Route to `/renmark:plan` |
| 3 | Bad NIM API key | Tell user to set `NVIDIA_NIM_API_KEY` |
| 4 | Quota exhausted | Wait / upgrade tier |
| 5 | NIM unavailable | Retry later |
| 10 | Paused | Read `.renmark/state/PAUSED` + escalation artifacts |

### 5. On escalation

Read `.renmark/state/escalations/task-N/{metadata.json,prompt.txt,response.txt,verifier.log}`. Propose 2-3 options: fix manually + resume, switch executor in the plan + resume, skip the task.

### 6. Update memory

After the run, append to `.renmark/memory/learnings.md` and `routing.md`:
- Tasks that succeeded on which executor
- Tasks that failed and on what model
- Cost surprises

## Reference

- CLI flags: `renmark-execute --help`
- Plan format: `PLAN.md` § "Plan file format"
- State dir: `.renmark/state/`

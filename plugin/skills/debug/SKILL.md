---
name: debug
description: Use when the user reports a bug or unexpected behavior — typed as /renmark:debug or phrases like "debug this", "why is X failing", "investigate the error", "find the root cause". Systematic reproduce → hypothesize → investigate → fix loop. Routes cheap investigation (greps, line counts) to NIM, multi-file traces to Codex, and cross-system reasoning to Opus. State preserved in .renmark/debug/<session-id>/ so the session survives /clear.
---

# debug

## Overview

Modeled after `superpowers:systematic-debugging` + `context-mode:diagnose`. The loop:

1. **Reproduce** — get a minimal repro from the user; verify you can trigger the bug
2. **Hypothesize** — generate 3–5 ranked hypotheses for what's going wrong
3. **Investigate** — route each inspection to the cheapest model that can do it
4. **Fix** — Opus drafts the fix; route emission to NIM/Codex if it's a clean single-file change, else Opus edits directly
5. **Verify** — the repro fails (bug gone), regression test added

State lives in `.renmark/debug/<session-id>/`. A debug session survives `/clear`.

## When to Use

- "Why does X return 500?"
- "This test was passing yesterday and now it's not"
- "Find the root cause of <error>"
- Any reproducible failure

**Do NOT use:**
- For new features — use `/renmark:brainstorm` → `/renmark:plan` → `/renmark:orchestrate`
- For code review — use `/renmark:codereview`

## Status note (v0.0.1)

Phase 3 work. The skill ships as a documented workflow; the per-step model routing (NIM for greps, Codex for traces) requires Phase 1 dispatch to be online first. For v0.0.1 you can follow the loop manually with Opus driving — the structure below is the playbook.

## The loop

### 1. Capture the bug

Open a new session dir: `.renmark/debug/$(date +%Y%m%d-%H%M%S)/`. Write `session.md` with:
- Symptom (what the user reported)
- Expected vs. actual
- Where it happens (file, function, command)
- Repro steps

### 2. Reproduce

Run the failing command yourself. If it doesn't fail, ask the user for the exact command and environment.

### 3. Hypothesize

List 3–5 plausible causes, ranked by likelihood. Write to `session.md`.

### 4. Investigate

For each hypothesis, plan an inspection:

| Inspection type | Suggested model |
|---|---|
| Grep for a symbol, count lines, check file existence | NIM (cheap, fast) |
| Trace a function across multiple files, find usages | Codex (agentic, reads context) |
| Reason about race conditions, async flow, architecture | Opus |

Run the inspection. Update `session.md` with findings — eliminate or confirm hypotheses.

### 5. Root cause

Once you've isolated WHY the bug exists (not just what fixes it), write the root-cause statement in `session.md`.

### 6. Fix

Draft the fix. If it's a clean single-file change, write a 1-task renmark plan and run `/renmark:orchestrate` on it. Otherwise Opus edits directly.

### 7. Verify

Run the original repro. It should now fail (i.e., the bug is gone). Add a regression test that would have caught this earlier.

### 8. Close the session

Append to `.renmark/memory/learnings.md`:
- Bug pattern (e.g., "MIME lookup with `.split('.')[-1]` doesn't match dict keys that include the dot")
- Fix pattern (e.g., "use `os.path.splitext(path)[1].lower()`")

## Iron Law

**No fixes without a confirmed root cause.** Don't patch symptoms. If you can't articulate the root cause in one sentence, keep investigating.

## Reference

- `superpowers:systematic-debugging` SKILL.md for the broader pattern
- `context-mode:diagnose` for the reproduce-minimize-hypothesize-instrument-fix discipline

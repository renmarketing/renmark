---
name: debug
description: Use for the Debug pipeline when something is broken and you need to fix or change it — typed as /renmark:debug or plain dev requests like "debug this", "fix this bug", "fix X", "why is X failing", "investigate the error", "find the root cause", "make X work", "change the broken behavior". Runs reproduce → root cause → fix → regression test → verify, keeping scope tight (no feature expansion). Routes cheap investigation (greps, line counts) to Haiku/Bash, multi-file traces to Codex, and cross-system reasoning to Opus. State preserved in .renmark/debug/<session-id>/ so the session survives /clear.
---

# debug

## Overview

The **Debug pipeline** — fix what's broken without expanding scope. Modeled after `superpowers:systematic-debugging` + `context-mode:diagnose`. The loop:

1. **Reproduce** — get a minimal repro from the user; verify you can trigger the bug
2. **Hypothesize** — generate 3–5 ranked hypotheses for what's going wrong
3. **Investigate** — route each inspection to the cheapest model that can do it
4. **Fix** — Opus drafts the fix; route emission to Codex if it's a clean single-file change, else Opus edits directly
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

## Module support (v0.1.5+)

The `renmark.debug` Python module exposes the session helpers the skill drives:

- `debug.new_session(repo, symptom)` — creates `.renmark/debug/<id>/session.md`
- `debug.add_hypothesis(session, idx, title, likely)` — appends to Hypotheses section
- `debug.log_investigation(session, *, hypothesis, inspector, finding, rules_out=False)` — appends to log
- `debug.set_root_cause(session, text)` — replaces the Root cause section
- `debug.close_session(session, repo, *, title, severity, symptom, root_cause, fix, lesson=None)` — finalizes + writes a `bugs.md` entry
- `debug.suggest_inspector(intent)` — returns the cheapest executor for a step:
  - `haiku` (or direct Bash) for grep / file-read / line-count / regex
  - `codex` for multi-file-trace / find-usages / context-gather
  - `opus` for reasoning / race-condition / architecture
- `debug.latest_session(repo)` — resume the most recent session

Call from inside the skill via:
```bash
python3 -c "from renmark import debug; s = debug.new_session('.', '<symptom>'); print(s.session_id)"
```

## Steps

**Step 0 — Context check.** Call `lifecycle.skill_preamble(repo, 'debug')`. If it returns a non-None hint, surface as a one-line note — debug is the `debug` domain, so transitioning into it from `build` or `audit` is a common cross-domain trigger.

**Lifecycle note:** Debug is orthogonal to the lifecycle — it does NOT update `lifecycle.json.stage`. The current feature stage is preserved across debug sessions; when debug ends, `/renmark:resume` continues from whatever stage was active before.

## The loop

### 1. Capture the bug

Call `debug.new_session(repo, symptom)`. This creates `.renmark/debug/<id>/session.md` with skeleton sections (Symptom, Hypotheses, Investigation log, Root cause, Fix, Verification). Update `session.md` with:
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
| Grep for a symbol, count lines, check file existence | Haiku or Bash (cheap, fast) |
| Trace a function across multiple files, find usages | Codex (agentic, reads context) |
| Reason about race conditions, async flow, architecture | Opus |

Run the inspection. Update `session.md` with findings — eliminate or confirm hypotheses.

### 5. Root cause

Once you've isolated WHY the bug exists (not just what fixes it), write the root-cause statement in `session.md`.

### 6. Fix

**Gate — before writing any code:** the root cause must be written as a single sentence in `session.md`. If you cannot state WHY the bug exists (not what fixes it), return to step 4. Patching symptoms without a confirmed root cause creates new bugs.

Draft the fix. If it's a clean single-file change, write a 1-task renmark plan and run `/renmark:orchestrate` on it. Otherwise Opus edits directly.

### 7. Verify

Run the original repro. It should now fail (i.e., the bug is gone). Add a regression test that would have caught this earlier.

### 8. Close the session

Append to `.renmark/memory/learnings.md`:
- Bug pattern (e.g., "MIME lookup with `.split('.')[-1]` doesn't match dict keys that include the dot")
- Fix pattern (e.g., "use `os.path.splitext(path)[1].lower()`")

## Iron Law

**No fixes without a confirmed root cause.** See CLAUDE.md § Root cause before any fix. Don't patch symptoms. If you can't articulate the root cause in one sentence, keep investigating.

## What's next

Debug is a class-3 aux / terminal skill. End by calling `renmark.lifecycle.next_steps(repo, "debug")` and render per `${CLAUDE_PLUGIN_ROOT}/skills/_shared/next-steps.md` (class 3 — resume-pipeline + 1–2 local actions). The in-flight feature's next command is `(Recommended)`; add debug's local follow-ups. Render via `AskUserQuestion` (handoff-menu.md rules 6–9); require an explicit choice — never auto-proceed.

Debug-specific local actions, after a confirmed fix:
- **`/renmark:verify`** — re-run the verifier to confirm the bug is gone and no regression slipped in (the repro must now pass, plus the goal-backward smoke test).
- **Resume the in-flight feature** — debug doesn't advance `lifecycle.json.stage`, so the in-flight feature's `next_recommended()` (from `lifecycle.json`) returns the user to whatever pipeline stage was active before the bug. If no feature is in flight, this option becomes `/renmark:start`.

If the failing verifier itself was the bug, re-running it directly is the right local action.

## Reference

- `superpowers:systematic-debugging` SKILL.md for the broader pattern
- `context-mode:diagnose` for the reproduce-minimize-hypothesize-instrument-fix discipline

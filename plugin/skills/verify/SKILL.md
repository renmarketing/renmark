---
name: verify
description: Use after /renmark:orchestrate completes — runs functional smoke tests derived from the plan's stated feature goal and reports how many requirements were confirmed. Never reads source code into conversation.
---

# verify

## Overview

Goal-backward smoke test. Reads the plan's context paragraph, extracts stated behaviors, runs one command per behavior, reports pass/fail. Never reads source files — only command output (exit code + first 3 lines of stdout).

## When to Use

- After `/renmark:orchestrate` completes successfully
- Before `/renmark:finish`

**Do NOT use:**
- As a substitute for a test suite — this is feature-level smoke testing, not unit coverage
- To fix failures — route those to `/renmark:debug`

## Steps

### 1. Read the plan context

Open the plan file. Read the context paragraph at the top. Extract N stated user-visible behaviors as a checklist — what the feature is supposed to do, not how it was decomposed.

### 2. Build smoke tests

For each behavior, write one shell command a user would actually run. Not internal module checks — observable output.

| Behavior | Example smoke test |
|---|---|
| "create entries with frontmatter" | `node src/journal.js new "Test" --tags "x" && echo OK` |
| "list past entries" | `node src/journal.js list \| grep "Test"` |
| "search by keyword" | `node src/journal.js search "Test" \| grep "Test"` |
| "store in SQLite" | `test -f ~/md-journal/journal.db && echo OK` |

### 3. Run and report

Run each command. Capture exit code + first 3 lines of stdout only. Do NOT read source files.

```
verify: <feature-name>

✅ create entry — exit 0
✅ list entries — exit 0, output contains "Test"
❌ search entries — exit 1: Error: no such table: entries

Result: 2/3 requirements verified.
Failed: search entries — run /renmark:debug with symptom: "search exits 1: no such table: entries"
```

### 4. Hand off (wizard step)

Renmark is a wizard pipeline. After reporting results:

- **All pass** → prompt:
  > *"N/N requirements verified. Ready to finish?*
  > *  [f] Finish — run /renmark:finish to create PR or merge*
  > *  [n] Nothing — done"*

  On **f** → invoke `/renmark:finish`. On **n** → stop.

- **Any fail** → prompt:
  > *"N/M requirements verified. Route failures to /renmark:debug?*
  > *  [d] Debug — start a debug session for the first failure*
  > *  [n] No — I'll handle it manually"*

  On **d** → invoke `/renmark:debug` with the first failed command's symptom. Do not attempt fixes here.

---
name: verify
description: Use after `/renmark:orchestrate` completes — runs goal-backward smoke tests derived from the plan's stated feature goal, cross-references open bugs for regressions, reports how many requirements were confirmed, writes a `.verification.md` artifact, and appends a learning entry. Never reads source code into conversation.
---

# verify

## Overview

Goal-backward smoke test. Reads the plan's intent paragraph via `parser.parse_plan()`, extracts stated user-visible behaviors, cross-references `.renmark/memory/bugs.md` for open regressions whose files overlap with the plan's targets, runs one command per behavior + regression, and reports pass/fail with bounded output (exit code + first 3 lines via `summary.verifier_tail`).

**Compounding verification (G8):** every run — pass or fail — appends to `.renmark/memory/learnings.md`. Failures additionally append a `bugs.md` entry. Verification history accrues as organizational memory.

**Context hygiene (G3, G5):** the orchestrator NEVER reads source files. Only command output, bounded at 3 lines per command. The full verification artifact lives at `.renmark/reviews/YYYY-MM-DD-<sha>.verification.md`; the orchestrator emits only the pointer summary.

## When to Use

- After `/renmark:orchestrate` completes successfully (`pipeline_state.current_phase` cleared, `lifecycle.stage == "created"`)
- Before `/renmark:finish`

**Do NOT use:**
- As a substitute for a test suite — this is feature-level smoke testing, not unit coverage
- To fix failures — route those to `/renmark:debug`
- When the orchestrate pipeline is still in flight — refuse if `pipeline_is_resumable(repo)` is True

## Steps

**Step 0 — Context check + pipeline gate.** Call `state.context_budget_check(repo, 'verify', 'build')`. If `'clear'` returned, surface as a one-line note. Then call `state.record_skill_invocation(repo, 'verify', 'build')`. Also check `state.read_pipeline_state(repo)` — if a prior orchestrate run is paused or in flight (`pipeline_is_resumable(repo)` is True), refuse:

> *"Orchestrate did not finish cleanly. Run `/renmark:debug` first or re-run `/renmark:orchestrate --resume`."*

Verify the lifecycle stage is `created` or later. If `stage == "init"` or `"plan-validated"`, refuse — there's nothing to verify yet.

### 1. Read the plan goal + cross-reference open bugs

```python
from renmark import parser, lifecycle
from pathlib import Path
plan_path = lifecycle.read_lifecycle(repo).artifacts.get("plan")
plan = parser.parse_plan(Path(plan_path))
goal_paragraph = plan.context  # the intent block at the top
target_files = {t.target for t in plan.tasks}
```

Extract N user-visible behaviors from `goal_paragraph` — what the feature is supposed to do, not how it was decomposed.

**Regression cross-reference (G8 compounding):** read `.renmark/memory/bugs.md`. For each open bug, check if its declared `files:` overlap with `target_files`. Add each overlapping bug as an additional smoke test — *"the fix for bug #N still holds: <bug.symptom>"*. This is how prior failures expand future regression coverage.

### 2. Build smoke tests

For each behavior + regression, write one shell command a user would actually run. Not internal module checks — observable output.

| Behavior | Example smoke test |
|---|---|
| "create entries with frontmatter" | `node src/journal.js new "Test" --tags "x" && echo OK` |
| "list past entries" | `node src/journal.js list \| grep "Test"` |
| "search by keyword" | `node src/journal.js search "Test" \| grep "Test"` |
| "store in SQLite" | `test -f ~/md-journal/journal.db && echo OK` |
| (regression) "bug #42 — empty input no longer crashes" | `echo "" \| node src/journal.js new && echo OK` |

### 3. Run and report

For each smoke test, call `summary.verifier_tail(cmd, cwd=repo, tail_lines=3)`. Orchestrator-visible output per test is bounded at 1 line: `exit <code> | <first 3 lines collapsed>`. Do NOT read source files.

Sample output:

```
verify: <feature-name>

✅ create entry — exit 0 | OK
✅ list entries — exit 0 | Test
❌ search entries — exit 1 | Error: no such table: entries
✅ bug #42 regression — exit 0 | OK

Result: 3/4 requirements verified.
Failed: search entries — run /renmark:debug with symptom: "search exits 1: no such table: entries"
```

### 4. Emit verification artifact (G6)

Write `.renmark/reviews/YYYY-MM-DD-<sha>.verification.md` via `summary.write_artifact`:

```python
from renmark import summary
summary.write_artifact(
    artifact_path,
    artifact_type="verification",
    body=full_test_log,  # all commands + bounded outputs
    summary_lines=[
        f"{passed}/{total} behaviors verified",
        f"feature: {feature_name}",
        f"failed: {', '.join(failed_names) or 'none'}",
        f"regressions checked: {n_regressions}",
        f"next: {recommended_next_command}",
    ],
    related_plan=plan_path,
    source_sha=summary.git_head_sha(repo),
    generator="verify",
    completion_state="complete" if passed == total else "partial",
    confidence="high" if passed == total else "medium",
    validation_status="validated",
)
```

Emit only the pointer to the orchestrator's conversation via `summary.emit_pointer(artifact_path, "verify")`.

### 5. Compounding learnings + bug logging (G8)

On EVERY run (pass or fail):

```python
from renmark.memory import append_learning
append_learning(
    repo,
    signal=f"verify-{feature_name}",
    observation=(
        f"{passed}/{total} behaviors verified; "
        f"failed: {','.join(failed_names) or 'none'}; "
        f"regressions: {n_regressions}"
    ),
    source=str(artifact_path),
    model="verify",
)
```

On any FAIL:

```python
from renmark.memory import log_bug
for failed in failed_tests:
    log_bug(
        repo,
        title=f"verify failure: {failed.name}",
        severity="medium",  # promote to high if it's a regression of a closed bug
        symptom=failed.bounded_output,
        root_cause="(unknown — route to /renmark:debug)",
        fix="(pending)",
        lesson=f"smoke test '{failed.name}' failed during verify of {feature_name}",
    )
```

This is what makes verification compound. Every failed verify expands the next verify's regression set; every passed verify accrues confidence in the routing memory.

### 6. Lifecycle update

```python
from renmark import lifecycle
lifecycle.write_lifecycle(repo, stage="verified",
                          artifact_update=("verification", str(artifact_path)))
```

Sets the stage to `verified` so `/renmark:resume` knows the next step is `/renmark:codereview` (or `/renmark:finish` if review was already done in a prior pass).

### 7. Hand off (wizard step)

After reporting results:

- **All pass** → prompt:
  > *"N/N requirements verified. Artifact: PATH. Ready for review?*
  > *  [c] Code review — run /renmark:codereview*
  > *  [f] Finish — skip review, mark ready-to-release*
  > *  [n] Nothing — done"*

  On **c** → invoke `/renmark:codereview`. On **f** → invoke `/renmark:finish`. On **n** → stop.

- **Any fail** → prompt:
  > *"N/M requirements verified. Artifact: PATH. Route failures to /renmark:debug?*
  > *  [d] Debug — start a debug session for the first failure*
  > *  [n] No — I'll handle it manually"*

  On **d** → invoke `/renmark:debug` with the first failed command's symptom. Do not attempt fixes here.

## Governance compliance

| # | Rule | How this skill complies |
|---|---|---|
| G2 | Canonical state | Reads plan via parser; writes verification artifact + lifecycle update; never relies on conversation. |
| G3 | Summary boundary | Output bounded via `summary.verifier_tail(tail_lines=3)`; artifact summary capped at 5 lines. |
| G5 | Executor isolation | N/A — verify runs shell commands locally; no LLM dispatch. |
| G6 | Artifact governance | Verification artifact carries full metadata via `summary.write_artifact`. |
| G7 | Compact semantics | All state on disk (artifact + lifecycle + memory); `/compact` mid-run is safe. |
| G8 | Compounding verification | Every run appends to `learnings.md`; every fail appends to `bugs.md`. Next verify reads bugs.md and adds regression tests. |
| G9 | Failure transparency | Artifact metadata sets `completion_state=partial` and `confidence=medium` on partial fails — honest about uncertainty. |
| G10 | Workflow recovery | Refuses if pipeline state is dirty; lifecycle.json updated on completion. |
| G11 | Task isolation | N/A — no subagent dispatch. |
| G12 | Lifecycle persistence | `lifecycle.write_lifecycle(stage='verified', artifact_update=...)` at end. |

---
name: orchestrate
description: Use when the user wants to execute an existing renmark plan — typed as /renmark:orchestrate or phrases like "deploy this plan", "execute the plan", "run the orchestrator", "build it". Reads the plan, dispatches each task to its assigned executor (opus, codex, sonnet, haiku), runs verifiers, commits per task, and writes summary state to .renmark/state/. Skill loads only summary lines into Opus context — generated code bodies stay in subprocesses or subagents.
---

# orchestrate

## Overview

Dispatches plan tasks in waves. Within a `parallel_group`, tasks run concurrently. **Two separate dispatch paths — never mix them:**

| Executor | Dispatch path | Quota consumed |
|---|---|---|
| `codex` | Bash call to `renmark-execute` | Codex account (OpenAI subscription) |
| `haiku`, `sonnet`, `opus` | Agent tool calls (no model override) | Claude Code account (Anthropic subscription) |

After each wave, the skill commits passing tasks serially in task-index order.

**Token-isolation contract:** the skill NEVER reads generated code into the conversation. Only per-task summaries (PASS/FAIL/skip + sha + token count). On escalation, the skill reads `.renmark/state/escalations/task-N/` artifacts.

## When to Use

- User has a `.renmark/plans/*.plan.md` file ready and wants it executed
- After `/renmark:plan` completes
- To `--resume` a paused run

**Do NOT use:**
- Without a plan file → `/renmark:plan` first
- For brainstorming or design — that's `/renmark:brainstorm`

## Steps

### 1. Discover plan

If the user gave a path, use it. Otherwise:

```bash
ls -1t .renmark/plans/*.plan.md 2>/dev/null | head -1
```

Confirm the path with the user before continuing.

### 2. Pre-flight (free)

Before running anything, check env vars for the executors the plan uses:

```bash
# codex CLI must be on PATH for any plan with executor: codex tasks
command -v codex >/dev/null || echo "codex not found — install openai-codex CLI first."
```

If codex is missing and the plan has codex tasks, **stop and tell the user before running**.

**Refactor safety check** — if the plan has any task with `complexity: hard` OR the spec mentions "refactor", "rename", "restructure", "migrate":
1. Run `git status` — confirm working tree is clean
2. Run a checkpoint commit: `git -c user.name="renmark-orchestrate" -c user.email="orchestrate@renmark.local" commit --allow-empty -m "chore: checkpoint before <plan name>"`
3. Run each affected task's verifier once now as baseline — if any fail, **stop**: the plan cannot proceed into a broken baseline

**Changelog check** — read the last 3 entries in `CHANGELOG.md` (if it exists) and flag any "Do not change" guards that overlap with the current plan's target files. Report them before proceeding.

**Plan validation** — invoke `/renmark:check-plan <plan>` before spending tokens. If it exits 1 (BLOCK), fix the plan first. WARNs can proceed.

```bash
renmark-execute --dry-run <plan>
```

Show the task list and cost preview. Ask: *"Proceed? [y/N]"*

### 3. Run codex tasks

**RED FLAG — never dispatch a `codex` task as an Agent call.** Codex tasks run exclusively through `renmark-execute` (a Bash subprocess that calls the Codex CLI). Dispatching them as Agents runs them on the parent Claude model instead, consuming Anthropic credits and ignoring the cost/routing intent of the plan.

Before starting a wave that has `executor: codex` tasks, pre-create the target directories so codex doesn't scaffold extra files to compensate for a missing directory context:
```bash
# For each codex task target in the wave:
mkdir -p "$(dirname <target>)"
```

```bash
renmark-execute <plan>
```

Stream summary lines as they arrive. Do NOT cat generated files. Monitor the background process with the `Monitor` tool — do NOT use `sleep N && cat output` (blocked by hooks).

After each successful wave commits, append a new entry to `CHANGELOG.md`:
```
## [YYYY-MM-DD] — [plan task title]
**Request:** [1-2 sentence plain-English summary of what was asked]
**Built:** [what was actually implemented]
**Files changed:**
- `<target>` — [what changed and why]
**Do not change:**
- [any invariants discovered during this task]
```
Include `CHANGELOG.md` in the same git add/commit as the task output.

### 3b. Run haiku/sonnet/opus tasks (in-context Agent dispatch)

`renmark-execute` does not call Claude — these are dispatched by **you** as Agent tool calls. See CLAUDE.md § Executor dispatch rules. For each task:

- Plain `Agent` call — no `model` override (triggers worktree creation)
- Specify absolute path in agent prompt: *"Working directory: `<abs_project_path>`. Write to `<abs_project_path>/<target>`."*
- Pass full task spec, target file, verifier, and "do not commit" constraint
- After agent returns, run the verifier yourself to confirm exit 0

**CWD rule:** Run all verifiers and git with absolute paths. For Node.js, run `npm install --prefix <abs>` before any `node -e "require(...)"` verifier. Use absolute require paths: `node -e "require('/abs/path/file.js')"`.

```bash
git -c user.name="renmark-orchestrate" -c user.email="orchestrate@renmark.local" commit -m "..."
```

### 4. Interpret outcome

| Exit | Meaning | Action |
|---|---|---|
| 0 | All tasks passed | Report totals; tag end |
| 2 | Plan parse error | Route to `/renmark:plan` |
| 10 | Paused | Read `.renmark/state/PAUSED` + escalation artifacts |

### 5. On escalation

Read `.renmark/state/escalations/task-N/{metadata.json,prompt.txt,response.txt,verifier.log}`. Propose 2-3 options: fix manually + resume, switch executor in the plan + resume, skip the task.

### 6. Update memory

Use `renmark.memory` helpers — **do NOT hand-edit memory files directly** (especially `routing.md` — direct edits corrupt its header table).

```python
from renmark.memory import log_feature, append_routing, append_learning, log_bug
# log_feature → features.md | append_routing → routing.md (Learned overrides only)
# append_learning → learnings.md | log_bug → bugs.md (escalations only)
```

Run `python3 -c "from renmark import memory; help(memory)"` for full API.

### 7. Hand off (wizard step)

**Re-verify before reporting done** — see CLAUDE.md § Verification before completion. Re-run all task verifiers in index order before showing the menu. Report any that now fail; do not claim success until all pass fresh.

Renmark is a wizard pipeline. After a clean run (exit 0), offer the next step:

> *"All N tasks committed (M commits, ~$X spent).*
> *What's next?*
> *  [v] Verify — run /renmark:verify to confirm the feature goal was achieved*
> *  [c] Code review — run /renmark:codereview HEAD~N..HEAD*
> *  [f] Finish — run /renmark:finish to create PR or merge*
> *  [s] Smoke test — open a shell and verify manually*
> *  [n] Nothing — done"*

On **v** → invoke `/renmark:verify`.
On **c** → invoke `/renmark:codereview <range>` with the appropriate ref range.
On **f** → invoke `/renmark:finish`.
On **s/n** → stop, leave the user in a clean state.

If exit != 0 (paused / escalated), do NOT offer the next step. Surface the failure and the resume command first.

## Reference

- CLI flags: `renmark-execute --help`
- Plan format: `PLAN.md` § "Plan file format"
- State dir: `.renmark/state/`

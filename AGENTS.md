# {{PROJECT_NAME}} — agent guide

> For non-Claude AI agents (Codex, Cursor, etc.). Mirror of `CLAUDE.md`, shorter.
> Keep in sync: any rule change in `CLAUDE.md` must be mirrored here in the same commit.

## What this project is

(Filled in by `/renmark:brainstorm`.)

## Core rules

**Parallelize large plans.** Independent file scopes run concurrently. Two agents touching the same file must be sequential.

**Stay on main for small changes.** Hotfixes, config edits, and single-file changes land directly on `main`. New features and significant refactors go through `/renmark:feature`, which creates a `feature/<slug>` branch and offers a PR on finish. See `CLAUDE.md` § `single-branch-rule`.

**Commit per chunk.** One commit per logical change. Each commit must compile. Don't batch unrelated work.

**Check and update CHANGELOG.md.** Before any task, read the last 5 entries for prior decisions and "Do not change" guards. After the task, append a new entry (request, files changed, invariants).

**Pre-refactor safety.** If touching >3 files or doing a refactor: confirm clean tree → checkpoint commit → baseline verifier → make changes → compare verifier. Stop if baseline is already broken.

**Absolute paths.** Always write files using the absolute path from the task spec. Never use relative paths — shell CWD is unpredictable across agent dispatches.

**Single-file scope.** Read and modify only the file named in the task `target`. Do not read other source files — the task spec is your source of truth.

**Root cause before any fix.** Before changing any code, write the root cause in one sentence. If you cannot, keep investigating.

**Verification before completion.** Re-run the task verifier fresh before declaring done. Do not rely on a result from earlier in the session.

**Orchestrator coordinates; does not accumulate.** Context degrades before it fills. Prefer artifacts, summaries, and persistent state over inline context. See `CLAUDE.md` § `orchestrator-role-rule`.

**Canonical state lives outside the conversation.** Truth lives in `.renmark/specs/`, `.renmark/reviews/`, `.renmark/memory/`, `.renmark/state/`, and CHANGELOG.md — not in chat history. See `CLAUDE.md` § `canonical-state-rule`.

**All renmark output stays inside the project.** Specs, plans, reviews, research, logs, memory — everything goes under this project's `.renmark/` subtree or a project-root doc. Never write to the global plugin install (`${CLAUDE_PLUGIN_ROOT}`, `~/.claude/...`), `$HOME`, or above the project root. Reading templates/reference files from the plugin is fine; the install is read-only. See `CLAUDE.md` § `project-write-boundary-rule`.

**Orchestrator-visible output ≤ 5 lines or ≤ 300 tokens.** Long task results live in artifact files; the orchestrator reads only a structured summary. Never paste diffs, generated code, or audit bodies back into conversation. See `CLAUDE.md` § `summary-boundary-rule`.

**Cross-domain skill transitions recommend `/clear`.** Domains: debug, build, audit, meta. `.renmark/memory/` survives clears. See `CLAUDE.md` § `context-contamination-rule`.

**Artifacts carry metadata.** Every written artifact includes `artifact_type`, `schema_version`, `created_at`, `source_sha`, `related_plan`, `generator`, optional `stale_after`, and `dependency_refs`. Untyped artifacts are not trusted as upstream context. See `CLAUDE.md` § `artifact-governance-rule`.

**`/compact` preserves operational state.** Preserve goals, blockers, pipeline state, artifact refs, verification status. Discard stale reasoning and duplicates. After compact, every workflow must still resume from `.renmark/state/`. See `CLAUDE.md` § `compact-semantics-rule`.

**Artifact existence ≠ correctness.** Every executor output exposes `completion_state`, `confidence`, `validation_status`, `retry_count`, `parser_success`, `schema_compliance`. Prefer explicit uncertainty over silent success. See `CLAUDE.md` § `failure-transparency-rule`.

**Workflows are resumable.** Every multi-step workflow survives interruption, partial completion, executor failure, context clearing, and orchestrator restart — via `.renmark/state/pipeline.json`, not conversational reconstruction. See `CLAUDE.md` § `workflow-recovery-rule`.

**`/renmark:orchestrate` isolates tasks.** Each task or parallel group runs in an isolated subagent context. Subagents receive only spec + paths + upstream pointers + dependency summaries + verifier; they emit only status + artifact path + touched files + sha + ≤5-line summary + dependency notes. Transcripts and generated code never re-enter the orchestrator. See `CLAUDE.md` § `task-isolation-rule`.

**Context budget — `/compact` at 60%, `/clear` on subject change.** At ~60% utilization, surface a `/compact` recommendation. At ~80%, refuse new long-running skills until /compact or /clear runs. Cross-domain transitions auto-recommend `/clear` via `renmark.state.context_budget_check`. See `CLAUDE.md` § `context-budget-rule`.

**Lifecycle persists across `/clear`.** Every workflow stage transition writes `.renmark/state/lifecycle.json`. After `/clear`, run `/renmark:resume` to recover — one file read, zero LLM calls. Runtime state lives in `pipeline.json`, never lifecycle.json. Human approval gates (release/merge/security override) flow through `human_review_required` / `human_review_completed` fields; `/renmark:approve` is the sole flip surface. See `CLAUDE.md` § `lifecycle-rule`.

## Conventions

- Plans: `.renmark/plans/`
- Specs: `.renmark/specs/`
- Reviews / verification: `.renmark/reviews/`
- Debug sessions: `.renmark/debug/<session-id>/`
- Audit reports: `.renmark/audits/`
- Project memory: `.renmark/memory/` — read `INDEX.md` first
- Changelog: `CHANGELOG.md` — persistent project history
- Tests: run via command in `CLAUDE.md` § Testing
- Source of truth: `PRD.md`. For new features/changes, dispatch a subagent to read `PRD.md` + docs and return a bounded alignment/drift summary — never load the full PRD into the orchestrator.

## Tooling — renmark workflow

| Command | When to use |
|---|---|
| `/renmark:start` | Plain-English entry — describe what to build, renmark routes the pipeline |
| `/renmark:brainstorm <topic>` | Flesh out an idea into a spec with scope contract |
| `/renmark:prd` | Create/update the project PRD — the durable source of truth |
| `/renmark:blueprint` | Generate/refresh the living schematic (+ prototype for UI builds) |
| `/renmark:plan <spec>` | Decompose a spec into atomic, executor-tagged tasks |
| `/renmark:check-plan <plan>` | Validate plan structure before spending tokens |
| `/renmark:orchestrate <plan>` | Execute a plan — routes tasks to Haiku / Codex / Sonnet / Opus |
| `/renmark:verify` | Confirm feature goal was achieved after orchestrate |
| `/renmark:feature` | Full pipeline with branch isolation (brainstorm → finish) |
| `/renmark:loop "<goal>"` | Bounded, resumable agentic loop (iterate until verified or budget hit) |
| `/renmark:finish` | Close branch — build version zip+snapshot into `.renmark/version/`, then PR, merge, or release (gh release only with a remote) |
| `/renmark:backlog` | Triage backlog items; "Approve and build" launches bounded Loop Mode |
| `/renmark:debug <symptom>` | Systematic root-cause loop for bugs |
| `/renmark:codereview <ref>` | Diff-proportional review: lite in-context for small diffs, full Codex pass for core code |
| `/renmark:audit` | Read-only self-audit — verifies registry/docs/skill parity; artifacts under `.renmark/audits/` |
| `/renmark:inventory` | Alias for `/renmark:audit` — lists registered skills and command surface |
| `/renmark:approve` | Flip the human-review gate (`human_review_completed`) — sole approval surface |
| `/renmark:hygiene --apply` | Flag and optionally clean stale artifacts, orphan branches, oversized memory |
| `/renmark:doctor` | Diagnose install health — run if `/renmark:*` commands don't appear |
| `/renmark:init` | Scaffold or update CLAUDE.md / AGENTS.md / `.renmark/` in an existing project |
| `/renmark:setup` | Thin alias for `/renmark:init` (rule-block refresh only) |
| `/renmark:resume` | Cold-start recovery — reads lifecycle.json, prints next recommended command |
| `/renmark:roadmap` | Project status, gap discovery (PRD vs shipped), and token usage |
| `/renmark:usage` | Rolling observed usage — 5-hour / weekly, top features, quota events |
| `/renmark:analytics` | Usage analytics over time — model/executor mix, verification outcomes |
| `/renmark:help` | List all commands |

## What renmark expects

When implementing a task from `.renmark/plans/*.plan.md`:
- Modify exactly the file in the task's `target` field
- Do not modify other files unless the spec says so
- Do not run `git commit` — the orchestrator handles commits
- Run the task's `verifier` to self-check before declaring done

## Key files

- `CLAUDE.md` — full project context and rules
- `CHANGELOG.md` — project history and "Do not change" guards
- `.renmark/memory/conventions.md` — code/test conventions for this project

<!-- BEGIN:project-stub -->
<!-- Managed by /renmark:init. Last refreshed: 2026-05-28 @ 95f0d9d. Edits inside this block will be overwritten. -->

## Project at a glance

**Stack:** Python >=3.10 (pyproject.toml) + Claude Code plugin
**Entry points:** `bin/renmark-execute`, `renmark/__main__.py`, `plugin/commands/*.md`

**Top-level layout:**
- `bin/` — executable scripts / wrappers
- `plugin/` — Claude Code plugin (commands, skills, templates)
- `renmark/` — Python runtime (CLI, dispatch, verifier, lifecycle)
- `tests/` — test suite
- `tools/` — maintainer scripts


**Dev gates:** test `pytest -q` · lint `ruff check` · types `mypy .` · CI: test
**Standards detail** → `.renmark/memory/dev-standards.md` (read before non-trivial changes).

**Detailed map** (modules, symbols, full tree) → `.renmark/memory/project-map.md`. Read it when you need to find a specific module or symbol.
<!-- END:project-stub -->

# renmark — guided build assistant (Claude Code plugin) — agent guide

> For non-Claude AI agents (Codex, Cursor, etc.). Mirror of `CLAUDE.md`, shorter.
> CLAUDE.md and AGENTS.md hold the same rule set in parallel. Mirror any rule change across both files in the same commit.

## What this project is

`renmark` is a Claude Code plugin (v0.10.0) — a guided build assistant that runs a full pipeline (`/renmark:start` → brainstorm → plan → check-plan → orchestrate → verify → finish). It routes each task to the cheapest capable executor (Haiku / Codex / Sonnet / Opus / Fable), keeps orchestrator context lean, and persists all state to disk so workflows survive `/clear`. Newer iteration than `legacy-plugin`; prefer it for new work. Python >=3.10 required for `renmark-execute`; Codex CLI optional. Doctrine: probabilistic AI for reasoning, deterministic code for execution; the orchestrator coordinates and never accumulates implementation context.

## Core rules

**Parallelize large plans.** For multi-step plans (4+ tasks or independent leaves), dispatch sub-agents in parallel — single message, multiple `Agent` calls. Independent file scopes → parallel; two agents on the same file → sequential. Read-only verification runs parallel alongside code work. Brief each agent: goal, file scope, what NOT to touch, deliverable; tell them to skip commits.

**Stay on main for small changes.** Hotfixes, config edits, and single-file changes land directly on `main`. Use `/renmark:feature` for new features or significant refactors — it branches, runs the full pipeline, and offers PR on finish.

**Commit per chunk, not per session.** Commit as soon as a logical chunk passes its check. One commit per logical fix/feature; commit before the next agent dispatch; each commit must pass lint; messages name the change, not the session ("fix(auth): handle 401").

**Check and update CHANGELOG.md on every task.** Before any task, read the last 5 `CHANGELOG.md` entries for prior decisions and "Do not change" guards. After completing a task, append an entry with: date + title, Request, Built, Files changed, Do not change. The changelog is the project's persistent memory — keep it honest and current.

**Pre-refactor safety protocol.** Before any change touching >3 files or tagged "refactor"/"migrate"/"restructure": (1) confirm clean tree (`git status`); (2) checkpoint with an empty commit; (3) run verifier/tests as baseline — if failing now, **stop and report**; (4) change, re-run, compare pass counts. If tests regress, revert targeted files.

**Context hygiene.** Never read generated file contents into the conversation — only per-task summaries (exit code, verifier pass/fail, path). To debug a generated file, route to `/renmark:debug`, which isolates the artifact in its own session.

**Absolute paths.** Always write files using the absolute path from the task spec. Never use relative paths — shell CWD is unpredictable across agent dispatches.

**Single-file scope.** Read and modify only the file named in the task `target`. Do not read other source files — the task spec is your source of truth.

**Root cause before any fix.** Before changing code to fix a bug, write the root cause in one sentence: WHY the bug exists, not what fixes it. If you can't write it, keep investigating. See Iron Law in `/renmark:debug`.

**Verification before completion.** Before claiming any task or plan complete, re-run the verifier fresh — a verifier that passed in wave 3 may be broken by wave 4. Evidence first, claim second.

**The orchestrator coordinates; it does not accumulate.** Treat orchestrator context as a degrading resource, not durable memory; quality drops before the window fills. Never fix an orchestration problem by adding inline context. Prefer artifact emission, structured summaries, file pointers, persistent state, resumable workflows. See `CLAUDE.md` § `orchestrator-role-rule`.

**Canonical state lives outside the conversation.** Conversation history is NOT authoritative. Canonical state lives in `.renmark/` artifacts (specs/reviews/memory), pipeline state files, memory logs (`features.md`, `bugs.md`, `decisions.md`, `learnings.md`), and artifact metadata. Any cross-phase workflow MUST persist state to disk, not rely on "what was said". See `CLAUDE.md` § `canonical-state-rule`.

**Source of truth: `PRD.md` (if present).** For new features/changes, dispatch a subagent to read `PRD.md` + docs and return a bounded alignment/drift summary — never load the full PRD into the orchestrator. See `CLAUDE.md` § `prd-delegation-rule`.

**All renmark output stays inside the project.** Every file renmark generates MUST be written inside this project, under `.renmark/` or a project-root doc. Canonical homes: specs→`.renmark/specs/`, plans→`.renmark/plans/`, reviews/verification→`.renmark/reviews/`, research→`.renmark/research/`, runtime→`.renmark/state/`, memory→`.renmark/memory/`, logs→`.renmark/logs/`, debug→`.renmark/debug/<session-id>/`, audits→`.renmark/audits/`. **Never write outside the project** — the global plugin install (`~/.claude/plugins/...`, `${CLAUDE_PLUGIN_ROOT}`), `$HOME`, and anything above the project root are read-only. Reading FROM the plugin dir is fine. See `CLAUDE.md` § `project-write-boundary-rule`.

**Orchestrator-visible output is bounded.** Every long/high-context task MUST end in (1) a durable artifact and (2) a compact summary. Orchestrator MAY read summaries, counts, status, paths, hashes, metadata. Orchestrator MUST NOT read full diffs, large logs, research dumps, generated code, audit bodies, architecture scans. **Default cap: 5 lines OR ≤ 300 tokens** per task unless the user overrides. Violations are bugs, not optimizations. See `CLAUDE.md` § `summary-boundary-rule`.

**Cross-domain transitions recommend `/clear`.** When a new skill is invoked from a different domain than the previous one, recommend `/clear` first. `.renmark/memory/` survives clears. Domains: `debug` (debug, codereview); `build` (start, brainstorm, plan, check-plan, orchestrate, verify, finish, feature, prd, blueprint, backlog, loop); `audit` (audit, inventory); `meta` (setup, roadmap, help, resume, approve, hygiene, doctor, init, usage, analytics). Same-domain transitions don't trigger it; cross-domain ones do. See `CLAUDE.md` § `context-contamination-rule`.

**Artifacts carry provenance and freshness metadata.** Every artifact a renmark skill writes MUST carry machine-readable top metadata: `artifact_type`, `schema_version`, `created_at`, `source_sha`, `related_plan`, `generator`, `stale_after` (optional), `dependency_refs`. Artifacts without freshness/provenance metadata are untrusted as upstream context. Prefer invalidation over silent drift; don't solve context rot with artifact rot. See `CLAUDE.md` § `artifact-governance-rule`.

**`/compact` is not truncation.** A compact MUST preserve operational continuity. Preserve: active goals, unresolved blockers, pipeline state, artifact references, verification status. Discard: stale reasoning, duplicate discussion, obsolete branches. After `/compact`, every workflow must still be resumable from `.renmark/state/`. See `CLAUDE.md` § `compact-semantics-rule`.

**Artifact existence ≠ artifact correctness.** All executor outputs MUST expose: `completion_state`, `confidence`, `validation_status`, `retry_count`, `parser_success`, `schema_compliance`. Prefer explicit uncertainty over silent success. A subagent returning an artifact path without these is treated as `confidence: low, validation_status: unvalidated` and flagged for review. See `CLAUDE.md` § `failure-transparency-rule`.

**Every multi-step workflow is resumable.** Orchestration MUST survive interruption, partial completion, executor failure, `/clear` mid-pipeline, and orchestrator restart. Recovery depends on persisted state at `.renmark/state/pipeline.json`, never conversational reconstruction. Every skill running >1 step MUST update pipeline state before returning. See `CLAUDE.md` § `workflow-recovery-rule`.

**`/renmark:orchestrate` runs each task in isolation.** Each task (or parallel group) runs in an isolated subagent/executor context (G11). The orchestrator MUST NOT carry implementation context between tasks unless the dependency graph requires it. Each subagent receives ONLY: task spec; required file paths; upstream artifact pointers (paths, never contents); dependency summaries from `.renmark/state/wave-summaries/`; verifier expectations. Each subagent writes ONLY: task artifact (code/diff lives here); status (`PASS`|`FAIL`|`SKIP`); touched files; sha/hash; summary ≤ 5 lines; dependency notes. Orchestrator aggregates ONLY: PASS/FAIL/SKIP; artifact path; token count; dependency status; next-wave readiness. Never merged back: subagent transcript, generated code, diff, long reasoning. See `CLAUDE.md` § `task-isolation-rule`.

**Context budget — `/compact` at 60%, `/clear` on subject change.** Orchestrator runs on Sonnet 200k; the window degrades before it fills, so act early. At ~60% (≈120k tokens): surface a one-line note suggesting `/compact` before the next skill — do NOT auto-run it. At ~80% (≈160k tokens): refuse to start a new long skill (`orchestrate`, `loop`, `audit`) until `/compact` or `/clear`; short skills still run. Cross-domain transition: recommend `/clear` (memory survives). The %-side is enforced by orchestrator self-monitoring; the cross-domain side is automated via `renmark.lifecycle.skill_preamble`. See `CLAUDE.md` § `context-budget-rule`.

**Lifecycle persistence (G12).** Every workflow stage transition MUST write `.renmark/state/lifecycle.json` before the skill returns; skills that don't are bugs. Canonical stage order: `init → brainstorm-complete → plan-drafted → plan-validated → created → verified → reviewed → documented → ready-to-release → released`. Separation: lifecycle.json carries WORKFLOW state only (identity, stage, artifact pointers, approval gates); RUNTIME state (wave indices, retry counts, pids) lives in `pipeline.json`. Over ~1KB is a bug (`LifecycleBloatError`). Human gates: lifecycle.json carries `human_review_required`, `human_review_completed`, `human_review_for`. Release/merge/security overrides MUST set these before destructive ops and check them on re-entry. `/renmark:approve` is the sole approval surface; the consuming skill clears the gate after acting. See `CLAUDE.md` § `lifecycle-rule`.

**Executor dispatch.** `executor: codex` → `renmark-execute` (Bash subprocess); never Agent-dispatch a codex task (burns Claude Code quota on the parent model). `executor: haiku / sonnet / opus` → Agent calls, no model override. `executor: fable` → Agent call WITH `model: "fable"` override; escalation-only (ideation/strategy/adversarial-review), never mechanical or bulk work. Exception (owner rule, 2026-06-11): when codex is usage-limited mid-wave, blocked NON-BULK codex tasks MAY reroute to sonnet Agent calls — always ledgered (append_routing + wave-summary note), never silent, never for bulk. See `CLAUDE.md` § `executor-dispatch-rule`.

## Tooling — renmark workflow

Full command list and usage → run `/renmark:help`. Typical order: start → brainstorm → prd → plan → check-plan → orchestrate → verify → finish.

## Conventions

- Plans: `.renmark/plans/` · Specs: `.renmark/specs/` · Reviews/verification: `.renmark/reviews/`
- Debug sessions: `.renmark/debug/<session-id>/` · Audit reports: `.renmark/audits/`
- Project memory: `.renmark/memory/` — read `INDEX.md` first
- Changelog: `CHANGELOG.md` — persistent project history; read before tasks, update after
- Before proposing a custom build, run the reuse check → see `plugin/skills/_shared/reuse-check.md`.
- Dispatched agents push back by default and skip sycophancy → see `plugin/skills/_shared/reasoning-contract.md`.

## What renmark expects

When implementing a task from `.renmark/plans/*.plan.md`:
- Modify exactly the file in the task's `target` field; do not modify others unless the spec says so
- Do not run `git commit` — the orchestrator handles commits
- Run the task's `verifier` to self-check before declaring done

## Executor preferences

Per-task-signature routing history → see `.renmark/memory/routing.md`. Defaults: haiku (mechanical), codex (test scaffolding/single file), sonnet (algorithms/refactors), opus (state machines, cross-file). `fable` is frontier reasoning — escalation-only, never default.

## Code conventions & Testing

Dev gates and standards → see `.renmark/memory/dev-standards.md`. Verifiers in renmark plans must match the project's test command.

## At a glance

Modules, symbols, full tree → `.renmark/memory/project-map.md`. Full project context and rules → `CLAUDE.md`.

*Mirror all rule changes in `CLAUDE.md` in the same commit.*

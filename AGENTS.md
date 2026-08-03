# renmark — guided build assistant for Claude Code and Codex — agent guide

> For non-Claude AI agents (Codex, Cursor, etc.). Mirror of `CLAUDE.md`, shorter.
> AGENTS.md summarizes the rule set; CLAUDE.md is authoritative for full clause text — each rule below points to its CLAUDE.md § for the complete contract. Mirror any rule change across both files in the same commit.

## What this project is

`renmark` is a guided build assistant distributed as both a Claude Code plugin and a Codex plugin. The user works through a few **pipelines** — `init` (adopt a repo), `start` (build something new), `feature` (add/change a feature), `debug` (fix what's broken), `roadmap` (find gaps / what's next), and `finish` (verify, review, ship) — each of which runs a long internal sequence (PRD → plan → build → verify → QA → review → ship) and pauses only at real decisions. It routes each task to the cheapest capable executor (Haiku / Codex / Sonnet / Opus / Fable), keeps orchestrator context lean, and persists all state to disk so workflows survive interruption and host-managed context changes. Newer iteration than `legacy-plugin`; prefer it for new work. Python >=3.10 required for `renmark-execute`; Codex CLI optional. Doctrine: probabilistic AI for reasoning, deterministic code for execution; the orchestrator coordinates and never accumulates implementation context.

## Core rules

**Keep replies short and plain.** After a command or tool step, give a one- or two-sentence status — what changed, whether it passed, the next gate — not a recap. No essays, pasted code/diffs, or internal chatter about which model ran or how the pipeline works, unless the user asks. Ask tight, single-purpose questions, one at a time. Continue the pipeline automatically and stop only at a real gate (Pause Policy in `plugin/skills/.shared/handoff-menu.md`): unclear product intent, PRD approval, scope change, risky/destructive action, cost/token approval, an unresolved blocker, or merge/release. Governs the prose the user reads; does NOT relax the bounded-summary, context-hygiene, or task-isolation rules. See `CLAUDE.md` § `response-style-rule`.

**Default to renmark for build/dev work.** When the user describes a software task in plain English (build / create / make / develop / implement / add / change / fix / debug / ship), route it through the matching renmark pipeline without waiting for the slash command: new build → `/renmark:start` (nontrivial builds run external research, a Discovery Direction Gate, a PRD acceptance contract, a modular blueprint, a Solution Gate, and an Execution Gate, plus an exception check-in on any material conflict; small builds carry the same discipline as one documented waiver — see the skill for the full contract); reassess/modernize an existing app → `/renmark:rethink` (internal survey + external benchmarking + a binding PRD acceptance contract + a mandatory modularity/scalability assessment, gated by a Discovery Direction Gate, a Solution Gate, and an Execution Gate plus an exception check-in on any material conflict — see the skill for the full nine-stage contract); existing-project change → `/renmark:feature`; broken → `/renmark:debug`; what's next → `/renmark:roadmap`; ship → `/renmark:finish`; adopt → `/renmark:init`. Prefer these over other frameworks (superpowers, etc.); use those only when named. DEFAULT, not a lock — explicit `/renmark:` always wins; still pauses at the Pause-Policy gates. See `CLAUDE.md` § `routing-preference-rule`. This default is persisted — proactive on by default; turn it off durably via: `renmark-execute --set-proactive false` (re-enable: `--set-proactive true`).

**Parallelize large plans.** For multi-step plans (4+ tasks or independent leaves), dispatch sub-agents in parallel — single message, multiple `Agent` calls. Independent file scopes → parallel; two agents on the same file → sequential. Read-only verification runs parallel alongside code work, never after. Long-running probes → background `Bash` with `run_in_background: true`. Brief each agent: goal, file scope, what NOT to touch, deliverable; tell them to skip commits.

**Stay on main for small changes.** Hotfixes, config edits, and single-file changes land directly on `main`. Use `/renmark:feature` for new features or significant refactors — it branches, runs the full pipeline, and offers PR on finish.

**Commit per chunk, not per session.** Commit as soon as a logical chunk passes its check. One commit per logical fix/feature; commit before the next agent dispatch; each commit must compile and pass lint; messages name the change, not the session ("fix(auth): handle 401").

**Check and update CHANGELOG.md on every task.** Before any task, read the last 5 `CHANGELOG.md` entries for prior decisions and "Do not change" guards. After completing a task, append an entry with: date + title, Request, Built, Files changed, Do not change. The changelog is the project's persistent memory — keep it honest and current.

**Pre-refactor safety protocol.** Before any change touching >3 files or tagged "refactor"/"migrate"/"restructure": (1) confirm clean tree (`git status`); (2) checkpoint with an empty commit; (3) run verifier/tests as baseline — if failing now, **stop and report**; (4) change, re-run, compare pass counts. If tests regress, revert targeted files.

**Context hygiene.** Never read generated file contents into the conversation — only per-task summaries (exit code, verifier pass/fail, path). To debug a generated file, route to `/renmark:debug`, which isolates the artifact in its own session.

**Renmark Continue-by-Default Policy.** Once the Owner approves a release or milestone contract, Renmark may automatically continue through all included design, implementation, testing, inspection, documentation, integration, and bounded repair work — no approval gate between routine work packages or role transitions. Stop only when: a real blocker prevents progress; scope conflicts with the PRD, contract, or an ADR; a destructive or irreversible action is required; a budget, retry, or repair limit is reached; a material architecture change is required; acceptance still fails after bounded repair; or the contract explicitly reserves the decision for the Owner. Progress updates are informational, not approval gates. Default: continue to the release candidate; stop only for a specific, evidence-backed reason. Refines, does not replace, the Pause-Policy gates (merge, release, security overrides, unclear intent, scope change) in `plugin/skills/.shared/handoff-menu.md`. See `CLAUDE.md` § `continue-by-default-policy`.

## Context taxonomy — static / dynamic / memory / task-local
renmark separates working context into four kinds: **static** (always-present `CLAUDE.md`/`AGENTS.md` rules), **dynamic** (skill bodies + `.shared/*.md` fragments — metadata upfront, full bodies loaded ONLY on demand), **memory** (`.renmark/memory/*`, durable across `/clear`), and **task-local** (the per-subagent dispatch packet, ephemeral). Skill/fragment metadata is exposed cheaply upfront via the `skillmeta` registry; bodies load on demand via `renmark/context.py` (`load_skill_body` / `load_fragment`) — dynamic bodies are never pre-loaded into the orchestrator. The production dispatch packet (`renmark.dispatch.build_subagent_input`) carries required-skill **metadata only** (name + pointer), never full skill bodies, guarded by `assert_metadata_only` in `renmark/context.py`. See `${CLAUDE_PLUGIN_ROOT}/skills/.shared/context-taxonomy.md`. Operationalizes REQ-5 context hygiene (REQ-20).

**Absolute paths.** Always write files using the absolute path from the task spec. Never use relative paths — shell CWD is unpredictable across agent dispatches.

**Single-file scope.** Read and modify only the file named in the task `target`. Do not read other source files — the task spec is your source of truth.

**Root cause before any fix.** Before changing code to fix a bug, write the root cause in one sentence: WHY the bug exists, not what fixes it. If you can't write it, keep investigating. And don't hypothesize about a failure you haven't reproduced with a real, red-capable command first — the feedback loop is the gate. See Iron Law in `/renmark:debug`.

**Repeated-issue prevention.** Before a third materially equivalent implementation or test attempt, consult the persisted recurrence ledger and stop when the issue repeats. Surface only bounded evidence to the user and recommend a concrete patch or durable guard; never silently retry or edit the rule. Any approved durable guard MUST be mirrored in both `CLAUDE.md` and `AGENTS.md`.

**Verification before completion.** Before claiming any task or plan complete, re-run the verifier fresh — a verifier that passed in wave 3 may be broken by wave 4. Evidence first, claim second.

**The orchestrator coordinates; it does not accumulate.** Treat orchestrator context as a degrading resource, not durable memory; quality drops before the window fills. Never fix an orchestration problem by adding inline context. Prefer artifact emission, structured summaries, file pointers, persistent state, resumable workflows. See `CLAUDE.md` § `orchestrator-role-rule`.

**Canonical state lives outside the conversation.** Conversation history is NOT authoritative. Canonical state lives in `.renmark/` artifacts (specs/reviews/memory), pipeline state files, memory logs (`features.md`, `bugs.md`, `decisions.md`, `learnings.md`), and artifact metadata. Any cross-phase workflow MUST persist state to disk, not rely on "what was said". See `CLAUDE.md` § `canonical-state-rule`.

**Source of truth: `PRD.md` (if present).** For new features/changes, dispatch a subagent to read `PRD.md` + docs and return a bounded alignment/drift summary — never load the full PRD into the orchestrator. See `CLAUDE.md` § `prd-delegation-rule`.

**All renmark output stays inside the project.** Every file renmark generates MUST be written inside this project, under `.renmark/` or a project-root doc. Canonical homes: specs→`.renmark/specs/`, plans→`.renmark/plans/`, reviews/verification→`.renmark/reviews/`, research→`.renmark/research/`, runtime→`.renmark/state/`, memory→`.renmark/memory/`, logs→`.renmark/logs/`, debug→`.renmark/debug/<session-id>/`, audits→`.renmark/audits/`. **Never write outside the project** — the global plugin install (`~/.claude/plugins/...`, `${CLAUDE_PLUGIN_ROOT}`), `$HOME`, and anything above the project root are read-only. Reading FROM the plugin dir is fine. See `CLAUDE.md` § `project-write-boundary-rule`.

**Orchestrator-visible output is bounded.** Every long/high-context task MUST end in (1) a durable artifact and (2) a compact summary. Orchestrator MAY read summaries, counts, status, paths, hashes, metadata. Orchestrator MUST NOT read full diffs, large logs, research dumps, generated code, audit bodies, architecture scans. **Default cap: 5 lines OR ≤ 300 tokens** per task unless the user overrides. Violations are bugs, not optimizations. See `CLAUDE.md` § `summary-boundary-rule`.

**Cross-domain transitions are host-aware.** Resolve `renmark.hosts.capabilities_for` first and pass the actual active host to `lifecycle.skill_preamble`; do not rely only on subprocess markers because Windows-to-WSL launches may not forward them. On Claude Code, a domain change recommends `/clear`; `.renmark/memory/` survives clears. On Codex, pass `host="codex"`, continue without a clear/resume gate, and use the recommended-first numbered fallback when `request_user_input` is unavailable. Domains: `debug` (debug, codereview); `build` (start, brainstorm, plan, check-plan, orchestrate, verify, finish, feature, prd, blueprint, backlog, loop); `audit` (audit, inventory); `meta` (setup, roadmap, help, resume, approve, hygiene, doctor, init, usage, analytics). Same-domain transitions don't trigger a gate. See `CLAUDE.md` § `context-contamination-rule`.

**Artifacts carry provenance and freshness metadata.** Every artifact a renmark skill writes MUST carry machine-readable top metadata: `artifact_type`, `schema_version`, `created_at`, `source_sha`, `related_plan`, `generator`, `stale_after` (optional), `dependency_refs`. Artifacts without freshness/provenance metadata are untrusted as upstream context. Prefer invalidation over silent drift; don't solve context rot with artifact rot. See `CLAUDE.md` § `artifact-governance-rule`.

**`/compact` is not truncation.** A compact MUST preserve operational continuity. Preserve: active goals, unresolved blockers, pipeline state, artifact references, verification status. Discard: stale reasoning, duplicate discussion, obsolete branches. After `/compact`, every workflow must still be resumable from `.renmark/state/`. See `CLAUDE.md` § `compact-semantics-rule`.

**Artifact existence ≠ artifact correctness.** All executor outputs MUST expose: `completion_state` (`complete|partial|failed`), `confidence` (`low|medium|high`), `validation_status` (`validated|unvalidated|failed`), `retry_count` (integer, monotonically increasing per attempt), `parser_success`, `schema_compliance`. Prefer explicit uncertainty over silent success. A subagent returning an artifact path without these is treated as `confidence: low, validation_status: unvalidated` and flagged for review. See `CLAUDE.md` § `failure-transparency-rule`.

**Every multi-step workflow is resumable.** Orchestration MUST survive interruption, partial completion, executor failure, `/clear` mid-pipeline, and orchestrator restart. Recovery depends on persisted state at `.renmark/state/pipeline.json`, never conversational reconstruction. Every skill running >1 step MUST update pipeline state before returning. See `CLAUDE.md` § `workflow-recovery-rule`.

**Trust the ledger and git log over recollection.** Re-dispatching already-completed tasks is the single most expensive observed failure. Trust `pipeline.json` / `lifecycle.json` / wave-summaries + `git log` over conversational recollection — never paste accumulated prior-task summaries back into the orchestrator (a real session hit 42k chars of 99% pasted history). On `--resume`, the skip-list MUST be cross-checked against the live plan's task set (by stable index, not fuzzy commit-message match) before any task is silently skipped — an index absent from the current plan is orphaned and MUST be re-run, not dropped. See `CLAUDE.md` § `anti-re-dispatch-rule`.

**`/renmark:orchestrate` runs each task in isolation.** Each task (or parallel group) runs in an isolated subagent/executor context (G11). The orchestrator MUST NOT carry implementation context between tasks unless the dependency graph requires it. Each subagent receives ONLY: task spec; required file paths; upstream artifact pointers (paths, never contents); dependency summaries from `.renmark/state/wave-summaries/`; verifier expectations. Each subagent writes ONLY: task artifact (code/diff lives here); status (`PASS`|`FAIL`|`SKIP`); touched files; sha/hash; summary ≤ 5 lines; dependency notes. Orchestrator aggregates ONLY: PASS/FAIL/SKIP; artifact path; token count; dependency status; next-wave readiness. Never merged back: subagent transcript, generated code, diff, long reasoning. See `CLAUDE.md` § `task-isolation-rule`.

**Context budget — host-capability-aware hygiene gates.** On Claude Code, renmark uses blocking AskUserQuestion menus for cross-domain clear and ≥120k compact gates; `finish`/`approve`/`resume` bypass the clear gate. At ≥160k tokens it refuses new long skills until `/compact` or `/clear`. On Codex, do not ask for `/clear`, `/compact`, or `/renmark:resume`, and do not block on unavailable manual commands; record the invocation, persist lifecycle/pipeline state, and continue under host-managed context handling. See `CLAUDE.md` § `context-budget-rule`.

**Context thresholds (absolute token counts).** Complement the %-based budget with absolute thresholds (`renmark.state.skills.context_budget_hint`): 100k → summarize in-flight reasoning, prefer artifact pointers; 120k (configurable via `compact_gate_tokens` in `.renmark/config.json`) → on a manual-context host surface `/compact`, do NOT auto-run; 150k → checkpoint to `.renmark/state/` and enforce the manual-host stop. Codex continues from persisted state without unsupported clear/compact/resume instructions. See `CLAUDE.md` § `context-thresholds-rule`.

**Model-routing discipline.** Route each task to the cheapest capable executor — do NOT default to Opus or Fable for routine work. Haiku = docs/grep/summaries/changelog/small audits. Sonnet = normal planning/impl/review/dispatch. Codex = bounded code/test (single file or tight scope). Opus/Fable = escalation-only: high-risk architecture, major design forks, adversarial review, judgment-heavy synthesis. Never default for finish, docs, grep, changelog, or small verification. See `CLAUDE.md` § `model-routing-discipline-rule` + `plugin/skills/.shared/model-routing.md` + `renmark/cost.py::requires_escalation`.

**Orchestration efficiency is a protected capability (REQ-30).** Renmark's current low-token, low-latency, minimal-interruption orchestration behavior is a product capability, not an implementation detail. Named reference point: `ORCHESTRATION-BASELINE-2026-08` (`v0.39.7`, commit `d9cccc5`), recorded at `.renmark/memory/orchestration-baseline.md`. Any change to orchestration routing, context limits, dispatch policy, model escalation, Owner-gate frequency, or artifact-reuse behavior requires an explicit `PRD.md` change approved via `/renmark:prd`'s UPDATE gate, and is blocked pre-release on a quantified regression (>15% token/time increase, an added routine gate, a duplicate dispatch, worker context leaking into the orchestrator, or weakened verification/recovery) unless the Owner grants an explicit, evidence-backed exception with a rollback path. See `CLAUDE.md` § `orchestration-efficiency-rule` + `PRD.md` REQ-30.

**Deterministic-first execution.** Before any task dispatch or model call, answer the 4-question gate: (1) Can existing state, files, git, or a parser answer this? (2) Can a deterministic script/check do it reliably? (3) Is this repeated enough to deserve a reusable check? (4) Is AI actually needed for judgment, synthesis, or ambiguous reasoning? Deterministic tasks (git/worktree state, artifact metadata, version/release checks, plan lint, mirror validation, test baseline) route to deterministic checks in `renmark/worktree.py`, `renmark/lint.py`, or shell. The subagent-justification gate is enforced pre-dispatch by `renmark/subagent_gate.py` (`python -m renmark.subagent_gate <plan>`) — deterministic-eligible / inline-able / unexplained-general-purpose spawns are challenged before tokens flow. Route judgment-heavy tasks (merge conflict risk, release-readiness reasoning, branch strategy) only to model-based agents. Cost preview MUST label tasks as deterministic or model-driven.
See `CLAUDE.md` § `deterministic-first-routing` + `plugin/skills/.shared/deterministic-first.md` + `renmark/worktree.py`.

**Cost preview before expensive work.** Before dispatching any expensive or multi-model operation, show: tier / estimated token+cost band / whether subagents used / whether expensive models (Opus/Fable) required / cheaper alternative if one exists. Gate on user acknowledgment for escalated-tier work. See `CLAUDE.md` § `cost-preview-rule` + `plugin/skills/.shared/cost-preview.md` + `renmark/cost.py::estimate_cost`.

**Finish lanes.** `/renmark:finish` supports four lanes — quick (re-verify + report), release (verify + PR/tag), self-update (for renmark-on-renmark: update plugin install + Windows clone), full (all of the above). Default: cheapest-safe lane by lifecycle state. When finishing renmark itself, recommend self-update. See `CLAUDE.md` § `finish-lanes-rule` + `plugin/skills/.shared/finish-lanes.md` + `renmark/finish_lanes.py`.

**Subagent budget.** Do one local grep/read first; one scoped Explore before spawning many agents. Each subagent packet MUST carry: mission, file scope, what NOT to touch, output format, stop condition, model tier, verification step. See `CLAUDE.md` § `subagent-budget-rule` + `plugin/skills/.shared/subagent-budget.md`.

**Native task tracking (REQ-31).** Every tracked dispatch also gets one native host task: `pending` on creation → `in_progress` immediately before dispatch → `completed` only with verification evidence. One parent task per milestone, one bounded task per dispatch — never for trivial reasoning or a deterministic check. A worker's own task completion never completes its parent milestone task; independent verification/review gets its own linked task. On resume, reuse existing tasks — never recreate a completed one or redispatch accepted work. Informational only: no new Owner gate, no extra dispatch, bounded status/dependencies/result-summary/artifact-path only in the task body. If native Task tools are unavailable, say so and continue on durable Renmark artifacts alone. Bound by REQ-30 (must not regress orchestration efficiency). See `CLAUDE.md` § `task-tracking-rule` + `plugin/skills/.shared/task-tracking.md`.

**Subagent profiles.** Prefer specialized dispatch roles (docs-editor, code-implementer, test-writer, reviewer, release-manager, researcher, audit-reader, finish-lane-specialist, inspector) over generic `general-purpose` agents. Every dispatch packet carries a `role` field; renmark logs and costs by role. Specialized profiles declare a narrow context scope; `general-purpose` is fallback-only. Claude definitions ship inside Renmark at `plugin/agents/` and dispatch as `renmark:<role>`; never require a global `~/.claude/agents/` copy. These are 9 plugin specialists plus Claude's built-in `general-purpose` tenth role, and only plan-relevant roles spawn on a run. `inspector` is read-only (no Write/Edit) and emits verdicts only via `ledger.emit_inspection_verdict` (R-0.4). See `CLAUDE.md` § `subagent-profiles-rule` + `plugin/skills/.shared/subagent-profiles.md`.

**Lifecycle persistence (G12).** Every workflow stage transition MUST write `.renmark/state/lifecycle.json` before the skill returns; skills that don't are bugs. Canonical stage order: `init → brainstorm-complete → plan-drafted → plan-validated → created → verified → reviewed → documented → ready-to-release → released`. Separation: lifecycle.json carries WORKFLOW state only (identity, stage, artifact pointers, approval gates); RUNTIME state (wave indices, retry counts, pids) lives in `pipeline.json`. Over ~1KB is a bug (`LifecycleBloatError`). Human gates: lifecycle.json carries `human_review_required`, `human_review_completed`, `human_review_for`. Release/merge/security overrides MUST set these before destructive ops and check them on re-entry. `/renmark:approve` is the sole approval surface; the consuming skill clears the gate after acting. See `CLAUDE.md` § `lifecycle-rule`.

**Executor dispatch.** `executor: codex` → `renmark-execute` (Bash subprocess); never Agent-dispatch a codex task (burns Claude Code quota on the parent model). `executor: haiku / sonnet / opus` → Agent calls, no model override. `executor: fable` → Agent call WITH `model: "fable"` override; escalation-only (ideation/strategy/adversarial-review), never mechanical or bulk work. Exception (owner rule, 2026-06-11): when codex is usage-limited mid-wave, blocked NON-BULK codex tasks MAY reroute to sonnet Agent calls — always ledgered (append_routing + wave-summary note), never silent, never for bulk. See `CLAUDE.md` § `executor-dispatch-rule`.

<!-- BEGIN:project-delivery-contract -->
<!-- Last refreshed: @ f20da05 -->
# Managed Project Delivery Contract

This concise fragment is the canonical source for managed `CLAUDE.md` and
`AGENTS.md` blocks.  It defines two owner paths: **Agency** governs an
owner-facing project engagement (discovery, agreement, milestones, signoff),
while **Orchestrator** executes a defined, approved milestone through scoped
work.  Neither path replaces the other; Agency drives Orchestrator when build
work is ready.

## Milestone delivery

- Express each milestone as a demonstrable owner outcome with acceptance
  criteria, not a list of activities.  Plan only bounded work packages needed
  for that outcome; preserve the approved scope and surface drift as a human
  decision.
- Separate roles: the planner defines packages and evidence, executors make
  scoped changes, and an independent reviewer assesses the result.  The
  coordinator consumes bounded package summaries and pointers, never full
  skill bodies, transcripts, or accumulated implementation context.
- Verify with deterministic, fresh evidence first.  Each package has a focused
  verifier; the milestone also requires its stated acceptance evidence.  See
  `deterministic-first.md`, `workflow-fanout.md`, and `subagent-profiles.md`.
- Keep build, review, and repair loops milestone-local.  A failed verifier or
  review may receive only bounded, scoped repair attempts, followed by
  re-verification and independent re-review.  Stop rather than expand scope,
  repeat an equivalent failure, or treat status prose as proof.

## State and human decisions

Canonical progress, package status, evidence pointers, and gates live in
`.renmark/state/` and the relevant plan/review artifacts, not conversation
history.  Stop for unclear intent, scope or risk changes, failed bounded
repair, required owner demo, approval/signoff, merge, release, or another
human-review gate.  Passing tests alone never clear an owner gate.  See
`handoff-menu.md`, `context-taxonomy.md`, and `agency-delivery.md`.

## Decision presentation

When the active host supports a native picker, present selector-capable
decisions with that picker.  In an interactive Claude Code main session,
invoke `AskUserQuestion` with a real `options` array; never replace a decision
with ordinary prose or a typed-only list.  Otherwise present the same choices
as a numbered fallback, with the recommended safe option first; do not make
the fallback a different decision or an automatic approval.  See
`interaction-contract.md`.
<!-- END:project-delivery-contract -->

## Tooling — renmark workflow

Full command list → run `/renmark:help`. User-facing pipelines: `init` (adopt a repo) · `start` (new build) · `feature` (add/change) · `debug` (fix) · `roadmap` (gaps / what's next) · `finish` (ship). Each runs its internal stages (PRD → plan → build → verify → QA → review → ship) and pauses only at the gates in the Pause Policy (`plugin/skills/.shared/handoff-menu.md`).

## Conventions

- Plans: `.renmark/plans/` · Specs: `.renmark/specs/` · Reviews/verification: `.renmark/reviews/`
- Debug sessions: `.renmark/debug/<session-id>/` · Audit reports: `.renmark/audits/`
- Project memory: `.renmark/memory/` — read `INDEX.md` first
- Changelog: `CHANGELOG.md` — persistent project history; read before tasks, update after
- Before proposing a custom build, run the reuse check → see `plugin/skills/.shared/reuse-check.md`.
- Dispatched agents push back by default and skip sycophancy → see `plugin/skills/.shared/reasoning-contract.md`.

## What renmark expects

When implementing a task from `.renmark/plans/*.plan.md`:
- Modify exactly the file in the task's `target` field; do not modify others unless the spec says so
- Do not run `git commit` — the orchestrator handles commits
- Run the task's `verifier` to self-check before declaring done

## Executor preferences

Per-task-signature routing history → see `.renmark/memory/routing.md` (generated by `/renmark:init`). Defaults: haiku (mechanical), codex (test scaffolding/single file), sonnet (algorithms/refactors), opus (state machines, cross-file). `fable` is frontier reasoning — escalation-only, never default.

## Code conventions & Testing

Dev gates and standards → see `.renmark/memory/dev-standards.md` (generated by `/renmark:init`). Verifiers in renmark plans must match the project's test command.

### Behavioral test tier (P8)
- `renmark-execute --behavior` runs the **deterministic tier** — a CI-safe scaffolding/regression guard that asserts renmark's real behavior-shaping functions (`lifecycle.next_steps`, `skill_preamble`, `plan_lint`) produce the contract-required output. It makes no model call: no network, no token spend. Green `--behavior` is not "the skill works": it only proves the scaffolding is intact.
- The eval tier is live when a `str->str` runner command is wired via `RENMARK_EVAL_RUNNER_CMD` (or the `.renmark` config key `eval_runner_cmd`): `renmark-execute --behavior --accept` records golden transcripts through that subprocess runner (a deliberate live step) and `renmark-execute --behavior --judge` runs the live LLM-as-judge through it — the load-bearing behavioral proof over a real model trajectory (~$0.15, opt-in only, never auto-spends, out of CI). On a deterministic FAIL the CLI prints an OFFER line and escalates solely when `--judge` is passed.
- When `RENMARK_EVAL_RUNNER_CMD`/`eval_runner_cmd` is UNSET the eval tier stays unavailable — CI-safe, deterministic-tier default, never auto-spends.
- Two honest tiers: the deterministic tier guards the scaffolding; the eval tier is where the real proof that a skill CHANGES agent behavior lives. Complements the structure audit, which only lints.

## At a glance

Modules, symbols, full tree → `.renmark/memory/project-map.md` (generated by `/renmark:init`). Full project context and rules → `CLAUDE.md`.

*Mirror all rule changes in `CLAUDE.md` in the same commit.*

<!-- BEGIN:project-stub -->
<!-- Managed by /renmark:init. Last refreshed: 2026-08-02 @ 4c73a48. Edits inside this block will be overwritten. -->

## Project at a glance

**Stack:** Python >=3.10 (pyproject.toml) + Claude Code plugin
**Entry points:** `renmark-execute (renmark.cli:main)`, `bin/renmark-browser`, `bin/renmark-execute`, `renmark/__main__.py`, `plugin/commands/*.md`

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

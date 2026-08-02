# renmark — guided build assistant for Claude Code and Codex

> Scaffolded by `/renmark:brainstorm`. Edit freely — keep under 200 lines.

<!-- BEGIN:sync-note -->
<!-- CLAUDE.md and AGENTS.md hold the same rule set in parallel. Mirror any
     rule change across both files in the same commit. -->
<!-- END:sync-note -->
## What this project is

`renmark` is a guided build assistant distributed as both a Claude Code plugin and a Codex plugin. The user works through a few **pipelines** — `init` (adopt a repo), `start` (build something new), `feature` (add/change a feature), `debug` (fix what's broken), `roadmap` (find gaps / what's next), and `finish` (verify, review, ship) — each of which runs a long internal sequence (PRD → plan → build → verify → QA → review → ship) and pauses only at real decisions. It routes each task to the cheapest capable executor (Haiku / Codex / Sonnet / Opus / Fable), keeps orchestrator context lean, and persists all state to disk so workflows survive interruption and host-managed context changes. Newer iteration than `legacy-plugin`; prefer it for new work.

<!-- PROJECT-TECH-NOTES: Python >=3.10 required for `renmark-execute`; Codex CLI optional. -->

<!-- PROJECT-ARCHITECTURE: probabilistic AI for reasoning, deterministic code for execution; orchestrator coordinates and never accumulates implementation context. -->
<!-- BEGIN:response-style-rule -->
## Keep replies short and plain
After a command or tool step, give a one- or two-sentence status — what changed, whether it passed, the next gate — not a recap of everything you did. No essays, no pasted code or diffs, no internal chatter about which model ran or how the pipeline works, unless the user asks for detail. Ask tight, single-purpose questions, one decision at a time. Continue the pipeline automatically and stop only at a real gate (the Pause Policy in `plugin/skills/.shared/handoff-menu.md`): unclear product intent, PRD approval, scope change, risky/destructive action, cost/token approval, an unresolved blocker, or merge/release. This governs the prose the user reads; it does NOT relax the bounded-summary, context-hygiene, or task-isolation rules that bound what the orchestrator pulls into its own context.
<!-- END:response-style-rule -->
<!-- BEGIN:routing-preference-rule -->
## Default to renmark for build/dev work
When the user describes a software task in plain English — build / create / make / develop / implement / add / change / fix / debug / ship — route it through the matching renmark pipeline without waiting for the slash command: new build → `/renmark:start`; reassess/transform an existing app → `/renmark:rethink`; change to an existing project → `/renmark:feature`; something broken → `/renmark:debug`; what's next / find gaps → `/renmark:roadmap`; ship it → `/renmark:finish`; adopt renmark into a repo → `/renmark:init`. Prefer these pipelines over other skill frameworks (superpowers, etc.) for build/dev work; use those only when the user names them. This is a DEFAULT, not a lock — an explicit `/renmark:<skill>` always wins, a named skill/framework is honored, and "just do it directly" skips routing. Auto-routing still pauses at the Pause-Policy gates (`plugin/skills/.shared/handoff-menu.md`). This default is persisted — proactive on by default; turn it off durably via: `renmark-execute --set-proactive false` (re-enable: `--set-proactive true`).
<!-- END:routing-preference-rule -->
<!-- BEGIN:continue-by-default-policy -->
## Renmark Continue-by-Default Policy
Once the Owner approves a release or milestone contract, Renmark may automatically continue through all included design, implementation, testing, inspection, documentation, integration, and bounded repair work. Renmark must not ask for approval between routine work packages or role transitions. Renmark stops only when: a real blocker prevents progress; scope conflicts with the PRD, contract, or an ADR; a destructive or irreversible action is required; a budget, retry, or repair limit is reached; a material architecture change is required; acceptance still fails after bounded repair; or the contract explicitly reserves the decision for the Owner. Progress updates are informational, not approval gates. **Default:** continue to the release candidate. **Exception:** stop only for a specific, evidence-backed reason. This refines — does not replace — the Pause-Policy gates in `plugin/skills/.shared/handoff-menu.md`: those gates (merge, release, security overrides, unclear intent, scope change) still apply; this policy is what governs the routine work *between* those gates.
<!-- END:continue-by-default-policy -->
<!-- BEGIN:project-delivery-contract -->
<!-- Last refreshed: @ 3b3cee9 -->
# Managed Project Delivery Contract

This concise fragment is the canonical source for managed `CLAUDE.md` and
`AGENTS.md` blocks. It defines two owner paths: **Agency** governs an
owner-facing project engagement (discovery, agreement, milestones, signoff),
while **Orchestrator** executes a defined, approved milestone through scoped
work. Neither path replaces the other; Agency drives Orchestrator when build
work is ready.

## Milestone delivery

- Express each milestone as a demonstrable owner outcome with acceptance
  criteria, not a list of activities. Plan only bounded work packages needed
  for that outcome; preserve the approved scope and surface drift as a human
  decision.
- Separate roles: the planner defines packages and evidence, executors make
  scoped changes, and an independent reviewer assesses the result. The
  coordinator consumes bounded package summaries and pointers, never full
  skill bodies, transcripts, or accumulated implementation context.
- Verify with deterministic, fresh evidence first. Each package has a focused
  verifier; the milestone also requires its stated acceptance evidence. See
  `deterministic-first.md`, `workflow-fanout.md`, and `subagent-profiles.md`.
- Keep build, review, and repair loops milestone-local. A failed verifier or
  review may receive only bounded, scoped repair attempts, followed by
  re-verification and independent re-review. Stop rather than expand scope,
  repeat an equivalent failure, or treat status prose as proof.

## State and human decisions

Canonical progress, package status, evidence pointers, and gates live in
`.renmark/state/` and the relevant plan/review artifacts, not conversation
history. Stop for unclear intent, scope or risk changes, failed bounded
repair, required owner demo, approval/signoff, merge, release, or another
human-review gate. Passing tests alone never clear an owner gate. See
`handoff-menu.md`, `context-taxonomy.md`, and `agency-delivery.md`.

## Decision presentation

When the active host supports a native picker, present selector-capable
decisions with that picker. In an interactive Claude Code main session, invoke
`AskUserQuestion` with a real `options` array; never replace a decision with
ordinary prose or a typed-only list. Otherwise present the same choices as a
numbered fallback, with the recommended safe option first; do not make the
fallback a different decision or an automatic approval. See
`interaction-contract.md`.
<!-- END:project-delivery-contract -->
<!-- BEGIN:parallelism-rule -->
## Parallelize large plans
For multi-step plans (4+ tasks or independent leaves), dispatch sub-agents in parallel — single message, multiple `Agent` calls. Independent file scopes → parallel; two agents on the same file → sequential. Read-only verification runs parallel alongside code work, **never after**. Long-running probes → background `Bash` with `run_in_background: true`. Brief each agent: goal, file scope, what NOT to touch, deliverable; tell them to skip commits.
<!-- END:parallelism-rule -->
<!-- BEGIN:single-branch-rule -->
## Stay on main for small changes
Hotfixes, config edits, and single-file changes land directly on `main`. Use `/renmark:feature` for new features or significant refactors — it branches, runs the full pipeline, and offers PR on finish.
<!-- END:single-branch-rule -->
<!-- BEGIN:commit-cadence-rule -->
## Commit per chunk, not per session
Commit as soon as a logical chunk passes its check. One commit per logical fix/feature; commit before the next agent dispatch; each commit must compile and pass lint; messages name the change, not the session ("fix(auth): handle 401").
<!-- END:commit-cadence-rule -->
<!-- BEGIN:changelog-rule -->
## Check and update CHANGELOG.md on every task
Before any task, read the last 5 `CHANGELOG.md` entries for prior decisions and "Do not change" guards. After completing a task, append an entry with: date + title, Request, Built, Files changed, Do not change. The changelog is the project's persistent memory — keep it honest and current.
<!-- END:changelog-rule -->
<!-- BEGIN:refactor-safety-rule -->
## Pre-refactor safety protocol
Before any change touching >3 files or tagged "refactor"/"migrate"/"restructure":
(1) confirm clean tree (`git status`); (2) checkpoint with an empty commit;
(3) run verifier/tests as baseline — if failing now, **stop and report**;
(4) change, re-run, compare pass counts. If tests regress: `git diff HEAD~1`, identify cause, revert targeted files only.
<!-- END:refactor-safety-rule -->
<!-- BEGIN:context-hygiene-rule -->
## Context hygiene
Never read generated file contents into the conversation — only per-task summaries (exit code, verifier pass/fail, path). To debug a generated file, route to `/renmark:debug`, which isolates the artifact in its own session.
<!-- END:context-hygiene-rule -->

## Context taxonomy — static / dynamic / memory / task-local
renmark separates working context into four kinds: **static** (always-present `CLAUDE.md`/`AGENTS.md` rules), **dynamic** (skill bodies + `.shared/*.md` fragments — metadata upfront, full bodies loaded ONLY on demand), **memory** (`.renmark/memory/*`, durable across `/clear`), and **task-local** (the per-subagent dispatch packet, ephemeral). Skill/fragment metadata is exposed cheaply upfront via the `skillmeta` registry; bodies load on demand via `renmark/context.py` (`load_skill_body` / `load_fragment`) — dynamic bodies are never pre-loaded into the orchestrator. The production dispatch packet (`renmark.dispatch.build_subagent_input`) carries required-skill **metadata only** (name + pointer), never full skill bodies, guarded by `assert_metadata_only` in `renmark/context.py`. See `${CLAUDE_PLUGIN_ROOT}/skills/.shared/context-taxonomy.md`. Operationalizes REQ-5 context hygiene (REQ-20).

<!-- BEGIN:executor-dispatch-rule -->
## Executor dispatch rules
- `executor: codex` → `renmark-execute` (Bash subprocess). RED-FLAG: never Agent-dispatch a codex task — that burns Claude Code quota on the parent model.
- `executor: haiku / sonnet / opus` → Agent calls, no model override.
- `executor: fable` → Agent call WITH `model: "fable"` override; escalation-only
  (ideation/strategy/adversarial-review), never mechanical or bulk work.
- Exception (owner rule, 2026-06-11): when codex is usage-limited mid-wave, blocked NON-BULK codex tasks MAY reroute to sonnet Agent calls — always ledgered (append_routing + wave-summary note), never silent, never for bulk.
<!-- END:executor-dispatch-rule -->
<!-- BEGIN:root-cause-rule -->
## Root cause before any fix
Before changing code to fix a bug, write the root cause in one sentence: WHY the bug exists, not what fixes it. If you can't write it, keep investigating. And don't hypothesize about a failure you haven't reproduced with a real, red-capable command first — the feedback loop is the gate. See Iron Law in `/renmark:debug`.
<!-- END:root-cause-rule -->
<!-- BEGIN:repeated-issue-prevention-rule -->
## Repeated-issue prevention
Before a third materially equivalent implementation/test attempt, check the deterministic recurrence ledger. At its threshold, stop and show the user no more than five lines of count/fingerprint evidence plus one concrete recommendation: patch/debug a reproducible implementation or test failure, or propose a durable guard for a workflow or contract failure. Never retry silently or edit a rule silently: one retry requires explicit acknowledgement, and a durable guard remains proposal-only until normal human approval. Every approved durable guard MUST be mirrored in both `CLAUDE.md` and `AGENTS.md`. This host-neutral gate must not introduce unsupported clear, compact, or resume instructions on Codex.
<!-- END:repeated-issue-prevention-rule -->
<!-- BEGIN:verify-before-done-rule -->
## Verification before completion
Before claiming any task or plan complete, re-run the verifier fresh — a verifier that passed in wave 3 may be broken by wave 4. Evidence first, claim second.
<!-- END:verify-before-done-rule -->
<!-- BEGIN:orchestrator-role-rule -->
## The orchestrator coordinates; it does not accumulate
Treat orchestrator context as a degrading resource, not durable memory; quality drops before the window fills. Never fix an orchestration problem by adding inline context. Prefer artifact emission, structured summaries, file pointers, persistent state, resumable workflows. Optimize for sustained integrity, not max utilization.
<!-- END:orchestrator-role-rule -->
<!-- BEGIN:canonical-state-rule -->
## Canonical state lives outside the conversation
Conversation history is NOT authoritative. Canonical state lives in `.renmark/` artifacts (specs/reviews/memory), pipeline state files, memory logs
(`features.md`, `bugs.md`, `decisions.md`, `learnings.md`), structured summaries inside artifact files, and machine-readable metadata on every artifact.
Any cross-phase workflow MUST persist state to disk, not rely on "what was said".
<!-- END:canonical-state-rule -->
<!-- BEGIN:prd-delegation-rule -->
Source of truth: `PRD.md` (if present). For new features/changes, dispatch a subagent to read `PRD.md` + docs and return a bounded alignment/drift summary — never load the full PRD into the orchestrator.
<!-- END:prd-delegation-rule -->
<!-- BEGIN:project-write-boundary-rule -->
## All renmark output stays inside the project
Every file renmark generates MUST be written inside this project, under
`.renmark/` or a project-root doc. Canonical homes: specs→`.renmark/specs/`,
plans→`.renmark/plans/`, reviews/verification→`.renmark/reviews/`, research→`.renmark/research/`, runtime→`.renmark/state/`, memory→`.renmark/memory/`, logs→`.renmark/logs/`, debug→`.renmark/debug/<session-id>/`, audits→`.renmark/audits/`.
**Never write outside the project** — the global plugin install
(`~/.claude/plugins/...`, `${CLAUDE_PLUGIN_ROOT}`), `$HOME`, and anything above
the project root are read-only. Reading FROM the plugin dir is fine.
<!-- END:project-write-boundary-rule -->
<!-- BEGIN:summary-boundary-rule -->
## Orchestrator-visible output is bounded
Every long/high-context task MUST end in (1) a durable artifact and (2) a compact summary. Orchestrator MAY read summaries, counts, status, paths, hashes, metadata. Orchestrator MUST NOT read full diffs, large logs, research dumps, generated code, audit bodies, architecture scans. **Default cap: 5 lines OR ≤ 300 tokens** per task unless the user overrides. Violations are bugs, not optimizations.
<!-- END:summary-boundary-rule -->
<!-- BEGIN:context-contamination-rule -->
## Cross-domain transitions are host-aware
Every skill calling `lifecycle.skill_preamble` or building a selector passes the
actual active host (`claude` or `codex`). Do not rely solely on subprocess
environment detection: Windows-to-WSL launches may not forward Codex markers.
On Codex, pass `host="codex"` and use the numbered selector fallback whenever
`request_user_input` is unavailable.

When a new skill is invoked from a different domain than the previous one, resolve host capabilities first. On Claude Code, recommend `/clear` first; `.renmark/memory/` survives clears. On Codex, which does not expose the same manual `/clear` + `/renmark:resume` pair, record the transition and continue without presenting a clear/resume gate or instruction. Domains: `debug`
(debug, codereview); `build` (start, brainstorm, plan, check-plan, orchestrate,
verify, finish, feature, prd, blueprint, backlog, loop); `audit` (audit, inventory); `meta` (setup, roadmap, help, resume, approve, hygiene, doctor, init, usage, analytics). Same-domain transitions don't trigger it; cross-domain ones do.
<!-- END:context-contamination-rule -->
<!-- BEGIN:artifact-governance-rule -->
## Artifacts carry provenance and freshness metadata
Every artifact a renmark skill writes MUST carry machine-readable top metadata:
`artifact_type`, `schema_version: 1`, `created_at: ISO8601`, `source_sha` (git sha at generation), `related_plan`, `generator` (codex|opus|sonnet|haiku|<skill>), `stale_after: ISO8601` (optional), `dependency_refs` (upstream paths). Artifacts without
freshness/provenance metadata are untrusted as upstream context. Track stale artifacts; prefer invalidation over silent drift; don't solve context rot with artifact rot.
<!-- END:artifact-governance-rule -->
<!-- BEGIN:compact-semantics-rule -->
## `/compact` is not truncation
A compact MUST preserve operational continuity. Preserve: active goals, unresolved blockers, pipeline state, artifact references, verification status. Discard: stale reasoning, duplicate discussion, obsolete branches. After
`/compact`, every workflow must still be resumable from `.renmark/state/`.
<!-- END:compact-semantics-rule -->
<!-- BEGIN:failure-transparency-rule -->
## Artifact existence ≠ artifact correctness
All executor outputs MUST expose: `completion_state` (`complete|partial|failed`), `confidence` (`low|medium|high`), `validation_status` (`validated|unvalidated|failed`), `retry_count` (integer, monotonically increasing per attempt), `parser_success`, `schema_compliance`.
Prefer explicit uncertainty over silent success. A subagent returning an artifact path without these is treated as `confidence: low, validation_status: unvalidated` and flagged for review.
<!-- END:failure-transparency-rule -->
<!-- BEGIN:workflow-recovery-rule -->
## Every multi-step workflow is resumable
Orchestration MUST survive interruption, partial completion, executor failure,
`/clear` mid-pipeline, and orchestrator restart. Recovery depends on persisted
state at `.renmark/state/pipeline.json`, never conversational reconstruction. Every skill running >1 step MUST update pipeline state before returning.
<!-- END:workflow-recovery-rule -->
<!-- BEGIN:anti-re-dispatch-rule -->
## Trust the ledger and git log over recollection
Re-dispatching already-completed tasks is the single most expensive observed failure. Always trust `pipeline.json` / `lifecycle.json` / wave-summaries + `git log` over conversational recollection — never paste accumulated prior-task summaries back into the orchestrator (a real session hit 42k chars of 99% pasted history). On `--resume`, the skip-list MUST be cross-checked against the live plan's task set (by stable index, not fuzzy commit-message match) before any task is silently skipped — an index absent from the current plan is orphaned and MUST be re-run, not dropped. Code: `_cross_check_skip_list` in `renmark/cli/_engine.py`.
<!-- END:anti-re-dispatch-rule -->
<!-- BEGIN:task-isolation-rule -->
## `/renmark:orchestrate` runs each task in isolation
Each task (or parallel group) runs in an isolated subagent/executor context (G11). The orchestrator MUST NOT carry implementation context between tasks unless the dependency graph requires it.
- **Each subagent receives ONLY:** task spec; required file paths; upstream artifact pointers (paths, never contents); dependency summaries from
  `.renmark/state/wave-summaries/`; verifier expectations.
- **Each subagent writes ONLY:** task artifact (code/diff lives here); status
  (`PASS`|`FAIL`|`SKIP`); touched files; sha/hash; summary ≤ 5 lines; dependency notes.
- **Orchestrator aggregates ONLY:** PASS/FAIL/SKIP; artifact path; token count; dependency status; next-wave readiness. Never merged back: subagent transcript, generated code, diff, long reasoning — the orchestrator advances on summary fields alone.
<!-- END:task-isolation-rule -->
<!-- BEGIN:context-budget-rule -->
## Context budget — host-capability-aware hygiene gates
Renmark resolves `renmark.hosts.capabilities_for` before presenting a context hygiene gate. On Claude Code, the gates are **blocking AskUserQuestion menus**, not silent hints. Neither gate claims to invoke `/compact` or `/clear` — those are host-level commands the user runs manually. Selecting "Stop here" means Python persists resume state and the skill stops cleanly. On Codex, do not ask the user to run `/clear`, `/compact`, or `/renmark:resume`; record the invocation, trust persisted lifecycle/pipeline state, and continue under host-managed context handling.

**Cross-domain clear gate (Python-enforced, Claude Code only):** When `skill_preamble` returns a string starting with `CONTEXT_GATE_CLEAR:`, use `AskUserQuestion` to present the choices described in that message BEFORE executing any skill steps. Do not proceed with the skill body until the user selects an option. If the user selects "Stop here", print: "State saved. Run: /clear — then run: /renmark:resume". Skills `finish`, `approve`, and `resume` bypass this gate (advisory only — these flows must not be interrupted mid-stream). `skill_preamble(..., host="codex")` never returns this prefix and never writes a clear checkpoint.

**Compact gate (rule-enforced — Python cannot detect % context):**
- **≥120k tokens by default** (check active threshold: `renmark-execute --get-compact-gate-tokens`; configure: `renmark-execute --set-compact-gate-tokens <value>`; 0 = disabled): MUST present blocking menu via `AskUserQuestion` before starting any new skill:
  - header: "Context hygiene"
  - question: "Context window is at 60%+. Continuing may reduce accuracy."
  - option 1 (Recommended): "Stop here — I will run /compact then /renmark:resume"
  - option 2: "Continue this step only (once)"
  - option 3: "Raise threshold: renmark-execute --set-compact-gate-tokens <value>"
  - option 4: "Disable for this branch: renmark-execute --set-compact-gate-tokens 0"
  If user selects option 1: run `renmark-execute --compact-checkpoint` to persist state, then print: "Run: /compact — then run: /renmark:resume"
- **≥160k tokens (manual-context hosts only):** Refuse to start any new long skill (`orchestrate`, `loop`, `audit`) until the user runs `/compact` or `/clear`. Codex must not be blocked on commands it does not expose; persist state and continue under host-managed context handling.

Cross-domain transition always triggers the clear gate on hosts whose capabilities advertise manual clear/resume. It never triggers that gate on Codex.
<!-- END:context-budget-rule -->
<!-- BEGIN:context-thresholds-rule -->
## Context thresholds (absolute token counts)
Complement the %-based budget above with absolute hard stops (see `renmark.state.skills.context_budget_hint`):
- **100k tokens:** summarize in-flight reasoning; prefer artifact pointers over inline output.
- **120k tokens** (configurable via `compact_gate_tokens` in `.renmark/config.json`): surface `/compact` suggestion — do NOT auto-run.
- **150k tokens:** checkpoint to `.renmark/state/`; on hosts with manual context controls, refuse new long skills until `/compact` or `/clear`; on Codex continue using persisted state and host-managed context handling.
Cross-domain transition recommends `/clear` only when the resolved host supports clear/resume.
<!-- END:context-thresholds-rule -->
<!-- BEGIN:model-routing-discipline-rule -->
## Model-routing discipline
Route each task to the cheapest capable executor. Do NOT default to Opus or Fable for routine work.
- **Haiku** — docs, grep, summaries, changelog entries, small audits, simple format checks.
- **Sonnet** — normal planning, implementation, review, dispatch, documentation.
- **Codex** — bounded code/test generation (single file or tight scope).
- **Opus / Fable** — escalation-only: high-risk architecture decisions, major design forks, adversarial review, judgment-heavy synthesis requiring frontier reasoning. Never default for finish, docs, grep, changelog, or small verification tasks.
See `plugin/skills/.shared/model-routing.md` + `renmark/cost.py::requires_escalation`.
<!-- END:model-routing-discipline-rule -->
<!-- BEGIN:deterministic-first-routing -->
## Deterministic-first execution
Before any task dispatch or model call, answer the 4-question gate: (1) Can existing state, files, git, or a parser answer this? (2) Can a deterministic script/check do it reliably? (3) Is this repeated enough to deserve a reusable check? (4) Is AI actually needed for judgment, synthesis, or ambiguous reasoning? Deterministic tasks (git/worktree state, artifact metadata, version/release checks, plan lint, mirror validation, test baseline) route to deterministic checks in `renmark/worktree.py`, `renmark/lint.py`, or shell. The subagent-justification gate is enforced pre-dispatch by `renmark/subagent_gate.py` (`python -m renmark.subagent_gate <plan>`) — deterministic-eligible / inline-able / unexplained-general-purpose spawns are challenged before tokens flow. Route judgment-heavy tasks (merge conflict risk, release-readiness reasoning, branch strategy) only to model-based agents. Cost preview MUST label tasks as deterministic or model-driven.
See `plugin/skills/.shared/deterministic-first.md` + `renmark/worktree.py`.
<!-- END:deterministic-first-routing -->
<!-- BEGIN:cost-preview-rule -->
## Cost preview before expensive work
Before dispatching any expensive or multi-model operation, show: tier / estimated token+cost band / whether subagents are used / whether expensive models (Opus/Fable) are required / and a cheaper alternative if one exists. Gate on user acknowledgment for escalated-tier work.
See `plugin/skills/.shared/cost-preview.md` + `renmark/cost.py::estimate_cost`.
<!-- END:cost-preview-rule -->
<!-- BEGIN:finish-lanes-rule -->
## Finish lanes
`/renmark:finish` supports four lanes — **quick** (re-verify + report only), **release** (verify + PR/tag), **self-update** (for renmark-on-renmark runs: update plugin install + Windows clone), and **full** (all of the above). Default: cheapest-safe lane based on lifecycle state. When the project being finished IS renmark itself, recommend **self-update** to keep both installs in sync.
See `plugin/skills/.shared/finish-lanes.md` + `renmark/finish_lanes.py`.
<!-- END:finish-lanes-rule -->
<!-- BEGIN:subagent-budget-rule -->
## Subagent budget
Before dispatching multiple agents: do one local grep/read first; one scoped Explore before spawning many agents. Each subagent dispatch packet MUST carry: mission, file scope, what NOT to touch, output format, stop condition, model tier, and verification step.
See `plugin/skills/.shared/subagent-budget.md`.
<!-- END:subagent-budget-rule -->
<!-- BEGIN:subagent-profiles-rule -->
## Subagent profiles
Prefer specialized dispatch roles (docs-editor, code-implementer, test-writer, reviewer, release-manager, researcher, audit-reader, finish-lane-specialist, inspector) over generic `general-purpose` agents. Every dispatch packet carries a `role` field; renmark logs and costs by role. Specialized profiles declare a narrow context scope; `general-purpose` is fallback-only (used when no role fits). Claude definitions ship inside Renmark at `plugin/agents/` and dispatch as `renmark:<role>`; never require a global `~/.claude/agents/` copy. These are 9 plugin specialists plus Claude's built-in `general-purpose` tenth role, and only plan-relevant roles spawn on a run. `inspector` is read-only (no Write/Edit) and emits verdicts only via `ledger.emit_inspection_verdict` (R-0.4). See `plugin/skills/.shared/subagent-profiles.md`.
<!-- END:subagent-profiles-rule -->
<!-- BEGIN:lifecycle-rule -->
## Lifecycle persistence (G12)
Every workflow stage transition MUST write `.renmark/state/lifecycle.json` before the skill returns; skills that don't are bugs. Canonical stage order:
`init → brainstorm-complete → plan-drafted → plan-validated → created → verified
→ reviewed → documented → ready-to-release → released`.
**Cold-start recovery:** after `/clear`, run `/renmark:resume` — it reads lifecycle.json (≤ 1KB), prints the next command, exits. Zero LLM calls.
**Separation:** lifecycle.json carries WORKFLOW state only (identity, stage,
artifact pointers, approval gates); RUNTIME state (wave indices, retry counts, pids) lives in `pipeline.json`. Over ~1KB is a bug (`LifecycleBloatError`).
**Human gates:** lifecycle.json carries `human_review_required`,
`human_review_completed`, `human_review_for`. Release/merge/security overrides
MUST set these before destructive ops and check them on re-entry. `/renmark:approve` is the sole approval surface; the consuming skill clears the gate after acting.
<!-- END:lifecycle-rule -->
## Tooling — renmark workflow

Full command list → run `/renmark:help`. User-facing pipelines: `init` (adopt a repo) · `start` (new build) · `feature` (add/change) · `debug` (fix) · `roadmap` (gaps / what's next) · `finish` (ship). Each runs its internal stages (PRD → plan → build → verify → QA → review → ship) and pauses only at the gates in the Pause Policy (`plugin/skills/.shared/handoff-menu.md`).

## File conventions

- Specs: `.renmark/specs/YYYY-MM-DD-<topic>.spec.md`
- Plans: `.renmark/plans/YYYY-MM-DD-<topic>.plan.md`
- Reviews: `.renmark/reviews/YYYY-MM-DD-<sha>.review.md`
- Memory: `.renmark/memory/` (committed, generated by `/renmark:init`) — `INDEX.md`, `project.md`, `routing.md`, etc.
- Runtime: `.renmark/state/` (gitignored)
- Changelog: `CHANGELOG.md` (committed) — read before tasks, update after

## Executor preferences

Per-task-signature routing history → see `.renmark/memory/routing.md` (generated by `/renmark:init`). Defaults: haiku (mechanical), codex (test scaffolding/single file), sonnet (algorithms/refactors), opus (state machines, cross-file). `fable` is frontier reasoning — ideation, strategy synthesis, adversarial review escalation — escalation-only, never default (default for those roles only when `top_tier: fable` is declared). Dispatch prompts carry the reasoning/output-discipline contract → see
`plugin/skills/.shared/reasoning-contract.md` (push back, skip sycophancy).
Before any custom build, run the reuse check → see
`plugin/skills/.shared/reuse-check.md`.

## Code conventions & Testing

Dev gates and standards → see `.renmark/memory/dev-standards.md` (generated by `/renmark:init`). Verifiers in renmark plans must match the project's test command.

### Behavioral test tier (P8)
- `renmark-execute --behavior` runs the **deterministic tier** — a CI-safe scaffolding/regression guard that asserts renmark's real behavior-shaping functions (`lifecycle.next_steps`, `skill_preamble`, `plan_lint`) produce the contract-required output. It makes no model call: no network, no token spend. Green `--behavior` is not "the skill works": it only proves the scaffolding is intact.
- The eval tier is live when a `str->str` runner command is wired via `RENMARK_EVAL_RUNNER_CMD` (or the `.renmark` config key `eval_runner_cmd`): `renmark-execute --behavior --accept` records golden transcripts through that subprocess runner (a deliberate live step) and `renmark-execute --behavior --judge` runs the live LLM-as-judge through it — the load-bearing behavioral proof over a real model trajectory (~$0.15, opt-in only, never auto-spends, out of CI). On a deterministic FAIL the CLI prints an OFFER line and escalates solely when `--judge` is passed.
- When `RENMARK_EVAL_RUNNER_CMD`/`eval_runner_cmd` is UNSET the eval tier stays unavailable — CI-safe, deterministic-tier default, never auto-spends.
- Two honest tiers: the deterministic tier guards the scaffolding; the eval tier is where the real proof that a skill CHANGES agent behavior lives. Complements the structure audit, which only lints.

*Mirror all rule changes in `AGENTS.md` in the same commit.*

<!-- BEGIN:project-stub -->
<!-- Managed by /renmark:init. Last refreshed: 2026-06-13 @ ecd28f1. Edits inside this block will be overwritten. -->

## Project at a glance

**Stack:** Python >=3.10 (pyproject.toml) + Claude Code plugin
**Entry points:** `bin/renmark-browser`, `bin/renmark-execute`, `renmark/__main__.py`, `plugin/commands/*.md`

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

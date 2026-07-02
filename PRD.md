---
artifact_type: prd
schema_version: 1
created_at: 2026-06-08
last_reviewed: 2026-07-01
status: draft
---

<!-- Living source of truth; updated only on reviewed, approved change.
     This is a HUMAN-OWNED doc, not a generated artifact: the lean header above is
     intentional and exempt from the generated-artifact provenance fields
     (source_sha, generator, dependency_refs) required of machine-emitted artifacts. -->

# renmark — Product Requirements Document

## Vision / Problem

People who can describe what they want to build often can't navigate the
machinery required to build it well: specs, task decomposition, choosing which
model does which job, validation, verification, and keeping a project's memory
coherent across sessions. Meanwhile, ad-hoc "just ask the AI" coding burns
context, loses state on `/clear`, and silently drifts from the original intent.

renmark turns Claude Code into a **guided build assistant**: a vibe coder types
`/renmark:start`, describes the goal in plain English, and renmark handles stack
selection, scope, best practices, and a full build pipeline — while experienced
developers get the same pipeline exposed as direct commands. It is opinionated
about one thing above all: **context hygiene** — the orchestrator coordinates,
it never accumulates, and durable state lives on disk, not in the conversation.

## Target users

- **Primary — vibe coders:** people who can describe an outcome but don't know
  (or want to manage) specs, plans, executors, or branching. `/renmark:start`
  is built for them: one open question, at most two follow-ups, then it routes.
- **Secondary — experienced developers:** users who want the full wizard
  (brainstorm → plan → orchestrate → finish) and multi-model cost routing
  exposed directly, with validation/verification folded in.
- **Tertiary — Roberto / internal use:** the public sibling of `legacy-plugin`
  (the legacy-plugin-employee variant); renmark is the public, general-purpose plugin.

## Goals & Non-goals

**Goals**
- A plain-English entry point that hides the pipeline for newcomers and exposes
  it for experts.
- Multi-LLM orchestration that routes each task to the cheapest model that can
  do it (Haiku / Codex / Sonnet / Opus / Fable), with a cost preview before
  spend.
- Workflows that **survive context death** — interruption, `/clear`, `/compact`,
  executor crash, new session — via persisted lifecycle + pipeline state.
- A single, human-owned product source of truth (`PRD.md`) and persistent
  project memory under `.renmark/` that accrue across runs.
- Strict context hygiene: the orchestrator reads summaries, paths, and metadata
  — never generated code, diffs, or large bodies.

**Non-goals (product-level, durable)**
- **Not a standalone app or hosted service.** renmark is a Claude Code plugin;
  it runs *inside* Claude Code and has no server, GUI, or web deployment.
- **Not its own model or model provider.** renmark orchestrates existing LLMs;
  it never ships or hosts a model.
- **Not a replacement for Claude Code or for the human.** AI may generate code;
  the human owns merges and releases (approval gates are load-bearing).
- **No third-party runtime dependencies in the core.** The Python runtime is
  stdlib-only; *capability layers* MAY require optional, opt-in external tools
  (Codex CLI as an executor; Playwright for browser automation) that are never
  required for core operation and degrade gracefully to a built-in path when absent.
- **Not `legacy-plugin`.** renmark is the public vibe-coder variant; the
  legacy-plugin-employee variant is a separate plugin, not a rename — features are not
  dual-written.
- **The PRD is not a task tracker, a feature spec, or a roadmap.** It states
  *what* and *why*; plans decompose, specs design a single feature, roadmap
  sequences.

## Requirements

1. `REQ-1` A user can go from a plain-English idea to working, committed code
   through a guided pipeline without prior knowledge of specs, plans, or executors.
2. `REQ-2` Each unit of work is routed to the most cost-appropriate model, and
   the user sees a cost preview before tokens are spent. The routed executor
   set is Haiku / Codex / Sonnet / Opus / Fable (`claude-fable-5`, top
   capability tier above Opus, 1M context, $10/$50 per MTok). Fable serves the
   highest-reasoning roles — ideation (brainstorm), strategy synthesis
   (plan / prd / blueprint), and adversarial audit / review passes. In a
   project that has declared `top_tier: fable` (a committed `## Model tiers`
   block in `.renmark/memory/routing.md`, set once via init / setup / doctor,
   per-user overridable with `RENMARK_TOP_TIER`), Fable is the DEFAULT for
   those roles; in an undeclared project it remains an opt-in escalation
   target and behavior is byte-identical to the pre-Fable baseline.
   Availability is always declared, never runtime-detected. Fable is never
   assigned to mechanical or bulk work regardless of declaration — plan
   validation enforces this deterministically — and an unavailable Fable
   dispatch falls back to Opus exactly once, logged, never silently; cost
   previews and sizing tables MUST reflect its pricing.
3. `REQ-3` Any multi-step workflow is resumable after interruption, `/clear`,
   `/compact`, executor failure, or a new session — recovery reads persisted
   state, never reconstructs from conversation.
4. `REQ-4` The project carries a single, human-owned `PRD.md` source of truth;
   automated stages may *propose* edits but never write it without explicit
   human approval.
5. `REQ-5` The orchestrator never loads generated code, diffs, full specs, or
   large artifact bodies into its context — only bounded summaries, paths, and
   metadata.
6. `REQ-6` Every renmark artifact is written inside the project's `.renmark/`
   subtree (or a project-root doc); the global plugin install stays read-only.
7. `REQ-7` Plans are validated before execution and features are verified
   goal-backward after execution; completion claims require fresh evidence.
8. `REQ-8` Existing projects can adopt renmark non-destructively through the
   `/renmark:init` front door — it scaffolds missing `CLAUDE.md` / `AGENTS.md` /
   `CHANGELOG.md` / `.renmark/` and merges missing rule blocks without
   overwriting — and a broken install is diagnosable (`/renmark:doctor`).
   `/renmark:setup` remains as a thin rule-block-refresh alias.
9. `REQ-9` Loops (Loop Mode) are bounded by an explicit budget AND a
   max-iterations cap — never unbounded — and always surface a cost preview
   before spend (extends REQ-2).
10. `REQ-10` Loop state persists under `.renmark/loops/<id>/` so a loop survives
    `/clear`, `/compact`, crash, and new sessions; `/renmark:resume` recovers it
    (extends REQ-3 / REQ-6).
11. `REQ-11` Each loop iteration decides continue-or-stop **goal-backward from
    fresh verification evidence** (extends REQ-7); the orchestrator reads only
    bounded summaries, paths, metadata, and verification status — never code,
    diffs, or full bodies (REQ-5).
12. `REQ-12` Human approval is required before a loop edits `PRD.md`, merges,
    releases, escalates its budget, or makes destructive changes (extends REQ-4).
13. `REQ-13` renmark provides a `/renmark:backlog` interactive intake layer — the
    human-gated **approval buffer between autonomous discovery and autonomous
    execution**. It lists candidate work items (title / status / source / risk /
    evidence); "Approve and build" launches bounded Loop Mode on a managed
    feature branch, gating on human merge approval. Default Loop Mode execution
    for backlog items is capped at 5 iterations unless an expert/internal flow
    explicitly overrides it, with no user-facing backlog IDs, budget flags, or
    iteration flags in the default vibe-coder flow; budget escalation remains
    human-gated. On merge the branch is deleted and the item completed; on
    failure the item is marked blocked with a keep/delete-branch choice — no
    orphan branches. Item state persists under `.renmark/state/` (extends
    REQ-3 / REQ-6).
14. `REQ-14` A scheduled QA / Deep-QA lane is reserved as a **read-only proposer**
    (design only, not MVP): scheduled subagents MAY inspect, research, run checks,
    write reports, and propose backlog items, but MUST NOT edit code, commit,
    merge, release, edit `PRD.md`, escalate budget, or auto-execute (extends
    REQ-12). Autonomous scheduled *execution* remains out of scope.
15. `REQ-15` renmark provides **local-only reporting, analytics, and usage
    status** entirely on disk — no external telemetry, no database, stdlib
    JSON/JSONL only. It writes task/loop/backlog/feature/release reports under
    `.renmark/reports/`, rolling analytics under `.renmark/analytics/`, and
    exposes bounded status views such as `/renmark:usage` and
    `/renmark:analytics`. Reports summarize what happened after tasks/features
    complete. Analytics track usage over time — observed tokens, requests, agent
    calls, model/executor usage, verification outcomes, loop iterations, branch
    dispositions, backlog throughput, failures, and release/version links.
    `/renmark:usage` shows rolling 5-hour / weekly observed usage, optional
    user-configured local limits with percent used, top token-heavy features,
    recent quota/rate-limit events, and provider-reported limit/reset data only
    when a reliable provider source exposes it. Python aggregates logs into
    bounded summaries; the orchestrator never reads raw JSONL into context
    (REQ-5) and every write stays in `.renmark/` (REQ-6). All account-limit
    output is labeled "Observed local usage only. Provider-side account limits
    may differ." unless provider-reported data is explicitly available and
    sourced (extends REQ-5 / REQ-6).
16. `REQ-16` When Loop Mode, orchestrate, or a subagent hits a provider
    rate/quota limit or a configured local usage ceiling, renmark **pauses
    safely instead of failing**: it persists state, records
    `pause_reason="usage_limit"` plus provider/reset data when reliable,
    otherwise records a conservative `resume_after` fallback such as 60 minutes,
    and lets `/renmark:resume` continue later. It must NOT poll repeatedly or
    auto-schedule retries in the MVP (extends REQ-3 / REQ-10 / REQ-12).

17. `REQ-17` A read-only self-audit surface (`/renmark:audit`, with
    `/renmark:inventory` as its alias) keeps the plugin registry, docs, and
    skill parity verifiable at any time, writing artifacts under
    `.renmark/audits/`. It MUST NOT edit code, commit, or modify docs — advisory
    output only.
18. `REQ-18` `/renmark:approve` is the sole surface for **granting** approval —
    setting `human_review_completed=True` in lifecycle.json; no other skill may
    set it. The consuming skill (e.g. prd, finish, backlog) clears the gate
    after acting on the approval. All human approval gates (release, merge,
    security override) route through it.
19. `REQ-19` renmark MAY drive a live browser through an **OPTIONAL Playwright
    layer** that persists session state (cookies, localStorage, `storageState`)
    so authenticated/stateful flows resume across verify runs without re-login.
    Playwright is opt-in and never required: the core runtime stays stdlib-only
    (per the amended non-goal), and when Playwright is unavailable renmark falls
    back to the existing Chrome DevTools MCP browser channel used by
    `/renmark:verify --qa`. Persisted browser session state lives inside
    `.renmark/` (REQ-6) and never enters orchestrator context (REQ-5).
20. `REQ-20` renmark separates its working context into four explicit kinds —
    **static** (always-present `CLAUDE.md` rules), **dynamic** (skill bodies and
    `_shared/` fragments loaded on demand), **memory** (`.renmark/memory/*`), and
    **task-local** (the per-subagent dispatch packet) — and exposes skill /
    fragment **metadata upfront while full instructions/bodies load only on
    demand**. Subagent dispatch packets carry task-local context + required-skill
    metadata only, never full skill bodies. Infrastructure that operationalizes
    the REQ-5 context-hygiene pillar (extends REQ-5).
21. `REQ-21` Before any model call or subagent dispatch, renmark checks in order:
    (1) can existing state, files, git, grep, or deterministic parsers answer
    this? (2) can a deterministic script or check do it reliably? (3) is this
    repeated enough to codify as reusable code? (4) is AI judgment, synthesis,
    ambiguity resolution, or risk interpretation actually needed? Repeated
    objective checks become reusable code (e.g. worktree lifecycle checks: git
    status, branch tracking, stale detection, diff size — all deterministic,
    never model-driven). Finish lanes surface whether worktree cleanup is
    included. Cost preview labels each task step as deterministic vs
    model-driven. **Deterministic-first execution**: git / grep / state /
    parser checks before subagents; deterministic checks before model calls.

## Success metrics

- A vibe coder reaches working, committed code from `/renmark:start` with no
  more than the entry question + 2 follow-ups before routing.
- Cold-start recovery after `/clear` is a single file read (`/renmark:resume`),
  zero LLM calls.
- Orchestrator-visible output per task stays within the bounded cap
  (≤5 lines / ≤300 tokens) — violations are treated as bugs.
- Routing sends mechanical/bulk work to cheaper models, escalating only on
  capability need; cost preview matches realized spend within reason.
- The plugin installs and registers cleanly across Mac / Linux / WSL / native
  Windows, with `/renmark:doctor` catching registration faults.

## Scope boundaries

- **In scope:** the `/renmark:*` skill pipeline (start, brainstorm, prd,
  blueprint, plan, check-plan, orchestrate, verify, finish, feature, debug,
  codereview, doctor, resume, roadmap, help, hygiene, usage, analytics,
  and `init` — the front-door adoption pipeline, with `setup` as its
  rule-block-refresh alias); the bounded loop execution engine (`loop`) +
  `.renmark/loops/` state; the `/renmark:backlog` intake + approval-buffer layer
  + `.renmark/state/` item storage; the local reporting/analytics/usage layer
  (`/renmark:usage`, `/renmark:analytics`, `.renmark/reports/`,
  `.renmark/analytics/`, observed-local by default, with usage-aware pause/resume
  for loops and orchestrated runs); the self-audit surface (`/renmark:audit`,
  `/renmark:inventory`) and the human-approval gate surface (`/renmark:approve`);
  the Python runtime (CLI dispatch, verifier, lifecycle, memory); persistent
  `.renmark/` state and memory; cross-platform install; the OPTIONAL Playwright
  browser-automation + session-persistence layer (opt-in, falls back to the
  Chrome DevTools MCP channel); graduated skill-preamble tiers that give
  zero-LLM / meta skills minimal context injection while pipeline skills receive
  the full preamble — a finer per-turn token dial that never compromises
  cold-start recovery or cross-domain detection (complements REQ-5).
- **Out of scope:** hosting, a GUI/web surface, shipping or fine-tuning models,
  managing user secrets, and feature parity dual-writing with `legacy-plugin`.
- **Deferred:** a roadmap "PRD progress view" (genuine altitude overlap, but
  bloat now — see ADR-005); first-class requirement-coverage reporting in
  verify (coverage flows implicitly via plan → tasks → verify traceability);
  **indefinite autonomous loops** and **autonomous scheduled / PR-triggered loop
  *execution*** (Loop Mode ships bounded + human-gated first; the scheduled lane
  is reserved as a read-only proposer only, per REQ-14 — it never executes).

## Loop Mode

renmark's execution engine for guided builds is a **bounded, verified,
cost-aware, resumable agentic loop** — trigger + goal + verifier + budget +
persisted state + stop condition. It wraps the existing plan → orchestrate →
verify pipeline and iterates (run → verify evidence → decide → repeat) until the
goal is verified, the budget is hit, max-iterations is hit, an approval gate is
pending, or no fresh evidence supports continuing. This is the realization of
the guided pipeline (REQ-1), not a separate product or standalone mode.

- **Experts:** `/renmark:loop "<goal>"` (with `--goal` / `--verify` / `--budget`
  / `--max-iterations`).
- **Vibe coders:** loop behavior is hidden behind `/renmark:start` — they never
  see the word "loop."

## Backlog & lanes

Backlog is a **thin intake + decision layer** over the existing pipeline — it
does not replace `/renmark:feature`, `/renmark:plan`, `/renmark:orchestrate`,
`/renmark:verify`, or `/renmark:finish`. It is the approval buffer where ideas,
bugs, research findings, and QA findings wait for a human "Approve and build"
before any code is written. Approved items are consumed by Loop Mode internally
— vibe coders never type backlog IDs, budgets, or iteration flags.

`/renmark:backlog` is interactive: it first shows a selectable list of backlog
items with status / source / risk / pending decision, then opens a detail view
for the selected item with actions such as Approve and build, Research more,
Split, Reject, and Back.

renmark separates work into **four lanes**:
1. **Foreground feature** — the user actively builds with `/renmark:feature` / Loop Mode.
2. **Backlog intake** — candidate work collected from any source, awaiting approval.
3. **Scheduled QA** — read-only proposer lane (REQ-14); inspects and proposes, never executes.
4. **Execution** — approved items built one at a time.

**Parallelism rule:** parallel *read-only* work is allowed; parallel
*code-writing* work requires isolation — **only one code-writing loop may run
per working tree**.

## Open questions

- Should `PRD.md` requirement IDs (`REQ-n`) be wired into `/renmark:plan`'s
  optional `serves:` traceability field for every plan, or remain opt-in?
- How should renmark and `legacy-plugin` stay conceptually in sync without
  dual-writing features — is a shared-core extraction ever worth it?
- ~~What is the minimum viable telemetry to validate the success metrics above
  without violating the "writes stay in the project" / no-secrets doctrine?~~
  **Resolved (2026-06-09, REQ-15 / REQ-16):** local-only reporting and
  observed-usage analytics — on-disk JSON/JSONL under `.renmark/`, no external
  telemetry, no database, no account-level claims unless a provider exposes
  reliable limit/reset data. Python aggregates raw logs into bounded summaries
  so reporting never bloats orchestrator context. Usage/rate/quota limits pause
  loops and orchestrated runs safely for later `/renmark:resume`; MVP does not
  poll or auto-schedule retries.

---

**Revision note (2026-06-09, human-approved diff):** Added REQ-17 (audit
surface — `/renmark:audit` + `/renmark:inventory`) and REQ-18
(`/renmark:approve` as the sole surface for granting approval; consuming
skills clear the gate after acting — wording clarified at human review);
updated Scope boundaries to include `audit`, `inventory`, and `approve`;
removed ghost command `secure` from the in-scope list (never implemented).
These commands ship in 0.9.0. The full diff was reviewed and explicitly
approved by the project owner on 2026-06-09.

**Revision note (2026-06-10, human-approved diff):** Amended REQ-2 and the
multi-LLM Goals bullet to extend the routed executor set with **Fable**
(`claude-fable-5`, top capability tier above Opus, 1M context, $10/$50 per
MTok), reserved as an escalation target for the highest-reasoning roles
(ideation, strategy, adversarial audit/review) — never a default for
mechanical or bulk work. Proposed by the fable-integration feature's
PRD-alignment gate; diff reviewed and explicitly approved by the project
owner on 2026-06-10 via `/renmark:approve`.

**Revision note (2026-06-11, human-approved diff):** Amended REQ-2 to adopt
the declared-capability Fable routing strategy: Fable becomes the **default**
for the highest-reasoning roles (ideation, strategy synthesis, adversarial
audit/review) when a project declares `top_tier: fable` in
`.renmark/memory/routing.md`; undeclared projects keep escalation-only,
byte-identical pre-Fable behavior. Availability is declared, never
runtime-detected; mechanical/bulk prohibition is absolute and
deterministically enforced; Fable→Opus fallback is single-retry and logged.
Strategy evidence: `.renmark/research/2026-06-11-fable-routing-strategy.md`
(9-agent design workflow). Diff reviewed and explicitly approved by the
project owner on 2026-06-11 via the `/renmark:prd` UPDATE gate.

**Revision note (2026-06-12, human-approved diff):** Added REQ-19 (optional
Playwright browser-automation layer with persisted session state, falling back
to the Chrome DevTools MCP channel) and amended the "no third-party runtime
dependencies" non-goal to clarify that the *core* stays stdlib-only while
*capability layers* may require optional, opt-in external tools (Codex CLI,
Playwright). Proposed by the playwright-browser-control feature's PRD-alignment
gate; reviewed and approved by the project owner on 2026-06-12 via the
`/renmark:prd` UPDATE gate.

**Revision note (2026-06-25, human-approved diff):** Clarified the In-scope
boundary to cover **graduated skill-preamble tiers** (zero-LLM/meta skills get a
minimal/no preamble; pipeline skills get the full block) — a per-turn token
optimization that complements the REQ-5 context-hygiene pillar and the v0.20.0
trigger-only-description work. Not a new product requirement; no behavioral
non-goal changes. Proposed by the "graduated preamble-tier" (P3) feature's
PRD-alignment gate; reviewed and approved by the project owner on 2026-06-25.

**Revision note (2026-07-01, human-approved diff):** Added REQ-20 (dynamic skill
loading — a four-way context taxonomy of static / dynamic / memory / task-local,
with skill & `_shared/` fragment metadata exposed upfront while full bodies load
only on demand, and subagent dispatch packets carrying task-local context +
required-skill metadata only). Captures the deferred harness-mission acceptance
criterion AC5 as an infrastructure requirement that operationalizes the REQ-5
context-hygiene pillar. Proposed by the "dynamic-skill-loading" feature's
PRD-alignment gate; reviewed and approved by the project owner on 2026-07-01 via
the `/renmark:prd` UPDATE gate.

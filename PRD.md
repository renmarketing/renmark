---
artifact_type: prd
schema_version: 1
created_at: 2026-06-08
last_reviewed: 2026-06-08
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
  do it (Haiku / Codex / Sonnet / Opus), with a cost preview before spend.
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
- **No third-party runtime dependencies.** The Python runtime is stdlib-only;
  Codex CLI is an optional executor, never required.
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
   the user sees a cost preview before tokens are spent.
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
8. `REQ-8` Existing projects can adopt renmark non-destructively (`/renmark:setup`),
   and a broken install is diagnosable (`/renmark:doctor`).

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
  codereview, secure, setup, doctor, resume, roadmap, help, init, hygiene); the
  Python runtime (CLI dispatch, verifier, lifecycle, memory); persistent
  `.renmark/` state and memory; cross-platform install.
- **Out of scope:** hosting, a GUI/web surface, shipping or fine-tuning models,
  managing user secrets, and feature parity dual-writing with `legacy-plugin`.
- **Deferred:** a roadmap "PRD progress view" (genuine altitude overlap, but
  bloat now — see ADR-005); first-class requirement-coverage reporting in
  verify (coverage flows implicitly via plan → tasks → verify traceability).

## Open questions

- Should `PRD.md` requirement IDs (`REQ-n`) be wired into `/renmark:plan`'s
  optional `serves:` traceability field for every plan, or remain opt-in?
- How should renmark and `legacy-plugin` stay conceptually in sync without
  dual-writing features — is a shared-core extraction ever worth it?
- What is the minimum viable telemetry (if any) to validate the success metrics
  above without violating the "writes stay in the project" / no-secrets doctrine?

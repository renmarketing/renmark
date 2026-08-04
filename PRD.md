---
artifact_type: prd
schema_version: 1
created_at: 2026-06-08
last_reviewed: 2026-08-04
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

renmark turns Claude Code and Codex into a **guided build assistant**: a vibe
coder describes the goal in plain English (or invokes a direct `/renmark:*`
skill), and renmark handles stack selection, scope, best practices, and a full
build pipeline — while experienced developers get the same pipeline exposed as
direct commands. It is opinionated about one thing above all: **context
hygiene** — the orchestrator coordinates, it never accumulates, and durable
state lives on disk, not in the conversation. Claude Code and Codex are
first-class hosts for the same product workflow, not separate product forks.

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
- Internal orchestration (planning, bounded workers, independent inspection,
  deterministic policy/integration/ledger) stays invisible by default —
  visible process is added only when it measurably helps (REQ-26).
- Substantial builds ship as a sequence of user-testable milestone releases,
  not internal-only progress; small bounded work uses a fast path instead of
  full planning ceremony (REQ-27).
- A distinct entry point for **reassessing and transforming an existing
  application** (brownfield), separate from `/renmark:start`'s greenfield
  entry point — survey before structural change, never a silent rewrite
  (REQ-28).
- For a non-trivial new build (greenfield), external evidence, binding PRD
  traceability, and deliberate modular architecture before a single line of
  target code is written — proportional to scope, with a documented waiver
  for genuinely small builds (REQ-29).
- Renmark's current low-token, low-latency, minimal-interruption
  orchestration behavior is a protected product capability, measured against
  a named baseline, not a subjective impression that can silently regress as
  new features land (REQ-30).
- Every dispatched unit of work is visible as a native host task with an
  honest lifecycle — created once, updated in place, never self-approved,
  never silently recreated on resume (REQ-31).

**Non-goals (product-level, durable)**
- **Not a standalone app or hosted service.** renmark is a plugin/workflow
  bundle for Claude Code and Codex; it uses host-provided interaction surfaces
  and has no server, standalone GUI, or web deployment.
- **Not its own model or model provider.** renmark orchestrates existing LLMs;
  it never ships or hosts a model.
- **Not a replacement for Claude Code, Codex, or the human.** AI may generate
  code; the human owns merges and releases (approval gates are load-bearing).
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
- **Not a visible internal bureaucracy.** Internal execution roles, authority
  boundaries, and governance artifacts (see REQ-26) are implementation
  detail; users are never required to understand, configure, or manually
  approve per-role handoffs to use renmark.

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
22. `REQ-22` **Two-mode milestone delivery.** Renmark exposes exactly two
    owner-selectable delivery modes: **Agency** and **Orchestrator**. Agency
    starts from an idea or product-level outcome and owns discovery, PRD
    agreement, stack recommendation, milestone-roadmap approval, demos,
    feedback, milestone signoff, and release. Orchestrator starts from a defined
    goal, feature, bug, specification, or approved milestone and owns scope and
    acceptance validation, work-package planning, model routing, dispatch,
    verification, independent code review, bounded repair, and finish. Agency
    delegates every milestone build to Orchestrator; the modes share one
    milestone/work-package execution engine rather than duplicating pipeline,
    state, cost, or verification logic. Conductor is no longer a public or
    persisted mode: its useful behavior survives only as an automatically
    selected `guided/direct` execution policy inside Orchestrator. Mode is
    selected per delivery run, persists for resume, and may be explicitly
    overridden by the owner.

    Every milestone carries a goal, expected outcome, acceptance evidence,
    dependencies, risks, cost lane, demo point, and signoff policy. A milestone
    is complete only after fresh verification and independent review are clean.
    `/renmark:loop` is a bounded, milestone-local Orchestrator primitive, not a
    third mode: implementation failures may enter
    `build → verify → repair → verify`, and review findings may enter
    `review → scoped fix → verify → re-review`. Each loop requires a verifier,
    budget, maximum iterations, fresh evidence, and no-progress fingerprint; it
    stops on success, exhaustion, repeated evidence, scope drift, or an approval
    gate. A loop may not change product scope, advance a milestone, or bypass
    owner signoff. Before a third materially equivalent attempt, recurring-issue
    prevention takes control (extends REQ-3, REQ-4, REQ-5, REQ-7, REQ-9,
    REQ-11, REQ-20, REQ-21, REQ-24).
    - *Acceptance:* done when Agency executes each approved milestone through
      Orchestrator without duplicating state or pipeline code; done when a clear
      feature can run directly in Orchestrator without Agency discovery gates;
      done when Conductor cannot be selected or persisted as a public mode; done
      when milestone-local build and review loops stop at their evidence,
      budget, recurrence, scope, and approval boundaries.
23. `REQ-23` **Claude Code / Codex host parity.** Renmark ships the same named,
    versioned plugin and the same product-level pipeline outcomes on both hosts.
    Host adapters translate interaction, implicit routing, plugin installation,
    and subagent dispatch without forking lifecycle, loop, approval, verifier,
    or artifact semantics. Every user-choice menu has exactly one visibly
    labeled `(Recommended)` option at index 0; it uses the host-native selector
    when that selector is available and an identically ordered numbered
    fallback otherwise. This is a **selector-capable** contract, not a promise
    that every host surface can render native buttons: only unresolved
    decisions, approval gates, and handoffs use a choice menu, while
    informational status remains ordinary prose and never creates a pause.
    The active adapter resolves selector availability and option capacity at
    render time rather than persisting a host assumption. When choices exceed
    the native capacity, no action is silently truncated: an explicit
    `More options…` action pages to the remaining choices, continuation pages
    provide `Back` and `Cancel` / `Reject` as appropriate, and dangerous gates
    keep their safe refusal action reachable. If the selector is unavailable,
    errors, or returns no valid selection, Renmark renders the complete
    recommended-first numbered fallback and accepts a number, stable choice
    code, exact label, or free-text continuation.

    The semantic pending decision and approval class are recoverable from
    canonical workflow state, but native-tool availability and page position
    are presentation details re-resolved on continuation or resume. Renmark
    does not attempt to switch a host's collaboration mode. In particular,
    Codex may expose its native picker in Plan mode while Default mode requires
    the numbered fallback; selector absence MUST NOT classify an interactive
    Codex session as headless. Plain-English triggers including “plan this”,
    “dispatch this”, “loop until this passes”, “fix this”, “build this”,
    “what's next”, and “ship this” route to the same intended pipeline on both
    hosts without requiring `/renmark:*` syntax. Host-native subagents preserve
    the existing bounded input/output, cost, wave, verifier, pause, and resume
    contracts (extends REQ-1, REQ-2, REQ-3, REQ-5, REQ-7, REQ-20, REQ-21).
    - *Acceptance:* done when both hosts report the same installed Renmark name
      and release version; done when the trigger matrix selects the same skills
      and every selector/fallback is recommended-first; done when interaction
      fixtures prove Claude native selection, Codex Plan-mode native selection
      within the active option cap, Codex Default-mode fallback, overflow
      navigation, cancellation, free-text continuation, and resume; done when
      plan → dispatch → verify and bounded loop → pause → resume trajectories
      reach the same golden outcomes on Claude Code and Codex.
24. `REQ-24` **Proactive recurring-issue prevention.** Before dispatching another
    model attempt after the same materially equivalent implementation or testing
    issue recurs, Renmark detects the recurrence using a host-neutral fingerprint
    within the active run and bounded structured project memory across runs. It
    notifies the user with concise recurrence evidence and recommends either
    patching the reproducible underlying defect or proposing a mirrored durable
    guard in `CLAUDE.md` and `AGENTS.md` when workflow instruction would prevent
    another occurrence. It preserves human approval gates, never auto-writes
    product or rule documents, avoids loading raw histories into orchestrator
    context, and behaves equivalently on Claude Code and Codex (extends REQ-2,
    REQ-3, REQ-5, REQ-20, REQ-21, and REQ-23).
    - *Acceptance:* done when the second equivalent occurrence is surfaced before
      a third model attempt; done when the warning includes bounded evidence and
      a concrete patch-or-durable-guard recommendation; done when recurrence
      evidence persists locally without raw transcript or history injection.
25. `REQ-25` **Project contract propagation.** Every project adopted or built
    through Renmark carries a concise managed delivery contract in both
    `CLAUDE.md` and `AGENTS.md`. The two blocks are semantically mirrored, with
    host-specific wording only where host behavior genuinely differs, and are
    derived from one canonical source rather than hand-maintained copies. The
    contract explains the Agency and Orchestrator paths, milestone goals and
    outcomes, bounded work-package scope, planner/executor/reviewer role
    separation, deterministic verification, milestone-local loops, independent
    review and repair, canonical state, stop conditions, and human gates. It
    also states the selector-capable interaction rule: real decisions use the
    active host's native picker when available and the equivalent numbered
    fallback otherwise; informational status stays prose; native clickability
    may require a user-selected host surface such as Codex Plan mode. It cites
    dynamically loaded skills and shared contracts by pointer instead of
    inlining their full bodies.

    `/renmark:init` owns the non-destructive managed-block merge.
    `/renmark:start` and `/renmark:feature` run the same deterministic freshness
    check before planning and route missing or stale blocks through that single
    refresh primitive; they do not invent their own writers or contract text.
    Refreshes preserve all project-specific instructions outside managed
    markers and never replace an unmarked user section. Root guidance,
    templates, installed blocks, and host variants are guarded by deterministic
    parity and idempotency checks (extends REQ-1, REQ-5, REQ-8, REQ-20,
    REQ-21, REQ-22, REQ-23).
    - *Acceptance:* done when `init` on a new or existing project and `start` or
      `feature` on a stale project converge on the same current managed
      contract; done when running the refresh twice produces no second diff;
      done when custom content outside managed markers remains byte-for-byte
      unchanged; done when deterministic checks fail on semantic drift between
      `CLAUDE.md`, `AGENTS.md`, their templates, or installed host variants.
26. `REQ-26` **Invisible-by-default internal governance.** Renmark may
    implement its pipelines using internal execution roles and authority
    boundaries (planning, bounded implementation, independent verification,
    and deterministic policy/integration/record-keeping), but no internal
    role, handoff, artifact schema, or governance state may become a
    required user-facing step by default. Any user-visible governance
    surface (a role explanation, a per-handoff approval, a governance
    artifact shown to the user) is permitted only when it measurably
    reduces user effort, inference cost, or failure rate; otherwise it must
    not execute. The single plain-English entry point (`/renmark:start` et
    al.) and the existing approval-gate surfaces (REQ-4, REQ-12, REQ-18)
    remain the only required points of user interaction (extends REQ-1,
    REQ-20).
    - *Acceptance:* done when a normal `/renmark:feature` run exposes no new
      required approval step, role name, or governance artifact beyond what
      existed before internal governance work began, unless that step
      demonstrably reduced rework, cost, or failure rate and was explicitly
      added as a result.
27. `REQ-27` **Work classification and release-oriented delivery.** Before
    orchestrating requested work, renmark classifies it and routes
    accordingly. A bounded correction with no material new user journey uses
    a **fast path** — implementation, targeted tests, and inspection only
    when risk warrants it — skipping full milestone planning and
    multi-agent orchestration. A substantial build is planned and delivered
    as a sequence of **milestone releases**: each release defines a
    distinct, user-testable capability, not merely completed internal
    modules, and passes engineering verification, independent inspection, a
    user-level acceptance scenario, and a rollback path before being
    considered complete. Renmark prefers vertical release slices that
    deliver end-to-end usable capability over horizontal technical layers
    that stay unusable until the end. This classification-and-delivery
    behavior applies to every project renmark plans, implements, verifies,
    and releases — including renmark's own development — not only to a
    single class of work (extends REQ-1, REQ-7, REQ-26).
    - *Acceptance:* done when a small bounded fix skips full milestone
      planning and multi-agent orchestration ceremony; done when a
      substantial feature build is decomposed into releases each
      demonstrating a real user-testable capability rather than horizontal
      layers with nothing usable until the end; done when a release is not
      marked complete on internal task completion alone but requires its
      acceptance and observation evidence.
28. `REQ-28` **Brownfield modernization entry point.** Renmark provides a
    distinct pipeline (`/renmark:rethink`) for reassessing and transforming
    an *existing* application, separate from `/renmark:start`'s greenfield
    (new-project) entry point. Before any structural change, it confirms a
    **Transformation Intake** (desired outcome, protected behavior,
    constraints, non-goals, areas open to change — Owner-level blocking
    questions only) and then runs nine bounded stages: (a) surveys the
    current system internally (architecture,
    data flows, in-use features, tests/integrations/deployment/ops
    dependencies, known pain and cost) via a bounded subagent — the full
    survey never enters orchestrator context (extends REQ-5); (b) establishes
    a behavioral baseline (what must keep working, current outputs/acceptance
    examples, measurements, compatibility tests) before any structural edit;
    (c) extracts a **PRD acceptance contract** — every applicable PRD
    requirement, non-goal, and acceptance criterion mapped to current
    evidence, compliance status, target behavior, planned release, and
    verification method, with missing/ambiguous/contradictory/obsolete/
    untestable criteria flagged and material conflicts routed to the Owner;
    behavioral compatibility (b) and PRD compliance (c) are distinct — current
    behavior is never treated as correct merely because it exists; (d)
    performs **external discovery and benchmarking** — a separate, mandatory
    subagent stage researching comparable products, competitors, and
    industry-standard architecture/UX/security/observability/deployment/
    scaling patterns relevant to this product's actual domain, with sourced,
    dated, evidence-rated findings separated into verified facts / inferences
    / recommendations / unknowns; if external access is unavailable the stage
    is reported blocked/incomplete and never silently backed by model memory;
    (e) runs a **modularity, scalability, and maintainability assessment** —
    domain/module boundaries, coupling and dependency direction, duplication,
    data ownership, API/contract stability, extension points, testability,
    observability, and scaling bottlenecks, producing current- and
    target-state module/dependency maps while avoiding speculative
    microservices; (f) classifies existing components as Keep / Improve /
    Replace / Remove / Unknown-needs-spike, each decision citing internal
    evidence, PRD impact, external evidence where relevant, and modularity
    impact — architectural redesign is not limited to `Replace`, as an
    `Improve` item may need boundary extraction, decomposition, dependency
    inversion, or interface stabilization. Between stage 5 and stage 6, a
    **Discovery Direction Gate** presents material findings/implications,
    PRD/architecture/capability/research gaps, a recommended transformation
    direction, up to two viable alternatives, and the exact Owner decision
    required, and obtains one explicit Owner direction before classification
    or blueprint work continues; (g) produces a target modular blueprint
    (desired capabilities traced to PRD requirements, new/restructured
    architecture for `Replace` and evidence-justified `Improve` items, module
    contracts and dependency directions, migration constraints, explicit
    non-goals). Between stage 7 and stage 8, a **Solution Gate** presents the
    proposed classification and blueprint — behavioral/PRD changes, protected
    behavior, module/data/integration boundaries, removals/incompatibilities
    and their migration risk, and material tradeoffs/exclusions/unresolved
    decisions — and obtains one explicit Owner approval before the roadmap is
    finalized; (h) produces an incremental transformation roadmap of small,
    independently-usable, user-testable releases, each carrying PRD-traceable
    acceptance scenarios, a compatibility/rollback path, and a verification
    method — never a big-bang rewrite, and old/new components may coexist
    temporarily; (i) an **Execution Gate** presenting that roadmap — release
    outcomes, PRD criteria, compatibility guarantees, dependencies, migration,
    verification, observability, rollback, and Owner acceptance scenarios —
    and obtaining one explicit Owner approval before any target production
    code changes or Agency execution begins. A cross-cutting **exception
    check-in** interrupts the current stage immediately — pausing only the
    affected decision, discarding no completed work — on a material PRD/
    Owner-intent conflict, unreliable or blocked research, a major cost/
    scope/security impact, a proposed removal of protected behavior, or a
    high-impact unknown that cannot be safely bounded, rather than waiting
    for the next scheduled gate. No gate's approval may be inferred from
    silence or from a different gate's approval, and no agent may approve
    its own recommendation at any of the three gates. Rethink hands off to
    renmark's existing milestone/Agency execution machinery rather than a
    parallel system (extends REQ-22, REQ-27), and does not implement or
    restructure anything — nor may any agent self-approve a structural
    recommendation — until the PRD acceptance contract, the external-benchmark
    findings, the modularity assessment, the keep/improve/replace/remove
    classification, and the first migration milestone are explicit and
    Owner-approved (extends REQ-4, REQ-12).
    - *Acceptance:* done when invoking rethink on an existing project
      produces a survey + baseline + PRD-acceptance-map + external-benchmark +
      modularity-assessment + classification + target-blueprint + roadmap
      artifact set with no production code changed; done when the
      external-benchmark artifact reports an honest `complete` /
      `blocked` / `incomplete` status and is never marked complete from
      model memory alone; done when the transformation is never reported
      complete while an applicable PRD acceptance criterion is failed,
      omitted, unverified, or changed without explicit Owner approval; done
      when at least one `Improve`-classified item's blueprint reflects a
      modularity-driven boundary change without full replacement, whenever
      the modularity assessment identifies one; done when the first proposed
      release is a baseline/compatibility-coverage release, not an
      architecture replacement, unless the Owner explicitly overrides that
      default with recorded evidence; done when the Discovery Direction
      Gate, the Solution Gate, and the Execution Gate each require and
      record one distinct explicit Owner decision, none skipped or merged
      into another; done when a material PRD/Owner-intent conflict,
      unreliable/blocked research, a major cost/scope/security impact, a
      proposed removal of protected behavior, or a high-impact unknown
      triggers an exception check-in immediately rather than waiting for the
      next scheduled gate, pausing only the affected decision without
      discarding completed work; done when a resumed rethink run reuses
      existing stage artifacts and cleared gate decisions rather than
      re-dispatching completed research or re-asking a cleared gate; done
      when execution of any migration milestone routes through the same
      Owner-gated milestone machinery `/renmark:start`'s Agency mode already
      uses, not a bespoke rethink-only executor.
29. `REQ-29` **Evidence-based greenfield entry point.** For a non-trivial
    (Complex-scope) `/renmark:start` build, before any target application
    code is written: (a) performs external discovery — a bounded subagent
    researches comparable products, domain-standard workflows, and relevant
    architecture/UX/security/observability/deployment/scaling patterns for
    this product's actual domain, with sourced, dated, evidence-rated
    findings separated into facts / inferences / recommendations / unknowns;
    research informs but never overrides Owner intent, and unavailable
    external access is reported `blocked`/`incomplete` rather than silently
    backed by model memory; a clearly-scoped (Simple) build carries this
    forward as one documented, Owner-approved waiver (reason, risk, scope)
    inside its existing confirmation, never a silent skip; (b) presents a
    **Discovery Direction Gate** — findings, implications, a recommended
    direction, viable alternatives, assumptions, risks, and the exact
    decisions required — and obtains one explicit Owner direction choice
    before the PRD is drafted; (c) establishes a **PRD acceptance/
    traceability contract** after PRD approval — every applicable PRD
    requirement and acceptance criterion mapped to planned behavior, its
    target module/contract, its planned release, and its verification
    method, with missing/ambiguous/contradictory/untestable criteria flagged
    and material PRD/scope changes routed to the Owner; no release is
    reported complete while an applicable criterion is failed, omitted,
    unverified, or changed without explicit Owner approval; (d) produces a
    **prospective modular blueprint** before execution — domain boundaries,
    dependency direction, data ownership, public contracts/adapters,
    extension points, test seams, observability, and security boundaries for
    the system about to be built, reusing `/renmark:blueprint`'s existing
    diagram convention, preferring the simplest maintainable design over
    speculative microservices or premature abstraction; (e) presents a
    **Solution Gate** — scope, workflows, requirements, module boundaries,
    exclusions, unresolved decisions, and material tradeoffs — and obtains
    one explicit Owner approval before the release roadmap is finalized;
    (f) produces an **incremental release roadmap** whose every release
    states its user value, PRD criteria, affected modules/contracts,
    dependencies, migration, verification, observability, and Owner
    acceptance scenario; (g) presents an **Execution Gate** — the finalized
    roadmap or plan — and obtains one explicit Owner approval before any
    build task is dispatched, with no agent in the pipeline permitted to
    self-approve a structural or scope decision at any of the three gates;
    and (h) triggers an immediate **exception check-in** — interrupting the
    current stage rather than waiting for its scheduled gate — on a material
    PRD conflict, unreliable/blocked research bearing on a live decision, a
    major cost/scope/security implication, or a high-impact unknown,
    presenting the specific finding and concrete options (never raw research)
    for one explicit Owner decision; an unresolved high-impact unknown
    becomes a bounded spike (question, scope, evidence requirement, budget,
    stop condition) rather than a silent assumption. This is `/renmark:start`'s
    greenfield counterpart to REQ-28's brownfield discipline: it excludes
    brownfield-only concerns (system survey, compatibility baseline,
    Keep/Improve/Replace/Remove classification — there is no existing system)
    while applying the same evidence, traceability, and modularity discipline
    to a system that does not exist yet (extends REQ-1, REQ-4, REQ-5, REQ-12,
    REQ-27, REQ-28).
    - *Acceptance:* done when a Complex-scope build produces an
      external-research artifact reporting an honest `complete` / `blocked` /
      `incomplete` status (never claimed complete from model memory alone), a
      PRD-acceptance-map artifact, and a modular blueprint, all before any
      target code exists; done when the Discovery Direction Gate, the
      Solution Gate, and the Execution Gate each require and record one
      distinct explicit Owner decision, and none is skipped or merged into
      another for a Complex build; done when a material PRD conflict,
      `blocked` research bearing on a live decision, a major cost/scope/
      security implication, or a high-impact unknown triggers an exception
      check-in immediately rather than waiting for the next scheduled gate;
      done when a Simple-scope build instead records one explicit,
      Owner-approved waiver (reason, risk, scope) and proceeds through its
      existing single confirmation with no added gate; done when a build is
      never reported complete while an applicable PRD acceptance criterion
      is failed, omitted, unverified, or changed without Owner approval;
      done when execution of any release — single-feature or staged-program
      — routes through the same Owner-gated milestone machinery
      `/renmark:rethink` and `/renmark:start`'s Agency mode already use, not
      a parallel executor.
30. `REQ-30` **Orchestration efficiency and UX stability is a protected
    capability.** Renmark's current low-token, low-latency, owner-focused
    orchestration behavior — bounded subagent dispatch, context hygiene,
    deterministic-first execution, work-classification fast paths, and
    minimal Owner-gate interruption — is a product capability, not an
    implementation detail, and every pipeline (`init`, `start`, `feature`,
    `debug`, `roadmap`, `finish`, `rethink`, and the `orchestrate` engine
    they share) must cite and preserve it.
    - **Required behavior** (each clause extends an existing requirement;
      REQ-30 does not restate their mechanics, it protects them from silent
      regression): (a) the orchestrator coordinates bounded subagents and
      artifacts — it does not absorb detailed worker context, research
      bodies, diffs, or logs (extends REQ-5, REQ-20); (b) completed or
      approved artifacts are reused — renmark does not repeat discovery,
      reread unchanged files, regenerate plans, or redispatch completed work
      unless an input was invalidated (extends REQ-3, REQ-24); (c)
      deterministic checks run before LLM reasoning, and the smallest capable
      model is the default — escalation requires an explicit trigger such as
      failure, ambiguity, high-risk judgment, or unresolved review (extends
      REQ-2, REQ-21); (d) one bounded worker per task is the default —
      parallel or additional dispatch requires independent work and a clear
      time/quality benefit, and duplicate investigation is prohibited
      (extends REQ-21, REQ-24); (e) the Owner is asked only for decisions
      requiring Owner authority — never a technical question renmark can
      resolve safely from evidence (extends REQ-27, and the Discovery
      Direction/Solution/Execution gate contracts in REQ-28/REQ-29); (f)
      every Owner-facing gate stays structured as findings → implications →
      recommendation → alternatives → the exact decision required, with raw
      research and agent logs staying in artifacts (extends REQ-5, REQ-28,
      REQ-29); (g) a new pipeline stage may add a durable artifact — it may
      not add retained orchestrator context or a parallel execution engine
      (extends REQ-5, REQ-22); (h) every pipeline reuses the existing
      Agency/milestone executor unless the Owner explicitly approves a
      replacement (extends REQ-22, REQ-28, REQ-29); (i) any change to
      orchestration routing, context limits, dispatch policy, model
      escalation, Owner-gate frequency, or artifact-reuse behavior requires
      an explicit PRD change and Owner approval through `/renmark:prd`'s
      UPDATE gate — it is never a side effect of an unrelated feature.
    - **Named baseline.** The release tagged `v0.39.7`
      (commit `d9cccc5`, 2026-08-02) is the reference point for this
      requirement, named **`ORCHESTRATION-BASELINE-2026-08`**, recorded at
      `.renmark/memory/orchestration-baseline.md`. "Preserve current
      behavior" means preserve *that* recorded baseline's structural
      guarantees and — once captured — its measured token/latency/dispatch
      numbers, not a subjective later impression of "still feels fast."
    - **Regression protection.** Before any change touching orchestration
      routing, context limits, dispatch policy, model escalation, Owner-gate
      frequency, or artifact reuse, run the same representative Start /
      Feature-or-Fix / Orchestrate / Rethink scenarios against
      `ORCHESTRATION-BASELINE-2026-08` and capture: total input/output
      tokens, wall-clock and active execution time, agent dispatch count,
      repeated file/artifact reads, Owner question/gate count, time to first
      useful Owner checkpoint, and verification/completion results. A
      release is **blocked** when it: increases median token use or
      execution time by more than 15% over the baseline; adds a routine
      Owner question or gate beyond the named gates each pipeline already
      defines; introduces a duplicate dispatch or repeats completed work;
      sends detailed worker context into the orchestrator; or weakens
      verification, completion, or recovery behavior. An exception requires
      quantified evidence, explicit Owner approval, a documented benefit, and
      a rollback path — new functionality alone never justifies an
      efficiency regression.
    - *Acceptance:* done when orchestrator-visible summaries stay bounded
      (≤5 lines / ≤300 tokens) and artifact-linked on every task; done when
      an interrupted run resumes from durable state without repeating a
      completed stage or re-asking a cleared gate; done when routine work
      routes to the lowest-cost capable executor and escalation carries a
      documented reason; done when the Owner sees only material decisions
      and actionable checkpoints, never a raw research dump or a resolvable
      technical question; done when `init`, `start`, `feature`, `debug`,
      `roadmap`, `finish`, `rethink`, and `orchestrate` each cite this
      requirement in their own SKILL.md; done when a proposed orchestration
      change is blocked, or explicitly Owner-exempted with quantified
      evidence and a rollback path, per the regression-protection rule above.
31. `REQ-31` **Native task tracking for dispatched work.** Every pipeline
    that dispatches agents (`start`, `feature`, `debug`, `rethink`,
    `orchestrate`, `codereview`, `finish`, and any future pipeline that
    dispatches) tracks that work through **two distinct, non-substitutable
    mechanisms**, defined once in `${CLAUDE_PLUGIN_ROOT}/skills/.shared/
    task-tracking.md` and cited — never restated — by each pipeline's
    dispatch path via the existing `subagent-budget.md` contract:
    (i) **the live host's own native Task tools** (Claude Code's
    `TaskCreate`/`TaskUpdate`/`TaskList`/`TaskGet`) — whenever an interactive
    session is itself executing a renmark skill and calls `Agent` to
    dispatch a subagent, that session calls its own native tools around the
    dispatch; this is a skill instruction to the executing agent, satisfied
    only by that agent's real tool calls, and is the sole mechanism that
    satisfies "before dispatching work, create a native task using the
    available Task tools" — no Python module can invoke a host's tools on
    an agent's behalf; and (ii) **`renmark.task_tracking`**
    (`.renmark/state/tasks.json`), a real, tested Python mirror of the same
    lifecycle wired into the one dispatch path that has no live session to
    call native tools at all — `renmark.cli._engine.execute_plan`'s
    `_runner`, which hands work to the headless `codex`/subprocess executor.
    Mechanism (ii) is scoped strictly to that headless path; it never
    substitutes for (i) when a live agent is present. One
    parent task per milestone, one bounded task per dispatch — never a task
    for trivial internal reasoning or a deterministic check. Each dispatched
    task's content mirrors the dispatch packet's existing required fields
    (title/role/scope-and-expected-result/dependencies/verification
    requirement) — no new schema. Lifecycle: `pending` on creation →
    `in_progress` immediately before dispatch → blockers/retries/
    reassignment/failure recorded on the same task as they occur →
    `completed` only once required output and verification evidence exist.
    A worker's own task completion never completes its parent milestone
    task — independent verification/review gets its own linked task, and
    `renmark.task_tracking.complete_worker_task` mechanically enforces this
    by reusing `renmark.ledger.check_dispatch_independence` (the same
    dispatch-identity independence check R-0.4's Inspector already relies
    on) rather than trusting a caller-asserted flag (extends REQ-4, REQ-12,
    REQ-28, REQ-29). On interruption or
    resume, existing tasks are reloaded and reused — a completed or
    accepted task is never recreated or redispatched (extends REQ-3,
    REQ-24). A scope change updates or explicitly closes the existing task
    with a reason before any replacement is created. Task tracking is
    strictly informational: it adds no Owner gate, question, or agent
    dispatch of its own, and carries only bounded status/dependencies/
    result-summary/artifact-path — never raw research, transcripts, or logs
    — into the native task (extends REQ-5, REQ-30). Graceful degradation
    (requirement 12) applies only to a genuinely tool-less path — a headless
    `renmark-execute` invocation with no live session attached — never to an
    interactive session where the native tools are simply present in the
    tool palette; there, calling them is not optional. When they are
    genuinely unavailable, renmark states that live tracking is unavailable
    and continues on durable Renmark artifacts (and, for the headless path,
    `renmark.task_tracking`'s own state) alone; it never claims a native
    task was created or updated when the live host tool was not actually
    called.
    - *Acceptance:* done when an interactive session executing any
      dispatching pipeline calls its own host's `TaskCreate` before, and
      `TaskUpdate` through, each real `Agent` dispatch — a live, in-transcript
      tool call, not a Python side effect, per the skill instructions in
      `task-tracking.md`/`subagent-budget.md`/`orchestrate/SKILL.md`; done
      when `renmark.cli._engine.execute_plan`'s real headless dispatch loop
      (proven by `tests/test_task_tracking_engine_wiring.py`, not by a
      fragment's presence) creates or reuses exactly one native worker task
      per dispatched plan task and one parent task per plan run;
      done when a task's status transitions match its actual dispatch
      lifecycle (`pending` → `in_progress` → `completed`, with
      blockers/retries/failure recorded in place, proven by
      `tests/test_task_tracking.py`); done when a worker task's completion
      alone never marks itself `completed` while its linked verification
      task is not itself `completed` and provably independent — proven by a
      real `SelfApprovalError`/`MissingVerificationError` raised from
      `renmark.task_tracking.complete_worker_task`, not asserted about
      documentation; done when a resumed run reuses existing tasks rather
      than recreating or redispatching completed work — proven by
      `should_skip_dispatch` and idempotent `create_or_reuse_task`; done when
      a `renmark.task_tracking` failure never blocks the real dispatch/commit
      it wraps (best-effort, never-raising to the caller); done when task
      tracking
      introduces no additional Owner gate, question, or dispatch, and no
      measured token/time regression beyond REQ-30's 15% threshold; done
      when native Task tools being unavailable is reported honestly rather
      than silently skipped or fabricated.

## Success metrics

- A vibe coder reaches working, committed code from `/renmark:start` with no
  more than the entry question + 2 follow-ups before routing.
- Agency and Orchestrator golden trajectories reach the same verified,
  independently reviewed milestone outcome from their different entry
  altitudes, and Agency advances only after the owner accepts that outcome.
- `init`, `start`, and `feature` converge on the same current managed
  `CLAUDE.md` / `AGENTS.md` contract, preserve project-specific instructions,
  and pass parity plus second-run idempotency checks.
- Cold-start recovery after `/clear` is a single file read (`/renmark:resume`),
  zero LLM calls.
- Orchestrator-visible output per task stays within the bounded cap
  (≤5 lines / ≤300 tokens) — violations are treated as bugs.
- Routing sends mechanical/bulk work to cheaper models, escalating only on
  capability need; cost preview matches realized spend within reason.
- The plugin installs and registers cleanly across Mac / Linux / WSL / native
  Windows on Claude Code and Codex, with `/renmark:doctor` catching host-specific
  registration, identity, cache, and version faults.
- Natural-language trigger, selector-ordering, full-pipeline, and loop/resume
  parity fixtures pass on both Claude Code and Codex; the interaction matrix
  covers Claude native selectors, Codex Plan-mode selectors, Codex Default-mode
  numbered fallback, overflow navigation, cancellation, continuation, and
  resume.
- Repeated-issue parity fixtures confirm that both hosts warn before a third
  futile attempt and produce the same remediation class.

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
  `.renmark/` state and memory; cross-platform, dual-host plugin installation;
  host-neutral interaction/routing contracts and Claude Code/Codex native
  subagent adapters; cross-host deterministic and live trajectory tests; the OPTIONAL Playwright
  browser-automation + session-persistence layer (opt-in, falls back to the
  Chrome DevTools MCP channel); graduated skill-preamble tiers that give
  zero-LLM / meta skills minimal context injection while pipeline skills receive
  the full preamble — a finer per-turn token dial that never compromises
  cold-start recovery or cross-domain detection (complements REQ-5); the
  two-mode Agency / Orchestrator milestone-delivery model, with Conductor
  retained only as an internal guided/direct policy (REQ-22); and concise,
  mirrored project delivery contracts installed and refreshed non-destructively
  through the shared `init` primitive used by `init`, `start`, and `feature`
  (REQ-25).
- **Out of scope:** hosting, a GUI/web surface, shipping or fine-tuning models,
  replacing host-provided selectors with a standalone Renmark UI, managing user
  secrets, and feature parity dual-writing with `legacy-plugin`.
- **Deferred:** a roadmap "PRD progress view" (genuine altitude overlap, but
  bloat now — see ADR-005); first-class requirement-coverage reporting in
  verify (coverage flows implicitly via plan → tasks → verify traceability);
  **indefinite autonomous loops** and **autonomous scheduled / PR-triggered loop
  *execution*** (Loop Mode ships bounded + human-gated first; the scheduled lane
  is reserved as a read-only proposer only, per REQ-14 — it never executes).

## Loop Mode

Within Orchestrator, iterative work uses a **bounded, verified, cost-aware,
resumable milestone-local loop** — trigger + goal + verifier + budget +
persisted state + stop condition. It wraps a work package or milestone repair
path and iterates from fresh evidence until the goal is verified, the budget or
maximum iteration count is hit, recurrence/no-progress is detected, scope
drifts, or an approval gate is pending. Independent review findings use the
same engine but must re-enter verification before re-review. This is an internal
execution primitive shared by Agency and direct Orchestrator runs, not a third
delivery mode and never an authority to advance milestones or change scope.

- **Experts:** `/renmark:loop "<goal>"` (with `--goal` / `--verify` / `--budget`
  / `--max-iterations`).
- **Vibe coders:** loop behavior is selected automatically by `start` or
  `feature` when verifier-driven iteration is warranted; they do not manage loop
  IDs, budgets, or iteration flags.

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

**Revision note (2026-07-02, human-approved diff):** Added REQ-22 (Agency Mode —
an optional higher-level project-delivery workflow above Conductor/Orchestrator
that drives the discovery → PRD → roadmap → milestones → build → demo → feedback
→ signoff → release loop; explicit opt-in, lightweight resumable agency state,
owner-level gates, dynamic agency-body loading, reuse of cost-control/finish-
lane/deterministic-first infra) and a matching In-scope clause. Proposed by the
agency-mode feature's PRD-alignment gate; spec at
`.renmark/specs/2026-07-02-agency-mode.spec.md`. Reviewed and approved by the
project owner on 2026-07-02 via the `/renmark:prd` UPDATE gate.

**Revision note (2026-07-15, human-approved diff):** Expanded Renmark from a
Claude Code-only plugin to a first-class Claude Code + Codex plugin/workflow
bundle; added REQ-23 for dual-host distribution identity, recommended-first
selector/fallback behavior, implicit trigger parity, host-native subagent
dispatch, and shared pipeline/loop trajectory proof. Updated Vision, durable
non-goals, success metrics, and scope boundaries. Proposed by the
Codex/Claude-parity feature's PRD-alignment gate and explicitly approved by the
project owner on 2026-07-15.

**Revision note (2026-07-29, human-approved diff):** Amended REQ-22 to define
Agency and Orchestrator as Renmark's two delivery modes, demote Conductor to an
internal guided/direct policy, make milestones the owner-alignment boundary,
and place bounded build plus review-repair loops inside Orchestrator. Added
REQ-25 for concise, semantically mirrored `CLAUDE.md` / `AGENTS.md` contracts
that `init` owns and `start` / `feature` refresh through the same
non-destructive primitive, with parity, preservation, and idempotency proof.
Updated success metrics, scope boundaries, and Loop Mode placement. This
supersedes the peer-mode language in the original REQ-22 and requires a
follow-up ADR to supersede ADR-039. Approved explicitly by the project owner on
2026-07-29 via `/renmark:approve`.

**Revision note (2026-07-29, human-approved diff):** Amended REQ-23 to
distinguish Renmark's host-neutral selector-capable contract from native
clickability, resolve picker availability and capacity per active surface, add
bounded `More` / `Back` / `Cancel` overflow behavior, preserve numbered
fallback and continuation semantics, and cover Codex Plan versus Default mode.
Amended REQ-25 and success metrics so the same concise rule propagates through
managed project contracts and cross-host golden fixtures. M1 delivery-state
scope remains unchanged; interaction implementation begins in M2. Approved
explicitly by the project owner on 2026-07-29 via `/renmark:approve`.

**Revision note (2026-08-01, human-approved diff):** Added REQ-26
(invisible-by-default internal governance — internal execution roles,
handoffs, and governance artifacts stay implementation detail unless they
measurably reduce user effort, inference cost, or failure rate) and REQ-27
(work classification and release-oriented delivery — bounded corrections use
a fast path; substantial builds are planned and delivered as a sequence of
user-testable milestone releases rather than internal-only progress, applying
to every project renmark manages including its own development). Added two
matching Goals bullets and one Non-goals bullet ("not a visible internal
bureaucracy"). Reconciles the product PRD with the internal
governed-orchestration methodology under active design in
`.bootstrap-renmark/` (work package WP-1 of release R-0.0). Proposed by the
General Contractor per the R-0.0 release contract; reviewed and explicitly
approved by the project owner on 2026-08-01 via the `/renmark:prd` UPDATE
gate, including one owner-requested revision (REQ-27 added; a draft open
question about the doctrine staying `.bootstrap-renmark/`-only was removed in
favor of making it a real product requirement).

**Revision note (2026-08-02, human-approved diff):** Added REQ-28
(brownfield transformation entry point — `/renmark:rethink`, a distinct
pipeline for reassessing and transforming an existing application, separate
from `/renmark:start`'s greenfield lane: survey → behavioral baseline →
Keep/Improve/Replace/Remove/Unknown classification → target blueprint →
independently-usable-release roadmap → hand off to renmark's existing
milestone/Agency execution machinery; no structural change before baseline +
classification + first milestone are Owner-approved). Added a matching Goals
bullet. Proposed by `/renmark:feature`'s PRD-alignment gate for the
`add-rethink-pipeline-skill` feature; reviewed and explicitly approved by the
project owner on 2026-08-02 via the `/renmark:prd` UPDATE gate.

**Revision note (2026-08-02, human-approved diff):** Amended REQ-28 to expand
`/renmark:rethink` from a six-stage survey/baseline/classify/blueprint/
roadmap pipeline into a nine-stage evidence-based modernization pipeline.
Renamed to "brownfield modernization entry point." Added: (1) a mandatory
**PRD acceptance contract** stage, distinct from the behavioral baseline —
existing behavior is not treated as correct merely because it exists, and the
transformation cannot be reported complete while an applicable PRD acceptance
criterion is failed, omitted, unverified, or changed without Owner approval;
(2) a mandatory **external discovery and benchmarking** stage, distinct from
the internal survey — sourced, dated, evidence-rated competitor/industry
research that must honestly report `blocked`/`incomplete` when external
access is unavailable rather than substituting model memory; (3) a mandatory
**modularity, scalability, and maintainability assessment**, whose findings
now inform classification and blueprint decisions for `Improve` items too, not
only `Replace` items. Classification decisions must now cite internal, PRD,
external, and modularity evidence. This does not invalidate rethink's prior
approved behavior — the original survey → baseline → classify → blueprint →
roadmap → handoff shape and its Owner-gate, no-production-mutation, and
milestone-handoff guarantees are preserved and extended, not replaced.
Proposed by `/renmark:feature`'s PRD-alignment gate for the
`upgrade-rethink-modernization-pipeline` change; reviewed and explicitly
approved by the project owner on 2026-08-02 via the `/renmark:prd` UPDATE
gate.


**Revision note (2026-08-02, human-approved diff):** Added REQ-29
(evidence-based greenfield entry point — `/renmark:start`'s Complex-scope
builds now run mandatory external discovery, a PRD acceptance/traceability
contract, and a prospective modular blueprint, gated by an explicit
readiness-review approval before any target code is written; Simple-scope
builds carry the same discipline forward as one documented, Owner-approved
waiver inside their existing single confirmation, preserving the
entry-question-plus-2-follow-ups fast path). Explicitly excludes
brownfield-only concerns (system survey, compatibility baseline,
Keep/Improve/Replace/Remove classification) — REQ-29 is the greenfield
counterpart to REQ-28, not a duplicate of it. Added a matching Goals bullet.
Does not invalidate `/renmark:start`'s prior approved behavior for Simple
builds — the entry question, the 2-follow-up cap, and the single-confirmation
gate are preserved and extended, not replaced. Proposed by
`/renmark:feature`'s PRD-alignment gate for the
`upgrade-start-evidence-traceability-modularity` change; reviewed and
explicitly approved by the project owner on 2026-08-02 via the
`/renmark:prd` UPDATE gate.


**Revision note (2026-08-02, human-approved diff):** Amended REQ-29 to split
its single "readiness-review" gate into three distinct, named Owner gates —
the **Discovery Direction Gate** (direction, before the PRD is drafted), the
**Solution Gate** (scope/design, before the roadmap is finalized), and the
**Execution Gate** (the finalized roadmap, before any build task is
dispatched) — and added a cross-cutting **exception check-in** that
interrupts the current stage immediately on a material PRD conflict,
unreliable/blocked research bearing on a live decision, a major cost/scope/
security implication, or a high-impact unknown, rather than waiting for the
next scheduled gate. This is a structural elaboration of REQ-29's existing
discipline, not a new requirement or a reversal: the external-research,
PRD-traceability, and modular-blueprint substance from REQ-29's original
approval is unchanged, and the Simple-scope fast-path waiver (one documented
waiver, no added gate) is preserved exactly as before. Proposed by
`/renmark:feature`'s PRD-alignment gate for the
`upgrade-start-three-gate-structure` change; reviewed and explicitly approved
by the project owner on 2026-08-02 via the `/renmark:prd` UPDATE gate.


**Revision note (2026-08-02, human-approved diff):** Amended REQ-28 to add a
**Transformation Intake** (desired outcome, protected behavior, constraints,
non-goals, areas open to change — Owner-level blocking questions only)
ahead of stage 1, and to thread three named Owner gates through rethink's
existing nine stages at the points where a real decision is made: the
**Discovery Direction Gate** (between stage 5 and stage 6 — direction, not
yet classification), the **Solution Gate** (between stage 7 and stage 8 —
the classification and blueprint, not yet the roadmap), and the **Execution
Gate** (stage 9, elaborated — the finalized roadmap, before any production
code or Agency execution). Added a cross-cutting **exception check-in** that
interrupts the current stage immediately on a material PRD/Owner-intent
conflict, unreliable/blocked research, a major cost/scope/security impact, a
proposed removal of protected behavior, or an unboundable high-impact
unknown, pausing only the affected decision without discarding completed
work. This is a structural elaboration of REQ-28's existing discipline, not a
pipeline redesign: the nine stages, their artifacts, their bounded-subagent
dispatch, the ≤5-line orchestrator-visible summaries, the incremental-roadmap
`Program` format, and the hand-off to renmark's existing Agency/milestone
machinery are all unchanged. No gate's approval may be inferred from silence
or another gate's approval, and no agent may approve its own recommendation.
A resumed run reuses existing stage artifacts and cleared gate decisions
rather than re-dispatching completed work. Proposed by `/renmark:feature`'s
PRD-alignment gate for the `rethink-owner-gate-contract` change; reviewed and
explicitly approved by the project owner on 2026-08-02 via the
`/renmark:prd` UPDATE gate.


**Revision note (2026-08-02, human-approved diff):** Added REQ-30
(orchestration efficiency and UX stability is a protected capability —
renmark's current bounded-dispatch, context-hygiene, deterministic-first,
fast-path, and minimal-Owner-interruption behavior, already specified
piecemeal by REQ-2/REQ-5/REQ-20/REQ-21/REQ-22/REQ-24/REQ-27, is now an
explicit cross-cutting requirement that every pipeline must cite and that
blocks a release on a quantified efficiency regression unless the Owner
grants an explicit, evidence-backed exception with a rollback path). Named
the current release the reference baseline — `ORCHESTRATION-BASELINE-2026-08`
(`v0.39.7`, commit `d9cccc5`) — recorded at
`.renmark/memory/orchestration-baseline.md`, so "preserve current behavior"
points to a dated, versioned artifact rather than becoming subjective later.
Added a matching Goals bullet. This does not restate REQ-2/5/20/21/22/24/27's
mechanics — it protects them from being silently loosened by a future
feature that doesn't realize it's touching orchestration. Proposed by the
project owner directly, motivated by observed token/latency savings from the
current dispatch discipline; reviewed and explicitly approved by the project
owner on 2026-08-02 via the `/renmark:prd` UPDATE gate.


**Revision note (2026-08-02, human-approved diff):** Added REQ-31 (native
task tracking for dispatched work — every dispatching pipeline tracks its
work as native Claude Code tasks, defined once in `${CLAUDE_PLUGIN_ROOT}/
skills/.shared/task-tracking.md` and cited via the existing
`subagent-budget.md` dispatch-packet contract rather than restated per
pipeline: one parent task per milestone, one bounded task per dispatch,
pending → in_progress → completed-with-evidence lifecycle, no worker
self-approval of its own milestone, resume reuses existing tasks instead of
recreating them, and the mechanism adds no Owner gate, question, or
dispatch of its own — informational scaffolding around dispatch, not a
second execution path). Explicitly bound by REQ-30: task tracking must not
regress token/time efficiency or add routine interruptions. Added a matching
Goals bullet. Implemented once in `_shared/task-tracking.md` and wired
through `_shared/subagent-budget.md`'s existing contract rather than
rewriting each pipeline's SKILL.md, per the Owner's explicit instruction to
avoid duplicating the mechanism per pipeline. Proposed by the project owner
directly; reviewed and explicitly approved by the project owner on
2026-08-02 via the `/renmark:prd` UPDATE gate.

**Revision note (2026-08-02, human-approved diff):** Amended REQ-31 to
require and name a real, host-independent Python enforcement layer —
`renmark.task_tracking` (`.renmark/state/tasks.json`) — wired into the
actual per-task dispatch call site in `renmark.cli._engine.execute_plan`'s
`_runner`: one native parent task per plan run, one worker task per
dispatched task, one linked verification task per worker (dispatched under
the same `_INSPECTOR_DISPATCH_IDENTITY` R-0.4 already uses), and
`complete_worker_task` mechanically enforcing no-self-approval by reusing
`renmark.ledger.check_dispatch_independence` rather than trusting an
asserted flag. This closes the gap the first REQ-31 revision left open — a
markdown contract describing intended behavior with only content-presence
tests proving the contract text existed, not that any dispatch actually
created, updated, or completed a task under enforced invariants. The
skill-level `task-tracking.md` guidance (native Claude Code Task tools for
live in-session dispatch) is unchanged; this adds the mechanically verified
backing for `/renmark:orchestrate`'s actual dispatch loop specifically, with
real unit tests (`tests/test_task_tracking.py`) and real dispatch-loop
integration tests (`tests/test_task_tracking_engine_wiring.py`) replacing
content-presence-only proof. Every `task_tracking` call site in the engine
is best-effort/never-raising, matching the existing ledger-emission
convention, so this addition carries zero dispatch/commit-path regression
risk. Proposed by the project owner directly, in response to a Stop-hook
rejection of the prior revision for providing specification without
enforcement; reviewed and explicitly approved by the project owner on
2026-08-02 via the `/renmark:prd` UPDATE gate.

**Revision note (2026-08-02, human-approved diff):** Corrected REQ-31's
second revision, which had conflated two distinct mechanisms into one
sentence in a way a reader could mistake `renmark.task_tracking`'s Python
state file for satisfying "create a native Claude Code task using the
available Task tools." REQ-31 now names them explicitly as separate,
non-substitutable: (i) the live host's own `TaskCreate`/`TaskUpdate` —
satisfied only by the executing agent's real tool calls in an interactive
session, which is the sole mechanism requirement 1 names, and (ii)
`renmark.task_tracking`, scoped strictly to the one dispatch path with no
live session at all (`renmark.cli._engine.execute_plan`'s headless
`codex`/subprocess executor). Mechanism (ii) never substitutes for (i).
Graceful degradation (requirement 12) is now scoped to genuinely tool-less
paths only — an interactive session always has the tools and must use them.
`task-tracking.md`, `subagent-budget.md`, and `orchestrate/SKILL.md` were
reworded from descriptive ("track dispatches per...") to imperative ("call
`TaskCreate` yourself") to remove the ambiguity. No change to the module,
its engine wiring, or its tests from the prior revision — this corrects
which requirement they satisfy, not their behavior. Proposed by the project
owner directly, in response to a second Stop-hook rejection identifying that
the fix for the first rejection still did not name the live host tools as
the actual requirement-1 mechanism; reviewed and explicitly approved by the
project owner on 2026-08-02 via the `/renmark:prd` UPDATE gate.

**Revision note (2026-08-04, human-approved diff):** Pre-authorizes the
rethink-architecture roadmap's Release 6 (`cost.resolve_executor(task)` —
centralizing the ~12 scattered model/executor-routing call sites in `cli/`,
`dispatch.py`, `plan_lint.py`, `codex_routing.py`, `subagent_profiles.py`,
and others behind one seam in `cost.py`) as an exception under REQ-30(i)'s
"any change to orchestration routing... requires an explicit PRD change and
Owner approval" clause, and REQ-30's regression-protection exception path
("quantified evidence, explicit Owner approval, a documented benefit, and a
rollback path"). Documented benefit: a new executor tier drops from 4+
uncoordinated touch points to one provider adapter + one branch in
`cost.resolve_executor`. Quantified evidence required before any call site
is migrated: a golden before/after routing-decision test proving
byte-identical tier selection for a representative task sample, run before
and after each migrated call site, plus the standing full-suite
compatibility guarantee (currently 1936 passed/31 skipped). `cost.py`
remains a leaf — `resolve_executor` reads only `config`/`hosts`-level
arguments, never imports `dispatch`/`_engine`/`subagent_profiles`, so
callers depend on `cost.py`, not the reverse (no new cycle). Rollback:
revert per-call-site commit; `cost.py`'s pre-existing routing functions are
untouched until each caller is proven byte-identical and migrated. REQ-2's
routed executor set (Haiku/Codex/Sonnet/Opus/Fable) and REQ-30's Owner-gate/
dispatch-count/context guarantees are unaffected — this is a call-graph
consolidation, not a policy change. Proposed by the renmark-architecture
rethink roadmap's Release 6; reviewed and explicitly approved by the
project owner on 2026-08-04 via the `/renmark:prd` UPDATE gate.

---
artifact_type: feature-request
schema_version: 1
created_at: 2026-07-02T00:00:00Z
source_sha: 4fb7ae960ada24e6087c681d4107597a1b776e29
related_plan: null
generator: feature
status: queued
depends_on: cost-control-finish-lanes
stale_after: null
dependency_refs:
  - .renmark/memory/features.md
  - renmark/mode.py
  - plugin/skills/_shared/context-taxonomy.md
---

# Agency Mode — queued feature request

**Status:** QUEUED on the roadmap (2026-07-02). **Blocked by:** the
`cost-control-finish-lanes` feature (finish lanes, model-routing discipline,
subagent budgets, context thresholds, cost previews) — Agency Mode is explicitly
designed to *reuse* that infrastructure, so it must ship first.

**Do NOT build yet.** When picked up, the first deliverable is a spec/plan that
answers the design questions below and defines the smallest MVP — not a large
implementation.

## Core goal

Evolve Renmark into an agency-style agentic-engineering harness on top of Claude
Code. Agency Mode sits **above** Conductor and Orchestrator and does **not**
replace them:

- **Conductor** = hands-on, small-step work.
- **Orchestrator** = goal-level multi-agent execution.
- **Agency Mode** = full project-delivery loop, like hiring a software agency.

In Agency Mode the owner gives intent, approves direction, reviews demos, makes
owner-level decisions, and signs off milestones. Renmark manages the
product-development lifecycle behind the scenes:

Discovery → PRD agreement → tech-stack recommendation → roadmap/milestones →
implementation loops → demos → feedback → roadmap updates → verification → final
signoff → release/maintenance.

## Design questions to answer FIRST (before any implementation)

1. Is Agency Mode best implemented as a third persisted mode in `renmark/mode.py`,
   or as a higher-level project workflow that uses Orchestrator internally?
2. Which Renmark pipelines should become Agency-aware?
3. What should each pipeline do differently when Agency Mode is active?
4. What skills/fragments should be loaded or referenced in Agency Mode?
5. How does Agency Mode reuse the cost-control infrastructure?
6. How do we avoid loading every full skill body into context while still making
   every relevant pipeline Agency-aware?

## Agency Mode behavior

- Ask what the owner wants built; clarify goal, users, constraints, risks, success
  criteria. Avoid unnecessary technical questions; ask only owner-level decisions.
- Produce/update a PRD; owner approves before major build; PRD stays source of truth.
- Recommend a practical tech stack based on intent; explain tradeoffs simply; avoid
  overcomplicated stacks.
- Create a roadmap with milestones, checkpoints, demos, and signoff points.
- Continue working until the next milestone instead of constantly stopping.
- Use background agents for research, implementation, tests, docs, verification,
  review; one main agent communicates with the owner directly.
- Show progress at milestone checkpoints; convert feedback into updated tasks,
  roadmap changes, or new milestones; continue until final signoff.

## Inference & tooling behavior (reuses cost-control infra)

- Prefer free/local/cheaper inference; use stronger/paid models only when required.
- Show token/cost estimates before expensive work.
- Use web research when current information is needed.
- Use Playwright/browser automation for UI verification or web interaction.
- Keep work modular, nimble, minimally scoped; use finish lanes correctly; use
  milestone-level budgets.

## Per-pipeline Agency behavior to define

- **/renmark:start** — Agency discovery entry: discovery call, project intent,
  user/customer/problem, outcome definition, owner-level questions, project
  classification (new app / feature / migration / automation / research-build).
- **/renmark:prd** — Agency agreement point: PRD create/update, owner approval,
  source-of-truth locking, change control when feedback changes the project.
- **/renmark:roadmap** — milestones, checkpoints, demo points, signoff points,
  sequencing, risk & dependency mapping.
- **/renmark:feature** — select next milestone/feature from roadmap; PRD-alignment
  check; avoid isolated one-off drift; update roadmap/PRD if feedback changes scope.
- **/renmark:plan** — atomic tasks, cost preview, executor/model routing,
  verification criteria, milestone acceptance criteria.
- **/renmark:orchestrate** — background agents, scoped subagent packets, cheap/free
  inference where possible, progress summaries, continue-until-checkpoint behavior.
- **/renmark:verify** — tests, browser/Playwright checks when relevant, what passed,
  what remains unverified, readiness for demo.
- **/renmark:codereview** — full review before signoff, risk findings, merge
  readiness, no premature "done".
- **/renmark:finish** — milestone demo summary, owner feedback, owner signoff,
  release/merge decision, finish-lane selection, roadmap update on new feedback,
  next-milestone recommendation.
- **/renmark:resume** — resume from last milestone/checkpoint, summarize where we
  left off, continue without re-discovering everything.

## Skill-loading requirement

Make every relevant pipeline Agency-aware without loading every full skill body:

- Agency metadata upfront; full Agency instructions load only when Agency Mode is
  active; pipeline-specific Agency behavior loads on demand.
- Shared Agency contract in a `_shared` fragment if appropriate.
- Subagents receive only the agency context needed for their task; avoid bloat.

Possible approach: add an `agency-delivery` shared fragment; add Agency Mode blocks
to relevant `SKILL.md` files; add mode-conditioned preamble behavior; add
lightweight agency project state (current phase, current milestone, next checkpoint,
signoff status, budget/cost lane, roadmap link).

## Non-goals (first pass)

Do not rebuild Conductor, Orchestrator, dynamic skill loading, live eval runner,
agent-turn runner, Codex routing, existing verification system, or cost-control
infra. Do not turn this into a giant implementation immediately — produce the
spec/plan and smallest MVP first.

## MVP candidate

1. Add Agency as a third mode or higher-level delivery mode.
2. Add Agency-aware behavior to /start, /prd, /roadmap, /feature, /plan,
   /orchestrate, /verify, /finish, /resume.
3. Add shared Agency delivery contract.
4. Add lightweight agency project state.
5. Reuse cost-control infrastructure.
6. Update help output.
7. Add tests proving Agency Mode changes preamble/pipeline behavior without loading
   all skill bodies.

## Reuses these primitives (from cost-control-finish-lanes)

Agency Mode MUST reuse — not re-implement — the following infrastructure shipped in `cost-control-finish-lanes` (acceptance criterion 8 of this feature):

- `renmark/finish_lanes.py` — lane selection logic (quick/release/self-update/full); Agency finish uses `recommend_lane()` (+ `resolve_lane()` for explicit overrides) to pick the cheapest-safe lane per milestone.
- `renmark/cost.py` — `estimate_cost()` for pre-dispatch cost previews; `requires_escalation()` to gate Opus/Fable use; Agency mode shows cost band before any expensive multi-agent wave.
- `renmark.state.skills.context_budget_hint` — absolute token-count thresholds (100k/120k/150k); Agency mode's long delivery loops MUST respect these checkpoints.
- `renmark/subagent_profiles.py` — specialized role profiles; Agency background agents pick a specialized profile (general-purpose fallback-only) and inherit its narrow context/tier.
- `plugin/skills/_shared/model-routing.md` — executor tier rules; Agency agents inherit the same Haiku/Sonnet/Codex/Opus/Fable discipline.
- `plugin/skills/_shared/subagent-budget.md` — scoped subagent packet contract; all Agency background agents follow this format.
- `plugin/skills/_shared/finish-lanes.md` — lane descriptions; Agency finish step references this fragment.
- `plugin/skills/_shared/cost-preview.md` — cost-preview display contract; Agency pre-wave display follows this format.

## Acceptance criteria

1. Clear Agency Mode definition.
2. Does not replace Conductor or Orchestrator.
3. Affected pipelines clearly defined.
4. Uses dynamic skill loading, not loading every skill body.
5. Reuses cost-control and finish-lane infrastructure.
6. Supports discovery → PRD → roadmap → milestones → build → demo → feedback → signoff.
7. Owner-level questions, not unnecessary technical questions.
8. Main agent communicates while background agents do scoped work.
9. Milestones/checkpoints persisted and resumable.
10. Help/docs explain Agency Mode clearly.
11. Tests/behavior checks prove Agency Mode changes Renmark behavior.

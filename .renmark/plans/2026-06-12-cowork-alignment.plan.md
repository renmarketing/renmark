---
artifact_type: plan
schema_version: 1
created_at: 2026-06-12T15:30:00+00:00
source_sha: HEAD
related_spec: Cowork operating-instructions alignment exercise (2026-06-12 session)
generator: fable
dependency_refs: [plugin/skills/_shared/reasoning-contract.md]
---

# cowork-alignment — four agent-discipline improvements

**Goal:** port the four gaps the Cowork-alignment exercise surfaced into renmark contracts:
(1) a **reuse/inventory check** — "check what already exists before proposing a custom
build" — wired into brainstorm and plan, dispatched as a cheap subagent returning a
bounded "what already covers this" verdict; (2) an explicit **push-back-by-default /
no-sycophancy** stance line in the shared reasoning contract; (3) a **surface-contradictions
-before-overwriting** reflex extending the CHANGELOG "Do not change" guard into a softer
"this conflicts with a prior decision — reconcile?" check; (4) a **re-interview-on-premise
-change** move in brainstorm/feature re-entry instead of silently continuing from state.

All prose/doc + one new shared reference; no Python or schema changes. Bounded subagent
returns honor REQ-5; the reuse-check is a delegation (REQ-5), not orchestrator work.

### Task 1: reuse-check shared contract
- **mode:** A
- **target:** plugin/skills/_shared/reuse-check.md
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 1
- **est_tokens:** 600
- **est_cost_usd:** 0.032
- **verifier:** grep -qi 'already exists' plugin/skills/_shared/reuse-check.md && grep -qi 'bounded' plugin/skills/_shared/reuse-check.md
- **serves:** REQ-1
- **spec:**
  NEW shared reference file, modeled structurally on plugin/skills/_shared/prd-alignment.md
  (header: what it is + who consumes it; why-a-subagent; the bounded return format; a
  citable dispatch blockquote; why-a-shared-file closer). Content: the reuse-check is a
  cheap subagent (haiku by default; sonnet for a large search surface) dispatched BEFORE a
  skill proposes a custom build. It searches, in its own context: (a) loaded renmark skills
  + commands (the registry), (b) available MCP connectors/tools surfaced in the session,
  (c) prior specs under `.renmark/specs/` and plans under `.renmark/plans/`, (d)
  `.renmark/memory/features.md` (already-shipped features). It returns a bounded ≤5-line
  verdict: `reuse: found | none` + for `found`, a one-line pointer to the existing
  skill/MCP/spec/feature that already covers the request (path or name). The consuming
  skill surfaces it and defaults to reuse unless there's a clear reason to build custom —
  "report findings before proposing custom work." Honors REQ-5 (orchestrator reads only the
  bounded verdict, never the searched bodies) and carries the reasoning-contract citation.
  Provide ONE citable blockquote skills paste (like prd-alignment's Dispatch reference).
  Note `_shared/` is linter-skipped.

### Task 2: reasoning-contract — push-back stance + no sycophancy
- **mode:** B
- **target:** plugin/skills/_shared/reasoning-contract.md
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 1
- **est_tokens:** 250
- **est_cost_usd:** 0.001
- **verifier:** grep -qi 'sycophancy\|push back\|disagree' plugin/skills/_shared/reasoning-contract.md
- **serves:** REQ-1
- **spec:**
  Additive — add a short "Stance" clause to the canonical instruction body AND fold a
  pointer into the citable blockquote so every dispatched agent carries it: "Push back by
  default — disagree when the request is off-strategy, technically wrong, or inconsistent
  with a prior decision on file; flag tradeoffs the asker may not have weighed. No
  sycophancy: do not open with affirmation ('great idea', 'you're right') unless you mean
  it after reasoning it through. Surfacing a contradiction or a question is cheaper than
  silently proceeding on a bad premise." Keep it tight (the contract stays scannable); do
  not duplicate the existing multi-perspective/blocking-vs-deferrable text — this is a new
  stance bullet, not a rewrite. The canonical text stays single-sourced here.

### Task 3: brainstorm — reuse-check + re-interview-on-change
- **mode:** B
- **target:** plugin/skills/brainstorm/SKILL.md
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 2
- **est_tokens:** 500
- **est_cost_usd:** 0.032
- **verifier:** grep -qi 'reuse-check' plugin/skills/brainstorm/SKILL.md && grep -qi 're-interview\|re-establish' plugin/skills/brainstorm/SKILL.md
- **serves:** REQ-1
- **spec:**
  Two additive edits. (1) Before Step 4 (propose approaches): add a **reuse check** —
  dispatch the reuse-check subagent per `${CLAUDE_PLUGIN_ROOT}/skills/_shared/reuse-check.md`
  (cite, don't paste) and surface its bounded verdict; if `found`, lead with the existing
  thing and require a clear reason before proposing a custom build. This pairs with the
  existing Step 3 prior-art research (external) — reuse-check is the *internal/in-reach*
  counterpart. (2) Re-entry note (Step 0 or the discovery preamble): if the user signals
  the premise changed ("things changed", "actually, scope is different now"), **re-establish
  the scope contract** (re-ask the changed Q1–Q3) rather than continuing from the persisted
  spec/stack — name the conflict and reconcile. Preserve frontmatter; don't touch the
  one-question-at-a-time flow otherwise.

### Task 4: plan — reuse-check + contradiction-reconcile reflex
- **mode:** B
- **target:** plugin/skills/plan/SKILL.md
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 2
- **est_tokens:** 500
- **est_cost_usd:** 0.032
- **verifier:** grep -qi 'reuse-check' plugin/skills/plan/SKILL.md && grep -qi 'reconcile' plugin/skills/plan/SKILL.md
- **serves:** REQ-1
- **spec:**
  Two additive edits. (1) In Step 1 (read the spec) or Step 0, before decomposition: a
  **reuse check** — dispatch the reuse-check subagent (cite
  `${CLAUDE_PLUGIN_ROOT}/skills/_shared/reuse-check.md`) and, on `found`, surface it so the
  plan can reuse rather than re-decompose a custom build. (2) Strengthen the existing
  CHANGELOG "Do not change" read (Step 1 already reads the last 5 entries): make it an
  explicit **contradiction-reconcile reflex** — when a task in the proposed plan would
  contradict a "Do not change" guard OR a recorded decision, do NOT silently proceed; name
  the conflict to the user ("this is different from <what's on file> — reconcile?") and
  resolve before writing the plan. Preserve frontmatter; the dispatch-gate ownership rules
  (§8b) are unchanged.

### Task 5: orchestrate — contradiction reflex in changelog check
- **mode:** B
- **target:** plugin/skills/orchestrate/SKILL.md
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 2
- **est_tokens:** 250
- **est_cost_usd:** 0.001
- **verifier:** grep -qi 'reconcile\|conflicts with' plugin/skills/orchestrate/SKILL.md
- **serves:** REQ-1
- **spec:**
  In the pre-flight Changelog check ("read the last 3 entries; flag any 'Do not change'
  guards that overlap with the plan's target files"), extend with one line: if an overlap
  is a genuine **contradiction** (the plan would undo/overwrite a guarded decision), surface
  it and pause for reconciliation BEFORE dispatching — never silently overwrite a recorded
  decision. (Pre-flight already flags; this makes the flag a stop-and-reconcile, not just a
  note.) No other changes; RED-FLAG and reroute/fallback sections untouched.

### Task 6: feature — re-interview on premise change
- **mode:** B
- **target:** plugin/skills/feature/SKILL.md
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 2
- **est_tokens:** 250
- **est_cost_usd:** 0.001
- **verifier:** grep -qi 're-interview\|premise changed\|re-establish' plugin/skills/feature/SKILL.md
- **serves:** REQ-1
- **spec:**
  Additive note in the router flow (near Step 2 PRD alignment / Step 3 plan handoff): if the
  user signals the premise changed mid-feature ("things changed", a materially different
  description than the branch was opened for), the router **re-runs PRD alignment and
  re-establishes scope** rather than continuing the persisted pipeline silently — surface
  the shift, reconcile, then proceed. The router stays a router (no planning/coding); this
  is a re-entry guard, not new reasoning. Preserve frontmatter.

### Task 7: CLAUDE.md — reuse + stance rule pointers
- **mode:** B
- **target:** CLAUDE.md
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 2
- **est_tokens:** 250
- **est_cost_usd:** 0.001
- **verifier:** grep -qi 'reuse-check' CLAUDE.md
- **serves:** REQ-1
- **spec:**
  Add a short rule block (or extend an existing one) with two pointer lines: (a)
  "Before proposing a custom build, run the reuse check — see
  plugin/skills/_shared/reuse-check.md (check loaded skills, MCP connectors, prior
  specs/plans, features.md; default to reuse)." (b) "Dispatched agents push back by
  default and skip sycophancy — see plugin/skills/_shared/reasoning-contract.md."
  MIRROR: Task 8 applies the byte-identical block to the CLAUDE template. AGENTS.md mirror
  pair — if a matching anchor exists in AGENTS.md add it there too in this same task
  (CLAUDE.md and AGENTS.md are the mirror pair; keep shared wording byte-identical).

### Task 8: CLAUDE.md.template — mirror of Task 7
- **mode:** B
- **target:** plugin/templates/CLAUDE.md.template
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 2
- **est_tokens:** 200
- **est_cost_usd:** 0.001
- **verifier:** grep -qi 'reuse-check' plugin/templates/CLAUDE.md.template
- **serves:** REQ-1
- **spec:**
  Apply Task 7's exact pointer lines to the CLAUDE template (byte-identical wording). If the
  AGENTS.md.template carries the matching rule-block anchor, mirror there too; otherwise add
  nothing without an anchor. Only template files in this task.

## Cost preview

| # | Task | Executor | est_tokens | est cost |
|---|---|---|---|---|
| 1 | reuse-check contract (new) | sonnet | 600 | $0.032 |
| 2 | reasoning-contract stance | haiku | 250 | $0.001 |
| 3 | brainstorm reuse + re-interview | sonnet | 500 | $0.032 |
| 4 | plan reuse + reconcile | sonnet | 500 | $0.032 |
| 5 | orchestrate reconcile | haiku | 250 | $0.001 |
| 6 | feature re-interview | haiku | 250 | $0.001 |
| 7 | CLAUDE.md pointers | haiku | 250 | $0.001 |
| 8 | CLAUDE template mirror | haiku | 200 | $0.001 |

Haiku/sonnet costs include the ~10k-token Agent overhead per task (honest accounting).
**Total: ~$0.13 · ~82k tokens incl. overhead · 8 tasks (wave 1: 2 parallel, wave 2: 6 parallel)**

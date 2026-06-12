---
artifact_type: plan
schema_version: 1
created_at: 2026-06-11T19:30:00+00:00
source_sha: 9b49afd
related_spec: .renmark/research/2026-06-11-fable-routing-strategy.md
generator: fable
part: 2 of 2
dependency_refs: [.renmark/plans/2026-06-11-fable-routing-part1.plan.md]
---

# fable-routing — Part 2: skill surfaces, declarations, busy-work demotions

**Depends on Part 1** (capabilities.py + gates exist and are test-pinned). This part
wires the declared-capability strategy into the skill prose surfaces and ships the
phase-0 busy-work demotions. Canonical resolution language (reuse verbatim where a
surface explains the flag): *"top tier is declared, never detected: `top_tier: fable`
in `.renmark/memory/routing.md` (## Model tiers), set once via init/setup/doctor,
per-user override `RENMARK_TOP_TIER`; absent → opus, byte-identical pre-Fable behavior."*

**Judge-pinned pitfalls (from the strategy decision record — honor in every spec):**
no per-checkpoint fable Agent calls inside interactive loops; the Model tiers block is
hand-curated and `memory.append_routing` never touches it; every fable→opus fallback is
LOGGED (append_routing + wave summary), never silent; keep "Fable 5 when available,
Opus otherwise" as the single user-facing formula.

### Task 1: orchestrate SKILL — logged fable→opus fallback
- **mode:** B
- **target:** plugin/skills/orchestrate/SKILL.md
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 1
- **est_tokens:** 400
- **est_cost_usd:** 0.031
- **verifier:** grep -qi 'fallback' plugin/skills/orchestrate/SKILL.md
- **serves:** REQ-2
- **spec:**
  In Step 3b where Agent-dispatch executors are described (the fable dispatch row + the
  "For executor: haiku | sonnet | opus | fable tasks" prose added 2026-06-11), add the
  fallback contract: when an Agent call with `model: "fable"` errors on dispatch
  (model unavailable / rejected), retry ONCE with no model override (opus tier), record
  `fallback: fable→opus` in that task's wave-summary entry (dependency_notes or a
  dedicated note field), and log it via `memory.append_routing` so repeated fallbacks
  become routing evidence — never silent. Exactly one retry; a second failure is an
  ordinary task FAIL. Also note: orchestrate's pre-flight already runs plan_lint, whose
  fable gates (declared/mechanical) make an undeclared fable dispatch unreachable in the
  normal flow — the fallback is defense-in-depth. Do NOT alter the codex RED-FLAG rules.

### Task 2: plan SKILL — declaration-aware fable row
- **mode:** B
- **target:** plugin/skills/plan/SKILL.md
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 1
- **est_tokens:** 400
- **est_cost_usd:** 0.031
- **verifier:** grep -qi 'top_tier' plugin/skills/plan/SKILL.md
- **serves:** REQ-2
- **spec:**
  Three edits. (1) Step 4 routing table fable row: append "— only in projects with a
  declared `top_tier: fable` (plan_lint BLOCKs it otherwise)". (2) Step 4 complexity
  mapping line: extend the existing "fable is never auto-assigned by complexity alone"
  clause with "and never assigned at all in undeclared projects (capabilities.top_tier)".
  (3) Step 6 cost table fable row notes cell: append "; renders fable→opus when
  undeclared". Preserve frontmatter quoting; do NOT touch the frontmatter description
  (it was reconciled 2026-06-11 — escalation wording is current).

### Task 3: brainstorm SKILL — research demotion + tier hint
- **mode:** B
- **target:** plugin/skills/brainstorm/SKILL.md
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 1
- **est_tokens:** 500
- **est_cost_usd:** 0.032
- **verifier:** grep -qi 'model: sonnet' plugin/skills/brainstorm/SKILL.md || grep -qi 'sonnet subagent' plugin/skills/brainstorm/SKILL.md
- **serves:** REQ-2
- **spec:**
  Two edits, additive. (1) Step 3 (prior-art research): restructure the instruction so
  the 2–4 WebSearch/WebFetch/Context7 queries run inside PARALLEL `model: sonnet`
  subagents (single-message multi-Agent dispatch per the parallelism rule), each writing
  its findings into the `.renmark/research/` artifact and returning ONLY a ≤5-line
  summary — the session brain reads the summaries and synthesizes in Step 4. This keeps
  web busywork off the top tier (it currently runs inline at session price). (2) Step 0:
  note that `skill_preamble` now surfaces the declared-tier hint ("declared top tier:
  fable — … /model fable") and the skill should surface it verbatim like other hints.
  Do NOT change the one-question-at-a-time interactive flow (no per-checkpoint fable
  Agent calls — judge-pinned). Preserve frontmatter quoting/description.

### Task 4: blueprint SKILL — prototype bulk demotion
- **mode:** B
- **target:** plugin/skills/blueprint/SKILL.md
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 1
- **est_tokens:** 400
- **est_cost_usd:** 0.031
- **verifier:** grep -qi 'codex' plugin/skills/blueprint/SKILL.md
- **serves:** REQ-2
- **spec:**
  In the PROTOTYPE.html generation step (Step 3b or equivalent — find where the HTML
  mockup is authored): split it into (a) the session brain writes a ~10-line design spec
  (layout, sections, IA, palette tokens) and (b) the bulk HTML/CSS emission is dispatched
  to codex via `renmark-execute --task` (or a codex-tagged task) consuming that spec —
  bulk markup is codex's designated role per routing defaults; only the design judgment
  stays on the top tier. The Mermaid SCHEMATIC step stays inline (sonnet-grade,
  already-distilled input; note "never escalate this step"). Keep the
  no-invented-nodes/marker-splice contracts unchanged.

### Task 5: shared prd-alignment — haiku pin
- **mode:** B
- **target:** plugin/skills/_shared/prd-alignment.md
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 1
- **est_tokens:** 300
- **est_cost_usd:** 0.031
- **verifier:** grep -qi 'haiku' plugin/skills/_shared/prd-alignment.md
- **serves:** REQ-2
- **spec:**
  In "What the router dispatches": pin the Agent call to `model: "haiku"` by default —
  bounded read-and-summarize is haiku-grade; today the subagent inherits the session
  tier (Fable-priced PRD reads). Add the size escalation: when `PRD.md` exceeds ~800
  lines, dispatch on `model: "sonnet"` instead (a haiku verdict on a large PRD risks
  missed drift on the gate whose purpose is drift detection). Update the Dispatch
  reference blockquote (the text skills cite) to carry the model pin so callers can't
  drift. Keep the ≤5-line verdict contract unchanged.

### Task 6: init SKILL — declaration question
- **mode:** B
- **target:** plugin/skills/init/SKILL.md
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 1
- **est_tokens:** 400
- **est_cost_usd:** 0.031
- **verifier:** grep -qi 'top_tier' plugin/skills/init/SKILL.md
- **serves:** REQ-2
- **spec:**
  Add a one-time declared-capability step to the scaffold/back-fill flow: when
  `.renmark/memory/routing.md` exists (or is being created) and has NO `## Model tiers`
  block, ask once via AskUserQuestion: "Do you have Claude Fable 5 access for this
  project? [Yes → top_tier: fable / No → top_tier: opus]" and write the block (grammar:
  `## Model tiers` / `top_tier: <answer>` / `declared_at: <date>`) ABOVE the Learned
  overrides section. Idempotent: an existing block is never overwritten (init reports it
  instead). Non-interactive runs default to opus (safe). Note that `/renmark:setup`
  inherits this via its delegation to init's rule-block merge.

### Task 7: doctor SKILL — declaration report
- **mode:** B
- **target:** plugin/skills/doctor/SKILL.md
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 1
- **est_tokens:** 250
- **est_cost_usd:** 0.001
- **verifier:** grep -qi 'top_tier' plugin/skills/doctor/SKILL.md
- **serves:** REQ-2
- **spec:**
  Add one diagnostic row to doctor's checks: report the current Model tiers declaration —
  `top_tier: fable|opus|(undeclared → opus)` resolved via `renmark.capabilities.top_tier`,
  plus whether RENMARK_TOP_TIER is overriding the file. Advisory only (no --fix write in
  this pass beyond suggesting /renmark:init for the declaration question). Follow the
  existing check-row format in the file.

### Task 8: codereview + audit SKILLs — declaration-aware escalation wording
- **mode:** B
- **target:** plugin/skills/codereview/SKILL.md
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 1
- **est_tokens:** 200
- **est_cost_usd:** 0.001
- **verifier:** grep -qi 'top_tier' plugin/skills/codereview/SKILL.md
- **serves:** REQ-2
- **spec:**
  One-line amendment to the fable adversarial-escalation note added 2026-06-11: the
  fable refutation subagents apply "in projects with a declared `top_tier: fable`
  (renmark.capabilities); undeclared projects use opus for the same passes." No other
  changes; frontmatter untouched.

### Task 9: audit SKILL — same declaration-aware wording
- **mode:** B
- **target:** plugin/skills/audit/SKILL.md
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 1
- **est_tokens:** 200
- **est_cost_usd:** 0.001
- **verifier:** grep -qi 'top_tier' plugin/skills/audit/SKILL.md
- **serves:** REQ-2
- **spec:**
  Same one-line amendment as Task 8 applied to audit's Step 2b fable routing note
  (added 2026-06-11): refutation subagents route to fable "in projects with a declared
  `top_tier: fable`; undeclared projects run the same passes on opus." No other changes.

### Task 10: routing.md template — Model tiers default block
- **mode:** B
- **target:** plugin/templates/memory/routing.md.template
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 2
- **est_tokens:** 150
- **est_cost_usd:** 0.001
- **verifier:** grep -q 'top_tier' plugin/templates/memory/routing.md.template
- **serves:** REQ-2
- **spec:**
  Add the `## Model tiers` section ABOVE the Learned overrides section with the safe
  default plus an opt-in comment:
  `## Model tiers` / `top_tier: opus` / `declared_at: {{DATE}}` /
  `<!-- Set top_tier: fable if this project's sessions have Claude Fable 5 access; -->` /
  `<!-- /renmark:init asks this once. Hand-curated — append_routing never edits it. -->`
  If the template file lives at a different path (check plugin/templates/ for the
  routing template), apply there; if NO routing template exists, create it minimal with
  just this block following the root routing.md's format conventions.

### Task 11: project routing.md — declare fable here
- **mode:** B
- **target:** .renmark/memory/routing.md
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 2
- **est_tokens:** 120
- **est_cost_usd:** 0.001
- **verifier:** python3 -c "from renmark.capabilities import is_top_tier_declared; from pathlib import Path; assert is_top_tier_declared(Path('.'))"
- **serves:** REQ-2
- **spec:**
  This project's sessions run on Fable 5 (the owner declared it) — add the block ABOVE
  the `## Defaults` section: `## Model tiers` / `top_tier: fable` /
  `declared_at: 2026-06-11`. Touch nothing else (Defaults and Learned overrides stay
  byte-identical).

### Task 12: CLAUDE.md pointer line
- **mode:** B
- **target:** CLAUDE.md
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 2
- **est_tokens:** 150
- **est_cost_usd:** 0.001
- **verifier:** grep -q 'top_tier' CLAUDE.md
- **serves:** REQ-2
- **spec:**
  In the "## Executor preferences" Defaults list, amend the Frontier-reasoning fable row
  (added 2026-06-11) by appending: " — default for those roles when `top_tier: fable` is
  declared in `.renmark/memory/routing.md` (## Model tiers); escalation-only otherwise".
  MIRROR: Task 13 applies the byte-identical edit to AGENTS.md in the same wave — do not
  paraphrase.

### Task 13: AGENTS.md mirror of Task 12
- **mode:** B
- **target:** AGENTS.md
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 2
- **est_tokens:** 100
- **est_cost_usd:** 0.001
- **verifier:** grep -qi 'fable' AGENTS.md
- **serves:** REQ-2
- **spec:**
  Mirror Task 12's exact appended wording into AGENTS.md WHERE the anchor exists
  (AGENTS.md carried only the tooling row as of 2026-06-11 — if no Executor-preferences
  fable row exists, add nothing; the verifier then passes via the existing tooling row).
  Byte-identical wording with CLAUDE.md wherever both carry the block.

### Task 14: CLAUDE.md.template + AGENTS.md.template pointer
- **mode:** B
- **target:** plugin/templates/CLAUDE.md.template
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 2
- **est_tokens:** 150
- **est_cost_usd:** 0.001
- **verifier:** grep -q 'top_tier' plugin/templates/CLAUDE.md.template
- **serves:** REQ-2
- **spec:**
  Apply Task 12's exact appended wording to the template's Frontier-reasoning
  preferences row (present since 2026-06-11). ONLY this template file in this task
  (one file per task); the AGENTS template carried no preferences row, so it needs no
  edit — verified by Task 13's anchor rule.

## Cost preview — Part 2

| # | Task | Executor | est_tokens | est cost |
|---|---|---|---|---|
| 1 | orchestrate fallback | sonnet | 400 | $0.031 |
| 2 | plan SKILL rows | sonnet | 400 | $0.031 |
| 3 | brainstorm demotion | sonnet | 500 | $0.032 |
| 4 | blueprint split | sonnet | 400 | $0.031 |
| 5 | prd-alignment pin | sonnet | 300 | $0.031 |
| 6 | init declaration Q | sonnet | 400 | $0.031 |
| 7 | doctor report row | haiku | 250 | $0.001 |
| 8 | codereview wording | haiku | 200 | $0.001 |
| 9 | audit wording | haiku | 200 | $0.001 |
| 10 | routing template | haiku | 150 | $0.001 |
| 11 | project declaration | haiku | 120 | $0.001 |
| 12 | CLAUDE.md pointer | haiku | 150 | $0.001 |
| 13 | AGENTS.md mirror | haiku | 100 | $0.001 |
| 14 | CLAUDE template | haiku | 150 | $0.001 |

Haiku/sonnet costs include the ~10k-token Agent overhead per task (honest accounting).
**Part 2 total: ~$0.20 · ~144k tokens incl. overhead · 14 tasks (wave 1: 9 parallel, wave 2: 5 parallel)**

---

**Feature total (both parts): 23 tasks · ~$0.42 · executors: haiku×9, codex×5, sonnet×9,
opus×0, fable×0** — REQ-2's cheapest-capable rule applies to renmark's own build; no task
here needs fable itself (the strategy work was already done at decision time).

---
artifact_type: plan
schema_version: 1
created_at: 2026-06-12T16:30:00+00:00
source_sha: HEAD
related_spec: External PRD-generator framework alignment exercise (2026-06-12 session)
generator: fable
dependency_refs: [plugin/skills/_shared/reuse-check.md]
---

# prd-template-enrichment — surgical PRD upgrade

**Goal:** enrich renmark's product-PRD template and the prd SKILL with 5 additive pieces
harvested from an external PRD-generator framework, WITHOUT importing the sections that
duplicate the pipeline. The PRD stays a lean, product-level, human-owned source of truth
(REQ-4). The five additions: (1) **optional** requirement sub-categories incl. an AI/Agent
slot; (2) blocking-vs-deferrable tags on Open Questions + a Constraints note; (3) a
PRD-local **Decision Log** (options considered/rejected during authoring, distinct from
project-wide decisions.md); (4) a **Final Recommendation** verdict the prd SKILL renders;
(5) wiring the CREATE interview to the just-shipped reuse-check + contradiction-surfacing.

**Explicitly OUT — documented in the template so nobody "completes" it later:** build plan
(→ `/renmark:plan`), testing sections (→ `/renmark:verify` + task verifiers), full
edge-case/risk catalog (→ brainstorm spec + `--deep-qa`), reversibility restatement (→
REQ-12 gates + `/careful`), current-system asset snapshots (→ reuse-check + project-map).

**Do NOT touch the project's own PRD.md** — it's human-owned and populated; retrofitting it
to the new template is a separate human-gated decision, not this feature.

### Task 1: PRD template — additive structure
- **mode:** B
- **target:** plugin/templates/PRD.md.template
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 1
- **est_tokens:** 700
- **est_cost_usd:** 0.032
- **verifier:** grep -qi 'Decision Log' plugin/templates/PRD.md.template && grep -qi 'Recommendation' plugin/templates/PRD.md.template && grep -qi 'Agent' plugin/templates/PRD.md.template
- **serves:** REQ-4
- **spec:**
  Enrich the existing 7-section template (keep its lean header, the human-owned comment, and
  the existing sections) with these ADDITIVE pieces, all kept OPTIONAL so a minimal PRD stays
  valid:
  (1) Under `## Requirements`: add a brief HTML comment offering OPTIONAL sub-grouping when a
  project benefits from it — "Functional / Non-functional (quality, security, perf,
  portability) / Data & Schema / UI-UX / AI-Agent (role, allowed+forbidden tools, output
  contract, when-to-stop)". Make explicit these are optional groupings of REQ-n, not required
  headers — a flat REQ list stays valid. The AI/Agent group is the genuinely new slot
  (renmark builds AI plugins).
  (2) Under `## Open questions`: add a one-line convention that each question MAY be tagged
  `[blocking]` or `[deferrable]` (blocking must be resolved before build). Add a short
  `## Constraints & dependencies` section (optional) where each item is tagged
  `[blocking | deferrable | unknown]`.
  (3) New `## Decision log` section (optional) — a compact table or list capturing decisions
  made WHILE authoring/revising this PRD: decision · why · alternatives considered · tradeoff.
  Comment that this is PRD-authoring history (product-level), DISTINCT from project-wide
  `.renmark/memory/decisions.md` ADRs — cross-reference, don't duplicate.
  (4) New `## Recommendation` section — a one-line verdict slot:
  `build-now | revise-scope | discovery-first | do-not-build-yet`, with a sentence of why.
  (5) Add ONE HTML comment block near the top listing what this template deliberately does
  NOT include and where each lives instead (build plan → /renmark:plan; testing →
  /renmark:verify; risk catalog → brainstorm + --deep-qa; reversibility → REQ-12 + /careful;
  asset inventory → reuse-check + project-map) — the anti-completion guard.
  Preserve `{{PROJECT_NAME}}`/`{{DATE}}` placeholders and the frontmatter exactly.

### Task 2: prd SKILL — interview wiring + recommendation rendering
- **mode:** B
- **target:** plugin/skills/prd/SKILL.md
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 2
- **est_tokens:** 700
- **est_cost_usd:** 0.032
- **verifier:** grep -qi 'reuse-check' plugin/skills/prd/SKILL.md && grep -qi 'recommendation' plugin/skills/prd/SKILL.md
- **serves:** REQ-4
- **spec:**
  Four additive edits to the prd SKILL (do not disturb the human-gate, context-hygiene, or
  altitude sections):
  (1) CREATE mode (both fresh-interview and mature-synthesize sub-paths): before presenting
  the draft, run the **reuse check** — dispatch the reuse-check subagent (cite
  `${CLAUDE_PLUGIN_ROOT}/skills/_shared/reuse-check.md`) so a "we already have this" finding
  surfaces before a new product capability is drafted; and **surface contradictions** — if the
  draft conflicts with an existing non-goal or a recorded decision, name it and reconcile
  rather than silently overwriting (this generalizes the existing "call out conflicts"
  instruction; reuse the contradiction-surfacing language now standard in plan/orchestrate).
  (2) Document the new template sections (requirement sub-categories optional, blocking/
  deferrable tags, Decision log, Recommendation) as available structure the skill populates
  when relevant — explicitly noting they're optional so a lean PRD is still valid.
  (3) Add a step (CREATE and UPDATE): the skill ends its draft/diff with a **Final
  Recommendation** verdict — `build-now | revise-scope | discovery-first | do-not-build-yet`
  + one sentence — surfaced to the human alongside the approval gate (the verdict is advisory;
  the human still owns the write per REQ-4).
  (4) In the CREATE output behavior, fold in a short "context-recovery summary +
  contradictions/missing-info" preamble before the draft, consistent with the
  reasoning-contract discipline (state what's missing instead of guessing). Carry the
  reasoning-contract citation where the skill dispatches the reuse-check subagent.
  Preserve frontmatter (quoted description) and the §95-onward altitude/governance sections.

## Cost preview

| # | Task | Executor | est_tokens | est cost |
|---|---|---|---|---|
| 1 | PRD template additive structure | sonnet | 700 | $0.032 |
| 2 | prd SKILL interview + recommendation | sonnet | 700 | $0.032 |

Haiku/sonnet costs include the ~10k-token Agent overhead per task (honest accounting).
**Total: ~$0.06 · ~21k tokens incl. overhead · 2 tasks (wave 1 → wave 2, sequential — task 2 references task 1's section names)**

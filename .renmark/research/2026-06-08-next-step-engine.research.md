---
artifact_type: research
schema_version: 1
created_at: 2026-06-08T15:15:10+00:00
source_sha: null
related_plan: null
generator: brainstorm-research
stale_after: null
dependency_refs: []
completion_state: complete
confidence: medium
validation_status: unvalidated
retry_count: 0
parser_success: true
schema_compliance: true
---

# Research: Next-Step Engine for renmark skills

## TASK A — Internal survey: how renmark skills hand off today

Surveyed every `plugin/skills/<name>/SKILL.md` (excluding `_shared`). Columns:
- **next-sec**: SKILL.md has a "What's next" / "Hand off" / next-step / next-command / AskUserQuestion section
- **handoff-menu**: cites `${CLAUDE_PLUGIN_ROOT}/skills/_shared/handoff-menu.md` (the shared single-source menu)
- **lifecycle**: invokes `lifecycle.write_lifecycle` / `next_recommended`
- **kind**: terminal (work ends / branch closes / meta) vs pipeline (a clear single next stage exists)

| skill       | next-sec | handoff-menu | lifecycle | kind |
|-------------|----------|--------------|-----------|------|
| blueprint   | no       | no           | yes       | pipeline |
| brainstorm  | yes      | no           | yes       | pipeline |
| check-plan  | yes      | no           | yes       | pipeline |
| codereview  | yes      | YES          | no        | pipeline (quality gate) |
| debug       | no       | no           | no        | terminal-ish |
| doctor      | no       | no           | no        | terminal (meta) |
| feature     | yes      | no           | no        | pipeline (orchestrates sub-stages) |
| finish      | yes      | no           | yes       | terminal (branch close) |
| help        | yes      | no           | no        | terminal (meta) |
| hygiene     | no       | no           | no        | terminal (meta) |
| init        | yes      | no           | no        | terminal (meta) |
| orchestrate | yes      | YES          | yes       | pipeline |
| plan        | yes      | no           | yes       | pipeline |
| prd         | yes      | no           | yes       | pipeline |
| resume      | yes      | no           | yes       | pipeline (router) |
| roadmap     | no       | no           | no        | terminal (meta) |
| setup       | yes      | no           | no        | terminal (meta) |
| start       | yes      | no           | no        | pipeline (entry router) |
| verify      | yes      | YES          | yes       | pipeline (quality gate) |

### Counts (19 skills surveyed)
- **No next-step section at all: 5** — blueprint, debug, doctor, hygiene, roadmap.
- Has *some* next-step prose but does NOT cite the shared menu: **11** — brainstorm,
  check-plan, feature, finish, help, init, plan, prd, resume, setup, start.
- Cites the shared `handoff-menu.md`: **3 only** — verify, codereview, orchestrate
  (and the menu file itself is scoped in its header to "verify + codereview").

### Sizing the refit
Only **3 / 19** skills route through the single-source-of-truth handoff menu. The
other 16 either hand-roll their own next-step prose (11) or have none (5). So the
refit surface = **16 skills lacking a consistent next-step affordance** (no shared
menu), of which **5 have no next-step affordance whatsoever**. The shared
`handoff-menu.md` already exists (8.9KB, `plugin/skills/_shared/handoff-menu.md`)
but is deliberately scoped to the quality-gate cluster — it is NOT a generic
"what's next from any stage" surface yet. A general next-step engine should
generalize that file (or add a sibling) and have all pipeline skills cite it.

### Existing state->next machinery (REUSE, do not rebuild) — `renmark/lifecycle.py`
- **`NEXT_BY_STAGE: dict[str,str]`** — canonical stage->command map
  (`init`->brainstorm, `brainstorm-complete`->plan, `plan-drafted`->check-plan,
  `plan-validated`->orchestrate, `created`->verify, `verified`->codereview,
  `reviewed`/`documented`->finish, `ready-to-release`/`released`/`restored`->manual hints).
  `NEXT_BY_STAGE_PLANNED` documents aspirational targets once unbuilt skills ship.
- **`next_recommended(repo)`** — reads lifecycle.json, honors the human-approval
  gate first (`human_review_required && !completed` short-circuits to a manual
  gate string), else takes `state.next_recommended or NEXT_BY_STAGE[stage]` and
  passes it through `_resolve_next`. Zero LLM calls. Cold start (no lifecycle) ->
  `"/renmark:start (no feature in flight)"`.
- **`_resolve_next(candidate, stage)`** — guards against pointing a vibe coder at
  an unimplemented skill: if the `/renmark:<skill>` target is not in
  `IMPLEMENTED_SKILLS`, it rewrites to a manual-hint fallback string instead.
- **`IMPLEMENTED_SKILLS: frozenset`** — the 14 skills the router may emit
  (brainstorm, check-plan, codereview, debug, feature, finish, help, orchestrate,
  plan, resume, roadmap, setup, start, verify). NOTE drift: blueprint, prd, doctor,
  hygiene, init exist on disk but are NOT in this set; secure/document/map/research/
  release/restore/approve/issue are in DOMAIN_BY_SKILL but unbuilt.

**Design implication:** a next-step engine should call `next_recommended()` as its
deterministic backbone (state->command, already safe against unimplemented targets)
and only layer LLM-driven *gap/roadmap* reasoning on top — it must NOT reimplement
the stage map. `write_lifecycle()` already sets `next_recommended` on every stage
write, so the "always show a next step" property is one read away.

---

## TASK B — External prior art

### B1. "Next best action" / contextual next-step in CLI / dev tools (no nagging)
- **git status as the gold standard**: status output "gives you hints as to what
  commands you might use next" and on typos "politely suggests a similar command"
  rather than just erroring. Lesson: surface the next step *as part of output you
  already show*, contextual to current state — never as a separate nag.
- **Lucas da Costa, "UX patterns for CLI tools"**: "Instead of spitting out lots of
  complicated documentation at users, nudge them towards the commands they're more
  likely to use." Interactive prompts "feel natural rather than forced"; interactive
  mode = "guardrails ... constraining their choices" to prevent mistakes. Anti-nag
  rule: always offer a bypass / scriptable path so the prompt guides, not gates.
- **"12 Rules of Great CLI UX" (dev.to)**: biggest amateur->pro differentiator is
  telling the user "what happened, why, and what to do about it" — i.e. every
  terminal state should carry an actionable next step. No implicit steps; surface
  the recommendation explicitly.
- **GitHub Copilot CLI**: contextual command suggestions from current task/NL —
  the LLM-augmented version of the git-status hint.
- **Salesforce Einstein / Amazon Personalize "Next Best Action"**: formal NBA =
  recommendation engine picking the single most relevant next step from
  business-logic filters + (optional) AI prediction, "in real time without relying
  on guesses." Maps onto: deterministic filter (`NEXT_BY_STAGE`) + optional AI layer.

**Synthesis for renmark:** always-show-one-next-step, derived from current state,
embedded in the skill's normal closing output; interactive (`AskUserQuestion`)
when available, printed fallback otherwise; always include a "Nothing / stop here"
escape so it guides without gating. `handoff-menu.md` rules 6/7 already do exactly
this for the quality cluster — generalize it.

### B2. Gap-discovery / "what should I build next" engines (roadmap + changelog)
- **"Moving the Needle: Analyze Your Product Roadmap Monthly" (dev.to/js402)** —
  closest prior art. Two-stage LLM workflow:
  1. Feed *what actually shipped* (changelog / working-items summary, a neutral
     factual record) + the *original roadmap* + the dev method. Prompt the model to
     "Identify discrepancies between planned and actual outcomes," "Assess delivery
     velocity," "Flag signs of strategic shifts or pivots."
  2. Meta-reflection: a *second* conversation feeds the first analysis back in, model
     role-plays "a new PM reviewing this," producing prioritization. Pattern:
     "compare [actual] against your original intent" to surface drift -> next moves.
  Portable: renmark's `PRD.md` = roadmap/intent; `CHANGELOG.md` +
  `.renmark/memory/features.md` = what-shipped; the diff = gaps.
- **CanDist (Forte Group)** — "separates candidate generation by a large language
  model from decision distillation by a smaller model, rather than forcing an LLM to
  commit prematurely." Backlog = "structured orchestration between models and
  humans." Implication: *generate* candidate next-builds (large model) then
  *rank/distill* to one recommendation, human-gated — mirrors renmark's executor
  tiering + human-approval gate.
- **LLM requirement gap analysis (Bandaru, Analyst's Corner)** — LLMs detect
  "omissions, inconsistencies, or ambiguities"; gaps "could lead to project failure
  if not identified early." Risk: gap analysis can hallucinate requirements — keep it
  advisory + human-confirmed (fits renmark's PRD-is-human-owned doctrine; never
  silently rewrite).
- **"Outgrowing the Backlog" (Tessmann, Medium)** — bottleneck shifted from
  build-speed to decide-what-to-build; favors "smaller pairings with specific,
  narrowly scoped goals." Supports a *narrow wedge* next-step over a big backlog dump.

### B3. Gating local analysis vs optional live web research
- The roadmap workflow's first pass is entirely *local* (roadmap + changelog) — no
  web. Web/deep research is the *expensive escalation*, reserved for insufficient
  local artifacts (novel domain, external benchmarking).
- CLI-UX principle reinforces this: do the cheap contextual thing by default
  (git-status-style, instant, no network); make the expensive interactive / AI / web
  path *opt-in* (the "would you like to compress?" nudge — offered, not forced). NBA
  engines run business-logic filters first, AI prediction as an *optional* layer.
- **Recommended gate for renmark:** Tier 0 = deterministic `next_recommended()`
  (always, free, instant). Tier 1 = local LLM gap analysis over PRD + CHANGELOG +
  features.md (cheap, offline). Tier 2 = live web research — gated behind explicit
  flag / opt-in, only when Tier 1 flags an unknown-domain gap or the user asks
  "research the market." Never auto-run the network path. Emit a research artifact;
  keep orchestrator-visible output bounded.

## Authoritative sources
- git status / typo-suggestion + nudge pattern — Lucas da Costa, https://www.lucasfcosta.com/blog/ux-patterns-cli-tools
- "12 Rules of Great CLI UX" — https://dev.to/chengyixu/the-12-rules-of-great-cli-ux-lessons-from-building-30-developer-tools-39o6
- Roadmap monthly analysis (2-stage LLM, ship-vs-intent gap) — https://dev.to/js402/moving-the-needle-how-to-analyze-your-product-roadmap-monthly-3f0p
- CanDist backlog generation (generate->distill->human) — https://fortegrp.com/insights/llm-candidate-distillation-backlog-generation
- LLM requirement gap analysis (risks) — https://medium.com/analysts-corner/using-large-language-models-for-requirement-gap-analysis-opportunities-and-risks-d922d65a9cb4
- Outgrowing the Backlog (narrow wedge) — https://medium.com/@himeag/outgrowing-the-backlog-0bb5e59fa93c
- NBA formalism — Salesforce Einstein NBA; Amazon Personalize Next-Best-Action recipe

## Summary

- Internal: only 3/19 skills (verify, codereview, orchestrate) cite the shared handoff-menu.md; 16 lack a consistent next-step affordance, of which 5 have NONE (blueprint, debug, doctor, hygiene, roadmap).
- REUSE lifecycle.py: NEXT_BY_STAGE + next_recommended() + _resolve_next() already give a free, deterministic, unimplemented-safe state->command backbone (write_lifecycle sets next_recommended on every stage write); generalize the existing 8.9KB handoff-menu.md (rules 6/7) rather than rebuild.
- CLI prior art (git status, Lucas da Costa, 12 Rules, Copilot CLI, Einstein/Personalize NBA): always embed ONE contextual next step in normal output, interactive-with-bypass + a 'Nothing/stop' escape, so it guides without nagging.
- Gap-discovery prior art (Moving-the-Needle 2-stage, CanDist generate->distill, LLM req-gap analysis): compare PRD(intent) vs CHANGELOG+features.md(shipped) to surface drift/uncovered work; advisory + human-gated, never silently rewrite PRD (hallucination risk).
- Gate the cost in 3 tiers: T0 deterministic next_recommended (always/free), T1 local LLM gap analysis offline (cheap), T2 live web research opt-in only when T1 flags an unknown domain.

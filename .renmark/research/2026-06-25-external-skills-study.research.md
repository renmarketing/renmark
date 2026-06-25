---
artifact_type: research
schema_version: 1
created_at: 2026-06-25T00:00:00Z
source_sha: 8f1513be393ba4b43f363c75677339a7483fc48a
related_plan: null
generator: opus
stale_after: 2026-12-25T00:00:00Z
dependency_refs:
  - https://github.com/mattpocock/skills
  - https://github.com/obra/superpowers
  - https://github.com/garrytan/gstack
completion_state: complete
confidence: high
validation_status: unvalidated
---

# External skills study — learnings for renmark

Deep study of three Claude Code skill frameworks, compared against renmark, through the
lens of renmark's pillar (context hygiene) plus efficiency, speed, usability, token cost,
and plain-word triggering. Each repo was studied in an isolated subagent that cloned it,
went feature-by-feature, and returned a bounded structured report — so the raw repo bodies
never entered the orchestrator context.

Clones (scratch, ephemeral): `/home/renmark/.claude/jobs/.../tmp/study/{mattpocock-skills,superpowers,gstack}`

## The three repos in one line each
- **mattpocock/skills** — tiny prose skills (median ~70 lines, flagship "grilling" is 10 lines); pioneered the **model-invoked vs user-invoked** axis as a token-budget tool.
- **obra/superpowers** (v6.0.3) — no slash commands at all; a 14-skill behavioral framework whose flagship is **subagent-driven-development**: file-handoff controller loop with dual review. Strongest context-hygiene engineering of the three.
- **garrytan/gstack** (v1.58.x) — ~40 role-based skills ("virtual eng team"); ships real tooling (headless browser, gbrain memory) and **template-generated SKILL.md** + tiered skill testing.

---

## THE headline finding (both mattpocock AND superpowers, independently)

**A skill's `description` must state WHEN to invoke it — never WHAT it does.**

superpowers has a *tested* result: a description that summarized the workflow ("review code
between tasks") made the agent perform ONE review instead of the skill's TWO — the summary
became a shortcut that **replaced reading the body**. mattpocock frames the same rule as
"one trigger per branch, collapse synonyms; front-load the leading word."

Renmark's descriptions are the opposite — they pack the full pipeline into the description
(e.g. debug: "Runs reproduce → root cause → fix → regression test → verify… Routes cheap
investigation to Haiku/Bash, multi-file traces to Codex…"). This costs on **three** axes:
1. **Tokens** — every model-invoked description loads on every turn. 28 skills × ~80–120
   words = a large permanent steady-state cost, directly against the pillar.
2. **Triggering reliability** — a workflow-summary in the description lets the model act on
   the summary instead of loading the body, silently skipping steps.
3. **Maintenance** — workflow described in two places (description + body) drifts.

This is the highest-impact, lowest-cost change available and is the spine of the proposals below.

---

## Ranked proposals for renmark

### Tier 1 — do these (high impact, cheap, on-pillar)

**P1. Rewrite skill descriptions to trigger-only; move workflow into the body.**
Source: superpowers (tested), mattpocock. Cut "Runs X → Y → Z … Routes … to …" from every
`description`; keep only WHEN + plain-word triggers. Collapse synonym lists ("add X / build
X / implement X / create X / code up X") to distinct branches. Saves steady-state tokens on
every turn, sharpens auto-routing, removes drift. Pair with renmark's existing
description-drift audit pass.

**P2. Adopt the model-invoked / user-invoked axis (`disable-model-invocation: true`).**
Source: mattpocock. Every model-invoked description is a permanent per-turn context cost;
user-invoked = zero steady-state load. Reclassify the **zero-LLM / meta / human-driven**
skills as user-invoked: `analytics`, `usage`, `inventory`, `help`, `approve`, `resume`,
`doctor`, `hygiene`, `audit`, `scan`, `check-plan`. Keep the **auto-routing pipeline** skills
(`start`, `feature`, `debug`, `roadmap`, `finish`, `init`, `brainstorm`, `plan`) model-invoked
— those *must* fire on plain English. This alone could remove ~10 long descriptions from the
every-turn budget without touching the plain-word UX.

**P3. Graduated context injection (`preamble-tier`).**
Source: gstack. Renmark's `skill_preamble` is all-or-nothing per domain. Let zero-LLM skills
carry a minimal preamble and heavy pipelines the full block. Complements P2; finer token dial.

**P4. File-handoff helper scripts to operationalize "no diffs in the orchestrator".**
Source: superpowers (`task-brief PLAN N`, `review-package BASE HEAD` → write a uniquely-named
file, print the path; subagent reads it in one call, bytes never touch the controller).
Renmark *forbids* reading diffs into the orchestrator but enforces it by discipline. A
deterministic helper in `renmark-execute` (or `bin/`) turns the rule into mechanism. Directly
strengthens the pillar.

### Tier 2 — strong, moderate effort

**P5. Anti-re-dispatch ledger doctrine: trust the ledger + `git log` over recollection.**
Source: superpowers ("re-dispatching completed tasks is the single most expensive observed
failure"; "do not paste accumulated prior-task summaries — a real session hit 42k chars of
99% pasted history"). Renmark already has `pipeline.json`/`lifecycle.json`/wave-summaries —
this is a *doctrine* add, and it maps onto a known renmark bug (roadmap "retried" false
negatives + `renmark-execute --resume` silently skipping real tasks). Add an explicit rule and
a cross-check of the resume skip-list against the live plan.

**P6. Two-verdict task review: spec-compliance AND code-quality, scored separately.**
Source: superpowers. Renmark's codereview is effectively one axis. Splitting "did it build the
*right* thing" from "is it *well* built" catches over-building and under-building that a single
score hides.

**P7. Template-generated SKILL.md with build-time placeholder resolution.**
Source: gstack (`gen-skill-docs.ts`; "never resolve conflicts on generated SKILL.md, fix the
`.tmpl` and regenerate"). Renmark *audits* for description drift; gstack *prevents* it
structurally. A generation step for the shared blocks (preamble, trigger lists) would remove a
class of drift the audit currently only flags after the fact.

**P8. Behavioral skill testing + cheap LLM-as-judge eval tier.**
Source: superpowers (skills authored via TDD: baseline-fail → add skill → pass, under subagent
pressure tests) + gstack (Tier3 LLM-judge eval ~$0.15). Renmark's audit lints *structure* but
never tests that a skill actually *changes agent behavior*. A small behavioral harness would
harden the skills the way renmark hardens products.

### Tier 3 — usability / ergonomics

**P9. A router / decision-tree skill (vs the flat `help` list).**
Source: mattpocock `ask-matt`. "Idea → ship? on-ramp? standalone?" lowers the cognitive load
of remembering which pipeline fits. renmark's `help` is a flat enumeration.

**P10. Formal spawned/headless-session contract.**
Source: gstack (`$OPENCLAW_SESSION`: disable `AskUserQuestion`, auto-pick the recommended
option, return prose-only "shipped / decided / uncertain"). Especially relevant because renmark
is already run inside background jobs — a declared headless mode makes pipelines behave when
driven by an outer orchestrator instead of interactively.

**P11. Persisted proactivity toggle.**
Source: gstack (`gstack-config set proactive false`). Renmark's auto-routing is a doc-level
default; a persisted on/off switch makes "just do it directly" durable across sessions instead
of per-message.

**P12. Feedback-loop-first debugging gate.**
Source: mattpocock `diagnosing-bugs` (refuses to hypothesize until a tight, red-capable command
has been *run*). Stronger than renmark's "root cause in one sentence" Iron Law — add the
"reproduce with a real command first" precondition.

---

## Trade-offs / deliberate divergences (noted, not recommended wholesale)

- **superpowers SessionStart `<EXTREMELY_IMPORTANT>` 1%-rule injection** makes plain-word
  triggering very reliable, but it injects a large mandate every session — that *fights*
  renmark's context-hygiene pillar. Borrow the *red-flags rationalization table* concept
  lightly (a few lines), not the heavyweight injection.
- **Shared-context-for-alignment vs isolate-everything.** mattpocock keeps ONE unbroken thread
  across grill→PRD→issues (alignment must share context), then clears per implementation.
  Renmark isolates every task. The principled split is "alignment shares context, execution
  isolates" — worth considering for renmark's brainstorm→prd→plan run, which arguably benefits
  from a shared thread while orchestrate stays isolated.
- **gstack gbrain (Supabase/PGLite semantic memory) and the shipped headless browser** are
  philosophy divergences, not gaps: renmark deliberately keeps state file-based in-project
  (`.renmark/`) and uses Chrome DevTools MCP rather than bundling a browser.
- **ETHOS.md single injected doctrine file** (gstack) is easier to keep honest but less
  auditable than renmark's discrete CLAUDE.md rule-blocks. Keep renmark's per-rule blocks.

## Suggested sequencing
P1 + P2 together as one `/renmark:feature` (both edit skill frontmatter; biggest token win),
then P4 (helper scripts) and P5 (ledger doctrine) as the context-hygiene hardening pass, then
Tier 2/3 opportunistically.

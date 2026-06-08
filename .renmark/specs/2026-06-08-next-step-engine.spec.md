---
artifact_type: spec
schema_version: 1
created_at: 2026-06-08
source_sha: TBD
generator: brainstorm
related_plan: TBD
dependency_refs:
  - .renmark/research/2026-06-08-next-step-engine.research.md
  - PRD.md
  - plugin/skills/_shared/handoff-menu.md
  - renmark/lifecycle.py
status: draft
---

# Spec — next-step-engine (guided next-step + gap discovery)

## Context

renmark's promise is a *guided* pipeline, but the guidance is uneven. A codebase
survey (see research artifact) found that of 19 skills, **only 3** (verify,
codereview, orchestrate) cite the shared hand-off contract; **16 lack a
consistent next-step affordance**, and **5 have none at all** (blueprint, debug,
doctor, hygiene, roadmap). So many interactions dead-end: the user finishes a
skill and is left guessing what to run next. Separately, finishing a *feature*
ends with a generic "start a new one with /renmark:start" — no help deciding
*what* to build next against the product's actual gaps.

This feature makes **every interaction guided** and turns "feature complete" into
a gap-driven "what's next." It is largely a **generalization of machinery that
already exists** — `NEXT_BY_STAGE` + `next_recommended()` in `lifecycle.py`, and
the `_shared/handoff-menu.md` quality-gate contract — not new construction.

PRD alignment ran upstream: **aligned** (REQ-1 guided pipeline, REQ-3
state-derived recovery; optional web research precedented by brainstorm, breaches
no non-goal).

## Goals

1. No renmark skill dead-ends: each completion surfaces a contextual next step
   derived from **durable state** (lifecycle.json + pipeline.json), never from
   conversational memory — so it survives `/clear`.
2. `/renmark:verify` (and the gate skills) suggest the verification steps **not
   yet run for the current sha/feature** — `--qa`, `--deep-qa`, `/renmark:codereview`.
3. Finishing a feature flows into **gap discovery**: compare PRD-intent vs
   shipped (CHANGELOG + features.md) and suggest the next feature, advisory and
   human-gated.
4. `/renmark:init` ends with the same gap-discovery hand-off, so a freshly
   mapped/initialized project is immediately guided toward its uncovered work.
5. One shared contract drives all of the above — adding a future gate or skill is
   a single edit, enforced by a lint/test so it can't drift.

## Non-goals (feature-scoped)

- A standalone `/renmark:next` skill — gap discovery **extends `/renmark:roadmap`**
  instead (see ADR below; supersedes the deferred item in ADR-005).
- Live web research **on by default** — it is Tier-2, opt-in, default off.
- Auto-writing `PRD.md` or any roadmap file — the engine is advisory; PRD changes
  route to `/renmark:prd` (human-gated, per ADR-005 one-writer rule).
- Per-skill bespoke menus — every skill defers to the shared contract.
- New runtime dependencies — stdlib Python + markdown only.

(Product-level non-goals live in `PRD.md`; not duplicated here.)

## Architecture — three tiers, reusing existing machinery

**Tier 0 — Deterministic next (free, always).** Reuse `NEXT_BY_STAGE` +
`next_recommended()` (already unimplemented-skill-safe via `IMPLEMENTED_SKILLS` /
`_resolve_next`). Every skill, on completion, surfaces the in-flight feature's
next step from this backbone.

**Tier 1 — Quality-gate menu (verify stage).** The existing `handoff-menu.md`
stays as the verify/codereview gate sub-menu, filtered by which gates ran for the
current sha (existing rules 1–9). The new umbrella contract *references* it — no
duplication.

**Tier 2 — Gap discovery (`/renmark:roadmap`, extended).** Compares PRD-intent vs
CHANGELOG + `features.md` to surface uncovered requirements/gaps and suggest the
next feature. Cost-gated:
- **T0** deterministic next (free) — always.
- **T1** local LLM gap analysis, offline, over PRD + CHANGELOG + memory — default.
- **T2** live web research for best-practice next-step ideas — **opt-in, default
  off**; triggered only on explicit user opt-in or when T1 flags an unknown
  domain. Runs via Claude Code's own web tools (no Python dep).

## Components

1. **`plugin/skills/_shared/next-steps.md`** — NEW umbrella contract. Defines how
   *any* skill computes and renders its next step from lifecycle/pipeline state.
   Three skill classes:
   - **Pipeline skills** (start, brainstorm, plan, check-plan, orchestrate,
     verify, finish, feature, prd, blueprint) → Tier-0 stage routing via
     `next_recommended()`.
   - **Quality gates** (verify/--qa/--deep-qa, codereview) → defer to
     `handoff-menu.md`.
   - **Aux / terminal skills** (debug, doctor, hygiene, roadmap, init, blueprint,
     setup, help, resume) → suggest **resume-pipeline** (the in-flight feature's
     `next_recommended()`) + 1–2 domain-appropriate local actions
     (e.g. debug → re-verify the fix; doctor → re-run the failing skill).
   Cites `handoff-menu.md`; reuses its rendering rules 6–9 (AskUserQuestion
   primary, printed fallback, always a visible choice).

2. **`renmark/lifecycle.py` helper** — NEW `next_steps(repo, skill)` (pure,
   stdlib). Returns a structured "what's left / what's next" derived from
   `stage`, `stages_completed`, gate artifacts for the current sha
   (`summary.read_metadata` over `.renmark/reviews/*.qa.md` etc.), and
   `pipeline.json`. Drives the contract's rendering; never reads source/PRD body.

3. **Skill refit (all 19 skills)** — each SKILL.md gets a uniform "What's next"
   hand-off section citing `next-steps.md`. 16 standardized, 5 added from scratch
   (blueprint, debug, doctor, hygiene, roadmap).

4. **`/renmark:roadmap` gap-discovery extension** — adds the T0/T1/T2 gap mode:
   PRD vs shipped diff, opt-in web research, advisory output. Heavy analysis +
   web research run in **subagents**; roadmap sees only bounded summaries. Never
   auto-writes PRD/roadmap — proposals route to `/renmark:prd`.

5. **`/renmark:finish` wiring** — the terminal hand-off (post-release) routes into
   roadmap's gap mode instead of the generic "start a new one."

6. **`/renmark:init` wiring** — after documenting the project (map/stack), init
   ends by routing to roadmap's gap mode, so a freshly initialized/re-mapped
   project is immediately guided to its uncovered work. (Per the tweak: roadmap
   gap discovery is part of init's hand-off.)

7. **Tests + lint** — `tests/test_next_steps.py` (helper logic, unimplemented-skill
   safety, gate filtering by sha, aux-skill resume routing) + a lint check that
   every non-`_shared` skill cites `next-steps.md` (drift guard, mirrors the
   existing command-pair lint).

## Data flow

```
skill completes
  → lifecycle.next_steps(repo, skill)            # Tier 0, durable state
      reads: stage, stages_completed, pipeline.json, gate artifacts (by sha)
  → render via next-steps.md rules
      pipeline skill → next_recommended()
      gate skill     → handoff-menu.md sub-menu (filtered by sha)
      aux skill      → resume-pipeline + domain actions
  → user picks (AskUserQuestion primary; printed fallback; always a choice)

finish (released) / init (mapped)
  → /renmark:roadmap --gaps
      T1 subagent: PRD vs CHANGELOG+features.md → bounded gap list
      [opt-in] T2 subagent: web research → bounded best-practice ideas
  → advisory suggestions; PRD changes route to /renmark:prd (human-gated)
```

## Error handling / edge cases

- No in-flight feature (lifecycle at `released`/`restored`/`init`) → aux/finish
  hand-off falls through to gap discovery rather than a stale stage pointer.
- Gate artifact missing/partial for the sha → that gate stays *offered* (not
  hidden); `--deep-qa` stays gated behind a passing `--qa` for the sha (existing
  rule 2).
- Unimplemented skill target → `_resolve_next` fallback hint (existing).
- `next_steps()` must never raise into a skill's hand-off — on any read error it
  degrades to the plain `next_recommended()` string.
- T2 web research unavailable (headless/no network) → silently skip to T1 output.

## Success criteria

- All 19 skills end with a state-derived next-step hand-off; lint passes proving
  every skill cites `next-steps.md`.
- `/renmark:verify` lists exactly the gates not yet run for the current sha.
- After `/clear`, the next step is still correct (read from disk, zero LLM calls
  for Tier 0).
- `/renmark:roadmap` (and finish/init hand-offs) produce an advisory gap list from
  PRD vs shipped; web research stays off unless opted in.
- `next_steps()` is pure + stdlib; `pytest -q`, `ruff check`, `mypy .` all green;
  lifecycle.json stays ≤1KB (no runtime cruft leak).

## ADR — supersede ADR-005's deferred roadmap view

ADR-005 *deferred* a "roadmap PRD progress view" as bloat-now. This feature
reactivates it deliberately, scoped tightly to stay inside the anti-bloat
doctrine: gap discovery is **read-only + advisory + human-gated**, reuses the
ALIGN subagent pattern (roadmap never reads the PRD body inline), and never
becomes a second PRD writer. The plan should emit a new ADR recording this
supersession with this scoping rationale.

## Prior art & references

- Research artifact: `.renmark/research/2026-06-08-next-step-engine.research.md`
  (internal skill survey + external CLI next-action / gap-discovery prior art).
- Internal: `renmark/lifecycle.py` (`NEXT_BY_STAGE`, `next_recommended`,
  `IMPLEMENTED_SKILLS`), `plugin/skills/_shared/handoff-menu.md`.
- External (in artifact): CLI "next best action" patterns (git status, Copilot
  CLI), 2-stage gap-analysis (generate→distill), LLM requirement-gap analysis.

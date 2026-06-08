# Plan — next-step-engine (Part 1 of 2): foundation + behaviors + refit batch A

**Spec:** `.renmark/specs/2026-06-08-next-step-engine.spec.md`
**Branch:** `feature/next-step-engine`

Part 1 builds the shared contract + state helper that everything else depends on,
adds the gap-discovery behavior to roadmap and wires finish/init into it, then
refits the first 5 pipeline skills' hand-offs. Part 2 finishes the refit and adds
the lint drift-guard. **Task 1 (the contract) is the gate** — every citing task
reads its snippet, so it runs first. Gate skills (verify, codereview, orchestrate)
already cite `handoff-menu.md` and are intentionally NOT edited; the Part 2 lint
accepts either citation.

---

### Task 1: next-steps shared contract
- **mode:** A
- **target:** plugin/skills/_shared/next-steps.md
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 1
- **est_tokens:** 1500
- **est_cost_usd:** 0.03
- **verifier:** test -f plugin/skills/_shared/next-steps.md && grep -q "next_steps" plugin/skills/_shared/next-steps.md
- **spec:**
  Create the umbrella "Next-Step" contract (single source of truth), modeled on the
  sibling files `plugin/skills/_shared/handoff-menu.md` and `scope-contract.md` (read
  both first for tone/structure). It defines how ANY skill computes + renders its next
  step from durable state, and is REFERENCED by skills — never pasted.
  Cover:
  - **Purpose:** no renmark interaction dead-ends; every skill ends recommending a
    state-derived next step. State source = `lifecycle.json` + `pipeline.json` (durable,
    survives /clear) — never conversational memory.
  - **The state helper:** skills call `renmark.lifecycle.next_steps(repo, skill)` (built in
    Task 2) to get the structured next-step set; render it via AskUserQuestion (primary) /
    printed numbered fallback, reusing handoff-menu.md rendering rules 6–9 verbatim
    (reference them, don't restate).
  - **Three skill classes** and the citation snippet each uses:
    1. *Pipeline skills* (start, brainstorm, plan, check-plan, orchestrate, verify, finish,
       feature, prd, blueprint) → Tier-0 stage routing via `next_recommended()`.
    2. *Quality gates* (verify/--qa/--deep-qa, codereview) → defer to `handoff-menu.md`'s
       gate sub-menu (this contract references it; gate skills may cite EITHER file).
    3. *Aux/terminal skills* (debug, doctor, hygiene, roadmap, init, setup, help, resume) →
       suggest resume-pipeline (the in-flight feature's `next_recommended()`) PLUS 1–2
       domain-appropriate local actions.
  - **Tiered cost gating for gap discovery** (used by roadmap/finish/init): T0 deterministic
    next (free, always) → T1 local LLM gap analysis (PRD vs CHANGELOG+features.md, default)
    → T2 live web research (OPT-IN, default OFF; only on user opt-in or T1 unknown-domain flag).
  - **A "When citing this contract in a SKILL.md, write:" block** giving the exact short
    blockquote each of the three classes pastes (like handoff-menu.md's closing block).
  - **Why a shared file** (one edit point; `_shared/` skipped by lint).
  Do NOT duplicate handoff-menu.md's gate menu text — reference it.

### Task 2: lifecycle.next_steps() helper
- **mode:** B
- **target:** renmark/lifecycle.py
- **complexity:** hard
- **executor:** sonnet
- **parallel_group:** 2
- **est_tokens:** 1300
- **est_cost_usd:** 0.03
- **verifier:** python3 -c "from renmark import lifecycle; assert hasattr(lifecycle,'next_steps'); print('ok')" && ruff check renmark/lifecycle.py && mypy renmark/lifecycle.py
- **spec:**
  Add a pure, stdlib-only function `next_steps(repo, skill)` to `renmark/lifecycle.py`
  (do NOT remove or alter existing functions). It returns a structured next-step result
  derived from DURABLE STATE only — never source or PRD body. Behavior:
  - Read lifecycle via the existing `read_lifecycle(repo)`. From `stage`, compute the
    Tier-0 next command using the existing `NEXT_BY_STAGE` / `next_recommended()` /
    `_resolve_next()` machinery (reuse them; do not reimplement routing).
  - Classify `skill` (pipeline / gate / aux) using the same skill lists as the
    `next-steps.md` contract (define module-level frozensets, mirroring `DOMAIN_BY_SKILL`
    style). Return the appropriate suggestions per class:
      * pipeline → `[next_recommended()]`
      * gate → marker indicating "defer to handoff-menu gate sub-menu" + the gates not yet
        run for the current sha (detect by reading `.renmark/reviews/*.qa.md` /
        `*.review.md` metadata via `renmark.summary.read_metadata`, filtered by
        `source_sha == git_head_sha(repo)` and `completion_state == "complete"`; mirror
        handoff-menu.md rule 2). If summary/git helpers are unavailable, degrade gracefully.
      * aux → resume-pipeline (`next_recommended()`) + up to 2 domain actions from a small
        per-skill map (e.g. debug → re-run /renmark:verify; doctor → re-run failing skill).
  - Return a small dataclass or dict (e.g. `{'tier0': str, 'suggestions': list[str],
    'skill_class': str}`). Keep it JSON-trivial and typed.
  - **Never raise into a caller:** wrap state reads so any failure returns a minimal result
    containing just the `next_recommended()` string. Add a module docstring line noting this
    is the contract helper for `_shared/next-steps.md`.
  Match existing code style (type hints, no new imports beyond stdlib + existing renmark modules).

### Task 3: next_steps() unit tests
- **mode:** A
- **target:** tests/test_next_steps.py
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 3
- **est_tokens:** 1500
- **est_cost_usd:** 0.03
- **verifier:** python3 -m pytest tests/test_next_steps.py -q
- **spec:**
  Write pytest tests for `lifecycle.next_steps(repo, skill)` (routed to sonnet per ADR-007 —
  new test files fail under codex's read-only sandbox). Use a tmp_path repo with a written
  `.renmark/state/lifecycle.json` (use `lifecycle.write_lifecycle` / `begin_feature` to set
  it up — follow patterns in existing `tests/`). Cover:
  - pipeline skill at each major stage → returns the correct Tier-0 next command (assert
    against `NEXT_BY_STAGE`).
  - unimplemented-skill safety: a stage whose target isn't in `IMPLEMENTED_SKILLS` returns
    the fallback hint, never a dead `/renmark:<x>`.
  - aux skill (e.g. debug) → result includes resume-pipeline next + at least one domain action.
  - gate skill (e.g. verify) → `skill_class == 'gate'`; with no `.qa.md` artifact for the
    sha, deep-qa is reported as not-yet-available (mirrors handoff-menu rule 2).
  - graceful degradation: a missing/corrupt lifecycle.json does NOT raise — returns a minimal
    result. Keep tests hermetic (no network, no real git mutation beyond tmp).

### Task 4: roadmap gap-discovery extension
- **mode:** B
- **target:** plugin/skills/roadmap/SKILL.md
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 4
- **est_tokens:** 2500
- **est_cost_usd:** 0.04
- **verifier:** grep -q "next-steps.md" plugin/skills/roadmap/SKILL.md && grep -qi "gap" plugin/skills/roadmap/SKILL.md
- **spec:**
  Extend the roadmap SKILL.md with a **gap-discovery mode** implementing ADR-009 (read
  `.renmark/memory/decisions.md` ADR-009 + the spec first). Requirements:
  - New mode that compares PRD-intent vs shipped (CHANGELOG + `.renmark/memory/features.md`)
    to surface uncovered requirements/gaps and suggest the next feature.
  - **Tiered cost gating** per the next-steps.md contract: T0 deterministic (free) → T1 local
    LLM gap analysis (default, offline over PRD+CHANGELOG+memory) → T2 live web research
    (OPT-IN, default OFF; only on explicit opt-in or T1 unknown-domain flag).
  - **Read-only / advisory / human-gated:** roadmap MUST NOT read the PRD body inline — it
    dispatches the ALIGN subagent (`_shared/prd-alignment.md` pattern) so the body stays out
    of context; heavy analysis + any web research run in SUBAGENTS returning bounded ≤5-line
    summaries. Roadmap NEVER writes PRD.md or any roadmap file — proposals route to
    `/renmark:prd` (human-gated). State the one-writer rule explicitly.
  - Add a "What's next" hand-off citing `_shared/next-steps.md` (aux-skill snippet).
  - Preserve existing roadmap behavior; add, don't replace. Mirror any rule-affecting change
    note for AGENTS.md/CLAUDE.md sync at the bottom.

### Task 5: finish wiring → roadmap gap mode
- **mode:** B
- **target:** plugin/skills/finish/SKILL.md
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 4
- **est_tokens:** 1200
- **est_cost_usd:** 0.03
- **verifier:** grep -q "next-steps.md" plugin/skills/finish/SKILL.md && grep -qi "roadmap" plugin/skills/finish/SKILL.md
- **spec:**
  Update the finish SKILL.md so the terminal/post-release hand-off routes into roadmap's
  gap-discovery mode instead of the generic "start a new one with /renmark:start". Read the
  current finish hand-off first and preserve the PR/merge/release options; only change the
  "what to build next" tail to offer `/renmark:roadmap` gap mode (advisory). Add/standardize
  the "What's next" section to cite `_shared/next-steps.md` (pipeline-skill snippet — finish
  is a pipeline skill). Keep AGENTS.md/CLAUDE.md sync note if present.

### Task 6: init wiring → roadmap gap mode
- **mode:** B
- **target:** plugin/skills/init/SKILL.md
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 4
- **est_tokens:** 1200
- **est_cost_usd:** 0.03
- **verifier:** grep -q "next-steps.md" plugin/skills/init/SKILL.md && grep -qi "roadmap" plugin/skills/init/SKILL.md
- **spec:**
  Update the init SKILL.md so that AFTER it documents the project (writes project-map.md /
  stack.md and merges the map block), it ends by routing to roadmap's gap-discovery mode —
  giving a freshly initialized/re-mapped project a guided "here are the uncovered gaps / next
  moves" hand-off (per the user tweak in ADR-009). Read the current init flow first; keep its
  map-writing behavior unchanged (init stays the sole writer of map/stack; blueprint stays the
  sole writer of SCHEMATIC/PROTOTYPE). Add a "What's next" section citing `_shared/next-steps.md`
  (aux-skill snippet) whose primary action is `/renmark:roadmap` gap mode. Keep AGENTS.md/CLAUDE.md
  sync note if present.

### Task 7: refit start hand-off
- **mode:** B
- **target:** plugin/skills/start/SKILL.md
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 5
- **est_tokens:** 300
- **est_cost_usd:** 0.00
- **verifier:** grep -q "next-steps.md" plugin/skills/start/SKILL.md
- **spec:**
  Standardize start's hand-off to cite the shared contract. Add (or fold into the existing
  hand-off section) the pipeline-skill citation blockquote from
  `plugin/skills/_shared/next-steps.md` (read it first and copy the exact pipeline snippet).
  Do not rewrite start's logic — only ensure its "what's next" defers to the contract. If a
  sync note for AGENTS.md/CLAUDE.md exists, leave it intact.

### Task 8: refit brainstorm hand-off
- **mode:** B
- **target:** plugin/skills/brainstorm/SKILL.md
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 5
- **est_tokens:** 300
- **est_cost_usd:** 0.00
- **verifier:** grep -q "next-steps.md" plugin/skills/brainstorm/SKILL.md
- **spec:**
  Add the pipeline-skill citation blockquote from `plugin/skills/_shared/next-steps.md` to
  brainstorm's Step 7 hand-off (read the contract first; copy the exact pipeline snippet).
  Brainstorm already has a hand-off menu — just ensure it references the shared contract;
  do not change its plan/wait/no options.

### Task 9: refit plan hand-off
- **mode:** B
- **target:** plugin/skills/plan/SKILL.md
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 5
- **est_tokens:** 300
- **est_cost_usd:** 0.00
- **verifier:** grep -q "next-steps.md" plugin/skills/plan/SKILL.md
- **spec:**
  Add the pipeline-skill citation blockquote from `plugin/skills/_shared/next-steps.md` to
  plan's Step 8 hand-off (read the contract first; copy the exact pipeline snippet). Do NOT
  alter the single-dispatch-gate contract text (Step 8b) — only add the shared-contract
  citation reference.

### Task 10: refit feature hand-off
- **mode:** B
- **target:** plugin/skills/feature/SKILL.md
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 5
- **est_tokens:** 300
- **est_cost_usd:** 0.00
- **verifier:** grep -q "next-steps.md" plugin/skills/feature/SKILL.md
- **spec:**
  Add the pipeline-skill citation blockquote from `plugin/skills/_shared/next-steps.md` to
  feature's Step 6 (Verify + Finish) hand-off (read the contract first; copy the exact
  pipeline snippet). Do not change feature's router contract or dispatch-gate ownership text.

### Task 11: refit prd hand-off
- **mode:** B
- **target:** plugin/skills/prd/SKILL.md
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 5
- **est_tokens:** 300
- **est_cost_usd:** 0.00
- **verifier:** grep -q "next-steps.md" plugin/skills/prd/SKILL.md
- **spec:**
  Add a "What's next" hand-off to prd's SKILL.md citing the pipeline-skill snippet from
  `plugin/skills/_shared/next-steps.md` (read the contract first; copy the exact snippet).
  After a PRD create/update, the natural next step is the in-flight feature's stage (or
  `/renmark:roadmap` gap mode if no feature is in flight). Do not change the human-gate logic.

---

## Cost preview (Part 1)

| Task | Executor | Total tokens (incl. ~10k overhead) | Cost |
|---|---|---|---|
| 1 next-steps.md | sonnet | 11,500 | $0.0345 |
| 2 lifecycle helper | sonnet | 11,300 | $0.0339 |
| 3 helper tests | sonnet | 11,500 | $0.0345 |
| 4 roadmap gap mode | sonnet | 12,500 | $0.0375 |
| 5 finish wiring | sonnet | 11,200 | $0.0336 |
| 6 init wiring | sonnet | 11,200 | $0.0336 |
| 7–11 refit (haiku ×5) | haiku | 10,300 ea | $0.0052 |

**Tasks: 11 (5 parallel groups). Executors: haiku×5, sonnet×6.**
**Total tokens: ~131k. Total cost: ~$0.21**

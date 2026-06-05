# Plan — `PRD.md` source of truth + `/renmark:prd`

**Spec:** `.renmark/specs/2026-06-05-prd-source-of-truth.spec.md`
**Research:** `.renmark/research/2026-06-05-prd-taskmaster.research.md`

Adds a per-project root `PRD.md` source of truth, a `/renmark:prd` skill
(create/update, human-gated), pipeline wiring in `start`/`feature`, a
subagent-based PRD↔work drift check that keeps the PRD out of orchestrator
context, a plan traceability note, and plain-text (never `@import`) PRD pointers
in CLAUDE.md/AGENTS.md + their templates. The prototype/schematic step is a
separate follow-up and explicitly out of scope.

**Invariants (from CHANGELOG "Do not change" + tests):**
- `commands/` mirrors `skills/` exactly (`test_commands_directory_complete`).
- `test_plugin_has_required_skill_files` hardcodes the documented-skill set — add `prd`.
- New SKILL.md: frontmatter `name` == dir name; include a `## Governance compliance` section.
- CLAUDE.md ↔ AGENTS.md changes mirrored in the same wave.
- Pointer lines are **plain text, never `@import`** (an import auto-loads the PRD every session).

---

### Task 1: PRD template
- **mode:** A
- **target:** plugin/templates/PRD.md.template
- **complexity:** medium
- **executor:** codex
- **parallel_group:** 1
- **est_tokens:** 600
- **est_cost_usd:** 0.02
- **verifier:** test -f plugin/templates/PRD.md.template && grep -q "REQ-1" plugin/templates/PRD.md.template
- **spec:**
  Create the PRD template scaffolded into new projects. Start with a YAML
  provenance header: `artifact_type: prd`, `schema_version: 1`,
  `created_at: {{DATE}}`, `last_reviewed: {{DATE}}`, `status: draft`. Then a
  `# {{PROJECT_NAME}} — Product Requirements Document` title and these lean
  sections as `##` headings, each with a one-line placeholder prompt in
  parentheses: **Vision / Problem** (the WHY), **Target users**, **Goals &
  Non-goals** (note non-goals prevent scope creep), **Requirements** (a numbered
  list seeded with `REQ-1` … written as behaviors/outcomes, not solutions),
  **Success metrics**, **Scope boundaries** (in / out / deferred), **Open
  questions**. Keep it lean — a comment near the top: "Living source of truth;
  updated only on reviewed, approved change." Use `{{PROJECT_NAME}}` and
  `{{DATE}}` placeholders consistent with the other templates in this dir.

### Task 2: prd skill
- **mode:** A
- **target:** plugin/skills/prd/SKILL.md
- **complexity:** hard
- **executor:** opus
- **parallel_group:** 1
- **est_tokens:** 2600
- **est_cost_usd:** 0.19
- **verifier:** python3 -c "from renmark import lint; d=lint.parse_frontmatter(open('plugin/skills/prd/SKILL.md').read()); assert d and d['name']=='prd', d" && grep -q "Governance compliance" plugin/skills/prd/SKILL.md
- **spec:**
  Create the core `/renmark:prd` skill. Follow the canonical SKILL.md structure
  (see `plugin/skills/check-plan/SKILL.md` and `plugin/skills/verify/SKILL.md`):
  frontmatter `name: prd` + a one-paragraph `description`; sections Overview,
  When to Use / Do NOT use, Steps, and a closing `## Governance compliance`
  section ticking the 9 rules in `plugin/skills/CONTRIBUTING.md`.
  Behavior to specify:
  - **Step 0 — context check:** call `lifecycle.skill_preamble(repo, 'prd')`,
    surface any non-None hint.
  - **Mode detection:** `PRD.md` present at project root → update mode; absent →
    create mode.
  - **Create mode:** if the project is fresh, interview one-question-at-a-time
    (brainstorm style, `AskUserQuestion`, ≤4 options); if mature, synthesize a
    draft from `CLAUDE.md` + `.renmark/specs/` + `CHANGELOG.md`. Present the full
    draft for explicit approval, THEN write `PRD.md` from
    `plugin/templates/PRD.md.template` and append a `## [date] — PRD created`
    CHANGELOG entry.
  - **Update mode:** read current `PRD.md`, reconcile against the requested
    change, present a DIFF, and write ONLY after explicit human approval (living
    doc, human-gated — consistent with renmark's approval-gate doctrine). Bump
    `last_reviewed`; append a `## [date] — PRD updated` CHANGELOG entry.
  - **Human gate:** when a PRD write is *proposed by an automated stage* (e.g.
    feature's drift check), set/check the lifecycle `human_review_*` fields; never
    write the PRD without approval.
  - **Context hygiene:** the full PRD is read only inside this dedicated skill
    invocation; note that orchestrator/router callers must NOT read the PRD body
    (they dispatch the alignment subagent — see `_shared/prd-alignment.md`).
  - **Final step:** the skill writes `PRD.md` (project root, committed) and a
    CHANGELOG entry — no lifecycle stage advance required (PRD is cross-stage).
  Document the `## Governance compliance` section honestly (G2 state = PRD.md +
  CHANGELOG; G3 ≤5-line summaries; G5/G11 alignment reading delegated to a
  subagent; etc.).

### Task 3: alignment subagent contract
- **mode:** A
- **target:** plugin/skills/_shared/prd-alignment.md
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 1
- **est_tokens:** 800
- **est_cost_usd:** 0.03
- **verifier:** test -f plugin/skills/_shared/prd-alignment.md && grep -q "verdict" plugin/skills/_shared/prd-alignment.md
- **spec:**
  Create the shared brief for the **PRD alignment subagent** — the
  hygiene-preserving contract reused by `feature` (and any new-feature/change
  flow). Mirror the style of `plugin/skills/_shared/scope-contract.md` and
  `handoff-menu.md`. Specify: the orchestrator/router dispatches an isolated
  subagent (Agent tool) passing ONLY the feature description + file scope; the
  subagent reads `PRD.md` + relevant docs IN ITS OWN CONTEXT and returns a
  bounded ≤5-line result with fields: `verdict: aligned | drift`; if `drift`, a
  one-line reason + an optional proposed PRD addition (markdown snippet). State
  explicitly: the router/orchestrator MUST NOT read the PRD body itself; it sees
  only the verdict; on `drift` it routes the proposed addition into
  `/renmark:prd` update mode (human-gated). This is the G11/"orchestrator does
  not accumulate" enforcement point.

### Task 4: prd command shim
- **mode:** A
- **target:** plugin/commands/prd.md
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 1
- **est_tokens:** 200
- **est_cost_usd:** 0.00
- **verifier:** test -f plugin/commands/prd.md && grep -q "skills/prd/SKILL.md" plugin/commands/prd.md
- **spec:**
  Create the command shim mirroring `plugin/commands/feature.md` exactly in
  shape. Frontmatter: a `description` (one paragraph: when to use `/renmark:prd`
  — create or update the project PRD source of truth) and
  `argument-hint: '[create | update | change description]'`. Body:
  `Read ${CLAUDE_PLUGIN_ROOT}/skills/prd/SKILL.md and follow its instructions exactly. The user provided this input: $ARGUMENTS`
  followed by `If $ARGUMENTS is empty, begin the prd skill's flow.`

### Task 5: register prd domain
- **mode:** B
- **target:** renmark/lifecycle.py
- **complexity:** medium
- **executor:** codex
- **parallel_group:** 1
- **est_tokens:** 250
- **est_cost_usd:** 0.01
- **verifier:** python3 -c "from renmark import lifecycle; assert lifecycle.DOMAIN_BY_SKILL.get('prd')=='build', lifecycle.DOMAIN_BY_SKILL.get('prd')" && python3 -m py_compile renmark/lifecycle.py
- **spec:**
  In `renmark/lifecycle.py`, add `"prd": "build",` to the `DOMAIN_BY_SKILL`
  dict (the build-domain group, alongside `feature`). Do not change any other
  entry. This makes `lifecycle.skill_preamble(repo, 'prd')` resolve the correct
  domain for cross-domain `/clear` recommendations.

### Task 6: wire prd into start
- **mode:** B
- **target:** plugin/skills/start/SKILL.md
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 2
- **est_tokens:** 700
- **est_cost_usd:** 0.03
- **verifier:** grep -q "renmark:prd" plugin/skills/start/SKILL.md
- **spec:**
  Edit the `start` skill to add a PRD step for new projects: after scaffolding /
  scope is established and before/around routing to brainstorm or plan, if no
  `PRD.md` exists at the project root, offer to invoke `/renmark:prd` (create
  mode) so the project gets its source of truth early. Keep it skippable (offer,
  don't force). Match the skill's existing tone and step numbering; do not
  restructure unrelated steps.

### Task 7: wire alignment check into feature
- **mode:** B
- **target:** plugin/skills/feature/SKILL.md
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 2
- **est_tokens:** 800
- **est_cost_usd:** 0.03
- **verifier:** grep -q "prd-alignment" plugin/skills/feature/SKILL.md
- **spec:**
  Edit the `feature` router skill to add a PRD alignment step. Per the router
  contract (feature is a router, not a reasoning agent), it must DISPATCH the
  check, not reason it inline: dispatch the PRD alignment subagent per
  `plugin/skills/_shared/prd-alignment.md`, passing the feature description +
  file scope, and receive a bounded `verdict`. On `drift`, route the proposed
  PRD addition into `/renmark:prd` update mode (human-gated). State explicitly
  that the router MUST NOT read the `PRD.md` body — it sees only the verdict.
  Place the step logically before/around the Plan dispatch. Reference the shared
  contract by path; do not inline the full brief.

### Task 8: plan traceability note
- **mode:** B
- **target:** plugin/skills/plan/SKILL.md
- **complexity:** medium
- **executor:** codex
- **parallel_group:** 2
- **est_tokens:** 600
- **est_cost_usd:** 0.02
- **verifier:** grep -q "serves" plugin/skills/plan/SKILL.md
- **spec:**
  Edit the `plan` skill so each generated task carries an optional one-line
  traceability note `serves: REQ-n` (or `serves: new`) tying it to a PRD
  requirement when a `PRD.md` exists. Add it to the task-field list in the
  Overview and to the plan-file format example as an optional field. Keep it
  lightweight and NON-enforcing (no hard gating, no failure if absent) — and do
  NOT make plan read the full PRD into context; the note is best-effort from the
  requirement IDs surfaced by the alignment step / spec. Do not change routing,
  cost, or validation logic.

### Task 9: list prd in help
- **mode:** B
- **target:** plugin/skills/help/SKILL.md
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 2
- **est_tokens:** 300
- **est_cost_usd:** 0.00
- **verifier:** grep -q "renmark:prd" plugin/skills/help/SKILL.md
- **spec:**
  Add `/renmark:prd` to the help skill's command listing with a one-sentence
  description: "Create or update the project's PRD — the per-project source of
  truth that plans and features align to." Place it logically (near brainstorm/
  start, the project-documentation commands). Match existing formatting exactly.

### Task 10: CLAUDE.md pointer + tooling row
- **mode:** B
- **target:** CLAUDE.md
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 2
- **est_tokens:** 350
- **est_cost_usd:** 0.00
- **verifier:** grep -q "PRD.md" CLAUDE.md
- **spec:**
  Edit the project-root `CLAUDE.md`. (1) Add a `/renmark:prd` row to the
  "Tooling — renmark workflow" table: "Create/update the project PRD — the
  source of truth that plans and features align to." (2) Add one **plain-text**
  pointer line (NOT an `@import` — an import would auto-load the PRD into every
  session): "Source of truth: `PRD.md`. For new features/changes, dispatch a
  subagent to read `PRD.md` + docs and return a bounded alignment/drift summary —
  never load the full PRD into the orchestrator." Do not use `@PRD.md` syntax
  anywhere. This change MUST be mirrored in `AGENTS.md` (Task 11).

### Task 11: AGENTS.md pointer (mirror)
- **mode:** B
- **target:** AGENTS.md
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 2
- **est_tokens:** 350
- **est_cost_usd:** 0.00
- **verifier:** grep -q "PRD.md" AGENTS.md
- **spec:**
  Mirror Task 10 into the project-root `AGENTS.md` (the two files are kept in
  sync per the CLAUDE.md mirror rule): add the same `/renmark:prd` tooling entry
  and the same **plain-text** PRD pointer line. Never use `@import` / `@PRD.md`
  syntax. Keep wording identical to the CLAUDE.md change so the two stay in sync.

### Task 12: CLAUDE.md template pointer
- **mode:** B
- **target:** plugin/templates/CLAUDE.md.template
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 2
- **est_tokens:** 300
- **est_cost_usd:** 0.00
- **verifier:** grep -q "PRD.md" plugin/templates/CLAUDE.md.template
- **spec:**
  Add the same **plain-text** PRD pointer line to the CLAUDE.md template so new
  projects scaffolded by renmark inherit it: "Source of truth: `PRD.md` (if
  present). For new features/changes, dispatch a subagent to read `PRD.md` +
  docs and return a bounded alignment/drift summary — never load the full PRD
  into the orchestrator." Never use `@import` syntax. Mirror into the AGENTS.md
  template (Task 13).

### Task 13: AGENTS.md template pointer (mirror)
- **mode:** B
- **target:** plugin/templates/AGENTS.md.template
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 2
- **est_tokens:** 300
- **est_cost_usd:** 0.00
- **verifier:** grep -q "PRD.md" plugin/templates/AGENTS.md.template
- **spec:**
  Mirror Task 12 into `plugin/templates/AGENTS.md.template` — identical
  plain-text PRD pointer line, no `@import` syntax. Keep wording identical to the
  CLAUDE.md template change.

### Task 14: enforce prd in install test
- **mode:** B
- **target:** tests/integration/test_plugin_install.py
- **complexity:** medium
- **executor:** codex
- **parallel_group:** 3
- **est_tokens:** 400
- **est_cost_usd:** 0.01
- **verifier:** cd /home/renmark/projects/ai-system && python3 -m pytest tests/integration/test_plugin_install.py -q
- **spec:**
  In `test_plugin_has_required_skill_files`, add `"prd"` to the `required` set so
  the documented-skill set enforces the new skill's existence, and update the
  docstring count ("all 14 documented skills" → "15"). Do not change
  `test_commands_directory_complete` (it derives names dynamically and will pass
  once the prd skill+command exist). Depends on Tasks 2 and 4 (prd skill +
  command must exist) — runs in a later wave.

---

## Cost preview (honest — includes ~10k Agent overhead per haiku/sonnet/opus task)

| Task | Executor | est_tokens | cost |
|---|---|---|---|
| 1 PRD template | codex | 600 | $0.02 |
| 2 prd skill | opus | 2600 | $0.19 |
| 3 alignment contract | sonnet | 800 | $0.03 |
| 4 prd command | haiku | 200 | $0.00 |
| 5 lifecycle domain | codex | 250 | $0.01 |
| 6 start wiring | sonnet | 700 | $0.03 |
| 7 feature wiring | sonnet | 800 | $0.03 |
| 8 plan traceability | codex | 600 | $0.02 |
| 9 help listing | haiku | 300 | $0.00 |
| 10 CLAUDE.md | haiku | 350 | $0.00 |
| 11 AGENTS.md | haiku | 350 | $0.00 |
| 12 CLAUDE.md template | haiku | 300 | $0.00 |
| 13 AGENTS.md template | haiku | 300 | $0.00 |
| 14 install test | codex | 400 | $0.01 |

**Total: 14 tasks · 3 waves · ~$0.37**
Executors: haiku×6, codex×4, sonnet×3, opus×1

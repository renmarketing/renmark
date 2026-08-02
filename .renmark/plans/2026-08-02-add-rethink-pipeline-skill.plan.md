---
artifact_type: plan
schema_version: 1
created_at: 2026-08-02T00:00:00+00:00
source_sha: f01762d
related_plan: null
generator: sonnet
completion_state: complete
confidence: high
validation_status: unvalidated
retry_count: 0
parser_success: true
schema_compliance: true
dependency_refs:
  - PRD.md
  - CHANGELOG.md
  - plugin/skills/roadmap/SKILL.md
  - plugin/skills/help/SKILL.md
  - plugin/skills/guide/SKILL.md
  - plugin/skills/.shared/agency-delivery.md
  - plugin/skills/.shared/prd-alignment.md
  - plugin/skills/.shared/handoff-menu.md
  - plugin/skills/.shared/next-steps.md
  - renmark/program.py
  - renmark/agency.py
---

# Add `/renmark:rethink` — brownfield transformation pipeline

**Context.** REQ-28 (approved 2026-08-02) requires a distinct entry point for
reassessing and transforming an *existing* application, separate from
`/renmark:start`'s greenfield lane. This plan adds the skill, its thin command
wrapper, and updates every place renmark documents its pipeline list
(`CLAUDE.md`, `AGENTS.md`, `README.md`, `/renmark:help`, `/renmark:guide`,
plugin manifests) so `rethink` is discoverable alongside `start` / `feature` /
`debug` / `roadmap` / `finish`.

**Non-goals for this plan:** implementing any actual survey/baseline/blueprint
logic beyond the skill's documented steps (those steps dispatch bounded
subagents at *run time* — this plan only builds the skill definition itself,
not a demo run against a real project). No changes to `renmark/agency.py` or
`renmark/program.py` — `rethink` reuses their existing public API
(`agency.activate`, `program.write_program`) rather than extending it.

### Task 1: rethink pipeline skill definition

- **mode:** A
- **target:** plugin/skills/rethink/SKILL.md
- **complexity:** hard
- **executor:** opus
- **role:** general-purpose
- **role_reason:** authoring a new pipeline contract (gates, subagent dispatch shapes, staged hand-off into existing milestone machinery) is architecture-level design work; no specialized profile (docs-editor is a fixed-template mechanical editor) fits designing a novel pipeline's control flow.
- **parallel_group:** 1
- **est_tokens:** 3500
- **est_cost_usd:** 0.0653
- **verifier:** test -f plugin/skills/rethink/SKILL.md && grep -q "^name: rethink" plugin/skills/rethink/SKILL.md
- **serves:** REQ-28
- **spec:**
  Write `plugin/skills/rethink/SKILL.md`, a new renmark pipeline skill, following
  the structural conventions of this repo's existing pipeline skills (read
  `plugin/skills/roadmap/SKILL.md` and `plugin/skills/feature/SKILL.md` first
  for tone/format — frontmatter with `name`/`description`, `# rethink` header,
  `## Overview`, `## When to Use`, `## Steps`, `## Do not`, `## What's next`).

  Frontmatter `description` (used for skill discovery — match this style):
  `"Use for the Brownfield Transformation pipeline (/renmark:rethink) when reassessing or migrating an EXISTING application — plain requests like 'rethink this app', 'this codebase needs a rebuild plan', 'help me modernize X'. Surveys before it structurally changes anything; for a brand-new project use /renmark:start, for a bounded addition within the existing direction use /renmark:feature."`

  **Overview.** State plainly: rethink is the brownfield counterpart to
  `/renmark:start`'s greenfield lane. Analogy (from REQ-28 / the Owner's brief):
  renovating an occupied building — inspect what exists, decide what stays, then
  renovate in usable sections without shutting everything down. Cite REQ-28.

  **Steps — six stages, each a bounded artifact + a gate before the next:**

  1. **Survey the current system** — dispatch ONE bounded subagent (Agent tool,
     `role: researcher` or `general-purpose`, per this project's context-hygiene
     rule — REQ-5) that reads the target project's architecture, data flows,
     features actually in use (not just declared), tests/integrations/deployment/
     ops dependencies, and known pain/duplication/fragility/cost signals (grep
     TODO/FIXME, check test coverage gaps, stale dependencies). The subagent
     writes a survey artifact to `.renmark/rethink/<slug>/survey.md` and returns
     ONLY a bounded ≤5-line summary (counts, top findings, artifact path) — the
     full survey body never enters orchestrator context (REQ-5). Reuse
     `/renmark:init`'s project-map generation where the target already has one
     (`.renmark/memory/project-map.md`) instead of re-deriving it from scratch —
     point the survey subagent at it as a starting input.

  2. **Establish a behavioral baseline** — a second bounded subagent (or the
     same one, same artifact directory) captures: what must keep working (the
     current outputs/acceptance examples), any measurable performance/quality/
     cost baseline, and a set of compatibility tests/checks that must stay green
     through the transformation. Written to
     `.renmark/rethink/<slug>/baseline.md`. This baseline is what every later
     migration release is checked against — no structural change may regress it
     without an explicit, Owner-approved exception.

  3. **Classify the existing system** — using the survey + baseline, classify
     each identified component/capability as one of: **Keep** (works, stays
     as-is) / **Improve** (works, needs bounded rework) / **Replace** (target
     architecture supersedes it) / **Remove** (dead weight, no longer earns its
     keep) / **Unknown — needs a spike** (insufficient evidence to classify;
     names a bounded time/scope-boxed investigation, not open-ended research).
     Written to `.renmark/rethink/<slug>/classification.md`.

  4. **Create the target blueprint** — desired capabilities and boundaries,
     new architecture ONLY where the classification justifies it (Replace
     items), explicit migration constraints (what must not break, what budget/
     timeline applies), and an explicit non-goals list (what this transformation
     is deliberately NOT attempting). Reuse `/renmark:blueprint`'s existing
     Mermaid-diagram-from-`project-map.md` convention for the *current* state
     diagram, paired with a new *target* state diagram — do not invent a
     separate diagramming approach. Written to
     `.renmark/rethink/<slug>/target-blueprint.md`.

  5. **Produce a transformation roadmap** — a sequence of SMALL, independently
     usable releases (never a big-bang rewrite); each release states its own
     compatibility guarantee and rollback path; old and new components may
     coexist temporarily. This roadmap is built as a `renmark.program` (reuse
     `renmark.program.write_program` / the `Program`/`StageNode` shapes already
     used by `/renmark:roadmap`'s forward-plan mode — do NOT invent a parallel
     roadmap format). The FIRST release in the roadmap defaults to "baseline and
     compatibility coverage" (turning stage 2's baseline into real, runnable
     compatibility tests) rather than any architecture replacement — this is a
     hard default; only an explicit Owner override may reorder it.

  6. **Owner gate, then hand off to milestone execution** — before any stage
     transitions from planning to execution, present the classification +
     target blueprint + roadmap as a bounded summary and require one explicit
     `AskUserQuestion` approval (REQ-4/REQ-12 style human gate — mirror
     `plugin/skills/.shared/agency-delivery.md`'s milestone-approval pattern,
     cite it by pointer, do not re-describe its mechanics here). On approval,
     activate renmark's EXISTING Agency/milestone execution machinery
     (`renmark.agency.activate` + the `Program` written in stage 5) rather than
     building a bespoke rethink-only executor — Architect (target structure,
     already produced in stage 4) → Engineer (migration milestones, the
     `Program` stages from stage 5) → Workers (bounded per-milestone changes,
     via the existing `orchestrate`/`feature` dispatch path) → Inspectors
     (verify old behavior preserved via the stage-2 baseline/compatibility
     tests AND new capability delivered) → Owner accepts each usable release
     (mirrors `/renmark:finish`'s existing accept/release gate — do not
     duplicate it). Rethink's own responsibility ends at handing off an
     Owner-approved `Program`; it does not re-implement orchestrate/finish.

  **Context hygiene throughout:** every stage's heavy artifact (survey,
  baseline, classification, blueprint, roadmap body) is written to
  `.renmark/rethink/<slug>/` on disk; the orchestrator/router only ever sees
  bounded ≤5-line summaries + artifact paths between stages (REQ-5). Do not
  design any stage that reads a prior stage's full artifact body back into the
  primary conversation.

  **`## Do not` section** should explicitly list: do not implement or
  restructure anything before the Owner approves classification + blueprint +
  first milestone (REQ-28's acceptance criterion); do not invent a parallel
  execution system — reuse `agency.py`/`program.py`/`orchestrate`/`finish`; do
  not default the first release to architecture replacement; do not skip the
  survey/baseline stages even for a project the user claims to already know
  well — evidence before claim (mirrors the project's existing "Verification
  before completion" rule).

  **`## What's next`** should follow the class-1 pipeline pattern (cite
  `plugin/skills/.shared/next-steps.md` by pointer, `AskUserQuestion`,
  state-derived recommendation) — same shape as `feature`/`finish`'s existing
  "What's next" sections; do not paste the rendering rules inline, cite the
  file.

### Task 2: rethink command wrapper

- **mode:** A
- **target:** plugin/commands/rethink.md
- **complexity:** simple
- **executor:** haiku
- **role:** docs-editor
- **parallel_group:** 1
- **est_tokens:** 150
- **est_cost_usd:** 0.0011
- **verifier:** test -f plugin/commands/rethink.md && grep -q "rethink/SKILL.md" plugin/commands/rethink.md
- **serves:** REQ-28
- **spec:**
  Create `plugin/commands/rethink.md` as a thin command-wrapper file, exactly
  mirroring the format of `plugin/commands/roadmap.md` (read it first for the
  exact shape — frontmatter `description` + `argument-hint`, then a body that
  reads: "Read `${CLAUDE_PLUGIN_ROOT}/skills/rethink/SKILL.md` and follow its
  instructions exactly. The user provided this input: $ARGUMENTS" followed by
  "If `$ARGUMENTS` is empty, begin the rethink skill's flow."). Frontmatter
  `description`: "Use for the Brownfield Transformation pipeline
  (/renmark:rethink) when reassessing or migrating an EXISTING application —
  plain requests like 'rethink this app', 'this needs a rebuild plan',
  'modernize X'. Surveys before structurally changing anything; for a new
  project use /renmark:start, for a bounded addition use /renmark:feature."
  No `argument-hint` needed (rethink takes a free-text app/project description,
  not flags) — omit that frontmatter key entirely if `roadmap.md`'s format
  makes it optional, matching whichever existing command file (e.g.
  `plugin/commands/debug.md`) has no `argument-hint` for a free-text case.

### Task 3: plugin.json pipeline count + description

- **mode:** B
- **target:** plugin/.claude-plugin/plugin.json
- **complexity:** simple
- **executor:** haiku
- **role:** general-purpose
- **role_reason:** JSON config value edit — no specialized profile's allowed_targets covers plugin manifests (docs-editor is markdown-only, code-implementer is renmark/**/*.py-only).
- **parallel_group:** 1
- **est_tokens:** 120
- **est_cost_usd:** 0.0011
- **verifier:** python3 -c "import json; d=json.load(open('plugin/.claude-plugin/plugin.json')); assert 'rethink' in d['description']" && echo OK
- **serves:** REQ-28
- **spec:**
  In `plugin/.claude-plugin/plugin.json`, edit the `"description"` field only.
  It currently reads (verify exact current text before editing, it may have
  drifted): "Pipeline-first build assistant for Codex and Claude Code. The user
  works through six pipelines — /renmark:init (adopt a repo), /renmark:start
  (new build), /renmark:feature (add/change), /renmark:debug (fix),
  /renmark:roadmap (gaps / what's next), /renmark:finish (ship) — backed by
  guided planning, implementation, verification, recovery, and release skills.
  Persistent project state lives in .renmark/." Change "six pipelines" to
  "seven pipelines" and insert `/renmark:rethink (reassess/transform an
  existing app)` immediately after `/renmark:start (new build)` in the listed
  sequence — keep every other word identical, this is a minimal insertion, not
  a rewrite. Do not touch `"version"` or any other field.

### Task 4: codex-plugin.json description

- **mode:** B
- **target:** plugin/.codex-plugin/plugin.json
- **complexity:** simple
- **executor:** haiku
- **role:** general-purpose
- **role_reason:** same as Task 3 — JSON config, no matching specialized profile.
- **parallel_group:** 1
- **est_tokens:** 100
- **est_cost_usd:** 0.0011
- **verifier:** python3 -c "import json; json.load(open('plugin/.codex-plugin/plugin.json'))" && echo OK
- **serves:** REQ-28
- **spec:**
  `plugin/.codex-plugin/plugin.json`'s `"description"` and `interface.longDescription`
  fields describe renmark generically (no per-pipeline list, no "six" count) —
  read the file first. If either field already lists specific pipelines by
  name, apply the same "six"→"seven" + insert-rethink-after-start edit as Task
  3. If neither field names individual pipelines (current text is generic —
  "guided Codex and Claude Code skills for project initialization, planning,
  feature work, debugging, audits, verification, recovery, and finish lanes"),
  make NO edit — leave the file untouched, since there is nothing pipeline-count
  specific to update. Do not touch `"version"` or any other field either way.

### Task 5: marketplace.json pipeline count + description

- **mode:** B
- **target:** .claude-plugin/marketplace.json
- **complexity:** simple
- **executor:** haiku
- **role:** general-purpose
- **role_reason:** same as Task 3 — JSON config, no matching specialized profile.
- **parallel_group:** 1
- **est_tokens:** 120
- **est_cost_usd:** 0.0011
- **verifier:** python3 -c "import json; d=json.load(open('.claude-plugin/marketplace.json')); assert 'rethink' in d['plugins'][0]['description']" && echo OK
- **serves:** REQ-28
- **spec:**
  In `.claude-plugin/marketplace.json`, edit `plugins[0].description` only. It
  currently reads (verify exact current text first): "Pipeline-first build
  assistant for Codex and Claude Code. Six pipelines — /renmark:init (adopt a
  repo), /renmark:start (new build), /renmark:feature (add/change),
  /renmark:debug (fix), /renmark:roadmap (gaps / what's next), /renmark:finish
  (ship) — plus guided planning, implementation, verification, recovery, and
  release skills. Persistent project state lives in .renmark/." Change "Six
  pipelines" to "Seven pipelines" and insert `/renmark:rethink
  (reassess/transform an existing app)` immediately after `/renmark:start (new
  build)`. Minimal insertion, identical wording otherwise. Do not touch
  `"version"` (top-level or nested) or any other field.

### Task 6: CLAUDE.md routing table

- **mode:** B
- **target:** CLAUDE.md
- **complexity:** simple
- **executor:** haiku
- **role:** docs-editor
- **parallel_group:** 1
- **est_tokens:** 150
- **est_cost_usd:** 0.0011
- **verifier:** grep -q "renmark:rethink" CLAUDE.md
- **serves:** REQ-28
- **spec:**
  In `CLAUDE.md`, find the "Default to renmark for build/dev work" paragraph
  (search for the exact text: "route it through the matching renmark pipeline
  without waiting for the slash command: new build → `/renmark:start`; change
  to an existing project → `/renmark:feature`; something broken →
  `/renmark:debug`; what's next / find gaps → `/renmark:roadmap`; ship it →
  `/renmark:finish`; adopt renmark into a repo → `/renmark:init`."). Insert `;
  reassess/transform an existing app → \`/renmark:rethink\`` immediately after
  the `/renmark:start` clause and before the `/renmark:feature` clause (i.e.
  the routing list becomes: new build → start; reassess/transform an existing
  app → rethink; change to an existing project → feature; broken → debug; ...).
  Change ONLY this one sentence — do not touch any other section, do not
  reorder unrelated bullets, do not touch the "Managed Project Delivery
  Contract" or any other CLAUDE.md section.

### Task 7: AGENTS.md routing table (mirror)

- **mode:** B
- **target:** AGENTS.md
- **complexity:** simple
- **executor:** haiku
- **role:** docs-editor
- **parallel_group:** 1
- **est_tokens:** 150
- **est_cost_usd:** 0.0011
- **verifier:** grep -q "renmark:rethink" AGENTS.md
- **serves:** REQ-28
- **spec:**
  In `AGENTS.md`, find the "Default to renmark for build/dev work" line
  (search for: "new build → `/renmark:start`; existing-project change →
  `/renmark:feature`; broken → `/renmark:debug`; what's next →
  `/renmark:roadmap`; ship → `/renmark:finish`; adopt → `/renmark:init`.").
  Insert `; reassess/transform an existing app → \`/renmark:rethink\`` after
  the `/renmark:start` clause and before the `/renmark:feature` clause,
  matching Task 6's edit to CLAUDE.md exactly (same insertion point, same
  semantic ordering) — this file must stay semantically mirrored with
  CLAUDE.md per this project's own durable-guard mirroring rule. Change ONLY
  this one sentence.

### Task 8: README pipeline listings

- **mode:** B
- **target:** README.md
- **complexity:** simple
- **executor:** haiku
- **role:** docs-editor
- **parallel_group:** 1
- **est_tokens:** 300
- **est_cost_usd:** 0.0019
- **verifier:** grep -q "renmark:rethink" README.md
- **serves:** REQ-28
- **spec:**
  In `README.md`, make three insertions (read the file first to get exact
  surrounding text/formatting — match existing style precisely):
  1. In the top bullet list (near lines 6-10, the `- **\`/renmark:start\`**  —
     build something new from plain English` style list), add a new bullet
     `- **\`/renmark:rethink\`** — reassess and transform an existing app`
     immediately after the `/renmark:start` bullet.
  2. Change the "## The six pipelines" heading to "## The seven pipelines" and
     add a new table row immediately after the `/renmark:start` row (in the
     table with columns like `| /renmark:start | Build something new |
     intent → brainstorm ... |`):
     `| \`/renmark:rethink\` | Reassess/transform an existing app | survey →
     behavioral baseline → keep/improve/replace/remove/spike classification →
     target blueprint → transformation roadmap → milestone hand-off |`
  3. In the fuller skills table further down (the one with rows like
     `| \`/renmark:feature\` | Full pipeline with branch isolation ... |`), add
     a row: `| \`/renmark:rethink\` | Brownfield survey → baseline →
     classify → blueprint → migration roadmap; hands off to milestone
     execution |` in a sensible position near `/renmark:start`/`/renmark:feature`.
  Do not touch any other README section (install instructions, etc.).

### Task 9: help skill static block

- **mode:** B
- **target:** plugin/skills/help/SKILL.md
- **complexity:** simple
- **executor:** haiku
- **role:** docs-editor
- **parallel_group:** 1
- **est_tokens:** 250
- **est_cost_usd:** 0.0016
- **verifier:** grep -q "renmark:rethink" plugin/skills/help/SKILL.md
- **serves:** REQ-28
- **spec:**
  In `plugin/skills/help/SKILL.md`, inside the fenced text block under
  "## When invoked" (the literal help output text), two edits:
  1. In the `── Pipelines ──` section, add a new pipeline block immediately
     after the `/renmark:start [idea]` block and before `/renmark:feature`,
     matching the exact existing format (e.g.
     `  /renmark:rethink [app]      Reassess and transform an existing app.\n
     \      survey → behavioral baseline → keep/improve/replace/remove/spike →\n
     \      target blueprint → migration roadmap → milestone hand-off`
     — match indentation/arrow style of the surrounding blocks exactly, read
     them first).
  2. In the "Which one?" quick map line (`new app → start   existing app →
     feature   broke → debug`), add `existing app, needs rethinking → rethink`
     as an additional clause, keeping the line's existing terse style.
  3. In the "── All skills (grouped) ──" section, under "Product / spec", add
     a line `/renmark:rethink   — brownfield survey → baseline → classify →
     blueprint → migration roadmap` positioned near `/renmark:start`/
     `/renmark:feature`.
  Do not touch any other part of the printed block or the surrounding prose —
  this file's whole contract is "keep it honest, only describe what exists,"
  so make these three precise insertions and nothing else.

### Task 10: guide skill routing question

- **mode:** B
- **target:** plugin/skills/guide/SKILL.md
- **complexity:** simple
- **executor:** haiku
- **role:** docs-editor
- **parallel_group:** 1
- **est_tokens:** 250
- **est_cost_usd:** 0.0016
- **verifier:** grep -q "renmark:rethink" plugin/skills/guide/SKILL.md
- **serves:** REQ-28
- **spec:**
  In `plugin/skills/guide/SKILL.md`'s "### 1. Ask the one routing question"
  numbered list (currently 8 options ending in "8. I'm not sure — show me the
  options"), insert a new option "2. Reassess or transform an app I already
  have — survey it, decide what stays, plan a migration" immediately after
  option "2. Change or add to an existing build" (so it becomes the new
  option 3), and renumber every subsequent option by one (old 3→4, 4→5, 5→6,
  6→7, 7→8, 8→9). Then update the "### 2. Route based on answer" table to add
  a matching row `| 3 — reassess/transform | \`/renmark:rethink\` | Mention
  \`/renmark:feature\` if it turns out to be a small bounded addition, not a
  full reassessment |` in the correct position, and renumber every other row's
  leading "Answer" number to match the new numbering (old 3→4 debug, 4→5
  roadmap, 5→6 finish, 6→7 init, 7→8 interrupted, 8→9 not sure). Keep every
  other word of every unrenumbered row identical — this is a renumber +
  one-insert edit, not a rewrite.

## Cost preview

| Executor | Count | Tokens (incl. agent overhead) | $/kT | Cost |
|---|---:|---:|---:|---:|
| opus | 1 | 3500 + 10000 = 13500 | $0.015 | $0.2025 |
| haiku | 9 | (150+100+120+120+150+150+300+250+250) + 9×10000 = 91540 | $0.0001 | $0.0092 |

**Total: 10 tasks, 1 parallel group, ~105,040 tokens, ~$0.21**

---
artifact_type: plan
schema_version: 1
created_at: 2026-06-05
source_sha: 8d3d0c21daa8918d0f3d25c047a1c75fa818d125
generator: plan
dependency_refs:
  - .renmark/specs/2026-06-05-blueprint.spec.md
  - .renmark/research/2026-06-05-blueprint.research.md
completion_state: complete
confidence: high
validation_status: unvalidated
---

# Plan — `/renmark:blueprint` (prototype/schematic pipeline step)

Implements the Phase-3 blueprint feature from
`.renmark/specs/2026-06-05-blueprint.spec.md`: a standalone-plus-embedded
renmark step that synthesizes a living `SCHEMATIC.md` (always) and `PROTOTYPE.html`
(UI builds only) from `.renmark/memory/project-map.md`, using a hybrid
marker-based update. No new runtime dependencies. Three waves: foundational
code/templates → command/integration/docs → skill + tests.

**Standing constraints (from CHANGELOG "Do not change" + spec guardrails):**
- `project-map.md` is the ONLY architecture source — blueprint synthesizes, never rescans.
- Hybrid update: regenerate ONLY content between `<!-- RENMARK:GENERATED:<ID>:START/END -->` markers; byte-preserve everything outside; single current-state artifact.
- Blueprint is an artifact **touchpoint like PRD, NOT a lifecycle stage** — do not add it to `STAGES`/`NEXT_BY_STAGE`.
- Write-boundary: `/renmark:init` writes only `project-map.md`/`stack.md`; `/renmark:blueprint` is the SOLE writer of `SCHEMATIC.md`/`PROTOTYPE.html`.
- `source_sha` in a generated block = hash of `project-map.md`, not an implied repo scan.
- No deterministic language parsers in this phase (deferred).

---

### Task 1: blueprint splice helper
- **mode:** A
- **target:** renmark/blueprint.py
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 1
- **est_tokens:** 1200
- **est_cost_usd:** 0.034
- **verifier:** python3 -c "import renmark.blueprint" && ruff check renmark/blueprint.py
- **serves:** new
- **spec:**
  Create `renmark/blueprint.py`, the deterministic core of the blueprint feature.
  Pure stdlib, PEP 8, fully type-annotated (mypy clean). Provide:

  1. Marker constants / builder. Generated regions are delimited by HTML comments:
     `<!-- RENMARK:GENERATED:<ID>:START source-sha=<sha> -->` … `<!-- RENMARK:GENERATED:<ID>:END -->`.
     `<ID>` is `SCHEMATIC` or `PROTOTYPE`. Provide a helper to build the START
     marker given an id + source sha (the sha is the `project-map.md` hash, NOT
     a repo scan — see constraints).
  2. `splice_generated_block(text: str, marker_id: str, new_content: str, *, source_sha: str) -> str`
     — replace ONLY the span between the START/END markers for `marker_id` with
     `new_content`, rebuilding the START marker with `source_sha`. Byte-preserve
     everything outside the markers. MUST be idempotent: splicing the same
     content twice yields identical output. If the markers are absent from
     `text`, raise a clear exception (e.g. `MarkerNotFoundError`) — callers use
     this to decide between "create from template" (no file) and "abort, don't
     clobber" (file exists without markers). Handle a START without a matching
     END as an error too.
  3. `detect_ui(stack_md_text: str | None) -> bool | None` — parse the `Frontend`
     field from a `stack.md` body. Return `True` if Frontend is present and not
     `none`/empty, `False` if explicitly `none`, and `None` if `stack.md` is
     missing or has no Frontend field (caller then asks the user). Be tolerant of
     the documented `## Frontend` section heading AND an inline `Frontend:` line.
  Keep it small (~targeting the research's ~30-LOC splice core plus the two
  parsers). No diagram/HTML generation here — that is the skill's LLM job.

### Task 2: SCHEMATIC.md template
- **mode:** A
- **target:** plugin/templates/SCHEMATIC.md.template
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 1
- **est_tokens:** 400
- **est_cost_usd:** 0.001
- **verifier:** test -f plugin/templates/SCHEMATIC.md.template && grep -q "RENMARK:GENERATED:SCHEMATIC:START" plugin/templates/SCHEMATIC.md.template && grep -q "RENMARK:GENERATED:SCHEMATIC:END" plugin/templates/SCHEMATIC.md.template
- **serves:** new
- **spec:**
  Create the `SCHEMATIC.md` skeleton template. Structure exactly:
  `# Schematic` title; a `## Overview` section with a one-line human-editable
  placeholder comment (human-owned, preserved across regen); a
  `## Current Architecture` section containing the generated block —
  `<!-- RENMARK:GENERATED:SCHEMATIC:START source-sha=PENDING -->`, then a fenced
  ```mermaid``` block with a minimal `flowchart TD` placeholder, then
  `<!-- RENMARK:GENERATED:SCHEMATIC:END -->`; and a `## Notes / Decisions` section
  with a human-editable placeholder. Use `{{PROJECT_NAME}}` / `{{DATE}}`
  placeholders consistent with the other files in `plugin/templates/`. Make clear
  in a comment that everything OUTSIDE the generated markers is human-owned.

### Task 3: PROTOTYPE.html template
- **mode:** A
- **target:** plugin/templates/PROTOTYPE.html.template
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 1
- **est_tokens:** 600
- **est_cost_usd:** 0.001
- **verifier:** test -f plugin/templates/PROTOTYPE.html.template && grep -q "RENMARK:GENERATED:PROTOTYPE:START" plugin/templates/PROTOTYPE.html.template && grep -q "RENMARK:GENERATED:PROTOTYPE:END" plugin/templates/PROTOTYPE.html.template
- **serves:** new
- **spec:**
  Create the `PROTOTYPE.html` skeleton template: a self-contained, dependency-free
  HTML5 document (`<!DOCTYPE html>`, `<head>` with `<title>{{PROJECT_NAME}} — Prototype</title>`
  and a minimal inline `<style>`). The regenerable region wraps the mockup body:
  `<!-- RENMARK:GENERATED:PROTOTYPE:START source-sha=PENDING -->` immediately
  inside `<body>`, a placeholder mockup (e.g. a centered card saying the prototype
  will be generated), then `<!-- RENMARK:GENERATED:PROTOTYPE:END -->`. Keep an
  HTML comment outside the markers noting that human edits outside the generated
  region are preserved. No external CSS/JS/CDN links.

### Task 4: blueprint skill
- **mode:** A
- **target:** plugin/skills/blueprint/SKILL.md
- **complexity:** hard
- **executor:** opus
- **parallel_group:** 3
- **est_tokens:** 2500
- **est_cost_usd:** 0.188
- **verifier:** test -f plugin/skills/blueprint/SKILL.md && grep -q "name: blueprint" plugin/skills/blueprint/SKILL.md
- **serves:** new
- **spec:**
  Author the `blueprint` skill, mirroring the structure/voice of
  `plugin/skills/prd/SKILL.md`. Frontmatter `name: blueprint` + a description in
  the same style as other skills. The skill orchestrates (it does NOT itself
  contain the splice algorithm — that lives in `renmark/blueprint.py`):
  - **Step 0 — Context check:** call `lifecycle.skill_preamble(repo, 'blueprint')`,
    surface any hint.
  - **Step 1 — Freshness gate:** read `.renmark/memory/project-map.md`. If missing
    or stale (compare its `Last refreshed @ <sha>` against current `git rev-parse HEAD`,
    same pattern dev-standards.md uses), HALT and route the user to `/renmark:init`.
    Never fabricate architecture. project-map.md is the ONLY architecture source —
    do not rescan the repo.
  - **Step 2 — UI gate:** read `.renmark/memory/stack.md`, use `renmark.blueprint.detect_ui`.
    `True` → confirm with a one-line override prompt; `False`/declined → schematic
    only; `None` → ask the user "does this build have a UI?".
  - **Step 3 — Synthesize:** the LLM produces a Container-granularity Mermaid
    `flowchart`/`graph` from project-map.md (NOT full 4-level C4), and — when UI —
    a self-contained HTML/CSS mockup body.
  - **Step 4 — Splice & write:** for each artifact, if the root file is absent,
    create it from `plugin/templates/{SCHEMATIC.md,PROTOTYPE.html}.template`; if it
    exists WITH markers, call `splice_generated_block(..., source_sha=<project-map.md hash>)`;
    if it exists WITHOUT markers, ABORT with a clear message (never clobber human
    content). Record the project-map.md hash as `source_sha`.
  - **Final step — Lifecycle:** `lifecycle.write_lifecycle(repo, artifact_update=('schematic', 'SCHEMATIC.md'))`
    and, when written, `('prototype', 'PROTOTYPE.html')`. Do NOT pass a `stage=` —
    blueprint is a touchpoint, not a lifecycle stage.
  Include a "Write-boundary guardrail" note (init vs blueprint) and a
  "Governance compliance" section like sibling skills. Bounded orchestrator output.

### Task 5: blueprint command
- **mode:** A
- **target:** plugin/commands/blueprint.md
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 2
- **est_tokens:** 300
- **est_cost_usd:** 0.001
- **verifier:** test -f plugin/commands/blueprint.md && grep -qi "blueprint/SKILL.md" plugin/commands/blueprint.md
- **serves:** new
- **spec:**
  Create the thin command entry `plugin/commands/blueprint.md`, structurally
  identical to `plugin/commands/prd.md` (read it first and mirror its
  frontmatter/body shape). It instructs the model to read
  `plugin/skills/blueprint/SKILL.md` and follow it, passing the user's input
  through. Match the existing command-file conventions exactly.

### Task 6: blueprint tests
- **mode:** A
- **target:** tests/test_blueprint.py
- **complexity:** medium
- **executor:** codex
- **parallel_group:** 3
- **est_tokens:** 1200
- **est_cost_usd:** 0.024
- **verifier:** pytest -q tests/test_blueprint.py
- **serves:** new
- **spec:**
  Pytest unit tests for `renmark.blueprint` (import as `from renmark import blueprint`).
  Cover: (1) `splice_generated_block` replaces only the marked span and
  byte-preserves surrounding human prose; (2) idempotency — splicing identical
  content twice yields identical output; (3) re-splicing after a manual edit to a
  human section preserves that edit; (4) markers absent → raises the documented
  exception (so callers can distinguish create-vs-abort); (5) `detect_ui` returns
  True for a non-none Frontend, False for `none`, None when Frontend/stack is
  absent; (6) the START marker records the supplied `source_sha`. Use the real
  marker format from `renmark/blueprint.py`. Follow existing test style in
  `tests/` (plain pytest functions, no new deps).

### Task 7: register blueprint domain
- **mode:** B
- **target:** renmark/lifecycle.py
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 1
- **est_tokens:** 150
- **est_cost_usd:** 0.001
- **verifier:** python3 -c "from renmark.lifecycle import DOMAIN_BY_SKILL; assert DOMAIN_BY_SKILL.get('blueprint')=='build'"
- **serves:** new
- **spec:**
  In `renmark/lifecycle.py`, add a single entry `"blueprint": "build",` to the
  `DOMAIN_BY_SKILL` dict (near the other `build`-domain skills, after `"prd": "build",`).
  Do NOT touch `STAGES` or `NEXT_BY_STAGE` — blueprint is a touchpoint, not a
  lifecycle stage. Change nothing else.

### Task 8: wire blueprint into start
- **mode:** B
- **target:** plugin/skills/start/SKILL.md
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 2
- **est_tokens:** 700
- **est_cost_usd:** 0.032
- **verifier:** grep -qi "blueprint" plugin/skills/start/SKILL.md
- **serves:** new
- **spec:**
  Read the existing PRD touchpoint at `plugin/skills/start/SKILL.md` §"5a. Offer
  PRD creation" and mirror its non-blocking, offer-once style. Add a step
  (after the PRD offer) that offers to generate the first blueprint via
  `/renmark:blueprint` during onboarding — one-line offer, skip silently if
  declined, never block or repeat. Keep the surrounding numbering coherent. Do not
  alter unrelated steps.

### Task 9: wire blueprint into feature
- **mode:** B
- **target:** plugin/skills/feature/SKILL.md
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 2
- **est_tokens:** 700
- **est_cost_usd:** 0.032
- **verifier:** grep -qi "blueprint" plugin/skills/feature/SKILL.md
- **serves:** new
- **spec:**
  Read the existing PRD-alignment touchpoint at `plugin/skills/feature/SKILL.md`
  §2 and mirror its placement. Add a step where the feature pipeline updates the
  living blueprint with the feature's delta via `/renmark:blueprint` (a
  non-blocking touchpoint — it reconciles SCHEMATIC.md/PROTOTYPE.html, does not
  gate the build). Make clear blueprint is a touchpoint, not a new lifecycle
  stage, and that it never fabricates architecture (routes to `/renmark:init` if
  project-map is stale). Do not alter unrelated steps.

### Task 10: list blueprint in help
- **mode:** B
- **target:** plugin/skills/help/SKILL.md
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 2
- **est_tokens:** 200
- **est_cost_usd:** 0.001
- **verifier:** grep -qi "blueprint" plugin/skills/help/SKILL.md
- **serves:** new
- **spec:**
  In `plugin/skills/help/SKILL.md`, add a `/renmark:blueprint` entry to the
  command list, in the same two-line format as the adjacent `/renmark:prd` entry
  (command on one line, one-sentence description indented below): "Generate the
  project's living schematic (always) and UI prototype (when there's a UI)."
  Place it logically near prd. Change nothing else.

### Task 11: document blueprint in CLAUDE.md
- **mode:** B
- **target:** CLAUDE.md
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 2
- **est_tokens:** 300
- **est_cost_usd:** 0.001
- **verifier:** grep -q "renmark:blueprint" CLAUDE.md
- **serves:** new
- **spec:**
  In the project `CLAUDE.md`, add a row to the "Tooling — renmark workflow" table
  for `/renmark:blueprint` with the when-to-use: "Generate/refresh the living
  schematic (+ prototype when there's a UI)". Place it near the `/renmark:prd`
  row. This change MUST be mirrored identically in `AGENTS.md` (Task 12). Change
  nothing else.

### Task 12: document blueprint in AGENTS.md
- **mode:** B
- **target:** AGENTS.md
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 2
- **est_tokens:** 300
- **est_cost_usd:** 0.001
- **verifier:** grep -q "renmark:blueprint" AGENTS.md
- **serves:** new
- **spec:**
  Mirror Task 11 exactly in `AGENTS.md`: add the same `/renmark:blueprint` row to
  the renmark workflow / tooling table, identical wording, same placement relative
  to `/renmark:prd`. CLAUDE.md and AGENTS.md must stay in sync. Change nothing else.

---

## Cost preview

| Wave | Tasks | Executors |
|---|---|---|
| group 1 | T1 blueprint.py, T2 schematic tpl, T3 prototype tpl, T7 lifecycle | sonnet×1, haiku×3 |
| group 2 | T5 command, T8 start, T9 feature, T10 help, T11 CLAUDE, T12 AGENTS | sonnet×2, haiku×4 |
| group 3 | T4 skill (opus), T6 tests (codex) | opus×1, codex×1 |

| Executor | Tasks | Est. spend (incl. ~10k overhead/Claude task) |
|---|---|---|
| haiku | 7 | ~$0.0072 |
| sonnet | 3 | ~$0.098 |
| opus | 1 | ~$0.188 |
| codex | 1 | ~$0.024 (subprocess, no overhead) |

**Total: ~121k tokens · ~$0.32**

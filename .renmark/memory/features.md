# Features

Running log. Newest at top within each section. Updated by `/renmark:orchestrate` when tasks pass.

## Shipped





### 2026-06-08 — next-step-engine: guided next-step contract + roadmap gap discovery

**Files:** `plugin/skills/_shared/next-steps.md`, `renmark/lifecycle.py`, `renmark/lint.py`, `plugin/skills/*/SKILL.md (16 refit)`, `tests/test_next_steps.py`, `tests/test_lint_next_steps.py`
**Spec:** `.renmark/specs/2026-06-08-next-step-engine.spec.md`
**Plan:** `.renmark/plans/2026-06-08-next-step-engine-part1.plan.md (+part2)`
**Commits:** `10c6166..b477009`

Shared _shared/next-steps.md hand-off contract + lifecycle.next_steps() state helper; all 19 skills now cite it (lint-enforced). roadmap gains PRD-vs-shipped gap discovery (T0/T1/T2, web research opt-in, ADR-009); finish/init route into it. 24 new tests.

---

### 2026-06-05 — PRD source of truth + /renmark:prd

**Files:** `plugin/skills/prd/SKILL.md`, `plugin/skills/_shared/prd-alignment.md`, `plugin/commands/prd.md`, `plugin/templates/PRD.md.template`, `renmark/lifecycle.py`
**Spec:** `.renmark/specs/2026-06-05-prd-source-of-truth.spec.md`
**Plan:** `.renmark/plans/2026-06-05-prd-source-of-truth.plan.md`

Per-project root PRD.md as durable source of truth; /renmark:prd create/update skill (human-gated); start/feature wiring; subagent-based PRD drift check (orchestrator never reads PRD body); plan traceability note; plain-text (never @import) pointers in CLAUDE.md/AGENTS.md + templates.

---

### 2026-06-04 — QA flow memory + QA bootstrap

**Files:** `.renmark/memory/qa-flows.md`, `plugin/skills/verify/SKILL.md`, `.renmark/memory/INDEX.md`, `plugin/skills/orchestrate/SKILL.md`, `tests/test_qa_flows.py`
**Plan:** `.renmark/plans/2026-06-04-qa-flow-memory.plan.md`
**Commits:** `851bb7a..1202fba`

Markdown QA playbook store (qa-flows.md); verify reads/promotes flows + --qa --bootstrap; orchestrate recommends browser QA (not auto). 5 tasks / 5 commits / shell-smoke default preserved.

---

### 2026-06-04 — verify browser QA refinement

**Files:** `plugin/skills/verify/SKILL.md`
**Plan:** `.renmark/plans/2026-06-04-verify-browser-qa.plan.md`
**Commits:** `a142ada`

--qa/--deep-qa: when-to-use guide, visual/layout integrity (overlap/clip/off-screen), before/after UI-change tracking, stop-on-break logging. Default shell smoke + opt-in preserved.

---

(Each entry is one feature, with date and files touched. Auto-appended.)

### YYYY-MM-DD — (example) Add /healthz endpoint

**Files:** `src/server.py`, `tests/test_healthz.py`
**Spec:** `.renmark/specs/YYYY-MM-DD-healthz.spec.md`
**Plan:** `.renmark/plans/YYYY-MM-DD-healthz.plan.md`
**Commits:** `<sha>..<sha>`

Returns server status and version. Used by load balancers and uptime monitoring.

---

## In progress


### 2026-06-05 — blueprint (/renmark:blueprint)

**Spec:** `.renmark/specs/2026-06-05-blueprint.spec.md`
**Plan:** `.renmark/plans/2026-06-05-blueprint.plan.md`
**Commits:** `8a1ddc7..HEAD on feature/blueprint`

Living SCHEMATIC.md (always) + PROTOTYPE.html (UI builds) synthesized from project-map.md via hybrid marker-based update; standalone + start/feature touchpoints.

---

(Features the current plan is mid-execution on. Cleared on completion.)

(Empty.)

---

## Planned

(Backlog. Hand-edited or written by `/renmark:brainstorm` when scoping future work.)

### init-as-front-door pipeline + setup consolidation (decided 2026-06-08 — Option A)

**Problem:** `/renmark:init` hard-errors (`init.py:1295`, exit 1) when `CLAUDE.md` is
absent — it requires a pre-existing CLAUDE.md and only refreshes the map. Users
(matching Claude Code's native `/init`) expect it to *initialize* the project.
`/renmark:setup` is the actual bootstrapper, so the two-door onboarding is confusing
and overlaps (both touch CLAUDE.md/AGENTS.md/.renmark/ + stack detection).

**Decision (Option A):** make `/renmark:init` the single front-door **pipeline**:
1. Detect project state (CLAUDE.md/AGENTS.md/CHANGELOG.md/.renmark/, git, stack)
2. Scaffold-if-missing (create CLAUDE.md/AGENTS.md/CHANGELOG.md/.renmark/ from templates + merge rule blocks) — setup's bootstrap, folded in
3. Scan & map (symbols → project-map.md; merge project-stub block)
4. Standards (dev-standards.md + health gaps)
5. **Roadmap gap discovery as the final step** (`/renmark:roadmap --gaps`; nudge `/renmark:prd` if no PRD) — added per user 2026-06-08
6. Hand off

`/renmark:setup` folds into init (or becomes a thin "refresh rule blocks" alias).
Scaffold logic lives in ONE place. **Build via `/renmark:feature` after a `/clear`.**

### acceptance criteria in the PRD (decided 2026-06-08 — ADD)

PRD has Requirements + Success metrics but no per-REQ testable acceptance criteria.
**Decision:** add OPTIONAL per-REQ "done when…" acceptance criteria under each
`REQ-n` — a `PRD.md.template` change + `/renmark:prd` skill update (CREATE asks for
them, UPDATE can add them). Product-level outcome criteria, not task-level (verify's
goal-backward smoke can lean on them). Build via `/renmark:prd` / `/renmark:feature`.

### modularity / scalability health lens (decided 2026-06-08 — BUILD advisory)

Renmark enforces modularity at plan-time (one-file-per-task, no mode C) but never
MEASURES it on the shipped codebase — no file-size/coupling/god-object health gap.
**Decision:** build an ADVISORY modularity health lens — add oversized-file /
coupling "gaps" to `init`'s standards-health (and/or `/renmark:hygiene`), surfaced
like the existing advisory health gaps (never blocking). Build via `/renmark:feature`.

### Sequencing (decided 2026-06-08)

`/clear` first (long session), then build in order: **(1) init/setup front-door
pipeline** → (2) acceptance-criteria-in-PRD → (3) modularity health lens. Each via
`/renmark:feature` (or `/renmark:prd` for #2's template part).

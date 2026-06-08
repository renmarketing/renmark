# Features

Running log. Newest at top within each section. Updated by `/renmark:orchestrate` when tasks pass.

## Shipped







### 2026-06-08 — acceptance-criteria: optional per-REQ done-when criteria in the PRD

**Files:** `plugin/templates/PRD.md.template`, `plugin/skills/prd/SKILL.md`
**Plan:** `.renmark/plans/2026-06-08-acceptance-criteria.plan.md`
**Commits:** `07f48f0..3010f96`

PRD template + /renmark:prd now support optional product-level acceptance criteria ("done when…" bullets) per REQ-n; CREATE asks (skippable), UPDATE edits via diff, human-gated. Altitude note: not task verifiers, not verify --coverage (ADR-005).

---

### 2026-06-08 — init-pipeline: /renmark:init as front-door adoption pipeline

**Files:** `renmark/init.py`, `renmark/lint.py`, `plugin/skills/init/SKILL.md`, `plugin/skills/setup/SKILL.md`, `tests/test_init_pipeline.py`
**Spec:** `.renmark/specs/2026-06-08-init-pipeline.spec.md`
**Plan:** `.renmark/plans/2026-06-08-init-pipeline.plan.md`
**Commits:** `e42b81b..87d03cc`

init now scaffolds when CLAUDE.md is absent (bootstrap + CHANGELOG) instead of exit-1; new deterministic merge_rule_blocks() back-fills missing BEGIN/END rule blocks byte-verbatim (shared iter_rule_blocks helper in lint.py). init SKILL redefined as 6-step pipeline ending in roadmap gap discovery; setup is now a thin alias. 9 new tests.

---

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

*(init-as-front-door pipeline + setup consolidation — SHIPPED 2026-06-08, see Shipped section above.)*

*(acceptance criteria in the PRD — SHIPPED 2026-06-08 as v0.7.3, see Shipped above.)*

### pipeline cost efficiency — C+A (IN PROGRESS, feature/proportional-pipeline)

A 2-task feature cost ~340k tokens (~40% a 120–130k codex codereview paid once per
feature regardless of size). **Building now (C+A):** proportional codereview
(auto-skip/downgrade codex on tiny/doc diffs; opt-in always) + size-tier lite-lane
(tiny features bypass heavy stages). Makes cost ∝ risk/size, automatic, low-risk.

### roadmap-as-pipeline / batch execution — B (DEFERRED, next after C+A)

Queue N planned/gap items → ONE plan→orchestrate→verify→codereview→finish run,
amortizing fixed overhead. ~60% off for backlogs. Deferred (situational; reduces
per-feature isolation; bigger build). Natural home for the modularity lens below.

### modularity / scalability health lens (decided 2026-06-08 — BUILD advisory)

Renmark enforces modularity at plan-time (one-file-per-task, no mode C) but never
MEASURES it on the shipped codebase — no file-size/coupling/god-object health gap.
**Decision:** build an ADVISORY modularity health lens — add oversized-file /
coupling "gaps" to `init`'s standards-health (and/or `/renmark:hygiene`), surfaced
like the existing advisory health gaps (never blocking). Build via `/renmark:feature`.

### Sequencing (decided 2026-06-08)

Build order: ~~(1) init/setup front-door pipeline~~ ✅ SHIPPED 2026-06-08 →
**(2) acceptance-criteria-in-PRD** (next) → (3) modularity health lens. Each via
`/renmark:feature` (or `/renmark:prd` for #2's template part).

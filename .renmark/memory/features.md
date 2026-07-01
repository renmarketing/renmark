# Features

Running log. Newest at top within each section. Updated by `/renmark:orchestrate` when tasks pass.

## Shipped

### 2026-07-01 — harness-operating-modes: Conductor/Orchestrator mode selection (MVP)

**Files:** `renmark/mode.py`, `renmark/lifecycle.py`, `renmark/cli/_engine.py`, `CLAUDE.md`, `AGENTS.md`, `plugin/skills/help/SKILL.md`
**Spec:** `.renmark/specs/2026-07-01-harness-operating-modes.spec.md`
**Plan:** `.renmark/plans/2026-07-01-harness-operating-modes.plan.md`

Persisted operating mode (ask-once, smart default, --set-mode override); skill_preamble emits mode directive/choose-prompt; help + rule-block harness framing. Dynamic skill loading deferred.

---

### 2026-06-09 — reporting-and-usage-analytics: local usage reporting and analytics layer

**Files:** `renmark/analytics.py`, `renmark/reports.py`, `plugin/skills/usage/SKILL.md`, `plugin/skills/analytics/SKILL.md`, `plugin/commands/usage.md`, `plugin/commands/analytics.md`
**ADR:** ADR-022
**Commits:** (feature/reporting-and-usage-analytics → merged main)

Local-only reporting/analytics: on-disk JSON/JSONL under `.renmark/reports/` and `.renmark/analytics/`; `/renmark:usage` rolling 5hr/weekly observed usage; `/renmark:analytics` model/executor/verification outcome trends. No external telemetry. Python aggregates raw logs into bounded summaries (REQ-5). Usage-aware pause/resume for loops/orchestrate (REQ-16).

---

### 2026-06-09 — release-version-snapshot: release tagging + zip snapshot

**Files:** `tools/release.sh`, `plugin/skills/finish/SKILL.md`, `.renmark/version/`
**ADR:** ADR-020 / ADR-021 (v0.7.8 release)
**Commits:** (feature/release-version-snapshot → merged main)

Version snapshot tooling: `tools/release.sh` tags + builds zip; `/renmark:finish` routes to it at `ready-to-release`; snapshot in `.renmark/version/<tag>/`. Tagged v0.7.8 dogfood copy.

---

### 2026-06-09 — backlog-driven-loop-execution: backlog → Loop Mode bridge

**Files:** `renmark/backlog.py`, `plugin/skills/backlog/SKILL.md`, `plugin/commands/backlog.md`, `tests/test_backlog.py`
**ADR:** ADR-018 / ADR-019 (v0.7.7 release)
**Commits:** (feature/backlog-driven-loop-execution → merged main)

`/renmark:backlog` interactive intake (list → detail → Approve and build); bridges approval buffer to bounded Loop Mode on a managed feature branch (max 5 iter, human merge gate, no orphan branches). Item state in `.renmark/state/`. Satisfies REQ-13.

---

### 2026-06-05 — blueprint (/renmark:blueprint): living schematic + prototype

**Files:** `renmark/blueprint.py`, `plugin/skills/blueprint/SKILL.md`, `plugin/commands/blueprint.md`, `tests/test_blueprint.py`
**Spec:** `.renmark/specs/2026-06-05-blueprint.spec.md`
**Plan:** `.renmark/plans/2026-06-05-blueprint.plan.md`
**ADR:** ADR-008
**Commits:** `8a1ddc7..bb09cad` (feature/blueprint → merged main)

Living SCHEMATIC.md (always) + PROTOTYPE.html (UI builds) synthesized from project-map.md via hybrid marker-based update; standalone + start/feature touchpoints. codereview caught 4 Majors (detect_ui, inline regex, splice guard, SKILL.md contradiction) — all fixed.

---







### 2026-06-09 — loop-mode (MVP): bounded resumable agentic loop

**Files:** `renmark/state/usage.py`, `renmark/loop.py`, `tests/test_loop.py`, `plugin/skills/loop/SKILL.md`, `plugin/commands/loop.md`, `plugin/skills/resume/SKILL.md`, `plugin/skills/start/SKILL.md`
**Spec:** `.renmark/specs/2026-06-09-loop-mode.spec.md`
**Plan:** `.renmark/plans/2026-06-09-loop-mode.plan.md`
**Commits:** `e711d15..a13fb5d`

Loop Mode MVP: renmark/loop.py state machine (loop.json under .renmark/loops/<id>/, budget [tokens|$], build_decision from verify metadata + ledger, stop conditions) + state.usage_by_run_id. /renmark:loop skill (single upfront gate, autonomous orchestrate→verify→decide loop, commit-per-iteration, gate at finish/REQ-12); /renmark:start vibe-coder wiring; /renmark:resume recovers loop state. 34 tests. Defaults: max-iter 5, budget 300k tokens.

---

### 2026-06-08 — modularity-health-lens: advisory ast code-health gaps

**Files:** `renmark/modularity.py`, `renmark/init.py`, `tests/test_modularity.py`, `plugin/skills/init/SKILL.md`
**Spec:** `.renmark/specs/2026-06-08-modularity-health-lens.spec.md`
**Plan:** `.renmark/plans/2026-06-08-modularity-health-lens.plan.md`
**Commits:** `f830f8a..cd274fc`

New renmark/modularity.py: pure-ast, zero-dep, never-raise analyzer — 5 metrics (module LOC, fn length, cyclomatic branch count, import fan-out, nesting-weighted cognitive complexity), two bands, FP suppression (tests/generated/__init__). Merged into init standards-health (HEALTH line stays a bounded summary; dev-standards.md gets a capped Modularity subsection). Advisory/never-blocking. 21 new tests. (renmark self-scan: 111 gaps — 20 major/91 warn.)

---

### 2026-06-08 — proportional-pipeline: pipeline cost proportional to feature size/risk

**Files:** `renmark/sizing.py`, `tests/test_sizing.py`, `plugin/skills/feature/SKILL.md`, `plugin/skills/codereview/SKILL.md`
**Spec:** `.renmark/specs/2026-06-08-proportional-pipeline.spec.md`
**Plan:** `.renmark/plans/2026-06-08-proportional-pipeline.plan.md`
**Commits:** `451e869..e41bf1d`

New deterministic sizing.classify_plan/classify_diff → lite|standard|full. Feature router adds a size-tier lite lane (tiny features land on main, skip codex/release, keep verify+plan-validate); --lite/--full overrides. codereview is proportional: lite/doc diff → cheap built-in /review default + one-key codex escalate (never silent skip), --full/--skip flags. verify+plan-validation always run (REQ-7). 10 new tests.

---

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

### 2026-06-29 — p7-skill-consistency-lint

**Files:** `renmark/skillmeta.py`, `renmark/skillgen.py`, `renmark/init.py`, `tools/precommit.sh`
**Spec:** `.renmark/specs/2026-06-29-p7-skill-templates.spec.md`
**Plan:** `.renmark/plans/2026-06-29-p7-skill-templates.plan.md`

Pivoted from template-generation to a consistency lint: skillmeta registry + skillgen --check (frontmatter discipline + doc-slimming guard) wired into precommit. Generation/migration dropped (doc-slimming already single-sourced everything).

---

### 2026-06-26 — p10-headless-contract

**Files:** `renmark/config.py`, `renmark/lifecycle.py`, `plugin/skills/_shared/headless-contract.md`, `renmark/cli/_engine.py`
**Spec:** `.renmark/specs/2026-06-26-p10-headless-contract.spec.md`
**Plan:** `.renmark/plans/2026-06-26-p10-headless-contract.plan.md`

Formal headless/spawned-session contract: layered detection (config.is_headless), shared doctrine, safe-gate auto-pick vs dangerous-gate halt (lifecycle.halt_for_human_review), --set-headless CLI flag.

---

(Features the current plan is mid-execution on. Cleared on completion.)

---

## Planned

(Backlog. Hand-edited or written by `/renmark:brainstorm` when scoping future work.)

*(init-as-front-door pipeline + setup consolidation — SHIPPED 2026-06-08, see Shipped section above.)*

*(acceptance criteria in the PRD — SHIPPED 2026-06-08 as v0.7.3, see Shipped above.)*

*(pipeline cost efficiency C+A / proportional-pipeline — SHIPPED 2026-06-08, see Shipped above.)*

*(Loop Mode MVP — SHIPPED 2026-06-09, see Shipped section above.)*

### roadmap-as-pipeline / batch execution — B (DEFERRED, the last remaining item)

Queue N planned/gap items → ONE plan→orchestrate→verify→codereview→finish run,
amortizing fixed overhead. ~60% off for backlogs. Deferred (situational; reduces
per-feature isolation; bigger build). NOTE: Loop Mode (shipped) is the per-feature
iterate-until-verified engine; B is the cross-feature batch amortizer — distinct.

*(modularity / scalability health lens — SHIPPED 2026-06-08, see Shipped section above.)*

### Sequencing (decided 2026-06-08)

Build order: ~~(1) init/setup front-door pipeline~~ ✅ v0.7.2 →
~~(2) acceptance-criteria-in-PRD~~ ✅ v0.7.3 →
~~(3) proportional-pipeline (C+A)~~ ✅ v0.7.4 →
~~(5) modularity health lens~~ ✅ v0.7.5 (this session). **Remaining backlog:**
only **(4) roadmap-batch (B)** — one pipeline run over N items. Via `/renmark:feature`.

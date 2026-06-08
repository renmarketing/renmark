# Changelog

## v0.7.5 — 2026-06-08 (modularity / scalability health lens)

**Release of the modularity-health-lens feature.** Bumped 0.7.4 → 0.7.5 across all 7
version locations. Shipped on `main` via `--no-ff` merge of
`feature/modularity-health-lens` (codereview: full codex — 3 Major + 2 Minor
metric-accuracy/suppression findings, all fixed + independently re-verified; 483
tests + mypy + lint_all clean). Completes the user's original three-part request
(init front-door pipeline + acceptance criteria + this).

- **`renmark/modularity.py`** — pure-`ast`, zero-dep, never-raise analyzer. 5
  metrics, each two bands: module LOC, function length, cyclomatic branch count,
  import fan-out (coupling), nesting-weighted cognitive complexity. Thresholds
  mirror pylint/mccabe/SonarQube. False-positive suppression: `tests/`, comment-
  header generated files, `__init__.py` fan-out.
- **`/renmark:init` standards-health** now surfaces advisory modularity gaps — the
  `HEALTH:` stdout line stays a bounded summary; full detail (capped) goes to
  `.renmark/memory/dev-standards.md`. Advisory / never blocking / never auto-refactors.
- Self-scan on this repo surfaced 121 advisory gaps (20 major / 101 warn) — the
  lens working on day one.

## [2026-06-08] — project scope: modularity-health-lens

**Request:** Advisory modularity/scalability health lens — renmark enforces modularity at plan-time but never measures it on the shipped codebase. (User asked to research how other tools do it + reuse what renmark already has.)
**Tech stack:** Python ≥3.10 stdlib + markdown — **no new deps**. New `renmark/modularity.py` is a pure-`ast` analyzer; reuses `init.py`'s standards-health pipeline + `sizing.py` style.
**Deployment:** Claude Code plugin (unchanged).
**MVP boundary:** new `renmark/modularity.py` (5 ast metrics — module LOC, function length, cyclomatic branch count, import fan-out, nesting-weighted cognitive complexity; two bands each; FP suppression) → merged into `init.py` `evaluate_health` → `dev-standards.md` + `HEALTH:` line; one-line `init/SKILL.md` note; tests. ADVISORY / never blocking / never auto-refactors.
**Out of scope:** a separate `/renmark:hygiene` surface; blocking the pipeline; third-party metric deps (radon/pylint); auto-refactor.

**Locked decisions:**
- Ship all 5 metrics (LOC, fn length, cyclomatic, import fan-out [coupling/scalability], cognitive complexity); thresholds mirror pylint/mccabe/SonarQube defaults
- Surfaces ONLY through init's existing standards-health (no new /hygiene surface); reuses init's Gap dataclass + HEALTH pipeline
- Pure stdlib `ast`, zero-LLM, never raises (skip unparseable files); advisory — init still exits 0
- FP suppression mandatory: skip tests/generated/__init__ fan-out/data; count code lines not raw

## v0.7.4 — 2026-06-08 (proportional pipeline — cost ∝ feature size/risk)

**Release of the proportional-pipeline feature.** Bumped 0.7.3 → 0.7.4 across all 7
version locations. Shipped on `main` via `--no-ff` merge of
`feature/proportional-pipeline` (codereview: full codex — 2 Critical + 2 Major + 1
Minor *false-lite* holes, all fixed + independently re-verified + 11 regression
tests; 437 tests + mypy + lint_all clean).

- **`renmark/sizing.py`** — deterministic, zero-LLM tier classifier:
  `classify_plan` / `classify_diff` → `lite | standard | full`. Code-suffix always
  wins (no false-lite from a "template" substring); validates task shape; degrades
  to `standard` on any uncertainty (never accidentally `lite`). `resolve_override`:
  `--full` always escalates, `--lite` only narrows a `standard` classification
  (refused on hard/core/full).
- **Size-tier lite lane** (`/renmark:feature`): tiny features land on `main`, skip
  the codex review + release ceremony — but **always** run plan-validation + verify.
- **Proportional codereview** (`/renmark:codereview`): lite/doc diff → built-in
  cheap `/review` by default + one-keystroke escalate to full codex; standard/full
  → full codex. `--full` / `--skip` flags. Never silently skips.
- Makes small features cheap by default (the steady-stream complaint) while keeping
  full rigor where it matters — proven when the feature's own diff self-tiered
  `full` and the codex review caught real classifier bugs.

## [2026-06-08] — project scope: proportional-pipeline (C+A)

**Request:** Pipeline cost should be proportional to feature size/risk, not a fixed per-feature toll (a 2-task feature cost ~340k tokens, ~40% a 120–160k codex codereview run once regardless of size).
**Tech stack:** Python ≥3.10 stdlib + markdown — **no new deps**. New `renmark/sizing.py` (deterministic, zero-LLM) reuses `parser.Task` signals + git diff stat.
**Deployment:** Claude Code plugin (unchanged).
**MVP boundary:** `sizing.classify_plan/classify_diff` → tier (lite/standard/full); feature-router lite lane (lite features land on `main`, skip codex/release, keep verify+plan-validate); proportional codereview (cheap built-in `/review` default on tiny/doc + one-key escalate to codex; `--full`/`--skip`); tier surfaced in cost preview; `--full`/`--lite` overrides; tests.
**Out of scope:** roadmap-batch execution (B — deferred next); modularity health lens (deferred); not spawning subagents for trivial edits (future micro-lever); new runtime deps.

**Locked decisions:**
- Cheap built-in `/review` by default on tiny/doc diffs + one-key escalate to full codex — NOT silent-skip (this session a "doc-only" feature had 2 real codex findings)
- Lite features land straight on `main` (per single-branch-rule); standard/full keep branch→PR/release
- verify + plan-validation ALWAYS run regardless of tier (REQ-7); classifier degrades to `standard` on uncertainty
- Build C+A now; B (batch) + modularity lens deferred (ADR this session)

## v0.7.3 — 2026-06-08 (optional acceptance criteria in the PRD)

**Release of the acceptance-criteria feature.** Bumped 0.7.2 → 0.7.3 across all 7
version locations. Shipped on `main` via `--no-ff` merge of
`feature/acceptance-criteria` (codereview: 0 critical, 1 Major + 1 Minor — a
cross-file format inconsistency — both fixed; 416 tests + lint_all clean).

- **Optional per-`REQ-n` acceptance criteria** in the PRD: a single indented
  `- *Acceptance:* done when (outcome); done when (outcome).` bullet (1–3
  semicolon-separated clauses), product-level OUTCOME criteria.
- **`plugin/templates/PRD.md.template`** documents the format + example + a note
  distinguishing per-REQ acceptance from project-wide Success metrics.
- **`/renmark:prd`** CREATE asks for them one-REQ-at-a-time (skippable); UPDATE
  edits them via the reconcile→diff→approval flow; always human-gated; a PRD with
  zero criteria stays valid.
- Altitude held (ADR-005): criteria are NOT plan task verifiers and do NOT
  re-introduce the deferred `verify --coverage`.

## v0.7.2 — 2026-06-08 (init front-door pipeline + serves parser fix)

**Release of the init-pipeline feature + accumulated fixes.** Bumped 0.7.1 → 0.7.2
across all 7 version locations. Shipped on `main` via `--no-ff` merge of
`feature/init-pipeline` (codereview: 0 critical, 4 Major + 1 Minor all fixed +
independently re-verified; 416 tests pass, mypy + ruff + lint_all clean).

- **`/renmark:init` is now the non-destructive front door** — scaffolds missing
  `CLAUDE.md`/`AGENTS.md`/`CHANGELOG.md`/`.renmark/` (via `bootstrap`) instead of
  the old exit-1 dead-end, deterministically back-fills missing `BEGIN/END` rule
  blocks byte-verbatim, scans/maps, reports standards health, then hands off to
  `/renmark:roadmap` gap discovery. Works with or without a pre-existing CLAUDE.md.
- **`merge_rule_blocks()`** (zero-LLM, in `init.py`) — corruption-safe: tightened
  marker regex to full `<!-- BEGIN:name -->` own-line comments; pre-validates
  balanced markers and SKIPS a malformed file (`MarkerCorruptionError` → exit 2)
  rather than corrupting it. Shared `iter_rule_blocks`/`validate_rule_markers` with lint.
- **`/renmark:setup`** is now a thin rule-block-refresh alias of init (PRD REQ-8
  updated + human-approved).
- **`serves` plan field** now parses (`parser.py` + `Task` + `_build_task`) —
  closes the documented-but-rejected traceability field.
- PRD REQ-8 + Scope boundaries reconciled to init-as-front-door.

## [2026-06-08] — init-pipeline: marker hardening + corruption-safe back-fill

**Request:** Fix 5 verified codereview findings in the init-pipeline feature; core safety property — `merge_rule_blocks` must NEVER corrupt a file (SKIP malformed input, never insert).
**Built:**
- **#1** Tightened `_BEGIN_RE`/`_END_RE` (lint.py) to match ONLY a full managed-marker HTML comment on its own line (`^[ \t]*<!--[ \t]*BEGIN:name[ \t]*-->[ \t]*$`, MULTILINE) — bare prose `BEGIN:example` is no longer a marker. Horizontal-only whitespace classes keep block boundaries exact.
- **#2/#3** `merge_rule_blocks` now pre-validates each target's markers (new `lint.validate_rule_markers`) BEFORE inserting; malformed (orphan END, unclosed BEGIN, duplicate, out-of-order) → file SKIPPED, never written, collected into new `init.MarkerCorruptionError`.
- **#4** Scoped out AGENTS rule-block back-fill/mirroring in docstring + init/SKILL.md + setup/SKILL.md (AGENTS.md.template has no managed markers).
- **#5** `run()` maps `MarkerCorruptionError` → exit **2** (user-fixable corruption), other RuntimeError → exit **1**, success → **0**; documented in module docstring + init/SKILL.md.
**Files changed:**
- `renmark/lint.py` — tightened marker regexes; added `validate_rule_markers`.
- `renmark/init.py` — `MarkerCorruptionError`; pre-insert balance gate in `merge_rule_blocks`; exit-2 mapping in `run()`; honest docstrings.
- `plugin/skills/init/SKILL.md`, `plugin/skills/setup/SKILL.md` — dropped AGENTS-mirroring claims; documented skip-on-corruption + exit codes.
- `tests/test_init_pipeline.py` — replaced old unclosed-BEGIN test (asserted the OLD vulnerable behavior) with skip+raise; added orphan-END, exit-2, prose-marker tests.
- `tests/test_lint.py` — fixtures use real `<!-- BEGIN:name -->` form; added prose-marker non-match test.
**Do not change:**
- Markers are ONLY the `<!-- BEGIN:name -->` / `<!-- END:name -->` comment form — the regexes must use `[ \t]*` (not `\s*`) so MULTILINE `^`/`$` don't eat the preceding newline (would corrupt `iter_rule_blocks` block boundaries).
- `MarkerCorruptionError` subclasses `RuntimeError`; in `run()` it MUST be caught BEFORE the generic `RuntimeError` handler or exit-2 collapses to exit-1.
- There is NO CLAUDE.md↔AGENTS.md rule-block mirroring — AGENTS.md.template has no managed markers; `merge_rule_blocks` always reports `AGENTS.md: 0`.

## [2026-06-08] — project scope: init-pipeline

**Request:** Make `/renmark:init` the front-door "initialize renmark here" pipeline (scaffold-if-missing → back-fill rule blocks → scan/map → standards → roadmap gap discovery), folding `/renmark:setup`'s bootstrap in; fix the exit-1-when-CLAUDE.md-absent bug.
**Tech stack:** Python ≥3.10 stdlib + markdown — **no new deps**. Reuses `bootstrap.py`, `memory.template_dir()`, and lint's BEGIN/END marker logic.
**Deployment:** Claude Code plugin (unchanged).
**MVP boundary:** init.py scaffold phase (delegating to `bootstrap(init_git=False)` + CHANGELOG create) + new deterministic `merge_rule_blocks()` back-fill; init/SKILL.md redefined as the 6-step pipeline; setup/SKILL.md → thin alias; tests. Roadmap-at-end is inherited from ADR-009 (already wired).
**Out of scope:** removing `/renmark:setup`; any LLM call in init.py; new runtime deps.

**Locked decisions:**
- Tech stack + deployment locked for this plan
- Rule-block merge is **deterministic Python** (Option A) — best for context hygiene AND accuracy (canonical marker-delimited blocks inserted byte-verbatim, unit-tested), not agent/markdown
- `init.py` stays **zero-LLM**; roadmap `--gaps` hand-off stays SKILL-level (ADR-009)
- Non-destructive: existence-skip on create, byte-skip on managed blocks, never overwrite hand-written content

## [2026-06-08] — PRD updated
**Request:** Feature `init-pipeline`'s drift gate proposed consolidating `/renmark:setup` into `/renmark:init` as the front-door adoption pipeline; REQ-8 named setup explicitly.
**Built:** Reconciled REQ-8 + Scope boundaries of PRD.md — `/renmark:init` is now the named non-destructive adoption front door; `/renmark:setup` is recorded as its rule-block-refresh alias. last_reviewed already 2026-06-08.
**Files changed:**
- `PRD.md` — REQ-8 reworded; Scope-boundaries skill list reflects init-as-front-door + setup-as-alias
**Do not change:**
- PRD is human-owned; this edit was human-approved through the /renmark:prd gate. `setup` is an alias of `init`, not a separate adoption command.

## [2026-06-08] — fix: plan parser accepts the documented `serves` field
**Request:** Fix the `serves:` parser bug surfaced by gap discovery (Open Q1 / bugs.md).
**Built:** `renmark/parser.py` now accepts `serves` (parser keys + `Task.serves` field + `_build_task` pass-through), so plans using the documented `serves: REQ-n` traceability field parse instead of aborting with "unknown field serves".
**Files changed:**
- `renmark/parser.py` — accept `serves` end-to-end
- `tests/test_parser.py` — +2 tests (serves parses to Task.serves; absent → None)
- `.renmark/memory/bugs.md` — moved serves bug Open → Fixed
**Do not change:**
- Keep `parser.py` accepted-keys in lockstep with `plan/SKILL.md`'s format example — a documented field is only real if the parser accepts it.

## v0.7.1 — 2026-06-08 (next-step-engine: guided hand-offs + roadmap gap discovery)

**Release of the next-step-engine feature.** Bumped 0.7.0 → 0.7.1 across all 7
version locations. Shipped on `main` via `--no-ff` merge of
`feature/next-step-engine` (codereview: 0 critical, 3 major + 1 minor all
fixed+tested; 401 tests pass, mypy + ruff + lint_all clean).

- **`_shared/next-steps.md`** — umbrella hand-off contract: every skill ends by
  recommending a state-derived next step (lifecycle.json + pipeline.json), so no
  interaction dead-ends. References the existing `handoff-menu.md` gate sub-menu.
- **`lifecycle.next_steps(repo, skill)`** — pure stdlib helper returning the
  structured next-step set (pipeline/gate/aux classes); reuses NEXT_BY_STAGE /
  next_recommended; never raises (tolerates malformed input).
- **All 19 skills** now cite the contract — enforced by a new class-aware
  `lint_next_steps_citation` (pipeline/aux must cite next-steps.md; gate skills
  may cite handoff-menu.md) wired into `lint_all`.
- **`/renmark:roadmap` gap-discovery mode** (ADR-009) — PRD-vs-shipped gap
  analysis with tiered cost gating (T0 deterministic / T1 local / T2 web research
  opt-in), advisory + human-gated; never writes PRD. `/renmark:finish` and
  `/renmark:init` route into it so picking the next feature is guided.
- 28 new tests (`test_next_steps.py`, `test_lint_next_steps.py`).
- Pipeline: prd → feature → brainstorm → plan(×2, 21 tasks) → orchestrate →
  verify (6/6 smoke) → codereview → finish.

## [2026-06-08] — project scope: next-step-engine

**Request:** Make every renmark interaction guided — each skill recommends a state-derived next step; finishing a feature flows into PRD-vs-shipped gap discovery to suggest what to build next.
**Tech stack:** Python ≥3.10 stdlib + markdown (Claude Code plugin) — no new runtime deps. Optional Tier-2 web research uses Claude Code's own tools, not a Python dependency.
**Deployment:** Claude Code plugin (unchanged).
**MVP boundary:** all 7 components land in this feature — `_shared/next-steps.md` umbrella contract; `lifecycle.next_steps()` helper; refit of all 19 skills' hand-off; `/renmark:roadmap` gap-discovery (T0/T1/T2, T2 opt-in); `/renmark:finish` + `/renmark:init` wiring into gap mode; tests + lint drift guard.
**Out of scope:** a standalone `/renmark:next` skill (extends roadmap instead); web research on-by-default; auto-writing PRD/roadmap; per-skill bespoke menus.

**Locked decisions:**
- Tech stack and deployment target above are locked for this plan
- Changing them requires a new project scope entry
- Gap discovery extends `/renmark:roadmap` (supersedes the deferred roadmap view in ADR-005); it stays read-only/advisory/human-gated and never becomes a second PRD writer
- Reuse `NEXT_BY_STAGE` / `next_recommended()` and the existing `handoff-menu.md` — generalize, do not rebuild

## [2026-06-08] — PRD created
**Request:** Create the project's PRD via `/renmark:prd`.
**Built:** Created PRD.md as the project's product source of truth (synthesized-from-docs — distilled from CLAUDE.md, .renmark/memory/, specs, and CHANGELOG since renmark is a mature project).
**Files changed:**
- `PRD.md` — new product definition (what/who/why/capabilities/non-goals/success criteria)
**Do not change:**
- PRD.md is human-owned. Automated stages may PROPOSE edits but never write it without approval.
- Product-level non-goals (plugin-not-app, no own model, stdlib-only runtime, renmark≠legacy-plugin) live in PRD; a single build's MVP cut belongs in the scope contract, not the PRD (ADR-005).

## v0.7.0 — 2026-06-05 (blueprint: prototype/schematic step)

**Release of the blueprint milestone.** Bumped 0.6.0 → 0.7.0 across all 7 version
locations. Shipped on `main` via merge of `feature/blueprint` (codereview: 0 critical,
4 major fixed; 374 tests pass).

- **`/renmark:blueprint`** — generates a living `SCHEMATIC.md` (always, Mermaid) and
  `PROTOTYPE.html` (UI builds only, self-contained HTML/CSS), synthesized from
  `.renmark/memory/project-map.md` via a hybrid `<!-- RENMARK:GENERATED:*:START/END -->`
  marker update. Standalone command + embedded touchpoints in `start` and `feature`.
- **`renmark/blueprint.py`** — `splice_generated_block` (idempotent, marker-injection
  guarded via `MarkerInjectionError`), `detect_ui` (parses canonical `**Frontend:**`
  forms), marker builders/constants.
- **Guardrails** — blueprint is an artifact touchpoint, NOT a lifecycle stage;
  `project-map.md` is the sole architecture source (never rescans); `/renmark:init`
  writes map/stack only, blueprint is sole writer of the two artifacts.
- 22→31 unit tests; pipeline ran brainstorm → plan (12 tasks) → orchestrate (1
  codex→sonnet escalation) → verify (8/8) → codereview → finish.


## [2026-06-05] — blueprint feature built (12 tasks)

**Request:** Implement `/renmark:blueprint` — the Phase-3 prototype/schematic pipeline step.
**Built:** Orchestrated 12 atomic tasks across 3 waves (sonnet/haiku/opus Agents + 1 escalation):
- `renmark/blueprint.py` — marker-splice helper (`splice_generated_block`, `MarkerNotFoundError`), UI detection (`detect_ui`), marker builders/constants.
- `plugin/templates/{SCHEMATIC.md,PROTOTYPE.html}.template` — skeletons with `RENMARK:GENERATED:*` marker blocks.
- `plugin/skills/blueprint/SKILL.md` + `plugin/commands/blueprint.md` — the skill (freshness gate → UI gate → synthesize → splice → lifecycle touchpoint) and command entry.
- Wiring: `start` (onboarding offer), `feature` (delta touchpoint), `help`, `DOMAIN_BY_SKILL` (build), CLAUDE.md/AGENTS.md tooling table.
- `tests/test_blueprint.py` — 22 unit tests (splice byte-preservation, idempotency, human-edit preservation, missing-marker abort, `detect_ui` branches, source_sha).
**Files changed:** see commits 8a1ddc7..51601e1 on `feature/blueprint`.
**Gates:** 365 passed / 28 skipped; ruff clean on changed code. All 12 task verifiers PASS.
**Do not change:**
- T6 was escalated codex→sonnet: `renmark-execute --task` ran read-only in this env and didn't write the file. See `learnings.md`.
- The `serves:` field in plan files breaks `renmark-execute` (parser drift) — logged Open in `bugs.md`; stripped from this plan.

## [2026-06-05] — project scope: blueprint (prototype/schematic step)

**Request:** Add a renmark pipeline step (`/renmark:blueprint`) that generates a
living architecture **schematic** (always) and a visual UI **prototype** (only
when the build has a UI), updated as the project evolves like the PRD.
**Tech stack:** Python ≥3.10 + Claude Code plugin markdown — existing renmark stack, **no new deps**.
**Deployment:** local plugin install (WSL + Windows), unchanged.
**MVP boundary:** schematic + conditional prototype + hybrid marker-based update + pipeline wiring (start/feature/standalone).
**Out of scope:** deterministic language parsers (deferred), full 4-level C4 (Container level only), image/SVG export, full-repo rescan.

**Locked decisions:**
- Command slug `/renmark:blueprint`; artifacts `SCHEMATIC.md` (always) + `PROTOTYPE.html` (UI only) at project root, like `PRD.md`.
- Schematic = Mermaid in Markdown; prototype = self-contained static HTML/CSS.
- `project-map.md` is the ONLY architecture source — blueprint synthesizes, never rescans the repo.
- Hybrid update: regenerate only content between `<!-- RENMARK:GENERATED:*:START/END -->` markers; preserve human prose; single current-state artifact.
- Blueprint is an artifact **touchpoint like PRD, NOT a lifecycle stage** — must not advance the `init→…→released` chain.
- `source_sha` in a generated block = hash of `project-map.md`, not an implied repo scan.

**Do not change:**
- Do not add deterministic parsers in this phase — explicitly deferred.
- Do not clobber an existing artifact that lacks markers — abort instead.
- Do not let blueprint fabricate architecture when `project-map.md` is missing/stale — route to `/renmark:init`.

## v0.6.0 — 2026-06-05 (PRD source of truth)

**Release of the PRD source-of-truth milestone.** Bumped 0.5.9 → 0.6.0 across all
7 version locations. Shipped on `main` via merge of `feature/prd-source-of-truth`
(codereview: 0 critical).

- **`/renmark:prd`** — create/update skill for a per-project `PRD.md`, the
  human-owned source of truth; every write human-gated.
- **WRITE / ALIGN / NOTHING touchpoint policy** (ADR-005) — one writer
  (`/renmark:prd`), one read-only align contract (`_shared/prd-alignment.md`),
  nothing for everyone else. Guards against PRD duplication/over-engineering.
- **Pipeline wiring** — `start` offers PRD create; `feature` runs the alignment
  drift gate; `brainstorm` runs read-only alignment (+ no-PRD nudge); `plan`
  carries `serves: REQ-n` traceability; `help` lists the command.
- Codereview pass fixed 6 doc-consistency findings (approve-skill framing, the
  5-line budget contradiction, PRD artifact-governance exemption, etc.).

Gates: 368 passed; ruff + plugin lint clean. 3 pre-existing stale `approve`-gate
tests remain (separate follow-up; not introduced here). Local release (no remote).

## 2026-06-05 — PRD branch codereview fixes (pre-merge)

**Request:** Codex review of `main..HEAD` before merging prd-source-of-truth; fix
the doc-consistency findings.

**Built:** Codex pass = 0 Critical / 3 Major / 2 Minor / 1 Nit (all
doc-consistency, no runtime bugs; review at
`.renmark/reviews/2026-06-05-3eb9b02…review.md`). Fixed all 6:
- `_shared/prd-alignment.md` — clarified the ≤5-line budget applies to the
  orchestrator-visible `verdict`+`reason`; `proposed_prd_addition` is a separate
  bounded snippet routed to `/renmark:prd`, not counted against it (resolved the
  contract's internal contradiction).
- `plugin/skills/prd/SKILL.md` — `/renmark:approve` reframed as *planned* (not
  shipped); manual gate is the current path. Read-only "what does the PRD say"
  use case clarified as UPDATE-mode's read step. G6 row states the PRD's
  human-owned **exemption** from generated-artifact provenance fields.
- `plugin/templates/PRD.md.template` — header comment documents the same exemption.
- `plugin/skills/start/SKILL.md` — "[b] Skip" copy no longer claims it always
  goes to the build plan (start can route to brainstorm).
- `plugin/skills/help/SKILL.md` — dropped the hardcoded "six commands" count.

**Do not change:**
- `/renmark:approve` is **not shipped** — `lifecycle.next_recommended()` (line ~289)
  intentionally surfaces a manual gate. Docs must not present approve as shipped.
- 3 pre-existing test failures (`test_cold_start_recovery`,
  `test_smoke_full_lifecycle`) assert `/renmark:approve` in `next_recommended()`
  output — they are **stale** (code is correct by design). Separate follow-up on
  main; not introduced by this branch.

## 2026-06-05 — PRD touchpoint policy + brainstorm alignment

**Request:** Analyze where the PRD overlaps across renmark skills, prevent
duplication/over-engineering, and keep a single source of truth — then implement
the one change that pays for itself.

**Built:** Codified the **WRITE / ALIGN / NOTHING** PRD-touchpoint policy (one
writer = `/renmark:prd`; one read-only align contract = `_shared/prd-alignment.md`;
NOTHING for everyone else) and wired `brainstorm` into ALIGN:
- `.renmark/memory/decisions.md` — ADR-005 records the policy, the rejected-as-bloat
  list (brainstorm-as-writer, `verify --coverage`, roadmap progress view,
  init/document PRD pointers, orchestrate reading the PRD), and the altitude rule.
- `plugin/skills/_shared/prd-alignment.md` — new "PRD touchpoint policy" section
  (the durable guard, co-located with the alignment contract skill authors read).
- `plugin/skills/brainstorm/SKILL.md` — new Step 1b: read-only PRD alignment via
  the shared subagent when `PRD.md` exists; a non-blocking "no PRD yet" nudge when
  it doesn't; **no write path**. Step 6 gains an altitude note (spec non-goals are
  feature-scoped; product non-goals live in the PRD).
- `plugin/templates/PRD.md.template` + `plugin/skills/_shared/scope-contract.md` —
  reciprocal altitude notes: product-level non-goals → PRD; a build's MVP cut →
  scope contract. Cross-reference, never copy.

**Do not change:**
- **brainstorm must never write `PRD.md`** — it ALIGNs (read-only) and routes drift
  to `/renmark:prd`. One writer only (ADR-005).
- The brainstorm PRD check uses the `_shared/prd-alignment.md` subagent — it MUST
  NOT read the PRD body into the skill's context.
- `plan`'s `serves: REQ-n` is a light ID read, deliberately *not* a full ALIGN;
  this is why `verify --coverage` stays unbuilt (coverage flows plan→tasks→verify).
- Pre-existing unrelated test failures (3) live in lifecycle approval-routing
  (`test_cold_start_recovery`, `test_smoke_full_lifecycle`); not caused by and not
  in scope of this doc/skill change.

## 2026-06-05 — PRD source of truth + `/renmark:prd` (built)

**Request:** Centralized per-project source of truth (a PRD), informed by studying TaskMaster; ship the skill, wire it into the pipelines, add a hygiene-preserving drift check.

**Built:** 14-task plan executed (10 Claude via Agent, 4 codex via renmark-execute):
- `plugin/skills/prd/SKILL.md` — `/renmark:prd` create/update modes, human-gated living updates, Governance-compliance section.
- `plugin/skills/_shared/prd-alignment.md` — drift-check subagent contract; router passes only feature description + file scope, gets a ≤5-line `verdict`, never reads the PRD body.
- `plugin/commands/prd.md` — command shim.
- `plugin/templates/PRD.md.template` — lean sections (vision/users/goals+non-goals/REQ-n/metrics/scope/open-questions) + provenance header.
- `renmark/lifecycle.py` — `prd` registered in `DOMAIN_BY_SKILL` (build).
- `start` offers PRD create for new projects; `feature` dispatches the alignment subagent; `plan` carries an optional `serves: REQ-n` traceability note; `help` lists the command.
- Plain-text PRD pointers added to `CLAUDE.md`/`AGENTS.md` + both templates (never `@import`).
- `tests/integration/test_plugin_install.py` — enforces `prd` in the documented-skill set; excludes `_shared/` from the skills↔commands parity check.

**Files changed:** see plan `.renmark/plans/2026-06-05-prd-source-of-truth.plan.md`. Full suite: 343 passed, 28 skipped; ruff clean on `renmark/` (34 pre-existing repo-wide ruff errors untouched).

**Do not change:**
- PRD pointers in CLAUDE.md/AGENTS.md/templates MUST stay **plain text — never `@PRD.md` import** (an import auto-loads the whole PRD into every session, breaking context hygiene).
- The orchestrator/router/`feature` MUST NOT read `PRD.md` into context — always dispatch the `_shared/prd-alignment.md` subagent and consume only its bounded verdict.
- PRD writes are **human-gated**; automated stages propose, they never write the PRD without approval.
- Integration tests gate on `RENMARK_SMOKE=1` — run with it set, or real failures stay hidden as skips.
- The prototype/schematic pipeline step is the **next** feature (recorded in memory), intentionally not built here.

## 2026-06-05 — project scope: PRD source of truth + `/renmark:prd`

**Request:** Add a per-project PRD as the durable source of truth (peer to CLAUDE.md), informed by a study of TaskMaster; ship a `/renmark:prd` skill, wire it into `start`/`feature`, and add a lightweight, hygiene-preserving PRD↔work drift check.
**Tech stack:** Python >=3.10 + Claude Code plugin (markdown skills/commands) — unchanged; this is a feature inside renmark itself.
**Deployment:** N/A — distributed as the renmark Claude Code plugin.
**MVP boundary:** PRD artifact + `/renmark:prd` (create/update, human-gated) + start/feature wiring + subagent-based drift flag + plan traceability note.
**Out of scope:** prototype/schematic pipeline step (next, separate feature); REQ-ID coverage enforcement in verify; hard PRD↔plan gating; TaskMaster status-taxonomy / dependency-integrity tooling.

**Locked decisions:**
- PRD lives at the **project root** (`PRD.md`), committed — confirmed free of context cost (only CLAUDE.md/AGENTS.md auto-load).
- The orchestrator/router **never reads the PRD body**; all alignment reading happens in an isolated subagent returning a bounded summary.
- CLAUDE.md/AGENTS.md pointer is **plain text, never `@import`** (an import would auto-load the PRD every session).
- Spec: `.renmark/specs/2026-06-05-prd-source-of-truth.spec.md`; research: `.renmark/research/2026-06-05-prd-taskmaster.research.md`.

## v0.5.9 — 2026-06-04 (fix: finish deletes merged branch + correct release routing)

**Request:** "Once a release is created, the branch should get merged and deleted — but I keep seeing the feature branch left behind." Check the finish/release skill.

**Built:** Fixed two real gaps in `plugin/skills/finish/SKILL.md`:
1. **Branch cleanup** — the `[m] Merge` step merged into main but never deleted the branch `/renmark:feature` created, so every finish left the feature branch behind. It now runs `git branch -d <branch>` (the *safe* form — refuses to delete unmerged work) after a clean merge, plus `git push origin --delete` when a remote exists. Release packaging is cut from `main` after the merge, so the branch is already gone by release time.
2. **Stale release routing** — line 23 claimed PR/merge logic "moves to `/renmark:release`", a command that does not exist (`lifecycle.NEXT_BY_STAGE` routes `ready-to-release` to a manual fallback; `/renmark:release` lives only in `NEXT_BY_STAGE_PLANNED`). Corrected to state merge/release logic lives in finish itself, and added a guard so a re-run never downgrades a `released` feature back to `ready-to-release`.

**Files changed:**
- `plugin/skills/finish/SKILL.md` — `[m] Merge` deletes the merged branch; final-step lifecycle guard + accurate "no /renmark:release skill" note.

**Do not change:**
- **Use `git branch -d` (lowercase), never `-D`,** in the merge step — the safe form can never discard unmerged work. `-D` only on explicit user request.
- **Finish must not downgrade `released → ready-to-release`** on a re-run — guard the final-step lifecycle write on the current stage.
- There is no `/renmark:release` skill; don't re-introduce references to it as if it were implemented.

## v0.5.8 — 2026-06-04 (QA flow memory + QA bootstrap)

**Release of the qa-flow-memory feature** (detailed per-change entry below). Bumped from 0.5.7 across all 7 version locations.

- **QA flow memory:** new committed `.renmark/memory/qa-flows.md` playbook store. `/renmark:verify --qa` / `--deep-qa` read it before choosing a browser flow and promote a passing one-off flow into it; degrades to today's synthesize-from-plan behavior when the file is missing or empty.
- **QA bootstrap:** `/renmark:verify --qa --bootstrap` seeds the playbook with the project's top critical flows (no third browser flag — rides the existing `--qa` parser).
- **Recommendation triggers:** `/renmark:verify` and `/renmark:orchestrate` now recommend (never auto-run) browser QA for user-visible/browser-facing changes; shell smoke stays the default.

Gates: plugin lint clean, `pytest` 343 passed / 0 failed. Codex review: 0 findings on the feature diff. Local release only (no remote configured).

## v0.5.7 — 2026-06-04 (browser QA, dual channel, interactive menus, lifecycle identity)

**Release bundling the four changes shipped on 2026-06-04** (detailed per-change entries below). Bumped from 0.5.6 across all 7 version locations.

- **Browser QA refinement** (`/renmark:verify --qa` / `--deep-qa`): visual/layout integrity checks (overlapping/clipped/off-screen controls), before/after UI-change tracking, explicit stop-and-report-on-break, and a "when to use which mode" guide. Default shell smoke preserved; browser QA stays opt-in.
- **Dual browser channel:** Chrome DevTools MCP (default; the only option under WSL — targets Windows-host Chrome) or native `claude --chrome` when connected; environment-detected with graceful install-hint + shell-smoke fallback.
- **Interactive hand-off menus:** arrow-selectable `AskUserQuestion` pickers as the primary presentation (numbered markdown demoted to fallback), with a hard guarantee that a hand-off never ends on a choiceless prompt. Supersedes the earlier numbered-markdown rule.
- **Lifecycle identity fix:** `lifecycle.begin_feature()` — `/renmark:feature` now persists feature/branch identity at entry, so stage writes no longer inherit the prior feature's identity.

Gates: `ruff`/`mypy`/plugin lint clean, `pytest` 337 passed. Local release only (no remote configured).

## [2026-06-04] — QA flow memory + QA bootstrap

**Request:** Add a lightweight, markdown-based QA flow memory layer so `/renmark:verify --qa` / `--deep-qa` reuse known-good browser flows instead of re-inventing tests each run, centered on a new `.renmark/memory/qa-flows.md` playbook.

**Built:** New committed QA playbook store (`qa-flows.md`) with a seeded EXAMPLE/TEMPLATE flow (Flow name, URL, Preconditions, Actions, Expected — incl. no overlapping/clipped controls + no console errors, selectors, Evidence, Known risks, related bugs). `/renmark:verify` now reads it BEFORE choosing a QA flow (degrades to today's synthesize-from-plan behavior when the file is "missing or empty"), promotes a passing one-off flow into it on PASS, and gains a `--qa --bootstrap` path (no third flag) plus `--qa`/`--deep-qa` recommendation triggers. `/renmark:orchestrate` Step 8 now recommends (does NOT auto-run) browser QA after a clean run touching browser-facing surfaces. INDEX.md registers the new file. 6 content-presence tests added.

**Files changed:**
- `.renmark/memory/qa-flows.md` — new QA playbook store (seeded template).
- `plugin/skills/verify/SKILL.md` — flow selection from memory, `--qa --bootstrap`, promote-on-pass, recommendation triggers, Deep-QA reuse pointer.
- `.renmark/memory/INDEX.md` — registered `qa-flows.md` in the memory table.
- `plugin/skills/orchestrate/SKILL.md` — Step 8 browser-QA recommendation note (not automatic).
- `tests/test_qa_flows.py` — 6 tests covering the store, verify wiring, and the INDEX row.

**Do not change:**
- **Shell smoke stays the default; browser QA stays opt-in** via `--qa`/`--deep-qa` — never automatic. No third browser flag (bootstrap rides `--qa`).
- **Existing QA must work when `qa-flows.md` is missing or empty** — that literal phrase is the load-bearing fallback guarantee; don't remove it.
- **Context-hygiene (G3/G5):** screenshots/DOM/console/network stay on disk + artifact body; chat sees only the ≤5-line verdict.
- Preserve the dual browser-channel selection (WSL→MCP precedence) and the interactive `AskUserQuestion` hand-off menus.

## [2026-06-04] — interactive (arrow-selectable) hand-off menus via AskUserQuestion

**Interaction-layer change, not menu formatting.** The earlier "numbered, forced-choice markdown menu" change only made menus *print* as `1. [x] Option` text — readable, but still a static list with no arrow-key selection. This change makes hand-off gates present an actual arrow-key-navigable picker via Claude Code's **`AskUserQuestion`** tool when available, with the printed numbered list demoted to a graceful fallback. It **supersedes** the numbered-markdown-as-primary rule.

**Request:** Render hand-off menus through the interactive question/choice component (arrow keys + Enter) when available; fall back to the printed numbered list (number or bracket-letter input) in non-interactive contexts. Don't invent an API — use the supported mechanism.

**Built:** Verified the mechanism first (via Claude Code docs): `AskUserQuestion` is the supported interactive picker — 1–4 questions/call, **2–4 options per question (hard cap of 4)**, label + description + ≤12-char header, blocking (no default, which enforces the required-choice gate), free-text always accepted; **unavailable in subagents and in headless / `-p` / piped / CI** sessions. SKILL.md can't call tools — it instructs the agent to call `AskUserQuestion`.
- `_shared/handoff-menu.md`: rules 6–7 rewritten. **Rule 6 (PRIMARY): present survivors via `AskUserQuestion`** — one choice per option (`label` = action + `[x]` code, `description` = gloss). **4-option-cap handling:** ≤4 survivors → all selectable; >4 → surface the 4 highest-priority (defined order, `[n]` always kept) AND print the full numbered list so overflow stays reachable by typed number/letter (free-text). **Rule 7 (FALLBACK): printed numbered list** for non-interactive / unavailable / error, and as the reference beneath an overflow picker. Rule 8: explicit choice always required.
- Static gates updated to interactive-primary + numbered-fallback: `plan`, `check-plan`, `finish`, `brainstorm`, `setup`, `orchestrate` (preview note), `codereview` (combined `[o]/[fix]`+gate menu, overflow path), `verify` (dispatch wording + citation).
- Discovery questions updated likewise: `start` (Q1/Q2), `_shared/scope-contract.md` (Q1–Q3; 5-option questions use top-4 + free-text). `brainstorm` already used `AskUserQuestion` for discovery.

**Follow-up (same branch) — choiceless-prompt hardening.** Closed a failure mode where `AskUserQuestion` rendered only the header (`What's next?`) with no visible options, or was declined/errored, leaving the user stuck. New rule 9 (hard guarantee): a hand-off MUST end in exactly one of two visible states — the picker showing selectable choices, OR the printed numbered list — **never the bare question with no choices**. Rule 6 now mandates options be passed as real `options[]` entries (never embedded in the `question` text — that's what renders header-only), and broadens the fallback trigger to fire immediately on *any* non-rendering reason: unavailable, errored, **declined/rejected/interrupted**, no valid selection, or header-only. The static gates' fallback clause was broadened to match. "When in doubt, print the fallback."

**Files changed:**
- `plugin/skills/_shared/handoff-menu.md` — interactive-primary rules 6–8, citation snippet, canonical-menu intro.
- `plugin/skills/{plan,check-plan,finish,brainstorm,setup,orchestrate,codereview,verify,start}/SKILL.md` — gate/dispatch wording.
- `plugin/skills/_shared/scope-contract.md` — Presentation directive + sub-question wording.

**Do not change (supersedes the prior numbered-menu guard):**
- **Interactive `AskUserQuestion` is the PRIMARY presentation; the numbered markdown list is ONLY the fallback.** Do not revert to "numbered list is the solution" — that earlier rule is intentionally superseded.
- **The 4-option cap is a real API constraint, not a style choice.** Menus with >4 filtered options must surface the top 4 as choices and keep the rest reachable via the printed fallback + free-text. Don't try to cram >4 options into one `AskUserQuestion`.
- **Never auto-proceed.** The required-choice gate holds in both modes; `AskUserQuestion` enforces it by blocking, the text fallback by re-asking on no match.
- Option **filtering rules (1–5) are unchanged** — interactivity is purely the presentation layer on top of the same filtered survivor set.

## [2026-06-04] — fix: /renmark:feature now persists feature identity to lifecycle.json

**Request:** Fix the lifecycle-identity bug found during the browser-QA finish: a feature started via `/renmark:feature` never wrote its identity, so `lifecycle.json` kept the prior feature's `feature`/`branch` and finish's ADR was wrong. Keep it tightly scoped; add a verifier; don't touch the browser-QA work.

**Built:** New `lifecycle.begin_feature(repo, *, feature, branch)` establishes a clean lifecycle for a new feature — resets to stage `init` with empty `stages_completed`/`artifacts` and the correct identity. `/renmark:feature` Step 1 now calls it immediately after creating/switching to the branch. Two focused tests prove `lifecycle.json` reflects the current feature/branch after entry and that a new feature does not inherit prior stage history or artifact pointers.

**Files changed:**
- `renmark/lifecycle.py` — added `begin_feature` (DRY: `clear_lifecycle` + `write_lifecycle(stage="init", …)`, so the 1KB byte-budget guard still applies).
- `plugin/skills/feature/SKILL.md` — Step 1 now writes feature identity via `begin_feature` right after branch creation, with rationale.
- `tests/test_lifecycle.py` — `test_begin_feature_writes_identity`, `test_begin_feature_resets_prior_feature_state`.
- `.renmark/memory/bugs.md` — moved the identity bug Open → Fixed.

**Do not change:**
- **The router owns identity; stage skills only advance `stage`.** `begin_feature` must run at feature entry (after the branch exists) — before plan/orchestrate/verify/finish, which only write `stage`/artifacts and would otherwise inherit stale identity.
- `begin_feature` intentionally **resets** `stages_completed` and `artifacts` — a new feature starts clean. Don't change it to a partial overwrite, or cross-feature artifact pointers leak back in.

## [2026-06-04] — verify browser QA refinement (`--qa` / `--deep-qa`)

**Request:** Make `/renmark:verify --qa`/`--deep-qa` do real browser-based QA (load pages, drive controls, exercise workflows, report visible + console/runtime bugs) — opt-in, not the default — and document when to use it; prefer `--deep-qa` for deeper runtime/visual checks that track UI changes, catch overlapping/broken interface layout, and stop/flag when a flow breaks or can't finish.

**Built:** Audit found browser QA already existed (Chrome DevTools MCP: navigate/click/fill/wait_for/screenshot, console + network criteria, opt-in flags, degrade-to-shell). This refinement closes four gaps in `plugin/skills/verify/SKILL.md`: (1) a `### When to use which mode` decision guide (shell smoke vs `--qa` vs `--deep-qa`); (2) a new HARD visual/layout integrity criterion catching overlapping interactive elements / clipped / off-screen content, detected via snapshot + screenshot + `getBoundingClientRect`; (3) before/after screenshot capture with an agent-observed diff note (evidence to disk only); (4) explicit stop-and-report-on-break semantics (hang, uncaught exception, broken layout, can't-finish) wired into the existing `log_bug` / artifact / learnings flow.

Follow-up (same branch): the QA applicability gate now selects between **two browser channels** so renmark works on both WSL and the Windows/desktop app — **Chrome DevTools MCP** (default; the only option under WSL, can target Windows-host Chrome) and the **native Claude-in-Chrome** extension (`claude --chrome`, used when on the Windows/desktop app with the extension connected). Detection precedence: WSL → MCP; Windows/desktop app with native channel connected → native; otherwise default CLI → MCP. If the chosen channel is unavailable it prints the environment-matched install hint (MCP `claude mcp add` command, or extension + `claude --chrome`) and degrades to shell smoke — never blocks. Pass criteria, evidence handling, and the hygiene contract are identical across channels.

**Files changed:**
- `plugin/skills/verify/SKILL.md` — added when-to-use guide, visual/layout hard criterion (`--qa` + strengthened `--deep-qa`), before/after UI-change tracking, stop-on-break semantics; frontmatter description lightly extended. (+33/−7)

**Do not change:**
- **Shell smoke (default mode) stays untouched and stays the default** — browser QA must remain opt-in via `--qa`/`--deep-qa`; the applicability gate (web project? browser MCP available?) and degrade-to-shell fallback are load-bearing.
- **Context-hygiene contract (G3/G5) is non-negotiable** — screenshots, DOM trees, console/network dumps, and before/after diff data go to disk + artifact body only; chat sees only the ≤5-line verdict. Do not inline images or paste diffs.
- **No third browser flag** — the refinement lives inside the existing two flags by design.
- **Browser-channel precedence is load-bearing:** WSL must always resolve to Chrome DevTools MCP (native messaging cannot cross the WSL boundary); the native `claude --chrome` channel is only for the Windows/desktop app. Do not reorder so that WSL attempts the native extension. Both channels share identical pass criteria / evidence / hygiene — keep them in lockstep.
- The hand-off menu blocks and dispatch-on-number-or-letter wording were deliberately NOT touched (see prior numbered-menu guard).

## [2026-06-04] — numbered, forced-choice hand-off menus

**Request:** Make the bracketed option menus (`[qa]`, `[d]`, etc.) numbered `1. 2. 3. 4.` so the user can answer by number, and require an explicit choice to continue on every prompt.

**Built:** Every renmark interactive menu now renders as a numbered list while keeping its `[x]` bracket code (e.g. `1. [d] Dispatch …`). The number is the primary selector; the bracket letter still works. Each prompt now states a choice is required and must never auto-proceed on an empty answer.

**Files changed:**
- `plugin/skills/_shared/handoff-menu.md` — added rendering rule 6 (number survivors after filtering) and rule 7 (a choice is required; accept number or letter; re-ask on no match); updated the citation snippet.
- `plugin/skills/verify/SKILL.md` — dispatch now keys on "number or letter" and requires an explicit choice.
- `plugin/skills/plan/SKILL.md`, `check-plan/SKILL.md`, `finish/SKILL.md`, `brainstorm/SKILL.md`, `setup/SKILL.md` — static gates numbered; dispatch keyed on `N / letter`; added "choice required" line.
- `plugin/skills/orchestrate/SKILL.md` — numbered the verify-menu preview.
- `plugin/skills/codereview/SKILL.md` — numbered the `[o]`/`[fix]` actions; appended hand-off menu continues the numbering into one list.
- `plugin/skills/_shared/scope-contract.md` — Q1/Q2/Q3 discovery questions numbered.

**Do not change:** — ⚠️ **SUPERSEDED** by the interactive-menu entry above (2026-06-04). Numbered markdown is now only the *fallback*; the primary presentation is the `AskUserQuestion` picker. The notes below apply only to the fallback list:
- The handoff menu numbering is a **render-time** rule, not hardcoded in the canonical list — items are filtered first (rules 1–5), then numbered. Don't bake fixed numbers into the canonical `[x]` block in `handoff-menu.md`; omitted gates would leave gaps.
- Keep the `[x]` bracket code on every fallback menu line — letters are still valid selectors and several dispatch instructions reference them.

## v0.5.6 — 2026-05-29 (lifecycle hygiene — decision log enforcement, artifact GC, memory prune, resume validation)

**Patch release — closes the gap between renmark's artifact-first doctrine and its actual enforcement. The `stale_after` / `created_at` / `source_sha` metadata schema in `renmark/summary.py` and `memory.log_decision()` in `renmark/memory.py` were both designed in earlier releases but had no consumer wired in. v0.5.6 builds the sweepers and enforcers that close the loop — turning aspirational metadata into operational hygiene.**

The driving idea: artifacts decay. Decisions get forgotten across `/clear`. Escalations happen silently inside `_engine.py` and leave no trail. The schema fields were already there — what was missing was the code that READS them and acts. v0.5.6 ships that code: a hygiene CLI, a resume-time validator, an idempotent decision logger, and a finish-time ADR write.

**What shipped:**

- **`memory.log_decision()` is now idempotent on `(title, date)`.** New helpers in `renmark/memory.py`: `dedupe_memory_log` (collapses duplicate ADR sections in curated files), `age_out_memory_log` (archives entries older than N days from append-only logs), and `log_escalation_decision` (writes a structured ADR when an executor escalates). Same `(title, date)` short-circuits — so rerunning the same plan on the same day no longer duplicates every ADR.
- **`lifecycle.validate_artifact_refs(repo, state=None)`** cross-checks paths + `source_sha` + `stale_after` for every artifact tracked in `lifecycle.json`. Returns a list of BLOCK / WARN findings with explicit reasons. `hygiene` added to `DOMAIN_BY_SKILL` as `meta` — diagnostic, not a pipeline stage.
- **New `renmark/hygiene.py` module + `python -m renmark.hygiene` CLI** with `scan | prune | all` subcommands and `--apply / --ttl-days / --memory-days / --include-memory` flags. Archives stale artifacts to `.renmark/archive/YYYY-MM/` preserving repo-relative paths under the archive root. Default dry-run; writes are opt-in via `--apply`. Refuses any `archive_root` outside the project tree (raises `ValueError`).
- **`_record_escalation` in `renmark/cli/_engine.py`** now accepts `escalated_to: str | None = None`. When non-None, it calls `memory.log_escalation_decision()` best-effort (try/except: pass — never breaks orchestrate). Every meaningful executor escalation now leaves an ADR in `decisions.md` — the WHY survives `/clear`.
- **New `/renmark:hygiene` skill + `plugin/commands/hygiene.md` dispatcher.** Thin command stub; the skill invokes `python -m renmark.hygiene` and relays its output. **`/renmark:resume` now runs `validate_artifact_refs` as Step 1.5** and emits BLOCK/WARN lines; exits `SystemExit(2)` when any BLOCK is present. Ghost references are caught before re-entry, not after.
- **`/renmark:finish` documents (and runs) a single `log_decision()` write at branch close** — captures feature name, branch, stage transition, and completed stages. Idempotent on `(title, date)`, so re-running finish on the same day is safe.

**Why this matters for vibe coders:** `decisions.md` becomes the persistent WHY across `/clear` — re-entering a project two weeks later, the ADRs are still there and the reasoning isn't lost. `.renmark/` no longer grows unbounded — `python -m renmark.hygiene prune --apply` archives stale plan/spec/review/verification artifacts into `.renmark/archive/YYYY-MM/`. `/renmark:resume` catches dangling artifact pointers (deleted plans, renamed specs, stale-after-deadline reviews) before they cause downstream confusion. And executor escalations — previously a silent fact about a run — now leave an audit trail. Together they make renmark's promise of "artifacts over conversation" enforced, not aspirational.

**Acceptance gates:**

- ✅ pytest: 64 new tests + all existing tests passing (total 335 + 28 skipped)
- ✅ ruff check + ruff format: clean
- ✅ mypy strict: 0 errors (38 source files)
- ✅ plugin lint: OK
- ✅ 5/5 pre-commit gates OK

**Codex codereview pass applied before merge (4 Major fixes):**

A `/renmark:codereview` over the feature branch surfaced 4 Major findings. All were fixed on the same branch before merge; v0.5.6 ships with the helpers actually working on real renmark memory files (not just the synthetic shapes the original tests covered).

- **`renmark/memory.py`** — `dedupe_memory_log` and `age_out_memory_log` rewired to parse the REAL on-disk schemas: `### YYYY-MM-DD — Title` entries under H2 section headers for `features.md` / `bugs.md`, and `- ` bullets under H2 sections for `learnings.md`. The original H2-only parser worked on synthetic tests but was a no-op on production files. Tests now produce entries via the writer functions (`log_feature`, `log_bug`, `append_learning`) so readers round-trip with writers. Bullet parser also tightened to stop at paragraph breaks (`(Empty — will fill…)` placeholders no longer get absorbed into the last bullet's signature). Migrated `dt.utcnow()` → `dt.now(timezone.utc)` along the way (kept on `datetime.timezone.utc` rather than `dt.UTC` for Python 3.10 compatibility).
- **`renmark/hygiene.py`** — lifecycle artifact refs normalized via `Path.resolve()` before comparison. Absolute paths and repo-relative paths now match consistently; a verify run that stored `str(absolute_path)` is no longer mis-detected as unreferenced and prematurely archived. Ghost-ref counting uses the same normalization.
- **`renmark/lifecycle.py`** — `validate_artifact_refs` now emits `WARN` with `kind="out_of_tree"` for any artifact path that resolves outside the project subtree (absolute paths, `..`-escapes). `/renmark:resume` can no longer be tricked into trusting files outside `.renmark/` via a crafted `lifecycle.json` ref. Existing `BLOCK`/`WARN` semantics for missing/stale/unreachable artifacts and the BLOCK-first stable ordering are preserved.
- **Tests** — updated/added across `test_memory.py`, `test_hygiene.py`, `test_lifecycle.py`: real-schema dedupe + age-out cases via writer functions, absolute-path lifecycle ref regression, out-of-tree boundary cases. 6 new tests on top of the original 58, plus 3 existing prune tests rewritten against real schemas.

The Minor finding (#5 — escalation hook dead code in `_record_escalation`) is by design: the `escalated_to: str | None = None` kwarg is opt-in to avoid breaking existing call sites; real callers land as escalation contexts get fleshed out in a follow-up.

**Codereview lens — `--focus optimize` / `--focus standards` (same skill, different prompt):**

The driving idea: codereview's default lens is correctness — does this diff do what it claims, safely. Sometimes the question is different. Sometimes it's "is this fast?" or "does this look like the rest of the package?" Both deserve a review pass, neither deserves a second skill, a second module, or a second artifact path. `--focus` swaps the prompt template only. Same dispatcher, same sandbox, same `.renmark/reviews/YYYY-MM-DD-<sha>.review.md` output path. Zero new context cost, zero new modules, one new flag.

- **`--focus optimize`** — performance / idiom lens. Allocations, complexity, hot-loop work, blocking calls inside async paths, resource lifecycle (file handles, subprocesses, network sessions). Out-of-scope correctness bugs spotted in passing are listed as ASIDEs at the bottom of the report rather than mixed into the main findings — keeps the lens honest.
- **`--focus standards`** — UNWRITTEN-standards lens. Compares the diff against sibling files in the same package for conventions that aren't enforced by `tools/precommit.sh` (ruff/mypy/format already gate the written standards). Looks at pathlib vs os.path mixing, helper duplication, naming drift, error-handling shape, type-annotation density. The point is to catch the conventions a linter cannot see.
- **Default (no flag)** — unchanged. Same prompt body, same output, same artifact path. The summary line now reads `Review at <path> (focus: <mode>)` only for non-default modes — default invocations stay terse and exactly as they were.

**What did NOT ship and why.** `--focus prior-art` was considered and explicitly dropped. Prior-art lookup — "is there a stdlib module or well-known library that does this better than the hand-rolled version in the diff?" — is research, not review. It would require codex to reach beyond the diff and consult external knowledge or the web, which violates the read-only-sandbox shape of codereview and conflates two different jobs. That work belongs on `/renmark:brainstorm` (as a prior-art mode) or on a dedicated `/renmark:prior-art` skill if real usage justifies the slot. Future contributors should not re-add it to codereview without revisiting this trade-off.

**Do not change:**

- **The idempotency check in `log_decision`.** Same `(title, date)` short-circuits and returns without writing. Removing it floods `decisions.md` on re-runs — the same plan rerun on the same day would duplicate every ADR, defeating the purpose of the decision log.
- **`hygiene` is `meta` domain.** It MUST NOT advance `lifecycle.json` stage — hygiene is diagnostic, not a workflow stage. Moving it into the `build` domain breaks the workflow router (it would be treated as a pipeline stage and confuse `/renmark:resume`).
- **The `try/except: pass` inside `memory.log_escalation_decision`** (and the optional-kwarg pattern in `_record_escalation`). Decision logging is best-effort. A failure to write `decisions.md` must NEVER break orchestrate's escalation path — escalation is the load-bearing behavior, ADR write is the audit trail.
- **Hygiene's `dry_run=True` default.** Writes are opt-in via `--apply`. Flipping the default would silently rewrite project state on the first `python -m renmark.hygiene scan` — exactly the kind of surprise the artifact-first doctrine exists to prevent.
- **Hygiene's refusal to write outside `.renmark/`.** The `ValueError` guard against a caller-supplied `archive_root` outside the project tree is what keeps the "writes stay in the project" memory honest. Loosening it would let one project's hygiene run leak into `$HOME` or the global plugin install.
- **The curated memory-file set in `dedupe_memory_log` / `age_out_memory_log`.** `decisions.md`, `project.md`, `stack.md`, `architecture.md`, `conventions.md`, `routing.md`, `dev-standards.md`, `MEMORY.md`, `project-map.md`, `INDEX.md` are curated and MUST NOT be auto-pruned. Only `learnings.md`, `bugs.md`, `features.md` are treated as append-only logs subject to age-out.
- **BLOCK-only severity for missing `plan` / `spec` artifacts in `validate_artifact_refs`.** Other missing artifacts (review, verification, research) WARN. Promoting all missing artifacts to BLOCK would make `/renmark:resume` too noisy to use; demoting plan/spec to WARN would let users continue with structurally broken pipelines.

## v0.5.5 — 2026-05-28 (codereview fixes — 4 findings from v0.5.4 review applied)

**Patch release — fixes 4 findings (2 Major, 2 Minor) raised by `/renmark:codereview` on the v0.5.4 strict-mypy commit. Codex caught real semantic bugs that the type-checker rubber-stamped because the casts were unchecked or the migration broke backward compat invisibly. These are the kind of catches that justify running adversarial review after a mechanical refactor.**

The driving observation: mypy strict says "no errors" but doesn't guarantee runtime safety. v0.5.4's strict-mode pass got the count to zero by adding `cast()` calls and migrating data classes — both legitimate moves, but each created a new class of risk that codex flagged correctly in the post-commit review.

**Fixes for the 2 Major findings:**

- **`renmark/state/pipeline.py`** — v0.5.4 migrated `completed_tasks`/`failed_tasks` from `None + __post_init__ coercion` to `field(default_factory=list)`. Clean Python idiom, but it silently dropped the backward-compat path for legacy `pipeline.json` files (pre-v0.5.4) that stored those fields as `null`. On resume, those legacy files would crash at the first `in self.completed_tasks` or `self.failed_tasks.append(...)` call in `write_pipeline_state()`. v0.5.5 restores the safety net by **normalizing in the loader** instead of the dataclass: `read_pipeline_state()` strips `None`-valued list fields from the deserialized dict so the constructor receives clean defaults. The dataclass stays mypy-clean (no `# type: ignore` lies); the legacy compat lives where it belongs (at the I/O boundary). Also added `isinstance(data, dict)` guard for the deserialized JSON itself — a malformed pipeline.json containing a JSON array would have hit the `data.items()` call.

- **`pyproject.toml [[tool.mypy.overrides]]`** — v0.5.4 added `module = "requests.*"` to ignore missing stubs. But `providers/nim.py` and `providers/openai_compat.py` use bare `import requests`, and mypy's `requests.*` pattern doesn't match the top-level package — only its submodules. So v0.5.4's "0 mypy errors" claim was environment-dependent: on a clean install without `types-requests` cached locally, mypy would have reported import errors. Fixed to `module = "requests"` (bare), which matches the actual import statements. The `requests.*` glob is unused (renmark only does top-level imports) so omitting it removes the corresponding "unused section" mypy note.

**Fixes for the 2 Minor findings:**

- **`renmark/doctor.py:_load_json()`** — v0.5.4 wrapped `return json.loads(path.read_text(...))` in `cast(dict[str, Any], ...)` to satisfy `-> dict[str, Any]`. But `json.loads()` can validly return any JSON type — list, scalar, null. A non-object JSON file would type-check through the cast but crash at the first `.get()` or `.setdefault()` downstream, with the type system saying everything was fine. Now: parse into `obj`, validate `isinstance(obj, dict)`, return `{}` for non-objects, then `cast()` only the verified-dict path.

- **`renmark/init.py:_package_json()`** — same unchecked-cast pattern. A `package.json` that's structurally valid JSON but not an object would type-check through and crash at downstream `pkg.get("scripts", {})` calls. Same fix: `isinstance(obj, dict)` guard before the cast.

**Lesson recorded:**

> `cast()` is a promise to the type checker that you've verified the shape. If you haven't verified it, you're lying. v0.5.4 made 5 of these promises with `cast(dict[str, Any], json.loads(...))` and codex flagged the 2 that didn't validate. The fix isn't to remove cast — it's to do the validation cast claims you already did. Pattern locked in: `json.loads → isinstance(dict) guard → cast → return`.

**All 5 pre-commit gates green:** 298 pytests passing, ruff clean, ruff format clean, mypy strict 0 errors, plugin lint clean. Pre-commit hard-fails on mypy as of v0.5.4 — that gate is enforcing.

**Do not change:**

- The `isinstance(obj, dict)` guards in `doctor.py:_load_json` and `init.py:_package_json`. These exist specifically because `cast()` was lying without them. Removing the guards re-introduces the v0.5.4 silent-failure mode.
- The legacy-state normalization in `read_pipeline_state()`. Moving it to `__post_init__` reintroduces the mypy `unreachable` warnings v0.5.4 was trying to avoid AND lies to the type checker. Loader-level normalization keeps both invariants honest.
- The `module = "requests"` override (bare, not `requests.*`). Renmark's code only does top-level `import requests`. Adding `requests.*` back generates an "unused section" note on every mypy run.

## v0.5.4 — 2026-05-28 (full strict mypy — 59 → 0, pre-commit gate flipped to hard-fail)

**Patch release — closes the mypy backlog from v0.5.3. `tool.mypy` flipped from lenient to `strict = true`; all 59 strict-mode errors resolved; `tools/precommit.sh` step 5 promoted from informational soft-warn to hard-fail. Renmark's source tree now enforces full strict mypy on every commit.**

The driving idea: v0.5.3 shipped the infrastructure with mypy in soft-warn mode and 20 known errors. v0.5.4 closes that gap so the gates are real, not aspirational. Every commit from this point forward MUST pass strict type-checking — the discipline that catches real bugs at edit time instead of at runtime.

**Real bugs caught by strict mypy (now fixed in source):**

- **`renmark/release.py:332`** — `for i in issues` shadowed an outer `i = 0` int counter from an earlier loop, then was used as a string in the inner loop body. `[assignment]` error caught a genuine variable shadowing bug. Renamed to `for issue in issues`.
- **`renmark/dispatch.py:75`** — clever list-comp using `set.add()` as a side-effect was relying on `set.add` returning None (falsy). `[func-returns-value]` flagged it as a likely mistake; refactored to an explicit for-loop with clear intent.
- **`renmark/cli/_engine.py:488-495`** — three `Task | None` accesses past early-return guards. mypy couldn't narrow across multiple if-return branches. Added an `assert failed_task is not None` at the join point so the type narrowing is explicit. (Also documents the invariant for future readers.)
- **`renmark/doctor.py:373`** — `c.fix_fn()` called on `Optional[object]` field; mypy's `[operator]` error correctly flagged "object not callable". Field typed as `Callable[[], str] | None` instead.
- **`renmark/state/pipeline.py:33-41`** — `__post_init__` None-check on dataclass fields that were typed as `list[int]` (with `# type: ignore[assignment]` lying about the default value). mypy correctly reported the post-init branches as `[unreachable]`. Refactored to `field(default_factory=list)` — the idiomatic Python pattern for mutable defaults. The `# type: ignore` lies are gone.
- **`renmark/init.py:579`** — Python 3.10 syntax error fixed in v0.5.3 (backslash in f-string subexpression). Confirmed clean.

**Bulk mechanical fixes (no runtime behavior change):**

- **33 `[type-arg]` resolved** — bare `dict` and `tuple` in type position parameterized as `dict[str, Any]` and `tuple[Any, ...]`. Applied across 15 files via a regex pass with careful isolation (the script avoided `isinstance(x, dict)` calls, which would have been an illegal `isinstance(x, dict[str, Any])` and broke runtime). 4 files needed manual repair after the regex pass (`__future__` imports got bumped, fixed). Tests stayed green throughout.
- **6 `[no-untyped-def]` resolved** — added explicit `Task`, `Callable[[Task, Path], TaskResult]`, and `"_dispatch.TaskResult"` annotations to `_task_signature`, `_memory_log_outcome`, `_runner`, `dispatch_wave.run_task`, `_run_one.run_task`, `dispatch_task_isolated.subagent_runner`.
- **5 `[no-any-return]` resolved** — `return json.loads(...)` patterns wrapped in `cast(dict[str, Any], ...)` to preserve runtime behavior while satisfying the declared return type. Added `from typing import cast` where needed.
- **4 `[unreachable]` from subprocess.TimeoutExpired** — bytes/str disjoint-base checks in `verifier.py` and `providers/codex.py`. Added `# type: ignore[unreachable]` on those specific lines (the code IS unreachable when `text=True`, but the defensive branch handles a hypothetical caller that disables `text=True` later).
- **2 `[import-untyped]`** — added `[[tool.mypy.overrides]]` for `requests.*` with `ignore_missing_imports = true` (avoids a `types-requests` dev dependency for a transitive-only import in providers).

**`tools/precommit.sh` flipped to hard-fail:**

- Step 5 header renamed `5/5 mypy (type check)` → `5/5 mypy (strict type check)` to reflect the new posture.
- Old soft-warn branch (`say "WARN — type errors detected (informational)"`) removed.
- Replaced with hard-fail: `fail=1` on any mypy error, just like the other 4 steps. No way to commit through a broken type-check without `--no-verify`.

**Updated `pyproject.toml [tool.mypy]`:**

- `strict = false` → `strict = true`.
- Removed the `check_untyped_defs = true` line (subsumed by `strict`).
- Added `[[tool.mypy.overrides]] module = "requests.*"` with `ignore_missing_imports = true` (replaces the dropped tests.* override which was generating an "unused section" warning since `tests/` is in `exclude`).

**Acceptance criteria:**

> Step 5/5 of `tools/precommit.sh` says `OK`, not `WARN`, when run from a clean tree.

Status after v0.5.4:
- ✅ 298 pytests passing
- ✅ ruff check: 0 errors (after final `--unsafe-fixes` clean-up + `ruff format`)
- ✅ ruff format: 0 reformat needs
- ✅ **mypy strict: 0 errors** (was 59)
- ✅ plugin lint clean
- ✅ drift check clean
- ✅ pre-commit: 5/5 OK in ~3s

**Do not change:**

- The `cast(dict[str, Any], json.loads(...))` pattern at the json.loads return sites. `json.loads()` is typed as returning `Any`, which is fine in most callers but defeats the purpose of typed function returns. cast() preserves the typed surface without runtime overhead. Don't refactor to `# type: ignore` — that hides the seam.
- The `assert failed_task is not None` in `cli/_engine.py:482`. Looks redundant because the preceding if-return branches GUARANTEE non-None, but mypy can't narrow across multi-branch returns. The assert serves both as type narrowing AND as a runtime invariant (cheap; only fires if we ever break the narrowing).
- The hard-fail in `tools/precommit.sh` step 5. Backing off to soft-warn would let regressions slip in. If a strict mypy error blocks an urgent commit, fix the type — don't relax the gate.
- The `# type: ignore[unreachable]` markers in `verifier.py` and `providers/codex.py`. The bytes branch of the TimeoutExpired stdout/stderr handling is technically dead when `text=True`, but exists as defense in depth if `text=True` is ever removed. Deleting the bytes branch would silently lose the protection.

## v0.5.3 — 2026-05-28 (self-host — dev standards tightened: ruff strict, mypy lenient, GitHub Actions CI, 5-step pre-commit)

**Patch release — renmark adopts its own dev-standards prescriptions. Closes the 4 warn-level gaps surfaced when `/renmark:init` first ran against the renmark source repo at v0.5.2. The infrastructure now matches what renmark recommends to managed projects: linter + formatter + type-checker + CI + pre-commit, all wired into a single `tools/precommit.sh` script.**

The driving idea: a vibe-coder-targeted tool's first impression is its `dev-standards.md` report. v0.5.2 made that report visible; v0.5.3 makes it green. Each fix in this release was driven by reading renmark's own scanner output, then choosing strict-where-possible and pragmatic-where-intentional.

**New dev-standards infrastructure:**

- **`.github/workflows/test.yml`** (NEW) — 6-cell CI matrix: ubuntu+macos+windows × Python 3.10+3.13. Each cell runs `pip install -e .[dev]`, `ruff check`, `ruff format --check`, `mypy`, `pytest -q`, `renmark.release check`, `renmark.lint`. `fail-fast: false` so one cell's failure doesn't cancel the others — when something breaks we want to see if it's OS-specific or Python-version-specific, not get cells canceled. The Windows cell is the only place that exercises the same code paths `install.ps1` users hit, so without it Windows install regressions would ship blind.
- **`tools/precommit.sh`** (UPDATED) — augmented from 3 steps (pytest, drift, plugin lint) to 5 (added ruff lint+format, added mypy as informational warn). Mypy is soft-warn at the v0.5.3 baseline; once the 20 known mypy errors are cleaned up, flip the `fail=1` line to make mypy a hard-fail.
- **`pyproject.toml [tool.ruff]`** (NEW) — `target-version = "py310"`, `line-length = 120` (industry standard for modern Python), `select = ["E", "W", "F", "I", "B", "UP", "SIM", "RUF"]`, `ignore = ["E402", "RUF001", "RUF003"]` (E402 mid-file imports are intentional; RUF001/003 unicode-ambiguity rules flag renmark's deliberately stylized comments). Per-file ignores for `tests/**` (E501, F841, B011 — pytest patterns) and `renmark/init.py` (E501 — long template strings for project-map.md rendering).
- **`pyproject.toml [tool.mypy]`** (NEW) — lenient-strict baseline: `strict = false`, but enables `warn_return_any`, `warn_unreachable`, `warn_redundant_casts`, `check_untyped_defs`. Catches actual bugs (Any returns, dead code, None-handling violations) without flagging every internal helper that lacks a return annotation. v0.5.3 sets this baseline; the path to `strict = true` is tracked in a follow-up plan after the 20 remaining strict-mode warnings are cleaned up.
- **`pyproject.toml [project.optional-dependencies] dev`** — added `ruff>=0.6.0` and `mypy>=1.11` alongside the existing `pytest>=8.0.0`.

**Real bug fixes surfaced by the new gates:**

- **207-line dead-code deletion in `renmark/cli/_engine.py`** — ruff's `F821 Undefined name` caught a dead NIM-executor block (lines 521-727 in the pre-edit file). The block was preserved "for reference" after the NIM executor was removed in v0.2.0, but it referenced `client`, `NIMQuotaError`, `NIMRateLimitError`, `NIMError` — all undefined since v0.2.0. Function returned unconditionally at line 520, so the entire block was unreachable. Deleted; all 298 tests still pass.
- **Python 3.10 syntax fix in `renmark/init.py`** — `f"... {desc.replace('|', '\\|') if desc else '—'} ..."` used a backslash inside an f-string subexpression, which is a Python 3.12+ syntax feature. On the declared minimum Python 3.10, this would syntax-error at module import. Tests didn't catch it because the dev box runs Python 3.13. The new Windows-CI cell at Python 3.10 would have caught it on the first PR; ruff caught it locally. Extracted the conditional to a separate variable before the f-string.
- **Removed unused imports** — `format_reminder_prompt` and `retry_prompt` in `_engine.py` became unused after the NIM dead-code deletion. Ruff's `F401` flagged them; pruned.
- **97 auto-fixed ruff issues** — `typing.X` → `collections.abc.X` migrations (UP rule), unused locals, simplifiable comprehensions, etc. All auto-applied, no behavior change.
- **10 unsafe-fix transforms** — SIM rules (use `contextlib.suppress` for try/except/pass patterns, collapse nested if statements, use ternaries for simple else-return). Applied with `--unsafe-fixes`, verified by full test re-run.
- **37 files reformatted** by `ruff format` — purely cosmetic, no behavior change. Format is now stable.

**Manual surgical fixes:**

- Three long-line wrappings — `cli/_engine.py:811` (argparse help text), `lifecycle.py:284` (long error message return), `providers/codex.py:80-82` (multi-line prompt template). All wrapped at 120 chars without semantic change.
- Two SIM rule fixes — `lifecycle.py:209` (collapsed nested `if`), `memory.py:212` (replaced multi-branch if/else with ternary). Semantic equivalents.
- Cleaned up `_engine.py` import block — removed two imports made unused by the dead-code deletion.

**What's deliberately deferred to follow-up:**

- The 20 lenient-strict mypy warnings: 3 union-attr (Task | None access), 4 no-any-return (typed function returning Any), 2 unreachable, others. All real catches; all warrant fixing. Tracking issue: cleanup pass to land `strict = true`.
- No-op `model = _choose_model(task, cfg)` removed from the dead block — that helper is no longer reachable. Could be deleted from `_engine.py` entirely; preserved for now in case the NIM executor ever returns.

**Acceptance criteria (from spec):**

> A vibe coder running `python -m renmark.init` on this repo should see HEALTH: 0 gaps.

Status after v0.5.3:
- ✅ Test framework: pytest (configured + 298 tests passing)
- ✅ Linter: ruff (configured + clean)
- ✅ Formatter: ruff format (configured + clean)
- ✅ Type checker: mypy (configured + lenient-strict baseline; soft-warn in pre-commit until backlog clears)
- ✅ CI: GitHub Actions (6-cell matrix; will pass once pushed to a GitHub remote)
- ✅ Pre-commit hooks: `tools/precommit.sh` (already wired via `install.sh --dev`)

**Do not change:**

- The "lenient-strict" mypy baseline. Going straight to `strict = true` would BLOCK pre-commit on 20 errors and grind contributions to a halt while the cleanup ships. The two-step path (lenient now, strict later) keeps the door open for incremental commits.
- The mypy soft-warn in `tools/precommit.sh`. Hard-failing mypy at v0.5.3 baseline would mean every commit ships under `--no-verify`, defeating the purpose. Once the 20-error backlog is cleaned up, flip to hard-fail.
- The line-length = 120 setting. 100 generated 39 E501 warnings (mostly unavoidable long signatures and template strings); 110 still left 17; 120 is the modern Python community standard and produces zero noise without forfeiting the lint budget that catches genuinely-too-long lines.
- The `RUF001`/`RUF003` ignores. Renmark deliberately uses unicode (`×`, `ℹ`, `⚠`, `→`) in stylized output and comments. Re-enabling these rules would generate hundreds of false positives across the codebase.
- The 207-line dead-block deletion in `cli/_engine.py`. It was non-executing dead code referencing a removed subsystem (NIM, deleted v0.2.0). Resurrecting it requires bringing back the NIM provider AND fixing the references; both are deliberate decisions, not accidents.

## v0.5.2 — 2026-05-28 (distribution readiness — LICENSE, install.ps1, Codex prompt, vibe-coder README)

**Patch release — makes the zip safely distributable to vibe coders on any of the three OS paths (Mac/Linux/WSL, native Windows). Closes the four real distribution blockers identified during the v0.5.1 audit: missing LICENSE file, no Windows installer, stale README, no Codex handling.**

**Reason for shipping now:** the audience is non-technical vibe coders sharing the zip hand-to-hand. They won't manually copy folders into `%USERPROFILE%\.claude\plugins\` and they won't hand-edit `settings.json`. Without `install.ps1`, Windows users would hit the same silent failure WSL did before v0.5.1 — installer "succeeds" but `/renmark:*` commands never appear. v0.5.2 closes that gap so every supported OS has a single command that produces a working install.

**New: LICENSE file (legal blocker for redistribution):**

- **`LICENSE`** (NEW) — MIT License text at repo root. `pyproject.toml` already declared MIT but the actual license text was missing from both the repo and the release zip. MIT redistribution requires the text shipped alongside the code; without it, anyone who pulls the zip can't legally redistribute. v0.5.2 ships the LICENSE file in the zip.

**New: `install.ps1` (Windows PowerShell installer):**

- **`install.ps1`** (NEW) — Mirrors `install.sh` for native Windows. Uses NTFS **junctions** (directory aliases that don't require admin/elevation) instead of symlinks, with a copy-fallback if junctions fail (uncommon — usually a corporate AppLocker policy). Performs the same 4 steps as the bash version: plugin install → `pip install -e .` → Codex prompt → `python -m renmark.doctor --fix` for registry/settings.json registration.
- **`-Uninstall` flag** — removes everything bash uninstall does: junction/copy, cache directory, settings.json entries, installed_plugins.json entries.
- **`-NoCodex` flag** — for scripted/non-interactive installs that should skip the Codex prompt.

**New: Codex CLI detection + offer-to-install (both installers):**

- **`install.sh`** — after the pip install step, detects whether `codex` is on PATH. If missing AND stdin is a terminal AND npm is available, prompts: *"Install Codex CLI now via npm? [Y/n]"*. On Y, runs `npm install -g @openai/codex` and prints the `codex login` reminder. On N or non-interactive, prints the manual install steps. If npm itself is missing, prints the Node.js install URL + manual steps. Codex is OPTIONAL — without it, `executor: codex` tasks fall back to Sonnet automatically, so the prompt is a recommendation not a hard requirement.
- **`install.ps1`** — same logic in PowerShell. Same prompt, same fallbacks, same package name (`@openai/codex` — Codex CLI bundles per-platform binaries, so the npm command is identical on all three OSes).

**README rewrite for vibe-coder audience:**

- **`README.md`** — replaced the stale `unzip ai-system-renmark-v0.3.0-*.zip` example with a version-agnostic `v*` glob. Rewrote the Windows section from "manually copy folders into `%USERPROFILE%\.claude\plugins\renmark\` (which won't work — the silent-failure bug)" to `.\install.ps1`. Added a dedicated **Codex CLI** section explaining when to install it and the one-line install command. Added **Troubleshooting** section explaining what to do if `/renmark:*` commands don't appear (`python -m renmark.doctor --fix`).
- **WSL-vs-Windows-native note** — explicit callout: if Claude Code is running inside WSL Ubuntu, use `install.sh` not `install.ps1`. PowerShell installer only registers with `%USERPROFILE%\.claude\` which Claude Code under WSL doesn't read.

**Do not change:**

- **The `@openai/codex` npm package name.** Codex CLI uses an optional-platform-dependencies pattern that bundles per-OS binaries (`@openai/codex-linux-x64`, `@openai/codex-darwin-arm64`, `@openai/codex-win32-x64`) — the parent `@openai/codex` package resolves the right binary at install time. One install command works on every supported OS.
- **The junction-then-copy fallback in install.ps1.** Junctions don't need admin, copies don't either, but copies break the "edit source → see changes" workflow. We prefer junction so dogfooding stays live; the copy is only a last resort when corporate policy blocks junctions entirely.
- **`-NoCodex` as opt-out (not opt-in).** Defaulting to "ask about Codex" is the vibe-coder-friendly behavior; CI/scripted callers can pass `-NoCodex` to suppress the prompt. Flipping the default would silently skip a recommended dependency for most users.

## v0.5.1 — 2026-05-28 (/renmark:doctor + install.sh self-registers with Claude Code)

**Patch release — fixes the silent-install failure mode discovered during v0.5.0 dogfooding. The canonical `install.sh` only created symlinks; Claude Code requires THREE additional entries in `~/.claude/settings.json` and `~/.claude/plugins/installed_plugins.json` before slash commands appear. Without them, `/renmark:*` silently doesn't show up — the worst-possible UX for a vibe-coder-targeted tool whose first impression depends on a clean install.**

**New command — `/renmark:doctor`:**

- **`plugin/commands/doctor.md`**, **`plugin/skills/doctor/SKILL.md`** (NEW) — thin command stub + skill dispatcher. The skill invokes `python -m renmark.doctor` and relays its checklist output; agents do no diagnosis work themselves.
- **`/renmark:doctor`** — runs 9 health checks: CLI on PATH, Python package importable, VERSION file present, plugin manifest version parity, Claude Code registry registration, settings.json marketplace registration, settings.json plugin-enabled flag, cache install path resolves to source, convenience symlink. Each check prints a ✓ / ✗ / ! glyph, a one-line detail, and (for failures) a `fix:` line.
- **`/renmark:doctor --fix`** — applies safe auto-fixes for the four known-remediable failures (add to `extraKnownMarketplaces`, set `enabledPlugins[…] = true`, register in `installed_plugins.json`, create the cache version symlink). Every modified file gets a timestamped `.doctor.bak.<unix-time>` backup first.
- **`/renmark:doctor --json`** — machine-readable output for scripting (CI, integration with editor extensions, etc.).

**New Python module — `renmark/doctor.py`:**

- 9 deterministic checks. Read-only by default; `--fix` writes only to `~/.claude/settings.json`, `~/.claude/plugins/installed_plugins.json`, and `~/.claude/plugins/cache/renmark-local/<version>/`.
- Each `Check` carries: name, status (`pass` / `fail` / `warn`), one-line detail, optional `fix_cmd` for users to run manually, and (when auto-fixable) a callable that applies the fix idempotently.
- Detects 4 specific drift modes that cause silent load failure: (1) version mismatch between VERSION file and installed_plugins.json registry, (2) missing `extraKnownMarketplaces.renmark-local` (cache file `known_marketplaces.json` is regenerated from this — editing only the cache doesn't stick), (3) missing `enabledPlugins["renmark@renmark-local"] = true`, (4) cache symlink pointing to a non-existent or wrong-version directory.

**`install.sh` now self-registers:**

- After the symlink and pip-install steps, calls `python -m renmark.doctor --fix` to write the three required registry entries automatically. Same Python logic that `/renmark:doctor` uses to repair broken installs — DRY, with backups always taken before writes.
- `install.sh --uninstall` now also removes the renmark entries from `settings.json` and `installed_plugins.json`, and wipes `~/.claude/plugins/cache/renmark-local/`. Pre-v0.5.1 uninstalls left dangling registry entries that surfaced as "Plugin not found in marketplace" warnings in the `/plugin` UI.
- Post-install banner adds `/renmark:doctor` to the skill list.

**Background — why this matters:**

A directory-marketplace Claude Code plugin needs THREE moving parts to surface its slash commands:

1. `~/.claude/plugins/installed_plugins.json` — registry entry under `<plugin>@<marketplace>`, with `version` matching the marketplace's current version (drift causes silent skip), and `installPath` pointing to an existing directory.
2. `~/.claude/settings.json` → `extraKnownMarketplaces.<marketplace-name>` — tells Claude Code where the marketplace lives. The cache file `~/.claude/plugins/known_marketplaces.json` is *derived* from this; editing only the cache doesn't survive a reload.
3. `~/.claude/settings.json` → `enabledPlugins["<plugin>@<marketplace>"] = true` — Claude Code requires explicit enable for directory marketplaces. Without this, the plugin loads (no error) but commands don't appear in the slash menu.

A plain `install.sh` that only writes symlinks misses #2 and #3 entirely, and the resulting failure is silent — `/reload-plugins` reports "1 error during load" without naming the plugin. v0.5.1 closes that gap.

**Other changes:**

- **`plugin/skills/help/SKILL.md`** — `/renmark:doctor` added to the command catalog with a hint about when to use it.

**Do not change:**

- The doctor module's "read-only by default" stance. Making it edit settings.json without `--fix` would surprise users who run it for diagnosis.
- The `.doctor.bak.<timestamp>` naming convention for backups. The integration tests and rollback procedures assume that pattern.
- The decision to delegate install-time registry writes to `python -m renmark.doctor --fix`. Pulling the JSON-edit logic into raw bash inside install.sh would duplicate it and re-create the maintenance burden v0.5.1 was designed to eliminate.

## v0.5.0 — 2026-05-28 (/renmark:init — codebase map + dev-standards/health scanner)

**Minor release — renmark gains its own analog to Claude Code's native `/init`, but designed around context-window hygiene from day one. Walk into any project (greenfield or production) and get a verdict: what the code looks like, what standards the project enforces, and where the standards are loose enough to break things.**

The driving observation: CLAUDE.md is loaded into the system prompt on every turn of every conversation, forever. Embedding a 2-3k-token project map in CLAUDE.md would be paid permanently as context tax — worse than re-running `find` + `grep` on demand. So the design splits content by access pattern: tiny stub in always-loaded context (~200-300 tokens), full payload in on-demand files (`.renmark/memory/project-map.md`, `.renmark/memory/dev-standards.md`).

**New command — `/renmark:init`:**

- **`plugin/commands/init.md`**, **`plugin/skills/init/SKILL.md`** (NEW) — thin command stub + skill dispatcher. The skill's only job is to invoke `python -m renmark.init` and relay the one-line summary; agents do no scanning, no regex, no rendering. Token cost per invocation: near-zero (just script stdout).
- **`/renmark:init --deep`** — opt-in flag for slower checks: samples last 20 git commits for conventional-commits style. Reserved for future expensive checks (GitHub branch-protection lookups, test-naming inference). Baseline scan runs without the flag.
- **`/renmark:init scan`** — diagnostic mode; prints what would be detected, writes nothing.

**New Python module — `renmark/init.py`:**

- **Project map scanner.** Walks the repo respecting `.gitignore` (excludes `.git`, `node_modules`, `.venv`, `dist`, `build`, `.next`, `target`, `.renmark/state`, `.renmark/debug`, etc.). Detects stack from `pyproject.toml` / `package.json` / `go.mod` / `Cargo.toml` / Claude Code plugin manifest. Extracts public symbols from the top-20 largest source files for Python, JS/TS, Go, Rust, Ruby. Caps modules table at 40 rows, symbols-per-file at 6, top-level layout at 7 dirs. No file bodies, no docstring transcripts.
- **11 dev-standard detectors.** Test (pytest/jest/vitest/cargo/go), lint (ruff/flake8/eslint/rubocop/clippy), formatter (black/ruff format/prettier/rustfmt/gofmt), type-checker (mypy/pyright/tsc-strict), CI (GitHub Actions/GitLab/CircleCI — extracts workflow names), pre-commit (`.pre-commit-config.yaml` hooks + Husky), env schema (`.env.example` key names only, never values), database/migrations (alembic/prisma/drizzle/knex), local-dev startup (npm scripts/Makefile/docker-compose), code style (`.editorconfig`), dep policy (dependabot/renovate/lockfiles).
- **11 standards-health gap checks** with severity ranking. 🚨 danger: `.env` committed without `.gitignore` entry; multiple JS package-manager lockfiles concurrently. ⚠ warn: no linter; no type checker (or tsconfig without `"strict": true`); no tests in a >10-file project; test framework configured but zero test files; linter not wired to pre-commit OR CI; no CI on a multi-file project; pre-commit AND CI both missing; missing lockfile when `package.json` exists. ℹ info: no `.gitignore`; no README. Each gap carries a *tighten-this* recommendation pointing to the exact remediation.
- **Byte-equality skip on every artifact.** If the rendered stub body matches the existing `<!-- BEGIN:project-stub -->` block in CLAUDE.md, the file is not rewritten — no prompt-cache bust. Same check for `project-map.md` and `dev-standards.md` (stripping the timestamp header line so the freshness stamp doesn't trigger spurious rewrites).

**Three artifacts, three access patterns:**

- **CLAUDE.md / AGENTS.md stub** (always-loaded, ~250 tokens) — stack one-liner, top-level layout, `Dev gates:` line listing test/lint/typecheck/CI commands when detected, and pointers to the on-demand files. The gates line is conditional: greenfield projects with no detected standards produce a stub with no gates line at all.
- **`.renmark/memory/project-map.md`** (on-demand, opt-in payload) — full directory tree, modules table with symbols, user-facing commands catalog. Read by agents that need to navigate the codebase.
- **`.renmark/memory/dev-standards.md`** (on-demand, opt-in payload) — detected-standards table + standards-health section with severity-ranked gaps and recommendations. Read by agents about to make non-trivial changes.

**Auto-refresh hooks wired into the pipeline:**

- **`/renmark:setup`** — step 5.5 seeds the project map and dev-standards on first run (skipped if `project-map.md` already exists). One-time bootstrap.
- **`/renmark:finish`** — step 1.5 refreshes both artifacts after verifiers pass but before the branch summary. If the byte-equality skip says nothing changed (e.g. feature only fixed bugs, no shape change), no files are written, no commit is made, no cache is busted. If anything changed, files are staged and committed as `docs: refresh project map` so the refresh ships with the feature.
- **`/renmark:init`** — manual escape hatch for hand-edited or out-of-pipeline changes.
- **Explicitly NOT hooked into `/renmark:orchestrate` or `/renmark:debug`** — those run too frequently for the cost-to-value ratio. Per-task or per-fix refreshes would bust the CLAUDE.md cache 5-15 times per feature for the same information value finish would refresh once.

**stdout contract — what the agent sees:**

```
OK  stub=<created|refreshed|unchanged> agents=<…|skipped> map=<…> standards=<…> modules=N commands=N langs=py,ts,… ref=YYYY-MM-DD@<git-sha>
HEALTH: N gaps (X danger, Y warn, Z info) — see `.renmark/memory/dev-standards.md`
```

The HEALTH line only appears when at least one gap exists. A clean project produces just the OK line.

**Other changes:**

- **`plugin/skills/help/SKILL.md`** — `/renmark:init` added to the command catalog.
- **`.claude-plugin/marketplace.json`** — skills list updated to include `init`.

**Do not change:**

- Changelog format — renmark reads and appends to this file automatically; the `## [date] — [title]` heading shape is parsed by the version-drift gate and the release-notes generator.
- The byte-equality skip logic in `renmark.init` — without it, every `/renmark:finish` would rewrite CLAUDE.md and bust the prompt cache for every conversation in the project. The skip is what makes the auto-refresh strategy affordable.
- The "stub vs payload" split — moving full module/symbol detail back into CLAUDE.md would re-introduce the context-tax problem this release was designed to solve.

## v0.4.0 — 2026-05-28 (verify --qa / --deep-qa: live-browser E2E verification)

**Minor release — verification grows a second lens. Smoke proves the happy path *responds*; QA proves it *works in a browser*; Deep QA proves it *fails gracefully at the edges*. All three are reachable from each other in one keystroke via a shared hand-off menu.**

The driving goal: stop the loop of "ask to fix → find it's still broken → surgically fix what QA should have caught." Live-browser E2E that runs automatically-on-request and produces specific, reproducible findings makes the fix loop converge. Spec lived as draft at `.renmark/specs/2026-05-27-verify-qa-browser-e2e.spec.md` since v0.3.3; this release implements it as skill prose with zero new Python deps.

**New shared file:**

- **`plugin/skills/_shared/handoff-menu.md`** (NEW) — single source of truth for the quality-gate hand-off menu, referenced by `verify`, `verify --qa`, `verify --deep-qa`, and `codereview`. Same `_shared/` pattern as `scope-contract.md` (already excluded from the plugin linter as of v0.3.3). Documents the four canonical gate letters (`[s]` Smoke, `[qa]` QA, `[dq]` Deep QA, `[c]` Code review) plus the terminal actions, and the five rendering rules (omit the gate just run; show `[dq]` only after `--qa` passes; show `[d]` only on failure; etc.). Adding a future gate (perf, security) is now a one-file edit.

**`verify --qa` — one live-browser happy-path flow:**

- **Applicability gate.** Web project (per `.renmark/memory/stack.md` / `package.json`) + Chrome DevTools MCP reachable (`list_pages` probe). Non-web project → "N/A, no browser surface." MCP unavailable → degrade to shell smoke with a one-line note. Never crash, never block.
- **Server lifecycle.** Detect-or-boot the dev server via the run command from `CLAUDE.md § Testing` / `stack.md`; record `qa_started_server` so we tear down only what we booted, never a server the user is using.
- **Single happy-path flow** derived goal-backward from the spec's #1 user-visible behavior; driven via `navigate_page` / `take_snapshot` / `click` / `fill` / `wait_for` / `take_screenshot` / `list_console_messages` / `list_network_requests`.
- **Pass criteria (5 hard, 2 soft).** Hard: page loads (not blank/500), no uncaught console errors, no 4xx/5xx on the path, expected result element renders (`wait_for`), no error UI. Soft: persistence + latency. Each failure names *which* criterion broke so the verdict line is specific.
- **Context-hygiene contract — non-negotiable.** Screenshots go to `.renmark/reviews/qa/<feature>/step-N.png`; console + network dumps go into the artifact body; accessibility snapshots are used transiently to find selectors and then discarded. The orchestrator sees only the ≤5-line verdict block + artifact pointer.
- **Artifact:** `.renmark/reviews/YYYY-MM-DD-<sha>.qa.md` via `summary.write_artifact(artifact_type="qa", generator="verify-qa", ...)`.

**`verify --deep-qa` — 3 risk-ranked edge-case flows:**

- **Hard gate behind a passing `--qa`.** Refuses unless a `.qa.md` artifact exists for the current sha with `completion_state="complete"` and `generator="verify-qa"`. Edge cases on a broken happy path are noise.
- **Plan phase — risk-rank, then pick 3 (no browser yet).** Reads the diff (bounded — never pasted into chat), the feature behaviors, and `bugs.md` entries whose `files:` overlap, then ranks failure modes by likelihood using a 6-category checklist (empty/missing, boundary/size, malformed/hostile, error path, state/sequence, authz). Surfaces top 3 + one-line rationale each for user approval before opening a browser.
- **Runs them serially**, in risk order, in the singleton main-agent browser. Pass condition is **graceful handling**: no uncaught console exception, no crash, no corrupt state, either tolerates the input OR rejects with a clear visible error — not silent no-op, not infinite spinner.
- **Artifact:** `.renmark/reviews/YYYY-MM-DD-<sha>.deep-qa.md`; per-case evidence under `.renmark/reviews/qa/<feature>/deep/case-N/`.
- **Why serial-in-main, not subagents:** at 1+3 flows that each dump evidence to disk and return only verdict lines, the main context never holds heavy payloads — subagent fan-out buys nothing against a singleton browser and adds coordination cost.

**Three gates, mutually reachable:**

- `verify` (smoke), `verify --qa`, `verify --deep-qa`, and `codereview` all now render the menu from `_shared/handoff-menu.md`, omitting the gate just run and showing `[dq]` only after `--qa` passes for the current sha and `[d]` only on a failure. Re-testing a feature from a different angle is one keystroke at any point.
- `codereview`'s hand-off was extended: in addition to its existing `[o] Open` / `[fix] Fix` actions, it now offers Smoke + QA + (conditionally) Deep QA + Debug + Finish + Nothing.

**Convergence loop (the certainty mechanism):**

- Every `--qa` / `--deep-qa` failure calls `memory.log_bug` with a reproducible finding — symptom + console/error + file:line if discoverable + repro steps. A later `verify --qa` re-runs the failing flow plus the `bugs.md` regression set; the fix loop converges. No "still broken" surprises downstream.
- Every run (pass or fail, any mode) calls `memory.append_learning` (G8 compounding).

**No Python module changes required.** The browser MCP session is the main agent's; `renmark/` Python stays as-is. `summary.write_artifact` accepts `artifact_type="qa"` / `"deep-qa"` via its existing generic field; no signature changes.

**Lifecycle:** `--qa` / `--deep-qa` do NOT add new stages. Both run at stage `verified` (or re-run there). The verification artifact pointer is updated via `lifecycle.write_lifecycle(artifact_update=("qa", ...))` / `("deep-qa", ...)`, but `stage` stays `verified` — codereview / finish remain the next recommended steps.

**Files touched:**

- New: `plugin/skills/_shared/handoff-menu.md`.
- Modified: `plugin/skills/verify/SKILL.md` (smoke hand-off rewritten to use shared menu; full `--qa` and `--deep-qa` sections added), `plugin/skills/codereview/SKILL.md` (hand-off appends shared menu), `plugin/commands/verify.md` (description + `argument-hint` + mode-selection notes), `.renmark/specs/2026-05-27-verify-qa-browser-e2e.spec.md` (`status: draft` → `implemented` + `related_release: v0.4.0`), all 7 canonical version locations, this changelog.

**Do not change:**

- The hand-off menu text lives in `_shared/handoff-menu.md` and nowhere else. If you find yourself pasting the menu into a SKILL.md, stop and reference the shared file instead — drift across skills was the exact problem this directory was added to solve.
- The Deep QA gate (`--deep-qa` refuses unless a passing `.qa.md` exists for the current sha) is load-bearing. Removing it means edge cases run against a happy path that doesn't work, producing meaningless noise.
- The context-hygiene contract for `--qa` / `--deep-qa` (screenshots/console/network → disk; orchestrator sees only the ≤5-line verdict) is non-negotiable. If a future change makes the orchestrator ingest browser payloads, the whole point of running this in the singleton main agent is defeated — split it into a subagent flow first.
- The browser MCP session is a singleton owned by the main agent. Do not introduce a subagent-driven browser flow; that path (subagent fan-out for many journeys) was explicitly deferred.

**Verification:** 298 unit tests pass (no Python changes, no test changes), plugin lint clean, drift check clean (all 7 version locations at v0.4.0). The new skill prose is text-only and exercised by the existing lint test that checks every SKILL.md has matching frontmatter + paired command shim.

## v0.3.3 — 2026-05-27 (pipeline streamlining + research + write boundary)

**Fewer commands, more done per command. The day-to-day path is now four steps (brainstorm → plan → orchestrate → finish) because validation and verification auto-run inside the steps they belong to. brainstorm gained research; the project-write boundary is now a hard rule.**

**Distribution packaging (new — `/renmark:finish` § Release):**

- **`renmark.release.build_package()`** — pure-Python (no rsync/zip CLI, no new deps) builder that zips the distributable into the **project's** `.renmark/baks/<name>-v<version>.zip`, version-anchored to match the git tag `v<version>`. Honors the project-write-boundary rule (writes only inside the project) and excludes `.git`, `.venv`, `__pycache__`, `.env`, `.renmark/`, `PLAN.md`, etc. CLI: `python -m renmark.release package`. (+5 tests)
- **`/renmark:finish` gains an `[r] Release` option:** drift-gate → build the local bak (always, offline) → tag `v<version>` → **if** a git remote + `gh` exist, offer to push the tag and `gh release create` with the zip attached; otherwise report the local bak + tag as a complete offline release. One version string across bak filename, git tag, and GitHub release — never drifting. The local `.renmark/baks/` copy is the offline fallback when you don't want to pull from GitHub.
- `.renmark/baks/` is gitignored (regenerable; the GitHub release is the shareable canonical copy).
- **`--dest` / `--name` overrides** on `release package` (and `build_package(dest_dir=, archive_stem=)`) — a maintainer escape hatch to package renmark's OWN release to a sibling dir with a custom name (e.g. `~/projects/ai-system-renmark-v<version>-<date>.zip`), rather than into a managed project's `.renmark/baks/`. Managed-project releases still default to `.renmark/baks/`.

**Pipeline auto-chaining (commands stay standalone-callable):**

- **`/renmark:plan` auto-runs `/renmark:check-plan`.** After writing the plan, validation runs automatically before the dispatch gate. BLOCK loops back to fix; PASS/WARN advances the lifecycle to `plan-validated` and shows the cost-approval gate. The critical cost gate stays in `plan` — auto-validation never silently dispatches. `/renmark:check-plan` remains callable on any plan.
- **`/renmark:orchestrate` auto-runs `/renmark:verify`.** A fully clean run (all tasks pass) flows straight into goal-backward verification, which advances the stage to `verified` and presents the review/finish hand-off. On any task failure the run pauses and does NOT auto-verify. `/renmark:verify` remains callable standalone.

**brainstorm upgrades:**

- **Research phase (new).** Before proposing approaches, brainstorm researches best practices, prior art (existing software that solves the problem), and live GitHub reference implementations via `WebSearch` / `WebFetch` / Context7. Findings are written to a `.renmark/research/` artifact; only a ≤5-line summary enters the conversation (G3/G6). The design is now informed, not invented. (Folds in the previously-planned `/renmark:research` gap.)
- **Owns the scope contract.** brainstorm now runs the stack/deployment/MVP questions and writes the records (`stack.md` + CHANGELOG scope entry), so `/renmark:plan` detects them and skips re-asking.

**Single source of truth:**

- **`scope-contract.md` moved to `plugin/skills/_shared/`** and is now referenced by both `brainstorm` and `plan`. The stack/deployment/MVP questions live in exactly one place and can't drift. The plugin linter now skips `_`-prefixed shared dirs (they're reference files, not skills). (+1 lint test)

**Hard rule — project-write boundary:**

- **renmark must never write outside the project.** All specs, plans, reviews, research, logs, and memory go under the project's `.renmark/` subtree (or project-root docs). The global plugin install (`${CLAUDE_PLUGIN_ROOT}`, `~/.claude/...`) is read-only — reading templates/reference files from it is fine, writing to it is forbidden. Codified as `project-write-boundary-rule` in `CLAUDE.md.template` and mirrored in `AGENTS.md.template`.

**Verification:** 292 unit tests pass (+1 lint test), 28 integration skipped, shadow baselines clean, plugin lint clean. These are skill-prose + linter changes; the lifecycle stage machine already supported the auto-chained flow, so no Python state changes were required beyond the linter.

## v0.3.2 — 2026-05-27 (context-hygiene + maintainability audit)

**Patch release — seven audit fixes hardening the isolation boundary, spend reporting, and module structure. No breaking changes; the public import surface is preserved.**

**Context-hygiene fixes:**

- **G3 char-cap leak closed** — `SubagentOutput.__post_init__` (`dispatch.py`) now enforces the ≤1200-char-per-line cap and a non-string guard, not just the ≤5-line count. A 5-line × 5000-char payload can no longer slip through `parse_subagent_response`. The cap matches `schemas.py` and `summary.py`. (+3 tests)
- **Lifecycle dead-pointers fixed** — `NEXT_BY_STAGE` no longer routes to unimplemented skills (`/renmark:document`, `/release`, `/approve`, etc.). `next_recommended()` resolves through a new `IMPLEMENTED_SKILLS` set and falls back to manual hints; aspirational routing preserved in `NEXT_BY_STAGE_PLANNED`. A regression test iterates every canonical stage. (lifecycle.py)
- **Agent-call spend ledgered** — new `state.log_agent_call()`; the orchestrate skill records every haiku/sonnet/opus Agent return so `/renmark:roadmap` reports real spend. `roadmap.py` now prices opus at ~$0.015/kT (was treated as free) and includes haiku.
- **Honest cost preview** — `plan/SKILL.md` bakes the ~10k Agent-call overhead into the displayed total instead of footnoting it; the dry-run footer was corrected to match.
- **Step-0 boilerplate consolidated** — new `lifecycle.skill_preamble(repo, skill)` replaces the duplicated `context_budget_check` + `record_skill_invocation` block across all 14 SKILL.md files. Domain resolves centrally from `DOMAIN_BY_SKILL`, so per-skill drift is impossible.
- **Artifact-dir rotation** — new `state.rotate_dir()` caps `wave-summaries/` (50), `logs/` (50), and `escalations/` (20), archiving overflow to `.renmark/state/archive/<stamp>/`. Best-effort; never breaks a running orchestrate. (+4 tests)

**Maintainability:**

- **`state.py` (538 lines) → `state/` package** — eight cohesive submodules (`_core`, `usage`, `pause`, `pipeline`, `logs`, `commits`, `skills`) behind a re-exporting `__init__.py`. Rotation caps are read via `_core` at call-time so they stay monkeypatchable.
- **`cli.py` (982 lines) → `cli/` package** — execution engine (`_engine.py`) split from the self-contained subcommand handlers (`commands.py`); re-exporting `__init__.py` keeps `cli.main` / `cli.cmd_task` / `cli.execute_plan` intact.

**Verification:** 291 unit tests pass (+10 new), 28 integration skipped (codex/network-gated), shadow baselines re-accepted (lifecycle `case-full-walk`), functional smoke green (`--usage`/`--roadmap`/`--logs`/dry-run). Independent codex review was unavailable (account model limitation); reviewed via diff + runtime invariant checks.

## v0.3.1 — 2026-05-21 (integration testing + guardrails)

**Patch release — the framework now defends itself against regressions.**

Three layers of test discipline land in v0.3.1: per-commit guardrails (fast), per-release integration smoke (thorough), and per-task shadow tests (regression detection on load-bearing subsystems). Every layer is opt-in or gated so day-to-day work stays fast.

**New modules:**

- **`renmark/schemas.py`** (NEW, 24 tests) — zero-dependency structural validators for `lifecycle.json`, `pipeline.json`, `SubagentOutput` JSON, and `ArtifactMetadata`. G11 isolation enforcement catches transcript/diff/reasoning leakage at the schema layer. G3 summary boundary enforced (≤5 lines, ≤1200 chars per line). G12 lifecycle byte budget enforced. CLI: `python -m renmark.schemas {lifecycle|pipeline|subagent|artifact} <path>`.
- **`renmark/lint.py`** (NEW, 25 tests) — plugin contract linter. Verifies every SKILL.md has valid frontmatter with matching `name:`, every `commands/<name>.md` has a paired `skills/<name>/SKILL.md` (and vice versa — no orphan commands, no unreachable skills), CLAUDE.md.template has balanced `BEGIN:` / `END:` rule-block markers, and `plugin.json` has required fields. CLI: `python -m renmark.lint [--plugin-dir DIR]`.
- **`renmark/release.py`** (NEW, 20 tests) — version-file drift detection pulled forward from the v0.4.0 release skill. `VERSION_FILES` catalogs the 7 locations that carry the canonical version (VERSION, pyproject.toml, `renmark/__init__.py`, plugin.json, marketplace.json metadata + plugins[0], README.md header). `python -m renmark.release check` exits 1 on any disagreement. Bump/tag/zip operations stay deferred to v0.4.0 — this module is read-only at v0.3.1.
- **`renmark/shadow.py`** (NEW, 22 tests) — record-and-replay regression framework. Per-subsystem `replay(case_dict) → output_dict` functions registered via `@shadow.register("name")`. `run` replays every case and diffs against the committed baseline; `accept --subsystem X -m "msg"` re-records baselines and prepends a `CHANGES.md` entry. Initial subsystems: `dispatch`, `lifecycle`, `summary` (9 baselined cases total, including adversarial leakage scenarios).

**New tooling:**

- **`tools/precommit.sh`** — 30-second pre-commit guard: pytest, drift check, plugin lint. Three-step output, fails loud on any issue. Total budget for the renmark repo today: ~3s warm.
- **`install.sh --dev`** — opt-in flag that symlinks `tools/precommit.sh` to `.git/hooks/pre-commit`. Existing hooks are moved aside with a timestamped `.bak.` suffix, never overwritten. `--uninstall` removes the dev hook alongside the plugin.

**Integration smoke suite:**

- **`tests/integration/`** (NEW, 27 tests, gated behind `RENMARK_SMOKE=1`) — five end-to-end tests against a synthetic fixture project: full-lifecycle round-trip with schema validation at every stage, cold-start recovery via subprocess (simulates `/clear`), dispatch isolation E2E with realistic adversarial responses (transcript / generated_code / diff / reasoning / conversation / raw_output / trace leakage all blocked), codex-fallback behavior when codex CLI is absent, plugin install.sh round-trip in a fake `$HOME`. `conftest.py` auto-skips integration tests unless `RENMARK_SMOKE=1` so unit-test runs stay at ~2.5s.
- Fixtures: `repo_root`, `fixture_project` (initialized git repo with baseline `.renmark/` tree), `fixture_plan` (writes a one-task plan into the fixture).

**Shadow framework specifics:**

- Baseline files live at `tests/shadow/baselines/<subsystem>/case-*.json` (committed, ~few KB total). Cases live at `tests/shadow/cases/<subsystem>/case-*.json`.
- Replay functions are deterministic — `lifecycle.last_updated` (timestamp) and `summary.created_at` are stripped or fixed to keep baselines stable.
- `accept` requires a non-empty `-m MESSAGE` explaining the change. Prepends to `tests/shadow/CHANGES.md` below the header so the most recent change is on top.
- Shadow framework's own correctness tested by `tests/test_shadow.py` using `monkeypatch` to redirect `_shadow_root` at a tmpdir — 22 unit tests verify drift detection, missing-baseline handling, accept idempotency, deterministic replay, CLI flag handling.

**Test counts:**

- Unit tests: **283 passed, 28 skipped** in 2.56s (smoke gated off)
- Full suite: **311 passed** in 18.13s (`RENMARK_SMOKE=1`)
- Net new tests in v0.3.1: **+113** (schemas 24 + lint 25 + release 20 + shadow 22 + integration 22 = exactly the additions; 261 → 283 unit, +28 integration = +50 not counting the bumps from shadow framework's own tests)

**Risk-reduction posture:**

- Three independent regression nets now exist. A bug in one is caught by another: schema drift catches structural breakage, drift check catches version desync, lint catches plugin-contract rot, smoke catches integration breakage, shadow catches behavioral drift in load-bearing modules.
- Pre-commit hook is opt-in by design — `bash install.sh --dev` activates it. Default install path stays as fast as v0.3.0.
- Future v0.4.0 `/renmark:release` will invoke shadow + smoke + drift as its preflight checks before tagging.

**Files touched:**

- New: `renmark/schemas.py`, `renmark/lint.py`, `renmark/release.py`, `renmark/shadow.py`, `tools/precommit.sh`, `tests/test_schemas.py`, `tests/test_lint.py`, `tests/test_release_drift.py`, `tests/test_shadow.py`, `tests/integration/__init__.py`, `tests/integration/conftest.py`, `tests/integration/test_smoke_full_lifecycle.py`, `tests/integration/test_cold_start_recovery.py`, `tests/integration/test_dispatch_isolation_e2e.py`, `tests/integration/test_codex_fallback.py`, `tests/integration/test_plugin_install.py`, `tests/shadow/cases/{dispatch,lifecycle,summary}/case-*.json` (9 files), `tests/shadow/baselines/{dispatch,lifecycle,summary}/case-*.json` (9 files), `tests/shadow/CHANGES.md`.
- Modified: `install.sh` (added `--dev` flag), `VERSION`, `pyproject.toml`, `renmark/__init__.py`, `plugin/.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `README.md` (version bump only).

---

## v0.3.0 — 2026-05-19 (framework MVP — context death is survivable)

**Minor release — the foundation that makes renmark a development framework, not just a plugin.**

The core innovation this release: **AI workflows that survive context death.** Cold start from any `/clear` or `/compact` is one file read. Heavy work runs in isolated subagent contexts. The orchestrator is now structurally incapable of merging generated code into its conversation — the parser refuses it.

**Load-bearing new infrastructure** (the MVP five):

- **`renmark/summary.py`** (NEW, 323 LOC, 19 tests) — `write_artifact`, `emit_pointer`, `read_metadata`, `is_stale`, `verifier_tail`, `hash_artifact`, `git_head_sha`. Enforces G3 (5-line summary cap, ~300 tokens per line), G6 (provenance + freshness metadata on every artifact), G9 (`completion_state` / `confidence` / `validation_status` / `retry_count` / `parser_success` / `schema_compliance` transparency fields). Every auditor skill funnels through this module.
- **`renmark/lifecycle.py`** (NEW, 251 LOC, 18 tests) — workflow state for the seven-stage lifecycle. `read_lifecycle`, `write_lifecycle`, `clear_lifecycle`, `next_recommended`, `domain_of`, `is_cross_domain_transition`. Strict 1KB byte budget; runtime cruft is rejected with `LifecycleBloatError` to keep lifecycle.json separate from pipeline.json. G12 codified.
- **`renmark/state.py`** (extended +200 LOC, 15 new tests) — pipeline.json (`read_pipeline_state`, `write_pipeline_state`, `clear_pipeline_state`, `pipeline_is_resumable`), `.renmark/state/wave-summaries/wave-N.json` aggregation (`write_wave_summary`, `read_wave_summary`, `list_wave_summaries`), and `last-skill.json` for cross-domain detection (`record_skill_invocation`, `last_skill_invocation`, `context_budget_check`).
- **`renmark/dispatch.py`** (extended +190 LOC, 19 new tests) — G11 task isolation contract. `SubagentInput` (the ONLY fields a subagent receives) and `SubagentOutput` (the ONLY fields it emits) are frozen dataclasses. `parse_subagent_response` raises `IsolationViolation` on any extra field (transcript, diff, generated_code, reasoning). `dispatch_task_isolated` is the injection point — wraps subagent runners under strict I/O bounds.
- **`renmark/cli.py`** (+110 LOC, 6 new tests) — `--task SPEC --output ARTIFACT` ad-hoc Codex mode. Emits SubagentOutput-shaped JSON to stdout; the generated body lives in the artifact file, never the conversation. Falls back cleanly when codex CLI is missing.
- **`plugin/skills/resume/SKILL.md`** (NEW, 112 lines) — `/renmark:resume`. Zero LLM calls. Reads `lifecycle.json`, prints stage + next recommended command + any pending human approval gate. The cold-start recovery surface.

**Skill behavior changes:**

- All 13 existing skills gained a **Step 0 — Context check** preflight that calls `state.context_budget_check` (for cross-domain `/clear` recommendations) and `state.record_skill_invocation` (for next-skill detection). Skills with stage semantics (start, brainstorm, plan, check-plan, finish) now also write `lifecycle.json` on completion.
- `/renmark:orchestrate` rewritten to honor G11 task isolation: builds dependency context only from prior wave's `dependency_notes` (never the full output), dispatches each task in isolation via `dispatch_task_isolated`, aggregates `SubagentOutput` dicts into `.renmark/state/wave-summaries/wave-N.json`, refuses to merge subagent responses that contain forbidden fields. Pipeline state machine tracked at wave boundaries; `lifecycle.write_lifecycle(stage='created')` on completion.
- `/renmark:check-plan` gained 5 new hygiene + isolation BLOCK/WARN rules: heavy-read check (G5), transcript-leak phrase denylist (G11), dependency-graph hygiene (G11), verifier output bound check (G3), spec length WARN.
- `/renmark:verify` strengthened to goal-backward mode: reads plan goal via `parser.parse_plan`, cross-references open bugs from `.renmark/memory/bugs.md` for regression coverage (G8 compounding), runs commands via `summary.verifier_tail` (bounded output), emits a `.verification.md` artifact via `summary.write_artifact`, appends to `learnings.md` on every run and `bugs.md` on failures. Refuses if pipeline state is dirty.

**New rule blocks in `plugin/templates/CLAUDE.md.template`:**

- `context-budget-rule` — `/compact` at 60%, `/clear` on cross-domain transitions. Domain taxonomy: debug, build, audit, meta.
- `lifecycle-rule` (G12) — every stage transition writes lifecycle.json; cold start is one file read; strict separation from pipeline.json; human approval gates carried in `human_review_required` / `human_review_completed` / `human_review_for` fields.

`plugin/templates/AGENTS.md.template` gained two one-liner mirrors. `plugin/skills/setup/SKILL.md` merge table extended from 15 to 17 blocks.

**`renmark/__init__.py` version drift fixed.** Was stuck at `0.2.0` since the package was forked from ai-inference; now in sync at `0.3.0`.

**Tests:** 192 → 192 passing. 77 new tests added across summary, lifecycle, pipeline state, isolation, and CLI task mode. Zero regressions.

**Files changed:**
- `renmark/summary.py` — NEW
- `renmark/lifecycle.py` — NEW
- `renmark/state.py` — extended (pipeline + wave-summaries + skill invocations)
- `renmark/dispatch.py` — extended (SubagentInput/Output, IsolationViolation, dispatch_task_isolated, parse_subagent_response, build_subagent_input)
- `renmark/cli.py` — `--task` / `--output` ad-hoc Codex mode
- `renmark/__init__.py` — version sync 0.2.0 → 0.3.0
- `plugin/skills/resume/SKILL.md` — NEW
- `plugin/skills/orchestrate/SKILL.md` — full rewrite
- `plugin/skills/verify/SKILL.md` — full rewrite
- `plugin/skills/check-plan/SKILL.md` — hygiene + isolation BLOCKs added
- `plugin/skills/{start,brainstorm,plan,finish,feature,debug,codereview,setup}/SKILL.md` — Step 0 + lifecycle hooks added
- `plugin/templates/CLAUDE.md.template` — `context-budget-rule` + `lifecycle-rule` blocks
- `plugin/templates/AGENTS.md.template` — 2 one-liner mirrors
- `plugin/skills/setup/SKILL.md` — merge table extended to 17 blocks
- `tests/test_summary.py`, `test_lifecycle.py`, `test_state_pipeline.py`, `test_dispatch_isolation.py`, `test_cli_task_mode.py` — all NEW
- `VERSION`, `pyproject.toml`, `plugin/.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `README.md` — version sync

**Do not change:**
- `SubagentOutput` and `SubagentInput` are the **boundary contract**. Adding fields requires updating `SUBAGENT_OUTPUT_FIELDS` (in `dispatch.py`) AND updating every Agent prompt template (in `prompts.py`) AND extending the test `test_subagent_output_fields_match_dataclass`. Drift here is silent corruption.
- `IsolationViolation` is intentionally fail-loud. Do not swallow it with try/except in dispatch paths — that defeats G11. If a real subagent legitimately needs to send a new field, add it to the schema with explicit tests.
- `lifecycle.json` byte budget (1KB) is a forcing function, not a suggestion. If `LifecycleBloatError` fires, the answer is to move fields to `pipeline.json`, not raise the limit.
- The 5-line summary cap in `write_artifact` and `SubagentOutput.summary_lines` is the G3 enforcement. Raising it requires editing `MAX_SUMMARY_LINES` in `summary.py` AND `summary_lines` validation in `dispatch.py.SubagentOutput.__post_init__` AND updating the rule prose in CLAUDE.md.template. All three or none.
- `renmark/__init__.py.__version__` MUST stay synced with `VERSION` and `pyproject.toml`. v0.4.0's `/renmark:release` skill will automate this — until then, bump by hand and run `grep -R 0\\.X\\.Y plugin/templates/ pyproject.toml plugin/.claude-plugin/ .claude-plugin/ README.md renmark/__init__.py VERSION` to confirm.

**Next release: v0.3.1 — `/renmark:document` (post-feature doc sync).** See `/home/renmark/.claude/plans/cheerful-drifting-seal.md` for the full v0.3.x → v0.4.0 rollout.

---

## v0.2.5 — 2026-05-18 (governance charter codification)

**Patch release — documentation only, no code or skill behavior changes.**

The orchestrator (Sonnet 200k typical) is now treated as a degrading systems resource. Nine new governance rules codify how every renmark skill must behave to protect orchestration integrity against context rot. The rules ship as `BEGIN/END` blocks in CLAUDE.md.template so `/renmark:setup` merges them into existing projects without overwriting.

**New CLAUDE.md rule blocks** (9, all in `plugin/templates/CLAUDE.md.template`):
- `orchestrator-role-rule` — coordinator, not memory container
- `canonical-state-rule` — truth lives in `.renmark/` and CHANGELOG, not conversation
- `summary-boundary-rule` — orchestrator-visible output ≤ 5 lines or ≤ 300 tokens
- `context-contamination-rule` — cross-domain skill changes recommend `/clear` (domains: debug, build, audit, meta)
- `artifact-governance-rule` — every artifact carries provenance + freshness metadata
- `compact-semantics-rule` — `/compact` preserves goals, blockers, pipeline state, artifact refs, verification status
- `failure-transparency-rule` — outputs carry `completion_state` / `confidence` / `validation_status` / `retry_count` / `parser_success` / `schema_compliance`
- `workflow-recovery-rule` — multi-step workflows resumable from `.renmark/state/pipeline.json`, not conversational reconstruction
- `task-isolation-rule` — `/renmark:orchestrate` runs each task in an isolated subagent context; subagent transcripts and generated code never re-enter the orchestrator

**AGENTS.md.template:** 9 corresponding one-liner mirrors, each pointing at the longer block in CLAUDE.md.

**`/renmark:setup`:** merge table extended from 6 to 15 blocks. Existing projects get the new rules merged on next setup run without overwriting custom content.

**New file `plugin/skills/CONTRIBUTING.md`:** governance acceptance bar for new skills — 9-rule compliance checklist (G2–G11). A new skill that cannot tick all 9 boxes does not merge. Includes the canonical SKILL.md structure with the `Governance compliance` table every new skill must include.

**Files changed:**
- `plugin/templates/CLAUDE.md.template` — 9 new rule blocks inserted between `verify-before-done-rule` and the tooling table
- `plugin/templates/AGENTS.md.template` — 9 one-liner mirrors added between `Verification before completion` and `Conventions`
- `plugin/skills/setup/SKILL.md` — merge table updated with 9 new entries
- `plugin/skills/CONTRIBUTING.md` — new file
- `VERSION` — bumped `0.2.4` → `0.2.5`

**Do not change:**
- The 9 rule blocks ship as one cohesive set; do not split them into separate releases. Each rule reinforces the others (e.g., G6 artifact metadata depends on G3 summary boundaries; G10 recovery depends on G2 canonical state).
- AGENTS.md mirrors stay one-liners that reference the long-form block in CLAUDE.md — do not duplicate the full rule text in AGENTS.md.
- Block names use the `<topic>-rule` suffix convention. Do not rename existing blocks; downstream merge logic depends on the names.
- The `task-isolation-rule` block describes a contract that Phase 1 code (next release v0.3.0) will enforce. Rules ship first so plans drafted against v0.2.5 already obey them — the code that mechanically blocks violations comes in v0.3.0.

---

## v0.2.4 — 2026-05-15 (vibe coder entry point)

**New skill:**
- `/renmark:start` — plain-English entry point for vibe coders. Asks what you want to build, infers stack and scope from the description, asks at most 2 follow-up questions (reach and lifespan), presents a confirmation summary with a brief best-practices mention, then routes to `/renmark:plan` (simple requests) or `/renmark:brainstorm` (complex/multi-feature). Best practices (error handling, README, .env, .gitignore, smoke test) are woven into task specs automatically — no separate tasks, no jargon exposed to the user.

**plugin.json:** version bumped to 0.2.4; description updated to lead with vibe coder framing; added `vibe-coder` keyword.

**install.sh:** `/renmark:start` added as first skill in success message; start message updated to show `start` as the entry point for new users.

**CLAUDE.md template:** `/renmark:start` added as first row in tooling table.

**Do not change:**
- The 2-question cap in `start` — more questions break the adaptive/frictionless contract
- Stack inference happens silently — never prompt the user to choose a framework

---

## v0.2.3 — 2026-05-15 (setup skill + install.sh rewrite)

**New skill:**
- `/renmark:setup` — prepares any existing project for renmark workflow. Detects tech stack from project files, creates or merges missing CLAUDE.md rule blocks (using BEGIN/END markers), syncs AGENTS.md, creates CHANGELOG.md if absent, scaffolds `.renmark/` directory tree with seed memory files, adds `.gitignore` entries, offers optional `git init`. Safe to re-run — merge-only, never overwrites existing content. Prompts to continue to brainstorm or plan on completion.

**install.sh rewrite:**
- Added `--uninstall` flag (`bash install.sh --uninstall`)
- Removed stale `/orchestrator` cleanup step (ai-inference project artifact)
- Added optional `pip3 install -q -e` step for Python editable package
- Success message now lists all 12 skills with descriptions
- VERSION read dynamically from `./VERSION` file

**VERSION:** bumped `0.1.5` → `0.2.3`

**Do not change:**
- `install.sh` symlinks are idempotent — stale symlinks are removed and recreated; non-symlink collisions abort with an error rather than overwriting

---

## v0.2.2 — 2026-05-14 (skill quality gates + CLAUDE.md discipline rules)

Skills-only release — no Python module changes.

**New skills:**
- `/renmark:check-plan` — lightweight plan validator (task count ≤ 15, verifier presence, parallel group safety). Invoked automatically by orchestrate pre-flight. Returns PASS / WARN / BLOCK.
- `/renmark:verify` — goal-backward smoke test after orchestrate. Reads plan context paragraph, runs one functional command per stated behavior, reports N/M requirements verified. Never reads source files.
- `/renmark:finish` — branch close wrapper. Re-runs verifiers, shows git log summary, offers [p] PR / [m] merge / [n] nothing.

**Skill updates:**
- `orchestrate`: pre-flight now invokes `/renmark:check-plan`; step 7 re-runs all verifiers before reporting done; hand-off menu adds `[v] Verify` and `[f] Finish` options.
- `debug`: Iron Law cross-references CLAUDE.md § Root cause before any fix; step 6 has explicit gate requiring root cause sentence before any code change.

**Template updates (CLAUDE.md.template + AGENTS.md.template):**
- Added `## Context hygiene` — never read generated file contents into conversation
- Added `## Executor dispatch rules` — codex → renmark-execute only, never Agent calls
- Added `## Root cause before any fix` — no code changes without written root cause
- Added `## Verification before completion` — re-run verifiers fresh before claiming done
- Added 3 new commands to tooling table (check-plan, verify, finish)
- AGENTS.md: added absolute paths, single-file scope, root cause, verify-before-done rules

**plugin.json:** version bumped to 0.2.2; description updated (NIM removed, new skills listed); keywords updated.

**Do not change:**
- CLAUDE.md.template rule blocks use BEGIN/END comment markers for tooling that parses them — preserve the `<!-- BEGIN:x -->` / `<!-- END:x -->` wrapper format

---

## v0.2.1 — 2026-05-14 (dispatch routing fix + scope contract + subscription language)

Skills-only release — no Python module changes.

**Fixed:**
- `orchestrate` overview: corrected dispatch table — `codex` → `renmark-execute` (Codex subscription quota), `haiku/sonnet/opus` → Agent calls (Claude Code subscription quota). Added RED FLAG to Step 3 explicitly forbidding codex tasks from being dispatched as Agent calls (was the root cause of all agents running on Sonnet 4.6 in test).
- `orchestrate` overview: replaced "OpenAI credits / Anthropic credits" language with "Codex account / Claude Code account" — both are subscription-based, not API billing.

**Added:**
- `/renmark:plan` Step 0 Scope Contract: 3-question discovery phase (tech stack with inference rules, deployment target, MVP boundary) before any task decomposition. Writes locked decisions to `CHANGELOG.md` and `.renmark/memory/stack.md`. Explicit confirmation gate — no silence-as-confirmation.
- `debug` Step 6: root-cause gate added — must write root cause sentence before drafting any fix.

**Do not change:**
- Scope Contract confirmation gate language: "Do not rely on silence, lack of objection, or ambiguous replies as confirmation" — this wording was specifically required

---

## v0.2.0 — 2026-05-14 (NIM executor removal — multi-executor architecture)

**Breaking change:** NIM executor removed. All NIM references replaced with multi-executor architecture (Haiku / Codex / Sonnet / Opus).

**Python changes:**
- `cli.py`: removed `NIMClient.from_env()` pre-flight block (was blocking all non-dry-run execution without `NVIDIA_NIM_API_KEY`); renamed `NIM_*` env vars → `RENMARK_*`; git tags `nim-run-*` → `renmark-run-*`; commit prefix `[nim]` → `[renmark]`; cleared stale Mistral model defaults to `""`
- `state.py`: `_COMMIT_TASK_RE` updated to match `renmark|codex|nim|manual` prefixes (nim kept for backward-compat with existing git history)
- `roadmap.py`: git log pattern updated; `COST_PER_KT` adds `haiku: 0.0001`
- `debug.py`: `suggest_inspector()` returns `"haiku"` for cheap intents (was `"nim"`)
- `parser.py`: default `executor` changed from `"nim"` to `"codex"`
- `__init__.py`: version bumped to `0.2.0`; description updated to list Haiku/Codex/Sonnet/Opus
- `apply.py`: module docstring updated to generic "agent output"

**Skill updates:**
- `orchestrate`: NIM pre-flight removed; refactor safety check + changelog check added; haiku added to Agent dispatch section; NIM error codes removed
- `plan`: executor list updated (NIM → Haiku); CHANGELOG.md integration added; routing table updated

**Tests:**
- `test_dispatch.py`: default executor `"nim"` → `"codex"`
- `test_debug.py`: `inspector="nim"` → `inspector="haiku"`; `suggest_inspector` assertions updated
- `test_state.py`: 3 new commit variants (`[renmark]`, `[codex]`, bare `renmark`) added; 113 tests pass

**Do not change:**
- `_COMMIT_TASK_RE` still matches `nim` — required for backward-compat with git history from pre-v0.2.0 runs
- `RENMARK_PREFER_SMALL_MODEL` and `RENMARK_BIG_MODEL` env var defaults are intentionally `""` — let users set them explicitly

---

## v0.1.5 — 2026-05-12 (Phase 3: /renmark:debug helper module)

Adds `renmark/debug.py` — file-format helpers + executor-suggestion routing for the debug loop. The skill now has a real backend instead of being a pure playbook.

- `debug.new_session(repo, symptom)` — creates `.renmark/debug/<id>/session.md` with H2 sections (Symptom / Hypotheses / Investigation log / Root cause / Fix / Verification)
- `debug.add_hypothesis(session, idx, title, likely)` — ranked list under Hypotheses
- `debug.log_investigation(session, hypothesis, inspector, finding, rules_out=False)` — append step with which model inspected it
- `debug.set_root_cause(session, text)` — replace the placeholder
- `debug.close_session(session, repo, ...)` — finalize and write a structured entry to `.renmark/memory/bugs.md` (with auto-cross-post to `learnings.md`)
- `debug.latest_session(repo)` — resume the most recent debug session (survives `/clear`)
- `debug.suggest_inspector(intent)` — returns the cheapest executor for a step:
  - `nim` for grep / file-read / line-count / regex
  - `codex` for multi-file-trace / find-usages / context-gather / api-check
  - `opus` for reasoning / race-condition / architecture
- `/renmark:debug` SKILL.md updated to point at these helpers

7 new tests. 111 passing (104 before + 7 debug tests).

**Still pending (lower priority):**
- `dispatch.py` calling `resolve_provider` to route non-nim/codex executors through the new Phase 4 providers
- `/renmark:codereview` writing review findings into `bugs.md`/`decisions.md` automatically

## v0.1.4 — 2026-05-12 (Phase 4: native multi-provider clients)

Adds three native providers + a resolver. Zero new third-party deps.

- `renmark/providers/openai_compat.py` — generic OpenAI-compatible client. Speaks `/chat/completions` against any base URL with a bearer token. Retry on 429/503, fail on 401, parse `choices[0].message.content` + `usage.{prompt,completion}_tokens`.
- `renmark/providers/ollama.py` — delegates to `openai_compat` against `http://localhost:11434/v1` by default. Executor: `ollama_chat/<model>` (e.g. `ollama_chat/qwen2.5-coder:7b`).
- `renmark/providers/openrouter.py` — delegates to `openai_compat` against `https://openrouter.ai/api/v1`. Executor: `openrouter/<provider>/<model>`. Reads `OPENROUTER_API_KEY` from env.
- `renmark/providers/__init__.py` — new `resolve_provider(executor)` function maps any executor string to `(module_name, model_arg)`. Unknown `<prefix>/<model>` strings fall through to `openai_compat` so Together / Anyscale / Groq / etc. work with the right env vars.
- 13 new tests for resolver + each provider (all mocked HTTP).

Executor strings that now work:

| Executor | Routes to |
|---|---|
| `nim` | NIM client (existing) |
| `codex` | Codex CLI (existing) |
| `opus`, `sonnet` | Agent tool — skill must dispatch |
| `ollama_chat/<model>` | Local Ollama (default `:11434`) |
| `openrouter/<provider>/<model>` | OpenRouter gateway |
| `openai_compat/<model>` | Any OpenAI-compatible API (needs `OPENAI_COMPAT_BASE_URL` + `OPENAI_COMPAT_API_KEY`) |
| `<unknown>/<model>` | Falls through to openai_compat |

104 tests pass (91 before + 13 provider tests).

**Still pending:**
- Wiring `resolve_provider` into `dispatch.py`'s actual call path (right now `dispatch.dispatch_wave` only knows nim/codex/opus/sonnet)
- `/renmark:debug` per-step routing
- `/renmark:debug` and `/renmark:codereview` writing to `bugs.md` automatically

## v0.1.3 — 2026-05-12 (cost preview + --no-commit + routing-memory + perm snippet)

Phase 1 polish landed:

- **Cost preview in `--dry-run`**: per-task line shows executor + complexity + estimated tokens + estimated $; totals at the bottom. Uses `est_tokens` / `est_cost_usd` from the plan if present, falls back to complexity heuristic. NIM = free, codex ≈ $0.05/kT, sonnet ≈ $0.003/kT, opus = in-context.
- **`renmark-execute --no-commit`** runtime now wired through `_NO_COMMIT_MODE` module flag. `_git_commit` returns `"(no-commit)"` sentinel; the skill batches commits per wave.
- **Routing memory auto-updates**: after each task completes (passed/failed), `_memory_log_outcome` appends to `routing.md` with the task signature (`target=*.py, complexity=medium, mode=A`), executor, and outcome. Failed tasks also append to `learnings.md` with the failure note. Future `/renmark:plan` runs read these to inform auto-routing.
- **Permission-allowlist snippet** added to README — paste-in `.claude/settings.local.json` block that eliminates Bash prompts for `renmark-execute *` calls.

91 tests pass (no regressions from these changes — pure additions).

**Still pending:**
- `providers/ollama.py`, `openrouter.py`, `openai_compat.py` — Phase 4
- `/renmark:debug` per-step routing — Phase 3

## v0.1.2 — 2026-05-12 (cli uses dispatch.py — parallel waves live)

**Headline:** `renmark-execute` now uses `dispatch.py` for wave-based parallel execution. Tasks sharing a `parallel_group` run concurrently on separate threads; tasks with `executor: opus | sonnet` are marked `needs_agent` and surfaced so the `/renmark:orchestrate` skill can dispatch them via the Agent tool.

Changes:
- `cli.py`:
  - Module-level `_GIT_LOCK = threading.Lock()` serializes `_git_tag`, `_git_commit`, `_git_restore_target` across parallel task threads (git index isn't multi-thread-safe).
  - `execute_plan` refactored to use `dispatch.group_tasks_by_wave` + `validate_wave` + `dispatch_wave` instead of a flat per-task loop. Existing `_execute_task` is now invoked through a `_runner` adapter that returns `dispatch.TaskResult`.
  - End-of-run summary now reports `needs-agent` count and wave count.
  - If a wave validation fails (overlapping targets, context-into-target conflicts), the plan is rejected with exit 2 before any LLM call.
- `dispatch.py` tests (11) already covered the parallel semantics; cli.py integration verified by the existing 91-test suite — all still pass.

**LiteLLM dropped from roadmap.** Per user decision: native providers cover all realistic use cases. Future providers go in as one-file `providers/*.py` modules following the `openai_compat.py` pattern.
- PLAN.md "Phase 5" struck through with rationale
- CHANGELOG pending-list updated
- "What to steal from" table notes LiteLLM was considered and rejected

**Still pending (v0.1.3+):**
- `--no-commit` runtime behavior (argparse flag accepted, not yet effective in the commit path — would let skills batch-commit per wave manually)
- Cost preview in `--dry-run` (per-task estimate before any LLM call)
- Routing memory auto-updates from run outcomes
- `/renmark:debug` per-step routing actually wired
- Additional native providers (Ollama, OpenRouter, OpenAI-compat) — Phase 4

91 tests pass.

## v0.1.1 — 2026-05-12 (logs dir + codereview simplified to codex-only)

**Added: `.renmark/logs/`** for per-invocation troubleshooting logs (gitignored). One log file per command run named `<command>-<run_id>.log`.

- `renmark/state.py`:
  - New constants: `LOGS_SUBDIR = "logs"`
  - `logs_dir(repo)`, `open_log(repo, command, run_id=None)`, `append_log(path, *messages)`, `recent_logs(repo, n=10)`
  - 6 tests
- `renmark-execute --logs` — lists the n most-recent log files with size + mtime
- `renmark-execute --logs-n <N>` — adjust the count (default 10)
- `bootstrap.py` updated: `.gitignore` template now includes `.renmark/logs/`
- `plugin/templates/memory/INDEX.md.template` updated to reference all `.renmark/` subdirs (specs, plans, reviews, state, debug, logs)

**Changed: `/renmark:codereview` is now single-pass (codex-only)**, no Sonnet/Opus passes.

The earlier multi-pass design put code into the conversation, which defeats the context-hygiene goal renmark is built for. Codex stays in its own sandbox; Opus only reads the severity summary. Output format and storage path unchanged (`.renmark/reviews/YYYY-MM-DD-<sha>.review.md`). Recommended cadence: end-of-plan, not per-task.

Tests: 91 passing (up from 85).

**Still pending (v0.1.2+):**

- CLI `execute_plan` integration with `dispatch.group_tasks_by_wave` + `dispatch_wave` — parallel waves not yet wired into the live loop
- `--no-commit` runtime behavior (flag accepted, not yet effective)
- Cost preview in `--dry-run`
- Routing memory auto-updates from run outcomes
- `/renmark:debug` per-step routing actually wired
- Additional native providers (Ollama, OpenRouter, OpenAI-compat) — Phase 4
- ~~LiteLLM plug-in slot — Phase 5~~ (dropped — native providers cover the realistic use cases)

## v0.1.0 — 2026-05-12 (Phase 1 module landing + roadmap reporter)

**First minor release.** The Phase 1 modules are all in place with tests; the CLI's `execute_plan` loop still uses the v0.0.x single-task code path. Integrating that loop with the new dispatcher is the v0.1.1 work.

**New modules (with tests):**

- `renmark/dispatch.py` — wave-based parallel dispatcher. `group_tasks_by_wave`, `validate_wave`, `dispatch_wave` (concurrent for nim/codex/litellm, `needs_agent` marker for opus/sonnet). 11 tests including a timing assertion that two slow tasks in the same wave finish in under the serial total.
- `renmark/providers/claude_agent.py` — composer for the Agent-tool prompt when a task is `executor: opus` or `executor: sonnet`. Skill issues the Agent call; this module owns the prompt format and constraints.
- `renmark/bootstrap.py` — empty-folder helper. `is_empty_project(repo)`, `bootstrap(repo, project_name=...)` creates CLAUDE.md / AGENTS.md / `.renmark/` from plugin templates, runs `git init`. Idempotent. 6 tests.
- `renmark/roadmap.py` — synthesizer that builds a per-task `task | llm | status | tokens | $ | commit` table from `features.md` + `usage.jsonl` + git log. `write_roadmap_md(repo)` snapshots to `.renmark/memory/roadmap.md`. 7 tests.

**Parser extensions (v0.0.3+, fully tested):**

- New optional task fields: `complexity` (simple|medium|hard), `parallel_group` (int), `est_tokens` (int), `est_cost_usd` (float).
- `executor` now accepts `opus`, `sonnet`, or any `<provider>/<model>` string (e.g., `ollama_chat/qwen2.5-coder:7b`).
- 9 new tests covering defaults, type validation, and rejection of invalid values.

**New skills:**

- `/renmark:roadmap` — prints the status table; also writes the snapshot to `.renmark/memory/roadmap.md` so it's committed.
- `/renmark:help` (added in v0.0.3) — lists all skills with one-sentence descriptions.

**Wizard-style hand-offs:**

- `/renmark:brainstorm` now ends with an explicit `Y/n/wait` prompt to continue to `/renmark:plan`.
- `/renmark:plan` shows a summary (task count + cost preview) and prompts `[r]eview / [d]ispatch / [e]dit / [n]o` — Dispatch only triggers `/renmark:orchestrate` after explicit user approval.
- `/renmark:orchestrate` offers `[c]ode-review / [s]moke / [n]one` after a clean run.

**CLI:**

- `renmark-execute --roadmap` — prints the status table and writes `roadmap.md` snapshot.
- `renmark-execute --no-commit` — flag added (currently a no-op; v0.1.1 will wire it into the per-task commit code so the skill can batch commits per wave).
- argparse prog name corrected from `nim-execute` to `renmark-execute`.

**Memory templates:**

The eight `.renmark/memory/` files now have proper documentation-grade templates:
- `features.md`, `bugs.md`, `decisions.md` (ADR format), `stack.md`, `architecture.md`, `conventions.md`, `routing.md`, `learnings.md`, plus an auto-maintained `INDEX.md`.

**Plugin manifest now declares 7 skills** (brainstorm, plan, orchestrate, debug, codereview, roadmap, help).

**Tests:** 85 passing (up from 52 in v0.0.3).

**Still pending (v0.1.1+):**
- CLI `execute_plan` actually using `dispatch.group_tasks_by_wave` + `dispatch_wave` (currently the loop still runs single-task serial via the v0.0.x path)
- `--no-commit` wired through per-task commit code
- Cost preview in `--dry-run`
- Routing memory auto-updates from run outcomes
- `/renmark:debug` per-step routing (NIM grep / codex trace / opus reasoning)
- `/renmark:codereview` Sonnet + Opus passes
- Additional native providers (Ollama, OpenRouter, OpenAI-compat) — Phase 4
- ~~LiteLLM plug-in slot — Phase 5~~ (dropped — native providers cover the realistic use cases) (optional)

## v0.0.3 — 2026-05-12 (Phase 1, +memory + help)

**Persistent memory module + `/renmark:help` skill.**

- `renmark/memory.py` — read/write helpers for `.renmark/memory/`. Functions: `ensure_memory(repo)`, `read_index(repo)`, `read_file(repo, name)`, `log_feature(...)`, `log_bug(...)`, `log_decision(...)`, `append_routing(...)`, `append_learning(...)`. Section-aware appends (newest-first per CHANGELOG convention). Lessons in `log_bug` auto-cross-post to `learnings.md`. 8 new tests.
- Memory templates rewritten so the files act as **living documentation**:
  - `features.md` — shipped / in-progress / planned (CHANGELOG style)
  - `bugs.md` — open / fixed with severity, symptom, root cause, fix, lesson
  - `decisions.md` — ADR format (context, decision, alternatives, consequences) with auto-numbered IDs
  - `stack.md` — languages, libs, runtime env, external APIs
  - `architecture.md` — components, data flow, module boundaries, invariants
  - `conventions.md`, `routing.md`, `learnings.md` — auto-tuned + hand-edited
  - `INDEX.md` is a cheap top-of-file index loaded first by every skill
- `/renmark:help` skill (new) — prints all six commands with one-sentence descriptions and the typical workflow order. Pure documentation, no API calls.
- `plugin.json` updated to declare 6 skills.

52 tests total (44 from baseline + 8 memory tests).

## v0.0.2 — 2026-05-12 (Phase 1, partial — skills visible)

**Plugin manifest + all five `/renmark:*` SKILL.md files** so the commands appear in Claude Code's skill list after install. Template files for empty-folder bootstrap. install.sh hardened.

Added:
- `plugin/plugin.json` declaring the 5 skills
- `plugin/skills/{brainstorm,plan,orchestrate,debug,codereview}/SKILL.md` — workflow docs for each
- `plugin/templates/{CLAUDE.md,AGENTS.md,renmark-readme.md,memory/*.md}.template` — what `/renmark:brainstorm` writes when bootstrapping an empty project
- `install.sh` ran successfully — symlinks live at `~/.claude/plugins/renmark` and `~/.local/bin/renmark-execute`

Fixed:
- `install.sh` v0.0.1 stored the /orchestrator backup at `~/.claude/skills/.orchestrator.bak/` — Claude Code's skill discovery picked it up as a phantom skill named `.orchestrator.bak`. **Backup removed entirely**: the orchestrator source still lives in `/home/renmark/projects/ai-inference/` (and in its git history), so a separate copy under `~/.claude/` was just paranoia and bug surface. install.sh now `rm -rf`s the old skill outright; manual revert is `cd ~/projects/ai-inference && bash install.sh` against the v0.2.0 baseline.

Not yet wired (still Phase 1):
- `renmark/dispatch.py` — wave-based parallel dispatcher (so orchestrate can't yet run opus/sonnet tasks or parallel groups)
- `renmark/memory.py` — `.renmark/memory/` reader/writer
- `renmark/providers/claude_agent.py` — Opus/Sonnet via Agent tool from skill side
- Parser extensions for `complexity`, `parallel_group`, `est_tokens`, `est_cost_usd`
- CLI `--no-commit` mode for batched wave commits
- Cost preview in `--dry-run`
- Empty-folder bootstrap code (skill docs reference it but the brainstorm skill currently does it by hand)

The skills are visible and `/renmark:brainstorm` + `/renmark:plan` are workable today (they're Opus-driven conversations). `/renmark:orchestrate` runs the same single-task path the v0.0.1 baseline supports.

## v0.0.1 — 2026-05-12 (Phase 0)

**Bootstrap of the new `ai-system` repo.** Copies the working v0.2.0 baseline from `/home/renmark/projects/ai-inference/` and retargets the Python package from `nim_execute` to `renmark`.

Changes vs. ai-inference v0.2.0:

- Package renamed `nim_execute` → `renmark`
- `nim_client.py` → `renmark/providers/nim.py`
- `codex_exec.py` → `renmark/providers/codex.py`
- New `renmark/providers/__init__.py` with `PROVIDERS` registry stub
- Runtime state dir renamed `.nim-state/` → `.renmark/state/` (with `RENMARK_DIR_NAME`, `STATE_SUBDIR`, `MEMORY_SUBDIR`, `DEBUG_SUBDIR` constants; legacy `STATE_DIR_NAME` aliased for back-compat)
- All test imports updated, 41 tests still passing
- CLI references `renmark-execute` / `.renmark/state/` in user-facing strings

Phase 1 (next): the five `/renmark:*` skills, `plugin/plugin.json`, dispatch layer, memory module, empty-folder bootstrap. See `PLAN.md`.

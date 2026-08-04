---
artifact_type: rethink-modularity-assessment
schema_version: 1
created_at: 2026-08-03T00:00:00Z
source_sha: c6741856f7603aac3e01f324fbaa4b7e6478155e
related_plan: null
generator: renmark:researcher
stale_after: null
dependency_refs: [".renmark/rethink/renmark-architecture/survey.md"]
---

# Modularity, scalability, maintainability assessment — renmark (Stage 5 of /renmark:rethink)

Scope: `renmark/` (73 `.py` files) + the `renmark/` <-> `plugin/skills/*` boundary.
Method: direct reads + `Grep` over imports/defs (not a full AST/pydeps traversal —
noted as such where it matters).

## 1. Domain/service boundaries — current groupings

- **CLI/orchestration root**: `renmark/cli/_engine.py` (1698 lines, `main()` +
  `execute_plan()` + ~40 module functions), `renmark/cli/commands.py`,
  `renmark/cli/_codex_runner.py`. This is the de facto integration root —
  imports `state`, `ledger`, `parser`, `providers.codex`, `verifier`,
  `task_tracking`, `agency`, `delivery_state`, `hosts`, `mode`, `program`,
  `state.pipeline`, `summary`, `skillmeta` directly (confirmed by direct read
  of its import block, lines 1-68).
- **Workflow state machine**: `renmark/lifecycle.py` (1752 lines, ~50 top-level
  defs/classes) — stage transitions, gate logic, `next_steps`, `skill_preamble`,
  human-review halting, artifact validation, legacy-delivery reconciliation,
  mode/agency/headless note composition. This module alone owns at least 6
  distinguishable responsibilities (stage state I/O, next-steps computation,
  preamble/context-budget orchestration, human-review halting, artifact
  validation, legacy-delivery drift reconciliation).
- **Dispatch/parallelism**: `renmark/dispatch.py` (1063 lines) — wave scheduling,
  `AgentDispatch`, `SubagentOutput` field/enum constants, scope enforcement.
  Confirmed: imports only `fast_path`, `parser`, `providers.claude_agent` — a
  genuinely low-coupling module, but it doubles as the canonical *definition*
  site for `SubagentOutput` shape constants that `schemas.py` then imports back
  (see §2).
- **Program/staged execution**: `renmark/program.py` (846 lines),
  `program_driver.py`, `recurrence.py`, `scan.py`, `summary.py` — the
  rethink/roadmap staged-program model, a second "what happens next" engine
  parallel to `dispatch.py`'s wave engine and `_engine.py`'s plan-task engine.
  Three independent sequencing engines exist in this codebase (plan tasks via
  `_engine.py`, waves via `dispatch.py`, program stages via
  `program_driver.py`) — not confirmed duplicated logic (would need line-level
  diff), but a real cohesion risk: a fourth "what's next" bug class shows up
  three separate times in CHANGELOG per the stage-1 survey.
- **Validation**: `renmark/schemas.py` (800 lines) — structural JSON-shape
  checks for `lifecycle.json`, `pipeline.json`, `SubagentOutput`,
  `ArtifactMetadata`, `limits.json`, analytics/report/pause/event shapes.
- **Delivery/milestone bookkeeping**: `renmark/delivery_state.py` (716 lines) —
  `delivery.json` aggregate: milestones, work packages, provenance events, byte
  budget. Confirmed standalone leaf (imports nothing from `renmark.*`).
- **Config/host/routing leaves** (genuinely decoupled, good examples):
  `renmark/config.py`, `renmark/hosts.py`, `renmark/cost.py` — each imports
  zero other `renmark.*` modules (confirmed by direct grep). `renmark/skillmeta.py`
  is a frozen, stdlib-only, dependency-free per-skill metadata registry — the
  single best-isolated module in the codebase.
- **`renmark/state/`**: already-modernized package (per stage-1 survey) —
  `_core.py`/`usage.py`/`pause.py`/`pipeline.py`/`logs.py`/`commits.py`/`skills.py`,
  re-exported through `state/__init__.py`. This is the proven template for
  splitting `_engine.py` and `lifecycle.py`.

## 2. Coupling and dependency direction

**Confirmed: `schemas.py` inversion is real and specific**, not just directional
color. `schemas.py` (lines 38-58) imports:
- `CONTRACT_VERSION`, `LEGACY_REF_CAP`, `PROVENANCE_EVENT_CAP`,
  `SUMMARY_TEXT_LIMIT`, `WORK_PACKAGE_CAP`, `stable_milestone_id`,
  `stable_work_package_id`, `SCHEMA_VERSION` **from `renmark.delivery_state`**
- `SUBAGENT_OUTPUT_COMPLETION_STATES`, `SUBAGENT_OUTPUT_CONFIDENCE_VALUES`,
  `SUBAGENT_OUTPUT_FIELDS`, `SUBAGENT_OUTPUT_STATUS_VALUES` **from
  `renmark.dispatch`**
- `STAGES` **from `renmark.lifecycle`**

A "validate the shape of X" module should be the module domain owners import
for shape constants — instead `schemas.py` (positioned as a foundational,
zero-dependency utility per its own docstring: "Zero external dependencies")
depends *upward* on three domain modules to source the very constants it
validates against. This is a real inversion: it means `delivery_state.py`,
`dispatch.py`, and `lifecycle.py` cannot be tested/modified independently of
`schemas.py`'s import surface, and a genuinely standalone validator module is
not actually standalone.

**No hard circular import found** in the modules read this pass
(`schemas.py`, `dispatch.py`, `lifecycle.py`, `cli/_engine.py`, `cost.py`,
`hosts.py`, `config.py`, `skillmeta.py`, `subagent_profiles.py`,
`codex_routing.py`) — consistent with stage-1's spot-check finding. This
remains a spot-check (11-14 of 73 modules read import-line-by-import-line),
not an exhaustive graph traversal.

**`lifecycle.py` -> `skillmeta.py`** is a correctly-directed dependency
(domain module consumes a lower-level frozen registry) — a positive
counter-example showing the codebase knows how to do this right elsewhere.

## 3. Oversized modules — quantified

| Module | Lines | Top-level defs/classes | Notes |
|---|---|---|---|
| `lifecycle.py` | 1752 | ~50 | Largest module; docstring itself enumerates 6+ concerns (see §1) |
| `cli/_engine.py` | 1698 | ~40 | `execute_plan()` alone spans lines 602-996 (~395 lines) — the single largest function found this pass; `main()` spans 1461-end |
| `dispatch.py` | 1063 | not fully enumerated this pass | Lower coupling than the other two; size is more defensible (single cohesive "wave dispatch" concern) |
| `program.py` | 846 | — | Third parallel "what's next" engine (see §1) |
| `schemas.py` | 800 | — | Size is reasonable for its content (9 CLI subcommands x validator each); the *coupling* is the problem, not the size |
| `delivery_state.py` | 716 | — | Repeated same-shape byte-budget bugs per stage-1 CHANGELOG evidence — a fragility signal independent of size |

`execute_plan()` (394 lines) and `main()` in `_engine.py` are the two largest
single functions found — both well past a reasonable single-function
comprehension budget and both doing multiple things (arg dispatch, wave loop,
pause/resume, ledger emission, delivery-state writes) inline rather than via
extracted helpers, despite `_engine.py` already having ~15 small `_dispatch_*`
prefixed helper functions that show the extraction pattern is known and used
inconsistently (some flags get helper extraction, the main wave loop does not).

## 4. Data ownership and transaction boundaries

Confirmed (re-verified from stage-1, code-level not just docstring):
- `lifecycle.py` only touches `_lifecycle_path()` = `.renmark/state/lifecycle.json`,
  enforces `LifecycleBloatError` at 1024 bytes (`LIFECYCLE_JSON_BYTE_BUDGET`,
  line 265) — a real, code-enforced budget, not aspirational.
- `pipeline.json` lives entirely in `renmark/state/pipeline.py`
  (`PipelineState`), a separate module `lifecycle.py` does not import.
- `delivery_state.py` owns `delivery.json` / `delivery-archive.json`, is a
  standalone leaf module (imports nothing from `renmark.*`).

**Enforcement is code-level for the write path (each store has exactly one
owning module with a private path helper) but the *read/reconciliation* path
is where the boundary leaks**: `lifecycle.py`'s `read_legacy_delivery_summary`,
`_project_workflow_delivery`, `_workflow_drift_notes` (lines 1463-1646) read
`Program`/delivery state directly to reconcile against lifecycle stage — this
is the acknowledged repeat-offender area from stage-1's CHANGELOG evidence
(3+ separate staleness bugs across R-0.1/R-0.2/R-0.3). The three stores are
write-isolated but cross-read without a formal reconciliation contract/module
— each store's owning module independently decides how to interpret the
others' state, rather than a dedicated `reconciliation.py` owning that
cross-store read logic once.

## 5. Public API / internal contract boundary (`renmark/` <-> `plugin/skills/*`)

The boundary is real but implicit and only partly typed:
- `plugin/skills/*/SKILL.md` (markdown, model-invoked) calls into Python
  exclusively via `renmark-execute <subcommand>` (Bash tool), i.e. the CLI
  surface in `cli/commands.py` / `cli/_engine.py`'s `argparse` definitions
  **is** the contract — there is no separate importable "public API" module;
  the contract is "whatever argparse subcommands exist and whatever stdout/
  JSON they print."
- `renmark/skillmeta.py` is the one place this boundary is genuinely
  formalized: a frozen `SKILLS: dict[str, SkillMeta]` registry that both
  `lifecycle.py` (`DOMAIN_BY_SKILL`) and (per its own docstring) template
  scaffolding/lint/doc-gen consumers read, rather than re-grepping SKILL.md
  prose at each call site.
- **Brittleness**: nothing enforces that a new/renamed `plugin/skills/<name>/`
  directory has a corresponding `skillmeta.SKILLS["<name>"]` entry short of a
  lint pass (`renmark/plan_lint.py`/`skillgen.py`, not verified this pass to
  gate on skillmeta completeness specifically) — an unregistered skill likely
  silently falls back to `domain_of`'s default `"build"` rather than failing
  loudly (confirmed in code: `domain_of` returns `"build"` for unknown skills,
  never raises, lines 843-854). This is a deliberate "never raises" contract
  per the module's own docstring, but it means a missing registry entry fails
  silently rather than at skill-authoring time.

## 6. Provider/model-tier routing replaceability

**Routing logic is scattered, not centralized.** Grepping for
routing/tier/executor signals across `renmark/` surfaces 12 files touching
this concern: `cli/_engine.py`, `plan_lint.py`, `subagent_profiles.py`,
`dispatch.py`, `providers/claude_agent.py`, `behavior.py`, `cost.py`,
`parser.py`, `work_packages.py`, `codex_routing.py`, `capabilities.py`,
`providers/__init__.py`. `cost.py` (`requires_escalation`) is the closest
thing to a routing-policy authority (per `CLAUDE.md`'s own citation:
"`plugin/skills/.shared/model-routing.md` + `renmark/cost.py::requires_escalation`")
but is standalone (imports nothing from `renmark.*`), meaning the *policy*
of "which tier is cheapest-capable" lives in `cost.py` while the *mechanism*
of actually invoking a tier is split across `providers/claude_agent.py`
(Claude Agent SDK calls), `providers/codex.py` (Codex subprocess), and
`codex_routing.py` (routing decisions specific to Codex escalation), with
`_engine.py`'s `_choose_model()` (line 186) as yet another decision point.
**Adding a new executor tier today requires touching at minimum**: a new
`providers/<tier>.py` adapter, a `_choose_model()` branch in `_engine.py`,
possibly a `cost.py` escalation-threshold entry, and a `subagent_profiles.py`
role mapping — four+ files, no single "register a tier" seam.

## 7. Configuration/environment/host boundaries

This is a genuine strength, confirmed by code: `renmark/config.py` and
`renmark/hosts.py` are both standalone leaves (zero `renmark.*` imports).
`hosts.capabilities_for(HostKind)` is the single call site consumers use to
resolve claude-vs-codex capability differences (confirmed used by
`lifecycle.skill_preamble`, per CLAUDE.md's own citations and the read of
`skill_preamble`'s body at line 977). Host detection and config are already
centralized — no changes needed here.

## 8. Test isolation / testability

- `lifecycle.py` (1752 lines) has exactly one corresponding test file,
  `tests/test_lifecycle.py` — a single test file for a module with ~50
  top-level defs across 6+ distinguishable concerns is a coarse-grained
  mapping; whether that file's tests are unit-focused per-function or
  integration-style end-to-end was not read this pass (would require opening
  the test file — out of scope for the assessment's read budget) but the
  1:1 module-to-test-file ratio itself, at this size/concern-count, is a
  signal that refactor-safety net granularity is likely lower than the raw
  "113 test files, near 1:1 coverage" stat from stage-1 implies.
- `cli/_engine.py` (1698 lines) has **two** test files
  (`test_engine_resume_crosscheck.py`, `test_engine_budget_and_rollback.py`)
  — better than lifecycle's 1:1 but both filenames suggest scenario/regression
  coverage (resume-crosscheck, budget-and-rollback) rather than exhaustive
  per-function unit coverage of the ~40 module functions.
- **Implication for refactor safety**: splitting `_engine.py`/`lifecycle.py`
  along the `state/` package's proven pattern is lower-risk for the parts
  covered by named scenario tests, higher-risk for the ~30+ functions in each
  module not obviously named in any test file title — a splitting plan should
  inventory per-function test coverage before moving code, not assume the
  existing test suite is a complete safety net for arbitrary line moves.

## 9. Security/permission boundaries

Not deeply re-verified this pass beyond stage-1's survey (§5 there: heavy
`subprocess.run` git/bash dependence, `verifier.py`'s `bash -c` assumption).
No new finding beyond confirming `CLAUDE.md`'s own documented permission
contract (`inspector` role read-only, no Write/Edit) is enforced at the
subagent-profile/dispatch-role level (`renmark/subagent_profiles.py`) rather
than at a Python-level sandboxed execution boundary — permission enforcement
for what a dispatched agent can touch is a *convention carried by the dispatch
role contract*, not something `renmark/`'s Python layer can technically block
(the Python runtime does not sandbox filesystem access per role). This is an
inherent limitation of a CLI-orchestrated-agents architecture, not something
the target blueprint below tries to fix.

## 10. Adding a new `plugin/skills/<name>/SKILL.md` — actual current path

Traced end-to-end:
1. Create `plugin/skills/<name>/SKILL.md` (auto-discovered — `plugin/.claude-plugin/plugin.json`
   only declares `"skills"` as a category, not a per-skill manifest list —
   confirmed by reading `plugin.json`, no per-skill registration array found).
2. Create `plugin/commands/<name>.md` (the `/renmark:<name>` slash-command
   entry point) — this one IS a discrete per-file artifact that must exist,
   though nothing enforces name-parity with the skill directory beyond
   convention.
3. Add an entry to `renmark/skillmeta.py`'s `SKILLS` dict (domain,
   `next_steps_class`, `cites`, `has_handoff`, `disable_model_invocation`) —
   **not enforced**; a missing entry silently defaults (`domain_of` returns
   `"build"`, never raises).
4. If the skill needs a CLI subcommand, add an `argparse` subparser + handler
   in `cli/commands.py`/`cli/_engine.py`.
5. If the skill introduces a new lifecycle stage, extend `lifecycle.STAGES`
   and any stage-order-dependent logic in `next_recommended`/`_resolve_next`.

**This is a reasonably small, well-documented path (5 touch points, mostly
additive) but has exactly one silent-failure seam (step 3) and one
loosely-coupled-by-convention seam (step 2's name parity with step 1)** — not
a blocking scalability problem at 31 skills, but the registry-completion gap
is worth closing with a lint check (register-on-discover or fail-loud) before
the skill count grows meaningfully further.

## 11. Current-state module/dependency map (text diagram)

```
                        plugin/skills/*/SKILL.md  (model-invoked, markdown)
                                   |  (Bash: renmark-execute <subcmd>)
                                   v
                        renmark/cli/_engine.py  (1698L, integration root)
                         |     |      |      |        |
                         v     v      v      v        v
                    state/  dispatch  ledger parser  providers/{codex,claude_agent}
                     |         |                          |
                     |         v                          v
                     |    fast_path, parser          codex_routing
                     |
                     +--> agency --> delivery_state (leaf)
                     +--> program --> program_driver --> recurrence --> scan
                     +--> hosts (leaf)  +--> mode (leaf-ish)
                     +--> summary
                     +--> commands.py --> {analytics, heartbeat, logs, roadmap,
                                            scan, task, task_brief, usage}

        lifecycle.py (1752L) --> skillmeta.py (leaf, frozen registry)
              ^  (imported by cli/_engine.py, agency.py, program_driver.py, ...)
              |
        schemas.py (800L, "should be a leaf") --UP--> delivery_state.py
                                                --UP--> dispatch.py
                                                --UP--> lifecycle.py
              ^ INVERTED: validator depends on the domain modules it validates

        Genuine leaves (0 renmark.* imports, confirmed): config.py, hosts.py,
        cost.py, skillmeta.py, delivery_state.py
```

## 12. Proposed target modular architecture

Constraint respected throughout: no behavior/UX change, no distributed-system
patterns, no change to REQ-30 orchestration efficiency guarantees — this is a
same-process module-boundary reshuffle, following the `renmark/state/`
precedent already proven in this codebase.

**Change 1 — Fix the `schemas.py` inversion (smallest, highest-value fix).**
Extract the shared constants `schemas.py` currently imports *from*
`delivery_state.py`/`dispatch.py`/`lifecycle.py` into a new leaf module,
`renmark/contracts.py` (or fold into existing `renmark/schemas.py` itself as
literal constants it owns, with `delivery_state.py`/`dispatch.py`/`lifecycle.py`
importing them back FROM `schemas.py`/`contracts.py` instead of the reverse).
Either direction restores "validator is a leaf" without touching call-site
behavior — `CONTRACT_VERSION`, `SUBAGENT_OUTPUT_FIELDS`, `STAGES`, etc. are
already frozen constants; only the import direction changes. Zero runtime
behavior change, pure dependency-direction fix.

**Change 2 — Split `cli/_engine.py` along its already-visible seams**, mirroring
`renmark/state/`'s pattern:
- `cli/_dispatch_flags.py` — the 5 existing `_dispatch_*` flag-handler
  functions (already isolated, just physically relocate)
- `cli/_run_lifecycle.py` — `_setup_resume_state`, `_begin_run_state`,
  `_complete_clean_run`, `_handle_run_exit`, `_print_run_summary` (the
  run-bookkeeping cluster)
- `cli/_wave_loop.py` — the core of `execute_plan()`'s 394-line body,
  extracted into named helper functions first, then relocated
- `cli/_engine.py` keeps `main()`, `execute_plan()` (now a thin orchestrating
  shell calling into the above), and re-exports everything through
  `cli/__init__.py` for backward-compatible imports (same pattern
  `state/__init__.py` uses) — no call site outside `cli/` needs to change.

**Change 3 — Split `lifecycle.py`** into cohesive sub-concerns under a new
`renmark/lifecycle/` package (mirroring `state/`):
- `lifecycle/stage.py` — `LifecycleState`, `read_lifecycle`/`write_lifecycle`/
  `clear_lifecycle`, `STAGES`, `begin_feature`, byte-budget enforcement
- `lifecycle/next_steps.py` — `NextSteps`, `next_steps`, `next_recommended`,
  `_resolve_next`, `_gates_not_run`
- `lifecycle/preamble.py` — `skill_preamble`, `preamble_tier`,
  `persist_compact_checkpoint`, `milestone_context_checkpoint`, the
  `_with_*_note` composers
- `lifecycle/reconciliation.py` — `read_legacy_delivery_summary`,
  `_project_workflow_delivery`, `_workflow_drift_notes`,
  `milestone_signoff_readiness` and friends — **this isolates exactly the
  code that owns the repeat-offender cross-store staleness bug class (§4)**
  into one file, making the next staleness fix touch one focused module
  instead of a 1752-line one.
- `lifecycle/__init__.py` re-exports the full existing public surface
  (`domain_of`, `skill_preamble`, `next_steps`, etc.) so every existing
  `from renmark.lifecycle import X` / `from renmark import lifecycle;
  lifecycle.X` call site keeps working unchanged.

**Change 4 — Consolidate model-tier routing behind one seam.** Do not merge
`providers/claude_agent.py` and `providers/codex.py` (they are legitimately
different transports); instead give `cost.py` (already the policy authority
per `CLAUDE.md`'s own citation) a single `resolve_executor(task) -> Executor`
function that `_engine.py`'s `_choose_model()`, `codex_routing.py`, and
`subagent_profiles.py`'s role-to-tier mapping all call through, rather than
each independently deciding tier eligibility. Adding a new tier then means:
one `providers/<tier>.py` adapter + one branch in `cost.resolve_executor` —
down from four+ uncoordinated touch points today.

**Change 5 — Close the skillmeta silent-default gap.** Add a deterministic
lint check (extending the existing `plan_lint.py`/`skillgen.py` family, no
new module needed) that fails when a `plugin/skills/<name>/` directory has no
matching `skillmeta.SKILLS["<name>"]` entry, instead of silently defaulting
`domain_of` to `"build"`. This is a lint addition, not a runtime behavior
change — `domain_of`'s runtime "never raises" contract is preserved; only
the pre-merge lint gate becomes stricter, consistent with `CLAUDE.md`'s
"deterministic-first" convention already in place for other structural checks.

**Deliberately NOT proposed**: splitting `dispatch.py` (already the most
cohesive of the large modules, low coupling, single clear concern) or
`program.py`/`program_driver.py`/`delivery_state.py` (sized reasonably for
their scope; delivery_state's bugs were budget/logic bugs, not
size/cohesion bugs). Not proposing a formal plugin-manifest/registry system
beyond the lint check in Change 5 — the current convention-based skill
discovery works at 31 skills and a heavier registration mechanism would add
process weight without a demonstrated scaling problem (avoids the
"speculative microservices" trap at the plugin-discovery layer, too).

## 13. Summary for the target blueprint (stage 7)

Five bounded, additive-first, backward-compatible-import changes: (1) reverse
`schemas.py`'s dependency direction, (2) split `cli/_engine.py` into a
`cli/` sub-cluster, (3) split `lifecycle.py` into a `lifecycle/` package
isolating the reconciliation hotspot, (4) centralize executor-tier resolution
behind `cost.resolve_executor`, (5) add a skillmeta-completeness lint gate.
All five preserve every existing import path via `__init__.py` re-exports
(the `state/` package precedent), require no plugin/skills/*.md prose
changes, and do not touch REQ-30's measured orchestration-efficiency
guarantees — they only make the two largest, least-testable modules smaller
and the one inverted dependency correctly directed.

---

## Discovery Direction Gate — decision (2026-08-03)

**Chosen direction:** Structural-only modernization. Split `_engine.py`/
`lifecycle.py` into sub-packages mirroring the `renmark/state/` pattern,
reverse the `schemas.py` inversion, centralize executor routing behind one
seam — all behavior-preserving (exempt from REQ-30 per the 2026-08-03
exception decision in `intake.md`). First roadmap release measures the
REQ-30 baseline and confirms dev gates green. Git-worktree-per-agent
isolation (Stage 4 parity gap) is explicitly deferred as a future
Unknown/spike — NOT in scope for this transformation.

Owner selected this over "structural + worktree-isolation parity" and
"minimal/deferred" via AskUserQuestion.

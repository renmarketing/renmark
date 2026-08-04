---
artifact_type: rethink-classification
schema_version: 1
created_at: 2026-08-03T00:00:00Z
source_sha: c6741856f7603aac3e01f324fbaa4b7e6478155e
related_plan: null
generator: renmark:researcher
stale_after: null
dependency_refs: ["survey.md","baseline.md","prd-acceptance-map.md","external-benchmark.md","modularity-assessment.md","intake.md"]
---

# Evidence-based classification — Stage 6 of `/renmark:rethink` (renmark-architecture)

Scope: STRUCTURAL-ONLY modernization per Owner's Discovery Direction Gate
decision (`modularity-assessment.md` bottom) and the exception check-in in
`intake.md` (behavior-preserving split of `_engine.py`/`lifecycle.py` is
EXEMPT from REQ-30's UPDATE gate; anything touching actual routing/dispatch
POLICY is not). Classes: **Keep / Improve / Replace / Remove /
Unknown-needs-a-spike**. Every entry cites survey/baseline (internal),
PRD-acceptance impact (Stage 3), external evidence where relevant (Stage 4),
and modularity impact (Stage 5).

---

## 1. `renmark/cli/_engine.py` — **Improve**

Split into a `cli/` sub-cluster (`cli/_dispatch_flags.py`,
`cli/_run_lifecycle.py`, `cli/_wave_loop.py`), keeping `main()`/`execute_plan()`
as thin orchestrating shells, re-exported via `cli/__init__.py` — same public
API, same call sites.

- **Survey (Stage 1)**: 1698 lines, named (with `lifecycle.py`) as one of "the
  two clearest modernize-without-changing-behavior targets"; de facto
  integration root importing nearly every domain module.
- **PRD-acceptance impact (Stage 3)**: sits on REQ-30's tripwire (`_engine.py`
  *implements* dispatch policy) — resolved by `intake.md`'s exception
  check-in: a behavior-preserving structural extraction (same public
  functions/imports/call sites, before/after test-suite parity) is EXEMPT
  from the UPDATE gate. Any change that alters actual dispatch decisions is
  NOT exempt and stays out of this pass.
- **External evidence (Stage 4)**: F1/F2 — LangGraph/Claude Code's own Task
  system both formalize "state machine + isolated dispatch" as first-class
  library concerns; renmark's hand-rolled equivalent concentrated in one
  1698-line file is the un-modularized version of a now-standard pattern.
- **Modularity impact (Stage 5)**: `execute_plan()` alone is ~395 lines
  (largest single function found); `_engine.py` already has ~15
  `_dispatch_*`-prefixed helpers showing the extraction pattern is known but
  applied inconsistently. Proposed target (§12 Change 2) mirrors the
  `renmark/state/` precedent exactly.

## 2. `renmark/lifecycle.py` — **Improve**

Split into a `lifecycle/` package (`stage.py`, `next_steps.py`, `preamble.py`,
`reconciliation.py`), re-exported via `lifecycle/__init__.py` for full
backward-compatible import surface.

- **Survey (Stage 1)**: 1752 lines, largest module in the repo; module
  docstring itself enumerates 6+ distinguishable concerns.
- **PRD-acceptance impact (Stage 3)**: same REQ-30 exemption as `_engine.py`
  per `intake.md`'s exception check-in — structural split only, no gate/stage/
  UX wording change (protects REQ-1/REQ-3/REQ-4 etc., all "met/protect" rows).
- **External evidence (Stage 4)**: F7 (`python-statemachine`) offered as a
  possible library replacement for the hand-rolled stage-order logic, but
  flagged Unknown (U1, serialization-fit unverified) — **not** adopted in
  this pass; the chosen direction is the internal `state/`-style split only,
  consistent with the "stdlib-only core" non-goal (Stage 3 non-goals table).
- **Modularity impact (Stage 5)**: baseline's top risk #1 (`skill_preamble`'s
  dense, order-dependent host-branching) and top risk #2
  (`LIFECYCLE_JSON_BYTE_BUDGET` invariant + read-modify-write growth risk,
  same bug class as the real `delivery_state.py` byte-budget crash) both
  live inside this module — the split explicitly isolates the
  cross-store reconciliation hotspot (§4/§12 Change 3) that caused 3+
  CHANGELOG staleness bugs (R-0.1/R-0.2/R-0.3), reducing blast radius of the
  next fix to one focused file instead of 1752 lines. Test-isolation note
  (§8): only one test file (`test_lifecycle.py`) maps to ~50 top-level defs —
  split plan must inventory per-function coverage before moving code, not
  assume full safety net.

## 3. `renmark/schemas.py` inverted dependency — **Improve**

Reverse the direction: extract/own the shared constants (`CONTRACT_VERSION`,
`SUBAGENT_OUTPUT_FIELDS`, `STAGES`, etc.) so `delivery_state.py`/`dispatch.py`/
`lifecycle.py` import them FROM `schemas.py` (or a new leaf `contracts.py`),
not the reverse. Zero runtime behavior change — pure import-direction fix.

- **Survey (Stage 1)**: flagged as "worth flagging for the target blueprint" —
  a would-be low-level utility module depends upward on `delivery_state.py`,
  `dispatch.py`, `lifecycle.py`; no hard circular import found (spot-check,
  not exhaustive).
- **PRD-acceptance impact (Stage 3)**: flag 6 — "deferrable spec debt," not a
  compliance failure, but material input to Stage 5's dependency-direction
  analysis; correctly in-scope for this structural-only pass since it's a
  pure module-boundary fix with no behavior change.
- **External evidence (Stage 4)**: explicitly out of scope for Stage 4's
  agent-orchestration-domain research (recommendation 6) — deferred to
  Stage 1/2/5 internal analysis, standard dependency-inversion practice.
- **Modularity impact (Stage 5)**: confirmed real and specific (§2, lines
  38-58 of `schemas.py`) — `schemas.py`'s own docstring claims "zero external
  dependencies" while importing from three domain modules; this means those
  three modules cannot be tested/modified independently of `schemas.py`'s
  import surface. Smallest, highest-value fix per §12 Change 1.

## 4. Scattered model-tier/executor routing (12 files) — **Improve**

Centralize behind one seam: `cost.py` gets a single
`resolve_executor(task) -> Executor` that `_engine.py`'s `_choose_model()`,
`codex_routing.py`, and `subagent_profiles.py`'s role-to-tier mapping all call
through — consolidating touch points from 4+ to 2 (one `providers/<tier>.py`
adapter + one branch in `cost.resolve_executor`) for a new tier. **No policy
change** — cheapest-capable-model selection outcomes stay identical; only the
call graph changes.

Files touching this concern (per Stage 5's grep): `cli/_engine.py`,
`plan_lint.py`, `subagent_profiles.py`, `dispatch.py`,
`providers/claude_agent.py`, `behavior.py`, `cost.py`, `parser.py`,
`work_packages.py`, `codex_routing.py`, `capabilities.py`,
`providers/__init__.py`.

- **Survey (Stage 1)**: not directly named in Stage 1 (surfaced in Stage 5's
  deeper grep), but consistent with Stage 1's "three modules each with their
  own notion of what happens next" duplication-risk flag.
- **PRD-acceptance impact (Stage 3)**: REQ-2 ("cost-routed executor set incl.
  Fable") is `unverified` (no live pytest this session) but target behavior
  is explicitly "unchanged — protect." Consolidating the *seam* without
  changing routing *outcomes* keeps REQ-2/REQ-30 compliance intact; changing
  actual tier-eligibility logic would NOT be exempt and is out of this pass.
- **External evidence (Stage 4)**: F3 — industry-wide convergence on
  complexity-tiering routing layers (LiteLLM, RouteLLM, Portkey) as a single
  seam/gateway pattern, validating that a `resolve_executor` consolidation
  point is the standard shape for this concern, not a renmark-specific
  invention.
- **Modularity impact (Stage 5)**: §6 — "adding a new executor tier today
  requires touching at minimum" 4+ files with no single "register a tier"
  seam; `cost.py` is already the policy authority (per CLAUDE.md's own
  citation) but the *mechanism* is split across 3+ other files plus
  `_engine.py`'s `_choose_model()`. §12 Change 4 is the proposed fix.

**Note on scope**: this item is model-tier/executor routing specifically
(which tier handles a task). It is a distinct concern from item 5's
skillmeta-completeness lint gate (which skill-registry entries exist) —
the two touch different files (`cost.py`/`codex_routing.py`/
`subagent_profiles.py`'s role-tier mapping vs. `plan_lint.py`/
`skillmeta.py`) and are backed by different Stage 5 sections (§6 here vs.
§5 for item 5). They are counted as two separate Improve items, not one.

## 5. Skillmeta-completeness lint gate — **Improve** (optional/stretch)

Add a deterministic lint check (extending the existing
`plan_lint.py`/`skillgen.py` family, no new module) that fails when a
`plugin/skills/<name>/` directory has no matching `skillmeta.SKILLS["<name>"]`
entry, instead of silently letting `lifecycle.domain_of` default unknown
skills to `"build"`. Confirmed in code: `renmark/skillmeta.py`'s `get()`
never raises (returns `None` for an unregistered skill by design), and
`plan_lint.py`'s existing checks (including its Check 12, which governs
opus/fable escalation-signal linting) do not currently gate on skillmeta
registry completeness — this is a genuinely new, additive lint rule, not an
extension of an existing routing check. Lint-only; zero runtime-behavior
change (`domain_of`'s "never raises" contract is preserved).

- **Survey (Stage 1)**: not raised in Stage 1 (surfaced in Stage 5's deeper
  read of the `renmark/` <-> `plugin/skills/*` boundary); no direct Stage 1
  citation.
- **PRD-acceptance impact (Stage 3)**: no REQ row directly covers this — not
  a compliance gap, a structural hardening opportunity spotted during Stage 5.
- **External evidence (Stage 4)**: not applicable — out of Stage 4's
  agent-orchestration-domain research scope; this is an internal
  registry-completeness concern, not an industry-pattern comparison.
- **Modularity impact (Stage 5)**: §5 ("Public API / internal contract
  boundary") — `renmark/skillmeta.py` is "the one place this boundary is
  genuinely formalized," but "nothing enforces that a new/renamed
  `plugin/skills/<name>/` directory has a corresponding
  `skillmeta.SKILLS["<name>"]` entry short of a lint pass... an unregistered
  skill likely silently falls back to `domain_of`'s default `"build"` rather
  than failing loudly (confirmed in code... lines 843-854)." §12 Change 5 is
  the proposed fix, explicitly separate from Change 4 (item 4 above).
- **Disposition**: Stage 5 itself recommends deferring this to a later
  roadmap release — it is not required by any of the four required Improve
  items' evidence, and is flagged as optional/stretch. It is still a
  distinct, cited Improve classification (not a sub-bullet of item 4) because
  its evidence trace (§5, boundary-brittleness) is independent of item 4's
  evidence trace (§6, routing-mechanism scatter).

## 6. `renmark/state/` — **Keep**

- **Survey (Stage 1)**: "a clean example of prior modernization" — split into
  `_core.py`/`usage.py`/`pause.py`/`pipeline.py`/`logs.py`/`commits.py`/
  `skills.py`, re-exported via `state/__init__.py`, no circularity, both
  `from renmark import state; state.X` and `from renmark.state import X`
  still work. Named explicitly as "the template to reuse."
- **PRD-acceptance impact (Stage 3)**: underlies REQ-3 (resumable workflows,
  `met`) and REQ-5 (context hygiene, `partial` but not due to this package).
- **External evidence (Stage 4)**: F6 — directionally identical to Bernstein's
  `.sdd/`-outside-agent-memory pattern and Agent Kanban's file-based state —
  validated, not a gap.
- **Modularity impact (Stage 5)**: §1/§12 — the literal precedent Changes 2
  and 3 mirror. No changes proposed to `state/` itself.

## 7. `context_budget_hint` (`renmark/state/skills.py`) — **Remove**

- **Survey (Stage 1)**: CHANGELOG's own 2026-08-02 entry names it "dead code,
  zero production callers"; a repo-wide grep after that fix still shows no
  call site.
- **PRD-acceptance impact (Stage 3)**: REQ-5 row = `partial` because of this;
  flag 4 explicitly requires Stage 6/7 to classify Keep-and-wire vs. Remove
  rather than silently carry it forward. **Decision rationale**: *wiring* it
  in would touch orchestration-adjacent call sites gated by REQ-30 (routing/
  context-limit change requiring the still-unmeasured numeric baseline +
  UPDATE gate) — out of scope for this structural-only pass. *Removing*
  unreferenced dead code changes zero observable behavior (it never executes)
  and is a legitimate structural cleanup within scope. Remove is the
  scope-consistent choice; re-introducing equivalent enforcement is a future,
  separately-gated feature decision, not this pass's job.
- **External evidence (Stage 4)**: F4 — "dead scaffolding masquerading as
  enforcement" is exactly the context-rot-adjacent anti-pattern the literature
  warns against; removing it is the textbook-correct response.
- **Modularity impact (Stage 5)**: not separately re-verified in Stage 5
  (Stage 5 focused on `_engine.py`/`lifecycle.py`/`schemas.py`); no
  contrary evidence found.
- **Re-verification (2026-08-03, at HEAD `c6741856f7603aac3e01f324fbaa4b7e6478155e`
  / v0.41.0)**: re-ran `grep -rn "context_budget_hint" --include="*.py"
  --include="*.md" .` — still zero production callers in `renmark/` or
  `plugin/`; only its own definition in `renmark/state/skills.py`, its test
  in `tests/test_state_skills.py`, and doc references (`CLAUDE.md`,
  `AGENTS.md`, `CHANGELOG.md`, plans, reviews). The 2026-08-02 "orchestration
  baseline controls" CHANGELOG entry wired a related hook
  (`milestone_context_checkpoint`) but explicitly documents it as "dormant,
  not an active trigger" — it does not call `context_budget_hint` itself.
  **Remove decision stands unchanged.**

## 8. `renmark/shadow.py` — **Keep** (as manual dev tool, not pipeline-wired)

- **Survey (Stage 1)**: record-and-replay regression harness; only referenced
  by its own tests (`test_shadow.py`, `test_shadow_live.py`) and its own
  design doc; standalone `python -m renmark.shadow` CLI by design, per its
  own docstring — not vestigial, deliberately not pipeline-wired.
- **PRD-acceptance impact (Stage 3)**: not separately mapped to a REQ row;
  no compliance impact either direction.
- **External evidence (Stage 4)**: no directly comparable external finding;
  out of Stage 4's orchestration-domain research scope.
- **Modularity impact (Stage 5)**: not separately assessed in Stage 5 (out of
  the `_engine.py`/`lifecycle.py`/`schemas.py` focus); Stage 1's "explicitly
  classify Keep-as-dev-tool vs. Remove" instruction is resolved here as Keep —
  it is tested, single-purpose, and imposes zero maintenance drag on the
  pipeline runtime since it has no call site to keep in sync.

## 9. `renmark/skillgen.py` — **Keep** (as manual dev tool, not pipeline-wired)

Same reasoning and evidence pattern as item 8: SKILL.md doc-slimming lint,
standalone `python -m renmark.skillgen` CLI, referenced only by its own test
and a 2026-06-29 plan doc, no pipeline-runtime caller (Survey §3). No REQ row
impact (Stage 3). Not in Stage 4's scope. Not reassessed in Stage 5. Keep.

## 10. `.renmark/memory/orchestration-baseline.md`'s unmeasured numeric baseline — **not a code classification; recorded as a blocking prerequisite**

This is a measurement gap, not a component to Keep/Improve/Replace/Remove.
Recorded here per dispatch instruction so it is not silently dropped:

- **Survey/Baseline (Stages 1-2)**: `.renmark/memory/orchestration-baseline.md`
  documents only *structural/qualitative* guarantees; explicitly states real
  token/wall-clock/dispatch-count numbers for the four representative
  scenarios (Start/Feature-Fix/Orchestrate/Rethink) are "not yet measured" —
  its own open item, not invented here. Per-run telemetry
  (`tokens_in`/`tokens_out`/`duration_s`) is ~0 in production logs.
- **PRD-acceptance impact (Stage 3)**: REQ-30 row = `partial/untestable-as-
  written`; flag 2 is a **blocking, non-Owner precondition**: any change
  touching `_engine.py`/`dispatch.py`/`lifecycle.py` cannot be verified
  against REQ-30's 15%-regression rule without this baseline existing first.
- **External evidence (Stage 4)**: not applicable — internal measurement gap.
- **Modularity impact (Stage 5)**: not applicable.
- **Disposition**: this is a **spike/measurement task**, not a code
  classification. The Discovery Direction Gate decision (`modularity-
  assessment.md` bottom) already resolves the immediate blocker for THIS
  pass (behavior-preserving splits of `_engine.py`/`lifecycle.py` are exempt
  from needing the baseline first) but commits to measuring it in "the first
  roadmap release." Stage 7/8 must carry this forward as an explicit,
  budgeted task — not fold it silently into a structural work package.

## 11. Git-worktree-per-agent isolation — **Unknown-needs-a-spike (explicitly OUT OF SCOPE for this transformation's roadmap)**

- **Survey/Baseline**: not raised internally; renmark dispatches subagents
  into the same working tree today (convention: "two agents, same file →
  sequential"), not raised as a defect by Stages 1-2.
- **PRD-acceptance impact (Stage 3)**: no REQ row directly covers this; not
  a compliance gap, an external-parity observation.
- **External evidence (Stage 4)**: F6/F8/I2 — most 2026 OSS coding-agent
  orchestrators (Bernstein, Claude Squad, Vibe Kanban, Cursor) default to
  worktree-per-agent for true parallel file-level work; renmark relies on
  convention-based sequencing instead of isolation-based guarantees. Named
  explicitly as Recommendation 2 ("bounded spike... not a default-behavior
  change") and Unknown U2 (disk/setup latency, dual-host Claude Code/Codex
  interaction unmeasured).
- **Modularity impact (Stage 5)**: not assessed (out of the module-boundary
  focus of Stage 5).
- **Spike contract (if ever picked up in a future pass)**:
  - **Question**: Does git-worktree-per-subagent isolation reduce
    same-file-coordination bugs enough to justify its setup/disk cost, and
    is it compatible with renmark's dual-host (Claude Code/Codex) dispatch
    model?
  - **Scope**: local timed experiment only — 2-6 parallel tasks (renmark's
    typical wave size), measure worktree create/teardown latency and disk
    delta; no change to default dispatch behavior.
  - **Evidence requirement**: quantified timing + disk numbers, plus an
    explicit compatibility check against `renmark/hosts.py`'s Claude
    Code/Codex capability split.
  - **Budget**: single research/prototype session, no code merged to
    default paths.
  - **Stop condition**: stop at the measurement + a Keep/Improve/Replace/
    Remove recommendation memo; do NOT implement worktree isolation as part
    of this or any pass without a separate Owner-approved PRD change (it
    would alter dispatch behavior, triggering REQ-30's UPDATE gate).
- **Disposition per Owner's Discovery Direction Gate**: explicitly deferred,
  NOT in scope for this transformation. **Must NOT appear in Stage 8's
  roadmap releases** — recorded here only so it is not silently dropped from
  institutional memory.

---

## Additional components assessed for completeness (not in the "at minimum" list, no separate action required)

- **`renmark/dispatch.py` (1063L) — Keep.** Modularity §12: "Deliberately NOT
  proposed" for splitting — already the most cohesive of the large modules,
  low coupling (imports only `fast_path`/`parser`/`providers.claude_agent`),
  single clear concern (wave dispatch).
- **`renmark/program.py`/`program_driver.py`/`recurrence.py`/`scan.py` —
  Keep.** Modularity §12: sized reasonably for scope; not proposed for
  splitting. Flagged only as a soft duplication-risk ("third parallel
  'what's next' engine," not confirmed duplicated) — worth a future
  AST-level check, not an action item this pass.
- **`renmark/delivery_state.py` (716L) — Keep (module structure); bugs are
  logic/budget bugs, not size/cohesion bugs** per modularity §12 and survey
  §6 (repeated byte-budget/archival bugs are call-site/logic issues at
  `_engine.py`'s `_complete_clean_run`, not a reason to split this module).
- **`renmark/config.py` / `renmark/hosts.py` / `renmark/cost.py` /
  `renmark/skillmeta.py` — Keep.** Modularity §7/§1: genuinely decoupled
  leaves, explicitly cited as good examples; no changes proposed. (The
  skillmeta-completeness *lint gate* proposal is a separate Improve item —
  see §5 above — and does not change this Keep classification of the
  `skillmeta.py` module itself.)

---

## Classification counts

**Correction (2026-08-03)**: an earlier draft of this table counted the
skillmeta-completeness lint gate as a 5th Improve item without giving it its
own cited-evidence section — it was only mentioned in passing inside the
"Additional components" section. That was a defect (a classification with no
cited evidence is not a valid entry). It has now been given its own section
(§5 above) with real, distinct Stage 5 evidence (`modularity-assessment.md`
§5, boundary-brittleness / silent-failure-seam finding, separate from item
4's §6 routing-scatter evidence), so the Improve count remains **5**, but
every counted item now has its own dedicated evidence-citation section.

| Class | Count | Items |
|---|---|---|
| Keep | 9 | `renmark/state/`, `shadow.py`, `skillgen.py`, `dispatch.py`, `program.py` cluster, `delivery_state.py`, `config.py`, `hosts.py`, `cost.py`/`skillmeta.py` (leaves) |
| Improve | 5 | `cli/_engine.py` (§1), `lifecycle.py` (§2), `schemas.py` inversion (§3), scattered routing (12 files) → `cost.resolve_executor` (§4), skillmeta-completeness lint gate (§5, optional/stretch) |
| Replace | 0 | — |
| Remove | 1 | `context_budget_hint` (§7, re-verified 2026-08-03 — decision stands) |
| Unknown-needs-a-spike | 2 | orchestration-baseline numeric measurement (§10, prerequisite, budgeted-in-roadmap), git-worktree-per-agent isolation (§11, out of scope, excluded from roadmap) |

Every Unknown entry above carries its spike's question/scope/evidence
requirement/budget/stop condition per dispatch instruction (§10, §11).

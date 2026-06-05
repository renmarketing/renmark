---
artifact_type: audit
schema_version: 1
created_at: 2026-06-05
source_sha: 1706ebe
generator: skill-overlap-audit
completion_state: complete
confidence: high
validation_status: validated
scope: plugin/skills/ + plugin/commands/ + plugin/skills/_shared/ + renmark/lifecycle.py routing
method: 4 parallel read-only cluster analysts + orchestrator first-hand pipeline knowledge
---

# Renmark Skill Overlap Audit (v0.7.0)

**Decision document — analysis only, no code changes.** Read-only review of all 19
skills, 19 commands, 3 shared contracts, and lifecycle/domain routing. Produced by
4 parallel cluster analysts (build-entry, meta/scaffolding, execution/verify,
shared/routing) synthesized against first-hand knowledge of a full pipeline run.

---

## 1. Current skill map

**19 skills, grouped by altitude:**

| Altitude | Skills | Notes |
|---|---|---|
| **product-level** | `prd`, (`start` de facto) | prd owns PRD.md; start routes at product altitude |
| **feature-level** | `brainstorm`, `verify` | spec discovery; goal-backward verification |
| **process/lifecycle** | `plan`, `orchestrate`, `feature` | decompose / execute / wrapper-router |
| **artifact-touchpoint** | `blueprint`, `check-plan`, `codereview`, `prd`(also) | write/validate one artifact, no stage advance |
| **debugging/recovery** | `debug`, `resume` | root-cause loop; cold-start recovery |
| **mechanical/narrow (LEAVE UNTOUCHED)** | `init`, `doctor`, `hygiene`, `roadmap`, `help` | deterministic, zero/low LLM, single-purpose |
| **meta/scaffold** | `setup` | first-use bootstrap (LLM-assisted) |

**Canonical lifecycle chain** (`renmark/lifecycle.py`):
`init → brainstorm-complete → plan-drafted → plan-validated → created → verified →
reviewed → documented → ready-to-release → released` (+ `restored`).
`blueprint` is correctly **off-chain** (touchpoint, no stage).

---

## 2. Overlap findings + risk levels

### BLOCKING

**B1 — `plan` dispatch gate misfires when embedded in `/renmark:feature`.**
`plan` Step 8b always shows the "Dispatch [d]" approval gate. When `feature` invokes
`plan` as its Step 3, the dispatch decision belongs to `feature`'s router — but no
"called-by" suppression flag or contract is documented in either SKILL. Result: either
a double approval gate, or `feature` silently overrides plan's gate (a trust violation —
real API tokens flow without the user's own gate being honored). *Governance: violates
"the human owns dispatch."*

**B2 — Dual writers on scope-contract artifacts (`CHANGELOG.md` scope entry + `stack.md`).**
Both `brainstorm` (Step 2/6) and `plan` (Step 0) write the scope records. The
`scope-contract.md` "whichever runs first writes, the other skips" rule is enforced only
by `plan`'s heuristic read of recent CHANGELOG entries + stack.md — no machine-readable
tag marks "this entry is a scope-contract write." Cross-session (`start→brainstorm`, new
session `feature→plan`) or format drift ⇒ duplicate scope entries corrupting the
canonical stack decision for all downstream tasks. *Governance: violates "one writer per
artifact."*

**B3 — Dual writers on `CLAUDE.md` within `setup`.**
`setup` writes rule blocks (steps 2–3), then delegates to `renmark.init` (step 5.5) which
writes the `<!-- BEGIN:project-stub -->` block to the same file. If the template seeds a
stub placeholder and the init script also inserts the marker, the "corrupted markers"
abort (exit 2) can fire on first run. Mitigated by byte-equality-skip, not eliminated;
ordering is load-bearing and undocumented as a contract.

### IMPORTANT

**I1 — `orchestrate` Step 6 is an undocumented memory-write stub.**
Imports `log_feature`, `append_routing`, `append_learning`, `log_bug` with zero concrete
call sites. `log_bug` is the hazard: if orchestrate writes bugs.md on task FAIL, it
pollutes the regression set with *build* failures (owned by verify/debug, not execution).
*Governance: violates "keep orchestrate execution-only."* → Narrow to `log_feature` +
`append_routing`; remove `append_learning` + `log_bug` from orchestrate's scope.

**I2 — `AskUserQuestion` picker boilerplate copy-pasted across 5+ skills.**
The ~70-word "present as interactive picker / fallback / 4-option cap / never auto-proceed"
block is duplicated verbatim in `finish`, `setup`, `brainstorm`, `plan`, `check-plan`
(and now `blueprint`). `handoff-menu.md` covers only quality-gate menus. Already caused
one documented drift (the 4-option cap update). → Extract one shared interaction contract.

**I3 — Duplicate PRD-nudge entry points: `start` 5a vs `brainstorm` 1b.**
`start` offers a (blocking-optional) `/renmark:prd` invocation; `brainstorm` surfaces a
non-blocking nudge for the same no-PRD condition. When `start` routes to `brainstorm`, a
user who declined in 5a meets the nudge again — and a "yes" in brainstorm runs prd
mid-brainstorm, flipping its own `HAS_PRD` branch. State-ordering hazard, two styles, one
trigger.

**I4 — `orchestrate (created) → verify (verified)` stage contract is prose-only.**
Orchestrate Step 7 sets stage `created`, Step 8 auto-invokes verify which sets `verified`.
verify's in-flight guard *requires* `created`. Any future skill writing `verified`
directly bypasses the guard. The dependency is undocumented as a contract / not encoded in
the lifecycle module.

**I5 — `init` + `doctor` absent from `DOMAIN_BY_SKILL`; `doctor` has no Step 0.**
`init` silently defaults to domain `build` via fallthrough (probably correct, undocumented);
`doctor` isn't wired into cross-domain contamination detection at all. G4 gap.

**I6 — `setup` (seed) and `hygiene` (prune) both write `features.md`/`bugs.md`/`learnings.md`
with no cross-referenced schema contract.** If setup's seed frontmatter (`created_at`)
doesn't match hygiene's age/dedupe expectations, hygiene may mis-archive seeds.

### DEFERRABLE

**D1 — `check-plan` Step 4 hand-off doubles as a dispatch entry point.** Standalone
check-plan can trigger orchestrate directly, so re-checking an old plan can accidentally
re-execute it. orchestrate already calls check-plan in pre-flight; the shortcut is
redundant. → Gate behind `--dispatch` or remove.

**D2 — 8 ghost skills in `DOMAIN_BY_SKILL`** (`secure`, `document`, `map`, `research`,
`release`, `restore`, `approve`, `issue`) have domain assignments but no skill dirs.
`next_recommended()` is guarded by `IMPLEMENTED_SKILLS`; `domain_of()` is **not** — an
asymmetry that's harmless today but undocumented. → Prune to implemented set, or add a
parallel guard + comment.

**D3 — `roadmap.md` snapshot committed on every run** ⇒ git noise (single file, no
functional breakage). `documented` lifecycle stage is dead (skipped: `verified → reviewed
→ finish`).

### CLEAN (verified non-overlaps — do not "fix")

- `doctor` vs `hygiene`: disjoint namespaces (`~/.claude/` config vs `.renmark/` artifacts). No overlap.
- `init`: correctly narrow (Python module + stdout relay; dev-standards.md is same-pass, not creep).
- `blueprint`: structurally clean touchpoint — no stage write, uses no contract it shouldn't, correct write-boundary.
- `check-plan` double-invoke (plan post-write + orchestrate pre-flight): intentional defense-in-depth, not duplication.
- `bugs.md` written by `verify` + `debug`: intentional (runtime failures vs investigated root causes).

---

## 3. Proposed ownership boundaries (WRITE / ALIGN / ROUTE / NOTHING)

| Artifact | WRITE (sole) | ALIGN (read verdict) | ROUTE (to writer) | NOTHING |
|---|---|---|---|---|
| `PRD.md` | **prd** | feature, brainstorm (subagent) | start, feature/brainstorm on drift | all others; plan reads only REQ-n IDs (documented exception) |
| `*.spec.md` | **brainstorm** | plan (input) | — | others |
| `*.plan.md` | **plan** | orchestrate, check-plan, verify, feature | — | others |
| `CHANGELOG.md` scope entry | **brainstorm** (or plan iff brainstorm skipped — needs tag) | — | plan routes-or-skips | — |
| `CHANGELOG.md` per-task / release | orchestrate (task) / finish (release) — distinct sections | — | — | — |
| `stack.md` | **brainstorm** (scope) + orchestrate (new deps only, append) | — | plan routes-or-skips | — |
| `CLAUDE.md`/`AGENTS.md` rule blocks | **setup** | — | — | others |
| `CLAUDE.md`/`AGENTS.md` project-stub | **init (module)** | — | setup routes to init | others must not write stub |
| `CLAUDE.md`/`AGENTS.md` PRD pointer | **prd** (pointer line only) | — | — | others |
| `project-map.md`, `dev-standards.md` | **init (module)** | blueprint reads project-map | setup, finish route to init | blueprint NOTHING-writes |
| `SCHEMATIC.md`, `PROTOTYPE.html` | **blueprint** | — | start, feature | init NOTHING (write-boundary) |
| `bugs.md` | **verify** (runtime) + **debug** (root cause) | — | codereview routes via hand-off | **orchestrate NOTHING** (remove log_bug) |
| `learnings.md` | **verify** + **debug** | — | — | orchestrate NOTHING |
| `routing.md` | **orchestrate** | — | — | others |
| `decisions.md` (ADRs) | orchestrate (escalation) + finish (close) + brainstorm/plan — append-only | — | — | — |
| `roadmap.md` | **roadmap** | — | — | others |
| `lifecycle.json` stage | each pipeline skill advances its own; feature resets | all read (preamble) | — | mechanical skills NOTHING |
| `pipeline.json`, wave-summaries | **orchestrate** | verify reads guard | — | others |
| `~/.claude/*` (config) | **doctor** | — | — | others |

**One-writer violations to resolve:** scope CHANGELOG/stack (B2), CLAUDE.md stub vs rule
blocks (B3, region-scoped — fix by sequencing/markers not merging), orchestrate→bugs.md (I1).

---

## 4. Recommended pipeline structure

The chain is fundamentally sound; **do not restructure it.** Targeted cleanups only:

- Keep: `init → brainstorm → plan → check-plan → orchestrate → verify → codereview → finish`.
- `blueprint` stays a touchpoint invoked by `start`/`feature`, never a stage.
- **Dead `documented` stage:** either remove it from `STAGES` (no skill advances to it) or
  leave as a no-op — do **not** add a `document` skill to fill it (it's a ghost). Prefer removal.
- **`ready-to-release` → manual:** correct as-is; `finish` owns release. Do not add a
  `/renmark:release` skill (the `NEXT_BY_STAGE_PLANNED` aspiration should stay aspirational).
- **Entry points:** `start` (vibe), `brainstorm` (spec), `feature` (wrapper), direct `plan`
  all converge on `plan→orchestrate`. Acceptable, but resolve the `feature→plan` dispatch
  contract (B1) so the wrapper path has exactly one gate.

---

## 5. Shared logic to extract into `_shared/` (use existing-contract-first rule)

Only three extractions are justified; all consolidate **existing** duplication (no new mechanism):

1. **`_shared/interaction-contract.md`** — the `AskUserQuestion` picker rendering rule
   (primary/fallback/4-option cap/never-auto-proceed). Consumed by finish, setup, brainstorm,
   plan, check-plan, blueprint. (Closes I2; `handoff-menu.md` stays the quality-gate-menu specialization.)
2. **`_shared/artifact-schema.md`** — the provenance header (`artifact_type`, `schema_version`,
   `source_sha`, `generator`, `stale_after`, `dependency_refs`) + the human-doc exemption
   (PRD.md). Currently restated in verify, brainstorm, blueprint, prd; swept by hygiene.
3. **`_shared/step0-preamble.md`** *(optional / DEFERRABLE)* — the `skill_preamble` response
   policy ("surface one line" vs "ignore" vs "do not block"). Inconsistent across blueprint/
   prd/resume/debug. Lower value; could be a wording standardization instead of a new file.

**Do NOT extract:** PRD alignment (already one contract: `prd-alignment.md`), scope Q1–Q3
(already one contract: `scope-contract.md`) — these are correctly single-sourced.

---

## 6. Skills to leave UNTOUCHED (mechanical / intentionally narrow)

`init`, `doctor`, `hygiene`, `roadmap`, `help` — deterministic, zero/low-LLM, single-purpose,
disjoint namespaces. Only non-content change warranted: register `init`+`doctor` in
`DOMAIN_BY_SKILL` (I5), which is a routing-table edit, not a skill rewrite.

---

## 7. `verify` bloat verdict

529 lines, 3 modes. **Do not split into separate skills** — the QA convergence loop
(`bugs.md`/`learnings.md`/`qa-flows.md`) is deeply shared and a new skill adds a name the
user must discover. **Restructure the file instead:** smoke (the default, ~50 lines) first,
then a clearly-fenced "Browser QA extension" section for `--qa`/`--deep-qa`. Revisit a
`verify-browser` sub-skill only if a third browser channel pushes it past ~600 lines.

---

## 8. Explicit non-goals (avoid overengineering)

- ❌ Do **not** split `verify` into multiple skills (restructure the doc only).
- ❌ Do **not** add any new lifecycle stage; prefer removing the dead `documented` stage.
- ❌ Do **not** create `document`/`secure`/`map`/`research`/`release`/`restore`/`approve`/`issue`
  skills to satisfy ghost domain entries — **prune** the entries instead.
- ❌ Do **not** merge `setup` and `init` — ownership is clean; fix B3 by sequencing/markers.
- ❌ Do **not** make additional skills read `PRD.md` — `prd-alignment.md` is the one contract.
- ❌ Do **not** introduce a new mechanism where `scope-contract.md` / `handoff-menu.md` /
  `prd-alignment.md` already apply.
- ❌ Do **not** turn `blueprint` into a stage; it is correct as a touchpoint.

---

## 9. Smallest safe next move

**Resolve B1 (feature→plan dispatch contract) — a ~10-line, behavior-preserving doc fix
across two SKILL files.** It is the only finding that risks real API spend without the
user's gate, it touches no Python and no other skill, and it needs no new mechanism: add a
documented "when invoked by `feature`, `plan` suppresses its Step 8b dispatch gate and
returns control to the router; `feature` owns the single dispatch approval" contract to
both `plan/SKILL.md` (Step 8b) and `feature/SKILL.md` (Step 3).

**Then, in priority order (each its own small change):** B2 (add a machine-readable
scope-write tag to `scope-contract.md` + both consumers), I1 (narrow orchestrate Step 6),
I2 (extract `_shared/interaction-contract.md`), I5 (register init+doctor domains),
B3 (document the setup→init CLAUDE.md write sequence).

Recommend running these as a single `/renmark:plan` scoped to "skill-boundary hardening
(docs + routing only, no behavior rewrites)" once approved — most are doc/contract edits,
ideal for haiku/sonnet, and none require touching the execution engine.

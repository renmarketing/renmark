---
artifact_type: rethink-survey
schema_version: 1
created_at: 2026-08-04T00:00:00Z
source_sha: 9bd233548a7f7b34695124596c3faa6398ec044b
related_plan: null
generator: sonnet
stale_after: null
dependency_refs:
  - .renmark/rethink/artifact-lifecycle/intake.md
---

# Stage 1 Internal Survey — `.renmark/` artifact and persistent-context subsystem

Scope: read-only inventory of every distinct artifact type under `.renmark/`
in this repo. Byte totals below are **approximate** (this session's tool set
has no `du`/`find -printf`/shell access — counts are file-count-exact via
`Glob`, byte totals are derived from representative file reads and rounded;
flagged where estimated).

## 1. `.renmark/audits/audit-report-*.{md,json}` and `inventory-*.{md,json}`

1. **Path/pattern:** `.renmark/audits/audit-report-YYYY-MM-DD.{md,json}`,
   `.renmark/audits/inventory-YYYY-MM-DD.{md,json}`, plus one-off named audits
   (`skill-feature-inventory-*`, `overlap-findings-*`,
   `ownership-source-of-truth-map-*`, `context-hygiene-and-safety-risks-*`,
   `modularity-scorecard-*`, `recommended-cleanup-backlog-*`,
   `audit-delta-*`, `2026-06-12-plugin-context-footprint.md`,
   `2026-07-15-codex-claude-parity.audit.md`).
2. **Creator:** `renmark/audit.py` (`write_inventory_report` / audit-report
   writer around lines 551–645); also referenced by `renmark/subagent_profiles.py`
   (audit-reader role) and skills `plugin/skills/audit/SKILL.md`,
   `plugin/skills/inventory/SKILL.md`, command `plugin/commands/audit.md`.
3. **Trigger/frequency:** `python -m renmark.audit` / `/renmark:audit`
   (`--inventory-only` for the inventory pair). Dated by day — one pair per
   invocation day; this repo shows near-daily runs 2026-06-09 → 2026-08-04
   (≈13 dated pairs + several one-off named reports = 89 files).
4. **Readers:** `plugin/skills/.shared/artifact-lifecycle.md`,
   `plugin/templates/AGENTS.md.template`, `plugin/templates/CLAUDE.md.template`,
   `plugin/templates/memory/INDEX.md.template` reference the audits directory
   by convention/path, not by ingesting file bodies. No production code path
   found that reads a prior `audit-report-*.md` body back into a running skill
   — each run is a fresh, independent snapshot. Reads are pointer/mention-only.
5. **Startup context:** Not loaded at `skill_preamble`/startup. Only touched
   when `/renmark:audit` or `/renmark:inventory` is explicitly invoked.
6. **Classification:** derived (computed from source + git state each run).
7. **Required for:** none of recovery/verification/acceptance/release —
   informational/health-check only.
8. **Count/bytes/age:** 89 files under `audits/`. Representative `.md` files
   run ~3–15 KB, `.json` companions ~2–10 KB; estimated total ≈550–700 KB.
   Oldest: 2026-06-09; newest: 2026-08-04 (today) — ~8 weeks of near-daily
   accumulation, unbounded growth, no rotation observed.
9. **Regenerable:** yes — fully deterministic from current repo/git state
   (each run recomputes from source, not from prior audits).
10. **Overlaps:** `audit-report-*` and `inventory-*` on the same date overlap
    heavily (inventory is largely a subset — command/skill inventory — of the
    full audit report). Both overlap conceptually with
    `.renmark/memory/project-map.md` (also a structural map of the codebase,
    but hand/skill-maintained singular file vs. dated snapshots) and with
    `.renmark/rethink/*/survey.md` (this document's own type) when a rethink
    targets the same subsystem an audit already covered.
11. **Proposed:** owner: audit/inventory skills; retain last N (e.g. 10) dated
    pairs, archive/delete older; budget ~2 MB; retire via rotation at
    `/renmark:finish` or a dedicated audit-GC step — never silently, always
    logged.

## 2. `.renmark/plans/*.plan.md` (+ a few `.md`/`.program.md`/`.request.md` siblings)

1. **Path/pattern:** `.renmark/plans/YYYY-MM-DD-<topic>.plan.md`; one
   `.program.md` (`2026-06-25-external-skills-p4-p12.program.md`); a couple of
   plain `.md` without the `.plan` infix.
2. **Creator:** `/renmark:plan` pipeline stage — grep shows plan-writing spread
   across `renmark/program.py`, `renmark/program_driver.py`,
   `renmark/cli/_engine.py`, `renmark/cli/_run_lifecycle.py`, and
   `plugin/commands`/skills for `plan`, `feature`, `orchestrate`.
3. **Trigger/frequency:** per feature/milestone plan — one per `/renmark:plan`
   or `/renmark:feature` run that reaches the plan stage. ~76 files spanning
   2026-05-29 → 2026-08-04.
4. **Readers:** `renmark/plan_lint.py` (lint gate reads plan bodies),
   `renmark/cli/_engine.py`/`_wave_loop.py` (execution engine reads the active
   plan to drive waves), `renmark/roadmap.py` (roadmap cross-references plan
   paths). These are full-body reads of the *active* plan only — historical
   plans are not re-ingested once a feature ships.
5. **Startup context:** not loaded at preamble; only the plan named in
   `lifecycle.json`/`pipeline.json` for the in-flight workflow is read.
6. **Classification:** canonical (design/decision record for its feature).
7. **Required for:** recovery (resumable execution reads the active plan) and
   partially acceptance (plan defines the verifier contract).
8. **Count/bytes/age:** 76 files; typical plan 5–40 KB; estimated total
   ≈900 KB–1.2 MB. Oldest 2026-05-29, newest 2026-08-04.
9. **Regenerable:** no — plans capture human/agent design decisions not
   reconstructable from git diff alone (git log shows *what* shipped, not the
   rejected alternatives/rationale captured in the plan).
10. **Overlaps:** shipped plans overlap with `CHANGELOG.md` (both narrate what
    changed) and with `.renmark/reports/features/<slug>/report.md` (post-hoc
    report vs. pre-hoc plan for the same feature).
11. **Proposed:** owner: plan/feature pipeline; retain all (canonical decision
    record, cheap in aggregate ~1 MB); no automatic retirement — archive
    superseded plan variants only if a topic is re-planned multiple times.

## 3. `.renmark/reviews/*.{review,verification}.md` and `.review.json`/named variants

1. **Path/pattern:** `.renmark/reviews/YYYY-MM-DD-<sha>.review.md`,
   `...verification.md`, plus milestone-specific names
   (`*.milestone-demo.md`, `*.milestone-signoff.md`, `*.boundary.md`,
   `*-rereview.review.json`, `*.m2-preflight.md`, etc.).
2. **Creator:** `renmark/dispatch.py`, `renmark/delivery_state.py`,
   `renmark/subagent_profiles.py` (reviewer/inspector roles),
   `renmark/scan.py`, `renmark/release.py`, `renmark/lifecycle/next_steps.py` —
   review/verification writers are spread across the delivery/dispatch stack,
   one per reviewer/verifier dispatch.
3. **Trigger/frequency:** per `/renmark:codereview`, `/renmark:verify`,
   milestone-boundary review, or scan-review — effectively per work-package or
   per-commit-sha reviewed. 150 files spanning 2026-05-28 → 2026-07-30 (dense).
4. **Readers:** `renmark/delivery_state.py` and `renmark/lifecycle/next_steps.py`
   read the *current* review/verification artifact to gate next-step decisions
   (PASS/FAIL/blocker) — bounded (status field), not full prose. `renmark/ledger.py`
   emits/reads inspection verdicts referencing these paths as pointers.
5. **Startup context:** not preamble-loaded; read only when a delivery-state
   or lifecycle-next-step check needs the specific sha's verdict.
6. **Classification:** canonical (acceptance evidence) for the review/
   verification tied to a still-relevant milestone/release; otherwise
   historical/derived once superseded.
7. **Required for:** acceptance and release-readiness gates directly (this is
   the acceptance-evidence artifact family named as protected in the intake).
8. **Count/bytes/age:** 150 files; most 1–8 KB, a handful (milestone-signoff,
   boundary) up to ~15 KB; estimated total ≈700 KB–1 MB. Oldest 2026-05-28,
   newest 2026-07-30 (no reviews dated into August yet in this repo snapshot).
9. **Regenerable:** no — a review/verification is a point-in-time judgment
   call not mechanically reproducible after the fact (re-running a reviewer
   later would produce a different artifact, not restore this one).
10. **Overlaps:** `*.verification.md` and `*.review.md` for the same sha are
    two halves of one evaluation, not true duplicates. Some boundary/blocker
    files (`m2-part1-*-blocker.md`) overlap with `.renmark/state/handoffs/*` —
    both capture a blocked-task narrative for the same task.
11. **Proposed:** owner: delivery/review pipeline; retain all reviews tied to
    a released milestone permanently (acceptance evidence — protected per
    intake); archive/compress reviews for abandoned or superseded plan
    branches after the branch is closed.

## 4. `.renmark/state/**` (runtime, gitignored)

1. **Path/pattern:** many sub-shapes: `lifecycle.json`, `pipeline.json`
   (not present as a top-level file in this snapshot — see `program.json`,
   `delivery.json`, `agency.json`, `mode.json`, `tasks.json`,
   `compact_checkpoint.json`, `last-skill.json`, `recurrences.json`/
   `.lock`, `usage.jsonl`, `proposals.json`, `delivery-archive.json`,
   `backlog/BL-*.json`, `wave-summaries/wave-N.json`,
   `handoffs/*.brief.md`/`*.raw.md`/`*.json`, `escalations/task-N/{response.txt,
   verifier.log,prompt.txt,metadata.json}`, `_wave-prompts/task-N.json`,
   `adhoc-specs/*.md`, ad hoc `*-spec.md`/`*-task.md` files.
2. **Creator:** the largest source fan-out of any artifact family — 31 files
   under `renmark/` write here, notably `renmark/state/_core.py`,
   `renmark/state/pipeline.py`, `renmark/state/skills.py`,
   `renmark/state/pause.py`, `renmark/state/usage.py`, `renmark/state/logs.py`,
   `renmark/lifecycle/stage.py`/`preamble.py`, `renmark/cli/_engine.py`,
   `renmark/cli/_wave_loop.py`, `renmark/cli/_run_lifecycle.py`,
   `renmark/dispatch.py`, `renmark/agency.py`, `renmark/mode.py`,
   `renmark/backlog.py`, `renmark/task_tracking.py`, `renmark/scan.py`,
   `renmark/heartbeat.py`, `renmark/roadmap.py`, `renmark/plan_lint.py`.
3. **Trigger/frequency:** continuously, at nearly every skill/stage
   transition, wave dispatch, escalation, and task completion — the highest
   write frequency of any `.renmark/` subsystem.
4. **Readers:** the same modules read their own state back (e.g.
   `renmark/cli/_engine.py` resumes from `pipeline.json`/`tasks.json`;
   `renmark/lifecycle/preamble.py` reads `last-skill.json` and
   `compact_checkpoint.json`; `renmark/agency.py`/`renmark/mode.py` read
   `agency.json`/`mode.json` for the mode-hint fragments seen in Stage 1's
   grep of `preamble.py`). Reads are bounded — small JSON files, targeted
   fields — by design (this is the recovery-state layer, deliberately kept
   under ~1 KB per REQ per CLAUDE.md's lifecycle bloat guard).
5. **Startup context:** YES — this is the one family that IS read at
   preamble/startup time, but narrowly: `skill_preamble()` reads
   `last-skill.json`, `compact_checkpoint.json`, `mode.json`, `agency.json`/
   `delivery.json` only — never recursively walks `.renmark/state/`. Verified
   directly from `renmark/lifecycle/preamble.py` source in this survey.
6. **Classification:** canonical recovery state (protected per intake) for
   the small "live" files (`lifecycle.json`, `program.json`, `delivery.json`,
   `mode.json`, `tasks.json`); the `escalations/`, `_wave-prompts/`,
   `handoffs/*.raw.md`, `adhoc-specs/`, loose `*-spec.md`/`*-task.md` files are
   more temporary/task-scoped scratch that outlives its originating run.
7. **Required for:** recovery directly (this is the named-protected family);
   also feeds acceptance indirectly (wave-summaries feed delivery gates).
8. **Count/bytes/age:** ~55 files enumerated (many more likely exist across
   other in-flight/completed features not globbed exhaustively here — this
   family grows per-task, not per-day). Most files are small JSON (<2 KB);
   `usage.jsonl` and `recurrences.json` can grow append-only. Estimated total
   ≈300–500 KB in this snapshot. No cleanup/rotation code found for
   `escalations/`, `_wave-prompts/`, or `handoffs/` after a task/feature ships.
9. **Regenerable:** the "live" pointer files (`lifecycle.json`, `mode.json`)
   are NOT regenerable (they ARE the resumability state); task-scoped scratch
   (`escalations/task-N/*`, `_wave-prompts/*`) is regenerable only by
   re-running the dispatch, i.e. destructive to delete mid-flight but inert
   once the task/feature has shipped.
10. **Overlaps:** `handoffs/*.brief.md` overlaps narratively with
    `.renmark/reviews/*.boundary.md`/`*-blocker.md` for the same task.
    `delivery-archive.json` and `.renmark/state/delivery.json` overlap by
    design (archive vs. live pointer) — expected, not a duplication bug.
11. **Proposed:** owner: lifecycle/dispatch pipeline; keep live pointer files
    forever (small, load-bearing); retire `escalations/`, `_wave-prompts/`,
    `handoffs/*.raw.md`, ad hoc loose spec/task files once their parent
    plan/feature reaches `released` in `lifecycle.json` — archive or delete at
    `/renmark:finish` time, budget ~1 MB live scratch.

## 5. `.renmark/memory/*.md`

1. **Path/pattern:** `INDEX.md`, `project.md`, `architecture.md`,
   `conventions.md`, `stack.md`, `dev-standards.md`, `qa-flows.md`,
   `analytics.md`, `bugs.md`, `decisions.md`, `roadmap.md`,
   `project-map.md`, `orchestration-baseline.md`, `routing.md`,
   `learnings.md`, `features.md`.
2. **Creator:** `renmark/init.py` (initial scaffold from templates), then
   updated by `renmark/memory.py`, `renmark/roadmap.py`,
   `renmark/lifecycle/preamble.py`/`stage.py`, `renmark/context.py`,
   `renmark/health.py`, `renmark/capabilities.py`, `renmark/debug.py`,
   `renmark/cli/commands.py`, `renmark/cli/_engine.py`, `renmark/plan_lint.py`
   — the second-largest writer fan-out (12 files), consistent with memory
   being the durable cross-session knowledge base every pipeline updates.
3. **Trigger/frequency:** per `/renmark:init` (scaffold), then incrementally
   on feature completion, bug fix, decision, routing outcome — append/update,
   not per-run recreation. Low file *count* growth (fixed ~16 files) but
   unbounded *content* growth inside `features.md`/`bugs.md`/`decisions.md`/
   `learnings.md`/`routing.md` over project lifetime.
4. **Readers:** `renmark/context.py` (`load_fragment`), `plugin/skills/.shared/
   context-taxonomy.md`'s "static/dynamic/memory/task-local" contract, and
   `INDEX.md` is the deliberate single entry point — per `.renmark/README.md`
   "Renmark commands read `.renmark/memory/INDEX.md` first, then fetch other
   files on demand." This is the one family explicitly designed for bounded,
   on-demand full-body reads (never the whole directory at once).
5. **Startup context:** `INDEX.md` is read at the start of most skills (small,
   pointer-style); other memory files load on demand only, per file 4 above —
   already Hermes-compatible by design.
6. **Classification:** canonical (durable project knowledge, git-committed
   per `.renmark/README.md`).
7. **Required for:** recovery (routing/decisions inform resumed work) and
   indirectly acceptance (dev-standards feeds verifier expectations); not
   itself a release artifact.
8. **Count/bytes/age:** 16 files, fixed count; sizes vary — `project-map.md`
   and `orchestration-baseline.md` likely the largest (structural maps);
   estimated total ≈150–300 KB, growing slowly via appends. Committed to git
   (not gitignored), so age = full project history.
9. **Regenerable:** partially — `project-map.md`/`architecture.md` could be
   regenerated by re-scanning source; `decisions.md`/`learnings.md`/
   `routing.md` capture judgment history NOT regenerable from git alone.
10. **Overlaps:** `project-map.md` overlaps with `audits/inventory-*.md` and
    with `rethink/*/survey.md` (three different structural-map mechanisms for
    largely the same "what's in this codebase" question — a real dedup
    candidate). `roadmap.md` overlaps with `.renmark/roadmap/program.md`.
11. **Proposed:** owner: init/memory pipeline; keep forever (small, canonical,
    already git-tracked and bounded-read by design); no retirement needed —
    if anything, consolidate the project-map/inventory/survey trio (see
    overlap note) rather than prune this family.

## 6. `.renmark/ledger/events.jsonl`

1. **Path/pattern:** single append-only file, `.renmark/ledger/events.jsonl`.
2. **Creator:** `renmark/ledger.py` (`append_ledger_event`,
   `ledger_path`/`ledger_dir`), also referenced by `renmark/task_tracking.py`
   and `renmark/subagent_profiles.py` for inspection-verdict events.
3. **Trigger/frequency:** per dispatch/work-order/inspection-verdict event —
   high frequency, one line per event, append-only, never rewritten.
4. **Readers:** `renmark/ledger.py::read_ledger_events` and
   `latest_verdict_for` — used by `renmark/subagent_profiles.py`'s inspector
   role (R-0.4, `emit_inspection_verdict`) to look up the latest verdict for a
   subject. Reads are bounded (latest-matching-line lookup), not full-file.
5. **Startup context:** not preamble-loaded; read only when an inspector
   verdict lookup or dispatch-independence check runs.
6. **Classification:** canonical (structured audit trail of dispatch/
   inspection events) but append-only and unbounded — needs a retention
   policy distinct from "keep forever."
7. **Required for:** acceptance (inspection verdicts feed R-0.4 controlled-
   worker gates) and partial recovery (dispatch-independence checks).
8. **Count/bytes/age:** 1 file; JSONL, grows unboundedly with orchestration
   volume — exact size not confirmed in this session (no `wc -l`/`du`
   available); flagged for a follow-up deterministic check
   (`wc -l .renmark/ledger/events.jsonl`) before Phase 2 sizing decisions.
9. **Regenerable:** no — event log of what actually happened, not
   reconstructable after the fact.
10. **Overlaps:** conceptually adjacent to `.renmark/reviews/*` (both record
    verdicts) but structurally distinct (JSONL event stream vs. per-review
    markdown/JSON file) — not a true duplicate, more a "should reviews link
    to ledger event IDs" question for Phase 2/3.
11. **Proposed:** owner: ledger/inspection pipeline; retain all events tied to
    released milestones; consider periodic compaction/rotation (e.g. archive
    events older than N releases into a dated `.renmark/ledger/archive/`
    file) once volume is confirmed — this is the clearest "needs a real
    number" item for Phase 2.

## 7. `.renmark/reports/features/<slug>/{report.md,metrics.json}`

1. **Path/pattern:** `.renmark/reports/features/<slug>/report.md` +
   `metrics.json` (module docstring also names `tasks/loops/backlog/releases`
   siblings under `reports/`, none present in this snapshot).
2. **Creator:** `renmark/reports.py` (`build_feature_report`,
   `write_feature_report`, atomic-write helper) — sole writer, with
   `_safe_component` path-traversal guarding on `slug`.
3. **Trigger/frequency:** per finished feature — one directory per
   `/renmark:feature`/`/renmark:finish` completion. 17 feature slugs present.
4. **Readers:** `render_report_md` reads the in-memory report dict to render
   (not a re-read of a prior file); no other production reader found grepping
   `renmark/` — these appear to be terminal, human-facing artifacts rather
   than machine-consumed inputs to later pipeline stages.
5. **Startup context:** not preamble-loaded; write-only from the pipeline's
   perspective once generated.
6. **Classification:** derived/terminal (a rendering of state already proven
   elsewhere — plan + reviews + verification) but still useful as the single
   human-readable "what shipped" summary per feature.
7. **Required for:** none of recovery/verification directly; loosely
   supports release narrative/changelog cross-referencing.
8. **Count/bytes/age:** 17 feature dirs (34 files); `report.md` typically
   2–6 KB, `metrics.json` <1 KB; estimated total ≈100–150 KB.
9. **Regenerable:** yes in principle — `build_feature_report` takes structured
   inputs (git sha, review pointers, etc.) that mostly derive from plan +
   review artifacts, so this could be rebuilt if those upstream artifacts
   still exist.
10. **Overlaps:** duplicates `.renmark/plans/*.plan.md` (post-hoc summary vs.
    pre-hoc plan) and `CHANGELOG.md` entries for the same feature — three
    different narrations of "what shipped for feature X."
11. **Proposed:** owner: finish/reports pipeline; retain all (small, cheap,
    human-facing); no retirement needed given current volume.

## 8. `.renmark/rethink/<slug>/*.md` (+ `archive/`)

1. **Path/pattern:** `.renmark/rethink/renmark-architecture/{intake,baseline,
   classification,external-benchmark,modularity-assessment,
   prd-acceptance-map,survey,target-blueprint,roadmap}.md` +
   `archive/pre-roadmap-program-2026-08-03.{md,json}`; this run's own
   `.renmark/rethink/artifact-lifecycle/{intake.md,survey.md}`.
2. **Creator:** `/renmark:rethink` pipeline (skill-driven, dispatches
   researcher/planner subagents per stage — writes are subagent `Write` calls
   per the rethink skill contract, not a single dedicated Python module; no
   `renmark/rethink.py` found — this is currently skill-orchestrated rather
   than code-owned, unlike audits/reports/ledger).
3. **Trigger/frequency:** per `/renmark:rethink` invocation, one file per
   stage (9-stage contract per CLAUDE.md), one slug per rethink target. Two
   slugs exist in this repo: `renmark-architecture` (already released through
   its roadmap, now archived-in-place) and `artifact-lifecycle` (this run,
   Stage 1 only, gated to stop here per intake.md).
4. **Readers:** cross-referenced by `renmark/lifecycle/preamble.py`'s
   docstring pointer to `target-blueprint.md`, and by `.renmark/roadmap/
   program.md` (see §9) which is the execution vehicle for a released
   rethink's roadmap — bounded pointer references, not bulk re-ingestion.
5. **Startup context:** not preamble-loaded; explicit-dispatch only, per the
   rethink skill's own stage gating.
6. **Classification:** canonical for an active/recently-released rethink
   (design record equivalent to a PRD); becomes historical once its roadmap
   fully ships — `renmark-architecture`'s `archive/` subfolder shows the
   pipeline already has a "superseded doc → archive/" convention in-slug.
7. **Required for:** none of recovery/verification directly, but IS the
   upstream source for the `.renmark/roadmap/program.md` execution artifact
   (required for release planning of the rethink's approved changes).
8. **Count/bytes/age:** 12 files across both slugs (10 in `renmark-architecture`
   + 2 in `artifact-lifecycle` so far); `renmark-architecture` docs run
   several KB to tens of KB each (survey/blueprint are the largest);
   estimated total ≈150–250 KB. Oldest ~2026-08-02, newest today.
9. **Regenerable:** no — captures external benchmarking, judgment, and
   Owner-approved scope decisions, not mechanically reproducible.
10. **Overlaps:** `survey.md` (this artifact type) duplicates
    `.renmark/memory/project-map.md` and `audits/inventory-*.md` in *purpose*
    (structural inventory) though scoped differently per-rethink; flagged
    directly by this task's own instructions as a known overlap to resolve in
    Phase 2/3.
11. **Proposed:** owner: rethink pipeline; keep all stage docs for an active
    or recently-released rethink; once a rethink's roadmap fully ships, move
    the whole slug under `archive/` (the pattern already exists) rather than
    deleting — these are Owner-approved design decisions.

## 9. `.renmark/roadmap/*.md`

1. **Path/pattern:** `.renmark/roadmap/program.md` (canonical, tracked in git
   status as modified this session) and `agency-optimization-roadmap.md`.
2. **Creator:** `renmark/roadmap.py`, `renmark/program.py`,
   `renmark/program_driver.py`.
3. **Trigger/frequency:** per `/renmark:roadmap` run or program update; low
   frequency, updated in place (not dated/versioned per-run) — this is the
   one family that mutates a single file rather than accumulating new dated
   files, notably different growth shape from audits/reviews/state.
4. **Readers:** `renmark/lifecycle/next_steps.py` and `renmark/cli/_engine.py`
   read `program.md`/roadmap state to determine next work package; gate logic
   in the roadmap/rethink skills reads it to decide what's already scheduled.
5. **Startup context:** not preamble-loaded by default; read on explicit
   `/renmark:roadmap` or when a rethink's roadmap-stage needs current program
   state.
6. **Classification:** canonical (active execution plan / backlog of
   approved work).
7. **Required for:** recovery (what's next) and indirectly acceptance
   (defines the milestones that get verified).
8. **Count/bytes/age:** 2 files; `program.md` likely several KB to tens of
   KB given it aggregates milestone history; estimated ≈20–40 KB total.
9. **Regenerable:** no — encodes prioritization judgment, not derivable
   purely from git log.
10. **Overlaps:** `program.md` overlaps with `.renmark/memory/roadmap.md`
    (two roadmap-shaped files in different directories) — worth reconciling
    in Phase 2/3.
11. **Proposed:** owner: roadmap pipeline; keep current version; archive
    superseded program snapshots (the `rethink/.../archive/pre-roadmap-
    program-*.md` pattern already shows this happening for at least one
    rethink-triggered program rewrite).

## 10. `.renmark/specs/*.spec.md` (+ `.brief.md`, `.request.md`)

1. **Path/pattern:** `.renmark/specs/YYYY-MM-DD-<topic>.spec.md`, occasional
   `.brief.md`/`.request.md` siblings.
2. **Creator:** `/renmark:brainstorm` per `.renmark/README.md`; source grep
   shows `renmark/scan.py` and `renmark/loop.py` as the code paths touching
   `.renmark/specs`.
3. **Trigger/frequency:** per brainstormed feature — one per design session,
   21 files spanning 2026-05-27 → 2026-07-02 (none since, suggesting recent
   work has skipped the spec stage or used PRD/plan directly).
4. **Readers:** referenced by plan-writing stages as upstream design intent;
   no evidence of automatic re-ingestion beyond the originating plan/feature
   flow.
5. **Startup context:** not preamble-loaded.
6. **Classification:** canonical (design record, git-committed per README).
7. **Required for:** none of recovery/verification/release directly; input
   to plans.
8. **Count/bytes/age:** 21 files; typical 3–10 KB; estimated ≈150 KB total.
9. **Regenerable:** no — captures brainstorm-session design reasoning.
10. **Overlaps:** none strong — this family predates the plan and is largely
    superseded/absorbed by it, not duplicated.
11. **Proposed:** owner: brainstorm pipeline; keep all (small, canonical,
    already git-tracked); no retirement needed.

## 11. `.renmark/debug/<session-id>/*`

1. **Path/pattern:** `.renmark/debug/YYYYMMDD-HHMMSS-<hash>/session.md` (+
   occasional `repro.py`, `repro-repo/` (a full nested git repo for
   reproduction), `sandbox-probe-result.json`, `repro-result.json`).
2. **Creator:** `renmark/debug.py`, `renmark/init.py`/`renmark/bootstrap.py`
   (scaffold `.renmark/debug/` on init).
3. **Trigger/frequency:** per `/renmark:debug` session — one directory per
   invocation. 12 sessions present, 2026-06-14 → 2026-07-31.
4. **Readers:** session-local only — each debug session reads its own
   `session.md`/repro artifacts for isolation (per CLAUDE.md's "Context
   hygiene" rule: generated debug files route through `/renmark:debug`, never
   read directly into the orchestrator). No cross-session reader found.
5. **Startup context:** not preamble-loaded; gitignored per `.renmark/README.md`.
6. **Classification:** temporary/ephemeral by design (explicitly gitignored,
   explicitly session-isolated).
7. **Required for:** none of recovery/verification/acceptance/release once
   the debug session's fix has landed and been verified.
8. **Count/bytes/age:** 12 session dirs, ~45 files including one nested
   `.git` reproduction repo (`20260730-130449-c190/repro-repo/.git/...` —
   this single session embeds a full mini git repo, disproportionately large
   relative to the rest of the family); estimated ≈200–400 KB total, skewed
   by that one nested-repo session.
9. **Regenerable:** partially — the debug narrative (root cause, fix
   rationale) is not regenerable; the `repro-repo/` nested git checkout is
   regenerable (it's a reproduction scaffold) but currently persists after
   the session presumably closed.
10. **Overlaps:** none strong with other families; the nested `repro-repo/`
    is the one clear candidate for cleanup since it's a full duplicate git
    object store, not just markdown.
11. **Proposed:** owner: debug pipeline; retain `session.md` narratives for
    N days/until superseded; delete/archive `repro-repo/` and other
    reproduction scaffolding once the session's root cause is confirmed fixed
    and merged — this nested-git-repo pattern is worth a specific Phase 2
    guard (never let a debug repro leave a live `.git/objects` tree lying
    around indefinitely).

## 12. `.renmark/version/*` (release snapshots)

1. **Path/pattern:** `.renmark/version/renmark-v<ver>.zip` +
   `.renmark/version/v<ver>/` (full unpacked source tree per release).
2. **Creator:** `renmark/release.py` (`build_package`, `build_version_snapshot`,
   CLI `snapshot` command) — also touched by `renmark/reports.py` (resolves
   `release_link` from `version_path`) and `renmark/init.py`.
3. **Trigger/frequency:** per release/version bump — one zip + one unpacked
   dir per `python -m renmark.release snapshot`. 3 versions present
   (v0.39.7, v0.40.0, v0.41.0).
4. **Readers:** `renmark/reports.py::_resolve_release_link` reads the version
   directory name (not file bodies) to link a feature report to its release.
   No production code re-reads the unpacked source tree bodies.
5. **Startup context:** not preamble-loaded.
6. **Classification:** canonical release history (explicitly protected per
   intake) for the zips; the **unpacked** `v<ver>/` directories are a
   near-duplicate of the zip's own contents (same files, just exploded) —
   this is the single largest disk consumer in `.renmark/` by a wide margin
   (1,733 files matched under `.renmark/version/**` alone in this survey's
   initial glob, vs. ~435 across everything else combined).
7. **Required for:** release history / rollback reference.
8. **Count/bytes/age:** 3 zips + 3 unpacked trees (≈1,730 files in the
   unpacked trees). Each unpacked tree mirrors the full `renmark/` +
   `plugin/` + `tests/` source at that version — likely several MB per
   version, so ≈10–20+ MB total for 3 versions; this is a byte-total
   estimate flagged for a follow-up deterministic `du -sh` check before
   Phase 2 sizing decisions.
9. **Regenerable:** the unpacked `v<ver>/` trees ARE regenerable from their
   sibling zip (trivial `unzip`) — this is the clearest deletable-without-
   loss candidate in the whole survey: keep the zip (release artifact), drop
   the parallel unpacked directory (pure disk duplication of the zip).
10. **Overlaps:** each `v<ver>/` unpacked directory is a byte-for-byte content
    duplicate of its own `renmark-v<ver>.zip` sibling — the clearest, most
    unambiguous overlap found in this entire survey.
11. **Proposed:** owner: release pipeline; keep zips forever (small, single-
    file, canonical release history); **do not keep the unpacked `v<ver>/`
    directories on disk long-term** — regenerate on demand via unzip if ever
    needed, or retain only the single most-recent unpacked tree for quick
    diffing. This is the single highest-leverage cleanup candidate this
    survey found by byte count.

## 13. `.renmark/config.json`, `.renmark/README.md`

1. **Path/pattern:** two fixed top-level files.
2. **Creator:** `config.json` written/read via `renmark/config.py` (referenced
   throughout preamble/mode/headless code); `README.md` is a static
   hand-authored doc (per its own content, describing the directory).
3. **Trigger/frequency:** `config.json` updated on explicit
   `renmark-execute --set-*` calls; `README.md` essentially static.
4. **Readers:** `config.json` read constantly by `renmark/config.py`
   consumers (`compact_gate_tokens`, `is_headless`, etc.) — small, bounded,
   startup-relevant. `README.md` is documentation only, not code-read.
5. **Startup context:** `config.json` IS read at/near startup (small, single
   values) — appropriately lightweight for Hermes. `README.md` is not
   auto-loaded by any skill.
6. **Classification:** canonical config (`config.json`); canonical docs
   (`README.md`) — note `README.md`'s own "Committed" section is now stale:
   it doesn't mention `roadmap/`, `reports/`, `rethink/`, `ledger/`,
   `specs/.gitkeep`-style dirs that exist today, and its "Gitignored" section
   omits several state subfamilies found in this survey.
7. **Required for:** `config.json` — recovery/behavior config; `README.md` —
   none functionally, but it's the intended map for a human/agent orienting
   in `.renmark/` and is currently out of date.
8. **Count/bytes/age:** 2 files, <1 KB each.
9. **Regenerable:** `config.json` — defaults are code-defined, so a deleted
   file regenerates to defaults (loses only explicit overrides);
   `README.md` — not regenerable (hand-authored), and currently drifted from
   reality (see 6).
10. **Overlaps:** none.
11. **Proposed:** owner: config/docs; keep both; recommend `README.md` be
    refreshed as part of whatever Phase 3 implementation follows this survey
    (it's the most natural place to document a new retention/Hermes
    contract).

## Closing summary table

| Artifact type | Count | Bytes (approx.) | Class | Context-injecting | Regenerable |
|---|---|---|---|---|---|
| audits (`audit-report-*`, `inventory-*`, one-offs) | 89 | ~550–700 KB | derived | N (pointer only) | Y |
| plans (`*.plan.md`) | 76 | ~900 KB–1.2 MB | canonical | Y (active plan only, bounded to in-flight) | N |
| reviews (`*.review.md`/`*.verification.md`/variants) | 150 | ~700 KB–1 MB | canonical (acceptance evidence) | Y (bounded status field) | N |
| state (`.renmark/state/**`) | ~55+ (grows per-task) | ~300–500 KB | mixed: canonical (live pointers) / temporary (scratch) | Y — narrow, startup-relevant subset only (`last-skill.json`, `compact_checkpoint.json`, `mode.json`, `agency.json`) | live files N / task scratch Y (partial) |
| memory (`.renmark/memory/*.md`) | 16 | ~150–300 KB | canonical | Y (bounded, on-demand, by design) | partial |
| ledger (`events.jsonl`) | 1 | unconfirmed (flagged) | canonical | Y (bounded latest-event lookup) | N |
| reports (`reports/features/<slug>/*`) | 17 dirs / 34 files | ~100–150 KB | derived/terminal | N | Y (in principle) |
| rethink (`rethink/<slug>/*.md`) | 12 | ~150–250 KB | canonical (active) → historical (shipped) | N (pointer only) | N |
| roadmap (`roadmap/*.md`) | 2 | ~20–40 KB | canonical | Y (read by lifecycle/next_steps) | N |
| specs (`specs/*.spec.md`) | 21 | ~150 KB | canonical | N (superseded by plan) | N |
| debug (`debug/<session>/*`) | 12 dirs / ~45 files | ~200–400 KB (skewed by one nested repo) | temporary | N (session-isolated) | partial |
| version (`version/*.zip` + `version/v*/`) | 3 zips + 3 trees (~1,730 files) | ~10–20+ MB (flagged, largest by far) | canonical (zip) / **duplicate** (unpacked tree) | N | Y (unpacked trees fully, from zip) |
| config.json / README.md | 2 | <2 KB | canonical | Y (config only, small) | config: Y / README: N |

**Headline finding for Phase 2/3:** the single largest and clearest cleanup
candidate is `.renmark/version/v<ver>/` (unpacked source trees) — a full
byte-for-byte duplicate of its sibling zip, ~1,730 of the ~2,168 total files
under `.renmark/` in this repo. The clearest cross-family overlap needing a
Phase 2 decision is the three-way structural-map redundancy between
`.renmark/memory/project-map.md`, `.renmark/audits/inventory-*.md`, and
`.renmark/rethink/<slug>/survey.md`. Startup/Hermes exposure is already
narrow and well-bounded today — `skill_preamble()` reads only a handful of
small `.renmark/state/*.json` files, never recursing into audits, reviews,
rethink, reports, debug, or version — so the "Hermes-ready" goal in the
intake is largely about disk growth and *explicit-dispatch* read discipline,
not a startup-time regression to fix.

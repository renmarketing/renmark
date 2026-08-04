---
artifact_type: rethink-lifecycle-contract
schema_version: 1
created_at: 2026-08-04T00:00:00Z
source_sha: 9bd233548a7f7b34695124596c3faa6398ec044b
related_plan: null
generator: sonnet
stale_after: null
dependency_refs:
  - .renmark/rethink/artifact-lifecycle/survey.md
---

# Stage 2 Lifecycle Contract — `.renmark/` artifact retention

Design-only. Extends the existing provenance block (CLAUDE.md: `artifact_type`,
`schema_version`, `created_at`, `source_sha`, `related_plan`, `generator`,
`stale_after`, `dependency_refs`) and the lifecycle-field additions already
defined in `plugin/skills/.shared/artifact-lifecycle.md` (`owner`, `status`,
`dependencies`, `invalidated_by`, `replacement`, `retention`). No new metadata
schema is introduced. Every rule below is stated as a deterministic,
script-checkable predicate for Phase 3, not a judgment call.

Reference validators already in-repo that Phase 3 should reuse rather than
duplicate: `renmark/schemas.py` (`validate_artifact_metadata`, `validate_lifecycle`,
size-budget check pattern used for `lifecycle.json`'s 1024-byte cap),
`plugin/skills/.shared/artifact-lifecycle.md` (retirement policy: stop
generation → leave existing instances → redirect readers via `replacement`).

## Global rules used by every section below

- **Stale/superseded detection (deterministic):** an artifact is `stale` iff
  (a) `stale_after` is set and has passed, OR (b) a newer artifact of the
  same `artifact_type` + same slug/date-prefix exists (e.g. a later
  `audit-report-YYYY-MM-DD` for the same report family, a `replacement`
  pointer set on this file per `artifact-lifecycle.md`). No prose judgment —
  string/date comparison only.
- **Archive exclusion (deterministic):** a path is excluded from automatic
  context loading and recursive discovery/glob iff it contains an `archive/`
  path segment. This is the existing convention (`rethink/renmark-architecture/
  archive/`) generalized to every folder below — audit tooling, inventory
  globs, and `renmark.lint`/discovery walks MUST skip any path matching
  `**/archive/**`. No new manifest file needed; the directory-naming
  convention IS the allowlist mechanism, consistent with how `plugin/skills/
  .shared/` is already skipped by `renmark.lint` per that file's own note.
- **Safe-deletion criteria (ephemeral/generated only, no Owner gate):** an
  artifact instance may be auto-deleted with no gate iff ALL of: (1) its
  artifact type is classified `ephemeral/generated` below; (2) it is fully
  regenerable by a named deterministic command (recorded in `generator`/
  `dependency_refs`); (3) zero other artifact's `dependency_refs`/`replacement`/
  pointer cites its exact path (grep-checkable); (4) it is past its folder's
  max-age budget; (5) it is not the single most-recent instance of its
  type+slug (a keep-last-1 floor always applies, even past age, so a folder
  never goes to zero history). Fail any one condition → no auto-delete.
- **Protection for canonical/acceptance types (`plans/`, `reviews/`):** budget
  pressure MAY trigger a move to an archive tier (`archive/` subfolder, same
  exclusion rule as above) but MUST NEVER trigger deletion. Deletion of a
  plan or review requires an explicit Owner-approved retirement action,
  logged, per the three-step retirement policy in `artifact-lifecycle.md`.
- **Warning/blocking convention:** "warning" = surfaced at the next
  `/renmark:audit`/`/renmark:hygiene` run only (informational, no gate).
  "Blocking" for ephemeral/derived types = the writer skips creating a new
  instance until rotation runs; for canonical/protected types "blocking"
  never means delete — it means "route to archive-tier move, Owner-visible."

---

## 1. `.renmark/audits/` — `audit-report-*`, `inventory-*`, one-off named audits

- **Classification:** ephemeral/generated (derived, fully regenerable from
  current source+git state each run; not context-injected — pointer-only
  reads).
- **Canonical owner:** `renmark/audit.py` / audit+inventory skills.
- **Budget:** file count 60 (warn 48 / 80%), bytes 1.5 MB (warn 1.2 MB),
  max age 60 days.
- **Rotation/compaction (scriptable, no LLM):** keep the last 15 dated
  `audit-report`+`inventory` pairs (30 files) by filename date descending;
  move older dated pairs under `.renmark/audits/archive/`; one-off named
  audits (non-dated) are capped separately at 20 most-recent by mtime, same
  archive-move rule beyond that.
- **Stale detection:** any `audit-report-*`/`inventory-*` whose date prefix
  is older than the 15th-most-recent of its family is stale by definition
  (rule 10 above, no `stale_after` needed since these regenerate daily).
- **Protection:** none — ephemeral, safe-deletion criteria apply once moved
  to `archive/` and past 60 days with zero inbound references.

## 2. `.renmark/plans/*.plan.md` (+ `.program.md`/`.request.md` siblings)

- **Classification:** canonical evidence (design/decision record; feeds
  resumable execution and the verifier contract).
- **Canonical owner:** plan/feature/orchestrate pipeline (`renmark/program.py`,
  `renmark/cli/_engine.py`, `renmark/plan_lint.py`).
- **Budget:** file count 150 soft cap (warn 120 / 80%, current 76), bytes
  3 MB (warn 2.4 MB), age: unbounded — no automatic age-based action.
- **Rotation:** none by deletion. At 100% of the file-count budget, new
  plans still write normally; the warning routes to `/renmark:hygiene`
  suggesting an archive-tier sweep of plans whose parent feature reached
  `released` in `lifecycle.json` AND has no open dependency_refs pointing to
  it — move (never delete) those under `.renmark/plans/archive/`.
- **Stale detection:** a plan is superseded (not deleted) once a newer plan
  for the same topic slug exists with `status: superseded` + `replacement`
  set per `artifact-lifecycle.md`.
- **Protection:** full protection per Global rule — archive-tier move only,
  Owner-approved retirement required for delete, never budget-triggered
  deletion.

## 3. `.renmark/reviews/*.{review,verification}.md` and variants

- **Classification:** canonical (acceptance evidence) while tied to a
  still-relevant milestone/release; historical once the milestone/branch is
  closed/superseded.
- **Canonical owner:** review/verification/delivery pipeline
  (`renmark/delivery_state.py`, `renmark/lifecycle/next_steps.py`,
  `renmark/ledger.py`).
- **Budget:** file count 250 soft cap (warn 200 / 80%, current 150), bytes
  1.5 MB (warn 1.2 MB), age: unbounded for reviews tied to a released
  milestone.
- **Rotation:** reviews for abandoned/superseded plan branches (the parent
  plan carries `status: superseded` with no shipped release) may move to
  `.renmark/reviews/archive/` once that branch is closed — move only.
- **Stale detection:** a review is historical once its `sha`'s parent
  milestone reaches `released` AND a newer review/verification exists for
  the same task/sha family (rule 10); acceptance evidence for a released
  milestone stays canonical forever, not "historical."
- **Protection:** same as plans — archive-tier move allowed, delete
  requires explicit Owner-approved retirement, never budget-triggered.

## 4. `.renmark/state/**` (runtime, gitignored)

- **Classification:** mixed. Live pointer files (`lifecycle.json`,
  `program.json`, `delivery.json`, `mode.json`, `agency.json`, `tasks.json`,
  `compact_checkpoint.json`, `last-skill.json`) = **active context**
  (preamble-read) and canonical recovery state — protected. Task-scoped
  scratch (`escalations/task-N/*`, `_wave-prompts/*`, `handoffs/*.raw.md`,
  `adhoc-specs/*`, loose `*-spec.md`/`*-task.md`) = **ephemeral/generated**.
- **Canonical owner:** `renmark/state/*`, `renmark/lifecycle/preamble.py`,
  `renmark/dispatch.py`.
- **Budget:** live pointer files — hard 1024-byte cap per file, already
  enforced by `schemas.py::validate_lifecycle`; total live-file family
  budget 50 KB. Scratch family: file count 200 (warn 160 / 80%), bytes
  1 MB (warn 800 KB), max age 14 days past parent feature's `released`
  stage.
- **Rotation:** scratch subfamilies auto-delete (safe-deletion criteria
  apply directly — fully regenerable by re-dispatch, task-scoped, no
  cross-reference once the parent plan/feature is `released`) at
  `/renmark:finish` time or the next hygiene sweep past the 14-day mark.
  `handoffs/*.brief.md` (non-raw) is the one scratch-adjacent file that
  narrates a blocker for cross-referencing — exclude it from scratch
  auto-delete, treat it like a review/boundary artifact (archive-move only).
- **Stale detection:** `stale_after` on ad hoc spec/task files if set;
  otherwise "parent feature/plan reached `released`" is the deterministic
  trigger for scratch eligibility.
- **Protection:** live pointer files are protected exactly like `plans/`/
  `reviews/` — never deleted, only ever overwritten in place by their owning
  code path.

## 5. `.renmark/memory/*.md`

- **Classification:** canonical, **active context** — `INDEX.md` is
  preamble-read; other files load on demand via `renmark/context.py::
  load_fragment`. This is the durable "current facts" layer.
- **Canonical owner:** `renmark/memory.py`, `renmark/init.py` (scaffold),
  updated incrementally by the modules listed in survey.md §5.
- **Budget:** fixed file count (16, no growth expected without a deliberate
  new-file decision). Per-file byte cap for the append-growth files
  (`features.md`, `bugs.md`, `decisions.md`, `learnings.md`, `routing.md`):
  500 KB warn / 750 KB block-new-appends. `project-map.md` cap: 300 KB
  (see §closing — this is now the sole canonical structural-map home).
- **Rotation/compaction:** when an append-growth file exceeds its 750 KB
  block threshold, the deterministic compaction rule is "keep last 200
  entries verbatim, move older entries to `.renmark/memory/archive/
  <file>-pre-<date>.md`" — a pure line-count/date-split operation, no LLM
  call, scriptable against each file's existing entry-delimiter convention
  (dated headers).
- **Stale detection:** `analytics.md` is the one memory file survey.md's
  own audit already flagged stale (no current writer) — treat "zero writer
  code path found by grep" as the deterministic staleness signal for any
  memory file, checked at hygiene-audit time, not guessed at runtime.
- **Protection:** memory files are canonical and git-committed; the same
  archive-move-not-delete rule applies to the split-off `archive/*.md`
  segments produced by compaction above.

## 6. `.renmark/ledger/events.jsonl`

- **Classification:** canonical (structured audit trail; feeds R-0.4
  inspection-verdict lookups) but append-only and currently unbounded.
- **Canonical owner:** `renmark/ledger.py`.
- **Budget:** line count 50,000 (warn 40,000 / 80%), bytes 25 MB (warn
  20 MB). Exact current size unconfirmed per survey.md — first Phase 3 step
  is `wc -l`/`du -sh` before enforcing.
- **Rotation:** deterministic line-count-based split — once over budget,
  move all lines whose event `ts` predates the oldest still-`active`
  milestone's start into `.renmark/ledger/archive/events-pre-<date>.jsonl`;
  keep the live file append-only for events tied to any milestone not yet
  `released`. Pure JSONL line filter, no LLM call.
- **Stale detection:** an event line is archive-eligible once its
  referenced milestone/task id is no longer in any `active`/`in_progress`
  state across `.renmark/state/delivery.json` and `lifecycle.json`.
- **Protection:** events tied to a released milestone are canonical
  evidence — archived, never deleted.

## 7. `.renmark/reports/features/<slug>/{report.md,metrics.json}`

- **Classification:** derived/terminal (rendering of state already proven
  by plan+review artifacts; human-facing, not machine-reingested).
- **Canonical owner:** `renmark/reports.py`.
- **Budget:** 100 feature dirs (warn 80 / 80%, current 17), bytes 500 KB
  (warn 400 KB). No age limit — cheap, keep all at current volume.
- **Rotation:** none needed below budget; above it, move whole
  `<slug>/` dirs for features shipped >180 days ago to
  `.renmark/reports/features/archive/<slug>/`.
- **Stale detection:** none needed (terminal artifact, doesn't get
  superseded — a re-run of the same feature slug creates a new report
  which becomes the newer instance per the global rule).
- **Protection:** not acceptance-critical; may be regenerated in principle
  from plan+review pointers per survey.md item 9, so ordinary
  safe-deletion criteria (regenerable + no cross-ref + past age) apply once
  archived, not full plan/review-level protection.

## 8. `.renmark/rethink/<slug>/*.md` (+ `archive/`)

- **Classification:** canonical for an active or recently-released rethink
  (design record equivalent to a PRD); archived history once the rethink's
  roadmap fully ships.
- **Canonical owner:** rethink pipeline (skill-orchestrated; no dedicated
  `renmark/rethink.py`).
- **Budget:** per-slug file count 12 (the 9-stage contract + archive
  variants), bytes 500 KB per slug. No cross-slug cap — number of rethink
  targets is inherently low-frequency.
- **Rotation:** existing convention generalized as the rule: once a rethink
  slug's roadmap items are all `released`, move the entire `<slug>/`
  directory under `.renmark/rethink/archive/<slug>/` (already demonstrated
  for `renmark-architecture`'s in-slug `archive/`; this contract makes the
  whole-slug move the standard end state instead of a partial in-slug one).
- **Stale detection:** deterministic via `.renmark/roadmap/program.md` —
  a rethink slug is archive-eligible once every work item it originated has
  `status: released` there.
- **Protection:** canonical Owner-approved design decisions — archive-move
  only, never delete, matching plans/reviews.

## 9. `.renmark/roadmap/*.md`

- **Classification:** canonical (active execution plan/backlog).
- **Canonical owner:** `renmark/roadmap.py`, `renmark/program.py`,
  `renmark/program_driver.py`.
- **Budget:** 2 live files (fixed), plus unbounded `archive/` snapshots.
  Byte budget for the live `program.md`: 200 KB warn / 300 KB — beyond
  that, snapshot-and-truncate (see rotation).
- **Rotation:** when `program.md` exceeds its byte budget, snapshot the
  current file verbatim to `.renmark/roadmap/archive/pre-roadmap-program-
  <date>.md` (existing pattern, already observed once in this repo) and
  truncate the live file to only its currently-active/pending items —
  pure filter on each item's `status` field, no LLM call.
- **Stale detection:** any roadmap line item whose linked plan/review has
  reached `released` is a completed-and-archivable item at the next
  rotation pass.
- **Protection:** live `program.md`/canonical roadmap file is protected;
  the resolved duplicate (`.renmark/memory/roadmap.md`, see closing
  section) follows the retirement policy, not deletion.

## 10. `.renmark/specs/*.spec.md` (+ `.brief.md`, `.request.md`)

- **Classification:** canonical (design record, git-committed).
- **Canonical owner:** brainstorm pipeline (`renmark/scan.py`,
  `renmark/loop.py`).
- **Budget:** 100 files soft cap (warn 80 / 80%, current 21), bytes 500 KB
  (warn 400 KB). No age limit.
- **Rotation:** none required at current/projected volume; if the cap is
  ever hit, archive specs whose downstream plan reached `released` more
  than 180 days ago — move only.
- **Stale detection:** a spec is superseded once its downstream plan exists
  and that plan reached `plan-validated` or later in `lifecycle.json`
  (spec's design intent has been absorbed) — informational only, not
  auto-archived below budget.
- **Protection:** full canonical protection, same as plans/specs family —
  archive-move only.

## 11. `.renmark/debug/<session-id>/*`

- **Classification:** ephemeral by design (gitignored, explicitly
  session-isolated) — EXCEPT the `session.md` narrative itself, which
  captures non-regenerable root-cause reasoning and should be treated as a
  lightweight canonical-lite record, not deleted casually.
- **Canonical owner:** `renmark/debug.py`.
- **Budget:** 40 session dirs (warn 32 / 80%, current 12), bytes 1 MB
  (warn 800 KB — the nested `repro-repo/.git` tree is explicitly excluded
  from this budget and gets its own rule below), max age for
  `session.md` alone: 90 days.
- **Rotation/compaction:** `repro-repo/` and any other nested
  reproduction scaffold (identified by containing its own `.git/` dir)
  is auto-deletable per the safe-deletion criteria the moment its parent
  session's root-cause fix is confirmed merged (i.e. the referenced commit
  sha is reachable from `main` and the session's `lifecycle` pointer, if
  any, shows the bug closed) — regenerable via re-running the same repro
  steps, never cross-referenced by other artifacts. `session.md` narratives
  older than 90 days with no inbound reference are also safe-deletion
  eligible (satisfies all five global criteria: ephemeral-classified,
  regenerable only in the weak sense of "the bug is fixed so the repro no
  longer matters," no cross-ref, past age, not the sole/most-recent
  session).
- **Stale detection:** a session is stale once its fix commit sha is
  reachable from `main` (deterministic `git merge-base --is-ancestor`
  check) — the exact trigger already implied by CLAUDE.md's debug-session
  isolation rule.
- **Protection:** none beyond the 90-day narrative floor above; explicitly
  NOT acceptance evidence.

## 12. `.renmark/version/*.zip` + `.renmark/version/v<ver>/`

- **Classification split:** zips = canonical release history (protected,
  explicitly named in intake). Unpacked `v<ver>/` directories =
  **ephemeral/generated — a byte-for-byte duplicate of the sibling zip.**
- **Canonical owner:** `renmark/release.py` (`build_package`,
  `build_version_snapshot`).
- **Named recommendation — RETIRE-UNPACKED-VERSION-TREES:**
  - **Classification:** ephemeral/generated duplicate (not canonical, not
    context-injecting, not read by any production code path per survey.md
    item 4 of §12 — only the directory *name* is read, never file bodies).
  - **Budget:** 0 long-term retained unpacked trees beyond the single
    most-recent version. Zips: unbounded, keep forever (canonical).
  - **Rotation/retirement (three-step, per `artifact-lifecycle.md`):**
    (1) stop generation — change `build_version_snapshot` to stop
    persisting the unpacked `v<ver>/` tree for any version except the one
    just built (or stop unpacking at all, regenerating on demand);
    (2) leave existing unpacked trees for now — this design step doesn't
    delete anything; (3) redirect the one reader (`reports.py::
    _resolve_release_link`) to resolve its release link from the zip
    filename instead of the directory name, so removing older unpacked
    trees never breaks that pointer.
  - **Safe-deletion criteria applied:** each unpacked `v<ver>/` tree older
    than the current version satisfies all five global criteria — fully
    regenerable via `unzip renmark-v<ver>.zip`, zero production reader of
    file bodies, past any reasonable age, and not the sole/most-recent
    tree once at least one unpacked tree is retained for diffing. This is
    the single highest-leverage, lowest-risk auto-deletion candidate in
    the whole survey (~1,730 of ~2,168 files).

## 13. `.renmark/config.json`, `.renmark/README.md`

- **Classification:** `config.json` = active context (small, startup-read,
  canonical config). `README.md` = canonical docs, currently drifted/stale
  per survey.md item 6 (doesn't mention `roadmap/`, `reports/`, `rethink/`,
  `ledger/`).
- **Canonical owner:** `renmark/config.py` (config); Owner/docs authorship
  (README).
- **Budget:** both <5 KB, no growth expected; no rotation needed.
- **Stale detection for `README.md`:** deterministic drift check — README's
  documented directory list vs. the actual top-level dirs under
  `.renmark/` (a simple `os.listdir` diff) flags drift without any LLM
  judgment; Phase 3 should wire this as a hygiene check.
- **Protection:** both canonical, keep forever; `README.md` refresh is
  recommended as a Phase 3 follow-up, not executed here.

---

## Closing: cross-cutting recommendations

### A. Three-way structural-map overlap — resolved

**Canonical home: `.renmark/memory/project-map.md`.** It is the only member
of the trio that is (a) git-committed, (b) explicitly designed for bounded
on-demand reads via `renmark/context.py::load_fragment`, and (c) already the
documented single entry point alongside `INDEX.md` per `.renmark/README.md`.

- `.renmark/audits/inventory-*.md` — **retire from full-body duplication**,
  not from existence. Apply the three-step retirement policy: (1) stop
  generating full structural-content bodies in the inventory writer path
  in `renmark/audit.py`; going forward an inventory run emits only a dated
  *delta* against `project-map.md` (what changed since the last
  `project-map.md` update) plus a `dependency_refs: [".renmark/memory/
  project-map.md"]` pointer; (2) existing inventory files stay on disk,
  eligible for the audits/ rotation rule in §1; (3) any reader currently
  treating an inventory file as the structural source of truth redirects to
  `project-map.md`, backward-compatibly (missing/older inventory files must
  not break anything).
- `.renmark/rethink/<slug>/survey.md` — **derive-from-pointer.** A rethink
  survey MUST open with `dependency_refs: [".renmark/memory/project-map.md"]`
  and restate only the scope-specific delta/detail for its rethink target,
  not the full "what's in this codebase" inventory `project-map.md` already
  covers. This survey.md itself should be treated as the reference example
  going forward (it already cites `intake.md` in `dependency_refs`; add
  `project-map.md` there too on its next revision).
- `project-map.md` itself gets the §5 budget (300 KB) and compaction rule —
  it must not become the new bloat target after absorbing this role.

### B. `.renmark/version/v<ver>/` unpacked trees — see §12

Named recommendation **RETIRE-UNPACKED-VERSION-TREES** fully specified in
§12 above: classification ephemeral/generated duplicate, budget = 0 retained
beyond the single most-recent version, retirement = stop-generate →
leave-existing → redirect the one reader to the zip filename. This is the
single highest-leverage cleanup candidate in the survey by file count
(~1,730 of ~2,168) and is executed only in a future Phase 3, not here.

### C. Memory vs. evidence separation rule

`.renmark/memory/*` holds **current facts only** — the present-tense state
of the project (what exists, what's decided, how to route, what's stale).
`.renmark/rethink/*` and `.renmark/audits/*` hold **historical evidence** —
point-in-time snapshots and judgment records that justified how memory got
to its current state. The deterministic separation test: a file belongs in
`memory/` iff it is continuously overwritten/appended in place to reflect
the *current* truth (no date in the filename, single canonical path per
topic); it belongs in `rethink/`/`audits/` iff it is a **dated, immutable**
snapshot that is never edited after being written (date or sha in the
filename, one file per run). Cross-reference, never duplicate: a memory
file MAY cite a rethink/audit artifact by path in `dependency_refs`; a
rethink/audit artifact MAY cite `project-map.md`/other memory files the same
way; neither ever re-embeds the other's content inline. This resolves
survey.md finding #2 (memory/roadmap.md vs. roadmap/program.md,
memory/analytics.md staleness) the same way: the single mutable canonical
version lives in exactly one of the two families per topic, and the other
either retires (per the three-step policy) or becomes an explicit
`dependency_refs` pointer.

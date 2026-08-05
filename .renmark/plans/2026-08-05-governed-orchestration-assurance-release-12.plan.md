# Plan: Release 12 — Context/memory governance extension + state-fragmentation spike #22 (governed-orchestration-assurance)

**Context.** roadmap.md's Release 12 section closes AC-10 (PRD Req 10):
extend `hygiene.py`'s pruning/categorization toward the proposal's 7-way
category split (stable preferences / canonical artifacts / lifecycle state /
bounded task context / failure-rule registry / receipts / ephemeral
conversation), and resolve the state-fragmentation spike (#22) — whether
`CLAUDE.md`'s documented state-file set is stale relative to what actually
accumulates under `.renmark/`.

**Investigation findings (drive this decomposition):**
- `hygiene.py`'s `ARTIFACT_REGISTRY` already 4-way-classifies every
  `.renmark/` subtree (`active-context` / `canonical-evidence` /
  `archived-history` / `ephemeral`) with budgets and a real
  `validate_registry_compliance` compliance walk. "Pruning" today means:
  scan+archive stale/unreferenced canonical artifacts (`scan_artifacts`),
  age-out+dedupe 3 memory logs (`prune_memory`), plus a type-aware
  ephemeral+regenerable delete pass. The 7-way split the roadmap wants is a
  new, additive **reporting** categorization layered on top of the existing
  4-way `art_class` + `name` fields — it does not touch deletion logic.
- Checkpoint-before-compaction is NOT in `hygiene.py` or `context.py` — it
  lives in `renmark/lifecycle` as `persist_compact_checkpoint`, invoked from
  `renmark/cli/_dispatch_flags.py`'s `--compact-checkpoint` flag, writing
  `.renmark/state/compact_checkpoint.json` (also listed in `hygiene.py`'s
  `state-live` registry entry). Release 12 reuses this Keep item by
  reference only — no code change to it.
- `recurrence.failure_rules_due_for_review(repo, *, as_of=None) ->
  tuple[FailureRule, ...]` (Release 10, landed) is read-only: returns
  `status=="active"` rules whose `review_after` has passed. Its own
  docstring names this exact hygiene call site as its intended, still-unwired
  consumer. Signature confirmed stable for direct import.
- `context.py`'s `assert_metadata_only` (raises `ValueError` on a non-bare
  skill-name reference) and its `ContextKind` taxonomy
  (`STATIC`/`DYNAMIC`/`MEMORY`/`TASK_LOCAL`) are the Keep item named in the
  roadmap's compatibility guarantee #7. **This plan does not touch
  `context.py` in any task.**
- `plugin/skills/hygiene/SKILL.md` documents 3 subcommands (`scan`/
  `prune`/`all`) plus read-only `budget`/`validate`, one relayed-verbatim
  stdout contract ("Pass the bounded stdout through to the user unchanged").
  A new category-report line and a new `FAILURE-RULES due=N` line fit
  additively at the end of the existing scan/all stdout block without
  restructuring the skill; Task 3 updates the skill doc's "Relay the
  result" section to describe the new line(s).
- **State-fragmentation spike finding (concrete, narrow):** `CLAUDE.md`
  §"All renmark output stays inside the project" (mirrored verbatim in
  `AGENTS.md`) lists canonical homes for 9 categories (specs, plans,
  reviews, research, runtime/state, memory, logs, debug, audits) but is
  missing 6 categories that `hygiene.py`'s own `ARTIFACT_REGISTRY` — the
  actual source of truth — already governs and that exist live on disk
  today (`ls -la .renmark/` confirmed all 6 present): `analytics/`,
  `ledger/`, `reports/`, `rethink/`, `roadmap/`, `version/`. This is exactly
  the "one missing bullet in an existing list" case the HIGH CARE note
  allows as a narrow correction — not a rewrite. Task 2 below performs this
  correction, mirrored into both files in one task, per CLAUDE.md's own
  "Mirror all rule changes in AGENTS.md in the same commit" rule.
- **Role-capability caveat (non-blocking, flagged not fixed).**
  `subagent_profiles.PROFILES["docs-editor"].allowed_targets =
  "**/*.md, plugin/skills/**/*.md, docs/**"` is matched via
  `fnmatch.fnmatch(path, glob)` in `subagent_gate._envelope_path_verdict`.
  Confirmed by direct test: `fnmatch.fnmatch('CLAUDE.md', '**/*.md')` and
  `fnmatch.fnmatch('AGENTS.md', '**/*.md')` both return `False` — fnmatch's
  `**` requires a literal `/` to be present in the matched string, so
  repo-root files never match a `**/`-prefixed glob. Today this is
  non-blocking: Release 6 (capability-envelope wiring) has not landed yet
  in this program's execution order and `dispatch_wave()` does not call
  `check_capability_envelope` for the `path` dimension yet (confirmed by
  reading Release 6's own migration steps — "wire `dispatch_wave()` to
  actually call `enforce_wave_dispatch_scopes` ... currently never called").
  So `docs-editor` can practically write `CLAUDE.md`/`AGENTS.md` today. This
  is an out-of-scope gap in `subagent_profiles.py`'s glob pattern, not this
  release's concern — noted here for the record, not fixed in this plan.

**Compatibility guarantees this plan honors:**
(a) `context.py`'s taxonomy/`assert_metadata_only` stays completely
untouched — no task targets `renmark/context.py` or
`tests/test_context*.py`'s existing assertions (Task 4 only adds a new
byte-unchanged guard test, it does not modify `context.py` itself).
(b) The CLAUDE.md/AGENTS.md edit (Task 2) is narrow and corrective only —
one bullet-list addition, not a rewrite — and mirrors identically into both
files in the same task, never split across two tasks.
(c) The spike (Task 1) is investigation-only and produces a finding doc; it
does not edit `CLAUDE.md` itself. Because the spike (pre-planning
investigation, above) already found a concrete, narrow, warranted
correction, Task 2 IS included in this plan — it is not dropped.

---

### Task 1: State-fragmentation spike finding doc
- **mode:** A
- **target:** .renmark/rethink/governed-orchestration-assurance/release-12-state-fragmentation-spike.md
- **complexity:** medium
- **executor:** sonnet
- **role:** docs-editor
- **role_reason:** n/a (docs-editor is the matching profile)
- **parallel_group:** 1
- **est_tokens:** 900
- **est_cost_usd:** 0.0327
- **verifier:** test -f .renmark/rethink/governed-orchestration-assurance/release-12-state-fragmentation-spike.md
- **serves:** AC-10 (Req 10)
- **spec:**
  Read-only investigation, no CLAUDE.md/AGENTS.md edit in this task. Write a
  finding doc with standard artifact metadata frontmatter
  (`artifact_type: spike-finding`, `schema_version: 1`, `created_at`,
  `source_sha`, `related_plan: .renmark/plans/2026-08-05-governed-
  orchestration-assurance-release-12.plan.md`, `generator: sonnet`,
  `dependency_refs: [CLAUDE.md, AGENTS.md, renmark/hygiene.py]`). Body:
  (1) list every canonical-home bullet CLAUDE.md's "All renmark output
  stays inside the project" section currently documents; (2) cross-check
  against `renmark/hygiene.py`'s `ARTIFACT_REGISTRY` names and against a
  fresh `ls -la .renmark/` — confirm the 6 missing categories (`analytics`,
  `ledger`, `reports`, `rethink`, `roadmap`, `version`); (3) confirm
  `.renmark/memory/failure_rules.jsonl` (Release 10) is covered by the
  existing `memory→.renmark/memory/` bullet (it is — no new bullet needed
  for it specifically, only the 6 missing top-level categories need adding);
  (4) state the conclusion explicitly: CLAUDE.md's canonical-homes list IS
  stale, the fix is exactly 6 items appended to the existing comma-list in
  one sentence, not a rewrite, and name Task 2 of this plan as the task that
  performs the fix (do not perform the edit here). Do not touch
  `CLAUDE.md`, `AGENTS.md`, or any `.py` file in this task.

### Task 2: CLAUDE.md + AGENTS.md canonical-homes correction
- **mode:** B
- **target:** CLAUDE.md
- **complexity:** simple
- **executor:** sonnet
- **role:** docs-editor
- **role_reason:** n/a (docs-editor is the matching profile)
- **parallel_group:** 2
- **est_tokens:** 350
- **est_cost_usd:** 0.0311
- **verifier:** grep -q "analytics→" CLAUDE.md && grep -q "analytics→" AGENTS.md && grep -q "version→" CLAUDE.md && grep -q "version→" AGENTS.md
- **serves:** AC-10 (Req 10)
- **spec:**
  Narrow, corrective-only edit per Task 1's finding — NOT a rewrite. In
  BOTH `CLAUDE.md` and `AGENTS.md`'s "All renmark output stays inside the
  project" section, extend the existing "Canonical homes:" comma-separated
  list (currently ending "...debug→`.renmark/debug/<session-id>/`,
  audits→`.renmark/audits/`.") by appending exactly 6 new entries in the
  same `name→path` format, sourced from `renmark/hygiene.py`'s
  `ARTIFACT_REGISTRY`: `analytics→.renmark/analytics/`,
  `ledger→.renmark/ledger/`, `reports→.renmark/reports/`,
  `rethink→.renmark/rethink/`, `roadmap→.renmark/roadmap/`,
  `version→.renmark/version/`. Make the identical textual change in both
  files (CLAUDE.md's paragraph and AGENTS.md's mirrored paragraph) in this
  one task — do not split the mirror into a second task, do not touch any
  other line, section, or rule in either file, do not change wording
  elsewhere in the sentence.

### Task 3: hygiene.py — 7-way categorization + failure-rule review sweep
- **mode:** B
- **target:** renmark/hygiene.py
- **complexity:** medium
- **executor:** sonnet
- **role:** code-implementer
- **role_reason:** n/a (code-implementer is the matching profile)
- **parallel_group:** 3
- **est_tokens:** 2200
- **est_cost_usd:** 0.0366
- **verifier:** python3 -m py_compile renmark/hygiene.py
- **serves:** AC-10 (Req 10)
- **spec:**
  Additive-only — do not change existing deletion/archival logic, do not
  touch `context.py`. (a) Add a `SEVEN_WAY_CATEGORY` mapping (or a small
  `categorize_seven_way(spec: ArtifactTypeSpec) -> str` function) that maps
  every existing `ARTIFACT_REGISTRY` entry's `name`/`art_class`/`owner` onto
  one of the 7 proposal categories: `stable_preferences` (memory except
  failure_rules.jsonl), `canonical_artifacts` (plans, reviews, specs,
  rethink, roadmap, version-zip), `lifecycle_state` (state-live), `bounded_
  task_context` (state-scratch), `failure_rule_registry` (the
  `.renmark/memory/failure_rules.jsonl` file specifically, split out of the
  generic `memory` entry), `receipts` (ledger, reports, audits), `ephemeral_
  conversation` (debug, version-unpacked). Do this as a pure, additive
  reporting function — no new registry entries, no change to `art_class`
  values or budgets on the existing `ArtifactTypeSpec` tuples. (b) Add a
  `compute_seven_way_report(repo: Path) -> dict[str, list[str]]` (category
  name -> list of registry `name`s in it) built on top of (a) and
  `ARTIFACT_REGISTRY`, plus a CLI `budget` (or a new lightweight
  subcommand/flag) output line: `CATEGORIES  <cat1>=<n1>  <cat2>=<n2> ...`
  covering all 7 categories, non-breaking addition to existing `budget`
  output. (c) Import `renmark.recurrence` and add a helper
  `_failure_rules_due(repo: Path) -> int` calling `recurrence.
  failure_rules_due_for_review(repo)` (read-only, never mutates rule
  status), wrapped in try/except returning 0 on any error (recurrence module
  or file may not exist in every repo state) so hygiene never raises on
  this new call. Surface the count as a new stdout line in `scan`/`all`
  subcommands: `FAILURE-RULES  due_for_review=<n>` — printed only when
  `run_scan` is true, right after the existing `HYGIENE` line, following the
  file's existing "print one bounded status line" convention. This is
  read-only surfacing only — do not call `activate_failure_rule` or change
  any rule's `status`/`review_after`.

### Task 4: hygiene.py 7-way categorization + review-sweep tests
- **mode:** A
- **target:** tests/test_hygiene_release12_categorization.py
- **complexity:** medium
- **executor:** codex
- **role:** test-writer
- **role_reason:** n/a (test-writer is the matching profile)
- **parallel_group:** 4
- **est_tokens:** 1400
- **est_cost_usd:** 0.05
- **verifier:** pytest -q tests/test_hygiene_release12_categorization.py
- **serves:** AC-10 (Req 10)
- **spec:**
  Depends on Task 3 landing first (same module). Write tests covering: (1)
  `compute_seven_way_report`/`categorize_seven_way` classifies every entry
  in `ARTIFACT_REGISTRY` into exactly one of the 7 named categories (no
  entry unclassified, no entry in two categories); (2) seeding a due-for-
  review rule via `recurrence.propose_failure_rule(...)` +
  `recurrence.activate_failure_rule(repo, rule_id)` with a past
  `review_after`, then confirming `python -m renmark.hygiene scan` (or the
  new subcommand/flag) stdout contains a `FAILURE-RULES` line reporting
  `due_for_review=1`, and that the rule's `status` is unchanged
  (`"active"`) after the call — hygiene must not mutate it; (3) a guard
  test asserting `renmark/context.py`'s `assert_metadata_only` and the
  `ContextKind` enum's member set are byte-for-byte unchanged versus a
  captured snapshot (e.g. hash the function's `__code__.co_code` or the
  source text of `context.py` at test-collection time against a checked-in
  expected value, OR simply assert the file's git blob sha at HEAD is
  unchanged by re-reading `renmark/context.py` and comparing its full text
  to a value captured before this release's tasks ran — whichever the
  test-writer finds simpler to keep deterministic and dependency-free).
  Use `tmp_path`-based repo fixtures; do not touch the real project's
  `.renmark/` state.

### Task 5: hygiene skill doc — new stdout lines documented
- **mode:** B
- **target:** plugin/skills/hygiene/SKILL.md
- **complexity:** simple
- **executor:** sonnet
- **role:** docs-editor
- **role_reason:** n/a (docs-editor is the matching profile)
- **parallel_group:** 5
- **est_tokens:** 400
- **est_cost_usd:** 0.0312
- **verifier:** grep -q "CATEGORIES" plugin/skills/hygiene/SKILL.md && grep -q "FAILURE-RULES" plugin/skills/hygiene/SKILL.md
- **serves:** AC-10 (Req 10)
- **spec:**
  Depends on Task 3 landing first (documents its exact output). In the
  "### 2. Relay the result" section, add one sentence noting that `scan`/
  `all` output may now also include a `CATEGORIES ...` line (7-way
  categorization) and a `FAILURE-RULES due_for_review=<n>` line, both part
  of the same "relay verbatim, do not paraphrase" contract as the existing
  `HYGIENE`/`MEMORY`/`ERRORS` lines. Do not restructure the skill, do not
  add new subcommands to the "## Steps" numbered list, do not change any
  other section.

---

## Cost preview

| Task | Executor | Est. tokens (incl. overhead) | Est. cost |
|---|---|---|---|
| 1. State-fragmentation spike | sonnet | 900 + 10,000 = 10,900 | $0.0327 |
| 2. CLAUDE.md + AGENTS.md correction | sonnet | 350 + 10,000 = 10,350 | $0.0311 |
| 3. hygiene.py categorization + review sweep | sonnet | 2,200 + 10,000 = 12,200 | $0.0366 |
| 4. hygiene.py tests | codex | 1,400 (no overhead) | $0.05 |
| 5. hygiene SKILL.md doc update | sonnet | 400 + 10,000 = 10,400 | $0.0312 |

**Total tasks:** 5 (5 parallel groups — sequential: spike before the
CLAUDE.md fix it justifies; the CLAUDE.md fix is independent of the code
work; hygiene.py code before its own tests and before its own skill-doc
update).
**Total estimated tokens (incl. overhead):** ~45,250
**Total estimated cost: ~$0.1816**
**Executors:** sonnet×4, codex×1.
**No opus/fable** — none of this release's tasks meet the escalation bar
(no architecture fork, no adversarial review, no state-machine design).

---
artifact_type: plan
schema_version: 1
created_at: 2026-06-12T22:30:00+00:00
source_sha: HEAD
related_spec: .renmark/reviews/2026-06-12-doc-slimming-postship-review.md
generator: fable
dependency_refs: [.renmark/reviews/2026-06-12-doc-slimming-postship-review.md]
---

# doc-slimming-fixes — v0.14.3 fast-follow

**Goal:** fix the regressions the post-ship review confirmed in v0.14.2's doc-slimming —
restore the governance clauses the terse-rewrite silently dropped, fix the 1-of-4 mirror
drift, correct stale version stamps, and make the changelog/audit numbers honest. All four
docs stay ≤200 lines (brevity never required dropping the mandates — restore terse-but-
complete). No runtime change. Byte-identity contract holds: CLAUDE template authoritative,
CLAUDE.md copies its blocks verbatim, AGENTS mirrors in prose.

### Task 1: restore dropped clauses in CLAUDE template (authoritative)
- **mode:** B
- **target:** plugin/templates/CLAUDE.md.template
- **complexity:** hard
- **executor:** sonnet
- **parallel_group:** 1
- **est_tokens:** 1400
- **est_cost_usd:** 0.034
- **verifier:** test $(wc -l < plugin/templates/CLAUDE.md.template) -le 200 && grep -qi 'run_in_background' plugin/templates/CLAUDE.md.template && grep -qi 'renmark:resume' plugin/templates/CLAUDE.md.template && grep -qi 'compile' plugin/templates/CLAUDE.md.template && grep -qi 'never after' plugin/templates/CLAUDE.md.template && python3 -m renmark.lint 2>&1 | tail -1
- **serves:** REQ-5
- **spec:**
  Restore these dropped mandates into their existing BEGIN/END blocks, terse-but-complete
  (do NOT exceed 200 lines — compress elsewhere if needed; AGENTS proves the clauses fit):
  - `parallelism-rule`: add back "Long-running probes → background `Bash` with
    `run_in_background: true`." AND restore the "read-only verification runs parallel
    alongside code work, **never after**" timing prohibition (the "never after" clause).
  - `lifecycle-rule`: restore the cold-start recovery mandate — "after `/clear`, run
    `/renmark:resume`" (one line).
  - `commit-cadence-rule`: restore "compile" — "each commit must compile and pass lint".
  - `refactor-safety-rule`: restore the regression-diagnosis step + exclusivity — "If tests
    regress: `git diff HEAD~1`, identify cause, revert targeted files only."
  - `failure-transparency-rule`: restore the field VALUE constraints — completion_state
    `complete|partial|failed`, confidence `low|medium|high`, validation_status
    `validated|unvalidated|failed`, retry_count "integer, monotonically increasing".
  - `canonical-state-rule`: restore "structured summaries inside artifact files" to the list.
  - `artifact-governance-rule`: restore "Track stale artifacts / prefer invalidation over
    silent drift" + the field value formats.
  Also fix the typo "algorithms/ refactors" → "algorithms/refactors". Do NOT rename/reorder
  blocks; keep all 23. Run the verifier (≤200 + the grep set + lint) before returning.

### Task 2: sync CLAUDE.md to the restored template
- **mode:** B
- **target:** CLAUDE.md
- **complexity:** hard
- **executor:** sonnet
- **parallel_group:** 2
- **est_tokens:** 1400
- **est_cost_usd:** 0.034
- **verifier:** test $(wc -l < CLAUDE.md) -le 200 && grep -qi 'run_in_background' CLAUDE.md && grep -qi 'never after' CLAUDE.md && ! grep -q 'v0.10.0' CLAUDE.md && python3 -m renmark.lint 2>&1 | tail -1
- **serves:** REQ-5
- **spec:**
  Reproduce the restored BEGIN/END blocks from the now-fixed plugin/templates/CLAUDE.md.template
  (Task 1, committed) BYTE-FOR-BYTE into CLAUDE.md (read the template; copy each block incl.
  the `## Heading` verbatim — the byte-identity contract: merge_rule_blocks/audit must see no
  drift). Author only the non-block project-stub: in the "What this project is" description,
  replace the stale "(v0.10.0)" with the current version read from the VERSION file (or drop
  the inline version entirely so it can't go stale again — prefer dropping it). Keep ≤200.
  Run the verifier (incl. the `! grep v0.10.0` staleness check) before returning.

### Task 3: AGENTS template — never-after + mirror restored clauses
- **mode:** B
- **target:** plugin/templates/AGENTS.md.template
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 2
- **est_tokens:** 700
- **est_cost_usd:** 0.033
- **verifier:** test $(wc -l < plugin/templates/AGENTS.md.template) -le 200 && grep -qi 'never after' plugin/templates/AGENTS.md.template && grep -qi 'compile' plugin/templates/AGENTS.md.template && python3 -m renmark.lint 2>&1 | tail -1
- **serves:** REQ-5
- **spec:**
  AGENTS template already HAS the artifact-homes + most clauses (confirmed by review — do not
  re-add those). Ensure its prose mirror carries the same restored mandates Task 1 put in the
  CLAUDE template where AGENTS should mirror them: the parallelism "never after" timing clause
  (AGENTS currently is the ONLY file that has it — keep it), the commit "compile" gate (was
  dropped from AGENTS too), and the long-running-probes background-Bash note. Marker-free
  (no BEGIN: markers — pinned invariant). Keep ≤200. Match CLAUDE's terse wording for shared
  clauses.

### Task 4: AGENTS.md — mirror + version stamp
- **mode:** B
- **target:** AGENTS.md
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 3
- **est_tokens:** 700
- **est_cost_usd:** 0.033
- **verifier:** test $(wc -l < AGENTS.md) -le 200 && grep -qi 'never after' AGENTS.md && grep -qi 'compile' AGENTS.md && ! grep -q 'v0.10.0' AGENTS.md && python3 -m renmark.lint 2>&1 | tail -1
- **serves:** REQ-5
- **spec:**
  Mirror the fixed AGENTS template (Task 3, committed) into repo AGENTS.md: add the "never
  after" clause, restore the "compile" gate + background-Bash note, keeping shared rule prose
  identical with the terse CLAUDE.md. Replace the stale "(v0.10.0)" in the project description
  with the current VERSION (or drop the inline version — match whatever Task 2 did in CLAUDE.md).
  Keep this repo's real renmark specifics + AGENTS-only sections. Keep ≤200.

### Task 5: correct CHANGELOG + footprint-audit numbers
- **mode:** B
- **target:** CHANGELOG.md
- **complexity:** medium
- **executor:** haiku
- **parallel_group:** 2
- **est_tokens:** 500
- **est_cost_usd:** 0.001
- **verifier:** grep -qi '35%\|GREW\|grew' CHANGELOG.md && python3 -m py_compile /dev/null 2>/dev/null; grep -q 'Files changed' CHANGELOG.md
- **serves:** REQ-9
- **spec:**
  The v0.14.2 CHANGELOG entry oversold the result. Append a NEW honest correction entry (do
  NOT rewrite history destructively — add a "## [2026-06-12] — v0.14.2 metrics correction"
  entry near the top) stating the verified figures from the review
  (.renmark/reviews/2026-06-12-doc-slimming-postship-review.md): CLAUDE.md.template
  5226→3270 tok (-37%), CLAUDE.md 5502→3602 tok (-35%, ~58% lines), and that the AGENTS pair
  GREW in tokens (template 2410→2677 +11%, AGENTS.md 2576→3434 +33%) — only line counts fell;
  AGENTS.md is not loaded by Claude Code so per-session Claude impact = the CLAUDE.md saving
  only. Note the v0.14.2 entry omitted the "Files changed:" field. This entry MUST include a
  proper "**Files changed:**" field listing the corrected files. Keep it bounded (G3).

## Cost preview

| # | Task | Executor | est_tokens | est cost |
|---|---|---|---|---|
| 1 | CLAUDE template restore (authoritative) | sonnet | 1400 | $0.034 |
| 2 | CLAUDE.md sync + version | sonnet | 1400 | $0.034 |
| 3 | AGENTS template mirror | sonnet | 700 | $0.033 |
| 4 | AGENTS.md mirror + version | sonnet | 700 | $0.033 |
| 5 | CHANGELOG/audit numbers | haiku | 500 | $0.001 |

Haiku/sonnet costs include the ~10k-token Agent overhead per task (honest accounting).
**Total: ~$0.14 · ~57k tokens incl. overhead · 5 tasks (wave 1: task 1 → wave 2: tasks 2,3,5 parallel → wave 3: task 4). Byte-identity forces template-before-CLAUDE.md.**

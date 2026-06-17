<!--
artifact_type: plan
schema_version: 1
created_at: 2026-06-17T02:26:01Z
source_sha: b4dfb1ca7411b642f9a2def5731fa9b2e5df3097
related_plan: 2026-06-16-finish-branch-disposition
generator: opus
dependency_refs:
  - renmark/analytics.py
  - plugin/skills/finish/SKILL.md
  - renmark/backlog.py
-->

# Plan: finish-branch-disposition — close out analytics branch_disposition on merge/release

## Context

`/renmark:analytics` reports merged/released feature runs as perpetually `open`.
Root cause: `finish/SKILL.md` step 2.5 records the feature run with
`branch_disposition="open"` (fresh finish), and the `[m]` merge and `[r]` release
paths **never** record a closing terminal disposition. `analytics._agg_features`
counts `branch_disposition` **per row**, so the durable fix must **transform the
existing open row in place**, not append a second row (appending double-counts).

Source-fix-only scope: no one-time backfill of stale rows, no scan-proposer wiring.

**File-scope correction (vs. the original request):** the finish merge/release
logic lives in `plugin/skills/finish/SKILL.md` (inline Python the skill runs), NOT
in `renmark/cli/_engine.py` — `_engine.py` has no disposition code. So the fix is
(1) a transform helper in `renmark/analytics.py` and (2) wiring in `finish/SKILL.md`.

**Canonical terminal value:** `backlog.DISPOSITIONS = ("merged-deleted",
"abandoned-deleted", "kept")`. A merged-then-deleted branch closes to
`"merged-deleted"`; release is cut from `main` after the merge (branch already
gone), so it also closes to `"merged-deleted"`.

**Reuse check:** `none` — no existing transform/close-out function; `record_feature_run`
is append-only. PRD alignment: `aligned` (REQ-15 names branch dispositions explicitly).

---

### Task 1: analytics close-out helper (row transform, in place)
- **mode:** B
- **target:** renmark/analytics.py
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 1
- **est_tokens:** 1200
- **est_cost_usd:** 0.034
- **serves:** REQ-15
- **verifier:** `.venv/bin/python3 -c "from renmark.analytics import close_feature_disposition" && .venv/bin/python3 -m py_compile renmark/analytics.py`
- **spec:**
  Add a new public function to `renmark/analytics.py`:

  ```python
  def close_feature_disposition(
      repo: str | Path,
      *,
      feature: str,
      sha: str,
      disposition: str = "merged-deleted",
  ) -> bool:
  ```

  Behavior — **transform, never append**:
  1. Read all rows from `analytics_dir(repo) / FEATURE_RUNS_LEDGER` via `read_jsonl`.
  2. Find rows matching BOTH `feature` and `sha` whose current `branch_disposition`
     is **non-terminal** — treat empty string, `"open"`, and `"merged"` (the legacy
     non-canonical value written by finish step 2.5) as non-terminal. Set their
     `branch_disposition` to the passed `disposition`.
  3. If at least one row was changed, rewrite the **entire** ledger atomically using
     the same pattern already in this module's `summary.json` writer
     (`tempfile.mkstemp(dir=path.parent, suffix=".tmp")` → write all lines →
     `os.replace`). Return `True`.
  4. If no matching non-terminal row exists (already terminal, or feature/sha absent),
     it is a **no-op**: do not append, do not rewrite, return `False`. This makes the
     call idempotent and safe to re-run.
  5. Like `_append`, analytics is **observational, never load-bearing**: wrap IO in
     try/except and swallow `(OSError, TypeError, ValueError)` returning `False` — never raise.

  Add `"close_feature_disposition"` to the module `__all__`/exports list (near
  `FEATURE_RUNS_LEDGER` at line ~718). Do NOT modify `record_feature_run`,
  `_agg_features`, or any other function. Write each ledger line with the same
  compact `json.dumps(row, separators=(",", ":"))` form `_append` uses.

  Do not change: the append-only contract of `record_feature_run`; the per-row
  counting in `_agg_features`.

### Task 2: tests for close_feature_disposition
- **mode:** B
- **target:** tests/test_reports_analytics.py
- **complexity:** medium
- **executor:** codex
- **parallel_group:** 2
- **est_tokens:** 1600
- **est_cost_usd:** 0.032
- **serves:** REQ-15
- **verifier:** `bash -c 'set -o pipefail; .venv/bin/python3 -m pytest tests/test_reports_analytics.py -q --tb=line 2>&1 | tail -n 5'`
- **spec:**
  Add tests for `renmark.analytics.close_feature_disposition` to the existing
  `tests/test_reports_analytics.py` (match the file's existing fixture/tmp-repo
  style — use `record_feature_run` to seed an `open` row, then close it). Cover:

  1. **Transform, not append:** seed one `branch_disposition="open"` row for
     `(feature, sha)`; call `close_feature_disposition(..., disposition="merged-deleted")`;
     assert it returns `True`, the ledger still has **exactly one** row for that
     `(feature, sha)`, and that row's `branch_disposition == "merged-deleted"`.
  2. **No double-count in rollup:** after the transform, build the summary
     (`_agg_features` via the public summary path used elsewhere in this test file)
     and assert `branch_dispositions` counts `merged-deleted: 1` and `open: 0`
     (not both).
  3. **Idempotent:** calling `close_feature_disposition` a second time returns
     `False` and leaves the ledger unchanged (row count + disposition stable).
  4. **Absent feature/sha:** calling on a `(feature, sha)` that has no row returns
     `False` and appends nothing (ledger length unchanged).
  5. **Legacy "merged" value is treated as non-terminal:** a row with
     `branch_disposition="merged"` is transformed to `"merged-deleted"`.

  Depends on Task 1 (the function must exist). Touches a different file from Tasks
  1 and 3, so it runs in wave 2.

### Task 3: wire close-out into finish [m] merge and [r] release paths
- **mode:** B
- **target:** plugin/skills/finish/SKILL.md
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 2
- **est_tokens:** 1100
- **est_cost_usd:** 0.033
- **serves:** REQ-15
- **verifier:** `grep -q "close_feature_disposition" plugin/skills/finish/SKILL.md`
- **spec:**
  Edit `plugin/skills/finish/SKILL.md` to record the terminal disposition by calling
  the new helper on branch close. Do NOT touch step 2.5's initial `open` recording —
  that stays; the close-out transforms it later.

  1. **`[m]` Merge path (§3 "[m] Merge"):** after the branch is merged into `main`,
     pushed, and the feature branch deleted, add a **non-blocking** analytics close-out
     (wrap in try/except, log + continue — mirror the "non-blocking" discipline already
     stated for step 2.5):
     ```python
     from renmark import analytics
     analytics.close_feature_disposition(
         repo, feature=feature_name, sha=sha, disposition="merged-deleted")
     ```
     Use the `feature_name`/`sha` already computed in step 2.5 (re-derive from
     `lifecycle.read_lifecycle` + `git rev-parse HEAD` if they aren't in scope at that
     point in the skill flow). The merge `sha` to close is the **feature's recorded
     sha** (the one step 2.5 used), so the open row is matched.
  2. **`[r]` Release path (§4 "4c-post"):** in the post-release block (after
     `record_event(... kind="release" ...)` and **before** `clear_lifecycle`), add the
     same non-blocking close-out call with `disposition="merged-deleted"` (release is
     cut from `main` after merge — the branch is already gone).
  3. Add a one-sentence note near step 2.5 explaining that the `open` row recorded
     there is intentionally transformed to its terminal disposition by the `[m]`/`[r]`
     close-out (so a reader doesn't "fix" 2.5 to write a terminal value directly, which
     would break the fresh-finish case where the branch isn't yet closed).

  Do not change: the next-steps menu structure; the PR `[p]` path (out of scope — the
  remote merge disposition isn't observable locally); release packaging/tag steps.
  This is a skill-doc edit (the SKILL's inline Python is the "code") — no AGENTS.md
  mirror needed (only rule-block changes mirror to AGENTS.md, not skill files).

---

## Cost preview (honest — includes ~10k Agent overhead per Claude task)

| Task | Executor | Tokens (incl. overhead) | Cost |
|---|---|---|---|
| 1. analytics helper | sonnet | ~11.2k | $0.034 |
| 2. tests | codex | ~1.6k (no agent overhead) | $0.032 |
| 3. finish SKILL wiring | sonnet | ~11.1k | $0.033 |

**Total: ~23.9k tokens · ~$0.10**

Executors: sonnet×2, codex×1.
Waves: wave 1 = Task 1; wave 2 = Tasks 2 + 3 (parallel — disjoint files, both depend on Task 1).

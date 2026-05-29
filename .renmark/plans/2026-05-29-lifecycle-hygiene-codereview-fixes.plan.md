---
artifact_type: plan
schema_version: 1
created_at: 2026-05-29T00:00:00Z
source_sha: 7905b7b
generator: opus
related_spec: null
related_plan: .renmark/plans/2026-05-29-lifecycle-hygiene.plan.md
related_review: .renmark/reviews/2026-05-29-bee86c0.review.md
stale_after: 2026-08-29T00:00:00Z
dependency_refs:
  - .renmark/reviews/2026-05-29-bee86c0.review.md
---

# Lifecycle Hygiene — codereview Major Fixes (4)

**Branch:** `feature/lifecycle-hygiene` (same branch — fixes ship with v0.5.6, not a separate release)
**Base sha:** `7905b7b`
**Goal:** Fix the 4 Major findings from `.renmark/reviews/2026-05-29-bee86c0.review.md` so v0.5.6 ships with the hygiene helpers actually working on real renmark memory files (not just the synthetic H2 cases the original tests covered).

The Minor finding (#5: `_engine.py:779` escalation hook is dead code) is by design per T4 of the original plan (optional kwarg, callers landed in follow-up). Not included here.

## Findings being fixed

| # | File | What | Severity |
|---|------|------|----------|
| 1 | `renmark/hygiene.py:196` | Lifecycle artifact refs compared as raw strings — abs vs rel paths mis-match | Major |
| 2 | `renmark/memory.py:391` | `dedupe_memory_log` parses `##` but real files use `###` / bullets | Major |
| 3 | `renmark/memory.py:461` | `age_out_memory_log` — same parser issue | Major |
| 4 | `renmark/lifecycle.py:358` | `validate_artifact_refs` accepts abs paths + `..`-escaping | Major |

## Tasks

### Task 1: memory.py — schema-aware entry parsers
- **mode:** B
- **target:** renmark/memory.py
- **complexity:** hard
- **executor:** opus
- **parallel_group:** 1
- **est_tokens:** 3000
- **est_cost_usd:** 0.195
- **verifier:** python3 -c "from renmark.memory import dedupe_memory_log, age_out_memory_log; print('imports OK')"
- **spec:**
  Fix codereview findings #2 and #3: rework both `dedupe_memory_log` and `age_out_memory_log` to parse the real on-disk schemas, not synthetic H2 sections.

  **Inspect existing templates first** to lock in the actual schemas. Read these files for ground truth:
  - `plugin/templates/memory/features.md.template` — features.md entry shape
  - `plugin/templates/memory/bugs.md.template` — bugs.md entry shape
  - `plugin/templates/memory/learnings.md.template` — learnings.md entry shape
  - Also re-read `log_feature`, `log_bug`, and `append_learning` in `renmark/memory.py` — they produce the actual entries; the readers must round-trip with the writers.

  **Schema observations** (verify against the templates):
  - `features.md` — each shipped/in-progress/planned entry is `### YYYY-MM-DD — Title` followed by bold-key lines (`**Files:**`, `**Spec:**`, `**Plan:**`, `**Commits:**`), optional description, then `---`. Entries live under H2 section headers (`## Shipped`, `## In progress`, `## Planned`).
  - `bugs.md` — each entry is `### YYYY-MM-DD — Title` followed by `**Severity:**`, `**Symptom:**`, etc. Entries under H2 sections (`## Open`, `## Fixed`).
  - `learnings.md` — schema differs. Re-check the template; `append_learning` produces a different shape (likely a flat bullet or a `### YYYY-MM-DD —` entry under a section). Whatever the template says, that's the contract.

  **New abstraction:**
  Introduce a small internal helper `_parse_memory_entries(text: str, schema: str) -> list[_MemoryEntry]` (private; not exported). `_MemoryEntry` is a small dataclass:
  ```python
  @dataclass(frozen=True)
  class _MemoryEntry:
      schema: str             # "features" | "bugs" | "learnings"
      title: str              # the entry title (after the date) — empty for bullet-only schemas
      date: str | None        # parsed YYYY-MM-DD or None if not parseable
      raw: str                # the exact text of this entry, including trailing separator
      start: int              # offset in source text where entry begins
      end: int                # offset where entry ends (exclusive)
      section_header: str     # the enclosing "## Section" header (or "" if top-level)
  ```

  The parser must:
  - Walk by `###` headers within each `## Section`. For learnings.md, if the template uses bullets, walk by bullet (`-` or `*`) at column zero.
  - Capture the section header so age-out can re-insert into the SAME section in the archive.
  - Be lenient: entries that don't match the schema are skipped (not raised) so partial drift doesn't crash dedupe.

  **Rewire `dedupe_memory_log(repo, name, *, dry_run=False)`:**
  - Determine schema from `name`: `features.md` → `"features"`, `bugs.md` → `"bugs"`, `learnings.md` → `"learnings"`.
  - Call `_parse_memory_entries`. Compute signature `(entry.title.strip(), sha256(entry.raw.strip())[:12])`.
  - Remove later duplicates (keep first occurrence, which is newest under newest-first convention). Returns count removed.
  - For dry_run=True, count without writing.
  - The existing curated-file ValueError guard MUST be preserved unchanged.

  **Rewire `age_out_memory_log(repo, name, days, archive_root, *, dry_run=False)`:**
  - Same schema dispatch.
  - For each entry: use `entry.date` (None means KEEP).
  - Move entries older than `days` into `archive_root / "memory" / name`, appending. Preserve the enclosing section header on first move (so the archive file has `## Open\n\n### old entry…` and not just an orphaned entry).
  - For dry_run=True, count without writing.
  - The existing curated-file ValueError guard MUST be preserved unchanged.

  **Do NOT touch** `log_decision`, `log_decision`'s idempotency check, or `log_escalation_decision`. Those don't have this issue.

  **Stdlib only.** Mypy strict clean. Ruff format. The new `_parse_memory_entries` should be ~50–100 lines.

  After the rewrite, the existing `tests/test_memory.py` test cases that assumed H2 boundaries will fail. Task 4 rewrites those tests against the real schemas — sequence the work so the test rewrite lands together with this code change.

### Task 2: hygiene.py — normalize lifecycle artifact paths
- **mode:** B
- **target:** renmark/hygiene.py
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 1
- **est_tokens:** 500
- **est_cost_usd:** 0.032
- **verifier:** python3 -c "from renmark.hygiene import scan_artifacts; print('imports OK')"
- **spec:**
  Fix codereview finding #1: lifecycle-referenced artifacts compared as raw strings get mis-matched when the value is absolute vs repo-relative.

  Inside `scan_artifacts`, the "REFERENCED (never archive)" set is currently built from raw `state.artifacts.values()` strings. Change this to:

  ```python
  def _normalize_ref(repo: Path, ref: str) -> Path:
      """Return a canonical absolute resolved Path for a lifecycle artifact ref.
      Absolute paths are resolved as-is; relative paths are joined to repo."""
      p = Path(ref)
      if p.is_absolute():
          return p.resolve()
      return (repo / p).resolve()

  referenced: set[Path] = set()
  if state is not None:
      for ref in state.artifacts.values():
          if ref:
              try:
                  referenced.add(_normalize_ref(repo, ref))
              except OSError:
                  pass  # malformed path — skip silently
  ```

  Then in the scan loop, compare `path.resolve() in referenced` instead of comparing strings.

  Also fix the ghost-ref counter the same way: `ghost_refs += 1` only when `_normalize_ref(repo, ref).exists()` is False.

  **Do NOT change** the public function signatures, the dataclass shapes, the CLI, or the archive layout. This is a pure internal correctness fix.

  Mypy strict clean. Ruff format.

### Task 3: lifecycle.py — boundary guard in validate_artifact_refs
- **mode:** B
- **target:** renmark/lifecycle.py
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 1
- **est_tokens:** 400
- **est_cost_usd:** 0.031
- **verifier:** python3 -c "from renmark.lifecycle import validate_artifact_refs; print('imports OK')"
- **spec:**
  Fix codereview finding #4: `validate_artifact_refs` accepts absolute paths and `..`-escaping paths, letting `/renmark:resume` trust files outside the project.

  Before the existence/sha/staleness checks, add a path-boundary check. For each `(key, path_str)` in `state.artifacts.items()`:

  ```python
  raw = Path(path_str)
  # Reject absolute paths and any path that resolves outside the repo subtree.
  resolved = (repo / raw).resolve() if not raw.is_absolute() else raw.resolve()
  try:
      resolved.relative_to(Path(repo).resolve())
      inside = True
  except ValueError:
      inside = False
  if not inside:
      issues.append({
          "severity": "WARN",
          "kind": "out_of_tree",
          "artifact": key,
          "path": path_str,
          "detail": f"artifact '{key}' resolves outside project: {resolved}",
      })
      continue   # skip the existence/sha/staleness checks for out-of-tree paths
  ```

  Add `"out_of_tree"` to the documented `kind` values. Severity is `WARN` (not BLOCK) — out-of-tree means we can't validate further, not that the artifact is missing. The user gets a clear signal without resume blocking outright.

  Preserve all other behavior: BLOCK on missing plan/spec, WARN on other missing/unreachable_sha/stale_artifact, and the stable BLOCK-first / WARN-alpha ordering.

  Mypy strict clean. Type the new variables explicitly.

### Task 4: tests/test_memory.py — rewrite against real schemas
- **mode:** B
- **target:** tests/test_memory.py
- **complexity:** hard
- **executor:** codex
- **parallel_group:** 2
- **est_tokens:** 2500
- **est_cost_usd:** 0.075
- **verifier:** pytest -q tests/test_memory.py
- **spec:**
  Rewrite the `dedupe_memory_log` and `age_out_memory_log` tests so they exercise the REAL on-disk schemas:

  - `features.md` entries via `memory.log_feature()` (`### YYYY-MM-DD — Title` shape under `## Shipped`).
  - `bugs.md` entries via `memory.log_bug()` (`### YYYY-MM-DD — Title` shape under `## Open` or `## Fixed`).
  - `learnings.md` entries via `memory.append_learning()` (use whatever shape the writer produces — DO NOT hand-craft entries; produce them via the writer functions so the readers round-trip with reality).

  Update existing cases:
  - `test_dedupe_memory_log_removes_dupes` — write two identical entries via `log_feature`/`log_bug`/`append_learning`, assert second is removed.
  - `test_dedupe_memory_log_keeps_distinct` — distinct entries: nothing removed.
  - `test_dedupe_memory_log_rejects_curated_files` — KEEP unchanged.
  - `test_age_out_memory_log_moves_old` — write one entry 200 days ago (via `date=` kwarg if the writer supports it; otherwise monkeypatch `memory._today` for the write call) and one today; call with `days=180`; assert the old one is moved to `archive_root/memory/<name>` AND its enclosing section header is preserved.
  - `test_age_out_memory_log_keeps_undated` — entry without a parseable date stays put.

  Add new cases:
  - `test_dedupe_handles_each_schema` — one parameterized test exercising `features.md`, `bugs.md`, `learnings.md` schemas in sequence.
  - `test_age_out_preserves_section_header` — verify the archive file contains the original `## Open` (or whatever) section header above the moved entry.

  Keep the `log_decision` idempotency tests AS-IS — they already worked correctly and codereview did not flag them.

  Match the existing test style: `tmp_path` fixture, `from renmark import memory`, no private helpers imported.

### Task 5: tests/test_hygiene.py — add abs-path lifecycle ref case
- **mode:** B
- **target:** tests/test_hygiene.py
- **complexity:** medium
- **executor:** codex
- **parallel_group:** 2
- **est_tokens:** 800
- **est_cost_usd:** 0.024
- **verifier:** pytest -q tests/test_hygiene.py
- **spec:**
  Add ONE new test case + light updates:

  - `test_scan_referenced_via_absolute_path_never_archived` — same setup as the existing `test_scan_referenced_never_archived`, but write the lifecycle.json artifact value as an ABSOLUTE path (`str(absolute_path)`) instead of repo-relative. Without the fix, the file would be archived; with the fix, `archived=0, kept=1`. This is the regression test for codereview finding #1.

  Existing cases stay unchanged. If `test_scan_referenced_never_archived` currently uses absolute paths by accident, change it to use relative paths so the new test is the only "absolute" coverage and the contrast is clear.

  Match existing test style; use `tmp_path` and the existing `_write_artifact` helper.

### Task 6: tests/test_lifecycle.py — boundary-escape rejection cases
- **mode:** B
- **target:** tests/test_lifecycle.py
- **complexity:** medium
- **executor:** codex
- **parallel_group:** 2
- **est_tokens:** 600
- **est_cost_usd:** 0.018
- **verifier:** pytest -q tests/test_lifecycle.py
- **spec:**
  Add two new test cases for the boundary guard added in Task 3:

  - `test_validate_artifact_refs_absolute_outside_repo_warns` — `artifacts={"plan": "/tmp/escape.plan.md"}`; assert one issue with `severity="WARN"`, `kind="out_of_tree"`. The file's existence is irrelevant — the guard fires before existence checks.
  - `test_validate_artifact_refs_dotdot_escape_warns` — `artifacts={"plan": "../../../etc/passwd"}`; assert WARN + `out_of_tree`. Confirms `..`-relative paths that escape the repo are caught.

  Also update the existing ordering test (`test_validate_artifact_refs_order_block_first`) if needed: out-of-tree (WARN) entries should sort AFTER block entries, alphabetically among WARNs.

  Match existing test style; use `tmp_path` initialized as a git repo (subprocess.run(['git', 'init', tmp_path])) so the sha-reachability check has a context.

### Task 7: CHANGELOG.md — append "codex fixes" paragraph to v0.5.6
- **mode:** B
- **target:** CHANGELOG.md
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 3
- **est_tokens:** 500
- **est_cost_usd:** 0.001
- **verifier:** grep -q "codex review" CHANGELOG.md
- **spec:**
  Append a section to the existing `## v0.5.6` entry (do NOT create a new version entry). Add it just before the existing "Do not change" section so the v0.5.6 entry tells the full story: shipped → reviewed → fixed.

  New subsection title: **`Codex codereview pass applied before merge (4 Major fixes):`**

  Bullets (one per fix):
  - `renmark/memory.py` — `dedupe_memory_log` + `age_out_memory_log` rewritten to parse the REAL on-disk schemas (`###` entries under section headers for `features.md`/`bugs.md`, plus the actual learnings.md shape). The original H2-only parser worked on the synthetic tests but was a no-op on real memory files. Tests now produce entries via the writer functions (`log_feature`, `log_bug`, `append_learning`) so readers round-trip with writers.
  - `renmark/hygiene.py` — lifecycle artifact refs normalized via `Path.resolve()` before comparison; absolute paths and repo-relative paths now match consistently. Ghost-ref counting uses the same normalization.
  - `renmark/lifecycle.py` — `validate_artifact_refs` now WARNs with `kind="out_of_tree"` for artifact paths that resolve outside the project subtree (absolute paths, `..`-escapes). The existing BLOCK/WARN semantics for missing/stale/unreachable are unchanged.
  - Tests updated/added for all three: real-schema dedupe + age-out cases, absolute-path lifecycle ref regression test, out-of-tree boundary cases.

  Closing line: *"The Minor finding (#5 — escalation hook dead code) is by design: the `escalated_to` kwarg is opt-in to avoid breaking existing call sites; real callers land as escalation contexts get fleshed out in a follow-up."*

  Keep style consistent with the rest of v0.5.6. Do not touch any other entry.

---

## Cost preview (honest accounting — incl. ~10k Agent overhead per Claude task)

| Task | Executor | Output | Total tokens (w/ overhead) | Cost |
|------|----------|--------|----------------------------|------|
| 1 memory.py | opus | 3,000 | 13,000 | $0.195 |
| 2 hygiene.py | sonnet | 500 | 10,500 | $0.032 |
| 3 lifecycle.py | sonnet | 400 | 10,400 | $0.031 |
| 4 test_memory.py | codex | 2,500 | 2,500 | $0.075 |
| 5 test_hygiene.py | codex | 800 | 800 | $0.024 |
| 6 test_lifecycle.py | codex | 600 | 600 | $0.018 |
| 7 CHANGELOG.md | haiku | 500 | 10,500 | $0.001 |

**Total: ~$0.38 across 7 tasks in 3 waves.**

Executors: haiku×1, codex×3, sonnet×2, opus×1.

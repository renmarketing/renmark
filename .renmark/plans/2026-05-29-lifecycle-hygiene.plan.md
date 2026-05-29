---
artifact_type: plan
schema_version: 1
created_at: 2026-05-29T00:00:00Z
source_sha: f5e480c
generator: opus
related_spec: null
stale_after: 2026-08-29T00:00:00Z
dependency_refs: []
---

# Lifecycle Hygiene Bundle

**Branch:** `feature/lifecycle-hygiene`
**Base sha:** `f5e480c`
**Goal:** Close the gap between renmark's artifact-first doctrine and its actual enforcement. Four cohesive deliverables: (1) decision-log enforcement at escalation and finish; (2) artifact GC built on existing `summary.is_stale()` + `archive/` directory; (3) memory file pruning (dedupe + age-out for append-only logs); (4) artifact-freshness validation in resume.

## Context

Renmark already designed `stale_after` / `created_at` / `source_sha` metadata (`renmark/summary.py:240`), `is_stale()` (`summary.py:240`), and `log_decision()` (`memory.py:193`) — but the consumers were never built. This bundle finishes the loop.

**Patterns applied** (no external deps):
- TTL + never-evict-while-referenced (Bazel/Nix/ccache)
- ADR format abbreviated for 3-line cap (Michael Nygard)
- "show + flag" for memory logs (RFC 5861 stale-while-revalidate)

**Out of scope:** docs-drift scanner, perf budgets, dep vetting, summary-quality LLM audit.

## Tasks

### Task 1: memory.py — idempotent log_decision + prune helpers
- **mode:** B
- **target:** renmark/memory.py
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 1
- **est_tokens:** 900
- **est_cost_usd:** 0.033
- **verifier:** python3 -c "from renmark.memory import log_decision, dedupe_memory_log, age_out_memory_log, log_escalation_decision"
- **spec:**
  Extend `renmark/memory.py` with four additions; keep the file under its current style (newest-first, append-not-rewrite). Stdlib only.

  1. Make `log_decision()` idempotent. Before writing, scan the existing `decisions.md` for an ADR with the same `title` AND `date` (default today). If found, return without writing. Duplicate-detection signature: `(title.strip(), date)`.

  2. New `dedupe_memory_log(repo, name: str) -> int` — for `name in {"learnings.md", "bugs.md", "features.md"}`. Parses entries by H2 (`## ...`) boundaries. Computes signature `(title, sha256(first-non-blank-line)[:12])`. Removes duplicates, keeping the FIRST occurrence (newest, since files are newest-first). Returns count removed. Refuses to operate on `decisions.md`, `INDEX.md`, `project.md`, `stack.md`, `architecture.md`, `conventions.md`, `routing.md`, `dev-standards.md` (curated, not append-only) — raise ValueError.

  3. New `age_out_memory_log(repo, name: str, days: int, archive_root: Path) -> int` — same allowed names. Parses entries; for each entry, extracts the first `YYYY-MM-DD` token in the H2 line (or in a `**Date:**` line). Entries with no parseable date are KEPT (safe default). Entries older than `days` are moved to `archive_root/memory/<name>` appended in original newest-first order. Returns count moved.

  4. New `log_escalation_decision(repo, *, task_index: int, from_exec: str, to_exec: str, reason: str, plan_path: str | None = None) -> None` — thin wrapper around `log_decision()` that formats title as `Escalated task {idx} from {from_exec} to {to_exec}`, status `Accepted`, context = `reason` (truncated to 200 chars), decision = `Re-route to {to_exec}`, alternatives = [`Retry {from_exec}`, `Fail the task`], consequences = [`Higher cost`, `Higher capability`]. Pass `date=` today so idempotency catches re-runs in same day.

  Imports: add `import hashlib` if missing. Use existing `_today()` helper. Preserve all existing public functions unchanged in behavior except `log_decision` (which only adds a short-circuit).

### Task 2: lifecycle.py — hygiene domain + validate_artifact_refs
- **mode:** B
- **target:** renmark/lifecycle.py
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 1
- **est_tokens:** 1000
- **est_cost_usd:** 0.033
- **verifier:** python3 -c "from renmark.lifecycle import validate_artifact_refs, DOMAIN_BY_SKILL; assert DOMAIN_BY_SKILL['hygiene'] == 'meta'"
- **spec:**
  Two additions to `renmark/lifecycle.py`. Stdlib + subprocess (already imported in adjacent modules — use `summary.git_head_sha` style if you need git access).

  1. Add `"hygiene": "meta"` to the `DOMAIN_BY_SKILL` dict (`lifecycle.py:93`). Keep the meta block contiguous and sorted by current visual order (insert after `"issue": "meta",`).

  2. New function `validate_artifact_refs(repo: Path | str, state: LifecycleState | None = None) -> list[dict[str, str]]`. Returns a list of issue dicts; each has keys `severity` (`"BLOCK"` | `"WARN"`), `kind` (`"missing_path"` | `"unreachable_sha"` | `"stale_artifact"`), `artifact` (artifact key from state.artifacts), `path` (the referenced file path), `detail` (≤ 120 chars).

     Logic:
     - If `state` is None, read it via `read_lifecycle(repo)`. If still None, return `[]` (no in-flight feature; nothing to validate).
     - For each `(key, path_str)` in `state.artifacts.items()`:
       - Resolve relative to `repo`. If file does not exist:
         - severity `BLOCK` for keys in `{"plan", "spec"}`; `WARN` otherwise.
         - kind `missing_path`.
       - If file exists, read its YAML frontmatter via `from .summary import read_metadata` and:
         - If a `source_sha` is present, run `git -C <repo> cat-file -e <sha>` (with `subprocess.run`, timeout 5s, check=False); if non-zero exit, emit `WARN` / `unreachable_sha`.
         - If `summary.is_stale(path)` returns True, emit `WARN` / `stale_artifact`.
     - Order: BLOCK first, then WARN, then by `key` alphabetically.

  Add type imports as needed (`from .summary import read_metadata, is_stale`). Keep file under the 1KB lifecycle.json budget — this function does NOT touch lifecycle.json.

### Task 3: hygiene.py — scanner + GC + memory prune + CLI
- **mode:** A
- **target:** renmark/hygiene.py
- **complexity:** hard
- **executor:** opus
- **parallel_group:** 2
- **est_tokens:** 8000
- **est_cost_usd:** 0.270
- **verifier:** python3 -m renmark.hygiene --help
- **spec:**
  Create `renmark/hygiene.py`. Stdlib only. The module is the single source of truth for renmark's lifecycle hygiene — artifact GC + memory pruning + CLI.

  **Public API (importable):**

  ```python
  def scan_artifacts(repo: Path, *, ttl_days: int = 90, dry_run: bool = True,
                     archive_root: Path | None = None) -> ScanReport: ...
  def prune_memory(repo: Path, *, days: int = 180, dry_run: bool = True,
                   archive_root: Path | None = None) -> PruneReport: ...
  ```

  **Data classes** (use `@dataclass`):
  - `ScanReport(scanned: int, archived: int, kept: int, ghost_refs: int, archived_paths: list[Path], errors: list[str])`
  - `PruneReport(deduped: int, aged_out: int, files_touched: list[str], errors: list[str])`

  **Artifact GC logic** (`scan_artifacts`):
  - Walk these directories under `repo / ".renmark"`: `specs/`, `plans/`, `reviews/`, `research/`, `state/wave-summaries/`. Skip if directory does not exist.
  - For each markdown / YAML file (`*.md`, `*.yaml`, `*.yml`, `*.json`):
    - Read frontmatter via `renmark.summary.read_metadata(path)`.
    - Treat as STALE if any of:
      - `summary.is_stale(path)` returns True (covers `stale_after` + `source_sha` mismatches; `is_stale` already returns True when file missing — we won't hit that branch since we're iterating existing files), OR
      - `created_at` is older than `ttl_days` days from now (UTC), OR
      - `created_at` is missing AND file `mtime` is older than `ttl_days` days from now (fallback).
    - Treat as REFERENCED (never archive) if its repo-relative path appears as a value in `state.artifacts` of the current `lifecycle.json` (read via `lifecycle.read_lifecycle(repo)`).
    - Treat as GHOST if a `lifecycle.json` artifact path points to it but the file is missing (we won't see these by iteration; cross-check by iterating `state.artifacts` separately and counting paths whose file is absent — bump `ghost_refs`).
  - When `dry_run=False`, move stale + non-referenced files to `archive_root` (default `repo / ".renmark" / "archive" / "YYYY-MM"` using current UTC month). Preserve repo-relative path under that month dir (e.g. `.renmark/archive/2026-05/.renmark/specs/foo.spec.md`). Use `shutil.move`; if the destination exists, append `.N` suffix.
  - When `dry_run=True`, populate `archived_paths` with what WOULD be moved, but make no FS changes.
  - Always increment `scanned`. Bump `kept` if not stale OR if referenced. Bump `archived` if stale AND not referenced AND not dry-run; otherwise count under `kept` even when dry-run-would-move (we still report what dry-run would do via `archived_paths`).
  - Wrap each per-file operation in `try/except OSError` and append to `errors`; never raise from the public function.

  **Memory prune logic** (`prune_memory`):
  - Allowed names: `["learnings.md", "bugs.md", "features.md"]`.
  - For each: call `memory.dedupe_memory_log(repo, name)`; sum into `deduped`. Then call `memory.age_out_memory_log(repo, name, days, archive_root_resolved)`; sum into `aged_out`. Always append `name` to `files_touched`. Per-name try/except OSError into `errors`.
  - When `dry_run=True`, both helpers must NOT mutate. Easiest: when dry_run, *count* dupes and age-outs by replicating the parse logic locally (read-only). To avoid duplication, accept that `dedupe_memory_log` / `age_out_memory_log` ALREADY support `dry_run=True` via a kwarg — Task 1 must add this kwarg too. If Task 1 omitted it, hygiene must skip the actual call when `dry_run=True` and just count via its own parse.

  **CLI** (`if __name__ == "__main__":` or `def main(argv): ...`):
  - Subcommands: `scan` (artifact GC), `prune` (memory prune), `all` (both, sequential).
  - Flags: `--repo PATH` (default `.`), `--dry-run` (default True — opt-in to writes via `--apply`), `--apply` (negates dry-run), `--ttl-days N` (default 90 for scan), `--memory-days N` (default 180 for prune), `--include-memory` (when invoked as `scan`, also runs prune after).
  - Output: bounded ≤ 5 lines. Format exactly:
    ```
    HYGIENE  mode=<dry-run|apply>  scanned=<N>  archived=<M>  kept=<K>  ghost_refs=<G>
    MEMORY   deduped=<D>  aged_out=<A>  files=<learnings,bugs,features>
    [optional: ERRORS    <n> — see .renmark/logs/hygiene-YYYY-MM-DD.log]
    ```
  - When `errors` is non-empty AND `--apply` was used, also write the full error list to `repo / ".renmark" / "logs" / f"hygiene-{date}.log"` (one line per error). Logs dir lives under `.renmark/logs` (already gitignored per memory/INDEX.md convention).
  - Exit 0 on clean run; exit 2 on argument error; never exit 1 just because items were archived (archiving is the success case).

  **Step 0 (lifecycle preamble):** at the top of `main()`, call `lifecycle.skill_preamble(repo, 'hygiene')` and print the returned hint (if non-None) before the HYGIENE line. Hygiene is `meta` domain (per Task 2), so prompts only on cross-domain transitions.

  **Do NOT write to `lifecycle.json`** — hygiene is diagnostic, not a stage transition.

  **Do NOT read generated file contents** beyond the frontmatter — `read_metadata` is the only allowed file-read for artifacts. Memory files are short and may be read whole by `dedupe_memory_log` / `age_out_memory_log` (those run in their module).

  **All paths must stay inside `repo / ".renmark"`.** Refuse (raise ValueError) if `archive_root` resolves outside that subtree.

### Task 4: _engine.py — escalation → decision hook
- **mode:** B
- **target:** renmark/cli/_engine.py
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 2
- **est_tokens:** 600
- **est_cost_usd:** 0.032
- **verifier:** python3 -c "import ast,pathlib; src=pathlib.Path('renmark/cli/_engine.py').read_text(); assert 'log_escalation_decision' in src"
- **spec:**
  Wire `renmark.memory.log_escalation_decision()` into the orchestrate escalation flow. The escalation logic already exists at `renmark/cli/_engine.py` — `_record_escalation` is called in ~7 places (lines around 405, 548, 580, 624, 669, 723).

  Changes:

  1. Add import at the top: `from .. import memory as _memory` (match existing import style; if there's already a `from .. import memory` adjacent, use that name).

  2. Inside `_record_escalation` itself (definition at ~line 738), AFTER the existing escalation-dir write succeeds, call:
     ```python
     try:
         _memory.log_escalation_decision(
             repo,
             task_index=task.index,
             from_exec=task.executor,
             to_exec=escalated_to,   # whatever local var names the new executor
             reason=reason_text,     # the existing reason string passed into _record_escalation
         )
     except Exception:
         pass  # decision logging is best-effort; never break orchestrate
     ```
     Map the local variable names by reading the function signature. If the caller doesn't pass an `escalated_to` value to `_record_escalation`, accept a new keyword arg `escalated_to: str | None = None` and only log when it's non-None. Do NOT add the arg as required — that would break existing call sites.

  3. Update each of the ~7 call sites that have meaningful escalation context (i.e. where the code is choosing a different executor) to pass `escalated_to=` with the chosen executor name. Sites that record a TERMINAL failure (no escalation, just "give up") should NOT pass `escalated_to` — they're not decisions worth logging.

  Idempotency: `log_decision` is now idempotent on `(title, date)` per Task 1, so re-runs of the same escalation on the same day won't duplicate the ADR.

  Do not change any other behavior in this file. Existing tests must keep passing — that's the verifier-gate for the post-edit checks.

### Task 5: tests/test_memory.py — new helpers + log_decision idempotency
- **mode:** B
- **target:** tests/test_memory.py
- **complexity:** medium
- **executor:** codex
- **parallel_group:** 3
- **est_tokens:** 1500
- **est_cost_usd:** 0.045
- **verifier:** pytest -q tests/test_memory.py
- **spec:**
  Add tests for the new helpers added in Task 1. Match existing test style in this file (look at the existing `test_log_*` functions for fixtures/conventions). All tests use `tmp_path` fixture.

  Required cases:

  1. `test_log_decision_idempotent_same_day` — call `log_decision(tmp_path, title="X", decision="Y")` twice on the same day; assert only one ADR appears.
  2. `test_log_decision_distinct_titles_both_appear` — two distinct titles on the same day both appear.
  3. `test_log_decision_same_title_different_date` — explicit `date=` arguments differing; both appear.
  4. `test_log_escalation_decision_writes_adr` — call helper, then read `decisions.md`; assert title contains "Escalated task" and the from/to executors.
  5. `test_dedupe_memory_log_removes_dupes` — write two entries with identical first-non-blank-line, assert second is removed and first remains.
  6. `test_dedupe_memory_log_keeps_distinct` — distinct content, nothing removed.
  7. `test_dedupe_memory_log_rejects_curated_files` — assert ValueError for `decisions.md` and `project.md`.
  8. `test_age_out_memory_log_moves_old` — write an entry dated 200 days ago and one dated today; call with `days=180`; assert the old one is moved to `archive_root` and the recent one remains.
  9. `test_age_out_memory_log_keeps_undated` — entry with no parseable date stays put.

  Use `from renmark import memory` and call functions through the module. Do not import private helpers. Date-sensitive tests should monkeypatch `memory._today` if needed.

### Task 6: tests/test_lifecycle.py — validate_artifact_refs + domain
- **mode:** B
- **target:** tests/test_lifecycle.py
- **complexity:** medium
- **executor:** codex
- **parallel_group:** 3
- **est_tokens:** 1200
- **est_cost_usd:** 0.036
- **verifier:** pytest -q tests/test_lifecycle.py
- **spec:**
  Add tests for the additions in Task 2. Match existing style — look at how `write_lifecycle` is currently tested.

  Required cases:

  1. `test_hygiene_is_meta_domain` — assert `lifecycle.DOMAIN_BY_SKILL["hygiene"] == "meta"`.
  2. `test_validate_artifact_refs_no_lifecycle` — fresh `tmp_path` with no lifecycle.json: result is `[]`.
  3. `test_validate_artifact_refs_all_ok` — write lifecycle.json with `artifacts={"plan": "p.md"}`, create `p.md` with valid frontmatter; result is `[]`.
  4. `test_validate_artifact_refs_missing_plan_blocks` — `artifacts={"plan": "missing.md"}`; assert one issue, `severity="BLOCK"`, `kind="missing_path"`.
  5. `test_validate_artifact_refs_missing_aux_warns` — `artifacts={"notes": "missing.md"}`; assert `severity="WARN"`, `kind="missing_path"`.
  6. `test_validate_artifact_refs_unreachable_sha` — file exists with frontmatter `source_sha: deadbeefdeadbeef` (clearly bogus). Assert `severity="WARN"`, `kind="unreachable_sha"`. Tests must run from a git repo (use the renmark repo's git context — `tmp_path` itself isn't a git repo, so monkeypatch the git check or initialize `tmp_path` as a git repo with `subprocess.run(['git', 'init', tmp_path])`).
  7. `test_validate_artifact_refs_stale_artifact` — file with `stale_after: 2020-01-01T00:00:00Z`; assert `severity="WARN"`, `kind="stale_artifact"`.
  8. `test_validate_artifact_refs_order_block_first` — combine a missing plan (BLOCK) and a stale aux (WARN); assert BLOCK appears first.

  Use the project's `summary.write_metadata` (or whatever the file-writing function is — read `renmark/summary.py` to confirm) to produce frontmatter-bearing files. If only a private helper exists, write the frontmatter as a raw string from the test.

### Task 7: tests/test_hygiene.py — module unit tests
- **mode:** A
- **target:** tests/test_hygiene.py
- **complexity:** hard
- **executor:** codex
- **parallel_group:** 3
- **est_tokens:** 3000
- **est_cost_usd:** 0.090
- **verifier:** pytest -q tests/test_hygiene.py
- **spec:**
  Create unit tests for the new `renmark.hygiene` module. Match existing test style. All tests use `tmp_path`.

  **Setup helper** — write a tiny fixture function in the test file:
  ```python
  def _write_artifact(path: Path, *, created_at: str, stale_after: str | None = None,
                     source_sha: str | None = None, body: str = "content") -> None:
      """Write a .renmark artifact with frontmatter so hygiene can read it."""
  ```
  Use `renmark.summary` helpers when available; otherwise write the YAML frontmatter manually using the same format `summary.read_metadata` parses.

  **Required cases for `scan_artifacts`:**

  1. `test_scan_empty_repo` — no `.renmark` dirs exist; `scanned=0, archived=0, errors=[]`.
  2. `test_scan_fresh_artifact_kept` — recent `created_at`, no `stale_after`; `archived=0, kept=1`.
  3. `test_scan_expired_stale_after_archived` — `stale_after` in the past, `--apply`; assert file moved under `.renmark/archive/YYYY-MM/`; `archived=1`.
  4. `test_scan_ttl_fallback` — no `stale_after`, `created_at` 100 days ago, `ttl_days=90`, `--apply`; assert archived.
  5. `test_scan_referenced_never_archived` — file is stale AND listed in `lifecycle.json` `artifacts={"plan": str(path)}`; assert `archived=0, kept=1`.
  6. `test_scan_dry_run_no_writes` — stale file, `dry_run=True`; `archived=0`, `archived_paths=[<that file>]`, file still in place.
  7. `test_scan_ghost_ref_counted` — `lifecycle.json` references a path that doesn't exist; `ghost_refs=1`.
  8. `test_scan_refuses_archive_outside_renmark` — pass `archive_root=tmp_path / "outside"`; assert ValueError.

  **Required cases for `prune_memory`:**

  9. `test_prune_dedupes_learnings` — write `learnings.md` with two identical entries; `--apply`; `deduped=1`.
  10. `test_prune_ages_out_old_bugs` — write `bugs.md` with an entry dated 200d ago and one today; `days=180`, `--apply`; `aged_out=1`.
  11. `test_prune_dry_run_no_writes` — same setup as #9, `dry_run=True`; `deduped=1` (count only), source file unchanged.
  12. `test_prune_refuses_curated_files` — implicit: function only iterates the allowed list, so curated files like `decisions.md` are never touched. Assert decisions.md is unchanged before/after a prune cycle.

  **Required CLI smoke test:**

  13. `test_cli_help_exits_zero` — invoke `python -m renmark.hygiene --help` via subprocess; assert exit 0.
  14. `test_cli_scan_outputs_bounded` — set up a single stale artifact, run `python -m renmark.hygiene scan --apply --repo <tmp>`; capture stdout; assert at most 5 lines and that line 1 starts with `HYGIENE  mode=apply`.

  Per-test budget: avoid sleeping; use explicit dates in the past. Subprocess tests use `sys.executable` + `["-m", "renmark.hygiene", ...]`.

### Task 8: skill — /renmark:hygiene
- **mode:** A
- **target:** plugin/skills/hygiene/SKILL.md
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 4
- **est_tokens:** 1200
- **est_cost_usd:** 0.001
- **verifier:** test -f plugin/skills/hygiene/SKILL.md && head -3 plugin/skills/hygiene/SKILL.md | grep -q "^name: hygiene"
- **spec:**
  Create `plugin/skills/hygiene/SKILL.md`. Match the structure used by `plugin/skills/init/SKILL.md` — frontmatter (`name`, `description`), then `# hygiene`, `## Overview`, `## When to Use`, `## Steps`, `## Flags`, `## Boundaries` sections.

  Frontmatter:
  ```yaml
  ---
  name: hygiene
  description: Use to garbage-collect stale renmark artifacts and prune append-only memory logs. Scans .renmark/specs|plans|reviews|research|state/wave-summaries for artifacts past their stale_after or TTL, archives them to .renmark/archive/YYYY-MM/ while preserving paths. Optionally dedupes and ages out entries in learnings.md/bugs.md/features.md. Default dry-run; opt-in to writes via --apply. Meta domain — never advances lifecycle.json.
  ---
  ```

  Sections to include (each terse, ≤ 200 words total skill body):
  - **Overview** — one paragraph explaining what hygiene does and why (closes the loop on existing stale_after metadata).
  - **When to Use** — bullets: monthly cleanup; after a long-running feature branch; before archiving a project; when `.renmark/` is bloated.
  - **Steps** — Step 0 context check; Step 1 `python -m renmark.hygiene scan --apply` (and variants).
  - **Flags** — list `--dry-run` (default), `--apply`, `--ttl-days N`, `--memory-days N`, `--include-memory`. Show 3 example invocations.
  - **Boundaries** — never advances lifecycle.json; all writes inside `.renmark/`; archive preserves paths; never touches curated memory files (decisions/project/stack/architecture/conventions/routing/dev-standards).

### Task 9: command — /renmark:hygiene dispatcher
- **mode:** A
- **target:** plugin/commands/hygiene.md
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 4
- **est_tokens:** 100
- **est_cost_usd:** 0.001
- **verifier:** test -f plugin/commands/hygiene.md
- **spec:**
  Create `plugin/commands/hygiene.md`. Match the format of other small command files in `plugin/commands/` (look at e.g. `plugin/commands/resume.md` or `plugin/commands/help.md` for the exact frontmatter + body). The file is a one-line dispatcher that tells Claude Code to invoke the `hygiene` skill, passing through user input as `$ARGUMENTS`.

  Body should follow the existing template: a short instruction line like:
  > Read `/home/renmark/projects/ai-system/plugin/skills/hygiene/SKILL.md` and follow its instructions exactly. The user provided this input: $ARGUMENTS
  >
  > If `$ARGUMENTS` is empty, begin the hygiene skill's flow.

  (Adapt to the actual conventional format used by sibling commands — peek at one before authoring.)

### Task 10: resume skill — artifact-freshness validation step
- **mode:** B
- **target:** plugin/skills/resume/SKILL.md
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 4
- **est_tokens:** 400
- **est_cost_usd:** 0.001
- **verifier:** grep -q "validate_artifact_refs" plugin/skills/resume/SKILL.md
- **spec:**
  Update `plugin/skills/resume/SKILL.md` to add an explicit artifact-freshness validation step.

  Edits:
  - In `## Steps`, add **Step 1.5 — Validate artifact freshness** between the existing "Read lifecycle state" (Step 1) and "Surface pending approval gates" (Step 2).
  - Step 1.5 body: ≤ 8 lines. Show invoking `lifecycle.validate_artifact_refs(Path('.'))` via the same inline `python3 -c` block style used by Step 1. Document the behavior: ghost references emit `⚠ WARN` lines; BLOCK-level issues emit `❌ BLOCK` and the skill exits non-zero so the user investigates before continuing.
  - Update `## Boundaries` (or equivalent footer) to note that resume now reads artifact frontmatter for the cross-check — still zero LLM calls, still bounded output.

  Do not alter any other section. Keep the file under 120 lines total.

### Task 11: finish skill — decision-logging hook
- **mode:** B
- **target:** plugin/skills/finish/SKILL.md
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 4
- **est_tokens:** 300
- **est_cost_usd:** 0.001
- **verifier:** grep -q "log_decision\|decisions.md" plugin/skills/finish/SKILL.md
- **spec:**
  Update `plugin/skills/finish/SKILL.md` to document the new decision-logging behavior at branch close.

  Add a short subsection (under Steps, or near the lifecycle-update final step) titled **Decision log entry**. ≤ 6 lines. State that finish appends a single ADR to `.renmark/memory/decisions.md` via `memory.log_decision()` capturing: feature name (from `state.feature`), branch, summary of waves and tasks completed (from `pipeline.json` if present), and the lifecycle stage transition (e.g. `documented → ready-to-release`). Idempotent per Task 1.

  Do NOT include actual implementation code — finish's lifecycle handling stays as-is; the new decision-write is described here as a documented behavior. (Implementation lives wherever finish currently calls `lifecycle.write_lifecycle`; the actual code addition for finish is small enough to fold into this same skill.md update with a one-line `python3 -c` snippet.)

  Show the `python3 -c` snippet that finish runs:
  ```python
  from renmark import memory, lifecycle
  from pathlib import Path
  s = lifecycle.read_lifecycle(Path('.'))
  if s:
      memory.log_decision(Path('.'),
          title=f"Finished feature {s.feature}",
          decision=f"Branch {s.branch} reached stage {s.stage}",
          context=f"Completed stages: {', '.join(s.stages_completed)}")
  ```

  This snippet is the canonical reference; finish-time runtime invokes it once.

### Task 12: orchestrate skill — escalation decision logging note
- **mode:** B
- **target:** plugin/skills/orchestrate/SKILL.md
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 4
- **est_tokens:** 300
- **est_cost_usd:** 0.001
- **verifier:** grep -q "log_escalation_decision\|decisions.md" plugin/skills/orchestrate/SKILL.md
- **spec:**
  Add a short subsection (≤ 6 lines) to `plugin/skills/orchestrate/SKILL.md` titled **Escalation decision log**, explaining that whenever a task is escalated to a higher-tier executor, an ADR is appended to `.renmark/memory/decisions.md` via `memory.log_escalation_decision()`. State that this is automatic (handled in `renmark/cli/_engine.py`'s `_record_escalation`), idempotent (no dup ADRs for re-runs same day), best-effort (decision-logging failures do not break orchestrate), and pointer-only in the conversation (orchestrator never reads decisions.md).

  Do not alter any other section.

### Task 13: CHANGELOG — v0.5.6 entry
- **mode:** B
- **target:** CHANGELOG.md
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 5
- **est_tokens:** 2000
- **est_cost_usd:** 0.036
- **verifier:** head -3 CHANGELOG.md | grep -q "v0.5.6"
- **spec:**
  Prepend a new `## v0.5.6 — 2026-05-29 (lifecycle hygiene — decision log, artifact GC, memory prune, resume validation)` entry to `CHANGELOG.md`. Match the voice and structure of recent entries (v0.5.5, v0.5.4 are good templates — driving idea + concrete changes + "Do not change" guards).

  Sections to include:
  - **Driving idea** — close the gap between renmark's artifact-first doctrine and its actual enforcement; the metadata schema (stale_after / source_sha / created_at) and `log_decision()` already existed but nothing consumed them.
  - **What shipped** — bullets covering: (1) `memory.log_decision()` idempotent + new helpers `dedupe_memory_log`, `age_out_memory_log`, `log_escalation_decision`; (2) `lifecycle.validate_artifact_refs()` and `hygiene` added to `DOMAIN_BY_SKILL`; (3) new `renmark/hygiene.py` module + `python -m renmark.hygiene` CLI; (4) `_record_escalation` now writes an ADR via `log_escalation_decision` (best-effort); (5) new `/renmark:hygiene` skill + command; (6) resume now runs `validate_artifact_refs` and emits BLOCK/WARN lines.
  - **Why this matters for vibe coders** — one paragraph: decisions.md becomes the persistent WHY across `/clear`; `.renmark/` no longer grows unbounded; resume catches ghost references before re-entry.
  - **Acceptance gates** — pytest, ruff, mypy strict, plugin lint, 5/5 pre-commit OK.
  - **Do not change** guards — at minimum: (a) the idempotency check in `log_decision` (same title+date short-circuits — removing it floods decisions.md on re-runs); (b) hygiene's `dry_run=True` default (writes are opt-in via `--apply`); (c) the `meta` domain for hygiene (it MUST NOT advance lifecycle stage); (d) the `try/except: pass` around `log_escalation_decision` in `_record_escalation` (decision logging is best-effort; never break orchestrate); (e) hygiene's refusal to write outside `.renmark/`.

  Keep entry length comparable to v0.5.5 (~80–120 lines). No emojis unless adjacent entries used them (they don't — none).

---

## Cost preview (honest accounting — includes ~10k Agent overhead per Claude task)

| Task | Executor | Output | Total tokens (w/ overhead) | Cost |
|------|----------|--------|----------------------------|------|
| 1 memory.py | sonnet | 900 | 10,900 | $0.033 |
| 2 lifecycle.py | sonnet | 1,000 | 11,000 | $0.033 |
| 3 hygiene.py | opus | 8,000 | 18,000 | $0.270 |
| 4 _engine.py | sonnet | 600 | 10,600 | $0.032 |
| 5 test_memory.py | codex | 1,500 | 1,500 | $0.045 |
| 6 test_lifecycle.py | codex | 1,200 | 1,200 | $0.036 |
| 7 test_hygiene.py | codex | 3,000 | 3,000 | $0.090 |
| 8 hygiene SKILL.md | haiku | 1,200 | 11,200 | $0.001 |
| 9 hygiene command | haiku | 100 | 10,100 | $0.001 |
| 10 resume SKILL.md | haiku | 400 | 10,400 | $0.001 |
| 11 finish SKILL.md | haiku | 300 | 10,300 | $0.001 |
| 12 orchestrate SKILL.md | haiku | 300 | 10,300 | $0.001 |
| 13 CHANGELOG.md | sonnet | 2,000 | 12,000 | $0.036 |

**Total: ~$0.58 across 13 tasks in 5 waves.**

Executors: haiku×5, codex×3, sonnet×4, opus×1.

<!--
artifact_type: plan
schema_version: 1
created_at: 2026-06-17T01:30:00Z
source_sha: da6e9db
related_plan: .renmark/plans/2026-06-17-req14-scan-review-fixes.plan.md
generator: plan
dependency_refs:
  - .renmark/reviews/2026-06-17-da6e9db-fixes.review.md
-->

# Plan — REQ-14 scan: pivot read-only to structural + fix 3 Majors

Re-review (`.renmark/reviews/2026-06-17-da6e9db-fixes.review.md`) found the Bash
denylist hook still bypassable (2 Critical: absolute-path/`env`/`command`/wrapper
forms; `$(...)`/backtick substitution). **Decision (user-approved): stop trying
to make the denylist airtight.** The scan engine is pure Python with no
mutate path, so the scheduled trigger becomes `renmark-execute --scan --propose`
directly (no LLM, no Bash tool) — read-only is then STRUCTURAL. The hook is
demoted to optional best-effort defense-in-depth for anyone using a `claude -p`
trigger; it is no longer the guarantee, which resolves both Criticals (they only
mattered while the hook was the trust boundary). Also fixes the 3 Majors.

---

### Task 1: scan.py — pivot trigger + demote hook + fix 3 Majors
- **mode:** B
- **target:** renmark/scan.py
- **complexity:** hard
- **executor:** opus
- **parallel_group:** 1
- **est_tokens:** 1800
- **est_cost_usd:** 0.18
- **verifier:** python3 -c "import renmark.scan as s; assert s.emit_cron('.').count('renmark-execute --scan')>=1; assert 'write_lifecycle' not in open('renmark/scan.py').read()" && ruff check renmark/scan.py >/dev/null && echo OK
- **serves:** REQ-14
- **spec:**
  Read `renmark/scan.py` and `.renmark/reviews/2026-06-17-da6e9db-fixes.review.md` first.
  - **PIVOT emit_cron (resolves both Criticals):** make the PRIMARY emitted trigger the direct Python CLI — `renmark-execute --scan --propose` — run from the repo root on a schedule (WSL cron / Task Scheduler). State plainly that read-only is STRUCTURAL: this process only writes the report, the dedup ledger, and backlog `write_item`; it has no code path that commits/merges/pushes/edits, so no LLM, no Bash tool, and no hook are involved. Then add a clearly-labeled OPTIONAL section: "If you instead trigger via `claude -p \"/renmark:scan --propose\"` (a model-driven run with a Bash tool), add this best-effort PreToolUse hook as defense-in-depth — note it is best-effort, NOT a guarantee; the structural guarantee is the direct-Python trigger above." Keep the existing `READONLY_HOOK`/tokenizer as that optional hook (do NOT delete it, do NOT chase airtightness). Update the module comment + any docstring that claimed the hook enforces read-only.
  - **MAJOR (report path, ~line 416):** `_report_rel_path` still collides — include `checks_failed_to_run` in the hash AND add a true per-write nonce (e.g. `os.urandom(4).hex()`), so two same-second scans never overwrite. Keep date+time prefix for readability.
  - **MAJOR (flock silent degrade, ~line 374):** when `_ledger_lock` cannot acquire the lock (non-POSIX / open or flock failure), do NOT silently proceed as if serialized — set an explicit degraded flag and surface it (a one-line stderr/log warning and/or a field the caller can report). Concurrency safety must not silently vanish.
  - **MAJOR (rollback ownership, ~line 590):** `_propose_one` rollback must only unlink a backlog file it can confirm is its OWN reserved placeholder (e.g. read it back and verify it is still the placeholder, not a real item another writer created) — never unlink an id another writer legitimately populated.
  Invariant unchanged: no `write_lifecycle`, no commit; sole writes = report + ledger + `write_item`. Keep ruff + mypy clean.

### Task 2: scan SKILL.md — document the structural trigger
- **mode:** B
- **target:** plugin/skills/scan/SKILL.md
- **complexity:** simple
- **executor:** sonnet
- **parallel_group:** 1
- **est_tokens:** 600
- **est_cost_usd:** 0.03
- **verifier:** grep -q 'renmark-execute --scan' plugin/skills/scan/SKILL.md && echo OK
- **serves:** REQ-14
- **spec:**
  Update the scheduling / `--emit-cron` description in `plugin/skills/scan/SKILL.md`
  to reflect the pivot: the scheduled trigger is `renmark-execute --scan --propose`
  run directly via external cron / Task Scheduler (no LLM, no Bash). State that
  read-only is STRUCTURAL (the engine has no mutate path), and that the
  PreToolUse Bash-denylist hook is now OPTIONAL best-effort defense-in-depth, only
  relevant if a user triggers via `claude -p` instead — explicitly not the
  guarantee. Keep the read-only MAY/MUST-NOT contract and the next-steps.md
  citation intact. Do not weaken the REQ-14 invariant wording.

### Task 3: tests — update emit_cron expectations + Major regressions
- **mode:** B
- **target:** tests/test_scan.py
- **complexity:** medium
- **executor:** codex
- **parallel_group:** 2
- **est_tokens:** 1200
- **est_cost_usd:** 0.04
- **verifier:** python3 -m pytest -q tests/test_scan.py
- **serves:** REQ-14
- **spec:**
  Read the updated `renmark/scan.py` first. Update/extend `tests/test_scan.py` (keep all currently-passing tests green):
  - emit_cron: assert the output contains the direct `renmark-execute --scan --propose` trigger and a clear statement that read-only is structural; the hook section is present but labeled optional/best-effort. Drop any assertion that the hook is the guarantee.
  - report-path nonce: two `write_report` calls with identical findings AND identical `checks_failed_to_run` on the same day/second still produce DISTINCT paths.
  - flock degraded surfaced: when the lock cannot be acquired (simulate by monkeypatching the lock open/flock to fail), the degraded condition is surfaced (flag/warning), not silently swallowed — and the scan still completes.
  - rollback ownership: when `write_item` fails after `next_id`, rollback removes only the placeholder it created; a file representing a real item is NOT unlinked (simulate the collision).
  Use real backlog/summary APIs (no mocking the seam). Verifier: `python3 -m pytest -q tests/test_scan.py`.

---

## Cost preview

| Task | Target | Exec | Tokens (incl. overhead) | Cost |
|---|---|---|---|---|
| 1 | renmark/scan.py | opus | 11,800 | $0.18 |
| 2 | plugin/skills/scan/SKILL.md | sonnet | 10,600 | $0.03 |
| 3 | tests/test_scan.py | codex | 1,200 | $0.04 |

**Total: ~24k tokens · ~$0.25** · Executors: opus×1, sonnet×1, codex×1

<!--
artifact_type: plan
schema_version: 1
created_at: 2026-06-17T00:00:00Z
source_sha: e6244a2
related_plan: .renmark/plans/2026-06-15-req14-scan-proposer.plan.md
generator: plan
dependency_refs:
  - .renmark/reviews/2026-06-17-e6244a2.review.md
-->

# Plan — REQ-14 scan: code-review fixes (1 Critical, 4 Major, 1 Minor)

Addresses the codex review at `.renmark/reviews/2026-06-17-e6244a2.review.md`.
Wave 1 fixes the three code files in parallel (disjoint); Wave 2 extends the
test suite to lock in the fixes. The `cmd_scan` exit-code finding is scoped to
the partial case only (a proposer exiting 0 on findings is correct — findings
are expected output, not a gate failure).

---

### Task 1: scan.py — Critical hook bypass + 4 Major correctness fixes
- **mode:** B
- **target:** renmark/scan.py
- **complexity:** hard
- **executor:** opus
- **parallel_group:** 1
- **est_tokens:** 2400
- **est_cost_usd:** 0.18
- **verifier:** python3 -c "import renmark.scan as s; assert all(hasattr(s,n) for n in ('run_scan','propose_findings','write_report','emit_cron','READONLY_HOOK'))" && ruff check renmark/scan.py >/dev/null && echo OK
- **serves:** REQ-14
- **spec:**
  Fix five review findings in `renmark/scan.py` (read the review artifact for full context). Read the file first.
  - **CRITICAL (~line 507) — READONLY_HOOK denylist is bypassable.** The hook only blocks `git <verb>` when the mutating verb is adjacent. Make it robust: the hook command must parse the Bash command into shell words and BLOCK when the effective program is `git` (in any form — including `git -C <path>`, `git --git-dir=…`, `git --work-tree=…`, leading env assignments like `FOO=bar git …`) AND any mutating subcommand appears (commit, push, merge, rebase, reset, tag, branch -d/-D, checkout -b, am, cherry-pick, revert, stash, clean, gc, update-ref, fast-import) — regardless of position after global options. Also keep blocking `rm -rf` and obvious destructive redirections. Prefer a small embedded Python/shell tokenizer over a brittle single regex. In `emit_cron`, add one line stating the PRIMARY guarantee is `--disallowedTools Edit,Write` + restricted `--tools` + `--permission-mode dontAsk`, and the hook is defense-in-depth (allowlist posture). Add a module comment noting denylists are best-effort.
  - **MAJOR (~line 334) — report path collision.** `write_report` uses a date-only filename, so same-day scans overwrite each other and retarget all `evidence_path` links. Make the path unique (append a time component from `state.now_iso()` and/or a short content hash). CRITICAL ORDERING: compute/return the actual written path and ensure `propose_findings` uses THAT exact path for `evidence_path` (pass it in or store it on the report), not a recomputed date-only guess.
  - **MAJOR (~line 443) — stale-ledger suppression.** In the changed-fingerprint branch, if the ledger entry's `backlog_id` resolves to a missing item (`backlog.read_item(...) is None`), treat it as a stale miss: create a FRESH backlog item and update the ledger to the new id, instead of updating the ledger and skipping item creation (which permanently suppresses the finding).
  - **MAJOR (~line 429) — dedup race.** The load→check→write→save cycle on `.renmark/state/proposals.json` is unlocked; concurrent scans (explicitly allowed by SCHEDULED-QA.md) can double-file. Serialize the read/update/write with a file lock (e.g. a `.proposals.lock` via `os.open(O_CREAT|O_EXCL)` retry, or `fcntl.flock`), or an atomic compare-and-swap. Keep it dependency-free (stdlib).
  - **MAJOR (~line 462) — ghost backlog item.** `next_id()` writes a placeholder file as a side effect; if the subsequent `write_item()` fails, a ghost item leaks. Either allocate the id without a write side effect, or wrap so a failed `write_item` rolls back the reserved id/file. The whole propose-one-finding step must be all-or-nothing.
  Preserve the hard invariant: still NO `write_lifecycle`, no commit, sole writes = report + ledger + `write_item`. Keep ruff + mypy clean.

### Task 2: commands.py — partial-scan exit code
- **mode:** B
- **target:** renmark/cli/commands.py
- **complexity:** simple
- **executor:** sonnet
- **parallel_group:** 1
- **est_tokens:** 400
- **est_cost_usd:** 0.03
- **verifier:** python3 -c "from renmark.cli.commands import cmd_scan" && ruff check renmark/cli/commands.py >/dev/null && echo OK
- **serves:** REQ-14
- **spec:**
  In `cmd_scan` (renmark/cli/commands.py ~line 83): a successful scan (clean OR with findings that were reported/proposed) and `--emit-cron` still return 0 — a proposer is not a gate, findings are expected output. BUT return a non-zero code (e.g. 2) when the scan is PARTIAL — i.e. `report.checks_failed_to_run` is non-empty — so a scheduler can detect a degraded run. Update the bounded summary to note partial status. Do not change the 0-on-findings behavior. Read the file first to match style.

### Task 3: _engine.py — gate --propose/--emit-cron on --scan
- **mode:** B
- **target:** renmark/cli/_engine.py
- **complexity:** simple
- **executor:** sonnet
- **parallel_group:** 1
- **est_tokens:** 400
- **est_cost_usd:** 0.03
- **verifier:** python3 -m renmark --scan --emit-cron >/dev/null && echo OK
- **serves:** REQ-14
- **spec:**
  In `main()` argparse (renmark/cli/_engine.py ~line 999): `--propose` and `--emit-cron` are only meaningful with `--scan`. After parsing, if either is set without `args.scan`, print a one-line error to stderr and return a non-zero exit (e.g. 2) — fail fast instead of falling through to unrelated CLI paths. Do not break the valid `--scan` / `--scan --propose` / `--scan --emit-cron` invocations. Read the file first.

### Task 4: tests — lock in the review fixes
- **mode:** B
- **target:** tests/test_scan.py
- **complexity:** medium
- **executor:** codex
- **parallel_group:** 2
- **est_tokens:** 1400
- **est_cost_usd:** 0.04
- **verifier:** python3 -m pytest -q tests/test_scan.py
- **serves:** REQ-14
- **spec:**
  Extend `tests/test_scan.py` (keep the existing 9 tests passing) with regression tests for the review fixes. Read the updated `renmark/scan.py` first for exact APIs.
  - Hook robustness: assert the READONLY_HOOK / emit_cron deny logic blocks `git -C /tmp commit -m x`, `git --git-dir=.git commit`, and `FOO=1 git commit` (not just `git commit`), and still ALLOWS `git status` / `git diff` / `pytest`.
  - Report path uniqueness: two `write_report` calls "same day" produce DISTINCT paths (or assert a proposed item's `evidence_path` equals the actually-written report path, never a stale one).
  - Stale-ledger recreate: a ledger entry whose `backlog_id` no longer exists + a changed fingerprint → a NEW backlog item is created (finding not suppressed).
  - Partial exit code: `cmd_scan` returns non-zero when `checks_failed_to_run` is non-empty, and 0 on a clean/with-findings run.
  - Flag gating: `python -m renmark --propose` (no --scan) exits non-zero; `--scan --emit-cron` still exits 0.
  - (Best-effort) ghost-item: if `write_item` fails mid-propose, no orphan backlog file remains.
  Use real backlog/summary APIs (no mocking the seam). Verifier: `python3 -m pytest -q tests/test_scan.py`.

---

## Cost preview

| Task | Target | Exec | Tokens (incl. overhead) | Cost |
|---|---|---|---|---|
| 1 | renmark/scan.py | opus | 12,400 | $0.19 |
| 2 | renmark/cli/commands.py | sonnet | 10,400 | $0.03 |
| 3 | renmark/cli/_engine.py | sonnet | 10,400 | $0.03 |
| 4 | tests/test_scan.py | codex | 1,400 | $0.04 |

**Total: ~35k tokens · ~$0.29** · Executors: sonnet×2, opus×1, codex×1

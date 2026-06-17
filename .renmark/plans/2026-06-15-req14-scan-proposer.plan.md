<!--
artifact_type: plan
schema_version: 1
created_at: 2026-06-15T13:58:18Z
source_sha: e14ab253cd12d878df0065c60db8cd6d40ddacaf
related_plan: ""
generator: plan
dependency_refs:
  - .renmark/specs/2026-06-15-req14-scan-proposer.spec.md
-->

# Plan — `/renmark:scan`: scheduled read-only QA proposer lane (REQ-14)

Implements the spec at `.renmark/specs/2026-06-15-req14-scan-proposer.spec.md`. v1
ships a read-only worker (`renmark/scan.py`) that composes `run_audit()` + shell
verifiers, dedupes findings via `.renmark/state/proposals.json`, writes a report,
and (with `--propose`) lands `source="qa"` backlog items through the REQ-13 seam.
`--emit-cron` prints the restricted-tool cron line **and** the PreToolUse
Bash-denylist hook (read-only is enforced, not conventional). Scheduling stays
external (Option 1). No `verify --qa` composition in v1 (deferred). Stack
unchanged — Python ≥3.10, stdlib + pytest/ruff/mypy gates, no new deps.

**Wave plan:** Wave 1 builds the engine + all disjoint doc/registry files in
parallel; Wave 2–3 wire the CLI surface (serial — `_engine` imports `cmd_scan`);
Wave 4 tests the whole path.

---

### Task 1: scan engine + dedup ledger + emit-cron/hook
- **mode:** A
- **target:** renmark/scan.py
- **complexity:** hard
- **executor:** opus
- **parallel_group:** 1
- **est_tokens:** 2500
- **est_cost_usd:** 0.19
- **verifier:** python3 -c "import renmark.scan as s; assert all(hasattr(s,n) for n in ('run_scan','finding_key','ScanReport','Finding','emit_cron','propose_findings'))"
- **serves:** REQ-14
- **spec:**
  New module `renmark/scan.py`. Zero-LLM, never raises (mirror `renmark/audit.py`
  discipline). Public surface:
  - `@dataclass Finding`: `check, rule_id, target, risk, title, summary,
    recommended_action, fingerprint`.
  - `finding_key(f) -> str` → `f"{f.check}:{f.rule_id}:{f.target}"` (stable
    SARIF-style dedup key).
  - `@dataclass ScanReport`: `findings: list[Finding]`, `checks_run: list[str]`,
    `checks_failed_to_run: list[str]`, plus G9 fields `completion_state`
    (`complete|partial|failed`), `confidence`, `validation_status`.
  - `run_scan(repo) -> ScanReport`: calls `renmark.audit.run_audit(repo)` and
    normalizes its findings into `Finding`s; runs the project shell verifiers
    (`pytest -q`, `ruff check`, `mypy .`) via `renmark.verifier.run_verifier`,
    mapping failures to `Finding`s. A check that can't run → append to
    `checks_failed_to_run`, set `completion_state="partial"`, lower confidence;
    never crash.
  - Dedup ledger at `.renmark/state/proposals.json`: `load_ledger(repo)` /
    `save_ledger(repo, ledger)` mapping `finding_key → {backlog_id, fingerprint,
    first_seen, last_seen, state}`. Corrupt/missing → treat as empty (rebuild),
    never block.
  - `propose_findings(repo, report) -> list[str]`: for each finding — unseen →
    `renmark.backlog.write_item(repo, BacklogItem(id=renmark.backlog.next_id(repo),
    title=..., status="needs review", source="qa", evidence_path=<report path>,
    risk=..., summary=..., recommended_action=...))` + record in ledger;
    seen+same fingerprint → skip; seen+changed → update the linked item /
    re-surface. Returns the list of newly-proposed backlog IDs.
  - Report writer: `write_report(repo, report) -> str` via
    `renmark.summary.write_artifact(".renmark/reviews/<YYYY-MM-DD>-scan.review.md",
    artifact_type="scan", body=<full findings + evidence>, summary_lines=[≤5],
    generator="scan", confidence=..., validation_status=...)`. Date via
    `renmark.state.now_iso()` (no `Date.now()`); returns the path.
  - `READONLY_HOOK` constant: a PreToolUse hook JSON config (matcher `Bash`)
    whose command DENIES git-mutating / destructive commands — regex covering
    `git commit`, `git push`, `git merge`, `git rebase`, `git reset --hard`,
    `git tag`, `git branch -d|-D`, `git checkout -b`, `rm -rf`. Must emit a
    deny decision (non-zero / `{"decision":"block"}`) on match, allow otherwise.
  - `emit_cron(repo) -> str`: returns the text to print — the headless cron line
    `claude -p "/renmark:scan --propose" --tools "Read,Bash,Grep,Glob"
    --disallowedTools "Edit,Write" --permission-mode dontAsk`, the `READONLY_HOOK`
    JSON to paste into settings.json, and the one-time auth note
    (`claude setup-token` → `CLAUDE_CODE_OAUTH_TOKEN`). Pure string; no writes.
  - MUST NOT import/call `renmark.lifecycle.write_lifecycle`. Sole writes are the
    report, the ledger, and (via propose) `write_item`.
  Read the spec's Components + Read-only enforcement sections for exact intent.

### Task 2: CLI handler `cmd_scan`
- **mode:** B
- **target:** renmark/cli/commands.py
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 2
- **est_tokens:** 800
- **est_cost_usd:** 0.03
- **verifier:** python3 -c "from renmark.cli.commands import cmd_scan"
- **serves:** REQ-14
- **spec:**
  Add `cmd_scan(repo: Path, *, propose: bool = False, emit_cron: bool = False) ->
  int` mirroring the style of the existing `cmd_usage`/`cmd_analytics` handlers in
  this file. Behavior: if `emit_cron` → `print(renmark.scan.emit_cron(repo))` and
  return 0 (no scan, no writes). Else → `report = renmark.scan.run_scan(repo)`,
  `path = renmark.scan.write_report(repo, report)`; if `propose` →
  `ids = renmark.scan.propose_findings(repo, report)` and print a bounded ≤5-line
  summary (counts: findings, newly proposed, deduped-skipped, report path); if not
  `propose`, print the same bounded summary with "proposed: 0 (run with --propose)".
  Never print full findings (G11). Import `renmark.scan` lazily inside the function
  (match the lazy-import pattern of the sibling handlers). Also add `cmd_scan` to
  `renmark/cli/__init__.py`'s imports + `__all__` (keep the re-export surface
  consistent with the other `cmd_*`).

### Task 3: argparse wiring for `--scan`
- **mode:** B
- **target:** renmark/cli/_engine.py
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 3
- **est_tokens:** 700
- **est_cost_usd:** 0.03
- **verifier:** python3 -m renmark --scan --emit-cron >/dev/null && echo OK
- **serves:** REQ-14
- **spec:**
  In `main()`'s argparse setup (where `--usage`/`--analytics`/`--roadmap` are
  registered), add a `--scan` flag plus `--propose` and `--emit-cron` modifiers,
  and route `--scan` to `cmd_scan(repo, propose=args.propose, emit_cron=args.emit_cron)`
  (import from `.commands`). Match the existing flag-dispatch idiom exactly; do not
  restructure unrelated parsing. `--scan --emit-cron` must run read-only and exit 0
  without touching disk. Verifier exercises the full CLI path (depends on Tasks 1–2).

### Task 4: tests for the scan lane
- **mode:** A
- **target:** tests/test_scan.py
- **complexity:** medium
- **executor:** codex
- **parallel_group:** 4
- **est_tokens:** 1600
- **est_cost_usd:** 0.04
- **verifier:** python3 -m pytest -q tests/test_scan.py
- **serves:** REQ-14
- **spec:**
  Pytest suite using tmp_path repos. Cover: (1) `finding_key` stability /
  format; (2) dedup — same finding twice → one backlog item, second
  `propose_findings` returns []; (3) changed fingerprint → updates/re-surfaces,
  not duplicated; (4) default path (`cmd_scan` without propose) writes a report
  but ZERO backlog items (assert `.renmark/state/backlog/` empty); (5) `--propose`
  writes a `BacklogItem` with `source="qa"`, `status="needs review"`, and
  `evidence_path` pointing at the report; (6) `emit_cron` output contains the
  restricted `--tools`/`--disallowedTools`/`--permission-mode dontAsk` flags AND a
  hook that blocks `git commit`; (7) enforcement — assert `renmark.scan` never
  references `write_lifecycle` (e.g. source-scan / monkeypatch guard) and that a
  scan run leaves git/lifecycle untouched; (8) corrupt `proposals.json` → treated
  as empty, scan still succeeds. Use `renmark.backlog`/`renmark.summary` real APIs;
  do not mock the seam.

### Task 5: register `scan` in the lifecycle registry
- **mode:** B
- **target:** renmark/lifecycle.py
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 1
- **est_tokens:** 300
- **est_cost_usd:** 0.00
- **verifier:** python3 -c "from renmark.lifecycle import DOMAIN_BY_SKILL, IMPLEMENTED_SKILLS, AUX_SKILLS; assert DOMAIN_BY_SKILL.get('scan')=='audit'; assert 'scan' in IMPLEMENTED_SKILLS; assert 'scan' in AUX_SKILLS"
- **serves:** REQ-14
- **spec:**
  Add `'scan'` to `IMPLEMENTED_SKILLS` (frozenset, ~line 50), add
  `"scan": "audit"` to `DOMAIN_BY_SKILL` (dict, ~line 105), and add `'scan'` to
  `AUX_SKILLS` (frozenset, ~line 165). Preserve alphabetical/existing ordering and
  formatting. Pure additions — touch nothing else.

### Task 6: `/renmark:scan` SKILL.md
- **mode:** A
- **target:** plugin/skills/scan/SKILL.md
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 1
- **est_tokens:** 1500
- **est_cost_usd:** 0.03
- **verifier:** test -f plugin/skills/scan/SKILL.md && grep -q '^name: scan' plugin/skills/scan/SKILL.md
- **serves:** REQ-14
- **spec:**
  New skill doc (audit domain). Frontmatter `name: scan` + a description matching
  the help entry (Task 8). Body: Overview (read-only QA proposer lane, REQ-14,
  upstream of backlog); Step 0 context check via
  `lifecycle.skill_preamble(repo, 'scan')`; the three modes (`renmark-execute
  --scan`, `--scan --propose`, `--scan --emit-cron`) and what each prints; the
  hard read-only contract (MAY inspect/run read-only checks/write report/propose;
  MUST NOT edit/commit/merge/release/edit PRD/escalate budget/auto-execute — cite
  REQ-14 + `plugin/skills/backlog/SCHEDULED-QA.md`); the bounded-output rule (Opus
  reads only the ≤5-line summary, never findings — G11); and a "What's next"
  pointing at `/renmark:backlog` to triage proposed items. Mirror the structure of
  `plugin/skills/audit/SKILL.md`. Note in a maintainer line that read-only +
  external-scheduling are invariants (mirror in CLAUDE.md/AGENTS.md).

### Task 7: `/renmark:scan` command shim
- **mode:** A
- **target:** plugin/commands/scan.md
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 1
- **est_tokens:** 250
- **est_cost_usd:** 0.00
- **verifier:** test -f plugin/commands/scan.md
- **serves:** REQ-14
- **spec:**
  Thin command shim matching the format of `plugin/commands/audit.md`: point at
  `plugin/skills/scan/SKILL.md` and pass through the user input. Do not duplicate
  skill logic — shim only.

### Task 8: add `/renmark:scan` to `/renmark:help`
- **mode:** B
- **target:** plugin/skills/help/SKILL.md
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 1
- **est_tokens:** 250
- **est_cost_usd:** 0.00
- **verifier:** grep -q 'renmark:scan' plugin/skills/help/SKILL.md
- **serves:** REQ-14
- **spec:**
  Add a `/renmark:scan` entry to the printed help block, in the
  "Governance / reporting" section near `/renmark:audit`/`/renmark:backlog`. Two to
  three lines: name + that it's the read-only scheduled QA proposer lane
  (`--propose` lands deduped backlog items, `--emit-cron` prints the safe trigger).
  Keep the existing block's spacing/format so `audit`'s description_drift pass
  stays green.

---

## Cost preview

| Task | Target | Exec | Tokens (incl. overhead) | Cost |
|---|---|---|---|---|
| 1 | renmark/scan.py | opus | 12,500 | $0.19 |
| 2 | renmark/cli/commands.py | sonnet | 10,800 | $0.03 |
| 3 | renmark/cli/_engine.py | sonnet | 10,700 | $0.03 |
| 4 | tests/test_scan.py | codex | 1,600 | $0.04 |
| 5 | renmark/lifecycle.py | haiku | 10,300 | $0.00 |
| 6 | plugin/skills/scan/SKILL.md | sonnet | 11,500 | $0.03 |
| 7 | plugin/commands/scan.md | haiku | 10,250 | $0.00 |
| 8 | plugin/skills/help/SKILL.md | haiku | 10,200 | $0.00 |

**Total: ~88k tokens · ~$0.33** · Executors: haiku×3, codex×1, sonnet×3, opus×1

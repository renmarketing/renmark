<!--
artifact_type: spec
schema_version: 1
created_at: 2026-06-15T13:58:18Z
source_sha: e14ab253cd12d878df0065c60db8cd6d40ddacaf
related_plan: ""
generator: brainstorm
stale_after: 2026-09-15T00:00:00Z
dependency_refs:
  - PRD.md (REQ-14, REQ-12, REQ-13, REQ-15)
  - plugin/skills/backlog/SCHEDULED-QA.md
  - .renmark/research/2026-06-14-req14-scheduling-access.research.md
  - .renmark/research/2026-06-14-req14-prior-art.research.md
  - .renmark/research/2026-06-14-req14-reuse.research.md
-->

# Spec — `/renmark:scan`: scheduled read-only QA proposer lane (REQ-14)

## Context

REQ-14 reserves a **scheduled QA / Deep-QA lane** as a **read-only proposer**:
scheduled subagents MAY inspect, research, run checks, write reports, and
*propose* backlog items, but MUST NOT edit code, commit, merge, release, edit
`PRD.md`, escalate budget, or auto-execute. It is the third of renmark's four
lanes (foreground feature → backlog intake → **scheduled QA** → bounded
execution) and the **upstream** of the backlog intake buffer (REQ-13).

REQ-13 already shipped the integration seam (`plugin/skills/backlog/SCHEDULED-QA.md`):
the lane's *only* mutation into shared state is a single
`write_item(repo, BacklogItem(..., source="qa", status="needs review", evidence_path=...))`
call. This spec designs the worker that calls it.

PRD alignment (checked 2026-06-14): **aligned** — designing the read-only
proposer is inside REQ-14's stated scope; autonomous scheduled *execution*
remains out of scope and is untouched here.

## Goals

1. Ship `/renmark:scan` — a read-only worker that composes existing read-only
   checks, writes a bounded report, and (with `--propose`) lands deduped
   `source="qa"` backlog items for human triage.
2. Make read-only **enforced**, not conventional: the scheduled invocation runs
   under a restricted tool-list **and** a PreToolUse Bash-denylist hook.
3. Keep scheduling **external** to renmark (Option 1): renmark ships the worker
   and a `--emit-cron` helper that prints the safe trigger command; renmark
   never daemonizes, never registers or tracks a schedule.
4. Guarantee proposal **deduplication** before any backlog write, so repeated
   scheduled runs never spam the backlog (the Dependabot noise failure mode).

## Non-goals (feature-scoped)

- **Autonomous scheduled execution** — out of scope per REQ-14 (product-level
  non-goal; see PRD, do not duplicate here). The lane proposes; it never runs
  the fix.
- **renmark-managed scheduling** — no `/renmark:schedule` surface, no CronCreate
  registration, no schedule state under `.renmark/`. The trigger is owned by the
  user's OS cron / Task Scheduler (Option 1). `--emit-cron` only *prints*.
- **`verify --qa` / `--deep-qa` composition** — deferred to v2. v1 composes only
  programmatic/shell checks (`run_audit()` + verifiers). The browser flow is
  skill-only today and not callable as a function.
- **Cloud Routines (`/schedule`) as the trigger** — ruled out: cloud routines
  run on a fresh GitHub clone with no access to the local working tree, so they
  cannot read git or write `.renmark/`.
- No merge / PR / release / `PRD.md` edit / budget escalation / Loop Mode trigger.

## Architecture

```
[external trigger]                         renmark (the worker)
 WSL cron / Task Scheduler                  ┌───────────────────────────────────┐
   │                                        │  /renmark:scan [--propose]          │
   │  claude -p "/renmark:scan --propose" \ │   1. run read-only checks:          │
   │    --tools "Read,Bash,Grep,Glob" \     │      run_audit(repo) -> AuditReport │
   │    --disallowedTools "Edit,Write" \    │      + shell verifiers (pytest/     │
   │    --permission-mode dontAsk           │        ruff/mypy via run_verifier)  │
   │  + PreToolUse hook (git/rm denylist)   │   2. normalize -> findings[]        │
   └───────────────────────────────────────│   3. dedupe vs proposals.json       │
                                            │   4. write report (.renmark/reviews)│
                                            │   5. (--propose) write_item(source= │
                                            │        "qa", status="needs review") │
                                            └───────────────────────────────────┘
                                                          │ single seam
                                                          ▼
                                            .renmark/state/backlog/BL-NNNN.json
                                                          │
                                            human runs /renmark:backlog → triage
                                            → "Approve and build" → bounded Loop (REQ-13)
```

Read-only run, parallel-safe (exempt from the one-loop-per-tree execution lock,
per SCHEDULED-QA.md).

## Components

### 1. `renmark/scan.py` (new module — the engine)
- `run_scan(repo) -> ScanReport` — runs `run_audit()` + the project's shell
  verifiers, normalizes results into a flat `findings: list[Finding]`. Pure,
  zero-LLM, never raises (mirrors `audit.run_audit` discipline).
- `Finding` dataclass: `check`, `rule_id`, `target`, `severity`/`risk`,
  `title`, `summary`, `recommended_action`, `fingerprint`.
- `finding_key(f) -> str` = `f"{f.check}:{f.rule_id}:{f.target}"` (SARIF-style
  stable key — the dedup primitive).
- `ScanReport`: findings + run metadata (checks_run, checks_failed_to_run,
  completion_state, confidence, validation_status).

### 2. Dedup ledger — `.renmark/state/proposals.json`
- Maps `finding_key` → `{backlog_id, fingerprint, first_seen, last_seen, state}`.
- `load_ledger` / `save_ledger`; unreadable/corrupt → treat as empty and rebuild
  (never block a scan).
- Decision per finding before write: **unseen** → propose + record; **seen +
  same fingerprint** → skip; **seen + changed fingerprint** → update the linked
  item / re-surface. Lives in gitignored `.renmark/state/` (consistent with the
  backlog item store).

### 3. Backlog seam (reuse — no new API)
- `--propose` calls `renmark.backlog.write_item(repo, BacklogItem(id=next_id(repo),
  title=..., status="needs review", source="qa", evidence_path=<report path>,
  risk=..., summary=..., recommended_action=...))` — exactly the documented seam.
- Default `/renmark:scan` (no `--propose`) writes **zero** backlog items.

### 4. Report writer (reuse)
- `summary.write_artifact(".renmark/reviews/YYYY-MM-DD-scan.review.md",
  artifact_type="scan", body=<full findings + evidence>, summary_lines=[≤5],
  generator="scan", confidence=..., validation_status=...)`. Heavy evidence on
  disk; orchestrator/user sees only the ≤5-line summary (G6/G11).

### 5. `--emit-cron` (the trigger helper)
- Prints (does not execute) the exact read-only invocation for WSL cron /
  Windows Task Scheduler, including the restricted tool-list flags and the
  PreToolUse hook install line. Also prints the one-time auth note
  (`claude setup-token` → `CLAUDE_CODE_OAUTH_TOKEN`).

### 6. PreToolUse Bash-denylist hook (v1 — enforced read-only)
- A hook config + matcher that **denies** Bash commands matching git-mutating /
  destructive verbs: `git commit|push|merge|rebase|tag|reset --hard`,
  `git branch -d|-D`, `git checkout -b`, `rm -rf`, redirections into tracked
  paths. Emitted/installed by `--emit-cron` setup so the scheduled run *cannot*
  mutate even though Bash is enabled for verifiers.
- Defense-in-depth layered on top of `--disallowedTools "Edit,Write"` +
  `--permission-mode dontAsk`.

### 7. SKILL + shim + registry wiring
- `plugin/skills/scan/SKILL.md` (audit domain) + `plugin/commands/scan.md` shim.
- `renmark/lifecycle.py`: add `scan` → `audit` in `DOMAIN_BY_SKILL`, and to
  `IMPLEMENTED_SKILLS` / `AUX_SKILLS`.
- Add the `/renmark:scan` entry to `/renmark:help`'s static list (else
  `audit`'s `description_drift` pass flags it).

## Data flow (read-only contract)

The **only** writes a scan run performs:
1. Its report artifact under `.renmark/reviews/`.
2. The dedup ledger `.renmark/state/proposals.json`.
3. (`--propose` only) backlog items via `write_item(... source="qa")`.

It never advances `lifecycle.json`, never commits, never touches product code.

## Read-only enforcement (three layers)

| Layer | Mechanism | Stops |
|---|---|---|
| Tool-list isolation | `--tools "Read,Bash,Grep,Glob" --disallowedTools "Edit,Write"` | Direct model Edit/Write |
| Permission mode | `--permission-mode dontAsk` | Anything not pre-approved (no stall, unlike plan mode headless) |
| **PreToolUse hook** | git/rm/destructive-verb Bash denylist | Mutation *through* Bash (the residual gap) |
| Skill convention | never call `write_lifecycle`; only mutations = report + ledger + `write_item` | In-process drift |

## Error handling

- A check that can't run (e.g. pytest absent) → record in `checks_failed_to_run`,
  set `completion_state="partial"`, lower `confidence`, continue. Never crash.
- Corrupt/missing ledger → treat as empty, rebuild.
- `write_item` failure → report still persists; surface the failure in the
  bounded summary; do not lose findings.
- Zero findings → write report, propose nothing, exit clean.
- All executor outputs carry G9 fields (`completion_state`, `confidence`,
  `validation_status`, `parser_success`, `schema_compliance`).

## Success criteria

1. `/renmark:scan` runs read-only, writes a `.renmark/reviews/*-scan.review.md`
   report, and writes **zero** backlog items.
2. `/renmark:scan --propose` writes deduped `source="qa"` / `status="needs review"`
   items with `evidence_path` → the report; a second immediate run with no code
   change proposes **0** new items (dedup proven).
3. A changed finding (different fingerprint) updates/re-surfaces its item rather
   than duplicating it.
4. `/renmark:scan --emit-cron` prints the read-only cron line + hook install +
   auth note, and writes nothing.
5. The scheduled invocation cannot commit/merge/edit code: verified by a test
   asserting the hook denies `git commit` and that scan never calls
   `write_lifecycle`.
6. `scan` is registered in `DOMAIN_BY_SKILL` (audit), `IMPLEMENTED_SKILLS`,
   `AUX_SKILLS`, and `/renmark:help`; `/renmark:audit` description_drift passes.

## Testing

- **Unit:** `finding_key` stability; dedup decisions (unseen→propose,
  same→skip, changed→update); default mode writes 0 items; `--propose` builds a
  correct `BacklogItem`; `--emit-cron` output contains the restricted flags +
  hook and exits without writes.
- **Integration:** scan a repo with a known audit finding → report + 1 proposed
  item; re-run → 0 new items.
- **Enforcement:** assert the PreToolUse hook denylist rejects `git commit` /
  `git push` / `rm -rf`; assert scan never calls `lifecycle.write_lifecycle`.
- Verifier (plan): `pytest -q` (matches project dev gate).

## Prior art & references

- `.renmark/research/2026-06-14-req14-scheduling-access.research.md` — Claude Code
  scheduling/access: cloud routines ruled out (fresh clone); WSL cron + headless
  `claude -p "/renmark:scan"` is the local trigger; read-only flags; auth via
  `CLAUDE_CODE_OAUTH_TOKEN`; plan-mode stalls headless.
- `.renmark/research/2026-06-14-req14-prior-art.research.md` — name the worker
  after what it does (not `:scout`/`:patrol`); Renovate branch-as-key dedup;
  SARIF finding schema; "tool-list isolation, not self-restraint"; stable
  finding-key is a prerequisite, not v2.
- `.renmark/research/2026-06-14-req14-reuse.research.md` — `run_audit(repo)`
  returns structured findings (reuse); `write_item`/`next_id` in
  `renmark/backlog.py`; `verify --qa` is skill-only (defer); read-only is
  convention-only today (this spec upgrades it to enforced); domain = `audit`.
- `plugin/skills/backlog/SCHEDULED-QA.md` — the pre-built integration seam.

## Open questions for `/renmark:plan`

- Exact `Finding` normalization mapping from `AuditReport` fields → `risk`.
- Whether the PreToolUse hook ships as a template file installed by `--emit-cron`
  or printed inline for the user to add to settings.json (lean: print + offer to
  write).

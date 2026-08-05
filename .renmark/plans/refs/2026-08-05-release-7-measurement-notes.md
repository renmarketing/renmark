# Release 7 measurement notes (sibling reference for Task 1)

Real facts and exact query recipes gathered during planning
(2026-08-05), for the Task 1 executor to cross-check its own mining
against. These are starting points, not a substitute for the executor
re-running the queries fresh.

## Rethink (governed-orchestration-assurance, Releases 1-6)

- **Plan files:** `.renmark/plans/2026-08-0[4-5]-governed-orchestration-assurance-release-*.plan.md`
  (releases 1-6). Task counts found at planning time: release-1: 2,
  release-2: 1, release-3: 5, release-4: 6, release-5: 3, release-6: 9 —
  total 26 tasks. Executor mix found at planning time (grep `executor:`
  across those files): codex×9, haiku×3, opus×2, sonnet×12.
- **Token spend:** `.renmark/analytics/task-runs.jsonl` rows with
  `ts >= "2026-08-04T00:00:00"` — 2 rows found at planning time, both
  sonnet, both `measured: false`, totaling 21,800 tokens (10,000 +
  11,800). No codex rows carry tokens in this log (known gap — codex
  doesn't surface tokens, per the 2026-08-02 audit already cited in
  `orchestration-baseline.md`).
- **Ledger cross-check:** `.renmark/ledger/events.jsonl` — 24 total rows,
  all dated 2026-08-02 through 2026-08-05T03:40; 7 `work_order` / 7
  `work_result` (all `status: complete`) / 7 `inspection_report` (all
  `pass`) / 3 `escalation`. This is materially fewer than the 26 planned
  tasks above — a ledger-coverage gap, not evidence of fewer real
  dispatches.
- **Owner-gate count:** `.renmark/rethink/governed-orchestration-assurance/roadmap.md`'s
  "Execution Gate — decision (2026-08-04)" section records exactly one
  Owner approval (Stage 9, AskUserQuestion) covering Releases 1+.
  `.renmark/state/delivery.json`'s `provenance_events` — 12 total events,
  0 with `ts >= "2026-08-04"` at planning time — consistent with zero
  additional routine per-work-package gates since.
- **Git evidence of Releases 2-6 completion:** `git log --oneline` shows
  checkpoint/completion commits `4b29358`..`1d6787b` (2026-08-05) for
  releases 2-6, confirming they ran (not just planned).

## Feature/Fix

- Existing figure in `orchestration-baseline.md`'s 2026-08-04 capture:
  502,107 measured tokens (`orchestration-baseline-controls` feature,
  2026-08-02/03) — 12 `measured: true` rows in `task-runs.jsonl` (haiku
  173,631 / sonnet 278,389 / opus 50,087).
- At planning time, no fresher `measured: true` rows or feature-run
  entries were found postdating that capture other than the 2 Rethink
  rows listed above (which belong to the Rethink scenario, not
  Feature/Fix). Re-check `task-runs.jsonl` and
  `.renmark/analytics/feature-runs.jsonl` fresh before concluding.

## Orchestrate

- No data newer than the 2026-08-02 audit (M2 milestone, R-0.2, R-0.3)
  was found at planning time. Re-check fresh before concluding.

## Start

- No qualifying `/renmark:start` run was found on disk at planning time
  (still `unknown`). Re-check fresh before concluding.

## AGENT_OVERHEAD_TOKENS drift check

- `renmark/cost.py`: `AGENT_OVERHEAD_TOKENS: int = 10_000` (line ~83).
- `renmark/roadmap.py`: `AGENT_OVERHEAD_TOKENS = 10_000` (line ~38).
- `git log -p --since="2026-08-02" -- renmark/cost.py renmark/roadmap.py`
  produced no hits on `AGENT_OVERHEAD_TOKENS` at planning time — the
  constant has not changed since the `ORCHESTRATION-BASELINE-2026-08`
  pin (`d9cccc5`, 2026-08-02).

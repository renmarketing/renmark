---
artifact_type: rethink-roadmap
schema_version: 1
created_at: 2026-08-06T22:31:00Z
source_sha: 3142267
related_plan: null
generator: sonnet
---

# Incremental transformation roadmap — cross-host-native-tool-leverage

Four small, independently usable releases, built from the Owner-approved
Solution Gate (classification.md + target-blueprint.md). Zero
Remove/Replace items; everything additive; no new abstraction layer. Old
and new mechanisms coexist deliberately (cron heartbeat + ScheduleWakeup;
git-worktree shell-out fallback + ExitWorktree) — not a defect.

## Release 1 — Baseline and compatibility coverage

- **Value**: turns Stage 2's baseline into real, runnable compatibility
  tests specific to this transformation's surface — the host/dispatch/
  interaction-targeted subset (220 passed/17 skipped) and the core
  cross-host files (70 passed) get an explicit, named test target so later
  releases have a fast, precise regression gate instead of only the full
  suite.
- **AC-ids**: none new — this release formalizes Stage 2's existing
  baseline evidence, it does not advance a PRD requirement itself.
- **Compatibility guarantee**: full suite stays green (2101 passed, 32
  skipped as of this rethink's Stage 2 measurement); the targeted
  host/dispatch/interaction subset becomes a named `pytest -k` target
  documented in this file for reuse by releases 2-4's own verifiers.
- **Migration steps**: none (test-only, no production code moves).
- **Observability hook**: `pytest -q -k "host or codex or claude or dispatch or interaction"` becomes the standard fast-gate command cited by every later release's verifier.
- **Rollback path**: revert the test-target documentation commit; no
  runtime behavior change either way.
- **Owner acceptance scenario**: Owner runs the named fast-gate command and
  sees the same pass count Stage 2 recorded, confirming no drift occurred
  between Stage 2's measurement and Release 2's start.

## Release 2 — Consolidate dispatch.py's HostName onto hosts.py's HostKind

- **Value**: closes the real duplication Stage 5's modularity assessment
  found — `renmark/dispatch.py` currently defines its own independent
  `HostName` Literal and validation, fully bypassing `renmark/hosts.py`'s
  `HostKind`/aliases/UNKNOWN fallback. One host-type encoding, not two that
  can silently drift.
- **AC-ids**: advances the modularity finding from classification.md
  (`dispatch.py`'s `HostName` Literal — classified Improve).
- **Compatibility guarantee**: #1 (`pytest -q` count) — specifically, every
  test exercising `dispatch.py`'s host branching must produce byte-identical
  routing decisions before and after the consolidation; the Release 1
  fast-gate target is the primary regression check.
- **Migration steps**: replace `dispatch.py`'s own `HostName` Literal +
  validation with imports from `hosts.py`'s `HostKind`/`capabilities_for`;
  update every consumer of the old type; no change to any host-branch
  DECISION, only to where the type/validation is defined.
- **Observability hook**: a new test asserting `dispatch.py` has zero
  independent host-type definitions (grep-based regression guard, matching
  this program's own established pattern for preventing drift — see
  `tests/test_dangerous_gate_wiring.py` for the precedent style).
- **Rollback path**: revert the consolidation commit; `dispatch.py`'s
  original (duplicated) encoding is restored, functionally identical to
  today.
- **Owner acceptance scenario**: Owner runs the new grep-based regression
  test and sees it pass, confirming `hosts.py` is genuinely the sole source
  of host-type truth.

## Release 3 — ExitWorktree adoption + a bounded ScheduleWakeup spike

*(Revised 2026-08-06 — Stage 8a Inspector challenge FAIL, one bounded
correction pass: the original draft of this release grouped `ScheduleWakeup`
with `ExitWorktree` as two equally-confirmed native tools, dropped
classification.md's own stated fallback-to-spike contingency, and
misattributed REQ-30 as a requirement these items "advance." All three
corrected below; re-submitted to the Inspector once, per the pipeline's
one-correction-pass rule.)*

- **Value**: adopts `ExitWorktree` — a **confirmed, primary-source-verified**
  native Claude Code tool (external-benchmark.md §1: "verified fact") —
  for `finish/SKILL.md` §3.6's one mutating `git worktree remove`
  shell-out. `ScheduleWakeup` is treated differently in this release: its
  live-session-invokability was **only inferred**, never confirmed by
  primary-source external research (external-benchmark.md §1: "Scheduled/
  cron agent execution: not found in official docs... insufficiently
  sourced, flagged in Unknowns"), so this release does NOT commit to
  shipping it — it runs the bounded spike classification.md itself said
  a "tool does not exist" wall would require, instead of asserting the
  tool works.
- **AC-ids**: none directly. REQ-30 (orchestration efficiency) is a
  **guardrail** on this release, not a requirement it advances or
  satisfies — target-blueprint.md §1's traceability table is explicit that
  "REQ-30 is the guardrail... the capability itself is not tied to a
  numbered REQ." This release must stay under REQ-30's 15% budget; it does
  not close any PRD acceptance criterion.
- **Compatibility guarantee**: #1, plus explicitly: on any host without
  the new `HostCapabilities.supports_exit_worktree` field set True,
  behavior is byte-identical to today (the existing safe non-`--force`
  shell-out remains the fallback, unconditionally). `ScheduleWakeup` ships
  no capability field or behavior change in this release — see spike below.
- **Migration steps (ExitWorktree — committed)**: add
  `supports_exit_worktree: bool = False` to `hosts.py`'s
  `HostCapabilities` dataclass (additive, default False); add one
  `finish/SKILL.md` §3.6 instruction to try `ExitWorktree` first when the
  capability field is True, falling back to the existing shell-out
  otherwise. Skill-prose plus a capability gate — `ExitWorktree` is
  host-invoked, never Python-invoked, so there is no new importable Python
  function that calls it directly (confirmed by Stage 7's blueprint
  correction).
- **Bounded spike (ScheduleWakeup — not committed)**: **Question:** is
  `ScheduleWakeup` (or an equivalent scheduled-resume primitive) actually
  callable by a live Claude Code session executing a renmark skill today?
  **Scope:** attempt one real `ScheduleWakeup`-equivalent call from within
  a live orchestrate-pause scenario; if unavailable, note the exact
  failure. **Evidence requirement:** either a successful live invocation
  (screenshot/log of the call succeeding) or a confirmed "tool does not
  exist in this harness" result — either outcome closes the spike.
  **Budget:** one session, no production code changes beyond the spike
  harness itself. **Stop condition:** if confirmed available, a FOLLOW-UP
  release (not this one) adds the `supports_schedule_wakeup` capability
  field and skill-prose wiring, mirroring `ExitWorktree`'s pattern exactly;
  if confirmed unavailable, close as a documented Keep-as-is (the existing
  cron/heartbeat path remains the sole resume mechanism, no code change).
- **Observability hook**: `renmark-execute --usage` shows whether
  `ExitWorktree` or the shell-out fallback fired for a given worktree
  cleanup (a bounded log line, not a new persistence field).
- **Rollback path**: revert the `HostCapabilities.supports_exit_worktree`
  field addition and the one skill-prose instruction; it defaults to
  False, so not setting it anywhere is already a full rollback. The
  ScheduleWakeup spike produces no code to roll back.
- **Owner acceptance scenario**: Owner triggers `finish`'s worktree
  cleanup step on a host with `supports_exit_worktree=True` and observes
  `ExitWorktree` fire instead of the raw shell-out. Separately, Owner
  reviews the ScheduleWakeup spike's evidence (call succeeded, or
  confirmed unavailable) before any decision to build the follow-up
  release.

### Execution note — ExitWorktree wiring dropped (2026-08-07, Owner decision)

At implementation time, `ExitWorktree`'s actual tool contract was checked
directly (not just external-benchmark.md's existence claim) and found
unusable for `finish/SKILL.md` §3.6's target scenario:

- `ExitWorktree` only operates on a worktree created by `EnterWorktree`
  **in the current session** — it explicitly excludes worktrees made with
  `git worktree add`, and worktrees from a prior session (even ones
  `EnterWorktree` made earlier in that prior session).
- It takes no `path` parameter — there is no way to target an arbitrary
  existing worktree by path at all.
- Deeper finding: §3.6's own target scenario ("the feature worktree that
  `/renmark:feature` created") does not exist in current renmark — no
  code path creates a feature worktree at all (`feature/SKILL.md` does a
  plain `git checkout -b`; `renmark/worktree.py` only lists/checks
  staleness). `git worktree list` on this repo shows only `main`. §3.6 is
  stale prose from an earlier worktree-per-feature design that was
  replaced by branch-per-feature. Logged separately as an Open bug in
  `.renmark/memory/bugs.md` ("finish/SKILL.md §3.6 worktree-cleanup
  targets a dead code path") — out of this release's chartered scope to
  fix.

**Owner decision (AskUserQuestion):** ship the additive
`supports_exit_worktree` capability field only (documents the tool's
existence, `True` for `HostKind.CLAUDE_CODE`, `False` elsewhere, zero
behavior change — matches the original compatibility guarantee exactly).
Do **not** wire the §3.6 instruction — it would be dead wiring that never
fires. This closes the ExitWorktree half of Release 3 as a documented
Keep-as-is-but-flagged rather than a completed adoption; the field exists
for a future release that either fixes §3.6's real worktree-creation gap
or finds a different, in-session use for `ExitWorktree`.

## Release 4 — REQ-31 Codex task-tracking CLI wrapper + skill wiring

- **Value**: closes REQ-31's Codex gap in code (the PRD text was already
  amended this same rethink pass). A live, interactive Codex session
  acting as host currently has zero `task_tracking` calls anywhere in its
  dispatch path — this release gives it one.
- **AC-ids**: REQ-31 (native task tracking for dispatched work) — the
  final piece closing this requirement to `met` for both hosts.
- **Compatibility guarantee**: #1, plus: the existing headless
  `codex`/subprocess path (`renmark/cli/_wave_loop.py`, already wired) is
  completely untouched — this release only adds a NEW path for live,
  interactive Codex-as-host sessions, which today has no `task_tracking`
  calls at all (net-new coverage, not a modification of existing behavior).
- **Migration steps**: add `renmark-execute --task-create`/
  `--task-in-progress`/`--task-complete` CLI subcommands wrapping
  `renmark.task_tracking`'s existing functions (`create_or_reuse_task`,
  `mark_in_progress`, `complete_task`) — this is the corrected design from
  Stage 7's blueprint (the classification's original plan to call
  `task_tracking` directly from `dispatch.py`'s codex-branch would have
  violated `build_host_dispatch_plan`'s documented "no dispatch, no
  state/ledger writes" invariant). Add an `orchestrate/SKILL.md`
  instruction telling a live Codex session to shell out to these new
  subcommands around each dispatch, mirroring the existing Claude-Code
  `TaskCreate`/`TaskUpdate` prose pattern.
- **Observability hook**: `.renmark/state/tasks.json` gains real entries
  from live Codex sessions (today it only ever gets entries from the
  headless subprocess path) — a `source: "codex-live"` vs
  `"codex-headless"` field (additive) makes this observable in
  `renmark-execute --analytics`.
- **Rollback path**: revert the new CLI subcommands and the skill-prose
  instruction; the headless path is untouched throughout, so this is a
  clean, isolated rollback.
- **Owner acceptance scenario**: Owner runs a renmark skill from a live,
  interactive Codex CLI session, dispatches a subagent, and sees a real
  task entry appear in `.renmark/state/tasks.json` with
  `source: "codex-live"` — proving REQ-31 is now genuinely met on Codex,
  not just correctly worded in the PRD.

## Deferred (not in this roadmap, tracked separately)

- **`lifecycle/stage.py::_lifecycle_host` precedence duplication** —
  classification.md's one `Unknown — needs a spike` entry. Bounded (30
  min, single-file read + one test run), not blocking, explicitly out of
  this roadmap's 4 approved scope items. Logged for a future rethink pass
  or a cheap bundle-in if Release 2's PR ends up touching adjacent code
  anyway.
- **Hermes** — deferred at the Transformation Intake; not part of this
  transformation at all.

## Non-goals reaffirmed

No new host-adapter abstraction layer (Direction Gate explicitly rejected
this alternative). No change to `WorkOrder`/capability-envelope/G11
isolation, the already-adopted Workflow-fanout decision, or
`task_tracking.py`'s domain logic — all confirmed Keep by external research
(Stage 4) as genuine value neither host provides natively.

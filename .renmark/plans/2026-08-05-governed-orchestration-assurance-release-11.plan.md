---
artifact_type: plan
schema_version: 1
created_at: 2026-08-05
source_sha: 342cf6e197659e02b9000d7525583eb32c60319d
related_plan: .renmark/rethink/governed-orchestration-assurance/roadmap.md#release-11
generator: sonnet
stale_after: 2026-09-05
dependency_refs:
  - .renmark/rethink/governed-orchestration-assurance/roadmap.md
  - .renmark/memory/orchestration-baseline.md
  - renmark/dispatch.py
  - renmark/usage.py
  - renmark/ledger.py
  - renmark/recurrence.py
---

# Plan: Release 11 — Routing-overlap spike (#18) + policy-aware dispatch scheduling

Release 11 of the `governed-orchestration-assurance` program closes AC-9
(Req 9, "partial" status) in two parts. Part A is a bounded, no-code-change
spike confirming whether `renmark/codex_routing.py` and
`renmark/global_routing.py` duplicate logic. Part B extends the wave
scheduler with risk-tier, quota/provider-availability, and rework-budget
aware signals.

**Live-path scoping (confirmed this session, re-derived fresh — do not
assume the Release 6 finding still applies verbatim).** `plugin/skills/
orchestrate/SKILL.md` Step 3 calls `dispatch.group_tasks_by_wave(tasks)`
then, for host-agent (`needs_agent`) tasks, `dispatch.
build_host_dispatch_plan_with_scope(wave, host=...)` directly — it never
calls `dispatch.dispatch_wave()`. Unlike Release 6's F1 finding,
`dispatch_wave()` is **not** dead code here: it has real live callers in
`renmark/cli/_wave_loop.py:472` and `renmark/cli/_engine.py:735`, which
back the `renmark-execute` CLI/subprocess loop (used for `codex`-executor
tasks and CLI-driven runs). So there are two live scheduling paths that
diverge below `group_tasks_by_wave`: the Claude Code host-agent Agent-tool
path (skips `dispatch_wave` entirely) and the CLI/codex subprocess path
(goes through `dispatch_wave`, which already accepts a `max_workers` knob).
`group_tasks_by_wave` is the one function **both** paths call. This release
therefore adds policy-aware batching to `group_tasks_by_wave` (the true
shared, universally-live entry point) and lets `dispatch_wave`'s existing
`max_workers` parameter consume the same `max_parallelism` signal on the
CLI path — it does not gate the new signals behind `dispatch_wave` alone.

**Routing-overlap answer (confirmed this session by reading both files in
full).** `renmark/codex_routing.py` (`route_for_task`, `build_native_dispatch`)
resolves a per-task Codex model/reasoning-effort pair from task complexity/
role/kind — pure task-level dispatch routing. `renmark/global_routing.py`
(`install_global_rule`, `detect_global_rule`) installs/repairs the
`renmark-routing` marker block inside the user's GLOBAL per-host
`~/.claude/CLAUDE.md` / `~/.codex/AGENTS.md` file — an onboarding/bootstrap
concern (teaching a bare host to default plain-English asks to renmark
pipelines before a project adopts renmark). The two modules share no state,
no functions, and no conceptual boundary dispute: one is per-task model
routing, the other is global-instruction-file installation. Task 1 below
still runs the spike for real (per the roadmap's own migration step (a)) and
records this as its independently-confirmed finding rather than skipping the
read.

**Explicit non-goals (state per the dispatch instructions):**
(a) This release does **not** invent new provider-quota polling. The quota/
provider-availability signal is `renmark.usage.build_usage_view(repo,
now=...)`'s existing bounded local-limit view (`percent`, `limit_exceeded`,
`recent_limit_events` — all derived from local ledger files, never a live
provider API call) — reused as-is, not extended.
(b) A wave with **no** new scheduling signals present (no `max_parallelism`,
no `quota_view`, no `rework_state`/`risk_resolver` callables passed) MUST
schedule byte-identically to pre-Release-11 `group_tasks_by_wave`/
`dispatch_wave` behavior — every new parameter defaults to `None` and is a
strict no-op when absent. No existing caller (`renmark/cli/_engine.py:364`,
`renmark/cli/_wave_loop.py:91`/`472`, `plugin/skills/orchestrate/SKILL.md`
Step 3, `tests/test_cross_host_dispatch_e2e.py`) changes behavior without
opting in.
(c) REQ-30 compliance evidence is a hard requirement of this release, not
optional — Task 4 below is the named before/after overhead measurement task,
reusing `.renmark/memory/orchestration-baseline.md`'s existing scenario-
capture pattern (Releases 1 and 7) and Release 7's budget-methodology
amendment: actual-vs-pin comparisons are restricted to non-codex executors,
or recorded `unknown` for codex — no fabricated aggregate percentage.

`ledger.classify_risk_tier(work_order)` is importable from `dispatch.py`
without a new cycle — `dispatch.py` already does `from . import fast_path,
ledger` (wired since Release 3's `work_order_for_task`), confirmed this
session by reading `dispatch.py`'s import block. No rework-cap module
named `rework_cap`/`max_rework` exists anywhere in `renmark/` (grepped this
session, zero hits) — the closest real mechanism is
`renmark.recurrence.pre_attempt`'s `occurrence_count`/`retry_blocked`
threshold gate, which today runs only from `orchestrate/SKILL.md`'s Step
3a-ter pre-dispatch prose, never from inside `group_tasks_by_wave` itself.
Task 2 below reuses that existing `recurrence` state as a read-only input
signal to scheduling (never a second retry-blocking mechanism, and never
altering `recurrence.pre_attempt`'s own authority to block a third attempt).

---

### Task 1: Routing-overlap spike finding doc

- **mode:** A
- **target:** .renmark/rethink/governed-orchestration-assurance/release-11-routing-overlap-spike.md
- **complexity:** medium
- **executor:** sonnet
- **role:** researcher
- **parallel_group:** 1
- **est_tokens:** 900
- **est_cost_usd:** 0.0327
- **verifier:** test -f .renmark/rethink/governed-orchestration-assurance/release-11-routing-overlap-spike.md
- **serves:** AC-9 (spike, #18)
- **spec:**
  Bounded, read-and-diff spike — no code change. Read `renmark/codex_routing.py`
  and `renmark/global_routing.py` in full. Determine independently whether
  they duplicate logic. Write a one-page finding doc (frontmatter:
  `artifact_type: research`, `schema_version: 1`, `created_at`, `source_sha`,
  `related_plan: .renmark/rethink/governed-orchestration-assurance/roadmap.md#release-11`,
  `generator: sonnet`) covering: (1) what each module actually does — name
  its public functions and what problem each solves; (2) verdict: "no
  overlap, boundary is X" or "overlap found at Y, recommend merging into Z"
  — if merge is recommended, state explicitly that it is a new, separately
  scoped follow-up item and is NOT decided or implemented in this spike;
  (3) one paragraph on why the two modules' names are easy to conflate
  (both contain "routing") despite operating in different domains, so a
  future reader doesn't re-raise this question without reading the finding.
  Do not modify `codex_routing.py`, `global_routing.py`, or any other source
  file — this task's only output is the finding doc.

### Task 2: Policy-aware wave scheduling in dispatch.py

- **mode:** B
- **target:** renmark/dispatch.py
- **complexity:** hard
- **executor:** opus
- **role:** code-implementer
- **parallel_group:** 1
- **est_tokens:** 3500
- **est_cost_usd:** 0.2025
- **verifier:** python3 -m py_compile renmark/dispatch.py && python3 -m pytest tests/test_dispatch.py tests/test_cross_host_dispatch_e2e.py -q 2>&1 | tail -3
- **serves:** AC-9 (Req 9)
- **spec:**
  Extend `group_tasks_by_wave` (the shared, universally-live scheduling
  entry point — both the Claude Code host-agent path and the CLI/codex
  `dispatch_wave` path call it) with additive, keyword-only, default-`None`
  parameters. Every parameter must be a strict no-op when omitted — a call
  with no new arguments must return the exact same `list[list[Task]]` as
  today, byte-for-byte, for every existing test in `tests/test_dispatch.py`
  and `tests/test_cross_host_dispatch_e2e.py`.

  New signature shape:
  ```python
  def group_tasks_by_wave(
      tasks: list[Task],
      *,
      max_parallelism: int | None = None,
      quota_view: dict[str, Any] | None = None,
      rework_lookup: Callable[[Task], Any] | None = None,
      risk_resolver: Callable[[Task], str | None] | None = None,
  ) -> list[list[Task]]:
  ```

  Behavior when a parameter is present:
  - `max_parallelism`: when a grouped wave has more members than
    `max_parallelism`, split it into consecutive sub-waves (stable order,
    same relative task ordering) of at most `max_parallelism` tasks each,
    preserving the original `parallel_group` id as the sub-wave's
    `group_id` (do not renumber `Task.parallel_group` itself — only the
    returned list-of-lists shape changes). `max_parallelism <= 0` is
    treated as "no limit" (defensive, never raises).
  - `quota_view`: the exact dict shape returned by
    `renmark.usage.build_usage_view(repo, now=...)` (do NOT call
    `build_usage_view` from inside `dispatch.py` — the caller passes the
    already-built view in; `dispatch.py` gains no new import of `usage.py`
    beyond reading this dict's existing keys: `percent[provider]
    [rolling_5h_tokens|weekly_tokens]`, `limit_exceeded`). When
    `quota_view.get("limit_exceeded")` is true for a provider a wave's
    tasks route to, treat that provider's tasks as an additional
    `max_parallelism`-style cap of 1 for that provider within the wave
    (throttle, never drop a task) — this reuses `usage.py`'s existing
    bounded local-limit view; do not add any new provider-polling code.
  - `rework_lookup`: an injected callable (test-friendly, mirrors
    `dispatch_wave`'s existing `run_task` injection pattern) mapping a
    `Task` to whatever rework-count value the caller already tracks
    (recurrence occurrence data, or `None`). When it returns a value the
    caller's own convention treats as "at or over budget," annotate that
    task (e.g. a `note`/log-only signal on the returned structure — do NOT
    silently reorder or drop it; scheduling awareness only, never a second
    retry-blocking authority — `recurrence.pre_attempt` remains the sole
    blocking gate).
  - `risk_resolver`: an injected callable mapping a `Task` to a risk-tier
    string (a thin adapter a caller can wire to
    `ledger.classify_risk_tier(work_order)` when a `WorkOrder` is available
    for that task; `dispatch.py` does not force-construct a `WorkOrder` just
    to get a tier — when the caller has none, it passes `risk_resolver=None`
    or a resolver that returns `None`, and scheduling proceeds exactly as
    without the signal). When present, use it only to order same-wave tasks
    (higher risk first) — never to move a task across wave boundaries or
    change `validate_wave`'s disjoint-target requirement.

  Also thread `max_parallelism` through to `dispatch_wave`'s existing
  `max_workers: int | None = None` parameter path so the CLI/codex loop
  (`renmark/cli/_wave_loop.py`, `renmark/cli/_engine.py`) gets the same cap
  for concurrent non-Claude execution when a caller opts in — do not change
  `dispatch_wave`'s existing default (`max_workers=None`) behavior.

  Do not touch `validate_wave`, `dispatch_wave`'s Claude-task /
  `scoped_dispatches` handling, or `build_host_dispatch_plan_with_scope` —
  this task is additive scheduling logic only. Add module docstring notes
  explaining the two live scheduling paths (host-agent vs CLI/codex) so a
  future reader does not reintroduce the Release 6/11 confusion about which
  function is live.

### Task 3: Scheduling regression + signal-consumption tests

- **mode:** A
- **target:** tests/test_release11_dispatch_scheduling.py
- **complexity:** medium
- **executor:** codex
- **role:** test-writer
- **parallel_group:** 2
- **est_tokens:** 1500
- **est_cost_usd:** 0.045
- **verifier:** python3 -m pytest tests/test_release11_dispatch_scheduling.py -q 2>&1 | tail -3
- **serves:** AC-9 (Req 9)
- **spec:**
  New test file covering Task 2's `group_tasks_by_wave` extension in
  `renmark/dispatch.py`. Cover: (1) **backward-compatibility regression
  guard** — a wave with no new signals passed schedules byte-identical to
  calling `group_tasks_by_wave(tasks)` with the old (pre-Release-11)
  positional-only signature, asserted against at least 3 of the existing
  fixture task lists already used in `tests/test_dispatch.py`
  (`test_group_tasks_by_wave_default_serial`,
  `test_group_tasks_by_wave_groups_shared`) — import and reuse those
  fixtures/helpers rather than duplicating task-construction boilerplate;
  (2) `max_parallelism` configurability — a wave of 5 same-group tasks with
  `max_parallelism=2` yields 3 sub-waves of sizes [2, 2, 1] in stable order;
  `max_parallelism=0` and `max_parallelism=None` are both no-ops; (3) quota
  signal consumption — build a stub `quota_view` dict matching
  `usage.build_usage_view`'s real shape (do NOT call `build_usage_view`
  itself or hit real `.renmark/state` — construct the dict literal inline)
  with `limit_exceeded=True` for one provider and confirm that provider's
  tasks are capped to 1-at-a-time within the wave while an unaffected
  provider's tasks are unaffected; (4) `rework_lookup` — a stub callable
  returning an over-budget marker for one task confirms that task is
  annotated (per Task 2's chosen shape) without being dropped, reordered
  across waves, or blocking dispatch (recurrence's own blocking behavior is
  out of scope for this file); (5) `risk_resolver` — present orders a
  high-risk task first within its wave; absent (`None`, the default)
  changes nothing versus test (1)'s baseline. Do not stub or mock
  `renmark.recurrence` or `renmark.usage` internals — only construct plain
  dicts/callables as Task 2's function signature expects.

### Task 4: REQ-30 overhead measurement (before/after)

- **mode:** A
- **target:** .renmark/rethink/governed-orchestration-assurance/release-11-overhead-measurement.md
- **complexity:** medium
- **executor:** sonnet
- **role:** audit-reader
- **parallel_group:** 2
- **est_tokens:** 800
- **est_cost_usd:** 0.0324
- **verifier:** test -f .renmark/rethink/governed-orchestration-assurance/release-11-overhead-measurement.md
- **serves:** REQ-30 (compatibility guarantee #8)
- **spec:**
  Reuse `.renmark/memory/orchestration-baseline.md`'s existing scenario-
  capture pattern (the same method Releases 1 and 7 used) to record a
  before/after overhead measurement for this release's shipped
  `group_tasks_by_wave` extension (Task 2, already landed when this task
  runs — read the actual diff via `git show` against this release's
  commit(s), do not describe a hypothetical). Apply Release 7's budget
  methodology exactly: restrict actual-vs-pin token/wall-clock comparisons
  to non-codex executors; record codex-path overhead as `unknown` rather
  than fabricating a number if no real codex-path measurement exists.
  Measure at minimum: (a) a synthetic wave with no new signals passed
  (confirms the "byte-identical, zero overhead" no-signal-present claim
  from this plan's intent paragraph — cite the actual test from Task 3
  that proves it); (b) a synthetic wave exercising `max_parallelism` +
  `quota_view` together, measuring added Python-level call overhead only
  (no LLM call is on this code path, so token overhead is necessarily
  `0`/`n/a` — state that honestly rather than inventing a token delta).
  Be explicit in the doc about what is and is not measurable in one
  session (per this plan's honesty standard, matching Release 7's own).
  Frontmatter: `artifact_type: research`, `schema_version: 1`,
  `created_at`, `source_sha`, `related_plan:
  .renmark/memory/orchestration-baseline.md`, `generator: sonnet`. Close
  with one line stating whether this release stays under Release 7's
  measured overhead budget (cite the specific number/threshold from
  `.renmark/memory/orchestration-baseline.md` or `PRD.md` REQ-30).

---

## Cost preview

| Task | Executor | Est. tokens (incl. overhead) | Est. cost |
|---|---|---|---|
| 1. Routing-overlap spike doc | sonnet | 10,900 | $0.0327 |
| 2. dispatch.py scheduling extension | opus | 13,500 | $0.2025 |
| 3. Scheduling tests | codex | 1,500 | $0.0450 |
| 4. REQ-30 overhead measurement | sonnet | 10,800 | $0.0324 |

Tasks: 4 (2 parallel groups). Total tokens (incl. ~10k Agent overhead where
applicable): **~36,700**. **Total cost: ~$0.3126**.

Executors: sonnet×2, opus×1, codex×1. No `haiku`, no `fable` (no escalation
signal present — this is a scoped extension, not frontier architecture
work).

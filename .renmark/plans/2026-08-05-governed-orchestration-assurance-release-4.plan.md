# Plan: Release 4 — Task tracker bound to `WorkOrder.order_id` + selector bypass guard

**Context.** `governed-orchestration-assurance` Release 4 (see
`.renmark/rethink/governed-orchestration-assurance/roadmap.md`). Release 3
shipped `ledger.WorkOrder`/`ledger.work_order_for_task` and wired
`dispatch.build_subagent_input` to call `work_order_for_task` once per
Claude-executor dispatch. This release does two independent, additive
things: (1) `task_tracking.create_or_reuse_task` gains an optional
`order_id` string it persists on the `TaskRecord`, threaded from the
existing local `order_id = f"{run_id}-{task.index}"` value already computed
in `renmark/cli/_wave_loop.py`'s `_runner` (the same value already fed to
the real ledger `WorkOrder`/`WorkResult` emission calls
`_emit_work_order`/`_emit_work_result`) — this avoids forcing
`task_tracking.py` to import `renmark.ledger` while still binding the task
record to a real ledger order id; (2) `renmark/interaction.py` gains an
opt-in `enforce_native` guard on `build_selector` that raises instead of
silently returning a numbered-fallback payload when the caller suppressed
an actually-available native picker (`tool_available=False` while the raw,
un-overridden `hosts.capabilities_for` result for that host still reports a
`selector_tool`) — the regression class behind the real 2026-06-14
"Hand-off picker not re-rendered on continuation turns" incident
(`.renmark/memory/bugs.md`, `CHANGELOG.md` `[2026-06-14] — fix(handoff):
re-render the picker on hand-off continuation turns`), where a skill
answered a continuation turn in prose instead of re-rendering the
clickable picker.

**Compatibility guarantees respected (verified before writing this plan):**
- **#6** — `complete_worker_task`'s no-self-approval gate
  (`check_dispatch_independence` call inside `task_tracking.py`) is
  untouched. Only task *creation* (`create_or_reuse_task`) binds to
  `order_id`; no task changes touch the independence-check call.
- **#7** — Neither change adds anything to `SubagentInput` or dispatch
  prompt construction. `dispatch.build_subagent_input` and
  `SubagentInput`'s field set are not touched by this plan; `order_id`
  threading stays entirely inside `task_tracking.py`/`_wave_loop.py`'s
  native-task-tracking layer (`.renmark/state/tasks.json`), a separate
  concern from the dispatch packet.

**Reuse check:** `reuse: none` — no existing skill/spec/plan/feature
implements order_id-bound task records or a native-selector enforcement
mode; this is new plumbing for Release 4.

### Task 1: task_tracking.py order_id field
- **mode:** B
- **target:** renmark/task_tracking.py
- **complexity:** medium
- **executor:** sonnet
- **role:** code-implementer
- **parallel_group:** 1
- **est_tokens:** 700
- **est_cost_usd:** 0.0321
- **verifier:** python3 -m pytest tests/test_task_tracking.py -q 2>&1 | tail -5
- **serves:** AC-3
- **spec:**
  Add an `order_id: str = ""` field to the `TaskRecord` dataclass (place it
  near `dispatch_identity`, e.g. right after it — both are dispatch-
  correlation fields). Add a keyword-only `order_id: str = ""` parameter to
  `create_or_reuse_task(...)` and pass it through to the `TaskRecord(...)`
  construction for the newly-created record. Preserve the function's
  existing idempotent-by-design resume-reuse contract exactly: when
  `existing is not None and existing.status != "deleted"`, the function
  still returns `existing` unchanged (a later call with a different
  `order_id` must NOT overwrite an already-created record's `order_id` —
  same rule that already applies to every other field on resume-reuse).
  Update the class/function docstrings to mention `order_id` in one
  sentence each. Do not touch `complete_worker_task`, `_require_task`, or
  any function that calls `check_dispatch_independence` — the no-self-
  approval gate is out of scope for this task (compatibility guarantee
  #6). Do not add any import of `renmark.ledger` to this module — the
  caller (see Task 2) already has the order_id string in hand and passes
  it in directly. `read_tasks`/`write_tasks` need no changes — they already
  round-trip `TaskRecord` generically via `asdict`/`**fields`.

### Task 2: thread order_id through the real dispatch call site
- **mode:** B
- **target:** renmark/cli/_wave_loop.py
- **complexity:** medium
- **executor:** sonnet
- **role:** code-implementer
- **parallel_group:** 2
- **est_tokens:** 500
- **est_cost_usd:** 0.0315
- **verifier:** python3 -m pytest tests/test_task_tracking_engine_wiring.py -q 2>&1 | tail -5
- **serves:** AC-3
- **spec:**
  `_track_worker_dispatch(...)` (creates the per-dispatch native task via
  `_task_tracking.create_or_reuse_task`) currently does not receive the
  task's `order_id`, even though the caller (`_runner`, inside
  `execute_plan`'s wave loop) already computes
  `order_id = f"{run_id}-{task.index}"` at the top of the function and
  passes that same value to `_emit_work_order(_repo, task, order_id)` and
  later `_emit_work_result(..., order_id=order_id, ...)` — the real ledger
  `WorkOrder`/`WorkResult` events. Add an `order_id: str` keyword-only
  parameter to `_track_worker_dispatch` and pass it straight through to its
  `_task_tracking.create_or_reuse_task(...)` call as `order_id=order_id`
  (this requires Task 1's new `create_or_reuse_task` parameter to already
  exist). At the call site inside `_runner` (the
  `_track_worker_dispatch(_repo, task, worker_task_id=..., parent_task_id=...,
  dispatch_identity=...)` call), add `order_id=order_id` using the
  already-computed local variable — no new order_id scheme, no change to
  how `order_id` itself is generated. Do not change `_create_parent_task`
  (the one milestone-level parent task has no corresponding per-dispatch
  WorkOrder, so it keeps its default empty `order_id`). Do not touch
  `_inspect_and_track` or any `check_dispatch_independence` call
  (compatibility guarantee #6). Do not add or change any field on
  `SubagentInput`/`build_subagent_input` (compatibility guarantee #7) —
  this task only touches the native-task-tracking call, not the dispatch
  packet.

### Task 3: interaction.py enforced selector mode
- **mode:** B
- **target:** renmark/interaction.py
- **complexity:** medium
- **executor:** sonnet
- **role:** code-implementer
- **parallel_group:** 1
- **est_tokens:** 900
- **est_cost_usd:** 0.0327
- **verifier:** python3 -m pytest tests/test_interaction.py -q 2>&1 | tail -5
- **serves:** AC-4
- **spec:**
  Add a new `class SelectorBypassError(ChoiceError):` near the existing
  `ChoiceError` definition. Add a keyword-only `enforce_native: bool = False`
  parameter to `build_selector(...)`. When `enforce_native` is `True`:
  after resolving `selected_host = resolve_host(host)` and the effective
  `caps = capabilities_for(selected_host, render_surface=render_surface,
  selector_available=tool_available)` (unchanged), also resolve the RAW,
  un-overridden capabilities for the same host —
  `raw_caps = capabilities_for(selected_host, render_surface=render_surface)`
  (no `selector_available` override). If `raw_caps.selector_tool is not
  None` (a native picker genuinely exists for this host/surface) but the
  effective `caps.selector_tool is None` specifically because the caller
  passed `tool_available=False` (i.e. the caller itself suppressed an
  available picker — NOT because the host lacks one), raise
  `SelectorBypassError` instead of returning the `_fallback_payload(...)`
  that the current code would otherwise return for
  `reason="selector_unavailable"`. Do NOT raise for the other existing
  fallback reasons (`single_choice_requires_fallback`,
  `selector_requires_multiple_options`, `selector_capacity_unavailable`) —
  those are legitimate fallbacks even when a native picker exists (single
  choice, host option-count limits) and must keep returning their normal
  fallback payload unchanged even with `enforce_native=True`. When
  `enforce_native` is omitted (default `False`), `build_selector`'s
  behavior must be byte-for-byte unchanged from today — this is the
  rollback path the roadmap names ("interaction.py's existing advisory
  mode remains available as a fallback flag if the enforced mode regresses
  a host"). Add `SelectorBypassError` to the module's public names used by
  callers (no `__all__` currently exists in this file — do not add one
  unless one already exists; just make sure the class is importable, which
  it is by default). One-sentence docstring addition on `build_selector`
  naming the motivating regression: a caller/skill deciding not to use an
  available native picker on a continuation turn (the 2026-06-14 "Hand-off
  picker not re-rendered on continuation turns" bug class). Do not touch
  `continue_selector`, `resolve_selection`, `with_recommendation`, or any
  dispatch/`SubagentInput` code (compatibility guarantee #7 — this module
  has no dispatch-packet involvement to begin with).

### Task 4: task_tracking order_id tests
- **mode:** B
- **target:** tests/test_task_tracking.py
- **complexity:** medium
- **executor:** codex
- **role:** test-writer
- **parallel_group:** 2
- **est_tokens:** 400
- **est_cost_usd:** 0.008
- **verifier:** python3 -m pytest tests/test_task_tracking.py -q 2>&1 | tail -5
- **serves:** AC-3
- **spec:**
  Extend this existing test file (do not create a new file). Add: (1) a
  test that `create_or_reuse_task(..., order_id="run-1-3")` persists
  `order_id="run-1-3"` on the returned `TaskRecord` and on the record
  re-read via `read_tasks(...)`; (2) a test proving resume-reuse
  idempotency for `order_id` specifically — call `create_or_reuse_task`
  once with `order_id="run-1-3"`, then call it again for the SAME
  `task_id` with a different `order_id="run-2-3"` (simulating a resumed
  run with a new `run_id`), and assert the returned/persisted record still
  has `order_id="run-1-3"` (the original), matching this module's existing
  "second call for the same id must be a true no-op" pattern already
  exercised by `test_create_or_reuse_task_is_idempotent_resume_reuse` and
  `tests/test_task_tracking_engine_wiring.py`'s reuse test. Depends on
  Task 1's `order_id` parameter existing on `create_or_reuse_task`.

### Task 5: dispatch-engine order_id wiring test
- **mode:** B
- **target:** tests/test_task_tracking_engine_wiring.py
- **complexity:** medium
- **executor:** codex
- **role:** test-writer
- **parallel_group:** 3
- **est_tokens:** 500
- **est_cost_usd:** 0.01
- **verifier:** python3 -m pytest tests/test_task_tracking_engine_wiring.py -q 2>&1 | tail -5
- **serves:** AC-3
- **spec:**
  Extend `test_execute_plan_creates_worker_and_verification_tasks` (or add
  a sibling test in this file — do not create a new file) to assert that
  after a real `_engine.execute_plan(...)` run, the worker `TaskRecord` in
  `.renmark/state/tasks.json` carries a non-empty `order_id` matching the
  same scheme `_wave_loop.py` already uses for the real ledger
  `WorkOrder`/`WorkResult` events (`f"{run_id}-{task.index}"` — read the
  actual `run_id`/task index the test's existing plan/task setup produces,
  do not hardcode an unrelated string). This is the end-to-end proof (real
  dispatch engine, no live LLM call — `_execute_task` stays monkeypatched
  per this file's existing pattern) that Task 2's wiring actually lands an
  order_id on the real task record, not just that the unit-level
  `create_or_reuse_task` parameter works in isolation. Depends on Task 1
  (the `order_id` parameter) and Task 2 (the `_wave_loop.py` call-site
  wiring) both landing first.

### Task 6: interaction.py enforced-mode regression test
- **mode:** B
- **target:** tests/test_interaction.py
- **complexity:** medium
- **executor:** codex
- **role:** test-writer
- **parallel_group:** 2
- **est_tokens:** 500
- **est_cost_usd:** 0.01
- **verifier:** python3 -m pytest tests/test_interaction.py -q 2>&1 | tail -5
- **serves:** AC-4
- **spec:**
  Extend this existing test file (do not create a new file). Add a
  regression test named/documented after the real 2026-06-14 "Hand-off
  picker not re-rendered on continuation turns" incident
  (`.renmark/memory/bugs.md`): call `build_selector(question, choices,
  host="claude", tool_available=False, enforce_native=True)` — Claude Code
  genuinely has a native `AskUserQuestion` selector per
  `hosts.capabilities_for`, so `tool_available=False` here is exactly the
  "skill suppressed an available picker" shape that produced the real bug
  (a continuation-turn reply dropping to a prose numbered list instead of
  re-rendering the picker) — and assert it raises
  `renmark.interaction.SelectorBypassError` instead of returning a
  fallback payload. Add a second test proving `enforce_native=False`
  (the default, i.e. omitted) with the same `tool_available=False`
  arguments returns the normal fallback payload unchanged (no regression
  to existing advisory-mode behavior/tests already in this file, e.g.
  `test_missing_codex_selector_is_fallback_not_headless`). Add a third
  test proving `enforce_native=True` does NOT raise for a legitimate
  fallback reason unrelated to caller suppression — e.g. a single-choice
  `ChoiceSet` (`single_choice_requires_fallback`) still returns its normal
  fallback payload even with `enforce_native=True`. Depends on Task 3's
  `enforce_native` parameter and `SelectorBypassError` existing.

## Cost preview

| Task | Executor | Tokens (incl. overhead) | Cost |
|---|---|---|---|
| 1. task_tracking.py order_id field | sonnet | 10,700 | $0.0321 |
| 2. _wave_loop.py order_id threading | sonnet | 10,500 | $0.0315 |
| 3. interaction.py enforced mode | sonnet | 10,900 | $0.0327 |
| 4. test_task_tracking.py | codex | 400 | $0.008 |
| 5. test_task_tracking_engine_wiring.py | codex | 500 | $0.01 |
| 6. test_interaction.py | codex | 500 | $0.01 |

Tasks: 6 (3 parallel groups: group 1 = tasks 1,3; group 2 = tasks 2,4,6;
group 3 = task 5). Executors: sonnet×3, codex×3. No haiku/opus/fable.

**Total tokens (incl. overhead): ~33,500**
**Total cost: ~$0.1243**

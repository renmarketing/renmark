# Release 14 — Guardrail metrics (governed-orchestration-assurance)

*(Revised 2026-08-05 — Owner edit before dispatch: AC-13 cannot close with
2/5 metrics unmeasured; the 3 measured metrics must share one aligned
measurement window instead of mixing differently-scoped denominators; and
this release must carry its own REQ-30 overhead checklist item, per the
Release 7 PRD amendment's requirement that Releases 8-16 each demonstrate
staying under the measured overhead budget before shipping.)*

Extends `analytics.py`'s aggregators with the proposal's named guardrail
fields. **AC-13 (Req 13) stays `partial` after this release** — it does
NOT close here. Investigation before writing this plan found that 3 of the
5 named metrics have NO existing durable data source anywhere in the
codebase:

- **scope-violation rate**: `dispatch.py::enforce_host_agent_dispatch_scope`/
  `enforce_wave_dispatch_scopes` raise `WaveScopeViolationError` but never
  record a durable event — Task 1 (already committed, see below) closes
  this gap with one additive `record_event(..., kind="scope_violation")`
  call per violation, before the raise (raise behavior unchanged).
- **false-pass/reopen rate**: `recurrence.py::observe_issue`'s `starts_fresh`
  branch already distinguishes a fingerprint-identical re-observation of a
  previously-`resolved` entry (a true reopen) from an unrelated fresh issue,
  but doesn't count it — Task 2 adds an additive `reopen_count` field +
  a **windowed** `reopen_rate()` helper.
- **Owner-interruptions-per-milestone** and **duplicate-artifact rate**: NO
  durable log of `AskUserQuestion` gate calls or re-dispatch/duplicate-
  artifact events exists anywhere. Per the roadmap's own instruction to
  "define and measure renmark's own baseline... rather than importing an
  external vendor statistic" — and per this program's established Release 1
  discipline against overclaiming — these two fields report as `null` with
  an explicit `_note` explaining the gap, NOT a fabricated zero. Closing
  them for real requires wiring every skill's gate call site, which is out
  of this release's bounded scope; logged as a follow-up in `bugs.md`. This
  is precisely why AC-13 does not close this release: only 3 of 5 named
  metrics get a real measured value.

**Measurement-window alignment (the Owner's core correctness concern).**
Without a shared window, `scope_violation_rate` would divide a numerator
that only starts accumulating from Task 1's ship-forward timestamp by an
all-time `tasks.total` denominator that includes years of pre-feature
history — silently understating the rate rather than reporting "not yet
enough data." Task 3 therefore computes ALL THREE measured rates
(`scope_violation_rate`, `unknown_usage_rate`, `false_pass_reopen_rate`)
over the SAME explicit, configurable trailing window (default 30 days,
`window_days` parameter), filtering raw rows/entries by timestamp before
counting — never mixing an all-time denominator against a windowed
numerator. The returned dict is self-documenting: it carries
`window_days`, `window_start`, and `window_end` alongside the three rates,
so any consumer can see exactly what period a rate covers rather than
inferring it.

**REQ-30 overhead checklist (added per Owner instruction — a verify-time
checklist item, not new code).** Per the Release 7 PRD amendment and
`.renmark/memory/orchestration-baseline.md`'s recommended budget line, this
release's own `/renmark:verify` pass must record: (a) actual token spend
for the 3 non-codex (sonnet) dispatches in this plan against the
`AGENT_OVERHEAD_TOKENS = 10,000` pin, restricting the "actual vs. pin"
claim to those non-codex dispatches; (b) the 3 codex dispatches recorded
explicitly as an `unknown`-cost line item, never assumed compliant. This is
NOT a new aggregator field in `analytics.py` — it is a one-time checklist
line in this release's verification artifact, matching the budget's own
"checklist item on this program's own verification convention, not new
code" framing.

`unknown_usage_rate` and `scope_violation_rate` both already have (or gain
in Task 1) real underlying counts — `_agg_tasks`'s existing
`unmeasured_task_count`/`total` needs no new data source, just windowed
arithmetic in `aggregate()`.

**Compatibility guarantee:** `pytest -q` count only grows; every existing
`summary.json`/`build_health_report`/`render_health_md` key is unaffected —
all new fields are additive under a new `summary["guardrail_metrics"]` key.

### Task 1: scope-check event recording (all checks, not just violations) — DONE, revised in-flight

*(This task already executed once under an earlier spec that recorded
`kind="scope_violation"` only on failures. The Owner correctly flagged
that as biased: a rate needs a denominator of ALL checks performed, not
just tasks dispatched — most dispatches never go through the fast-path
scope check at all, so "tasks total" silently overcounts the denominator.
The implementation was revised in-flight — directly, not re-dispatched,
given the surgical size — to the spec below, and the amended version is
what's on disk and passing `tests/test_dispatch.py` (26 passed). This
block is kept for plan-history accuracy; no further action needed on
Task 1.)*

- **mode:** B
- **target:** renmark/dispatch.py
- **complexity:** medium
- **executor:** sonnet
- **role:** code-implementer
- **parallel_group:** 1
- **est_tokens:** 900
- **est_cost_usd:** 0.0327
- **verifier:** python3 -m pytest -q tests/test_dispatch.py 2>&1 | tail -5
- **serves:** AC-13 (Req 13)
- **spec:**
  In `enforce_host_agent_dispatch_scope` and `enforce_wave_dispatch_scopes`
  (both in this file), record ONE `analytics.record_event(..., kind=
  "scope_check", task_index=..., passed=<bool>)` call for EVERY scope
  check actually performed — both passes and failures, not only
  violations — so a rate can later be computed as (failed checks) /
  (all checks), never (failed checks) / (unrelated denominator like total
  tasks dispatched). In `enforce_host_agent_dispatch_scope`, every entry
  in `host_plan.scoped_dispatches` is already opted-in (only populated
  when `agent_dispatch.scope` was set), so record one event per loop
  iteration. In `enforce_wave_dispatch_scopes`, inline the same
  `verify_agent_dispatch_scope` call `verify_wave_dispatch_scopes` uses
  internally (both are public functions in this file) so the per-dispatch
  verdict is visible here; skip recording when the verdict is `None`
  (not opted in — nothing was actually checked, matching R-0.1: `None`
  means "not opted in," never "verified clean"). In both functions,
  wrap only the `record_event` call in `try/except Exception: pass` —
  never the violation-collection logic or the final
  `raise WaveScopeViolationError(tuple(violations))`, which must fire
  unchanged in message/payload from before this change. Import
  `analytics` lazily inside each function.

### Task 2: recurrence reopen tracking

- **mode:** B
- **target:** renmark/recurrence.py
- **complexity:** medium
- **executor:** sonnet
- **role:** code-implementer
- **parallel_group:** 1
- **est_tokens:** 1300
- **est_cost_usd:** 0.0339
- **verifier:** python3 -m pytest -q tests/test_recurrence.py 2>&1 | tail -5
- **serves:** AC-13 (Req 13)
- **spec:**
  A single `last_observed_at` field per entry cannot correctly window
  repeated reopen/resolve cycles — an entry resolved 60 days ago and
  reopened 5 days ago has only ONE `last_observed_at`, so filtering by it
  either drags the 60-day-old resolution into a 30-day window or drops the
  5-day-old reopen out of it. Fix: track EACH resolve/reopen as its own
  timestamped event, bounded lists, so the two can be windowed
  independently and paired apples-to-apples (this is the Owner's "timestamp
  each reopen" instruction).

  Add THREE keys to `_new_entry`'s returned dict (additive; old on-disk
  entries without them must keep working via `.get(..., [])`/`.get(..., 0)`
  everywhere read): `"reopen_count": 0` (fast all-time counter, unchanged
  from before), `"reopen_timestamps": []`, `"resolved_timestamps": []`.

  In `resolve_issue`, immediately after setting `entry["resolved_at"] =
  timestamp`, append that same timestamp to a carried-forward, bounded
  list: `entry["resolved_timestamps"] = (list(raw_entry.get(
  "resolved_timestamps", [])) + [timestamp])[-50:]` (cap at the last 50
  entries — bounded growth, matching this module's other capped-list
  conventions; grep this file for an existing `[-N:]`-style cap and match
  its N if one exists, otherwise use 50).

  In `observe_issue`'s `starts_fresh` branch, when `starts_fresh` is True
  specifically BECAUSE `previous is not None and bool(previous.get(
  "resolved")) and previous.get("fingerprint") == fingerprint` (a true
  reopen of a resolved issue — NOT a fresh, unrelated fingerprint change):
  set `entry["reopen_count"] = _positive_int(previous.get("reopen_count"),
  0) + 1` (unchanged from before), AND set `entry["reopen_timestamps"] =
  (list(previous.get("reopen_timestamps", [])) + [observed_at])[-50:]`
  (same 50-cap convention).

  Add one new read-only, never-raising function:

  ```python
  def reopen_rate(
      repo: str | os.PathLike[str], *, window_days: int = 30, now: str | None = None,
  ) -> dict[str, object]:
  ```

  returning `{"resolved_total": <int>, "reopened_total": <int>,
  "window_days": window_days, "window_start": <iso>, "window_end": <iso>}`.
  `now` defaults to the module's own timestamp helper (match however this
  file already gets "now" elsewhere; do not import `datetime.now()`
  directly if the module has its own convention). `window_start = now -
  window_days`. Compute by reading the existing state file via
  `_read_state`/`_state_paths`, then across ALL entries: `resolved_total`
  = count of individual timestamps in every entry's `resolved_timestamps`
  list that fall within `[window_start, now]` (parse with the module's
  existing timestamp parsing helper; an unparseable timestamp is EXCLUDED,
  not included by default); `reopened_total` = count of individual
  timestamps in every entry's `reopen_timestamps` list that fall within
  the same window. This counts EVENTS, not entries — an entry resolved
  twice and reopened twice within the window contributes 2 to each total.
  Degrade to `{"resolved_total": 0, "reopened_total": 0, "window_days":
  window_days, "window_start": <iso>, "window_end": <iso>}` on any
  missing/corrupt file — never raise. Do not change `pre_attempt`,
  `acknowledge_issue`, or any existing field's meaning.

### Task 3: analytics guardrail_metrics aggregation

- **mode:** B
- **target:** renmark/analytics.py
- **complexity:** medium
- **executor:** sonnet
- **role:** code-implementer
- **parallel_group:** 2
- **est_tokens:** 1700
- **est_cost_usd:** 0.0351
- **verifier:** python3 -m pytest -q tests/test_reports_analytics.py tests/test_analytics_ledger_guardrails.py 2>&1 | tail -5
- **serves:** AC-13 (Req 13)
- **spec:**
  Add `"scope_check_events": kind_c.get("scope_check", 0)` to
  `_agg_events`'s returned dict (matches its existing `kind_c.get(...)`
  pattern, all-time count, covers both passed/failed checks via Task 1's
  `passed` bool field; unchanged for backward-compat — the WINDOWED
  breakdown below lives only inside `guardrail_metrics`).

  Add a new function:

  ```python
  def _agg_guardrail_metrics(
      repo, *, task_rows: list[dict], event_rows: list[dict],
      now: str, window_days: int = 30,
  ) -> dict[str, object]:
  ```

  that, never raising (same try/except-degrade-to-defaults pattern as
  `_agg_ledger_guardrails`), computes ALL THREE measured rates over the
  SAME explicit trailing window (Owner fix: never a windowed numerator
  over an all-time denominator). `window_start = now - window_days` (use
  this module's existing timestamp helpers, not `datetime.now()`
  directly). Filter `task_rows`/`event_rows` to rows whose `ts` falls in
  `[window_start, now]` (unparseable/missing `ts` EXCLUDED, not defaulted
  in — same honesty rule as Task 2's `reopen_rate`). From the windowed
  sets, compute:
  - `scope_violation_rate`: `checks = [r for r in windowed event_rows if
    r.get("kind") == "scope_check"]` is the TRUE denominator (every check
    performed, pass or fail) — NOT `len(windowed task_rows)` (most
    dispatches never hit the fast-path scope check, so task-count would
    overcount the denominator; this is the Owner's "record all checks"
    fix). Rate = `(checks where `_as_bool(r.get("passed")) is False`) /
    max(1, len(checks))`, 4 decimals, `0.0` when `len(checks)` is 0.
  - `unknown_usage_rate`: `(windowed task_rows where not
    _as_bool(r.get("measured"))) / max(1, len(windowed task_rows))`, 4
    decimals, `0.0` if windowed task count is 0 (reuses `_as_bool` and
    `_agg_tasks`'s existing "measured" semantics, now windowed).
  - `false_pass_reopen_rate`: lazily `from renmark import recurrence`,
    call `recurrence.reopen_rate(repo, window_days=window_days, now=now)`
    (SAME `window_days`/`now` — all three rates share one window),
    `reopened_total / max(1, resolved_total)`, 4 decimals, `0.0` on
    exception or `resolved_total == 0`.
  - `owner_interruptions_per_milestone`: `None` + `"owner_interruptions_note":
    "no durable log of Owner gate (AskUserQuestion) interactions exists
    yet — out of this release's bounded scope, tracked as a follow-up
    (see .renmark/memory/bugs.md)"`.
  - `duplicate_artifact_rate`: `None` + `"duplicate_artifact_note": "no
    durable log of duplicate/re-dispatched artifact emission exists yet —
    out of this release's bounded scope, tracked as a follow-up (see
    .renmark/memory/bugs.md)"`.
  Include `"window_days": window_days, "window_start": <iso>,
  "window_end": now` in the returned dict alongside the five metric keys,
  so every consumer sees the exact period covered. Wire
  `_agg_guardrail_metrics(repo, task_rows=<raw rows already read for
  `_agg_tasks`>, event_rows=<raw rows already read for `_agg_events`>,
  now=now)` into `aggregate()` (reuse the SAME raw-row lists already read
  via `read_jsonl`, do not re-read) under a NEW top-level
  `summary["guardrail_metrics"]` key — do not rename/remove/restructure
  any existing `summary` key. Wire the same result into
  `build_health_report`'s dict under `"guardrail_metrics"` (same pattern
  as `"guardrails": summary.get("guardrails", {})`). In
  `render_health_md`, add one short line after the existing "Guardrails:
  N escalations..." line, e.g. `f"- Guardrail metrics: scope-violation
  {rate:.1%}, unknown-usage {rate:.1%}, reopen {rate:.1%}
  (Owner-interruptions and duplicate-artifact rate: not yet measured)"` —
  only when `guardrail_metrics` is present and non-empty, matching the
  existing `if guardrails:` guard style.

### Task 4: guardrail_metrics test coverage

- **mode:** A
- **target:** tests/test_analytics_guardrail_metrics.py
- **complexity:** medium
- **executor:** codex
- **role:** test-writer
- **parallel_group:** 3
- **est_tokens:** 1500
- **est_cost_usd:** 0.035
- **verifier:** python3 -m pytest -q tests/test_analytics_guardrail_metrics.py 2>&1 | tail -5
- **serves:** AC-13 (Req 13)
- **spec:**
  Write tests for `renmark.analytics._agg_guardrail_metrics` and its wiring
  into `aggregate()`/`build_health_report()`/`render_health_md()`. Cover:
  (1) with a `task_rows`/`event_rows` fixture where 4 `kind="scope_check"`
  events (2 `passed=True`, 2 `passed=False`) and 4 unrelated task rows all
  carry `ts` inside the default 30-day window, `scope_violation_rate ==
  0.5` — confirm the DENOMINATOR is `len(checks)` (4), NOT
  `len(task_rows)` (4 here coincidentally equal — also add a second
  sub-case with a different task_rows count than checks count, e.g. 4
  checks but 10 task rows, to prove the denominator tracks checks, not
  tasks); (2) with 4 windowed task rows where 1 has `measured` falsy,
  `unknown_usage_rate == 0.25`; (3) a `scope_check` row and a task row
  each with `ts` OUTSIDE the window (e.g. 40 days old) are excluded from
  both the numerator and denominator — confirm the rate differs from what
  it would be if the stale rows were counted; (4) with a repo where
  `renmark.recurrence.observe_issue` resolves an entry then observes an
  equivalent finding again within the window (using
  `renmark.recurrence.IssueObservation`/`resolve_issue`/`observe_issue`
  directly, matching the calling convention in `tests/test_recurrence.py`),
  `false_pass_reopen_rate` reflects the reopen — and add a case where the
  resolve happened OUTSIDE the window but the reopen is INSIDE it,
  confirming `reopen_rate`'s per-event timestamp windowing (not a single
  `last_observed_at`) is what's actually driving the result; (5) the returned dict
  carries `window_days`, `window_start`, `window_end` and they're
  consistent with the `window_days` argument passed in (default 30 when
  omitted); (6) `owner_interruptions_per_milestone` and
  `duplicate_artifact_rate` are both `None` with their `_note` keys
  present and non-empty; (7) on a repo with none of
  `events.jsonl`/task rows/recurrence state present, every rate degrades
  to `0.0` and nothing raises; (8) `aggregate()`'s returned dict has a
  `"guardrail_metrics"` key and every pre-existing key (`features`,
  `tasks`, `loops`, `events`, `usage`, `guardrails`) is unchanged in shape
  from before this release (compare against `tests/test_reports_analytics.py`'s
  existing fixtures/assertions — do not duplicate that file's setup,
  import and reuse its helpers if present).

### Task 5: scope-check event-recording test (pass AND fail)

- **mode:** B
- **target:** tests/test_dispatch.py
- **complexity:** medium
- **executor:** codex
- **role:** test-writer
- **parallel_group:** 3
- **est_tokens:** 1100
- **est_cost_usd:** 0.028
- **verifier:** python3 -m pytest -q tests/test_dispatch.py 2>&1 | tail -5
- **serves:** AC-13 (Req 13)
- **spec:**
  `renmark/dispatch.py`'s `enforce_host_agent_dispatch_scope` and
  `enforce_wave_dispatch_scopes` (this file already has fixtures for both
  functions' `WaveScopeViolationError` raise-path tests — find and reuse
  them, do not duplicate setup) now record one `analytics` event of
  `kind="scope_check"` with a `passed: bool` field for EVERY check
  performed — both passing and failing dispatches, not only violations.
  Add tests confirming: (1) a wave/plan with ONLY passing scoped
  dispatches (no violation, no raise) still records one `scope_check`
  event per dispatch with `passed=True` — read
  `renmark.analytics.read_jsonl` against `events.jsonl`, or monkeypatch
  `renmark.analytics.record_event` and assert call count matches
  dispatch count; (2) a wave/plan with a mix of passing and failing
  dispatches records BOTH — the right count of `passed=True` and
  `passed=False` events, matching which task indices actually failed;
  (3) in `enforce_wave_dispatch_scopes` specifically, a dispatch whose
  `agent_dispatch.scope is None` (not opted in — `verify_agent_dispatch_scope`
  returns `None`) records NO event at all (there was nothing to check);
  (4) `WaveScopeViolationError` still raises unchanged (same message,
  same `violations` tuple contents) when there's at least one failure —
  compare against this file's existing raise-path assertions; (5) when
  `record_event` itself raises (monkeypatch it to raise), the original
  `WaveScopeViolationError` (or the passing return, for the all-pass
  case) still completes unchanged — best-effort recording must never mask
  or replace the real outcome. Do not modify any existing test in this
  file — additive only.

### Task 6: recurrence reopen_count test coverage

- **mode:** B
- **target:** tests/test_recurrence.py
- **complexity:** medium
- **executor:** codex
- **role:** test-writer
- **parallel_group:** 3
- **est_tokens:** 1600
- **est_cost_usd:** 0.032
- **verifier:** python3 -m pytest -q tests/test_recurrence.py 2>&1 | tail -5
- **serves:** AC-13 (Req 13)
- **spec:**
  Add tests for Task 2's `reopen_count`/`reopen_timestamps`/
  `resolved_timestamps` fields and windowed `reopen_rate()` function.
  Cover: (1) a fresh `observe_issue` call creates an entry with
  `reopen_count == 0` and empty `reopen_timestamps`/`resolved_timestamps`;
  (2) `resolve_issue` appends a timestamp to `resolved_timestamps` (list
  grows by exactly 1, matches `resolved_at`); (3) `resolve_issue` then an
  equivalent `observe_issue` (same check/rule_id/target/title/
  summary_text, so the fingerprint matches) increments `reopen_count` to
  `1` AND appends a timestamp to `reopen_timestamps` on the new entry;
  (4) an `observe_issue` with a DIFFERENT fingerprint (different
  title/summary_text) after a resolve does NOT increment `reopen_count`
  or touch `reopen_timestamps` (it's a fresh, unrelated issue, not a
  reopen); (5) two full resolve-then-reobserve cycles bring
  `reopen_count` to `2` and `reopen_timestamps`/`resolved_timestamps`
  each to length 2; (6) `reopen_rate(repo)` on a repo with no recurrence
  state file returns `{"resolved_total": 0, "reopened_total": 0, ...}`
  (plus window keys) without raising; (7) `reopen_rate(repo)` after
  scenario (3), called with the default `window_days=30`, reflects the
  reopen in its returned counts; (8) the CORE windowing fix: construct an
  entry whose `resolved_timestamps` has one entry 60 days before `now`
  and whose `reopen_timestamps` has one entry 5 days before `now` (a
  single `last_observed_at` could not represent this split correctly) —
  `reopen_rate(repo, window_days=30, now=<that now>)` excludes the
  60-day-old resolution from `resolved_total` but INCLUDES the 5-day-old
  reopen in `reopened_total`, proving the function windows each list of
  timestamps independently rather than gating on one entry-level
  timestamp; (9) the returned dict carries `window_days`/`window_start`/
  `window_end` matching
  the arguments passed. Match this file's existing fixture/helper style
  (look for how it currently constructs `IssueObservation` and calls
  `observe_issue`/`resolve_issue`) — do not duplicate setup, reuse existing
  helpers if present.

---

**Total tasks:** 6 (3 parallel groups)
**Total tokens (incl. ~10k Agent overhead/task for sonnet, none for codex):** ~6400 output + 30k Agent overhead (3 sonnet tasks) = ~36.4k
**Total cost:** ~$0.213
**Executors:** sonnet×3, codex×3

**AC-13 status after this release:** stays `partial` — 3/5 named metrics
(scope-violation rate, unknown-usage rate, false-pass/reopen rate) get a
real, window-aligned measured value; 2/5 (Owner-interruptions-per-milestone,
duplicate-artifact rate) remain `null`+documented gap. Per Owner instruction
2026-08-05 ("schedule instrumentation for the remaining 2 metrics before
AC-13 can close"), this is tracked as a concrete, findable open item —
`.renmark/memory/bugs.md` "AC-13 closure path" entry (2026-08-05) — with a
specific implementation design for both metrics (an `owner_gate` event kind
via the handoff-menu contract; a `(feature, target, index)` duplicate
correlation over `task-runs.jsonl`), not a vague "someday" note. It is
explicitly proposed as its OWN bounded, Owner-approved future release
(number not unilaterally assigned here) rather than silently folded into
Release 15/16's already-scoped work.

**REQ-30 checklist (verify-time, no new code):** this release's
`/renmark:verify` pass records actual token spend for the 3 non-codex
(sonnet) dispatches against the `AGENT_OVERHEAD_TOKENS = 10,000` pin, and
explicitly lists the 3 codex dispatches as `unknown`-cost — never assumed
compliant — per `.renmark/memory/orchestration-baseline.md`'s recommended
budget line.

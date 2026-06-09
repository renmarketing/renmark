# Plan: reporting-and-usage-analytics — Part 1 (engine)

artifact_type: plan
schema_version: 1
created_at: 2026-06-09
generator: opus
related_feature: feature/reporting-and-usage-analytics
serves_prd: REQ-15, REQ-16

## Context

Local-only reporting/analytics/usage engine for renmark (REQ-15) + usage-aware
pause/resume (REQ-16). Stdlib JSON/JSONL only, no DB, no external telemetry.
**Part 1 builds the deterministic Python engine + tests**; Part 2 wires the CLI,
commands, skills, and integration hooks.

**Design reconciliations (locked — do not deviate):**
- The existing `.renmark/state/usage.jsonl` ledger (read by `renmark/state/usage.py`,
  consumed by `roadmap.py` + loop budget) stays the **token source of truth**. Do
  NOT create a second token ledger. The new `.renmark/analytics/` tree holds only
  the *new* event streams (`events/task-runs/feature-runs/loop-runs.jsonl`),
  `summary.json` (aggregated), and `limits.json` (config).
- REQ-16 pause extends the existing `renmark/state/pause.py` `PauseState` with
  optional, defaulted fields — old `PAUSED` files must still load via `PauseState(**data)`.
- All new code obeys dev-standards: full type annotations, non-raising ledger reads
  (degrade to None/[]), **no `datetime.now()` — inject `now`/`ts`** (use
  `renmark.state.now_iso()` at call sites), atomic writes, ≤100 lines/function,
  pytest `tmp_path` style.
- Mandatory disclaimer string (verbatim, exported as a constant):
  `"Observed local usage only. Provider-side account limits may differ."`

Dev gates (feature-level verify runs these): `pytest -q` · `ruff check` · `mypy .`

---

### Task 1: extend PauseState with usage-limit fields
- **mode:** B
- **target:** renmark/state/pause.py
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 1
- **est_tokens:** 700
- **est_cost_usd:** 0.03
- **verifier:** python -c "import renmark.state.pause as p; p.PauseState(run_id='r',plan_path='x',last_task_index=0,reason='usage_limit',ts='t')" && ruff check renmark/state/pause.py
- **serves:** REQ-16
- **spec:**
  Add optional, defaulted fields to `PauseState` for usage-limit pauses, keeping
  full back-compat (`read_pause` does `PauseState(**data)`, so EVERY new field MUST
  have a default; existing PAUSED files lacking them must still load). Add:
  `pause_kind: str = ""` (e.g. "usage_limit"), `provider: str = ""`,
  `model: str = ""`, `observed_usage: str = ""` (one-line summary), 
  `provider_reset_at: str = ""`, `resume_after: str = ""`,
  `fallback_retry_minutes: int = 60`, `feature: str = ""`, `loop_id: str = ""`,
  `iteration: int = 0`, `max_iterations: int = 0`.
  Keep the existing `reason` field (free text). Add a small helper
  `def usage_limit_pause(*, run_id, plan_path, last_task_index, ts, provider="",
  model="", observed_usage="", provider_reset_at="", resume_after="",
  fallback_retry_minutes=60, feature="", loop_id="", iteration=0,
  max_iterations=0) -> PauseState` that constructs a PauseState with
  `reason="usage limit reached"`, `pause_kind="usage_limit"`. Do not change
  write_pause/read_pause/clear_pause signatures. Mirror the new exports into
  `renmark/state/__init__.py` if you add the helper (add `usage_limit_pause`).

### Task 2: usage-window helpers + UsageRecord enrichment
- **mode:** B
- **target:** renmark/state/usage.py
- **complexity:** hard
- **executor:** opus
- **parallel_group:** 1
- **est_tokens:** 1400
- **est_cost_usd:** 0.04
- **verifier:** python -c "import renmark.state.usage as u; assert hasattr(u,'usage_in_window')" && ruff check renmark/state/usage.py
- **serves:** REQ-15
- **spec:**
  Two additive changes, both fully back-compatible (existing `usage.jsonl` rows
  must still parse; `as_jsonl`/`read_usage` semantics unchanged).
  (1) Enrich `UsageRecord` with optional defaulted fields: `provider: str = ""`,
  `cached_tokens: int = 0`, `context_window_tokens: int = 0`,
  `agent_calls: int = 0`, `requests: int = 0`, `feature: str = ""`,
  `source: str = "local-observed"` (one of: local-observed | configured-local-limit
  | provider-reported | estimated | unknown), `kind: str = ""`. Construction from
  old rows (missing keys) must not break — `read_usage` already returns dicts, so
  only `UsageRecord` callers are affected; keep all new params keyword-defaulted.
  (2) Add windowed read helpers, all taking an INJECTED `now: str` (ISO) — no
  `datetime.now()`:
  `def _parse_ts(ts: str) -> float | None` (epoch secs; None on bad),
  `def usage_in_window(repo, *, now: str, seconds: int) -> dict` returning
  `{"total_tokens":int,"prompt_tokens":int,"completion_tokens":int,"requests":int,
  "agent_calls":int,"rows":int}` summed over rows whose ts is within `now-seconds`,
  `def usage_last_5h(repo, *, now) -> dict` (seconds=5*3600),
  `def usage_last_week(repo, *, now) -> dict` (seconds=7*24*3600),
  `def tokens_by_feature(repo, *, now: str, seconds: int, top: int = 5) ->
  list[tuple[str,int]]` (descending). Non-raising; missing/corrupt → zeros/[].
  Export the new helpers from `renmark/state/__init__.py`.

### Task 3: usage-status engine (windows, limits, pause classification)
- **mode:** A
- **target:** renmark/usage.py
- **complexity:** hard
- **executor:** opus
- **parallel_group:** 2
- **est_tokens:** 2200
- **est_cost_usd:** 0.05
- **verifier:** python -c "import renmark.usage as u; assert u.DISCLAIMER and hasattr(u,'build_usage_view') and hasattr(u,'classify_usage_pause')" && ruff check renmark/usage.py
- **serves:** REQ-15, REQ-16
- **spec:**
  New module `renmark/usage.py` — the `/renmark:usage` view-model engine + pause
  classifier. Pure/deterministic; injects `now`. Depends on Task 2 helpers and
  Task 1 PauseState.
  - `DISCLAIMER = "Observed local usage only. Provider-side account limits may differ."`
  - `def read_limits(repo) -> dict` — read `.renmark/analytics/limits.json`
    (schema `{"claude":{"rolling_5h_tokens":int,"weekly_tokens":int,
    "rolling_5h_requests":int,"weekly_requests":int}, "codex":{...}}`); non-raising,
    `{}` if absent.
  - `def percent_used(observed: int, limit: int | None) -> float | None` —
    None when no limit configured; else `round(100*observed/limit,1)` (limit>0).
  - `def build_usage_view(repo, *, now: str) -> dict` — assemble bounded view:
    rolling-5h + weekly observed (tokens/requests/agent_calls from Task 2 helpers),
    configured limits + percent_used per provider (or "no configured local limit"),
    top token-heavy features (`tokens_by_feature`), recent rate/quota events
    (scan usage rows where `kind`∈{"rate_limit","quota"} — last 5), paused runs
    waiting for reset (`renmark.state.read_pause`; include resume_after / suggested
    resume time), and `disclaimer=DISCLAIMER`. Provider-reported limit/reset only
    surfaces when a row carries `source="provider-reported"`; otherwise omit (never
    fabricate account quota).
  - `def classify_usage_pause(*, run_id, plan_path, last_task_index, now, provider="",
    model="", observed_usage="", provider_reset_at="", limits=None, feature="",
    loop_id="", iteration=0, max_iterations=0) -> PauseState` — implements the
    fallback rule for `resume_after`: provider_reset_at if given; else next local
    rolling-window boundary if configured 5h limit exists (compute from `now`);
    else `now + 60 min`. Returns `pause.usage_limit_pause(...)`. MVP: NO polling,
    NO auto-retry scheduling.
  - `def render_usage_md(view: dict) -> str` — bounded markdown; ALWAYS ends with
    the disclaimer line. Never dumps raw rows.

### Task 4: report builders (feature/task/loop/release)
- **mode:** A
- **target:** renmark/reports.py
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 2
- **est_tokens:** 1800
- **est_cost_usd:** 0.05
- **verifier:** python -c "import renmark.reports as r; assert hasattr(r,'build_feature_report') and hasattr(r,'write_feature_report')" && ruff check renmark/reports.py
- **serves:** REQ-15
- **spec:**
  New module `renmark/reports.py` — bounded local report builders. Deterministic;
  inject `now`/`ts`. Writes under `.renmark/reports/{tasks,loops,backlog,features,
  releases}/`.
  - `def feature_reports_dir(repo, slug) -> Path` → `.renmark/reports/features/<slug>/`.
  - `def build_feature_report(repo, *, feature: str, branch: str = "", sha: str = "",
    version_path: str = "", verification: str = "", codereview: str = "",
    files_changed: int = 0, token_cost: dict | None = None, loop_iterations: int = 0,
    stop_reason: str = "", branch_disposition: str = "", shipped: list[str] | None =
    None, deferred: list[str] | None = None, next_backlog: list[str] | None = None,
    task_id: str = "", backlog_item_id: str = "", loop_id: str = "", now: str = "")
    -> dict` — assemble the metrics dict with ALL REQ-15 report fields. If a
    release `version_path` is given (or `.renmark/version/<version>/` exists), include
    a link to it.
  - `def render_report_md(report: dict) -> str` — human-readable bounded report.md.
  - `def write_feature_report(repo, slug, report: dict) -> tuple[Path, Path]` —
    write `report.md` + `metrics.json` (atomic) into the feature dir; return paths.
  - `def write_run_report(repo, kind: str, run_id: str, report: dict) -> Path` —
    generic writer for tasks/loops/backlog/releases → `.renmark/reports/<kind>/
    <run_id>.json`. Non-raising on mkdir.
  Keep bounded: reports summarize; they never embed code or diffs.

### Task 5: analytics event ledgers + aggregation + health report
- **mode:** A
- **target:** renmark/analytics.py
- **complexity:** hard
- **executor:** opus
- **parallel_group:** 3
- **est_tokens:** 2400
- **est_cost_usd:** 0.05
- **verifier:** python -c "import renmark.analytics as a; assert hasattr(a,'record_event') and hasattr(a,'aggregate') and hasattr(a,'build_health_report')" && ruff check renmark/analytics.py
- **serves:** REQ-15
- **spec:**
  New module `renmark/analytics.py` — append-only event ledgers under
  `.renmark/analytics/` + Python aggregation into a small `summary.json`. Reads the
  existing `.renmark/state/usage.jsonl` (via `renmark.state.read_usage`) for token
  rollups — does NOT duplicate it. Inject `ts`/`now`. Non-raising.
  - `def analytics_dir(repo) -> Path` → `.renmark/analytics/` (mkdir parents).
  - Append helpers (one JSONL each, compact line, `open("a")`):
    `record_event(repo, *, ts, kind, **fields)` → `events.jsonl`;
    `record_task_run(repo, *, ts, task_id, title="", executor="", model="",
    provider="", status="", verifier_result="", retry_count=0, failure_reason="",
    duration_s=0.0, tokens_in=0, tokens_out=0, total_tokens=0, est_cost_usd=0.0,
    sha="")` → `task-runs.jsonl`;
    `record_feature_run(repo, *, ts, feature, branch="", status="", sha="",
    files_changed=0, verification="", token_cost=None, branch_disposition="")` →
    `feature-runs.jsonl`;
    `record_loop_run(repo, *, ts, loop_id, goal="", backlog_item_id="",
    max_iterations=0, iterations_used=0, stop_reason="", goal_reached=False,
    total_tokens=0, est_cost_usd=0.0, branch_disposition="")` → `loop-runs.jsonl`.
    Each record carries a `source` field defaulting to `"local-observed"`.
  - `def read_jsonl(path) -> list[dict]` — shared non-raising reader (skip corrupt).
  - `def aggregate(repo, *, now: str) -> dict` — roll up the ledgers into the
    bounded summary: features started/completed/blocked; task success/failure/skipped;
    backlog completed/blocked/rejected; loop success/failure + avg iterations;
    verification pass/fail; common failure reasons (top 5); branch dispositions;
    releases created; token usage by provider/model/executor and by feature; request +
    agent-call counts; quota/rate-limit + pause/resume event counts. Write to
    `.renmark/analytics/summary.json` (atomic) and return it.
  - `def build_health_report(repo, *, now: str) -> dict` — the `/renmark:analytics`
    view: shipped/blocked features, recent releases, recent verification failures,
    loop success rate, avg loop iterations, backlog throughput, branch-disposition
    summary, token/cost by recent feature, common failure reasons. Bounded; NEVER
    returns raw rows.
  - `def render_health_md(report: dict) -> str` — bounded markdown.

### Task 6: schema validators for new artifacts
- **mode:** B
- **target:** renmark/schemas.py
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 4
- **est_tokens:** 900
- **est_cost_usd:** 0.03
- **verifier:** python -c "import renmark.schemas as s; assert s.validate_limits({})==[] or isinstance(s.validate_limits({}),list); assert hasattr(s,'validate_analytics_summary')" && ruff check renmark/schemas.py
- **serves:** REQ-15
- **spec:**
  Add non-raising validators (return `list[str]` of issues, `[]` = valid), matching
  the existing `validate_*` convention in this file:
  `validate_limits(data)` — optional `claude`/`codex` objects with int ceilings;
  unknown keys allowed; negative/zero limits flagged.
  `validate_analytics_summary(data)` — `aggregate()` output shape (dict with the
  documented keys; types sane).
  `validate_report_metrics(data)` — feature-report metrics.json shape (feature name
  present; counts ints; lists are lists).
  `validate_usage_pause(data)` — PauseState dict with `pause_kind="usage_limit"`
  carries `resume_after` and `provider`/`fallback_retry_minutes`.
  Do not raise; mirror the structural style of `validate_lifecycle`.

### Task 7: tests — state pause/usage back-compat + windows
- **mode:** A
- **target:** tests/test_state_pause_usage.py
- **complexity:** medium
- **executor:** codex
- **parallel_group:** 5
- **est_tokens:** 1200
- **est_cost_usd:** 0.03
- **verifier:** pytest tests/test_state_pause_usage.py -q
- **serves:** REQ-15, REQ-16
- **spec:**
  Pytest (`tmp_path`, plain functions, injected timestamps). Cover:
  - Old PAUSED file (only run_id/plan_path/last_task_index/reason/ts) still loads via
    `read_pause` after the PauseState extension (back-compat).
  - `usage_limit_pause(...)` builds a PauseState with `pause_kind="usage_limit"` and
    round-trips through write_pause/read_pause.
  - `UsageRecord` with new fields round-trips via `as_jsonl` + `read_usage`; an old
    row dict (missing new keys) reads fine.
  - `usage_in_window` / `usage_last_5h` / `usage_last_week` sum only rows inside the
    window given an injected `now`; out-of-window rows excluded; empty ledger → zeros.
  - `tokens_by_feature` ranks descending and respects `top`.

### Task 8: tests — usage-status engine
- **mode:** A
- **target:** tests/test_usage.py
- **complexity:** medium
- **executor:** codex
- **parallel_group:** 5
- **est_tokens:** 1300
- **est_cost_usd:** 0.03
- **verifier:** pytest tests/test_usage.py -q
- **serves:** REQ-15, REQ-16
- **spec:**
  Pytest. Cover:
  - `read_limits` returns `{}` when no limits.json; parses a written limits.json.
  - `percent_used` → None with no limit; correct % with a limit.
  - `build_usage_view` includes 5h + weekly blocks, top features, paused-run block
    when a PAUSED file exists, and ALWAYS the exact DISCLAIMER constant.
  - `build_usage_view` states "no configured local limit" when limits.json absent.
  - `classify_usage_pause` fallback rule: (a) uses provider_reset_at when given;
    (b) computes a local-window resume when only configured limits exist; (c) falls
    back to now+60min otherwise. Assert `pause_kind="usage_limit"`.
  - `render_usage_md` output ends with the disclaimer; never contains raw JSONL.

### Task 9: tests — reports + analytics aggregation
- **mode:** A
- **target:** tests/test_reports_analytics.py
- **complexity:** medium
- **executor:** codex
- **parallel_group:** 5
- **est_tokens:** 1400
- **est_cost_usd:** 0.03
- **verifier:** pytest tests/test_reports_analytics.py -q
- **serves:** REQ-15
- **spec:**
  Pytest. Cover:
  - `build_feature_report` populates all REQ-15 fields; `write_feature_report`
    writes `report.md` + `metrics.json` under `.renmark/reports/features/<slug>/`;
    metrics.json validates via `schemas.validate_report_metrics`.
  - release report links to a `.renmark/version/<version>/` path when provided.
  - `record_task_run`/`record_feature_run`/`record_loop_run`/`record_event` append
    parseable JSONL under `.renmark/analytics/`.
  - `aggregate` rolls counts/averages correctly from seeded ledgers, writes
    `summary.json`, and validates via `schemas.validate_analytics_summary`.
  - `build_health_report` returns bounded keys and never raw rows; empty project
    degrades to zeros/empty lists without raising.

## Cost preview (Part 1)

| Task | file | executor | est tokens (+overhead) | est $ |
|---|---|---|---|---|
| 1 | state/pause.py | sonnet | 700 +10k | 0.03 |
| 2 | state/usage.py | opus | 1400 +10k | 0.17 |
| 3 | usage.py | opus | 2200 +10k | 0.18 |
| 4 | reports.py | sonnet | 1800 +10k | 0.035 |
| 5 | analytics.py | opus | 2400 +10k | 0.19 |
| 6 | schemas.py | sonnet | 900 +10k | 0.033 |
| 7 | test_state_pause_usage.py | codex | 1200 | 0.03 |
| 8 | test_usage.py | codex | 1300 | 0.03 |
| 9 | test_reports_analytics.py | codex | 1400 | 0.04 |

**Part 1 total: ~9 tasks, 5 waves, ~$0.77** (opus overhead dominates; codex tests flat).
Executors: sonnet×2, opus×3, codex×3, (haiku×0). Wave plan: W1[1,2] · W2[3,4] · W3[5] · W4[6] · W5[7,8,9].

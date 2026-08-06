---
artifact_type: rethink-baseline
schema_version: 1
created_at: 2026-08-06T18:40:37Z
source_sha: 286d016a61a8c1ffbcbac09f83e937328771c3d4
related_plan: /renmark:rethink cross-host-native-tool-leverage, Stage 2
generator: sonnet
---

# Cross-host behavioral baseline — "cross-host native-tool leverage"

Captures the CURRENT behavior that any adoption of more native host tools
must not break, per Stage 2 of `/renmark:rethink`.

## Current cross-host behavior

### 1. `renmark.interaction.build_selector` (`renmark/interaction.py:147-267`)

- Resolves host via `resolve_host(host)` (`renmark/hosts.py:91`), then pulls
  `HostCapabilities` via `capabilities_for` (`hosts.py:114`).
- **Single-choice guard**: if `len(decision.choices) == 1`, always returns the
  numbered fallback (`interaction.py:188-195`) regardless of host — a native
  selector is never rendered for a single option.
- **No native selector tool** (`caps.selector_tool is None`,
  `interaction.py:196-211`): returns the fallback payload. If the caller set
  `enforce_native=True` and `tool_available=False` while a native selector
  genuinely exists for the host, raises `SelectorBypassError`
  (`interaction.py:197-204`) — this is the guard against the documented
  "hand-off picker not re-rendered on continuation turns" bug class.
- **Page sizing differs by host** (`hosts.py:46-67`): Claude Code
  (`selector_min_options=1, selector_max_options=4`, tool
  `AskUserQuestion`, `selector_available=True` by default) vs. Codex
  (`selector_min_options=2, selector_max_options=3`, tool
  `request_user_input`, `selector_available=False` by default — Codex
  Default mode does not expose the tool). `_native_page`
  (`interaction.py:384-456`) paginates choices to fit the host's
  min/max window, adding `more`/`back` entries as needed.
- When no page fits the host's option window, `_native_page` returns `None`
  and the caller falls back; the `reason` string differs by host:
  `"selector_requires_multiple_options"` for Codex (its `min_options=2`
  can't render a 1-choice-plus-extras page) vs.
  `"selector_capacity_unavailable"` for Claude (`interaction.py:214-220`).
- **Native arguments shape differs by host** (`interaction.py:229-250`):
  Codex's `request_user_input` gets `{"header": ...[:12], "id": decision_id,
  "question": ..., "options": [...]}` (header truncated to 12 chars, plus an
  `id` field Claude does not receive); Claude's `AskUserQuestion` gets
  `{"header": ..., "question": ..., "multiSelect": False, "options": [...]}`
  (no truncation, no `id`, adds `multiSelect`).
- Regardless of host, the returned payload always carries a complete
  `fallback` (numbered list) and `page.bindings` so a caller can resolve an
  answer without re-invoking the native tool (`continue_selector`,
  `interaction.py:270-311`).

### 2. Dispatch transport selection (`renmark/dispatch.py`)

- `build_host_dispatch_plan` (`dispatch.py:1057-1121`) filters the wave to
  `claude_agent.is_claude_executor(task.executor)` tasks — `executor: codex`
  tasks are explicitly excluded and stay on the deterministic
  `renmark-execute` subprocess path on *both* hosts (`dispatch.py:1072-1074`,
  docstring).
- `host` must normalize to exactly `"claude"` or `"codex"`
  (`dispatch.py:1077-1080`); anything else raises `ValueError`.
- `strategy` is `"single"` for one task, `"fanout"` for >1 task
  (`dispatch.py:1095`), independent of host.
- **Claude branch** (`_build_claude_host_calls`, `dispatch.py:1223-1265`):
  - >1 task → one `HostDispatchCall` with `tool="Workflow"`, `arguments={"args": [...]}` — one payload per task, each carrying a resolved `agent_type` from `subagent_profiles.native_agent_type(inp.role)`.
  - exactly 1 task → one call with `tool="Agent"`, `arguments={"description", "prompt"}`; adds `subagent_type` when a native agent type resolves, and adds `model="fable"` only when `task.executor == "fable"`.
- **Codex branch** (`_build_codex_host_calls`, `dispatch.py:1268-1299`):
  always one call **per task** (never a fan-out tool) — each built via
  `codex_routing.build_native_dispatch`, with `tool=native.spawn_tool`
  (i.e. `spawn_agent`) and a `model_route` block (`model`,
  `reasoning_effort`, `tier`, `reason`) that Claude calls never carry.
  `build_host_dispatch_plan` additionally sets `wait_tool="wait_agent"` and
  `followup_tool="followup_task"` only for the Codex plan
  (`dispatch.py:1109-1121`) — Claude's plan leaves those `None`.
- `build_host_dispatch_plan_with_scope` (`dispatch.py:1124-1177`) is a thin
  wrapper: for `host == "claude"` it additionally populates
  `scoped_dispatches` via `_maybe_scoped_claude_dispatch` (single-task,
  `fast_path.classify_fast_path`-eligible only); for `host == "codex"` it
  **intentionally leaves `scoped_dispatches` empty** — per the docstring,
  "Owner's 2026-08-05 scope decision: Codex gets no pre-action scoping this
  release and stays on the `verified_after`, Layer-B-only path"
  (`dispatch.py:1145-1147`). This is a live, explicit host-behavior
  asymmetry, not an oversight — any native-tool change must decide
  deliberately whether to close or preserve it.

### 3. `renmark.headless.resolve_gate` (`renmark/headless.py:33-87`)

Does **not** branch on host at all. Headless/interactive detection is owned
solely by `config.is_headless(repo)` (`headless.py:63`); the `tool_available`
parameter is accepted only for backward API compatibility and explicitly
ignored (`headless.py:64`, `"_ = tool_available  # Compatibility-only;
selector absence != headless."`). Selector availability (a host trait) is
deliberately decoupled from headless detection (an execution-mode trait) —
skills consult `renmark.interaction` separately for the former. Any
native-tool leverage work must preserve this separation: a host gaining a
richer native tool must not be allowed to silently redefine "headless."

### 4. Cross-host parity tests

- `tests/test_cross_host_dispatch_e2e.py`:
  - `test_simulated_plan_dispatch_verify_has_cross_host_semantic_parity`
    (line 112) — asserts a simulated plan→dispatch→verify flow produces
    semantically equivalent outcomes across both hosts.
  - `test_simulated_loop_resume_has_cross_host_semantic_parity` (line 175) —
    same for a loop/resume flow.
- `tests/test_hosts.py`, `tests/test_interaction.py`,
  `tests/test_selector_contract.py`, `tests/test_dispatch.py` all contain
  paired `codex`/`claude` assertions (capability table values, selector
  payload shape per host, dispatch-call tool selection per host).
- `tests/behavioral/selector_codex.behavior.json` — behavioral-tier fixture
  locking the Codex selector transcript shape.

## Compatibility tests (run fresh, this session)

- `python3 -m pytest -q tests/ -k "host or codex or claude or dispatch or interaction"`
  → **220 passed, 17 skipped, 1896 deselected**
- `python3 -m pytest -q tests/test_dispatch.py tests/test_hosts.py tests/test_interaction.py tests/test_cross_host_dispatch_e2e.py tests/test_selector_contract.py`
  → **70 passed**
- Full suite: `python3 -m pytest -q`
  → **2099 passed, 32 skipped, 2 failed** (both in
  `tests/test_analytics_guardrail_metrics.py`:
  `test_agg_guardrail_metrics_false_pass_reopen_rate_tracks_event_timestamps`,
  `test_aggregate_build_health_and_render_health_surface_guardrail_metrics`
  — pre-existing, unrelated to host/dispatch/interaction; guardrail-metrics
  aggregation, not touched by this research).

## Measured baseline to hold (`.renmark/memory/orchestration-baseline.md`)

Pinned to `ORCHESTRATION-BASELINE-2026-08` (`v0.39.7`, commit `d9cccc5`,
2026-08-02); most recently re-measured 2026-08-05.

- **`AGENT_OVERHEAD_TOKENS = 10,000`** (`renmark/cost.py:83`,
  `renmark/roadmap.py:38`) — unchanged since the pin, confirmed via
  `git log -p --since=2026-08-02` on both files (zero hits). Any native-tool
  adoption that changes per-dispatch overhead must re-check this constant
  and stay within REQ-30's 15% regression band.
- **Codex is token-blind**: 9 of 26 Rethink dispatches (35%) and an unknown
  share of Feature/Fix and Orchestrate dispatches never surface tokens.
  Only 2 non-codex (sonnet, `local-observed`) samples exist against the
  10,000 pin: 10,000 and 11,800 tokens (~0% and ~18% over). Sample too
  small to certify calibration. **Concretely for REQ-30's 15% threshold**:
  any comparison of a native-tool change's token cost must explicitly
  disclose the excluded codex share rather than compute a blended
  system-wide percentage that silently omits ~35%+ of dispatch volume.
- **Feature/Fix measured total**: 502,107 tokens across 12 `measured:true`
  rows (haiku 173,631 / sonnet 278,389 / opus 50,087) from the
  `orchestration-baseline-controls` build (2026-08-02/03) — the only
  fully-measured (not self-reported) figure on file. Held as the
  Feature/Fix reference point; a future comparison run belongs to whichever
  feature triggers it, not automatically to this number.
- **Owner-gate count discipline**: exactly 1 Execution Gate observed across
  the entire 26-task, Releases 1-6 Rethink run to date (`delivery.json`
  `provenance_events`, 0 new entries since 2026-08-04) — confirms the
  "no routine per-work-package gate" baseline
  (`feedback_wp_progression_no_gate`). Any native-tool change that adds a
  routine gate beyond a pipeline's named gates is a REQ-30 regression by
  definition, independent of the 15% token/time threshold.
- **Dispatch-count discipline**: no duplicate/repeated-completed-work
  dispatches found in the Releases 1-6 Rethink sample (7 `work_order`, 7
  `work_result` all `status: complete`, 7 `inspection_report` all
  `verdict: pass`) — a ledger-coverage gap exists (24 ledger rows vs. 26
  planned tasks) but no evidence of re-dispatch. This is the baseline
  "no duplicate dispatch" bar a native-tool change must not cross.
- **Start scenario**: still `unknown` — no `/renmark:start` run exists on
  disk to compare against. Not a blocker for this baseline, but any
  native-tool change touching the Start pipeline has no prior numeric
  baseline to regress against and should capture one before/after.

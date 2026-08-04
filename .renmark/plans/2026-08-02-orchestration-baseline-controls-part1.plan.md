# Orchestration baseline controls — Part 1: usage instrumentation + context-lifecycle checkpoint

Implements audit §9 items 1 and 3 from `.renmark/audits/orchestration-baseline-audit-2026-08-02.md`
(Owner-accepted ORCHESTRATION-BASELINE-2026-08), extending REQ-30/REQ-31 machinery — no parallel
systems. Two threads: (a) make per-dispatch usage honestly measured-or-marked-unknown instead of
hardcoded 0, using the same live-host-vs-headless two-layer pattern REQ-31's task-tracking already
established; (b) wire the existing but currently dead-code `context_budget_hint` to a real signal at
Agency milestone boundaries, producing a manual checkpoint instruction (never fabricated automation),
gated so it never fires on every milestone — only when the configured threshold is actually reached.
Part 2 (routing enforcement + artifact contract) is a separate plan file to stay under the per-run
task cap.

### Task 1: UsageRecord measured flag
- **mode:** B
- **target:** renmark/state/usage.py
- **complexity:** simple
- **executor:** codex
- **role:** code-implementer
- **parallel_group:** 1
- **est_tokens:** 400
- **est_cost_usd:** 0.02
- **verifier:** python3 -m py_compile renmark/state/usage.py
- **serves:** REQ-30
- **spec:**
  `UsageRecord` (dataclass, ~line 19) already has a documented back-compat pattern: optional
  keyword-defaulted fields added after the required ones (see the `provider`/`cached_tokens`/
  `context_window_tokens`/`agent_calls`/`requests`/`feature` block, REQ-15). Add one more field in
  that same style, after `feature`:
  ```python
  # Honest-measurement flag (REQ-30 instrumentation). False means prompt_tokens/
  # completion_tokens are NOT a real measured value — do not treat 0 as "zero
  # tokens used." Defaults False so every pre-existing usage.jsonl row (which
  # predates this field) parses as "unmeasured", which is the truthful reading.
  measured: bool = False
  ```
  Do not change any existing field, the constructor call sites, or `as_jsonl`/`append_usage`
  logic beyond what dataclass field serialization already does automatically. Do not add validation
  that rejects old rows lacking this key.

### Task 2: record_task_run measured param + honest aggregation
- **mode:** B
- **target:** renmark/analytics.py
- **complexity:** medium
- **executor:** sonnet
- **role:** code-implementer
- **parallel_group:** 2
- **est_tokens:** 900
- **est_cost_usd:** 0.03
- **verifier:** python3 -m py_compile renmark/analytics.py
- **serves:** REQ-30
- **spec:**
  Two additive changes, no removals:

  1. `record_task_run` (~line 161): add a trailing keyword param `measured: bool = False`, and
     include `"measured": measured` in the appended dict (mirrors the existing `tokens_in`/
     `tokens_out` pattern). Every existing call site (which omits `measured`) keeps writing
     `measured: false` — behavior for existing callers is unchanged.
  2. `_agg_tasks` (~line 482): currently sums `tokens_by_executor`/`tokens_by_model`/
     `tokens_by_provider` from `total_tokens` or `tokens_in+tokens_out`, without regard to whether
     that number is real. Add two NEW keys to its returned dict (do not remove or rename any
     existing key): `"measured_tokens_total"` (int — sum of `tokens` only over rows where
     `r.get("measured")` is truthy) and `"unmeasured_task_count"` (int — count of rows where
     `tokens` was nonzero-truthy in the existing sum but `measured` was falsy, i.e. rows whose
     token figure is unverified). This makes `summary.json` honestly distinguish "we counted a
     number" from "we measured a real number" without breaking any existing consumer of the
     current keys.

### Task 3: usage-instrumentation contract (new shared fragment)
- **mode:** A
- **target:** plugin/skills/.shared/usage-instrumentation.md
- **complexity:** medium
- **executor:** sonnet
- **role:** docs-editor
- **parallel_group:** 3
- **est_tokens:** 700
- **est_cost_usd:** 0.0261
- **verifier:** test -f plugin/skills/.shared/usage-instrumentation.md
- **serves:** REQ-30
- **spec:**
  New reference doc, same shape as `plugin/skills/.shared/task-tracking.md` (read that file for the
  two-layer pattern and prose style before writing this one — cite it, do not restate its content).
  Content:

  - **Why:** Claude Code's own `Agent` tool completion already returns a real, measured usage block
    per subagent dispatch (`subagent_tokens`, `tool_uses`, `duration_ms` — visible in every
    `<task-notification>` a live session receives). No Python module can intercept that block on
    the agent's behalf — only the live agent that just made the `Agent` tool call can see it. This
    is the exact same reasoning `task-tracking.md` already documents for why native `TaskCreate`/
    `TaskUpdate` must be a live in-transcript tool call, not a Python side effect — the same
    two-layer split applies here.
  - **Layer 1 (primary, live host):** whenever an interactive session dispatches an `Agent` tool
    call as part of running a renmark pipeline (orchestrate, feature, debug, rethink, etc.), it
    MUST, immediately after receiving the result, call
    `renmark.analytics.record_task_run(repo, ts=..., task_id=..., executor=..., model=..., status=...,
    duration_s=<duration_ms/1000>, tokens_in=<subagent_tokens>, total_tokens=<subagent_tokens>,
    measured=True, ...)` using the REAL numbers from the `<usage>` block it just received — not an
    estimate, not the plan's `est_tokens`. This is a skill instruction to the live agent, satisfied
    only by a real Python call using real numbers seen in the transcript.
  - **Layer 2 (headless fallback):** the `renmark-execute` CLI's Codex/subprocess dispatch path
    (`renmark/cli/_engine.py`'s `execute_plan`) has no live Agent-tool result to read usage from,
    and the Codex CLI itself does not currently surface token usage (see
    `renmark/cli/commands.py:452`'s comment). That path continues to record `measured=False` — this
    is honest, not a bug, and is explicitly out of scope for this contract (mirrors R-0.3's
    documented "explicitly out of scope, not an oversight" precedent for partial dispatch-path
    coverage).
  - **What NOT to do:** never estimate a token figure and record it with `measured=True`. Never
    read the `.output` transcript file to extract usage — only the `<usage>` block already surfaced
    inline in the task-notification/tool-result is a real measured number.

### Task 4: orchestrate dispatch-step citation
- **mode:** B
- **target:** plugin/skills/orchestrate/SKILL.md
- **complexity:** simple
- **executor:** haiku
- **role:** docs-editor
- **parallel_group:** 4
- **est_tokens:** 200
- **est_cost_usd:** 0.0092
- **verifier:** grep -q "usage-instrumentation.md" plugin/skills/orchestrate/SKILL.md
- **serves:** REQ-30
- **spec:**
  Find the existing task-tracking citation in this file (added for REQ-31, references
  `_shared/task-tracking.md`) and add one sentence immediately after it, same style, citing the new
  `${CLAUDE_PLUGIN_ROOT}/skills/.shared/usage-instrumentation.md` contract from Task 3: after each
  real `Agent` tool dispatch, call `renmark.analytics.record_task_run(..., measured=True)` with the
  real usage numbers per that contract. Do not inline the contract's content — pointer only, one
  or two sentences.

### Task 5: milestone_context_checkpoint
- **mode:** B
- **target:** renmark/lifecycle.py
- **complexity:** medium
- **executor:** sonnet
- **role:** code-implementer
- **parallel_group:** 5
- **est_tokens:** 1100
- **est_cost_usd:** 0.0363
- **verifier:** python3 -m py_compile renmark/lifecycle.py
- **serves:** REQ-30
- **spec:**
  Add a new function, near `persist_compact_checkpoint` (~line 869):
  ```python
  def milestone_context_checkpoint(
      repo: Path | str,
      *,
      skill: str,
      estimated_tokens: int | None = None,
      host: str | HostKind | None = None,
  ) -> str | None:
      """At an approved Agency milestone boundary, recommend a compact checkpoint
      ONLY when a real context-size signal has been provided and it has reached
      the configured threshold. Never fires on every milestone — only when
      `estimated_tokens` is given and crosses `config.compact_gate_tokens(repo)`.
      No SDK/launcher exists in this codebase to send /compact programmatically
      (see the ORCHESTRATION-BASELINE-2026-08 audit) — this returns a manual
      instruction string, never fabricated automation. Never raises.
      """
  ```
  Implementation:
  - `from . import config as _config` (lazy import, matches existing lazy-import convention in this
    module).
  - If `estimated_tokens is None`: return `None` immediately — no signal, no checkpoint, no
    fabricated automation. This is the honest "no reliable signal" branch.
  - Compute `threshold = _config.compact_gate_tokens(repo)`. If `threshold == 0` (gate disabled) or
    `estimated_tokens < threshold`: return `None` — below threshold, do not checkpoint.
  - Otherwise (`estimated_tokens >= threshold > 0`): call
    `persist_compact_checkpoint(repo, skill=skill, reason="milestone-boundary", host=host)`
    (best-effort — wrap the whole function body in `try/except Exception: return None`, matching
    the never-raising convention `context_budget_hint`/`persist_compact_checkpoint` already use),
    then return exactly one manual-instruction string:
    `"Context at milestone boundary: ~{estimated_tokens} tokens (threshold {threshold}). "
    "Checkpoint written to .renmark/state/compact_checkpoint.json. "
    "Run: /compact — then run: /renmark:resume"`
    (adjust wording to match this repo's existing compact-gate message style in `skill_preamble`,
    ~line 985-995 — reuse that exact phrasing convention rather than inventing new copy).
  - Do not call this function from anywhere in this task — wiring a caller is Task 6.

### Task 6: wire checkpoint into Agency milestone boundaries
- **mode:** B
- **target:** renmark/agency.py
- **complexity:** medium
- **executor:** sonnet
- **role:** code-implementer
- **parallel_group:** 6
- **est_tokens:** 900
- **est_cost_usd:** 0.03
- **verifier:** python3 -m py_compile renmark/agency.py
- **serves:** REQ-30
- **spec:**
  `agency.py` calls `append_provenance_event` at two sites (~line 262, ~line 343). Do NOT modify
  `append_provenance_event` itself (in `delivery_state.py` — it's a shared pure function used by
  many event kinds, not just milestone boundaries; changing it is out of scope and risks changing
  behavior for non-milestone callers). Instead, at the call site(s) in THIS file where the event
  `kind` represents an actual milestone boundary (i.e. `"milestone-passed"` or
  `"milestone-released"` — read the surrounding code to confirm which kind string each call site
  passes; only hook the ones that are genuinely milestone-boundary, not every provenance event),
  add a best-effort call immediately after the event is appended:
  ```python
  try:
      from . import lifecycle as _lifecycle
      hint = _lifecycle.milestone_context_checkpoint(repo, skill="agency")
  except Exception:
      hint = None
  ```
  Note: `estimated_tokens` is intentionally omitted here (defaults to `None`) — this repo has no
  reliable Python-side context-size signal (confirmed by the audit), so this call site honestly
  never triggers a checkpoint on its own; it exists so a FUTURE caller with a real self-reported
  estimate (e.g. a live agent passing its own estimate through a future parameter on
  `approve_milestone_for_orchestrator`) has a wiring point already in place. Do not invent an
  estimate here — that would violate "never compact after every milestone" by making every call
  synthetically cross the threshold. This task's job is the honest wiring, not a fabricated trigger.
  If `hint` is not None, do not silently drop it — attach it to whatever this function already
  returns to its caller (check the function's return type; if it returns `DeliveryState` only,
  add it as a module-level side-effect print/log consistent with how this file already surfaces
  non-blocking notes elsewhere, or return it as a second value only if that does not break existing
  callers — prefer the least invasive option that doesn't change `approve_milestone_for_orchestrator`'s
  existing return contract).

### Task 7: context checkpoint tests
- **mode:** A
- **target:** tests/test_context_checkpoint.py
- **complexity:** medium
- **executor:** codex
- **role:** test-writer
- **parallel_group:** 7
- **est_tokens:** 800
- **est_cost_usd:** 0.03
- **verifier:** pytest tests/test_context_checkpoint.py -q
- **serves:** REQ-30
- **spec:**
  Test `renmark.lifecycle.milestone_context_checkpoint`:
  1. `estimated_tokens=None` → returns `None` (no signal, no checkpoint).
  2. `estimated_tokens` below the configured threshold (use `renmark.config.set_compact_gate_tokens`
     to pin a known threshold in a tmp repo fixture) → returns `None`.
  3. `estimated_tokens` at/above threshold → returns a non-None string containing `/compact` and
     `/renmark:resume`, AND `.renmark/state/compact_checkpoint.json` exists after the call.
  4. Threshold `0` (disabled) → always returns `None` regardless of `estimated_tokens`.
  5. Never raises: monkeypatch `persist_compact_checkpoint` to raise, confirm the function still
     returns without propagating the exception.
  Use a tmp_path-based fake repo fixture consistent with this test suite's existing conventions
  (check `tests/test_lifecycle.py` for the fixture pattern already used in this repo).

### Task 8: usage instrumentation tests
- **mode:** A
- **target:** tests/test_usage_instrumentation.py
- **complexity:** medium
- **executor:** codex
- **role:** test-writer
- **parallel_group:** 8
- **est_tokens:** 800
- **est_cost_usd:** 0.03
- **verifier:** pytest tests/test_usage_instrumentation.py -q
- **serves:** REQ-30
- **spec:**
  Test:
  1. `renmark.state.usage.UsageRecord(...)` without `measured` defaults to `measured=False`; with
     `measured=True` round-trips through `as_jsonl`/`read_usage` correctly.
  2. `renmark.analytics.record_task_run(..., measured=True)` writes a row with `"measured": true`
     in `task-runs.jsonl`; omitting `measured` writes `"measured": false`.
  3. `renmark.analytics._agg_tasks` (or whatever public summary function wraps it — check for a
     `build_summary`/`summary` public entry point in `renmark/analytics.py` and test through that
     if one exists, else test `_agg_tasks` directly): given a mix of `measured=True` and
     `measured=False`/absent rows, `measured_tokens_total` sums ONLY the measured rows, and
     `unmeasured_task_count` counts the rest. Existing keys (`tokens_by_executor` etc.) are
     unaffected — assert they still sum ALL rows as before (regression guard: this feature must not
     change what those existing keys report).
  4. A pre-existing `task-runs.jsonl` row (dict) with no `measured` key at all parses without error
     and is treated as unmeasured — back-compat guard.

## Cost preview

| Executor | Count | Tokens (incl. agent overhead) | $/kT | Cost |
|---|---:|---:|---:|---:|
| haiku | 1 | 200 + 10000 = 10200 | $0.0001 | $0.0010 |
| sonnet | 3 | (900+700+900) + 3×10000 = 32500 | $0.003 | $0.0975 |
| codex | 4 | 400+800+800+1100(task5 is sonnet, not counted here) | see below | see below |

Recompute cleanly by executor:
- haiku × 1 (Task 4): 200 + 10000 = 10200 tok → $0.00102
- sonnet × 4 (Tasks 2, 3, 5, 6): (900+700+1100+900) + 4×10000 = 43600 tok → $0.1308
- codex × 3 (Tasks 1, 7, 8): 400+800+800 = 2000 tok → ~$0.03–$0.05 est (codex has no fixed $/kT; using plan's $0.01–$0.05 band, midpoint $0.03/task × 3 = $0.09)

**Total: 8 tasks, 8 parallel groups (fully independent files — safe to run as one wave), ~55,800 tokens, ~$0.22**

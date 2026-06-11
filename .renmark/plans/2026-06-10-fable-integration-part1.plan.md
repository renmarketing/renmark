---
artifact_type: plan
schema_version: 1
created_at: 2026-06-10T19:40:00+00:00
source_sha: c0860c5
related_spec: PRD.md#REQ-2 (2026-06-10 amendment)
generator: fable
part: 1 of 2
dependency_refs: []
---

# fable-integration — Part 1: engine + tests

**Goal (feature-level, shared by both parts):** make `fable` (Claude Fable 5, model id
`claude-fable-5`) a first-class renmark executor tier above `opus`, per the human-approved
REQ-2 amendment: routed set Haiku / Codex / Sonnet / Opus / Fable; Fable is an escalation
target reserved for ideation, strategy, and adversarial audit/review — never mechanical or
bulk work; cost previews reflect its pricing ($10/$50 per MTok ⇒ $0.030/kT, 2× opus's 0.015).

**Dispatch fact:** Claude Code's Agent tool accepts `model: "fable"` as a subagent override.
renmark's dispatch already groups Agent-dispatched tasks via
`claude_agent.is_claude_executor()` and the orchestrate skill passes `model=task.executor`,
so adding `"fable"` to `CLAUDE_EXECUTORS` + the parser allowlist propagates end-to-end with
no new mapping layer.

**Out of scope (explicit):** `renmark/debug.py` intent routing stays opus-peaked (Fable is
never a default; debug is not an approved Fable role). `renmark/schemas.py`
`LIMITS_PROVIDERS` and `renmark/usage.py` provider loops stay `("claude", "codex")` — fable
bills under the `claude` provider. `renmark/sizing.py` classifies by complexity/files, not
executor names — no change.

Part 2 (`2026-06-10-fable-integration-part2.plan.md`) carries the prose/doc sync.

### Task 1: parser executor allowlist
- **mode:** B
- **target:** renmark/parser.py
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 1
- **est_tokens:** 250
- **est_cost_usd:** 0.001
- **verifier:** grep -q '"fable"' renmark/parser.py && python3 -m py_compile renmark/parser.py
- **serves:** REQ-2
- **spec:**
  Two-line edit, exact anchors. At line 222 the executor validation reads:
  `if executor not in ("haiku", "codex", "sonnet", "opus") and "/" not in executor:`
  — extend the tuple to `("haiku", "codex", "sonnet", "opus", "fable")`.
  At line 224 the error message reads:
  `f"executor must be one of haiku, codex, sonnet, opus, or a provider/model string, got {executor!r}"`
  — update to `... haiku, codex, sonnet, opus, fable, or a provider/model string ...`.
  No other changes. Do not reorder the existing tokens.

### Task 2: CLAUDE_EXECUTORS constant
- **mode:** B
- **target:** renmark/providers/claude_agent.py
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 1
- **est_tokens:** 150
- **est_cost_usd:** 0.001
- **verifier:** python3 -c "from renmark.providers.claude_agent import CLAUDE_EXECUTORS, is_claude_executor; assert is_claude_executor('fable') and CLAUDE_EXECUTORS[-1]=='fable'"
- **serves:** REQ-2
- **spec:**
  At line 24: `CLAUDE_EXECUTORS = ("haiku", "sonnet", "opus")` → append `"fable"` last
  (capability order, lowest→highest): `("haiku", "sonnet", "opus", "fable")`.
  At line 33 the `AgentDispatch.model` field comment says `# "opus" or "sonnet" (the Agent
  tool's model param)` — update to `# "haiku", "sonnet", "opus", or "fable" (the Agent
  tool's model param)`. Nothing else.

### Task 3: plan_lint heavy-read tier set
- **mode:** B
- **target:** renmark/plan_lint.py
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 1
- **est_tokens:** 120
- **est_cost_usd:** 0.001
- **verifier:** python3 -c "from renmark.plan_lint import _HEAVY_READ_BLOCK_EXECUTORS as H; assert 'fable' in H and 'sonnet' in H and 'opus' in H"
- **serves:** REQ-2
- **spec:**
  At line 73: `_HEAVY_READ_BLOCK_EXECUTORS = frozenset({"sonnet", "opus"})` →
  `frozenset({"sonnet", "opus", "fable"})`. Fable is the most expensive tier, so the G5
  heavy-read BLOCK must cover it. One line; no other changes.

### Task 4: roadmap cost table
- **mode:** B
- **target:** renmark/roadmap.py
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 1
- **est_tokens:** 120
- **est_cost_usd:** 0.001
- **verifier:** python3 -c "from renmark.roadmap import COST_PER_KT; assert abs(COST_PER_KT['fable']-0.030)<1e-9"
- **serves:** REQ-2
- **spec:**
  In the `COST_PER_KT` dict (lines 28–34) add the row `"fable": 0.030,` directly after the
  `"opus": 0.015,` row. Rationale (add as a trailing comment on the fable line):
  `# 2x opus — Fable 5 lists at $10/$50 per MTok vs Opus's $5/$25`. Keep the legacy
  `"nim": 0.0` row untouched.

### Task 5: loop blend-rate comment
- **mode:** B
- **target:** renmark/loop.py
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 1
- **est_tokens:** 100
- **est_cost_usd:** 0.001
- **verifier:** grep -q 'fable' renmark/loop.py && python3 -m py_compile renmark/loop.py
- **serves:** REQ-2
- **spec:**
  Comment-only doc-truth fix. The comment at ~line 56 enumerates per-model rates:
  `#: (haiku 0.0001 · sonnet 0.003 · opus 0.015 · codex 0.05 per 1k)` — extend to
  `#: (haiku 0.0001 · sonnet 0.003 · opus 0.015 · fable 0.030 · codex 0.05 per 1k)`.
  Do NOT change the blended constant value itself.

### Task 6: parser acceptance test
- **mode:** B
- **target:** tests/test_parser.py
- **complexity:** medium
- **executor:** codex
- **parallel_group:** 2
- **est_tokens:** 400
- **est_cost_usd:** 0.02
- **verifier:** .venv/bin/python3 -m pytest tests/test_parser.py -q --tb=line
- **serves:** REQ-2
- **spec:**
  In `test_executor_claude_models_accepted` (line 206) the loop iterates
  `for ex in ("haiku", "sonnet", "opus"):` — add `"fable"` to the tuple. Also add a small
  dedicated test `test_executor_fable_accepted_and_unknown_rejected` asserting (a) a plan
  task with `executor: fable` parses cleanly, and (b) an unknown executor like `frontier`
  still raises PlanError mentioning the allowlist. Follow the existing test fixtures/style
  in this file.

### Task 7: dispatch grouping test
- **mode:** B
- **target:** tests/test_dispatch.py
- **complexity:** medium
- **executor:** codex
- **parallel_group:** 2
- **est_tokens:** 700
- **est_cost_usd:** 0.03
- **verifier:** .venv/bin/python3 -m pytest tests/test_dispatch.py -q --tb=line
- **serves:** REQ-2
- **spec:**
  Add a test pinning that a task with `executor="fable"` is grouped into the Claude/Agent
  dispatch path, not the codex subprocess path: build a wave containing
  `_task(..., executor="fable", ...)` alongside a codex task (mirror the existing fixture
  pattern at line 18 / line 96) and assert `claude_agent.is_claude_executor("fable")` is
  True and the wave-partition logic puts the fable task in `claude_tasks`. Use whatever
  existing seam test_dispatch.py already uses for this partition — do not invent new
  dispatch APIs.

### Task 8: plan_lint fable tests
- **mode:** B
- **target:** tests/test_plan_lint.py
- **complexity:** medium
- **executor:** codex
- **parallel_group:** 2
- **est_tokens:** 700
- **est_cost_usd:** 0.03
- **verifier:** .venv/bin/python3 -m pytest tests/test_plan_lint.py -q --tb=line
- **serves:** REQ-2
- **spec:**
  Two additions, mirroring the existing `test_heavy_read_sonnet_block` pattern (line 293):
  (a) `test_heavy_read_fable_block` — a fable-executor task whose spec instructs reading a
  heavy context file must BLOCK exactly like sonnet/opus; (b) `test_executor_fable_lints_clean`
  — a minimal well-formed plan whose task uses `executor: fable` passes lint with no
  executor-related finding. Reuse the file's task-template helper (line 40).

### Task 9: roadmap cost test
- **mode:** B
- **target:** tests/test_roadmap.py
- **complexity:** medium
- **executor:** codex
- **parallel_group:** 2
- **est_tokens:** 300
- **est_cost_usd:** 0.02
- **verifier:** .venv/bin/python3 -m pytest tests/test_roadmap.py -q --tb=line
- **serves:** REQ-2
- **spec:**
  Add `test_cost_per_kt_has_fable_tier` pinning `COST_PER_KT["fable"] == 0.030` and that it
  is strictly greater than `COST_PER_KT["opus"]` (tier ordering guard). Follow existing
  test style in this file.

## Cost preview — Part 1

| # | Task | Executor | est_tokens | est cost |
|---|---|---|---|---|
| 1 | parser allowlist | haiku | 250 | $0.001 |
| 2 | CLAUDE_EXECUTORS | haiku | 150 | $0.001 |
| 3 | plan_lint tier set | haiku | 120 | $0.001 |
| 4 | roadmap cost table | haiku | 120 | $0.001 |
| 5 | loop comment | haiku | 100 | $0.001 |
| 6 | parser test | codex | 400 | $0.02 |
| 7 | dispatch test | codex | 700 | $0.03 |
| 8 | plan_lint tests | codex | 700 | $0.03 |
| 9 | roadmap test | codex | 300 | $0.02 |

Haiku/sonnet costs include the ~10k-token Agent overhead per task (honest accounting).
**Part 1 total: ~$0.11 · ~53k tokens · 9 tasks (wave 1: 5 parallel, wave 2: 4 parallel)**

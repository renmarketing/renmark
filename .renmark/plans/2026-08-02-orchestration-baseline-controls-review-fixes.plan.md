# Orchestration baseline controls — codereview fix pass

Fixes the 2 Minor findings from `.renmark/reviews/2026-08-02-6c92037.review.md` (codex full review of
`main...feature/orchestration-baseline-controls`) and clarifies the "under-built" spec-compliance note
about `milestone_context_checkpoint`'s currently-dormant wiring. No other behavior changes.

### Task 1: fix false-positive architecture WARN
- **mode:** B
- **target:** renmark/plan_lint.py
- **complexity:** medium
- **executor:** sonnet
- **role:** code-implementer
- **parallel_group:** 1
- **est_tokens:** 500
- **est_cost_usd:** 0.0315
- **verifier:** python3 -m py_compile renmark/plan_lint.py
- **serves:** REQ-30
- **spec:**
  In `escalation_reason_for` (~line 391), `kind = "architecture"` is currently derived only when
  `task.complexity == "hard"` AND an architecture-marker substring is present in the spec text —
  meaning a legitimate `opus` architecture/design-fork task at `medium` or `simple` complexity gets a
  false-positive WARN even though `cost.requires_escalation()` would accept it on `kind` alone
  (codereview finding, `.renmark/reviews/2026-08-02-6c92037.review.md`). Fix: drop the
  `and task.complexity == "hard"` gate from that `elif` branch — derive `kind="architecture"` purely
  from the architecture-marker substring check, independent of complexity. `requires_escalation`
  already weighs `complexity` and `kind` together; let it decide justification, don't pre-filter on
  complexity before calling it. Do not change the `role == "reviewer"` → `kind="adversarial-review"`
  branch, or any other logic in this function.

### Task 2: fix zero-token undercounting in honesty metrics
- **mode:** B
- **target:** renmark/analytics.py
- **complexity:** medium
- **executor:** sonnet
- **role:** code-implementer
- **parallel_group:** 2
- **est_tokens:** 500
- **est_cost_usd:** 0.0315
- **verifier:** python3 -m py_compile renmark/analytics.py
- **serves:** REQ-30
- **spec:**
  In `_agg_tasks` (~line 512), `measured_tokens_total` and `unmeasured_task_count` are currently only
  updated inside the same `if tokens:` truthy branch that drives `tokens_by_executor`/`tokens_by_model`/
  `tokens_by_provider` — so a real `measured=True` row with `tokens == 0` is never counted as measured,
  and an unmeasured row with `tokens == 0` is never flagged as unmeasured either (codereview finding).
  Fix: classify every row's measured status **independently** of whether `tokens` is truthy — read
  `r.get("measured")` unconditionally per row (outside/alongside the existing `if tokens:` block) and
  increment `measured_tokens_total` by whatever `tokens` value is (including 0) when `measured` is
  truthy, else increment `unmeasured_task_count`. Do **not** change the existing `tokens_by_executor`/
  `tokens_by_model`/`tokens_by_provider` aggregation — that stays gated on nonzero `tokens` for its own
  unrelated reason (avoiding zero-token noise in per-executor totals). Only the two new counters change.

### Task 3: document milestone_context_checkpoint's dormant-hook status
- **mode:** B
- **target:** .renmark/memory/orchestration-baseline.md
- **complexity:** simple
- **executor:** haiku
- **role:** docs-editor
- **parallel_group:** 3
- **est_tokens:** 250
- **est_cost_usd:** 0.0101
- **verifier:** grep -q "dormant" .renmark/memory/orchestration-baseline.md
- **serves:** REQ-30
- **spec:**
  Near the existing "## Audit — 2026-08-02" section, add a short note (a few sentences, not a new
  section header): `milestone_context_checkpoint` (renmark/lifecycle.py) is wired at the real Agency
  milestone boundary (renmark/agency.py's `approve_milestone_for_orchestrator`), but that call site
  currently always passes `estimated_tokens=None` — there is no reliable Python-side context-size
  signal to feed it yet (per this audit's findings). This makes it a **dormant hook today, not an
  active compaction trigger**: the manual `/compact` recommendation can be produced by the function
  when given a real signal, but nothing supplies one yet. Closing this gap requires either a
  host-exposed context-size API or a self-reported estimate from the calling agent — neither exists
  yet. Flagged by codex codereview (`.renmark/reviews/2026-08-02-6c92037.review.md`) as spec
  "under-built" for exactly this reason — this note makes the limitation explicit rather than implying
  the mechanism is fully active.

## Cost preview

| Executor | Count | Tokens (incl. agent overhead) | $/kT | Cost |
|---|---:|---:|---:|---:|
| sonnet | 2 | (500+500) + 2×10000 = 21000 | $0.003 | $0.063 |
| haiku | 1 | 250 + 10000 = 10250 | $0.0001 | $0.001 |

**Total: 3 tasks, 3 parallel groups (fully independent files), ~31,250 tokens, ~$0.064**

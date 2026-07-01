<!--
artifact_type: plan
schema_version: 1
created_at: 2026-07-01T00:00:00Z
source_sha: 4477ee3
related_plan: null
generator: plan
stale_after: null
dependency_refs:
  - .renmark/specs/2026-07-01-p8-behavioral-skill-testing.spec.md
-->

# Plan — P8-v2: behavioral skill testing (tests-vs-evals tier split)

Redesign of the reviewed v1 P8 build per the v2 spec. Two honestly-labelled tiers:
the **deterministic tier** runs renmark's *real* behavior-shaping functions
(`lifecycle.next_steps`, `skill_preamble`, `plan_lint`) on live inputs and asserts
their genuine current output (recomputed every run → fixes Major 1; no snapshot →
fixes bootstrap; CI-safe), and the **eval/judge tier** adjudicates a live model
trajectory, reachable only under `--accept`/`--judge` (out of CI).

**Binding constraints (from CHANGELOG guards, reconciled):** the deterministic
tier is **intentionally no longer snapshot-driven** for its assertions — that
golden-echo was the fatal Major 1 (the v2 CHANGELOG entry supersedes the v1
"snapshot-driven" guard). The following guards are PRESERVED and must not break:
default `--behavior` stays **network-free / token-free** (never constructs a live
runner); the judge/eval tier **never auto-spends** — capture only under `--accept`,
judge only under `--judge`; malformed judge payloads stay `unvalidated`, never a
silent pass. Docs must keep the honest split explicit (green `--behavior` ≠ "skill
works"). `renmark/judge.py` reviewed clean in v1 — do not redesign it.

---

### Task 1: behavior.py — deterministic tier rewrite + eval-tier gating
- **mode:** B
- **target:** renmark/behavior.py
- **complexity:** hard
- **executor:** opus
- **parallel_group:** 1
- **est_tokens:** 2500
- **est_cost_usd:** 0.19
- **verifier:** ruff check --quiet renmark/behavior.py && ! grep -q _current_transcript renmark/behavior.py
- **serves:** new
- **spec:**
  Rewrite the behavioral harness for the v2 two-tier model. Remove the
  golden-echo path entirely: delete `_current_transcript`, the replay-against-
  stored-golden logic, and the transcript-snapshot dependency of the
  DETERMINISTIC tier (Major 1).

  **New `Case` shape** (loaded from `tests/behavioral/<skill>.behavior.json`):
  `skill: str`, `prompt: str`, `deterministic: {call: str, assertions: list[str]}`,
  `eval: {contract: str, golden_ref: str}`. Keep `BehaviorConfigError` on malformed
  cases. Preserve the existing assertion mini-format
  (`contains:`/`not_contains:`/`matches:`/`line_ends:`/`min_lines:`/plain-substring;
  an unknown op-shaped token is a FAIL, not a silent pass).

  **Deterministic tier (default, CI-safe, the ONLY thing `run()` does without
  flags):** for each case, resolve `deterministic.call` to a real renmark function
  via a small explicit allow-list dispatch table — at minimum
  `lifecycle.next_steps`, `lifecycle.skill_preamble`, and a `plan_lint` read-only
  check (`_check_transcript_leak` / `lint_plan`). Invoke it on live inputs derived
  from the case (`repo`, `skill`), render its output to text, and run the case's
  assertions against that GENUINE CURRENT output. No snapshot is read; nothing
  ERRORs on a fresh checkout. Unknown `call` → FAIL with a clear message. Return
  the existing `Result` shape (PASS/FAIL, per-assertion detail).

  **Eval/judge tier (gated):** keep `capture()` and `_escalate_to_judge()` but make
  them reachable only when an explicit live `subagent_runner` is passed. Add a
  runner-factory adapter that turns `renmark.providers.claude_agent` into the
  `SubagentRunner = Callable[[str], str]` shape both this module and `judge.py`
  expect; the factory is invoked ONLY by capture/escalate, never by the default
  deterministic path. `capture()` records the eval `golden_ref` transcript under
  `snapshots/`. On a deterministic FAIL, `run(...)` surfaces the OFFER line and
  escalates to `judge.judge_behavior` ONLY when `judge=True`. `run()` signature
  keeps `judge=False`, `on_fail_offer=True`, `repo=None`, `subagent_runner=None`.

  Keep `ACCEPT_FIRST_HINT` for the eval-tier missing-golden case ("run --accept
  first") — but it now applies ONLY to the judge path, never to the deterministic
  tier. Update the module docstring to state the honest split. Preserve
  `__all__` exports plus any newly public names.

### Task 2: CLI — --behavior (deterministic only) / --accept / --judge wiring
- **mode:** B
- **target:** renmark/cli/_engine.py
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 2
- **est_tokens:** 1200
- **est_cost_usd:** 0.03
- **verifier:** ruff check --quiet renmark/cli/_engine.py
- **serves:** new
- **spec:**
  Update the `--behavior` command path to the v2 tiers (depends on Task 1's
  behavior.py API). `renmark-execute --behavior` runs the **deterministic tier
  only** — it must NOT construct or pass a live subagent runner (guarantees zero
  token spend / no network in CI); exits non-zero on any FAIL/ERROR.
  `--behavior --accept` records eval-tier golden transcripts via the live runner
  factory from Task 1 (deliberate live step). `--behavior --judge` enables judge
  escalation on a deterministic FAIL; the CLI prints the OFFER line (est cost
  `JUDGE_EST_COST_USD`) on a deterministic FAIL and escalates ONLY when `--judge`
  is present — never auto-spends. Keep the existing guard that `--accept`/`--judge`
  require `--behavior`. Do not change unrelated CLI commands.

### Task 3: reference case — next-steps menu contract (v2 format)
- **mode:** B
- **target:** tests/behavioral/next_steps_menu.behavior.json
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 2
- **est_tokens:** 450
- **est_cost_usd:** 0.00
- **verifier:** python3 -m json.tool tests/behavioral/next_steps_menu.behavior.json | grep -q '"deterministic"' && python3 -m json.tool tests/behavioral/next_steps_menu.behavior.json | grep -q '"eval"'
- **serves:** new
- **spec:**
  Rewrite this reference case to the v2 two-block format. Structure:
  `{"skill": "roadmap", "prompt": "<a prompt exercising the next-steps menu
  contract>", "deterministic": {"call": "lifecycle.next_steps", "assertions":
  [...]}, "eval": {"contract": "<plain-language: the agent actually ENDED its real
  turn with a recommended-first, terminal next-steps menu>", "golden_ref":
  "snapshots/next_steps_menu.golden"}}`. Deterministic assertions must restore full
  contract force over the rendered `next_steps(repo,"roadmap")` output: assert
  `(Recommended)` label present (`contains:(Recommended)`), recommended-first
  ordering, and that the terminal Finish/Nothing fallback is present (menu is
  terminal). Use only the mini-format ops. Do NOT weaken to a bare `min_lines`.

### Task 4: reference case — roadmap read-only contract (v2 format)
- **mode:** B
- **target:** tests/behavioral/roadmap.behavior.json
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 2
- **est_tokens:** 450
- **est_cost_usd:** 0.00
- **verifier:** python3 -m json.tool tests/behavioral/roadmap.behavior.json | grep -q '"deterministic"' && python3 -m json.tool tests/behavioral/roadmap.behavior.json | grep -q '"eval"'
- **serves:** new
- **spec:**
  Rewrite this reference case to the v2 two-block format. Deterministic block:
  `{"call": "plan_lint", ...}` asserting the read-only contract over generated
  roadmap output — `not_contains:Agent(`, `not_contains:codex exec`,
  `not_contains:renmark-execute --task`, plus a positive marker that the read-only
  `plan_lint` verdict holds. Eval block: `contract` = "the agent stayed read-only
  across the whole live session — no writes or commits attempted anywhere in the
  trajectory", `golden_ref`: "snapshots/roadmap.golden". Restore full contract
  force — do not drop the `not_contains:` dispatch-token assertions.

### Task 5: rewrite tests/test_behavior.py for the v2 tiers
- **mode:** B
- **target:** tests/test_behavior.py
- **complexity:** medium
- **executor:** codex
- **parallel_group:** 3
- **est_tokens:** 1600
- **est_cost_usd:** 0.05
- **verifier:** python3 -m pytest tests/test_behavior.py -q
- **serves:** new
- **spec:**
  Rewrite to cover the v2 behavior.py contract (depends on Tasks 1–2). Cover:
  (a) deterministic tier runs real functions and PASSes on a correct scaffolding
  output; (b) a NEGATIVE test — a case whose assertions don't match the real
  function output FAILs (proves the tier isn't self-satisfying); (c) an unknown
  `deterministic.call` → FAIL with a clear message; (d) the default `run()` path
  never constructs/calls a live runner (assert a would-raise runner is never
  invoked when `judge=False`); (e) judge escalation invoked ONLY when `judge=True`
  and only on a deterministic FAIL; (f) eval-tier missing `golden_ref` under judge
  → ERROR ("run --accept first"), never a silent pass; (g) the assertion
  mini-format incl. unknown-op → FAIL. Keep every test deterministic and free
  (mock any runner). No live capture, no network.

### Task 6: docs — honest two-tier framing in CLAUDE.md
- **mode:** B
- **target:** CLAUDE.md
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 2
- **est_tokens:** 400
- **est_cost_usd:** 0.00
- **verifier:** grep -qi "deterministic tier" CLAUDE.md && grep -qi "eval tier" CLAUDE.md && grep -q "not \"the skill works\"" CLAUDE.md
- **serves:** new
- **spec:**
  Update the "### Behavioral test tier (P8)" block to the v2 honest split. State
  exactly: `renmark-execute --behavior` runs the **deterministic tier** — a
  CI-safe scaffolding/regression guard that asserts renmark's real
  behavior-shaping functions; it is NOT proof the skill works (add the literal
  phrase: green `--behavior` is not "the skill works"). `--behavior --accept`
  records eval-tier golden transcripts (deliberate live step). `--behavior
  --judge` runs the **eval tier** — the load-bearing behavioral proof via
  LLM-as-judge over a real model trajectory (~$0.15, opt-in, never auto-spends,
  out of CI). Keep it concise (≈6–8 lines), matching the surrounding style.

### Task 7: docs — mirror the two-tier framing in AGENTS.md
- **mode:** B
- **target:** AGENTS.md
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 2
- **est_tokens:** 400
- **est_cost_usd:** 0.00
- **verifier:** grep -qi "deterministic tier" AGENTS.md && grep -qi "eval tier" AGENTS.md && grep -q "not \"the skill works\"" AGENTS.md
- **serves:** new
- **spec:**
  Mirror Task 6's exact "### Behavioral test tier (P8)" block into AGENTS.md
  (CLAUDE.md and AGENTS.md are intentionally kept in sync). Use the identical
  wording so the two files do not drift.

---

## Cost preview

| Task | Executor | Est. tokens (incl. overhead) | Est. cost |
|---|---|---|---|
| T1 behavior.py rewrite | opus | 12,500 | $0.19 |
| T2 CLI wiring | sonnet | 11,200 | $0.03 |
| T3 next-steps case | haiku | 10,450 | $0.00 |
| T4 roadmap case | haiku | 10,450 | $0.00 |
| T5 test_behavior.py | codex | 1,600 | $0.05 |
| T6 CLAUDE.md | haiku | 10,400 | $0.00 |
| T7 AGENTS.md | haiku | 10,400 | $0.00 |

**Total: ~$0.28** (7 tasks, 3 waves; executors: haiku×4, sonnet×1, codex×1, opus×1)

<!--
artifact_type: plan
schema_version: 1
created_at: 2026-07-01T00:00:00Z
source_sha: b286cc0
related_plan: null
generator: plan
stale_after: null
dependency_refs:
  - .renmark/specs/2026-07-01-p8-behavioral-skill-testing.spec.md
-->

# Plan — P8: Behavioral skill testing + LLM-as-judge eval tier

**Context.** Add a behavioral test tier to renmark that proves a skill changes
agent behavior (not just that it lints). Default tier replays recorded golden
transcripts and diffs them deterministically in CI (reusing `renmark/shadow.py`);
an opt-in LLM-as-judge tier (`renmark/judge.py`) adjudicates on deterministic
failure, gated behind explicit opt-in. MVP seeds 2 reference behavioral cases.
Spec: `.renmark/specs/2026-07-01-p8-behavioral-skill-testing.spec.md`. Ships in
v0.23.0 alongside the P7 lint (merge-only, branch `worktree-p7-skill-templates`).

Golden/baseline snapshots for the `.behavior.json` reference cases are captured
via `renmark-execute --behavior --accept` (a deliberate live step, run once
post-build) — that capture is a runtime action, not a plan task. The harness's
own unit tests use inline fixtures + a mocked `subagent_runner`, so they pass in
CI with zero live capture.

---

### Task 1: LLM-as-judge tier module
- **mode:** A
- **target:** renmark/judge.py
- **complexity:** hard
- **executor:** opus
- **parallel_group:** 1
- **est_tokens:** 1200
- **est_cost_usd:** 0.17
- **verifier:** python3 -m py_compile renmark/judge.py
- **serves:** new
- **spec:**
  Implement the escalation-only LLM-as-judge tier. Public entry
  `judge_behavior(repo, *, skill, prompt, baseline, golden, actual, contract,
  subagent_runner=None) -> Verdict`. `Verdict` is a dataclass carrying
  `outcome` (`pass|fail`), `confidence` (`low|medium|high`),
  `validation_status`, and `rationale` (str). It compares the with-skill
  behavior against the baseline given the skill's contract and returns a
  structured semantic verdict. It MUST route its live model call through
  `renmark.dispatch`'s injectable `subagent_runner` (accept a `subagent_runner`
  param defaulting to the real one) so tests can inject a mock. Parse the model
  response defensively: on parse failure/timeout return
  `validation_status="unvalidated"`, never a silent `pass`. Expose the
  approx cost (~$0.15) as a module constant `JUDGE_EST_COST_USD`. Do NOT invoke
  the judge from import side effects; it runs only when called. No CLI here.

### Task 2: behavioral harness module
- **mode:** A
- **target:** renmark/behavior.py
- **complexity:** hard
- **executor:** opus
- **parallel_group:** 2
- **est_tokens:** 1800
- **est_cost_usd:** 0.18
- **verifier:** python3 -m py_compile renmark/behavior.py
- **serves:** new
- **spec:**
  Implement the behavioral test harness, building on the `renmark/shadow.py`
  baseline replay+diff pattern (`run_subsystem`/`accept_subsystem`). Load
  declarative cases from `tests/behavioral/*.behavior.json` (schema:
  `{skill, prompt, assertions[], baseline_ref, golden_ref}`). Provide:
  (1) `load_cases(dir) -> list[Case]`;
  (2) `replay(case) -> Result` — deterministic: reads the recorded golden +
  baseline snapshots, diffs the replayed transcript against golden, and asserts
  the with-skill transcript both matches golden AND differs meaningfully from
  baseline (the skill had an effect). Pure I/O over recorded snapshots — NO
  network, NO tokens. If a snapshot is missing, return an ERROR result (message
  "run --accept first"), never a pass;
  (3) `capture(case, subagent_runner)` — the live `--accept` path that records
  baseline+golden via the injectable runner;
  (4) `run(dir, *, judge=False, on_fail_offer=True) -> list[Result]` — runs
  replay over all cases; on a deterministic FAIL, if `judge` is True call
  `renmark.judge.judge_behavior` (lazy import to avoid cycles), else if
  `on_fail_offer` mark the result as `judge_offered=True` so the CLI can prompt
  for opt-in. Never auto-invoke the judge unless `judge=True`. Results expose
  `completion_state`, `confidence`, `validation_status` per the artifact
  contract. Import judge lazily inside `run`, not at module top.

### Task 3: CLI --behavior wiring
- **mode:** B
- **target:** renmark/cli/_engine.py
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 3
- **est_tokens:** 700
- **est_cost_usd:** 0.03
- **verifier:** python3 -m py_compile renmark/cli/_engine.py && bin/renmark-execute --help 2>&1 | grep -q -- --behavior
- **spec:**
  Add a `--behavior` flag to the `renmark-execute` argparser (mirror the style
  of the existing `--audit`/`--roadmap` subcommand flags). `--behavior` runs
  `renmark.behavior.run(repo, judge=False)` over `tests/behavioral/` and prints
  a bounded PASS/FAIL summary (per-case one-liner + totals) — deterministic, no
  spend. Add companion flags: `--accept` (with `--behavior`) → runs the live
  capture path; `--judge` (with `--behavior`) → enables the judge escalation on
  failure. When a deterministic case FAILS and neither `--judge` nor headless,
  print the judge OFFER line including the ~$0.15 cost note from
  `renmark.judge.JUDGE_EST_COST_USD` and instruct the user to re-run with
  `--judge` — do NOT auto-spend. Follow existing CLI error/exit-code
  conventions. Do not change unrelated flags.

### Task 4: roadmap reference behavioral case
- **mode:** A
- **target:** tests/behavioral/roadmap.behavior.json
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 4
- **est_tokens:** 300
- **est_cost_usd:** 0.00
- **verifier:** python3 -m json.tool tests/behavioral/roadmap.behavior.json | grep -q '"golden_ref"'
- **serves:** new
- **spec:**
  Create the reference behavioral case for the `roadmap` skill asserting its
  read-only / zero-LLM contract. JSON object with keys: `skill`: "roadmap";
  `prompt`: a representative invocation of `/renmark:roadmap` (status mode);
  `assertions`: a list of deterministic checks over the transcript — e.g. "makes
  no LLM/subagent dispatch call in status mode", "writes only
  .renmark/memory/roadmap.md", "does not modify git history"; `baseline_ref`:
  "tests/behavioral/_snapshots/roadmap.baseline.json"; `golden_ref`:
  "tests/behavioral/_snapshots/roadmap.golden.json". Snapshots themselves are
  produced later via `--accept`; this task writes only the case definition.

### Task 5: next-steps-menu reference behavioral case
- **mode:** A
- **target:** tests/behavioral/next_steps_menu.behavior.json
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 4
- **est_tokens:** 300
- **est_cost_usd:** 0.00
- **verifier:** python3 -m json.tool tests/behavioral/next_steps_menu.behavior.json | grep -q '"golden_ref"'
- **serves:** new
- **spec:**
  Create the reference behavioral case for the cross-cutting "every skill ends
  its turn with an AskUserQuestion next-steps menu (recommended-first)" contract.
  JSON object: `skill`: pick a representative skill that ends with the menu (e.g.
  "roadmap" or "help") — set `skill` accordingly; `prompt`: a representative
  invocation; `assertions`: deterministic checks — e.g. "final turn issues an
  AskUserQuestion next-steps menu", "first option is labeled (Recommended)";
  `baseline_ref`: "tests/behavioral/_snapshots/next_steps_menu.baseline.json";
  `golden_ref`: "tests/behavioral/_snapshots/next_steps_menu.golden.json".
  Definition only; snapshots come from `--accept`.

### Task 6: harness unit tests
- **mode:** A
- **target:** tests/test_behavior.py
- **complexity:** medium
- **executor:** codex
- **parallel_group:** 5
- **est_tokens:** 1200
- **est_cost_usd:** 0.04
- **verifier:** pytest -q tests/test_behavior.py
- **serves:** new
- **spec:**
  Unit-test `renmark/behavior.py` with a mocked `subagent_runner` and inline
  fixture snapshots (write small temp snapshot files in a tmp_path — do NOT
  require live capture). Cover: `load_cases` parses a `.behavior.json`;
  `replay` PASSes when replayed transcript matches golden AND differs from
  baseline; `replay` FAILs when it matches baseline (skill had no effect);
  `replay` returns ERROR (not pass) when a snapshot file is missing; `run` does
  NOT invoke the judge when `judge=False` (assert the lazy judge import / call
  is not made — patch `renmark.judge.judge_behavior` and assert not called);
  `run` DOES call it when `judge=True` on a failing case. All deterministic,
  no network.

### Task 7: judge unit tests
- **mode:** A
- **target:** tests/test_judge.py
- **complexity:** medium
- **executor:** codex
- **parallel_group:** 5
- **est_tokens:** 1000
- **est_cost_usd:** 0.03
- **verifier:** pytest -q tests/test_judge.py
- **serves:** new
- **spec:**
  Unit-test `renmark/judge.py` with a mocked `subagent_runner`. Cover:
  `judge_behavior` returns a well-formed `Verdict` (`outcome`, `confidence`,
  `validation_status`, `rationale`) when the mock returns a valid response;
  parse failure / malformed response → `validation_status="unvalidated"` and
  NOT a silent `pass`; `JUDGE_EST_COST_USD` constant exists and is a positive
  float; the judge makes no model call at import time. All deterministic, no
  network.

### Task 8: document the behavioral tier
- **mode:** B
- **target:** CLAUDE.md
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 6
- **est_tokens:** 600
- **est_cost_usd:** 0.03
- **verifier:** grep -qi "behavior" CLAUDE.md && grep -qi "behavior" AGENTS.md
- **serves:** new
- **spec:**
  Document the P8 behavioral test tier. Add a short subsection under the
  testing/dev-gates area describing: `renmark-execute --behavior` (deterministic
  replay, CI-safe, no spend), `--behavior --accept` (record goldens), and the
  opt-in `--judge` escalation (~$0.15, never auto-spends). **Mirror the exact
  same edit into AGENTS.md in this same task** (project rule: CLAUDE.md and
  AGENTS.md are kept in sync and edited in the same commit). Keep it under ~12
  lines total; do not restate the whole spec.

---

## Cost preview

| task | file | executor | est_tokens (+overhead) | est_cost |
|------|------|----------|-----------------------:|---------:|
| 1 | renmark/judge.py | opus | 11,200 | $0.17 |
| 2 | renmark/behavior.py | opus | 11,800 | $0.18 |
| 3 | renmark/cli/_engine.py | sonnet | 10,700 | $0.03 |
| 4 | tests/behavioral/roadmap.behavior.json | haiku | 10,300 | $0.00 |
| 5 | tests/behavioral/next_steps_menu.behavior.json | haiku | 10,300 | $0.00 |
| 6 | tests/test_behavior.py | codex | 1,200 | $0.04 |
| 7 | tests/test_judge.py | codex | 1,000 | $0.03 |
| 8 | CLAUDE.md (+AGENTS.md) | sonnet | 10,600 | $0.03 |

**Total: 8 tasks · 6 parallel groups · ~67,100 tokens (incl. ~10k Agent overhead/Claude task) · ~$0.48**

Executors: haiku×2, codex×2, sonnet×2, opus×2.

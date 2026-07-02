<!--
artifact_type: spec
schema_version: 1
created_at: 2026-07-02T00:00:00Z
source_sha: a2f97da
related_plan: .renmark/plans/2026-07-02-live-eval-runner.plan.md
generator: opus
stale_after:
dependency_refs:
  - renmark/behavior.py
  - renmark/judge.py
  - renmark/cli/_engine.py
  - renmark/providers/__init__.py
  - renmark/config.py
-->

# Spec — live-eval-runner (P8 eval tier execution bridge)

## Problem (root cause, one sentence)

The P8 behavioral **eval tier** cannot run because `renmark.behavior.build_subagent_runner`
unconditionally `raise LiveRunnerUnavailable` — a pure-Python `renmark-execute`
subprocess cannot issue a model call — so `--behavior --accept` (record goldens) and
`--behavior --judge` (LLM-as-judge escalation) always degrade to the deterministic tier.

## What exists today (verified against sha a2f97da)

- `renmark/behavior.py:565` — `build_subagent_runner(repo, model)` raises `LiveRunnerUnavailable`.
- `renmark/behavior.py:588` — `capture(case, subagent_runner)` records a golden by feeding a
  skill-enabled prompt through the injected `str->str` runner; `_write_snapshot`
  (`behavior.py:330`) already `mkdir(parents=True, exist_ok=True)` the snapshots dir.
- `renmark/behavior.py:606` — `_escalate_to_judge` threads the runner into
  `renmark.judge.judge_behavior(..., subagent_runner=runner)`.
- `renmark/cli/_engine.py:1070` — `_behavior_accept` calls `build_subagent_runner`, then
  `capture` per case; `_cmd_behavior --judge` (line 1082) calls `build_subagent_runner`,
  catches `LiveRunnerUnavailable`, degrades, else threads the runner into `behavior.run`.
- `renmark/providers/claude_agent.py` — prompt **composer** only (for orchestrate's
  opus/sonnet dispatch); it is NOT a `str->str` runner.
- `renmark/config.py` — env→config→default precedence helpers already exist
  (`is_headless` / `_env_headless`); the pattern to mirror.

**Key finding — no CLI edit needed.** Both `_behavior_accept` and `_cmd_behavior --judge`
already call `build_subagent_runner`, thread the runner through, and handle
`LiveRunnerUnavailable`. The *only* missing piece is `build_subagent_runner` returning a
real runner when explicitly configured. Wiring that one function lights up both CLI paths.

## Design decision (owner-approved 2026-07-02)

**Pluggable seam + subprocess runner now; agent-turn runner deferred to a seam only.**

1. A small `EvalRunner` seam (`Callable[[str], str]`, reusing the existing `SubagentRunner`
   type) lives in a new `renmark/providers/eval_runner.py`, so renmark is not locked into
   subprocess-only behavior.
2. The **shipped** implementation is a **subprocess-command** runner: given a configured
   shell command, return a closure that runs it with the prompt on **stdin** and returns
   **stdout** as the model response. This is the only mechanism realizable from the
   `renmark-execute` subprocess, and it mirrors how `providers/codex.py` already shells out.
3. **Default is unavailable.** With no command configured, `build_subagent_runner` continues
   to raise `LiveRunnerUnavailable` — preserving the current CI-safe degrade and guaranteeing
   **no accidental token spend**.
4. When configured (via `RENMARK_EVAL_RUNNER_CMD` env, or a `.renmark/` config key), the
   subprocess runner powers both `--behavior --accept` and `--behavior --judge`.
5. A host-injected **agent-turn** runner is **explicitly NOT built now** — only the seam is
   left so it can be added later without redesigning the eval tier.

## Scope boundary (hard — do NOT cross)

- Do **not** touch the deterministic tier (`behavior.run` default path, its dispatch table,
  or `deterministic`-block assertions). Zero-token CI behavior must be byte-identical.
- Do **not** change the dispatch-packet schema (`renmark/dispatch.py` `SubagentInput` /
  `to_dict` / `required_skills`). The runner *consumes* renmark's existing composed prompt;
  it does not alter how dispatch packets are built.
- Opt-in, out-of-CI, never auto-spends: unconfigured ⇒ `LiveRunnerUnavailable`.
- This is a **new feature** (behavioral-proof acceptance bridge), **not** a reopen of the
  closed P8-v2 release scope.

## Acceptance criteria

- AC-1: With no runner configured, `renmark-execute --behavior` is unchanged (deterministic,
  zero tokens); `--behavior --judge` degrades exactly as today; `--behavior --accept` reports
  unavailable and exits non-zero.
- AC-2: With `RENMARK_EVAL_RUNNER_CMD` set to a `str->str` command, `--behavior --accept`
  records `snapshots/<golden_ref>.json` per case, and `--behavior --judge` escalates FAILs
  through the live subprocess runner into `judge_behavior`.
- AC-3: Subprocess failures (non-zero exit, timeout) surface as an error, never a silent pass.
- AC-4: `build_subagent_runner` keeps its `(repo, model)` signature and `LiveRunnerUnavailable`
  contract; the seam allows a future agent runner with no eval-tier redesign.
- AC-5: The full existing suite (`pytest -q`) stays green, including the deterministic-tier
  behavior tests.

## Traceability

Serves the mission **behavioral-proof acceptance criterion** (AC5 / P8 eval tier), operationalizes
REQ-7 (fresh evidence for completion claims), and consumes REQ-20 dynamic-skill-loading
infrastructure (required-skill metadata carried in the composed prompt). Not P8-v2.

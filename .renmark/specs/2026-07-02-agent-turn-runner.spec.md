<!--
artifact_type: spec
schema_version: 1
created_at: 2026-07-02T00:00:00Z
source_sha: 9b9e9fe
related_plan: .renmark/plans/2026-07-02-agent-turn-runner.plan.md
generator: opus
dependency_refs:
  - renmark/behavior.py
  - renmark/judge.py
  - renmark/providers/eval_runner.py
  - renmark/skillmeta.py
  - renmark/lifecycle.py
-->

# Spec — agent-turn eval runner (`/renmark:eval`, in-session eval path)

## Problem (root cause, one sentence)

The v0.26.0 eval tier can run live evals only through an **external CLI** subprocess
(`RENMARK_EVAL_RUNNER_CMD`); there is no way to run the eval **inside the current agent
session** — using the session's own model, dynamic skill loading, and Agent-tool access —
which is the more faithful "does this skill change *this* agent's behavior" proof.

## What exists today (verified against sha 9b9e9fe)

- `renmark/providers/eval_runner.py` — `EvalRunner` seam + `build_subprocess_runner` +
  `resolve_eval_runner` (subprocess CLI path; shipped v0.26.0). **Untouched by this feature.**
- `renmark/behavior.py:596` — `capture(case, subagent_runner)` composes a skill-enabled
  prompt inline (lines 605–608) then writes the snapshot (609–611).
- `renmark/judge.py:258` — `judge_behavior(...)` builds the judge prompt via private
  `_build_prompt` and parses via private `_parse_response`.
- Skill registration touchpoints (lint/registry-sync enforced): `renmark/skillmeta.py`
  (`SKILLS` dict), `renmark/lifecycle.py` (`IMPLEMENTED_SKILLS`, `AUX_SKILLS`),
  `plugin/skills/<name>/SKILL.md`, `plugin/commands/<name>.md`.

## Design decision (owner-approved 2026-07-02)

**Agent-driven skill flow — the agent IS the runner.** A pure-Python `renmark-execute`
subprocess cannot issue a model call, so the in-session path is NOT a Python-constructed
`EvalRunner`. Instead a new **`/renmark:eval` skill** orchestrates, within the current agent
turn:

1. Load behavior case(s) (`behavior.load_cases`).
2. Compose the skill-enabled eval prompt (`behavior.compose_eval_prompt(case)`).
3. **The agent issues a real Agent tool call** with that prompt → the with-skill transcript
   (this is the in-session model turn; uses the session's model + dynamic skill loading).
4. Record the golden via `behavior.capture_from_transcript(case, transcript)`.
5. (optional `--judge`) compose the judge prompt (`judge.compose_judge_prompt(...)`), issue a
   second Agent call, parse with `judge.parse_judge_verdict(response)` → verdict.

renmark supplies the **composition + capture + parse entry points**; the model call is the
agent's, not Python's. This is why it lives as a skill, not a `build_agent_turn_runner`
callable — a callable would still need an in-process model call the subprocess can't make.

## Scope boundary (hard — do NOT cross)

- Do **not** change the subprocess runner (`eval_runner.py`), the **deterministic tier**
  (`behavior.run` and its dispatch/assertions), or the **dispatch-packet schema**
  (`renmark/dispatch.py`).
- Do **not** change dynamic skill loading, Conductor/Orchestrator mode, or Codex routing.
- The `behavior`/`judge` changes are **pure refactors + additive public wrappers** — `capture()`
  keeps identical behavior (delegates to the two extracted helpers); `judge_behavior()`
  keeps identical behavior (private helpers stay, new public wrappers call them).
- Opt-in / out-of-CI / no auto-spend: `/renmark:eval` is `disable-model-invocation: true`
  (manual invocation only); it is a skill (never in `pytest`); it spends tokens only when the
  user runs it.
- NOT a reopen of the closed P8-v2 scope; this is the deferred second injection path noted in
  the live-eval-runner spec.

## Acceptance criteria

- AC-1: `behavior.compose_eval_prompt(case)` and `behavior.capture_from_transcript(case, t)`
  exist and `capture()` is refactored to use them with byte-identical behavior (existing
  `tests/test_behavior.py` still green).
- AC-2: `judge.compose_judge_prompt(...)` and `judge.parse_judge_verdict(response)` exist as
  thin public wrappers over the private helpers; `judge_behavior()` behavior unchanged.
- AC-3: `plugin/skills/eval/SKILL.md` + `plugin/commands/eval.md` exist; the skill documents
  the agent-driven capture (+ optional judge) flow, context-hygiene (transcripts → snapshots
  on disk, bounded verdict to chat), and a hand-off menu; `disable-model-invocation: true`.
- AC-4: `eval` is registered in `skillmeta.SKILLS` (domain build, class 3 aux) and
  `lifecycle.IMPLEMENTED_SKILLS` + `AUX_SKILLS`; `python -m renmark.audit --quick` is clean
  (registry-sync + shim-thinness + description-drift all pass).
- AC-5: New tests cover the extracted/added Python entry points; full `pytest -q` stays green.

## Traceability

Serves the mission **behavioral-proof acceptance criterion** (the in-session evals path) and
REQ-7 (fresh evidence). Complements, does not replace, the v0.26.0 subprocess runner. Not P8-v2.

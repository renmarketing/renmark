<!--
artifact_type: plan
schema_version: 1
created_at: 2026-07-02T00:00:00Z
source_sha: 9b9e9fe
related_plan: .renmark/specs/2026-07-02-agent-turn-runner.spec.md
generator: opus
dependency_refs:
  - .renmark/specs/2026-07-02-agent-turn-runner.spec.md
  - renmark/behavior.py
  - renmark/judge.py
  - renmark/skillmeta.py
  - renmark/lifecycle.py
-->

# Plan — agent-turn eval runner (`/renmark:eval` in-session eval path)

**Context.** Add the deferred in-session eval path as a new **`/renmark:eval` skill** (the agent
IS the runner: compose prompt → agent issues a real Agent tool call → capture transcript →
existing capture/judge path). renmark supplies composition/capture/parse entry points via pure
refactors + additive public wrappers; the model call is the agent's. Keep the v0.26.0 subprocess
runner, the deterministic tier, dynamic loading, mode, Codex routing, and the dispatch schema
untouched. Opt-in (`disable-model-invocation: true`), out-of-CI, no auto-spend. NOT a P8-v2 reopen.
Spec: `.renmark/specs/2026-07-02-agent-turn-runner.spec.md`.

---

### Task 1: refactor behavior.py capture into reusable entry points
- **mode:** B
- **target:** renmark/behavior.py
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 1
- **est_tokens:** 500
- **est_cost_usd:** 0.03
- **verifier:** python -c "from renmark.behavior import compose_eval_prompt, capture_from_transcript; print('ok')" | tail -1
- **serves:** behavioral-proof / REQ-7
- **spec:**
  Extract two public helpers from `capture()` WITHOUT changing its behavior:
  `compose_eval_prompt(case: Case) -> str` (returns the exact skill-enabled prompt currently
  built inline at lines 605–608) and `capture_from_transcript(case: Case, transcript: str) -> str`
  (writes `snapshots/<golden_ref>.json` via `_write_snapshot(_snapshot_path(...))` and returns
  the transcript — lines 609–611). Rewrite `capture(case, subagent_runner)` to
  `return capture_from_transcript(case, subagent_runner(compose_eval_prompt(case)))`. Add both
  names to `__all__`. Do NOT touch `run`, `_escalate_to_judge`, the deterministic tier, or any
  other function. `tests/test_behavior.py` MUST stay green (run it to confirm).

### Task 2: add public judge prompt/parse wrappers
- **mode:** B
- **target:** renmark/judge.py
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 1
- **est_tokens:** 450
- **est_cost_usd:** 0.03
- **verifier:** python -c "from renmark.judge import compose_judge_prompt, parse_judge_verdict; print('ok')" | tail -1
- **spec:**
  Add two thin PUBLIC wrappers over the existing private helpers, changing no existing behavior:
  `compose_judge_prompt(*, skill, prompt, baseline, golden, actual, contract) -> str` delegating
  to `_build_prompt(...)`, and `parse_judge_verdict(response: str) -> Verdict` delegating to
  `_parse_response(...)`. These let the `/renmark:eval` skill drive the judge model call itself
  (agent turn) and parse the verdict. `judge_behavior` MUST keep calling the private helpers and
  behave identically. Add both new names to `__all__` if one exists. Do not alter `Verdict`,
  `_default_subagent_runner`, or the escalation contract.

### Task 3: register eval in the skill metadata registry
- **mode:** B
- **target:** renmark/skillmeta.py
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 1
- **est_tokens:** 200
- **est_cost_usd:** 0.00
- **verifier:** python -c "from renmark.skillmeta import SKILLS; assert 'eval' in SKILLS; print('ok')" | tail -1
- **spec:**
  Add an `"eval"` entry to the `SKILLS` dict in alphabetical position (between `debug` and
  `feature`), mirroring the `audit` entry's shape: `domain="build"`, `next_steps_class=3`
  (aux/terminal), `cites=("next-steps","handoff-menu")`, `has_handoff=True`,
  `disable_model_invocation=True`. Match the exact `SkillMeta(...)` field names used by
  sibling entries (inspect `audit`/`scan`). Change nothing else.

### Task 4: register eval in lifecycle skill sets
- **mode:** B
- **target:** renmark/lifecycle.py
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 1
- **est_tokens:** 250
- **est_cost_usd:** 0.00
- **verifier:** python -c "from renmark import lifecycle as l; assert 'eval' in l.IMPLEMENTED_SKILLS and 'eval' in l.AUX_SKILLS; print('ok')" | tail -1
- **spec:**
  Add `"eval",` to both the `IMPLEMENTED_SKILLS` frozenset and the `AUX_SKILLS` frozenset, each
  in alphabetical position (after `debug`). Do NOT add it to `PIPELINE_SKILLS` or `GATE_SKILLS`
  (eval is aux/terminal). Leave `PREAMBLE_TIER_BY_SKILL` and `AUX_LOCAL_ACTIONS` at defaults
  unless a value is needed (default full tier + resume-pipeline hand-off is fine). Change nothing
  else; keep alphabetical ordering intact.

### Task 5: command shim for /renmark:eval
- **mode:** A
- **target:** plugin/commands/eval.md
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 1
- **est_tokens:** 200
- **est_cost_usd:** 0.00
- **verifier:** test -f plugin/commands/eval.md && grep -q "skills/eval/SKILL.md" plugin/commands/eval.md && echo ok
- **spec:**
  Create the shim mirroring `plugin/commands/audit.md` EXACTLY in structure: frontmatter with a
  `description:` (1–2 sentences, sharing wording with the SKILL.md description in Task 6 to pass
  the description-drift check) and an `argument-hint:`; body = the literal
  `Read \`${CLAUDE_PLUGIN_ROOT}/skills/eval/SKILL.md\` and follow its instructions exactly. The user provided this input: $ARGUMENTS`
  plus the empty-args fallback line. Must contain the literal string `skills/eval/SKILL.md`
  (shim-thinness check). Keep it thin — no logic in the shim.

### Task 6: the /renmark:eval skill (agent-driven in-session eval flow)
- **mode:** A
- **target:** plugin/skills/eval/SKILL.md
- **complexity:** hard
- **executor:** opus
- **parallel_group:** 2
- **est_tokens:** 1400
- **est_cost_usd:** 0.21
- **verifier:** test -f plugin/skills/eval/SKILL.md && grep -q "^name: eval" plugin/skills/eval/SKILL.md && grep -q "disable-model-invocation: true" plugin/skills/eval/SKILL.md && echo ok
- **spec:**
  Author the skill. Frontmatter: `name: eval`; `description:` (trigger-style, sharing wording
  with the shim); `disable-model-invocation: true`. Body documents the AGENT-DRIVEN flow, citing
  the real APIs: (0) context check `lifecycle.skill_preamble(repo,'eval')`; (1) parse args —
  optional case/skill filter + `--judge`; (2) load cases via `behavior.load_cases("tests/behavioral")`;
  (3) per case: `prompt = behavior.compose_eval_prompt(case)`, then **the agent issues a real
  Agent tool call** with that prompt (in-session model turn, skill enabled) and captures the full
  response as `transcript`, then `behavior.capture_from_transcript(case, transcript)` records the
  golden; (4) if `--judge`: `judge.compose_judge_prompt(...)` → agent issues a second Agent call →
  `judge.parse_judge_verdict(response)` → verdict; (5) bounded ≤5-line verdict to chat, full
  transcripts/evidence to `snapshots/` + a `.renmark/reviews/*.eval.md` artifact (context hygiene —
  never paste transcripts into chat); (6) hand-off menu per `${CLAUDE_PLUGIN_ROOT}/skills/_shared/next-steps.md`
  (class 3 aux) + `handoff-menu.md`. State plainly: this is the IN-SESSION path (uses the session's
  model + dynamic skill loading); the subprocess CLI path (`--behavior --accept/--judge` with
  `RENMARK_EVAL_RUNNER_CMD`) is unchanged and remains the CI/headless option; the deterministic
  tier remains the always-safe default. Include a Boundaries section (no deterministic-tier change,
  opt-in, out-of-CI). Mirror the section/citation conventions of `audit/SKILL.md`.

### Task 7: tests for the new behavior + judge entry points
- **mode:** A
- **target:** tests/test_eval_agent_turn.py
- **complexity:** medium
- **executor:** codex
- **parallel_group:** 2
- **est_tokens:** 1200
- **est_cost_usd:** 0.04
- **verifier:** python -m pytest tests/test_eval_agent_turn.py -q | tail -3
- **spec:**
  Hermetic unit tests (tmp_path, no network, no model calls): (1) `compose_eval_prompt(case)`
  returns the skill-enabled prompt containing `[skill ENABLED: <skill>]` and the case prompt;
  (2) `capture_from_transcript(case, "TX")` writes `snapshots/<golden_ref>.json` and returns "TX",
  and `capture(case, lambda p: "TX")` produces the SAME snapshot (proves the refactor is
  behavior-preserving — feed a stub runner); (3) `compose_judge_prompt(...)` returns a non-empty
  prompt containing the contract text; (4) `parse_judge_verdict` on a valid JSON verdict returns a
  `Verdict` with the right `outcome`, and on garbage returns an unvalidated `fail` (never a silent
  pass). Reuse a `Case` fixture like the one in `tests/test_eval_runner.py`. Do NOT modify
  `tests/test_behavior.py`.

### Task 8: CHANGELOG entry + final registry/lint gate
- **mode:** B
- **target:** CHANGELOG.md
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 3
- **est_tokens:** 300
- **est_cost_usd:** 0.00
- **verifier:** python -m renmark.audit --quick >/dev/null 2>&1 && python -m pytest -q >/dev/null 2>&1 && echo audit+suite-ok
- **spec:**
  Prepend a CHANGELOG.md entry dated 2026-07-02 titled "agent-turn eval runner (/renmark:eval,
  in-session eval path)" with Request / Built / Verified / Do-not-change lines (summarize: new
  agent-driven /renmark:eval skill; behavior.compose_eval_prompt + capture_from_transcript refactor;
  judge.compose_judge_prompt + parse_judge_verdict wrappers; registry wiring; subprocess runner +
  deterministic tier untouched). This task's verifier is the FINAL GATE: it runs the full
  `renmark.audit --quick` (registry-sync/shim-thinness/description-drift must be clean now that all
  wiring is in) AND the full `pytest -q` suite — so it must run after every other task.

---

## Cost preview

| Task | File | Executor | Tokens (incl ~10k overhead) | Cost |
|---|---|---|---|---|
| 1 | renmark/behavior.py | sonnet | 10,500 | $0.032 |
| 2 | renmark/judge.py | sonnet | 10,450 | $0.031 |
| 3 | renmark/skillmeta.py | haiku | 10,200 | $0.001 |
| 4 | renmark/lifecycle.py | haiku | 10,250 | $0.001 |
| 5 | plugin/commands/eval.md | haiku | 10,200 | $0.001 |
| 6 | plugin/skills/eval/SKILL.md | opus | 11,400 | $0.171 |
| 7 | tests/test_eval_agent_turn.py | codex | 1,200 | $0.036 |
| 8 | CHANGELOG.md | haiku | 10,300 | $0.001 |

**Total: 8 tasks · ~74k tokens · ~$0.27** · executors: haiku×4, codex×1, sonnet×2, opus×1
Waves: group 1 (tasks 1–5, disjoint files) → group 2 (tasks 6,7) → group 3 (task 8, final audit+suite gate).

<!--
artifact_type: plan
schema_version: 1
created_at: 2026-07-02T00:00:00Z
source_sha: a2f97da
related_plan: .renmark/specs/2026-07-02-live-eval-runner.spec.md
generator: opus
stale_after:
dependency_refs:
  - .renmark/specs/2026-07-02-live-eval-runner.spec.md
  - renmark/behavior.py
  - renmark/config.py
  - renmark/cli/_engine.py
-->

# Plan — live-eval-runner (P8 eval-tier execution bridge)

**Context.** Wire the deferred P8 eval-tier live runner. `build_subagent_runner` currently
raises unconditionally, so `--behavior --accept/--judge` always degrade. We ship a
**subprocess-command** runner behind a small `EvalRunner` **seam** (`renmark/providers/eval_runner.py`),
gated on explicit config so the default stays **unavailable / CI-safe / no auto-spend**. The
existing CLI paths already thread the runner and handle `LiveRunnerUnavailable`, so **no CLI
edit is required** — lighting up `build_subagent_runner` lights up both paths. The
deterministic tier and the dispatch-packet schema are **not touched**. Agent-turn runner is a
seam only (not built now). Spec: `.renmark/specs/2026-07-02-live-eval-runner.spec.md`.

---

### Task 1: config accessor for the eval-runner command
- **mode:** B
- **target:** renmark/config.py
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 1
- **est_tokens:** 400
- **est_cost_usd:** 0.03
- **verifier:** python -c "from renmark import config; assert hasattr(config,'eval_runner_cmd'); print('ok')" | tail -1
- **serves:** behavioral-proof (AC5) / REQ-7
- **spec:**
  Add an `eval_runner_cmd(repo) -> str | None` accessor mirroring the existing
  `is_headless` / `_env_headless` env→config→default precedence in this file. Precedence:
  (1) env var `RENMARK_EVAL_RUNNER_CMD` if set and non-empty; (2) a `.renmark/` config key
  (e.g. `eval_runner_cmd`) via the existing `_read_raw`; (3) `None`. Add the env name as a
  module constant next to `_ENV_HEADLESS`. Also add `eval_runner_source(repo) -> str`
  (`"env" | "config" | "default"`) for parity with `headless_source`. Do NOT change any
  existing function. Keep it pure/read-only (no writes beyond an optional
  `set_eval_runner_cmd` if the file's pattern includes setters — match the local style;
  a setter is optional, the getter is required).

### Task 2: EvalRunner seam + subprocess-command runner
- **mode:** A
- **target:** renmark/providers/eval_runner.py
- **complexity:** hard
- **executor:** opus
- **parallel_group:** 2
- **est_tokens:** 1200
- **est_cost_usd:** 0.17
- **verifier:** python -c "from renmark.providers import eval_runner as e; r=e.build_subprocess_runner('cat'); assert r('hi')=='hi'; print('ok')" | tail -1
- **spec:**
  New module defining the pluggable eval-runner seam and the shipped subprocess impl.
  Reuse the `Callable[[str], str]` runner shape (alias `EvalRunner`). Provide:
  (a) `build_subprocess_runner(cmd: str, *, timeout: float = 120.0) -> EvalRunner` — returns
  a closure that runs `cmd` via `subprocess.run` with **`shell=False`** on
  **`shlex.split(cmd)`** (NO shell interpretation — the safer default for a
  command-execution surface; `claude -p` still works, complex shell needs a wrapper
  script), feeding the prompt on **stdin** (`input=prompt`, `text=True`,
  `capture_output=True`), returning `stdout`. Raise `EvalRunnerError` (define it here) on: an
  empty/blank `cmd` after split, `FileNotFoundError` (command not on PATH), non-zero exit
  (include truncated stderr), and `subprocess.TimeoutExpired`. Never return silently on
  failure. (b) `resolve_eval_runner(repo, model="sonnet") -> EvalRunner | None` — reads
  `renmark.config.eval_runner_cmd(repo)`; returns `build_subprocess_runner(cmd)` when
  configured, else `None`. Document the seam: an agent-turn runner can be injected later by
  adding another builder without changing callers. Do NOT import behavior.py (avoid cycles);
  import config lazily/at top as appropriate. Depends on Task 1.

### Task 3: rewire build_subagent_runner to the seam
- **mode:** B
- **target:** renmark/behavior.py
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 3
- **est_tokens:** 500
- **est_cost_usd:** 0.03
- **verifier:** env -u RENMARK_EVAL_RUNNER_CMD python -c "from renmark import behavior as b; from pathlib import Path;\ntry: b.build_subagent_runner(Path('.')); raise SystemExit('should-have-raised')\nexcept b.LiveRunnerUnavailable: print('unavailable-ok')" | tail -1
- **spec:**
  Rewire `build_subagent_runner(repo, model='sonnet')` to delegate to
  `renmark.providers.eval_runner.resolve_eval_runner(repo, model)` (lazy import to avoid
  cycles). If it returns a runner, return it; if it returns `None`, raise
  `LiveRunnerUnavailable` with the SAME message/contract as today. Keep the signature and the
  `LiveRunnerUnavailable` type unchanged (callers and `__all__` untouched). Do NOT modify
  `capture`, `run`, `_escalate_to_judge`, the deterministic dispatch table, or any
  deterministic-tier code. Update only the `build_subagent_runner` docstring to describe the
  new subprocess-backed, config-gated behavior. Depends on Task 2.

### Task 4: tests for the runner seam + delegation
- **mode:** A
- **target:** tests/test_eval_runner.py
- **complexity:** medium
- **executor:** codex
- **parallel_group:** 4
- **est_tokens:** 1400
- **est_cost_usd:** 0.04
- **verifier:** python -m pytest tests/test_eval_runner.py -q | tail -3
- **spec:**
  Cover the full seam (unit + delegation), using `monkeypatch` for env and a real trivial
  shell command for the subprocess path. Cases: (1) `eval_runner_cmd` precedence — env wins
  over config, config over default `None`; (2) `build_subprocess_runner('cat')('hello') ==
  'hello'` (stdin→stdout round-trip; confirm `shlex.split` + `shell=False`); (3) failure
  modes each raise `EvalRunnerError` — non-zero exit (`'sh -c "exit 3"'`), a
  missing/unknown command (`FileNotFoundError`), and an empty/blank `cmd`; (4)
  `resolve_eval_runner` returns `None` when
  unconfigured and a callable when `RENMARK_EVAL_RUNNER_CMD` is set; (5)
  `behavior.build_subagent_runner` raises `LiveRunnerUnavailable` when unconfigured and
  returns a working runner when configured (monkeypatch env, assert `capture` writes a
  snapshot using a stub command like `cat`). Keep tests hermetic (tmp_path repo, no network,
  clear the env var in setup/teardown). Do NOT modify tests/test_behavior.py. Depends on Task 3.

### Task 5: refresh the P8 behavioral-tier doc in CLAUDE.md
- **mode:** B
- **target:** CLAUDE.md
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 5
- **est_tokens:** 300
- **est_cost_usd:** 0.00
- **verifier:** grep -q "RENMARK_EVAL_RUNNER_CMD" CLAUDE.md
- **spec:**
  In the "Behavioral test tier (P8)" section, update the eval-tier lines: the eval/judge tier
  is no longer purely HOST-pending — when `RENMARK_EVAL_RUNNER_CMD` (or the `.renmark` config
  key) points at a `str->str` command, `--behavior --accept` records goldens and
  `--behavior --judge` runs the live judge; unset ⇒ unavailable, CI-safe, no auto-spend. Keep
  it to 2–3 lines; do not rewrite the deterministic-tier description. Preserve the existing
  "eval tier is opt-in, never auto-spends, out of CI" framing.

### Task 6: mirror the P8 doc change in AGENTS.md
- **mode:** B
- **target:** AGENTS.md
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 5
- **est_tokens:** 300
- **est_cost_usd:** 0.00
- **verifier:** grep -q "RENMARK_EVAL_RUNNER_CMD" AGENTS.md
- **spec:**
  Apply the identical eval-tier update made to CLAUDE.md (Task 5) to the mirrored section in
  AGENTS.md, per the repo's "mirror all rule changes in AGENTS.md" convention. Same 2–3 line
  scope; deterministic-tier text unchanged.

---

## Cost preview

| Task | File | Executor | Tokens (incl ~10k overhead) | Cost |
|---|---|---|---|---|
| 1 | renmark/config.py | sonnet | 10,400 | $0.031 |
| 2 | renmark/providers/eval_runner.py | opus | 11,200 | $0.168 |
| 3 | renmark/behavior.py | sonnet | 10,500 | $0.032 |
| 4 | tests/test_eval_runner.py | codex | 1,400 | $0.042 |
| 5 | CLAUDE.md | haiku | 10,300 | $0.001 |
| 6 | AGENTS.md | haiku | 10,300 | $0.001 |

**Total: 6 tasks · ~54k tokens · ~$0.28** · executors: haiku×2, codex×1, sonnet×2, opus×1
Ordering: 1 → 2 → 3 → (4, 5, 6). Tasks 5 & 6 touch disjoint files → parallel_group 5.

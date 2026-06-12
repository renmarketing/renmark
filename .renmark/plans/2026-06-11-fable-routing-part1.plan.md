---
artifact_type: plan
schema_version: 1
created_at: 2026-06-11T19:30:00+00:00
source_sha: 9b49afd
related_spec: .renmark/research/2026-06-11-fable-routing-strategy.md
generator: fable
part: 1 of 2
dependency_refs: [.renmark/research/2026-06-11-fable-routing-strategy.md]
---

# fable-routing — Part 1: capabilities engine + deterministic gates + tests

**Goal (feature-level, shared by both parts):** implement the declared-capability Fable
routing strategy per amended REQ-2: a committed `## Model tiers` declaration
(`top_tier: fable|opus`) in `.renmark/memory/routing.md`, read by a new pure-Python
`renmark/capabilities.py` helper (env override `RENMARK_TOP_TIER`); plan_lint gains two
deterministic BLOCK rules (fable-in-undeclared-project; fable-on-mechanical-work); the
engine cost preview prices fable rows through the declaration; `skill_preamble` surfaces
a declared-tier hint for synthesis skills. Undeclared projects behave byte-identical to
today (absent flag → opus). Availability is declared, never detected.

**Canonical `## Model tiers` block grammar (capabilities.py is the single parser):**
```
## Model tiers
top_tier: fable
declared_at: 2026-06-11
```
`top_tier` value must be `fable` or `opus`; anything else (or an absent block/file)
resolves to `opus` — never raise. `RENMARK_TOP_TIER` env var (same value set) overrides
the file. The block lives in `.renmark/memory/routing.md` ABOVE the Learned overrides
section and is hand-curated — `memory.append_routing` never touches it.

**Out of scope (explicit):** no runtime availability detection; no change to
haiku/sonnet/opus no-override dispatch; no shared rate-table refactor (deferred per
strategy); skill prose/doc surfaces are Part 2.

### Task 1: capabilities module
- **mode:** A
- **target:** renmark/capabilities.py
- **complexity:** medium
- **executor:** codex
- **parallel_group:** 1
- **est_tokens:** 800
- **est_cost_usd:** 0.03
- **verifier:** python3 -c "from renmark.capabilities import top_tier, effective_executor, is_top_tier_declared, read_tiers; from pathlib import Path; print(top_tier(Path('.')))" | tail -1
- **serves:** REQ-2
- **spec:**
  NEW pure-function stdlib-only module (match the house style of renmark/summary.py:
  module docstring, `from __future__ import annotations`, typed signatures, no side
  effects, never raises out of the public functions). Public API:
  `read_tiers(repo: Path) -> dict[str, str]` — parse the `## Model tiers` block from
  `<repo>/.renmark/memory/routing.md` (grammar in the plan header): scan for the heading,
  then read `key: value` lines until the next `## ` heading or EOF; missing file/block →
  `{}`; malformed lines skipped. `top_tier(repo: Path) -> str` — resolution order:
  `RENMARK_TOP_TIER` env var if set and in `{"fable","opus"}` → that; else
  `read_tiers()['top_tier']` if in `{"fable","opus"}` → that; else `"opus"`.
  `is_top_tier_declared(repo: Path) -> bool` — True iff resolution (env or file) yields
  `"fable"`. `effective_executor(executor: str, repo: Path) -> str` — returns `executor`
  unchanged for all non-fable values; for `"fable"` returns `"fable"` when declared else
  `"opus"` (the undeclared fallback mapping). All reads are one bounded file read; cache
  nothing (callers are one-shot CLI/skill invocations). Gates: ruff clean, mypy strict
  clean (annotate fully).

### Task 2: plan_lint declared/mechanical fable gates
- **mode:** B
- **target:** renmark/plan_lint.py
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 2
- **est_tokens:** 600
- **est_cost_usd:** 0.032
- **verifier:** python3 -c "from renmark import plan_lint; assert hasattr(plan_lint, '_check_fable_declared') and hasattr(plan_lint, '_check_fable_mechanical')" && python3 -m py_compile renmark/plan_lint.py
- **serves:** REQ-2
- **spec:**
  Add two BLOCK checks following the existing `_check_*(tasks, repo_root) -> list[tuple[str, str]]`
  pattern (mirror `_check_heavy_read` at line ~186) and register them where the other
  checks compose in `lint_plan` (as checks 9 and 10, after the existing 8):
  (a) `_check_fable_declared` — for each task with `executor == "fable"`, if
  `capabilities.top_tier(repo_root) != "fable"` emit BLOCK:
  `Task {i}: executor `fable` but this project has not declared `top_tier: fable`.
  Declare it in .renmark/memory/routing.md (## Model tiers) or reassign to `opus`.`
  (b) `_check_fable_mechanical` — for each task with `executor == "fable"` and
  `complexity == "simple"` emit BLOCK:
  `Task {i}: executor `fable` on a simple/mechanical task — REQ-2 prohibits fable for
  mechanical or bulk work regardless of declaration. Route to haiku/codex.`
  Import `from . import capabilities` (lazy inside the function is fine to keep import
  graph light). Mirror contract: the check-plan SKILL doc side is Task 5 in THIS plan —
  both sides + tests land in the same feature per the v0.10.0 guard. Gates: ruff + mypy clean.

### Task 3: engine cost preview + env knob
- **mode:** B
- **target:** renmark/cli/_engine.py
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 2
- **est_tokens:** 500
- **est_cost_usd:** 0.032
- **verifier:** python3 -c "from renmark.cli._engine import Config; import inspect; assert 'RENMARK_TOP_TIER' in inspect.getsource(Config.from_env)" && python3 -m py_compile renmark/cli/_engine.py
- **serves:** REQ-2
- **spec:**
  Two edits. (1) `Config.from_env()` (~line 43–66, beside RENMARK_BIG_MODEL): add
  `top_tier` field sourced from `RENMARK_TOP_TIER` (validated against {"fable","opus"};
  empty/absent → "" meaning "defer to capabilities file resolution"). (2) The dry-run
  estimator (~line 400, the inline `cost_per_kt` table that already has `"fable": 0.030`):
  before pricing a task, map its executor through
  `capabilities.effective_executor(task.executor, repo)`; when the mapping downgrades
  (fable→opus because undeclared), price at the opus rate AND render the row's executor
  cell as `fable→opus` so the preview is honest about the fallback. Declared projects
  render and price `fable` unchanged. No other estimator behavior changes. Gates: ruff +
  mypy clean.

### Task 4: skill_preamble declared-tier hint
- **mode:** B
- **target:** renmark/lifecycle.py
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 2
- **est_tokens:** 400
- **est_cost_usd:** 0.031
- **verifier:** python3 -c "import inspect; from renmark import lifecycle; assert 'top_tier' in inspect.getsource(lifecycle.skill_preamble)" && python3 -m py_compile renmark/lifecycle.py
- **serves:** REQ-2
- **spec:**
  In `skill_preamble(repo, skill)`: define a module-level frozenset
  `SYNTHESIS_SKILLS = frozenset({"brainstorm", "plan", "prd", "blueprint"})`. When
  `skill in SYNTHESIS_SKILLS` and `capabilities.top_tier(repo) == "fable"`, append (or
  return as the hint when no other hint fired) one line:
  `declared top tier: fable — for best ideation/strategy results run this session on
  Fable 5 (/model fable)`. Compose with the existing cross-domain hint: if both fire,
  join with " | " into the single returned string (the preamble returns one bounded
  string or None — preserve that contract). Import capabilities lazily inside the
  function. No lifecycle.json writes change. Gates: ruff + mypy clean.

### Task 5: check-plan SKILL — document the two new gates
- **mode:** B
- **target:** plugin/skills/check-plan/SKILL.md
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 2
- **est_tokens:** 200
- **est_cost_usd:** 0.001
- **verifier:** grep -qi 'top_tier' plugin/skills/check-plan/SKILL.md
- **serves:** REQ-2
- **spec:**
  Mirror-contract doc edit (engine side is Task 2). In the checks list (after check 8 /
  the WARN rows, following the existing numbered format), append two BLOCK rows:
  `9. No \`executor: fable\` task in a project without a declared \`top_tier: fable\`
  (.renmark/memory/routing.md ## Model tiers) → **BLOCK**` and
  `10. No \`executor: fable\` task with \`complexity: simple\` (mechanical/bulk — REQ-2
  unconditional prohibition) → **BLOCK**`. No other changes.

### Task 6: capabilities tests
- **mode:** A
- **target:** tests/test_capabilities.py
- **complexity:** medium
- **executor:** codex
- **parallel_group:** 3
- **est_tokens:** 700
- **est_cost_usd:** 0.03
- **verifier:** .venv/bin/python3 -m pytest tests/test_capabilities.py -q --tb=line 2>&1 | tail -2
- **serves:** REQ-2
- **spec:**
  NEW test file following the house style (tmp_path fixtures, no mocks of stdlib). Pin:
  (a) absent routing.md → top_tier == "opus", is_top_tier_declared False;
  (b) routing.md with `## Model tiers`/`top_tier: fable` → "fable"/True;
  (c) `top_tier: opus` explicit → "opus"; (d) garbage value `top_tier: gpt9` → "opus";
  (e) RENMARK_TOP_TIER=fable env override beats a file saying opus (use monkeypatch.setenv),
  and an invalid env value is ignored; (f) effective_executor: non-fable executors pass
  through unchanged (haiku/codex/sonnet/opus), fable→fable when declared, fable→opus when
  not; (g) block parsing stops at the next `## ` heading (a Learned-overrides section
  below must not leak in). Gates: ruff clean.

### Task 7: plan_lint fable-gate tests
- **mode:** B
- **target:** tests/test_plan_lint.py
- **complexity:** medium
- **executor:** codex
- **parallel_group:** 3
- **est_tokens:** 500
- **est_cost_usd:** 0.02
- **verifier:** .venv/bin/python3 -m pytest tests/test_plan_lint.py -q --tb=line 2>&1 | tail -2
- **serves:** REQ-2
- **spec:**
  Reuse the file's task-template helper (line ~40) and tmp-repo pattern. Add:
  (a) `test_fable_undeclared_blocks` — a medium-complexity fable task in a repo with NO
  Model tiers declaration → BLOCK naming top_tier;
  (b) `test_fable_declared_passes` — same task in a repo whose
  .renmark/memory/routing.md declares `top_tier: fable` → no fable-related finding
  (write the block via tmp fixture; remember `_check_fable_declared` consults
  capabilities which reads the repo arg, and clear RENMARK_TOP_TIER via monkeypatch.delenv
  so the env can't leak);
  (c) `test_fable_mechanical_blocks_even_when_declared` — declared repo, fable task with
  complexity simple → BLOCK (the unconditional REQ-2 prohibition);
  (d) existing `test_executor_fable_lints_clean` (line ~300s) will now hit the undeclared
  BLOCK — update it to declare top_tier in its fixture repo so it keeps testing what it
  pinned (executor acceptance), and keep a comment noting why.

### Task 8: engine preview fallback test
- **mode:** B
- **target:** tests/test_engine_budget_and_rollback.py
- **complexity:** medium
- **executor:** codex
- **parallel_group:** 3
- **est_tokens:** 400
- **est_cost_usd:** 0.02
- **verifier:** .venv/bin/python3 -m pytest tests/test_engine_budget_and_rollback.py -q --tb=line 2>&1 | tail -2
- **serves:** REQ-2
- **spec:**
  Extend the existing dry-run cost tests (mirror `test_dry_run_fable_task_without_est_cost_is_not_free`,
  added 2026-06-11): (a) in an UNDECLARED tmp repo, a fable task renders `fable→opus` in
  the preview and is priced at the opus rate (0.015), not 0.030 and not free; (b) in a
  repo declaring `top_tier: fable` (write the routing.md block in the fixture), the same
  task renders `fable` and prices at 0.030. Clear RENMARK_TOP_TIER via monkeypatch.delenv
  in both. Follow the file's existing fixture style.

### Task 9: preamble hint test
- **mode:** B
- **target:** tests/test_lifecycle.py
- **complexity:** medium
- **executor:** codex
- **parallel_group:** 3
- **est_tokens:** 400
- **est_cost_usd:** 0.02
- **verifier:** .venv/bin/python3 -m pytest tests/test_lifecycle.py -q --tb=line 2>&1 | tail -2
- **serves:** REQ-2
- **spec:**
  Add tests pinning the new skill_preamble behavior (find the existing skill_preamble
  tests in tests/test_lifecycle.py and mirror their fixture style): (a) declared repo
  (routing.md block) + skill "brainstorm" → returned hint contains "declared top tier:
  fable"; (b) declared repo + non-synthesis skill ("verify") → no tier hint; (c)
  UNDECLARED repo + "brainstorm" → no tier hint; (d) when a cross-domain hint also fires,
  both fragments appear joined in one string. Clear RENMARK_TOP_TIER via
  monkeypatch.delenv.

## Cost preview — Part 1

| # | Task | Executor | est_tokens | est cost |
|---|---|---|---|---|
| 1 | capabilities module | codex | 800 | $0.03 |
| 2 | plan_lint gates | sonnet | 600 | $0.032 |
| 3 | engine preview + env | sonnet | 500 | $0.032 |
| 4 | preamble tier hint | sonnet | 400 | $0.031 |
| 5 | check-plan doc mirror | haiku | 200 | $0.001 |
| 6 | capabilities tests | codex | 700 | $0.03 |
| 7 | plan_lint tests | codex | 500 | $0.02 |
| 8 | engine preview test | codex | 400 | $0.02 |
| 9 | preamble hint test | codex | 400 | $0.02 |

Haiku/sonnet costs include the ~10k-token Agent overhead per task (honest accounting).
**Part 1 total: ~$0.22 · ~46k tokens · 9 tasks (waves: 1 → 4 parallel → 4 parallel)**

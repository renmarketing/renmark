# Plan: deterministic-plan-validation (v0.10.0)

Goal: `/renmark:check-plan` and `/renmark:orchestrate` pre-flight validate plans
through ONE deterministic Python engine — `renmark/plan_lint.py` — producing
identical PASS/WARN/BLOCK verdicts with bounded output, so the two surfaces can
never drift and Claude never reasons through structure Python can check.
Behavior-preserving: every check keeps the severity the check-plan SKILL assigns
today (structural 1–3 + heavy-read + transcript-leak + dependency-hygiene =
BLOCK; verifier-output-bound + spec-length = WARN). No new user-facing commands.

Executor note: codex CLI is not installed on this host — test scaffolding is
routed to sonnet instead of the codex default (routing.md newest-wins also
records codex for tests/**; unavailable here).

Related: PRD REQ-5 / REQ-7 / REQ-3 (alignment verdict: aligned). Picks up the
"check-plan Python backing" item explicitly deferred in the v0.9.1 changelog.

## Tasks

### Task 1: renmark/plan_lint.py — deterministic plan validation engine
- **mode:** A
- **target:** renmark/plan_lint.py
- **context_files:** [plugin/skills/check-plan/SKILL.md]
- **verifier:** python -m mypy renmark/plan_lint.py 2>&1 | tail -1
- **executor:** sonnet
- **complexity:** medium
- **parallel_group:** 1
- **est_tokens:** 4000
- **est_cost_usd:** 0.15
- **spec:**
  New module composing renmark.parser.parse_plan (NEVER re-parsing by hand).
  PlanError from parse → a single BLOCK issue (graceful; an empty/corrupt plan
  must not crash). Implement exactly the checks plugin/skills/check-plan/SKILL.md
  defines, same severities: (1) task count ≤ 15 → BLOCK; (2) non-empty verifier
  per task → BLOCK, with the SKILL's `test -f`-only refinement → WARN;
  (3) duplicate target within a parallel_group → BLOCK; (4) heavy-read G5:
  any context_file > 200 on-disk lines with executor sonnet/opus → BLOCK;
  (5) transcript-leak G11: case-insensitive spec match against the 7-phrase
  denylist embedded verbatim from check-plan SKILL §2.5 → BLOCK; (6) dependency
  hygiene G11: spec references a prior task's full output without naming an
  artifact path/interface (the SKILL's heuristic) → BLOCK; (7) verifier-output
  bound G3: unbounded cat/find/git-diff/git-log without head/tail/grep/-n caps
  → WARN; (8) spec length > 80 lines → WARN. Sanity extras (all WARN, never
  BLOCK — behavior-preserving): est_tokens/est_cost_usd negative or absurd
  (>200k tokens / >$50 per task). Public API: lint_plan(path) -> PlanLintReport
  dataclass (verdict: PASS|WARN|BLOCK, issues: list[str], task_count,
  executor_counts) and a __main__ CLI `python -m renmark.plan_lint <plan.md>`
  printing the check-plan report format (header, BLOCK list, WARN list, verdict
  line) with exit 0 PASS / 0-with-WARNs / 1 BLOCK — matching the SKILL's
  documented exit semantics. mypy strict + ruff clean; no new dependencies;
  never raises out of lint_plan.

### Task 2: tests/test_plan_lint.py — pin every check
- **mode:** A
- **target:** tests/test_plan_lint.py
- **context_files:** [plugin/skills/check-plan/SKILL.md]
- **verifier:** python -m pytest tests/test_plan_lint.py -q 2>&1 | tail -1
- **executor:** sonnet
- **complexity:** medium
- **parallel_group:** 2
- **est_tokens:** 4000
- **est_cost_usd:** 0.15
- **spec:**
  Fixture-based tests (tmp_path plan files, mirroring tests/test_parser.py
  style): valid plan → PASS exit 0; missing verifier → BLOCK; 16 tasks → BLOCK;
  duplicate target in same parallel_group → BLOCK; invalid executor → BLOCK via
  parse error; invalid mode (C) → BLOCK via parse error; malformed metadata
  (bad est_tokens type) → BLOCK gracefully; empty file and non-plan garbage →
  BLOCK verdict, no exception; `test -f`-only verifier → WARN; unbounded `cat`
  verifier → WARN; >80-line spec → WARN; heavy-read context file with sonnet →
  BLOCK; denylist phrase in spec → BLOCK; negative est_tokens → WARN.
  Single-source-of-truth pin: one test asserting BOTH
  plugin/skills/check-plan/SKILL.md and plugin/skills/orchestrate/SKILL.md
  contain the literal `python -m renmark.plan_lint` invocation (text-level
  guard that the two surfaces share the engine). CLI exit-code tests via
  subprocess.

### Task 3: rewire check-plan SKILL onto the engine
- **mode:** B
- **target:** plugin/skills/check-plan/SKILL.md
- **context_files:** [plugin/skills/hygiene/SKILL.md]
- **verifier:** python -m pytest tests/test_lint.py tests/test_lint_next_steps.py -q 2>&1 | tail -1
- **executor:** sonnet
- **complexity:** simple
- **parallel_group:** 3
- **est_tokens:** 1500
- **est_cost_usd:** 0.05
- **spec:**
  Steps 1–2.5 collapse into: run `python -m renmark.plan_lint <plan>` and pass
  its bounded report through verbatim (hygiene-style "the format is the
  contract"). Keep UNCHANGED: Step 0 preamble, the lifecycle plan-validated
  write rules (PASS or user-accepted WARN only; never on BLOCK), the Step 4
  hand-off menu, the plan-suppresses-this-gate contract note, frontmatter, and
  next-steps citation. Add one advisory line: judgment-only smells (naming,
  spec quality) remain the LLM's job and are advisory, never verdict-changing.
  Live lint tests must stay green.

### Task 4: orchestrate pre-flight uses the same engine
- **mode:** B
- **target:** plugin/skills/orchestrate/SKILL.md
- **context_files:** []
- **verifier:** grep -c "renmark.plan_lint" plugin/skills/orchestrate/SKILL.md | tail -1
- **executor:** sonnet
- **complexity:** simple
- **parallel_group:** 3
- **est_tokens:** 1200
- **est_cost_usd:** 0.04
- **spec:**
  In §2 Pre-flight, replace "invoke /renmark:check-plan <plan>" with running
  `python -m renmark.plan_lint <plan>` directly (same engine, no skill-to-skill
  hop), keeping the existing semantics line: exit 1 (BLOCK) → fix the plan
  first; WARNs can proceed with user acknowledgment. Note the defense-in-depth
  rationale stays (plan validated at plan-time AND dispatch-time by the same
  code). No other pre-flight step changes.

### Task 5: check-plan shim description reflects the deterministic engine
- **mode:** B
- **target:** plugin/commands/check-plan.md
- **context_files:** [plugin/skills/check-plan/SKILL.md]
- **verifier:** python -m renmark.lint --strict-frontmatter 2>&1 | tail -1
- **executor:** haiku
- **complexity:** simple
- **parallel_group:** 3
- **est_tokens:** 300
- **est_cost_usd:** 0.01
- **spec:**
  Refresh the one-line description: validation now runs through the
  deterministic renmark.plan_lint engine (shared with orchestrate pre-flight);
  keep PASS/WARN/BLOCK wording and strict-YAML-safe quoting.

### Task 6: doc rows mention the deterministic validator
- **mode:** B
- **target:** CLAUDE.md
- **context_files:** [AGENTS.md, plugin/templates/CLAUDE.md.template, plugin/templates/AGENTS.md.template, plugin/skills/help/SKILL.md]
- **verifier:** grep -c "plan_lint" CLAUDE.md AGENTS.md | tail -1
- **executor:** haiku
- **complexity:** simple
- **parallel_group:** 4
- **est_tokens:** 800
- **est_cost_usd:** 0.02
- **spec:**
  Single logical edit mirrored per repo rule: update the check-plan row in the
  tooling tables of CLAUDE.md, AGENTS.md, both templates, and the help SKILL
  list to say validation is deterministic Python (renmark.plan_lint) shared by
  check-plan and orchestrate pre-flight. Row wording only — no other doc
  content. Do not touch managed BEGIN/END stub blocks.

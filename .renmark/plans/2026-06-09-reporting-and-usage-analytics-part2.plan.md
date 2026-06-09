# Plan: reporting-and-usage-analytics — Part 2 (surfaces + integration)

artifact_type: plan
schema_version: 1
created_at: 2026-06-09
generator: opus
related_feature: feature/reporting-and-usage-analytics
serves_prd: REQ-15, REQ-16
depends_on: 2026-06-09-reporting-and-usage-analytics-part1.plan.md

## Context

Part 2 surfaces the Part-1 engine to users and wires it into the live pipeline.
**Part 1 (renmark/usage.py, renmark/reports.py, renmark/analytics.py,
state/pause.py + state/usage.py extensions) MUST be merged before running Part 2** —
every task here imports those modules.

Surfaces: `/renmark:usage` + `/renmark:analytics` (command shims + skills, both
zero-LLM — they invoke `renmark-execute` and display bounded output). Integration:
orchestrate records task events + Tier-1 preflight + Tier-2 pause-not-fail; loop
records iteration metrics + usage-limit pause; finish writes the feature report;
resume surfaces usage-paused runs; `.gitignore` keeps raw analytics JSONL out of git.

**Locked constraints (same as Part 1):** stdlib only; inject `now`/`ts`; orchestrator
NEVER reads raw JSONL into context — skills call `renmark-execute --usage/--analytics`
and show only the bounded rendered output; mandatory disclaimer on all usage output.

Dev gates: `pytest -q` · `ruff check` · `mypy .` (feature-level verify runs these).

---

### Task 1: CLI handlers — enrich cmd_usage, add cmd_analytics
- **mode:** B
- **target:** renmark/cli/commands.py
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 1
- **est_tokens:** 1300
- **est_cost_usd:** 0.04
- **verifier:** python -c "from renmark.cli.commands import cmd_usage, cmd_analytics" && ruff check renmark/cli/commands.py
- **serves:** REQ-15
- **spec:**
  Enrich `cmd_usage(repo)` to render the rich view: call
  `renmark.usage.build_usage_view(repo, now=renmark.state.now_iso())` then
  `print(renmark.usage.render_usage_md(view))`; keep the existing
  "no usage recorded yet" empty path; always print the disclaimer (render_usage_md
  already appends it). Add `def cmd_analytics(repo: Path) -> int` — call
  `renmark.analytics.aggregate(repo, now=now_iso())` then
  `renmark.analytics.build_health_report(repo, now=now_iso())`, print
  `render_health_md(report)`, write the snapshot to `.renmark/memory/analytics.md`
  (committed, like roadmap.md), return 0. Non-raising; degrade to a friendly
  "no analytics yet" message on empty project. Do NOT print raw JSONL.

### Task 2: CLI arg wiring — --analytics flag
- **mode:** B
- **target:** renmark/cli/_engine.py
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 2
- **est_tokens:** 700
- **est_cost_usd:** 0.03
- **verifier:** python -m renmark --help >/dev/null 2>&1; renmark/cli/_engine.py && ruff check renmark/cli/_engine.py
- **serves:** REQ-15
- **spec:**
  Add `ap.add_argument("--analytics", action="store_true", help="show build-health
  analytics and exit")`. In the dispatch block, add `if args.analytics: return
  cmd_analytics(repo)` (import alongside the existing `cmd_usage` import). Update the
  final `ap.error(...)` string to include `--analytics` in the
  "plan path is required unless ..." list. Leave `--usage` wired to the (now
  enriched) `cmd_usage`. NOTE: verifier above is illustrative — use
  `python -c "import renmark.cli._engine"` && `ruff check renmark/cli/_engine.py`.

### Task 3: CLI re-exports
- **mode:** B
- **target:** renmark/cli/__init__.py
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 2
- **est_tokens:** 200
- **est_cost_usd:** 0.01
- **verifier:** python -c "from renmark.cli import cmd_analytics, cmd_usage"
- **serves:** REQ-15
- **spec:**
  Add `cmd_analytics` to the `from .commands import ...` line and to `__all__`,
  preserving alphabetical order and the existing back-compat comment.

### Task 4: /renmark:usage command shim
- **mode:** A
- **target:** plugin/commands/usage.md
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 3
- **est_tokens:** 250
- **est_cost_usd:** 0.01
- **verifier:** test -f plugin/commands/usage.md && grep -q "skills/usage/SKILL.md" plugin/commands/usage.md
- **serves:** REQ-15
- **spec:**
  Command shim mirroring `plugin/commands/roadmap.md` exactly in shape. Frontmatter
  `description:` — one line: observed local usage status (rolling 5h / weekly, local
  limits, paused runs); zero LLM calls. Body:
  ``Read `${CLAUDE_PLUGIN_ROOT}/skills/usage/SKILL.md` and follow its instructions
  exactly. The user provided this input: $ARGUMENTS`` + the standard
  "If `$ARGUMENTS` is empty, begin the usage skill's flow." line.

### Task 5: /renmark:analytics command shim
- **mode:** A
- **target:** plugin/commands/analytics.md
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 3
- **est_tokens:** 250
- **est_cost_usd:** 0.01
- **verifier:** test -f plugin/commands/analytics.md && grep -q "skills/analytics/SKILL.md" plugin/commands/analytics.md
- **serves:** REQ-15
- **spec:**
  Command shim mirroring `plugin/commands/roadmap.md`. Frontmatter `description:` —
  bounded project build-health summary (shipped/blocked features, loop success rate,
  token/cost by feature); zero LLM calls. Body delegates to
  `${CLAUDE_PLUGIN_ROOT}/skills/analytics/SKILL.md` with the same `$ARGUMENTS`
  pattern as the other command shims.

### Task 6: /renmark:usage skill
- **mode:** A
- **target:** plugin/skills/usage/SKILL.md
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 4
- **est_tokens:** 1400
- **est_cost_usd:** 0.04
- **verifier:** test -f plugin/skills/usage/SKILL.md && grep -q "Observed local usage only" plugin/skills/usage/SKILL.md
- **serves:** REQ-15, REQ-16
- **spec:**
  Zero-LLM status skill modeled on `plugin/skills/roadmap/SKILL.md`. Frontmatter
  `name: usage` + a description matching the command shim. Body:
  Step 0 — context check `lifecycle.skill_preamble(repo,'usage')`, surface hint.
  Main — run `renmark-execute --usage` (it prints the bounded view from
  `renmark.usage.render_usage_md`); show that output to the user verbatim. Explicitly
  state the rule: NEVER read `.renmark/analytics/*.jsonl` or `.renmark/state/usage.jsonl`
  into context — the Python layer aggregates; the skill only displays bounded output.
  Call out that output ALWAYS carries "Observed local usage only. Provider-side
  account limits may differ." and that provider-reported limits appear only when a
  reliable provider source exposed them. If paused runs exist, surface the suggested
  resume time and point to `/renmark:resume`. End with the next-steps handoff per
  `${CLAUDE_PLUGIN_ROOT}/skills/_shared/next-steps.md` (aux/terminal class — resume
  pipeline + local actions). Mirror any rule into AGENTS.md note if present.

### Task 7: /renmark:analytics skill
- **mode:** A
- **target:** plugin/skills/analytics/SKILL.md
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 4
- **est_tokens:** 1300
- **est_cost_usd:** 0.04
- **verifier:** test -f plugin/skills/analytics/SKILL.md && grep -q "renmark-execute --analytics" plugin/skills/analytics/SKILL.md
- **serves:** REQ-15
- **spec:**
  Zero-LLM skill modeled on roadmap's. Frontmatter `name: analytics`. Body:
  Step 0 context check. Main — run `renmark-execute --analytics`; show the bounded
  build-health summary (it also writes `.renmark/memory/analytics.md`). Hard rule:
  NEVER dump raw logs / load `.renmark/analytics/*.jsonl` into context — Python
  aggregates, skill displays only the bounded summary. End with next-steps handoff
  (aux/terminal class).

### Task 8: finish integration — write feature report + record run
- **mode:** B
- **target:** plugin/skills/finish/SKILL.md
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 5
- **est_tokens:** 1100
- **est_cost_usd:** 0.04
- **verifier:** test -f plugin/skills/finish/SKILL.md && grep -q "reports" plugin/skills/finish/SKILL.md
- **serves:** REQ-15
- **spec:**
  Add a step (after verifiers pass + branch summary, before the next-steps menu):
  build + write the feature report via `renmark.reports.build_feature_report(...)`
  / `write_feature_report(...)` — populate feature name, branch, final SHA
  (`git rev-parse HEAD`), files-changed count (`git diff --stat` count), verification
  result (from lifecycle/verify artifact), codereview result if present, version/tag/
  release path if a release happened (`.renmark/version/<version>/`), branch
  disposition, what shipped / deferred, recommended next backlog items. Also call
  `renmark.analytics.record_feature_run(...)`. The orchestrator reads only the
  returned report path (≤5-line summary), NEVER the report body. Add `[a] Analytics`
  to the offer-next-steps menu (runs `/renmark:analytics`). Keep all existing finish
  behavior intact. Mirror the rule change into AGENTS.md per the sync convention.

### Task 9: orchestrate integration — event recording + usage preflight/pause
- **mode:** B
- **target:** plugin/skills/orchestrate/SKILL.md
- **complexity:** hard
- **executor:** opus
- **parallel_group:** 5
- **est_tokens:** 1800
- **est_cost_usd:** 0.17
- **verifier:** test -f plugin/skills/orchestrate/SKILL.md && grep -q "usage_limit" plugin/skills/orchestrate/SKILL.md
- **serves:** REQ-15, REQ-16
- **spec:**
  Three additive touchpoints, each as bounded calls (no raw-log reads):
  (1) Tier-1 usage preflight — before dispatching a wave, run `renmark-execute
  --usage` semantics via `renmark.usage.build_usage_view`; if a configured local
  limit in `.renmark/analytics/limits.json` is already exceeded, PAUSE before spend
  (write a usage-limit PauseState via `renmark.usage.classify_usage_pause`) instead of
  dispatching. (2) Event recording — after each wave, call
  `renmark.analytics.record_task_run(...)` per task from the bounded WaveResult
  summary (status, executor, duration, tokens, sha) — never from transcripts.
  (3) Tier-2 provider-error classification — if a task fails with a rate-limit /
  quota / retry-later / usage-exceeded signal, classify the run as PAUSED (write the
  usage-limit PauseState; `pause_reason="usage_limit"`) NOT failed, and stop the wave
  so `/renmark:resume` can continue later. MVP: no polling, no auto-retry. Preserve
  the existing G11 isolation contract — orchestrator aggregates only PASS/FAIL/paths.
  Mirror the rule into AGENTS.md.

### Task 10: loop integration — iteration metrics + usage-limit pause
- **mode:** B
- **target:** plugin/skills/loop/SKILL.md
- **complexity:** hard
- **executor:** opus
- **parallel_group:** 5
- **est_tokens:** 1600
- **est_cost_usd:** 0.16
- **verifier:** test -f plugin/skills/loop/SKILL.md && grep -q "record_loop_run" plugin/skills/loop/SKILL.md
- **serves:** REQ-15, REQ-16
- **spec:**
  Add: per-iteration, call `renmark.analytics.record_loop_run(...)` (loop_id, goal,
  backlog_item_id, max_iterations, iterations_used, stop_reason, goal_reached,
  total_tokens, branch_disposition) from the bounded loop state — not transcripts.
  Add the usage-limit pause hook: on a provider rate/quota signal OR a configured
  local-limit preflight failure between iterations, write a usage-limit PauseState
  (via `renmark.usage.classify_usage_pause`, carrying current iteration +
  max_iterations) and STOP the loop in a resumable state (`/renmark:resume`
  continues). Reaffirm REQ-9/REQ-11 bounds (budget + max-iterations + goal-backward
  evidence) — usage pause is an ADDITIONAL stop condition, not a replacement. No
  polling / auto-retry in MVP. Mirror the rule into AGENTS.md.

### Task 11: resume integration — surface usage-paused runs
- **mode:** B
- **target:** plugin/skills/resume/SKILL.md
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 5
- **est_tokens:** 900
- **est_cost_usd:** 0.03
- **verifier:** test -f plugin/skills/resume/SKILL.md && grep -q "usage" plugin/skills/resume/SKILL.md
- **serves:** REQ-16
- **spec:**
  Add a branch: when `renmark.state.read_pause` returns a PauseState with
  `pause_kind="usage_limit"`, surface it specifically — e.g. "Loop/run paused because
  a usage limit was reached. Suggested resume time: <resume_after>. Observed local
  usage only. Provider-side account limits may differ." — and tell the user they can
  resume now (state is persisted) or wait until the suggested time. Keep resume
  zero-LLM and ≤1 file read. Preserve the existing lifecycle-based resume behavior.
  Mirror the rule into AGENTS.md.

### Task 12: gitignore — raw analytics JSONL out of git
- **mode:** B
- **target:** .gitignore
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 6
- **est_tokens:** 150
- **est_cost_usd:** 0.01
- **verifier:** grep -q "analytics" .gitignore
- **serves:** REQ-6
- **spec:**
  Under the "renmark runtime (regenerable per project)" block, add
  `.renmark/analytics/*.jsonl` (raw event streams are runtime/regenerable). Do NOT
  ignore `.renmark/analytics/summary.json`, `.renmark/analytics/limits.json`, or
  `.renmark/reports/` — those are durable, committed project memory. Add an explicit
  un-ignore if needed (`!.renmark/analytics/summary.json`, `!.renmark/analytics/limits.json`)
  so the `*.jsonl` rule never shadows them. Keep the existing comment style.

## Cost preview (Part 2)

| Task | file | executor | est tokens (+overhead) | est $ |
|---|---|---|---|---|
| 1 | cli/commands.py | sonnet | 1300 +10k | 0.034 |
| 2 | cli/_engine.py | sonnet | 700 +10k | 0.032 |
| 3 | cli/__init__.py | haiku | 200 +10k | 0.001 |
| 4 | commands/usage.md | haiku | 250 +10k | 0.001 |
| 5 | commands/analytics.md | haiku | 250 +10k | 0.001 |
| 6 | skills/usage/SKILL.md | sonnet | 1400 +10k | 0.034 |
| 7 | skills/analytics/SKILL.md | sonnet | 1300 +10k | 0.034 |
| 8 | skills/finish/SKILL.md | sonnet | 1100 +10k | 0.033 |
| 9 | skills/orchestrate/SKILL.md | opus | 1800 +10k | 0.17 |
| 10 | skills/loop/SKILL.md | opus | 1600 +10k | 0.16 |
| 11 | skills/resume/SKILL.md | sonnet | 900 +10k | 0.033 |
| 12 | .gitignore | haiku | 150 +10k | 0.001 |

**Part 2 total: ~12 tasks, 6 waves, ~$0.58.**
Executors: haiku×4, sonnet×6, opus×2. Wave plan:
W1[1] · W2[2,3] · W3[4,5] · W4[6,7] · W5[8,9,10,11] · W6[12].

**Combined feature: ~21 tasks, ~$1.35 est** (excl. verify/codereview). Part 1
merges before Part 2 runs.

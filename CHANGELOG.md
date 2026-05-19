# Changelog

## v0.3.0 — 2026-05-19 (framework MVP — context death is survivable)

**Minor release — the foundation that makes renmark a development framework, not just a plugin.**

The core innovation this release: **AI workflows that survive context death.** Cold start from any `/clear` or `/compact` is one file read. Heavy work runs in isolated subagent contexts. The orchestrator is now structurally incapable of merging generated code into its conversation — the parser refuses it.

**Load-bearing new infrastructure** (the MVP five):

- **`renmark/summary.py`** (NEW, 323 LOC, 19 tests) — `write_artifact`, `emit_pointer`, `read_metadata`, `is_stale`, `verifier_tail`, `hash_artifact`, `git_head_sha`. Enforces G3 (5-line summary cap, ~300 tokens per line), G6 (provenance + freshness metadata on every artifact), G9 (`completion_state` / `confidence` / `validation_status` / `retry_count` / `parser_success` / `schema_compliance` transparency fields). Every auditor skill funnels through this module.
- **`renmark/lifecycle.py`** (NEW, 251 LOC, 18 tests) — workflow state for the seven-stage lifecycle. `read_lifecycle`, `write_lifecycle`, `clear_lifecycle`, `next_recommended`, `domain_of`, `is_cross_domain_transition`. Strict 1KB byte budget; runtime cruft is rejected with `LifecycleBloatError` to keep lifecycle.json separate from pipeline.json. G12 codified.
- **`renmark/state.py`** (extended +200 LOC, 15 new tests) — pipeline.json (`read_pipeline_state`, `write_pipeline_state`, `clear_pipeline_state`, `pipeline_is_resumable`), `.renmark/state/wave-summaries/wave-N.json` aggregation (`write_wave_summary`, `read_wave_summary`, `list_wave_summaries`), and `last-skill.json` for cross-domain detection (`record_skill_invocation`, `last_skill_invocation`, `context_budget_check`).
- **`renmark/dispatch.py`** (extended +190 LOC, 19 new tests) — G11 task isolation contract. `SubagentInput` (the ONLY fields a subagent receives) and `SubagentOutput` (the ONLY fields it emits) are frozen dataclasses. `parse_subagent_response` raises `IsolationViolation` on any extra field (transcript, diff, generated_code, reasoning). `dispatch_task_isolated` is the injection point — wraps subagent runners under strict I/O bounds.
- **`renmark/cli.py`** (+110 LOC, 6 new tests) — `--task SPEC --output ARTIFACT` ad-hoc Codex mode. Emits SubagentOutput-shaped JSON to stdout; the generated body lives in the artifact file, never the conversation. Falls back cleanly when codex CLI is missing.
- **`plugin/skills/resume/SKILL.md`** (NEW, 112 lines) — `/renmark:resume`. Zero LLM calls. Reads `lifecycle.json`, prints stage + next recommended command + any pending human approval gate. The cold-start recovery surface.

**Skill behavior changes:**

- All 13 existing skills gained a **Step 0 — Context check** preflight that calls `state.context_budget_check` (for cross-domain `/clear` recommendations) and `state.record_skill_invocation` (for next-skill detection). Skills with stage semantics (start, brainstorm, plan, check-plan, finish) now also write `lifecycle.json` on completion.
- `/renmark:orchestrate` rewritten to honor G11 task isolation: builds dependency context only from prior wave's `dependency_notes` (never the full output), dispatches each task in isolation via `dispatch_task_isolated`, aggregates `SubagentOutput` dicts into `.renmark/state/wave-summaries/wave-N.json`, refuses to merge subagent responses that contain forbidden fields. Pipeline state machine tracked at wave boundaries; `lifecycle.write_lifecycle(stage='created')` on completion.
- `/renmark:check-plan` gained 5 new hygiene + isolation BLOCK/WARN rules: heavy-read check (G5), transcript-leak phrase denylist (G11), dependency-graph hygiene (G11), verifier output bound check (G3), spec length WARN.
- `/renmark:verify` strengthened to goal-backward mode: reads plan goal via `parser.parse_plan`, cross-references open bugs from `.renmark/memory/bugs.md` for regression coverage (G8 compounding), runs commands via `summary.verifier_tail` (bounded output), emits a `.verification.md` artifact via `summary.write_artifact`, appends to `learnings.md` on every run and `bugs.md` on failures. Refuses if pipeline state is dirty.

**New rule blocks in `plugin/templates/CLAUDE.md.template`:**

- `context-budget-rule` — `/compact` at 60%, `/clear` on cross-domain transitions. Domain taxonomy: debug, build, audit, meta.
- `lifecycle-rule` (G12) — every stage transition writes lifecycle.json; cold start is one file read; strict separation from pipeline.json; human approval gates carried in `human_review_required` / `human_review_completed` / `human_review_for` fields.

`plugin/templates/AGENTS.md.template` gained two one-liner mirrors. `plugin/skills/setup/SKILL.md` merge table extended from 15 to 17 blocks.

**`renmark/__init__.py` version drift fixed.** Was stuck at `0.2.0` since the package was forked from ai-inference; now in sync at `0.3.0`.

**Tests:** 192 → 192 passing. 77 new tests added across summary, lifecycle, pipeline state, isolation, and CLI task mode. Zero regressions.

**Files changed:**
- `renmark/summary.py` — NEW
- `renmark/lifecycle.py` — NEW
- `renmark/state.py` — extended (pipeline + wave-summaries + skill invocations)
- `renmark/dispatch.py` — extended (SubagentInput/Output, IsolationViolation, dispatch_task_isolated, parse_subagent_response, build_subagent_input)
- `renmark/cli.py` — `--task` / `--output` ad-hoc Codex mode
- `renmark/__init__.py` — version sync 0.2.0 → 0.3.0
- `plugin/skills/resume/SKILL.md` — NEW
- `plugin/skills/orchestrate/SKILL.md` — full rewrite
- `plugin/skills/verify/SKILL.md` — full rewrite
- `plugin/skills/check-plan/SKILL.md` — hygiene + isolation BLOCKs added
- `plugin/skills/{start,brainstorm,plan,finish,feature,debug,codereview,setup}/SKILL.md` — Step 0 + lifecycle hooks added
- `plugin/templates/CLAUDE.md.template` — `context-budget-rule` + `lifecycle-rule` blocks
- `plugin/templates/AGENTS.md.template` — 2 one-liner mirrors
- `plugin/skills/setup/SKILL.md` — merge table extended to 17 blocks
- `tests/test_summary.py`, `test_lifecycle.py`, `test_state_pipeline.py`, `test_dispatch_isolation.py`, `test_cli_task_mode.py` — all NEW
- `VERSION`, `pyproject.toml`, `plugin/.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `README.md` — version sync

**Do not change:**
- `SubagentOutput` and `SubagentInput` are the **boundary contract**. Adding fields requires updating `SUBAGENT_OUTPUT_FIELDS` (in `dispatch.py`) AND updating every Agent prompt template (in `prompts.py`) AND extending the test `test_subagent_output_fields_match_dataclass`. Drift here is silent corruption.
- `IsolationViolation` is intentionally fail-loud. Do not swallow it with try/except in dispatch paths — that defeats G11. If a real subagent legitimately needs to send a new field, add it to the schema with explicit tests.
- `lifecycle.json` byte budget (1KB) is a forcing function, not a suggestion. If `LifecycleBloatError` fires, the answer is to move fields to `pipeline.json`, not raise the limit.
- The 5-line summary cap in `write_artifact` and `SubagentOutput.summary_lines` is the G3 enforcement. Raising it requires editing `MAX_SUMMARY_LINES` in `summary.py` AND `summary_lines` validation in `dispatch.py.SubagentOutput.__post_init__` AND updating the rule prose in CLAUDE.md.template. All three or none.
- `renmark/__init__.py.__version__` MUST stay synced with `VERSION` and `pyproject.toml`. v0.4.0's `/renmark:release` skill will automate this — until then, bump by hand and run `grep -R 0\\.X\\.Y plugin/templates/ pyproject.toml plugin/.claude-plugin/ .claude-plugin/ README.md renmark/__init__.py VERSION` to confirm.

**Next release: v0.3.1 — `/renmark:document` (post-feature doc sync).** See `/home/renmark/.claude/plans/cheerful-drifting-seal.md` for the full v0.3.x → v0.4.0 rollout.

---

## v0.2.5 — 2026-05-18 (governance charter codification)

**Patch release — documentation only, no code or skill behavior changes.**

The orchestrator (Sonnet 200k typical) is now treated as a degrading systems resource. Nine new governance rules codify how every renmark skill must behave to protect orchestration integrity against context rot. The rules ship as `BEGIN/END` blocks in CLAUDE.md.template so `/renmark:setup` merges them into existing projects without overwriting.

**New CLAUDE.md rule blocks** (9, all in `plugin/templates/CLAUDE.md.template`):
- `orchestrator-role-rule` — coordinator, not memory container
- `canonical-state-rule` — truth lives in `.renmark/` and CHANGELOG, not conversation
- `summary-boundary-rule` — orchestrator-visible output ≤ 5 lines or ≤ 300 tokens
- `context-contamination-rule` — cross-domain skill changes recommend `/clear` (domains: debug, build, audit, meta)
- `artifact-governance-rule` — every artifact carries provenance + freshness metadata
- `compact-semantics-rule` — `/compact` preserves goals, blockers, pipeline state, artifact refs, verification status
- `failure-transparency-rule` — outputs carry `completion_state` / `confidence` / `validation_status` / `retry_count` / `parser_success` / `schema_compliance`
- `workflow-recovery-rule` — multi-step workflows resumable from `.renmark/state/pipeline.json`, not conversational reconstruction
- `task-isolation-rule` — `/renmark:orchestrate` runs each task in an isolated subagent context; subagent transcripts and generated code never re-enter the orchestrator

**AGENTS.md.template:** 9 corresponding one-liner mirrors, each pointing at the longer block in CLAUDE.md.

**`/renmark:setup`:** merge table extended from 6 to 15 blocks. Existing projects get the new rules merged on next setup run without overwriting custom content.

**New file `plugin/skills/CONTRIBUTING.md`:** governance acceptance bar for new skills — 9-rule compliance checklist (G2–G11). A new skill that cannot tick all 9 boxes does not merge. Includes the canonical SKILL.md structure with the `Governance compliance` table every new skill must include.

**Files changed:**
- `plugin/templates/CLAUDE.md.template` — 9 new rule blocks inserted between `verify-before-done-rule` and the tooling table
- `plugin/templates/AGENTS.md.template` — 9 one-liner mirrors added between `Verification before completion` and `Conventions`
- `plugin/skills/setup/SKILL.md` — merge table updated with 9 new entries
- `plugin/skills/CONTRIBUTING.md` — new file
- `VERSION` — bumped `0.2.4` → `0.2.5`

**Do not change:**
- The 9 rule blocks ship as one cohesive set; do not split them into separate releases. Each rule reinforces the others (e.g., G6 artifact metadata depends on G3 summary boundaries; G10 recovery depends on G2 canonical state).
- AGENTS.md mirrors stay one-liners that reference the long-form block in CLAUDE.md — do not duplicate the full rule text in AGENTS.md.
- Block names use the `<topic>-rule` suffix convention. Do not rename existing blocks; downstream merge logic depends on the names.
- The `task-isolation-rule` block describes a contract that Phase 1 code (next release v0.3.0) will enforce. Rules ship first so plans drafted against v0.2.5 already obey them — the code that mechanically blocks violations comes in v0.3.0.

---

## v0.2.4 — 2026-05-15 (vibe coder entry point)

**New skill:**
- `/renmark:start` — plain-English entry point for vibe coders. Asks what you want to build, infers stack and scope from the description, asks at most 2 follow-up questions (reach and lifespan), presents a confirmation summary with a brief best-practices mention, then routes to `/renmark:plan` (simple requests) or `/renmark:brainstorm` (complex/multi-feature). Best practices (error handling, README, .env, .gitignore, smoke test) are woven into task specs automatically — no separate tasks, no jargon exposed to the user.

**plugin.json:** version bumped to 0.2.4; description updated to lead with vibe coder framing; added `vibe-coder` keyword.

**install.sh:** `/renmark:start` added as first skill in success message; start message updated to show `start` as the entry point for new users.

**CLAUDE.md template:** `/renmark:start` added as first row in tooling table.

**Do not change:**
- The 2-question cap in `start` — more questions break the adaptive/frictionless contract
- Stack inference happens silently — never prompt the user to choose a framework

---

## v0.2.3 — 2026-05-15 (setup skill + install.sh rewrite)

**New skill:**
- `/renmark:setup` — prepares any existing project for renmark workflow. Detects tech stack from project files, creates or merges missing CLAUDE.md rule blocks (using BEGIN/END markers), syncs AGENTS.md, creates CHANGELOG.md if absent, scaffolds `.renmark/` directory tree with seed memory files, adds `.gitignore` entries, offers optional `git init`. Safe to re-run — merge-only, never overwrites existing content. Prompts to continue to brainstorm or plan on completion.

**install.sh rewrite:**
- Added `--uninstall` flag (`bash install.sh --uninstall`)
- Removed stale `/orchestrator` cleanup step (ai-inference project artifact)
- Added optional `pip3 install -q -e` step for Python editable package
- Success message now lists all 12 skills with descriptions
- VERSION read dynamically from `./VERSION` file

**VERSION:** bumped `0.1.5` → `0.2.3`

**Do not change:**
- `install.sh` symlinks are idempotent — stale symlinks are removed and recreated; non-symlink collisions abort with an error rather than overwriting

---

## v0.2.2 — 2026-05-14 (skill quality gates + CLAUDE.md discipline rules)

Skills-only release — no Python module changes.

**New skills:**
- `/renmark:check-plan` — lightweight plan validator (task count ≤ 15, verifier presence, parallel group safety). Invoked automatically by orchestrate pre-flight. Returns PASS / WARN / BLOCK.
- `/renmark:verify` — goal-backward smoke test after orchestrate. Reads plan context paragraph, runs one functional command per stated behavior, reports N/M requirements verified. Never reads source files.
- `/renmark:finish` — branch close wrapper. Re-runs verifiers, shows git log summary, offers [p] PR / [m] merge / [n] nothing.

**Skill updates:**
- `orchestrate`: pre-flight now invokes `/renmark:check-plan`; step 7 re-runs all verifiers before reporting done; hand-off menu adds `[v] Verify` and `[f] Finish` options.
- `debug`: Iron Law cross-references CLAUDE.md § Root cause before any fix; step 6 has explicit gate requiring root cause sentence before any code change.

**Template updates (CLAUDE.md.template + AGENTS.md.template):**
- Added `## Context hygiene` — never read generated file contents into conversation
- Added `## Executor dispatch rules` — codex → renmark-execute only, never Agent calls
- Added `## Root cause before any fix` — no code changes without written root cause
- Added `## Verification before completion` — re-run verifiers fresh before claiming done
- Added 3 new commands to tooling table (check-plan, verify, finish)
- AGENTS.md: added absolute paths, single-file scope, root cause, verify-before-done rules

**plugin.json:** version bumped to 0.2.2; description updated (NIM removed, new skills listed); keywords updated.

**Do not change:**
- CLAUDE.md.template rule blocks use BEGIN/END comment markers for tooling that parses them — preserve the `<!-- BEGIN:x -->` / `<!-- END:x -->` wrapper format

---

## v0.2.1 — 2026-05-14 (dispatch routing fix + scope contract + subscription language)

Skills-only release — no Python module changes.

**Fixed:**
- `orchestrate` overview: corrected dispatch table — `codex` → `renmark-execute` (Codex subscription quota), `haiku/sonnet/opus` → Agent calls (Claude Code subscription quota). Added RED FLAG to Step 3 explicitly forbidding codex tasks from being dispatched as Agent calls (was the root cause of all agents running on Sonnet 4.6 in test).
- `orchestrate` overview: replaced "OpenAI credits / Anthropic credits" language with "Codex account / Claude Code account" — both are subscription-based, not API billing.

**Added:**
- `/renmark:plan` Step 0 Scope Contract: 3-question discovery phase (tech stack with inference rules, deployment target, MVP boundary) before any task decomposition. Writes locked decisions to `CHANGELOG.md` and `.renmark/memory/stack.md`. Explicit confirmation gate — no silence-as-confirmation.
- `debug` Step 6: root-cause gate added — must write root cause sentence before drafting any fix.

**Do not change:**
- Scope Contract confirmation gate language: "Do not rely on silence, lack of objection, or ambiguous replies as confirmation" — this wording was specifically required

---

## v0.2.0 — 2026-05-14 (NIM executor removal — multi-executor architecture)

**Breaking change:** NIM executor removed. All NIM references replaced with multi-executor architecture (Haiku / Codex / Sonnet / Opus).

**Python changes:**
- `cli.py`: removed `NIMClient.from_env()` pre-flight block (was blocking all non-dry-run execution without `NVIDIA_NIM_API_KEY`); renamed `NIM_*` env vars → `RENMARK_*`; git tags `nim-run-*` → `renmark-run-*`; commit prefix `[nim]` → `[renmark]`; cleared stale Mistral model defaults to `""`
- `state.py`: `_COMMIT_TASK_RE` updated to match `renmark|codex|nim|manual` prefixes (nim kept for backward-compat with existing git history)
- `roadmap.py`: git log pattern updated; `COST_PER_KT` adds `haiku: 0.0001`
- `debug.py`: `suggest_inspector()` returns `"haiku"` for cheap intents (was `"nim"`)
- `parser.py`: default `executor` changed from `"nim"` to `"codex"`
- `__init__.py`: version bumped to `0.2.0`; description updated to list Haiku/Codex/Sonnet/Opus
- `apply.py`: module docstring updated to generic "agent output"

**Skill updates:**
- `orchestrate`: NIM pre-flight removed; refactor safety check + changelog check added; haiku added to Agent dispatch section; NIM error codes removed
- `plan`: executor list updated (NIM → Haiku); CHANGELOG.md integration added; routing table updated

**Tests:**
- `test_dispatch.py`: default executor `"nim"` → `"codex"`
- `test_debug.py`: `inspector="nim"` → `inspector="haiku"`; `suggest_inspector` assertions updated
- `test_state.py`: 3 new commit variants (`[renmark]`, `[codex]`, bare `renmark`) added; 113 tests pass

**Do not change:**
- `_COMMIT_TASK_RE` still matches `nim` — required for backward-compat with git history from pre-v0.2.0 runs
- `RENMARK_PREFER_SMALL_MODEL` and `RENMARK_BIG_MODEL` env var defaults are intentionally `""` — let users set them explicitly

---

## v0.1.5 — 2026-05-12 (Phase 3: /renmark:debug helper module)

Adds `renmark/debug.py` — file-format helpers + executor-suggestion routing for the debug loop. The skill now has a real backend instead of being a pure playbook.

- `debug.new_session(repo, symptom)` — creates `.renmark/debug/<id>/session.md` with H2 sections (Symptom / Hypotheses / Investigation log / Root cause / Fix / Verification)
- `debug.add_hypothesis(session, idx, title, likely)` — ranked list under Hypotheses
- `debug.log_investigation(session, hypothesis, inspector, finding, rules_out=False)` — append step with which model inspected it
- `debug.set_root_cause(session, text)` — replace the placeholder
- `debug.close_session(session, repo, ...)` — finalize and write a structured entry to `.renmark/memory/bugs.md` (with auto-cross-post to `learnings.md`)
- `debug.latest_session(repo)` — resume the most recent debug session (survives `/clear`)
- `debug.suggest_inspector(intent)` — returns the cheapest executor for a step:
  - `nim` for grep / file-read / line-count / regex
  - `codex` for multi-file-trace / find-usages / context-gather / api-check
  - `opus` for reasoning / race-condition / architecture
- `/renmark:debug` SKILL.md updated to point at these helpers

7 new tests. 111 passing (104 before + 7 debug tests).

**Still pending (lower priority):**
- `dispatch.py` calling `resolve_provider` to route non-nim/codex executors through the new Phase 4 providers
- `/renmark:codereview` writing review findings into `bugs.md`/`decisions.md` automatically

## v0.1.4 — 2026-05-12 (Phase 4: native multi-provider clients)

Adds three native providers + a resolver. Zero new third-party deps.

- `renmark/providers/openai_compat.py` — generic OpenAI-compatible client. Speaks `/chat/completions` against any base URL with a bearer token. Retry on 429/503, fail on 401, parse `choices[0].message.content` + `usage.{prompt,completion}_tokens`.
- `renmark/providers/ollama.py` — delegates to `openai_compat` against `http://localhost:11434/v1` by default. Executor: `ollama_chat/<model>` (e.g. `ollama_chat/qwen2.5-coder:7b`).
- `renmark/providers/openrouter.py` — delegates to `openai_compat` against `https://openrouter.ai/api/v1`. Executor: `openrouter/<provider>/<model>`. Reads `OPENROUTER_API_KEY` from env.
- `renmark/providers/__init__.py` — new `resolve_provider(executor)` function maps any executor string to `(module_name, model_arg)`. Unknown `<prefix>/<model>` strings fall through to `openai_compat` so Together / Anyscale / Groq / etc. work with the right env vars.
- 13 new tests for resolver + each provider (all mocked HTTP).

Executor strings that now work:

| Executor | Routes to |
|---|---|
| `nim` | NIM client (existing) |
| `codex` | Codex CLI (existing) |
| `opus`, `sonnet` | Agent tool — skill must dispatch |
| `ollama_chat/<model>` | Local Ollama (default `:11434`) |
| `openrouter/<provider>/<model>` | OpenRouter gateway |
| `openai_compat/<model>` | Any OpenAI-compatible API (needs `OPENAI_COMPAT_BASE_URL` + `OPENAI_COMPAT_API_KEY`) |
| `<unknown>/<model>` | Falls through to openai_compat |

104 tests pass (91 before + 13 provider tests).

**Still pending:**
- Wiring `resolve_provider` into `dispatch.py`'s actual call path (right now `dispatch.dispatch_wave` only knows nim/codex/opus/sonnet)
- `/renmark:debug` per-step routing
- `/renmark:debug` and `/renmark:codereview` writing to `bugs.md` automatically

## v0.1.3 — 2026-05-12 (cost preview + --no-commit + routing-memory + perm snippet)

Phase 1 polish landed:

- **Cost preview in `--dry-run`**: per-task line shows executor + complexity + estimated tokens + estimated $; totals at the bottom. Uses `est_tokens` / `est_cost_usd` from the plan if present, falls back to complexity heuristic. NIM = free, codex ≈ $0.05/kT, sonnet ≈ $0.003/kT, opus = in-context.
- **`renmark-execute --no-commit`** runtime now wired through `_NO_COMMIT_MODE` module flag. `_git_commit` returns `"(no-commit)"` sentinel; the skill batches commits per wave.
- **Routing memory auto-updates**: after each task completes (passed/failed), `_memory_log_outcome` appends to `routing.md` with the task signature (`target=*.py, complexity=medium, mode=A`), executor, and outcome. Failed tasks also append to `learnings.md` with the failure note. Future `/renmark:plan` runs read these to inform auto-routing.
- **Permission-allowlist snippet** added to README — paste-in `.claude/settings.local.json` block that eliminates Bash prompts for `renmark-execute *` calls.

91 tests pass (no regressions from these changes — pure additions).

**Still pending:**
- `providers/ollama.py`, `openrouter.py`, `openai_compat.py` — Phase 4
- `/renmark:debug` per-step routing — Phase 3

## v0.1.2 — 2026-05-12 (cli uses dispatch.py — parallel waves live)

**Headline:** `renmark-execute` now uses `dispatch.py` for wave-based parallel execution. Tasks sharing a `parallel_group` run concurrently on separate threads; tasks with `executor: opus | sonnet` are marked `needs_agent` and surfaced so the `/renmark:orchestrate` skill can dispatch them via the Agent tool.

Changes:
- `cli.py`:
  - Module-level `_GIT_LOCK = threading.Lock()` serializes `_git_tag`, `_git_commit`, `_git_restore_target` across parallel task threads (git index isn't multi-thread-safe).
  - `execute_plan` refactored to use `dispatch.group_tasks_by_wave` + `validate_wave` + `dispatch_wave` instead of a flat per-task loop. Existing `_execute_task` is now invoked through a `_runner` adapter that returns `dispatch.TaskResult`.
  - End-of-run summary now reports `needs-agent` count and wave count.
  - If a wave validation fails (overlapping targets, context-into-target conflicts), the plan is rejected with exit 2 before any LLM call.
- `dispatch.py` tests (11) already covered the parallel semantics; cli.py integration verified by the existing 91-test suite — all still pass.

**LiteLLM dropped from roadmap.** Per user decision: native providers cover all realistic use cases. Future providers go in as one-file `providers/*.py` modules following the `openai_compat.py` pattern.
- PLAN.md "Phase 5" struck through with rationale
- CHANGELOG pending-list updated
- "What to steal from" table notes LiteLLM was considered and rejected

**Still pending (v0.1.3+):**
- `--no-commit` runtime behavior (argparse flag accepted, not yet effective in the commit path — would let skills batch-commit per wave manually)
- Cost preview in `--dry-run` (per-task estimate before any LLM call)
- Routing memory auto-updates from run outcomes
- `/renmark:debug` per-step routing actually wired
- Additional native providers (Ollama, OpenRouter, OpenAI-compat) — Phase 4

91 tests pass.

## v0.1.1 — 2026-05-12 (logs dir + codereview simplified to codex-only)

**Added: `.renmark/logs/`** for per-invocation troubleshooting logs (gitignored). One log file per command run named `<command>-<run_id>.log`.

- `renmark/state.py`:
  - New constants: `LOGS_SUBDIR = "logs"`
  - `logs_dir(repo)`, `open_log(repo, command, run_id=None)`, `append_log(path, *messages)`, `recent_logs(repo, n=10)`
  - 6 tests
- `renmark-execute --logs` — lists the n most-recent log files with size + mtime
- `renmark-execute --logs-n <N>` — adjust the count (default 10)
- `bootstrap.py` updated: `.gitignore` template now includes `.renmark/logs/`
- `plugin/templates/memory/INDEX.md.template` updated to reference all `.renmark/` subdirs (specs, plans, reviews, state, debug, logs)

**Changed: `/renmark:codereview` is now single-pass (codex-only)**, no Sonnet/Opus passes.

The earlier multi-pass design put code into the conversation, which defeats the context-hygiene goal renmark is built for. Codex stays in its own sandbox; Opus only reads the severity summary. Output format and storage path unchanged (`.renmark/reviews/YYYY-MM-DD-<sha>.review.md`). Recommended cadence: end-of-plan, not per-task.

Tests: 91 passing (up from 85).

**Still pending (v0.1.2+):**

- CLI `execute_plan` integration with `dispatch.group_tasks_by_wave` + `dispatch_wave` — parallel waves not yet wired into the live loop
- `--no-commit` runtime behavior (flag accepted, not yet effective)
- Cost preview in `--dry-run`
- Routing memory auto-updates from run outcomes
- `/renmark:debug` per-step routing actually wired
- Additional native providers (Ollama, OpenRouter, OpenAI-compat) — Phase 4
- ~~LiteLLM plug-in slot — Phase 5~~ (dropped — native providers cover the realistic use cases)

## v0.1.0 — 2026-05-12 (Phase 1 module landing + roadmap reporter)

**First minor release.** The Phase 1 modules are all in place with tests; the CLI's `execute_plan` loop still uses the v0.0.x single-task code path. Integrating that loop with the new dispatcher is the v0.1.1 work.

**New modules (with tests):**

- `renmark/dispatch.py` — wave-based parallel dispatcher. `group_tasks_by_wave`, `validate_wave`, `dispatch_wave` (concurrent for nim/codex/litellm, `needs_agent` marker for opus/sonnet). 11 tests including a timing assertion that two slow tasks in the same wave finish in under the serial total.
- `renmark/providers/claude_agent.py` — composer for the Agent-tool prompt when a task is `executor: opus` or `executor: sonnet`. Skill issues the Agent call; this module owns the prompt format and constraints.
- `renmark/bootstrap.py` — empty-folder helper. `is_empty_project(repo)`, `bootstrap(repo, project_name=...)` creates CLAUDE.md / AGENTS.md / `.renmark/` from plugin templates, runs `git init`. Idempotent. 6 tests.
- `renmark/roadmap.py` — synthesizer that builds a per-task `task | llm | status | tokens | $ | commit` table from `features.md` + `usage.jsonl` + git log. `write_roadmap_md(repo)` snapshots to `.renmark/memory/roadmap.md`. 7 tests.

**Parser extensions (v0.0.3+, fully tested):**

- New optional task fields: `complexity` (simple|medium|hard), `parallel_group` (int), `est_tokens` (int), `est_cost_usd` (float).
- `executor` now accepts `opus`, `sonnet`, or any `<provider>/<model>` string (e.g., `ollama_chat/qwen2.5-coder:7b`).
- 9 new tests covering defaults, type validation, and rejection of invalid values.

**New skills:**

- `/renmark:roadmap` — prints the status table; also writes the snapshot to `.renmark/memory/roadmap.md` so it's committed.
- `/renmark:help` (added in v0.0.3) — lists all skills with one-sentence descriptions.

**Wizard-style hand-offs:**

- `/renmark:brainstorm` now ends with an explicit `Y/n/wait` prompt to continue to `/renmark:plan`.
- `/renmark:plan` shows a summary (task count + cost preview) and prompts `[r]eview / [d]ispatch / [e]dit / [n]o` — Dispatch only triggers `/renmark:orchestrate` after explicit user approval.
- `/renmark:orchestrate` offers `[c]ode-review / [s]moke / [n]one` after a clean run.

**CLI:**

- `renmark-execute --roadmap` — prints the status table and writes `roadmap.md` snapshot.
- `renmark-execute --no-commit` — flag added (currently a no-op; v0.1.1 will wire it into the per-task commit code so the skill can batch commits per wave).
- argparse prog name corrected from `nim-execute` to `renmark-execute`.

**Memory templates:**

The eight `.renmark/memory/` files now have proper documentation-grade templates:
- `features.md`, `bugs.md`, `decisions.md` (ADR format), `stack.md`, `architecture.md`, `conventions.md`, `routing.md`, `learnings.md`, plus an auto-maintained `INDEX.md`.

**Plugin manifest now declares 7 skills** (brainstorm, plan, orchestrate, debug, codereview, roadmap, help).

**Tests:** 85 passing (up from 52 in v0.0.3).

**Still pending (v0.1.1+):**
- CLI `execute_plan` actually using `dispatch.group_tasks_by_wave` + `dispatch_wave` (currently the loop still runs single-task serial via the v0.0.x path)
- `--no-commit` wired through per-task commit code
- Cost preview in `--dry-run`
- Routing memory auto-updates from run outcomes
- `/renmark:debug` per-step routing (NIM grep / codex trace / opus reasoning)
- `/renmark:codereview` Sonnet + Opus passes
- Additional native providers (Ollama, OpenRouter, OpenAI-compat) — Phase 4
- ~~LiteLLM plug-in slot — Phase 5~~ (dropped — native providers cover the realistic use cases) (optional)

## v0.0.3 — 2026-05-12 (Phase 1, +memory + help)

**Persistent memory module + `/renmark:help` skill.**

- `renmark/memory.py` — read/write helpers for `.renmark/memory/`. Functions: `ensure_memory(repo)`, `read_index(repo)`, `read_file(repo, name)`, `log_feature(...)`, `log_bug(...)`, `log_decision(...)`, `append_routing(...)`, `append_learning(...)`. Section-aware appends (newest-first per CHANGELOG convention). Lessons in `log_bug` auto-cross-post to `learnings.md`. 8 new tests.
- Memory templates rewritten so the files act as **living documentation**:
  - `features.md` — shipped / in-progress / planned (CHANGELOG style)
  - `bugs.md` — open / fixed with severity, symptom, root cause, fix, lesson
  - `decisions.md` — ADR format (context, decision, alternatives, consequences) with auto-numbered IDs
  - `stack.md` — languages, libs, runtime env, external APIs
  - `architecture.md` — components, data flow, module boundaries, invariants
  - `conventions.md`, `routing.md`, `learnings.md` — auto-tuned + hand-edited
  - `INDEX.md` is a cheap top-of-file index loaded first by every skill
- `/renmark:help` skill (new) — prints all six commands with one-sentence descriptions and the typical workflow order. Pure documentation, no API calls.
- `plugin.json` updated to declare 6 skills.

52 tests total (44 from baseline + 8 memory tests).

## v0.0.2 — 2026-05-12 (Phase 1, partial — skills visible)

**Plugin manifest + all five `/renmark:*` SKILL.md files** so the commands appear in Claude Code's skill list after install. Template files for empty-folder bootstrap. install.sh hardened.

Added:
- `plugin/plugin.json` declaring the 5 skills
- `plugin/skills/{brainstorm,plan,orchestrate,debug,codereview}/SKILL.md` — workflow docs for each
- `plugin/templates/{CLAUDE.md,AGENTS.md,renmark-readme.md,memory/*.md}.template` — what `/renmark:brainstorm` writes when bootstrapping an empty project
- `install.sh` ran successfully — symlinks live at `~/.claude/plugins/renmark` and `~/.local/bin/renmark-execute`

Fixed:
- `install.sh` v0.0.1 stored the /orchestrator backup at `~/.claude/skills/.orchestrator.bak/` — Claude Code's skill discovery picked it up as a phantom skill named `.orchestrator.bak`. **Backup removed entirely**: the orchestrator source still lives in `/home/renmark/projects/ai-inference/` (and in its git history), so a separate copy under `~/.claude/` was just paranoia and bug surface. install.sh now `rm -rf`s the old skill outright; manual revert is `cd ~/projects/ai-inference && bash install.sh` against the v0.2.0 baseline.

Not yet wired (still Phase 1):
- `renmark/dispatch.py` — wave-based parallel dispatcher (so orchestrate can't yet run opus/sonnet tasks or parallel groups)
- `renmark/memory.py` — `.renmark/memory/` reader/writer
- `renmark/providers/claude_agent.py` — Opus/Sonnet via Agent tool from skill side
- Parser extensions for `complexity`, `parallel_group`, `est_tokens`, `est_cost_usd`
- CLI `--no-commit` mode for batched wave commits
- Cost preview in `--dry-run`
- Empty-folder bootstrap code (skill docs reference it but the brainstorm skill currently does it by hand)

The skills are visible and `/renmark:brainstorm` + `/renmark:plan` are workable today (they're Opus-driven conversations). `/renmark:orchestrate` runs the same single-task path the v0.0.1 baseline supports.

## v0.0.1 — 2026-05-12 (Phase 0)

**Bootstrap of the new `ai-system` repo.** Copies the working v0.2.0 baseline from `/home/renmark/projects/ai-inference/` and retargets the Python package from `nim_execute` to `renmark`.

Changes vs. ai-inference v0.2.0:

- Package renamed `nim_execute` → `renmark`
- `nim_client.py` → `renmark/providers/nim.py`
- `codex_exec.py` → `renmark/providers/codex.py`
- New `renmark/providers/__init__.py` with `PROVIDERS` registry stub
- Runtime state dir renamed `.nim-state/` → `.renmark/state/` (with `RENMARK_DIR_NAME`, `STATE_SUBDIR`, `MEMORY_SUBDIR`, `DEBUG_SUBDIR` constants; legacy `STATE_DIR_NAME` aliased for back-compat)
- All test imports updated, 41 tests still passing
- CLI references `renmark-execute` / `.renmark/state/` in user-facing strings

Phase 1 (next): the five `/renmark:*` skills, `plugin/plugin.json`, dispatch layer, memory module, empty-folder bootstrap. See `PLAN.md`.

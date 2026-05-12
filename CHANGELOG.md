# Changelog

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

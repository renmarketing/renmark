# Changelog

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
- LiteLLM plug-in slot — Phase 5 (optional)

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

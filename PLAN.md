# Plan: `renmark` — multi-LLM orchestration plugin with persistent project memory

## Project home

**New repo: `/home/renmark/projects/ai-system/`** (clean slate, separate from `/home/renmark/projects/ai-inference/`).

The existing `nim_execute` package and `codex_exec` module get **copied in** as starting material, then evolve under the new repo's `renmark/` Python package. `ai-inference` stays frozen at v0.2.0 as the working `/orchestrator` baseline; `ai-system` is the home for the renmark plugin and CLI going forward.

This plan file should be copied to `/home/renmark/projects/ai-system/PLAN.md` as the first implementation step, so future Claude Code sessions opened in that folder pick it up natively.

## Context

The user wants a single Claude Code plugin (`renmark`) that owns the full feature-development workflow — brainstorm → plan → orchestrate → debug → code review — across multiple LLMs (NIM, Codex, Opus, Sonnet, plus native Ollama/OpenRouter providers in later phases). The driving goals:

1. **Context hygiene above all.** NIM and Codex do the bulky emit; Opus stays light. Persistent file-based memory in `.renmark/` survives between sessions so future runs don't re-derive everything.
2. **Permission economy.** Designed for non-auto-mode use. Bundle operations so the user grants permission ≤1× per wave, not per task.
3. **Parallelism within waves.** Tasks with disjoint targets run concurrently. In MVP from day one.
4. **Auto-routing by complexity.** The planner scores each task and assigns the cheapest model that can do it.
5. **Empty-folder bootstrap.** Detect a fresh project and seed CLAUDE.md, AGENTS.md, and `.renmark/` structure.
6. **Own the provider HTTP code.** No LiteLLM dependency; native clients per provider under `renmark/providers/`. LiteLLM is an optional plug-in slot for later.
7. **`/renmark:*` replaces `/orchestrator`.** The renmark plugin's five skills (`brainstorm`, `plan`, `orchestrate`, `debug`, `codereview`) supersede the existing `/orchestrator` skill entirely. `install.sh` removes the old skill (backing it up to `~/.claude/skills/.orchestrator.bak/` first for safety) and registers the renmark plugin. The existing `/home/renmark/projects/ai-inference/` repo remains untouched on disk as a code-archive baseline but is no longer the live install.

## Skill surface (five commands)

| Slash command | Purpose | Primary model | Side artifacts |
|---|---|---|---|
| `/renmark:brainstorm <topic>` | One-Q-at-a-time spec discovery; bootstraps empty projects | Opus | `.renmark/specs/YYYY-MM-DD-<topic>.spec.md`, updates `.renmark/memory/project.md` |
| `/renmark:plan <spec>` | Decomposes into atomic tasks; scores complexity; assigns executor; emits cost preview | Opus | `.renmark/plans/YYYY-MM-DD-<topic>.plan.md` |
| `/renmark:orchestrate <plan>` | Wave-based parallel dispatch to nim/codex/opus/sonnet/litellm | Opus dispatcher + chosen executors | git commits + `.renmark/state/*` |
| `/renmark:debug <symptom>` | Systematic root-cause loop; routes hypotheses to cheap models, fixes to capable models | Opus driver + NIM/codex for inspection | `.renmark/debug/<session>/` |
| `/renmark:codereview <ref>` | Multi-pass review of a diff: codex-adversarial + sonnet-quality + opus-architecture/security | Routes per pass | `.renmark/reviews/YYYY-MM-DD-<sha>.review.md` |

## The `.renmark/` directory — persistent project memory

This is the load-bearing architectural choice. All renmark commands read from and write to this structure so Opus never has to re-derive what was learned in prior sessions.

```
<project>/
├── CLAUDE.md                       # always loaded by Claude Code, ≤200 lines, points at .renmark/
├── AGENTS.md                       # mirror for non-Claude tools, ≤200 lines
├── .gitignore                      # ignores .renmark/state/, .renmark/debug/
└── .renmark/
    ├── README.md                   # one-pager explaining this dir
    ├── memory/                     # PERSISTENT — committed to git
    │   ├── INDEX.md                # cheap top-of-file index; skills load this first
    │   ├── project.md              # tech stack, file layout, what this project is
    │   ├── conventions.md          # code/test conventions (mostly user-edited)
    │   ├── decisions.md            # decision log: what, why, when, by whom
    │   ├── learnings.md            # patterns learned from runs (failure modes, costs)
    │   └── routing.md              # auto-tuned: which executor for which task signature
    ├── specs/                      # PERSISTENT — committed
    │   └── YYYY-MM-DD-<topic>.spec.md
    ├── plans/                      # PERSISTENT — committed
    │   └── YYYY-MM-DD-<topic>.plan.md
    ├── reviews/                    # PERSISTENT — committed
    │   └── YYYY-MM-DD-<sha>.review.md
    ├── state/                      # GITIGNORED — runtime
    │   ├── usage.jsonl             # token ledger (one row per LLM call, all executors)
    │   ├── PAUSED                  # current paused run if any
    │   └── escalations/<task-N>/   # artifacts for failed tasks
    └── debug/                      # GITIGNORED — transient debug sessions
        └── <session-id>/
```

**Token-hygiene contract:** skills load `.renmark/memory/INDEX.md` first (cheap), then fetch only the files relevant to the current command. Memory files cap each at ~100–200 lines so any single load stays under ~1k tokens. The orchestrator NEVER reads generated code bodies; it only reads escalation artifacts on failure.

**Auto-updated memory:** after every orchestrate or debug run, the skill appends to `learnings.md` and `routing.md`:
- "Task X (target=tests/*.py, complexity=medium) succeeded on codex" → `routing.md` raises codex weight for tests/
- "Task Y (target=*.js, signal=canvas) failed on nim 3×, succeeded on opus" → `routing.md` blacklists nim for that signature
- Cost surprises ("codex burned 148k for lane violation") → `learnings.md`

`routing.md` is consumed by `/renmark:plan` next time to inform auto-routing. This is the persistent feedback loop that prevents repeating the snake-game session's mistakes.

## Plan file format

Extends nim-execute's format with three new fields. Backwards-compatible (existing plans work).

```markdown
### Task 3: build snake game logic
- **mode:** A
- **target:** static/snake.js
- **complexity:** hard               # NEW: simple | medium | hard
- **executor:** opus                 # existing field; expanded values
- **parallel_group:** 2              # NEW: tasks in same group run concurrently (must touch disjoint targets)
- **est_tokens:** 4500               # NEW: planner estimate
- **est_cost_usd:** 0.07             # NEW: planner estimate
- **verifier:** node --check static/snake.js
- **spec:**
  ... prose ...
```

Executor values: `nim` | `codex` | `opus` | `sonnet` | `<litellm-provider-string>` (e.g. `ollama_chat/qwen2.5-coder:32b`, `openrouter/anthropic/claude-haiku`).

## Executor dispatch & permission economy

| Executor | Backend | Permission cost in non-auto-mode |
|---|---|---|
| `nim` | nim-execute CLI (existing, unchanged) | Bundled in one Bash call per wave |
| `codex` | codex_exec module (existing, unchanged) | Bundled in same Bash call per wave |
| `opus` / `sonnet` | Agent tool with model override | Bundled in one Agent batch per wave |
| `<litellm>/<model>` | LiteLLM call inside renmark-execute | Bundled in same Bash call per wave |

**One Bash call per wave** for nim/codex/litellm tasks. The `renmark-execute --wave <plan> --tasks 1,3,5` command parallel-dispatches all listed tasks via Python `asyncio.gather` and returns when all done.

**One Agent message per wave** for opus/sonnet tasks. Multiple Agent tool calls in a single Claude turn run concurrently.

Plugin README ships a `.claude/settings.local.json` snippet pre-approving the `renmark-execute` command pattern, so after first install the user sees zero prompts during runs.

## Parallel execution rules

1. Tasks sharing a `parallel_group` MUST have disjoint `target` paths.
2. No task in a group may list another task's `target` in its `context_files`.
3. Validated at plan-parse time. Violations abort with a clear message and a suggested decomposition.
4. Each task writes its target file but does NOT commit (renmark-execute uses `--no-commit`).
5. After all wave tasks complete (success or failure), the orchestrate skill issues serial `git add` + `git commit` in task-index order. Avoids git index lock contention.
6. Next parallel_group starts only after current group's commits land.

## Auto-routing heuristics

`/renmark:plan` scores each task and picks executor:

| Signal in spec / target | Default executor | Why |
|---|---|---|
| Mechanical files (.gitignore, simple .css, JSON config, plain HTML) | `nim` | NIM nails boilerplate |
| `tests/**`, fixtures, mocks, scaffolding | `codex` | Codex is agentic, reads context, runs verifiers |
| Game logic, state machines, coordinate math, DOM APIs, threading, regex | `opus` | NIM/Sonnet historically crash on these |
| Medium domain reasoning, refactors, well-scoped algorithms | `sonnet` | Cost-effective mid-tier |
| Local model preferred (offline, privacy) | `ollama_chat/<model>` | User intent |

Routing weights tuned by `.renmark/memory/routing.md` over time.

## `/renmark:debug` design

Modeled after `superpowers:systematic-debugging` + `context-mode:diagnose`. Loop:

1. **Reproduce** — user provides symptom; Opus drafts a minimal repro.
2. **Hypothesize** — Opus generates 3–5 ranked hypotheses.
3. **Investigate** — for each hypothesis, route inspection to the cheapest model that can do it:
   - File greps, line counts, simple checks → NIM
   - Multi-file traces, "find where X is used" → Codex
   - Cross-system reasoning → Opus
4. **Fix** — Opus drafts fix; if it's a single file with clear bounds, route to NIM/Codex via /renmark:orchestrate; else Opus edits directly.
5. **Verify** — repro fails (bug gone), regression test added.

State preserved in `.renmark/debug/<session-id>/` so a debug session survives `/clear`.

## `/renmark:codereview` design

Reviews a diff (working tree or `<ref>..<ref>`) in passes, each routed to the right model:

| Pass | Executor | Focus |
|---|---|---|
| 1. Adversarial | `codex exec --sandbox read-only` with "find bugs" prompt | Runtime/logic bugs |
| 2. Quality | Sonnet via Agent | Style, naming, readability |
| 3. Architecture / security | Opus via Agent | Hot files only (size > threshold, or touches security paths) |

Output: structured markdown at `.renmark/reviews/YYYY-MM-DD-<sha>.review.md` with severity-ranked findings. Pluggable focus modes (`--focus security|perf|style|all`).

## Empty-folder bootstrap

When `/renmark:brainstorm` or `/renmark:plan` runs in a directory that lacks `CLAUDE.md`, `AGENTS.md`, or `.renmark/`:

1. Detect: empty/sparse dir (no source files, no `.git`, no `docs/`).
2. Ask user: *"This looks like a fresh project. Scaffold `CLAUDE.md`, `AGENTS.md`, and `.renmark/` to organize work? [Y/n]"*
3. On yes, create:
   - **CLAUDE.md (≤200 lines)** — Claude Code memory pre-filled with renmark workflow:
     - Project section (placeholder filled by brainstorm answers)
     - Tooling section listing `/renmark:*` commands and when to use each
     - Plan/spec/memory conventions (where files live, format)
     - Executor preferences pulled from `.renmark/memory/routing.md`
     - Test conventions placeholder
     - Footer: "Update this file as the project evolves; renmark also auto-maintains `.renmark/memory/`"
   - **AGENTS.md (≤200 lines)** — agent-neutral mirror (Codex, OpenAI Agents, others read this). Shorter, just essentials.
   - **`.renmark/`** directory with `README.md`, empty `memory/` files (INDEX, project, conventions, decisions, learnings, routing), `specs/`, `plans/`, `reviews/`, `.gitkeep`s.
   - **`.gitignore`** with `.renmark/state/` and `.renmark/debug/` entries.
   - **`git init`** + initial commit `"chore: renmark scaffold"`.

Templates ship inside the plugin at `~/.claude/plugins/renmark/templates/`.

## Repo layout (single source of truth at `/home/renmark/projects/ai-system/`)

```
/home/renmark/projects/ai-system/                # ← new repo, primary working tree
├── PLAN.md                                   # this file, copied here
├── README.md                                 # install + settings.local.json snippet
├── VERSION
├── CHANGELOG.md
├── requirements.txt
├── plugin/                                   # what gets symlinked into ~/.claude/plugins/renmark/
│   ├── plugin.json                           # manifest declaring 5 skills
│   ├── skills/
│   │   ├── brainstorm/SKILL.md
│   │   ├── plan/SKILL.md
│   │   ├── orchestrate/SKILL.md
│   │   ├── debug/SKILL.md
│   │   └── codereview/SKILL.md
│   └── templates/
│       ├── CLAUDE.md.template
│       ├── AGENTS.md.template
│       ├── renmark-readme.md
│       └── memory/                           # blank memory file templates
├── renmark/                                  # Python package — NO third-party LLM-adapter deps
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli.py                                # `renmark-execute --wave <plan> --tasks N,M,...`
│   ├── parser.py                             # extended plan-file parser (copied + evolved from nim_execute/parser.py)
│   ├── dispatch.py                           # routes tasks to providers/ based on executor field
│   ├── apply.py                              # write file / patch diff (copied from nim_execute/apply.py)
│   ├── verifier.py                           # subprocess verifier (copied from nim_execute/verifier.py)
│   ├── memory.py                             # read/update .renmark/memory/*
│   ├── state.py                              # .renmark/state/ ledger + escalations
│   ├── prompts.py                            # mode A / mode B prompt templates per provider
│   └── providers/                            # native HTTP clients, one file per provider
│       ├── __init__.py                       # PROVIDERS registry
│       ├── nim.py                            # NVIDIA NIM (copied + evolved from nim_client.py)
│       ├── codex.py                          # Codex CLI wrapper (copied from codex_exec.py)
│       ├── claude_agent.py                   # opus/sonnet — *skill-side* helper (Agent tool dispatch)
│       ├── ollama.py                         # local Ollama HTTP (Phase 4)
│       ├── openrouter.py                     # OpenRouter HTTP (Phase 4)
│       ├── openai_compat.py                  # any OpenAI-compatible endpoint (Phase 4)
│       └── litellm_plugin.py                 # OPTIONAL slot (Phase 5), off by default
├── bin/renmark-execute                       # shell shim → python -m renmark
├── tests/                                    # pytest suite (copied + extended from nim_execute tests)
├── install.sh                                # symlinks plugin/ → ~/.claude/plugins/renmark/, bin/ → ~/.local/bin/
└── .env.example
```

Install model: `install.sh` symlinks `plugin/` into `~/.claude/plugins/renmark/` and `bin/renmark-execute` into `~/.local/bin/`. Source-of-truth lives in `/home/renmark/projects/ai-system/`; the global skill directory is just a pointer.

## What to steal from where

| Source | What |
|---|---|
| `nim_execute` (this repo) | Plan parser, task lifecycle, verifier loop, escalation artifacts, `--resume`, `--usage`, `codex_exec` module |
| `superpowers:brainstorming` | One-Q-at-a-time pattern, design-doc commit at end |
| `superpowers:writing-plans` | Plan structure conventions, task decomposition discipline |
| `superpowers:subagent-driven-development` | Subagent isolation as token-saving primitive |
| `superpowers:dispatching-parallel-agents` | Concurrent Agent calls in one message |
| `superpowers:systematic-debugging` | Debug loop structure |
| `context-mode:diagnose` | Reproduce-minimize-hypothesize-instrument-fix pattern |
| `claude-mem` | File-based persistent memory pattern (we build a lightweight project-local version) |
| Plandex | Per-role model config; cost preview; persistent state ledger |
| Aider (architect/editor) | Planner-emitter role separation |
| LiteLLM | Multi-provider HTTP unification |
| Goose recipes | Plans-as-portable-units shape |

## Phasing

### Phase 0 — Bootstrap the new repo (~30 min, mostly file moves)
- `mkdir -p /home/renmark/projects/ai-system/{renmark/providers,plugin/skills,plugin/templates,bin,tests}`
- Copy `PLAN.md` (this file) into the new repo root
- Copy + rename from `/home/renmark/projects/ai-inference/`:
  - `nim_execute/parser.py` → `renmark/parser.py`
  - `nim_execute/nim_client.py` → `renmark/providers/nim.py`
  - `nim_execute/codex_exec.py` → `renmark/providers/codex.py`
  - `nim_execute/apply.py` → `renmark/apply.py`
  - `nim_execute/verifier.py` → `renmark/verifier.py`
  - `nim_execute/state.py` → `renmark/state.py` (rename `.nim-state` references to `.renmark/state/`)
  - `nim_execute/prompts.py` → `renmark/prompts.py`
  - All `tests/` files → `tests/` with import paths updated
- `git init -b main` in the new repo
- Create `install.sh` that symlinks `plugin/` → `~/.claude/plugins/renmark/` and `bin/renmark-execute` → `~/.local/bin/renmark-execute`
- Run existing tests to verify the copy didn't break anything
- Note: `/home/renmark/projects/ai-inference/` is NOT modified — it remains the working v0.2.0 baseline

### Phase 1 — MVP foundation, includes parallelism (~600 lines net new)
- Plugin manifest (`plugin/plugin.json`)
- 5 skill files (`plugin/skills/{brainstorm,plan,orchestrate,debug,codereview}/SKILL.md`)
- `renmark/dispatch.py` — wave-based parallel dispatcher
- `renmark/providers/claude_agent.py` — skill-side helper format for opus/sonnet Agent calls
- `renmark/memory.py` — `.renmark/memory/` read/update
- Extend `renmark/parser.py` with `complexity`, `parallel_group`, `est_tokens`, `est_cost_usd` fields
- `/renmark:brainstorm` + empty-folder bootstrap (CLAUDE.md, AGENTS.md, `.renmark/` templates from `plugin/templates/`)
- `/renmark:plan` with static-heuristic auto-routing (no memory learning yet)
- `/renmark:orchestrate` with parallel_group wave dispatch on day one
- Cost preview in dry-run
- `renmark-execute --no-commit` mode so the orchestrate skill batches commits at end of each wave (no `ai-inference` modification needed; this lives in the new repo)

### Phase 2 — Memory feedback loop (~150 lines)
- Routing memory auto-updates from run outcomes (`routing.md` weights adjusted based on observed failures and costs)
- Permission-allowlist README snippet so `.claude/settings.local.json` pre-approves the renmark-execute command pattern

### Phase 3 — Debug + code review skills (~250 lines)
- `/renmark:debug` with debug session state in `.renmark/debug/<session-id>/`
- `/renmark:codereview` with three-pass routing (codex adversarial → sonnet quality → opus architecture on hot files)
- Memory writes from both skills (decisions, learnings)

### Phase 4 — Additional native providers (~150 lines, no third-party deps)
- `providers/ollama.py` — local Ollama HTTP
- `providers/openrouter.py` — OpenRouter HTTP
- `providers/openai_compat.py` — any OpenAI-compatible endpoint (Together, Anyscale, etc.)
- Provider-string executors (`ollama_chat/qwen2.5-coder:32b`, `openrouter/anthropic/claude-haiku`) work out of the box
- Token tracking unified through each provider's native usage emission

### Phase 5 (optional) — LiteLLM plug-in slot
- `providers/litellm_plugin.py` opt-in: user installs `pip install litellm` themselves; renmark imports lazily
- Routes provider strings not in the native registry through LiteLLM
- Disabled by default — renmark owns its own HTTP code and only delegates to LiteLLM if the user explicitly opts in

## Files to create

All paths under `/home/renmark/projects/ai-system/` unless noted.

**Phase 0 (scaffold):**
- `PLAN.md` (copy of this file)
- `README.md`, `VERSION` (`0.1.0`), `CHANGELOG.md`, `requirements.txt`, `.env.example`, `.gitignore`
- `install.sh` (creates symlinks)
- `renmark/{__init__,__main__,cli,parser,apply,verifier,state,prompts}.py` — initial copies from `ai-inference/nim_execute/`, import paths fixed
- `renmark/providers/{nim,codex}.py` — initial copies from `ai-inference/nim_execute/nim_client.py` and `codex_exec.py`
- `tests/test_*.py` — copies of nim_execute tests, paths fixed
- `bin/renmark-execute` shim

**Phase 1 (MVP, all new in the new repo):**
- `plugin/plugin.json`
- `plugin/skills/{brainstorm,plan,orchestrate,debug,codereview}/SKILL.md`
- `plugin/templates/{CLAUDE.md.template,AGENTS.md.template,renmark-readme.md,memory/INDEX.md,memory/project.md,memory/conventions.md,memory/decisions.md,memory/learnings.md,memory/routing.md}.template`
- `renmark/dispatch.py` (wave-based parallel dispatcher)
- `renmark/memory.py` (`.renmark/memory/` reader/writer)
- `renmark/providers/__init__.py` (PROVIDERS registry)
- `renmark/providers/claude_agent.py` (Agent-tool helper format)
- Extensions to `renmark/parser.py` for `complexity`, `parallel_group`, `est_tokens`, `est_cost_usd`
- Extensions to `renmark/cli.py` for wave dispatch and `--no-commit` mode
- New tests for parser extensions, dispatch, memory, providers/__init__

**Phase 3:** add `plugin/skills/{debug,codereview}/SKILL.md`, debug session helpers in `renmark/state.py`

**Phase 4:** add `renmark/providers/{ollama,openrouter,openai_compat}.py`

**Phase 5 (optional):** add `renmark/providers/litellm_plugin.py`

**Unchanged outside the new repo:**
- Everything in `/home/renmark/projects/ai-inference/`
- `~/.claude/skills/orchestrator/SKILL.md`
- `~/.local/bin/nim-execute` (the existing global wrapper)

`install.sh` is the only thing that touches `~/.claude/plugins/` and `~/.local/bin/`, via symlinks pointing at `/home/renmark/projects/ai-system/plugin/` and `/home/renmark/projects/ai-system/bin/renmark-execute`.

## Verification

Per phase:

1. **Phase 1 smoke:** brainstorm "add a /healthz endpoint to a fresh Flask project". Bootstrap fires (creates CLAUDE.md, AGENTS.md, `.renmark/`). Plan produces 3-task plan with mixed executors. Orchestrate runs sequentially; all pass. Memory files updated with project facts + routing observations.
2. **Phase 1 permission test (non-auto-mode):** count prompts during full flow. Target: ≤2 per orchestrate (one Bash, one Agent batch); zero if README's settings.local.json snippet was applied.
3. **Phase 2 parallelism:** plan with 2 parallel_groups (2 tasks each). State ledger shows pairs starting within 2s; groups are serialized.
4. **Phase 3 debug smoke:** intentionally-broken Flask app; `/renmark:debug "GET /healthz returns 500"` walks the loop, identifies cause, proposes fix.
5. **Phase 3 review smoke:** `/renmark:codereview HEAD~3..HEAD` produces structured review with findings ranked by severity.
6. **Phase 4 multi-provider:** task with `executor: ollama_chat/qwen2.5-coder:7b` (assumes Ollama running) completes with real token counts.
7. **Regression:** existing 41 nim-execute unit tests still pass; existing `/orchestrator` still works on its old plan format.

## Critical files to read before implementation

- `/home/renmark/projects/ai-inference/nim_execute/{cli,parser,codex_exec,state}.py` — reuse logic
- `/home/renmark/.claude/skills/orchestrator/SKILL.md` — pattern to mirror
- `/home/renmark/.claude/plugins/cache/claude-plugins-official/superpowers/5.1.0/skills/brainstorming/SKILL.md`
- `/home/renmark/.claude/plugins/cache/claude-plugins-official/superpowers/5.1.0/skills/writing-plans/SKILL.md`
- `/home/renmark/.claude/plugins/cache/claude-plugins-official/superpowers/5.1.0/skills/systematic-debugging/SKILL.md`
- One existing `plugin.json` to copy the manifest shape

## Resolved decisions

- **Parallelism is in MVP (Phase 1).** Wave dispatch + disjoint-target validation ship from day one.
- **No LiteLLM dependency.** Renmark owns its own provider HTTP code under `providers/`. LiteLLM may be added later as an opt-in plug-in slot (`providers/litellm_plugin.py`), loaded lazily only if the user explicitly enables it. Default install has zero third-party LLM-adapter dependencies.
- **Fresh repo at `/home/renmark/projects/ai-system/`.** Not modifying `ai-inference`; code is copied in as starting material.
- **`/renmark:*` replaces `/orchestrator`.** `install.sh` backs up the old skill to `~/.claude/skills/.orchestrator.bak/` then registers the renmark plugin so the only orchestration surface going forward is renmark's five commands.

## Migration from `/orchestrator`

`install.sh` performs this once:

1. If `~/.claude/skills/orchestrator/` exists → `mv ~/.claude/skills/orchestrator ~/.claude/skills/.orchestrator.bak`
2. `ln -s /home/renmark/projects/ai-system/plugin ~/.claude/plugins/renmark`
3. `ln -s /home/renmark/projects/ai-system/bin/renmark-execute ~/.local/bin/renmark-execute`
4. Print: *"Old /orchestrator skill backed up to ~/.claude/skills/.orchestrator.bak. Use /renmark:orchestrate going forward. Restore with `mv ~/.claude/skills/.orchestrator.bak ~/.claude/skills/orchestrator` if needed."*

The `nim-execute` binary at `~/.local/bin/nim-execute` (pointing at `ai-inference`) is **not removed** — `renmark-execute` is a sibling, not a replacement of the binary. If the user wants to fully retire the old CLI: `rm ~/.local/bin/nim-execute` is a separate manual step.

## Bootstrap note

Renmark is built BY Opus (this conversation and future sessions). It can't bootstrap itself. Once shipped, future features built via `/renmark:*` start paying off the token investment from the next project onward.

## Hard non-goals

- Don't auto-push or auto-merge.
- Don't add auto-escalate-on-failure between tiers (NIM→Codex→Opus); the data doesn't justify it yet.
- Don't ship pre-scaffolding hacks for codex lane violations; better prompt + memory-driven routing solves it.
- Don't build a web UI / dashboard in this scope.
- Don't keep `/orchestrator` as a parallel surface — it's superseded by `/renmark:orchestrate`. The backup at `~/.claude/skills/.orchestrator.bak` is for emergency revert only.

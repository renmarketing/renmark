---
artifact_type: research
schema_version: 1
created_at: 2026-08-05T18:38:59Z
source_sha: 8404cde84dcd302ced9c21da4ea3aaa99d20139f
related_plan: .renmark/rethink/governed-orchestration-assurance/roadmap.md#release-11
generator: sonnet
---

# Spike: does `codex_routing.py` overlap with `global_routing.py`?

## Scope

Bounded read-and-diff spike. No code was modified. Full contents of both
files were read:

- `renmark/codex_routing.py` (155 lines)
- `renmark/global_routing.py` (268 lines)

## What each module actually does

### `renmark/codex_routing.py` — per-task Codex model/effort routing

Solves: given one renmark task (role, complexity, kind, title), decide which
Codex-native model and reasoning-effort setting should run it, and build the
transport arguments for a Codex `spawn_agent` call. This is runtime dispatch
logic invoked once per task during orchestration.

Public surface:

- `CodexRoute` (dataclass) — resolved `model` / `reasoning_effort` / `tier` /
  `reason` for one task.
- `CodexNativeDispatch` (dataclass) — the Codex host transport for one
  isolated task: `task_index`, `task_name`, `role`, `route`, `spawn_args`
  (containing `task_name`, `fork_turns="none"`, `message`), plus the
  `spawn_tool` / `wait_tool` / `followup_tool` names.
- `route_for_task(task) -> CodexRoute` — classifies a task as hard
  (`gpt-5.5`/high), easy (`gpt-5.4-mini`/low), or default-medium
  (`gpt-5.5`/medium) based on `complexity`, `role` membership in
  `EASY_ROLES`, `kind` membership in `HARD_KINDS`, or a title keyword scan
  (`_has_hard_signal`). Defensive: never raises, falls back to a safe medium
  default on any exception.
- `build_native_dispatch(task, *, role, prompt) -> CodexNativeDispatch` —
  builds the `spawn_agent` call shape. Notably `route` is carried as
  metadata only; `spawn_args` intentionally omits model/effort because the
  Codex collaboration tool has no such parameter today.
- Private helpers: `_field`, `_int_field` (permissive task-attribute
  readers over dict-or-object task shapes), `_task_name` (slug builder),
  `_has_hard_signal` (title keyword match against `HARD_KINDS`-adjacent
  signals).

This module answers: **"which Codex model/effort should handle this one
task, and what does the spawn call look like?"**

### `renmark/global_routing.py` — global instruction-file rule installer

Solves: idempotently install (or detect/repair) the "default to renmark for
build/dev work" routing *rule block* inside a **global, per-user** host
instruction file — `~/.claude/CLAUDE.md` for Claude Code or
`~/.codex/AGENTS.md` for Codex — so that host defaults to routing
plain-English build/dev requests into renmark pipelines even before a given
project has adopted renmark. This is a one-time (or repair-time) file-system
operation, not a per-task runtime decision.

Public surface (per its own module docstring, confirmed against the code):

- `ROUTING_BLOCK_NAME`, `ROUTING_BLOCK` (+ `CLAUDE_ROUTING_BLOCK` /
  `CODEX_ROUTING_BLOCK`) — the managed marker name and block bodies.
- `WINDOWS_HOME_NOTE` — guidance string about the separate Windows
  `.claude` directory.
- `global_claude_path(claude_dir=None) -> Path`, `global_codex_path(codex_dir=None) -> Path`,
  `global_instruction_path(host=None, host_dir=None) -> Path` — path
  resolution for the two supported hosts.
- `detect_global_rule(claude_dir=None, *, host=None) -> str` — classifies
  current state as `missing` / `present-without-rule` / `present-with-rule`
  / `present-malformed`, with explicit raw marker-balance checking so a
  broken pre-existing block doesn't cause infinite re-appending.
- `install_global_rule(claude_dir=None, *, host=None) -> dict` —
  idempotent create/append/repair-refusal against the detected state,
  taking a unique `.bak` backup before any append and never touching a
  malformed block.
- Private helper: `_unique_backup_path`, `_routing_block`.

This module answers: **"is the renmark auto-routing rule installed in this
user's global Claude/Codex instruction file, and if not, install it safely?"**

## Verdict: no overlap, boundary is domain (per-task Codex model dispatch vs. global instruction-file installation)

The two modules operate on entirely different objects, at different times,
for different purposes:

| | `codex_routing.py` | `global_routing.py` |
|---|---|---|
| Unit of work | one renmark **task** | one **host instruction file** on disk |
| When it runs | every time a task is dispatched to Codex during orchestration | once (or on repair) during `/renmark:init`/`/renmark:doctor`-style setup |
| Output | a `CodexRoute` / `CodexNativeDispatch` in memory | bytes written to `~/.claude/CLAUDE.md` or `~/.codex/AGENTS.md` |
| Concern | which **model** handles a task, and how to shape the `spawn_agent` call | whether the renmark **routing rule text** is present/well-formed in a global file |
| State touched | none (pure function of task input) | filesystem (reads/writes/backs up a global file) |

There is no shared function, shared dataclass, shared constant, or shared
state between the two files. Neither imports the other (`global_routing.py`
imports `lint` and `hosts`; `codex_routing.py` imports only stdlib `re` and
`dataclasses`). The only thing they have in common is the English word
"routing," applied to two unrelated ideas: routing a *task to a model*, and
routing a *user request to a pipeline* (whose default-on behavior happens to
be installed as a text block via this module). No merge is recommended — the
modules should stay separate.

## Why the names are easy to conflate (informational, to preempt re-raising this)

Both files have "routing" in the name, and renmark's own `CLAUDE.md` uses
"routing" for at least three distinct concepts in the same document: model
tier routing (haiku/sonnet/codex/opus per `model-routing.md`), skill/pipeline
routing (the "default to renmark" behavior this module installs), and
Codex-specific model/effort routing (this module's actual job). A reader
skimming module names alone, without opening either file, could reasonably
guess `codex_routing.py` and `global_routing.py` are two halves of "the
routing system" and go looking for a merge opportunity. They aren't halves
of one system — `codex_routing.py` is dispatch-time decision logic scoped to
a single task, while `global_routing.py` is a filesystem installer scoped to
a user's global config, and neither's behavior depends on the other
existing. Future readers should treat the name collision as coincidental
English-language overlap, not a code-boundary signal, and can cite this
finding doc instead of re-investigating from scratch.

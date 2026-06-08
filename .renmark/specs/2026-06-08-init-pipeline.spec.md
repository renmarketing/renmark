---
artifact_type: spec
schema_version: 1
created_at: 2026-06-08
source_sha: TBD
generator: brainstorm
related_plan: TBD
dependency_refs:
  - .renmark/research/2026-06-08-init-pipeline.research.md
  - PRD.md
  - renmark/init.py
  - renmark/bootstrap.py
  - plugin/skills/setup/SKILL.md
  - plugin/skills/init/SKILL.md
status: draft
---

# Spec — init-pipeline (init as the front-door adoption pipeline)

## Context

`/renmark:init` hard-errors today (`renmark/init.py:1295`, exit 1
"CLAUDE.md not found. Run /renmark:setup first") when `CLAUDE.md` is absent — it
only refreshes the project map and *requires* a pre-existing CLAUDE.md. Users
(matching Claude Code's native `/init`) expect `init` to *initialize* the
project. `/renmark:setup` is the actual bootstrapper, so onboarding is a
confusing two-door path and the two skills overlap (both touch
CLAUDE.md/AGENTS.md/.renmark/ + stack detection).

PRD REQ-8 was updated + human-approved this session to make `/renmark:init` the
named non-destructive adoption front door, with `/renmark:setup` as a thin
rule-block-refresh alias (Option A).

**Research unlock:** `renmark/bootstrap.py::bootstrap(repo, init_git=False)`
ALREADY scaffolds CLAUDE.md/AGENTS.md/.gitignore/.renmark/ non-destructively from
templates (existence-skip), resolving templates via `memory.template_dir()`. So
this feature is mostly *wiring existing pieces* + one new deterministic merge
function — not new construction. (See research artifact.)

## Goals

1. `/renmark:init` works in any project — with or without CLAUDE.md — and never
   dead-ends: it scaffolds what's missing, maps the code, and ends pointing at
   what to build next.
2. The CLI (`python -m renmark.init`) self-bootstraps **deterministically and
   zero-LLM**: scaffold missing files + back-fill missing rule blocks as code, so
   the orchestrator never reads CLAUDE.md/template bodies into context
   (context-hygiene + accuracy: canonical marker-delimited blocks are inserted
   byte-verbatim, unit-tested, idempotent).
3. `/renmark:setup` remains a real, lint-valid command that delegates to init's
   rule-block refresh (alias, not removed — PRD-committed).
4. Non-destructive + idempotent guarantees preserved (existence-skip on create;
   byte-equality skip on managed blocks; never overwrite hand-written content).

## Non-goals (feature-scoped)

- Removing `/renmark:setup` (PRD keeps it as an alias).
- Adding new runtime dependencies (stdlib + markdown only; reuse `bootstrap.py`,
  `memory.template_dir()`, lint's marker logic).
- Putting any LLM call into `init.py` (it stays strictly zero-LLM).
- Re-running roadmap gap discovery inside `init.py` — that's a SKILL-level
  hand-off (already wired per ADR-009), inherited unchanged.

## Architecture — the 6-step front-door pipeline

`/renmark:init` (the SKILL) orchestrates; `renmark/init.py` (the CLI) does the
deterministic work:

1. **Detect** — project state (CLAUDE.md/AGENTS.md/CHANGELOG.md/.renmark/, git,
   stack). (init.py already detects stack; SKILL surfaces state.)
2. **Scaffold-if-missing** — at the TOP of `init.run()`, before the old line-1295
   check: call `bootstrap(repo, init_git=False)` + create `CHANGELOG.md` if
   absent. After this, CLAUDE.md exists, so the old hard-error becomes a
   should-never-happen guard. Existence-skip = non-destructive.
3. **Rule-block back-fill (NEW, deterministic)** — `merge_rule_blocks()` in
   init.py: for an existing CLAUDE.md/AGENTS.md missing canonical
   `BEGIN:<name>`…`END:<name>` rule blocks, insert the template's blocks
   byte-verbatim at the right markers. Reuse the marker primitives already proven
   in `lint.lint_template_rule_blocks`. Idempotent (skip blocks already present),
   non-destructive (never edit existing block content), mirrors CLAUDE.md↔AGENTS.md.
4. **Scan & map** — existing behavior: symbols → `project-map.md`; merge the
   `BEGIN:project-stub` block; byte-equality skip.
5. **Standards** — existing behavior: `dev-standards.md` + health gaps.
6. **Roadmap `--gaps` at the end + hand off** — SKILL-level (already wired per
   ADR-009): a freshly initialized project is routed to `/renmark:roadmap` gap
   mode (nudge `/renmark:prd` if no PRD). Inherited unchanged.

`/renmark:setup` → thin alias: `skills/setup/SKILL.md` + `commands/setup.md`
stay (lint pairing green), `name: setup`, cites `next-steps.md` (aux class); body
delegates to init's rule-block-refresh (step 3) rather than duplicating scaffold
logic.

## Components

1. **`renmark/init.py`** — (a) scaffold phase at top of `run()` delegating to
   `bootstrap(init_git=False)` + CHANGELOG create; (b) NEW `merge_rule_blocks(repo,
   *, template_dir)` deterministic back-fill reusing marker logic; (c) wire it
   into `run()` after scaffold, before scan; (d) replace the hard exit-1 with a
   post-scaffold guard. Keep zero-LLM, byte-skip, bounded stdout line (extend the
   `OK …` line with a `blocks=` field).
2. **`renmark/init.py` (or a small shared helper)** — marker-merge primitive;
   reuse/extract from `lint.py`'s `_BEGIN_RE`/`_END_RE` so the linter and the
   merger share one source of truth (avoid drift).
3. **`plugin/skills/init/SKILL.md`** — redefine as the 6-step front-door pipeline;
   document scaffold + back-fill + roadmap-at-end; keep boundaries (zero-LLM CLI,
   roadmap hand-off at SKILL level).
4. **`plugin/skills/setup/SKILL.md`** — rewrite as a thin alias delegating to init's
   rule-block refresh; keep frontmatter `name: setup`, keep the `next-steps.md`
   citation (aux class).
5. **Tests** — `tests/test_init_scaffold.py` (or extend existing init tests):
   init scaffolds CLAUDE.md/AGENTS.md/CHANGELOG.md when absent (no more exit 1);
   non-destructive when present; `merge_rule_blocks` inserts missing blocks
   byte-verbatim, is idempotent, never edits existing blocks, keeps CLAUDE.md↔
   AGENTS.md in sync; stdout line reports what changed.

## Data flow

```
/renmark:init (SKILL)
  → python -m renmark.init        # deterministic, zero-LLM
       run():
         scaffold_missing → bootstrap(init_git=False) + CHANGELOG create   (existence-skip)
         merge_rule_blocks → back-fill missing BEGIN/END blocks            (verbatim, idempotent)
         scan_repo → write project-map.md + merge project-stub block       (byte-skip)
         write_standards_md → dev-standards.md + health gaps
       → bounded stdout: "OK stub=… map=… standards=… blocks=… HEALTH:…"
  → SKILL reads only the stdout line (never file bodies)
  → /renmark:roadmap --gaps hand-off (ADR-009)  |  nudge /renmark:prd if no PRD
```

## Error handling / edge cases

- Templates unreadable / `template_dir()` missing → init reports a clear error,
  does not partial-scaffold silently.
- CLAUDE.md present but malformed markers (unbalanced BEGIN/END) → `merge_rule_blocks`
  refuses to edit that block, reports it as a skipped/flagged block (never corrupts).
- Hand-modified rule block (present but altered) → treated as present; NOT
  overwritten (non-destructive — only *missing* blocks are inserted).
- AGENTS.md absent but CLAUDE.md present → scaffold creates AGENTS.md from
  template, then back-fill keeps the pair in sync.
- Re-run on a fully-initialized project → all phases byte/existence-skip → "unchanged".

## Success criteria

- `python -m renmark.init` in a repo with NO CLAUDE.md scaffolds it (+ AGENTS.md,
  CHANGELOG.md, .renmark/) and completes — **no exit 1**.
- `merge_rule_blocks` back-fills only missing canonical blocks, byte-verbatim,
  idempotent, non-destructive, CLAUDE.md↔AGENTS.md in sync — proven by unit tests.
- `init.py` stays zero-LLM; orchestrator sees only the bounded stdout line.
- `/renmark:setup` still resolves (lint command↔skill pairing green; cites
  next-steps.md) and delegates to init's refresh.
- `pytest -q`, `ruff check`, `mypy .`, and `lint_all` all green.

## Prior art & references

- Research artifact: `.renmark/research/2026-06-08-init-pipeline.research.md`
  (init.py structure, bootstrap.py reuse, setup scaffold inventory, lint pairing,
  template locations).
- Internal: `renmark/bootstrap.py` (existing scaffold), `renmark/init.py`
  (scan/map/standards), `renmark/lint.py` (`_BEGIN_RE`/`_END_RE`,
  `lint_template_rule_blocks`, `lint_command_shims`, `lint_next_steps_citation`),
  `renmark/memory.py` (`template_dir`).
- Decision: PRD REQ-8 (updated 2026-06-08), features.md Planned (Option A).

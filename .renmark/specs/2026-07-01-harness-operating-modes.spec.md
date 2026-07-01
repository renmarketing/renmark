---
artifact_type: spec
schema_version: 1
created_at: 2026-07-01T00:00:00+00:00
source_sha: c2f733e579e7da1d8e8c86490b471031ae165fdc
related_plan: null
generator: brainstorm
stale_after: null
dependency_refs:
  - .renmark/research/2026-06-25-external-skills-study.research.md
completion_state: complete
confidence: high
validation_status: validated
retry_count: 0
parser_success: true
schema_compliance: true
---

# Harness operating modes — Conductor / Orchestrator (MVP)

## Context

renmark stays a Claude Code plugin at the packaging level, but its **role** is an
**agentic-engineering / vibe-coding harness on top of Claude Code**: Claude Code is the
model/tool execution + interactive reasoning layer; renmark shapes how work is planned,
scoped, delegated, verified, documented, and kept context-efficient. The goal is to move
the user from casual vibe coding toward disciplined agentic engineering without losing speed.

This spec is the **first, smallest testable slice** of that mission: explicit **Conductor
vs Orchestrator** operating-mode selection plus the harness mission framing. A prior
reuse-check (2026-07-01) confirmed most harness machinery already exists — context hygiene
(CLAUDE.md rules, `skill_preamble` tiers, `context_budget_check`), bounded ≤5-line subagent
summaries, task isolation (G11), memory files, verification stages + the P8 behavior tier,
and Codex-as-worker routing. **Only mode selection is fully net-new; help-framing and the
subagent-contract fields are partial.** True dynamic skill loading is deliberately **deferred**
to a follow-up feature.

PRD alignment: **aligned** (no drift) — deepens REQ-5 (orchestrator never accumulates),
REQ-1 (vibe-coder entry + expert exposure), and multi-LLM routing; adds no net-new product scope.

## Goals

1. A persisted **operating mode** (`conductor` | `orchestrator`) selected once per session,
   surviving `/clear`, with a smart per-skill default and an override command.
2. Mode changes behavior in a **clear, testable** way — `skill_preamble` emits a
   mode-specific directive line, asserted by the deterministic behavior tier (AC#3 + AC#10).
3. `/renmark:help` and the CLAUDE.md/AGENTS.md rule blocks **reframe renmark's mission** as
   the harness model and document the two modes.
4. **Existing workflows keep working** — no new pause on auto-routing beyond a single
   first-time mode ask; no hard dispatch guards.

## Non-goals (feature-scoped)

- **True dynamic skill loading** (metadata-upfront / body-on-demand; static/dynamic/memory/
  task-local context separation) — deferred to a follow-up feature.
- **Hard dispatch guards** — Conductor mode guides via prose/preamble only; it does NOT
  programmatically block subagent dispatch (rejected as too risky to existing pipelines).
- Reworking context hygiene, memory/docs, verification, or Codex routing — these already
  exist and are only *referenced* by the mode behavior, not rebuilt.
- Product-level direction changes — see `PRD.md`; none required (alignment confirmed).

## Architecture

**Mode state — `renmark/mode.py` (new).** Persists to `.renmark/state/mode.json`
(gitignored runtime, mirrors `last-skill.json`; NOT committed `config.json`, so mode is
per-checkout/session, not shared across teammates). API:
- `read_mode(repo) -> "conductor" | "orchestrator" | None`
- `set_mode(repo, mode) -> None`
- `clear_mode(repo) -> None`
- `default_mode_for_skill(skill) -> "conductor" | "orchestrator"`
- Corrupt/missing file → `None` (never raises), mirroring existing state readers.

"Ask once" semantics: mode is asked only when `read_mode` returns `None`. Because it
persists on disk it survives `/clear`; the override command (or `clear_mode`) is how the
user changes or resets it.

**Smart default map** (`default_mode_for_skill`):
- Conductor default: `debug`, `brainstorm` (interactive, small-step, exploratory).
- Orchestrator default: `start`, `feature`, `orchestrate`, `finish`, `loop` (goal-level,
  multi-step, benefits from parallel scoped subagents).
- `roadmap` / meta skills: advisory — default orchestrator, but never force a mode prompt.

**Preamble integration — `lifecycle.skill_preamble(repo, skill)`.** Extend the existing
preamble (which already resolves domain + runs `context_budget_check`):
- If a mode is set → append one directive line, e.g.
  *"Operating mode: Orchestrator — goal-level; use narrow scoped subagents where useful,
  load skills on demand, review outcomes not keystrokes."* / *"Operating mode: Conductor —
  hands-on; prefer single-file scoped edits, avoid subagents unless necessary, explain the
  next move before editing."*
- If unset AND the skill is a meaningful entry point → return a **choose-mode hint** telling
  the orchestrator to ask the user (Conductor vs Orchestrator) via `AskUserQuestion`, with
  `default_mode_for_skill(skill)` pre-selected as `(Recommended)`; the skill then calls
  `set_mode`.
- Ordering must preserve the existing record-before-check contract (load-bearing per
  [[project_p3_preamble_tier_queued]]).

**CLI override — `renmark-execute`.** Add `--set-mode conductor|orchestrator`,
`--get-mode`, `--clear-mode` (mirrors `--set-proactive`). This is the session-level
override surface referenced by the SKILL.md blocks and help.

**SKILL.md behavior blocks.** Add a short `## Operating mode` section to the pipeline skills
(`start`, `feature`, `debug`, `roadmap`, `finish`, `orchestrate`) describing the concrete
Conductor-vs-Orchestrator delta for that skill (≤6 lines each). Kept brief — the preamble
line is the enforced/tested surface; the block is the human-readable elaboration.

**Help + rule blocks.** Reframe `plugin/skills/help/SKILL.md` (and `plugin/commands/help.md`
if it carries content) from "guided build assistant" to the harness mission, with sections
for Conductor Mode, Orchestrator Mode, context hygiene, subagent discipline, memory/docs,
and verification. Add a mirrored **"Operating modes"** rule block to `CLAUDE.md` **and**
`AGENTS.md` (same commit) documenting the two modes, smart defaults, ask-once semantics, and
the override command — explicitly noting the mode ask must NOT become a per-entry gate that
breaks auto-routing.

## Data flow

1. User invokes a meaningful workflow (e.g. `/renmark:feature`).
2. Skill calls `lifecycle.skill_preamble(repo, skill)`.
3. Preamble reads mode. Unset + entry skill → returns choose-mode hint → skill asks via
   `AskUserQuestion` (smart default recommended) → `mode.set_mode(...)`.
4. Set → preamble returns the mode directive line; orchestrator follows it for the workflow.
5. User can override anytime: `renmark-execute --set-mode conductor` (or a thin
   `/renmark:mode`-style surface if desired later — out of MVP).

## Error handling

- Corrupt/absent `mode.json` → `read_mode` returns `None` (re-ask), never raises.
- Invalid `--set-mode` value → non-zero exit + clear message; state unchanged.
- Preamble mode line is additive; if mode logic errors it must degrade to the existing
  preamble output (mode is enhancement, not a hard dependency of the pipeline).

## Testing

- `tests/test_mode.py` — round-trip read/set/clear, corrupt-file → None, unknown-field drop,
  `default_mode_for_skill` mapping for every pipeline skill.
- `tests/test_lifecycle.py` — `skill_preamble` emits the Conductor line vs the Orchestrator
  line by mode; unset + entry skill → choose-mode hint; preamble degrades gracefully on error.
- `tests/behavioral/mode.behavior.json` — deterministic behavior-tier case asserting the
  `skill_preamble` output for the SAME skill **differs** between Conductor and Orchestrator
  (the load-bearing AC#3/#10 proof; CI-safe, no model call).
- Full suite (`pytest -q`), `ruff check`, `mypy renmark/mode.py` must stay green;
  existing behavior/verify tests must not regress (AC#9).

## Success criteria (MVP subset of the 10 ACs)

- **AC1** mission defined as harness-on-Claude-Code — ✅ (help + rule blocks).
- **AC2** asks Conductor/Orchestrator at the right entry points — ✅ (ask-once + smart default).
- **AC3** each mode changes behavior testably — ✅ (preamble line + behavior test).
- **AC4** context-hygiene enforced/guided — ✅ referenced (already exists; modes reinforce it).
- **AC5** dynamic skill loading — ⏸ **deferred** (follow-up feature; explicitly out of scope).
- **AC6** subagents scoped/deliberate — ✅ already exists; Orchestrator block reinforces it.
- **AC7** memory/docs lightweight/structured — ✅ already exists.
- **AC8** help explains the harness model — ✅.
- **AC9** existing workflows still work — ✅ (no per-entry gate, no hard guards; suite green).
- **AC10** tests confirm new behavior — ✅ (unit + behavior tier).

## Prior art & references

- Internal reuse-check (2026-07-01): mode-selection = net-new; help-framing + subagent-contract
  fields = partial; everything else already exists.
- External skills study — `.renmark/research/2026-06-25-external-skills-study.research.md`
  (superpowers / gstack / mattpocock; informed the trigger-only + disable-model-invocation work).
- Anchor: "The New SDLC With Vibe Coding" (Agent = Model + Harness; harness ~90%).
- Related but separate thread: P8 eval-tier host-runner (the verification half of the same mission).

## Follow-up (post-MVP)

- **True dynamic skill loading** — the deferred AC5 gap (metadata upfront, body on demand;
  static/dynamic/memory/task-local separation). Its own brainstorm/spec.
- **Subagent-contract fields** — add explicit stop-condition + no-scope-expansion + required-
  skills-only fields to the dispatch template (partial today); small, could fold in here or next.

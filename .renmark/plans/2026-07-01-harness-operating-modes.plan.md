---
artifact_type: plan
schema_version: 1
created_at: 2026-07-01T00:00:00+00:00
source_sha: c2f733e579e7da1d8e8c86490b471031ae165fdc
related_spec: .renmark/specs/2026-07-01-harness-operating-modes.spec.md
generator: plan
completion_state: complete
confidence: high
validation_status: unvalidated
retry_count: 0
parser_success: true
schema_compliance: true
---

# Plan — Harness operating modes (Conductor / Orchestrator MVP)

Decomposes `.renmark/specs/2026-07-01-harness-operating-modes.spec.md`. Adds a persisted
operating mode (Conductor/Orchestrator) with ask-once selection, a smart per-skill default,
and a `--set-mode` override; wires a mode-conditioned line into `skill_preamble` (the tested
surface); reframes help + rule blocks; and proves the behavior delta with the deterministic
behavior tier. **Deferred (non-goals):** true dynamic skill loading; hard dispatch guards.

**Constraints honored (CHANGELOG "Do not change" guards):**
- Mode ask stays **ask-once** (never a per-entry gate) so auto-routing keeps working; no programmatic subagent blocking.
- Preamble edit MUST preserve the load-bearing record-before-check ordering (P3 tier work).
- Behavior-tier deterministic cases MUST carry a **non-empty** assertion set (P8 guard).
- `CLAUDE.md` ↔ `AGENTS.md` rule blocks are mirrored (T9 then T10; identical block).

Waves: **Group 1** foundation + docs (no deps) → **Group 2** code depending on `mode.py` /
mirror → **Group 3** tests + behavior case depending on the code.

---

### Task 1: mode state module
- **mode:** A
- **target:** renmark/mode.py
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 1
- **est_tokens:** 700
- **est_cost_usd:** 0.03
- **verifier:** set -o pipefail; python -c "from renmark.mode import read_mode,set_mode,clear_mode,default_mode_for_skill; import tempfile; d=tempfile.mkdtemp(); set_mode(d,'conductor'); assert read_mode(d)=='conductor'; clear_mode(d); assert read_mode(d) is None; assert default_mode_for_skill('debug')=='conductor'; assert default_mode_for_skill('orchestrate')=='orchestrator'" 2>&1 | tail -5
- **serves:** new
- **spec:**
  New module persisting the operating mode to `.renmark/state/mode.json` (gitignored runtime;
  mirror the read/write style of existing state readers — corrupt/missing → return None, never raise).
  API: `read_mode(repo) -> "conductor"|"orchestrator"|None`; `set_mode(repo, mode)` (validate the
  value, raise ValueError on unknown); `clear_mode(repo)`; `default_mode_for_skill(skill) -> "conductor"|"orchestrator"`.
  Default map: conductor for `debug`, `brainstorm`; orchestrator for `start`, `feature`,
  `orchestrate`, `finish`, `loop`; orchestrator fallback for anything else (incl. `roadmap`/meta).
  Type-clean under mypy. Do NOT touch lifecycle or CLI here.

### Task 2: help mission reframing
- **mode:** B
- **target:** plugin/skills/help/SKILL.md
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 1
- **est_tokens:** 800
- **est_cost_usd:** 0.03
- **verifier:** grep -qi "conductor" plugin/skills/help/SKILL.md && grep -qi "orchestrator mode" plugin/skills/help/SKILL.md && grep -qi "harness" plugin/skills/help/SKILL.md
- **serves:** REQ-1
- **spec:**
  Reframe the overview from "guided build assistant" to renmark's mission as an
  **agentic-engineering / vibe-coding harness on top of Claude Code**. Add concise sections:
  Conductor Mode, Orchestrator Mode (what each changes), context hygiene, subagent discipline,
  memory/docs, verification. Mention the ask-once mode selection + `renmark-execute --set-mode`
  override. Keep the existing command list intact. Do not remove existing help content — augment it.

### Task 3: CLAUDE.md operating-modes rule block
- **mode:** B
- **target:** CLAUDE.md
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 1
- **est_tokens:** 450
- **est_cost_usd:** 0.03
- **verifier:** grep -qi "Operating mode" CLAUDE.md && grep -qi "conductor" CLAUDE.md && grep -qi "set-mode" CLAUDE.md
- **serves:** REQ-5
- **spec:**
  Add a new "## Operating modes (Conductor / Orchestrator)" rule block. Content: the two modes and
  how each shapes behavior; ask-once + persisted (survives /clear) + smart per-skill default;
  override via `renmark-execute --set-mode conductor|orchestrator` (`--get-mode`, `--clear-mode`).
  Explicitly state the mode ask MUST stay ask-once, never a per-entry gate that breaks auto-routing,
  and Conductor never programmatically blocks subagents (guidance only). Keep the block concise.
  Note at the end that this block is mirrored in AGENTS.md.

### Task 4: feature SKILL.md mode block
- **mode:** B
- **target:** plugin/skills/feature/SKILL.md
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 1
- **est_tokens:** 250
- **est_cost_usd:** 0.00
- **verifier:** grep -qi "conductor" plugin/skills/feature/SKILL.md && grep -qi "orchestrator" plugin/skills/feature/SKILL.md
- **serves:** new
- **spec:**
  Add a short "## Operating mode" section (≤6 lines): in Orchestrator mode (feature's default),
  favor goal-level execution with narrow scoped subagents; in Conductor mode, keep changes
  single-file/tight and explain the next move before editing. Reference the ask-once selection.
  Do not alter existing pipeline steps.

### Task 5: debug SKILL.md mode block
- **mode:** B
- **target:** plugin/skills/debug/SKILL.md
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 1
- **est_tokens:** 250
- **est_cost_usd:** 0.00
- **verifier:** grep -qi "conductor" plugin/skills/debug/SKILL.md && grep -qi "orchestrator" plugin/skills/debug/SKILL.md
- **serves:** new
- **spec:**
  Add a short "## Operating mode" section (≤6 lines): Conductor is debug's default (hands-on,
  small-step, minimal context, explain before editing); Orchestrator may fan out scoped
  investigation subagents for large surfaces. Keep the Iron Law / root-cause steps unchanged.

### Task 6: orchestrate SKILL.md mode block
- **mode:** B
- **target:** plugin/skills/orchestrate/SKILL.md
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 1
- **est_tokens:** 250
- **est_cost_usd:** 0.00
- **verifier:** grep -qi "conductor" plugin/skills/orchestrate/SKILL.md && grep -qi "orchestrator" plugin/skills/orchestrate/SKILL.md
- **serves:** new
- **spec:**
  Add a short "## Operating mode" section (≤6 lines): Orchestrator is the default (parallel scoped
  subagents, Codex offload, review outcomes); in Conductor mode, prefer serial single-task
  execution with tighter user checkpoints. Do not change the isolation/aggregation rules.

### Task 7: start SKILL.md mode block
- **mode:** B
- **target:** plugin/skills/start/SKILL.md
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 1
- **est_tokens:** 250
- **est_cost_usd:** 0.00
- **verifier:** grep -qi "conductor" plugin/skills/start/SKILL.md && grep -qi "orchestrator" plugin/skills/start/SKILL.md
- **serves:** new
- **spec:**
  Add a short "## Operating mode" section (≤6 lines): start defaults to Orchestrator for goal-level
  build-out; note that the first meaningful workflow is where the mode is chosen (ask-once). Keep
  existing new-build steps intact.

### Task 8: skill_preamble mode integration
- **mode:** B
- **target:** renmark/lifecycle.py
- **complexity:** hard
- **executor:** opus
- **parallel_group:** 2
- **est_tokens:** 650
- **est_cost_usd:** 0.16
- **verifier:** set -o pipefail; { mypy renmark/lifecycle.py && python -c "import inspect, renmark.lifecycle as L; s=inspect.getsource(L.skill_preamble); assert 'mode' in s"; } 2>&1 | tail -5
- **serves:** REQ-5
- **spec:**
  Integrate operating mode into `skill_preamble(repo, skill)` (imports `renmark.mode`).
  When a mode is set, append ONE directive line to the returned hint: Conductor → "Operating mode:
  Conductor — hands-on; prefer single-file scoped edits, avoid subagents unless necessary, explain
  the next move before editing." Orchestrator → "Operating mode: Orchestrator — goal-level; use
  narrow scoped subagents where useful, load skills on demand, review outcomes not keystrokes."
  When unset AND `skill` is a meaningful entry point (start/feature/debug/roadmap/finish/orchestrate),
  return a choose-mode hint instructing the orchestrator to ask Conductor vs Orchestrator via
  AskUserQuestion with `mode.default_mode_for_skill(skill)` as the recommended default, then persist
  via `mode.set_mode`. CRITICAL: preserve the existing record-before-check ordering and the tiered
  preamble behavior — mode is additive and must degrade gracefully (any mode error → existing
  preamble output unchanged). Do not edit tests here.

### Task 9: CLI mode flags
- **mode:** B
- **target:** renmark/cli/_engine.py
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 2
- **est_tokens:** 550
- **est_cost_usd:** 0.03
- **verifier:** set -o pipefail; { mypy renmark/cli/_engine.py && python -c "import renmark.cli._engine"; } 2>&1 | tail -5
- **serves:** new
- **spec:**
  Add `--set-mode {conductor,orchestrator}`, `--get-mode`, and `--clear-mode` flags mirroring the
  existing `--set-proactive` wiring. `--set-mode` calls `mode.set_mode` and prints confirmation;
  `--get-mode` prints the current mode (or "unset"); `--clear-mode` calls `mode.clear_mode`. Invalid
  value → non-zero exit with a clear message, state unchanged. Keep all existing flags/behavior intact.

### Task 10: AGENTS.md mirror block
- **mode:** B
- **target:** AGENTS.md
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 2
- **est_tokens:** 450
- **est_cost_usd:** 0.00
- **verifier:** grep -qi "Operating mode" AGENTS.md && grep -qi "conductor" AGENTS.md && grep -qi "set-mode" AGENTS.md
- **serves:** REQ-5
- **spec:**
  Mirror the exact "## Operating modes (Conductor / Orchestrator)" rule block added to CLAUDE.md in
  Task 3 — copy it verbatim so the two files stay in sync (project mirror rule). Content identical;
  only adjust the closing "mirrored in ..." pointer to reference CLAUDE.md.

### Task 11: mode.py unit tests
- **mode:** A
- **target:** tests/test_mode.py
- **complexity:** medium
- **executor:** codex
- **parallel_group:** 3
- **est_tokens:** 800
- **est_cost_usd:** 0.02
- **verifier:** set -o pipefail; python -m pytest tests/test_mode.py -q 2>&1 | tail -3
- **serves:** new
- **spec:**
  Unit tests for `renmark/mode.py`: set→read round-trip for both modes; clear resets to None;
  corrupt/missing `mode.json` → None (no raise); unknown-field payload dropped/None; `set_mode`
  rejects an invalid value (ValueError); `default_mode_for_skill` returns the correct default for
  every pipeline skill (debug/brainstorm→conductor; start/feature/orchestrate/finish/loop→orchestrator;
  unknown→orchestrator). Use tmp_path for the repo.

### Task 12: skill_preamble mode tests
- **mode:** B
- **target:** tests/test_lifecycle.py
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 3
- **est_tokens:** 600
- **est_cost_usd:** 0.03
- **verifier:** set -o pipefail; python -m pytest tests/test_lifecycle.py -q 2>&1 | tail -3
- **serves:** new
- **spec:**
  Add tests asserting `skill_preamble` emits the Conductor directive line when mode=conductor and the
  Orchestrator directive line when mode=orchestrator (same skill, different output — the AC#3 proof);
  unset + a meaningful entry skill returns the choose-mode hint; mode errors degrade to the existing
  preamble output. Do not weaken existing preamble/ordering tests. (Routed sonnet: codex has hit
  verifier-env exit-127 on this file historically.)

### Task 13: CLI mode-flag tests
- **mode:** A
- **target:** tests/test_mode_cli.py
- **complexity:** medium
- **executor:** codex
- **parallel_group:** 3
- **est_tokens:** 600
- **est_cost_usd:** 0.02
- **verifier:** set -o pipefail; python -m pytest tests/test_mode_cli.py -q 2>&1 | tail -3
- **serves:** new
- **spec:**
  Tests exercising the `--set-mode` / `--get-mode` / `--clear-mode` CLI paths (invoke the engine
  entry the way existing CLI tests do): set persists + get reflects it; clear resets; invalid value
  exits non-zero and leaves state unchanged. Use tmp_path as the repo root.

### Task 14: mode behavior-tier case
- **mode:** A
- **target:** tests/behavioral/mode.behavior.json
- **complexity:** medium
- **executor:** codex
- **parallel_group:** 3
- **est_tokens:** 350
- **est_cost_usd:** 0.01
- **verifier:** bin/renmark-execute --behavior
- **serves:** REQ-5
- **spec:**
  Add a deterministic behavior-tier case (mirror tests/behavioral/roadmap.behavior.json and
  next_steps_menu.behavior.json) with `skill: "feature"`, `deterministic.call: "lifecycle.skill_preamble"`.
  RETARGETED (the behavior adapter calls skill_preamble on the real repo and cannot pre-set mode without
  editing behavior.py, which is out of scope): assert the UNSET-mode entry-skill preamble emits the
  choose-mode PROMPT — proving mode-awareness is wired into the live preamble (AC#2). Assertions
  (non-empty per the P8 guard): `contains:Operating mode: not yet set`, `contains:Conductor vs Orchestrator`.
  The by-mode DIRECTIVE diff (Conductor line vs Orchestrator line) is proven separately by the T12
  unit tests, which CAN set mode via a tmp repo. Verifier `bin/renmark-execute --behavior` (deterministic
  tier, CI-safe, no model call) must exit 0. Include an `eval` block mirroring the other cases' shape.

---

## Cost preview

| Task | Target | Exec | Group | Tokens (incl. overhead) | Cost |
|---|---|---|---|---|---|
| 1 | renmark/mode.py | sonnet | 1 | 10,700 | $0.032 |
| 2 | help/SKILL.md | sonnet | 1 | 10,800 | $0.032 |
| 3 | CLAUDE.md | sonnet | 1 | 10,450 | $0.031 |
| 4 | feature/SKILL.md | haiku | 1 | 10,250 | $0.001 |
| 5 | debug/SKILL.md | haiku | 1 | 10,250 | $0.001 |
| 6 | orchestrate/SKILL.md | haiku | 1 | 10,250 | $0.001 |
| 7 | start/SKILL.md | haiku | 1 | 10,250 | $0.001 |
| 8 | renmark/lifecycle.py | opus | 2 | 10,650 | $0.160 |
| 9 | renmark/cli/_engine.py | sonnet | 2 | 10,550 | $0.032 |
| 10 | AGENTS.md | haiku | 2 | 10,450 | $0.001 |
| 11 | tests/test_mode.py | codex | 3 | 800 | $0.020 |
| 12 | tests/test_lifecycle.py | sonnet | 3 | 10,600 | $0.032 |
| 13 | tests/test_mode_cli.py | codex | 3 | 600 | $0.020 |
| 14 | tests/behavioral/mode.behavior.json | codex | 3 | 350 | $0.010 |

**Total: 14 tasks · 3 waves · executors haiku×5, codex×3, sonnet×5, opus×1 · ~$0.37**

Deferred to fast-follow (still get the preamble mode line, no elaboration block):
`roadmap` and `finish` SKILL.md "## Operating mode" blocks — out of this MVP to stay under budget/scope.

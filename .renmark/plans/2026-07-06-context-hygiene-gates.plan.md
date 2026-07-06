---
artifact_type: plan
schema_version: 1
created_at: 2026-07-06T00:00:00Z
source_sha: e5d39f0
generator: sonnet
related_spec: null
stale_after: 2026-10-06T00:00:00Z
dependency_refs:
  - renmark/lifecycle.py
  - renmark/state/skills.py
  - renmark/config.py
  - renmark/cli/_engine.py
  - CLAUDE.md
  - AGENTS.md
  - plugin/skills/_shared/context-taxonomy.md
  - tests/test_lifecycle.py
  - tests/test_config.py
---

# Hard-stop context hygiene gates (selectable AskUserQuestion menus)

**Branch:** `feature/context-hygiene-gates`
**Base sha:** `e5d39f0`

## Goal

Replace the existing advisory "consider /clear" and dead "consider /compact" hints in
`skill_preamble` with **blocking AskUserQuestion menus** that surface as selectable options —
never pretending to run `/compact` or `/clear` directly, but making context hygiene
unavoidable by requiring the user to acknowledge and choose before the skill proceeds.

Two gates:

**1. Cross-domain clear gate (Python-detectable)**
When `context_budget_check` detects a domain transition, `skill_preamble` returns a
structured message prefixed with `CONTEXT_GATE_CLEAR:` and persists a compact checkpoint.
The CLAUDE.md/AGENTS.md rule says: on that prefix, use `AskUserQuestion` to present:
  - (Recommended) Stop here — I will run /clear then /renmark:resume
  - Continue in same context (this step only)
  - Queue this as next task after current work finishes
  - Cancel
Bypass skills (`finish`, `approve`, `resume`): advisory hint only — these must not be
blocked mid-stream.

**2. Compact gate (rule-enforced — Python cannot detect % context utilization)**
Harness does not expose context size to Python. Gate is enforced by a strengthened
CLAUDE.md/AGENTS.md rule at >=120k tokens (configurable via `compact_gate_tokens` in
`.renmark/config.json`). Rule instructs Claude to run `renmark-execute --compact-checkpoint`
(persists resume state), then use `AskUserQuestion` to present:
  - (Recommended) Stop here — I will run /compact then /renmark:resume
  - Continue this step only (once)
  - Adjust threshold: renmark-execute --set-compact-gate-tokens <value>
  - Disable for this branch: renmark-execute --set-compact-gate-tokens 0

## Key invariants

- Neither gate claims to invoke `/compact` or `/clear` — those are host-level commands.
- Selecting "Stop here" means: Python persists the checkpoint, Claude stops the skill body
  and prints the command the user must run manually.
- `persist_compact_checkpoint` is the Python helper that writes the resume state.
- Configurable threshold stored in `.renmark/config.json["compact_gate_tokens"]`, default
  120,000 (proxy for 60% of Sonnet 200k window, since real % is not detectable).

## Out of scope

- Claude Code SDK control or programmatic `/compact`/`/clear` invocation.
- Real %-context detection from inside a skill — harness does not expose it.
- Moving thresholds into `skills.py` — they belong in `config.py` with other user preferences.

---

## Tasks

### Task 1: renmark/config.py — compact_gate_tokens helper
- **mode:** B
- **target:** renmark/config.py
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 1
- **est_tokens:** 400
- **est_cost_usd:** 0.0001
- **verifier:** python3 -c "from renmark.config import compact_gate_tokens; from pathlib import Path; assert compact_gate_tokens(Path('.')) == 120_000; print('OK')"
- **serves:** new
- **spec:**
  Following the exact same pattern as `is_proactive`/`set_proactive`, add:
  - `compact_gate_tokens(repo: str | Path) -> int` — reads `config.json["compact_gate_tokens"]`.
    Must be a non-negative int; 0 is valid and means disabled (gate never fires).
        Any missing/negative/non-int value returns the default 120_000.
    Never raises.
  - `set_compact_gate_tokens(repo: str | Path, value: int) -> None` — reads existing config,
    updates only the `compact_gate_tokens` key, writes back. Never raises. A value of 0
    effectively disables the gate (threshold never reached in practice).
  Place both after `set_eval_runner_cmd`. Do not touch any other key or function.

### Task 2: renmark/lifecycle.py — persist_compact_checkpoint + cross-domain gate upgrade
- **mode:** B
- **target:** renmark/lifecycle.py
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 1
- **est_tokens:** 1400
- **est_cost_usd:** 0.0011
- **verifier:** python3 -m pytest tests/test_lifecycle.py -q -x 2>&1 | tail -5
- **serves:** new
- **spec:**
  Three changes to `renmark/lifecycle.py`:

  **1. `_CONTEXT_BYPASS_SKILLS: frozenset[str]`** (new module-level constant near `_MODE_ENTRY_SKILLS`):
  - Value: `frozenset({"finish", "approve", "resume"})`

  **2. `persist_compact_checkpoint(repo, skill, reason) -> None`** (new exported function):
  - `reason` is "compact" or "clear".
  - Writes `.renmark/state/compact_checkpoint.json`:
    `{"skill": "<skill>", "reason": "<reason>", "resume_cmd": "/renmark:resume", "timestamp": "<iso>"}`
  - Use `from .state._core import state_dir, now_iso` (or via `from . import state as _state`).
  - Creates parent dir. Wraps in try/except. Never raises.

  **3. Upgrade `skill_preamble` clear-verdict to CONTEXT_GATE_CLEAR prefix**:
  - Read `last = _state.last_skill_invocation(repo)` BEFORE `context_budget_check` call,
    so `prev_domain` is captured before `record_skill_invocation` overwrites it.
  - When `verdict == "clear"`:
    - If `skill in _CONTEXT_BYPASS_SKILLS`: existing advisory fragment (unchanged).
    - Else: call `persist_compact_checkpoint(repo, skill, reason="clear")`, return immediately:
      ```
      CONTEXT_GATE_CLEAR: cross-domain transition detected (prev: `{prev_domain}` -> `{domain}`).
      State persisted to .renmark/state/compact_checkpoint.json.
      Present the user with AskUserQuestion before proceeding with this skill:
        header: "Context hygiene"
        question: "Domain change detected. Run /clear to start fresh (memory survives), or continue?"
        options:
          1. Stop here — I will run /clear then /renmark:resume (Recommended)
          2. Continue in same context (this step only)
          3. Queue this as next task after current work finishes
          4. Cancel
      ```
      where `prev_domain` = `last.get("domain", "?") if last else "?"`.
  - The `verdict == "compact"` advisory path stays unchanged.

### Task 3: renmark/cli/_engine.py — --compact-checkpoint + --set-compact-gate-tokens
- **mode:** B
- **target:** renmark/cli/_engine.py
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 1
- **est_tokens:** 500
- **est_cost_usd:** 0.0001
- **verifier:** python3 -m renmark --compact-checkpoint --repo /tmp && echo OK
- **serves:** new
- **spec:**
  Add two flags in the --set-proactive/--set-headless group:

  `--compact-checkpoint`: calls `lifecycle.persist_compact_checkpoint(repo, "manual", "compact")`
  then prints the 2-step resume instructions. Returns 0.

  `--set-compact-gate-tokens TOKENS`: calls `config.set_compact_gate_tokens(repo, value)`,
  prints confirmation. Returns 0. Document that 0 disables the gate.

### Task 4: CLAUDE.md + AGENTS.md — upgrade context-budget rules to blocking menus
- **mode:** B
- **target:** CLAUDE.md, AGENTS.md
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 2
- **est_tokens:** 700
- **est_cost_usd:** 0.0001
- **verifier:** grep -q "CONTEXT_GATE_CLEAR" CLAUDE.md && grep -q "compact-checkpoint" CLAUDE.md && grep -q "AskUserQuestion" CLAUDE.md && grep -q "CONTEXT_GATE_CLEAR" AGENTS.md && grep -q "compact-checkpoint" AGENTS.md && grep -q "AskUserQuestion" AGENTS.md
- **serves:** updated
- **spec:**
  Replace the `## Context budget — /compact at 60%, /clear on subject change` rule block with:

    ## Context budget — selectable hygiene gates at 60% and on domain change

    Two context hygiene gates as blocking AskUserQuestion menus (not silent hints). Neither gate
    claims to invoke /compact or /clear — those are host-level commands. Selecting "Stop here"
    means Python persists state and the skill stops cleanly.

    Cross-domain clear gate (Python-enforced): When skill_preamble returns a string starting
    with CONTEXT_GATE_CLEAR:, use AskUserQuestion with the choices described in that message
    BEFORE executing any skill steps. If user selects "Stop here", print:
      "State saved. Run: /clear — then run: /renmark:resume"
    Bypass skills: finish, approve, resume (advisory only — flows must not be blocked mid-stream).

    Compact gate (rule-enforced — Python cannot detect % context):
    - >=120k tokens (configurable via compact_gate_tokens in .renmark/config.json, default 120k):
      MUST present AskUserQuestion before starting any new skill:
      header: "Context hygiene"
      question: "Context window is at 60%+. Continuing may reduce accuracy."
      option 1 (Recommended): "Stop here — I will run /compact then /renmark:resume"
      option 2: "Continue this step only (once)"
      option 3: "Raise threshold: renmark-execute --set-compact-gate-tokens <value>"
      option 4: "Disable for this branch: renmark-execute --set-compact-gate-tokens 0"
      If user selects option 1: run renmark-execute --compact-checkpoint to persist state,
      then print: "Run: /compact — then run: /renmark:resume"
    - >=160k tokens: Refuse new long skills (orchestrate, loop, audit) until /compact or /clear.

    Cross-domain transition always triggers the clear gate regardless of token count.

  Also update Context thresholds rule to note the 120k threshold is configurable.
  Mirror all changes identically in AGENTS.md.

### Task 5: plugin/skills/_shared/context-taxonomy.md — document the two gate types
- **mode:** B
- **target:** plugin/skills/_shared/context-taxonomy.md
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 2
- **est_tokens:** 400
- **est_cost_usd:** 0.0001
- **verifier:** grep -q "CONTEXT_GATE_CLEAR" plugin/skills/_shared/context-taxonomy.md
- **serves:** updated
- **spec:**
  Add "Context hygiene gates" section (under 20 lines) covering:
  - Clear gate: Python-enforced via skill_preamble/context_budget_check; persist_compact_checkpoint
    called; CONTEXT_GATE_CLEAR prefix triggers AskUserQuestion. Bypass: finish/approve/resume.
  - Compact gate: rule-enforced; threshold in config.json["compact_gate_tokens"] (default 120k,
    0=disabled); CLI: renmark-execute --compact-checkpoint.
  - persist_compact_checkpoint(repo, skill, reason): writes compact_checkpoint.json for /renmark:resume.

### Task 6: tests/test_lifecycle.py — gate tests
- **mode:** B
- **target:** tests/test_lifecycle.py
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 3
- **est_tokens:** 900
- **est_cost_usd:** 0.0007
- **verifier:** python3 -m pytest tests/test_lifecycle.py -q -x 2>&1 | tail -5
- **serves:** new
- **spec:**
  Add four tests after test_cross_domain_transition:

  test_skill_preamble_cross_domain_emits_gate_prefix: records debug invocation, calls
  skill_preamble(tmp_path, "start"), asserts hint starts with "CONTEXT_GATE_CLEAR:" and
  contains "/clear", "/renmark:resume", "AskUserQuestion".

  test_skill_preamble_bypass_skill_no_gate_prefix: records debug invocation, calls
  skill_preamble(tmp_path, "finish"), asserts hint is None or does not start with
  "CONTEXT_GATE_CLEAR:".

  test_persist_compact_checkpoint_writes_file: calls persist_compact_checkpoint(tmp_path,
  "start", "clear"), asserts .renmark/state/compact_checkpoint.json exists with correct
  {skill, reason, resume_cmd, timestamp} fields.

  test_persist_compact_checkpoint_never_raises: calls with "/nonexistent/path/xyz" —
  must not raise.

### Task 7: tests/test_config.py — compact_gate_tokens tests
- **mode:** B
- **target:** tests/test_config.py
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 3
- **est_tokens:** 400
- **est_cost_usd:** 0.0001
- **verifier:** python3 -m pytest tests/test_config.py -q -x 2>&1 | tail -3
- **serves:** new
- **spec:**
  Add five tests:
  1. default returns 120_000
  2. set then get (e.g. 80_000) returns that value
  3. set 0 then get returns 0 (disabled — 0 is valid, not treated as missing)
  4. negative value stored in config.json returns 120_000 (not 0)
  5. non-int config value returns 120_000

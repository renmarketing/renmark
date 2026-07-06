---
artifact_type: plan
schema_version: 1
created_at: 2026-07-06T00:00:00Z
source_sha: f95f4e3
generator: sonnet
related_spec: null
stale_after: 2026-10-06T00:00:00Z
dependency_refs: [plugin/skills/_shared/subagent-profiles.md, renmark/subagent_profiles.py, renmark/dispatch.py, plugin/skills/orchestrate/SKILL.md]
---

# Upgrade renmark to Claude-native subagent definitions + wave-level Workflow fan-out

**Branch:** `feature/agent-team-migration`
**Base sha:** `f95f4e3`
**Goal:** Two narrow upgrades, not a substrate migration:

1. Convert the 8 specialized roles in `plugin/skills/_shared/subagent-profiles.md` from
   prompt-only descriptions into real Claude Code native subagent-type files
   (`.claude/agents/*.md`) with enforced tool allowlists and model tiers, so orchestrate's
   Agent calls actually get restricted tools instead of relying on prose to describe intent.
2. Add an optional wave-level `Workflow`-tool fan-out path to `/renmark:orchestrate` for
   dispatching multiple `needs_agent` (Claude-executor) tasks in one wave concurrently,
   **without** touching the deterministic Python policy layer (`dispatch.py`'s wave
   grouping/validation, `subagent_gate.py`'s pre-dispatch challenge, `cost.py`'s estimate/ack
   gate, or the G11 isolation contract).

## Out of scope (decided during scoping, do not re-propose without revisiting)

- **Whole-plan Workflow-native execution.** `Workflow`'s `resumeFromRunId` is same-session
  only — it cannot survive `/clear`, which would break G12 (`lifecycle.json`/`pipeline.json`
  cross-session resumability, load-bearing since v0.24.0). Wave-level use only.
- **Moving codex-subprocess tasks into a Workflow script.** Workflow scripts have no
  filesystem/Bash access — codex tasks stay on the existing `renmark-execute` subprocess path.
- **Reimplementing G11 isolation validation in JS.** `SubagentOutput`/`IsolationViolation`
  stay Python-only; Workflow-returned results are validated back through
  `dispatch.parse_subagent_response` after the fact, never inline in the script.
- **`general-purpose` gets no `.claude/agents/general-purpose.md` file** — it's the harness's
  built-in fallback name already; no native file to author for it.

## Tasks

### Task 1: subagent-profiles.md — document native agent mapping + fix model-tier drift
- **mode:** B
- **target:** plugin/skills/_shared/subagent-profiles.md
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 1
- **est_tokens:** 700
- **est_cost_usd:** 0.0001
- **verifier:** grep -q ".claude/agents/" plugin/skills/_shared/subagent-profiles.md && grep -q "test-writer.*haiku" plugin/skills/_shared/subagent-profiles.md
- **serves:** new
- **spec:**
  Update the role table: add a "Native agent file" column pointing each of the 8 specialized
  roles at `.claude/agents/<role>.md` (general-purpose keeps "— (built-in)"). Fix the
  pre-existing Model-tier drift against `renmark/subagent_profiles.py::PROFILES` (the actual
  code, source of truth): `test-writer` is Haiku here (not Codex — Codex isn't a valid Claude
  Code agent `model:` value; the code's `model_tier="codex"` still governs the
  `renmark-execute` dispatch path, this table's Model column is about the *native agent file*
  only), `release-manager` is Sonnet, `researcher` is Sonnet, `finish-lane-specialist` is
  Sonnet (matching the .py registry, not the old table values). Replace rule 5 ("UI may still
  display general-purpose") — it's now stale: say instead that orchestrate passes
  `subagent_type: <role>` on the Agent call when `subagent_profiles.has_native_agent_file(role)`
  is true, so the harness now actually enforces the role's tool allowlist, not just the label.
  Do not touch any other section.

### Task 2: .claude/agents/docs-editor.md
- **mode:** A
- **target:** .claude/agents/docs-editor.md
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 1
- **est_tokens:** 300
- **est_cost_usd:** 0.0001
- **verifier:** test -f .claude/agents/docs-editor.md && grep -q "^name: docs-editor" .claude/agents/docs-editor.md
- **serves:** new
- **spec:**
  Create a Claude Code subagent-type file. Frontmatter: `name: docs-editor`, a one-line
  `description` matching the mission in `plugin/skills/_shared/subagent-profiles.md`'s
  docs-editor row ("Create/update docs, comments, and docstrings — narrow scope: source file
  + related docs"), `tools: Read, Edit, Write, Grep, Glob`, `model: haiku`. Body: 3-5 short
  lines restating the role's stop condition (file written, lint clean) and verification
  (read back, verify formatting) from the profiles table — no filler.

### Task 3: .claude/agents/code-implementer.md
- **mode:** A
- **target:** .claude/agents/code-implementer.md
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 1
- **est_tokens:** 300
- **est_cost_usd:** 0.0001
- **verifier:** test -f .claude/agents/code-implementer.md && grep -q "^name: code-implementer" .claude/agents/code-implementer.md
- **serves:** new
- **spec:**
  Same pattern as Task 2 for the code-implementer row: `tools: Read, Edit, Write, Bash, Grep,
  Glob`, `model: sonnet`. Body restates stop condition (code compiles, verifier passes) and
  verification (verifier + lint run) from the profiles table.

### Task 4: .claude/agents/test-writer.md
- **mode:** A
- **target:** .claude/agents/test-writer.md
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 1
- **est_tokens:** 300
- **est_cost_usd:** 0.0001
- **verifier:** test -f .claude/agents/test-writer.md && grep -q "^name: test-writer" .claude/agents/test-writer.md
- **serves:** new
- **spec:**
  Same pattern for the test-writer row: `tools: Read, Write, Edit, Bash, Grep, Glob`,
  `model: haiku` (note in the body: the `.py` registry's `model_tier="codex"` governs the
  separate `renmark-execute` subprocess dispatch path for this role; this native agent file
  is only reached when the harness dispatches the role via the Agent tool, where Codex is not
  a selectable model). Body restates stop condition (test file passes own syntax, verifier
  runs) and verification (`pytest`/`npm test` green).

### Task 5: .claude/agents/reviewer.md
- **mode:** A
- **target:** .claude/agents/reviewer.md
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 1
- **est_tokens:** 300
- **est_cost_usd:** 0.0001
- **verifier:** test -f .claude/agents/reviewer.md && grep -q "^name: reviewer" .claude/agents/reviewer.md
- **serves:** new
- **spec:**
  Same pattern for the reviewer row: `tools: Read, Grep, Glob, Bash`, `model: sonnet`
  (read-only — no Edit/Write in the allowlist, matching "N/A (read-only)" target in the
  profiles table). Body restates stop condition (review artifact written) and verification
  (findings JSON parses; PASS/FAIL gate).

### Task 6: .claude/agents/release-manager.md
- **mode:** A
- **target:** .claude/agents/release-manager.md
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 1
- **est_tokens:** 300
- **est_cost_usd:** 0.0001
- **verifier:** test -f .claude/agents/release-manager.md && grep -q "^name: release-manager" .claude/agents/release-manager.md
- **serves:** new
- **spec:**
  Same pattern for the release-manager row: `tools: Read, Edit, Bash, Grep, Glob`,
  `model: sonnet` (matches `renmark/subagent_profiles.py`, not the stale Haiku value in the
  old table). Body restates stop condition (version bumped, CHANGELOG appended) and
  verification (`git tag -l` confirms version).

### Task 7: .claude/agents/researcher.md
- **mode:** A
- **target:** .claude/agents/researcher.md
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 1
- **est_tokens:** 300
- **est_cost_usd:** 0.0001
- **verifier:** test -f .claude/agents/researcher.md && grep -q "^name: researcher" .claude/agents/researcher.md
- **serves:** new
- **spec:**
  Same pattern for the researcher row: `tools: Read, WebSearch, WebFetch, Grep, Glob`,
  `model: sonnet` (matches the `.py` registry). Body restates stop condition (summary
  written, sources cited) and verification (links verified, claims traceable).

### Task 8: .claude/agents/audit-reader.md
- **mode:** A
- **target:** .claude/agents/audit-reader.md
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 1
- **est_tokens:** 300
- **est_cost_usd:** 0.0001
- **verifier:** test -f .claude/agents/audit-reader.md && grep -q "^name: audit-reader" .claude/agents/audit-reader.md
- **serves:** new
- **spec:**
  Same pattern for the audit-reader row: `tools: Read, Grep, Glob`, `model: haiku` (read-only,
  no Write/Edit/Bash — matches "no source code" scope). Body restates stop condition
  (artifact read, summary written) and verification (summary JSON parses; confidence ≥medium).

### Task 9: .claude/agents/finish-lane-specialist.md
- **mode:** A
- **target:** .claude/agents/finish-lane-specialist.md
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 1
- **est_tokens:** 300
- **est_cost_usd:** 0.0001
- **verifier:** test -f .claude/agents/finish-lane-specialist.md && grep -q "^name: finish-lane-specialist" .claude/agents/finish-lane-specialist.md
- **serves:** new
- **spec:**
  Same pattern for the finish-lane-specialist row: `tools: Read, Bash, Grep, Glob`,
  `model: sonnet` (matches the `.py` registry, not the stale Haiku value). Body restates stop
  condition (finish-lane checks passed, lifecycle gate advanced) and verification (lane exists
  in `renmark.finish_lanes.LANES`).

### Task 10: subagent_profiles.py — has_native_agent_file helper
- **mode:** B
- **target:** renmark/subagent_profiles.py
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 2
- **est_tokens:** 900
- **est_cost_usd:** 0.033
- **verifier:** python3 -c "from renmark import subagent_profiles; assert subagent_profiles.has_native_agent_file('docs-editor') is True; assert subagent_profiles.has_native_agent_file('general-purpose') is False; assert subagent_profiles.has_native_agent_file('not-a-role') is False; print('OK')" 2>&1 | tail -3
- **serves:** new
- **spec:**
  Add a pure function `has_native_agent_file(role: str, repo: Path | None = None) -> bool`
  to `renmark/subagent_profiles.py`, following this module's existing "never raises, safe
  fallback" contract (mirror the try/except style already used by `resolve_profile` and
  `profile_tier`). A static frozenset of the 8 specialized role names that have
  `.claude/agents/<role>.md` files (docs-editor, code-implementer, test-writer, reviewer,
  release-manager, researcher, audit-reader, finish-lane-specialist) is the primary check —
  `general-purpose` and any unknown role name always return `False`. When `repo` is passed
  (optional), additionally verify `repo / ".claude" / "agents" / f"{role}.md"` actually exists
  on disk before returning `True` (defensive — a role could be added to the static set before
  its file lands); on any filesystem error, fall back to the static-set-only answer rather
  than raising. Add a short docstring; no changes to `PROFILES`, `resolve_profile`, or
  `profile_tier`.

### Task 11: tests/test_subagent_profiles.py — has_native_agent_file tests
- **mode:** B
- **target:** tests/test_subagent_profiles.py
- **complexity:** medium
- **executor:** codex
- **parallel_group:** 3
- **est_tokens:** 700
- **est_cost_usd:** 0.02
- **verifier:** pytest -q tests/test_subagent_profiles.py
- **serves:** new
- **spec:**
  Add tests for `subagent_profiles.has_native_agent_file`: (1) each of the 8 specialized role
  names returns `True` with no `repo` arg; (2) `general-purpose` returns `False`; (3) an
  unknown/garbage role string returns `False` and does not raise; (4) with a `repo` arg
  pointing at a `tmp_path` that has a matching `.claude/agents/<role>.md` file, returns `True`;
  with a `repo` arg where the file is absent, returns `False` even though the role is in the
  static set. Follow the existing test file's fixture/assertion style — do not restructure it.

### Task 12: workflow-fanout.md — shared fragment for wave-level Workflow dispatch
- **mode:** A
- **target:** plugin/skills/_shared/workflow-fanout.md
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 2
- **est_tokens:** 1800
- **est_cost_usd:** 0.045
- **verifier:** test -f plugin/skills/_shared/workflow-fanout.md && grep -q "parse_subagent_response" plugin/skills/_shared/workflow-fanout.md
- **serves:** new
- **spec:**
  New shared reference doc (same pattern as `_shared/prd-alignment.md` and
  `_shared/reuse-check.md` — a single-source contract referenced by pointer, not inlined).
  Document the wave-level `Workflow`-tool fan-out pattern for `/renmark:orchestrate`'s Step 3b:

  - **When to use it:** only when a wave's non-codex (`needs_agent`) task count is > 1.
    A single needs_agent task in a wave stays a plain `Agent` call — Workflow ceremony isn't
    worth it for one task.
  - **What stays in Python (unchanged):** wave grouping (`dispatch.group_tasks_by_wave`),
    target-collision validation (`dispatch.validate_wave`), the pre-dispatch
    `subagent_gate`/cost-preview/ack gate, and building each task's `SubagentInput` via
    `dispatch.build_subagent_input`. None of this moves into the Workflow script.
  - **What the Workflow script does:** receives the wave's list of `SubagentInput.to_dict()`
    payloads (produced by `dispatch.build_workflow_fanout_args`, see `renmark/dispatch.py`) as
    `args`. For each item, calls `agent(prompt, {schema: SUBAGENT_OUTPUT_SCHEMA, agentType:
    item.role})` inside a `parallel()` — `agentType` is the resolved role name so each task's
    subagent gets its own tool allowlist from `.claude/agents/<role>.md` (falling back to no
    `agentType` / default when `has_native_agent_file(role)` is false). The prompt embeds the
    task_spec + verifier_expectations + the same G11 JSON-shape instruction orchestrate
    already gives Agent calls. Returns the raw array of agent() results — the script does
    **no validation** of the results itself (G11 stays Python-only).
  - **What happens after the Workflow call returns (back in Python/skill context):** each
    returned result is passed through `dispatch.parse_subagent_response()` exactly like a
    plain Agent-call result today. An `IsolationViolation` fails that one task the same way
    it does on the non-Workflow path — the fan-out mechanism doesn't change failure handling.
  - **Cost/ledger note:** do NOT use the Workflow tool's own `budget`/token tracking for
    this — `state.log_agent_call` remains the single ledger, to avoid double-counting spend
    already covered by `cost.py`'s pre-dispatch estimate.
  - Include one short example script skeleton (schema block + `parallel()` call) so skill
    authors can copy it rather than re-deriving the shape.

### Task 13: dispatch.py — build_workflow_fanout_args helper
- **mode:** B
- **target:** renmark/dispatch.py
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 2
- **est_tokens:** 1000
- **est_cost_usd:** 0.033
- **verifier:** python3 -c "from renmark import dispatch; assert hasattr(dispatch, 'build_workflow_fanout_args'); print('OK')" 2>&1 | tail -3
- **serves:** new
- **spec:**
  Add `build_workflow_fanout_args(wave: list[Task], *, dependency_summaries: list[str] |
  None = None, upstream_artifact_pointers: list[str] | None = None) -> list[dict[str, Any]]`
  to `renmark/dispatch.py`, placed near `build_subagent_input` (reuse it, don't duplicate its
  logic). For each Claude-executor task in `wave` (skip any `claude_agent.is_claude_executor`
  is False — codex tasks never go through this path), call `build_subagent_input(task,
  dependency_summaries=..., upstream_artifact_pointers=...)` and append its `.to_dict()` to
  the returned list, in the same order as `wave`. This is a pure packet-shaping function —
  it does not call the `Workflow` tool itself (Python has no access to it); it only produces
  the `args` payload the calling skill passes to a `Workflow` invocation per
  `_shared/workflow-fanout.md`. No changes to `SubagentInput`, `SubagentOutput`,
  `parse_subagent_response`, or the isolation-contract validation logic.

### Task 14: tests/test_dispatch.py — build_workflow_fanout_args tests
- **mode:** B
- **target:** tests/test_dispatch.py
- **complexity:** medium
- **executor:** codex
- **parallel_group:** 3
- **est_tokens:** 800
- **est_cost_usd:** 0.02
- **verifier:** pytest -q tests/test_dispatch.py
- **serves:** new
- **spec:**
  Add tests for `dispatch.build_workflow_fanout_args`: (1) a wave of N Claude-executor tasks
  (e.g. `executor="sonnet"`) returns N dicts in wave order, each matching
  `build_subagent_input(task).to_dict()` for that task; (2) a wave containing a mix of
  `executor="codex"` and Claude-executor tasks returns dicts only for the Claude-executor
  ones (codex tasks excluded); (3) an all-codex wave returns an empty list. Follow the
  existing test file's fixture/mock style (it already builds `Task` fixtures for
  `build_subagent_input` tests) — reuse those fixtures, don't invent new ones.

### Task 15: orchestrate/SKILL.md — wire subagent_type + wave-level Workflow fan-out
- **mode:** B
- **target:** plugin/skills/orchestrate/SKILL.md
- **complexity:** hard
- **executor:** sonnet
- **parallel_group:** 4
- **est_tokens:** 2200
- **est_cost_usd:** 0.047
- **verifier:** grep -q "workflow-fanout.md" plugin/skills/orchestrate/SKILL.md && grep -q "subagent_type" plugin/skills/orchestrate/SKILL.md && grep -q "has_native_agent_file" plugin/skills/orchestrate/SKILL.md
- **serves:** new
- **spec:**
  Update Step 3b ("Dispatch each task in this wave (parallel)") in
  `plugin/skills/orchestrate/SKILL.md`. Two changes, both additive — do not remove or weaken
  the existing G11 isolation language, the codex RED-FLAG warnings, or the fable-fallback
  logic already documented there:

  1. **Native subagent_type on plain Agent calls.** In the "For `executor: haiku | sonnet |
     opus | fable` tasks" block, add: before issuing the `Agent` call, check
     `subagent_profiles.has_native_agent_file(task's resolved role)` (the role comes from
     `dispatch.build_subagent_input`'s `role` field, already computed via
     `subagent_profiles.resolve_profile`). If true, pass `subagent_type: <role>` on the Agent
     call; if false (role is `general-purpose` or the file doesn't exist), omit
     `subagent_type` (defaults to the harness's general-purpose agent, unchanged from today).
     Note explicitly: `model` override behavior is unchanged — `subagent_type` selects the
     tool allowlist, the existing executor-tier `model` rules from the table above this
     section still apply.

  2. **Wave-level Workflow fan-out.** Immediately before the per-task Agent-call loop, add a
     branch: if the wave's non-codex task count is > 1, dispatch per
     `${CLAUDE_PLUGIN_ROOT}/skills/_shared/workflow-fanout.md` (pointer, do not inline the
     fragment's content) instead of looping individual `Agent` calls — build the args via
     `dispatch.build_workflow_fanout_args(wave, dependency_summaries=...)`, invoke `Workflow`,
     then pass each returned result through `dispatch.parse_subagent_response()` exactly as
     the single-task path does today (same `IsolationViolation` → FAIL handling, same ledger
     call via `state.log_agent_call` per task — do not use Workflow's own budget tracking,
     per the fragment's cost/ledger note). If the wave's non-codex count is ≤ 1, keep the
     existing single Agent-call path unchanged. Codex tasks are entirely unaffected by this
     change — they keep dispatching via `renmark-execute` exactly as today.

  Keep the file's existing structure and heading names; this is an edit to Step 3b's body,
  not a restructure of the skill.

## Wave plan

| Wave | parallel_group | Tasks |
|---|---|---|
| 1 | 1 | 1–9 (docs + 8 native agent files — all independent) |
| 2 | 2 | 10, 12, 13 (subagent_profiles.py helper, workflow-fanout.md, dispatch.py helper — disjoint files) |
| 3 | 3 | 11, 14 (tests for wave 2's two Python helpers) |
| 4 | 4 | 15 (orchestrate/SKILL.md — depends on 10, 12, 13 all existing) |

## Cost preview

| Executor | Count | Notes |
|---|---|---|
| haiku | 10 | tasks 1–9 (docs + agent files) |
| sonnet | 4 | tasks 10, 12, 13, 15 (Python helpers + fragment + SKILL.md) |
| codex | 2 | tasks 11, 14 (test scaffolding) |

**Total tokens (incl. ~10k Agent overhead/task where applicable):** ~106,300
**Total cost:** ~$0.30 (deterministic-first: no task here required AI to decide *whether*
to dispatch — see the subagent-justification gate output at dispatch time for the per-task
`role`/`role_reason` breakdown)

# Workflow Fan-Out — Contract Reference (single source of truth)

**Shared by `/renmark:orchestrate` Step 3b (and any future skill that dispatches
more than one `needs_agent` task in the same wave).** This is the one place the
Workflow-tool fan-out pattern lives so skills can't drift. It is an
**optimization of how Step 3b issues Agent calls** — it does not change what
crosses the G11 isolation boundary, who validates results, or who owns the
ledger.

---

## When to use it

Use the Workflow-tool fan-out **only when a wave's non-codex (`needs_agent`)
task count is > 1.** A wave with exactly one `needs_agent` task stays a plain
`Agent` call, per Step 3b as written today — the `parallel()` / schema /
per-item `agentType` ceremony has a fixed cost that isn't worth paying to
dispatch a single task.

This pattern does **not** extend to:

- **`executor: codex` tasks.** A Workflow script has no filesystem/Bash
  access, so codex tasks stay exclusively on the `renmark-execute` subprocess
  path (unchanged — see Step 3b's existing RED FLAG on this).
- **Cross-`/clear` resumability.** A Workflow's `resumeFromRunId` is
  same-session only; it is not a substitute for `.renmark/state/pipeline.json`
  checkpointing. If a wave needs to survive `/clear` or a restart, that still
  goes through the existing pipeline-state persistence, not through Workflow
  run IDs.

---

## What stays in Python (unchanged)

The Workflow script is a thin dispatch shim around work Step 3b already does.
None of the following moves into the Workflow script or changes behavior:

- **Wave grouping** — `dispatch.group_tasks_by_wave`.
- **Target-collision validation** — `dispatch.validate_wave`.
- **The pre-dispatch gate chain** — `subagent_gate` / cost-preview / user ack.
  This still runs, and still blocks dispatch, before any Workflow call is made.
- **Building each task's input** — `dispatch.build_subagent_input(task,
  dependency_summaries=...)` per task, exactly as today.

If any of these were to move into the Workflow script, they would stop being
inspectable/testable as plain Python and would bypass the pre-dispatch gates —
that is the reason they stay out.

---

## What the Workflow script does

The Workflow script receives the wave's list of `SubagentInput.to_dict()`
payloads — produced by `dispatch.build_workflow_fanout_args(tasks)` in
`renmark/dispatch.py` — as its `args`. The Workflow script itself has no
Python import access, so the `has_native_agent_file` check happens **before**
the payloads leave Python: `build_workflow_fanout_args` resolves, per task,
whether `subagent_profiles.has_native_agent_file(item.role)` is true and bakes
the result into the payload as a plain field (e.g. `agent_type: renmark:<role> |
null`) — the Workflow script only ever reads that pre-resolved field, it never
calls back into Python. For each item the script then:

1. Reads `agent_type` from the payload: pass `agentType: item.agent_type` to
   the `agent()` call when it is non-null (so the task's subagent gets its own
   tool allowlist from the plugin's `agents/<role>.md`); omit `agentType` (default
   agent) when it is `null`.
2. Builds the prompt by embedding `task_spec` + `verifier_expectations` from
   the item, plus the same G11 JSON-shape instruction Step 3b already gives
   plain Agent calls (the `"Your final response MUST be valid JSON matching
   this shape..."` block — read the exact text from
   `plugin/skills/orchestrate/SKILL.md` Step 3b rather than re-deriving it) and
   the canonical reasoning-contract blockquote from
   `${CLAUDE_PLUGIN_ROOT}/skills/.shared/reasoning-contract.md`.
3. Calls `agent(prompt, { schema: SUBAGENT_OUTPUT_SCHEMA, agentType })` for
   that item, inside a `parallel()` so all of the wave's items run
   concurrently.
4. Returns the raw array of `agent()` results, in the same order as `args`.

**The script does NO validation of the results.** It does not check
`status`, does not reject extra fields, does not enforce the G11 field
allowlist. That logic is Python-only (see next section) — duplicating it
inside the Workflow script would create a second, driftable copy of the G11
contract.

### Example skeleton

```js
// workflow-fanout.workflow.js — skeleton; not itself an artifact to load
// verbatim, adapt the schema import to your Workflow-tool binding.
const SUBAGENT_OUTPUT_SCHEMA = { /* mirrors dispatch.SUBAGENT_OUTPUT_FIELDS */ };

export default async function run({ args }) {
  // args: SubagentInput.to_dict() payloads from
  // dispatch.build_workflow_fanout_args(tasks)
  const results = await parallel(
    args.map((item) => {
      const opts = { schema: SUBAGENT_OUTPUT_SCHEMA };
      if (item.agent_type) opts.agentType = item.agent_type;
      return () => agent(buildPrompt(item), opts);
    })
  );
  return results; // raw array, same order as args — no validation here
}

function buildPrompt(item) {
  return [
    item.task_spec,
    `Verifier expectations: ${item.verifier_expectations}`,
    G11_JSON_SHAPE_INSTRUCTION, // verbatim from orchestrate SKILL.md Step 3b
    REASONING_CONTRACT_BLOCKQUOTE, // verbatim from _shared/reasoning-contract.md
  ].join("\n\n");
}
```

---

## What happens after the Workflow call returns (back in Python/skill context)

Each item in the returned array is passed through
`dispatch.parse_subagent_response()` **exactly like a plain Agent-call result
today.** Nothing about failure handling changes because the dispatch mechanism
changed:

- An `IsolationViolation` (forbidden/extra fields, missing required fields,
  schema violation) fails **that one task** the same way it does on the
  non-Workflow path — it does not fail the whole wave, and it is not retried
  automatically.
- Downstream steps (3c verifier run, 3d escalation logging, wave-summary
  aggregation) are unaffected — they consume `SubagentOutput` instances, and
  don't know or care whether the instance came from a plain `Agent` call or a
  Workflow fan-out item.

---

## Cost / ledger note

Do **not** use the Workflow tool's own `budget`/token-tracking for wave
dispatch. `state.log_agent_call` remains the single ledger for Agent-path
spend (see Step 3b's "Ledger the call" section) — recording spend twice, once
via Workflow's own tracking and once via `log_agent_call`, would double-count
tokens already covered by `cost.py`'s pre-dispatch estimate. Ledger each
returned, successfully-parsed result exactly as Step 3b does today, per task.

---

## Dispatch reference (for skill authors)

When citing this contract in a SKILL.md, write:

> *When a wave has more than one `needs_agent` task, fan out via the Workflow
> tool per `${CLAUDE_PLUGIN_ROOT}/skills/.shared/workflow-fanout.md`: build
> each task's input with `dispatch.build_subagent_input`, pass the wave as
> `dispatch.build_workflow_fanout_args(tasks)` (which pre-resolves each item's
> `agent_type` via `subagent_profiles.has_native_agent_file(role)` in Python)
> to a `parallel()`-based Workflow script that calls `agent()` per item using
> that pre-resolved `agent_type`, then parse every returned
> result through `dispatch.parse_subagent_response()` exactly as the
> non-Workflow path does. A single-task wave stays a plain `Agent` call. Codex
> tasks and cross-`/clear` resumability stay on the existing Python paths.*

Do not paste the example skeleton verbatim into a calling SKILL.md — point to
this file instead.

---

## Why a shared file

A per-skill fan-out implementation would drift the moment a second
skill needed wave-level parallel dispatch, and would risk silently
reimplementing (and diverging from) the G11 validation Python already owns.
Centralizing here means:

- One edit point for the fan-out shape; `renmark/dispatch.py` stays the single
  place that defines what a subagent may receive and return.
- Linter-friendly. `plugin/skills/.shared/` is skipped by `renmark.lint` (it's
  a reference dir, not a skill).
- Symmetric with `_shared/prd-alignment.md` and `_shared/reuse-check.md` —
  same pattern (isolated work, bounded interface, orchestrator reads only the
  parsed result), same precedent.

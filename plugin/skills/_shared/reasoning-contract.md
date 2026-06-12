# Reasoning & Output-Discipline Contract — Reference (single source of truth)

**Shared by every skill that dispatches subagents:** `orchestrate` (all task
dispatch), `verify` (QA subagents), `codereview` / `audit` (refutation
subagents), `finish` (release-readiness pass), and `prd` / `brainstorm`
(non-interactive fable lanes and brainstorm's parallel research subagents). This is the one place the reasoning instruction
and its output-discipline mapping live, so dispatch prompts can't drift. Skills
cite the blockquote below; they do not paste or paraphrase the body.

---

## The canonical reasoning instruction (verbatim — single source)

Include the following instruction, verbatim, in every dispatched subagent
prompt:

> Before concluding, break the problem into multiple perspectives or
> interpretations; explicitly list assumptions and potential edge cases; then
> synthesize the final answer from the most robust reasoning path. Mark each
> issue blocking vs deferrable. Separate findings from recommendations.
> Preserve evidence (file paths, commands, test output). If context is
> incomplete, state what is missing instead of guessing. Confidence is not
> completion.

This is the only authoritative copy. If the wording above and a skill's
dispatch section ever disagree, this file wins — fix the skill.

---

## Output-discipline mapping (SubagentOutput / G9 fields)

The instruction is not advisory prose — each clause lands in a specific field
of the structured `SubagentOutput` contract (G9: artifact existence ≠ artifact
correctness):

| Clause | Where it lands |
|---|---|
| *Confidence is not completion* | The `confidence`, `completion_state`, and `validation_status` fields exist for exactly this. A subagent that "feels done" but did not validate reports `completion_state: complete` only with `validation_status: validated`; otherwise it reports honestly (`partial` / `unvalidated`) and lowers `confidence`. |
| *Blocking vs deferrable* | Marked explicitly in `summary_lines` — every reported issue carries a `blocking:` or `deferrable:` tag so the orchestrator can gate the wave on summary fields alone. |
| *Findings vs recommendations* | Separated sections in the output: findings (what IS, with evidence) never interleaved with recommendations (what SHOULD change). The orchestrator may act on findings; recommendations are routed, not auto-applied. |
| *Preserve evidence* | File paths, commands run, and test output go in the **artifact body** on disk — never in chat. The orchestrator-visible summary carries pointers, not dumps (G11 boundary). |
| *State what is missing, never guess* | Missing context is reported as an explicit gap line in the summary plus `confidence: low` — not papered over with a plausible-sounding answer. |

A subagent output that skips these fields is treated as `confidence: low,
validation_status: unvalidated` and flagged for review (per G9).

---

## Browser-validation clause (QA subagents)

QA subagents validating UI acceptance criteria are explicitly told they have
browser automation access via the Chrome DevTools MCP and MUST NOT rely on
static code inspection alone. (renmark's browser channel is Chrome DevTools
MCP — see verify SKILL's channel selection.)

A QA verdict of PASS on a UI acceptance criterion that was never exercised in
a live browser is a G9 violation: report it as `validation_status:
unvalidated`, not as a pass.

---

## Dispatch reference (for skill authors)

When citing this contract in a SKILL.md dispatch section, write:

> *Include the reasoning/output-discipline contract from
> `${CLAUDE_PLUGIN_ROOT}/skills/_shared/reasoning-contract.md` in every
> dispatched subagent prompt: multi-perspective decomposition → explicit
> assumptions/edge cases → synthesis; blocking vs deferrable; findings vs
> recommendations; evidence preserved; missing context stated, never guessed.*

Do not paste the canonical instruction or the mapping table into the calling
SKILL.md — cite this file.

---

## Why a shared file

Earlier drafts had each dispatching skill carry its own variant of "think
carefully, be honest about confidence." The wording drifted per skill within
one release. Centralizing here means:

- One edit point. Any future dispatching skill (or fable lane) reads the same
  contract.
- Linter-friendly. `plugin/skills/_shared/` is skipped by `renmark.lint` (it's
  a reference dir, not a skill).
- Symmetric with `_shared/prd-alignment.md`, `_shared/scope-contract.md`, and
  `_shared/handoff-menu.md` — same pattern, same precedent.

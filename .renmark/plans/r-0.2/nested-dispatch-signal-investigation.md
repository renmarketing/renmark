---
artifact_type: research
schema_version: 1
created_at: 2026-08-01T00:00:00+00:00
source_sha: 559f410
related_plan: .renmark/plans/2026-08-01-r-0.2-controlled-worker-execution-contract.md
generator: sonnet
completion_state: complete
confidence: high
validation_status: validated
retry_count: 0
parser_success: true
schema_compliance: true
dependency_refs:
  - .bootstrap-renmark/decisions/ADR-002-worker-scope-enforcement.md
  - .bootstrap-renmark/milestones/R-0.1/scope-enforcement-design.md
  - .bootstrap-renmark/milestones/R-0.1/closeout.md
  - renmark/subagent_profiles.py
  - renmark/dispatch.py
  - plugin/agents/*.md
---

# R-0.2 / WP-6 — Nested-dispatch signal investigation (R-007 revisit)

## Headline finding

**Partially available — a stronger, PREVENTIVE mechanism exists, but it is
not the DETECTIVE transcript-scan mechanism R-0.1's design doc asked about,
and it only covers Renmark's 8 specialized dispatch roles, not the
`general-purpose` fallback.**

R-0.1/scope-enforcement-design.md §6 asked only about option (b): "does the
host expose tool-use transcripts to the orchestrator in a structured,
cheap-to-check form" for a post-hoc scan. As of this investigation, no such
transcript-exposure API is documented for Claude Code's Agent tool — option
(b) as literally worded is still unavailable. However, a different,
stronger mechanism was found that R-0.1 did not evaluate: Claude Code's
subagent frontmatter `tools:` field is a documented **allowlist**. A
subagent invoked with an explicit `tools:` list can only use the tools on
that list; if a tool is omitted from the list, the subagent is
**structurally unable to invoke it at all** — this is preventive, not
detective, and requires no transcript inspection.

## 1. Does the Agent tool expose a structured "did the subagent nest-dispatch" signal?

No documented API for post-hoc transcript inspection of a subagent's own
tool calls was found (web search: "Claude Code subagent frontmatter tools
field restrict available tools Task Agent", 2026-08-01). No first-party doc
describes exposing a completed subagent's tool-call transcript back to the
orchestrating context in a structured, cheap-to-check form. Renmark's own
G11 isolation design (`renmark/dispatch.py` "orchestrator never sees the
subagent's transcript, generated code, or diff") independently confirms
this: Renmark deliberately does not receive transcript data today, and
nothing in the platform surface found during this investigation contradicts
that as the current default.

What IS documented and confirmed: subagent definitions (`.md` files with
YAML frontmatter, matching Renmark's `plugin/agents/*.md` shape) support a
`tools:` field. Per public documentation: "The tools field is an allowlist;
specify it, and the subagent can only use those tools. Omit it, and it
inherits all tools." The Agent/Task tool itself ("Task tool… renamed Agent
tool as of Claude Code v2.1.63") is one of the tools that can be included
or omitted from that allowlist. Omitting it means the subagent cannot spawn
further subagents — not merely "is instructed not to."

This is a different and stronger guarantee than what R-0.1 evaluated:
- R-0.1's option (a) = contractual/prompt-level only (what R-0.1 shipped).
- R-0.1's option (b) = detective, post-hoc transcript scan (not available).
- **Newly identified option (c) = preventive, tool-allowlist exclusion**
  (available today, already partially in effect — see §3).

Sources:
- [Subagent Tool Restrictions - Claude Code - Developers Digest](https://www.developersdigest.tech/guides/subagent-tool-restrictions)
- [Claude Code Subagents: A 2026 Practical Guide - Tembo.io](https://www.tembo.io/blog/claude-code-subagents)
- [Claude Code Best Practice - Subagents](https://github.com/shanraisshan/claude-code-best-practice/blob/main/best-practice/claude-subagents.md)

## 2. Existing renmark code touching this area

`grep -rn "nested|subagent|tool_use|transcript" renmark/*.py plugin/agents/*.md`
found no transcript-parsing or telemetry code. Relevant existing constructs:

- `renmark/dispatch.py` — G11 isolation contract comment (line ~213-215)
  states the orchestrator never sees subagent transcript/code/diff by
  design; enforces `IsolationViolation` if a `SubagentOutput` tries to leak
  a `transcript` field back (line ~386). This is about the orchestrator not
  *wanting* transcript data, not about being unable to get it — it does not
  bear on whether the host *could* expose nested-dispatch evidence.
- `renmark/dispatch.py` (~line 128) — the fast-path dispatch prompt already
  contains the literal instruction: "You must not invoke another agent,
  subagent, Task, or Agent tool call" — this is R-0.1's option (a),
  confirmed still in place, prompt-level only, no code checks compliance.
- `renmark/subagent_profiles.py` — defines the 8 specialized `ProfileSpec`
  roles and `native_agent_type(role)`, which returns `"renmark:<role>"`
  when `plugin/agents/<role>.md` exists on disk (`has_native_agent_file`).
- `renmark/dispatch.py` line ~693 — `arguments["subagent_type"] = agent_type`
  confirms the resolved native agent type IS actually passed as the Agent
  tool's `subagent_type` parameter at real dispatch time, i.e. the
  `plugin/agents/<role>.md` definition (frontmatter and all) is the
  definition Claude Code actually loads for that dispatch — this is not a
  dead/unused code path.

No existing code computes or checks a nested-dispatch signal of any kind
(neither transcript-based nor tool-allowlist-based) today.

## 3. Do renmark's existing agent-definition files already restrict the toolset?

**Yes, for all 8 specialized roles, as of this investigation.** Every file
in `plugin/agents/*.md` declares an explicit `tools:` frontmatter line, and
none of the 8 include `Agent` or `Task`:

| Role | `tools:` frontmatter |
|---|---|
| `code-implementer` | `Read, Grep, Glob, Edit, Write, Bash` |
| `reviewer` | `Read, Grep, Glob, Bash, Write` |
| `release-manager` | `Read, Grep, Glob, Edit, Write, Bash` |
| `audit-reader` | `Read, Grep, Glob, Write` |
| `finish-lane-specialist` | `Read, Grep, Glob, Bash, Write` |
| `researcher` | `Read, Grep, Glob, WebFetch, WebSearch, Write` |
| `test-writer` | `Read, Grep, Glob, Edit, Write, Bash` |
| `docs-editor` | `Read, Grep, Glob, Edit, Write, Bash` |

If the documented allowlist semantics hold (tools field = allowlist;
omitted tool = unavailable to that subagent), then **any Worker dispatched
through one of these 8 native profiles is already mechanically prevented
from invoking the Agent/Task tool** — R-007's no-nested-delegation
guarantee is already stronger than "documented, not enforced" for these
paths, and R-0.1's team did not flag this because R-0.1/ADR-002 §6 only
asked about post-hoc transcript detection (option b), not tool-allowlist
exclusion (option c).

**This finding is CONDITIONAL, not fully verified**, on two points this
investigation could not confirm from inside this session:
1. Whether Claude Code's frontmatter `tools:` allowlist is actually
   enforced by the platform (hard block) versus advisory (a hint the model
   is expected to honor but could route around) — public docs describe it
   as a hard allowlist, but this could not be empirically reproduced from
   inside this text-only investigation task.
2. **Coverage gap:** the `general-purpose` fallback role
   (`renmark/subagent_profiles.py::PROFILES["general-purpose"]`) has no
   native `plugin/agents/*.md` file and therefore no `tools:` restriction —
   it inherits the full toolset, Agent/Task included. Per
   `resolve_profile()`, `general-purpose` is used whenever a task doesn't
   match one of the 8 specialized heuristics. Any dispatch that falls back
   to `general-purpose` gets ONLY the prompt-level (option a) guarantee,
   identical to R-0.1's status quo — the tool-allowlist guarantee does not
   extend there.
3. Codex, renmark's other supported host, is not know to expose an
   equivalent per-subagent tool-allowlist frontmatter; this finding is
   Claude-Code-specific, not host-independent in the literal sense R-0.1's
   design doc used the phrase.

## 4. What a minimal implementation would look like, if pursued

This is offered as an option for a future WP, not built here (WP-6 is
documentation-only). If the Owner wants to close the `general-purpose`
coverage gap and formally elevate R-007 from "documented" to "enforced for
covered paths":

1. **No renmark/** or `plugin/**` change needed for the 8 already-restricted
   roles** — the guarantee already exists structurally; only the wording of
   R-007's status in `.renmark/memory/decisions.md` / ADR-002 needs
   updating to say "mechanically prevented for the 8 native profiles via
   tool-allowlist exclusion; prompt-level-only for `general-purpose`."
2. **To close the `general-purpose` gap**, two options, neither requires a
   new detection mechanism:
   - (a) Narrow `resolve_profile()`'s fallback surface so more task shapes
     resolve to a specialized (tools-restricted) role, shrinking how often
     `general-purpose` is used — a classification change in
     `renmark/subagent_profiles.py`, not a new subsystem.
   - (b) Add a `plugin/agents/general-purpose.md`-equivalent override (if
     Claude Code allows redefining/restricting the built-in fallback agent
     via a plugin-provided definition of the same name) with an explicit
     `tools:` allowlist omitting Agent/Task — would need verification that
     the platform lets a plugin agent file shadow the built-in
     `general-purpose` type; not confirmed in this investigation.
3. **A regression test** (in the WP-4/WP-5 test suite, not this WP) could
   assert `"Agent" not in tools_line and "Task" not in tools_line` for
   every `plugin/agents/*.md` file — a deterministic, cheap, non-model
   check that would catch a future edit accidentally re-adding nested-
   dispatch capability to a specialized role. This is squarely inside
   "deterministic-first" per `CLAUDE.md` — no model call needed.

## 5. Bottom line for R-007 / R-0.2 scope

- R-0.1's literal question (transcript-based post-hoc detection, option b)
  — **still unanswered "no" today**, same as R-0.1's honest gap.
- A different, preventive mechanism (tool-allowlist exclusion, option c)
  — **already exists and already covers renmark's 8 specialized dispatch
  roles**, discovered by this investigation, not previously credited in
  ADR-002 or R-0.1's closeout.
- **Net effect on R-007's status:** upgrade from "documented, not enforced"
  to "mechanically enforced for the 8 native-profile dispatch paths;
  prompt-level-only for the `general-purpose` fallback and for Codex." Per
  the R-0.2 contract's scope note, this WP investigates and documents only
  — no code change is made here, and none is required for the finding
  itself to be true today.

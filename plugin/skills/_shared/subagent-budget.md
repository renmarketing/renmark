# Subagent Budget Discipline — Reference (single source of truth)

**Shared by `/renmark:orchestrate`, `/renmark:finish`, `/renmark:feature`, and `/renmark:brainstorm`.** This is the one place the rules for spawning, sizing, and costing subagents live: when to spawn them, how to pack dispatch inputs, what output formats to enforce, and warning signals for subagent-heavy workflows. Operationalizes context hygiene (REQ-5 / G11) and cost discipline (REQ-19).

---

## Before you spawn — the local-first rule

Before dispatching a subagent, check FIRST:

1. **Local grep / Read.** Can I answer this with a quick search in the current repo? (symbol location, simple pattern match, file list).
2. **Single Explore pass.** If I genuinely need to search, run ONE scoped Explore agent call — breadth "quick" or "medium" — and see if that closes the question. Do not spawn an Explore subagent if a local grep suffices.
3. **Prior artifact.** Does a cached artifact (spec, plan, prior review) already have the answer? Cite it instead of re-searching.

**Exception:** Workflows explicitly designed for parallelism (multi-file code review, independent test scaffolding, parallel feature branches) are **not** covered by the local-first rule — they are subagent-justified from the outset.

---

## The dispatch-packet contract

Every subagent MUST receive a complete, bounded packet with NO ambiguity about scope or output:

| Field | Required | Content |
|---|---|---|
| `mission` | Yes | One-sentence task goal (e.g., "review this code for memory leaks"). |
| `files` or `search_targets` | Yes | Explicit file paths OR grep/search queries — **not** vague ("the whole project"). |
| `output_format` | Yes | Structured format (JSON, Markdown list, YAML) OR prose ceiling (≤5 lines, ≤300 tokens). |
| `stop_condition` | Yes | What makes this task done? (e.g., "PASS when all tests pass and verifier runs clean"). |
| `model_tier` | Yes | Explicit `haiku` / `sonnet` / `codex` / `opus` (default: sonnet unless overridden by model-routing discipline). |
| `verification_expectation` | Yes | How will the orchestrator validate the output? (artifact path, summary fields, exit code). |

A dispatch packet missing any of these is incomplete and MUST NOT be sent.

---

## Cost escalation rules for subagents

When a workflow requires MANY subagents (5+):

1. **Batch independent tasks.** Group read-only tasks with the same model tier into single agents, not one-per-task.
2. **Prefer cheaper models for read-only work.** Grep / search / read-only verification → Haiku (not Sonnet).
3. **Warn the user.** If a plan calls for >5 subagents, flag it in cost preview BEFORE execution. Show: estimated agents, model tiers, total cost band.

---

## What the orchestrator does NOT do

- Does NOT inspect subagent transcript or code output — only reads the `status` / `summary` / artifact path.
- Does NOT carry implementation context between subagents unless the dependency graph requires it.
- Does NOT spawn a subagent "just to be thorough" — every subagent must have a explicit mission in the plan.
- Does NOT reuse a subagent for a second, different task — each task gets its own isolated context.

---

## Specialized subagent profiles

**Subagent-profiles** (`_shared/subagent-profiles.md`) is the registry of 9 dispatch roles: 8 specialized profiles (docs-editor, code-implementer, test-writer, reviewer, release-manager, researcher, audit-reader, finish-lane-specialist) + `general-purpose` fallback-only. Prefer a specialized profile before a generic agent; every dispatch packet carries a `role` field (string) and renmark logs the intended role in routing ledgers and cost summaries.

---

## Interaction with reuse-check and context-taxonomy

**Reuse-check** (`_shared/reuse-check.md`) is a special subagent: it searches a large surface (registry, specs, plans) in bounded time. It is **not** a violation of the local-first rule — it's the gate that prevents reinventing wheels.

**Context-taxonomy** (`_shared/context-taxonomy.md`) defines what can be in a dispatch packet. Rule: the packet carries **task-local context + required-skill metadata, never a full skill body**. Enforce this via `renmark.dispatch.assert_metadata_only`.

---

## Examples

**Good dispatch packet:**
```
mission: Review code for deadlock risk in acquire/release sequences
files: [renmark/cost.py, renmark/lifecycle.py]
output_format: JSON {findings: [...], severity: HIGH|MEDIUM|LOW, confidence: ...}
stop_condition: Code review produces <output_format> and is validated against
  renmark.lint
model_tier: sonnet
verification_expectation: Artifact path renmark/reviews/YYYY-MM-DD-<sha>.review.md
```

**Bad dispatch packet (missing fields):**
```
mission: Review our Python code
files: [everything in renmark/]
(no output_format, no stop_condition, no model_tier, unclear what "review" means)
```

---

## Why a shared file

Early drafts left subagent dispatch discipline to individual skills. One skill spawned agents without specifying output format; another forgot verification expectations. Centralizing here means:

- One edit point. Dispatch contract, costing rules, and local-first discipline are defined once.
- Enforced by tooling. `renmark.dispatch.build_subagent_input` validates the packet; violations are bugs.
- Cross-referenced. Cite alongside `_shared/context-taxonomy.md`, `_shared/reuse-check.md`, and `_shared/model-routing.md`.

When citing in a SKILL.md, write:

> *Honor subagent budget discipline in `${CLAUDE_PLUGIN_ROOT}/skills/_shared/subagent-budget.md`: local-first (grep/read before spawning); each dispatch packet carries mission, files, output_format, stop_condition, model_tier, and verification_expectation; prefer cheaper models for read-only work; warn when >5 subagents are needed. Do not pass full skill bodies in dispatch packets (see `_shared/context-taxonomy.md`).*

Do not paste the contract table or examples into the calling SKILL.md — cite this file.

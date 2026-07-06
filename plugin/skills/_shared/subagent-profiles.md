# Subagent Profiles — Role-Based Dispatch Reference (single source of truth)

**Used by:** `/renmark:orchestrate`, `/renmark:feature`, `/renmark:start`, `/renmark:finish`, `/renmark:plan`, and any skill that dispatches subagents to specialized roles. This is the authoritative registry of 9 dispatch roles — 8 specialized profiles + 1 fallback. Renmark prefers specialized profiles for cost, context, and output discipline; `general-purpose` is FALLBACK ONLY.

---

## The nine dispatch roles

| Role | Mission | Context scope | File targets | Output | Stop condition | Model | Native agent file | Verification |
|---|---|---|---|---|---|---|---|---|
| **docs-editor** | Create/update docs, comments, and docstrings | Narrow (source file + related docs) | `.md`, `.rst`, docstring blocks | Markdown sections or code blocks | File written, lint clean | Haiku | `.claude/agents/docs-editor.md` | Read back and verify formatting |
| **code-implementer** | Write/modify feature code (non-test) | Broad (full module + imports, few cross-module) | `.py`, `.ts`, `.tsx`, `.rs` (logic only) | Diff or full file | Code compiles, passes basic lint | Sonnet | `.claude/agents/code-implementer.md` | Verifier + lint run |
| **test-writer** | Write unit/integration tests (scaffolding) | Narrow (test framework + SUT signature) | `test_*.py`, `*.test.ts`, spec files | Test file(s) | Test file passes own syntax; verifier runs | Haiku | `.claude/agents/test-writer.md` | `pytest`/`npm test` runs green |
| **reviewer** | Code review for logic bugs, style, and risk | Broad (full diff + context) | N/A (read-only) | JSON findings: `{issues: [...], severity, confidence}` | Review artifact written | Sonnet | `.claude/agents/reviewer.md` | Findings JSON parses; PASS/FAIL gate |
| **release-manager** | Version bumps, CHANGELOG, tag selection, merge readiness | Narrow (config + metadata + CHANGELOG) | `CHANGELOG.md`, `pyproject.toml`, `package.json`, version tags | Markdown + git commands | Version incremented, CHANGELOG appended | Sonnet | `.claude/agents/release-manager.md` | `git tag -l` confirms version |
| **researcher** | Web research, data lookup, design patterns | Broad (external sources + repo docs) | N/A (read-only + web) | Markdown summaries with citations | Summary written, sources cited | Sonnet | `.claude/agents/researcher.md` | Links verified, claims traceable |
| **audit-reader** | Read audit/generated-code artifacts for gaps/risks | Narrow (audit file only; no source code) | `.audit.md`, `.review.md`, generated logs | JSON summary: `{gaps: [...], blocking, confidence}` | Artifact read, summary written | Haiku | `.claude/agents/audit-reader.md` | Summary JSON parses; confidence ≥medium |
| **finish-lane-specialist** | Determine finish lane (quick/release/self-update/full), cost band, escalation | Broad (plan + cost data + lifecycle) | N/A (read-only state) | Markdown lane recommendation + rationale | Lane selected, cost band shown | Sonnet | `.claude/agents/finish-lane-specialist.md` | Lane exists in `renmark.finish_lanes.LANES` |
| **general-purpose** | Fallback: no specialized role fits | Per task | Per task | Per task | Per task | Sonnet | — (built-in) | Per task |

---

## Dispatch rules

1. **Prefer specialized profiles.** Before dispatching a generic `general-purpose` agent, check whether a specialized role fits. Every subagent must declare its role in the dispatch packet's `role` field.

2. **Fallback only.** `general-purpose` is **FALLBACK ONLY** — used only when no specialized role covers the task. It receives the full context budget and no narrow context scope restrictions.

3. **Dispatch packet carries role.** Every `SubagentInput` (in `renmark/dispatch.py`) carries a `role` field (string) — either a specialized role name (from the table above) or `general-purpose`. The dispatch assembler (`build_subagent_input`) validates the role against this registry.

4. **Narrow context for specialized roles.** Specialized profiles declare a narrow context scope in the table above. The dispatcher MUST respect this boundary — a docs-editor receives file + related docs, not the entire codebase. Broad-scope roles (`code-implementer`, `reviewer`, `finish-lane-specialist`) receive more context; narrow-scope roles (`test-writer`, `release-manager`, `researcher`) receive bounded input.

5. **Native agent file dispatch.** When a specialized role has a native agent file at `.claude/agents/<role>.md`, renmark's orchestrate function passes `subagent_type: <role>` to the Agent tool call. This enables Claude Code to enforce the role's tool allowlist and context scope via the native agent file, rather than relying on a label or tracking convention. Roles without native agent files (`general-purpose`) use the built-in dispatch mechanism.

6. **Cost and model tier.** Specialized roles inherit a recommended model tier from the table (Haiku for read-only, Sonnet for code logic). The cost estimator (`renmark/cost.py::estimate_cost`) accumulates roles and reports them per wave to help surface skewed workloads (5+ test-writers vs 1 code-implementer).

7. **Verification expectation per role.** Each role has a specific stop condition and verification target. The orchestrator validates against the `verification_expectation` field in the dispatch packet, not the role's description.

---

## Dispatch reference (for skill authors)

When dispatching a subagent in a SKILL.md, write:

> *Dispatch specialized subagent role (prefer over generic `general-purpose`): `docs-editor` (docs/comments), `code-implementer` (feature code), `test-writer` (tests), `reviewer` (code review), `release-manager` (version/release), `researcher` (web research), `audit-reader` (audit artifacts), `finish-lane-specialist` (lane selection). Full registry: `${CLAUDE_PLUGIN_ROOT}/skills/_shared/subagent-profiles.md`. Fallback to `general-purpose` only when no role fits; in that case, set `role: general-purpose` and relax context scope.*

---

## Why a registry

Early drafts had subagents dispatch with only task-local context and no declared role. Costs scaled unpredictably (a 20-subagent plan might use 10 Sonnet, 5 Haiku, 5 Opus by accident). Centralizing role definitions here means:

- One edit point. Every future dispatcher references the same 9 roles and respects the same context boundaries.
- Cost discipline. The cost summary (`estimate_cost()`) aggregates roles and surfaces imbalance (many cheap-scoped tasks vs few expensive ones).
- Linter-friendly. `plugin/skills/_shared/` is skipped by `renmark.lint`.
- Symmetric with `_shared/subagent-budget.md`, `_shared/context-taxonomy.md`, `_shared/reasoning-contract.md` — same pattern.

Update this registry when adding a new specialized role; do not let roles drift in individual skill dispatch prompts.

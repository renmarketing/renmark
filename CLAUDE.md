# {{PROJECT_NAME}}

> Scaffolded by `/renmark:brainstorm` on {{DATE}}. Edit freely — keep under 200 lines.

<!-- BEGIN:sync-note -->
<!-- CLAUDE.md and AGENTS.md hold the same rule set in parallel. When you add
     or update a rule in one file, mirror the same change in the other in the
     same commit. -->
<!-- END:sync-note -->

## What this project is

(Filled in by `/renmark:brainstorm` — replace with a 2–3 sentence description.)

<!-- PROJECT-TECH-NOTES: add framework-specific notes here (version, deprecated APIs, gotchas). -->

<!-- PROJECT-ARCHITECTURE: add core constraints after brainstorm (component boundaries, invariants, removed patterns). -->

<!-- BEGIN:parallelism-rule -->
## Parallelize large plans
When implementing a multi-step plan (4+ tasks, or any task list with independent
leaves), dispatch sub-agents in parallel. **Single-message, multiple `Agent` tool
calls** — that's how they run concurrently. Sequential dispatch is the slow path.

- Independent file scopes → parallel. Two agents touching the same file must be sequential.
- Read-only verification → always parallel alongside code work, never after.
- Long-running probes → background `Bash` with `run_in_background: true`.
- Brief each agent: goal, file scope, what NOT to touch, deliverable. Tell them skip commits.
<!-- END:parallelism-rule -->

<!-- BEGIN:single-branch-rule -->
## Stay on main for small changes
Hotfixes, config edits, and single-file changes land directly on `main`.
Use `/renmark:feature` for new features or significant refactors — it creates
a branch, runs the full pipeline, and offers PR on finish.
<!-- END:single-branch-rule -->

<!-- BEGIN:commit-cadence-rule -->
## Commit per chunk, not per session
As soon as a logical chunk passes its check, commit it.

- One commit per logical fix or feature
- Commit before the next agent dispatch — don't pile up diffs
- Each commit must compile/pass lint before committing
- Commit messages name the change, not the session ("fix(auth): handle 401" not "session checkpoint")
<!-- END:commit-cadence-rule -->

<!-- BEGIN:changelog-rule -->
## Check and update CHANGELOG.md on every task
Before starting any task, read the last 5 entries of `CHANGELOG.md` for prior
decisions and "Do not change" guards. After completing a task, append a new entry:

```
## [YYYY-MM-DD] — [task title]
**Request:** [user's ask in 1–2 plain sentences]
**Built:** [what was implemented]
**Files changed:**
- `path/file` — [what changed and why]
**Do not change:**
- [invariants or pitfalls discovered]
```

The changelog is the project's persistent memory — keep it honest and current.
<!-- END:changelog-rule -->

<!-- BEGIN:refactor-safety-rule -->
## Pre-refactor safety protocol
Before any change touching >3 files or tagged "refactor"/"migrate"/"restructure":
1. Confirm git working tree is clean (`git status`)
2. Checkpoint: `git commit --allow-empty -m "chore: checkpoint before <change>"`
3. Run the relevant verifier/tests once as baseline — if they fail now, **stop and report**
4. Make changes; run verifier/tests again; compare pass counts
If tests regress: `git diff HEAD~1`, identify cause, revert targeted files only.
<!-- END:refactor-safety-rule -->

<!-- BEGIN:context-hygiene-rule -->
## Context hygiene
Never read generated file contents into the conversation. Only per-task summaries
(exit code, verifier pass/fail, file path). To debug a generated file route to
`/renmark:debug` — it isolates the artifact in its own session.
<!-- END:context-hygiene-rule -->

<!-- BEGIN:executor-dispatch-rule -->
## Executor dispatch rules
- `executor: codex` → `renmark-execute` (Bash subprocess). Never dispatch a codex
  task as an Agent call — that runs it on the parent model and burns Claude Code quota.
- `executor: haiku / sonnet / opus` → Agent tool calls, no model override.
<!-- END:executor-dispatch-rule -->

<!-- BEGIN:root-cause-rule -->
## Root cause before any fix
Before changing any code to fix a bug, write the root cause in one sentence: WHY
the bug exists, not what fixes it. If you cannot write that sentence, keep
investigating. See Iron Law in `/renmark:debug`.
<!-- END:root-cause-rule -->

<!-- BEGIN:verify-before-done-rule -->
## Verification before completion
Before claiming any task or plan complete: re-run the verifier fresh. A verifier
that passed in wave 3 may be broken by wave 4. Evidence first, claim second.
<!-- END:verify-before-done-rule -->

<!-- BEGIN:orchestrator-role-rule -->
## The orchestrator coordinates; it does not accumulate
Treat orchestrator context as a degrading systems resource, not durable memory.
Reasoning quality deteriorates **before** the window is full. Never solve an
orchestration problem by adding more inline context. Prefer:
- artifact emission
- structured summaries
- file pointers
- persistent state
- resumable workflows

Optimize for sustained orchestration integrity, not maximum context utilization.
<!-- END:orchestrator-role-rule -->

<!-- BEGIN:canonical-state-rule -->
## Canonical state lives outside the conversation
Conversation history is NOT authoritative state. Canonical state must live in:
- artifacts under `.renmark/specs/`, `.renmark/reviews/`, `.renmark/memory/`
- pipeline state files under `.renmark/state/`
- memory logs (`features.md`, `bugs.md`, `decisions.md`, `learnings.md`)
- structured summaries inside artifact files
- machine-readable metadata on every artifact

Any workflow with continuity across phases MUST persist state outside the
conversation. If you find yourself relying on "what was said earlier" to
continue work, write that fact to disk instead.
<!-- END:canonical-state-rule -->

<!-- BEGIN:prd-delegation-rule -->
Source of truth: `PRD.md` (if present). For new features/changes, dispatch a subagent to read `PRD.md` + docs and return a bounded alignment/drift summary — never load the full PRD into the orchestrator.
<!-- END:prd-delegation-rule -->

<!-- BEGIN:project-write-boundary-rule -->
## All renmark output stays inside the project
Every file renmark generates — specs, plans, reviews, research, audits,
verification artifacts, logs, memory — MUST be written inside **this project**,
under the project's `.renmark/` subtree or a project-root doc (CLAUDE.md,
CHANGELOG.md, stack.md). Canonical artifact homes:

- specs → `.renmark/specs/`
- plans → `.renmark/plans/`
- reviews / verification → `.renmark/reviews/`
- research → `.renmark/research/`
- runtime state → `.renmark/state/`
- memory → `.renmark/memory/`
- logs → `.renmark/logs/`

**Never write outside the project.** Do NOT create or modify files in the global
plugin install (`~/.claude/plugins/...`, `${CLAUDE_PLUGIN_ROOT}`), in `$HOME`, or
anywhere above the project root. Reading FROM the plugin dir (templates, the
shared `_shared/scope-contract.md`) is fine — it's reference data — but the
plugin install is read-only. One project's work must never leak into the plugin
or into another project.
<!-- END:project-write-boundary-rule -->

<!-- BEGIN:summary-boundary-rule -->
## Orchestrator-visible output is bounded
Every long-running or high-context task MUST terminate in (1) a durable artifact
and (2) a compact structured summary.

**Orchestrator MAY read:** summaries, counts, status, paths, hashes, metadata.

**Orchestrator MUST NOT read:** full diffs, large logs, research dumps, generated
code, audit bodies, architecture scans.

**Default cap: 5 lines OR ≤ 300 tokens** of orchestrator-visible output per task,
unless explicitly overridden by the user. Violations are bugs, not optimizations.
<!-- END:summary-boundary-rule -->

<!-- BEGIN:context-contamination-rule -->
## Cross-domain transitions recommend `/clear`
Domain transitions are contamination risks. When a new skill is invoked from a
different domain than the previous one, recommend `/clear` to the user before
continuing. `.renmark/memory/` survives clears — persistent state is preserved.

**Domains:**
- `debug` — debug, codereview
- `build` — start, brainstorm, plan, check-plan, orchestrate, verify, finish, feature
- `audit` — secure, document, map, research
- `meta` — setup, roadmap, help

Same-domain transitions do not trigger the recommendation. Cross-domain ones do.
Do not assume debugging context is useful for planning; planning context for
auditing; or audit context for implementation.
<!-- END:context-contamination-rule -->

<!-- BEGIN:artifact-governance-rule -->
## Artifacts carry provenance and freshness metadata
Every artifact written by a renmark skill MUST include machine-readable
metadata at the top:

```yaml
artifact_type: research | security | docs | architecture | verification | ...
schema_version: 1
created_at: ISO8601
source_sha: git sha at generation time
related_plan: .renmark/plans/...
generator: codex | opus | sonnet | haiku | <skill-name>
stale_after: ISO8601 (optional)
dependency_refs: [paths to upstream artifacts]
```

Artifacts without freshness/provenance metadata are unstable and must not be
trusted as upstream context. Prefer **invalidation** over silent drift. Track
stale artifacts, conflicting specs, outdated summaries, obsolete architecture
maps. Do not solve context rot by introducing artifact rot.
<!-- END:artifact-governance-rule -->

<!-- BEGIN:compact-semantics-rule -->
## `/compact` is not truncation
A compact operation MUST preserve operational continuity:

**Preserve:** active goals · unresolved blockers · pipeline state · artifact
references · verification status.

**Discard:** stale conversational reasoning · duplicate discussion · obsolete
branches.

If you are asked to compact a session, do not blindly summarize — protect the
fields above. After `/compact`, every running workflow must still be resumable
from `.renmark/state/` without re-reading conversation history.
<!-- END:compact-semantics-rule -->

<!-- BEGIN:failure-transparency-rule -->
## Artifact existence ≠ artifact correctness
All executor outputs MUST expose:
- `completion_state` — `complete | partial | failed`
- `confidence` — `low | medium | high`
- `validation_status` — `validated | unvalidated | failed`
- `retry_count` — integer, monotonically increasing per attempt
- `parser_success` — did the orchestrator parse the response cleanly?
- `schema_compliance` — did the output match the expected schema?

Prefer explicit uncertainty over silent success. A subagent that returns an
artifact path without these fields is treated as `confidence: low,
validation_status: unvalidated` and flagged for review.
<!-- END:failure-transparency-rule -->

<!-- BEGIN:workflow-recovery-rule -->
## Every multi-step workflow is resumable
Long-running orchestration MUST survive:
- interruption (Ctrl-C, network drop)
- partial completion (some tasks PASS, others fail mid-wave)
- executor failure (codex CLI crashes, API errors)
- context clearing (`/clear` mid-pipeline)
- orchestrator restart (new session)

Recovery depends on persisted pipeline state at `.renmark/state/pipeline.json`,
never on conversational reconstruction. Every skill that runs more than one
step must update pipeline state before returning, so the next session can pick
up exactly where this one stopped.
<!-- END:workflow-recovery-rule -->

<!-- BEGIN:task-isolation-rule -->
## `/renmark:orchestrate` runs each task in isolation
During orchestrate, each task — or each parallel group — runs in an isolated
subagent/executor context. The orchestrator MUST NOT carry implementation
context between tasks unless the plan's dependency graph explicitly requires it.

**Each subagent receives ONLY:**
- the task spec
- required file paths
- upstream artifact pointers (paths, never contents)
- dependency summaries from `.renmark/state/wave-summaries/`
- verifier expectations

**Each subagent writes ONLY:**
- task artifact (generated code/diff lives here, not in conversation)
- status (`PASS` | `FAIL` | `SKIP`)
- touched files
- sha / hash
- summary ≤ 5 lines
- dependency notes (what downstream tasks need from this one)

**Orchestrator aggregates ONLY:**
- PASS / FAIL / SKIP
- artifact path
- token count
- dependency status
- next-wave readiness

**Never merged back into orchestrator context:** subagent transcript, generated
code, diff, long reasoning. The orchestrator decides whether to advance the
wave based on summary fields alone — it does not "look at the work."
<!-- END:task-isolation-rule -->

<!-- BEGIN:context-budget-rule -->
## Context budget — `/compact` at 60%, `/clear` on subject change

The orchestrator is assumed to run on Sonnet 200k. Sonnet's window degrades
well before it's full — track utilization and act early:

- **At ~60% utilization (≈ 120k tokens):** suggest `/compact` to the user
  before invoking the next skill. Do NOT auto-run /compact silently — surface
  the recommendation as a one-line note: *"Context at ~60% — consider
  `/compact` before continuing."*
- **At ~80% utilization (≈ 160k tokens):** refuse to start a new long-running
  skill (`orchestrate`, `research`, `map`, `secure`) until the user runs
  `/compact` or `/clear`. Short skills (`roadmap`, `help`, `check-plan`,
  `resume`) still run.
- **On cross-domain skill transition** (per `context-contamination-rule`):
  recommend `/clear`, with note that `.renmark/memory/` survives clears.

The %-utilization side of this rule is enforced by the orchestrator
self-monitoring — the harness does not reliably expose context size to
skill code. The cross-domain side IS automated via
`renmark.lifecycle.skill_preamble(repo, skill)` — the single Step-0 helper
every skill calls, which resolves the domain from `DOMAIN_BY_SKILL`, runs
`context_budget_check`, records the invocation, and returns the hint string
to surface. Skills no longer inline these calls (consolidated v0.3.2).

Domains for subject-change detection (per `renmark.lifecycle.DOMAIN_BY_SKILL`):

| Domain | Skills |
|---|---|
| `debug` | debug, codereview |
| `build` | start, brainstorm, plan, check-plan, orchestrate, verify, finish, feature |
| `audit` | secure, document, map, research |
| `meta` | setup, roadmap, help, resume, release, restore, approve, issue |

Same-domain transitions don't trigger the prompt. Cross-domain ones do.
<!-- END:context-budget-rule -->

<!-- BEGIN:lifecycle-rule -->
## Lifecycle persistence (G12)

Every renmark workflow stage transition MUST write `.renmark/state/lifecycle.json`
before the skill returns. Cold start from any `/clear` is one file read.
Skills that don't update lifecycle.json on completion are bugs.

The canonical lifecycle stages (in order):

```
init → brainstorm-complete → plan-drafted → plan-validated → created
     → verified → reviewed → documented → ready-to-release → released
```

Plus `restored` (after `/renmark:restore`).

**Cold-start recovery:** after `/clear`, run `/renmark:resume`. It reads
lifecycle.json (≤ 1KB), prints the recommended next command, exits. Zero
LLM calls. The cost of survival is one file read.

**Strict separation:** lifecycle.json carries WORKFLOW state only (feature
identity, stage, artifact pointers, human approval gates). RUNTIME state
(wave indices, retry counts, subprocess pids) lives in `pipeline.json`.
If lifecycle.json exceeds ~1KB, it's a bug — runtime cruft has leaked in.
`renmark.lifecycle.write_lifecycle` raises `LifecycleBloatError` to catch
this at write time.

**Human approval gates:** lifecycle.json carries `human_review_required`,
`human_review_completed`, `human_review_for` fields. Release, restore,
merge, and security overrides MUST set these before destructive operations
and MUST check them on re-entry. `/renmark:approve` is the only way to
flip the bit. AI may generate code; the human owns merges and releases.
<!-- END:lifecycle-rule -->

## Tooling — renmark workflow

| Command | When to use |
|---|---|
| `/renmark:start` | Starting point for vibe coders — plain-English entry to the full pipeline |
| `/renmark:brainstorm <topic>` | Fleshing out an idea into a spec |
| `/renmark:prd` | Create/update the project PRD — the source of truth that plans and features align to |
| `/renmark:blueprint` | Generate/refresh the living schematic (+ prototype when there's a UI) |
| `/renmark:plan <spec>` | Decomposing a spec into atomic, executor-tagged tasks |
| `/renmark:orchestrate <plan>` | Executing a plan (Haiku / Codex / Sonnet / Opus) |
| `/renmark:check-plan <plan>` | Validate plan structure before spending tokens |
| `/renmark:verify` | Confirm feature goal was achieved after orchestrate |
| `/renmark:finish` | Close branch — create PR, merge, or clean up |
| `/renmark:debug <symptom>` | Systematic root-cause loop for bugs |
| `/renmark:codereview <ref>` | Multi-pass diff review (adversarial + quality + architecture) |

## File conventions

- Specs: `.renmark/specs/YYYY-MM-DD-<topic>.spec.md`
- Plans: `.renmark/plans/YYYY-MM-DD-<topic>.plan.md`
- Reviews: `.renmark/reviews/YYYY-MM-DD-<sha>.review.md`
- Memory: `.renmark/memory/` (committed) — `INDEX.md`, `project.md`, `routing.md`, etc.
- Runtime: `.renmark/state/` (gitignored)
- Changelog: `CHANGELOG.md` (committed) — read before tasks, update after

Source of truth: `PRD.md`. For new features/changes, dispatch a subagent to read `PRD.md` + docs and return a bounded alignment/drift summary — never load the full PRD into the orchestrator.

## Executor preferences

`.renmark/memory/routing.md` records which model worked best per task signature.

Defaults:
- Mechanical edits (`.gitignore`, simple CSS, JSON config) → `haiku`
- Test scaffolding, single well-defined file → `codex`
- Well-scoped algorithms, refactors → `sonnet`
- State machines, DOM APIs, cross-file reasoning → `opus`

## Code conventions

(Fill in as the project develops — language version, style guide, test framework.)

## Testing

(How to run tests. Verifiers in renmark plans should match this command.)

*Mirror all rule changes in `AGENTS.md` in the same commit.*

<!-- BEGIN:project-stub -->
<!-- Managed by /renmark:init. Last refreshed: 2026-05-28 @ 95f0d9d. Edits inside this block will be overwritten. -->

## Project at a glance

**Stack:** Python >=3.10 (pyproject.toml) + Claude Code plugin
**Entry points:** `bin/renmark-execute`, `renmark/__main__.py`, `plugin/commands/*.md`

**Top-level layout:**
- `bin/` — executable scripts / wrappers
- `plugin/` — Claude Code plugin (commands, skills, templates)
- `renmark/` — Python runtime (CLI, dispatch, verifier, lifecycle)
- `tests/` — test suite
- `tools/` — maintainer scripts


**Dev gates:** test `pytest -q` · lint `ruff check` · types `mypy .` · CI: test
**Standards detail** → `.renmark/memory/dev-standards.md` (read before non-trivial changes).

**Detailed map** (modules, symbols, full tree) → `.renmark/memory/project-map.md`. Read it when you need to find a specific module or symbol.
<!-- END:project-stub -->

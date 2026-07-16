---
name: plan
description: "Use when the user has a spec and wants it decomposed into an executable task list — typed as /renmark:plan or phrases like \"plan this\", \"write a plan\", \"decompose this\", \"create the plan for X\". Splits the spec into atomic tasks and emits a cost preview."
---

# plan

## Overview

Reads a spec (from `/renmark:brainstorm` or any markdown file) and emits a renmark-format plan at `.renmark/plans/YYYY-MM-DD-<topic>.plan.md`. Each task in the plan declares:

- `mode` — A (new file) or B (edit existing)
- `target` — exactly one file path
- `complexity` — simple / medium / hard
- `executor` — opus / codex / sonnet / haiku, plus fable by explicit escalation only (auto-assigned, ordered by capability)
- `parallel_group` — tasks sharing a group run concurrently
- `verifier` — shell command that exits 0 when the task is done
- `serves` — optional one-line traceability note such as `REQ-3` or `new`; best-effort only when a `PRD.md` exists, using requirement IDs already surfaced by alignment/spec work
- `est_tokens` and `est_cost_usd` — planner's estimates
- `spec` — prose telling the executor what to build

The plan is consumed by `/renmark:orchestrate`.

## When to Use

- After `/renmark:brainstorm` produces a spec
- When the user has a feature description and wants it broken into tasks
- When an existing plan needs to be re-decomposed

**Do NOT use:**
- Without a spec or clear feature description — route to `/renmark:brainstorm` first
- For executing — that's `/renmark:orchestrate`

## When Agency Mode is active

In Agency Mode, `plan` decomposes the assigned **milestone** (not the full PRD) into atomic tasks, attaches the milestone's **acceptance criteria** as the verifier success target (what "done + demo-ready" means for the owner), and **always displays a cost preview before dispatch**. Reference the full agency delivery contract by pointer only — `${CLAUDE_PLUGIN_ROOT}/skills/.shared/agency-delivery.md`. This behavior is additive; existing plan behavior is unchanged when agency is off.

## Steps

**Step 0a — Context check.** Call `lifecycle.skill_preamble(repo, 'plan')`. If it returns a non-None hint, surface as a one-line note.

**Final step — Lifecycle update.** After the plan is written to `.renmark/plans/YYYY-MM-DD-<topic>.plan.md`, call `lifecycle.write_lifecycle(repo, stage='plan-drafted', artifact_update=('plan', <plan-path>))`. **Validation then runs automatically** (Step 8 below auto-invokes `/renmark:check-plan`) — the user does not run it by hand.

### 0. Establish Scope Contract

Before decomposing a directly provided feature description, establish a lightweight scope contract to prevent silent assumptions about stack, deployment, or MVP scope.

**When to run discovery** — all of the following must be true:
- The user provided a feature description directly (not a path to an existing `.spec.md` or `.plan.md`)
- The request is for new functionality, a new project, or a major feature
- No sufficient scope/stack decisions exist in `.renmark/memory/stack.md`, `CHANGELOG.md`, or an existing spec/plan

**Skip discovery and go to Step 1 when:**
- The user provided an existing `.spec.md` or `.plan.md`
- `stack.md` clearly covers the requested work
- `CHANGELOG.md` already has a recent `project scope` or `bootstrap` entry covering stack and deployment
- The request is a small change inside an already-scoped project

**Do not skip if the new request conflicts with existing stack or scope records.** When a conflict exists, ask first:
> I found an existing scope/stack decision, but this request may conflict with it: [brief conflict]. Should I preserve the existing decision or create a new scope entry for this plan?

---

**Discovery flow** — ask at most 3 questions, one at a time. See `${CLAUDE_PLUGIN_ROOT}/skills/.shared/scope-contract.md` (the single source of truth shared with `/renmark:brainstorm`) for the full Q1–Q3 question text, stack inference rules, and option menus. Do not decompose until discovery is complete.

---

**Confirm decisions.** After Q3, summarize:
> I'll plan this with:
> - Tech stack: [confirmed stack]
> - Deployment: [confirmed target]
> - MVP boundary / out of scope: [confirmed exclusions]

Proceed only after the user explicitly confirms the summarized scope contract, selects an option that clearly implies confirmation, or gives a direct instruction to continue. Do not rely on silence, lack of objection, or ambiguous replies as confirmation.

---

**Record decisions.** See `${CLAUDE_PLUGIN_ROOT}/skills/.shared/scope-contract.md` for the CHANGELOG scope entry format and `stack.md` template. Write both before decomposing (skip if brainstorm already wrote them — they're the shared contract). The generated task plan must respect all locked decisions — do not introduce new major stack choices during decomposition unless the user asks.

---

### 1. Read the spec

Open the spec file. Also read `.renmark/memory/INDEX.md` (cheap) and pull any of `routing.md`, `conventions.md`, `learnings.md` that look relevant.

If `CHANGELOG.md` exists at the project root, read the last 5 entries. Use the "Do not change" guards to avoid re-introducing removed approaches and to populate each task's spec with known constraints.

**Contradiction-reconcile reflex (do not silently proceed).** The "Do not change" guards and recorded decisions in `CHANGELOG.md` (and `.renmark/memory/decisions.md` if present) are binding constraints, not background reading. When any task you are about to plan would **contradict** a "Do not change" guard or a recorded decision — re-introduce a removed approach, reverse a locked stack/scope choice, or rebuild something a decision rejected — do NOT decompose around it silently. Name the conflict to the user and reconcile before writing the plan:

> This is different from what's on file: [the proposed task] contradicts [the "Do not change" guard / recorded decision, quoted]. Reconcile — should I honor the existing guard, or are you overriding it for this plan?

Resolve the conflict (honor the guard, or get an explicit override) before proceeding to decomposition. Do not treat silence or an ambiguous reply as an override.

**Reuse check — before decomposition (don't re-decompose an existing build).** Before splitting the spec into a custom task list, dispatch the reuse-check subagent from `${CLAUDE_PLUGIN_ROOT}/skills/.shared/reuse-check.md`: Agent tool call (`model: haiku`; `sonnet` for a large search surface), passing ONLY `request_description`. The subagent searches loaded skills/commands, session MCP tools, `.renmark/specs/` + `.renmark/plans/`, and `.renmark/memory/features.md` in its own context, and returns ONLY the ≤5-line `reuse: found | none` verdict (+ a one-line pointer when found). On `reuse: found`, surface the `pointer` and **default to reuse** — recommend the existing skill / MCP tool / spec / feature instead of re-decomposing a custom build, unless there is a clear, stated reason it doesn't fit. Do NOT read the searched bodies in the orchestrator context (REQ-5).

### 2. Decompose into atomic tasks

Rules:
- **One file per task.** If a feature touches `server.py` and `tests/test_server.py`, that's two tasks.
- **Order so verifiers pass.** Implementation before tests. Static assets before code that references them.
- **No mode C** (cross-file refactors). Decompose into A/B per file.
- **Drop non-emission steps.** `mkdir`, `git init`, `git commit`, manual smoke tests are not tasks — the orchestrator handles directories and commits itself.

### 3. Score each task

For each task, set `complexity`:
- **simple** — `.gitignore`, plain HTML, simple CSS, JSON config, single-line file
- **medium** — single-file Python module with clear spec, server routing with edge cases, test scaffolding
- **hard** — game logic, state machines, coordinate math, DOM APIs, threading, regex parsing

### 4. Auto-route executor

Default routing (override if `.renmark/memory/routing.md` says otherwise):

| Signal | Executor |
|---|---|
| frontier reasoning: ideation/strategy synthesis, adversarial audit/review passes, architecture where opus is insufficient — escalation only, never default — only with a declared `top_tier: fable` — routing.md block or per-user `RENMARK_TOP_TIER` env (REQ-2); plan_lint BLOCKs it otherwise | `fable` |
| hard / state machines / coord math / DOM APIs / cross-file reasoning / architecture | `opus` |
| `tests/**`, fixtures, scaffolding, single well-defined file with verifier | `codex` |
| well-scoped algorithms, refactors, moderate domain logic | `sonnet` |
| simple, mechanical (config, JSON, `.gitignore`, plain HTML, simple CSS) | `haiku` |

Complexity → executor mapping: `hard` → opus, `medium` → codex (file-write + verifier) or sonnet (reasoning-heavy), `simple` → haiku; `fable` is never auto-assigned by complexity alone — only by explicit escalation signals (REQ-2); and never assigned at all in undeclared projects (capabilities.top_tier).

### 5. Assign parallel_group

Tasks that touch disjoint files AND don't depend on each other's outputs get the same `parallel_group`. Conservative default: each task in its own group (serial). Set the same group only when you're confident the targets won't collide.

### 6. Estimate cost (honest accounting — no hidden overhead)

For each task, compute **total spend** = `(output_tokens + agent_overhead) × $/kT`:

| Executor | $/kT | Agent overhead | Notes |
|---|---|---|---|
| `haiku`  | $0.0001 | + 10k tokens | cheapest Claude tier |
| `codex`  | $0.01–$0.05 | none | runs as `renmark-execute` subprocess |
| `sonnet` | $0.003  | + 10k tokens | |
| `opus`   | $0.015  | + 10k tokens | Anthropic billing — NOT "in-context free" |
| `fable`  | $0.030  | + 10k tokens | top reasoning tier — 2× opus; escalation only; renders fable→opus when undeclared |

**Agent overhead is real spend.** Every haiku/sonnet/opus task receives ~10k tokens of system prompt + task spec on top of its output, and that overhead bills to the user's Claude Code quota. Earlier renmark versions footnoted this; that broke vibe-coder trust when "$0.02 estimated" became "$0.20 actual." Bake the overhead into the displayed total. No footnotes.

Concretely: for a sonnet task with `est_tokens: 500`, display cost = `(500 + 10000) / 1000 × 0.003 = $0.0315`, not `$0.0015`.

Show per-task cost AND a single bold total at the bottom. The vibe coder should see one honest number.

### 7. Write the plan

Save to `.renmark/plans/YYYY-MM-DD-<topic>.plan.md`. Include:
- Title + context (1 paragraph)
- Task blocks in the format above
- Cost preview at the bottom

**Before writing, check task count.** `renmark-execute` caps at 15 tasks per run (default). If the plan exceeds this, split at a wave boundary into two plan files (`...-part1.plan.md`, `...-part2.plan.md`) and tell the user before showing the hand-off prompt.

**Node.js projects:** If the plan has a `package.json` task, add a `npm install` setup task immediately after it in the same wave or the next wave — before any task whose verifier does `node -e "require(...)"`. The verifier will fail if `node_modules` doesn't exist yet. Mark it `executor: haiku`, `complexity: simple`, `verifier: test -d node_modules`.

### 8. Auto-validate, then hand off (wizard step — review gate before any LLM spend)

**8a. Validate automatically.** Immediately after writing the plan, run the `/renmark:check-plan` validation against it — the user does NOT invoke it separately. Run check-plan's checks (Steps 1–3 of that skill) but **do not trigger check-plan's own orchestrate hand-off**: plan owns the dispatch gate below, so check-plan here is validation-only.

- **BLOCK** → report the blocking issues, fix them in the plan file (or tell the user what to change), and re-validate. Do not show the dispatch gate until the plan passes. Lifecycle stays `plan-drafted`.
- **PASS / WARN** → surface any WARNs as one-liners, then call `lifecycle.write_lifecycle(repo, stage='plan-validated')` and continue to 8b. (This is why the user never runs check-plan by hand — a clean plan lands at `plan-validated` automatically.)

**8b. Dispatch gate.** This is the critical approval gate. Once `/renmark:orchestrate` runs, real API tokens start flowing. Make the user actively approve.

**Invocation-context contract (single dispatch gate — never two, never silent).**
The dispatch gate has exactly one owner per flow:

- **Standalone** (`/renmark:plan` invoked directly by the user): `plan` **owns** this Step 8b
  dispatch gate. Run it as written below.
- **Embedded in `/renmark:feature`** (plan invoked as that wrapper's Step 3): `plan`
  **suppresses** this Step 8b gate entirely. It stops after 8a at `plan-validated` and
  returns control to the `feature` router — `feature` owns the single dispatch approval
  before it invokes orchestrate (see `feature/SKILL.md` §3–4). Do **not** show the
  dispatch menu, and do **not** auto-invoke orchestrate, from within the embedded plan.

This guarantees the wrapper flow presents **one** dispatch approval (owned by `feature`),
never two, and orchestrate is **never** reached without an explicit human approval.

**Headless gate (standalone path only).** This branch lives inside the standalone
ownership block above — the embedded-in-`feature` path has already suppressed this
gate and is unaffected. When `plan` **owns** the gate (standalone), before rendering
the dispatch picker consult:

```python
from renmark import headless
result = headless.resolve_gate(
    repo, "dispatch", kind="dangerous",
    originating_skill="plan",
    what="dispatch N tasks ~$X",
)
```

- **Headless** (`result["mode"] != "interactive"`): cost/dispatch needs a human, so
  `resolve_gate` returns the `halt_for_human_review` `needs_input` envelope. Emit that
  envelope as the fenced JSON block and `headless.render_return(result)` as the single
  prose line, then **STOP** — do **not** render the dispatch menu and do **not** invoke
  orchestrate.
- **Interactive** (`result["mode"] == "interactive"`): the contract is inert — render
  the existing dispatch menu unchanged (everything below).

Show a clear summary:

> *"Plan written to `.renmark/plans/<name>.plan.md` — validated ✓ (check-plan: PASS, W warnings)*
> *Tasks: N (M parallel groups)*
> *Total tokens (incl. ~10k Agent overhead/task): ~T*
> *Total cost: ~$X*
> *Executors: haiku×a, codex×b, sonnet×c, opus×d*
>
> *What's next?*
> *  1. [d] Dispatch (Recommended) — spin up AI subagents to implement the plan, then auto-verify on completion*
> *  2. [r] Review — open the plan file so you can read every task before approving*
> *  3. [e] Edit — tell me what to change; I'll rewrite the plan and re-validate it*
> *  4. [n] No — stop here; the validated plan stays on disk to dispatch later"*

**Present this through `renmark.interaction.build_selector`** (PRIMARY): mark
`Dispatch [d]` as the sole recommendation so it is option 1 on both hosts.
Claude Code uses `AskUserQuestion` (all 4 options); Codex uses
`request_user_input` (recommended + highest-priority alternatives, with the full
numbered fallback printed for overflow). If the selector is unavailable,
declined, empty, or invalid, print the same recommended-first numbered fallback;
selector absence alone is not headless. A choice is required either way.

On **1 / d** → immediately invoke `/renmark:orchestrate <plan-path>`. Don't make the user retype.
On **2 / r** → cat/open the plan file in the conversation, then re-ask the same prompt.
On **3 / e** → ask what to change, rewrite the plan, re-run 8a (re-validate), then re-show the summary.
On **4 / n** → stop. Plan stays on disk for later (already validated at `plan-validated`).

**Next-step contract (shared, by reference — class 1 / Pipeline).** This hand-off
follows the single-source next-step contract. Per
`${CLAUDE_PLUGIN_ROOT}/skills/.shared/next-steps.md`:

> *End by calling `renmark.lifecycle.next_steps(repo, "plan")` and render the
> result per `${CLAUDE_PLUGIN_ROOT}/skills/.shared/next-steps.md` (class 1 —
> Tier-0 stage routing). Present via `AskUserQuestion` (handoff-menu.md rules
> 6–9); the state-derived next command is the `(Recommended)` option. Require an
> explicit choice — never auto-proceed.*

(The Dispatch gate above is plan's stage-derived recommendation when standalone;
the single-dispatch-gate ownership rules in 8b are unchanged.)

## Plan file format example

```markdown
### Task 1: gitignore
- **mode:** A
- **target:** .gitignore
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 1
- **est_tokens:** 150
- **est_cost_usd:** 0.00
- **verifier:** test -f .gitignore
- **serves:** REQ-1
- **spec:**
  Create a .gitignore with __pycache__/, *.pyc, .venv/, .pytest_cache/.

### Task 2: server module
- **mode:** A
- **target:** server.py
- **complexity:** medium
- **executor:** codex
- **parallel_group:** 2
- **est_tokens:** 900
- **est_cost_usd:** 0.02
- **verifier:** python3 -m py_compile server.py
- **serves:** new
- **spec:**
  ...
```

## Reference

- Auto-routing heuristics: `PLAN.md` § "Auto-routing heuristics"
- Memory files: `.renmark/memory/routing.md`, `learnings.md`, `conventions.md`

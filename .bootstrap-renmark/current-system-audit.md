# Current-System Audit

**Phase B deliverable** per `governing-bootstrap-directive.md` §5. This audit is **descriptive only** — it does not redesign the system, and no production code was modified to produce it.

**Method:** the General Contractor dispatched 5 parallel read-only Explore subagents (no write/edit tools) against the repository, one per required audit domain, then synthesized their findings below. This is consistent with the bootstrap authority matrix (`authority-matrix.md`): these are audit helpers, not Workers under the target role model — they carry no authority and their raw output is not treated as approved findings on its own; this synthesis is the actual audit artifact.

**Note on one subagent result:** the first subagent's raw output was flagged by the harness as containing "instruction-shaped" text and was auto-neutralized before reaching the General Contractor. On inspection, the flagged text was template placeholder syntax (`${CLAUDE_PLUGIN_ROOT}/skills/<name>/SKILL.md`) being quoted from the plugin's own command-shim convention, not an actual injected instruction. Treated as a normal finding below; no other action taken.

---

## 1. Command entrypoints and plugin initialization

`plugin/commands/` has **30** thin markdown shims, one per `/renmark:*` subcommand (analytics, approve, audit, backlog, blueprint, brainstorm, check-plan, codereview, debug, doctor, eval, feature, finish, guide, heartbeat, help, hygiene, init, inventory, loop, orchestrate, plan, prd, resume, roadmap, scan, setup, start, usage, verify). Each is YAML frontmatter (`description`, `argument-hint`) + one line: "Read `${CLAUDE_PLUGIN_ROOT}/skills/<name>/SKILL.md` and follow its instructions exactly." All actual logic lives in `plugin/skills/<name>/SKILL.md` prose files. `plugin/.claude-plugin/plugin.json` / `plugin/.codex-plugin/plugin.json` are simple manifests — command/skill discovery is directory-convention-based, not manifest-declared.

**Install:** `install.sh` symlinks `plugin/` → `~/.claude/plugins/renmark` and registers via `python3 -m renmark.doctor --fix` (writes `extraKnownMarketplaces`, `enabledPlugins`, `installed_plugins.json`). Codex side symlinks `~/plugins/renmark` and registers in `~/.agents/plugins/marketplace.json`. Also symlinks `renmark-execute`/`renmark-browser` into `~/.local/bin` and does an editable `pip install -e`.

## 2. Orchestration core (4 modules, no direct LLM calls)

- **`renmark/program.py`** (846 lines) — staged-program data model, persisted to `.renmark/state/program.json`. `Program`/`StageNode`/`TaskNode`, `read_program`/`write_program`, `mark_task`/`mark_stage`/`bump_retry`.
- **`renmark/program_driver.py`** (641 lines) — deterministic outer state machine. Reads only structured `stage_result` dicts, never prose ("a pass is never inferred from free text"). `next_stage`, `evaluate_stop`, `advance_on_success` (write-before-return for crash safety).
- **`renmark/dispatch.py`** (718 lines) — wave-based parallel dispatcher for `/renmark:orchestrate`. `group_tasks_by_wave`/`validate_wave` enforce disjoint write targets per parallel group. `SubagentInput`/`SubagentOutput` (frozen dataclasses, schema-enforced via `IsolationViolation`) are the **only** fields a subagent may receive/emit — this is effectively today's Work-Order/Worker-Return contract already. Because Python can't call Claude directly, `build_host_dispatch_plan` shapes a `HostDispatchPlan` that the *calling agent turn* actually executes via Claude's Agent/Workflow tools or Codex's `spawn_agent`/`wait_agent`.
- **`renmark/lifecycle.py`** (1715 lines, largest module) — per-feature workflow state (`lifecycle.json`), enforcing Brainstorm → Plan → Create → Test → Review → Document → Release, kept strictly separate from `pipeline.json`. Owns `next_recommended`/`next_steps` (the canonical "what next" contract every skill consumes), human-approval gating (`halt_for_human_review`), and `skill_preamble`.

**Typical flow:** command md → SKILL.md prose drives the agent → `lifecycle.py` for state/gating → `program.py` for the plan → `program_driver.py` decides next stage → `dispatch.py` fans tasks to isolated subagents → outputs collected and validated → `advance_on_success` persists.

## 3. Agent dispatch, Claude/Codex execution, model routing

- **`renmark/subagent_gate.py`** — pure, zero-LLM "deterministic-first" gate run *before* any dispatch: 4 mechanical questions (deterministic-eligible? scriptable? inlineable under ~400 tokens? complexity justifies a subagent?). Defaults conservative.
- **`renmark/subagent_profiles.py`** — registry of 8 role profiles + `general-purpose` fallback, each declaring `model_tier` (cheapest-capable — haiku for read-only/docs/audit, sonnet for code/tests/review), `allowed_targets`, `context_scope` (narrow/broad).
- **`renmark/worktree.py`** — git-worktree isolation, pure subprocess, no model calls.
- **`renmark/providers/claude_agent.py`** — since Python can't call Claude, only *prepares* dispatch (`build_agent_dispatch` → model ∈ {haiku,sonnet,opus,fable}); the orchestrate skill issues the actual `Agent` tool call and logs via `record_outcome()`.
- **`renmark/providers/codex.py`** — `run_codex_task` shells out to `codex exec` via subprocess, diffs git-porcelain before/after, `check_only_target_modified()` rejects out-of-scope edits.
- **`renmark/codex_routing.py`** — Claude-tier → Codex-native model/effort translation (`EASY_ROLES`/`HARD_KINDS`).
- **`bin/renmark-execute`** — the single subprocess CLI entrypoint (`python3 -m renmark`), not Codex-specific.
- **Model routing is a composite**, not one function: `subagent_profiles` picks cheapest-capable Claude tier by role; `codex_routing` picks Codex model/effort; `renmark/cost.py::requires_escalation` gates opus/fable (only for `complexity=="hard"` or kind ∈ {architecture, adversarial-review, design-fork}); `renmark/sizing.py::classify_plan/classify_diff` gates lite/standard/full pipeline lane (`DEFAULT_TIER="standard"` safe fallback).
- **`renmark/global_routing.py`** is unrelated to model routing — it installs the "default plain-English asks to renmark pipelines" instruction block into the host's global config file.

**WritingMate:** zero references anywhere in `renmark/` source, `bin/`, or tests. Only appears in this bootstrap's own planning docs (Milestone 10, explicitly gated/blocked).

## 4. Context, memory, PRD/planning

- **`renmark/context.py`** — a taxonomy/classification module (`ContextKind`: STATIC/DYNAMIC/MEMORY/TASK_LOCAL), not a loader. `assert_metadata_only` guards against pre-loading skill bodies.
- **Budget check** lives in `renmark/state/skills.py`: `context_budget_hint(tokens)` (100k/120k/150k tiers → summarize/compact/checkpoint hints) and `context_budget_check` (cross-domain transition → recommend `/clear`). Wired into `lifecycle.skill_preamble`.
- **`renmark/memory.py`** (732 lines) — append-only writers per memory file (`log_feature`, `log_bug`, `log_decision`, `append_routing`, `append_learning`), plus `dedupe_memory_log`/`age_out_memory_log` maintenance. `.renmark/memory/` holds 13 files (INDEX, project, stack, architecture, features, bugs, decisions, conventions, routing, learnings, qa-flows, project-map, dev-standards, analytics, roadmap) — an already-established "load index before body" convention.
- **PRD → plan → tasks:** `/renmark:prd` owns `PRD.md` as the human-gated source of truth (not used for decomposition). `/renmark:plan` reads a spec → emits `.renmark/plans/*.plan.md` (each task: mode/target/complexity/executor/parallel_group/verifier/serves-PRD-req-id/est_tokens/est_cost). `renmark/parser.py` parses these (`parse_plan`, `parse_package_plan` → `WorkPackage`/`Milestone`/`PackagePlan`). `renmark/plan_lint.py` (`/renmark:check-plan`) runs ~10 mechanical checks → PASS/WARN/BLOCK verdict. `renmark/work_packages.py` compiles `WorkPackage`s into dispatch-ready `CompiledTask`s.
- **State persistence:** `renmark/state/_core.py` defines shared paths/rotation caps. `pipeline.json` (runtime-only: phase, plan, wave index, completed/failed tasks) is explicitly kept separate from `lifecycle.json` (workflow/approval state) — this separation is already exactly what the target architecture's Milestone Contract vs. Pipeline State distinction wants. `renmark/delivery_state.py` manages `delivery.json` with a hard byte budget (4096 bytes, raises `DeliveryStateBloatError`) and caps on provenance events/work packages — an existing precedent for enforced artifact size limits.

## 5. Verification, retry/replan, compatibility

- **`renmark/verifier.py`** — mechanical: `exit_code==0 and not timed_out`. No semantic interpretation.
- **`plugin/skills/verify/SKILL.md`** — 3 modes: Smoke (default, shell-only, `.verification.md`), QA (`--qa`, live browser happy-path via Playwright/Chrome DevTools MCP, `.qa.md`), Deep QA (`--deep-qa`, 3 risk-ranked edge cases, gated on a passing QA for the current sha, `.deep-qa.md`). Explicit principle: "shell tests prove exit 0, not user-visible correctness." Every run appends to `learnings.md`; failures append to `bugs.md` (compounding verification).
- **`renmark/browser.py`/`browser_cli.py`** — real Playwright-backed session/profile manager backing the QA path.
- **Retry/replan is already bounded in two independent layers:**
  - `renmark/loop.py` (`/renmark:loop`): `DEFAULT_MAX_ITERATIONS=5`, `budget_tokens`, `stop_reason()` checks budget-exhausted → max-iter, in that order. `build_decision()` derives `goal_reached` strictly from structured verification fields, never prose.
  - `renmark/program_driver.py`: `MAX_TASK_RETRIES=3`; `evaluate_stop()` maps structured stage-result signals to a `StopReason` in strict severity order (RETRY_EXHAUSTED → PLAN_BLOCK → PRD_DRIFT → CODEREVIEW_CRITICAL → AWAITING_APPROVAL → PAUSED → VERIFY_FAILED). Explicit design note: "stops degrade toward stopping, never running unbounded."
  - `renmark/recurrence.py` is a separate, distinct mechanism — tracks *repeated issue signals* (not task retries), decides patch vs. durable-guard escalation, capped at `MAX_ENTRIES=512`.
- **No unbounded recursion found.** Dispatch is one bounded call per subagent, schema-enforced (`IsolationViolation` on breach). All iteration ceilings are explicit and independently enforced by two different modules.
- **Host compatibility:** `renmark/hosts.py` (`HostKind`: CLAUDE_CODE/CODEX/UNKNOWN, capability table for selector tool availability, resolved via explicit arg → env var → auto-detect → default). `renmark/mode.py` handles delivery-mode persistence with explicit legacy-value compatibility handling (old `"conductor"` mode silently normalized on read, never written).

## 6. Artifact schemas, tests, analytics/ledgers

- **`renmark/schemas.py`** (800 lines) — 11 `validate_*(data) -> list[str]` functions (lightweight issue-list validators, not Pydantic classes): milestone doc, lifecycle, pipeline, delivery-state, subagent-output (the isolation gate), artifact-metadata, limits, analytics-summary, report-metrics, event, usage-pause. Real dataclasses exist only in `renmark/cost.py` (`CostPreview` family).
- **Tests:** 89 top-level entries in `tests/`, ~80 `test_*.py` files, **1683 tests collected**. Categories: dispatch/orchestration, lifecycle/state, verification, loop/engine, analytics/cost, scan/backlog, schemas, program/roadmap/hygiene/usage/heartbeat/memory/worktree. `tests/integration/` (5 e2e: cold-start recovery, plugin install, Codex fallback, full smoke lifecycle). `tests/behavioral/` (5 JSON behavior fixtures incl. `selector_claude`/`selector_codex`).
- **Analytics/cost:** `renmark/analytics.py` (835 lines) — append-only JSONL under `.renmark/analytics/` (`events.jsonl`, `task-runs.jsonl`, `feature-runs.jsonl`, `loop-runs.jsonl`, `summary.json`), registered `EVENT_KINDS` (loop_iteration, pause, resume, rate_limit, quota, release, backlog_completed/blocked/rejected — unregistered kinds still persist, flagged). `renmark/cost.py` (448 lines) does deterministic cost estimation, reading (never duplicating) the separate token-usage ledger.
- **Existing ledger mechanisms — already plural, not unified:** analytics events/task-runs/feature-runs/loop-runs; token usage ledger (`renmark/usage.py`); scan dedup ledger (`renmark/scan.py`, with an advisory lock serializing load→check→write→save); delivery-state provenance (`append_provenance_event`); memory routing/learning appends; debug session log; backlog (explicitly documented as "the deterministic, persistent ledger of work items"). **This is the single biggest gap versus the target architecture's Milestone 2 (single canonical `ledger/events.jsonl`)** — Renmark today has many siloed purpose-specific logs, not one.

---

## Cross-cutting observations (descriptive, not proposals)

These are patterns visible across all five audit domains, noted here as evidence for the Milestone 0 contract and the future Architect pass — not architectural decisions.

1. **A large fraction of the target architecture's Milestone 1–2 primitives already exist** under different names: `SubagentInput`/`SubagentOutput` ≈ Work Order/Worker Return; `subagent_gate.py` + `subagent_profiles.py` ≈ partial Governor/Foreman; `pipeline.json` vs `lifecycle.json` separation ≈ partial Milestone-Contract/Role-state separation; `program_driver.py`'s structured-signal-only stop evaluation ≈ R-009 ("no unsupported success claims") already partially enforced; `delivery_state.py`'s byte-budget-with-hard-error ≈ precedent for R-008-style enforced limits.
2. **The largest true gap is a unified Ledger** (target Milestone 2) — today's ledgers are siloed per subsystem with no cross-referencing schema.
3. **No Role/Authority enforcement layer exists** (target Milestone 1) — `subagent_gate.py` and `subagent_profiles.py` gate *whether/how* to dispatch, not *whether the dispatched role is permitted to do what it's attempting*. There is no `IsolationViolation`-equivalent for e.g. "an Inspector tried to write a file."
3a. There is also no Architect/Engineer separation (target Milestone 3) — `/renmark:brainstorm` and `/renmark:plan` are both single-pass skill invocations without a frozen-blueprint gate between them.
4. **WritingMate integration is correctly absent** from the codebase — consistent with the governing roadmap's explicit Milestone 10 sequencing (blocked on M-1–M-6).
5. **Test coverage is substantial** (1683 tests) — any refactor touching `dispatch.py`, `lifecycle.py`, `program_driver.py`, or `schemas.py` has a large existing regression net to preserve, which the baseline-scenario measurement in Milestone 0 should account for (running the full suite is itself a cost data point).

## What this audit deliberately did not do

- Did not propose new modules, schemas, or file layouts.
- Did not estimate migration effort or file-level Milestone 1+ scope.
- Did not run the three baseline scenarios from governing-architecture-roadmap.md §14.2 — that requires Owner approval of the M-0 contract's budget/scope first (see `milestones/M-0/contract.yaml`).
- Did not invoke any `/renmark:*` command.

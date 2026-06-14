---
artifact_type: research
schema_version: 1
created_at: 2026-06-14T01:51:29+00:00
source_sha: b5b252e020a1dae0e5c1a597569f5a4399d1c015
related_plan: null
generator: brainstorm-research
stale_after: null
dependency_refs: []
completion_state: complete
confidence: medium
validation_status: unvalidated
retry_count: 0
parser_success: true
schema_compliance: true
---

# Prior Art & Best Practices: Staged/Autonomous Multi-Step Agentic Execution with HITL

## Research Context

**Problem:** Design a "staged program planner" for renmark (Claude Code plugin) that breaks a
feature/project into STAGES → TASKS, then after a single human approval autonomously drives each
stage through plan → execute → verify, proceeding on success and stopping only on
failure/blocker.

**Stack:** Python 3.10+ + Claude Code plugin (markdown skills + Python runtime).

**Date:** 2026-06-13

---

## Sources Consulted

1. Kinde — "Orchestrating Multi-Step Agents: Temporal/Dagster/LangGraph Patterns for Long-Running Work"
   https://www.kinde.com/learn/ai-for-software-engineering/ai-devops/orchestrating-multi-step-agents-temporal-dagster-langgraph-patterns-for-long-running-work/
2. Augment Code — "Why Multi-Agent LLM Systems Fail and How to Fix Them"
   https://www.augmentcode.com/guides/why-multi-agent-llm-systems-fail-and-how-to-fix-them
3. Towards Data Science — "Building Human-In-The-Loop Agentic Workflows"
   https://towardsdatascience.com/building-human-in-the-loop-agentic-workflows/
4. Durable Execution for Crashproof AI Agents (DBOS)
   https://www.dbos.dev/blog/durable-execution-crashproof-ai-agents
5. Zylos Research — "AI Agent Workflow Checkpointing and Resumability (2026)"
   https://zylos.ai/research/2026-03-04-ai-agent-workflow-checkpointing-resumability/
6. CallSphere — "Comparing Workflow Engines for AI Agents: Temporal vs Prefect vs Airflow vs Custom"
   https://callsphere.ai/blog/comparing-workflow-engines-ai-agents-temporal-prefect-airflow-custom
7. Vellum — "The 2026 Guide to AI Agent Workflows"
   https://www.vellum.ai/blog/agentic-workflows-emerging-architectures-and-design-patterns
8. ZenML — "What 1,200 Production Deployments Reveal About LLMOps in 2025"
   https://www.zenml.io/blog/what-1200-production-deployments-reveal-about-llmops-in-2025
9. OpenHands Agent Framework (arxiv 2511.03690)
   https://arxiv.org/html/2511.03690v1
10. Xgrid — "Temporal AI Agent Failures: 11 Production Pitfalls"
    https://www.xgrid.co/resources/temporal-ai-agent-orchestration-failure-patterns/

---

## Assumptions & Perspective

**Assumptions made:**
- renmark's pipeline already has single-task execution (orchestrate skill); "staged planner" adds
  a layer ABOVE it: multi-stage grouping with a single upfront human gate.
- "Stop on failure" means the runner halts the stage, writes failure state to disk, and surfaces a
  human-readable blocker before doing nothing further — it does NOT roll back autonomously unless
  the Saga pattern is explicitly implemented.
- "Single human approval" is the key constraint: approve the PLAN once, then run autonomously.
  This is distinct from per-task approval (which LangGraph interrupt() supports but renmark
  intentionally avoids for flow).
- Context window is Sonnet 200k and is a binding constraint — the staged planner must NOT
  accumulate stage-level context across stages.

**Edge cases flagged:**
- What if stage N's output invalidates stage N+1's plan? (Drift between plan time and execute
  time.)
- What if a stage has partial success — some tasks pass, some fail? Does the stage fail atomically
  or does it checkpoint at the task level?
- Concurrent writers across stages that touch shared files: renmark's current model is
  sequential-per-task; staged planner must inherit that constraint.
- A "blocker" vs a "transient error" distinction: runaway retries are a known anti-pattern;
  the runner must classify failures before deciding to stop vs retry.

---

## Findings (Evidence-Based)

### A. Stage→Task Structure & Progress Tracking

**LangGraph pattern (most relevant):** StateGraph with nodes (tasks) and edges (routing logic).
Each node modifies a shared graph state object; conditional edges implement "proceed on success,
stop on failure." State persists between node executions via checkpointer (SQLite or Redis
backend), enabling resume from interruption.
- Key quote: "The graph consists of nodes (functions or tools) and edges (logic that directs the
  flow from one node to another)." Nodes modify shared state; edges route conditionally.
- Interrupt mechanism: `interrupt_before=["node_name"]` pauses the graph and waits for external
  input. Can be used for a single upfront gate (interrupt before the first execution node, not
  on every task).

**Temporal pattern (durable execution):** Workflow code runs to completion regardless of infra
failures. Each "activity" is a durable step. Temporal replays from last checkpoint on crash.
- Key quote: "If the worker crashes while executing a step, Temporal will restart it on another
  worker without re-running previous activity."
- Idempotent activities are mandatory; each activity must produce the same result on retry.
- Heartbeat pattern: long-running LLM calls must heartbeat; otherwise the platform times out
  and issues duplicate calls.

**Dagster pattern (asset-based lineage):** Each step produces a "software-defined asset"
(persistent file, DB record). Re-running partial pipelines resumes from materialized upstream
assets. Best for data-pipeline-style workflows where outputs are discrete artifacts.

**Synthesis for renmark:**
The most borrowable pattern is: stage = named state machine phase; task = idempotent activity
within that phase; progress state = JSON on disk (already renmark's pattern in pipeline.json).
LangGraph's conditional-edge routing maps cleanly to renmark's existing wave-based orchestration.
The staged planner adds a "stage loop" above the existing wave loop:

```
for stage in plan.stages:
    if pipeline_state.stage_status[stage.id] == "complete": continue  # resume
    for task in stage.tasks:
        result = execute_task(task)
        write_task_state(task.id, result)
        if result.status == "FAIL": raise StageBlocker(task, result)  # stop stage
    write_stage_state(stage.id, "complete")
```

**Key borrow from Temporal:** Write state BEFORE returning from each activity (task), not after.
This is the difference between "checkpoint" and "log."

### B. Human Gates: Where They Add Safety vs. Friction

**Empirical evidence from production:**
- 41.77% of multi-agent failures are specification problems (MAST taxonomy, Augment Code research).
  Human review of the PLAN (before execution) addresses the highest-frequency failure class.
- Verification gaps (21.30%) are best addressed by automated judge agents, NOT human review
  mid-pipeline — human mid-pipeline review is slower and adds context-switching overhead.
- The OpenHands/Devin model uses a single upfront human trigger (issue ticket) → autonomous
  execution → human review only at PR submission. This maps directly to renmark's "approve plan
  once, then run" design.

**Where human gates GENUINELY add safety (blocking requirements):**
1. Plan approval (before execution begins): covers the 41.77% specification-failure class.
   Human can catch scope creep, wrong decomposition, dangerous file-touch lists.
2. Post-stage gate for DESTRUCTIVE stages (e.g., DB migrations, schema changes, irreversible
   file deletions): these are low-frequency but high-consequence. Recommend a per-stage metadata
   flag `requires_human_gate: true` that the runner checks.
3. Blocker surfacing: when a stage halts on failure, the runner writes a structured blocker
   report and requires explicit human `/renmark:approve` before resuming. This is NOT a
   mid-task interruption — it's a stop-and-wait-for-input at stage boundary.

**Where human gates ADD FRICTION without safety payoff (deferrable):**
- Per-task approval on mechanical/haiku-routed tasks (file writes, boilerplate generation).
  LangGraph's middleware can do this but renmark explicitly avoids it — correct call.
- Approval prompts on tasks already covered by CI/verifier (if the verifier passes, the output
  is validated; human approval is redundant).

**Anti-pattern (from Augment Code):** Requiring approval so frequently that operators approve
without reading. Cognitive load from high-frequency gates erodes the safety they provide.

### C. Failure-Detection Patterns

**MAST taxonomy (Augment Code, 79% of production failures):**
- Specification problems: detected by verifier/judge agent checking output against original spec.
- Coordination failures: detected by resource ownership tracking (which agent/task owns which
  file).
- Verification gaps: detected by mandatory post-task validator with structured pass/fail result.

**Concrete detection signals (actionable for renmark):**

1. **Structured exit codes + validation_status field** (already in renmark artifact schema):
   Every task artifact carries `completion_state`, `validation_status`, `confidence`. The stage
   runner reads ONLY these fields. If `completion_state != "complete"` or
   `validation_status == "failed"`, the stage stops. This avoids LLM interpretation of success.

2. **Idempotency check before retry:** Before retrying a failed task, verify the task's output
   file does NOT already exist in a partial-success state. Temporal heartbeat pattern: check
   `did_task_already_produce_output()` before re-running.

3. **Circuit breaker for runaway retries (Augment Code):** Set `max_retry_count` per task (e.g.,
   3). If `retry_count >= max_retry_count`, classify as BLOCKER (not transient), write
   `stage_status = "blocked"`, and require human intervention. Never retry indefinitely.

4. **Concurrent writer detection:** Renmark already serializes tasks sequentially within a wave.
   The staged planner must enforce: tasks in different stages NEVER touch the same file unless
   they are in a declared dependency chain. Enforce this at plan-check time, not at runtime.

5. **Drift detection between plan and execution:** After each stage completes, write a
   `stage_N_completion_sha` to pipeline.json. Before starting stage N+1, verify the relevant
   source files haven't diverged from what was planned. If SHA changed, surface a drift warning.

**Anti-patterns to avoid (from research):**
- Silent drift: agent interprets ambiguous task slightly differently per run. Fix: machine-
  readable task specs (JSON schema), not prose-only descriptions.
- Context rot in long stage chains: if the orchestrator reads all prior stage outputs into
  context, window fills and quality drops. Fix: orchestrator reads ONLY summary_lines (≤5 lines,
  ≤300 tokens) from each stage's artifact — renmark already mandates this.
- Runaway loops: simple "repeat until done" loops without iteration limits. Fix: every task has
  a `max_retry_count`; every stage has a `max_task_count` assertion at plan-check time.

---

## Recommendations (Synthesized)

### (a) How to structure stage→task progress + resumability

**Structure:**
```
pipeline.json (runtime)
  stages: [
    { id, name, status: pending|running|complete|blocked, tasks: [task_ids] }
  ]
  tasks: [
    { id, stage_id, status, artifact_path, retry_count, completion_state, validation_status }
  ]
  current_stage: int
  current_task: int
  stage_completion_shas: { stage_id: git_sha }
```

**Resumability rules:**
- On startup, read pipeline.json. Skip stages with status=="complete".
- For blocked stages, require explicit human unblock (/renmark:approve) before resuming.
- For running stages (crashed mid-execution), re-read task statuses from artifact files (not
  from pipeline.json alone) — artifact files are the source of truth for task completion.
- Never re-run a task with `completion_state=="complete"` and `validation_status=="validated"`.

**Progress checklist:** Write a human-readable `.renmark/state/progress.md` after each task and
each stage transition. This is separate from pipeline.json (machine state) — it's for human
inspection during long runs. Keep it bounded (≤20 lines; overwrite, don't append).

### (b) Where human gates genuinely add safety vs. friction

**ADD (blocking requirements):**
1. Single upfront plan approval (covers 41.77% of failure class; highest ROI gate).
2. Per-stage gate for stages flagged `requires_human_gate: true` in plan metadata.
3. Explicit resume-from-blocker gate (human must acknowledge failure before pipeline continues).

**REMOVE / avoid (friction only):**
1. Per-task approval on verified/mechanical tasks.
2. Approval prompts after successful CI/verifier pass.
3. Mid-stage interruptions for non-destructive operations.

**Recommended UX:** After plan approval, show a live progress checklist. Only interrupt the
human when: (a) a stage hits BLOCKER, or (b) a stage has `requires_human_gate: true`.

### (c) Failure-detection patterns (concrete)

1. **Structured artifact fields are the primary signal.** Never use LLM-interpreted success.
   Read `completion_state` and `validation_status` from task artifacts.
2. **Circuit breaker at `max_retry_count` (recommend: 3).** Exceeded → BLOCKER, not transient.
3. **Post-stage SHA snapshot** in pipeline.json for drift detection before next stage.
4. **Resource ownership declared at plan time.** Concurrent-writer conflicts caught at
   plan-check (before execution), not at runtime.
5. **Judge/verifier agent isolation.** Independent verifier with its own context checks
   implementation against original spec after each stage (not just each task).

---

## What This Research Does NOT Cover (Gaps)

- Exact renmark Python class design for the stage runner (not in scope for research).
- Whether to store pipeline.json in SQLite vs flat JSON for concurrent-writer safety (renmark is
  single-writer by design, so flat JSON is fine; revisit if parallel stage execution is added).
- Rollback/saga pattern implementation — compensating actions for destructive stages were noted
  but not detailed. Mark as DEFERRABLE for v2 if destructive stages are added.
- Specific LLM token budgets per stage vs per task — this depends on stage complexity; no
  empirical data found for renmark's specific workload.

---

## Tradeoffs the Asker May Not Have Weighed

1. **"Single human approval" is optimistic for multi-day runs.** If the plan is approved on
   Monday and stage 4 runs Wednesday after unrelated commits landed, the plan may reference
   stale file states. The SHA-snapshot drift detection above mitigates this, but does not
   eliminate it. Consider: re-validate plan freshness at each stage start (cheap: compare
   `stage_completion_sha` to HEAD).

2. **"Stop on failure" vs "stop on stage failure" distinction.** Stopping on a TASK failure
   (strict) vs stopping only when the STAGE as a whole fails (lenient, e.g., if 4/5 tasks pass)
   has different UX implications. The strict model is safer for renmark's current design.
   Lenient mode requires a "partial stage" state and more complex resume logic.

3. **Living progress checklist is useful but creates a new stale-artifact risk.** If the
   progress.md is written by the orchestrator (reads summaries) and the orchestrator context is
   compacted mid-run, the checklist may fall behind. Mitigation: write progress.md from
   pipeline.json (machine state), not from LLM memory.

4. **Human approval UX inside Claude Code is limited.** LangGraph's `interrupt()` mechanism is
   rich (edit/approve/reject/respond). Claude Code's equivalent is /renmark:approve — simpler.
   Don't design the gate to require structured human input (e.g., "edit this JSON") because
   that UX doesn't exist cleanly in the CLI. Keep gates binary: approve/reject + optional
   free-text reason.

## Summary

- Best practice: plan-once-approve gate covers 41.77% of failures; structured exit codes (not LLM interpretation) drive stop-on-failure.
- Top prior art: LangGraph StateGraph checkpoints + Temporal idempotent activities + Dagster asset-based lineage.
- Failure-detection: read completion_state+validation_status from artifact metadata; circuit-break at max_retry_count=3.
- Key risk: plan-time drift — source files may change between approval and stage execution; snapshot stage SHAs in pipeline.json.
- Artifact: .renmark/research/2026-06-13-roadmap-staged-planner-bestpractice.research.md

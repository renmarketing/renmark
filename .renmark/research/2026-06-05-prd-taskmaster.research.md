---
artifact_type: research
schema_version: 1
created_at: 2026-06-05T14:25:08+00:00
source_sha: null
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

# Research: TaskMaster (claude-task-master) PRD & Task Management vs renmark

## Sources
- TaskMaster repo README: https://github.com/eyaltoledano/claude-task-master
- Task structure doc: https://github.com/eyaltoledano/claude-task-master/blob/main/docs/task-structure.md
- Command reference: https://github.com/eyaltoledano/claude-task-master/blob/main/docs/command-reference.md
- IntelliSoft, lean PRD: https://intellisoft.io/product-requirements-document-prd-why-make-it-lean/
- Plane, PRD engineers read: https://plane.so/blog/how-to-write-a-prd-that-engineers-actually-read
- Atlassian PRD guide: https://www.atlassian.com/agile/product-management/requirements
- Aha! PRD template: https://www.aha.io/roadmapping/guide/requirements-management/what-is-a-good-product-requirements-document-template
- Uladzislau Shauchenka, modern PRD: https://www.uladshauchenka.com/p/how-to-write-a-good-product-requirements

## 1. TaskMaster — PRD ingestion (parse-prd flow)

- **PRD file location:** new projects -> `.taskmaster/docs/prd.txt`; existing/legacy -> `scripts/prd.txt` (migrate with `task-master migrate`).
- **Format:** plain text document (`.txt`). Doctrine: "Always start with a detailed PRD. The more detailed your PRD, the better the generated tasks will be."
- **Command:** `task-master parse-prd <prd-file.txt>`
  - `--num-tasks=5` limits generated tasks (default 10); `--num-tasks=0` = dynamic count based on PRD complexity.
  - `--append`, `--input`, `--output`, `--research` flags exist (research-backed generation).
- **Conversion:** an LLM reads the PRD prose and emits a structured task list into `tasks.json`. One-shot generation — the PRD is an INPUT, not a maintained linked artifact.

## 2. TaskMaster — task model (tasks.json)

Tagged top-level format (multi-context / per-branch):
```json
{
  "master":         { "tasks": [ { task } ] },
  "feature-branch": { "tasks": [ { task } ] }
}
```
Each tag has isolated task context and independent ID sequences.

Task fields:
- `id` (number) — unique within tag context
- `title` (string)
- `description` (string) — concise summary
- `status` (string) — `pending | in-progress | done | review | deferred | cancelled`
- `dependencies` (array of ids) — prerequisite tasks
- `priority` (string) — `high | medium | low` (default medium)
- `details` (string) — in-depth implementation instructions
- `testStrategy` (string) — verification approach
- `subtasks` (array) — nested objects mirroring main task fields with local IDs (`parent.subtask` notation, e.g. `1.2`)

## 3. TaskMaster — expansion & complexity analysis

- `analyze-complexity` scores each task 1-10, writes report to `scripts/task-complexity-report.json` (or `--output`). Report contains: complexity score, recommended subtask count (vs `DEFAULT_SUBTASKS`), AI-generated per-task expansion prompts, and ready-to-run expansion commands. Flags: `--threshold=6`, `--model=`, `--research` (Perplexity-backed).
- `expand --id=<id> --num=<n>` decomposes a task into subtasks; `--all` expands all pending (highest complexity first); `--force` regenerates; `--research`; `--num=0` dynamic.
- `complexity-report` displays the saved report.
- Complexity is used for SUBTASK COUNT recommendation, NOT for model/executor routing.

## 4. TaskMaster — command surface (CLI / MCP)

MCP tool modes: `core` (7 tools), `standard` (15), `all` (36, ~21k tokens).
- PRD/tasks: `parse-prd`, `list`, `show <id>` (supports `1,3,5` and `1.2`), `next`
- Task mgmt: `add-task --prompt`, `update --from=<id> --prompt`, `update-task --id`, `update-subtask --id=5.2 --prompt` (appends with timestamp, preserves original), `set-status --id --status` (parent done -> subtasks done), `add-subtask`, `clear-subtasks`, `move --from --to`
- Deps: `add-dependency`, `remove-dependency`, `validate-dependencies`, `fix-dependencies`
- Expansion/complexity: `expand`, `expand --all`, `analyze-complexity`, `complexity-report`
- Research: `research "query"` with `--id`, `--files`, `--tree`, `--save-to=15.2`, `--save-file` (-> `.taskmaster/docs/research/`)
- Config: `models` (`--set-main`, `--set-research`, `--set-fallback`, `--codex-cli`, `--ollama`, `--openrouter`), `tags` (per-branch contexts), `init`, `rules`

## 5. TaskMaster — PRD <-> task sync

- **No bidirectional sync documented.** PRD is parsed once into tasks; thereafter tasks evolve independently via `update`/`add-task`/`expand`. There is NO consistency check between PRD prose and the task list, and no re-parse-diff mechanism. The PRD is a seed, not a living source-of-truth the tasks are reconciled against. (Flagged: based on current docs; could change in newer versions.)

## 6. PRD best practices (general)

A good lean PRD contains:
- **Problem / Objective** — the core purpose, the problem and for whom
- **Target users / personas** — segments, needs, pain points, motivations (grounds all decisions)
- **Goals & non-goals** — explicit in-scope vs out-of-scope; non-goals prevent feature creep
- **Requirements** — described as behaviors/outcomes, not solutions
- **Success metrics / release criteria** — KPIs defining "what good looks like"
- **Scope boundaries** — current priority vs deferred-to-future; defining boundaries early "saves countless hours of debate"
- **Open questions** — capture unknowns explicitly
- **Living document** — version tracking; requirements evolve; keep lightweight, link out to supporting materials, update as decisions resolve

Core principle: the PRD is a **living source-of-truth** that downstream plans/specs align to — concise, behavior-focused, collaboratively maintained, updated as decisions evolve.

## renmark vs TaskMaster — comparison inputs

### PRD handling
- **TaskMaster:** explicit single PRD file (`.taskmaster/docs/prd.txt`, plain `.txt`), strongly mandated as the starting artifact. One-shot input to `parse-prd`. No living-doc reconciliation.
- **renmark:** no first-class "PRD" object. The analogous artifact is the spec from `/renmark:brainstorm` (`.renmark/specs/YYYY-MM-DD-<topic>.spec.md`, markdown with provenance/freshness metadata). renmark has a richer doctrine of artifacts-as-canonical-state and explicit staleness/invalidation, but does not name or template a "PRD" with the standard sections above.
- **Alignment:** both treat an upstream human-authored doc as the seed of the pipeline. **Difference:** TaskMaster centralizes on one named PRD file and bakes "always start with a detailed PRD" into culture; renmark spreads this across brainstorm->spec and has no canonical PRD template/sections (problem/users/goals/non-goals/metrics/open-questions). This is renmark's clearest gap to learn from.

### Task / plan model
- **TaskMaster:** `tasks.json` (machine-readable JSON), tagged per-branch, fields incl. `testStrategy`, `details`, `subtasks`, statuses (`pending|in-progress|done|review|deferred|cancelled`), priority (`high|medium|low`).
- **renmark:** plan is a markdown task list (`.renmark/plans/...plan.md`) of atomic single-file tasks, each tagged with an executor and a verifier; runtime status lives in `pipeline.json` / `lifecycle.json`, not embedded in the plan doc.
- **Alignment:** both decompose into atomic tasks with dependencies and a per-task verification notion (TaskMaster `testStrategy` ~ renmark verifier).
- **Difference:** TaskMaster's task list is itself the mutable state store (JSON, status fields in-file); renmark separates the plan (markdown spec, relatively static) from runtime state (separate JSON). renmark lacks TaskMaster's status taxonomy (review/deferred/cancelled) and per-task priority field. TaskMaster has no executor/model tag per task.

### Task generation from PRD
- **TaskMaster:** `parse-prd` LLM generates the whole task list in one pass (count fixed or dynamic).
- **renmark:** `/renmark:plan` (Opus) reads the spec, splits into atomic single-file tasks, and additionally scores complexity + routes each task to a model + groups for parallelism + emits a cost preview.
- **Alignment:** both are LLM-driven decomposition of an upstream doc into tasks.
- **Difference:** renmark's planning step does more (routing + parallel grouping + cost preview) than TaskMaster's parse-prd; TaskMaster splits generation (parse-prd) from decomposition (expand) into two stages, whereas renmark plans atomic tasks up front.

### Dependency / parallelism modeling
- **TaskMaster:** explicit `dependencies` arrays per task; `next` computes the next workable task from deps+status; `validate-dependencies`/`fix-dependencies` integrity tools. No parallel execution — it's an advisory next-task picker for a human/agent working serially.
- **renmark:** dependency-aware **parallel wave execution** — independent leaves dispatched concurrently as subagents/executors; orchestrator advances waves on summary fields.
- **Alignment:** both model dependencies as a DAG.
- **Difference:** TaskMaster uses the DAG to recommend one next task (serial); renmark uses it to schedule concurrent waves (parallel). renmark has no equivalent of `validate-dependencies`/`fix-dependencies` integrity tooling — TaskMaster is stronger on dependency hygiene; renmark is stronger on execution concurrency.

### Complexity scoring & model routing
- **TaskMaster:** complexity 1-10 -> recommends subtask COUNT and generates expansion prompts; a single configured main model (plus research/fallback model) does the work. Complexity does NOT pick a per-task model.
- **renmark:** complexity -> per-task executor routing to haiku/codex/sonnet/opus (cheapest capable model wins). Models also separated by role implicitly.
- **Alignment:** both compute a complexity signal per task.
- **Difference:** they USE complexity differently — TaskMaster for decomposition depth, renmark for cost/model selection. renmark could borrow TaskMaster's "complexity report with recommended decomposition + ready-to-run expand commands" idea; TaskMaster could borrow renmark's complexity->model routing. (TaskMaster's `models` cmd does support main/research/fallback + codex-cli, so it has model config, just not per-task auto-routing.)

### State / resumability
- **TaskMaster:** state IS `tasks.json` (statuses persisted in-file, tagged per branch). Resumability = read the file and pick `next`. Simple, durable, but no explicit pipeline/wave/retry state.
- **renmark:** dual state — `lifecycle.json` (workflow stage, artifact pointers, approval gates, <=1KB) + `pipeline.json` (runtime: wave indices, retry counts, pids). `/renmark:resume` is a zero-LLM cold-start recovery from lifecycle.json. Explicit resumability doctrine across interruption/clear/crash.
- **Alignment:** both persist canonical state to disk, not conversation.
- **Difference:** renmark's state model is far more elaborate (stage machine + runtime separation + resume command + retry/confidence/validation metadata on artifacts). TaskMaster's is simpler/flatter but arguably more transparent (one human-editable JSON). renmark could learn TaskMaster's single-source task-state simplicity; TaskMaster could learn renmark's lifecycle/resume rigor.

### Human approval gates
- **TaskMaster:** none documented as formal gates. The human drives by choosing tasks, setting status, approving expansions ad hoc; no explicit "approval required before merge/release" bit.
- **renmark:** explicit `human_review_required/completed/for` fields in lifecycle.json; `/renmark:approve` is the only way to flip the bit; release/restore/merge are gated. "AI may generate code; the human owns merges and releases."
- **Alignment:** both keep a human in the loop.
- **Difference:** renmark formalizes approval as machine-checked gates tied to destructive ops; TaskMaster relies on the human's manual workflow. renmark is clearly more rigorous here.

### Context-hygiene philosophy
- **TaskMaster:** addresses context via MCP tool-mode tiers (core/standard/all = 7/15/36 tools, ~21k tokens at full) to limit tool-schema bloat, and per-branch tag isolation. No doctrine about not reading generated code; the agent freely reads task details.
- **renmark:** hard doctrine — orchestrator never reads generated code/diffs/large logs into conversation; <=5 lines / <=300 tokens per task summary; compact at ~60%, refuse long skills at ~80%; cross-domain `/clear` recommendations; artifacts carry provenance/freshness metadata.
- **Alignment:** both acknowledge context as a constrained resource.
- **Difference:** renmark's context hygiene is a deep enforced doctrine (the orchestrator-never-reads-code rule is central); TaskMaster's is limited to tool-count tiers. This is renmark's strongest differentiator.

### Net takeaways for renmark
1. **Adopt a named, templated PRD/spec** with the standard lean sections (problem, users, goals/non-goals, requirements, success metrics, scope boundaries, open questions) and treat it as a living source-of-truth that plans reconcile against.
2. **Consider a PRD<->plan drift check** — TaskMaster lacks this; renmark's invalidation/freshness doctrine could power a genuine re-parse-diff to flag when the spec and plan diverge (a feature TaskMaster does NOT have — opportunity to leapfrog).
3. **Borrow TaskMaster's status taxonomy** (review/deferred/cancelled) and per-task priority if useful; and its dependency-integrity tooling (`validate`/`fix-dependencies`).
4. renmark already exceeds TaskMaster on: parallel execution, per-task model routing, lifecycle+resume state, formal approval gates, and context hygiene — keep those as differentiators.

(Confidence: medium — TaskMaster details derived from current public README/docs via WebFetch summarization; exact JSON examples and some sync behavior were paraphrased, not read byte-for-byte. Flagged uncertainties: no-sync claim and complexity-not-used-for-routing claim are based on absence of evidence in docs.)

## Summary

- TaskMaster: PRD is one .txt (.taskmaster/docs/prd.txt) -> parse-prd LLM-generates tasks.json (tagged per-branch; fields id/title/desc/status/deps/priority/details/testStrategy/subtasks). No PRD<->task sync.
- Complexity (1-10) drives SUBTASK COUNT + expansion prompts, NOT model routing; one main model + research/fallback. Deps are serial (next picker) with validate/fix-dependencies hygiene.
- renmark already leads on: parallel waves, per-task model routing, lifecycle+pipeline resume, formal approval gates, orchestrator-never-reads-code context hygiene.
- Biggest gap: renmark has no named/templated PRD with lean sections (problem/users/goals/non-goals/metrics/scope/open-questions) as a living source-of-truth.
- Opportunity: a PRD<->plan drift/invalidation check would leapfrog TaskMaster (which has none). Could borrow TM status taxonomy + dependency-integrity tooling.

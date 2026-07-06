<!-- Managed by /renmark:init. Wholly regenerated on each run. Do not hand-edit. -->
<!-- Last refreshed: 2026-07-06 @ 5945c2e -->

# Project map — ai-system

**Stack:** Python >=3.10 (pyproject.toml) + Claude Code plugin
**Entry points:** `bin/renmark-browser`, `bin/renmark-execute`, `renmark/__main__.py`, `plugin/commands/*.md`
**Languages:** python=548

## Directory tree

```
ai-system/
├── bin/   executable scripts / wrappers
├── plugin/   Claude Code plugin (commands, skills, templates)
├── renmark/   Python runtime (CLI, dispatch, verifier, lifecycle)
├── tests/   test suite
└── tools/   maintainer scripts
```

## Modules

| Path | Purpose | Key symbols |
|---|---|---|
| `renmark/init.py` | Project-map generator — renmark's analog to Claude Code's native /init. | `FileInfo`, `Standard`, `Gap`, `StandardsScan`, `RepoScan`, `scan_repo` |
| `.claude/worktrees/agent-a5c36b122eaf37342/renmark/init.py` | Project-map generator — renmark's analog to Claude Code's native /init. | `FileInfo`, `Standard`, `Gap`, `StandardsScan`, `RepoScan`, `scan_repo` |
| `.claude/worktrees/agent-a71511e4df1998fc1/renmark/init.py` | Project-map generator — renmark's analog to Claude Code's native /init. | `FileInfo`, `Standard`, `Gap`, `StandardsScan`, `RepoScan`, `scan_repo` |
| `.claude/worktrees/agent-ad92b23240ad37881/renmark/init.py` | Project-map generator — renmark's analog to Claude Code's native /init. | `FileInfo`, `Standard`, `Gap`, `StandardsScan`, `RepoScan`, `scan_repo` |
| `renmark/lifecycle.py` | Lifecycle state for renmark features — enforces G12 (lifecycle persistence) and  | `skill_class`, `LifecycleBloatError`, `LifecycleState`, `read_lifecycle`, `write_lifecycle`, `clear_lifecycle` |
| `renmark/scan.py` | The v1 engine for the REQ-14 read-only scheduled QA proposer lane (``/renmark:sc | `Finding`, `finding_key`, `make_finding`, `ScanReport`, `run_scan`, `load_ledger` |
| `.claude/worktrees/agent-a5c36b122eaf37342/renmark/scan.py` | The v1 engine for the REQ-14 read-only scheduled QA proposer lane (``/renmark:sc | `Finding`, `finding_key`, `make_finding`, `ScanReport`, `run_scan`, `load_ledger` |
| `.claude/worktrees/agent-a71511e4df1998fc1/renmark/scan.py` | The v1 engine for the REQ-14 read-only scheduled QA proposer lane (``/renmark:sc | `Finding`, `finding_key`, `make_finding`, `ScanReport`, `run_scan`, `load_ledger` |
| `.claude/worktrees/agent-ad92b23240ad37881/renmark/scan.py` | The v1 engine for the REQ-14 read-only scheduled QA proposer lane (``/renmark:sc | `Finding`, `finding_key`, `make_finding`, `ScanReport`, `run_scan`, `load_ledger` |
| `.claude/worktrees/agent-a5c36b122eaf37342/renmark/lifecycle.py` | Lifecycle state for renmark features — enforces G12 (lifecycle persistence) and  | `skill_class`, `LifecycleBloatError`, `LifecycleState`, `read_lifecycle`, `write_lifecycle`, `clear_lifecycle` |
| `.claude/worktrees/agent-a71511e4df1998fc1/renmark/lifecycle.py` | Lifecycle state for renmark features — enforces G12 (lifecycle persistence) and  | `skill_class`, `LifecycleBloatError`, `LifecycleState`, `read_lifecycle`, `write_lifecycle`, `clear_lifecycle` |
| `.claude/worktrees/agent-ad92b23240ad37881/renmark/lifecycle.py` | Lifecycle state for renmark features — enforces G12 (lifecycle persistence) and  | `skill_class`, `LifecycleBloatError`, `LifecycleState`, `read_lifecycle`, `write_lifecycle`, `clear_lifecycle` |
| `.claude/worktrees/agent-a71511e4df1998fc1/tests/test_lifecycle.py` | Unit tests for renmark.lifecycle (G12 — lifecycle persistence). | `test_read_lifecycle_none_when_missing`, `test_write_then_read_lifecycle`, `test_stage_transitions_track_completed`, `test_begin_feature_writes_identity`, `test_begin_feature_resets_prior_feature_state`, `test_unknown_stage_rejected` |
| `tests/test_lifecycle.py` | Unit tests for renmark.lifecycle (G12 — lifecycle persistence). | `test_read_lifecycle_none_when_missing`, `test_write_then_read_lifecycle`, `test_stage_transitions_track_completed`, `test_begin_feature_writes_identity`, `test_begin_feature_resets_prior_feature_state`, `test_unknown_stage_rejected` |
| `renmark/analytics.py` | Analytics event ledgers + Python aggregation (REQ-15). | `analytics_dir`, `read_jsonl`, `record_event`, `record_task_run`, `record_feature_run`, `close_feature_disposition` |
| `.claude/worktrees/agent-a5c36b122eaf37342/renmark/analytics.py` | Analytics event ledgers + Python aggregation (REQ-15). | `analytics_dir`, `read_jsonl`, `record_event`, `record_task_run`, `record_feature_run`, `close_feature_disposition` |
| `renmark/cli/_engine.py` | renmark-execute CLI: orchestrates plan execution via Codex and Claude agents. | `Config`, `execute_plan`, `main` |
| `.claude/worktrees/agent-ad92b23240ad37881/renmark/cli/_engine.py` | renmark-execute CLI: orchestrates plan execution via Codex and Claude agents. | `Config`, `execute_plan`, `main` |
| `.claude/worktrees/agent-a5c36b122eaf37342/renmark/cli/_engine.py` | renmark-execute CLI: orchestrates plan execution via Codex and Claude agents. | `Config`, `execute_plan`, `main` |
| `.claude/worktrees/agent-a71511e4df1998fc1/renmark/cli/_engine.py` | renmark-execute CLI: orchestrates plan execution via Codex and Claude agents. | `Config`, `execute_plan`, `main` |
| `.claude/worktrees/agent-a71511e4df1998fc1/renmark/analytics.py` | Analytics event ledgers + Python aggregation (REQ-15). | — |

## Commands (user-facing)

| Command | Purpose |
|---|---|
| `/renmark:analytics` | "Use when the user wants a project build-health summary — typed as /renmark:analytics or \"build health\", \"feature met |
| `/renmark:approve` | "Use to clear a pending human-approval gate — typed as /renmark:approve or \"approve the release\", \"what's pending app |
| `/renmark:audit` | "Use to run a deterministic plugin/registry health audit — typed as /renmark:audit (--quick or --inventory-only). |
| `/renmark:backlog` | "Use when the user wants to review or act on tracked work items — typed as `/renmark:backlog` or phrases like \"show the |
| `/renmark:blueprint` | "Use when the user wants a visual blueprint of the project — typed as /renmark:blueprint or phrases like \"diagram this\ |
| `/renmark:brainstorm` | "Use when the user wants to flesh out a rough idea into a concrete spec — typed as /renmark:brainstorm or phrases like \ |
| `/renmark:check-plan` | "Use before executing a renmark plan to validate it — typed as /renmark:check-plan. |
| `/renmark:codereview` | "Use when the user wants a diff or PR reviewed — typed as /renmark:codereview or phrases like \"review this\", \"review  |
| `/renmark:debug` | "Use for the Debug pipeline (/renmark:debug) when something is broken — plain requests like \"fix X\", \"why is X failin |
| `/renmark:doctor` | "Use when /renmark:* commands aren't appearing, the plugin seems broken, or the user wants a sanity check on the install |
| `/renmark:eval` | "Use to run the in-session, agent-driven eval path — record golden transcripts or run the LLM-judge live inside the curr |
| `/renmark:feature` | "Use for the Feature pipeline (/renmark:feature) when adding to or changing an existing build, on an isolated branch — p |
| `/renmark:finish` | "Use for the Ship / Readiness pipeline (/renmark:finish) when implementation is done and you want to wrap up — plain req |
| `/renmark:guide` | "Use when the user types /renmark:guide or says \"I don't know which command to use\", \"help me pick a pipeline\", \"wh |
| `/renmark:help` | "Use when the user types /renmark:help or asks \"what can renmark do\", \"list renmark commands\", \"renmark overview\". |
| `/renmark:hygiene` | "Use to garbage-collect stale renmark artifacts and prune append-only memory logs — typed as /renmark:hygiene. |
| `/renmark:init` | "Use for the Project Setup pipeline (/renmark:init) to adopt renmark into a repo — plain requests like \"adopt renmark\" |
| `/renmark:inventory` | "Use to harvest a flat inventory of every renmark command and skill — typed as /renmark:inventory or \"list all commands |
| `/renmark:loop` | "Use when the user wants a bounded agentic loop toward a verifier — typed as /renmark:loop or phrases like \"loop until  |
| `/renmark:orchestrate` | "Use to execute a renmark plan — `/renmark:orchestrate` or \"execute the plan\", \"build it\", \"run the plan\". |
| `/renmark:plan` | "Use when the user has a spec and wants it decomposed into an executable task list — typed as /renmark:plan or phrases l |
| `/renmark:prd` | "Use when the user wants to author or maintain the project's Product Requirements Document — typed as /renmark:prd or ph |
| `/renmark:resume` | "Use after /clear or /compact, or at the start of a fresh session, to discover where the in-flight renmark feature stopp |
| `/renmark:roadmap` | "Use for the Maintenance / Gap pipeline (/renmark:roadmap) to see status and decide what comes next — plain requests lik |
| `/renmark:scan` | "Use to run the read-only QA proposer lane — typed as /renmark:scan (--propose to land backlog items, --emit-cron for th |
| `/renmark:setup` | "Use /renmark:setup to refresh or back-fill renmark's rule blocks in a project that already uses it — plain requests lik |
| `/renmark:start` | "Use for the New Build pipeline (/renmark:start) when starting something new from scratch — plain requests like \"build  |
| `/renmark:usage` | "Use when the user wants observed local usage status — typed as /renmark:usage or \"show usage\", \"rolling 5h\", \"week |
| `/renmark:verify` | Use after a build or `/renmark:orchestrate` to confirm it works — the post-build check that runs a shell smoke test by d |

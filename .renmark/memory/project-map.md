<!-- Managed by /renmark:init. Wholly regenerated on each run. Do not hand-edit. -->
<!-- Last refreshed: 2026-08-07 @ 3f94f37 -->

# Project map — renmark

**Stack:** Python >=3.10 (pyproject.toml) + Claude Code plugin
**Entry points:** `renmark-execute (renmark.cli:main)`, `bin/renmark-browser`, `bin/renmark-execute`, `renmark/__main__.py`, `plugin/commands/*.md`
**Languages:** python=217

## Directory tree

```
renmark/
├── bin/   executable scripts / wrappers
├── plugin/   Claude Code plugin (commands, skills, templates)
├── renmark/   Python runtime (CLI, dispatch, verifier, lifecycle)
├── tests/   test suite
└── tools/   maintainer scripts
```

## Modules

| Path | Purpose | Key symbols |
|---|---|---|
| `renmark/behavior.py` | Behavioral test harness — two honestly-labelled tiers (P8-v2). | `BehaviorConfigError`, `LiveRunnerUnavailable`, `DeterministicSpec`, `EvalSpec`, `Case`, `Result` |
| `renmark/dispatch.py` | Wave-based parallel dispatcher. | `TaskResult`, `WaveResult`, `group_tasks_by_wave`, `validate_wave`, `dispatch_wave`, `WaveScopeViolation` |
| `tests/test_lifecycle.py` | Unit tests for renmark.lifecycle (G12 — lifecycle persistence). | `test_read_lifecycle_none_when_missing`, `test_write_then_read_lifecycle`, `test_stage_transitions_track_completed`, `test_begin_feature_writes_identity`, `test_begin_feature_resets_prior_feature_state`, `test_unknown_stage_rejected` |
| `renmark/init.py` | Project-map generator — renmark's analog to Claude Code's native /init. | `FileInfo`, `RepoScan`, `scan_repo`, `render_stub`, `render_full_map`, `MarkerNotFoundError` |
| `renmark/recurrence.py` | Bounded, deterministic recurrence tracking for repeated issue signals. | `RecurrenceStateError`, `RecurrenceLockError`, `IssueObservation`, `RecurrenceDecision`, `observe_issue`, `pre_attempt` |
| `renmark/scan.py` | The v1 engine for the REQ-14 read-only scheduled QA proposer lane (``/renmark:sc | `Finding`, `finding_key_from_parts`, `finding_key`, `content_fingerprint`, `make_finding`, `ScanReport` |
| `renmark/lifecycle/stage.py` | Lifecycle state for renmark features — enforces G12 (lifecycle persistence) and  | `skill_class`, `LifecycleBloatError`, `LifecycleState`, `read_lifecycle`, `write_lifecycle`, `clear_lifecycle` |
| `renmark/analytics.py` | Analytics event ledgers + Python aggregation (REQ-15). | `analytics_dir`, `read_jsonl`, `record_event`, `record_task_run`, `record_feature_run`, `close_feature_disposition` |
| `renmark/ledger.py` | Canonical ledger for the four core Renmark artifact kinds — Work Order, Work Res | `LedgerValidationError`, `DispatchIndependenceError`, `ledger_dir`, `ledger_path`, `WorkOrder`, `work_order_for_task` |
| `renmark/release.py` | Version-file drift detection — Layer 1 guardrail. | `VersionFile`, `package_basename`, `build_package`, `compact_snapshot_dir`, `compact_previous_snapshots`, `build_version_snapshot` |
| `renmark/program_driver.py` | Staged-program DRIVER — the deterministic stage-sequencing state machine that si | `RepairPackagePointer`, `MilestoneDecision`, `StopReason`, `is_hard_stop`, `next_stage`, `evaluate_stop` |
| `renmark/subagent_gate.py` | Enforced subagent-justification gate — the deterministic-first check that runs B | `SubagentVerdict`, `PlanChallenge`, `justify_task`, `challenge_plan`, `preview_line`, `R008DispatchRejected` |
| `renmark/schemas.py` | JSON-shape validators for renmark's canonical state files and artifact payloads. | `validate_milestone_document`, `validate_lifecycle`, `validate_pipeline`, `validate_delivery_state`, `validate_subagent_output`, `validate_artifact_metadata` |
| `renmark/program.py` | Staged-program data model + persistence — the single source of truth for "where  | `ProgramStateError`, `program_json_path`, `program_md_path`, `TaskNode`, `StageNode`, `Program` |
| `renmark/hygiene.py` | Lifecycle hygiene — artifact GC + memory pruning + CLI. | `ArtifactTypeSpec`, `categorize_seven_way`, `compute_seven_way_report`, `ScanReport`, `PruneReport`, `BudgetEntry` |
| `tests/test_plan_lint.py` | --- artifact_type: renmark_task_output schema_version: 1 created_at: 2026-06-11T | `test_valid_plan_pass`, `test_valid_plan_cli_exit_0`, `test_missing_verifier_block`, `test_too_many_tasks_block`, `test_duplicate_target_same_group_block`, `test_same_target_different_groups_pass` |
| `renmark/doctor.py` | renmark.doctor — diagnose Claude Code and Codex plugin install health. | `Check`, `DoctorReport`, `check_cli_on_path`, `check_python_package`, `check_version_file`, `check_plugin_manifest` |
| `tests/test_recurrence.py` | — | `test_identity_matches_scan_and_persisted_state_excludes_raw_signal`, `test_equivalent_observations_block_across_runs_but_changed_signal_resets`, `test_remediation_acknowledgement_resolution_and_one_time_retry`, `test_fresh_observe_issue_initializes_reopen_tracking_fields`, `test_resolve_issue_appends_resolved_timestamp_and_equivalent_reobserve_marks_reopen`, `test_observe_issue_with_different_fingerprint_starts_fresh_issue_after_resolve` |
| `renmark/health.py` | Dev-standards scanning and health-gap detection for renmark. | `Standard`, `Gap`, `StandardsScan`, `evaluate_health`, `scan_standards`, `render_dev_gates_line` |
| `renmark/cli/_engine.py` | renmark-execute CLI: orchestrates plan execution via Codex and Claude agents. | `Config`, `execute_plan`, `main` |
| `renmark/loop.py` | Loop Mode state machine — the deterministic core of renmark's bounded, verified, | — |

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
| `/renmark:heartbeat` | "Use to monitor or schedule recovery when a renmark run is paused by a usage limit — typed as /renmark:heartbeat (--emit |
| `/renmark:help` | "Use when the user types /renmark:help or asks \"what can renmark do\", \"list renmark commands\", \"renmark overview\". |
| `/renmark:hygiene` | "Use to garbage-collect stale renmark artifacts and prune append-only memory logs — typed as /renmark:hygiene. |
| `/renmark:init` | "Use for the Project Setup pipeline (/renmark:init) to adopt renmark into a repo — plain requests like \"adopt renmark\" |
| `/renmark:inventory` | "Use to harvest a flat inventory of every renmark command and skill — typed as /renmark:inventory or \"list all commands |
| `/renmark:loop` | "Use when the user wants a bounded agentic loop toward a verifier — typed as /renmark:loop or phrases like \"loop until  |
| `/renmark:orchestrate` | "Use to execute a renmark plan — `/renmark:orchestrate` or \"execute the plan\", \"build it\", \"run the plan\". |
| `/renmark:plan` | "Use when the user has a spec and wants it decomposed into an executable task list — typed as /renmark:plan or phrases l |
| `/renmark:prd` | "Use when the user wants to author or maintain the project's Product Requirements Document — typed as /renmark:prd or ph |
| `/renmark:resume` | "Use after /clear or /compact, or at the start of a fresh session, to discover where the in-flight renmark feature stopp |
| `/renmark:rethink` | "Use for the Brownfield Modernization pipeline (/renmark:rethink) when reassessing or migrating an EXISTING application  |
| `/renmark:roadmap` | "Use for the Maintenance / Gap pipeline (/renmark:roadmap) to see status and decide what comes next — plain requests lik |
| `/renmark:scan` | "Use to run the read-only QA proposer lane — typed as /renmark:scan (--propose to land backlog items, --emit-cron for th |
| `/renmark:setup` | "Use /renmark:setup to refresh or back-fill renmark's rule blocks in a project that already uses it — plain requests lik |
| `/renmark:start` | "Use for the New Build pipeline (/renmark:start) when starting something new from scratch — plain requests like \"build  |
| `/renmark:usage` | "Use when the user wants observed local usage status — typed as /renmark:usage or \"show usage\", \"rolling 5h\", \"week |
| `/renmark:verify` | Use after a build or `/renmark:orchestrate` to confirm it works — the post-build check that runs a shell smoke test by d |

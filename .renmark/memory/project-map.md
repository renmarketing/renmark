<!-- Managed by /renmark:init. Wholly regenerated on each run. Do not hand-edit. -->
<!-- Last refreshed: 2026-07-02 @ e940c70 -->

# Project map — ai-system

**Stack:** Python >=3.10 (pyproject.toml) + Claude Code plugin
**Entry points:** `bin/renmark-browser`, `bin/renmark-execute`, `renmark/__main__.py`, `plugin/commands/*.md`
**Languages:** python=135

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
| `renmark/scan.py` | The v1 engine for the REQ-14 read-only scheduled QA proposer lane (``/renmark:sc | `Finding`, `finding_key`, `make_finding`, `ScanReport`, `run_scan`, `load_ledger` |
| `renmark/lifecycle.py` | Lifecycle state for renmark features — enforces G12 (lifecycle persistence) and  | `skill_class`, `LifecycleBloatError`, `LifecycleState`, `read_lifecycle`, `write_lifecycle`, `clear_lifecycle` |
| `renmark/analytics.py` | Analytics event ledgers + Python aggregation (REQ-15). | `analytics_dir`, `read_jsonl`, `record_event`, `record_task_run`, `record_feature_run`, `close_feature_disposition` |
| `tests/test_lifecycle.py` | Unit tests for renmark.lifecycle (G12 — lifecycle persistence). | `test_read_lifecycle_none_when_missing`, `test_write_then_read_lifecycle`, `test_stage_transitions_track_completed`, `test_begin_feature_writes_identity`, `test_begin_feature_resets_prior_feature_state`, `test_unknown_stage_rejected` |
| `renmark/behavior.py` | Behavioral test harness — two honestly-labelled tiers (P8-v2). | `BehaviorConfigError`, `LiveRunnerUnavailable`, `DeterministicSpec`, `EvalSpec`, `Case`, `Result` |
| `renmark/memory.py` | Persistent project memory at `.renmark/memory/`. | `memory_dir`, `template_dir`, `ensure_memory`, `log_feature`, `log_bug`, `log_decision` |
| `renmark/audit.py` | Deterministic plugin/registry audit engine — the zero-LLM core of ``/renmark:aud | `CommandEntry`, `build_inventory`, `registry_sync`, `no_raw_jsonl`, `disclaimer_present`, `shim_thinness` |
| `tests/test_plan_lint.py` | --- artifact_type: renmark_task_output schema_version: 1 created_at: 2026-06-11T | `test_valid_plan_pass`, `test_valid_plan_cli_exit_0`, `test_missing_verifier_block`, `test_too_many_tasks_block`, `test_duplicate_target_same_group_block`, `test_same_target_different_groups_pass` |
| `renmark/program.py` | Staged-program data model + persistence — the single source of truth for "where  | `ProgramStateError`, `program_json_path`, `program_md_path`, `TaskNode`, `StageNode`, `Program` |
| `renmark/release.py` | Version-file drift detection — Layer 1 guardrail. | `VersionFile`, `package_basename`, `build_package`, `build_version_snapshot`, `current_version`, `check_drift` |
| `tests/test_modularity.py` | Unit tests for renmark.modularity — the advisory code-health analyzer. | `test_module_loc_just_over_warn_is_warn`, `test_module_loc_just_over_major_is_danger`, `test_module_loc_just_under_warn_is_clean`, `test_func_loc_exactly_warn_is_warn`, `test_func_loc_just_over_warn_is_warn`, `test_func_loc_exactly_major_is_danger` |
| `renmark/loop.py` | Loop Mode state machine — the deterministic core of renmark's bounded, verified, | `LoopState`, `loop_id`, `loop_dir`, `read_loop`, `write_loop`, `parse_budget` |
| `tests/test_loop.py` | Unit tests for renmark.loop (Loop Mode state machine). | `test_write_then_read_loop_round_trip`, `test_loop_id_sanitises_slug`, `test_read_loop_missing_returns_none`, `test_read_loop_corrupt_returns_none_no_raise`, `test_read_loop_non_dict_payload_returns_none`, `test_read_loop_drops_unknown_fields` |
| `tests/test_memory.py` | Unit tests for renmark.memory. | `test_ensure_memory_creates_all_files`, `test_ensure_memory_idempotent`, `test_log_feature_appends_under_shipped`, `test_log_bug_appends_under_fixed`, `test_log_decision_numbers_adrs`, `test_append_routing` |
| `renmark/doctor.py` | renmark.doctor — diagnose Claude Code plugin install health. | `Check`, `DoctorReport`, `check_cli_on_path`, `check_python_package`, `check_version_file`, `check_plugin_manifest` |
| `tests/test_reports_analytics.py` | — | `test_build_and_write_feature_report`, `test_feature_report_uses_version_path_for_release_link`, `test_record_functions_append_parseable_jsonl`, `test_aggregate_and_health_report_cover_seeded_and_empty_projects`, `test_record_feature_run_idempotent_on_rerun`, `test_close_feature_disposition_transforms_not_appends` |
| `tests/test_parser.py` | Unit tests for renmark.parser. | `test_simple_plan_parses`, `test_mode_c_rejected`, `test_missing_required_field`, `test_target_traversal_rejected`, `test_absolute_target_rejected`, `test_no_tasks_rejected` |
| `renmark/cli/_engine.py` | renmark-execute CLI: orchestrates plan execution via Codex and Claude agents. | `Config`, `execute_plan`, `main` |
| `renmark/modularity.py` | Modularity / scalability health lens — pure stdlib ``ast``, zero-dep, never-rais | `analyze` |
| `renmark/roadmap.py` | Roadmap reporter. | — |

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

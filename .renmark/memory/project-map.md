<!-- Managed by /renmark:init. Wholly regenerated on each run. Do not hand-edit. -->
<!-- Last refreshed: 2026-06-17 @ 323793c -->

# Project map — ai-system

**Stack:** Python >=3.10 (pyproject.toml) + Claude Code plugin
**Entry points:** `bin/renmark-browser`, `bin/renmark-execute`, `renmark/__main__.py`, `plugin/commands/*.md`
**Languages:** python=98

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
| `renmark/analytics.py` | Analytics event ledgers + Python aggregation (REQ-15). | `analytics_dir`, `read_jsonl`, `record_event`, `record_task_run`, `record_feature_run`, `close_feature_disposition` |
| `renmark/lifecycle.py` | Lifecycle state for renmark features — enforces G12 (lifecycle persistence) and  | `skill_class`, `LifecycleBloatError`, `LifecycleState`, `read_lifecycle`, `write_lifecycle`, `clear_lifecycle` |
| `renmark/memory.py` | Persistent project memory at `.renmark/memory/`. | `memory_dir`, `template_dir`, `ensure_memory`, `log_feature`, `log_bug`, `log_decision` |
| `renmark/audit.py` | Deterministic plugin/registry audit engine — the zero-LLM core of ``/renmark:aud | `CommandEntry`, `build_inventory`, `registry_sync`, `no_raw_jsonl`, `disclaimer_present`, `shim_thinness` |
| `tests/test_plan_lint.py` | --- artifact_type: renmark_task_output schema_version: 1 created_at: 2026-06-11T | `test_valid_plan_pass`, `test_valid_plan_cli_exit_0`, `test_missing_verifier_block`, `test_too_many_tasks_block`, `test_duplicate_target_same_group_block`, `test_same_target_different_groups_pass` |
| `renmark/program.py` | Staged-program data model + persistence — the single source of truth for "where  | `ProgramStateError`, `program_json_path`, `program_md_path`, `TaskNode`, `StageNode`, `Program` |
| `renmark/release.py` | Version-file drift detection — Layer 1 guardrail. | `VersionFile`, `package_basename`, `build_package`, `build_version_snapshot`, `current_version`, `check_drift` |
| `tests/test_modularity.py` | Unit tests for renmark.modularity — the advisory code-health analyzer. | `test_module_loc_just_over_warn_is_warn`, `test_module_loc_just_over_major_is_danger`, `test_module_loc_just_under_warn_is_clean`, `test_func_loc_exactly_warn_is_warn`, `test_func_loc_just_over_warn_is_warn`, `test_func_loc_exactly_major_is_danger` |
| `renmark/loop.py` | Loop Mode state machine — the deterministic core of renmark's bounded, verified, | `LoopState`, `loop_id`, `loop_dir`, `read_loop`, `write_loop`, `parse_budget` |
| `tests/test_loop.py` | Unit tests for renmark.loop (Loop Mode state machine). | `test_write_then_read_loop_round_trip`, `test_loop_id_sanitises_slug`, `test_read_loop_missing_returns_none`, `test_read_loop_corrupt_returns_none_no_raise`, `test_read_loop_non_dict_payload_returns_none`, `test_read_loop_drops_unknown_fields` |
| `tests/test_memory.py` | Unit tests for renmark.memory. | `test_ensure_memory_creates_all_files`, `test_ensure_memory_idempotent`, `test_log_feature_appends_under_shipped`, `test_log_bug_appends_under_fixed`, `test_log_decision_numbers_adrs`, `test_append_routing` |
| `tests/test_lifecycle.py` | Unit tests for renmark.lifecycle (G12 — lifecycle persistence). | `test_read_lifecycle_none_when_missing`, `test_write_then_read_lifecycle`, `test_stage_transitions_track_completed`, `test_begin_feature_writes_identity`, `test_begin_feature_resets_prior_feature_state`, `test_unknown_stage_rejected` |
| `tests/test_reports_analytics.py` | — | `test_build_and_write_feature_report`, `test_feature_report_uses_version_path_for_release_link`, `test_record_functions_append_parseable_jsonl`, `test_aggregate_and_health_report_cover_seeded_and_empty_projects`, `test_record_feature_run_idempotent_on_rerun`, `test_close_feature_disposition_transforms_not_appends` |
| `tests/test_parser.py` | Unit tests for renmark.parser. | `test_simple_plan_parses`, `test_mode_c_rejected`, `test_missing_required_field`, `test_target_traversal_rejected`, `test_absolute_target_rejected`, `test_no_tasks_rejected` |
| `renmark/roadmap.py` | Roadmap reporter. | `RoadmapRow`, `build_rows`, `render_table`, `write_roadmap_md`, `render_program_table`, `reconcile_setup` |
| `renmark/cli/_engine.py` | renmark-execute CLI: orchestrates plan execution via Codex and Claude agents. | `Config`, `execute_plan`, `main` |
| `renmark/plan_lint.py` | Deterministic plan-validation engine shared by /renmark:check-plan and /renmark: | `PlanLintReport`, `lint_plan`, `main` |
| `renmark/modularity.py` | Modularity / scalability health lens — pure stdlib ``ast``, zero-dep, never-rais | `analyze` |
| `tests/test_scan.py` | --- | — |

## Commands (user-facing)

| Command | Purpose |
|---|---|
| `/renmark:analytics` | Use when you need a bounded project build-health summary — typed as /renmark:analytics. |
| `/renmark:approve` | "Use to clear a pending human-approval gate — `/renmark:approve` is the ONLY surface that flips `human_review_completed` |
| `/renmark:audit` | "Use to run a deterministic plugin/registry health audit — composes the lint, modularity, and version-drift checkers and |
| `/renmark:backlog` | Use to triage and approve backlog items — `/renmark:backlog` opens an interactive list, then a per-item detail view; 'Ap |
| `/renmark:blueprint` | "Use when the user wants a visual blueprint of the project — typed as /renmark:blueprint or phrases like \"diagram this  |
| `/renmark:brainstorm` | Use when the user wants to flesh out an idea into a concrete spec — typed as /renmark:brainstorm or phrases like "let's  |
| `/renmark:check-plan` | "Use before executing a renmark plan — deterministic validation via renmark.plan_lint engine (shared with orchestrate pr |
| `/renmark:codereview` | "Use when the user wants a diff or PR reviewed — typed as /renmark:codereview or phrases like \"review this\", \"review  |
| `/renmark:debug` | Use when the user reports a bug or unexpected behavior — typed as /renmark:debug or phrases like "debug this", "why is X |
| `/renmark:doctor` | Use when `/renmark:*` commands aren't appearing, the plugin seems broken, or the user just wants a sanity check on the i |
| `/renmark:feature` | "Use to start a new feature or significant change with branch isolation — typed as /renmark:feature or phrases like \"ne |
| `/renmark:finish` | Use when implementation is complete — re-runs verifiers, shows commit summary, then offers PR / merge / release / nothin |
| `/renmark:help` | "Use when the user types /renmark:help or asks \"what can renmark do\", \"list renmark commands\", \"renmark overview\". |
| `/renmark:hygiene` | Use to garbage-collect stale renmark artifacts and prune append-only memory logs. |
| `/renmark:init` | "Use when the user wants renmark to onboard or document a project — the non-destructive front door. |
| `/renmark:inventory` | "Use to harvest a flat inventory of every renmark command and skill — name, domain, class, line counts, descriptions. |
| `/renmark:loop` | Use to run a bounded agentic loop — `/renmark:loop` or "loop on this until it passes", "keep iterating until the verifie |
| `/renmark:orchestrate` | Use to execute a renmark plan — `/renmark:orchestrate` or "execute the plan", "build it", "run the plan". |
| `/renmark:plan` | Use when the user has a spec and wants it decomposed into an executable task list — typed as /renmark:plan or phrases li |
| `/renmark:prd` | Use to create or update the project's PRD (Product Requirements Document) — the per-project source of truth that plans a |
| `/renmark:resume` | Use after `/clear` or `/compact`, or at the start of a fresh session, to discover where the in-flight renmark feature st |
| `/renmark:roadmap` | "Use when the user wants a status report on what renmark has built in this project — typed as /renmark:roadmap, \"show t |
| `/renmark:scan` | "Use to run a deterministic read-only QA proposer lane — runs audit + verifiers, dedupes findings, proposes backlog item |
| `/renmark:setup` | "Thin alias — /renmark:setup refreshes/back-fills renmark rule blocks in an existing project by delegating to /renmark:i |
| `/renmark:start` | "Use when a vibe coder wants to build something and doesn't know where to begin — the plain-English entry point for the  |
| `/renmark:usage` | Use when the user wants observed local usage status — typed as /renmark:usage, "show usage", "rolling 5h", "weekly limit |
| `/renmark:verify` | Use after `/renmark:orchestrate` completes — three modes selected by flag. |

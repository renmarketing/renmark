<!-- Managed by /renmark:init. Wholly regenerated on each run. Do not hand-edit. -->
<!-- Last refreshed: 2026-06-08 @ e9aacea -->

# Project map — ai-system

**Stack:** Python >=3.10 (pyproject.toml) + Claude Code plugin
**Entry points:** `bin/renmark-execute`, `renmark/__main__.py`, `plugin/commands/*.md`
**Languages:** python=73

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
| `renmark/init.py` | Scans the repo for file structure, modules, and public symbols, then writes: | `FileInfo`, `Standard`, `Gap`, `StandardsScan`, `RepoScan`, `scan_repo` |
| `renmark/memory.py` | Files act as living documentation — features shipped, bugs fixed, decisions | `memory_dir`, `template_dir`, `ensure_memory`, `read_index`, `read_file`, `log_feature` |
| `renmark/lifecycle.py` | and the seven-stage workflow: Brainstorm → Plan → Create → Test → Review → | `skill_class`, `LifecycleBloatError`, `LifecycleState`, `read_lifecycle`, `write_lifecycle`, `clear_lifecycle` |
| `tests/test_memory.py` | Unit tests for renmark.memory. | `test_ensure_memory_creates_all_files`, `test_ensure_memory_idempotent`, `test_log_feature_appends_under_shipped`, `test_log_bug_appends_under_fixed`, `test_log_decision_numbers_adrs`, `test_append_routing` |
| `renmark/doctor.py` | Checks that renmark is properly registered with Claude Code and surfaces | `Check`, `DoctorReport`, `check_cli_on_path`, `check_python_package`, `check_version_file`, `check_plugin_manifest` |
| `tests/test_lifecycle.py` | Unit tests for renmark.lifecycle (G12 — lifecycle persistence). | `test_read_lifecycle_none_when_missing`, `test_write_then_read_lifecycle`, `test_stage_transitions_track_completed`, `test_begin_feature_writes_identity`, `test_begin_feature_resets_prior_feature_state`, `test_unknown_stage_rejected` |
| `tests/test_parser.py` | Unit tests for renmark.parser. | `test_simple_plan_parses`, `test_mode_c_rejected`, `test_missing_required_field`, `test_target_traversal_rejected`, `test_absolute_target_rejected`, `test_no_tasks_rejected` |
| `renmark/dispatch.py` | Groups tasks by parallel_group, validates that tasks sharing a group write | `TaskResult`, `WaveResult`, `group_tasks_by_wave`, `validate_wave`, `dispatch_wave`, `estimate_wave_cost` |
| `renmark/shadow.py` | subsystems. | `register`, `registered_subsystems`, `ShadowDiff`, `list_cases`, `run_subsystem`, `run_all` |
| `renmark/release.py` | Pulled forward from the v0.4.0 release skill: the full `/renmark:release` | `VersionFile`, `package_basename`, `build_package`, `current_version`, `check_drift`, `drift_report` |
| `renmark/summary.py` | governance metadata), G9 (failure transparency). | `SummaryBoundaryError`, `ArtifactMetadata`, `write_artifact`, `emit_pointer`, `read_metadata`, `is_stale` |
| `tests/test_next_steps.py` | These cover the next-steps.md contract: the structured "what next?" set every | `test_skill_class_pipeline`, `test_skill_class_gate`, `test_skill_class_aux`, `test_skill_class_unknown_defaults_aux`, `test_pipeline_skill_at_brainstorm_complete`, `test_pipeline_skill_at_plan_validated` |
| `renmark/lint.py` | CLAUDE.md.template rule blocks are well-formed. | `parse_frontmatter`, `lint_skill_files`, `lint_next_steps_citation`, `lint_command_shims`, `lint_template_rule_blocks`, `lint_plugin_json` |
| `tests/test_blueprint.py` | Unit tests for renmark.blueprint — marker builders, splice, detect_ui. | `test_marker_constants`, `test_build_start_marker_contains_sha`, `test_build_end_marker`, `test_build_markers_use_supplied_id`, `test_splice_replaces_only_inner_region`, `test_splice_sha_recorded_in_output` |
| `tests/test_dispatch_isolation.py` | Unit tests for G11 task-isolation contract in dispatch.py. | `make_task`, `test_subagent_input_serializes_to_json`, `test_build_subagent_input_bounds_inputs`, `test_subagent_output_valid`, `test_subagent_output_rejects_too_many_summary_lines`, `test_subagent_output_rejects_oversized_summary_line` |
| `tests/test_lint.py` | Tests for renmark.lint — plugin contract linter. | `test_parse_frontmatter_extracts_simple_kv`, `test_parse_frontmatter_strips_quotes`, `test_parse_frontmatter_returns_none_without_block`, `test_parse_frontmatter_ignores_comments_and_blanks`, `test_lint_skill_files_passes_valid`, `test_lint_skill_files_catches_missing_skill_md` |
| `tests/test_hygiene.py` | Write a .renmark artifact with frontmatter so hygiene can read it. | `test_scan_empty_repo`, `test_scan_fresh_artifact_kept`, `test_scan_expired_stale_after_archived`, `test_scan_ttl_fallback`, `test_scan_referenced_never_archived`, `test_scan_dry_run_no_writes` |
| `renmark/hygiene.py` | Single source of truth for renmark's diagnostic hygiene operations. Walks the | `ScanReport`, `PruneReport`, `scan_artifacts`, `prune_memory`, `main` |
| `renmark/schemas.py` | payloads. Zero external dependencies — validation is structural, not full | `validate_lifecycle`, `validate_pipeline`, `validate_subagent_output`, `validate_artifact_metadata`, `main` |
| `renmark/cli/_engine.py` | renmark-execute CLI: orchestrates plan execution via Codex and Claude agents. | `Config`, `execute_plan`, `main` |
| `tests/test_release_drift.py` | Tests for renmark.release — version-file drift detection. | — |

## Commands (user-facing)

| Command | Purpose |
|---|---|
| `/renmark:blueprint` | Use to create or update the project's blueprint — the technical architecture and implementation guide that plans and fea |
| `/renmark:brainstorm` | Use when the user wants to flesh out an idea into a concrete spec — typed as /renmark:brainstorm or phrases like "let's  |
| `/renmark:check-plan` | Use before executing a renmark plan — validates task count, verifier presence, and parallel group safety. |
| `/renmark:codereview` | Use when the user wants a diff or PR reviewed — typed as /renmark:codereview or phrases like "review this", "review my c |
| `/renmark:debug` | Use when the user reports a bug or unexpected behavior — typed as /renmark:debug or phrases like "debug this", "why is X |
| `/renmark:doctor` | Use when `/renmark:*` commands aren't appearing, the plugin seems broken, or the user just wants a sanity check on the i |
| `/renmark:feature` | Use to start a new feature or significant change with branch isolation — typed as /renmark:feature or phrases like "new  |
| `/renmark:finish` | Use when implementation is complete — re-runs verifiers, shows commit summary, then offers PR / merge / release / nothin |
| `/renmark:help` | Use when the user types /renmark:help or asks "what can renmark do", "list renmark commands", "renmark overview". |
| `/renmark:hygiene` | Use to garbage-collect stale renmark artifacts and prune append-only memory logs. |
| `/renmark:init` | Use when the user wants renmark to document the project itself — scans the repo for file structure, modules, and public  |
| `/renmark:orchestrate` | Use to execute a renmark plan — `/renmark:orchestrate` or "execute the plan", "build it", "run the plan". |
| `/renmark:plan` | Use when the user has a spec and wants it decomposed into an executable task list — typed as /renmark:plan or phrases li |
| `/renmark:prd` | Use to create or update the project's PRD (Product Requirements Document) — the per-project source of truth that plans a |
| `/renmark:resume` | Use after `/clear` or `/compact`, or at the start of a fresh session, to discover where the in-flight renmark feature st |
| `/renmark:roadmap` | Use when the user wants a status report on what renmark has built in this project — typed as /renmark:roadmap, "show the |
| `/renmark:setup` | Use when adding renmark to an existing project — creates missing CLAUDE.md, AGENTS.md, CHANGELOG.md, and .renmark/ struc |
| `/renmark:start` | Use when a vibe coder wants to build something and doesn't know where to begin — the plain-English entry point for the f |
| `/renmark:verify` | Use after `/renmark:orchestrate` completes — three modes selected by flag. |

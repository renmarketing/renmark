<!-- Managed by /renmark:init. Wholly regenerated on each run. Do not hand-edit. -->
<!-- Last refreshed: 2026-05-28 @ 95f0d9d -->

# Project map — ai-system

**Stack:** Python >=3.10 (pyproject.toml) + Claude Code plugin
**Entry points:** `bin/renmark-execute`, `renmark/__main__.py`, `plugin/commands/*.md`
**Languages:** python=66

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
| `renmark/doctor.py` | Checks that renmark is properly registered with Claude Code and surfaces | `Check`, `DoctorReport`, `check_cli_on_path`, `check_python_package`, `check_version_file`, `check_plugin_manifest` |
| `tests/test_parser.py` | Unit tests for renmark.parser. | `test_simple_plan_parses`, `test_mode_c_rejected`, `test_missing_required_field`, `test_target_traversal_rejected`, `test_absolute_target_rejected`, `test_no_tasks_rejected` |
| `renmark/dispatch.py` | Groups tasks by parallel_group, validates that tasks sharing a group write | `TaskResult`, `WaveResult`, `group_tasks_by_wave`, `validate_wave`, `dispatch_wave`, `estimate_wave_cost` |
| `renmark/shadow.py` | subsystems. | `register`, `registered_subsystems`, `ShadowDiff`, `list_cases`, `run_subsystem`, `run_all` |
| `renmark/release.py` | Pulled forward from the v0.4.0 release skill: the full `/renmark:release` | `VersionFile`, `package_basename`, `build_package`, `current_version`, `check_drift`, `drift_report` |
| `renmark/lifecycle.py` | and the seven-stage workflow: Brainstorm → Plan → Create → Test → Review → | `LifecycleBloatError`, `LifecycleState`, `read_lifecycle`, `write_lifecycle`, `clear_lifecycle`, `next_recommended` |
| `renmark/summary.py` | governance metadata), G9 (failure transparency). | `SummaryBoundaryError`, `ArtifactMetadata`, `write_artifact`, `emit_pointer`, `read_metadata`, `is_stale` |
| `renmark/memory.py` | Files act as living documentation — features shipped, bugs fixed, decisions | `memory_dir`, `template_dir`, `ensure_memory`, `read_index`, `read_file`, `log_feature` |
| `tests/test_dispatch_isolation.py` | Unit tests for G11 task-isolation contract in dispatch.py. | `make_task`, `test_subagent_input_serializes_to_json`, `test_build_subagent_input_bounds_inputs`, `test_subagent_output_valid`, `test_subagent_output_rejects_too_many_summary_lines`, `test_subagent_output_rejects_oversized_summary_line` |
| `tests/test_lint.py` | Tests for renmark.lint — plugin contract linter. | `test_parse_frontmatter_extracts_simple_kv`, `test_parse_frontmatter_strips_quotes`, `test_parse_frontmatter_returns_none_without_block`, `test_parse_frontmatter_ignores_comments_and_blanks`, `test_lint_skill_files_passes_valid`, `test_lint_skill_files_catches_missing_skill_md` |
| `tests/test_release_drift.py` | Tests for renmark.release — version-file drift detection. | `test_extract_plain`, `test_extract_pyproject`, `test_extract_init`, `test_extract_plugin_json`, `test_extract_marketplace_metadata`, `test_extract_marketplace_nested` |
| `tests/test_schemas.py` | SubagentOutput, ArtifactMetadata.""" | `test_validate_lifecycle_accepts_valid`, `test_validate_lifecycle_rejects_non_object`, `test_validate_lifecycle_rejects_missing_field`, `test_validate_lifecycle_rejects_unknown_stage`, `test_validate_lifecycle_rejects_bad_type`, `test_validate_lifecycle_flags_runtime_cruft` |
| `renmark/lint.py` | CLAUDE.md.template rule blocks are well-formed. | `parse_frontmatter`, `lint_skill_files`, `lint_command_shims`, `lint_template_rule_blocks`, `lint_plugin_json`, `lint_all` |
| `tests/test_shadow.py` | isolated tmpdir to avoid touching real tests/shadow/ baselines.""" | `shadow_root`, `test_register_adds_subsystem`, `test_run_match_when_baseline_agrees`, `test_run_drift_when_baseline_differs`, `test_run_missing_baseline_flagged`, `test_run_handles_corrupt_case` |
| `renmark/schemas.py` | payloads. Zero external dependencies — validation is structural, not full | `validate_lifecycle`, `validate_pipeline`, `validate_subagent_output`, `validate_artifact_metadata`, `main` |
| `renmark/cli/commands.py` | Self-contained CLI reporting + ad-hoc Codex task mode. These do not touch the | `cmd_usage`, `cmd_roadmap`, `cmd_logs`, `cmd_task` |
| `renmark/roadmap.py` | Synthesizes a status report from three sources: | `RoadmapRow`, `build_rows`, `render_table`, `write_roadmap_md` |
| `renmark/cli/_engine.py` | renmark-execute CLI: orchestrates plan execution via Codex and Claude agents. | `Config`, `execute_plan`, `main` |
| `renmark/parser.py` | Parses markdown plan files of the form: | `PlanError`, `Task`, `parse_plan` |
| `tests/test_summary.py` | Unit tests for renmark.summary (G3, G6, G9 enforcement). | — |

## Commands (user-facing)

| Command | Purpose |
|---|---|
| `/renmark:brainstorm` | Use when the user wants to flesh out an idea into a concrete spec — typed as /renmark:brainstorm or phrases like "let's  |
| `/renmark:check-plan` | Use before executing a renmark plan — validates task count, verifier presence, and parallel group safety. |
| `/renmark:codereview` | Use when the user wants a diff or PR reviewed — typed as /renmark:codereview or phrases like "review this", "review my c |
| `/renmark:debug` | Use when the user reports a bug or unexpected behavior — typed as /renmark:debug or phrases like "debug this", "why is X |
| `/renmark:doctor` | Use when `/renmark:*` commands aren't appearing, the plugin seems broken, or the user just wants a sanity check on the i |
| `/renmark:feature` | Use to start a new feature or significant change with branch isolation — typed as /renmark:feature or phrases like "new  |
| `/renmark:finish` | Use when implementation is complete — re-runs verifiers, shows commit summary, then offers PR / merge / release / nothin |
| `/renmark:help` | Use when the user types /renmark:help or asks "what can renmark do", "list renmark commands", "renmark overview". |
| `/renmark:init` | Use when the user wants renmark to document the project itself — scans the repo for file structure, modules, and public  |
| `/renmark:orchestrate` | Use to execute a renmark plan — `/renmark:orchestrate` or "execute the plan", "build it", "run the plan". |
| `/renmark:plan` | Use when the user has a spec and wants it decomposed into an executable task list — typed as /renmark:plan or phrases li |
| `/renmark:resume` | Use after `/clear` or `/compact`, or at the start of a fresh session, to discover where the in-flight renmark feature st |
| `/renmark:roadmap` | Use when the user wants a status report on what renmark has built in this project — typed as /renmark:roadmap, "show the |
| `/renmark:setup` | Use when adding renmark to an existing project — creates missing CLAUDE.md, AGENTS.md, CHANGELOG.md, and .renmark/ struc |
| `/renmark:start` | Use when a vibe coder wants to build something and doesn't know where to begin — the plain-English entry point for the f |
| `/renmark:verify` | Use after `/renmark:orchestrate` completes — three modes selected by flag. |

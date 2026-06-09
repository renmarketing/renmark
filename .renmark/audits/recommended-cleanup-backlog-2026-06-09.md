---
artifact_type: audit
schema_version: 1
created_at: 2026-06-09T17:17:52-04:00
source_sha: 9a050a8
related_plan: .renmark/audits/skill-feature-inventory-spec.md
generator: claude-fable-5 (orchestrator + 8 parallel read-only subagents)
dependency_refs:
  - .renmark/audits/skill-feature-inventory-2026-06-09.md
  - .renmark/audits/ownership-source-of-truth-map-2026-06-09.md
  - .renmark/audits/overlap-findings-2026-06-09.md
  - .renmark/audits/modularity-scorecard-2026-06-09.md
  - .renmark/audits/context-hygiene-and-safety-risks-2026-06-09.md
completion_state: complete
confidence: high
validation_status: unvalidated
---

# Recommended cleanup backlog · 2026-06-09 — PROPOSED, NOT IMPLEMENTED

Per the audit spec this pass changes nothing. Items are sized for small reviewable
tasks; P0 = correctness/safety, P1 = docs→code drift, P2 = structure/quality.
Suggested vehicle: `/renmark:feature skill-surface-cleanup-from-audit` for P0+P1;
P2 items can go through `/renmark:backlog` individually.

## P0 — correctness & safety (do first)

| # | item | tag | scope |
|---|---|---|---|
| 1 | Harden `lifecycle.read_lifecycle` (isinstance-dict guard + safe stage coercion), `validate_artifact_refs` (artifacts-shape guard), `state.skills.last_skill_invocation` (non-dict → None). These are resume-killers: corrupt state currently crashes the recovery surface and `skill_preamble` Step 0 of every skill | Needs-owner | renmark/lifecycle.py, renmark/state/skills.py + tests |
| 2 | Resolve `/renmark:approve`: build the skill (CLAUDE.md already specs it as "the only way to flip the bit") OR rewire backlog/resume/loop + CLAUDE.md to an existing gate. Today the cited approval surface does not exist | Needs-owner | new skill or 3 SKILL.md edits + CLAUDE.md |
| 3 | Idempotency keys: `analytics.record_feature_run` (dedup on slug+run_id; finish re-run currently double-counts), `state.usage.append_usage`/`log_agent_call` (dedup on run_id+task_id+attempt; phantom spend hits loop budget gate), `memory.append_routing` (dedupe or un-curate so hygiene can) | Needs-owner | renmark/analytics.py, renmark/state/usage.py, renmark/memory.py + tests |
| 4 | Registry sync in `renmark/lifecycle.py`: DOMAIN_BY_SKILL (drop 8 ghosts: secure/document/map/research/release/restore/approve/issue; add loop, doctor, init, usage, analytics), IMPLEMENTED_SKILLS (+9 missing), skill-class sets (+loop/usage/analytics), AUX_LOCAL_ACTIONS `--fix`→`--apply`, docstring "seven-stage"→11 | Needs-docs-sync (in code) | renmark/lifecycle.py + tests |
| 5 | Fix G9 inversion: `dispatch.SubagentOutput` missing-field defaults should be `confidence="low"`, `validation_status="unvalidated"` (or flag-for-review), not medium/complete | Needs-owner | renmark/dispatch.py + tests |

## P1 — docs→code drift (cheap, high trust value)

| # | item | tag |
|---|---|---|
| 6 | Regenerate `help` SKILL.md: 10/23 commands listed, "v0.0.x" banner, shim says "all six", stale multi-pass codereview blurb. Worst user-facing drift | Needs-docs-sync |
| 7 | Root CLAUDE.md + AGENTS.md (mirror in same commit): fix DOMAIN_BY_SKILL table (ghosts + missing), add 11 missing skills to tooling table (feature, resume, loop, doctor, hygiene, init, setup, help, roadmap, usage, analytics), fix "multi-pass" codereview row, fix lifecycle-stage claims, add `.renmark/debug/` + `.renmark/audits/` to canonical artifact homes | Needs-docs-sync |
| 8 | Stale shim descriptions: blueprint, codereview, init, setup, help; loop shim `--verifier`→`--verify` | Needs-docs-sync |
| 9 | README table (omits 9 skills) + marketplace.json description (omits 8) | Needs-docs-sync |
| 10 | `_shared/prd-alignment.md`: move roadmap from NOTHING to ALIGN (ADR-009) | Needs-docs-sync |
| 11 | analytics SKILL.md: document the summary.json write; drop pipeline.json/features.md from claimed sources (Python reads neither) | Needs-docs-sync |
| 12 | brainstorm Reference section: `~/.claude/plugins/renmark/templates/` → `${CLAUDE_PLUGIN_ROOT}` | Needs-docs-sync |

## P2 — structure & quality (schedule, don't rush)

| # | item | tag |
|---|---|---|
| 13 | Validator wiring: wire `validate_lifecycle`/`validate_pipeline` into their read/write paths, `validate_subagent_output` into orchestrate ingest, `validate_analytics_summary`/`validate_report_metrics` into their writers; DELETE `validate_limits`, `validate_usage_pause` (dead) or wire them. 0/8 currently called in production | Needs-owner |
| 14 | Event-kind registry: `EVENT_KINDS` frozenset in analytics.py (registering `loop_iteration`), `record_event` warns/buckets unknown kinds, mirror `validate_event` in schemas.py; emit-or-delete the 9 orphaned consumed kinds (pause/resume/rate_limit/quota/release/release_created/backlog_*) | Needs-owner |
| 15 | Lifecycle orphan stages: wire writers (feature writes `reviewed` after codereview; finish writes `released` on merge/release — un-deadening its own merged/shipped branches) or cut `reviewed`/`documented`/`released`/`restored` from STAGES | Needs-owner |
| 16 | Dead-code sweep: delete or quarantine providers/{nim,openai_compat,openrouter,ollama}.py + resolve_provider (test-only since v0.2.0), memory.read_index/read_file, reports.write_run_report, prompts.retry_prompt/format_reminder_prompt, lifecycle.clear_lifecycle (or actually call it from finish per its docstring) | Deprecate |
| 17 | doctor: add tests (currently ZERO), add DOMAIN_BY_SKILL entry, document its no-preamble rationale in SKILL.md | Needs-tests |
| 18 | roadmap: add Step 0 `skill_preamble` call (only registered skill that skips it) | Needs-owner |
| 19 | De-inline `_shared` violations: start's scope tables → cite scope-contract.md; orchestrate Step 8 → drop pasted verify menu; brainstorm → drop inline 3-option menu | Merge (into _shared pointers) |
| 20 | check-plan: push the 8 structural checks into a deterministic `renmark/plan_lint.py` (testable), keep SKILL.md as the thin caller; demote from user-facing tooling table | Split / make-internal |
| 21 | verify `--bootstrap`: extract QA-flow seeding into its own sub-file or skill (second job riding a flag on a 529-line SKILL) | Split |
| 22 | Backlog merge mechanics: route §3b through finish (single merge owner per doctrine) once #2 settles the approve gate | Merge |
| 23 | Lint additions: refresh `test_plugin_install.py` pinned 15-skill list → dynamic 23; add cross-skill no-raw-JSONL + disclaimer lint passes | Needs-tests |
| 24 | Cost-view cross-pointers: one "see also" line in usage/analytics/roadmap SKILL.md each | Needs-docs-sync |

## Keep as-is (explicitly no action)

All 23 skills keep their own command (no folds, renames, or deprecations warranted);
setup stays a thin alias; doctor's out-of-project writes stay sanctioned; loop/backlog
bounded-reuse of the loop state machine stays; the 7-location version-parity check is
accurate and healthy at 0.7.8.

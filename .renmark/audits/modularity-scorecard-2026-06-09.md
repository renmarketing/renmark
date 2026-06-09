---
artifact_type: audit
schema_version: 1
created_at: 2026-06-09T17:17:52-04:00
source_sha: 9a050a8
related_plan: .renmark/audits/skill-feature-inventory-spec.md
generator: claude-fable-5 (orchestrator + 8 parallel read-only subagents)
dependency_refs:
  - .renmark/audits/skill-feature-inventory-2026-06-09.md
completion_state: complete
confidence: high
validation_status: unvalidated
---

# Modularity scorecard · 2026-06-09

## Layering verdicts

| layer | contract | verdict |
|---|---|---|
| `plugin/commands/*.md` | thin shims only | **A−** · 23/23 are thin pointers (verify carries minor mode-parse). But **5 shim descriptions are stale**: blueprint, codereview, init, setup, help (+ loop's `--verifier`/`--verify` flag drift) |
| `plugin/skills/*/SKILL.md` | workflow instructions, not business logic | **B+** · no SKILL.md re-implements Python logic; heavy work is consistently pushed to `renmark.*`. Exception: **check-plan's 8 structural checks have zero Python backing** — deterministic-looking counts/greps executed as LLM prose (push-down candidate) |
| `renmark/*.py` | deterministic engine | **B** · engine is sound; but a whole **dead provider layer** (nim/openai_compat/openrouter/ollama, test-only since v0.2.0) and ~15 dead/test-only symbols remain (list below) |
| `renmark/state/*.py` | persisted-state helpers | **A−** · clean separation; reader-hardening inconsistent (see safety artifact) |
| `renmark/schemas.py` | validation only | **F for wiring** · validation-only respected, but **0 of 8 validators have a production call site** (6 test-only, 2 fully dead) — validator theater |
| `.renmark/*` | durable project state | **A** · single-writer-per-concept holds (see ownership map) |

## `_shared/` dedup contract (the key duplication check)

`_shared/` files: `next-steps.md` (hand-off contract), `handoff-menu.md` (gate menu
+ 9 rendering rules), `scope-contract.md` (discovery questions), `prd-alignment.md`
(WRITE/ALIGN/NOTHING policy).

| skill | next-steps | handoff-menu | scope-contract | prd-alignment |
|---|---|---|---|---|
| start | pointer | pointer | **INLINED** — own stack/reach/lifespan tables, file never cited | n/a |
| brainstorm | pointer | pointer | pointer | pointer (+ mild inline 3-option menu before the pointer) |
| orchestrate | pointer | **PARTIAL-INLINE** — Step 8 pastes verify's 4-option menu verbatim | n/a | n/a |
| verify, codereview | not-referenced (gate class — by design, matches test_next_steps) | pointer | n/a | n/a |
| all 18 others | pointer | pointer | n/a or pointer | n/a or pointer |

**Violators: 2 real (start, orchestrate), 1 mild (brainstorm).** Everything else cites
by pointer. Bonus drift: `prd-alignment.md`'s own table still lists roadmap under
NOTHING although roadmap `--gaps` uses ALIGN per ADR-009 — the shared file itself is stale.

**skill_preamble consolidation (v0.3.2) holds:** 20/23 call
`lifecycle.skill_preamble` by pointer; none re-inline the domain/context-budget
logic. The 3 non-callers: help (deliberate zero-cost), doctor (defensible —
must run when the package can't import — but undocumented), **roadmap (a bug —
registered in DOMAIN_BY_SKILL yet skips Step 0)**.

## Governance rule → enforcement-point matrix (G1–G12)

| rule | short name | status | enforcement point |
|---|---|---|---|
| G1 | orchestrator coordinates, doesn't accumulate | **PROSE** | — (only indirectly served by G3/G11 mechanisms) |
| G2 | canonical state on disk | PARTIAL | `lifecycle.read/write_lifecycle`, `state.pipeline.*`, `memory.*`, `validate_artifact_refs` |
| G3 | summary boundary ≤5 lines/300 tok | **CODE** | `summary.SummaryBoundaryError`, `write_artifact` caps, `emit_pointer`, `verifier_tail`, `SubagentOutput.__post_init__` caps |
| G4 | context contamination / cross-domain /clear | PARTIAL | `state.skills.context_budget_check`, `lifecycle.skill_preamble`/`domain_of` — %-utilization side prose-only by design (`state/skills.py:45` admits it); DOMAIN_BY_SKILL dict itself is drifted |
| G5 | executor isolation | PARTIAL | `bin/renmark-execute` → `cli._engine._execute_task_codex`, `providers.codex` subprocess; heavy-read BLOCK rules prose-only in check-plan |
| G6 | artifact provenance metadata | PARTIAL | `summary.ArtifactMetadata` mandatory in `write_artifact`, `read_metadata`/`is_stale`, `hygiene.scan_artifacts`; nothing forces skills through `write_artifact` |
| G7 | /compact semantics | **PROSE** | — (no function can govern /compact; rides on G2/G12). Note: `lifecycle.py:227` comment mislabels the human-approval gate "(G7)" |
| G8 | compounding verification (learnings/bugs) | PARTIAL (thin) | only 2 hardwired sites: `cli._engine`→`append_learning`, `debug.close_session`→`log_bug`; every other append is SKILL prose |
| G9 | failure transparency fields | PARTIAL | `SubagentOutput` required fields, `validate_subagent_output` (test-only!), `ArtifactMetadata` G9 fields — **but defaults contradict prose: missing fields default to `confidence="medium"`, `completion_state="complete"` instead of the documented treat-as-low** |
| G10 | workflow recovery | PARTIAL | `pipeline_is_resumable`, never-raise readers — except `read_lifecycle` itself raises on corrupt input (see safety artifact) |
| G11 | orchestrate task isolation | **CODE** | `dispatch.dispatch_task_isolated` + `parse_subagent_response` + `IsolationViolation`; caveat: live Agent dispatch must voluntarily route through the parser |
| G12 | lifecycle persistence | **CODE** | `lifecycle.write_lifecycle` + `LifecycleBloatError` (1KB) + STAGES validation; "write before every return" remains per-skill prose |

**Prose-only liabilities: G1, G7** (+ the unenforceable half of G4, by design).
**Code-enforced anchors: G3, G11, G12.** Everything else is partial.

## Registry drift inside `renmark/lifecycle.py` (single worst module for drift)

- `DOMAIN_BY_SKILL` (26 keys): **8 ghosts** — secure, document, map, research,
  release, restore, approve, issue — and **5 missing real skills** — loop, doctor,
  init, usage, analytics (each silently defaults to domain "build" via `domain_of`,
  so cross-domain /clear hints misfire).
- `IMPLEMENTED_SKILLS` (14 entries): missing **9 real skills** (prd, blueprint,
  backlog, loop, doctor, hygiene, init, usage, analytics) — `_resolve_next` would
  call them "not yet implemented".
- Skill-class sets (PIPELINE/GATE/AUX): cover 21/23 — loop, usage, analytics fall
  through to default "aux".
- `NEXT_BY_STAGE`: clean (all 7 targets real). `NEXT_BY_STAGE_PLANNED`: ghosts
  `/renmark:document`, `/renmark:release` (labeled aspirational — acceptable).
- `AUX_LOCAL_ACTIONS`: offers `/renmark:hygiene --fix`; real flag is `--apply`.
- Module docstring: "seven-stage workflow" vs 11 entries in `STAGES`.

## Dead / test-only code (sweep results)

**DEAD (zero references anywhere):** `memory.read_index`, `memory.read_file`,
`reports.write_run_report`, `prompts.retry_prompt`, `prompts.format_reminder_prompt`,
`schemas.validate_limits`, `schemas.validate_usage_pause`.

**TEST-ONLY:** entire `providers/nim.py` (NIMClient + 4 exception classes + RateLimiter),
`providers/openai_compat.py`, `providers/openrouter.py`, `providers/ollama.py`,
`providers.resolve_provider` (executor removed v0.2.0 — `cli/_engine.py:514` admits
"only codex reaches this"); `schemas.validate_analytics_summary`,
`schemas.validate_report_metrics`; `dispatch.estimate_wave_cost`; `shadow.run_all`;
`summary.hash_artifact`; `blueprint.build_end_marker`; `bootstrap.is_empty_project`;
`lifecycle.clear_lifecycle` (docstring claims finish calls it — nothing does);
`lifecycle.is_cross_domain_transition`; `state.pipeline.list_wave_summaries`;
`state.logs.open_log`/`append_log`; `providers/claude_agent.build_agent_dispatch`.

## Version parity (release.check)

"7 locations" is **still accurate**: VERSION (canonical), pyproject.toml,
`renmark/__init__.__version__`, `plugin/.claude-plugin/plugin.json`,
`.claude-plugin/marketplace.json` ×2 (metadata + plugins[0]), README h1.
All agree at **0.7.8** right now. No in-repo version-bearing file is uncovered
(CHANGELOG correctly excluded as historical). Notes: `check` alone is advisory —
the hard gate fires at package/snapshot time; and the out-of-repo workspace map
(`~/projects/CLAUDE.md`) still says "v0.4.0, current" — invisible to `check_drift`.

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

# Ownership / single-source-of-truth map · 2026-06-09

Verdict per concept: **canonical home → sole writer → readers → violations**.
Headline: the **storage layer is clean** — every concept has exactly one canonical
file and one writer, and Part 1's "no second token ledger" rule holds. Violations
live one level up: presentation-layer double-reporting, double-owned *mechanics*
(merge), and dangling gates.

## Concept table

| concept | canonical home | writer (owner) | readers | status |
|---|---|---|---|---|
| usage tokens | `.renmark/state/usage.jsonl` | `state.usage.append_usage` / `log_agent_call` (orchestrate) | usage view, roadmap, `analytics._agg_usage`, loop budget gate | ✅ single ledger holds |
| local usage limits | `.renmark/analytics/limits.json` | user-edited | `usage.read_limits` | ✅ (but `validate_limits` is DEAD code) |
| analytics events | `.renmark/analytics/events.jsonl` | `analytics.record_event` | `analytics._agg_events` | ⚠️ only one production emitter (`loop_iteration`); 9 consumed kinds have **no emitter** (see overlap-findings §taxonomy) |
| task runs | `.renmark/analytics/task-runs.jsonl` | `record_task_run` (orchestrate) | `_agg_tasks` | ✅ |
| feature runs | `.renmark/analytics/feature-runs.jsonl` | `record_feature_run` (finish) | `_agg_features` | ⚠️ blind-append — finish re-run double-counts |
| loop runs | `.renmark/analytics/loop-runs.jsonl` | `record_loop_run` (loop) | `_agg_loops` | ✅ |
| analytics summary | `.renmark/analytics/summary.json` | `analytics.aggregate` (atomic overwrite) | analytics skill | ⚠️ write is **undocumented in SKILL.md**; faithfully double-counts dup ledger rows |
| feature reports | `.renmark/reports/features/<slug>/` | `reports.write_feature_report` (finish) | humans | ✅ overwrite-by-slug, idempotent |
| release snapshots | `.renmark/version/<version>/` + zip | `release.build_version_snapshot` / `build_package` (finish §4) | humans, gh release | ✅ overwrite, drift-gated |
| loop state | `.renmark/loops/<id>/loop.json` | `loop.write_loop` (loop; backlog drives via loop) | resume (read-only), backlog | ✅ clean writer/reader split |
| pause/resume state | `.renmark/state/` pause file (`PauseState`) | `state.write_pause` (orchestrate, loop) | resume, `usage.build_usage_view` | ✅ |
| pipeline runtime | `.renmark/state/pipeline.json` | `state.write_pipeline_state` (orchestrate) | resume (hints), verify Step 0 | ✅ idempotent writes |
| wave summaries | `.renmark/state/wave-summaries/` | `state.write_wave_summary` (orchestrate) | orchestrate next wave | ✅ keyed by wave_index |
| lifecycle/workflow | `.renmark/state/lifecycle.json` | `lifecycle.write_lifecycle` (8 skills, see below) | every skill via `skill_preamble`/`next_steps`, resume | ⚠️ 4 orphan stages; reader raises on corrupt input (see safety artifact) |
| backlog | `.renmark/state/backlog/BL-<n>.json` | `backlog.write_item` | backlog | ✅ path-traversal-guarded, safe reader |
| plans / specs | `.renmark/plans/` / `.renmark/specs/` | plan / brainstorm | check-plan, orchestrate, verify | ✅ |
| memory logs | `.renmark/memory/*.md` | `memory.log_*` / `append_*` (orchestrate, debug, verify, finish) | plan, roadmap, humans | ⚠️ `append_routing` blind-appends AND `routing.md` is curated → hygiene refuses to dedupe it: **no remediation path** |
| debug sessions | `.renmark/debug/<session-id>/` | debug skill | debug (resume across /clear) | ⚠️ valid but **missing from CLAUDE.md's canonical-homes list** |
| PRD | `PRD.md` | **prd skill only** (human-gated) | feature/brainstorm/roadmap via ALIGN subagent | ✅ single writer, gate intact |
| project map | `.renmark/memory/project-map.md` (+ stub in CLAUDE.md/AGENTS.md) | `renmark.init` | blueprint (sole arch source), humans | ✅ |
| version string | `VERSION` (canonical) + 6 mirrors | `release.py` bump path | `release.check_drift` (7 locations) | ✅ all agree at 0.7.8 |

## Lifecycle stage writers (who advances what)

| stage | written by | exit (NEXT_BY_STAGE) |
|---|---|---|
| init | feature (`begin_feature`) + dataclass default | brainstorm |
| brainstorm-complete | brainstorm | plan |
| plan-drafted | plan | check-plan |
| plan-validated | plan (auto) + check-plan | orchestrate |
| created | orchestrate | verify |
| verified | verify | codereview |
| **reviewed** | **ORPHAN** — codereview defers to feature; feature never writes it | finish |
| **documented** | **ORPHAN** — no writer (`/renmark:document` never built) | finish |
| ready-to-release | finish | manual hint (intentional) |
| **released** | **ORPHAN** — finish *reads* `stage == "released"` but never sets it → its merged/shipped branches are unreachable | terminal |
| **restored** | **ORPHAN** — `/renmark:restore` does not exist | terminal |

## Violations & double-ownership (ranked)

1. **Merge mechanics double-owned.** Doctrine (loop SKILL, REQ-12) says merge belongs to
   `/renmark:finish`; but `backlog` §3b performs merge + post-merge re-verify + branch
   delete itself. Two implementations of the same gated mechanic.
2. **The approval gate has no home.** `backlog`, `resume`, `loop`, and root CLAUDE.md all
   route to `/renmark:approve` ("the only way to flip the bit") — **no such command or
   skill exists**. The human_review_* fields in lifecycle.json have writers (prd, finish)
   but no canonical flipper.
3. **"What did this cost?" answered three ways.** usage (`top_features`, 7d) vs analytics
   (cost-by-feature, all-time) vs roadmap ($ per task) — all derive from the single
   usage.jsonl ledger (✅ storage), but no surface cross-references the others (⚠️ UX).
4. **Two scaffolding front doors.** brainstorm (empty-folder bootstrap) and init both call
   `bootstrap()` — shared code, so not a true violation, but docs should name init as the
   canonical onboarding door (REQ-8 already implies it).
5. **Out-of-project writer (sanctioned).** doctor writes `~/.claude/*` — by design, gated,
   backed up; the only permitted exception to "all renmark output stays inside the project".

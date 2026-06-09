---
artifact_type: audit
schema_version: 1
created_at: 2026-06-09T17:17:52-04:00
source_sha: 9a050a8
related_plan: .renmark/audits/skill-feature-inventory-spec.md
generator: claude-fable-5 (orchestrator + 8 parallel read-only subagents)
dependency_refs:
  - .renmark/audits/skill-feature-inventory-2026-06-09.md
  - .renmark/audits/modularity-scorecard-2026-06-09.md
completion_state: complete
confidence: high
validation_status: unvalidated
---

# Context hygiene & safety risks · 2026-06-09

## A. Context hygiene per skill (REQ-5 / REQ-6) — overall PASS

**No skill instructs reading raw JSONL into context.** usage and analytics are the
model citizens (hard no-raw-log rules, Python-side aggregation, mandatory
disclaimer, "show verbatim"). hygiene's bounded-stdout contract is exemplary.

Flags (all minor):

| skill | flag |
|---|---|
| debug | inspection findings have **no explicit ≤5-line cap** (only un-capped skill) |
| plan | `[r]` review option cats the full plan into conversation — user-requested pre-spend review, acceptable but unbounded |
| verify | deep-QA plan phase reads bounded per-file diffs into *skill* context (never chat) — borderline, documented |
| codereview | lite lane is in-context by design (~10–25k tokens, stated) — sanctioned |
| doctor | writes outside the project (`~/.claude`) — by design, gated, backed up; sole sanctioned exception |

**Enforcement gap:** "no-raw-JSONL-read" and "disclaimer-present" exist as tests
only for the usage module (`test_usage.py`); neither is a cross-skill lint pass.

## B. Resume-killers (non-raising-read contract violations) — the top code risk

Part 1 hardened `read_pause`/`read_loop`/`read_usage`; the same contract is NOT
uniform:

| reader | status | failure mode |
|---|---|---|
| `lifecycle.read_lifecycle` | **RAISES** | valid-JSON non-dict (`[]`, `"x"`, `42`) → AttributeError at `data.items()` (lifecycle.py:265-271); unhashable `stage` → TypeError. `/renmark:resume` calls it unguarded — **a corrupt lifecycle.json kills the recovery surface it exists to provide** |
| `state.skills.last_skill_invocation` | PARTIAL | non-dict JSON returned as-is (bare cast) → AttributeError inside `context_budget_check` → **corrupt last-skill.json breaks `skill_preamble` Step 0 of every skill** |
| `lifecycle.validate_artifact_refs` / `next_recommended` / `next_steps` | PARTIAL | inherit read_lifecycle's raise paths; `state.artifacts.items()` raises if artifacts deserialize as a list |
| `state.usage.usage_today` / `usage_this_month` | PARTIAL | raw `int()` / `.startswith` on row values → ValueError/TypeError/AttributeError on type-malformed rows (newer siblings `usage_by_run_id`/`usage_in_window` coerce correctly) |
| `roadmap._aggregate_usage` / `build_rows` | PARTIAL | one malformed-but-valid-JSON ledger row kills `/renmark:roadmap` |
| `state.pipeline.pipeline_is_resumable` | PARTIAL | `wave_index < wave_total` TypeError when persisted as strings — gates orchestrate/verify Step 0 |
| `state.pipeline.read_wave_summary` | PARTIAL | JSON array returned as-is; caller `.get` raises |
| `memory.read_*`, `dedupe/age_out` | PARTIAL | unguarded `read_text` → UnicodeDecodeError on corrupt bytes |
| `state.logs.recent_logs` | PARTIAL | unguarded `f.stat()` OSError if log vanishes mid-glob |
| SAFE: `read_pause`, `read_usage`, `usage_by_run_id`/`usage_in_window`/`usage_last_5h`/`_week`/`tokens_by_feature`, `read_pipeline_state`, `completed_task_indices`, `loop.read_loop` + budget helpers, `backlog.read_item`/`list_items`, `analytics.read_jsonl`/`aggregate`, `usage.read_limits`, `build_usage_view` | | |

## C. Safety / gate consistency (dimension 11)

| capability | skills | gate status |
|---|---|---|
| merge | finish `[m]`, **backlog §3b** | finish gated ✅; backlog's gate routes to **nonexistent `/renmark:approve`** ⚠️ |
| release | finish `[r]` only | gated ✅ |
| delete branches | finish (`-d` post-merge), backlog (`-d`/`-D`) | follows recorded disposition ✅, but rides the same missing-approve gap ⚠️ |
| edit PRD.md | prd only | human-gated, single writer ✅ |
| edit code | orchestrate (via agents), debug (fix step), loop/backlog (indirect) | all behind dispatch/approval gates ✅ |
| increase budget | loop (upfront), backlog (hardcoded bounds) | no skill silently raises a budget ✅ |
| dispatch agents | brainstorm, orchestrate, feature, loop, backlog, debug, roadmap --gaps | all post-gate ✅ |
| resume paused work | resume (read-only pointer), loop --resume | ✅ |
| hidden auto-execute | none found | plan's `[d]` auto-invokes orchestrate but only from an explicit menu choice ✅ |

**The one systemic gate hole:** `/renmark:approve` is cited by backlog, resume,
loop, and root CLAUDE.md ("the only way to flip the bit") but is **not implemented**.
Until it exists (or callers are rewired), approval-gated paths are either blocked
or invite improvisation. G9's "missing fields ⇒ treat as low confidence" is also
inverted in code: `dispatch.SubagentOutput` defaults missing fields to
`confidence="medium"`, `completion_state="complete"`.

## D. Idempotency / re-run safety (worst offenders)

| writer | semantics | consequence |
|---|---|---|
| `analytics.record_feature_run` | BLIND-APPEND | re-running finish counts the feature twice in summary.json/health forever (aggregate has no dedup) — silently corrupts success metrics |
| `state.usage.append_usage` / `log_agent_call` | BLIND-APPEND, no (run_id, task_id) key | crash-then-resume re-logs spend; `usage_by_run_id` feeds the loop budget gate → loops stop early on phantom spend |
| `memory.append_routing` | BLIND-APPEND **and** routing.md is curated → hygiene refuses to dedupe | duplicates skew the executor-routing signal with no remediation path |
| `memory.log_feature`, `log_bug`, `append_learning` | BLIND-APPEND | dup memory entries (hygiene dedupe is opt-in remediation for learnings/bugs/features) |
| `analytics.record_event` / `record_task_run` / `record_loop_run` | BLIND-APPEND | same class, lower blast radius |
| SAFE: `log_decision`/`log_escalation_decision` (idempotent on title+date), `write_pipeline_state` (deduped indices), `write_lifecycle` (deduped stages + bloat cap), `write_feature_report`/`write_run_report` (overwrite by key), `release.build_package`/`build_version_snapshot` (overwrite), `write_wave_summary` (keyed) | | |

## E. Test-coverage gaps

- **doctor: ZERO tests** (module never even imported by a test) — the only skill at zero.
- Universal lint gates are strong (shim-exists, skill-exists, frontmatter, shim→SKILL
  reference, next-steps citation — all 23) — but `test_plugin_install.py::test_plugin_has_required_skill_files`
  **pins only 15 skills** (stale: misses blueprint, loop, backlog, doctor, hygiene, init, usage, analytics).
- Not enforced anywhere as cross-skill gates: no-raw-JSONL-read, disclaimer-present.
- Untested behavior: codereview's review flow, check-plan's verdict logic (no Python
  to test), prd create/update modes, feature's branch pipeline, finish re-run idempotency.

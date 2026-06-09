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
completion_state: complete
confidence: high
validation_status: unvalidated
---

# Overlap hotspot findings · 2026-06-09

Each spec-listed hotspot, verdict first. Summary: **7 of 9 hotspots are clean** —
the skill surface has real separation of concerns. The two genuine overlaps are
**backlog's merge mechanics** (duplicates finish's terminal role) and the
**three-way cost-reporting presentation** (single ledger, three uncoordinated views).

## 1. usage vs analytics vs roadmap — ⚠️ presentation overlap, storage clean

Distinct grains: **usage** = "am I near limits / paused?" (rolling 5h/7d windows,
per-provider); **analytics** = per-FEATURE health (shipped/blocked, loop success
rate, all-time); **roadmap** = per-TASK status/cost table (+ `--gaps` discovery).
All three derive from the one usage.jsonl ledger — no second ledger exists.
Overlap: tokens-by-feature is reported by usage (7d) AND analytics (all-time),
and token totals appear in all three, with **no cross-pointers** between surfaces.
→ Keep all three; add a one-line "see also" cross-pointer to each SKILL.md.

## 2. finish vs release/version-snapshot — ✅ single owner (finish), with a dead branch

finish solely owns release: drift check → tag → `renmark.release snapshot` →
optional gh release. `/renmark:release` exists only in `NEXT_BY_STAGE_PLANNED`
(explicitly aspirational). Defect, not overlap: finish never *writes*
`stage=released`, yet *reads* `stage == "released"` — its merged/shipped logic
is unreachable. → Decide: write the stage on merge/release, or cut the dead branch.

## 3. resume vs loop/orchestrate pause state — ✅ clean writer/reader split

loop + orchestrate write `.renmark/loops/<id>/loop.json` and the pause file;
resume only reads and points back to `/renmark:loop --resume`. No double ownership.

## 4. loop vs backlog (approve-and-build) — ⚠️ the one real mechanics overlap

`loop.py` owns the state machine; backlog reuses the documented driving procedure
with hardcoded bounds (max 5 iterations, default budget) — that part is sanctioned
reuse, not duplication. **The violation:** backlog §3b performs merge + post-merge
re-verify + branch delete itself, while doctrine (loop SKILL, REQ-12) assigns merge
to `/renmark:finish`. Merge mechanics now live in two places. Compounding it: the
gate both cite — `/renmark:approve` — **does not exist** (also cited by resume and
root CLAUDE.md G12 prose). → Either build `/renmark:approve` or rewire all callers
to an existing gate, and route backlog's merge through finish.

## 5. verify vs codereview vs secure — ✅ distinct (and `secure` is a ghost)

verify = goal-backward *behavior* gate (did the feature do what the plan promised);
codereview = *diff quality* gate (correctness/standards, proportional depth).
`secure` exists only as a ghost in DOMAIN_BY_SKILL/CLAUDE.md — no skill, no overlap.

## 6. feature vs plan vs orchestrate — ✅ clean three-layer contract

feature = pure router (branch + pipeline sequencing, single dispatch gate);
plan = decomposition + the dispatch approval gate (absorbed check-plan in v0.3.3,
documented single-owner contract with feature); orchestrate = execution engine.
No duplicated logic found.

## 7. doctor vs hygiene — ✅ clean separation

doctor owns install health *outside* the project (`~/.claude` settings, plugin
registry, cache, version parity, Python import); hygiene owns artifact freshness
*inside* `.renmark/`. Only blemish: `lifecycle.AUX_LOCAL_ACTIONS` advertises
`/renmark:hygiene --fix` but the real flag is `--apply`.

## 8. debug vs loop/backlog repair flow — ✅ mild, acceptable coupling

debug owns root-cause investigation with one-off fixes; loop self-retries within
budget — its `build_decision` *consumes debug's symptom line format* from verify
without invoking debug (a format coupling worth documenting); backlog's blocked
exit explicitly hands off to `/renmark:debug`. No duplicated repair loop.

## 9. init vs setup — ✅ setup confirmed thin and staying thin

setup is 59 lines, zero scaffold logic, pure delegation to `init.merge_rule_blocks`
(REQ-8). Only its command-shim description is stale (still advertises the old
full-scaffold behavior).

## Discovered overlaps not in the spec list

- **start vs `_shared/scope-contract.md`:** start carries its own stack-inference /
  reach / lifespan tables in Steps 2–4 and never cites the shared file — a
  paraphrase-fork of the scope contract that will drift (worst `_shared` violation found).
- **orchestrate vs `_shared/handoff-menu.md`:** Step 8 pastes verify's 4-option menu
  verbatim before citing the pointer (mild duplication).
- **brainstorm vs init scaffolding:** both bootstrap empty projects via the shared
  `bootstrap()` — same code, two front doors; docs should crown init canonical.

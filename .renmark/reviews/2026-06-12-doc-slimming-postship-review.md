---
artifact_type: review
schema_version: 1
created_at: 2026-06-12
generator: claude+workflow
related: v0.14.1..v0.14.2 doc-slimming post-ship review
method: 5-lens find workflow (40 agents) + deterministic ground-truth verification (Fable verify phase failed mid-run; re-verified on Opus)
---

# Post-ship review — v0.14.2 doc-slimming

**Bottom line:** the optimization is real and net-positive for the cost that matters
(CLAUDE.md — the file Claude actually loads — dropped ~35% by tokens / ~58% by lines),
but the compression was too aggressive: it silently dropped ~8 governance clauses from the
always-loaded CLAUDE template (which `init.py` back-fills into every scaffolded project),
introduced one new mirror inconsistency, and the changelog/audit numbers oversold it.
Nothing breaks at runtime (746 tests green, audit PASS) — this is a fast-follow doc patch,
not an emergency.

## Ground-truth measurements (chars/4)

| file | lines old→new | tokens old→new | verdict |
|---|---|---|---|
| CLAUDE.md.template | 426→167 | 5226→3270 (-37%) | genuine shrink |
| CLAUDE.md | 450→189 | 5502→3602 (-35%) | genuine shrink (the per-session Claude win) |
| AGENTS.md.template | 113→92 | 2410→**2677 (+11%)** | GREW in tokens |
| AGENTS.md | 133→114 | 2576→**3434 (+33%)** | GREW in tokens |

AGENTS files lost *lines* (newline-joining) but gained *content* (review-fix restored
clauses). AGENTS.md is NOT loaded by Claude Code, so per-session Claude impact = the
CLAUDE.md saving only.

## CONFIRMED findings (verified against files)

**Dropped governance clauses in CLAUDE.md.template (propagate to every project via init.py back-fill):**
- M: `parallelism-rule` — the `Long-running probes → background Bash with run_in_background: true` instruction dropped entirely (was v0.14.1 line 27).
- M: `lifecycle-rule` — the cold-start recovery mandate ("after /clear, run /renmark:resume") dropped from the block (skill still exists; the always-loaded *rule* no longer states it).
- m: `commit-cadence-rule` — "compile" requirement dropped from the per-commit gate (all 4 files; only "pass lint" remains).
- m: `refactor-safety-rule` — regression-diagnosis step (`git diff HEAD~1`, identify cause) + "only" exclusivity qualifier dropped.
- m: `failure-transparency-rule` — executor-output field enums + retry_count monotonicity dropped (6 field names kept, value constraints gone → field list now ambiguous).
- m: `canonical-state-rule` — "structured summaries inside artifact files" dropped from the canonical-state list.
- m: `artifact-governance-rule` — "Track stale artifacts…" instruction + field value formats dropped.
- nit: `context-budget-rule` short-skill exemption list dropped; `executor-dispatch-rule` REQ-2 anchor + full "adversarial audit/review" wording compressed.

**Mirror / consistency (review-fix-introduced):**
- M: `never after` verification-timing clause now present in ONLY plugin/templates/AGENTS.md.template — missing from CLAUDE.md.template, CLAUDE.md, AND AGENTS.md. The v0.14.2 review-fix restored it in the single wrong file, inverting the mirror.
- m: stale `(v0.10.0)` hardcoded in both always-loaded root docs (CLAUDE.md:11, AGENTS.md:8) at a v0.14.2 release — the project-description stub lies about the version.

**Claims honesty (CHANGELOG v0.14.2 + footprint audit):**
- M: "All four onboarding docs ~halved" is FALSE for the AGENTS pair — both GREW in tokens (+11%, +33%); only line counts fell.
- m: CLAUDE.md "~7.2k→~3.5k (halved)" — post ~3.5k correct; the real reduction is ~35% (tokens) / ~58% (lines). "Halved" is true for lines, optimistic for tokens.
- nit: footprint-audit "~2,440 tok command descriptions / ~2k de-dup win" slightly high (~2,158 tok; ~half are true duplicates).
- nit: v0.14.2 CHANGELOG entry omits the mandatory "Files changed:" field; 7 changed files unlisted by path.

## REFUTED (Find-phase over-claims, corrected by verification)
- "AGENTS template canonical artifact-homes (Codex Major #4) never landed / CHANGELOG ALL-FIXED is false" — FALSE: artifact-homes ARE present in both plugin/templates/AGENTS.md.template:38 and root AGENTS.md. The fix DID land.

## Why the branch-time codex review missed these
That review's scope was AGENTS-specific dropped clauses + dangling pointers — it caught those. The CLAUDE-template clause-drops (background-Bash, cold-start resume, compile, regression-diagnosis, field enums) were outside its lens, so they shipped. The task-1 commit message claimed "blocks+clauses preserved," which the diff contradicts.

## Recommendation
Fast-follow patch (v0.14.3): restore the dropped CLAUDE-template clauses (terse but complete — brevity didn't require dropping mandates; AGENTS proves clauses fit), fix the 1-of-4 "never after" drift across all four, correct the stale (v0.10.0) stamps to read from VERSION or drop the inline version, and correct the CHANGELOG/audit numbers to the honest figures above.

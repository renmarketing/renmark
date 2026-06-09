# renmark skill-feature inventory & modularity audit — ready-to-run spec

> **How to use:** after `/clear`, paste the block under "PROMPT TO PASTE" below.
> It is self-contained. This audit is **read-only** — it writes only audit
> artifacts under `.renmark/audits/`, never code, never a branch, never a refactor.
>
> Authored 2026-06-09, immediately after `reporting-and-usage-analytics` (REQ-15/16)
> merged to `main` at `128aecb`.

---

## Pre-findings (already discovered — don't re-derive, just confirm + expand)

1. **`/renmark:hygiene` is NOT an inventory** — it is a stale-artifact GC + memory-log
   pruner. A skill-feature inventory is genuinely missing; building it is not redundant.
2. **`CLAUDE.md` `DOMAIN_BY_SKILL` lists 4 skills that don't exist** — the `audit`
   domain names `secure, document, map, research`, but none have a `plugin/skills/<name>/`
   dir. Confirm + sweep `NEXT_BY_STAGE`, `NEXT_BY_STAGE_PLANNED`, the tooling tables,
   and `help` output for the same docs→code drift.
3. **No native audit-domain skill exists** to host this → run it as a read-only sweep,
   NOT through `/renmark:feature` (which PRD-aligns, branches, and orchestrates *code*
   tasks — all mismatched for a read-only doc audit).
4. **Known self-inflicted gap:** the Part-2 codereview fix added an analytics event
   `kind="loop_iteration"` (in `plugin/skills/loop/SKILL.md`) that is registered in no
   central enum. Use it as the seed for dimension G (event-kind taxonomy).

---

## PROMPT TO PASTE (after /clear)

```
Run a READ-ONLY skill/feature inventory + modularity audit of renmark. This is
audit-first: do NOT refactor, rename, delete, merge, or branch. Write ONLY audit
artifacts under .renmark/audits/. If cleanup is warranted, propose a SEPARATE
follow-up plan with small reviewable tasks — do not implement it in this pass.

Mechanism: this is read-only and embarrassingly parallel. Inventory the commands/
skills with parallel read-only subagents (one per skill cluster), each returning
STRUCTURED ROWS only (never file bodies, never diffs). Synthesize the artifacts
yourself from those rows. Honor context hygiene: never read raw .jsonl, report
bodies, or generated code into context — paths + bounded summaries only.

Two findings are already established (confirm + expand, don't re-derive):
- /renmark:hygiene is a stale-artifact GC, NOT an inventory.
- CLAUDE.md DOMAIN_BY_SKILL references secure/document/map/research, which do NOT
  exist as skills. Sweep all docs (DOMAIN_BY_SKILL, NEXT_BY_STAGE[_PLANNED], tooling
  tables, help output, README) for the same docs→code drift.

=== 1. INVENTORY MATRIX (one row per /renmark:* command) ===
command · skill file · command-shim path · Python modules called · one-sentence
purpose · category (build/aux/terminal/recovery/governance/reporting/meta) ·
user-facing or internal · reads PRD? · writes PRD? · writes code? · writes
.renmark/ state? · commits? · merges? · releases? · deletes branches? ·
dispatches agents? · uses Codex? · requires human-approval gate? · lifecycle
stage(s) touched · durable state paths · memory/report/analytics paths · related
PRD requirement IDs · tests/verifiers · docs/help/AGENTS/CLAUDE sync status.

=== 2. OVERLAP HOTSPOTS (does each have ONE distinct owner + purpose?) ===
- usage vs analytics vs roadmap
- finish vs release/version-snapshot
- resume vs loop/orchestrate pause state
- loop vs backlog (approve-and-build)
- verify vs codereview vs secure
- feature vs plan vs orchestrate
- doctor vs hygiene
- debug vs loop/backlog repair flow
- init vs setup (setup is a thin alias — confirm it stays thin)

=== 3. SINGLE SOURCE OF TRUTH (canonical home per concept; flag any violator) ===
usage tokens -> .renmark/state/usage.jsonl   (Part 1 forbade a 2nd token ledger)
analytics events -> .renmark/analytics/*.jsonl
analytics summary -> .renmark/analytics/summary.json
local usage limits -> .renmark/analytics/limits.json
feature reports -> .renmark/reports/features/<slug>/
release snapshots -> .renmark/version/<version>/
loop state -> .renmark/loops/<id>/loop.json
pause/resume state -> .renmark/state/ pause-state file (PauseState)
pipeline runtime -> .renmark/state/pipeline.json
lifecycle/workflow -> .renmark/state/lifecycle.json
backlog -> backlog state storage
plans -> .renmark/plans/   · specs -> .renmark/specs/
memory -> .renmark/memory/

=== 4. CONTEXT HYGIENE (per skill — REQ-5/REQ-6) ===
Flag any skill that: reads raw JSONL into context · dumps logs · reads full report
bodies when a path/summary suffices · re-implements Python aggregation in markdown ·
violates bounded-output (5-line/300-token) caps · writes outside the project.

=== 5. MODULARITY + THE _shared DEDUP CONTRACT ===
Verify layering: plugin/commands/*.md = thin shims only; plugin/skills/*/SKILL.md =
workflow instructions, NOT business logic; renmark/*.py = deterministic engine;
renmark/state/*.py = persisted-state helpers; renmark/schemas.py = validation only;
.renmark/* = durable project state.
THE KEY DUPLICATION CHECK: plugin/skills/_shared/ (next-steps.md, handoff-menu.md,
scope-contract.md) must be cited BY POINTER, never inlined. List every skill that
pastes/paraphrases the hand-off menu or next-steps rules instead of referencing
_shared. Confirm skill_preamble (consolidated v0.3.2) is not re-inlined anywhere.
Red flag: any SKILL.md becoming a second implementation of Python logic.

=== 6. GOVERNANCE RULE -> ENFORCEMENT-POINT MATRIX (highest value) ===
For each G1..G12 in CLAUDE.md: is it enforced IN CODE (name the function — e.g. G11
= dispatch.parse_subagent_response, G3 = summary.verifier_tail / SubagentOutput caps)
or PROSE-ONLY/aspirational? Prose-only rules are silent liabilities — list them.

=== 7. VALIDATOR WIRING (existence != used) ===
For each renmark/schemas.py validator, is it actually CALLED by the skill/module that
emits that artifact, or only defined? A validator nobody invokes is theater.

=== 8. NON-RAISING-READ CONSISTENCY ===
Part 1 hardened read_pause/read_loop/read_usage to never raise on corrupt input
(return None/zeros) so /renmark:resume survives. Audit EVERY state reader for the
same contract. Any reader that still throws on a malformed file is a resume-killer.

=== 9. LIFECYCLE REACHABILITY ===
Walk init -> brainstorm-complete -> plan-drafted -> plan-validated -> created ->
verified -> reviewed -> documented -> ready-to-release -> released (+ restored).
Every stage needs a skill that advances INTO it and one OUT of it — flag orphan/
unreachable stages. Confirm every multi-step skill writes lifecycle.json/pipeline.json
BEFORE returning (G12) so a mid-flow /clear is recoverable.

=== 10. ANALYTICS EVENT-KIND TAXONOMY ===
Enumerate every analytics event `kind` (task_run, feature_run, loop_run, and the
ad-hoc loop_iteration added in the Part-2 fix). Are kinds a central enum or scattered
string literals? Flag drift; recommend a registry if missing.

=== 11. SAFETY / GATE CONSISTENCY ===
Per command, which can: edit code · edit PRD.md · commit · merge · release · delete
branches · increase budget · dispatch agents · run loops · resume paused work · write
reports/analytics. Flag any missing human-approval gate or hidden auto-execute.

=== 12. UX COMPLEXITY ===
Per command: keep-separate / fold-into-menu / make-internal / rename / document-better
/ deprecate. Apply the one-sentence-purpose test: if the purpose needs an "and", it
is doing two jobs.

=== 13. OPERATIONAL CHECKS ===
- Idempotency/re-run safety: does re-running finish/verify/orchestrate double-write?
  (log_decision/log_escalation are idempotent on (title,date) — which others aren't?)
- Version parity: release.check's "7 version locations" — is the count still accurate
  and all covered?
- Dead code: renmark/*.py public symbols that no skill/command/test references.
- Test coverage: every skill should have a verifier for shim-exists, skill-exists,
  import-works, schema-validates, no-raw-JSONL, disclaimer-present, pause/resume,
  finish/report behavior.

=== OUTPUT (artifacts under .renmark/audits/, dated) ===
1. skill-feature-inventory-<date>.md   (+ .json machine-readable mirror)
2. ownership-source-of-truth-map-<date>.md
3. overlap-findings-<date>.md
4. modularity-scorecard-<date>.md       (incl. _shared dedup + G-rule matrix)
5. context-hygiene-and-safety-risks-<date>.md
6. recommended-cleanup-backlog-<date>.md   (Keep/Merge/Rename/Deprecate/Split/
   Needs-owner/Needs-tests/Needs-docs-sync — prioritized, NOT implemented)

End with a bounded summary: counts per category, top 5 findings, and a one-line
recommendation on whether a follow-up cleanup feature is warranted. Do not refactor.
```

---

## After the audit

Only if it surfaces real overlap, run a *separate* follow-up — e.g.
`/renmark:feature skill-surface-cleanup-from-audit` — with small, reviewable tasks.
Keep audit and cleanup as two passes so you never refactor a freshly-shipped system
before you understand its full surface.

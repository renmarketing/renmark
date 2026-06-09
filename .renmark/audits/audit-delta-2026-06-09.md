---
artifact_type: audit
schema_version: 1
created_at: 2026-06-09T19:20:00-04:00
source_sha: 618624c
related_plan: .renmark/audits/skill-feature-inventory-spec.md
generator: claude-fable-5 (delta re-run of the Opus audit; 19 agents — 10 adversarial verifiers, 7 novel sweeps, gates run, PRD-alignment)
dependency_refs:
  - .renmark/audits/skill-feature-inventory-2026-06-09.md
  - .renmark/audits/ownership-source-of-truth-map-2026-06-09.md
  - .renmark/audits/overlap-findings-2026-06-09.md
  - .renmark/audits/modularity-scorecard-2026-06-09.md
  - .renmark/audits/context-hygiene-and-safety-risks-2026-06-09.md
  - .renmark/audits/recommended-cleanup-backlog-2026-06-09.md
completion_state: complete
confidence: high
validation_status: validated
---

# Audit delta — Fable 5 re-run of the 2026-06-09 Opus audit

Method: every top finding of the original audit was handed to an **adversarial
verifier told to refute it** (with empirical reproduction where possible — the
crashes were actually triggered in /tmp sandboxes), plus 7 sweeps over
dimensions the original never ran. Result: **8/10 confirmed, 2/10 partial
(headline right, details corrected), 0 refuted — and 66 novel findings**,
including 3 criticals and a security gap.

## 1. Ground truth from running the actual dev gates (novel — original audit never ran them)

- `pytest -q`: **608 passed, 28 skipped** ✅ (now 615 after this session's fixes)
- `ruff check`: **FAIL — 39 errors, all in tests/** (16 F401, 9 SIM117, 7 I001, …)
- `mypy .`: **FAIL — 2 errors** in the dead provider modules (openai_compat.py:75, nim.py:143)
- **ruff and mypy are not installed in `.venv`** despite being declared dev
  dependencies and CLAUDE.md gates — the "ruff + mypy clean" CHANGELOG claims
  could not have been produced by this venv. (Caveat: gates were run with
  latest ruff/mypy from an out-of-repo install; a pinned older version may
  report fewer rules.)
- `.venv` Python is 3.14.3 vs system 3.12.3 — undocumented.
- **Gated integration tests fail silently**: `RENMARK_SMOKE=1 pytest` → 3
  FAILURES (stale `/renmark:approve` and `/renmark:release` assertions) that
  plain pytest never sees because of the conftest skip gate.

## 2. Verdict matrix on the original audit's top findings

| finding | verdict | corrections to the original |
|---|---|---|
| read_lifecycle raises on corrupt state | **confirmed** (reproduced) | WORSE than audited: `next_recommended` and `write_lifecycle` also raise → a corrupt file poisons every skill's stage write, not just resume. One detail wrong: `next_steps` does NOT inherit the raise (has its own try/except floor). **FIXED this session (0a4efcb)** |
| last-skill.json bare cast | **confirmed** (reproduced) | Severity worse: `record_skill_invocation` runs only after the crashing call, so the wedge is permanent until manual delete. **FIXED (7b2fef1)** |
| /renmark:approve missing | **partial** | Headline confirmed; details wrong: **prd is the only live human_review writer** (finish never touches it) and prd self-clears its own gate; the Python router already emits a manual-fallback hint, never "/renmark:approve". prd is a 5th caller (self-aware: "*planned*"). CHANGELOG carries a "Do not change" guard saying approve is not shipped — must be inverted in the same commit that builds it. |
| validators unwired (0/8) | **confirmed** | Wiring rule from the verifier: wire at WRITERS, never as hard gates at readers (reader tolerance is contractual + test-pinned). Circular-import constraint: schemas imports dispatch+lifecycle → wire via function-local imports. |
| lifecycle registry drift | **confirmed** | All 8 ghosts + 5 missing reals reproduced; `domain_of("secure")=="audit"` is test-pinned (test_lifecycle.py:212) — removing ghosts must update that test + CLAUDE.md/AGENTS.md + **plugin/templates/CLAUDE.md.template** (see §3). |
| append idempotency | **confirmed** | usage dedup key must be (run_id, task_id, **attempt**) — codex retries legitimately append identical (run_id, task_id) rows; `tests/test_state.py:13-27` codifies blind-append and must change with the contract. Honest-spend nuance: crash-resume usually re-dispatches for real; the phantom path is re-LEDGERING without a new call. |
| G9 defaults inversion | **partial** (was confirmed; parse-side now fixed in 618624c) | Emitting side still wrong: `cmd_task` declares PASS on bare artifact existence with medium/complete and omits validation_status/parser_success/schema_compliance entirely (commands.py:170-206). `summary.ArtifactMetadata` shares the optimistic confidence default. |
| fragile readers | **confirmed** (all reproduced) | Two corrections: `pipeline_is_resumable` with BOTH wave fields as strings doesn't crash — it compares **lexicographically ("10"<"9" → True), silently wrong**, worse than the crash; `read_wave_summary`'s real consumer fails with TypeError (subscript), not AttributeError. Bonus: `_core.rotate_dir:92` stats unguarded too. |
| docs drift pack | **confirmed** (all counts exact) | New nuances: AGENTS.md has NO domain table (only CLAUDE.md does); AGENTS.md rows use `\renmark:` backslashes; the doc-table ghosts mirror code-dict ghosts, so a pure docs pass must regenerate from the dict and fix the dict separately. |
| orphan stages | **confirmed** | Adjacent latents: **nothing ever calls `clear_lifecycle`** — after merge the file sits at ready-to-release forever and `/renmark:start` permanently redirects to resume; ADR-022's own Context proves stage-loss happened on a real run (missing verified/reviewed). |

PRD alignment (separate agent): every planned fix ALIGNED; only the approve
skill is NOT-COVERED by the PRD scope list → requires a human-gated
`/renmark:prd` scope addendum before building it.

## 3. Novel findings (66) — the things the original audit missed

### Critical (3)

1. **Loop decision engine is structurally blind — every failed verify stalls the loop on iteration 1.**
   `write_artifact` puts `summary_lines` in the artifact BODY; `read_metadata`
   parses YAML frontmatter only. So `loop.build_decision` (which derives
   `next_action` from `meta["summary_lines"]`) always sees `[]` → blank
   next_action → status `stalled`. The documented "failing verify with an
   actionable symptom CONTINUES the loop" behavior is unreachable.
   (renmark/loop.py:452,487 · summary.py:136,185 · loop SKILL.md:148-158.
   Same root cause degrades finish's `verification` field to "complete|partial"
   — feature reports/analytics never get the "N/M behaviors" line.)
2. **`execute_plan` reports false success on budget exhaustion** — budget/time
   gates `break` without setting `failed_task`; run prints "All tasks
   completed.", exits 0, writes NO pause state; skipped undercounts later
   waves. (cli/_engine.py:380-390,468-472)
3. **Parallel codex waves can destroy sibling work** — change detection is
   repo-global `git status --porcelain`, so a finishing task sees a sibling's
   in-flight file as out-of-lane and its rollback runs `git checkout -- .`
   (whole tree) + `git clean -fd`. The `_GIT_LOCK` doesn't cover this path.
   (cli/_engine.py:640-655 · providers/codex.py:33-52)

### Security (2, major)

4. **Release zip/snapshot packages secrets** — excludes only exact
   `.env`/`.env.local`; `.env.production`, `*.pem`, `id_rsa`,
   `credentials.json`, `.npmrc` etc. all get archived, and finish §4 uploads
   the zip via `gh release create`. (release.py:152-168) → **FIXED this session**
5. **`cmd_task` (the G5 codex path) runs `codex exec` with NO --sandbox flag
   and no lane check** — the most-used, least-guarded codex entry point;
   codereview's read-only sandbox is prose-only (no Python builds that
   command). (cli/commands.py:147-148) → sandbox flag **FIXED this session**

### Major — engine & contracts (9)

6. Orchestrate SKILL tells the agent to call `summary.verifier_tail(cmd, tail_lines=3)` — signature requires keyword-only `cwd` → TypeError on first passing task (SKILL.md:166,284). → **FIXED**
7. Orchestrate wave-dependency snippet reads `task_output['task_id']` — a key `to_dict()` never writes → KeyError; the only sanctioned cross-wave channel is broken as written (SKILL.md:88-91 vs :177). → **FIXED**
8. verify/orchestrate dereference `plan.context`/`plan.tasks` but `parse_plan` returns a bare `list[Task]` → AttributeError; no API exposes the plan's intent paragraph at all (verify SKILL.md:73-76, orchestrate :76). → **FIXED (snippets)**
9. Failed mode-A codex task leaves the bad untracked target on disk (checkout can't restore an untracked file, returncode ignored) → cascading out-of-lane misjudgments for the NEXT task (cli/_engine.py:708).
10. The entire post-NIM application layer is production-dead: apply.py, prompts.mode_a/b, _engine._build_prompt/_apply — the original dead-code sweep caught only 2 functions of it.
11. Shadow regression harness (guards G3/G11/G12 anchors) is wired into NO gate — precommit and CI never run it; real baselines never replayed.
12. `sizing`'s core-module safety floor hardcodes `renmark/`+`bin/` — in user projects it never fires, and missing est_tokens leans LITE ("never lite by accident" doctrine inverted).
13. Token budget is inert: codex usage records 0 tokens, so `RENMARK_MAX_TOKENS_PER_RUN` can never trip; "Tokens this run: 0/50000" is permanently misleading.
14. routing.md **and its shipped template** route simple tasks to executor `nim` — removed in v0.2.0, rejected by parser.py → live plan-parse failures; curated file, hygiene can't fix. → **FIXED this session**

### Major — plugin spec & docs (8)

15. **8 of 46 frontmatters are invalid strict YAML** (unquoted `: ` mid-value; plan.md's unescaped quotes) — and `lint.parse_frontmatter` is a regex, constitutionally unable to notice (the original audit's "frontmatter ✓ all 23" was wrong because the linter is blind).
16. **CLAUDE.md.template propagates every known ghost/stale table into each newly scaffolded project** — absent from the original fix lists; even after root-doc fixes land, new projects re-inherit the drift. (AGENTS.md.template too.)
17. CONTRIBUTING.md is the most-drifted file in the plugin: 17/23 skills violate its mandatory Governance-compliance section (including its own named exemplar); its Step-0 template teaches the deprecated pre-v0.3.2 API; its rule-block ritual points at a setup merge table that no longer exists and a `/home/renmark/...` private path; its G11 row names 4 ghost skills.
18. init's recovery path points at nonexistent `bin/renmark-install` (fires exactly when the package is broken).
19. blueprint (and an orchestrate doc pointer) load templates by repo-relative `plugin/templates/...` — dangles at install time; correct form is `${CLAUDE_PLUGIN_ROOT}/templates/...` (prd does it right).
20. backlog routes the "Research more" disposition to nonexistent `/renmark:research`. → **FIXED (route to brainstorm)**
21. feature Step 6 instructs choosing "[v] Verify" from orchestrate's menu — orchestrate has no such option (verify auto-runs since v0.3.3). → **FIXED**
22. `_shared/next-steps.md` class rosters contradict lifecycle.py: verify listed in two classes, backlog omitted, loop/usage/analytics in none; handoff-menu.md rule 6 ranks `[o]`/`[fix]` codes its own canon never defines.

### Major — memory subsystem (4)

23. features.md is missing the 3 newest shipped features and blueprint is stuck "In progress" since 06-05 → roadmap under-reports; the auto-update contract stopped being honored after loop-mode.
24. INDEX.md is stale on every axis it claims to maintain ("auto-maintained" counts all zero vs 22 ADRs/14 routing/10 features real) — and **no code maintains it**.
25. `memory._insert_after_section` leaks one blank line per append — compounding, in curated files hygiene refuses to touch (decisions.md ~16 blanks, learnings.md ~39…).
26. roadmap documents a "planned" status + features.md source that the code never implements (build_rows reads only git log + usage.jsonl); sample output still shows NIM-era models.

### Selected minors (full list in sweep outputs)

prd's documented gate-clear passes `human_review_for=None` which write_lifecycle treats as "leave unchanged" (stale gate text persists, burns the 1KB budget) → **FIXED (pass "")**; backlog SKILL misattributes status coercion to write_item (read-side only — silently flips bad status to "needs review", defeating resume detection); debug SKILL documents keyword-only helpers positionally (literal copy → TypeError); doctor claims exit 1 on warnings (code exits 0); codereview cites a renmark-CLI review lane + log path no code provides; release `--name` lacks the traversal guard its siblings have; author identity disagrees between plugin.json ("renmark") and marketplace.json ("renmark"); stack.md claims "stdlib only" vs declared requests+python-dotenv deps; project-map.md Purpose cells garbled mid-sentence (`_file_purpose` picks a wrapped docstring line); bugs.md/learnings.md placeholder-drift + one garbled entry; ADR-022 records an incomplete lifecycle (evidence of real stage loss); lint passes crash on unreadable files (modularity.py shows the right pattern); parser silently swallows malformed task headers; bootstrap's `is_empty_project` guard is never wired (`init_git=True` would `git add -A` a non-empty folder); codereview's standards prompt hardcodes renmark's own precommit toolchain into every user project; codereview argument-hint omits --full/--skip; doctor ships no argument-hint; modularity can't distinguish same-named methods.

## 4. What was clean (refutation attempts that failed)

Subprocess hygiene is strong (no shell=True anywhere, list-form argv, plan text via stdin, hardened rev args); path sanitization for loop_id/reports/debug/parser targets is solid; all CLI flags in cluster-B skills match real argparse; every REQ-* cited by skills exists in PRD.md; lifecycle stage strings in prose match STAGES; templates dir is complete (only path *forms* are broken); ADR-005/ADR-009 exist; project-map.md is fresh; dev-standards.md and qa-flows.md are accurate.

## 5. /renmark:audit design input (from the unexamined-modules sweep)

`renmark/lint.py` ALREADY deterministically implements 5 audit dimensions, live-pinned by tests against the real plugin every pytest run: inventory pairing (orphan shims/unreachable skills), frontmatter presence/name-match, shim→SKILL wiring, class-aware next-steps citation, rule-block integrity. `renmark/modularity.py` covers engine code-health (5 AST metrics → dev-standards.md via init). `release.check` covers version parity. **An audit skill should COMPOSE lint_all + modularity.analyze + release.check and add only the missing passes**: registry-sync (lifecycle dicts vs skills dir — the worst drift module has zero lint coverage), shim-thinness, shim/SKILL description drift, strict-YAML frontmatter validity, template-table parity, no-raw-JSONL/disclaimer cross-skill checks.

## 6. Fixes landed this session (sha-stamped)

| commit | fix |
|---|---|
| 0a4efcb | read_lifecycle hardening + type-filter + validate_artifact_refs guards + 6 tests |
| 7b2fef1 | last_skill_invocation non-dict guard + tests |
| 618624c | parse_subagent_response: omitted confidence → "low" (G9) + tests |
| (this wave) | fragile readers (usage_today/this_month, roadmap, pipeline coercion, wave-summary, recent_logs) · append_routing + record_feature_run idempotency · release secret-exclusion globs · cmd_task --sandbox flag · summary.read_summary_lines helper + loop/finish SKILL rewire · orchestrate/verify snippet contract fixes · routing.md nim→haiku (+template) · backlog research-route · feature [v] step · prd gate-clear |

## 7. Revised priority queue (supersedes the original backlog ordering)

**P0 — remaining after this session:** engine false-success on budget exhaustion (#2 crit); parallel-wave rollback isolation (#3 crit); mode-A rollback of untracked targets (#9); registry+docs+TEMPLATE mega-sync (original items 4,6-9 + template propagation #16 — one feature, mirror-committed); /renmark:approve build (PRD addendum first — human-gated); usage (run_id,task_id,attempt) dedup key.
**P1:** YAML frontmatter quoting + strict-YAML lint pass (#15); CONTRIBUTING.md rewrite (#17); shadow into precommit/CI (#11); memory blank-line leak + INDEX/features backfill (#23-25); validators wiring per the writer-side map; orphan stages wiring (reviewed/released + clear_lifecycle call); sizing floor (#12); cmd_task G9 emitting side.
**P2:** the minors above; ruff test cleanup (39, mostly autofixable) + pin gate versions + install dev extra; dead apply/prompts/providers deletion; bootstrap guard wiring.

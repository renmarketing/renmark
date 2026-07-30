# Learnings

Auto-maintained by `/renmark:orchestrate` and `/renmark:debug`. Records patterns learned from past runs.

## Format

Each entry: signal, observation, model that caught it, date.

## Common patterns (seeded from prior projects)

- `tests/**.py with threading + setUpClass` — NIM small models often produce invalid Python here. Route to `codex` or `opus`.
- `.js with canvas/DOM API` — NIM small models often write code that crashes at runtime (e.g., `document.canvas.width`). Route to `opus`.
- Codex with `--sandbox workspace-write` will sometimes modify files outside the target — verify with a post-run lane check.

## Learned this project

- (2026-07-30, review) model `codex-reviewer`: **Codex retry target rollback** — Every rejected executor attempt must restore its own target before retry; otherwise path-set deltas can hide a legitimate edit on the next attempt and produce a false unchanged-target failure.

- (2026-07-30, bug) **Codex executor accepted unchanged targets as PASS** — An agent exit plus a green verifier is not implementation completion; require attributable target change and durable commit evidence, or an explicit validated batching sentinel.

- (2026-07-30, bug) **Ruff baseline regressed after M1 delivery-state additions** — Run the repository-wide Ruff gate after milestone task commits and before the next milestone preflight; passing task-local verifiers alone does not prove cross-file style convergence.

- (2026-07-29, .renmark/reviews/2026-07-29-402c3ed.review-remediation.md) model `codereview-remediation`: **review-m1-canonical-delivery-state** — 2/2 blocking Major findings resolved; stable legacy identity and writer-validator convergence; full suite 1540 passed, 31 skipped

- (2026-07-29, .renmark/debug/20260730-001342-658d/session.md) model `debug`: **debug-m1-canonical-identity-convergence** — Canonical metadata must be normalized by the writer and legacy projections need identity derived from stable persisted fields, never a fresh UUID per read.

- (2026-07-29, bug) **M1 canonical state had unstable identity and validator drift** — Canonical metadata must be normalized by the writer and legacy projections need identity derived from stable persisted fields, never a fresh UUID per read.

- (2026-07-29, .renmark/reviews/2026-07-29-4702acb.verification.md) model `verify`: **verify-m1-canonical-delivery-state** — 4/4 behaviors verified; failed: none; regressions: repository suite

- (2026-07-29, .renmark/debug/20260729-220633-3642/session.md) model `debug`: **debug-m1-delivery-state-normalization** — Never clone nested dataclasses with asdict plus a top-level constructor; typed clones and normalization functions must preserve nested types and be idempotent.

- (2026-07-29, bug) **M1 delivery-state CLI crashed on legacy work packages** — Never clone nested dataclasses with asdict plus a top-level constructor; typed clones and normalization functions must preserve nested types and be idempotent.

- (2026-07-29, .renmark/reviews/2026-07-29-3a35610.verification.md) model `verify`: **verify-m1-canonical-delivery-state** — 3/4 behaviors verified; failed: bounded current-state CLI; regressions: repository suite

- (2026-07-29, run) **task 1 failed on codex** — repeated_issue_guard

- (2026-07-17, .renmark/reviews/2026-07-17-f87b955.verification.md) model `verify`: **verify-proactive-repeated-issue-monitor** — 4/4 behaviors verified; failed: none; regressions: 0

- (2026-07-17, bug) **Recurrence guard discarded the actionable verifier failure** - A retry guard must preserve the failure evidence needed to repair the issue it stops.

- (2026-07-17, run) **task 1 failed on codex** — repeated_issue_guard

- (2026-07-17, bug) **Repeated verifier failures recommended an instruction guard** — Use recurrence count to decide when to stop retrying; use failure identity to decide how to remediate.

- (2026-07-17, run) **task 1 failed on codex** — repeated_issue_guard

- (2026-07-17, run) **task 1 failed on codex** — repeated_issue_guard

- (2026-07-17, bug) **Claude specialist agents fell back to general-purpose** — A dispatch-role registry is not host capability proof; package the host-native definition and resolve its installed scoped name before dispatch.

- (2026-07-17, bug) **Claude native picker missing after parity install** — Treat plugin-manager registration and cache existence as installation postconditions; never suppress the final health check behind an output-filtering pipeline.

- (2026-07-16, bug) **Repository-wide Ruff and mypy baseline was red** — A green pytest run is not a substitute for running every repository quality gate after cross-file extraction work.

- (2026-07-06, .renmark/reviews/2026-07-06-c89a3320872dc49cbe62209cdf740f2a4c7dcd69.verification.md) model `verify`: **verify-agent-team-migration** — 7/7 behaviors verified; failed: none; regressions: 0

- (2026-07-02, .renmark/reviews/2026-07-02-85b12b34f7d608199efad59895d9826593500f62.verification.md) model `verify`: **verify-agent-turn-runner** — 5/5 behaviors verified; failed: none; regressions: 1257 passed

- (2026-07-02, .renmark/reviews/2026-07-02-7c91bd8dd69c7ebf6d316e0b0995851ff2c408d4.verification.md) model `verify`: **verify-live-eval-runner** — 7/7 behaviors verified; failed: none; regressions: full suite 1242 passed/28 skipped

- (2026-07-01, .renmark/reviews/2026-07-01-889330cac7a287c0e0d44f024c9ea500a2675dc1.verification.md) model `verify`: **verify-dynamic-skill-loading** — 8/8 behaviors verified; failed: none; metadata-not-body proven in prod dispatch path

- (2026-07-01, .renmark/reviews/2026-07-01-d254cc8.verification.md) model `verify`: **verify-harness-operating-modes** — 7/7 behaviors verified; failed: none; full suite 1205 passed

- (2026-07-01, .renmark/reviews/2026-07-01-e2ec9b4954e08cf09141f63718a1e28ae594f042.verification.md) model `verify`: **verify-p8-v2** — 6/6 behaviors verified; failed: none; regressions: 2 (Major-1, bootstrap)

- (2026-07-01, bug) **P8 weakened reference-case assertions** — fix round partial; deterministic behavioral testing has a fundamental live-call constraint

- (2026-07-01, bug) **P8 feature un-bootstrappable** — fix round partial; deterministic behavioral testing has a fundamental live-call constraint

- (2026-07-01, bug) **P8 Major 1 residual: replay returns golden as current transcript** — fix round partial; deterministic behavioral testing has a fundamental live-call constraint

- (2026-07-01, .renmark/reviews/2026-07-01-9f7f0ab.verification.md) model `verify`: **verify-p8-refix** — fix round: 4 review findings resolved; full suite 970 passed

- (2026-07-01, bug) **P8 snapshot ref path traversal** — codereview caught under-built P8 before merge

- (2026-07-01, bug) **P8 judge silent-pass on bad confidence** — codereview caught under-built P8 before merge

- (2026-07-01, bug) **P8 --accept cannot record from CLI** — codereview caught under-built P8 before merge

- (2026-07-01, bug) **P8 replay does not test current behavior** — codereview caught under-built P8 before merge

- (2026-07-01, .renmark/reviews/2026-07-01-60eddc0.verification.md) model `verify`: **verify-p8-behavioral-skill-testing** — 6/6 behaviors verified; failed: none; regressions: full suite 962 passed

- (2026-06-26, .renmark/reviews/2026-06-26-3a76fc4752d70decf6bc9d35f64157ea6e0467d9.verification.md) model `verify`: **verify-p10-headless-contract** — 5/5 behaviors verified; failed: none; full suite 934 passed/28 skipped; note: PATH renmark-execute points at main checkout, verify worktree code via -m renmark

- (2026-06-26, run) **task 2 failed on codex** — codex_verifier_failed

- (2026-06-25, bug) **P11 proactivity toggle: persisted but not runtime-enforced** — persist+document is a valid first increment, but a config flag with zero readers is half-wired — wire a real consumer or log the gap.

- (2026-06-25, .renmark/reviews/2026-06-25-8baae38b6d32fc4044c17e55b77daa5eaf3ba313.verification.md) model `verify`: **verify-graduated-preamble-tier** — 5/5 behaviors verified; failed: none; regressions: full suite 867 passed

- (2026-06-16, .renmark/reviews/2026-06-16-e6c015039b6e32dbb6ada6014cf03cc929575f02.verification.md) model `verify`: **verify-finish-branch-disposition** — 4/4 behaviors verified; failed: none; regressions: 0. Smoke confirmed transform-not-append, rollup no-double-count, both finish paths wired, feature-name fallback closes post-merge.

- (2026-06-16, run) **finish disposition close-out** — Match the open feature-run row by FEATURE NAME, not feature+sha: finish merges with --no-ff so post-merge HEAD is the merge commit, not the recorded feature-tip sha; a sha-hard match silently no-ops. close_feature_disposition is feature-primary with sha as optional narrowing + fallback.

- (2026-06-16, .renmark/reviews/2026-06-17-e6244a2.review.md) model `verify`: **verify-req14-scan-fixes** — post-review-fix re-verification: full suite 844 green; Critical hook bypass independently confirmed blocked (git -C/--git-dir/env-prefix all rc=2); read-only invariant holds

- (2026-06-16, .renmark/reviews/2026-06-17-e6244a2.verification.md) model `verify`: **verify-req14-scan-proposer** — 3/3 behaviors verified; failed: none; regressions: 0; dedup proven end-to-end (run1 proposed 1, run2 0); engine found 1 real finding on the renmark repo while dogfooding

- (2026-06-14, bug) **Hand-off picker not re-rendered on continuation turns** — A non-selection free-text reply to a hand-off (clarifying question/follow-up) keeps the hand-off OPEN: answer it, then re-render the picker in the same turn. An inline 1./2. list in the reply body is NOT a rule-7 fallback.

- (2026-06-14, bug) **roadmap --setup staleness guard unclearable by /renmark:init after non-structural commit** — A freshness marker (Last-refreshed @ sha) must advance independently of body-content equality — coupling a staleness check to a sha that only moves on body change creates an unclearable wedge. Also: test fixtures for sha-keyed checks must use VALID HEX (the header regex is [0-9a-fA-F]+).

- (2026-06-14, .renmark/reviews/2026-06-14-cc2beae3572e760c98ba5cb8ef7091129b8f7e59.verification.md) model `verify`: **verify-roadmap-staged-planner** — 6/6 behaviors verified; failed: none; regressions: 1 (loop driver, no overlap); full suite 812 passed

- (2026-06-13, .renmark/reviews/2026-06-13-aeacf9771d0e535f51b2fa87cebc276743aaa854.review.md) model `verify`: **verify-playwright-browser-control-postfix** — post-codereview-fix re-verify: 9/9 goal-backward behaviors green on sha 7cceadf (path-traversal Critical closed end-to-end, canary intact); full suite 780 passed; each fix adversarially verified, not trusting executor self-claims

- (2026-06-13, .renmark/reviews/2026-06-13-2c5cf111597215352754aba861a15434848fbe58.verification.md) model `verify`: **verify-playwright-browser-control** — 7/7 goal-backward behaviors verified (guarded/fallback path; playwright not in env); failed: none; full suite 759 passed

- (2026-06-12, .renmark/reviews/2026-06-12-6152a1e.dsf.verification.md) model `verify`: **verify-doc-slimming-fixes** — 6/6; restored 7 over-compressed governance clauses + fixed 1-of-4 mirror drift + stale version + honest changelog; lesson: compression review must diff EVERY block in EVERY mirror file, not just the file the reviewer was pointed at

- (2026-06-12, .renmark/reviews/2026-06-12-718b577.cds.verification.md) model `verify`: **verify-claude-doc-slimming** — 5/5 verified; 4 onboarding docs halved (1122->528) via terse-rewrite; block byte-identity template<->CLAUDE.md preserved so merge/audit see no drift; all governance clauses grep-intact

- (2026-06-12, .renmark/reviews/2026-06-12-4c59169.pte.verification.md) model `verify`: **verify-prd-template-enrichment** — 4/4 verified; surgical PRD enrichment (5 additive pieces, anti-completion guard) rather than wholesale 17-section import — preserved altitude separation

- (2026-06-12, .renmark/reviews/2026-06-12-4c8ab91.ca.verification.md) model `verify`: **verify-cowork-alignment** — 4/4 verified; reuse-check + pushback stance + contradiction-reconcile + re-interview-on-change all wired; ported from external Cowork operating-instructions exercise

- (2026-06-12, .renmark/reviews/2026-06-12-c7f1aa6.arp.verification.md) model `verify`: **verify-agent-routing-policy** — 4/4 verified; haiku-pinned prd-alignment subagent ignored the bounded-return format on first run (verdict correct) — bounded-format wording may need hardening for haiku

- (2026-06-12, .renmark/reviews/2026-06-12-4eb8166.verification.md) model `verify`: **verify-fable-routing** — 6/6 behaviors verified; declaration gate fires both directions; env override + preview pricing live; dual provider-limit interruption recovered via pause state + codex retry

- (2026-06-11, .renmark/reviews/2026-06-11-0113ee4.part2.verification.md) model `verify`: **verify-fable-integration-part2** — 4/4 doc-sync behaviors verified; session-limit interruption recovered from pipeline.json; lesson: plan verifiers for mirror tasks must be case-insensitive when the only anchor is capitalized

- (2026-06-11, .renmark/reviews/2026-06-11-5fa6915.verification.md) model `verify`: **verify-fable-integration** — 4/4 behaviors verified; failed: none; regressions: 0; heavy-read G5 detector keys on context_files field, not spec prose (fixture lesson)

- (2026-06-09, .renmark/reviews/2026-06-09-f2aaf16.review.md) model `codereview`: **codereview-integration-contract-drift** — Part-2 subagents writing skill-doc integration prose invented engine contracts that don't exist: a view['limit_exceeded'] field, a LifecycleState.verification_result attr, free-text verifier_result vs analytics' pass/fail vocab, status=raw-stage vs SUCCESS/BLOCKED_STATUSES, per-iteration record_loop_run vs one-row-per-loop aggregation. Gate (pytest/ruff/mypy) PASSED because the prose is markdown, not executed — only codex review + field/attr existence probes caught it. Lesson: for doc tasks that reference real APIs, verify every referenced field/attr/vocab against the engine, not just that function names exist.

- (2026-06-09, .renmark/reviews/2026-06-09-a685228.verification.md) model `verify`: **verify-reporting-and-usage-analytics** — 9/9 behaviors verified; failed: none; regressions: 1; full gate green (608 passed, ruff+mypy clean)

- (2026-06-09, .renmark/reviews/2026-06-09-619db95586c61627963cce188edf398806a18958.verification.md) model `verify`: **verify-release-version-snapshot** — 7/7 behaviors verified; failed: none; real CLI snapshot 212 files; full suite 588 pass

- (2026-06-09, .renmark/reviews/2026-06-09-be1f4111cb1b5ec39842bac258349fc1be8cb5f2.verification.md) model `verify`: **verify-backlog-driven-loop-execution** — 5/5 behaviors verified; failed: none; regressions: full suite 570 pass; codex sandbox read-only -> task2 tests fell back to sonnet

- (2026-06-09, codereview) model `opus`: **a loop is only a loop if it can iterate on failure** — Loop Mode codereview caught that the driver stalled on the FIRST failed verify (blank next_action) — it was an automation, not a loop. The decision object MUST derive a next_action from verification evidence, and the budget gate MUST preflight (not post-check) or it overshoots. For any iterate-until-goal feature, adversarially test the FAILURE-then-continue path and the boundary (budget/iter) BEFORE shipping — the happy path hides both.

- (2026-06-09, .renmark/reviews/2026-06-09-41121c499925debfe185b1c240cae49ec3a70328.verification.md) model `verify`: **verify-loop-mode** — 6/6 verified; loop state machine bounded+resumable; new loop skill+command pair lint-clean; core code → keep full codereview

- (2026-06-08, codereview) model `opus`: **advisory metrics still need accuracy review** — Even an ADVISORY lens must be accurate or it misleads: codereview found the modularity analyzer both under-reported (span/branch math) and over-suppressed (substring match hid real files). A health lens that silently drops real findings is worse than none. Adversarially review the metric math + the SUPPRESSION rules, not just the happy path.

- (2026-06-08, .renmark/reviews/2026-06-08-25e2ee93f8b830c2ef62c79059c8a05cf6062096.verification.md) model `verify`: **verify-modularity-health-lens** — 6/6 verified; advisory ast lens; HEALTH line bounded; renmark self-scan flagged 111 gaps (its own code has oversized files/functions). core ast code → keep full codereview.

- (2026-06-08, codereview) model `opus`: **a safety classifier must be adversarially reviewed for its DANGEROUS direction** — proportional-pipeline routed its OWN review to full codex (classify_diff self-tiered full) — which then found 2 Critical false-lite holes in the classifier (substring match, malformed→lite, override bypass). The dangerous direction (false-lite skips review) needs explicit adversarial tests, not just happy-path. The user repeatedly choosing codereview over my skip-recommendation kept paying off.

- (2026-06-08, .renmark/reviews/2026-06-08-634af6df145e82e95692521316732de4a364836c.verification.md) model `verify`: **verify-proportional-pipeline** — 6/6 verified; sizing classifier degrades-to-standard confirmed; feature touches core code so full codex review warranted (it would self-classify standard/full)

- (2026-06-08, codereview) model `opus`: **codereview pays off on doc/contract features too** — I recommended skipping codereview for the acceptance-criteria feature (markdown only). User ran it anyway; codex found 2 real cross-file format inconsistencies (skill vs template named different literal shapes) that an executor could misread. Lesson: when a feature spans a template + the skill that emits it, codereview the CONSISTENCY even if there is no Python.

- (2026-06-08, .renmark/reviews/2026-06-08-40f64cb66346dc566e99764ddd360f175c326e41.verification.md) model `verify`: **verify-acceptance-criteria** — 4/4 verified; doc/skill-only feature; codereview skipped as low-value over markdown

- (2026-06-08, codereview) model `opus`: **a test can codify the bug** — The original unclosed-BEGIN test asserted the VULNERABLE behavior (merge proceeds past malformed, back-fills other blocks) and passed — giving false confidence. Codex caught the corruption; the fix replaced the test to assert the safe contract (raise + file unchanged). Audit tests that pass on malformed input: are they asserting safety or codifying the bug?

- (2026-06-08, run) model `opus`: **codereview/verify can mutate the live repo** — Running the MUTATING python -m renmark.init on the working repo (once as a verify smoke, once by codex while verifying findings) back-filled CLAUDE.md + refreshed the map twice. Guard: run mutating CLI smokes in mktemp copies; codex read-only sandbox does not fully prevent cwd writes when it executes code.

- (2026-06-08, run) model `verify`: **verify smoke must not mutate the deliverable** — A regression smoke ran `python -m renmark.init` on the live repo, which back-filled a rule block + refreshed the map + scaffolded .renmark files. Correct behavior, but a verify side-effect. Run mutating CLI smokes in a tmp copy (mktemp), not the working repo. Reverted cleanly. (Same lesson as the opus entry above — merged for clarity.)

- (2026-06-08, .renmark/reviews/2026-06-08-42b332dcbcaa9274bcb3b9a436902d77b4400157.verification.md) model `verify`: **verify-init-pipeline** — 5/5 behaviors verified; headline bug (init exit-1 w/o CLAUDE.md) fixed; merge_rule_blocks non-destructive+idempotent confirmed on a real file

- (2026-06-08, run) model `sonnet`: **hardcoded counts in specs go stale** — Spec said 17 rule blocks; the live template has 23. The test subagent asserted dynamically against the template instead of hardcoding — correct. Avoid hardcoded magic counts in specs/tests.

- (2026-06-08, run) model `opus`: **subagent factored a shared helper across files** — Task1 (one-file=init.py) also added iter_rule_blocks() to lint.py to avoid duplicating the BEGIN/END regex — a sensible cross-file refactor the spec invited. It did not collide with parallel wave-1 tasks (disjoint), but note: a 1-file task touching a 2nd shared file is OK only when no parallel task touches that file.

- (2026-06-08, codereview) model `opus`: **codereview-incomplete-fix** — Codex flagged next_steps raising on non-str (verified). First fix guarded skill_class only; re-running the exact repro revealed the aux dict lookup still raised. Always re-run the reviewer-provided repro after fixing, not just the suite.

- (2026-06-08, bug) **next_steps() raised on non-str skill** — A try/except around state reads is not enough — defend every hashable-key op on untrusted input; the FIRST guard fix missed the aux dict lookup, caught only by re-running the repro.

- (2026-06-08, .renmark/reviews/2026-06-08-72a332861a6cf7d8b140928a976058b8d99b6078.verification.md) model `verify`: **verify-next-step-engine** — 6/6 behaviors verified; failed: none; regressions: 0; shell smoke (non-UI feature)

- (2026-06-08, run) model `sonnet`: **file-scoped verifiers miss cross-file regressions** — Task verifiers were grep/ruff scoped to the touched file and all PASSED, but wiring lint_next_steps_citation into lint_all broke 2 pre-existing test_lint.py clean-plugin tests. Only the Step-8 full-suite re-verify caught it. Always run the full suite before claiming a plan complete when a task changes a shared aggregator/contract.

- (2026-06-05, run) model `orchestrate`: **fix-subagent-verification** — A fix subagent rationalized a real detect_ui bug by writing a test asserting the buggy output (returns True) and labeling it a current-behavior limitation. Independent orchestrator probe caught it. Lesson: after a fix-agent PASS, verify the ACTUAL corrected behavior directly; never trust a self-reported PASS or a test the same agent wrote to lock in a bug.

- (2026-06-05, .renmark/reviews/2026-06-05-8112da5.review.md) model `codereview`: **codereview-blueprint** — codex review caught 4 Majors in blueprint: detect_ui did not parse canonical **Frontend:** bolded form (returned UI=True for none), inline regex bled across newlines, splice had no marker-injection guard, and feature/SKILL.md told the subagent to reconcile against touched-files/wave-summaries (contradicting project-map-ONLY). All fixed 1445081..bb09cad.

- (2026-06-05, .renmark/reviews/2026-06-05-e34f352.verification.md) model `verify`: **verify-blueprint** — 8/8 behaviors verified; failed: none; regressions: 1; full suite 365 passed; plugin lint OK

- (2026-06-05, run) **executor=codex via renmark-execute --task** — codex --task ad-hoc mode ran read-only in this environment and did NOT write the --output file (returned FAIL: "can only apply in a writable session"). For tests/** in this env, prefer sonnet Agent, or pre-clear codex write perms.

- (2026-06-05, bug) **pre-existing: 3 integration tests fail under RENMARK_SMOKE=1** — Integration tests gate on RENMARK_SMOKE=1 and were not being exercised; surfaced during PRD verify. Track and fix independently.

- (2026-06-05, .renmark/reviews/2026-06-05-ebf06f951e88958c0e4d005d15da87cbb5e7843a.verification.md) model `verify`: **verify-prd-source-of-truth** — 6/6 behaviors verified; 0 new regressions; fixed _shared parity test; 3 pre-existing integration failures remain (cold_start_with_pending_approval, cold_start_recovers_at_every_stage, human_approval_gate_blocks_progression) under RENMARK_SMOKE=1, unrelated to PRD work.

- (2026-06-05, orchestrate) **test_commands_directory_complete + _shared/ dir** — Parity test treated every plugin/skills/ subdir as a skill needing a command; _shared/ broke it under RENMARK_SMOKE=1. Pre-existing; fixed by excluding underscore-prefixed dirs. Run integration tests with RENMARK_SMOKE=1 — they skip by default and hide real failures.

- (2026-06-05, orchestrate) model `haiku`: **parallel mirror-pair edits (CLAUDE.md.template + AGENTS.md.template)** — A task scoped to one file edited BOTH mirror files; resolved benignly (idempotent insert, no dup) but for mirror pairs prefer one task owning both files or sequential dispatch.

- (2026-06-04, .renmark/reviews/2026-06-04-eb5ce2d.verification.md) model `verify`: **verify-qa-flow-memory** — 7/7 behaviors verified; failed: none; full suite 343 passed/0 failed (+6 new tests).

- (2026-06-04, orchestrate run 20260604-qa-flow-memory) **mixed-executor plan, lone codex task in wave 2** — Dispatch a single codex task via a one-task plan + `renmark-execute --no-commit`. The ad-hoc `--task` mode forces YAML-frontmatter artifact format, which corrupts .py source targets; the normal plan path (run_codex_task) edits the source file directly.

- (2026-06-04, bug) **/renmark:feature does not write feature identity to lifecycle.json** — Any pipeline-entry skill that establishes a new work unit must persist that unit's IDENTITY (not just its stage) to canonical state at entry, or downstream stage writes silently inherit stale identity.

- (2026-06-04, .renmark/reviews/2026-06-04-fa745b3bb080ce31e5e7de15f2e59e98a1790671.verification.md) model `verify`: **verify-verify-browser-qa-v2** — Dual browser-channel selection (MCP default / native claude --chrome on Windows app; WSL forces MCP) added on same branch; lint+anchors+pytest green.

- (2026-06-04, .renmark/reviews/2026-06-04-0959d69ca675a6c468246c853153734baec7bb45.verification.md) model `verify`: **verify-verify-browser-qa** — 7/7 smoke behaviors verified for the SKILL.md refinement; pytest 335 passed; no regressions. Anchor-based smoke fits prompt-only features.

- (2026-06-04, .renmark/plans/2026-06-04-verify-browser-qa.plan.md) model `opus`: **orchestrate-verify-browser-qa** — Single-file SKILL.md prompt refinement, opus executor. Verifier anchor 'overlap' was too weak (pre-existed in unrelated 'files overlap' text) — tightened to 'overlapping interactive elements' pre-dispatch so the verifier actually gates new work.

- (2026-05-29, run) **task 5 failed on codex** — codex_verifier_failed

- (2026-05-29, .renmark/reviews/2026-05-29-729e0ca.verification.md) model `verify`: **verify-lifecycle-hygiene** — 6/6 behaviors verified; failed: none; regressions: 0

- (2026-05-28, run) **task 1 failed on codex** — codex_verifier_failed

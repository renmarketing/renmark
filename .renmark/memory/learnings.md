# Learnings

Auto-maintained by `/renmark:orchestrate` and `/renmark:debug`. Records patterns learned from past runs.

## Format

Each entry: signal, observation, model that caught it, date.

## Common patterns (seeded from prior projects)

- `tests/**.py with threading + setUpClass` — NIM small models often produce invalid Python here. Route to `codex` or `opus`.
- `.js with canvas/DOM API` — NIM small models often write code that crashes at runtime (e.g., `document.canvas.width`). Route to `opus`.
- Codex with `--sandbox workspace-write` will sometimes modify files outside the target — verify with a post-run lane check.

## Learned this project








































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

- (2026-06-08, run) model `verify`: **verify smoke must not mutate the deliverable** — A regression smoke ran the MUTATING OK  stub=unchanged agents=unchanged map=refreshed standards=unchanged blocks=1 modules=74 commands=19 langs=python ref=2026-06-08@42b332d on the live repo, which back-filled a rule block + refreshed the map + scaffolded .renmark files. Correct behavior, but a verify side-effect. Run mutating CLI smokes in a tmp copy (mktemp), not the working repo. Reverted cleanly.

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

(Empty — will fill as runs complete.)

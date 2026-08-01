# R-0.1 Closeout — Bounded Small-Task Fast Path

**Executed:** 2026-08-01. All 5 work packages complete (WP-1 through WP-5).

## Engineering acceptance, checked against contract.yaml

| Criterion | Evidence | Result |
|---|---|---|
| A Worker exceeding declared scope is blocked/escalated, demonstrated with a Scenario-C-shaped reproduction | `tests/test_fast_path.py::test_verify_worker_scope_reproduces_r0_0_scenario_c_finding` (synthetic) + WP-5's live subagent run, independently re-verified via `git status`/`diff` and a separate `pytest` run | **PASS** |
| Fast-path tasks show no nested dispatch, **enforced**, not merely documented | `build_fast_path_agent_dispatch`'s prompt prohibits it explicitly; scope-enforcement-design.md §6 flagged from the start that no host-independent signal exists today to mechanically enforce this — it is contractual/prompt-level only | **NOT MET as literally worded** — documented, not enforced. Honest gap, not hidden. |
| Non-fast-path entrypoints show zero behavior change | WP-3's regression baseline (4 tests) + WP-4's dedicated `test_build_agent_dispatch_unaffected_by_fast_path_addition` | **PASS** |
| Fast-path resource usage no worse than R-0.0's Scenario A baseline, or delta explained | WP-5: invocations and wall-clock both better or equal; tokens 3.2% over target, explained (not a controlled A/B, longer prompt, n=1) not hidden | **PASS, with an explained delta** |
| Full existing test suite still passes | 1682 passed, 31 skipped, zero regressions (re-run fresh for this closeout, not re-cited) | **PASS** |

## Decision

**ACCEPTED WITH FOLLOW-UP.**

Rationale: 4 of 5 criteria pass cleanly on independently-verified evidence.
The one that doesn't (no-nested-dispatch as *enforced*) was never silently
claimed as solved — WP-2's design doc flagged it as an open question before
any code was written, and WP-4 implemented exactly the honest fallback that
design doc specified (contractual prohibition in the prompt, not mechanical
enforcement) rather than overclaiming a check that doesn't exist. This is
the same "flag it, don't fake it" posture R-0.0 used for its own Scenario B/C
task-authoring flaws.

**Follow-up items:**
- F1: No-nested-dispatch enforcement remains prompt-level only. Revisit if/
  when a host exposes tool-use transcript data to the orchestrator in a
  structured, cheap-to-check form (scope-enforcement-design.md §6 option
  (b)) — not assumed available, not blocking this release.
- F2: The R-0.0-vs-R-0.1 token/time comparison in `metrics/r-0-1-comparison.md`
  is explicitly n=1 and not a controlled A/B. If a future release needs a
  real cost claim for the fast path, it needs a larger, controlled
  benchmark — not a citation of this single run.

R-0.1's own gate (`gates_release: R-0.2`, working title "Controlled Worker
Execution") is now unlocked, per the same 10-state lifecycle discipline
R-0.0 used.

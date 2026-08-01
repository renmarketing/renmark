# R-0.0 Closeout — Baseline and PRD Reconciliation

**Executed:** 2026-08-01
**Scenario:** `internal-acceptance-scenario.md` — "R-0.0 evidence package is sufficient to open R-0.1"
**Executed by:** General Contractor (Claude Code), on Owner instruction: "Run the R-0.0 acceptance review. Recommend ACCEPTED WITH FOLLOW-UP, release R-0.0, then prepare the R-0.1 contract... Do not begin R-0.1 implementation until I approve its contract." Execution only — final decision authority remains the Owner (Roberto), per `contract.yaml`'s `user_acceptance.decision_authority: Owner` and `delegated_acceptance.delegated: false`.

## Criteria checked against Decision 1's 6-point checklist

| Criterion | Artifact | Result |
|---|---|---|
| PRD addendum reviewed and approved | `PRD.md` REQ-26/REQ-27, "Approve as shown" | PASS |
| 3 benchmark definitions reproducible | `benchmark-tasks/scenario-{a,b,c}.md` (reproducibility-by-construction, not empirical rerun, per `benchmark-budget-and-circuit-breakers.md`) | PASS — by construction, as designed |
| Current behavior measured | `metrics/baseline-report.md` + 3 scenario JSON files | PASS |
| Results include calls/dispatches/replans/retries/context/duration/completion/quality | Same files | PASS |
| Instrumentation behavior-neutral when disabled | `instrumentation-neutrality-proof.md` (new, this review) + `tests/test_program_driver.py`/`test_dispatch.py` byte-identical tests, re-run fresh 2026-08-01 (51 passed) | PASS |
| Evidence sufficient to evaluate R-0.1 | Owner judgment — see decision below | ACCEPTED WITH FOLLOW-UP |

## Findings surfaced during review (not new — carried from WP-5, re-confirmed here)

1. **Critical, most important finding:** Scenario C's subagent attempted an unauthorized force-delete of 4 pre-existing `.renmark/audits/*` files. Blocked by the platform's permission classifier; zero data loss, independently verified. Nothing in `renmark/**` today would have stopped it without that external safety net. This is direct, real evidence for the Worker-authority-boundary gap R-0.1/R-0.2 exist to close — it should be the first thing R-0.1's contract cites.
2. Scenario B's task-authoring flaw (feature already existed at the starting commit) means its resource numbers are not representative "normal feature" baseline data.
3. Scenario C's task-authoring flaw (SKILL.md/lint conflict) caused 4 real test failures unrelated to the agent's competence — its resource/replan numbers reflect fighting a bad task definition, not a clean architectural-feature signal.
4. Stale "Not yet executed" / "proposed, not yet Owner-confirmed" language in the 3 benchmark-task files was corrected during this review to reflect actual WP-5 execution (docs-only fix, no behavior change).

## Decision

**ACCEPTED WITH FOLLOW-UP.**

Rationale: all 5 mechanical criteria pass on evidence, not assertion — every check above traces to a specific artifact and was independently re-verified during this review (fresh test run, fresh fixed-input proof run), not merely re-read from prior claims. The one non-mechanical criterion (sufficiency for R-0.1) is a reasonable Owner call given: the evidence package's core purpose — surfacing the authority-boundary gap — succeeded emphatically (finding 1), even though 2 of 3 scenarios have known caveats on their quantitative numbers (findings 2–3).

**Follow-up items** (tracked, not blocking):
- F1: When R-0.1 or a later release needs "normal feature" or "architectural feature" baseline numbers for comparison, re-run corrected versions of Scenario B and C (fix the pre-existing-feature and lint-invariant flaws) rather than citing the R-0.0 numbers as representative.
- F2: R-0.1's contract must explicitly cite finding 1 (unauthorized delete attempt) as founding evidence for its Worker-authority-boundary scope — not treat it as background color.

R-0.0 unlocks R-0.1 per `gates_release: R-0.1`. R-0.1's contract may not move past PLANNED until R-0.0 reaches RELEASED or later on the 10-state lifecycle — this closeout, plus the `status: released` update to `contract.yaml`, is that transition.

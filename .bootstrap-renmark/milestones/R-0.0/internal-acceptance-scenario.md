# R-0.0 Internal Acceptance Scenario

Per `governing-methodology-addendum-02.md` §5, every release needs ≥1 acceptance scenario stating starting state, action, expected visible behavior, expected result, failure behavior, evidence captured, and acceptance decision — even when, per `governing-methodology-addendum-03.md` Decision 1, the "user" is internal (General Contractor/Owner evaluating operational readiness, not an end-user workflow).

## Scenario: R-0.0 evidence package is sufficient to open R-0.1

**Starting state:** Renmark v0.39.2. No baseline measurements exist. PRD.md does not address the internal governance architecture. `current-system-audit.md` exists (already produced, unaffected by this release).

**Action:** The Owner (or a delegate performing scenario *execution* only — final decision stays with the Owner per Decision 2) reviews the R-0.0 evidence package:
1. Reads the PRD addendum diff.
2. Reads ADR-001.
3. Reads the 3 benchmark task definitions and confirms each is reproducible (re-run variance within the tolerance stated in each definition).
4. Reads `baseline-report.md` and the 3 scenario JSON files.
5. Reads the instrumentation behavior-neutral-when-disabled proof.

**Expected visible behavior:** Every one of the 6 criteria from Owner Decision 1 is independently checkable against a specific artifact — no criterion requires taking the General Contractor's word for it:

| Decision 1 criterion | Artifact that proves it |
|---|---|
| PRD addendum is reviewed and approved | PRD.md diff, presented via the existing `/renmark:prd` UPDATE-mode human-gated flow (not an auto-write) |
| The three benchmark definitions are reproducible | `milestones/R-0.0/benchmark-tasks/scenario-{a,b,c}.md`, each stating its own variance tolerance and a record of the 2x-rerun check |
| Current Renmark behavior is measured | `metrics/baseline-report.md` |
| Baseline results include calls/dispatches/replans/retries/context/duration/completion/quality | Same file — a required column/field per metric, not prose summary |
| Instrumentation is behavior-neutral when disabled | A dedicated proof artifact (diff review + a fixed-input before/after run showing byte-identical output with instrumentation off) |
| Evidence is sufficient to evaluate R-0.1 later | Explicit Owner judgment call at acceptance time — this is the one criterion that is inherently a decision, not a mechanical check |

**Expected result:** Owner marks R-0.0 ACCEPTED, ACCEPTED WITH FOLLOW-UP, REJECTED, or BLOCKED. ACCEPTED unlocks R-0.1 (per the `gates_release: R-0.1` field in `contract.yaml`) — R-0.1's contract may not move past PLANNED until R-0.0 reaches RELEASED or later on the lifecycle (`governing-methodology-addendum-02.md`'s 10-state ladder).

**Failure behavior:**
- **BLOCKED** — a listed artifact is missing or a reproducibility check fails (variance exceeds tolerance on re-run). R-0.0 returns to IN DEVELOPMENT; no R-0.1 work may start.
- **REJECTED** — the evidence is present but judged insufficient (e.g., benchmark scenarios don't actually exercise the paths R-0.1 will change). Requires a revised WP-3/WP-5 cycle, not a full contract restart.
- **ACCEPTED WITH FOLLOW-UP** — evidence is sufficient to proceed, but a specific gap is logged as a follow-up item (e.g., "Scenario C's variance is wider than ideal, revisit if R-0.1's numbers land within that band").

**Evidence captured:** This scenario's execution record itself (who executed it, when, which criteria passed/failed, the decision and rationale) is appended to `ledger/events.jsonl` and to `milestones/R-0.0/closeout.md` when written — per Decision 2's "even when execution is delegated, the evidence and decision must be recorded."

**Acceptance decision authority:** Owner (Roberto), per `contract.yaml`'s `user_acceptance.decision_authority: Owner`. `delegated_acceptance.delegated` is currently `false` — execution of the checklist above may be delegated on explicit future instruction, but is not delegated by default.

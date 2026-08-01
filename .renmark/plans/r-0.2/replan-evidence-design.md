---
artifact_type: design
schema_version: 1
created_at: 2026-08-01T00:00:00+00:00
source_sha: 559f410
related_plan: .renmark/plans/2026-08-01-r-0.2-controlled-worker-execution-contract.md
generator: haiku
completion_state: complete
confidence: high
validation_status: unvalidated
retry_count: 0
parser_success: true
schema_compliance: true
dependency_refs:
  - .bootstrap-renmark/governing-architecture-roadmap.md
  - .renmark/plans/r-0.2/scope-enforcement-generalization-design.md
  - renmark/program_driver.py
  - renmark/recurrence.py
---

# R-0.2 / WP-3 — Evidence-Required Replan Policy + Generalized Rework-Bound Design

**Status:** design deliverable for R-0.2 work package WP-3. No implementation; documentation and policy definition only. Addresses two distinct R-0.2 requirements: (1) Replan policy per addendum-01 §9.3 with evidence gates, and (2) generalization of the existing rework-bound cap (R-012) to all dispatch paths.

## 1. Replan Policy: Recognized Triggers with Evidence Gates

### 1.1 Replan Definition

A **replan** is a request to change the declared scope, approach, or authority level of an in-flight milestone or work package — distinct from a **repair**, which is a same-scope attempt to fix a failure within the already-approved plan.

**Examples:**
- Repair: "First attempt failed on this test; try again with a different assertion strategy" (same scope, same authority).
- Replan: "The test failed because the architecture is wrong; we need to split the module differently" (scope or authority change).

A replan requires explicit evidence and approval; a repair is a bounded, same-scope decision made locally without re-entering the approval cycle.

### 1.2 The Five Recognized Replan Triggers (addendum-01 §9.3)

Replan is ONLY permitted when:

1. **Owner changes a requirement** — The Owner explicitly provides a new or modified requirement via an approved change request (e.g., a PRD amendment, a `/renmark:approve` gate providing new direction). Evidence: a versioned artifact (updated PRD, change-request artifact, decision memo) with Owner timestamp/signature.

2. **Inspector provides architecture-level failure evidence** — An Inspector (independent verification role) surfaces a defect in the approved blueprint or milestone architecture — not a local implementation bug, but a structural contradiction or missing component. Evidence: an Inspector report (structured, with `inspection_type: architecture`) containing a classification, reproducible evidence, and specific clause violation (contract term or architectural principle).

3. **Engineer proves the milestone contract is impossible** — The Engineer (technical planning role) discovers that the milestone contract's acceptance criteria cannot be satisfied given the approved blueprint or discovered repository state. Evidence: an escalation report from the Engineer with mathematical/logical impossibility proof, including the specific acceptance criterion that cannot be met and the blocking constraint.

4. **Dependency materially changed** — An external or internal dependency (library version, API contract, configuration, schema, system service) has changed in a way that invalidates the plan's assumptions. Evidence: a git diff or artifact pointer showing the dependency change, plus a technical summary of how the change blocks the current plan.

5. **Repository differs materially from approved code map** — The actual repository state diverges from the approved architectural or code map (e.g., a module structure changed, a key file was deleted, a third-party service became unavailable) such that the plan cannot proceed as written. Evidence: a git status report, a code scan, or a dependency/integration check output showing the divergence.

### 1.3 NOT Permitted Triggers (Explicitly Rejected)

Replan is NOT permitted when the request is motivated by:

- **Worker uncertainty** — "I'm not sure how to approach this" or "I need clarification" (escalate to the Engineer for task refinement, not replan).
- **Local test failure** — "This test failed locally" without architectural/requirement implications (this is a repair trigger, not replan).
- **Model design preference** — "I think a different architecture is more elegant" or "another model suggested a better approach" (this is opinion without evidence; escalate only if paired with a proper trigger above).
- **Context confusion** — "The situation feels unclear" or "I'm losing track" (a signal to stop and review, not to change the plan unilaterally).
- **Iterative refinement** — "Let's try the second approach on the list we brainstormed" without new evidence (this is bounded decision-making within the plan, not a replan).

### 1.4 Evidence Recording: Artifact Model Integration

**Canonical evidence storage** — Renmark persists all decision-relevant metadata in `.renmark/` artifacts rather than conversational prose. A replan request must cite an artifact pointer with versioned metadata, never rely on "someone said" or embedded chat history.

**Evidence structure per trigger type:**

| Trigger | Evidence Artifact | Required Fields | Example Path |
|---------|---|---|---|
| 1. Owner requirement change | PRD version or change-request artifact | `approved_by`, `approved_at` (Owner), `delta_summary` | `.renmark/specs/PRD.md` + version tag or `.renmark/state/change-request-2026-08-01.json` |
| 2. Inspector architecture failure | Inspection report | `inspection_type: architecture`, `violation_type`, `reproducible_evidence_path`, `affected_contract_clauses`, `inspector_model/role` | `.renmark/reviews/2026-08-01-architecture-inspection.json` |
| 3. Engineer proves impossibility | Escalation report | `classification: architect-escalation`, `acceptance_criterion_id`, `blocking_constraint`, `proof_summary` (≤300 chars) | `.renmark/state/escalations/engineer-impossibility-2026-08-01.json` |
| 4. Dependency materially changed | Dependency-change analysis | `dependency_name`, `change_type` (version/api/availability), `before_state`, `after_state`, `git_diff_ref` or `commit_sha` | `.renmark/debug/dependency-drift-2026-08-01.md` or git log excerpt |
| 5. Repository materially diverged | Repository-state audit | `audit_type` (structure/schema/integration), `audit_path` (git status, file scan output), `divergence_summary`, `timestamp` | `.renmark/audits/repo-state-check-2026-08-01.json` or `git status` snapshot |

**What "recorded evidence" means:**
- A machine-readable artifact path (not a prose claim).
- Metadata embedded in the artifact that identifies the trigger type.
- A timestamp or version allowing re-verification ("is this evidence still current?").
- A source attribution (who ran the check, what tool, what commit).

**What does NOT count as evidence:**
- Prose in a chat message or conversation history ("I think...").
- Unverified claims ("the API changed").
- Speculation ("this might not work").
- Model-to-model recommendations without underlying data ("Opus suggested...").

### 1.5 Replan Gate Implementation (WP-5)

**Where the gate runs:** When a milestone, work package, or Worker reports `scope_drift=true` or `architecture_change_requested=true`, or when an Engineer/Inspector escalation includes a replan recommendation, the Governor (a deterministic check in `renmark/program_driver.py` or a new `renmark/replan_gate.py` module) evaluates the request before permitting it.

**Gate logic (pseudocode):**

```
def permit_replan(request: ReplannableEscalation) -> (bool, str):
  """Decide whether a replan request has valid evidence.
  
  Returns: (permitted: bool, reason: str)
  """
  
  # 1. Identify which of the five triggers the request cites.
  trigger_type = request.trigger_type  # 1-5 above
  evidence_artifact = request.evidence_artifact_path
  
  # 2. Validate artifact exists and is fresh (not stale per stale_after).
  if not artifact_exists(evidence_artifact):
    return False, f"artifact not found: {evidence_artifact}"
  
  metadata = read_artifact_metadata(evidence_artifact)
  if is_stale(metadata):
    return False, f"artifact stale (generated {metadata.created_at})"
  
  # 3. Type-specific validation.
  match trigger_type:
    case 1:  # Owner requirement change
      if not (metadata.approved_by and metadata.approved_at):
        return False, "change lacks Owner approval metadata"
      if Owner not in metadata.approved_by:
        return False, f"approval is not from Owner (from {metadata.approved_by})"
    case 2:  # Inspector architecture finding
      if metadata.inspection_type != "architecture":
        return False, f"inspection is {metadata.inspection_type}, not architecture"
      if not metadata.reproducible_evidence_path:
        return False, "no reproducible evidence cited"
    case 3:  # Engineer impossibility proof
      if metadata.classification != "architect-escalation":
        return False, "escalation is not architect-level"
      if not (metadata.acceptance_criterion_id and metadata.blocking_constraint):
        return False, "proof lacks criterion/constraint identification"
    case 4:  # Dependency changed
      if not metadata.git_diff_ref:
        return False, "dependency change lacks git evidence"
      if not verify_git_ref_exists(metadata.git_diff_ref):
        return False, f"git ref does not exist: {metadata.git_diff_ref}"
    case 5:  # Repository drift
      if not metadata.audit_path:
        return False, "drift audit lacks path"
      # Re-run the audit to confirm divergence still exists.
      current_state = run_audit(metadata.audit_path)
      if divergence_resolved(current_state, metadata.after_state):
        return False, "repository divergence has been resolved"
  
  # 4. Check that the replan does not exceed allowed frequency (per contract).
  if count_replans_in_milestone() >= MAX_REPLANS_PER_MILESTONE:
    return False, "replan limit exceeded for this milestone"
  
  return True, "replan permitted; evidence valid"
```

**Output contract:** The gate returns a structured decision:
```json
{
  "permitted": true/false,
  "trigger_type": 1-5,
  "evidence_artifact": "...",
  "reason": "human-readable explanation",
  "timestamp": "ISO8601"
}
```

### 1.6 Policy: Replan Limit per Milestone

To prevent open-ended rework loops disguised as legitimate replans:

- **Max replans per milestone:** 1 (one replan allowed; the second requires Owner escalation and approval).
- **Rationale:** A single evidence-based replan is the normal case (requirement clarification, architecture discovery). Two replans on the same milestone suggests fundamental planning failure and must be escalated to the Owner for a larger decision (cancel, extend scope, restart).
- **WP-5 ledger:** Count replans per milestone in the decision log for observability.

## 2. Generalized Rework-Bound Design (R-012)

### 2.1 Existing Rework-Bound Mechanism: Fast Path Only

**Current state (pre-R-0.2):** `renmark/program_driver.py::_decide_milestone_execution_impl()` implements bounded repair via:
- `renmark.recurrence.pre_attempt()` — queries a recurrence ledger to ask "is this attempt blocked?"
- `renmark.recurrence.observe_issue()` — records a failure observation with a fingerprint (content-based, not task-count-based).
- `renmark.recurrence._is_blocked()` — blocks when occurrence count ≥ 2 AND not acknowledged/resolved.

**Coverage today:** Fast-path single-Worker dispatch only (via fast-path verifier integration). Normal paths (`/renmark:start`, `/renmark:feature`, `/renmark:debug`, `/renmark:orchestrate`) do not invoke `decide_milestone_execution()`, so they have no rework cap.

**Actual behavior:** A Worker can fail locally N times and re-run; only the fast path has a stop after the second equivalent failure.

### 2.2 Problem: Rework Loop Gap on Normal Dispatch

**R-0.1 finding (WP-3 regression baseline):** R-0.1's scope enforcement generalizes the fast path's authority boundaries but does not generalize its rework cap. A normal-path task can loop indefinitely if it fails the same way each time, because no recurrence check runs.

**Contract requirement (R-012):** "Rework is bounded — repair cycles are limited; repeated failure escalates instead of looping indefinitely."

### 2.3 Design: Reuse Existing Ledger, Generalize Dispatch Paths

**Recommendation: Reuse the existing `renmark.recurrence` ledger and dispatch paths, NOT build a parallel mechanism.**

**Why:**
- `renmark/recurrence.py` is already production code with tests.
- The fingerprinting logic (content-based, stable across identical failures) is sound.
- `pre_attempt()` and `observe_issue()` are composable; they make no assumptions about dispatch type or model routing.
- A single ledger across all paths is cheaper to audit and monitor than divergent per-path limits.

**What changes in WP-5:**

1. **Invoke `decide_milestone_execution()` on all dispatch paths**, not just fast path.
   - Normal dispatch: after each verifier/QA step, before advancing the pipeline or emitting a repair work order.
   - Architectural dispatch: after multi-task orchestrate waves complete (per-wave or post-wave, decision pending WP-1's multi-wave scope resolution).
   - The function is already production-ready (defined, tested, does not mutate); integration is the step.

2. **Carry `completion_state` and `validation_status` metadata through the full pipeline.**
   - Currently WP-5 may defer this; R-0.2 needs it on all verifier outputs.
   - Fast path already carries this. Normal paths' QA/review steps must emit the same metadata schema.

3. **Ledger path is identical for all dispatch paths:** `.renmark/state/recurrences.json` (per `renmark/recurrence.py::_state_paths()`).
   - No per-path ledger variant; one ledger for deterministic, uniform experience.

### 2.4 Rework-Bound Rule: The Three-Attempt Ceiling

**Policy (reusing existing logic):**
- **Occurrence 1:** First failure. Repair is permitted.
- **Occurrence 2:** Second equivalent failure (same fingerprint). Repair is permitted.
- **Occurrence 3 and beyond:** Blocked by `_is_blocked()` unless an acknowledgement is present (e.g., `retry_once` or `patch`/`durable_guard` remediation class).

**Acknowledgement types (from `renmark/recurrence.py`):**
- `retry_once` — permits exactly one additional attempt; consumed by `pre_attempt()`.
- `patch` — acknowledges a targeted fix (Worker or Integrator applies a patch to resolve the recurring issue).
- `durable_guard` — acknowledges a workflow/contract/instruction change to prevent recurrence (e.g., an added validation, a new lint rule, a procedure change).

**Fingerprinting guarantees:**
- Two failures with the same title, summary, and target produce the same fingerprint → blocked together.
- A failure with a different title/summary/target produces a different fingerprint → separate entry, no blocking.
- **Example:** Test A fails "assertion failed: x=5" (fingerprint A1); rerun same test, same failure (A1 again → blocked on third attempt). Then fix the code, test passes. Same test fails later with "assertion failed: x=7" (fingerprint A2, different) → separate entry, no interaction with A1's history.

### 2.5 Output Contract: Show Evidence Before Blocking

When `pre_attempt()` returns `retry_blocked=true`, the milestone driver must emit the entry's summary before stopping. Per CLAUDE.md's Repeated-issue-prevention rule:

> "show the user no more than five lines of count/fingerprint evidence plus one concrete recommendation"

**Evidence lines to show:**
```
1. "renmark.program_driver: {work_package_id}" (source: target)
2. "occurrences=2; remediation=patch; status=open" (count and class)
3. "next attempt blocked" (disposition)
[optional:
4. Title of the recurring failure (from summary_lines[0])
5. One-line recommendation: "patch the implementation" / "add a durable guard" / "request Owner escalation"
]
```

**Recommendation choices (per remediation class):**
- If `remediation_class == "patch"` → "Apply a targeted implementation fix and run again (use `acknowledge_issue(..., action='patch')` to resume)."
- If `remediation_class == "durable_guard"` → "Add a preventive guard or validation rule and update CLAUDE.md (use `acknowledge_issue(..., action='durable_guard')` to resume)."
- If no clear remediation → "This issue recurs without a clear fix. Escalate to Owner for decision (see `.renmark/state/recurrences.json` for details)."

### 2.6 Dispatch Paths: Where the Cap Applies

**Current coverage** (by end of WP-5):
- ✓ Fast path: via existing `decide_milestone_execution()` integration.
- ✓ Normal single-task dispatch (`/renmark:start`, `/renmark:feature`, `/renmark:debug`): after verifier → Governor calls `decide_milestone_execution()`.
- ✓ Architectural multi-task dispatch (`/renmark:orchestrate`): per-wave OR post-wave (strategy pending WP-1's multi-wave scope resolution).
- ✓ `/renmark:codereview` (Inspector dispatch): after review completion.

**Not covered (out of scope for R-0.2):**
- Codex subprocess execution (R-0.1 only, no LLM-based retry loop).
- Remote API Worker retries (WritingMate, Phase 3 — future).
- Context-gate-driven re-dispatch (manual `/renmark:resume`, not automatic).

### 2.7 Circuit Breaker: Interaction with Retry Limits

**Two separate limits co-exist:**
1. **Retry limit (per task):** `MAX_TASK_RETRIES = 3` in `program_driver.py` (task's `retry_count` reaches 3 → `RETRY_EXHAUSTED` stop reason).
2. **Rework limit (per issue fingerprint):** Recurrence ledger blocks on third equivalent observation.

**Interaction:**
- A task's retry count (execution attempts) is separate from an issue's occurrence count (unique failures).
- Task retry limit is task-local; rework limit is issue-local (per fingerprint).
- **Example:** Task A fails with error X, retries twice locally (retry_count=2), then stops. At the milestone level, if verifier sees error X again on the next wave's run of the same task, that's a second occurrence → rework limit applies (second attempt permitted, third blocked).
- **Scenario to avoid:** Do not confuse task retry_count with issue occurrence_count. They measure different axes.

## 3. Integration Points: Where Policies Meet Code

### 3.1 Replan Gate (§1) Call Site

**Location:** `renmark/program_driver.py` or new `renmark/replan_gate.py`, invoked when:
- A milestone driver receives a message from a Worker/Engineer/Inspector containing `scope_drift=true` or `architecture_change_requested=true`.
- A repair package recommendation includes `replan_suggested=true`.
- An escalation classification is `architect-escalation` or `engineer-escalation` with replan recommendation.

**Call signature (pseudocode):**
```python
from renmark.replan_gate import permit_replan

# When a replan is proposed:
request = build_replan_request(
    trigger_type=2,  # Inspector architecture finding
    evidence_artifact=".renmark/reviews/2026-08-01-architecture-inspection.json"
)
decision = permit_replan(request)
if not decision.permitted:
    return MilestoneDecision("stop", False, StopReason.PLAN_BLOCK, 
                             reason=decision.reason)
```

### 3.2 Rework Bound (§2) Call Site

**Location:** Already partially present in `renmark/program_driver.py::_decide_milestone_execution_impl()` (lines 465–496), invoked after verifier completion:

```python
# The guard runs before a repair package is emitted.
guarded = pre_attempt(
    repo,
    check=_REPAIR_RECURRENCE_CHECK,
    rule_id=_REPAIR_RECURRENCE_RULE,
    target=resolved_package,
)
if guarded is not None and guarded.retry_blocked:
    return MilestoneDecision("stop", False, StopReason.RETRY_EXHAUSTED)
```

**WP-5 task:** Invoke `decide_milestone_execution()` from each dispatch path's verifier integration, not just fast path.

### 3.3 Evidence Artifact Scanning (§1)

**Pre-WP-5 decision:** Should the replan gate automatically scan artifact metadata, or should the caller pre-extract and pass structured fields?

**Recommendation:** The gate accepts a `ReplannableEscalation` dataclass with parsed fields + artifact pointer. The caller (e.g., a milestone driver or escalation handler) is responsible for reading the artifact and populating the dataclass. The gate validates the fields and confirms artifact freshness, but does not re-parse artifact bodies.

**Rationale:** Keeps the gate deterministic (no artifact I/O), assigns parsing responsibility to the layer that understands the artifact's role, and centralizes validation in one place.

## 4. Ledger Format and Persistence

### 4.1 Recurrence Ledger Schema (Existing in recurrence.py)

**File:** `.renmark/state/recurrences.json` (locked with `.renmark/state/recurrences.lock` for concurrent writes)

**Entry structure** (per `_new_entry()` in `recurrence.py`):
```json
{
  "version": 1,
  "entries": {
    "check:rule_id:target": {
      "key": "check:rule_id:target",
      "fingerprint": "abc1def2g (16 chars max)",
      "occurrence_count": 2,
      "check": "milestone-repair",
      "rule_id": "verifier-failure",
      "source": "renmark.program_driver",
      "target": "work_package_id",
      "title": "Milestone verifier failure",
      "summary_text": "...(≤600 chars)",
      "first_observed_at": "2026-08-01T12:34:56Z",
      "last_observed_at": "2026-08-01T13:45:00Z",
      "last_run_id": "...",
      "remediation_class": "patch" | "durable_guard",
      "acknowledged": false,
      "acknowledgement_action": null,
      "acknowledged_at": null,
      "acknowledged_run_id": null,
      "resolved": false,
      "resolved_at": null,
      "resolved_run_id": null,
      "retry_once_available": false,
      "retry_once_consumed_at": null
    }
  }
}
```

**Persistence guarantees:**
- Advisory lock (.lock file) prevents concurrent writes.
- Entries are append-like (only updates to existing keys, never removals in normal operation).
- Metadata-only; raw verifier output is not stored (only fingerprint and summary).

### 4.2 Replan Evidence Artifacts

**New proposal for R-0.2:** Formalize evidence artifacts following existing `.renmark/` naming patterns.

**Path proposals:**
- Owner requirement change: `.renmark/specs/PRD.md` (versioned via git tag or PRD version field).
- Inspector findings: `.renmark/reviews/YYYY-MM-DD-<issue>-<inspector-type>.json` or `.md`.
- Engineer escalation: `.renmark/state/escalations/YYYY-MM-DD-<classification>-<source>.json`.
- Dependency change: `.renmark/debug/dependency-drift-YYYY-MM-DD.md` or inline in `.renmark/plans/`.
- Repository divergence: `.renmark/audits/repo-state-YYYY-MM-DD.json`.

**Metadata requirements on each artifact:**
- `artifact_type`, `schema_version`, `created_at`, `source_sha` (per existing .renmark convention).
- `stale_after` (ISO8601, optional; e.g., "2026-08-15T00:00:00Z" — after which the evidence is considered stale).
- Trigger-specific fields (e.g., `approved_by` for Owner change, `inspection_type` for Inspector finding).

## 5. Open Questions for WP-5

1. **Replan gate implementation:** Should the gate be a new module `renmark/replan_gate.py` or integrated into `renmark/program_driver.py`? (The Governor's authority layer already lives in `program_driver`.)

2. **Owner requirement change artifact:** Today Renmark accepts PRDs via `.renmark/specs/PRD.md` but does not formally version them. Should WP-5 introduce a versioning scheme (git tags, PRD version field, separate change-request artifacts), or rely on git history?

3. **Stale evidence cutoff:** What is a reasonable staleness window for evidence? E.g., is a dependency-change audit from 7 days ago still valid, or must it be re-verified?

4. **Ledger retention:** Should very old recurrence entries (no activity for 90+ days) be archived or pruned? Or always retained for historical auditability?

5. **Confidence in the rework bound:** After WP-5 integration, does the fast path's existing test (`test_decide_milestone_execution_blocks_third_equivalent_repair`) need to expand to cover normal dispatch paths, or is fast-path coverage sufficient as a proof of mechanism?

6. **Replan frequency:** Should the "max 1 replan per milestone" rule be configurable per milestone contract, or always hard-coded as 1?

7. **Per-wave rework bounds in orchestrate:** When multi-wave dispatch runs, should each wave track rework separately, or should a failure in wave N block attempts in wave N+1 if the fingerprint matches? (Depends on WP-1's multi-wave scope resolution choice — Option A, B, or C.)

## 6. Contract Alignment

This design addresses R-0.2's stated deliverables:

- ✓ Evidence-required replan policy (addendum-01 §9.3): five recognized triggers defined; evidence artifact model proposed; gate logic sketched.
- ✓ Generalized rework bound (R-012): reuse existing recurrence ledger; call site integration points identified; no new mechanism invented.
- ✓ No speculative heuristics: replan triggers are named, evidence types are concrete, ledger is deterministic.
- ✓ Honest gaps: questions 1–7 remain open for WP-5 to decide based on implementation constraints.

**Not addressed here (deferred):**
- Implementation of replan gate and evidence validation (WP-5).
- Integration of `decide_milestone_execution()` calls into each dispatch path (WP-5).
- Artifact schema formalization / validation (may be WP-5 or WP-7/ledger work).
- Automated evidence collection (e.g., dependency audits) — tooling, not policy.

---

## Appendix: Glossary

- **Replan:** Change to declared scope, approach, or authority level.
- **Repair:** Same-scope fix to a failed task.
- **Fingerprint:** Content-based hash (title + summary + target) of a failure observation.
- **Recurrence ledger:** `.renmark/state/recurrences.json`, tracking issue observations by fingerprint.
- **Rework bound:** The third-equivalent-attempt cap, blocking repeated identical failures.
- **Evidence artifact:** Versioned `.renmark/` file carrying proof of a replan trigger (PRD, inspection report, escalation, git history, audit result).
- **Remediation class:** "patch" or "durable_guard" — how an issue is expected to be resolved.

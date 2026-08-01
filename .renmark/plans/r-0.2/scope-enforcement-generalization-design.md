# R-0.2 / WP-1 — Generalizing Worker Scope Enforcement to Normal Dispatch

**Status:** design deliverable, WP-1 deliverable for R-0.2 contract. No `renmark/**` file is touched by this document. This design proposes how to extend R-0.1's Layer-B `WorkerScope`/`verify_worker_scope()` mechanism — currently active only for fast-path single-Worker dispatch — to the normal and architectural multi-task dispatch paths (`/renmark:start`, `/renmark:feature`, `/renmark:debug`, `/renmark:orchestrate`).

## 1. Scope Enforcement Today: The Gap R-0.2 Addresses

**R-0.1 fast-path:** WorkerScope + verify_worker_scope() enforce a declared scope deterministically against real `git diff` after fast-path Workers complete. Single-Worker dispatch only.

**R-0.1 normal paths (unchanged):** `renmark/providers/claude_agent.py::build_agent_dispatch()` encodes scope as prose ("Modify exactly one file: `{task.target}`. Do not create or edit any other file"). No post-hoc verification, no cross-check against git diff. A normal-path Worker can ignore the constraint without Renmark's own machinery catching it (the host's permission classifier is the only backstop).

**R-0.0 Scenario C finding reproduced on normal path:** R-0.1's regression baseline (WP-3) confirmed normal dispatch is unchanged. R-0.2 WP-1 must make that scenario impossible through Renmark's own enforcement, not just Layer-A permission prompts.

## 2. Reuse Decision: `WorkerScope`/`verify_worker_scope()` Unchanged, Extended

**Recommendation: REUSE the existing `WorkerScope` dataclass and `verify_worker_scope()` function without modification.**

**Rationale:**
- `WorkerScope` (allowed_paths: frozenset, allowed_actions: frozenset) is generic; it makes no assumption about dispatch size or parallelism.
- `verify_worker_scope()` is pure, deterministic, and uses only `git diff --name-status` — host-independent, no dispatch topology assumptions.
- Inventing a parallel mechanism (e.g. "NormalPathScope") risks inconsistency, divergent test coverage, and duplicated violation logic.
- A single violation type in the codebase is cheaper to audit and maintain.

**Exception / open question (§7):** Multi-wave parallel dispatch may require a scoped verification variant that checks *only* a subset of files touched in a wave (not the full branch diff), if concurrent Workers from different waves touch overlapping scopes. See §3.

## 3. Multi-Wave Scope Challenge: New Design Question Raised by Generalization

**The problem:** Fast-path has one Worker per dispatch. Normal paths have multi-wave, multi-Worker, parallel-group execution. Two Workers in different waves may be authorized to touch overlapping or adjacent files—e.g., task 1 modifies `config.py`, task 2 modifies `tests/test_config.py`. Each has a narrow declared scope. After both run, a full `git diff HEAD~n..HEAD` includes changes from *both* tasks. A naive call to `verify_worker_scope(scope_1, repo, base_sha)` on the full diff would correctly report all of task 2's changes as violations (since they're not in scope_1's allowed_paths), even though task 2 was authorized and ran correctly in its own wave.

**Design options (unresolved, WP-4 decision):**

**Option A: Scope verification per-wave after each wave completes.** After each wave finishes, record the git diff *just for that wave* (comparing HEAD before wave 0 with HEAD after wave n), then verify each task's scope only against its own wave's diff. Requires:
- Recording `base_sha` at wave entry, not just pipeline entry.
- Per-task scope verification only sees the deltas *that task* contributed, not the full accumulated diff.
- Parallel Workers in the same wave still have the full-wave diff (expected — they must not interfere).
- Auditable wave-scoped verification logs in the ledger.

**Pros:** Exact parity with fast-path semantics (single Worker verifies against its own scope); scales cleanly to any number of waves.

**Cons:** More bookkeeping; requires reverting scope verification until wave-scoped logic is in place, or conditionally disabling it for multi-wave dispatch until WP-5 lands (regression risk).

**Option B: Cumulative scope — forbid overlapping across waves.** Require that if wave N and wave N+1 both have tasks, they touch disjoint files (extend `dispatch.validate_wave`'s existing disjointness check across waves). Verify once at end using cumulative allowed_paths.

**Pros:** Simpler; no per-wave bookkeeping.

**Cons:** More restrictive on normal dispatch (requires replanning if overlaps exist); changes dispatch validation semantics mid-way through a release; may break existing plans that intentionally reuse/refine the same file across waves.

**Option C: Deferred for normal path, active for fast-path only.** Scope verification remains fast-path-only through R-0.2; normal paths get verification infrastructure in R-0.3 once Option A/B is decided. Fast-path is unaffected (already single-wave).

**Pros:** Unblocks R-0.2 design review and contract acceptance; no implementation risk to normal-path dispatch.

**Cons:** R-0.2's *expected result* (§ in contract) promises "normal-path Scenario C blocked by Renmark's own mechanism, not just Layer A." This trades that for documentation/contract-level guarantee only (Layer-A-only, same R-0.1 gap).

**This design does not choose.** See §7.

## 4. Carrying Scope into Normal Dispatch: `build_agent_dispatch()` Amendment

**Current state:** `build_agent_dispatch(task)` returns an `AgentDispatch` with `scope=None`. The prose constraint and no verification.

**Proposed amendment:**

1. **Declare scope at dispatch time, exactly as fast-path does:** After a task passes planning (same point where `Task` is validated), a scope scope *must* be declared. For normal single-task dispatch, this is straightforward: `allowed_paths = frozenset({task.target})` (or includes context files if they are writable; current fast-path restricts to target only — see WP-5 for policy decision). For architectural multi-task dispatch, each task's scope is populated identically.

   ```python
   def build_agent_dispatch(task: Task, repo: Path) -> AgentDispatch:
       # ... existing prompt building ...
       scope = WorkerScope(allowed_paths=frozenset({task.target}))
       return AgentDispatch(
           # ... existing fields ...
           scope=scope,  # NOW CARRIES SCOPE (same field as fast-path)
       )
   ```

   - This is a **backward-compatible amendment** to `AgentDispatch`: the field is optional (defaults to None); any existing caller that doesn't update continues to work (see §5 for the default-behavior decision).
   - The normal-path prompt remains unchanged (the prose constraint stays as-is for clarity).
   - The scope is **not** renegotiable mid-task (same fast-path principle: a Worker that discovers mid-task it needs a different scope must report `completion_state: "partial"` with `dependency_notes`, not make the change).

2. **Verification call location (Option A / Option B dependent, §3):**
   - **If Option A (per-wave):** After each wave completes and before advancing to the next, run `verify_worker_scope()` for each task in the wave against only that wave's diff.
   - **If Option B (cumulative):** After all waves complete, run `verify_worker_scope()` once with the cumulative allowed_paths.
   - **If Option C (deferred):** Scope verification is not called from normal dispatch yet; scope field is present but unused (design-only for R-0.2).

3. **Violation handling (mirrors fast-path, R-0.1 scope-enforcement-design.md §5):**
   - FAIL verdict → task output is not merged/committed/advanced.
   - No auto-revert (itself a destructive action outside the scope check's authority).
   - Escalation to Inspector/Owner via a new task status or existing `needs_agent`-shaped flag.
   - Ledger record of the violation (scope, diff, allowed_paths, violations) for audit.

## 5. Backward Compatibility: Default Scope When Not Declared

**Decision to make:** When a task is dispatched and `build_agent_dispatch()` is called (not build_fast_path_agent_dispatch), should the scope default be:

**Option A: Default scope = no enforcement.** If a caller does not explicitly set scope, `AgentDispatch.scope` remains `None`, and `verify_worker_scope()` is never called on that dispatch. This preserves exact R-0.1 behavior for any non-fast-path dispatch unchanged. A normal-path task can still touch any file the host permits. Gradual opt-in.

**Recommendation: ADOPT Option A.** 

**Reasoning:**
- R-0.1 WP-3's regression baseline requires unchanged behavior for existing non-fast-path dispatch. Option A preserves this.
- R-0.2's contract *permits* generalization to normal paths and provides the design; it does not mandate immediate enforcement in WP-1. WP-5 (implementation) can choose to roll out enforcement gradually, starting with fast-path (proven), then opt-in for normal paths, then mandatory.
- Failing closed (enforcing by default) on the first release of generalized enforcement risks breaking existing users' workflows before the mechanism is proven on the normal path.
- A clear default-to-legacy posture is more honest than a partial enforcement that claims to fix Scenario C but leaves loopholes.

**Alternative: Default scope = fail-closed** (Option B). Every task *must* declare an explicit scope at dispatch time, or the dispatch is rejected pre-inference. This guarantees no scope-less task runs.

- **Pros:** Scenario C reproduction becomes impossible by contract after WP-5 lands (no loophole).
- **Cons:** Requires amending every existing normal-path caller (build_agent_dispatch must now take an explicit scope parameter or raise); breaks backward compat; unproven on normal paths (we have no data that Scenario C is even possible on the normal path — R-0.1 only tested fast-path).

## 6. Normal-Path Scenario C Reproduction Test

**Required by R-0.2 contract / engineering acceptance §1:** Demonstrate that a normal-path task with a declared scope cannot perform an out-of-scope destructive action without being blocked or escalated.

**Test case (mirroring R-0.1's fast-path test `test_verify_worker_scope_reproduces_r0_0_scenario_c_finding`):**

**File:** `tests/test_r0_2_dispatch_regression_baseline.py` (WP-4 produces this; WP-1 defines the test structure here).

**Test:** `test_normal_dispatch_scenario_c_reproduction_out_of_scope_delete`

```
Given:
  - A Git repo with pre-existing audit files: .renmark/audits/audit-{1,2,3,4}.json
  - A normal-path task with declared scope = frozenset({"src/feature.py"})
    (the task is authorized to create/modify only src/feature.py)

When:
  - A subagent is dispatched with this task and scope
  - The subagent illegally deletes the 4 audit files (matching R-0.0 Scenario C exactly)
  - verify_worker_scope() is called with the declared scope and the diff showing deletions

Then:
  - verify_worker_scope() returns ScopeVerdict(passed=False, violations=[...])
  - All 4 deletions are listed as ScopeViolation(kind="disallowed_action", status_code="D")
  - The calling dispatcher does NOT merge / commit / advance the task
  - A test assertion confirms the violations exist and are auditable
```

**Regression:** Existing fast-path Scenario C test (test_verify_worker_scope_reproduces_r0_0_scenario_c_finding) must continue to pass, confirming no regression.

## 7. Open Questions for WP-4/WP-5

This design does not resolve these; they are explicit design decisions WP-5 must make after WP-4's regression baseline and investigation:

1. **Multi-wave scope verification strategy (§3):** Option A (per-wave), Option B (cumulative), Option C (deferred), or a new Option D? Implementation depends on the choice; no code lands until one is picked.

2. **Scope content for normal tasks:** Should `allowed_paths` include only the task's primary target, or also writable context files? Fast-path restricts to target only (per signal 1); normal paths may be larger. WP-5 must decide the policy and ensure lint/tests enforce it.

3. **Scope violation status mapping:** What task status or escalation mechanism communicates a scope violation? Reuse existing `needs_agent` / failed statuses, or introduce a new `scope_violation` status? WP-5 to decide based on the full orchestrate flow.

4. **Ledger format for scope violations:** Where and how are violations recorded for audit (append-only ledger, structured review artifact, dispatch-wave summary)? WP-5 must ensure consistency with R-0.0 baseline-trace and R-0.2 ledger consolidation design (WP-2 if it includes ledger amendments, or WP-7).

5. **Context files as writable scope:** R-0.1 fast-path treats context files as read-only (never in allowed_actions, never in allowed_paths); can a Worker modify a context file? The fast-path says no; normal paths may differ. Policy decision for WP-5.

6. **Parallelization and scope (§3 open):** If Option A (per-wave verification) is chosen, the implementation must prove that recording per-wave `base_sha` is compatible with concurrent wave execution and doesn't introduce race conditions or audit gaps. See program_driver.py's wave sequencing for context.

## 8. Interfaces with R-0.2 Work Packages

- **WP-1 → WP-2:** Scope enforcement primitives (WorkerScope, verify_worker_scope) are also used by WP-2's Inspector/repair separation to enforce that an Inspector role cannot directly mutate files (only report findings). WP-2 may introduce a variant or reuse existing primitives.

- **WP-1 → WP-3:** Evidence-required replan (WP-3) and scope enforcement (WP-1) are independent; scope addresses *what a Worker can touch*, replan addresses *whether a Worker can change its approach*. Both apply to the same dispatch, but differently.

- **WP-1 → WP-4:** The regression baseline (WP-4) must assert:
  - Fast-path Scenario C test still passes (no regression to R-0.1).
  - Existing non-fast-path UX is unchanged if scope verification is NOT yet active on normal paths (Option A above, default-to-legacy).
  - If scope verification IS active on normal paths (Option B above, or early WP-5 activation), the normal-path Scenario C reproduction test passes.
  - All existing tests still pass.

## 9. Reused vs. New (for Clarity)

**Reused, not reimplemented:**
- `WorkerScope` dataclass (unchanged)
- `verify_worker_scope()` function (unchanged, possibly with per-wave variant if Option A chosen — but same core logic)
- `ScopeViolation` and `ScopeVerdict` dataclasses (unchanged)
- The refuse-don't-silently-merge posture (same as R-0.1, mirrors IsolationViolation discipline)
- Ledger pattern (append-only, same as baseline-trace.jsonl)

**New for R-0.2 (WP-5 implementation scope, not built yet):**
- Amendment to `build_agent_dispatch()` to carry scope (field already exists, only needs population)
- Per-wave base_sha recording (if Option A chosen)
- Scope verification call site in normal dispatch flow (dispatch.py or program_driver.py)
- Violation escalation mechanism (task status / ledger record)
- Test suite coverage for normal-path enforcement and per-wave verification (if applicable)

## 10. Contract Alignment

This design addresses R-0.2's stated scope items:
- ✓ Generalize Worker-scope enforcement (R-0.1's verify_worker_scope) to non-fast-path paths
- ✓ Two-layer model maintained (Layer A host-level, Layer B deterministic Renmark check)
- ✓ Addresses R-0.0 Scenario C gap on normal paths (explicit test case defined)
- ✓ Backward compatible (Option A default-to-legacy preserves R-0.1 regression baseline)
- ✓ Open questions flagged rather than hidden (§7, §8)

**Not addressed here (deferred to WP-2, WP-3, WP-5):**
- Inspector/repair separation (R-006)
- Dispatch-reason/budget gate (R-008)
- Evidence-required replan (§9.3)
- Generalized rework cap (R-012)
- Nested-dispatch signal investigation (R-007)

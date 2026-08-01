# R-0.2 / WP-2B — Dispatch-Reason/Budget Gate Design (R-008)

**Status:** design deliverable, WP-2B deliverable for R-0.2 contract. No `renmark/**` file is touched by this document. This design extends the existing `renmark/subagent_gate.py` pre-dispatch justification gate to enforce R-008: "No speculative agents — every dispatch requires a work-order ID, contract, reason, scope, expected artifact, budget reservation."

## 1. Current State: `subagent_gate.py` Scope Today

**What it checks today:**
The existing `renmark/subagent_gate.py` module implements a pre-dispatch justification gate (`python -m renmark.subagent_gate <plan>`). It answers the **Deterministic-First 4-question gate**:

1. **Q1:** Can git/grep/parser/state answer this? → deterministic-eligible
2. **Q2:** Can a deterministic script/check answer this? → deterministic-eligible
3. **Q3:** Is this small/simple enough for the orchestrator to do inline? → inlineable
4. **Q4:** Is it large/ambiguous enough to justify a subagent? → justified

The gate classifies each task in a plan as:
- `deterministic_eligible` — a check/script should replace it, not spawn a subagent
- `inlineable` — small/simple enough for the orchestrator to do inline
- `justified` — large/complex enough to warrant a subagent dispatch
- `general-purpose-without-reason` — unjustified generic role (challengeable)

The gate **outputs a verdict per task** and **rolls up to a plan-level challenge** via `challenge_plan()`, which flags whether ≥50% of would-be subagent tasks are unjustified (deterministic-eligible, inlineable, or lacking a role reason).

**Exit code:**
- `0` if the plan is clean
- `1` if challenged (deterministic path found, inlineable task, or unjustified general-purpose role)
- `2` on parse/usage error

**What it does NOT check today:**
- Work-order IDs (no requirement yet)
- Contract references (no requirement yet)
- Dispatch reason (only checks via role_reason for general-purpose)
- Declared scope (only checks if a task has complexity/role, not explicit scope)
- Expected artifact (no schema exists yet)
- Budget reservation (no pre-dispatch budget check exists)

These six fields are R-008's requirements; subagent_gate.py checks only one of them (role reason, indirectly).

## 2. R-008 Requirements: Six Fields Per Dispatch

Per Constitution rule R-008 and CLAUDE.md's "No speculative agents" rule, every Agent/executor dispatch must carry:

1. **work_order_id** (string, unique) — a traceable identifier for this dispatch
2. **contract** (string, path or ID reference) — which milestone/release contract authorizes this
3. **reason** (string, ≤200 chars) — why is this dispatch necessary (e.g., "implement task 3", "repair finding #XYZ", "verify WP-2 deliverable")
4. **scope** (structured: target files, read-only context, prohibited files) — what is the worker authorized to touch
5. **expected_artifact** (string, path or schema) — what output is required
6. **budget_reservation** (structured: max_input_tokens, max_output_tokens, max_attempts) — resource limits

## 3. Design: Extend `subagent_gate.py` to Enforce R-008

### 3.1 New validation layer: `R008ChecklistValidator`

Add a new, pure deterministic validator class to `renmark/subagent_gate.py`:

```python
@dataclass(frozen=True)
class R008Checklist:
    """R-008 dispatch requirements — must be present before inference call."""
    work_order_id: str | None
    contract: str | None
    reason: str | None
    scope: dict | None  # {target_files, read_only_files, prohibited_files}
    expected_artifact: str | None
    budget_reservation: dict | None  # {max_input_tokens, max_output_tokens, max_attempts}

    @property
    def all_present(self) -> bool:
        """True iff all six required fields are present and non-empty."""
        return all([self.work_order_id, self.contract, self.reason, 
                    self.scope, self.expected_artifact, self.budget_reservation])

    def missing_fields(self) -> list[str]:
        """Return list of field names that are missing or empty."""
        missing = []
        if not self.work_order_id:
            missing.append("work_order_id")
        if not self.contract:
            missing.append("contract")
        if not self.reason:
            missing.append("reason")
        if not self.scope:
            missing.append("scope")
        if not self.expected_artifact:
            missing.append("expected_artifact")
        if not self.budget_reservation:
            missing.append("budget_reservation")
        return missing


def validate_r008_dispatch(dispatch_spec: dict) -> tuple[bool, list[str]]:
    """Check that a dispatch carries all R-008 required fields.
    
    Returns: (is_valid, missing_field_names)
    Pure function, never raises.
    """
    checklist = R008Checklist(
        work_order_id=dispatch_spec.get("work_order_id"),
        contract=dispatch_spec.get("contract"),
        reason=dispatch_spec.get("reason"),
        scope=dispatch_spec.get("scope"),
        expected_artifact=dispatch_spec.get("expected_artifact"),
        budget_reservation=dispatch_spec.get("budget_reservation"),
    )
    return checklist.all_present, checklist.missing_fields()
```

### 3.2 Integration point: pre-dispatch rejection

Update the primary dispatch path (`renmark/dispatch.py::build_subagent_input` or the calling site in `renmark/cli/_engine.py`) to invoke the R-008 validator:

```python
def dispatch_with_r008_check(dispatch_spec: dict, *, allow_missing: bool = False) -> SubagentInput | None:
    """Build a SubagentInput only if R-008 checklist is satisfied.
    
    If allow_missing=True (for backward-compat during migration), log a warning
    but proceed. If False (strict mode, new projects), reject and return None.
    
    In strict mode, the orchestrator must emit a work order with all fields
    before dispatch is attempted.
    """
    valid, missing = validate_r008_dispatch(dispatch_spec)
    
    if not valid:
        if allow_missing:
            log_warning(f"R-008 dispatch missing fields: {missing} — proceeding (legacy mode)")
            return build_subagent_input(dispatch_spec)
        else:
            log_error(f"R-008 dispatch rejected: missing {missing}")
            return None
    
    return build_subagent_input(dispatch_spec)
```

### 3.3 CLI: extend `renmark.subagent_gate` with R-008 checks

Extend the CLI in `renmark/subagent_gate.py::main` to support a new mode:

```bash
python -m renmark.subagent_gate <dispatch.json> --r008
```

When `--r008` is passed:
- Read the dispatch spec (JSON or YAML)
- Run `validate_r008_dispatch()` on it
- Print missing fields if any
- Exit 0 if valid, 1 if missing fields, 2 on parse error

Example output:
```
✓ R-008 dispatch checklist: all fields present
```

or:

```
✗ R-008 dispatch REJECTED: missing [contract, budget_reservation]
  work_order_id: WO-12345
  reason: implement feature task 3
  (Provide contract ref and budget before dispatch)
```

## 4. Scope of Enforcement: Which Dispatches Require R-008?

### 4.1 Fast-path dispatches

The fast-path (already bounded, already scoped) should carry minimal R-008 fields:
- `work_order_id` ✓ (already present as task ID)
- `contract` ✓ (fast-path contract implicit in fast-path mode)
- `reason` ✓ (task description/role_reason)
- `scope` ✓ (WorkerScope already enforced)
- `expected_artifact` ? (may be implicit; task structure defines it)
- `budget_reservation` ? (fast-path has implicit limits per CLAUDE.md)

**Decision for WP-5:** Confirm that fast-path dispatches can reuse the implicit work-order ID + contract + scope from the existing fast-path machinery, or whether they must be made explicit for R-008 compliance.

### 4.2 Normal-path dispatches

Every `/renmark:feature`, `/renmark:debug`, `/renmark:orchestrate` dispatch that spawns an Agent must carry explicit R-008 fields in the work order before calling the Agent.

### 4.3 Repair work orders (WP-2A)

Repair work orders produced by Inspector findings must carry R-008 fields:
- `work_order_id` (new, allocated by the Governor)
- `contract` (reference to the inspection finding's source contract)
- `reason` ("repair finding #XYZ from inspection ID ABC")
- `scope` (exactly which files the repair covers)
- `expected_artifact` (the repaired file; or re-verification artifact)
- `budget_reservation` (inherited from parent milestone, or reduced for bounded repair)

## 5. Integration with Existing Machinery

### 5.1 Interaction with `renmark/cost.py` and cost preview

The cost preview (shown before expensive tasks) can now reference R-008 fields:

```
Dispatch cost preview for WO-12345 (implement feature task 3):
  Estimated cost: ~50k tokens
  Work order: WO-12345
  Contract: R-0.2 WP-5
  Scope: [src/feature.py, tests/test_feature.py]
  Expected artifact: .renmark/reviews/WO-12345-result.md
  Budget: 60k input tokens, 10k output tokens, 2 attempts
```

### 5.2 Interaction with ledger/audit trail

Each dispatch is recorded in the ledger (`.renmark/state/` or `.renmark/ledger/`) with:
- The work-order ID (audit-traceable)
- The contract reference (policy-traceable)
- The reason (decision-traceable)
- Scope and budget used (resource-traceable)

### 5.3 Backward compatibility with existing plans/tasks

Tasks created before R-008 may lack some fields. WP-5 implementation must decide:

**Option A (strict):** All dispatches require R-008 fields; a task without them is rejected pre-dispatch. The orchestrator is responsible for populating these fields from the contract/plan.

**Option B (lenient):** Missing R-008 fields default to implicit values from the context (e.g., work_order_id = task.id, contract = current milestone, reason = task.description). Warn on inference; continue. A configuration flag allows projects to enforce strict mode if desired.

**Recommendation (for WP-5):** Adopt Option B initially with a strong warning, then migrate to strict mode (Option A) as projects populate R-008 fields.

## 6. Scope: What Counts as a "Dispatch"?

**Included (require R-008):**
- Agent tool calls via `SubagentInput` (Claude Code orchestrate, feature, debug, etc.)
- Codex subprocess calls via `renmark-execute` (scoped executors)
- WritingMate remote LLM calls (future, Phase 7+)

**Excluded (do not require R-008):**
- Deterministic checks (git, grep, Python parser, lint)
- Direct Python library calls (within the same process, already bounded)
- Local test execution (already scoped to repo)
- File operations (already authorized via the Work Order's scope)

## 7. Reused vs. New (for Clarity)

**Reused:**
- `renmark/subagent_gate.py` module (add R-008 checks to it, don't fork)
- Deterministic-first justification (keep existing Q1–Q4 checks)
- Work order concept (WP-1 and WP-2A already use task/work-order structures)
- Ledger infrastructure (existing `.renmark/` artifacts)
- Cost preview machinery (extend to show R-008 fields)

**New for R-0.2 (WP-5 implementation scope):**
- `R008Checklist` dataclass and `validate_r008_dispatch()` function
- `--r008` CLI mode for `python -m renmark.subagent_gate`
- Pre-dispatch rejection logic in `build_subagent_input()` or dispatch entry point
- Migration logic to infer R-008 fields from existing tasks (Option B lenient mode)
- Ledger events tagged with work-order ID + contract reference

## 8. Migration Path

### 8.1 Phase 1 (WP-5, early): Warning + inference

- R-008 fields are optional; inference from context provides defaults
- A warning is logged when fields are inferred
- Skill authors are notified to populate R-008 fields in their dispatch calls

### 8.2 Phase 2 (post-R-0.2): Strict mode opt-in

- Projects can enable strict mode via `.renmark/config.json`: `"enforce_r008_strict": true`
- In strict mode, missing R-008 fields are rejected pre-dispatch
- Default remains lenient (backward-compat)

### 8.3 Phase 3 (future release): Strict by default

- Strict mode becomes the default
- Legacy mode (`enforce_r008_strict: false`) is deprecated and supported via an explicit flag

## 9. Open Questions for WP-5

1. **Fast-path compatibility:** Does the existing fast-path dispatch infrastructure already provide R-008 fields implicitly (work_order_id = task.id, contract = fast-path contract)? Or must they be made explicit?

2. **Lenient vs. strict timeline:** Should WP-5 ship in lenient mode (Option B) or strict mode (Option A)? Backward-compat risk vs. enforcement strength trade-off.

3. **Budget reservation schema:** Should budget_reservation be a flat dict (max_input_tokens, max_output_tokens, max_attempts) or a nested structure (per role, per provider, per model)? WP-5 determines the schema.

4. **Scope schema:** Should scope carry set-based structures (frozenset of paths) or list-based (JSON-compatible)? Does it reuse WorkerScope from WP-1, or extend it?

5. **Error handling in existing skills:** If a skill attempts to dispatch without R-008 fields and strict mode is on, should the error be caught by the pre-dispatch gate or bubble up as a skill failure? WP-5 determines the error path.

6. **Audit trail depth:** Should every inference call be logged with R-008 metadata, or only high-cost dispatches? WP-5 determines the logging strategy.

7. **Cost preview integration:** The cost preview already exists; how deeply should R-008 fields be integrated? Show all six fields, or only work_order_id + reason? WP-5 refines the UX.

## 10. Contract Alignment

This design addresses R-0.2's stated R-008 scope item:
- ✓ No speculative agents — dispatch requires work-order ID
- ✓ Declared reason before inference — captured in reason field
- ✓ Declared scope before dispatch — enforced via scope field check
- ✓ Expected artifact before dispatch — documented in expected_artifact field
- ✓ Budget reservation before dispatch — validated before inference call
- ✓ Machine-checkable — pure validation functions, deterministic, pre-inference

**Backward compatible:**
- Existing dispatches without R-008 fields are warned (lenient mode) or rejected (strict mode)
- Migration path documented for skill authors
- No breaking change to existing projects until strict mode is enabled

**Not addressed here (deferred to WP-5, WP-3, Phase 4):**
- Full budget governor implementation (Phase 8 full feature; R-0.2 ships only reason + budget per call)
- Multi-dimension budget tracking (project / feature / milestone) — stays documented, not implemented
- Evidence-required replan triggering on missing budget approval (WP-3)
- Phase-4 Inspector registry and specialized Inspector framework

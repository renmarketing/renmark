# R-0.2 / WP-2A — Inspector/Repair Separation Design (R-006)

**Status:** design deliverable, WP-2A deliverable for R-0.2 contract. No `renmark/**` file is touched by this document. This design ensures that an Inspector-role dispatch (codereview, verify, or QA step) can only produce findings and evidence, never perform file mutations—and that any required repair becomes a separate, logged work order.

## 1. Current State: Tool-Restriction Gap

**Today's contractual intent:** The `subagent-profiles.md` registry declares the `reviewer` role as "read-only" with file targets `N/A` and output as "JSON findings." This is the product contract visible to skill authors.

**Today's implementation gap:** The actual `plugin/agents/reviewer.md` role definition declares:
```yaml
tools: Read, Grep, Glob, Bash, Write
```

The `Write` tool is present. An Inspector agent dispatched with this definition **CAN** directly mutate files in the same dispatch—it is not structurally prevented. The prohibition exists only as advice ("Do not modify production files" in the prompt text), not as a constraint enforced by the host platform's tool allowlist.

**Why this matters:** R-006 (Constitution rule 6) requires that "Inspectors cannot repair — findings and evidence only; a separate repair work order performs changes." Today, if a reviewer agent decided to commit a fix directly during the same dispatch, renmark has no mechanical gate to prevent it. This undermines the authority separation between Inspection (finding/judgment) and Repair (action/mutation).

## 2. Design Goal

Make it **impossible** (not just contractually discouraged) for an Inspector-role dispatch to mutate files. The separation must be enforced at dispatch time via tool restrictions, combined with a structural rule that any FAIL finding or severity-warranting issue produces a separate work order rather than being patched in-line.

## 3. Mechanical Enforcement: Tool Restriction on Inspector Roles

### 3.1 Agent definition amendment

Modify the role definitions for any role that functions as an Inspector:

- **`reviewer.md`** (code review role)
- **`QA`-equivalent role** if/when a dedicated QA agent is created (Phase 4)
- Any future Inspector-class role

**Current state (example: reviewer.md):**
```yaml
tools: Read, Grep, Glob, Bash, Write
```

**Proposed amendment (reviewer.md):**
```yaml
tools: Read, Grep, Glob, Bash
```

Remove the `Write` and `Edit` tool access from Inspector-class roles. Keep only read/query tools.

**Rationale:**
- The host platform (Claude Agent tool) enforces the declared tool allowlist at dispatch time.
- A role without `Write`/`Edit` cannot call those tools, even if the model attempts to.
- This is a structural, zero-prompt-hygiene enforcement — the attempt to repair fails at the tool invocation level before any file is touched.
- The `Bash` tool is retained because inspection often requires running tests, linters, and queries; the risk of Bash abuse is lower than Write/Edit for an Inspector role scoped to findings-only output.

### 3.2 Verification that all Inspector roles comply

**Audit point:** Before WP-5 implementation, every role that functions as an Inspector must be audited:

1. **Identify all Inspector-class roles.** Read `plugin/agents/*.md` and classify each role as:
   - **Inspector** (primary purpose is to verify, review, audit, or assess — NOT to fix): `reviewer.md`, `audit-reader.md` (currently). Any others?
   - **Worker** (primary purpose is to implement/create/write code): `code-implementer.md`, `test-writer.md`, `docs-editor.md`, etc.
   - **Planner** (primary purpose is to plan/design): (none currently in the 8 native roles).

2. **For each Inspector role, ensure tool list lacks Write/Edit.** If any Inspector-class role declares `Write` or `Edit`, flag it for amendment.

3. **Document the audit result.** Append findings to a `.renmark/audits/inspector-roles-audit.md` artifact.

## 4. Structural Enforcement: Repair Work Order Pattern

### 4.1 No in-line repair; separate work order required

When an Inspector-role dispatch produces a FAIL verdict or a finding with severity ≥ Major, the calling skill (codereview, verify, etc.) MUST:

1. **Record the finding** in a structured inspection report (`.renmark/reviews/YYYY-MM-DD-*.review.md` or equivalent).
2. **Emit a repair work order** — not perform the repair itself.
3. **Stop the dispatch** — do not attempt auto-fix in the same agent context.

**Example (codereview):**
- Current behavior (post-detection): If codereview finds a Critical bug, it reports it in-context or in the review artifact.
- Proposed behavior (WP-5): Codereview reports the Critical bug in the artifact and produces a structured repair work order (separate task, separate agent, separate dispatch).

The repair work order carries:
- `work_order_id` (unique, audit-traceable)
- `source_inspection_id` (pointer to the finding)
- `severity` (inherited from the finding)
- `scope` (exactly which file(s) and lines require repair)
- `description` (the repair needed, not just the problem)
- `acceptance_criteria` (how to verify the repair succeeded)

### 4.2 Skill-level enforcement: No self-repair clause

Every skill that dispatches an Inspector-role agent must document:

> **Inspector findings do not self-repair.** Any FAIL verdict, blocking finding, or finding with severity ≥ Major triggers a separate repair work order routed through the Governor, not an in-context fix. The Inspector role returns findings only; mutation is delegated.

This language must appear in the skill's description or a prominent early section (e.g., "How it runs").

### 4.3 Integration with the Governor and work-order dispatch

(WP-5 implementation detail, documented here for design completeness.)

When a repair work order is emitted:

1. The Governor validates the work order against R-008 (dispatch-reason/budget requirements—see WP-2B design).
2. The Governor records it in the ledger with a back-pointer to the source inspection.
3. The Governor routes it to an appropriate Worker role (code-implementer, test-writer, etc.) based on the repair scope.
4. The orchestration engine queues the repair as a follow-on task, not a nested dispatch (R-007 compliance).
5. After repair, a second independent verification pass is run (not by the same Inspector, to prevent escalation into back-and-forth loops).

## 5. Scope: Which Roles Are Inspectors?

**Currently identified Inspector roles:**
- `reviewer.md` — code review (read-only verdict on diffs)
- `audit-reader.md` — audit artifact analysis (read-only summary)

**Future Inspector roles (Phase 4 and beyond):**
- Dedicated QA Inspector (test execution + pass/fail verdict)
- Architecture Inspector (architectural compliance audit)
- Security Inspector (vulnerability/privacy audit)
- Etc.

**Note:** This design applies to all current and future Inspector roles; the pattern is universal.

## 6. Backward Compatibility and Migration

### 6.1 Fast-path review behavior

The fast-path already restricts Workers to a declared scope. Inspection within the fast path (if any) should follow the same no-repair pattern as the normal path.

### 6.2 Existing review dispatches

Existing projects that dispatch the `reviewer` role today may not have a formal repair work order pattern. WP-5 implementation must ensure:

- The `reviewer.md` tool restriction takes effect immediately (no Write/Edit).
- Skills that depend on `reviewer` (codereview, finish, etc.) are updated to emit repair work orders instead of assuming in-line fixes.
- If an existing skill attempts to repair based on a reviewer finding, it fails gracefully and escalates (never silently suppresses the repair).

## 7. Interfaces with R-0.2 Work Packages

### 7.1 WP-1 (Scope Enforcement)

WP-1 generalizes Worker scope enforcement to the normal dispatch path. Repair work orders produced by Inspectors will themselves be Workers (assigned to code-implementer, etc.) and thus subject to scope enforcement via WP-1's machinery.

### 7.2 WP-2B (Dispatch-Reason/Budget Gate, R-008)

Every repair work order must carry a declared work-order ID, contract reference (the inspection finding ID), reason ("repair finding #XYZ"), scope, expected artifact, and budget reservation. WP-2B's design extends the pre-dispatch gate to validate these fields before the repair is dispatched.

### 7.3 WP-3 (Evidence-Required Replan)

If an Inspector finding reveals a fundamental architectural or requirement incompatibility (vs. a simple bug), the repair work order is rejected and an evidence-required replan is triggered per WP-3's rules, not auto-fixed.

### 7.4 Regression testing (WP-4)

The baseline must demonstrate:
- An Inspector role cannot call Write/Edit tools (no tool available on the agent).
- A finding from an Inspector produces a work order, not an in-line fix (verifiable in dispatch logs).

## 8. Open Questions for WP-5

1. **Repair work order format:** Should repair work orders reuse the existing `Task` dataclass or a new `RepairWorkOrder` dataclass? WP-5 determines the schema and how it integrates with `renmark/dispatch.py`.

2. **Escalation on repeated failures:** If an Inspector produces a finding, a repair is attempted, and the same Inspector finds the same issue again, should this trigger a circuit breaker (per R-012)? WP-5 decides the policy.

3. **Inspector coordination:** Can multiple Inspectors run in parallel (e.g., both reviewer and audit-reader on the same artifact)? If yes, how are conflicting repair recommendations reconciled? WP-5 to clarify multi-inspector workflows.

4. **Repair orchestration timing:** Should all repair work orders from a single inspection be dispatched together, or sequenced? WP-5 determines the orchestration pattern.

5. **Scope of "Inspector" roles:** Are there other current roles (e.g., in older code paths or as implicit inspectors) that should be retroactively restricted? WP-5 audit may identify additional candidates.

6. **Bash safety for Inspectors:** The current design retains Bash for test execution and queries. Should there be further constraints on Bash (e.g., read-only flags, approved command whitelist) to harden this? WP-5 to assess risk.

## 9. Reused vs. New (for Clarity)

**Reused:**
- Tool-allowlist enforcement mechanism from the Agent tool (existing Claude Code / plugin infrastructure).
- Structured work-order pattern (WP-1 already uses Task; repair work orders extend this).
- Ledger/audit trail infrastructure (existing `.renmark/` artifact structure).

**New for R-0.2 (WP-5 implementation scope):**
- Tool restriction amendments to `plugin/agents/reviewer.md` and any other Inspector roles.
- Repair work order emission pattern in skills that call Inspectors (codereview, etc.).
- Repair work order schema (if distinct from Task) and integration points in dispatch.py.
- Ledger event classification for repairs (back-pointer from work order to source finding).
- Multi-inspector audit and coordinator logic (if multiple Inspectors run in parallel).

## 10. Contract Alignment

This design addresses R-0.2's stated R-006 scope item:
- ✓ Inspectors cannot repair — tool restriction prevents file mutation
- ✓ Findings and evidence only — the output contract is enforced
- ✓ Separate repair work order performs changes — structural pattern documented
- ✓ Backward compatible — existing Inspector dispatches fail gracefully on Write attempt (tool not available), escalating to a repair work order flow

**Not addressed here (deferred to WP-5, WP-3):**
- Full repair orchestration implementation (WP-5)
- Evidence-required replan trigger on architectural findings (WP-3)
- Multi-inspector coordination (Phase 4, deferred)

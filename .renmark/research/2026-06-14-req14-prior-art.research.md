---
artifact_type: research
schema_version: 1
created_at: 2026-06-14T17:36:53+00:00
source_sha: e14ab253cd12d878df0065c60db8cd6d40ddacaf
related_plan: null
generator: brainstorm-research
stale_after: 2026-07-14T00:00:00Z
dependency_refs: []
completion_state: complete
confidence: medium
validation_status: unvalidated
retry_count: 0
parser_success: true
schema_compliance: true
---

# REQ-14 Prior Art: Scheduled Read-Only Discovery That Proposes Work for Human Review

## Research Question

How do comparable systems design and NAME a "scheduled, read-only proposer lane" — a recurring agent that scans, writes a report, and surfaces candidate work items into a human-gated backlog, but NEVER executes (no commit/merge/release)?

Specific sub-questions:
1. Dependabot / Renovate / CodeQL / audit bots: how do they name the surfaces?
2. Idiomatic split: trigger/schedule config vs. the worker?
3. Deduplication of proposals across runs?
4. "Propose, never execute" boundary enforcement?
5. Build-vs-reuse signal?

---

## Sources Consulted

- https://docs.renovatebot.com/bot-comparison/
- https://docs.renovatebot.com/noise-reduction/
- https://docs.renovatebot.com/key-concepts/automerge/
- https://docs.renovatebot.com/mend-hosted/job-scheduling/
- https://docs.renovatebot.com/key-concepts/scheduling/
- https://vadim.blog/autonomous-agent-evaluation-human-approval/
- https://machinelearningmastery.com/building-a-human-in-the-loop-approval-gate-for-autonomous-agents/
- https://jasonet.co/posts/scheduled-actions/
- https://github.com/dependabot/dependabot-core/issues/4757 (deduplication issue)
- https://github.com/dependabot/dependabot-core/issues/3342 (duplicate PRs bug)
- https://www.bestaiweb.ai/what-is-human-in-the-loop-for-agents-and-how-approval-gates-keep-autonomous-workflows-safe/
- https://www.cognitivetoday.com/2026/05/human-in-the-loop-ai-approval-gate/
- https://www.getmaxim.ai/articles/manual-approval-vs-autonomous-tool-execution-designing-safe-ai-agent-loops/

---

## Finding 1: Naming — The Industry Split Is Scheduler vs. Worker (Not Scheduler vs. Proposer)

### Evidence from Renovate (strongest signal)

Renovate's own documented architecture uses three named tiers:

- **Job Scheduler** — selects which repos run and when; adds them to the queue. Four scheduler types by frequency (hourly, 4-hourly, daily, weekly).
- **Job Queue** — intermediary buffer between scheduler and runner.
- **Job Runner** — the execution component; does the actual scan and PR-open work.

The *worker that opens PRs* is called a **runner**, not a "proposer" or "scout." The scheduler is separate infrastructure. The runner's job is both to scan AND to open PRs (propose) — there is no further sub-split between "proposer" and "executor" in Renovate's model, because for Renovate, "opening a PR" IS the safe output (the PR itself is the gate before any merge).

**Key implication for REQ-14:** In Renovate's model, the worker that proposes is the runner. The "propose, not execute" boundary is enforced by the merge gate (branch protection, required reviews), not by the worker's own scope. The worker is free to write PRs; humans control what gets merged.

### Evidence from GitHub Actions scheduled workflows

The `schedule` event in GHA is the trigger config. The job(s) it fires have user-chosen names (`stale`, `audit`, `issue-creator`). There is NO industry-standard name for a job that opens issues without executing changes — practitioners name it by what it DOES (`stale-checker`, `dependency-audit`, `create-weekly-issue`). The scheduler keyword is always `schedule`; the worker name is domain-specific.

### Evidence from CodeQL

CodeQL scheduled scans use `on: schedule` in the workflow trigger, and the scan job is typically named `analyze` or `codeql`. The output is a SARIF report surfaced as GitHub security alerts — never auto-remediated. The boundary is implicit: CodeQL has no write permissions beyond writing the alert. No standard "proposer" nomenclature.

### Naming convention conclusion

The industry pattern is:
- The **trigger/config** is always called `schedule` (the word is universal).
- The **worker** is named after what it DOES: `scan`, `audit`, `analyze`, `runner`, `check`.
- No prior art uses `proposer`, `scout`, or `patrol` as a command/worker name in mainstream tooling.
- "Scout" and "patrol" appear in robotics/swarm literature, not in CI/CD.

**Verdict on the renmark naming debate (`/renmark:propose` vs `:scout`/`:patrol`):**
- `:scout` and `:patrol` have no CI/CD precedent; they import robot/surveillance connotations — likely confusing.
- `:propose` is accurate but names the OUTPUT, not the ACTION. It's the closest to precise but is implicit (the user knows proposals happen; the interesting part is that it scans/discovers).
- The strongest prior-art signal points toward naming the command after the WORK: `/renmark:audit` (already exists), `/renmark:scan`, or a compound like `/renmark:discover`. 
- **Recommendation:** Use `/renmark:propose` only if the user-facing story is "I want to submit candidate items for triage." If the story is "I want to run a read-only health scan and surface findings," prefer `/renmark:scan` or keep it as a scheduled invocation of `/renmark:audit` with a `--propose` flag.

---

## Finding 2: Deduplication of Proposals Across Runs

### Renovate's approach (strongest signal; most mature)

Renovate deduplicates by **branch state**, not by PR fingerprint:

1. When Renovate runs, it checks whether a branch for the proposed update already exists (e.g., `renovate/lodash-4.x`).
2. If the branch already exists AND the target version hasn't changed, Renovate skips creation — idempotent by branch tracking.
3. If the branch exists but the target version has changed (e.g., 4.17.19 → 4.17.21), Renovate UPDATES the existing PR rather than creating a duplicate.
4. PRs are only recreated if conflicts require it.

**This is branch-as-deduplication-key** — the branch name encodes the finding identity (dependency name + version range). The same pattern applied to renmark: proposals should carry a stable **finding key** (e.g., `{check_type}:{target_file}:{rule_id}`) so a second run can skip if an open proposal for the same key already exists.

### Dependabot's deduplication (weaker; known gaps)

Dependabot has a documented bug: it sometimes opens duplicate PRs for the same dependency when two manifest files overlap. Issue #4757 ("Avoid making duplicate PRs") is a long-standing feature request. Dependabot does NOT fingerprint proposals before opening — it relies on branch naming conventions but has race conditions.

**Key learning:** Dependabot's duplicate-PR problem is a cautionary tale. The failure mode is: scheduler fires, worker runs, worker doesn't check for existing open proposals with the same key, opens a duplicate. Users get PR noise. Renmark must not reproduce this.

### Industry best practice for deduplication

Three patterns found:

**Pattern A — Branch/Key Existence Check (Renovate)**
Before creating a proposal, check if an open item with the same stable key already exists. If yes: skip (idempotent) or update if the finding has changed. This is the most robust pattern.

**Pattern B — Fingerprint + TTL (security scanners)**
CodeQL and similar tools compute a fingerprint per finding (location + rule + snippet hash). If the fingerprint already exists in the alert state, the finding is SUPPRESSED as a duplicate. Findings have configurable TTL (auto-dismiss after N days without recurrence). This is more sophisticated but requires a persistent finding store.

**Pattern C — Scheduled Deduplication Window (Renovate noise reduction)**
Renovate's noise-reduction docs recommend batching related proposals into a single grouped PR (packageRules + groupName). This reduces volume rather than deduplicating identical proposals. Analogous to: instead of opening 10 separate "outdated dependency" proposals, open one "dependency health" proposal listing all 10. Volume control, not identity deduplication.

**Recommendation for REQ-14:** Implement Pattern A as the minimum. Persist a proposals ledger at `.renmark/state/proposals.json` keyed by `{check_type}:{rule_id}:{target}`. On each run: compute key, check ledger, skip if open, update if resolved/stale. Pattern B (fingerprinting with TTL) is the right long-term direction but can be deferred.

---

## Finding 3: "Propose, Never Execute" Boundary Enforcement

### How the best systems enforce it

**Renovate's model:** The worker (runner) is allowed to open PRs and push branches. It is structurally BLOCKED from merging by:
1. Branch protection rules requiring N approvals.
2. Required status checks (CI must pass).
3. Renovate automerge defaults to OFF — users must opt in.
4. When automerge is enabled, Renovate enforces test-gate: merge only if CI passes.
5. Sequential merge: only one branch per run per target branch.

The safety boundary is EXTERNAL to the worker — enforced by the platform's merge controls, not by the worker refusing to merge. The worker could technically merge if permissions allowed. The boundary is access control + default config.

**Human-in-the-loop approval gate literature (LangGraph pattern):**
The "propose, don't execute" pattern in agentic frameworks uses an **interrupt node**:
1. Agent generates a proposal (tool call, action, draft).
2. Execution pauses at an "approval interrupt."
3. The proposal is held as `pending_draft` or `pending_approval`.
4. A human approves/rejects via a separate interface.
5. Only on approval does execution resume past the interrupt.

Key quote from vadim.blog: "every outreach touch is composed, held as a pending draft, and stopped at an approval interrupt. The gateway, not the model, decides which proposals reach the system."

This is the pattern renmark needs: the proposer writes to `.renmark/state/proposals.json` (or the backlog); it has NO access to the commit/merge/release tools. The approval gate (human triage → `/renmark:approve`) is the only path from proposal to execution.

**CodeQL's model:** Read-only by construction. The scanner runs with read-only repo access and write-only access to the Security Alerts API. It CANNOT commit, open PRs, or run commands. The boundary is enforced by minimal-privilege token scope, not by the worker's self-restraint.

### Failure modes to guard against

1. **Permission creep:** A "proposer" tool that accumulates write permissions over time — starts proposing, ends committing. Mitigated by: declare tool list for the proposer process at definition time; no commit/push/merge tools in scope.
2. **Approval bypass:** A proposal that auto-approves via a side channel (e.g., a prior human approval for "check type X" is interpreted as approval for all findings of type X). Mitigated by: per-finding approval, not per-category.
3. **Ghost execution:** A proposer that "helpfully" also fixes the finding it reports. Mitigated by: verify-only tool set, no Edit/Write/Bash in proposer scope.

**Recommendation for REQ-14:** Enforce the boundary by tool-list isolation, not by self-restraint. The proposer process should have zero write tools except `Write` to `.renmark/` paths (proposal artifacts). This mirrors CodeQL's minimal-privilege model — the constraint is structural, not behavioral.

---

## Finding 4: Build vs. Reuse Signal

### Reuse candidates examined

**Renovate (self-hosted):** Most powerful prior art for the "schedule → scan → PR" pattern. However, Renovate is a dependency-update tool. Its scan logic, PR templates, and branch naming are all tightly coupled to dependency management. Wrapping it to propose arbitrary audit findings (code quality, architecture debt, spec drift) would require writing a custom Renovate data-source plugin — non-trivial, poor fit.

**CodeQL:** Read-only scan → SARIF output → GitHub Alerts. Very well-designed for security findings. The SARIF format is reusable (machine-readable finding schema with fingerprints, severity, location). **Reuse signal: HIGH for the output format.** SARIF is worth adopting as the findings schema for renmark proposals, even if CodeQL itself isn't used.

**GitHub Actions `create-an-issue` action:** Trivial — creates a GitHub issue from a Markdown template on schedule. This IS the simplest form of "scheduled proposer." For renmark, the equivalent is already in-project: write a structured finding to `.renmark/state/proposals.json`. No external tool needed.

**LangGraph interrupt nodes:** The "approval interrupt" pattern from LangGraph is reusable as a concept; the library itself is Python and could be used. However, renmark already has its own pipeline.json/lifecycle.json state machine. Adding LangGraph would be a framework dependency for a pattern renmark can implement natively with its existing state machinery. **Reuse signal: LOW (concept: HIGH; library: LOW).**

**Sweep / SweepAI:** An AI bot that opens PRs from GitHub issues. Named after "sweeping" the codebase for issues. Read-only scan → proposal → PR is exactly its model. However, Sweep is scoped to code-fix suggestions, not arbitrary audit findings. Not a good fit for wrapping.

### Build-vs-reuse recommendation

**Build natively, borrow the patterns:**
- Borrow SARIF's finding schema (fingerprint + severity + location + rule-id) for the proposals ledger format.
- Borrow Renovate's branch-as-key deduplication (finding key → idempotent proposal check).
- Borrow CodeQL's minimal-privilege boundary (proposer scope = zero write tools except `.renmark/` artifacts).
- Do NOT wrap Renovate, CodeQL, LangGraph, or Sweep — each is domain-specific or introduces heavyweight dependencies.

The renmark scheduler (trigger) already exists via external cron; the worker needs to be `/renmark:audit` invoked with `--mode=propose` or a new `/renmark:scan` command. The proposals ledger and the `/renmark:approve` gate already provide the architecture for the human-gated backlog.

---

## Assumptions and Edge Cases

### Assumptions
1. The "scheduled" trigger is external cron (GHA schedule, system cron) — not a renmark-internal scheduler daemon. This is consistent with the external cron pattern used by Renovate (Mend scheduler) and CodeQL (workflow schedule trigger).
2. "Human-gated backlog" means `.renmark/state/proposals.json` + `/renmark:approve` is the approval surface. If the intent is a GitHub Issues backlog, the architecture shifts significantly (GitHub write permissions needed).
3. "Read-only" means no commits, no PR opens, no merges. Writing to `.renmark/` artifacts is permitted (same as CodeQL writing to Alerts API).

### Edge cases
- **Blocking:** What if the findings store itself becomes corrupted or stale? The proposer must handle a missing/invalid proposals.json gracefully — treat as empty, not as error.
- **Deferrable:** What if a proposal is resolved externally (the issue was fixed in a commit the proposer didn't see)? Deduplication should check git state, not just proposal state. This is deferrable to v2.
- **Blocking:** If the proposer has no stable finding key per check type, deduplication is impossible. Finding key schema must be defined before any scan writes proposals.
- **Deferrable:** TTL-based auto-expiry of proposals (Pattern B). Useful but not needed for v1.

---

## Perspectives and Interpretations

### Perspective A: This is just `/renmark:audit` with a write step
The current `/renmark:audit` already does read-only scanning and writes a report. REQ-14 is an extension: audit → structured proposals.json with human-gate. The "new command" framing may be unnecessary — a `--propose` flag on `/renmark:audit` preserves the single-responsibility principle and avoids a new slash command.

### Perspective B: This deserves its own command because the cadence contract is new
The scheduled/cadenced nature changes the UX contract. A one-off audit is pull-based (user invokes it). A scheduled proposer is push-based (system invokes it, writes findings, waits for human). That's a different interaction model. A distinct command communicates the cadence contract to the user. Counter-argument: the command doesn't know it was invoked by a cron job vs. a human; the `--propose` output mode is what matters, not the command name.

### Perspective C: The naming debate is a distraction from the deduplication problem
`/renmark:scout` vs. `/renmark:propose` vs. `/renmark:audit --propose` matters less than whether the proposals ledger and deduplication key schema are designed correctly. A poorly deduplicated proposer will generate noise that makes humans stop paying attention — the exact failure mode that killed early Dependabot adopters.

---

## Separated Findings vs. Recommendations

### Findings (evidence-based)
1. Industry names the worker after what it DOES, not how it's triggered. "Runner" and "scanner" dominate; "proposer" is rare.
2. The scheduler/trigger is universally called `schedule`. The worker has a domain-specific name.
3. Renovate deduplicates by branch-as-key (stable identity per finding). Dependabot deduplicates poorly and has bug reports to show for it.
4. CodeQL enforces "propose never execute" via minimal-privilege token scope, not worker self-restraint.
5. LangGraph uses "approval interrupt" nodes; the human decision is the only path past the interrupt.
6. No existing tool is a good reuse candidate for wrapping. SARIF (finding schema) and Renovate's deduplication pattern are worth borrowing.

### Recommendations (synthesized from findings)
1. **Naming:** Use `/renmark:audit` with a `--propose` mode flag, OR a new `/renmark:scan` that calls audit internally. Avoid `:scout`/`:patrol`. Consider `:propose` only if user-facing story is explicitly "submit for triage."
2. **Deduplication:** Persist `.renmark/state/proposals.json` with finding keys `{check_type}:{rule_id}:{target}`. Check before writing. Skip if open; update if finding changed; close if resolved.
3. **Safety boundary:** Tool-list isolation, not self-restraint. Proposer scope = zero Bash/Edit/Write outside `.renmark/`. Mirror CodeQL's minimal-privilege design.
4. **Output format:** Adopt SARIF-inspired fields (fingerprint, severity, rule-id, location, confidence) for the proposals ledger schema. Enables future tooling integration.
5. **Don't add a new scheduler:** External cron calling the worker is the right model. Renovate's architecture validates this. The scheduler is configuration, not code.

## Summary

- Naming: industry names the WORKER after what it does (runner/scanner/analyzer); scheduler is always 'schedule'; no prior art for :scout/:patrol in CI/CD.
- Dedup: Renovate's branch-as-key (stable finding-id → skip-if-open/update-if-changed) is best practice; Dependabot's PR duplication bugs are the cautionary tale to avoid.
- Propose-not-execute boundary: enforce via tool-list isolation (zero write tools outside .renmark/), not worker self-restraint — mirrors CodeQL minimal-privilege token scope.
- Build natively; borrow SARIF's finding schema (fingerprint+severity+rule-id) and Renovate's dedup key pattern; do NOT wrap Renovate/CodeQL/LangGraph — all domain-mismatched or heavyweight.
- Risk: deduplication key schema must be defined before first run; without stable keys, every cycle re-proposes identical findings → proposal noise → humans stop triaging (Dependabot failure mode).

---
artifact_type: plan
schema_version: 1
created_at: 2026-07-17T14:50:00-04:00
source_sha: 701429cf5255fea14708592643563fafdf809429
related_plan: null
generator: renmark:plan
stale_after: null
dependency_refs:
  - PRD.md#REQ-24
completion_state: complete
confidence: high
validation_status: validated
retry_count: 0
parser_success: true
schema_compliance: true
---

# Proactive repeated-issue monitor

Implement REQ-24 by reusing Scan's stable finding identity model, adding a separate bounded recurrence ledger for implementation and verifier failures, stopping equivalent retries before a third model attempt, and presenting the same patch-or-durable-guard remediation on Claude Code and Codex. The core stays stdlib-only, raw histories never enter the ledger or orchestrator context, and rule-document edits remain human-gated and mirrored.

### Task 1: Promote Scan's stable identity primitives
- **mode:** B
- **target:** renmark/scan.py
- **context_files:** []
- **complexity:** medium
- **executor:** sonnet
- **role:** code-implementer
- **parallel_group:** 1
- **est_tokens:** 700
- **est_cost_usd:** 0.0321
- **verifier:** .venv/bin/pytest -q tests/test_scan.py
- **serves:** REQ-24
- **spec:**
  Turn Scan's proven stable identity behavior into a small public reuse seam without changing Scan's proposer-lane behavior.
  Add a public helper that builds the existing `check:rule_id:target` key from explicit parts and a public content-fingerprint helper with the existing hash semantics.
  Keep `finding_key(Finding)` delegating to the parts helper and retain `_fingerprint` as a compatibility alias so existing callers and tests do not break.
  Do not change `proposals.json`, backlog creation, resurface behavior, locking, or read-only scan invariants.

### Task 2: Add the bounded recurrence ledger and decision API
- **mode:** A
- **target:** renmark/recurrence.py
- **context_files:** []
- **complexity:** medium
- **executor:** sonnet
- **role:** code-implementer
- **parallel_group:** 2
- **est_tokens:** 1800
- **est_cost_usd:** 0.0354
- **verifier:** python3 -m py_compile renmark/recurrence.py
- **serves:** REQ-24
- **spec:**
  Add a deterministic stdlib-only issue observation API that reuses the public stable-key and fingerprint helpers from `renmark.scan`.
  Define typed observation and decision dataclasses. The decision must expose the stable key, short fingerprint, total occurrence count, whether another retry is blocked, a remediation class (`patch` or `durable_guard`), and at most five bounded summary lines.
  Persist only structured, bounded evidence under `.renmark/state/recurrences.json`: key, fingerprint, counts, source, target, timestamps/run id, remediation class, and acknowledgement/resolution status. Never persist raw verifier output, model transcripts, prompts, diffs, or full error bodies.
  Treat the second materially equivalent observation as the proactive threshold and block an unacknowledged third attempt. A changed fingerprint for the same logical key starts a fresh occurrence sequence so unrelated failures do not false-match.
  Provide a pre-attempt query plus an explicit acknowledge/resolve API for `patch`, `durable_guard`, or a one-time user-requested retry, so remediation cannot create a permanent deadlock.
  Use atomic best-effort writes, advisory locking where available, corrupt-file recovery, and a fixed maximum entry count so state never grows without bound. Do not reuse or mutate Scan's `proposals.json` ledger.

### Task 3: Guard Codex internal retries
- **mode:** B
- **target:** renmark/cli/_codex_runner.py
- **context_files:** []
- **complexity:** medium
- **executor:** sonnet
- **role:** code-implementer
- **parallel_group:** 3
- **est_tokens:** 900
- **est_cost_usd:** 0.0327
- **verifier:** python3 -m py_compile renmark/cli/_codex_runner.py
- **serves:** REQ-24
- **spec:**
  Integrate `renmark.recurrence` at every retry-eligible Codex failure seam: nonzero executor exit, lane violation, and verifier failure.
  Derive stable observations from failure class, task target, verifier identity, run id, and a bounded current signal. Let the recurrence module hash/normalize the signal and persist no raw output.
  The first equivalent failure may use the existing retry. On the second equivalent failure, stop before launching a third Codex call, emit a bounded proactive status containing recurrence evidence and the `patch` or `durable_guard` recommendation, and return a truthful terminal failure code such as `repeated_issue_guard`.
  Preserve rollback, usage ledger, escalation records, retry counts, provider-usage pause behavior, and sibling-lane safety. Never edit `CLAUDE.md` or `AGENTS.md` from the runner.

### Task 4: Apply the same recurrence gate to host-agent orchestration
- **mode:** B
- **target:** plugin/skills/orchestrate/SKILL.md
- **context_files:** []
- **complexity:** simple
- **executor:** haiku
- **role:** docs-editor
- **parallel_group:** 3
- **est_tokens:** 800
- **est_cost_usd:** 0.0011
- **verifier:** python3 -m renmark.lint --strict-frontmatter > /dev/null
- **serves:** REQ-24
- **spec:**
  Add a host-neutral repeated-issue step around non-usage task FAILs and verifier downgrades. Call the deterministic `renmark.recurrence` API; never parse or persist raw histories in skill prose.
  Before dispatch, stop when a target has an unacknowledged threshold decision so neither Claude Code nor Codex can begin a third equivalent model attempt silently.
  Surface a bounded notice with count/fingerprint evidence and a recommended action: route reproducible implementation/test failures to a patch/debug path, or propose a mirrored `CLAUDE.md` plus `AGENTS.md` guard for repeated workflow/contract failures.
  Present host-native recommended-first choices for patch, durable guard, or one explicit retry. A guard is proposal-only and requires normal human approval before either rule file changes; a retry records a one-time acknowledgement through the recurrence API.
  Preserve existing usage-limit pauses, fable fallback, Codex rerouting, SubagentOutput isolation, wave summaries, and Codex's rule against unsupported clear/compact/resume instructions.

### Task 5: Prove recurrence, retry, and host-parity behavior
- **mode:** A
- **target:** tests/test_recurrence.py
- **context_files:** []
- **complexity:** medium
- **executor:** codex
- **role:** test-writer
- **parallel_group:** 4
- **est_tokens:** 2200
- **est_cost_usd:** 0.0500
- **verifier:** .venv/bin/pytest -q tests/test_recurrence.py tests/test_scan.py tests/test_cross_host_dispatch_e2e.py
- **serves:** REQ-24
- **spec:**
  Add focused deterministic tests for the new recurrence module and its two integration surfaces.
  Cover stable-key/fingerprint compatibility with Scan; first versus second equivalent observations; within-run and cross-run counts; changed-fingerprint non-matches; corrupt ledger recovery; bounded pruning; atomic/lock degradation; and proof that raw signals/transcripts are absent from the persisted JSON.
  Cover deterministic remediation classification and acknowledge/resolve behavior for patch, durable guard, and one-time retry.
  Monkeypatch the Codex runner so repeated nonzero exits, lane violations, and verifier failures each launch at most two model attempts and surface a bounded remediation instead of a third call. Confirm usage-limit behavior remains unchanged.
  Pin the Orchestrate skill's host-neutral pre-attempt gate, recommended-first patch/guard/retry choices, approval requirement for rule edits, and Claude Code/Codex parity wording.

### Task 6: Add the authoritative Claude rule
- **mode:** B
- **target:** CLAUDE.md
- **context_files:** []
- **complexity:** simple
- **executor:** haiku
- **role:** docs-editor
- **parallel_group:** 5
- **est_tokens:** 350
- **est_cost_usd:** 0.0010
- **verifier:** python3 -c "from pathlib import Path; t=Path('CLAUDE.md').read_text(); assert 'Repeated-issue prevention' in t and 'third materially equivalent' in t and 'durable guard' in t" > /dev/null
- **serves:** REQ-24
- **spec:**
  Add a concise authoritative `Repeated-issue prevention` core rule.
  Require the recurrence ledger check before a third materially equivalent implementation/test attempt, bounded evidence to the user, and a concrete patch-or-durable-guard recommendation.
  State that no retry or rule edit happens silently, and that an approved durable guard must be mirrored in `CLAUDE.md` and `AGENTS.md`.
  Preserve every existing rule and the Codex host-context invariant.

### Task 7: Mirror the repeated-issue rule for Codex
- **mode:** B
- **target:** AGENTS.md
- **context_files:** []
- **complexity:** simple
- **executor:** haiku
- **role:** docs-editor
- **parallel_group:** 6
- **est_tokens:** 350
- **est_cost_usd:** 0.0010
- **verifier:** python3 -c "from pathlib import Path; t=Path('AGENTS.md').read_text(); assert 'Repeated-issue prevention' in t and 'third materially equivalent' in t and 'durable guard' in t" > /dev/null
- **serves:** REQ-24
- **spec:**
  Mirror the authoritative `Repeated-issue prevention` rule from the task specification in concise AGENTS.md language.
  Require the recurrence ledger check before a third materially equivalent implementation/test attempt, bounded evidence to the user, and a concrete patch-or-durable-guard recommendation.
  State that no retry or rule edit happens silently, and that an approved durable guard must be mirrored in `CLAUDE.md` and `AGENTS.md`.
  Preserve every existing rule and keep this file semantically synchronized with CLAUDE.md.

### Task 8: Propagate the Claude rule through project adoption
- **mode:** B
- **target:** plugin/templates/CLAUDE.md.template
- **context_files:** []
- **complexity:** simple
- **executor:** haiku
- **role:** docs-editor
- **parallel_group:** 5
- **est_tokens:** 350
- **est_cost_usd:** 0.0010
- **verifier:** python3 -c "from pathlib import Path; t=Path('plugin/templates/CLAUDE.md.template').read_text(); assert 'Repeated-issue prevention' in t and 'third materially equivalent' in t and 'durable guard' in t" > /dev/null
- **serves:** REQ-24
- **spec:**
  Add the same concise repeated-issue rule to the managed Claude project template so `/renmark:init` and setup propagate it.
  Keep the wording semantically identical to the root contract: check before a third equivalent attempt, show bounded evidence, recommend patch or durable guard, never silently retry or edit rules, and mirror approved guards.
  Preserve managed block markers and all existing template content.

### Task 9: Propagate the Codex rule through project adoption
- **mode:** B
- **target:** plugin/templates/AGENTS.md.template
- **context_files:** []
- **complexity:** simple
- **executor:** haiku
- **role:** docs-editor
- **parallel_group:** 6
- **est_tokens:** 350
- **est_cost_usd:** 0.0010
- **verifier:** python3 -c "from pathlib import Path; t=Path('plugin/templates/AGENTS.md.template').read_text(); assert 'Repeated-issue prevention' in t and 'third materially equivalent' in t and 'durable guard' in t" > /dev/null
- **serves:** REQ-24
- **spec:**
  Add the same concise repeated-issue rule to the managed AGENTS project template so Codex receives it during `/renmark:init` and setup.
  Keep the wording semantically identical to the root contract: check before a third equivalent attempt, show bounded evidence, recommend patch or durable guard, never silently retry or edit rules, and mirror approved guards.
  Preserve managed block markers and all existing template content.

## Cost preview

| Task | Executor | Estimated output tokens | Agent overhead | Estimated cost |
|---|---:|---:|---:|---:|
| 1 | sonnet | 700 | 10,000 | $0.0321 |
| 2 | sonnet | 1,800 | 10,000 | $0.0354 |
| 3 | sonnet | 900 | 10,000 | $0.0327 |
| 4 | haiku | 800 | 10,000 | $0.0011 |
| 5 | codex | 2,200 | 0 | $0.0500 |
| 6 | haiku | 350 | 10,000 | $0.0010 |
| 7 | haiku | 350 | 10,000 | $0.0010 |
| 8 | haiku | 350 | 10,000 | $0.0010 |
| 9 | haiku | 350 | 10,000 | $0.0010 |

**Estimated total: 87,800 tokens including agent overhead; approximately $0.1553.**
No Opus or Fable escalation is required. A cheaper single-agent edit would save dispatch overhead but would weaken file isolation, parallel verification, and host-parity review.

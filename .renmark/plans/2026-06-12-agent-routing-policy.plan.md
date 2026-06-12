---
artifact_type: plan
schema_version: 1
created_at: 2026-06-12T14:10:00+00:00
source_sha: e96db7a
related_spec: PRD.md#REQ-2 (owner AGENT REASONING + ROUTING POLICY, 2026-06-12)
generator: fable
dependency_refs: [.renmark/research/2026-06-11-fable-routing-strategy.md]
---

# agent-routing-policy — reasoning contract + fable QA lanes + policy rows

**Goal:** codify the owner's AGENT REASONING + ROUTING POLICY as renmark contracts:
(1) a shared reasoning/output-discipline contract injected into every dispatched subagent
prompt; (2) fable sub-agent lanes for the four role groups (PRD, brainstorm synthesis,
QA review, deep/adversarial QA) in declared projects, with interactive loops staying on
the session brain (judge-pinned); (3) default-model/effort policy rows (session default —
Opus/medium — for coding/planning/dispatch; fable only for the role groups); (4) browser
-validation instruction for QA subagents (Chrome DevTools MCP — renmark's channel; "do
not rely on static inspection when UI is in the acceptance criteria").

**Canonical reasoning instruction (verbatim, single source in the new shared file):**
"Before concluding, break the problem into multiple perspectives or interpretations;
explicitly list assumptions and potential edge cases; then synthesize the final answer
from the most robust reasoning path. Mark each issue blocking vs deferrable. Separate
findings from recommendations. Preserve evidence (file paths, commands, test output).
If context is incomplete, state what is missing instead of guessing. Confidence is not
completion."

**Out of scope:** no Python/schema changes (SubagentOutput untouched — the discipline is
prompt-level); no Playwright install (browser channel stays Chrome DevTools MCP); no
change to plan_lint gates or capabilities.py; interactive brainstorm/prd loops never
dispatch per-checkpoint fable calls.

### Task 1: shared reasoning contract
- **mode:** A
- **target:** plugin/skills/_shared/reasoning-contract.md
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 1
- **est_tokens:** 600
- **est_cost_usd:** 0.032
- **verifier:** grep -qi 'blocking' plugin/skills/_shared/reasoning-contract.md && grep -qi 'perspectives' plugin/skills/_shared/reasoning-contract.md
- **serves:** REQ-2
- **spec:**
  NEW shared reference file modeled on _shared/prd-alignment.md (header explaining what it
  is + who consumes it + a citable blockquote). Content: the canonical reasoning
  instruction from the plan header (verbatim), the output-discipline list (blocking vs
  deferrable; findings vs recommendations; evidence paths; missing-context statement;
  confidence ≠ completion mapped to the existing G9 fields), and the browser-validation
  clause: "QA subagents validating UI acceptance criteria are explicitly told they have
  browser automation access via the Chrome DevTools MCP and MUST NOT rely on static code
  inspection alone." Provide ONE citable blockquote skills paste into dispatch prompts
  (like prd-alignment's Dispatch reference). Note `_shared/` is linter-skipped.

### Task 2: orchestrate — inject the contract into dispatch prompts
- **mode:** B
- **target:** plugin/skills/orchestrate/SKILL.md
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 2
- **est_tokens:** 350
- **est_cost_usd:** 0.031
- **verifier:** grep -qi 'reasoning-contract' plugin/skills/orchestrate/SKILL.md
- **serves:** REQ-2
- **spec:**
  In Step 3b where the Agent prompt contract is defined ("The Agent prompt MUST instruct
  the subagent:"), add one requirement line: every dispatched subagent prompt ALSO
  includes the reasoning/output-discipline blockquote from
  `${CLAUDE_PLUGIN_ROOT}/skills/_shared/reasoning-contract.md` (cite, never paste the
  file body). Note it applies to BOTH Agent-path and codex ad-hoc task specs. No other
  changes; RED-FLAG rules and reroute/fallback sections untouched.

### Task 3: verify — fable QA review lane + browser instruction
- **mode:** B
- **target:** plugin/skills/verify/SKILL.md
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 2
- **est_tokens:** 500
- **est_cost_usd:** 0.032
- **verifier:** grep -qi 'fable' plugin/skills/verify/SKILL.md
- **serves:** REQ-2
- **spec:**
  Two additive edits. (1) New optional lane note after Smoke mode: in declared projects
  (`capabilities.top_tier == fable`), the hand-off MAY offer a **fable QA-review subagent**
  — implementation review vs the plan goal + acceptance criteria, regression-risk and
  edge-case review — dispatched per the reasoning-contract blockquote, returning a bounded
  ≤5-line verdict with blocking-vs-deferrable marking; evidence to a `.renmark/reviews/`
  artifact. Deterministic smoke remains the always-run default; the fable pass is
  additive, never replaces verifiers (REQ-7). (2) In QA/deep-QA modes: the browser-access
  instruction — QA subagents (when any are used) and the in-main browser flows are
  explicitly noted as having Chrome DevTools MCP access and must not rely on static
  inspection when UI is part of acceptance criteria (cite reasoning-contract.md).

### Task 4: codereview + finish — deep adversarial release gate
- **mode:** B
- **target:** plugin/skills/finish/SKILL.md
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 2
- **est_tokens:** 400
- **est_cost_usd:** 0.031
- **verifier:** grep -qi 'fable' plugin/skills/finish/SKILL.md
- **serves:** REQ-2
- **spec:**
  In finish Step 1 (re-run verifiers), add an optional **release-readiness adversarial
  pass** for declared projects before the [r] Release path: a fable subagent reviewing the
  branch diff summary + verification/review artifacts for subtle logic flaws,
  orchestration failure points, hidden coupling / dead-or-orphan code — dispatched per the
  reasoning-contract blockquote, bounded ≤5-line verdict, blocking findings stop the
  release path (route to debug), deferrable ones are logged to bugs.md. Recommended
  (not automatic) for release-tagged closes; cite reasoning-contract.md.

### Task 5: prd + brainstorm — non-interactive fable subagent lanes
- **mode:** B
- **target:** plugin/skills/prd/SKILL.md
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 2
- **est_tokens:** 400
- **est_cost_usd:** 0.031
- **verifier:** grep -qi 'fable' plugin/skills/prd/SKILL.md
- **serves:** REQ-2
- **spec:**
  Additive note in UPDATE mode step 2 (reconcile): in declared projects the
  reconcile-and-diff analysis (ambiguity detection, dependency mapping, conflict checks
  against non-goals) MAY be dispatched as a single non-interactive **fable subagent**
  (full PRD body + requested change in one bounded call, per the judge-grafted pilot),
  returning the proposed diff + ≤5-line rationale; the human gate and write flow are
  unchanged. Interactive CREATE interviews stay on the session brain (never
  per-checkpoint fable calls). Cite reasoning-contract.md for the dispatch prompt.

### Task 6: brainstorm — fable approach-synthesis option
- **mode:** B
- **target:** plugin/skills/brainstorm/SKILL.md
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 2
- **est_tokens:** 400
- **est_cost_usd:** 0.031
- **verifier:** grep -qi 'reasoning-contract' plugin/skills/brainstorm/SKILL.md
- **serves:** REQ-2
- **spec:**
  Additive note at Step 4 (propose approaches): in declared projects where the session is
  NOT running on Fable (no /model fable), Step 4's architecture-options/risk-discovery
  synthesis MAY be dispatched as ONE non-interactive fable subagent (inputs: the Step 2
  answers summary + Step 3 research summaries; output: 2-3 approaches w/ trade-offs +
  risks, ≤10 bounded lines) which the session brain then presents. When the session IS
  Fable, inline as today. The one-question-at-a-time loop is never dispatched. All
  dispatches cite reasoning-contract.md.

### Task 7: routing.md — policy rows
- **mode:** B
- **target:** .renmark/memory/routing.md
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 2
- **est_tokens:** 200
- **est_cost_usd:** 0.001
- **verifier:** grep -qi 'effort' .renmark/memory/routing.md
- **serves:** REQ-2
- **spec:**
  In the Defaults section, after the existing fable escalation row, add two rows:
  `- (signal=normal-coding|planning|dispatch|implementation|documentation, effort=medium) → session default (opus/medium) — do not overthink dispatch unless routing itself is uncertain`
  `- (signal=qa-review|regression-review|edge-case-review|acceptance-validation|release-readiness|adversarial-qa, stakes=high) → fable subagent (declared projects; reasoning-contract applies)`
  Touch nothing else (Model tiers and Learned overrides stay byte-identical).

### Task 8: CLAUDE.md + template — policy pointer line
- **mode:** B
- **target:** CLAUDE.md
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 2
- **est_tokens:** 200
- **est_cost_usd:** 0.001
- **verifier:** grep -qi 'reasoning-contract' CLAUDE.md
- **serves:** REQ-2
- **spec:**
  In the Executor preferences Defaults list, append one line after the Frontier-reasoning
  row: `- Subagent dispatch prompts carry the reasoning/output-discipline contract — see
  plugin/skills/_shared/reasoning-contract.md (multi-perspective → assumptions/edge cases
  → synthesis; blocking vs deferrable; findings vs recommendations).` MIRROR: Task 9
  applies the identical line to the CLAUDE template; AGENTS.md has no preferences block —
  nothing there.

### Task 9: CLAUDE.md.template — mirror of Task 8
- **mode:** B
- **target:** plugin/templates/CLAUDE.md.template
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 2
- **est_tokens:** 150
- **est_cost_usd:** 0.001
- **verifier:** grep -qi 'reasoning-contract' plugin/templates/CLAUDE.md.template
- **serves:** REQ-2
- **spec:**
  Apply Task 8's exact appended line to the template's Executor preferences Defaults list
  (byte-identical wording). Only this file.

## Cost preview

| # | Task | Executor | est_tokens | est cost |
|---|---|---|---|---|
| 1 | reasoning contract (new shared file) | sonnet | 600 | $0.032 |
| 2 | orchestrate prompt injection | sonnet | 350 | $0.031 |
| 3 | verify fable QA lane + browser note | sonnet | 500 | $0.032 |
| 4 | finish release-readiness gate | sonnet | 400 | $0.031 |
| 5 | prd fable reconcile lane | sonnet | 400 | $0.031 |
| 6 | brainstorm fable synthesis option | sonnet | 400 | $0.031 |
| 7 | routing.md policy rows | haiku | 200 | $0.001 |
| 8 | CLAUDE.md pointer | haiku | 200 | $0.001 |
| 9 | CLAUDE template mirror | haiku | 150 | $0.001 |

Haiku/sonnet costs include the ~10k-token Agent overhead per task (honest accounting).
**Total: ~$0.19 · ~93k tokens incl. overhead · 9 tasks (wave 1: 1, wave 2: 8 parallel)**

---
artifact_type: plan
schema_version: 1
created_at: 2026-06-10T19:40:00+00:00
source_sha: c0860c5
related_spec: PRD.md#REQ-2 (2026-06-10 amendment)
generator: fable
part: 2 of 2
dependency_refs: [.renmark/plans/2026-06-10-fable-integration-part1.plan.md]
---

# fable-integration — Part 2: prose + doc sync

**Depends on Part 1** (engine + tests). This part syncs every prose surface that enumerates
the executor set or assigns model roles, per the REQ-2 amendment. Canonical role language
(reuse verbatim where a role row is added): *"Fable (`claude-fable-5`) — top capability
tier above opus; escalation target reserved for ideation, strategy synthesis, and
adversarial audit/review passes — never mechanical or bulk work. $0.030/kT (2× opus)."*

**Dispatch-rule canonical wording** (CLAUDE.md/AGENTS.md/templates): haiku/sonnet/opus
Agent calls stay as-is (no model override — they inherit or downshift per existing rules);
`executor: fable` dispatches as an **Agent tool call with `model: "fable"`** — the one
executor that always passes an explicit model override. Never dispatch fable work as a
codex subprocess.

**Frontmatter caution:** descriptions containing `: ` MUST stay quoted (strict-YAML lint is
a hard precommit/CI gate). When editing any SKILL.md/command description, preserve existing
quoting style.

**Mirror rule:** CLAUDE.md and AGENTS.md (tasks 8–9) are a mirror pair — land them in the
same wave/commit so they never diverge; same for the two templates (tasks 10–11).

### Task 1: plan skill — routing + cost tables
- **mode:** B
- **target:** plugin/skills/plan/SKILL.md
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 1
- **est_tokens:** 800
- **est_cost_usd:** 0.032
- **verifier:** grep -q 'fable' plugin/skills/plan/SKILL.md
- **serves:** REQ-2
- **spec:**
  Four edits. (1) Frontmatter description: extend "(haiku, codex, sonnet, opus)" to
  "(haiku, codex, sonnet, opus, fable)". (2) Step 4 routing table (lines 103–108): add a
  new TOP row above the opus row:
  `| frontier reasoning: ideation/strategy synthesis, adversarial audit/review passes, architecture where opus is insufficient — escalation only, never default | \`fable\` |`
  Leave the opus row unchanged. (3) Step 4 complexity mapping line (~110): append
  "; `fable` is never auto-assigned by complexity alone — only by explicit escalation
  signals (REQ-2)". (4) Step 6 cost table (lines 120–126): add row
  `| \`fable\`  | $0.030  | + 10k tokens | top reasoning tier — 2× opus; escalation only |`
  after the opus row. Use the canonical role language from the plan header.

### Task 2: plan command shim
- **mode:** B
- **target:** plugin/commands/plan.md
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 1
- **est_tokens:** 150
- **est_cost_usd:** 0.001
- **verifier:** grep -q 'fable' plugin/commands/plan.md
- **serves:** REQ-2
- **spec:**
  Line 2 description: change "(haiku, codex, sonnet, opus)" to
  "(haiku, codex, sonnet, opus, fable)". Keep the description otherwise byte-identical to
  plugin/skills/plan/SKILL.md's frontmatter description (they are kept in sync).

### Task 3: orchestrate skill — dispatch table
- **mode:** B
- **target:** plugin/skills/orchestrate/SKILL.md
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 1
- **est_tokens:** 500
- **est_cost_usd:** 0.032
- **verifier:** grep -q 'fable' plugin/skills/orchestrate/SKILL.md
- **serves:** REQ-2
- **spec:**
  Three edits. (1) Dispatch-path table (~line 11): row
  `| \`haiku\`, \`sonnet\`, \`opus\` | Agent tool calls (no model override) | Claude Code account ... |`
  becomes two rows — keep the existing haiku/sonnet/opus row as-is, and add
  `| \`fable\` | Agent tool call with \`model: "fable"\` override | Claude Code account (Anthropic subscription) |`.
  (2) The agent-call ledger snippet comment (~line 198) `# 'haiku' | 'sonnet' | 'opus'`
  → `# 'haiku' | 'sonnet' | 'opus' | 'fable'`. (3) Wherever the prose enumerates the
  Claude-executor set, include fable. Do NOT alter the codex RED-FLAG rule (a fable task
  must never run as a codex subprocess, and a codex task never as an Agent call).

### Task 4: brainstorm skill — Fable as ideator
- **mode:** B
- **target:** plugin/skills/brainstorm/SKILL.md
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 1
- **est_tokens:** 300
- **est_cost_usd:** 0.031
- **verifier:** grep -qi 'fable' plugin/skills/brainstorm/SKILL.md
- **serves:** REQ-2
- **spec:**
  Frontmatter description currently says "Asks one question at a time using Opus" — change
  to "Asks one question at a time using the session's top reasoning tier (Fable 5 when
  available, Opus otherwise)". If the body prose names Opus as the ideation model, update
  those mentions the same way. Preserve frontmatter quoting. Do not change any other
  behavior.

### Task 5: brainstorm command shim
- **mode:** B
- **target:** plugin/commands/brainstorm.md
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 1
- **est_tokens:** 150
- **est_cost_usd:** 0.001
- **verifier:** grep -qi 'fable' plugin/commands/brainstorm.md
- **serves:** REQ-2
- **spec:**
  Line 2 description: apply the identical wording change as
  plugin/skills/brainstorm/SKILL.md ("using Opus" → "using the session's top reasoning tier
  (Fable 5 when available, Opus otherwise)"). Keep the two descriptions byte-identical.

### Task 6: codereview skill — adversarial escalation note
- **mode:** B
- **target:** plugin/skills/codereview/SKILL.md
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 1
- **est_tokens:** 250
- **est_cost_usd:** 0.031
- **verifier:** grep -qi 'fable' plugin/skills/codereview/SKILL.md
- **serves:** REQ-2
- **spec:**
  Additive only. In the body (near where review escalation/`--full` is described), add a
  short note: for the highest-stakes diffs (release-gating, security-sensitive, or
  engine/state code), adversarial verification subagents MAY be dispatched on `fable`
  (Agent tool, `model: "fable"`) to refute findings before they ship — REQ-2 escalation,
  never the default review path. The codex read-only sandbox pass and the bounded
  severity-summary contract are unchanged. Do NOT edit the frontmatter description (it is
  quoted; leave it byte-identical).

### Task 7: audit skill — adversarial escalation note
- **mode:** B
- **target:** plugin/skills/audit/SKILL.md
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 1
- **est_tokens:** 250
- **est_cost_usd:** 0.031
- **verifier:** grep -qi 'fable' plugin/skills/audit/SKILL.md
- **serves:** REQ-2
- **spec:**
  Additive only. Where the skill describes its read-only verification subagents/passes,
  add: delta/adversarial audit re-runs (the "refute each finding" pattern, as used for the
  v0.9.0 delta audit) SHOULD route refutation subagents to `fable` (Agent tool,
  `model: "fable"`) — Fable is the designated adversarial-audit tier per REQ-2. The audit
  remains read-only and artifact-bounded; no behavior change beyond the routing
  recommendation.

### Task 8: CLAUDE.md — dispatch rules + preferences + tooling row
- **mode:** B
- **target:** CLAUDE.md
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 2
- **est_tokens:** 400
- **est_cost_usd:** 0.031
- **verifier:** grep -q 'fable' CLAUDE.md
- **serves:** REQ-2
- **spec:**
  Three anchored edits. (1) Line 87 ("Executor dispatch rules" block): after the line
  `- \`executor: haiku / sonnet / opus\` → Agent tool calls, no model override.` add
  `- \`executor: fable\` → Agent tool call WITH \`model: "fable"\` override — the only executor that always passes an explicit model override. Escalation tier (REQ-2): ideation, strategy synthesis, adversarial audit/review only — never mechanical or bulk work.`
  (2) "Executor preferences" defaults list (Defaults section): add
  `- Frontier reasoning — ideation, strategy synthesis, adversarial audit/review escalation → \`fable\` (escalation only, never default)`
  after the opus row. (3) Line 372 tooling table: orchestrate row "routes tasks to
  Haiku / Codex / Sonnet / Opus" → "... / Opus / Fable". MIRROR: identical edits land in
  AGENTS.md (Task 9) in the same wave — keep wording byte-identical where the blocks match.

### Task 9: AGENTS.md — mirror of Task 8
- **mode:** B
- **target:** AGENTS.md
- **complexity:** medium
- **executor:** sonnet
- **parallel_group:** 2
- **est_tokens:** 300
- **est_cost_usd:** 0.031
- **verifier:** grep -q 'fable' AGENTS.md
- **serves:** REQ-2
- **spec:**
  Mirror Task 8 into AGENTS.md: update the orchestrate tooling row (line 76,
  "Haiku / Codex / Sonnet / Opus" → "... / Opus / Fable") and apply the same
  dispatch-rule/executor-preference additions to whichever of those blocks exist in this
  file (AGENTS.md may carry a subset — edit every executor enumeration present; add
  nothing that has no anchor). Keep shared wording byte-identical with CLAUDE.md.

### Task 10: CLAUDE.md.template — mirror blocks
- **mode:** B
- **target:** plugin/templates/CLAUDE.md.template
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 2
- **est_tokens:** 200
- **est_cost_usd:** 0.001
- **verifier:** grep -q 'fable' plugin/templates/CLAUDE.md.template
- **serves:** REQ-2
- **spec:**
  Same two anchored edits as CLAUDE.md where they exist in the template: line 87 dispatch
  rules (add the fable Agent-call-with-override line, wording byte-identical to Task 8) and
  line 372 orchestrate row ("Haiku / Codex / Sonnet / Opus" → "... / Opus / Fable"). If the
  template carries an Executor-preferences defaults list, add the same fable row there too.

### Task 11: AGENTS.md.template — mirror row
- **mode:** B
- **target:** plugin/templates/AGENTS.md.template
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 2
- **est_tokens:** 150
- **est_cost_usd:** 0.001
- **verifier:** grep -q 'fable' plugin/templates/AGENTS.md.template
- **serves:** REQ-2
- **spec:**
  Line 66 orchestrate row: "routes tasks to Haiku / Codex / Sonnet / Opus" →
  "... / Opus / Fable". Apply the same edit to any other executor enumeration present in
  this template; add nothing that has no existing anchor.

### Task 12: README executor row
- **mode:** B
- **target:** README.md
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 2
- **est_tokens:** 100
- **est_cost_usd:** 0.001
- **verifier:** grep -q 'Fable' README.md
- **serves:** REQ-2
- **spec:**
  Line 105 orchestrate row: "(Haiku / Codex / Sonnet / Opus, wave-parallel)" →
  "(Haiku / Codex / Sonnet / Opus / Fable, wave-parallel)". No other README changes.

### Task 13: routing.md fable default
- **mode:** B
- **target:** .renmark/memory/routing.md
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 2
- **est_tokens:** 120
- **est_cost_usd:** 0.001
- **verifier:** grep -q 'fable' .renmark/memory/routing.md
- **serves:** REQ-2
- **spec:**
  In the "## Defaults (until experience accumulates)" list, add one line after the opus
  signal row:
  `- (signal=ideation|strategy-synthesis|adversarial-audit|refutation-pass, stakes=highest) → fable (escalation only — REQ-2)`
  Do not touch the Learned overrides section.

### Task 14: check-plan skill — heavy-read set mirror
- **mode:** B
- **target:** plugin/skills/check-plan/SKILL.md
- **complexity:** simple
- **executor:** haiku
- **parallel_group:** 1
- **est_tokens:** 150
- **est_cost_usd:** 0.001
- **verifier:** grep -q 'fable' plugin/skills/check-plan/SKILL.md
- **serves:** REQ-2
- **spec:**
  Mirror-contract edit (v0.10.0 guard: plan_lint severities mirror check-plan SKILL §1–2.5
  — change both sides together). Line 54: check 4 reads
  `No context_file > 200 lines with \`executor: sonnet|opus\` (G5) → **BLOCK**`
  — change `sonnet|opus` to `sonnet|opus|fable` (matches Part 1 Task 3's
  `_HEAVY_READ_BLOCK_EXECUTORS` change). Line 66: the report example
  `Tasks: N  Executors: haiku×a codex×b sonnet×c opus×d` — append ` fable×e`.
  No other changes.

## Cost preview — Part 2

| # | Task | Executor | est_tokens | est cost |
|---|---|---|---|---|
| 1 | plan SKILL tables | sonnet | 800 | $0.032 |
| 2 | plan cmd shim | haiku | 150 | $0.001 |
| 3 | orchestrate SKILL | sonnet | 500 | $0.032 |
| 4 | brainstorm SKILL | sonnet | 300 | $0.031 |
| 5 | brainstorm cmd shim | haiku | 150 | $0.001 |
| 6 | codereview SKILL | sonnet | 250 | $0.031 |
| 7 | audit SKILL | sonnet | 250 | $0.031 |
| 8 | CLAUDE.md | sonnet | 400 | $0.031 |
| 9 | AGENTS.md | sonnet | 300 | $0.031 |
| 10 | CLAUDE template | haiku | 200 | $0.001 |
| 11 | AGENTS template | haiku | 150 | $0.001 |
| 12 | README | haiku | 100 | $0.001 |
| 13 | routing.md | haiku | 120 | $0.001 |

Haiku/sonnet costs include the ~10k-token Agent overhead per task (honest accounting).
**Part 2 total: ~$0.23 · ~134k tokens · 13 tasks (wave 1: 7 parallel, wave 2: 6 parallel)**

---

**Feature total (both parts): 22 tasks · ~$0.34 · ~187k tokens (incl. Agent overhead) ·
executors: haiku×11, codex×4, sonnet×7, opus×0, fable×0** — no task in this plan needs
fable itself; REQ-2's cheapest-capable rule applies to renmark's own build too.
